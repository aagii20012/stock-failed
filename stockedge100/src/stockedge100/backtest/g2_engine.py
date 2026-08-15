"""The multi-position session loop.

Generation 1's :class:`~stockedge100.backtest.engine.BacktestEngine` was written for an account that
holds at most one risky position. Two of its behaviours are correct under that assumption and wrong
without it, and both are silent rather than loud — they produce a plausible number, not an exception.
They are recorded together as **G2-CONFLICT-14** in
``governance/generation_2/STAGE_3_G2_ROTATION_PROTOCOL.md`` §4 and §7, and this module is the
resolution:

1. **Order sequencing.** ``_schedule`` sorts a fill session's orders by ``(symbol, side, order_id)``.
   With one position a session carries one order and the sort decides nothing. With `k > 1` a
   rebalance carries sells and buys together, and alphabetical order would execute a buy of ``AGG``
   before a sell of ``XLU`` — sizing the purchase against cash the sale had not yet released.
   :meth:`RotationEngine._execute` re-sorts by ``(0 if SELL else 1, symbol, order_id)``.

2. **The marks used to size a buy.** ``BacktestEngine._execute_buy`` values already-held positions
   with ``_mark(symbol, session)``, which returns that session's *close*. With at most one open
   position that call is either empty or self-referential and reads nothing, so it was harmless.
   With `k > 1` it would value the rest of the book at the close of the very session the buy fills at
   the open. :class:`RotationEngine` marks at the **open**, through its own helper rather than
   ``_mark`` — whose side effect of writing ``_last_close`` must not fire at an open price.

The third change is not a repair of Generation 1 but a constraint Generation 1 could not express: the
**50% single-position concentration ceiling**. The sealed cost model has no field for it, because a
one-position portfolio cannot breach a concentration limit that the 95% gross cap does not already
cover, and that file is frozen. The ceiling is declared in
``config/generation_2/g2_cost_model.json`` and enforced here, alongside the two sealed ceilings, as
one of three named clamps on every buy budget:

===================  ==========================================================================
``AGGREGATE``        ``0.95 · equity`` − total value of positions already held
``CASH_FLOOR``       ``cash`` − ``0.05 · equity``
``CONCENTRATION``    ``0.50 · equity`` − current value of *that* position
===================  ==========================================================================

The submitted budget is the minimum of the request and all three. If that minimum is not strictly
positive the order is rejected as ``INSUFFICIENT_CASH`` with the binding clamp named in the detail
string: ``orders.REASONS`` is a closed declared set owned by ``orders.py``, which Generation 2 does
not modify, so no new reason code is invented at runtime.

Every clamp is computed from marks taken at the **fill session's open**, never its close.

So is the request itself, when a ``budget_weight`` is supplied. The sealed sizing rule is "budget =
``w(k) · equity``, where equity is measured at the fill session's open", and the frozen ``Order``
cannot express it: a buy must carry an absolute budget fixed at the previous close. The order record
therefore holds the decision-close evaluation of that formula and this engine re-evaluates it at the
open, which is what the seal asks for. Recorded as G2-CONFLICT-16. It also matters arithmetically:
``w(k)`` is quantized ROUND_DOWN precisely so that ``k · w(k) ≤ 0.95``, and that guarantee only holds
if the requests and the ``AGGREGATE`` clamp are measured against the *same* equity. Split across an
overnight gap they are not, and the last buy of a rebalance would be clamped for a timing artefact.

Nothing else about the session loop changes. Dividends, corporate-action continuity, delisting,
staleness, the equity curve, the research shutdown and the decision ordering are all inherited
unchanged, and the equity curve is still marked at the close — a mark is not a fill.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from stockedge100.backtest.costs import CostModel, ZERO, exact
from stockedge100.backtest.dataset import PriceSeries
from stockedge100.backtest.engine import BacktestEngine, FillRecord, Probe
from stockedge100.backtest.errors import (
    ConfigViolation,
    DataIntegrityHalt,
    InvariantViolation,
)
from stockedge100.backtest.g2_costs import concentration_ceiling
from stockedge100.backtest.orders import Order, SELL
from stockedge100.backtest.window import ResearchWindow

__all__ = ["CLAMP_NAMES", "RotationEngine"]

#: The clamp labels a rejection detail may name. Ordered: the first of two equal minima binds, so the
#: order is part of the behaviour and not an accident of iteration.
CLAMP_NAMES = ("REQUESTED_BUDGET", "AGGREGATE", "CASH_FLOOR", "CONCENTRATION")


class RotationEngine(BacktestEngine):
    """Generation 2's engine: the Stage 2 loop, able to hold `k` risky positions at once.

    The class deliberately overrides two methods and adds one helper. Everything it does not override
    is inherited rather than re-implemented, so a change to the sealed session order reaches
    Generation 2 automatically and cannot be forked by accident.
    """

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
        budget_weight: Decimal | None = None,
    ) -> None:
        super().__init__(
            series,
            cost_model,
            window,
            probe,
            start=start,
            end=end,
            label=label,
            enforce_research_shutdown=enforce_research_shutdown,
        )

        # Read from the sealed declaration, never from a caller. A ceiling a test could pass in is a
        # ceiling a strategy could pass in.
        self.concentration_ceiling = concentration_ceiling()
        if not ZERO < self.concentration_ceiling <= Decimal(1):
            raise ConfigViolation(
                f"the declared concentration ceiling {self.concentration_ceiling} is not a fraction "
                "in (0, 1]"
            )

        if budget_weight is not None and not ZERO < budget_weight <= Decimal(1):
            raise ConfigViolation(
                f"budget_weight {budget_weight} is not a fraction in (0, 1]; it is the sealed w(k), "
                "not a share count"
            )
        self.budget_weight = budget_weight

        self.binding_clamp_counts: dict[str, int] = {name: 0 for name in CLAMP_NAMES}
        self.clamp_rejections = 0
        self.open_stale_marks = 0
        self.budget_reevaluations = 0

    # -- marks -----------------------------------------------------------------------------------

    def _open_mark(self, symbol: str, session: dt.date) -> tuple[Decimal, bool]:
        """The price to value a position at while sizing a fill on ``session``, and whether it is stale.

        Deliberately not :meth:`BacktestEngine._mark`. That method returns the session's *close* and
        caches it in ``_last_close``; both are wrong here. The fallback for a symbol with no bar today
        is the last close already cached, which — because ``_record_equity`` for session *s* runs
        after ``_execute`` for session *s* — is always from a session strictly before ``session``.
        Nothing this method returns is information the open of ``session`` did not already carry.
        """
        bar = self.series[symbol].get(session)
        if bar is not None:
            return bar.open, False
        known = self._last_close.get(symbol)
        if known is None:
            raise DataIntegrityHalt(
                f"{symbol}: no price has ever been seen but an open mark is required on "
                f"{session.isoformat()}"
            )
        self.open_stale_marks += 1
        return known, True

    # -- session steps ---------------------------------------------------------------------------

    @exact
    def _execute(self, session: dt.date) -> None:
        """Execute the session's scheduled orders, sells first.

        The key is total — side, then symbol, then order id — so the sequence is a function of the
        orders alone and a rerun reproduces it exactly.
        """
        orders = self._scheduled.pop(session, [])
        orders.sort(key=lambda o: (0 if o.side == SELL else 1, o.symbol, o.order_id))
        for order in orders:
            self._execute_one(session, order)

    @exact
    def _execute_buy(self, session: dt.date, order: Order, reference: Decimal) -> None:
        """Size and settle one purchase under three named ceilings.

        Structurally the same as the inherited method up to the budget, and different in exactly the
        way §4 of the sealed protocol says it is: the aggregate cap subtracts what is already held
        rather than treating each buy as if the book were empty, the concentration ceiling exists at
        all, and every value is marked at this session's open.
        """
        if self._shutdown_session is not None:
            self._reject(order, "RESEARCH_SHUTDOWN", "entries are blocked after a research shutdown")
            return

        symbol = order.symbol
        held = self.portfolio.open_symbols()
        if symbol not in held and len(held) >= self.costs.max_open_risky_positions:
            self._reject(order, "MAX_POSITIONS", f"already holding {len(held)} position(s)")
            return

        marks = {s: self._open_mark(s, session)[0] for s in held}
        values = {s: self.portfolio.quantity_of(s) * marks[s] for s in held}
        position_value = sum(values.values(), ZERO)
        own_value = values.get(symbol, ZERO)

        equity = self.portfolio.equity(marks)
        cash = self.portfolio.cash

        requested = order.budget if order.budget is not None else ZERO
        if self.budget_weight is not None:
            # The sealed rule is "budget = w(k) * equity, where equity is measured at the fill
            # session's open". The frozen Order contract cannot express that — a buy must carry an
            # absolute budget decided at the previous close — so the order record holds the
            # decision-close evaluation of the same formula and the engine re-evaluates it here at
            # the open. Recorded as G2-CONFLICT-16.
            #
            # This is not a refinement for its own sake. The sealed ROUND_DOWN quantization of w(k)
            # exists so that k * w(k) <= 0.95 exactly; if the request were measured against the
            # close's equity while the aggregate clamp used the open's, an overnight gap down would
            # make the k requests sum above the open cap and the AGGREGATE clamp would bind on the
            # last buy of the rebalance for a pure timing reason. Measuring both against one equity
            # is what makes the quantization do the job it was quantized for.
            requested = self.budget_weight * equity
            self.budget_reevaluations += 1

        clamps = (
            ("REQUESTED_BUDGET", requested),
            ("AGGREGATE", self.costs.max_gross_exposure_fraction * equity - position_value),
            ("CASH_FLOOR", cash - self.costs.min_cash_buffer_fraction * equity),
            ("CONCENTRATION", self.concentration_ceiling * equity - own_value),
        )
        binding, budget = clamps[0]
        for name, value in clamps[1:]:
            if value < budget:
                binding, budget = name, value

        if budget <= ZERO:
            self.clamp_rejections += 1
            self._reject(
                order,
                "INSUFFICIENT_CASH",
                f"budget resolved to {budget} from cash {cash}; the binding constraint was {binding} "
                + ", ".join(f"{name}={value}" for name, value in clamps),
            )
            return
        self.binding_clamp_counts[binding] += 1

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
        self._assert_ceilings_hold(session, symbol, reference, marks, equity)

    # -- assertions ------------------------------------------------------------------------------

    def _assert_ceilings_hold(
        self,
        session: dt.date,
        symbol: str,
        reference: Decimal,
        marks: dict[str, Decimal],
        equity: Decimal,
    ) -> None:
        """Re-derive both ceilings from the settled book, at the same open marks the clamps used.

        The clamp arithmetic above says the ceilings hold. This says so from the positions actually
        recorded, using no value the clamp computed, so an error in the clamp is caught by something
        that does not share a line of code with it. ``equity`` is the pre-fill equity on purpose:
        that is the quantity the sealed clamps are defined against, and re-measuring it after the
        friction has been paid would test a different statement.

        The concentration ceiling is asserted **of the symbol just bought**, not of every holding.
        §4 of the sealed protocol declares equal-weight *at entry* with no trim and no top-up, and
        adds explicitly that "drift caused purely by price appreciation is not an order and is not
        trimmed" — so a continuing holding may legitimately appreciate past 50% of equity while some
        *other* symbol is being bought. Asserting the ceiling of every position would halt the run on
        behaviour the protocol declares, which is a defect in the assertion and not in the book. What
        the ceiling forbids, and what is asserted here, is a *purchase* that leaves the bought
        position above the line. The aggregate needs no such qualification: a buy only reaches this
        point if its aggregate headroom was strictly positive, which is already the statement that
        the pre-existing total was inside the cap.
        """
        after = dict(marks)
        after[symbol] = reference
        total = ZERO
        for open_symbol in self.portfolio.open_symbols():
            mark = after.get(open_symbol)
            if mark is None:
                raise InvariantViolation(
                    f"{open_symbol} is held on {session.isoformat()} but was not marked at the open "
                    "while sizing this fill; a ceiling cannot be checked against a position left out "
                    "of the sum"
                )
            value = self.portfolio.quantity_of(open_symbol) * mark
            total += value
            if open_symbol == symbol and value > self.concentration_ceiling * equity:
                raise InvariantViolation(
                    f"CONCENTRATION_CEILING: buying {open_symbol} on {session.isoformat()} left it "
                    f"worth {value} against equity {equity}, above the declared ceiling "
                    f"{self.concentration_ceiling}. The clamp on this buy should have prevented it."
                )
        if total > self.costs.max_gross_exposure_fraction * equity:
            raise InvariantViolation(
                f"MAX_GROSS_EXPOSURE: positions are worth {total} on {session.isoformat()} against "
                f"equity {equity}, above the sealed ceiling "
                f"{self.costs.max_gross_exposure_fraction}. The clamp on this buy should have "
                "prevented it."
            )
        if len(self.portfolio.open_symbols()) > self.costs.max_open_risky_positions:
            raise InvariantViolation(
                f"MAX_POSITIONS: {len(self.portfolio.open_symbols())} positions are open on "
                f"{session.isoformat()}, above the derived limit "
                f"{self.costs.max_open_risky_positions}"
            )

    # -- evidence --------------------------------------------------------------------------------

    def clamp_summary(self) -> dict[str, object]:
        """What the ceilings actually did during the run, for a report that must show it."""
        return {
            "concentration_ceiling": f"{self.concentration_ceiling:f}",
            "budget_weight": None if self.budget_weight is None else f"{self.budget_weight:f}",
            "budget_reevaluations": self.budget_reevaluations,
            "max_gross_exposure_fraction": f"{self.costs.max_gross_exposure_fraction:f}",
            "min_cash_buffer_fraction": f"{self.costs.min_cash_buffer_fraction:f}",
            "max_open_risky_positions": self.costs.max_open_risky_positions,
            "binding_clamp_counts": dict(self.binding_clamp_counts),
            "clamp_rejections": self.clamp_rejections,
            "open_stale_marks": self.open_stale_marks,
        }
