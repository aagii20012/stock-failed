"""The Attempt 2 **episode ledger** — the resolution of ``G2A2-CONFLICT-18``, and nothing else.

Why this module exists
----------------------

``stockedge100.backtest.portfolio.Portfolio.apply_fill`` appends a :class:`~stockedge100.backtest.
portfolio.Trade` only when a sale takes a position to exactly zero. On a *partial* sale it rewrites
the position's cost basis pro rata and appends nothing. Attempt 1 could not produce a partial sale;
Attempt 2's aggregate throttle (``RA2-1``) and de-risk ladder (``RA2-4``) both reduce a position
without closing it, so Attempt 2 can, routinely.

The consequence measured against the frozen module before the criteria file was written, and quoted
in ``G2A2-CONFLICT-18``:

    A buy of 1 unit at 100.00, a 50 percent trim at 120.00 and a final exit at 90.00 produced
    exactly one recorded Trade with ``entry_cash 50.000``, ``exit_cash 45.00`` and ``pnl -5.000``,
    while the account's cash rose by 5.00. Recorded and true P&L had opposite signs.

So the four trade-based gate conditions — S3-C3, S3-C4, S3-C5, S3-C6 — cannot read ``result.trades``
under Attempt 2. They read the ledger this module builds from the engine's own fill record.

The sealed definition, implemented literally
--------------------------------------------

    An episode is one entry fill in a symbol together with every subsequent sale of that symbol up
    to and including the sale that returns the position to zero. ``entry_cash`` is the total cash
    paid on the episode's entry, ``exit_cash`` the total cash received across all of its sale legs,
    ``dividends`` those credited to the symbol while the episode was open, and
    ``pnl = exit_cash + dividends - entry_cash``. A closed episode is one that reached zero
    quantity; an episode still open on the final session is not closed and is not counted.

Two readings of that text needed a decision, and both are decided here in the direction that keeps
the ledger a *strict generalisation* of the frozen recorder rather than a second opinion about it:

**A buy into an already-open position is folded into the open episode**, not treated as the start of
a second one. ``apply_fill`` merges such a buy into the existing :class:`Position` — cost basis
accumulates and ``opened_session`` is preserved — so it produces no extra ``Trade``. S3-C4's
``counting_identity`` states that "a closed episode and a closed ``Portfolio.Trade`` are the same
event", and folding is the only reading under which that holds. ``entry_cash`` then is exactly what
the seal calls it: *the total cash paid on the episode's entry*. The candidate does not in fact
issue such an order — :meth:`RotationCandidateRA1.decide` enters only symbols it does not hold, and
no ``RA2`` leg is a buy — so :attr:`Reconciliation.multi_entry_episodes` is expected to be zero and
is reported rather than assumed.

**Dividends are attributed by replaying the engine's own ordering**, not by interval arithmetic on
episode dates. :meth:`BacktestEngine.run` credits dividends *before* it executes the session's
fills, and :meth:`Portfolio.record_dividend` accrues to a per-symbol bucket that is popped when the
position closes. Replaying dividends and fills as one chronological stream — dividends first within
a session — reproduces that attribution exactly, including the one case where a date interval is
ambiguous: a symbol whose episode closes on the same session another opens.

What this module does not do
----------------------------

It does not compute a condition, a threshold or a verdict; that is the gate module's work. It does
not modify, subclass or work around ``portfolio.py``, which is a frozen Generation 1 file — the
ledger is derived from :attr:`BacktestResult.fills`, which the engine records for its own
determinism digest, and the frozen ``Trade`` list is read only to be *checked against*.

Reconciliation, and the one place it is deliberately not a halt
---------------------------------------------------------------

``evaluation_integrity_rules`` §8 requires that the ledger be reconciled against ``Portfolio.trades``
on **every** run, not only the representative's: equal closed counts, and — for every episode with
exactly one sale leg — equal ``entry_cash``, ``exit_cash``, ``dividends`` and ``pnl``. A failure of
either "halts evaluation rather than being reported as a discrepancy, because it would mean the
generalisation of ``G2A2-CONFLICT-18`` is not the generalisation this file declares". Both are
raised from :func:`build_episode_ledger`, so no caller can obtain a ledger that failed them.

§9 adds that the reconciliation "must not be allowed to pass vacuously": the number of single-leg
episodes compared is asserted greater than zero *before* asserting they agree, and reported
alongside the mismatch count. That one is recorded rather than raised, and the distinction matters.
A run with no closed episode reconciles vacuously — zero equals zero, no mismatches — but it is a
legitimate, informative *result*: S3-C4 measures zero closed episodes against a floor of thirty and
fails on a measured value. Raising there would convert a FAIL the pre-registration explicitly
anticipates (``G2A2-CONFLICT-20``, ``SC-1``) into a crash, and would delete the evidence the
constitution requires to be kept on disk. So :attr:`Reconciliation.vacuous` is a reported flag,
:attr:`Reconciliation.reconciled` is **false** while it is set, and no caller may read a vacuous
reconciliation as agreement.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Iterable, Sequence

from stockedge100.backtest.config import dec
from stockedge100.backtest.costs import Fill, ZERO, exact
from stockedge100.backtest.engine import BacktestResult, FillRecord
from stockedge100.backtest.errors import DataIntegrityHalt, InvariantViolation
from stockedge100.backtest.orders import BUY, SELL
from stockedge100.backtest.portfolio import Trade

__all__ = [
    "CONFLICT_ID",
    "LEDGER_ID",
    "RECONCILED_FIELDS",
    "DividendCredit",
    "Episode",
    "EpisodeLedger",
    "EntryLeg",
    "Reconciliation",
    "SaleLeg",
    "build_episode_ledger",
]

LEDGER_ID = "SE100-G2-S3-C2-EPISODE-LEDGER"
CONFLICT_ID = "G2A2-CONFLICT-18"

#: The four figures ``evaluation_integrity_rules`` §8 names, and the only ones compared against the
#: frozen ``Trade``. ``entry_costs`` is deliberately absent: the frozen recorder stores ``ZERO``
#: there because a buy's fees are already inside ``cost_basis``, so comparing it would assert a
#: display artifact rather than a fact about the money.
RECONCILED_FIELDS = ("entry_cash", "exit_cash", "dividends", "pnl")


# -- legs ----------------------------------------------------------------------------------------


@dataclass(frozen=True)
class EntryLeg:
    """One buy fill belonging to an episode. ``cash`` is positive: what the account paid."""

    session: dt.date
    order_id: str
    quantity: Decimal
    cash: Decimal
    fees: Decimal

    def to_json(self) -> dict[str, str]:
        return {
            "session": self.session.isoformat(),
            "order_id": self.order_id,
            "quantity": f"{self.quantity:f}",
            "cash_paid": f"{self.cash:f}",
            "fees": f"{self.fees:f}",
        }


@dataclass(frozen=True)
class SaleLeg:
    """One sell fill belonging to an episode. ``cash`` is positive: what the account received.

    ``closing`` marks the leg that returned the position to zero — the only leg the frozen recorder
    ever saw. Every other leg on an episode is proceeds ``G2A2-CONFLICT-18`` shows are dropped.
    """

    session: dt.date
    order_id: str
    quantity: Decimal
    cash: Decimal
    fees: Decimal
    closing: bool

    def to_json(self) -> dict[str, Any]:
        return {
            "session": self.session.isoformat(),
            "order_id": self.order_id,
            "quantity": f"{self.quantity:f}",
            "cash_received": f"{self.cash:f}",
            "fees": f"{self.fees:f}",
            "closing": self.closing,
        }


@dataclass(frozen=True)
class DividendCredit:
    """One dividend credited to the symbol while this episode was open."""

    session: dt.date
    cash: Decimal

    def to_json(self) -> dict[str, str]:
        return {"session": self.session.isoformat(), "cash_credited": f"{self.cash:f}"}


# -- an episode ----------------------------------------------------------------------------------


@dataclass(frozen=True)
class Episode:
    """One entry in a symbol and every sale of it up to and including the one that zeroes it.

    ``open_index`` is the episode's position in entry order across the whole run; ``close_index`` is
    its position among *closed* episodes, in the order the position returned to zero, and is
    ``None`` while the episode is open. The frozen ``Portfolio.trades`` list is appended in exactly
    that closing order, so ``close_index`` is also the index of the ``Trade`` this episode must
    reconcile against — and it is the index S3-C5's tie-break means by "the earliest by index".
    """

    symbol: str
    open_index: int
    close_index: int | None
    entry_session: dt.date
    exit_session: dt.date | None
    entry_legs: tuple[EntryLeg, ...]
    sale_legs: tuple[SaleLeg, ...]
    dividend_credits: tuple[DividendCredit, ...]
    closed: bool
    quantity_bought: Decimal
    quantity_sold: Decimal

    # -- the sealed figures ------------------------------------------------------------------

    @property
    @exact
    def entry_cash(self) -> Decimal:
        """Total cash paid on the episode's entry, fees included, positive."""
        return sum((leg.cash for leg in self.entry_legs), ZERO)

    @property
    @exact
    def exit_cash(self) -> Decimal:
        """Total cash received across **every** sale leg, fees deducted, positive.

        This is the figure the frozen recorder gets wrong: it stores only the closing leg's
        proceeds. See :attr:`trimmed_proceeds`.
        """
        return sum((leg.cash for leg in self.sale_legs), ZERO)

    @property
    @exact
    def dividends(self) -> Decimal:
        return sum((credit.cash for credit in self.dividend_credits), ZERO)

    @property
    @exact
    def pnl(self) -> Decimal:
        """``exit_cash + dividends - entry_cash``, defined only once the episode has closed.

        An open episode has no P&L to report — its remaining shares are marked, not sold — and the
        seal counts only closed episodes. Raising here rather than returning a partial figure is
        what keeps an open position out of S3-C3, S3-C5 and S3-C6 by construction rather than by
        every caller remembering to filter.
        """
        if not self.closed:
            raise InvariantViolation(
                f"{self.symbol} episode {self.open_index} is still open on the final session; it "
                "has no episode P&L. Closed episodes only — see S3-C4."
            )
        return self.exit_cash + self.dividends - self.entry_cash

    # -- what the frozen recorder drops ------------------------------------------------------

    @property
    def closing_leg(self) -> SaleLeg | None:
        return self.sale_legs[-1] if self.closed else None

    @property
    @exact
    def trimmed_proceeds(self) -> Decimal:
        """Cash from sale legs that did **not** close the position.

        Zero for every episode Attempt 1 could produce. Its total across a run is the size of the
        distortion ``G2A2-CONFLICT-18`` describes, and S3-C3's ``attempt_2_note`` calls it "the
        measure of how much the risk architecture actually traded".
        """
        return sum((leg.cash for leg in self.sale_legs if not leg.closing), ZERO)

    @property
    @exact
    def entry_leg_fees(self) -> Decimal:
        return sum((leg.fees for leg in self.entry_legs), ZERO)

    @property
    @exact
    def exit_leg_fees(self) -> Decimal:
        return sum((leg.fees for leg in self.sale_legs), ZERO)

    @property
    def sale_leg_count(self) -> int:
        return len(self.sale_legs)

    @property
    def single_leg(self) -> bool:
        """True when the frozen ``Trade`` is expected to reproduce this episode exactly."""
        return self.closed and len(self.sale_legs) == 1

    def to_json(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "symbol": self.symbol,
            "open_index": self.open_index,
            "close_index": self.close_index,
            "entry_session": self.entry_session.isoformat(),
            "exit_session": None if self.exit_session is None else self.exit_session.isoformat(),
            "closed": self.closed,
            "entry_legs": [leg.to_json() for leg in self.entry_legs],
            "sale_legs": [leg.to_json() for leg in self.sale_legs],
            "dividend_credits": [credit.to_json() for credit in self.dividend_credits],
            "quantity_bought": f"{self.quantity_bought:f}",
            "quantity_sold": f"{self.quantity_sold:f}",
            "entry_cash": f"{self.entry_cash:f}",
            "exit_cash": f"{self.exit_cash:f}",
            "dividends": f"{self.dividends:f}",
            "trimmed_proceeds": f"{self.trimmed_proceeds:f}",
            "entry_leg_fees": f"{self.entry_leg_fees:f}",
            "exit_leg_fees": f"{self.exit_leg_fees:f}",
        }
        payload["pnl"] = f"{self.pnl:f}" if self.closed else None
        return payload


# -- reconciliation ------------------------------------------------------------------------------


@dataclass(frozen=True)
class Reconciliation:
    """The §8/§9 check, as a reported record rather than a boolean nobody can audit."""

    closed_episodes: int
    closed_trades: int
    single_leg_compared: int
    multi_leg_episodes: int
    multi_entry_episodes: int
    max_sale_legs: int
    mismatches: tuple[str, ...]
    total_trimmed_proceeds: Decimal
    episode_pnl_total: Decimal
    frozen_trade_pnl_total: Decimal

    @property
    def counts_agree(self) -> bool:
        return self.closed_episodes == self.closed_trades

    @property
    def vacuous(self) -> bool:
        """No single-leg episode existed, so agreement was asserted about nothing (§9)."""
        return self.single_leg_compared == 0

    @property
    def reconciled(self) -> bool:
        return self.counts_agree and not self.mismatches and not self.vacuous

    @property
    @exact
    def pnl_discrepancy(self) -> Decimal:
        """Episode-ledger P&L minus frozen-recorder P&L, over the same closing events.

        Zero on any run the frozen recorder describes correctly. Non-zero is not an error: it is
        the quantity ``G2A2-CONFLICT-18`` exists to expose, and it is reported in the evidence.
        """
        return self.episode_pnl_total - self.frozen_trade_pnl_total

    def to_json(self) -> dict[str, Any]:
        return {
            "closed_episodes": self.closed_episodes,
            "closed_trades": self.closed_trades,
            "counts_agree": self.counts_agree,
            "single_leg_compared": self.single_leg_compared,
            "multi_leg_episodes": self.multi_leg_episodes,
            "multi_entry_episodes": self.multi_entry_episodes,
            "max_sale_legs": self.max_sale_legs,
            "mismatches": list(self.mismatches),
            "vacuous": self.vacuous,
            "reconciled": self.reconciled,
            "reconciled_fields": list(RECONCILED_FIELDS),
            "total_trimmed_proceeds": f"{self.total_trimmed_proceeds:f}",
            "episode_pnl_total": f"{self.episode_pnl_total:f}",
            "frozen_trade_pnl_total": f"{self.frozen_trade_pnl_total:f}",
            "pnl_discrepancy": f"{self.pnl_discrepancy:f}",
        }


def _close_key(episode: Episode) -> int:
    """Sort key for closed episodes. Raises rather than coercing a ``None`` to a position."""
    if episode.close_index is None:
        raise InvariantViolation(
            f"{episode.symbol} episode {episode.open_index} is marked closed but carries no close "
            "index; it cannot be placed against the frozen trade list."
        )
    return episode.close_index


@dataclass(frozen=True)
class EpisodeLedger:
    """Every episode of one run, plus its reconciliation against the frozen trade list."""

    label: str
    scenario: str
    episodes: tuple[Episode, ...]  # entry order
    reconciliation: Reconciliation

    @property
    def closed_episodes(self) -> tuple[Episode, ...]:
        """Closed episodes in **closing** order — the order ``Portfolio.trades`` is appended in."""
        return tuple(sorted((e for e in self.episodes if e.closed), key=_close_key))

    @property
    def open_episodes(self) -> tuple[Episode, ...]:
        return tuple(e for e in self.episodes if not e.closed)

    @property
    def pnls(self) -> tuple[Decimal, ...]:
        """Closed-episode P&L in closing order — the sequence S3-C3 and S3-C5 read."""
        return tuple(e.pnl for e in self.closed_episodes)

    @exact
    def pnl_by_symbol(self) -> dict[str, Decimal]:
        """Closed-episode P&L summed per instrument — the numerator S3-C6 reads."""
        totals: dict[str, Decimal] = {}
        for episode in self.closed_episodes:
            totals[episode.symbol] = totals.get(episode.symbol, ZERO) + episode.pnl
        return totals

    def to_json(self) -> dict[str, Any]:
        return {
            "ledger_id": LEDGER_ID,
            "conflict_id": CONFLICT_ID,
            "label": self.label,
            "scenario": self.scenario,
            "episodes": [e.to_json() for e in self.episodes],
            "reconciliation": self.reconciliation.to_json(),
        }


# -- construction --------------------------------------------------------------------------------


class _OpenEpisode:
    """Mutable accumulator. Only :func:`build_episode_ledger` ever holds one."""

    __slots__ = ("symbol", "open_index", "entry_legs", "sale_legs", "credits", "quantity")

    def __init__(self, symbol: str, open_index: int) -> None:
        self.symbol = symbol
        self.open_index = open_index
        self.entry_legs: list[EntryLeg] = []
        self.sale_legs: list[SaleLeg] = []
        self.credits: list[DividendCredit] = []
        self.quantity: Decimal = ZERO

    def freeze(self, close_index: int | None) -> Episode:
        closed = close_index is not None
        sale_legs = list(self.sale_legs)
        if closed and sale_legs:
            last = sale_legs[-1]
            sale_legs[-1] = SaleLeg(
                session=last.session,
                order_id=last.order_id,
                quantity=last.quantity,
                cash=last.cash,
                fees=last.fees,
                closing=True,
            )
        return Episode(
            symbol=self.symbol,
            open_index=self.open_index,
            close_index=close_index,
            entry_session=self.entry_legs[0].session,
            exit_session=sale_legs[-1].session if closed else None,
            entry_legs=tuple(self.entry_legs),
            sale_legs=tuple(sale_legs),
            dividend_credits=tuple(self.credits),
            closed=closed,
            quantity_bought=sum((leg.quantity for leg in self.entry_legs), ZERO),
            quantity_sold=sum((leg.quantity for leg in sale_legs), ZERO),
        )


def _dividend_stream(events: Sequence[dict[str, str]]) -> list[tuple[dt.date, int, int, Any]]:
    stream: list[tuple[dt.date, int, int, Any]] = []
    for order, event in enumerate(events):
        session = dt.date.fromisoformat(event["session"])
        stream.append((session, 0, order, event))
    return stream


def _fill_stream(fills: Sequence[FillRecord]) -> list[tuple[dt.date, int, int, Any]]:
    return [(record.session, 1, order, record) for order, record in enumerate(fills)]


def _chronological(result: BacktestResult) -> list[tuple[dt.date, int, int, Any]]:
    """Dividends then fills, session by session — the order :meth:`BacktestEngine.run` uses.

    ``run()`` calls ``_credit_dividends(session)`` before ``_execute(session)`` and
    ``_handle_delistings(session)``, and ``Portfolio.record_dividend`` accrues to a per-symbol
    bucket that ``apply_fill`` pops when the position closes. Replaying that order is what makes the
    ledger's dividend attribution *the engine's own*, rather than a second opinion derived from
    episode date intervals — which would be ambiguous on a session where one episode in a symbol
    closes and another opens.
    """
    stream = _dividend_stream(result.dividend_events) + _fill_stream(result.fills)
    stream.sort(key=lambda item: (item[0], item[1], item[2]))
    return stream


@exact
def build_episode_ledger(result: BacktestResult) -> EpisodeLedger:
    """Derive the episode ledger of one run and reconcile it against the frozen trade list.

    Raises :class:`DataIntegrityHalt` when the reconciliation of ``evaluation_integrity_rules`` §8
    fails, so a caller cannot hold a ledger that disagrees with ``Portfolio.trades`` about a
    single-leg episode or about how many episodes closed. A *vacuous* reconciliation (§9) is
    recorded on the returned :class:`Reconciliation` instead of raised; see the module docstring.
    """
    open_by_symbol: dict[str, _OpenEpisode] = {}
    frozen: list[Episode] = []
    next_open_index = 0
    next_close_index = 0

    for session, phase, _order, payload in _chronological(result):
        if phase == 0:
            event = payload
            symbol = str(event["symbol"])
            episode = open_by_symbol.get(symbol)
            if episode is None:
                raise DataIntegrityHalt(
                    f"{session.isoformat()}: a dividend of {event['cash_credited']} was credited to "
                    f"{symbol} while no episode in it was open. The engine credits dividends only "
                    "to open positions, so this means the replay order in this module does not "
                    "match the engine's."
                )
            episode.credits.append(DividendCredit(session=session, cash=dec(event["cash_credited"])))
            continue

        record: FillRecord = payload
        fill: Fill = record.fill
        symbol = fill.symbol
        if fill.side == BUY:
            episode = open_by_symbol.get(symbol)
            if episode is None:
                episode = _OpenEpisode(symbol, next_open_index)
                next_open_index += 1
                open_by_symbol[symbol] = episode
            episode.entry_legs.append(
                EntryLeg(
                    session=session,
                    order_id=record.order_id,
                    quantity=fill.quantity,
                    cash=-fill.cash_delta,
                    fees=fill.commission + fill.sec_fee + fill.taf_fee,
                )
            )
            episode.quantity += fill.quantity
            continue

        if fill.side != SELL:
            raise DataIntegrityHalt(f"{record.order_id}: unknown fill side {fill.side!r}")

        episode = open_by_symbol.get(symbol)
        if episode is None:
            raise DataIntegrityHalt(
                f"{session.isoformat()}: a sale of {symbol} with no episode open in it. A long-only "
                "account cannot sell what it never bought."
            )
        episode.sale_legs.append(
            SaleLeg(
                session=session,
                order_id=record.order_id,
                quantity=fill.quantity,
                cash=fill.cash_delta,
                fees=fill.commission + fill.sec_fee + fill.taf_fee,
                closing=False,
            )
        )
        episode.quantity -= fill.quantity
        if episode.quantity < ZERO:
            raise DataIntegrityHalt(
                f"{session.isoformat()}: selling {fill.quantity} of {symbol} took the replayed "
                f"position to {episode.quantity}. The frozen portfolio refuses this, so a negative "
                "quantity here means this module is not replaying the same fills."
            )
        if episode.quantity == ZERO:
            frozen.append(episode.freeze(next_close_index))
            next_close_index += 1
            del open_by_symbol[symbol]

    for symbol in sorted(open_by_symbol):
        frozen.append(open_by_symbol[symbol].freeze(None))

    episodes = tuple(sorted(frozen, key=lambda e: e.open_index))
    reconciliation = _reconcile(episodes, result.trades)
    return EpisodeLedger(
        label=result.label,
        scenario=result.scenario,
        episodes=episodes,
        reconciliation=reconciliation,
    )


@exact
def _reconcile(episodes: Iterable[Episode], trades: Sequence[Trade]) -> Reconciliation:
    """``evaluation_integrity_rules`` §8 and §9, in that order.

    §8's two halting assertions are the count identity and the single-leg value identity. §9's
    non-vacuity is computed and returned, not raised.
    """
    episodes = tuple(episodes)
    closed = sorted((e for e in episodes if e.closed), key=_close_key)

    if len(closed) != len(trades):
        raise DataIntegrityHalt(
            f"{CONFLICT_ID}: the episode ledger closed {len(closed)} episode(s) while the frozen "
            f"Portfolio recorded {len(trades)} trade(s). S3-C4's counting_identity states these are "
            "the same event, so a difference means the generalisation this ledger implements is not "
            "the one the criteria file declares. Evaluation halts."
        )

    mismatches: list[str] = []
    compared = 0
    for episode, trade in zip(closed, trades):
        if episode.symbol != trade.symbol or episode.exit_session != trade.exit_session:
            raise DataIntegrityHalt(
                f"{CONFLICT_ID}: closed episode {episode.close_index} is "
                f"{episode.symbol} closing {episode.exit_session} but the frozen trade at that "
                f"index is {trade.symbol} closing {trade.exit_session}. The two lists are not "
                "describing the same closing events, so no comparison between them means anything."
            )
        if not episode.single_leg:
            continue
        compared += 1
        for field in RECONCILED_FIELDS:
            ours = getattr(episode, field)
            theirs = getattr(trade, field)
            if ours != theirs:
                mismatches.append(
                    f"{episode.symbol} episode {episode.close_index} {field}: ledger {ours} vs "
                    f"frozen trade {theirs}"
                )
        if episode.exit_leg_fees != trade.exit_costs:
            mismatches.append(
                f"{episode.symbol} episode {episode.close_index} exit fees: ledger "
                f"{episode.exit_leg_fees} vs frozen trade {trade.exit_costs}"
            )

    if mismatches:
        raise DataIntegrityHalt(
            f"{CONFLICT_ID}: {len(mismatches)} single-leg episode(s) disagree with the frozen "
            "Portfolio.Trade they reduce to. The ledger claims to be numerically identical to the "
            "frozen recorder wherever there is exactly one sale leg; where that fails, evaluation "
            "halts rather than reporting a discrepancy. First: " + mismatches[0]
        )

    return Reconciliation(
        closed_episodes=len(closed),
        closed_trades=len(trades),
        single_leg_compared=compared,
        multi_leg_episodes=sum(1 for e in closed if e.sale_leg_count > 1),
        multi_entry_episodes=sum(1 for e in episodes if len(e.entry_legs) > 1),
        max_sale_legs=max((e.sale_leg_count for e in closed), default=0),
        mismatches=tuple(mismatches),  # empty by construction: a non-empty list raised above
        total_trimmed_proceeds=sum((e.trimmed_proceeds for e in closed), ZERO),
        episode_pnl_total=sum((e.pnl for e in closed), ZERO),
        frozen_trade_pnl_total=sum((t.pnl for t in trades), ZERO),
    )
