"""Generation 2, Stage 3: the thirty-six declared runs, and the return-blind selection over them.

The seal declares eighteen variants and two runs each — ``#BASE`` and ``#STRESS`` — and states that
"Both runs of all eighteen variants are declared here and all 36 are executed. None is conditional
on the outcome of another." So :func:`run_grid` executes the full cross product unconditionally.
There is no early exit, no skip on a shutdown, and no ordering that lets one run's outcome change
whether a later one happens.

**The selection is return-blind by construction, not by discipline.** The sealed rule says: "No step
of this rule reads a return, a Sharpe ratio, a profit factor, an equity level, or any other
performance figure." Honouring that with a careful ``select_representative`` that merely *chooses*
not to look would leave the guarantee resting on a reading of the code. Instead the choice is made
by a function that cannot look: :func:`select_representative` takes a sequence of
:class:`SelectionInput`, a frozen record carrying a variant id, a research-shutdown count, and a
fill count, and nothing else. No ``BacktestResult``, no measurement dict, no equity curve is in
scope at the point the representative is decided. The projection happens once, in
:func:`selection_inputs`, which reads exactly three attributes off each run.

Returns are still measured for every one of the thirty-six runs and carried on the :class:`GridRun`
record, because the seal requires them reported. They travel to the report; they never travel to the
chooser.

Gate evaluation is narrower than the grid. The seal's ``gate_evaluation_scope`` names "the selected
representative's #BASE run only", with the stress run "reported, not gating"; :func:`gate_inputs`
assembles exactly that, plus the structural neighbours S3-C7 requires, and refuses anything else.

Nothing in Generation 1 is modified. :func:`~stockedge100.strategies.runner.measure` and
:func:`~stockedge100.strategies.runner.trade_ledger` are imported and reused as they stand.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, fields
from decimal import Decimal
from typing import Any, Callable, Sequence

from stockedge100.backtest.costs import BASE, SCENARIOS, CostModel
from stockedge100.backtest.engine import BacktestResult
from stockedge100.backtest.errors import ConfigViolation, InvariantViolation
from stockedge100.backtest.g2_costs import derive_mapping, rotation_cost_model
from stockedge100.backtest.g2_engine import RotationEngine
from stockedge100.strategies import g2_window_guard as guard
from stockedge100.strategies.g2_gate import load_criteria, neighbours_of
from stockedge100.strategies.g2_rotation import (
    STRATEGY_ID,
    RotationCandidate,
    RotationVariant,
    eligible_universe,
    load_protocol,
    rotation_variants,
    variant_by_id,
)

# Generation 1's measurement layer, imported and never modified. ``measure`` reads the raw cost
# model for its annualisation constants and is otherwise strategy-agnostic; ``trade_ledger`` is a
# plain projection of ``result.trades``. Both are correct for a portfolio of k as they stand.
from stockedge100.strategies.runner import measure, trade_ledger

#: The only three attributes of a completed run that the selection is allowed to see. Asserted
#: against :class:`SelectionInput` at import, so widening the record without widening this tuple —
#: or the reverse — fails immediately rather than quietly admitting a performance figure.
SELECTION_FIELD_NAMES = ("variant_id", "shutdown_events", "fill_count", "per_run")

GATE_RUN_LABEL = "#BASE"


# -- the declared runs -----------------------------------------------------------------------------


def run_labels() -> tuple[str, ...]:
    """The sealed run labels, checked against the sealed counts.

    ``count``, ``labels`` and ``total_runs`` are three statements of the same fact in the seal. If
    they ever disagreed, one of them would silently decide how many runs happen.
    """
    declared = load_protocol()["runs_per_variant"]
    labels = tuple(declared["labels"])
    if len(labels) != int(declared["count"]):
        raise ConfigViolation(
            f"the seal declares count={declared['count']} runs per variant but lists "
            f"{len(labels)} labels {list(labels)}"
        )
    if len(set(labels)) != len(labels):
        raise ConfigViolation(f"the sealed run labels are not distinct: {list(labels)}")
    expected = len(rotation_variants()) * len(labels)
    if int(declared["total_runs"]) != expected:
        raise ConfigViolation(
            f"the seal declares total_runs={declared['total_runs']}; "
            f"{len(rotation_variants())} variants x {len(labels)} labels is {expected}"
        )
    return labels


def scenario_for_label(label: str) -> str:
    """Map a sealed run label onto a cost scenario, by derivation rather than by a written table.

    ``#STRESS`` and ``STRESSED`` are not the same string, and a hand-written ``{"#STRESS":
    STRESSED}`` map would keep working if the seal were ever read wrong. Stripping the marker and
    requiring exactly one scenario prefixed by what remains refuses an ambiguous or unknown label
    instead of guessing at one.

    The label must itself be one the seal declares. Without that check the prefix match would
    happily resolve an invented ``#S`` to ``STRESSED``, which is exactly the guess this function
    exists to avoid.
    """
    declared = run_labels()
    if label not in declared:
        raise ConfigViolation(f"{label!r} is not one of the sealed run labels {list(declared)}")
    token = label.lstrip("#")
    matches = [scenario for scenario in SCENARIOS if scenario.startswith(token)]
    if len(matches) != 1:
        raise ConfigViolation(
            f"the sealed run label {label!r} resolves to {matches!r} among the declared cost "
            f"scenarios {list(SCENARIOS)}; exactly one is required"
        )
    return matches[0]


def load_grid_dataset() -> dict[str, Any]:
    """The development-window dataset, loaded through the Generation 2 window guard.

    Both calls matter. ``load_stage_3_dataset`` truncates at the development bound as it reads;
    ``assert_series_within_bound`` re-checks the loaded series, so a bar dated 2021-08-01 or later
    would have to survive a truncating loader *and* a separate audit of the result.
    """
    series = guard.load_stage_3_dataset(eligible_universe())
    guard.assert_series_within_bound(series)
    return series


@dataclass(frozen=True)
class GridRun:
    """One completed run of one variant under one cost scenario.

    Carries the measurement — required by the seal for all eighteen variants — and the strategy's
    own evidence. Neither is visible to the selection: see :func:`selection_inputs`.
    """

    variant: RotationVariant
    label: str
    scenario: str
    result: BacktestResult
    measurement: dict[str, Any]
    strategy_evidence: dict[str, Any]
    clamps: dict[str, Any]
    ledger: list[dict[str, Any]]

    @property
    def run_id(self) -> str:
        return f"{self.variant.variant_id}{self.label}"

    @property
    def fill_count(self) -> int:
        """Turnover, as the seal defines it: "len(result.fills) ... counting both entries and
        exits, including any forced liquidation fills"."""
        return len(self.result.fills)

    @property
    def shutdown_fired(self) -> bool:
        """A research shutdown fires at most once per run, so this is the run's event count."""
        return self.result.shutdown_session is not None

    def to_json(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "variant_id": self.variant.variant_id,
            "grid_index": self.variant.index,
            "label": self.label,
            "cost_scenario": self.scenario,
            "variant": self.variant.to_json(),
            "fill_count": self.fill_count,
            "research_shutdown_events": 1 if self.shutdown_fired else 0,
            "shutdown_session": (
                None if self.result.shutdown_session is None
                else self.result.shutdown_session.isoformat()
            ),
            "measurement": self.measurement,
            "strategy_evidence": self.strategy_evidence,
            "clamps": self.clamps,
        }


def run_one(
    variant: RotationVariant,
    label: str,
    series: dict[str, Any],
    *,
    protocol: dict[str, Any] | None = None,
) -> GridRun:
    """Execute one declared run.

    A fresh :class:`~stockedge100.strategies.g2_rotation.RotationCandidate` is built per run. The
    candidate accumulates the ranking hash and the rebalance counters as it goes, so reusing one
    across two runs would blend two runs' evidence into one digest and destroy the determinism
    claim the seal gates on.
    """
    protocol = load_protocol() if protocol is None else protocol
    if label not in run_labels():
        raise ConfigViolation(f"{label!r} is not one of the sealed run labels {list(run_labels())}")

    scenario = scenario_for_label(label)
    costs = rotation_cost_model(variant.top_k, scenario)
    _, raw, _ = derive_mapping(variant.top_k)
    candidate = RotationCandidate(variant, costs)

    span = protocol["run_span"]
    engine = RotationEngine(
        series,
        costs,
        guard.stage_3_window(),
        candidate,
        start=dt.date.fromisoformat(span["run_start"]),
        end=dt.date.fromisoformat(span["run_end"]),
        label=f"{variant.variant_id}{label}",
        budget_weight=candidate.weight,
    )
    result = engine.run()

    sessions = len(result.equity_curve)
    if sessions != int(span["run_sessions"]):
        raise InvariantViolation(
            f"{variant.variant_id}{label}: the run covered {sessions} sessions; the sealed run span "
            f"declares {span['run_sessions']}. Every variant shares one run start and one run end, "
            "so a differing session count means the dataset, not the strategy, changed."
        )

    return GridRun(
        variant=variant,
        label=label,
        scenario=scenario,
        result=result,
        measurement=measure(result, costs, raw),
        strategy_evidence=candidate.evidence(),
        clamps=engine.clamp_summary(),
        ledger=trade_ledger(result),
    )


def run_grid(
    series: dict[str, Any] | None = None,
    *,
    variants: Sequence[RotationVariant] | None = None,
    labels: Sequence[str] | None = None,
    progress: Callable[[int, int, GridRun], None] | None = None,
) -> tuple[GridRun, ...]:
    """Every declared run, unconditionally.

    The loop is variant-major and label-minor purely so a progress log reads in grid order. Nothing
    downstream depends on the order, and nothing in the loop inspects a completed run: the seal
    declares all thirty-six in advance and none is conditional on another's outcome.

    ``variants`` and ``labels`` exist for tests that need one cell of the grid. When both are left
    at their defaults the full cross product runs and the sealed ``total_runs`` is asserted.
    """
    protocol = load_protocol()
    if series is None:
        series = load_grid_dataset()
    full = variants is None and labels is None
    grid = tuple(rotation_variants()) if variants is None else tuple(variants)
    which = run_labels() if labels is None else tuple(labels)

    total = len(grid) * len(which)
    runs: list[GridRun] = []
    for variant in grid:
        for label in which:
            run = run_one(variant, label, series, protocol=protocol)
            runs.append(run)
            if progress is not None:
                progress(len(runs), total, run)

    if full and len(runs) != int(protocol["runs_per_variant"]["total_runs"]):
        raise InvariantViolation(
            f"the grid produced {len(runs)} runs; the seal declares "
            f"{protocol['runs_per_variant']['total_runs']}"
        )
    return tuple(runs)


# -- the return-blind projection -------------------------------------------------------------------


@dataclass(frozen=True)
class SelectionInput:
    """Everything the selection is permitted to know about one variant.

    Four fields, and every one of them is return-blind: an identifier, a count of research-shutdown
    events, a count of fills, and the same two counts split per declared run. There is deliberately
    no field for return, drawdown, profit factor, Sharpe, equity, win rate, or trade P&L, and no
    reference to the :class:`GridRun` that produced it — so no step of
    :func:`select_representative` can reach a performance figure even by accident.
    """

    variant_id: str
    shutdown_events: int
    fill_count: int
    per_run: tuple[tuple[str, int, int], ...]

    def to_json(self) -> dict[str, Any]:
        return {
            "variant_id": self.variant_id,
            "research_shutdown_events": self.shutdown_events,
            "fill_count": self.fill_count,
            "per_run": [
                {"label": label, "research_shutdown_events": events, "fill_count": fills}
                for label, events, fills in self.per_run
            ],
        }


_ACTUAL_SELECTION_FIELDS = tuple(field.name for field in fields(SelectionInput))
if _ACTUAL_SELECTION_FIELDS != SELECTION_FIELD_NAMES:
    raise ConfigViolation(
        f"SelectionInput carries {list(_ACTUAL_SELECTION_FIELDS)}; the declared return-blind "
        f"projection is {list(SELECTION_FIELD_NAMES)}. A field was added or removed without the "
        "return-blindness declaration being revisited."
    )


def selection_inputs(runs: Sequence[GridRun]) -> tuple[SelectionInput, ...]:
    """Project the completed runs down to what the sealed rule may read.

    This is the single place a :class:`GridRun` is touched on the way to a selection, and it reads
    exactly three things off each one: the variant id, whether the research shutdown fired, and how
    many fills there were. Grouping is by variant, and every declared label must be present exactly
    once — a variant missing its ``#STRESS`` run would otherwise pass the zero-shutdown screen on
    half the evidence the seal requires.
    """
    declared_labels = run_labels()
    grouped: dict[str, dict[str, GridRun]] = {}
    for run in runs:
        by_label = grouped.setdefault(run.variant.variant_id, {})
        if run.label in by_label:
            raise ConfigViolation(f"{run.run_id} was supplied more than once")
        by_label[run.label] = run

    inputs: list[SelectionInput] = []
    for variant_id in sorted(grouped):
        by_label = grouped[variant_id]
        missing = [label for label in declared_labels if label not in by_label]
        extra = sorted(set(by_label) - set(declared_labels))
        if missing or extra:
            raise ConfigViolation(
                f"{variant_id}: the sealed rule screens across BOTH declared runs "
                f"{list(declared_labels)}; missing={missing} unexpected={extra}"
            )
        per_run = tuple(
            (label, 1 if by_label[label].shutdown_fired else 0, by_label[label].fill_count)
            for label in declared_labels
        )
        inputs.append(
            SelectionInput(
                variant_id=variant_id,
                shutdown_events=sum(events for _, events, _ in per_run),
                fill_count=sum(fills for _, _, fills in per_run),
                per_run=per_run,
            )
        )
    return tuple(inputs)


# -- the sealed selection --------------------------------------------------------------------------

#: The sealed step order this module implements. Restating it is deliberate: it is a cross-check,
#: not a source. If the seal's steps were ever read in a different order, or a step renamed, the
#: code below would go on applying the rule it was written for while claiming to apply the sealed
#: one. :func:`sealed_steps` refuses instead.
EXPECTED_STEP_NAMES = {
    1: "zero_research_shutdown_events",
    2: "lowest_turnover",
    3: "lexicographic_variant_id",
}


def sealed_steps(rule: dict[str, Any]) -> dict[int, dict[str, Any]]:
    """The three selection steps keyed by their declared ``order``, checked against what this
    module implements."""
    steps: dict[int, dict[str, Any]] = {}
    for entry in rule["steps"]:
        order = int(entry["order"])
        if order in steps:
            raise ConfigViolation(f"the sealed selection rule declares order {order} twice")
        steps[order] = entry
    if sorted(steps) != sorted(EXPECTED_STEP_NAMES):
        raise ConfigViolation(
            f"the sealed selection rule declares steps {sorted(steps)}; this module implements "
            f"{sorted(EXPECTED_STEP_NAMES)}"
        )
    for order, name in EXPECTED_STEP_NAMES.items():
        if steps[order]["name"] != name:
            raise ConfigViolation(
                f"sealed selection step {order} is {steps[order]['name']!r}; this module "
                f"implements {name!r}"
            )
    return steps


def select_representative(
    inputs: Sequence[SelectionInput],
    *,
    protocol: dict[str, Any] | None = None,
    require_full_grid: bool = True,
) -> dict[str, Any]:
    """Apply the frozen three-step rule and record how it decided.

    Step 1 screens on zero research-shutdown events across **both** declared runs. Step 2 takes the
    lowest fill count summed over both runs. Step 3 breaks a remaining tie on the lexicographically
    smallest variant id — arbitrary on purpose, because an arbitrary tiebreak cannot be steered.

    If nothing survives step 1 the sealed ``no_candidate_path`` applies and no representative is
    returned. The grid is not loosened and the screen is not narrowed to the base run: the caller
    takes that verdict to :func:`~stockedge100.strategies.g2_gate.stage_verdict_g2` with
    ``representative_exists=False``.
    """
    protocol = load_protocol() if protocol is None else protocol
    rule = protocol["representative_selection_rule"]
    steps = sealed_steps(rule)
    step_1, step_2, step_3 = steps[1], steps[2], steps[3]

    supplied = [entry.variant_id for entry in inputs]
    if len(set(supplied)) != len(supplied):
        raise ConfigViolation(f"duplicate variant ids in the selection inputs: {sorted(supplied)}")
    if require_full_grid:
        declared = sorted(variant.variant_id for variant in rotation_variants())
        if sorted(supplied) != declared:
            raise ConfigViolation(
                "the selection runs over the complete declared grid; supplied "
                f"{len(supplied)} of {len(declared)} variants, "
                f"missing={sorted(set(declared) - set(supplied))} "
                f"unexpected={sorted(set(supplied) - set(declared))}"
            )

    ordered = tuple(sorted(inputs, key=lambda entry: entry.variant_id))
    eligible = tuple(entry for entry in ordered if entry.shutdown_events == 0)
    ineligible = tuple(entry for entry in ordered if entry.shutdown_events != 0)

    record: dict[str, Any] = {
        "rule_ref": f"{protocol['artifact_id']} representative_selection_rule",
        "frozen_before_any_variant_is_run": rule["frozen_before_any_variant_is_run"],
        "return_blind": rule["return_blind"],
        "return_blind_statement": rule["return_blind_statement"],
        "return_blind_enforcement": (
            "select_representative receives only SelectionInput records, whose fields are "
            f"{list(SELECTION_FIELD_NAMES)}. No BacktestResult, measurement, equity curve or trade "
            "P&L is in scope at the point the representative is decided."
        ),
        "variants_considered": len(ordered),
        "inputs": [entry.to_json() for entry in ordered],
        "step_1": {
            "order": 1,
            "name": step_1["name"],
            "rule": step_1["rule"],
            "scope_note": step_1["scope_note"],
            "mechanism": step_1["mechanism"],
            "eligible": [entry.variant_id for entry in eligible],
            "ineligible": [
                {"variant_id": entry.variant_id, "research_shutdown_events": entry.shutdown_events}
                for entry in ineligible
            ],
            "eligible_count": len(eligible),
        },
    }

    if not eligible:
        no_candidate = rule["no_candidate_path"]
        record.update(
            {
                "representative_variant_id": None,
                "representative_exists": False,
                "decided_at_step": None,
                "decided_by": "no_candidate_path",
                "step_2": None,
                "step_3": None,
                "no_candidate_path": no_candidate,
                "selection_note": (
                    f"All {len(ordered)} declared variants recorded at least one research-shutdown "
                    "event across their two declared runs, so no variant is eligible under step 1. "
                    "The sealed no_candidate_path applies: the grid is not loosened, the shutdown "
                    "threshold is not raised, the screen is not narrowed to the base run, and the "
                    "rule is not revised post hoc."
                ),
            }
        )
        return record

    lowest = min(entry.fill_count for entry in eligible)
    tied = tuple(entry for entry in eligible if entry.fill_count == lowest)
    chosen = min(tied, key=lambda entry: entry.variant_id)

    if len(eligible) == 1:
        decided_at, decided_by = 1, "zero_research_shutdown_events"
        note = (
            f"Exactly one variant, {chosen.variant_id}, recorded zero research-shutdown events "
            f"across both declared runs; the other {len(ineligible)} did not. Step 1 decided; "
            "steps 2 and 3 were not reached."
        )
    elif len(tied) == 1:
        decided_at, decided_by = 2, "lowest_turnover"
        note = (
            f"{len(eligible)} variants recorded zero research-shutdown events across both declared "
            f"runs. Among them {chosen.variant_id} had the lowest turnover, {lowest} fills summed "
            "over its two runs, and no other eligible variant matched that count. Step 2 decided; "
            "step 3 was not reached."
        )
    else:
        decided_at, decided_by = 3, "lexicographic_variant_id"
        note = (
            f"{len(eligible)} variants recorded zero research-shutdown events across both declared "
            f"runs, and {len(tied)} of them tied at the lowest turnover of {lowest} fills. The "
            f"lexicographically smallest variant id among the tie, {chosen.variant_id}, advanced."
        )

    record.update(
        {
            "representative_variant_id": chosen.variant_id,
            "representative_exists": True,
            "decided_at_step": decided_at,
            "decided_by": decided_by,
            "step_2": {
                "order": 2,
                "name": step_2["name"],
                "rule": step_2["rule"],
                "measurement": step_2["measurement"],
                "proxy_justification": step_2["proxy_justification"],
                "fill_counts": {entry.variant_id: entry.fill_count for entry in eligible},
                "lowest_fill_count": lowest,
                "tied_at_lowest": [entry.variant_id for entry in tied],
                "reached": True,
            },
            "step_3": {
                "order": 3,
                "name": step_3["name"],
                "rule": step_3["rule"],
                "purpose": step_3["purpose"],
                "reached": decided_at == 3,
                "ordering": [entry.variant_id for entry in sorted(
                    tied, key=lambda entry: entry.variant_id
                )],
            },
            "no_reselection": rule["no_reselection"],
            "second_fail_path": rule["second_fail_path"],
            "selection_note": note,
        }
    )
    if decided_at == 1:
        record["step_2"]["reached"] = False
    return record


# -- what the gate is given -------------------------------------------------------------------------


def run_for(runs: Sequence[GridRun], variant_id: str, label: str) -> GridRun:
    """The one completed run matching ``(variant_id, label)``, or a refusal."""
    found = [run for run in runs if run.variant.variant_id == variant_id and run.label == label]
    if len(found) != 1:
        raise ConfigViolation(
            f"expected exactly one run for {variant_id}{label}; found {len(found)}"
        )
    return found[0]


def gate_inputs(
    runs: Sequence[GridRun],
    variant_id: str,
    *,
    criteria: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble exactly what Gate 3 evaluates: the representative's ``#BASE`` run and its
    structural neighbours' ``#BASE`` runs.

    The seal's ``gate_evaluation_scope`` says the gate is evaluated on "the selected
    representative's #BASE run only", with the stress run "reported, not gating". The neighbour set
    is not chosen here — :func:`~stockedge100.strategies.g2_gate.neighbours_of` derives it from the
    grid axes, and S3-C7 re-derives it again and refuses a set that differs.
    """
    criteria = load_criteria() if criteria is None else criteria
    scope = load_protocol()["gate_evaluation_scope"]
    if GATE_RUN_LABEL not in scope["evaluated_on"]:
        raise ConfigViolation(
            f"the sealed gate scope is {scope['evaluated_on']!r}, which does not name "
            f"{GATE_RUN_LABEL}; refusing to assume which run the gate reads"
        )

    variant = variant_by_id(variant_id)
    primary = run_for(runs, variant_id, GATE_RUN_LABEL)
    neighbours = [
        (member, run_for(runs, member.variant_id, GATE_RUN_LABEL).result)
        for member in neighbours_of(variant, criteria)
    ]
    return {
        "variant": variant,
        "primary": primary.result,
        "primary_run": primary,
        "neighbours": neighbours,
        "stress_run": run_for(runs, variant_id, "#STRESS"),
        "evaluated_on": scope["evaluated_on"],
        "stress_run_treatment": scope["stress_run_treatment"],
        "not_a_disjunction": scope["not_a_disjunction"],
    }


def grid_report(runs: Sequence[GridRun]) -> list[dict[str, Any]]:
    """The descriptive record the seal requires for all eighteen variants, in grid order.

    ``reported_for_every_variant_but_not_gating`` is explicit about the standing of these figures:
    "These figures are a descriptive record. They may not be used to justify a selection other than
    the one the frozen rule produced, to argue that a different variant should have advanced, or to
    reopen the grid." They are produced here, after the selection, and are not an input to it.
    """
    by_key = {(run.variant.variant_id, run.label): run for run in runs}
    rows: list[dict[str, Any]] = []
    for variant in rotation_variants():
        for label in run_labels():
            run = by_key.get((variant.variant_id, label))
            if run is None:
                continue
            metrics = run.measurement
            rows.append(
                {
                    "grid_index": variant.index,
                    "variant_id": variant.variant_id,
                    "lookback_months": variant.lookback_months,
                    "top_k": variant.top_k,
                    "rebalance_frequency": variant.frequency,
                    "label": label,
                    "total_return": metrics["total_return"],
                    "cagr": metrics["cagr"],
                    "max_drawdown": metrics["max_drawdown"],
                    "profit_factor": metrics["profit_factor"],
                    "closed_trades": metrics["closed_trades"],
                    "research_shutdown_events": 1 if run.shutdown_fired else 0,
                    "shutdown_session": metrics["shutdown_session"],
                    "fills": run.fill_count,
                    # "Traded" is counted off the fills, not off the closed trades: a position
                    # still open at the run end contributes a fill and no trade, and the seal asks
                    # for distinct symbols traded, not distinct symbols realised.
                    "distinct_symbols_traded": len({fill.fill.symbol for fill in run.result.fills}),
                    "distinct_symbols_with_closed_trades": len(metrics["contribution_by_symbol"]),
                    "sharpe": metrics["sharpe"],
                    "daily_return_stdev": metrics["daily_return_stdev"],
                    "exposure_fraction": metrics["exposure_fraction"],
                    "win_rate": metrics["win_rate"],
                    "average_win": metrics["average_win"],
                    "average_loss": metrics["average_loss"],
                    "longest_flat_streak_sessions": metrics["longest_flat_streak_sessions"],
                    "trades_digest": metrics["trades_digest"],
                    "equity_digest": metrics["equity_digest"],
                    "ranking_digest": run.strategy_evidence["ranking_digest"],
                    "scheduled_rebalances": run.strategy_evidence["scheduled_rebalances"],
                    "executed_rebalances": run.strategy_evidence["executed_rebalances"],
                }
            )
    return rows
