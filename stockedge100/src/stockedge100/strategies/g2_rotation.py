"""``SE100-G2-S3-C1-ROTATION`` — the one Generation 2 candidate, and its eighteen parameterisations.

Everything this module does was fixed in ``config/generation_2/g2_rotation_protocol.json``
(``SE100-CFG-3101``) and its Markdown counterpart before any strategy code existed. So the module
reads the protocol rather than restating it: the grid, the variant ids, the target weights, the sort
key and the rebalance rule all come off disk, and where a value can be *derived* from something
sealed, it is derived and then checked against the declaration. A restated constant is a constant
that can drift; a derived one that disagrees with its declaration raises.

Three things are worth reading before the code.

**The ranking signal is a backward dividend chain, not an adjusted close.** The sealed formula is::

    TR(t0 -> t1) = (close[t1] / close[t0]) / prod over s in (t0, t1] of (1 - D[s] / close[s-1]) - 1

which equals ``adj[t1] / adj[t0] - 1`` under the adjustment convention Stage 1 measured. The two are
*not* interchangeable in code. ``adj_close[t]`` is a function of every dividend paid after ``t`` as
well, so reading the column at ``t1`` reaches into the future of ``t1``; on a backtest that is a
look-ahead the engine's own bound cannot catch, because the value sits inside a bar the view is happy
to hand over. The product form above touches only sessions inside the interval. ``adj_close`` is
never read here.

**The rebalance calendar looks strictly backwards.** A session is a rebalance if it is the run's first
or if its calendar month differs from that of the previous session the strategy saw. Month-*end*
would need tomorrow's date to be decidable today. See G2-CONFLICT-8.

**Equal weight is an entry rule, not a maintained state.** A symbol that survives a rebalance is left
exactly as it is — never trimmed, never topped up. See G2-CONFLICT-10.
"""

from __future__ import annotations

import calendar
import datetime as dt
import hashlib
import json
from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal
from functools import lru_cache
from typing import Any, Sequence

from stockedge100.audit import sha256_file
from stockedge100.backtest.config import PROJECT_ROOT, dec
from stockedge100.backtest.costs import BASE, CostModel, ZERO, exact, round_down_cent
from stockedge100.backtest.engine import DecisionContext, OrderRequest
from stockedge100.backtest.errors import ConfigViolation, DataIntegrityHalt
from stockedge100.backtest.g2_costs import concentration_ceiling, rotation_cost_model
from stockedge100.backtest.market import MarketView
from stockedge100.backtest.orders import BUY, SELL
from stockedge100.strategies.base import Candidate

__all__ = [
    "PROTOCOL_PATH",
    "PROTOCOL_ID",
    "STRATEGY_ID",
    "QUARTER_MONTHS",
    "load_protocol",
    "eligible_universe",
    "month_offset",
    "target_weight",
    "RotationVariant",
    "rotation_variants",
    "variant_by_id",
    "total_return",
    "RotationCandidate",
]

PROTOCOL_PATH = PROJECT_ROOT / "config" / "generation_2" / "g2_rotation_protocol.json"
PROTOCOL_ID = "SE100-CFG-3101"
STRATEGY_ID = "SE100-G2-S3-C1-ROTATION"
UNIVERSE_REL = "governance/STAGE_1_UNIVERSE.json"

#: The months a quarterly variant rebalances in. Read back from the seal in :func:`load_protocol`.
QUARTER_MONTHS = (1, 4, 7, 10)

MONTHLY = "MONTHLY"
QUARTERLY = "QUARTERLY"


# -- the seal ------------------------------------------------------------------------------------


@lru_cache(maxsize=1)
def load_protocol() -> dict[str, Any]:
    """The sealed Stage 3 protocol, checked for identity before any field of it is believed."""
    if not PROTOCOL_PATH.is_file():
        raise ConfigViolation(f"the Generation 2 rotation protocol is missing at {PROTOCOL_PATH}")
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))

    for field, expected in (
        ("artifact_id", PROTOCOL_ID),
        ("generation", 2),
        ("stage", 3),
        ("strategy_id", STRATEGY_ID),
    ):
        if protocol.get(field) != expected:
            raise ConfigViolation(
                f"{PROTOCOL_PATH.name} declares {field}={protocol.get(field)!r}; this module "
                f"implements {expected!r}"
            )
    if protocol.get("declared_before_any_strategy_code") is not True:
        raise ConfigViolation(
            f"{PROTOCOL_PATH.name} no longer asserts declared_before_any_strategy_code. The whole "
            "point of this file is that it predates this one."
        )

    universe = protocol["eligible_universe"]
    on_disk = sha256_file(PROJECT_ROOT / UNIVERSE_REL)
    if on_disk != universe["source_sha256"]:
        raise ConfigViolation(
            f"the protocol pins {UNIVERSE_REL} at {universe['source_sha256']} but the file on disk "
            f"is {on_disk}. The Stage 1 universe is frozen; a difference is a governance failure, "
            "not a value to update."
        )
    sealed_members = json.loads((PROJECT_ROOT / UNIVERSE_REL).read_text(encoding="utf-8"))["members"]
    if sorted(sealed_members) != sorted(universe["members"]) or len(sealed_members) != universe["member_count"]:
        raise ConfigViolation(
            f"the protocol's member list does not match {UNIVERSE_REL}. Generation 2 re-checks "
            "eligibility on development data; it never adds, drops or substitutes a symbol."
        )

    # The quarterly months are prose in the seal, not a list, so they are checked as prose. Naming
    # them in code and never confirming them against the artifact would leave the one place a
    # quarterly variant could silently rebalance on the wrong months unguarded.
    rule = protocol["rebalance"]["rule"]
    named = ", ".join(calendar.month_name[month] for month in QUARTER_MONTHS[:-1])
    if f"{named} and {calendar.month_name[QUARTER_MONTHS[-1]]}" not in rule:
        raise ConfigViolation(
            f"the sealed rebalance rule does not name the quarterly months this module implements "
            f"({named} and {calendar.month_name[QUARTER_MONTHS[-1]]}). Rule as sealed: {rule!r}"
        )
    return protocol


def eligible_universe() -> tuple[str, ...]:
    """The 34 frozen members, sorted. Ranked in full at every scheduled rebalance."""
    return tuple(sorted(load_protocol()["eligible_universe"]["members"]))


# -- calendar arithmetic -------------------------------------------------------------------------


def month_offset(day: dt.date, months: int) -> dt.date:
    """Shift the calendar month by ``months``, clamping the day to the last day of the result.

    Pure calendar arithmetic: it reads no market data and knows nothing about which days the exchange
    was open. ``month_offset(2021-03-31, -1)`` is ``2021-02-28``.
    """
    index = day.year * 12 + (day.month - 1) + months
    year, month_index = divmod(index, 12)
    month = month_index + 1
    return dt.date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def is_scheduled_rebalance(session: dt.date, previous: dt.date | None, frequency: str) -> bool:
    """The sealed rule, and nothing else: first session, or a month boundary already crossed.

    ``previous`` is the last session the strategy actually saw, so the comparison never consults a
    calendar of sessions that have not happened. See G2-CONFLICT-8 for why month-*end* was rejected.
    """
    if frequency not in (MONTHLY, QUARTERLY):
        raise ConfigViolation(f"unknown rebalance frequency {frequency!r}")
    if previous is None:
        return True
    if (session.year, session.month) == (previous.year, previous.month):
        return False
    return frequency == MONTHLY or session.month in QUARTER_MONTHS


# -- sizing --------------------------------------------------------------------------------------


@exact
def target_weight(k: int, costs: CostModel) -> Decimal:
    """``w(k) = min(0.95 / k, 0.50)``, quantized to ``share_decimals`` places, ROUND_DOWN.

    Both fractions are read from sealed files rather than written here, and the result is checked
    against the protocol's own declared table. ROUND_DOWN is load-bearing: at ``prec=34`` and
    ROUND_HALF_EVEN, ``0.95 / 3`` rounds up and three such weights exceed the gross ceiling by one
    ulp, which would make the aggregate clamp bind on the last buy of every k=3 rebalance for a pure
    representation reason.
    """
    if k <= 0:
        raise ConfigViolation(f"k={k!r} is not a position count")
    weight = min(costs.max_gross_exposure_fraction / k, concentration_ceiling())
    weight = weight.quantize(costs.share_quantum, rounding=ROUND_DOWN)

    declared = load_protocol()["position_sizing"]["target_weights"].get(str(k))
    if declared is None:
        raise ConfigViolation(f"the protocol declares no target weight for k={k}")
    if weight != dec(declared):
        raise ConfigViolation(
            f"w({k}) derives to {weight} from the sealed ceilings but the protocol declares "
            f"{declared}. Refusing to size a position against a weight that disagrees with its own "
            "pre-registration."
        )
    if k * weight > costs.max_gross_exposure_fraction:
        raise ConfigViolation(
            f"{k} * w({k}) = {k * weight} exceeds the sealed gross ceiling "
            f"{costs.max_gross_exposure_fraction}"
        )
    return weight


# -- the grid ------------------------------------------------------------------------------------


@dataclass(frozen=True)
class RotationVariant:
    """One of the eighteen declared parameterisations. Constructed only from the seal."""

    index: int
    variant_id: str
    lookback_months: int
    top_k: int
    frequency: str
    target_weight: Decimal
    scheduled_rebalance_sessions: int

    def to_json(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "variant_id": self.variant_id,
            "lookback_months": self.lookback_months,
            "top_k": self.top_k,
            "rebalance_frequency": self.frequency,
            "target_weight_per_position": f"{self.target_weight:f}",
            "scheduled_rebalance_sessions": self.scheduled_rebalance_sessions,
        }


def _variant_id(lookback: int, k: int, frequency: str) -> str:
    """The sealed id format. Zero-padded, because the final tiebreak is lexicographic and an
    unpadded ``L12`` would sort before ``L3``."""
    return f"{STRATEGY_ID}-L{lookback:02d}-K{k}-{frequency}"


@lru_cache(maxsize=1)
def rotation_variants() -> tuple[RotationVariant, ...]:
    """All eighteen, in the sealed order, rebuilt from the axes and checked against the seal.

    Rebuilding from ``grid.axes`` rather than reading ``grid.variants`` straight through means the
    declared list is *verified* rather than trusted: a variant silently added to or removed from the
    seal would show up as a length or id mismatch here instead of quietly becoming a nineteenth run.
    """
    protocol = load_protocol()
    grid = protocol["grid"]
    axes = grid["axes"]
    declared = {entry["variant_id"]: entry for entry in grid["variants"]}
    built: list[RotationVariant] = []
    index = 0
    for lookback in axes["lookback_months"]:
        for k in axes["top_k"]:
            for frequency in axes["rebalance_frequency"]:
                index += 1
                variant_id = _variant_id(int(lookback), int(k), str(frequency))
                entry = declared.get(variant_id)
                if entry is None:
                    raise ConfigViolation(
                        f"the axes generate {variant_id} but the sealed variant list does not "
                        "contain it"
                    )
                if entry["index"] != index:
                    raise ConfigViolation(
                        f"{variant_id} is declared at index {entry['index']} but the axes place it "
                        f"at {index}; the enumeration order is part of the seal"
                    )
                weight = target_weight(int(k), rotation_cost_model(int(k), BASE))
                if weight != dec(entry["target_weight_per_position"]):
                    raise ConfigViolation(
                        f"{variant_id} declares weight {entry['target_weight_per_position']} but "
                        f"w({k}) is {weight}"
                    )
                built.append(
                    RotationVariant(
                        index=index,
                        variant_id=variant_id,
                        lookback_months=int(lookback),
                        top_k=int(k),
                        frequency=str(frequency),
                        target_weight=weight,
                        scheduled_rebalance_sessions=int(entry["scheduled_rebalance_sessions"]),
                    )
                )

    if len(built) != grid["size"] or len(built) != len(declared):
        raise ConfigViolation(
            f"the axes generate {len(built)} variants against a declared size of {grid['size']} and "
            f"{len(declared)} declared entries. The grid is complete at eighteen and may not be "
            "widened, narrowed, or re-centred."
        )
    return tuple(built)


def variant_by_id(variant_id: str) -> RotationVariant:
    for variant in rotation_variants():
        if variant.variant_id == variant_id:
            return variant
    raise ConfigViolation(f"{variant_id!r} is not one of the eighteen declared variants")


# -- the ranking signal --------------------------------------------------------------------------


@exact
def total_return(
    view: MarketView,
    symbol: str,
    session: dt.date,
    lookback_months: int,
) -> Decimal | None:
    """N-month total return to ``session``'s close, or ``None`` if the symbol cannot be ranked.

    ``None`` means *excluded from this date's ranking*, which the caller records. It never means
    zero: a symbol with no history is not a symbol that went nowhere.
    """
    reference = month_offset(session, -lookback_months)
    bars = _bars_back_to(view, symbol, session, reference)
    if not bars or bars[-1].session != session:
        return None

    start = None
    for position in range(len(bars) - 1, -1, -1):
        if bars[position].session <= reference:
            start = position
            break
    if start is None or start == len(bars) - 1:
        return None

    interval = bars[start:]
    chain = Decimal(1)
    for previous, current in zip(interval, interval[1:]):
        if not current.dividend:
            continue
        if previous.close <= ZERO:
            raise DataIntegrityHalt(
                f"{symbol}: close {previous.close} on {previous.session.isoformat()} is not "
                "positive, so the dividend chain cannot be formed"
            )
        factor = Decimal(1) - current.dividend / previous.close
        if factor <= ZERO:
            raise DataIntegrityHalt(
                f"{symbol}: dividend {current.dividend} on {current.session.isoformat()} is not "
                f"below the previous close {previous.close}; the adjustment factor {factor} is not "
                "positive"
            )
        chain *= factor
    return (interval[-1].close / interval[0].close) / chain - 1


def _bars_back_to(view: MarketView, symbol: str, session: dt.date, reference: dt.date):
    """Visible bars reaching at least back to ``reference``, or as far back as the symbol goes.

    The count is doubled rather than guessed at once, so a long exchange closure or a data gap
    lengthens the request instead of silently truncating the interval. ``history`` is the only door
    into the data a strategy has, and it never returns anything after the decision session.
    """
    count = max((session - reference).days + 16, 16)
    while True:
        bars = view.history(symbol, count)
        if not bars or bars[0].session <= reference or len(bars) < count:
            return bars
        count *= 2


# -- the candidate -------------------------------------------------------------------------------


class RotationCandidate(Candidate):
    """Cross-sectional relative strength over the full eligible universe.

    Overrides :meth:`Candidate.decide` and :meth:`Candidate.entry_order`. The inherited ``decide`` is
    the single-position ``flat_first_rule``, which exists because Generation 1's engine sorts fills
    by ``(symbol, side, order_id)`` and would settle a purchase before the sale funding it;
    :class:`~stockedge100.backtest.g2_engine.RotationEngine` sells before it buys, so the two legs of
    a rotation are emitted together here. The inherited ``entry_order`` requests 95% of equity, which
    is the right size for a portfolio of one and the wrong size for a portfolio of k.
    """

    family = "CROSS_SECTIONAL_RELATIVE_STRENGTH"

    def __init__(
        self,
        variant: RotationVariant,
        costs: CostModel,
        *,
        universe: Sequence[str] | None = None,
    ) -> None:
        super().__init__(
            experiment_id=STRATEGY_ID,
            variant_id=variant.variant_id,
            universe=eligible_universe() if universe is None else universe,
            parameters={
                "lookback_months": variant.lookback_months,
                "top_k": variant.top_k,
                "rebalance_frequency": variant.frequency,
                "target_weight": variant.target_weight,
            },
            costs=costs,
        )
        self.variant = variant
        self.weight = target_weight(variant.top_k, costs)
        if self.weight != variant.target_weight:
            raise ConfigViolation(
                f"{variant.variant_id}: the candidate derived w={self.weight} against the variant's "
                f"{variant.target_weight}"
            )

        self._previous_session: dt.date | None = None
        self._ranking_hash = hashlib.sha256()

        # Evidence, not bookkeeping: every one of these is reported for all eighteen variants.
        self.scheduled_rebalances = 0
        self.executed_rebalances = 0
        self.rebalances_blocked_by_shutdown = 0
        self.exclusions: dict[str, int] = {}
        self.selection_log: list[dict[str, Any]] = []

    # -- decisions -------------------------------------------------------------------------------

    def rank(self, view: MarketView, session: dt.date) -> tuple[list[tuple[Decimal, str]], list[str]]:
        """The whole universe scored and sorted by the sealed key ``(-signal, symbol)``.

        The tie-break is the ascending ticker applied to exactly equal ``Decimal`` signals, so the
        result cannot depend on dict insertion order or on the order the files happened to load in.
        """
        scored: list[tuple[Decimal, str]] = []
        excluded: list[str] = []
        for symbol in self.universe:
            signal = total_return(view, symbol, session, self.variant.lookback_months)
            if signal is None:
                excluded.append(symbol)
                self.exclusions[symbol] = self.exclusions.get(symbol, 0) + 1
                continue
            scored.append((signal, symbol))
        scored.sort(key=lambda pair: (-pair[0], pair[1]))
        return scored, excluded

    def decide(self, view: MarketView, context: DecisionContext) -> list[OrderRequest]:
        session = context.session
        previous = self._previous_session
        self._previous_session = session

        if not is_scheduled_rebalance(session, previous, self.variant.frequency):
            return []
        self.scheduled_rebalances += 1

        if context.shutdown_active:
            # Entries are blocked and every position has already been liquidated at the open. Ranking
            # would read data to produce orders that cannot be filled.
            self.rebalances_blocked_by_shutdown += 1
            return []

        scored, excluded = self.rank(view, session)
        targets = [symbol for _, symbol in scored[: self.variant.top_k]]

        self._ranking_hash.update(
            f"{session.isoformat()}|{'|'.join(f'{s}:{v:f}' for v, s in scored)}\n".encode("utf-8")
        )

        held = set(context.open_symbols)
        exits = sorted(held.difference(targets))
        entries = [symbol for symbol in targets if symbol not in held]
        if set(exits) & set(entries):
            # OrderBook.submit rejects two orders in one symbol on one decision session whatever the
            # sides are, so this would raise DuplicateOrderError rather than misbehave quietly. It
            # cannot happen — a symbol is either in the target set or out of it — and is asserted
            # because "cannot happen" is a claim, not a guarantee.
            raise DataIntegrityHalt(
                f"{self.variant_id} on {session.isoformat()}: {sorted(set(exits) & set(entries))} "
                "would be both sold and bought on one session"
            )

        self.executed_rebalances += 1
        self.selection_log.append(
            {
                "session": session.isoformat(),
                "targets": list(targets),
                "ranked": len(scored),
                "excluded": excluded,
                "exits": exits,
                "entries": entries,
            }
        )

        requests = [self.exit_order(symbol) for symbol in exits]
        requests.extend(self.entry_order(symbol, context) for symbol in entries)
        return requests

    def entry_order(self, symbol: str, context: DecisionContext) -> OrderRequest:
        """``w(k) · equity``, evaluated here at the decision close.

        The engine re-evaluates the same formula against equity at the fill session's open, which is
        what the seal specifies; a frozen ``Order`` has nowhere to carry a weight, so this value is
        the record of the intent rather than the number that sizes the fill. See G2-CONFLICT-16.
        """
        budget = round_down_cent(self.weight * context.equity)
        return OrderRequest(symbol=symbol, side=BUY, budget=budget, tag=self.experiment_id)

    def target(self, view: MarketView, context: DecisionContext) -> str | None:
        """Unreachable. A cross-sectional candidate has a target *set*; ``decide`` is overridden."""
        raise NotImplementedError(
            "RotationCandidate selects k symbols; use rank() or decide(). A single-symbol target() "
            "would be the Generation 1 shape this generation exists to leave behind."
        )

    # -- evidence --------------------------------------------------------------------------------

    @property
    def ranking_digest(self) -> str:
        """SHA-256 over every ranking the run produced, in order.

        Determinism across a clean rerun is a gated claim in this stage, and equal equity curves are
        weaker evidence than equal *decisions*: two runs could agree on the curve while disagreeing
        about a rank whose difference never reached an order.
        """
        return self._ranking_hash.hexdigest()

    def evidence(self) -> dict[str, Any]:
        return {
            "variant": self.variant.to_json(),
            "universe_size": len(self.universe),
            "scheduled_rebalances": self.scheduled_rebalances,
            "executed_rebalances": self.executed_rebalances,
            "rebalances_blocked_by_shutdown": self.rebalances_blocked_by_shutdown,
            "exclusion_events": sum(self.exclusions.values()),
            "excluded_symbols": dict(sorted(self.exclusions.items())),
            "ranking_digest": self.ranking_digest,
            "distinct_symbols_targeted": len(
                {symbol for entry in self.selection_log for symbol in entry["targets"]}
            ),
        }
