"""Attempt 2's session loop: Attempt 1's rotation engine under risk architecture **RA2**.

Attempt 1 (``g2_engine.py``) ended ``FAIL — STAGE_3_G2_NO_CANDIDATE`` because all eighteen variants
recorded a research-shutdown event. It had a shutdown trip-wire and no mechanism to reduce exposure
*before* a breach. RA2 is that mechanism, sealed in
``config/generation_2/g2_rotation_ra1_protocol.json`` §``risk_architecture`` before any line of this
file existed, and this module is its implementation.

The module name carries the ``_ra1`` suffix and the architecture is called ``RA2``. That is not a
typo: the seal's ``provenance`` field records that RA2-2, RA2-3 and three of RA2-4's four bands are
carried from **Generation 1's RA1**, and the suffix names that lineage rather than the architecture's
own id. Attempt 1's modules keep their unsuffixed names and are imported, never modified.

Five components, all fixed constants applied uniformly to all eighteen variants and none of them a
grid axis:

===========  ==================================================================================
``RA2-1``    aggregate exposure ceiling, 50% of equity — an entry clamp *and* a continuous trim
``RA2-2``    10% annualized portfolio volatility target, measured on the **equity curve**
``RA2-3``    8% per-position stop against ``cost_basis / quantity``, exited at the next open
``RA2-4``    four-band de-risk ladder on the drawdown from the engine's own high-water mark
``RA2-5``    ten-session re-entry lockout gating every upward ladder transition
===========  ==================================================================================

Where the state lives, and why here
-----------------------------------

The candidate sees only :class:`~stockedge100.backtest.engine.DecisionContext`, which carries
``(session, cash, equity, open_symbols, shutdown_active)``. It carries no per-position cost basis —
needed for RA2-3 — and no high-water mark — needed for RA2-4. Extending it would mean editing
``backtest/engine.py``, a Generation 1 file that is frozen. So the engine owns the state, and it can,
because the Generation 1 session loop runs the risk step (step 6: record equity, update the
high-water mark, test the shutdown) strictly **before** the decision step (step 7: build the context
and call the candidate). Three override points suffice and no base-class line changes:

``_check_risk``      step 6. ``super()`` first — it updates ``_high_water`` before returning — then
                     RA2-2's scalar, RA2-4's band transition and RA2-5's countdown, from the equity
                     point that was appended a moment earlier. The shutdown verdict is returned
                     unchanged: RA2 never suppresses it.
``_schedule``        step 7. STOP and THROTTLE legs are computed and merged into the candidate's
                     EXIT/ENTRY requests under the frozen precedence ``STOP > EXIT > THROTTLE >
                     ENTRY`` before ``super()`` admits them. Guarded on ``not forced``: the base loop
                     uses the ``forced=True`` path for the shutdown liquidation and then abandons the
                     session, and injecting risk legs into it would fight the constitution.
``_execute_buy``     step 2 of the following session. Attempt 1's four clamps with ``AGGREGATE_RA2``
                     inserted second, and the budget re-evaluated as ``w(k) · f · equity`` rather
                     than ``w(k) · equity``.

Why ``AGGREGATE_RA2`` is a new clamp and not a lower cost-model ceiling
----------------------------------------------------------------------

:func:`stockedge100.backtest.g2_costs.derive_mapping` permits exactly **one** JSON-pointer difference
from the Generation 1 sealed cost model, and that single override is already spent on
``/account/max_open_risky_positions``. Lowering ``max_gross_exposure_fraction`` to 0.50 would need a
second one and would silently change the meaning of every cost-model-derived quantity Attempt 1
recorded. So the 0.95 ``AGGREGATE`` clamp stays in place, is never the binding one, and is reported
as such. Recorded as ``G2A2-CONFLICT-2`` and ``G2A2-CONFLICT-16``.

Why the throttle is mandatory rather than an extra
--------------------------------------------------

A ladder that reduced sizing only at entries would do nothing between scheduled rebalances — which is
exactly when Attempt 1's drawdowns happened; a quarterly variant takes 53 sizing decisions in
thirteen years. Worked example from the seal: gross 50, cash 50, equity 100, exposure 0.500; the
position doubles; gross 100, cash 50, equity 150, exposure 0.667. No order was placed and the ceiling
is breached by a third. Only a continuous measurement catches it. ``G2A2-CONFLICT-17``.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_DOWN, Decimal

from stockedge100.backtest.config import PROJECT_ROOT, dec
from stockedge100.backtest.costs import CostModel, ZERO, exact
from stockedge100.backtest.dataset import PriceSeries
from stockedge100.backtest.engine import FillRecord, OrderRequest, Probe
from stockedge100.backtest.errors import (
    ConfigViolation,
    DataIntegrityHalt,
    InvariantViolation,
)
from stockedge100.backtest.g2_engine import CLAMP_NAMES, RotationEngine
from stockedge100.backtest.orders import SELL, make_order_id
from stockedge100.backtest.window import ResearchWindow
from stockedge100.strategies.attempt2_indicators import (
    TRADING_DAYS_PER_YEAR,
    VOL20_BARS,
    VOL20_RETURNS,
    VOL20_VARIANCE_DENOMINATOR,
)

__all__ = [
    "CLAMP_NAMES_RA2",
    "ORDER_KIND_PRECEDENCE",
    "PROTOCOL_ID",
    "PROTOCOL_PATH",
    "SCALAR_DECIMALS",
    "SCALAR_QUANTUM",
    "SPELLED_DECIMALS",
    "STRATEGY_ID",
    "LadderBand",
    "RiskArchitecture",
    "RotationEngineRA1",
    "load_ra1_protocol",
    "load_risk_architecture",
    "quantize_scalar",
]

ONE = Decimal(1)

#: The sealed Attempt 2 protocol. Read, never written, and checked for identity before believed.
PROTOCOL_PATH = PROJECT_ROOT / "config" / "generation_2" / "g2_rotation_ra1_protocol.json"
PROTOCOL_ID = "SE100-CFG-3103"
STRATEGY_ID = "SE100-G2-S3-C2-ROTATION-RA1"

#: Clamp labels a rejection detail may name. Attempt 1's four with ``AGGREGATE_RA2`` inserted second,
#: so that the binding clamp is reported by its own name rather than masked by the looser 0.95 cap.
#: The order is behaviour, not iteration order: the first of two equal minima binds.
CLAMP_NAMES_RA2 = ("REQUESTED_BUDGET", "AGGREGATE_RA2", "AGGREGATE", "CASH_FLOOR", "CONCENTRATION")

#: Frozen precedence for merging order kinds by symbol. ``OrderBook.submit`` refuses two orders in one
#: symbol on one decision session whatever the sides are, so this is what keeps a stop and a signal
#: exit from colliding into a ``DuplicateOrderError``.
ORDER_KIND_PRECEDENCE = ("STOP", "EXIT", "THROTTLE", "ENTRY")

#: The sealed quantization of every risk scalar: nine decimal places, ROUND_DOWN.
SCALAR_DECIMALS = 9
SCALAR_QUANTUM = Decimal(1).scaleb(-SCALAR_DECIMALS)

#: The seal states the precision as an English word. Looking it up rather than hardcoding the string
#: means changing ``SCALAR_DECIMALS`` raises a ``KeyError`` here instead of quietly disagreeing with a
#: sealed document that still says "nine".
SPELLED_DECIMALS = {9: "nine"}


@exact
def quantize_scalar(value: Decimal) -> Decimal:
    """Nine decimal places, ROUND_DOWN. Always toward less exposure, never toward more."""
    return value.quantize(SCALAR_QUANTUM, rounding=ROUND_DOWN)


def load_ra1_protocol() -> dict[str, object]:
    """The sealed Attempt 2 protocol, checked for identity before any field of it is believed.

    Mirrors :func:`stockedge100.strategies.g2_rotation.load_protocol`. The point of the file is that
    it predates this one, so a copy that no longer says so is not the file this module implements.
    """
    if not PROTOCOL_PATH.is_file():
        raise ConfigViolation(f"the Attempt 2 rotation protocol is missing at {PROTOCOL_PATH}")
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))

    for field, expected in (
        ("artifact_id", PROTOCOL_ID),
        ("generation", 2),
        ("stage", 3),
        ("attempt", 2),
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
            "point of that file is that it predates this one."
        )
    if protocol.get("live_trading_authorized") is not False:
        raise ConfigViolation(
            f"{PROTOCOL_PATH.name} does not declare live_trading_authorized false; this is a "
            "development-window research module and may never run against a broker"
        )
    return protocol


@dataclass(frozen=True)
class LadderBand:
    """One rung of RA2-4. Closed at ``dd_from``, open at ``dd_to_exclusive``."""

    band: int
    dd_from: Decimal
    dd_to_exclusive: Decimal | None
    scalar: Decimal

    def contains(self, drawdown: Decimal) -> bool:
        if drawdown < self.dd_from:
            return False
        return self.dd_to_exclusive is None or drawdown < self.dd_to_exclusive

    def to_json(self) -> dict[str, object]:
        return {
            "band": self.band,
            "dd_from": f"{self.dd_from:f}",
            "dd_to_exclusive": None if self.dd_to_exclusive is None else f"{self.dd_to_exclusive:f}",
            "scalar": f"{self.scalar:f}",
        }


@dataclass(frozen=True)
class RiskArchitecture:
    """RA2's five constants, parsed from the seal and validated as a whole.

    Every value is read from the sealed protocol rather than accepted from a caller. A ceiling a test
    could pass in is a ceiling a strategy could pass in — the same reasoning Attempt 1 applied to its
    concentration ceiling.
    """

    architecture_id: str
    exposure_ceiling: Decimal
    volatility_target: Decimal
    stop_fraction: Decimal
    bands: tuple[LadderBand, ...]
    lockout_sessions: int

    def band_for(self, drawdown: Decimal) -> int:
        for band in self.bands:
            if band.contains(drawdown):
                return band.band
        raise InvariantViolation(
            f"drawdown {drawdown} falls in no declared ladder band; the bands are not exhaustive"
        )

    def scalar_of(self, band: int) -> Decimal:
        return self.bands[band].scalar

    def to_json(self) -> dict[str, object]:
        return {
            "architecture_id": self.architecture_id,
            "exposure_ceiling": f"{self.exposure_ceiling:f}",
            "volatility_target": f"{self.volatility_target:f}",
            "volatility_window_bars": VOL20_BARS,
            "volatility_returns": VOL20_RETURNS,
            "volatility_variance_denominator": VOL20_VARIANCE_DENOMINATOR,
            "annualisation_sessions": TRADING_DAYS_PER_YEAR,
            "stop_fraction": f"{self.stop_fraction:f}",
            "bands": [band.to_json() for band in self.bands],
            "lockout_sessions": self.lockout_sessions,
            "scalar_decimals": SCALAR_DECIMALS,
        }


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ConfigViolation(message)


def load_risk_architecture(protocol: dict[str, object] | None = None) -> RiskArchitecture:
    """Parse and validate RA2 from the seal.

    The validation is not decoration. Every rule below is a sentence the sealed document states in
    prose, restated as a predicate, so that a protocol which says something else refuses to run
    rather than being silently reinterpreted by this file.
    """
    protocol = protocol if protocol is not None else load_ra1_protocol()
    architecture = protocol["risk_architecture"]

    _require(architecture["id"] == "RA2", "the sealed risk architecture is not RA2")
    _require(
        architecture["frozen_before_any_variant_is_run"] is True,
        "the sealed risk architecture no longer asserts it was frozen before any variant was run",
    )
    _require(
        architecture["not_part_of_the_grid"] is True,
        "the sealed risk architecture no longer asserts its constants are not grid axes",
    )

    components = architecture["components"]
    combined = architecture["combined_scalar"]
    _require(
        "f_vol(t) * f_ladder(t)" in combined["formula"],
        "the sealed combined scalar is no longer the product of the two terms; this module "
        "multiplies them and would silently implement a different rule",
    )
    _require(
        f"{SPELLED_DECIMALS[SCALAR_DECIMALS]} decimal places" in combined["formula"]
        and "ROUND_DOWN" in combined["formula"],
        f"the sealed combined scalar no longer quantizes to {SCALAR_DECIMALS} places ROUND_DOWN",
    )
    _require(
        any("research shutdown" in item for item in combined["does_not_apply_to"]),
        "the sealed combined scalar no longer exempts the constitutional research shutdown",
    )

    ra1 = components["RA2-1"]
    _require(
        tuple(ra1["enforcement"]["part_a_entry_clamp"]["clamp_names"]) == CLAMP_NAMES_RA2,
        f"the sealed clamp names {ra1['enforcement']['part_a_entry_clamp']['clamp_names']} are not "
        f"the ones this engine applies {list(CLAMP_NAMES_RA2)}",
    )
    exposure_ceiling = dec(ra1["value"])

    ra2 = components["RA2-2"]
    _require(
        ra2["measured_on"] == "THE_EQUITY_CURVE",
        "the sealed volatility target is no longer measured on the equity curve",
    )
    volatility_target = dec(ra2["value"])

    ra3 = components["RA2-3"]
    _require(
        ra3["reference_price"] == "cost_basis / quantity",
        "the sealed stop reference price is no longer cost_basis / quantity",
    )
    stop_fraction = dec(ra3["value"])

    ra4 = components["RA2-4"]
    bands: list[LadderBand] = []
    for index, entry in enumerate(ra4["bands"]):
        _require(entry["band"] == index, "the sealed ladder bands are not indexed 0..n-1 in order")
        upper = entry["dd_to_exclusive"]
        bands.append(
            LadderBand(
                band=index,
                dd_from=dec(entry["dd_from"]),
                dd_to_exclusive=None if upper is None else dec(upper),
                scalar=dec(entry["scalar"]),
            )
        )

    ra5 = components["RA2-5"]
    lockout_sessions = ra5["value"]
    _require(
        isinstance(lockout_sessions, int) and not isinstance(lockout_sessions, bool),
        "the sealed re-entry lockout is not an integer number of sessions",
    )
    _require(
        ra5["counted_in_sessions_not_days"].startswith("Trading sessions"),
        "the sealed re-entry lockout is no longer counted in trading sessions",
    )

    architecture_object = RiskArchitecture(
        architecture_id=architecture["id"],
        exposure_ceiling=exposure_ceiling,
        volatility_target=volatility_target,
        stop_fraction=stop_fraction,
        bands=tuple(bands),
        lockout_sessions=lockout_sessions,
    )
    _validate_architecture(architecture_object)
    return architecture_object


def _validate_architecture(architecture: RiskArchitecture) -> None:
    """Shape checks that no single field can express."""
    _require(
        ZERO < architecture.exposure_ceiling <= ONE,
        f"the aggregate exposure ceiling {architecture.exposure_ceiling} is not a fraction in (0, 1]",
    )
    _require(
        architecture.volatility_target > ZERO,
        f"the volatility target {architecture.volatility_target} is not positive",
    )
    _require(
        ZERO < architecture.stop_fraction < ONE,
        f"the per-position stop {architecture.stop_fraction} is not a fraction in (0, 1)",
    )
    _require(
        architecture.lockout_sessions >= 0,
        f"the re-entry lockout {architecture.lockout_sessions} is negative",
    )

    bands = architecture.bands
    _require(len(bands) >= 2, "a ladder with fewer than two bands is not a ladder")
    _require(bands[0].dd_from == ZERO, "the shallowest ladder band does not start at a zero drawdown")
    _require(bands[0].scalar == ONE, "the shallowest ladder band does not size at full weight")
    _require(
        bands[-1].dd_to_exclusive is None,
        "the deepest ladder band has an upper bound, so a deep enough drawdown falls in no band",
    )
    for shallower, deeper in zip(bands, bands[1:]):
        _require(
            shallower.dd_to_exclusive is not None
            and shallower.dd_to_exclusive == deeper.dd_from,
            f"ladder bands {shallower.band} and {deeper.band} are not contiguous; a drawdown "
            "between them would fall in no band or in two",
        )
        _require(
            deeper.scalar < shallower.scalar,
            f"ladder band {deeper.band} does not size strictly below band {shallower.band}; a "
            "ladder that does not de-risk as the drawdown deepens is not a de-risk ladder",
        )
    for band in bands:
        _require(
            ZERO < band.scalar <= ONE,
            f"ladder band {band.band} scalar {band.scalar} is not a fraction in (0, 1]",
        )

    _require(
        CLAMP_NAMES_RA2[:1] == CLAMP_NAMES[:1] and CLAMP_NAMES_RA2[2:] == CLAMP_NAMES[1:],
        f"the Attempt 2 clamps {list(CLAMP_NAMES_RA2)} are not Attempt 1's {list(CLAMP_NAMES)} with "
        "exactly one clamp inserted; the inherited ceilings must all still be applied",
    )


class RotationEngineRA1(RotationEngine):
    """The Attempt 1 rotation engine under RA2.

    Subclasses rather than forks. Everything not overridden — dividends, corporate-action continuity,
    delisting, staleness, the equity curve, sell execution, the research shutdown, the decision
    ordering, and Attempt 1's own sells-before-buys re-sort — is inherited, so a change to the sealed
    session order reaches Attempt 2 automatically and cannot be forked by accident.
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
            budget_weight=budget_weight,
        )

        self.risk = load_risk_architecture()

        # -- RA2 state, owned here because DecisionContext cannot carry it ------------------------
        self._band = 0
        self._lockout_until_index: int | None = None
        self._vol_scalar = ONE
        self._combined_scalar = ONE
        #: decision session -> the combined scalar in force at that close, read again at the fill open.
        self._scalar_at_decision: dict[dt.date, Decimal] = {}
        #: set for the duration of one buy so the ceiling assertion can re-derive the same ceiling.
        self._fill_scalar: Decimal | None = None
        self._risk_trace: list[str] = []

        # -- measurement ---------------------------------------------------------------------------
        self.binding_clamp_counts = {name: 0 for name in CLAMP_NAMES_RA2}
        self.ladder_descents = 0
        self.ladder_ascents = 0
        self.lockout_arms = 0
        self.recoveries_blocked = 0
        self.deepest_band = 0
        self.sessions_in_band: dict[int, int] = {band.band: 0 for band in self.risk.bands}
        self.vol_scalar_sessions_below_one = 0
        self.vol_scalar_min = ONE
        self.combined_scalar_min = ONE
        self.combined_scalar_sessions_below_one = 0
        self._combined_scalar_total = ZERO
        self._combined_scalar_points = 0
        self._vol_scalar_total = ZERO
        self._vol_scalar_points = 0
        self.vol_scalar_undefined_sessions = 0
        self.stop_events: list[dict[str, object]] = []
        self.stop_preempted_signal_exit = 0
        self.throttle_legs_scheduled = 0
        self.throttle_legs_below_min_notional = 0
        self.throttle_sessions = 0
        self._throttle_excess_total = ZERO
        self._throttle_skipped_notional = ZERO
        self.max_gross_fraction_observed = ZERO
        self.max_gross_fraction_session: dt.date | None = None
        self.suppressed_legs: list[dict[str, str]] = []

    # -- step 6: risk ----------------------------------------------------------------------------

    @exact
    def _check_risk(self, session: dt.date, equity: Decimal) -> bool:
        """Update RA2's state for this session, then answer the shutdown question unchanged.

        ``super()`` runs **first** and unconditionally raises ``_high_water`` to this session's equity
        before anything else, which is what lets RA2-4 read the engine's own high-water mark rather
        than keeping a second one. The ladder and the constitutional shutdown therefore cannot
        disagree about the drawdown — there is only one number.

        The return value is ``super()``'s. RA2 reduces exposure; it never suppresses a shutdown.
        """
        triggered = super()._check_risk(session, equity)

        if not self._equity or self._equity[-1].session != session:
            raise InvariantViolation(
                f"RA2 expected the equity point for {session.isoformat()} to have been recorded "
                "before the risk step; the sealed session order has changed underneath this engine"
            )
        index = len(self._equity) - 1

        self._vol_scalar = self._volatility_scalar()
        self._advance_ladder(index, equity)
        self._combined_scalar = quantize_scalar(
            self._vol_scalar * self.risk.scalar_of(self._band)
        )
        if self._combined_scalar <= ZERO:
            raise InvariantViolation(
                f"the combined risk scalar quantized to {self._combined_scalar} on "
                f"{session.isoformat()}; the sealed range is (0, 1] and a zero scalar means the "
                "measured volatility is not a market observation"
            )
        if self._combined_scalar < self.combined_scalar_min:
            self.combined_scalar_min = self._combined_scalar
        # The seal asks for "minimum and mean combined risk scalar, and sessions on which it was
        # below 1" for every variant. The minimum alone would let a variant that spent one session
        # at 0.25 read the same as one that spent nine hundred there.
        self._combined_scalar_total += self._combined_scalar
        self._combined_scalar_points += 1
        if self._combined_scalar < ONE:
            self.combined_scalar_sessions_below_one += 1

        self._record_gross_fraction(session, equity)
        self._risk_trace.append(
            "%s|%d|%d|%s|%s"
            % (
                session.isoformat(),
                self._band,
                self._lockout_remaining(index),
                f"{self._vol_scalar:f}",
                f"{self._combined_scalar:f}",
            )
        )
        return triggered

    @exact
    def _volatility_scalar(self) -> Decimal:
        """RA2-2. ``min(1, target / sigma_p)`` on the equity curve, quantized ROUND_DOWN.

        Exactly the shape of :func:`stockedge100.strategies.attempt2_indicators.vol20` — 21 points,
        20 returns, divide by 19, times the square root of 252 — applied to the portfolio's own
        realized return series rather than to a price series. The window length, the sample
        denominator and the annualisation factor are Generation 1's and are not re-chosen here, which
        is why they are imported rather than restated.
        """
        if len(self._equity) < VOL20_BARS:
            self.vol_scalar_undefined_sessions += 1
            return ONE

        levels = [point.equity for point in self._equity[-VOL20_BARS:]]
        for level in levels:
            if level <= ZERO:
                raise DataIntegrityHalt(
                    f"an equity point of {level} entered the volatility window; a non-positive "
                    "equity is a data or accounting defect, not a volatility measurement"
                )
        returns = [levels[i] / levels[i - 1] - ONE for i in range(1, VOL20_BARS)]
        mean = sum(returns, ZERO) / Decimal(VOL20_RETURNS)
        variance = sum(((value - mean) ** 2 for value in returns), ZERO) / Decimal(
            VOL20_VARIANCE_DENOMINATOR
        )
        sigma = variance.sqrt() * Decimal(TRADING_DAYS_PER_YEAR).sqrt()

        self._vol_scalar_points += 1
        if sigma <= ZERO:
            # A portfolio that has not moved has no volatility to target. Not a special case.
            self._vol_scalar_total += ONE
            return ONE

        scalar = self.risk.volatility_target / sigma
        if scalar > ONE:
            scalar = ONE
        scalar = quantize_scalar(scalar)
        self._vol_scalar_total += scalar
        if scalar < ONE:
            self.vol_scalar_sessions_below_one += 1
        if scalar < self.vol_scalar_min:
            self.vol_scalar_min = scalar
        return scalar

    @exact
    def _advance_ladder(self, index: int, equity: Decimal) -> None:
        """RA2-4 and RA2-5. Immediate descent, one-band recovery, gated by the lockout."""
        if self._high_water <= ZERO:
            raise InvariantViolation(
                f"the high-water mark is {self._high_water}; a drawdown cannot be measured against it"
            )
        drawdown = (self._high_water - equity) / self._high_water
        if drawdown < ZERO:
            raise InvariantViolation(
                f"drawdown resolved to {drawdown} with equity {equity} above the high-water mark "
                f"{self._high_water}, which super()._check_risk should already have raised"
            )

        computed = self.risk.band_for(drawdown)
        if computed > self._band:
            # Descent is immediate and to the full computed band. A fast drawdown is exactly the case
            # the ladder exists for, so there is no smoothing.
            self._band = computed
            self.ladder_descents += 1
            self.lockout_arms += 1
            self._lockout_until_index = index + self.risk.lockout_sessions
        elif computed < self._band:
            if self._lockout_until_index is not None and index < self._lockout_until_index:
                self.recoveries_blocked += 1
            else:
                # At most one band per session, whatever the computed band is. Climbing from band 3
                # to band 0 in one session is the re-levering the lockout exists to prevent.
                self._band -= 1
                self.ladder_ascents += 1

        if self._band > self.deepest_band:
            self.deepest_band = self._band
        self.sessions_in_band[self._band] += 1

    def _lockout_remaining(self, index: int) -> int:
        if self._lockout_until_index is None:
            return 0
        return max(0, self._lockout_until_index - index)

    @exact
    def _record_gross_fraction(self, session: dt.date, equity: Decimal) -> None:
        """RA2-1 part c. The ceiling is a claim; this is what makes it checkable."""
        if equity <= ZERO:
            return
        gross = sum(self._close_marked_values(session).values(), ZERO)
        fraction = gross / equity
        if fraction > self.max_gross_fraction_observed:
            self.max_gross_fraction_observed = fraction
            self.max_gross_fraction_session = session

    def _close_marked_values(self, session: dt.date) -> dict[str, Decimal]:
        """Each held position's value at this session's close.

        Reads ``_last_close``, which ``_record_equity`` has just refreshed for every open symbol, so
        these are the same marks the equity point was built from rather than a second reading of the
        series that could disagree with it.
        """
        values: dict[str, Decimal] = {}
        for symbol in self.portfolio.open_symbols():
            mark = self._last_close.get(symbol)
            if mark is None:
                raise DataIntegrityHalt(
                    f"{symbol} is held on {session.isoformat()} but has never been marked; the risk "
                    "step cannot value the book"
                )
            values[symbol] = self.portfolio.quantity_of(symbol) * mark
        return values

    # -- step 7: decisions -----------------------------------------------------------------------

    @exact
    def _schedule(
        self, session: dt.date, requests: list[OrderRequest], *, forced: bool
    ) -> None:
        """Merge RA2's risk legs into the candidate's requests, then admit them unchanged.

        ``forced=True`` is the base loop's research-shutdown liquidation, which sells the whole book
        and then abandons the session. Nothing is merged into it: a stop or a trim on top of a full
        liquidation is at best redundant and at worst a duplicate order in the same symbol, and the
        constitution's shutdown is not this attempt's to modify.
        """
        self._scalar_at_decision[session] = self._combined_scalar
        if forced:
            super()._schedule(session, requests, forced=forced)
            return
        super()._schedule(session, self._merge_risk_legs(session, list(requests)), forced=forced)

    @exact
    def _merge_risk_legs(
        self, session: dt.date, requests: list[OrderRequest]
    ) -> list[OrderRequest]:
        """Apply the frozen precedence ``STOP > EXIT > THROTTLE > ENTRY``, one leg per symbol.

        An ENTRY can never collide with a STOP, an EXIT or a THROTTLE, because all three apply only
        to currently held symbols and an ENTRY is issued only for symbols not currently held. The
        precedence is applied unconditionally anyway and the merged list is asserted unique, because
        "cannot happen" is a claim and not a guarantee.
        """
        marks = {}
        for symbol in self.portfolio.open_symbols():
            mark = self._last_close.get(symbol)
            if mark is None:
                raise DataIntegrityHalt(
                    f"{symbol} is held on {session.isoformat()} but has never been marked; the risk "
                    "legs for this session cannot be computed"
                )
            marks[symbol] = mark

        stops = self._stop_legs(session, marks)
        exits = sorted((r for r in requests if r.side == SELL), key=lambda r: r.symbol)
        entries = sorted((r for r in requests if r.side != SELL), key=lambda r: r.symbol)
        for request in exits:
            if request.quantity is not None:
                raise InvariantViolation(
                    f"the candidate asked to sell {request.quantity} of {request.symbol} on "
                    f"{session.isoformat()}; the seal declares EXIT legs whole, and the throttle "
                    "excludes an exiting symbol from the projected book on that basis"
                )
        stopped = {request.symbol for request in stops}
        surviving = {
            symbol: value
            for symbol, value in ((s, self.portfolio.quantity_of(s) * marks[s]) for s in marks)
            if symbol not in stopped and symbol not in {r.symbol for r in exits}
        }
        throttles = self._throttle_legs(session, marks, surviving)

        offers = (
            [("STOP", request) for request in stops]
            + [("EXIT", request) for request in exits]
            + [("THROTTLE", request) for request in throttles]
            + [("ENTRY", request) for request in entries]
        )
        merged: dict[str, tuple[str, OrderRequest]] = {}
        for kind, request in offers:
            held = merged.get(request.symbol)
            if held is None:
                merged[request.symbol] = (kind, request)
                continue
            self.suppressed_legs.append(
                {
                    "session": session.isoformat(),
                    "symbol": request.symbol,
                    "suppressed": kind,
                    "by": held[0],
                }
            )
            if held[0] == "STOP" and kind == "EXIT":
                self.stop_preempted_signal_exit += 1

        chosen = sorted(
            merged.values(), key=lambda pair: (ORDER_KIND_PRECEDENCE.index(pair[0]), pair[1].symbol)
        )
        symbols = [request.symbol for _, request in chosen]
        if len(symbols) != len(set(symbols)):
            raise InvariantViolation(
                f"the merged risk legs for {session.isoformat()} name a symbol twice: {symbols}"
            )
        return [request for _, request in chosen]

    @exact
    def _stop_legs(
        self, session: dt.date, marks: dict[str, Decimal]
    ) -> list[OrderRequest]:
        """RA2-3. ``close(t) <= (1 - 0.08) * (cost_basis / quantity)``, whole position, next open.

        The reference is the **all-in** per-share cost basis. ``Position`` carries no entry price; it
        carries ``cost_basis``, the total cash paid including commission and fees, because the engine
        debits ``-fill.cash_delta``. The reference therefore sits marginally above the traded price
        and the stop triggers marginally earlier than a raw-price stop would — the conservative
        direction, frozen explicitly so the implementation could not pick the flattering reading
        after seeing which performed better. ``G2A2-CONFLICT-14``.
        """
        legs: list[OrderRequest] = []
        threshold_fraction = ONE - self.risk.stop_fraction
        for symbol in sorted(marks):
            position = self.portfolio.positions.get(symbol)
            if position is None or position.quantity <= ZERO:
                continue
            reference = position.cost_basis / position.quantity
            threshold = threshold_fraction * reference
            close = marks[symbol]
            if close > threshold:
                continue
            legs.append(OrderRequest(symbol=symbol, side=SELL, tag="STOP"))
            self.stop_events.append(
                {
                    "order_id": make_order_id(session, symbol, SELL, "STOP"),
                    "decision_session": session.isoformat(),
                    "symbol": symbol,
                    "close": f"{close:f}",
                    "reference_price": f"{reference:f}",
                    "threshold": f"{threshold:f}",
                    "drop_at_trigger": f"{close / reference - ONE:f}",
                    "quantity": f"{position.quantity:f}",
                }
            )
        return legs

    @exact
    def _throttle_legs(
        self,
        session: dt.date,
        marks: dict[str, Decimal],
        surviving: dict[str, Decimal],
    ) -> list[OrderRequest]:
        """RA2-1 part b. Sell down the excess over ``0.50 · f · equity``, largest position first.

        Measured on the **projected** book — after the STOP and EXIT legs already merged for this
        session — because trimming a position that is about to be sold in full would be turnover
        bought for nothing.

        A trim whose notional at this close falls below the sealed ``min_order_notional`` is skipped
        rather than submitted, since ``_execute_sell`` would reject it as ``MIN_NOTIONAL`` anyway.
        The consequence is that the ceiling can be transiently exceeded by less than one minimum lot.
        That is counted and disclosed, not papered over. ``G2A2-CONFLICT-17``.
        """
        if not surviving:
            return []
        if not self._equity or self._equity[-1].session != session:
            raise InvariantViolation(
                f"the throttle read an equity point for "
                f"{self._equity[-1].session.isoformat() if self._equity else 'no session'} while "
                f"deciding {session.isoformat()}; the ceiling would be measured against the wrong "
                "equity"
            )
        equity = self._equity[-1].equity
        ceiling = self.risk.exposure_ceiling * self._combined_scalar * equity
        projected_gross = sum(surviving.values(), ZERO)
        if projected_gross <= ceiling:
            return []

        self.throttle_sessions += 1
        excess = projected_gross - ceiling
        self._throttle_excess_total += excess

        legs: list[OrderRequest] = []
        remaining_excess = excess
        for symbol in sorted(surviving, key=lambda s: (-surviving[s], s)):
            if remaining_excess <= ZERO:
                break
            value = surviving[symbol]
            trim_value = value if value < remaining_excess else remaining_excess
            mark = marks[symbol]
            if mark <= ZERO:
                raise DataIntegrityHalt(
                    f"{symbol} is marked at {mark} on {session.isoformat()}; a trim cannot be sized"
                )
            # Round the share count **up** so the trim actually clears the slice of excess it was
            # allocated, then cap at what is held. Rounding down would leave a residue above the
            # ceiling for a representation reason.
            quantity = (trim_value / mark).quantize(
                self.costs.share_quantum, rounding=ROUND_CEILING
            )
            held_quantity = self.portfolio.quantity_of(symbol)
            if quantity > held_quantity:
                quantity = held_quantity
            if quantity <= ZERO:
                continue
            notional = quantity * mark
            if notional < self.costs.min_order_notional:
                self.throttle_legs_below_min_notional += 1
                self._throttle_skipped_notional += notional
                continue
            legs.append(
                OrderRequest(symbol=symbol, side=SELL, quantity=quantity, tag="THROTTLE")
            )
            self.throttle_legs_scheduled += 1
            remaining_excess -= notional
        return legs

    # -- step 2 of the next session: fills --------------------------------------------------------

    @exact
    def _execute_buy(self, session: dt.date, order, reference: Decimal) -> None:
        """Attempt 1's four clamps with ``AGGREGATE_RA2`` inserted second, under the RA2 scalar.

        Structurally Attempt 1's method and different in exactly two declared ways:

        1. the requested budget is ``w(k) · f · equity`` rather than ``w(k) · equity``, where ``f`` is
           the combined scalar measured at the **decision** close. That is not a choice — the loop
           records equity and updates risk state at step 6, decides at step 7, and fills at step 2 of
           the following session, so the scalar in force at a fill is necessarily the previous
           close's. Using this session's would require measuring a close that has not happened;
        2. ``AGGREGATE_RA2`` clamps the budget to ``max(0, 0.50 · f · equity − position_value)`` and
           is evaluated before the inherited 0.95 ``AGGREGATE``, so the binding clamp reports under
           its own name instead of being masked by a looser one.

        Everything else — the shutdown block, the position-count check, open marks, the sizing
        solver, the minimum-notional and cash checks — is Attempt 1's, restated because the clamp
        tuple is built inline there and offers no seam. The relationship between the two tuples is
        asserted at load time in :func:`_validate_architecture`, so this method cannot quietly drop
        an inherited ceiling.
        """
        if self._shutdown_session is not None:
            self._reject(order, "RESEARCH_SHUTDOWN", "entries are blocked after a research shutdown")
            return

        symbol = order.symbol
        held = self.portfolio.open_symbols()
        if symbol not in held and len(held) >= self.costs.max_open_risky_positions:
            self._reject(order, "MAX_POSITIONS", f"already holding {len(held)} position(s)")
            return

        scalar = self._scalar_at_decision.get(order.decision_session)
        if scalar is None:
            raise InvariantViolation(
                f"{order.order_id}: no RA2 scalar was recorded at its decision close "
                f"{order.decision_session.isoformat()}; the risk state and the order book disagree "
                "about which sessions took decisions"
            )

        marks = {s: self._open_mark(s, session)[0] for s in held}
        values = {s: self.portfolio.quantity_of(s) * marks[s] for s in held}
        position_value = sum(values.values(), ZERO)
        own_value = values.get(symbol, ZERO)

        equity = self.portfolio.equity(marks)
        cash = self.portfolio.cash

        requested = order.budget if order.budget is not None else ZERO
        if self.budget_weight is not None:
            requested = self.budget_weight * scalar * equity
            self.budget_reevaluations += 1

        clamps = (
            ("REQUESTED_BUDGET", requested),
            ("AGGREGATE_RA2", self.risk.exposure_ceiling * scalar * equity - position_value),
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
        self._fill_scalar = scalar
        try:
            self._assert_ceilings_hold(session, symbol, reference, marks, equity)
        finally:
            self._fill_scalar = None

    # -- assertions ------------------------------------------------------------------------------

    def _assert_ceilings_hold(
        self,
        session: dt.date,
        symbol: str,
        reference: Decimal,
        marks: dict[str, Decimal],
        equity: Decimal,
    ) -> None:
        """Attempt 1's three assertions, plus RA2-1 re-derived from the settled book.

        The clamp arithmetic above says the ceiling holds. This says so from the positions actually
        recorded, sharing no line of code with the clamp, which is the only way an error in the clamp
        is caught by something other than the clamp.
        """
        super()._assert_ceilings_hold(session, symbol, reference, marks, equity)

        scalar = self._fill_scalar
        if scalar is None:
            raise InvariantViolation(
                "the RA2 ceiling assertion ran with no scalar in force; it cannot be checked and "
                "must not be skipped"
            )
        after = dict(marks)
        after[symbol] = reference
        total = ZERO
        for open_symbol in self.portfolio.open_symbols():
            mark = after.get(open_symbol)
            if mark is None:
                raise InvariantViolation(
                    f"{open_symbol} is held on {session.isoformat()} but was not marked at the open "
                    "while sizing this fill; the RA2 ceiling cannot be checked against a position "
                    "left out of the sum"
                )
            total += self.portfolio.quantity_of(open_symbol) * mark
        ceiling = self.risk.exposure_ceiling * scalar * equity
        if total > ceiling:
            raise InvariantViolation(
                f"AGGREGATE_RA2_CEILING: positions are worth {total} on {session.isoformat()} "
                f"against the scaled ceiling {ceiling} (= {self.risk.exposure_ceiling} * {scalar} * "
                f"{equity}). The AGGREGATE_RA2 clamp on this buy should have prevented it."
            )

    # -- evidence --------------------------------------------------------------------------------

    def risk_state_digest(self) -> str:
        """SHA-256 over the per-session risk state, in session order.

        Equal equity curves are weaker evidence than equal decisions, and equal decisions are weaker
        evidence than equal risk state: two runs could agree on every fill while disagreeing about a
        band transition that never reached an order. No run id, timestamp or path enters the payload.
        """
        return hashlib.sha256(self.risk_state_payload().encode("utf-8")).hexdigest()

    def risk_state_payload(self) -> str:
        return "".join(line + "\n" for line in self._risk_trace)

    def risk_summary(self) -> dict[str, object]:
        """What the risk architecture actually did, for a report that must show it."""
        stops_by_id = {event["order_id"]: event for event in self.stop_events}
        stop_fills = []
        for record in self._fills:
            event = stops_by_id.get(record.order_id)
            if event is None:
                continue
            reference = Decimal(str(event["reference_price"]))
            stop_fills.append(
                {
                    "decision_session": event["decision_session"],
                    "fill_session": record.session.isoformat(),
                    "symbol": record.fill.symbol,
                    "close_at_trigger": event["close"],
                    "reference_price": event["reference_price"],
                    "drop_at_trigger": event["drop_at_trigger"],
                    "fill_reference_price": f"{record.fill.reference_price:f}",
                    "drop_at_fill": f"{record.fill.reference_price / reference - ONE:f}",
                }
            )

        mean_vol_scalar = (
            f"{self._vol_scalar_total / Decimal(self._vol_scalar_points):f}"
            if self._vol_scalar_points
            else None
        )
        mean_combined_scalar = (
            f"{self._combined_scalar_total / Decimal(self._combined_scalar_points):f}"
            if self._combined_scalar_points
            else None
        )
        return {
            "architecture": self.risk.to_json(),
            "max_gross_fraction_observed": f"{self.max_gross_fraction_observed:f}",
            "max_gross_fraction_session": (
                None
                if self.max_gross_fraction_session is None
                else self.max_gross_fraction_session.isoformat()
            ),
            "volatility_scalar": {
                "minimum": f"{self.vol_scalar_min:f}",
                "mean": mean_vol_scalar,
                "sessions_measured": self._vol_scalar_points,
                "sessions_below_one": self.vol_scalar_sessions_below_one,
                "sessions_undefined": self.vol_scalar_undefined_sessions,
            },
            "combined_scalar_minimum": f"{self.combined_scalar_min:f}",
            "combined_scalar": {
                "minimum": f"{self.combined_scalar_min:f}",
                "mean": mean_combined_scalar,
                "sessions_measured": self._combined_scalar_points,
                "sessions_below_one": self.combined_scalar_sessions_below_one,
            },
            "ladder": {
                "descents": self.ladder_descents,
                "ascents": self.ladder_ascents,
                "deepest_band": self.deepest_band,
                "final_band": self._band,
                "sessions_in_band": {str(k): v for k, v in sorted(self.sessions_in_band.items())},
                "recoveries_blocked_by_lockout": self.recoveries_blocked,
            },
            "lockout": {
                "sessions": self.risk.lockout_sessions,
                "arms": self.lockout_arms,
                "recoveries_blocked": self.recoveries_blocked,
            },
            "stops": {
                "triggered": len(self.stop_events),
                "filled": len(stop_fills),
                "preempted_signal_exit": self.stop_preempted_signal_exit,
                "fills": stop_fills,
            },
            "throttle": {
                "sessions_breaching_ceiling": self.throttle_sessions,
                "legs_scheduled": self.throttle_legs_scheduled,
                "legs_below_min_notional": self.throttle_legs_below_min_notional,
                "excess_value_total": f"{self._throttle_excess_total:f}",
                "skipped_notional_total": f"{self._throttle_skipped_notional:f}",
            },
            "suppressed_legs": len(self.suppressed_legs),
            "risk_state_digest": self.risk_state_digest(),
            "risk_state_sessions": len(self._risk_trace),
        }

    def clamp_summary(self) -> dict[str, object]:
        """Attempt 1's clamp evidence, widened by the one clamp Attempt 2 adds."""
        summary = super().clamp_summary()
        summary["clamp_names"] = list(CLAMP_NAMES_RA2)
        summary["aggregate_ra2_ceiling"] = f"{self.risk.exposure_ceiling:f}"
        summary["binding_clamp_counts"] = dict(self.binding_clamp_counts)
        return summary
