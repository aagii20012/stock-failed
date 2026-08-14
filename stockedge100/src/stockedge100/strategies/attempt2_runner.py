"""Turn the sealed Attempt 2 protocol into its eighteen declared runs, and measure each one.

The sealed ``iteration_budget`` splits the eighteen explicitly, and the split matters because the two
halves have different standing at the gate:

* ``total_declared_gating_variants: 15`` — three candidates, each a primary plus four registered
  robustness neighbours. These are the runs Gate 3 reads.
* ``total_declared_non_gating_stress_runs: 3`` — one stressed-cost run of each candidate's *primary*
  parameterisation, required by ``cost_stress_treatment``: "Each candidate's PRIMARY parameterisation
  is additionally run at 2x the complete base trading-friction assumption, over the same window, with
  the research shutdown enforced. Three such runs in total." Its ``gating`` field is ``false`` and its
  ``prohibition`` is explicit: "The STRESS_FRAGILE flag may not be used at Gate 3 to admit a
  candidate that failed a hard condition, nor to reject a candidate that satisfied all of them."

Everything Attempt 1's :mod:`stockedge100.strategies.runner` does that is not coupled to Attempt 1's
candidate set is imported from it rather than copied — :class:`~stockedge100.strategies.runner.VariantSpec`,
:class:`~stockedge100.strategies.runner.CandidatePlan`, :func:`~stockedge100.strategies.runner.run_start_for`,
:func:`~stockedge100.strategies.runner.measure` and the trade-level helpers. What is re-authored here
is exactly the set of functions that hard-bind an Attempt 1 symbol table, an Attempt 1 parameter-key
set, an Attempt 1 ``indicator_definitions`` shape, or ``Stage3Config``. A second copy of ``measure``
would be a second definition of ``max_drawdown`` and ``profit_factor``, which are gate inputs; those
are Gate-2 validated and are not re-derived here.

Three setup properties carry over from Attempt 1 unchanged, because the sealed ``shared_rules`` adopt
the rules that produce them unchanged:

**The engine is always given the whole development window, never a narrowed one.**
``MarketView.history`` filters visible bars on ``self._window.contains``, so a window starting at the
candidate's run start would delete the warm-up history the run start exists to guarantee. The run
start is passed as the engine's ``start`` argument, which moves the first *decision* without moving
the visibility bound.

**Warm-up is the largest lookback across the primary and every neighbour**, computed once per
candidate from its *declared* universe. All five gating runs and the stressed run therefore share one
window, which is what makes S3-C7 a comparison of rules rather than of periods. C3's sealed
``warmup_derivation`` states the consequence for its own neighbour: "The declared universe governs
the run start for every variant, so the defensive_symbol null neighbour runs over the same window as
the primary rather than over the longer window a SPY-only universe would allow."

**Each run loads exactly the symbols its own variant may trade.** The engine raises
``InvariantViolation`` for an order in a symbol it was not given and runs a staleness check over every
series it *was* given, so a wider load is both unnecessary and a way for an untraded instrument to
halt a run.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Sequence

from stockedge100.backtest.costs import BASE, STRESSED, CostModel
from stockedge100.backtest.dataset import PriceSeries, load_dataset
from stockedge100.backtest.engine import BacktestEngine, BacktestResult
from stockedge100.backtest.errors import ConfigViolation, InvariantViolation
from stockedge100.backtest.metrics import max_drawdown
from stockedge100.backtest.window import ResearchWindow
from stockedge100.strategies.attempt2_candidates import build_candidate, traded_symbols
from stockedge100.strategies.attempt2_config import Attempt2Config
from stockedge100.strategies.attempt2_indicators import VOL20_BARS
from stockedge100.strategies.attempt2_risk import Ra1Candidate
from stockedge100.strategies.runner import (
    NEIGHBOUR,
    PRIMARY,
    CandidatePlan,
    VariantSpec,
    measure,
    run_start_for,
)

#: Appended to a primary's variant id to label its non-gating stressed-cost run. The sealed protocol
#: registers no variant id for a stress run, so the label must be one no declared variant can carry:
#: ``variant_specs`` only ever emits ``#PRIMARY`` and ``#N1``..``#N4``.
STRESS_SUFFIX = "#STRESS"

#: Appended for the determinism re-execution. Also outside the declared variant-id space.
DETERMINISM_SUFFIX = "#RERUN"

#: The sealed flag name from ``cost_stress_treatment.gating_note``.
STRESS_FRAGILE = "STRESS_FRAGILE"


# -- planning ------------------------------------------------------------------------------------


def variant_specs(experiment: dict[str, Any]) -> tuple[VariantSpec, ...]:
    """The primary plus every sealed robustness neighbour, in sealed order. Five, never more.

    ``max_variants_per_candidate`` is 5 for all three candidates and this function enumerates the
    sealed lists rather than a range, so the count is a property of the protocol file. The neighbour
    ids are positional (``#N1``..``#N4``) and follow the sealed order of ``robustness_neighbours``,
    which is what lets a reader match a reported id back to the override that produced it.

    A neighbour may override ``universe``; none of Attempt 2's twelve does, but the mechanism is kept
    because C3's ``defensive_symbol: null`` neighbour changes which symbols are *traded* without
    changing the declared universe, and :func:`stockedge100.strategies.attempt2_candidates.traded_symbols`
    is what resolves that difference.
    """

    experiment_id = experiment["experiment_id"]
    declared_universe = tuple(experiment["universe"])
    primary = dict(experiment["primary_parameters"])
    specs = [
        VariantSpec(
            experiment_id=experiment_id,
            variant_id=f"{experiment_id}#PRIMARY",
            role=PRIMARY,
            index=0,
            universe=declared_universe,
            parameters=primary,
            symbols=traded_symbols(experiment_id, declared_universe, primary),
        )
    ]
    for position, neighbour in enumerate(experiment["robustness_neighbours"], start=1):
        overrides = dict(neighbour)
        universe = tuple(overrides.pop("universe", declared_universe))
        parameters = {**primary, **overrides}
        specs.append(
            VariantSpec(
                experiment_id=experiment_id,
                variant_id=f"{experiment_id}#N{position}",
                role=NEIGHBOUR,
                index=position,
                universe=universe,
                parameters=parameters,
                symbols=traded_symbols(experiment_id, universe, parameters),
            )
        )
    declared_max = int(experiment["max_variants"])
    if len(specs) != declared_max:
        raise ConfigViolation(
            f"{experiment_id}: enumerated {len(specs)} variants against a sealed max_variants of "
            f"{declared_max}; the protocol permits no extra variant and no omitted one"
        )
    return tuple(specs)


#: The parameter keys Attempt 2 uses that denote a lookback in visible bars. Deliberately *not*
#: Attempt 1's set: ``entry_lookback``, ``exit_lookback`` and ``momentum_lookback`` belong to the
#: breakout and rotation families, which ``families_excluded`` keeps out of this attempt. Carrying
#: keys no Attempt 2 candidate declares would mean a silent no-op if one were ever mistyped.
LOOKBACK_KEYS: tuple[str, ...] = ("sma_long", "sma_short", "exit_sma")


def largest_lookback(specs: Sequence[VariantSpec], rsi_warmup_changes: int) -> int:
    """Sealed ``warmup_rule``: the largest lookback used by the primary *or by any neighbour*,
    expressed as the number of visible bars the indicator consumes.

    Three conversions are fixed by the sealed ``warmup_derivation`` of the three candidates and none
    of them is cosmetic:

    * ``VOL20 requires 21`` — RA1-2 applies to every candidate, so 21 is a floor for all three. It
      binds none of them, because the smallest sealed warm-up is 101, but it is included because the
      seal includes it in every derivation and an implementation that omitted it would agree with the
      seal by luck rather than by construction.
    * The RSI family's binding lookback is the sealed ``warmup_changes``, not ``rsi_period``:
      Wilder's average is an infinite-memory recursion, so the seeding distance is the history the
      value actually depends on, and ``warmup_changes`` changes need ``warmup_changes + 1`` closes.
      That is why C2's sealed warm-up is 101 for an ``rsi_period`` of 2.
    * ``warmup_changes`` is read from the digest-verified Attempt 1 protocol, where the sealed
      Attempt 2 ``indicator_definitions`` place RSI under ``adopted_unchanged`` rather than restating
      it. Reading it from a literal here would let the two drift.

    Recomputing this is a check on the seal, not a substitute for it: :func:`plan_candidate` runs the
    declared ``warmup_sessions`` and this number against each other and refuses to plan a candidate
    where they disagree.
    """

    largest = VOL20_BARS
    for spec in specs:
        for key in LOOKBACK_KEYS:
            value = spec.parameters.get(key)
            if isinstance(value, int):
                largest = max(largest, value)
        if "rsi_period" in spec.parameters:
            largest = max(largest, int(rsi_warmup_changes) + 1)
    return largest


def plan_candidate(
    experiment: dict[str, Any],
    window: ResearchWindow,
    series: dict[str, PriceSeries],
    rsi_warmup_changes: int,
) -> CandidatePlan:
    """One candidate's five gating variants and the single window they and its stress run share."""

    specs = variant_specs(experiment)
    declared_universe = tuple(experiment["universe"])
    warmup = int(experiment["warmup_sessions"])
    effective = largest_lookback(specs, rsi_warmup_changes)
    if effective != warmup:
        raise ConfigViolation(
            f"{experiment['experiment_id']}: sealed warmup_sessions={warmup} but the largest "
            f"lookback across the primary and its neighbours consumes {effective} visible bars. "
            "The seal is the specification; report the discrepancy rather than adjusting either."
        )
    run_start, binding = run_start_for(declared_universe, warmup, window, series)
    all_symbols = sorted({symbol for spec in specs for symbol in spec.symbols})
    return CandidatePlan(
        experiment_id=experiment["experiment_id"],
        family=experiment["family"],
        declared_universe=declared_universe,
        warmup_sessions=warmup,
        effective_warmup=effective,
        run_start=run_start,
        run_end=window.end,
        binding_symbol=binding,
        variants=specs,
        all_symbols=tuple(all_symbols),
    )


def required_symbols(config: Attempt2Config) -> tuple[str, ...]:
    """Every symbol any declared Attempt 2 variant may trade, plus every declared universe member.

    The declared universe is included even where no variant trades it, because
    :func:`~stockedge100.strategies.runner.run_start_for` reads the *declared* universe to fix the run
    start — that is the sealed ``run_start_rule``, and C3's ``defensive_symbol: null`` neighbour is
    the case it exists for.
    """

    symbols: set[str] = set()
    for experiment in config.experiments:
        for spec in variant_specs(experiment):
            symbols.update(spec.symbols)
        symbols.update(experiment["universe"])
    return tuple(sorted(symbols))


def load_required_dataset(config: Attempt2Config) -> dict[str, PriceSeries]:
    """Load only what the sealed protocol names.

    ``excluded_symbols`` calls AAPL out by name and ``partitions.prohibited`` repeats it: "any symbol
    outside the frozen universe, including AAPL". A price file for it exists because Stage 1 measured
    the split convention against two AAPL split events. Nothing here can reach it, because nothing
    here names it — and the overlap check makes a seal that both required and excluded a symbol a
    refusal rather than a silent preference for one clause over the other.
    """

    excluded = set(config.excluded_symbols)
    wanted = list(required_symbols(config))
    overlap = sorted(set(wanted) & excluded)
    if overlap:
        raise ConfigViolation(f"sealed protocol both requires and excludes {overlap}")
    return load_dataset(wanted)


# -- running -------------------------------------------------------------------------------------


@dataclass(frozen=True)
class VariantRun:
    """One executed run, paired with the candidate object that produced it.

    The candidate is retained because the five ``NO_ENTRY_*`` counters and the RA1-5 rung tally live
    on it rather than in :class:`~stockedge100.backtest.engine.BacktestResult`: a blocked entry emits
    no order, so there is no engine artefact to read them from. The object is never reused for a
    second run — :func:`run_variant` builds a fresh one every time.
    """

    spec: VariantSpec
    scenario: str
    gating: bool
    label: str
    result: BacktestResult
    candidate: Ra1Candidate


def run_variant(
    spec: VariantSpec,
    plan: CandidatePlan,
    series: dict[str, PriceSeries],
    costs: CostModel,
    window: ResearchWindow,
    rsi_warmup_changes: int,
    *,
    gating: bool = True,
    label_suffix: str = "",
) -> VariantRun:
    """One declared run. A fresh candidate object every time.

    :class:`~stockedge100.strategies.attempt2_risk.Ra1Candidate` carries per-run mutable state — the
    high-water mark, ``sessions_held``, the lockout map, every diagnostic counter — so a reused object
    would both corrupt the second run and make the determinism check vacuous.

    ``enforce_research_shutdown=True`` is not a parameter. The sealed
    ``shutdown_behaviour.enforced_for_every_run`` is explicit: "primary runs, all four neighbour runs
    per candidate, and the three non-gating stressed-cost runs. It is never disabled for a candidate."
    The one account it is disabled for is the labelled SPY buy-and-hold benchmark reference, which
    :mod:`stockedge100.strategies.reference` handles and which is reported both ways.
    """

    candidate = build_candidate(
        experiment_id=spec.experiment_id,
        variant_id=spec.variant_id,
        universe=spec.universe,
        parameters=spec.parameters,
        costs=costs,
        rsi_warmup_changes=rsi_warmup_changes,
    )
    subset = {symbol: series[symbol] for symbol in spec.symbols}
    label = spec.variant_id + label_suffix
    engine = BacktestEngine(
        subset,
        costs,
        window,
        candidate,
        start=plan.run_start,
        end=plan.run_end,
        label=label,
        enforce_research_shutdown=True,
    )
    result = engine.run()
    if result.start != plan.run_start or result.end != plan.run_end:
        raise ConfigViolation(
            f"{label}: ran {result.start}..{result.end} against the planned "
            f"{plan.run_start}..{plan.run_end}. The sealed partial_or_failed_run_rule makes a run "
            "that did not reach the development window end NOT_RUN, never a patched result."
        )
    return VariantRun(
        spec=spec,
        scenario=costs.scenario,
        gating=gating,
        label=label,
        result=result,
        candidate=candidate,
    )


# -- measurement ---------------------------------------------------------------------------------


def shutdown_exits(result: BacktestResult) -> int:
    """How many forced ``EXIT_SHUTDOWN`` liquidations the engine scheduled — 0 or 1 here.

    The sealed ``secondary_metrics`` list EXIT_SHUTDOWN alongside the three candidate-attributed exit
    reasons, but no candidate can emit it: on the session the shutdown first triggers the engine
    schedules ``SELL`` for every open symbol with ``forced=True`` and ``continue``s without calling
    ``decide`` at all. So the count is read from the engine's own behaviour.

    The engine schedules that liquidation only when the trigger session is not the last session of the
    run — its loop ``continue``s on the final session before reaching the risk branch, because there
    is no following open to fill at. A shutdown detected on the final session therefore liquidates
    nothing, and reporting an exit for it would be reporting an exit that did not happen. With
    ``max_open_risky_positions`` of 1 the answer is otherwise the position count at the breaching
    close: 1 if a position was held, 0 if the account was already flat.
    """

    if result.shutdown_session is None:
        return 0
    if not result.equity_curve:
        raise InvariantViolation(f"{result.label}: a shutdown session with no equity curve")
    if result.shutdown_session == result.equity_curve[-1].session:
        return 0
    for point in result.equity_curve:
        if point.session == result.shutdown_session:
            return point.position_count
    raise InvariantViolation(
        f"{result.label}: shutdown session {result.shutdown_session.isoformat()} is not on the "
        "equity curve, so the number of forced liquidations cannot be established"
    )


def deepest_drawdown_4dp(result: BacktestResult) -> str:
    """Sealed ``secondary_metrics``: "deepest drawdown reached, reported to four decimal places, so
    that a near-miss is visible as a near-miss".

    Quantisation happens here and only here, in a reported string. The gate reads the unrounded value
    from :func:`~stockedge100.strategies.runner.measure`, because the sealed arithmetic rule is "no
    rounding before a threshold comparison" and S3-C2's comparison is against 0.15.
    """

    worst = max_drawdown([point.equity for point in result.equity_curve])
    return f"{worst.quantize(Decimal('0.0001')):f}"


def measure_variant(
    run: VariantRun, costs: CostModel, cost_model_raw: dict[str, Any]
) -> dict[str, Any]:
    """Everything the gate reads, plus every RA1 diagnostic the seal lists as never gating.

    :func:`~stockedge100.strategies.runner.measure` is Attempt 1's, imported unchanged: it computes
    ``total_return``, ``max_drawdown``, ``profit_factor`` and ``closed_trades``, which are gate inputs
    validated at Gate 2. Re-implementing them for Attempt 2 would put a second definition of a gate
    input on disk.
    """

    return {
        "variant_id": run.spec.variant_id,
        "role": run.spec.role,
        "scenario": run.scenario,
        "gating": run.gating,
        "parameters": run.spec.to_json()["parameters"],
        "symbols_loaded": list(run.spec.symbols),
        "ra1_parameters_in_force": run.candidate.ra1_to_json(),
        **measure(run.result, costs, cost_model_raw),
        "deepest_drawdown_4dp": deepest_drawdown_4dp(run.result),
        "ra1_diagnostics": {
            **run.candidate.ra1_diagnostics(),
            "exits_by_reason_shutdown": shutdown_exits(run.result),
        },
    }


def stress_evidence(
    base: dict[str, Any], stress: dict[str, Any], stress_multiplier: Decimal
) -> dict[str, Any]:
    """The non-gating stressed-cost record for one candidate, and its ``STRESS_FRAGILE`` flag.

    ``cost_stress_treatment`` in full on the point that matters: ``gating`` is ``false``; "Gate 3's
    seven hard conditions contain no stressed-cost condition. The stressed run is reported and
    flagged, never gating. A candidate whose stressed run turns its total return non-positive is
    recorded with a STRESS_FRAGILE flag in the evidence and is neither rejected nor admitted on that
    basis at Gate 3."

    The flag is raised on the literal condition in that sentence — the stressed total return is not
    strictly positive. The sealed word "turns" also supports a narrower reading in which the flag
    requires the base return to have been positive first, so ``base_total_return_positive`` is
    recorded beside it and a reader can apply either reading to the same numbers. The choice is
    immaterial to every verdict, because ``prohibition`` forbids the flag from moving admission in
    either direction, and a candidate whose *base* return is non-positive has already failed S3-C1.
    """

    base_return = Decimal(base["total_return"])
    stress_return = Decimal(stress["total_return"])
    flags: list[str] = []
    if stress_return <= 0:
        flags.append(STRESS_FRAGILE)
    return {
        "gating": False,
        "constitution_ref": "SE100-GOV-0001 section 7",
        "scenario": stress["scenario"],
        "stress_multiplier": f"{stress_multiplier:f}",
        "base_total_return": base["total_return"],
        "stressed_total_return": stress["total_return"],
        "base_total_return_positive": base_return > 0,
        "stressed_total_return_positive": stress_return > 0,
        "base_closed_trades": base["closed_trades"],
        "stressed_closed_trades": stress["closed_trades"],
        "base_max_drawdown": base["max_drawdown"],
        "stressed_max_drawdown": stress["max_drawdown"],
        "base_shutdown_session": base["shutdown_session"],
        "stressed_shutdown_session": stress["shutdown_session"],
        "flags": flags,
        "flag_semantics": (
            "STRESS_FRAGILE is raised when the stressed run's total return is not strictly positive. "
            "It is recorded, never gating: the sealed prohibition is that it 'may not be used at "
            "Gate 3 to admit a candidate that failed a hard condition, nor to reject a candidate "
            "that satisfied all of them'."
        ),
        "measure": stress,
    }


#: Both scenario names, re-exported so a caller need not import from two modules to build the pair.
SCENARIOS: tuple[str, str] = (BASE, STRESSED)
