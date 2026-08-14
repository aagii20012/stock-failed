"""The three sealed Attempt 2 candidates. Each supplies a signal; RA1 supplies everything else.

Exactly three candidates are authorised — ``SE100-S3A2-C1-PULLBACK-RA1``,
``SE100-S3A2-C2-MEANREV-RA1``, ``SE100-S3A2-C3-DEFENSIVE-RA1`` — and no fourth may be added, no
family may be substituted, and no exploratory variant may be introduced. :func:`build_candidate`
raises on any experiment id it does not recognise, so an unregistered candidate cannot be run by
accident.

Each ``target`` docstring quotes its sealed ``signal_target_rule`` verbatim before implementing it.
Read the docstring, then the code; if the two ever disagree, the seal is the specification and the
code is the defect.

Every class here derives from :class:`stockedge100.strategies.attempt2_risk.Ra1Candidate`, which is
the only place sizing, exits, lockouts and the order path exist. Attempt 1's
:mod:`stockedge100.strategies.families` classes are deliberately **not** subclassed: they inherit
:meth:`Candidate.entry_order`, whose sealed Attempt 1 sizing rule requests 95% of equity, and that is
precisely the rule ``shared_rules.replaced.sizing_rule`` replaces. Sharing a base class with the rule
Attempt 2 replaces would be the most plausible way for Attempt 1's exposure to reappear unnoticed.

The indicators, by contrast, *are* shared: :func:`~stockedge100.strategies.indicators.sma` and
:func:`~stockedge100.strategies.indicators.wilder_rsi` are imported from the Attempt 1 module because
the sealed ``indicator_definitions.adopted_unchanged`` list names SMA and RSI, and a second copy of a
sealed indicator is eventually the copy that is wrong.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from stockedge100.backtest.engine import DecisionContext
from stockedge100.backtest.errors import ConfigViolation
from stockedge100.backtest.market import MarketView
from stockedge100.strategies.attempt2_config import dec
from stockedge100.strategies.attempt2_indicators import VOL20_BARS
from stockedge100.strategies.attempt2_risk import Ra1Candidate
from stockedge100.strategies.indicators import sma, wilder_rsi

C1 = "SE100-S3A2-C1-PULLBACK-RA1"
C2 = "SE100-S3A2-C2-MEANREV-RA1"
C3 = "SE100-S3A2-C3-DEFENSIVE-RA1"

#: The complete authorised set, in sealed ``experiments`` order.
ATTEMPT_2_EXPERIMENT_IDS: tuple[str, ...] = (C1, C2, C3)


class PullbackRa1(Ra1Candidate):
    """C1 — ``SE100-S3A2-C1-PULLBACK-RA1``.

    Sealed hypothesis, in part: "Buying SPY only on short-term weakness inside a long-term uptrend,
    at half the exposure a fixed-budget rule would take ... earns a positive after-cost total return
    over the development window without account equity ever falling 15% below its running high-water
    mark."

    The signal form is shared with the rejected Attempt 1 candidate
    ``SE100-S3-F2-PULLBACK-SMA200-SMA10`` and both of its parameters keep the values F2 declared
    before any result. The seal is explicit about what that means:
    ``signal_form_held_fixed_deliberately`` — "if the return source is held fixed, any difference in
    risk behaviour is attributable to RA1 rather than to a new signal. It also means C1 is
    emphatically NOT an independent test of the pullback hypothesis."
    """

    family = "pullback"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.symbol = self.universe[0]
        self.sma_long = int(self.parameters["sma_long"])
        self.sma_short = int(self.parameters["sma_short"])

    def target(self, view: MarketView, context: DecisionContext) -> str | None:
        """Sealed ``signal_target_rule``: "signal_target = SPY if close(t) > SMA(sma_long)(t) AND
        close(t) < SMA(sma_short)(t), else cash."

        One rule serves entry and exit alike, which is what the sealed ``exit_rule`` means by
        "EXIT_SIGNAL if signal_target is cash, that is the close has recovered above SMA(sma_short)
        or the long-term regime has failed."

        Either average being uncomputable sends the session to cash under the adopted
        ``insufficient_history_rule``: "A missing indicator never produces a hold, a guess, or a
        carried-forward value."
        """

        need = max(self.sma_long, self.sma_short)
        bars = self.bars_at(view, self.symbol, context.session, need)
        long_average = sma(bars, self.sma_long)
        short_average = sma(bars, self.sma_short)
        if long_average is None or short_average is None:
            return None
        close = bars[-1].close
        if close > long_average and close < short_average:
            return self.symbol
        return None


class MeanReversionRa1(Ra1Candidate):
    """C2 — ``SE100-S3A2-C2-MEANREV-RA1``.

    Shares its signal form with Attempt 1's ``SE100-S3-F4-MEANREV-RSI2`` and keeps that candidate's
    declared parameters. The sealed ``neighbour_note`` explains why this candidate's neighbour set
    probes ``loss_control`` where C1's and C3's probe ``f_base``: "this is the candidate whose sealed
    Attempt 1 counterpart explicitly declared it had no stop, so the loss control is the single most
    consequential addition here."
    """

    family = "mean reversion"

    def __init__(self, *, warmup_changes: int, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.symbol = self.universe[0]
        self.rsi_period = int(self.parameters["rsi_period"])
        self.rsi_entry_below = dec(self.parameters["rsi_entry_below"])
        self.exit_sma = int(self.parameters["exit_sma"])
        self.warmup_changes = warmup_changes

    def target(self, view: MarketView, context: DecisionContext) -> str | None:
        """Sealed ``signal_target_rule``: "If flat: signal_target = SPY if RSI(rsi_period)(t) <
        rsi_entry_below, else cash. If holding SPY: signal_target = cash if close(t) >
        SMA(exit_sma)(t), else SPY. The account's own position, supplied by the engine's
        DecisionContext, is the only thing that selects between the two forms, and it is not future
        information."

        The final clause is the reason this asymmetry is admissible: ``context.open_symbols`` is the
        account's own state at the decision close, not a market observation, so branching on it reads
        nothing the candidate is not permitted to see.

        ``rsi_entry_below`` is compared as an exact ``Decimal`` against Wilder's RSI. The sealed
        arithmetic rule is "No comparison in floating point and no rounding before a threshold
        comparison", and the strict ``<`` is the sealed predicate — an RSI exactly equal to the
        threshold is not an entry.
        """

        need = max(self.warmup_changes + 1, self.exit_sma)
        bars = self.bars_at(view, self.symbol, context.session, need)
        if not bars:
            return None
        if context.open_symbols:
            average = sma(bars, self.exit_sma)
            if average is None:
                return None
            return None if bars[-1].close > average else self.symbol
        strength = wilder_rsi(bars, self.rsi_period, self.warmup_changes)
        if strength is None:
            return None
        return self.symbol if strength < self.rsi_entry_below else None


class DefensiveRegimeRa1(Ra1Candidate):
    """C3 — ``SE100-S3A2-C3-DEFENSIVE-RA1``, the only multi-instrument Attempt 2 candidate.

    ``universe_rationale``: "Multi-instrument, so S3-C6 applies. This is the only Attempt 2 candidate
    for which it does, which is why a multi-instrument candidate was kept in a three-candidate set."

    The ``defensive_symbol`` neighbour sets the leg to ``null``, which makes the defensive
    destination cash. Its run window is unchanged, because the adopted ``run_start_rule`` reads the
    DECLARED universe: "a neighbour that drops a symbol still runs over the same window as its
    primary."
    """

    family = "defensive regime logic"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.sma_long = int(self.parameters["sma_long"])
        self.risk_symbol = str(self.parameters["risk_symbol"])
        defensive = self.parameters.get("defensive_symbol")
        self.defensive_symbol = None if defensive is None else str(defensive)

    def target(self, view: MarketView, context: DecisionContext) -> str | None:
        """Sealed ``signal_target_rule``: "signal_target = risk_symbol if close(risk_symbol, t) >
        SMA(sma_long)(risk_symbol, t); else the defensive_symbol if it is non-null and has a visible
        bar at t; else cash. The regime is read from the risk symbol only: the defensive leg is a
        destination, never a signal."

        So the defensive leg is never consulted for the regime, and a defensive leg with no bar at
        ``t`` — every session before SHY's inception, and any session it is absent — resolves to
        cash rather than to a stale price or to the risk leg.
        """

        bars = self.bars_at(view, self.risk_symbol, context.session, self.sma_long)
        average = sma(bars, self.sma_long)
        if average is None:
            return None
        if bars[-1].close > average:
            return self.risk_symbol
        if self.defensive_symbol is None:
            return None
        if not view.has_data(self.defensive_symbol, context.session):
            return None
        return self.defensive_symbol


def traded_symbols(
    experiment_id: str, universe: tuple[str, ...], parameters: dict[str, Any]
) -> tuple[str, ...]:
    """The symbols a *variant* can actually trade, which is not always its declared universe.

    Only C3's ``defensive_symbol`` neighbour differs: with the leg set to ``null`` the variant can
    never hold SHY, so SHY is not loaded for it. The declared universe still governs the run start
    and still governs S3-C6's applicability, both of which read
    :attr:`CandidatePlan.declared_universe` rather than this.

    Narrowing the loaded set is not cosmetic. The engine raises ``InvariantViolation`` on an order in
    an unloaded symbol, so a variant that cannot hold a leg by rule also cannot hold it by accident.
    """

    if experiment_id == C3 and parameters.get("defensive_symbol") is None:
        return (str(parameters["risk_symbol"]),)
    return tuple(universe)


def build_candidate(
    *,
    experiment_id: str,
    variant_id: str,
    universe: tuple[str, ...],
    parameters: dict[str, Any],
    costs: Any,
    rsi_warmup_changes: int,
) -> Ra1Candidate:
    """Construct the one registered implementation of ``experiment_id``.

    ``rsi_warmup_changes`` is read by the caller from the digest-verified Attempt 1 protocol, whose
    RSI definition Attempt 2 adopts unchanged, and is passed only to C2. Restating the number here
    would create a second copy of a sealed value.

    An unknown ``experiment_id`` raises. §4 of the operating prompt authorises exactly three
    candidates and no exploratory, debug, alternative, or post-result variant, so there is no
    fallback branch for this function to take.
    """

    common: dict[str, Any] = {
        "experiment_id": experiment_id,
        "variant_id": variant_id,
        "universe": universe,
        "parameters": parameters,
        "costs": costs,
    }
    if experiment_id == C1:
        return PullbackRa1(**common)
    if experiment_id == C2:
        return MeanReversionRa1(warmup_changes=rsi_warmup_changes, **common)
    if experiment_id == C3:
        return DefensiveRegimeRa1(**common)
    raise ConfigViolation(
        f"no implementation registered for Attempt 2 experiment {experiment_id!r}; the sealed "
        f"protocol authorises exactly {list(ATTEMPT_2_EXPERIMENT_IDS)}"
    )


#: Every parameter key that contributes a lookback, and how many visible bars it needs.
#:
#: ``warmup_derivation`` in each sealed candidate block states the arithmetic this table reproduces.
#: VOL20's contribution is the sealed ``lookback_contribution_to_warmup`` of 21 bars and is constant,
#: so it is added by :func:`largest_lookback` rather than keyed to a parameter.
LOOKBACK_KEYS: tuple[str, ...] = ("sma_long", "sma_short", "exit_sma")


def largest_lookback(parameters: dict[str, Any], rsi_warmup_changes: int) -> int:
    """The largest number of visible bars any rule of this variant needs.

    Used only to cross-check each sealed ``warmup_sessions`` against its own
    ``warmup_derivation``; the run start itself is computed from the sealed ``warmup_sessions``,
    never from this. A candidate whose declared warm-up were *shorter* than its rules require would
    be a specification defect, and the check exists to surface it rather than to repair it.
    """

    needs = [VOL20_BARS]
    for key in LOOKBACK_KEYS:
        if key in parameters:
            needs.append(int(parameters[key]))
    if "rsi_period" in parameters:
        needs.append(rsi_warmup_changes + 1)
    return max(needs)


def signal_parameter_values(parameters: dict[str, Any]) -> dict[str, Any]:
    """The signal half of a variant's parameters, for the traceability evidence.

    Split out so the evidence can show, per variant, which keys belong to the sealed signal and
    which belong to RA1 — the distinction the whole Attempt 2 design rests on.
    """

    signal_keys = ("sma_long", "sma_short", "rsi_period", "rsi_entry_below", "exit_sma",
                   "risk_symbol", "defensive_symbol")
    out: dict[str, Any] = {}
    for key in signal_keys:
        if key in parameters:
            value = parameters[key]
            out[key] = f"{value:f}" if isinstance(value, Decimal) else value
    return out
