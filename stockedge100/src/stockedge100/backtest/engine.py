"""The session loop.

The whole of the engine's honesty is in the order of the steps below, so they are written once, here,
and every run takes exactly this path through a session *s*:

1. **Dividends** are credited on the position held *entering* ``s`` — before any of this session's
   fills. A buyer at the ex-date open pays the already-dropped price and does not receive the
   dividend; a seller at that open held the shares when the market opened and does.
2. **Fills** execute at the open of ``s``, for orders decided at the close of an earlier session.
3. **Corporate-action continuity** is asserted: a split on an already split-adjusted series must not
   have changed the share count.
4. **Delisting**: a symbol whose series ends at ``s`` while the run continues is liquidated at that
   final close.
5. **Marks** are taken at the close of ``s`` and one equity point is recorded.
6. **Risk**: the drawdown high-water mark is updated and the research shutdown may trigger.
7. **Decisions** are taken at the close of ``s``, from a market view that cannot see past ``s``, and
   the resulting orders are scheduled for the *next* exchange session.

Step 7 is last on purpose. Everything a decision can see has already happened; nothing that happens
after it can reach back.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Protocol

from stockedge100.audit import sha256_text_canonical_json
from stockedge100.backtest.costs import BASE, CostModel, ZERO, Fill, exact
from stockedge100.backtest.dataset import PriceSeries
from stockedge100.backtest.errors import (
    CorporateActionError,
    DataIntegrityHalt,
    DelistingError,
    DuplicateOrderError,
    InvariantViolation,
)
from stockedge100.backtest.market import MarketView
from stockedge100.backtest.orders import (
    BUY,
    SELL,
    Order,
    OrderBook,
    Rejection,
    make_order_id,
    next_session_after,
)
from stockedge100.backtest.portfolio import Portfolio, Trade
from stockedge100.backtest.window import ResearchWindow
from stockedge100.data.calendar import sessions_between


class Probe(Protocol):
    """An engine test instrument.

    Deliberately *not* called a strategy. Constitution §8 governs strategies; a probe has no signal,
    no parameter, and no fitting, and Stage 2 draws no conclusion from what one returns.
    """

    name: str

    def decide(self, view: MarketView, context: "DecisionContext") -> list["OrderRequest"]:
        ...


@dataclass(frozen=True)
class OrderRequest:
    """What a probe may ask for. It cannot name a fill session; the engine computes that."""

    symbol: str
    side: str
    budget: Decimal | None = None
    quantity: Decimal | None = None
    tag: str = ""


@dataclass(frozen=True)
class DecisionContext:
    """What a probe is told about the account at the moment it decides."""

    session: dt.date
    cash: Decimal
    equity: Decimal
    open_symbols: tuple[str, ...]
    shutdown_active: bool


@dataclass(frozen=True)
class EquityPoint:
    session: dt.date
    cash: Decimal
    equity: Decimal
    stale_mark: bool
    position_count: int

    def to_json(self) -> dict[str, Any]:
        return {
            "session": self.session.isoformat(),
            "cash": f"{self.cash:f}",
            "equity": f"{self.equity:f}",
            "stale_mark": self.stale_mark,
            "position_count": self.position_count,
        }


@dataclass(frozen=True)
class FillRecord:
    session: dt.date
    order_id: str
    fill: Fill

    def to_json(self) -> dict[str, Any]:
        return {"session": self.session.isoformat(), "order_id": self.order_id, **self.fill.to_json()}


@dataclass
class BacktestResult:
    label: str
    scenario: str
    symbols: tuple[str, ...]
    start: dt.date
    end: dt.date
    equity_curve: list[EquityPoint]
    fills: list[FillRecord]
    rejections: list[Rejection]
    trades: list[Trade]
    dividend_events: list[dict[str, str]]
    stale_marks: int
    shutdown_session: dt.date | None
    starting_equity: Decimal
    final_cash: Decimal
    final_equity: Decimal
    open_positions: list[dict[str, str]]
    cost_model: dict[str, str]

    # -- deterministic identity ------------------------------------------------------------------

    def trades_payload(self) -> list[dict[str, Any]]:
        """Everything a rerun must reproduce about the trading, and nothing else.

        No run id, no timestamp, no path: a digest that included one of those would compare equal to
        nothing and would prove nothing about determinism.
        """
        return [
            {"fills": [f.to_json() for f in self.fills]},
            {"trades": [t.to_json() for t in self.trades]},
            {"rejections": [r.to_json() for r in self.rejections]},
        ]

    def equity_payload(self) -> list[dict[str, Any]]:
        return [point.to_json() for point in self.equity_curve]

    def trades_digest(self) -> str:
        return sha256_text_canonical_json(self.trades_payload())

    def equity_digest(self) -> str:
        return sha256_text_canonical_json(self.equity_payload())

    def to_json(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "scenario": self.scenario,
            "symbols": list(self.symbols),
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "sessions": len(self.equity_curve),
            "starting_equity": f"{self.starting_equity:f}",
            "final_cash": f"{self.final_cash:f}",
            "final_equity": f"{self.final_equity:f}",
            "total_return": f"{self.total_return():f}",
            "fills": len(self.fills),
            "closed_trades": len(self.trades),
            "rejections": [r.to_json() for r in self.rejections],
            "dividend_events": self.dividend_events,
            "stale_marks": self.stale_marks,
            "research_shutdown_session": (
                None if self.shutdown_session is None else self.shutdown_session.isoformat()
            ),
            "open_positions": self.open_positions,
            "cost_model": self.cost_model,
            "trades_digest": self.trades_digest(),
            "equity_digest": self.equity_digest(),
        }

    @exact
    def total_return(self) -> Decimal:
        return self.final_equity / self.starting_equity - Decimal(1)


class BacktestEngine:
    """Runs one probe over one window under one cost scenario."""

    def __init__(
        self,
        series: dict[str, PriceSeries],
        cost_model: CostModel,
        window: ResearchWindow,
        probe: Probe,
        *,
        start: dt.date | None = None,
        end: dt.date | None = None,
        label: str = "",
        enforce_research_shutdown: bool = True,
    ) -> None:
        self.series = dict(sorted(series.items()))
        self.costs = cost_model
        self.window = window
        self.probe = probe
        self.label = label or probe.name

        # Constitution §5.1 puts the 15% research shutdown on a *strategy*, and the sealed benchmark
        # note says only that the tradable reference run carries the full cost model. A benchmark is
        # not a strategy, so the reading is genuinely ambiguous — and the ambiguity was noticed from
        # a result, which is exactly when a modelling choice must not be made quietly. So the flag
        # exists, defaults to enforcing, is set False only by an explicitly labelled benchmark
        # reference account, and both variants are reported side by side.
        self.enforce_research_shutdown = enforce_research_shutdown

        self.start = window.check(start or window.start, what="run start")
        self.end = window.check(end or window.end, what="run end")
        if self.end < self.start:
            raise InvariantViolation(f"run end {self.end} precedes run start {self.start}")

        self.portfolio = Portfolio(
            cost_model.starting_equity, max_positions=cost_model.max_open_risky_positions
        )
        self._scheduled: dict[dt.date, list[Order]] = {}
        self._books: dict[dt.date, OrderBook] = {}
        self._fills: list[FillRecord] = []
        self._rejections: list[Rejection] = []
        self._equity: list[EquityPoint] = []
        self._dividends: list[dict[str, str]] = []
        self._last_close: dict[str, Decimal] = {}
        self._stale_run: dict[str, int] = {}
        self._stale_marks = 0
        self._delisted: set[str] = set()
        self._shutdown_session: dt.date | None = None
        self._high_water = cost_model.starting_equity

    # -- helpers ---------------------------------------------------------------------------------

    def _reject(self, order: Order, reason: str, detail: str = "") -> None:
        """Record a rejection. It changes nothing else — that is the whole contract."""
        self._rejections.append(Rejection(order=order, reason=reason, detail=detail))

    def _in_range(self, symbol: str, session: dt.date) -> bool:
        s = self.series[symbol]
        return s.first_session <= session <= s.last_session

    def _mark(self, symbol: str, session: dt.date) -> tuple[Decimal, bool]:
        """The close to mark a position at, and whether it is stale."""
        bar = self.series[symbol].get(session)
        if bar is not None:
            self._last_close[symbol] = bar.close
            return bar.close, False
        known = self._last_close.get(symbol)
        if known is None:
            raise DataIntegrityHalt(
                f"{symbol}: no price has ever been seen but a mark is required on "
                f"{session.isoformat()}"
            )
        return known, True

    # -- session steps ---------------------------------------------------------------------------

    @exact
    def _credit_dividends(self, session: dt.date) -> None:
        for symbol in self.portfolio.open_symbols():
            bar = self.series[symbol].get(session)
            if bar is None or not bar.has_dividend:
                continue
            quantity = self.portfolio.quantity_of(symbol)
            cash = self.costs.dividend_cash(quantity, bar.dividend)
            self.portfolio.record_dividend(session, symbol, cash)
            self._dividends.append(
                {
                    "session": session.isoformat(),
                    "symbol": symbol,
                    "amount_per_share": f"{bar.dividend:f}",
                    "quantity": f"{quantity:f}",
                    "cash_credited": f"{cash:f}",
                }
            )

    @exact
    def _execute(self, session: dt.date) -> None:
        for order in self._scheduled.pop(session, []):
            self._execute_one(session, order)

    @exact
    def _execute_one(self, session: dt.date, order: Order) -> None:
        if order.fill_session != session:
            raise InvariantViolation(
                f"{order.order_id}: scheduled for {order.fill_session} but executed on {session}"
            )
        if order.fill_session <= order.decision_session:
            raise InvariantViolation(
                f"FILL_AFTER_DECISION: {order.order_id} would fill on or before its decision session"
            )

        symbol = order.symbol
        if symbol in self._delisted or session > self.series[symbol].last_session:
            # Past the end of the symbol's own data the correct reason is DELISTED, not STALE_PRICE.
            # A stale price is one that will be refreshed; this one never will be.
            self._reject(order, "DELISTED", f"{symbol} has no further sessions")
            return

        bar = self.series[symbol].get(session)
        if bar is None:
            self._reject(
                order,
                "STALE_PRICE",
                f"{symbol} has no bar on {session.isoformat()}; the sealed model permits "
                f"{self.costs.max_stale_sessions_for_fill} stale session(s) for a fill",
            )
            return

        if order.side == BUY:
            self._execute_buy(session, order, bar.open)
        else:
            self._execute_sell(session, order, bar.open)

    @exact
    def _execute_buy(self, session: dt.date, order: Order, reference: Decimal) -> None:
        if self._shutdown_session is not None:
            self._reject(order, "RESEARCH_SHUTDOWN", "entries are blocked after a research shutdown")
            return
        symbol = order.symbol
        held = self.portfolio.open_symbols()
        if symbol not in held and len(held) >= self.costs.max_open_risky_positions:
            self._reject(order, "MAX_POSITIONS", f"already holding {len(held)} position(s)")
            return

        marks = {s: self._mark(s, session)[0] for s in held}
        equity = self.portfolio.equity(marks)
        cash = self.portfolio.cash

        exposure_cap = self.costs.max_gross_exposure_fraction * equity
        cash_floor = self.costs.min_cash_buffer_fraction * equity
        budget = min(order.budget or ZERO, exposure_cap, cash - cash_floor, cash)
        if budget <= ZERO:
            self._reject(order, "INSUFFICIENT_CASH", f"budget resolved to {budget} from cash {cash}")
            return

        effective = self.costs.effective_buy_price(reference)
        quantity = self.costs.solve_buy_quantity(budget, effective)
        if quantity < self.costs.min_order_shares:
            self._reject(order, "ZERO_QUANTITY", f"budget {budget} buys nothing at {effective}")
            return

        fill = self.costs.buy_fill(symbol, quantity, reference)
        if fill.gross_notional < self.costs.min_order_notional:
            self._reject(
                order,
                "MIN_NOTIONAL",
                f"notional {fill.gross_notional} is below the sealed minimum "
                f"{self.costs.min_order_notional}",
            )
            return
        if -fill.cash_delta > cash:
            self._reject(order, "INSUFFICIENT_CASH", f"needs {-fill.cash_delta}, has {cash}")
            return

        self.portfolio.apply_fill(session, fill)
        self._fills.append(FillRecord(session=session, order_id=order.order_id, fill=fill))

    @exact
    def _execute_sell(self, session: dt.date, order: Order, reference: Decimal) -> None:
        symbol = order.symbol
        held = self.portfolio.quantity_of(symbol)
        if held <= ZERO:
            self._reject(order, "INSUFFICIENT_POSITION", f"no position in {symbol}")
            return
        quantity = held if order.quantity is None else order.quantity
        if quantity > held:
            self._reject(order, "INSUFFICIENT_POSITION", f"asked {quantity}, holds {held}")
            return
        if quantity <= ZERO:
            self._reject(order, "ZERO_QUANTITY", f"sell quantity resolved to {quantity}")
            return

        fill = self.costs.sell_fill(symbol, quantity, reference)
        if fill.gross_notional < self.costs.min_order_notional:
            self._reject(
                order,
                "MIN_NOTIONAL",
                f"proceeds {fill.gross_notional} are below the sealed minimum "
                f"{self.costs.min_order_notional}",
            )
            return

        self.portfolio.apply_fill(session, fill)
        self._fills.append(FillRecord(session=session, order_id=order.order_id, fill=fill))

    def _assert_corporate_action_continuity(
        self, session: dt.date, before: dict[str, Decimal], after: dict[str, Decimal]
    ) -> None:
        """A split on an already split-adjusted series must not move the share count.

        The check is separate from the code that applies corporate actions on purpose: a mutation
        injected into the applier is caught here, by an assertion that does not share a line of code
        with it.
        """
        for symbol in sorted(set(before) | set(after)):
            bar = self.series[symbol].get(session)
            if bar is None or not bar.has_split:
                continue
            held_before = before.get(symbol, ZERO)
            held_after = after.get(symbol, ZERO)
            if held_before != held_after:
                raise CorporateActionError(
                    f"{symbol} {session.isoformat()}: share count moved from {held_before} to "
                    f"{held_after} across a split of ratio {bar.split_ratio}. The sealed price space "
                    "is SPLIT_ADJUSTED, so the price series carries the split already; changing the "
                    "share count as well applies the same event twice."
                )
            prior = self.series[symbol].prior_session(session)
            if prior is None:
                continue
            prior_close = self.series[symbol].bars[prior].close
            if bar.close <= ZERO or prior_close <= ZERO:
                continue
            gap = prior_close / bar.close
            if abs(gap - bar.split_ratio) < Decimal("0.01") * bar.split_ratio:
                raise CorporateActionError(
                    f"{symbol} {session.isoformat()}: close fell from {prior_close} to {bar.close}, "
                    f"a gap matching the split ratio {bar.split_ratio}. The series is not "
                    "split-adjusted after all, which contradicts the sealed price space."
                )

    @exact
    def _handle_delistings(self, session: dt.date) -> None:
        for symbol in self.portfolio.open_symbols():
            series = self.series[symbol]
            if session != series.last_session or session >= self.end:
                continue
            bar = series.bars[session]
            quantity = self.portfolio.quantity_of(symbol)
            fill = self.costs.sell_fill(symbol, quantity, bar.close)
            if fill.gross_notional < self.costs.min_order_notional:
                raise DelistingError(
                    f"{symbol} ends at {session.isoformat()} but its liquidation proceeds "
                    f"{fill.gross_notional} fall below the sealed minimum notional. The engine will "
                    "not carry a position it cannot sell, and will not write one off silently."
                )
            self.portfolio.apply_fill(session, fill)
            self._fills.append(
                FillRecord(
                    session=session,
                    order_id=make_order_id(session, symbol, SELL, "DELIST"),
                    fill=fill,
                )
            )
            self._delisted.add(symbol)

    def _assert_no_position_past_last_bar(self, session: dt.date) -> None:
        for symbol in self.portfolio.open_symbols():
            if session > self.series[symbol].last_session:
                raise DelistingError(
                    f"{symbol} is still held on {session.isoformat()} but its series ended on "
                    f"{self.series[symbol].last_session.isoformat()}. A position past the end of its "
                    "own data is valued at a price that could not have been traded."
                )

    @exact
    def _record_equity(self, session: dt.date) -> Decimal:
        marks: dict[str, Decimal] = {}
        stale = False
        for symbol in self.portfolio.open_symbols():
            mark, is_stale = self._mark(symbol, session)
            marks[symbol] = mark
            stale = stale or is_stale
        equity = self.portfolio.equity(marks)
        if stale:
            self._stale_marks += 1
        self._equity.append(
            EquityPoint(
                session=session,
                cash=self.portfolio.cash,
                equity=equity,
                stale_mark=stale,
                position_count=len(marks),
            )
        )
        return equity

    def _track_staleness(self, session: dt.date) -> None:
        """Count consecutive sessions where an in-range symbol has no bar, and halt past the limit."""
        for symbol in self.series:
            if not self._in_range(symbol, session):
                continue
            if self.series[symbol].get(session) is not None:
                self._stale_run[symbol] = 0
                continue
            run = self._stale_run.get(symbol, 0) + 1
            self._stale_run[symbol] = run
            if run > self.costs.max_consecutive_stale:
                raise DataIntegrityHalt(
                    f"{symbol}: {run} consecutive exchange sessions with no bar, ending "
                    f"{session.isoformat()}. The sealed limit is "
                    f"{self.costs.max_consecutive_stale}. Continuing would produce an equity curve "
                    "nobody can defend."
                )

    @exact
    def _check_risk(self, session: dt.date, equity: Decimal) -> bool:
        """Update the high-water mark; return True on the session a shutdown first triggers."""
        if equity > self._high_water:
            self._high_water = equity
        if not self.enforce_research_shutdown or self._shutdown_session is not None:
            return False
        threshold = self._high_water * (Decimal(1) - self.costs.research_shutdown_drawdown)
        if equity < threshold:
            self._shutdown_session = session
            return True
        return False

    def _schedule(self, session: dt.date, requests: list[OrderRequest], *, forced: bool) -> None:
        """Admit this session's orders and schedule them for the next exchange session."""
        book = OrderBook(decision_session=session)
        self._books[session] = book
        fill_session = next_session_after(session)

        for request in requests:
            if request.symbol not in self.series:
                raise InvariantViolation(f"probe asked for unknown symbol {request.symbol!r}")
            order_id = make_order_id(session, request.symbol, request.side, request.tag)
            if fill_session is None or fill_session > self.end:
                placeholder = Order(
                    order_id=order_id,
                    symbol=request.symbol,
                    side=request.side,
                    decision_session=session,
                    fill_session=session + dt.timedelta(days=1),
                    budget=request.budget,
                    quantity=request.quantity,
                    tag=request.tag,
                )
                self._reject(
                    placeholder,
                    "NO_ELIGIBLE_SESSION",
                    "no exchange session remains inside the run window for this order to fill on",
                )
                continue
            if not forced and request.side == BUY and self._shutdown_session is not None:
                placeholder = Order(
                    order_id=order_id, symbol=request.symbol, side=request.side,
                    decision_session=session, fill_session=fill_session,
                    budget=request.budget, quantity=request.quantity, tag=request.tag,
                )
                self._reject(placeholder, "RESEARCH_SHUTDOWN", "entries are blocked")
                continue
            order = book.submit(
                Order(
                    order_id=order_id,
                    symbol=request.symbol,
                    side=request.side,
                    decision_session=session,
                    fill_session=fill_session,
                    budget=request.budget,
                    quantity=request.quantity,
                    tag=request.tag,
                )
            )
            self._scheduled.setdefault(fill_session, []).append(order)

        for day in self._scheduled:
            self._scheduled[day].sort(key=lambda o: (o.symbol, o.side, o.order_id))

    # -- the loop --------------------------------------------------------------------------------

    def run(self) -> BacktestResult:
        sessions = sessions_between(self.start, self.end)
        if not sessions:
            raise InvariantViolation(f"no exchange sessions in {self.start}..{self.end}")

        for session in sessions:
            self._track_staleness(session)
            self._assert_no_position_past_last_bar(session)

            before = {s: self.portfolio.quantity_of(s) for s in self.portfolio.open_symbols()}
            self._credit_dividends(session)
            self._execute(session)
            after = {s: self.portfolio.quantity_of(s) for s in self.portfolio.open_symbols()}
            self._assert_corporate_action_continuity(session, before, after)

            self._handle_delistings(session)
            equity = self._record_equity(session)
            triggered = self._check_risk(session, equity)

            if session == sessions[-1]:
                continue

            if triggered:
                self._schedule(
                    session,
                    [
                        OrderRequest(symbol=s, side=SELL, tag="SHUTDOWN")
                        for s in self.portfolio.open_symbols()
                    ],
                    forced=True,
                )
                continue

            view = MarketView(self.series, session, self.window)
            context = DecisionContext(
                session=session,
                cash=self.portfolio.cash,
                equity=equity,
                open_symbols=self.portfolio.open_symbols(),
                shutdown_active=self._shutdown_session is not None,
            )
            self._schedule(session, list(self.probe.decide(view, context)), forced=False)

        marks = {s: self._mark(s, sessions[-1])[0] for s in self.portfolio.open_symbols()}
        return BacktestResult(
            label=self.label,
            scenario=self.costs.scenario,
            symbols=tuple(self.series),
            start=self.start,
            end=self.end,
            equity_curve=list(self._equity),
            fills=list(self._fills),
            rejections=list(self._rejections),
            trades=list(self.portfolio.trades),
            dividend_events=list(self._dividends),
            stale_marks=self._stale_marks,
            shutdown_session=self._shutdown_session,
            starting_equity=self.costs.starting_equity,
            final_cash=self.portfolio.cash,
            final_equity=self.portfolio.equity(marks),
            open_positions=[self.portfolio.positions[s].to_json() for s in self.portfolio.open_symbols()],
            cost_model=self.costs.to_json(),
        )
