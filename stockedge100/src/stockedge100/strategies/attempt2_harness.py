"""Run Attempt 2's eighteen declared runs, evaluate the seven conditions, hand back the findings.

This module runs and measures. It does not decide the gate: :func:`run_all` returns the seven
condition verdicts exactly as :mod:`stockedge100.strategies.gate` computed them, and the stage token
exactly as the sealed ``verdict_token_derivation`` derives it from those verdicts. Nothing here can
turn a ``NOT_MET`` into a pass, because nothing here writes a verdict — it only collects them, and
:func:`_refuse_incoherent` refuses to hand back a set that disagrees with itself.

Four properties are worth stating because they are what a reader of the evidence would otherwise
have to take on trust.

**The run count is bounded by the seal, not by this code.** ``iteration_budget`` declares 15 gating
variants, 3 non-gating stressed-cost runs, 18 total and 0 revisions permitted.
:func:`stockedge100.strategies.attempt2_runner.variant_specs` enumerates the variants from the sealed
file and already refuses a count that differs from the sealed ``max_variants``; :func:`run_all` checks
all three totals against the sealed figures at the end. There is no branch here that reruns a
candidate, and no branch that reads a result before deciding what to run next. A failing candidate is
reported as failed — ``primary_decision_rule.fail_is_a_deliverable``.

**Every candidate is run before any of them is judged.** The gate evaluation is a pure function of a
run's outputs, so this ordering changes no number; it makes it structurally impossible for one
candidate's result to influence how the next one is run, which is the property constitution §11
protects when it says a material change made after seeing a result creates a new candidate.

**The determinism re-run is a verification, not a retry.** ``rerun_policy`` is unambiguous that a
completed valid run is the result and is never re-run "in the hope of a different number", and it
supplies the reason this one is nevertheless required: "a re-run of an unchanged variant must
reproduce byte-identical output. A re-run that produced a DIFFERENT number would be a determinism
defect and a blocker, not a better result." So each primary is executed a second time under a
distinct ``#RERUN`` label, only its digests are compared, and the reported result stays the first
execution's in every field. The re-run is outside the sealed 18 because it is not a declared variant.

**The stressed run cannot move a verdict.** ``cost_stress_treatment.gating`` is ``false`` and its
``prohibition`` is explicit: the ``STRESS_FRAGILE`` flag "may not be used at Gate 3 to admit a
candidate that failed a hard condition, nor to reject a candidate that satisfied all of them". The
stressed measures are assembled by :func:`~stockedge100.strategies.attempt2_runner.stress_evidence`
and are never passed to :mod:`stockedge100.strategies.gate`; the only call into the gate takes the
primary and its four neighbours, all under the base cost model.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Sequence

from stockedge100.backtest.config import load_stage2_config
from stockedge100.backtest.costs import BASE, STRESSED, CostModel
from stockedge100.backtest.errors import ConfigViolation
from stockedge100.backtest.window import DEVELOPMENT, ResearchWindow, development_window
from stockedge100.strategies import gate, reference
from stockedge100.strategies.attempt2_config import Attempt2Config, load_attempt2_config
from stockedge100.strategies.attempt2_runner import (
    DETERMINISM_SUFFIX,
    STRESS_SUFFIX,
    VariantRun,
    load_required_dataset,
    measure_variant,
    plan_candidate,
    run_variant,
    stress_evidence,
)
from stockedge100.strategies.runner import NEIGHBOUR, PRIMARY, trade_ledger

#: No Attempt 2 evidence id is pre-declared anywhere in ``config/``, ``governance/`` or
#: ``reports/stage3_attempt2/``; Attempt 1's evidence is ``SE100-EVID-3001``, so this is the next id
#: in the established series.
EVIDENCE_ARTIFACT_ID = "SE100-EVID-3002"

WINDOW_NOTE = (
    "Every run below is bounded by the Stage 1 holdout lock. ResearchWindow.check rejects a run "
    "start or a run end outside the development window, and MarketView raises LookAheadError on any "
    "read past the decision session, so no validation observation and no holdout observation enters "
    "a market view, a decision, a metric, or any number reported here. That is the mechanism the "
    "sealed partitions.enforcement names, and it is the Gate 2 validated one. It is a statement "
    "about what reached a computation: the normalized per-symbol CSVs are opened in full at load "
    "time, as they were at Gate 2 and at Attempt 1's Gate 3, so it is not a claim that no "
    "later-dated row was ever read off disk."
)

LEDGER_NOTE = (
    "The full closed-trade list for the primary run only, so S3-C3, S3-C5 and S3-C6 can be "
    "recomputed by hand from this file. Neighbour ledgers are omitted: only the sign of a "
    "neighbour's net return carries gate weight. The stressed run's ledger is omitted for the same "
    "reason in reverse — it carries no gate weight at all."
)

DETERMINISM_NOTE = (
    "Each primary is executed a second time under a distinct #RERUN label and only its trade and "
    "equity digests are compared. Sealed rerun_policy: 'a re-run of an unchanged variant must "
    "reproduce byte-identical output. A re-run that produced a DIFFERENT number would be a "
    "determinism defect and a blocker, not a better result.' The reported result is the first "
    "execution's in every field, and the re-run is not one of the 18 declared runs."
)


def _refuse_incoherent(
    stage: dict[str, Any], gate_results: Sequence[dict[str, Any]], binding: dict[str, Any]
) -> None:
    """Refuse to return a verdict set that matches any sealed ``incoherent_combinations_refused``.

    The sealed list is five entries long. Three are checkable here against the list itself — a PASS
    with no admitted candidate, a FAIL with one, and a candidate marked admitted while carrying an
    unsatisfied condition, which is how ``NOT_EVALUABLE`` or ``NOT_RUN`` would have to be treated as
    satisfied to reach a pass. The fourth entry, a PASS reached by aggregating rollup rows instead of
    evaluating conjunction within a candidate, is prevented by construction rather than detected:
    :func:`gate.stage_verdict` reads each candidate's own ``admitted`` flag and never sees a rollup
    row. What is checked instead is the property that error would violate — ``within_candidate:
    CONJUNCTIVE`` — in both directions, so a candidate whose ``admitted`` flag disagrees with the
    conjunction of its own conditions fails here either way. The fifth, a verdict written into a
    package the evidence does not reach, is checked by the package builder against this evidence file.

    The entries are read positionally out of a frozen, digest-verified file, so the length is
    asserted first: a seal that no longer carries five refusals must fail rather than be indexed.
    """

    rule = binding["admissible_candidate_exists"]
    refused = list(rule["incoherent_combinations_refused"])
    if len(refused) != 5:
        raise ConfigViolation(
            f"the sealed incoherent_combinations_refused carries {len(refused)} entries, not the 5 "
            "this check was written against"
        )
    admitted = list(stage["admitted_candidates"])

    if stage["verdict"] == "PASS" and not admitted:
        raise ConfigViolation(f"refused by the seal: {refused[0]}")
    if stage["verdict"] == "FAIL" and admitted:
        raise ConfigViolation(f"refused by the seal: {refused[1]}")

    for entry in gate_results:
        unsatisfied = [row["id"] for row in entry["conditions"] if not row["satisfied"]]
        if entry["admitted"] and unsatisfied:
            raise ConfigViolation(
                f"{entry['experiment_id']} is marked admitted while {unsatisfied} are not "
                f"satisfied; refused by the seal: {refused[2]}"
            )
        if not entry["admitted"] and not unsatisfied:
            raise ConfigViolation(
                f"{entry['experiment_id']} is marked not admitted while every one of its conditions "
                f"is satisfied; the sealed within_candidate rule is {rule['within_candidate']!r}, "
                "so the candidate flag must equal the conjunction of its own conditions"
            )

    for row in gate_results:
        for condition in row["conditions"]:
            expected = condition["verdict"] in (gate.MET, gate.NOT_APPLICABLE)
            if condition["satisfied"] != expected:
                raise ConfigViolation(
                    f"{row['experiment_id']} {condition['id']}: satisfied="
                    f"{condition['satisfied']} disagrees with the sealed satisfied_definition "
                    f"{rule['satisfied_definition']!r}"
                )


def condition_rollup(gate_results: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """The sealed per-condition rollup shape: three lists per row, aggregated on *satisfaction*.

    ``per_condition_rollup_is_not_the_gate.required_reporting_shape``: "Each per-condition row must
    carry three separate lists - met_by, not_met_by, and not_applicable_for - so that a
    NOT_APPLICABLE_BY_CONDITION_TEXT verdict is visible as such rather than folded into a pass or a
    fail."

    ``known_failure_mode_recorded``: "Aggregating a per-condition row on verdict == MET rather than
    on satisfaction produced a false FAIL for S3-C6 in Attempt 1's first rollup. The rollup must
    aggregate on satisfaction. It is recorded here so the same defect is not reintroduced by a fresh
    implementation." ``satisfied_by_at_least_one_candidate`` below is therefore computed from
    ``met_by`` **or** ``not_applicable_for``, and a fourth field records each candidate's raw verdict
    so a ``NOT_EVALUABLE`` inside ``not_met_by`` stays visible as what it is.

    And ``rule``: a row "means only 'at least one candidate satisfied this condition'. It is not
    evidence that any candidate satisfied all of them, and it settles nothing on its own." That
    sentence travels with every row rather than sitting once in a header.
    """

    if not gate_results:
        raise ConfigViolation("a per-condition rollup needs at least one evaluated candidate")

    order = [row["id"] for row in gate_results[0]["conditions"]]
    rows: list[dict[str, Any]] = []
    for condition_id in order:
        met_by: list[str] = []
        not_met_by: list[str] = []
        not_applicable_for: list[str] = []
        verdicts: dict[str, str] = {}
        for entry in gate_results:
            found = [row for row in entry["conditions"] if row["id"] == condition_id]
            if len(found) != 1:
                raise ConfigViolation(
                    f"{entry['experiment_id']} carries {len(found)} verdicts for {condition_id}; "
                    "every candidate must carry exactly one verdict for every sealed condition"
                )
            condition = found[0]
            name = entry["experiment_id"]
            verdicts[name] = condition["verdict"]
            if condition["verdict"] == gate.NOT_APPLICABLE:
                not_applicable_for.append(name)
            elif condition["verdict"] == gate.MET:
                met_by.append(name)
            else:
                not_met_by.append(name)
        rows.append(
            {
                "id": condition_id,
                "aggregated_on": "satisfaction, where satisfied means MET or "
                "NOT_APPLICABLE_BY_CONDITION_TEXT",
                "satisfied_by_at_least_one_candidate": bool(met_by or not_applicable_for),
                "met_by": met_by,
                "not_met_by": not_met_by,
                "not_applicable_for": not_applicable_for,
                "verdict_by_candidate": verdicts,
                "settles": (
                    "nothing on its own; this row means only that at least one candidate satisfied "
                    "this condition, not that any candidate satisfied all of them"
                ),
            }
        )
    return rows


def decisive_row(stage: dict[str, Any], binding: dict[str, Any]) -> dict[str, Any]:
    """The ``admissible_candidate_exists`` row — the one row that decides Gate 3.

    ``per_condition_rollup_is_not_the_gate.decisive_row``: "The conditions table must carry the
    admissible_candidate_exists row, and that row alone decides the gate. A conditions table that
    omits it is misleading and is not an acceptable deliverable."
    """

    rule = binding["admissible_candidate_exists"]
    admitted = list(stage["admitted_candidates"])
    return {
        "id": "admissible_candidate_exists",
        "frozen_rule": rule["frozen_rule"],
        "satisfied_definition": rule["satisfied_definition"],
        "within_candidate": rule["within_candidate"],
        "across_candidates": rule["across_candidates"],
        "value": bool(admitted),
        "admitted_candidates": admitted,
        "candidates_evaluated": stage["candidates_evaluated"],
        "decides_the_gate": True,
        "gate_verdict": stage["verdict"],
        # ``condition_token`` is the sealed *condition statement* the verdict rests on, not the
        # stage token; :func:`gate.stage_verdict` reads it from ``pass_condition``/``fail_condition``
        # while the tokens themselves come from ``pass_token``/``fail_token``. Naming it a token here
        # would put the wrong string next to the word "token" in the decisive row of the package.
        "gate_verdict_condition": stage["condition_token"],
        "gate_verdict_token": stage["pass_token"] if admitted else stage["fail_token"],
    }


def _determinism_entry(primary: VariantRun, rerun: VariantRun) -> dict[str, Any]:
    return {
        "experiment_id": primary.spec.experiment_id,
        "variant_id": primary.spec.variant_id,
        "label": primary.label,
        "rerun_label": rerun.label,
        "trades_digest": primary.result.trades_digest(),
        "equity_digest": primary.result.equity_digest(),
        "rerun_trades_digest": rerun.result.trades_digest(),
        "rerun_equity_digest": rerun.result.equity_digest(),
        "identical": (
            primary.result.trades_digest() == rerun.result.trades_digest()
            and primary.result.equity_digest() == rerun.result.equity_digest()
        ),
    }


def _window_block(config: Attempt2Config, window: ResearchWindow) -> dict[str, Any]:
    return {
        **window.to_json(),
        "declared_bounds_source": config.protocol["inputs_bound"]["window_bounds_source"],
        "partitions": config.protocol["partitions"],
        "authorized_windows": config.preregistration["authorized_windows"],
        "validation_state": config.preregistration["validation_window_state"],
        "holdout_state": config.preregistration["holdout_window_state"],
        "validation_observations_read": False,
        "holdout_observations_read": False,
        "boundary_changed": False,
        "note": WINDOW_NOTE,
    }


def _cost_block(base: CostModel, stressed: CostModel) -> dict[str, Any]:
    """Both scenarios, side by side, with what the stress does and does not change.

    The stress multiplies trading friction only. ``min_order_notional`` is unchanged, so RA1-2's
    sealed ``NO_ENTRY_SIZE_FLOOR`` threshold of USD 1.00 is the same number in both scenarios, and
    ``research_shutdown_drawdown`` is unchanged, so the sealed
    ``shutdown_behaviour.enforced_for_every_run`` holds identically for the three stressed runs. The
    two values are recorded here rather than asserted in prose.
    """

    return {
        "base": {
            **base.to_json(),
            "starting_equity_usd": f"{base.starting_equity:f}",
            "max_gross_exposure_fraction": f"{base.max_gross_exposure_fraction:f}",
            "min_cash_buffer_fraction": f"{base.min_cash_buffer_fraction:f}",
            "min_order_notional_usd": f"{base.min_order_notional:f}",
            "research_shutdown_drawdown": f"{base.research_shutdown_drawdown:f}",
            "gating": True,
        },
        "stressed": {
            **stressed.to_json(),
            "stress_multiplier": f"{stressed.stress_multiplier:f}",
            "min_order_notional_usd": f"{stressed.min_order_notional:f}",
            "research_shutdown_drawdown": f"{stressed.research_shutdown_drawdown:f}",
            "gating": False,
            "note": (
                "Applied to the three non-gating stressed-cost runs only. The stress scales trading "
                "friction; it leaves min_order_notional_usd and research_shutdown_drawdown at their "
                "base values, so RA1-2's size floor and the section 5.1 shutdown are the same in "
                "both scenarios."
            ),
        },
    }


def run_all() -> dict[str, Any]:
    """Every declared Attempt 2 run, measured and judged. The body of the Attempt 2 evidence file."""

    config = load_attempt2_config()
    stage2 = load_stage2_config()
    base = CostModel(stage2.cost_model, BASE)
    stressed = CostModel(stage2.cost_model, STRESSED)
    window = development_window()

    if window.name != DEVELOPMENT:
        raise ConfigViolation(
            f"Attempt 2 may read the development window only; got {window.name!r}"
        )

    tolerance = Decimal(stage2.engine_spec["benchmark_reconciliation"]["relative_tolerance"])
    sealed_benchmarks = dict(config.protocol["benchmarks"])
    budget = dict(config.iteration_budget)
    warmup_changes = config.rsi_warmup_changes

    series = load_required_dataset(config)

    candidates: list[dict[str, Any]] = []
    gate_results: list[dict[str, Any]] = []
    determinism: list[dict[str, Any]] = []
    gating_runs = 0
    stress_runs = 0

    for experiment in config.experiments:
        plan = plan_candidate(experiment, window, series, warmup_changes)

        runs: dict[str, VariantRun] = {}
        for spec in plan.variants:
            runs[spec.variant_id] = run_variant(
                spec, plan, series, base, window, warmup_changes, gating=True
            )
            gating_runs += 1

        primary_spec = plan.variants[0]
        if primary_spec.role != PRIMARY:
            raise ConfigViolation(f"{plan.experiment_id}: first variant is not the primary")
        primary = runs[primary_spec.variant_id]

        # A verification of the run just completed, not a second attempt at it. See the module
        # docstring and DETERMINISM_NOTE: only the digests are read, and this run is outside the 18.
        rerun = run_variant(
            primary_spec,
            plan,
            series,
            base,
            window,
            warmup_changes,
            gating=False,
            label_suffix=DETERMINISM_SUFFIX,
        )
        determinism.append(_determinism_entry(primary, rerun))

        # The one stressed-cost run this candidate is allowed, of the primary parameterisation only.
        stress = run_variant(
            primary_spec,
            plan,
            series,
            stressed,
            window,
            warmup_changes,
            gating=False,
            label_suffix=STRESS_SUFFIX,
        )
        stress_runs += 1

        neighbours = [
            (spec, runs[spec.variant_id].result)
            for spec in plan.variants
            if spec.role == NEIGHBOUR
        ]
        verdicts = gate.evaluate_candidate(
            plan=plan,
            primary=primary.result,
            neighbours=neighbours,
            criteria=config.criteria,
        )
        gate_results.append(verdicts)

        benchmarks = reference.candidate_benchmarks(
            plan, series, base, window, stage2.cost_model, sealed_benchmarks, tolerance
        )
        measured = {
            spec.variant_id: measure_variant(runs[spec.variant_id], base, stage2.cost_model)
            for spec in plan.variants
        }
        primary_measure = measured[primary_spec.variant_id]
        stress_measure = measure_variant(stress, stressed, stage2.cost_model)

        candidates.append(
            {
                "plan": plan.to_json(),
                "runs": measured,
                "stressed_cost_run": {
                    "declared_rule": config.protocol["cost_stress_treatment"]["attempt_2_rule"],
                    "prohibition": config.protocol["cost_stress_treatment"]["prohibition"],
                    **stress_evidence(primary_measure, stress_measure, stressed.stress_multiplier),
                },
                "gate": verdicts,
                "benchmarks": benchmarks,
                "benchmark_comparison": reference.comparison(primary_measure, benchmarks),
                "primary_trade_ledger": trade_ledger(primary.result),
                "primary_trade_ledger_note": LEDGER_NOTE,
            }
        )

    stage = gate.stage_verdict(gate_results, config.criteria)
    _refuse_incoherent(stage, gate_results, config.binding)

    executed_runs = gating_runs + stress_runs
    for label, executed, key in (
        ("gating variants", gating_runs, "total_declared_gating_variants"),
        ("non-gating stress runs", stress_runs, "total_declared_non_gating_stress_runs"),
        ("total runs", executed_runs, "total_declared_runs"),
    ):
        declared = int(budget[key])
        if executed != declared:
            raise ConfigViolation(
                f"executed {executed} {label} against a sealed {key} of {declared}; the protocol "
                "permits no extra run and no omitted one"
            )

    return {
        "artifact_id": EVIDENCE_ARTIFACT_ID,
        "title": "StockEdge100 Stage 3 Attempt 2 development admissibility evidence",
        "project": config.protocol["project"],
        "generation": config.protocol["generation"],
        "stage": 3,
        "attempt": config.protocol["attempt"],
        "attempt_id": config.protocol["attempt_id"],
        "gate_id": config.criteria["gate_id"],
        "gate_name": config.criteria["gate_name"],
        "constitution_ref": config.criteria["constitution_ref"],
        "window": _window_block(config, window),
        "sealed_inputs": {
            "preregistration": config.preregistration["document_id"],
            "preregistration_declared_utc": config.preregistration["declared_utc"],
            "preregistration_run_id": config.preregistration["run_id"],
            "protocol_artifact_id": config.protocol["artifact_id"],
            "binding_artifact_id": config.binding["artifact_id"],
            "criteria_artifact_id": config.criteria["artifact_id"],
            "digests_recomputed_at_load": dict(sorted(config.digests.items())),
            "sealed_before_any_attempt_2_strategy_code": config.preregistration[
                "sealed_before_any_attempt_2_strategy_code"
            ],
        },
        "cost_models": _cost_block(base, stressed),
        "iteration_budget": {
            **budget,
            "gating_variants_executed": gating_runs,
            "non_gating_stress_runs_executed": stress_runs,
            "runs_executed": executed_runs,
            "candidates_evaluated": len(gate_results),
            "revisions_made": 0,
            "variants_rerun_after_seeing_a_result": 0,
            "determinism_reruns_outside_the_declared_budget": len(determinism),
        },
        "adaptive_research": {
            "known_prior_evidence": config.protocol["known_prior_evidence"],
            "adaptive_research_disclosure": config.protocol["adaptive_research_disclosure"],
            "multiple_comparisons_disclosure": config.protocol[
                "multiple_comparisons_disclosure"
            ],
            "cumulative_experiment_count": config.protocol["cumulative_experiment_count"],
        },
        "determinism": {
            "condition": "each primary reproduces its own trades and equity digests on a re-run",
            "note": DETERMINISM_NOTE,
            "declared": config.protocol["reproducibility_requirements"]["determinism"],
            "random_seeds": config.protocol["reproducibility_requirements"]["random_seeds"],
            "random_seeds_note": config.protocol["reproducibility_requirements"][
                "random_seeds_note"
            ],
            "runs": determinism,
            "all_identical": all(entry["identical"] for entry in determinism),
        },
        "candidates": candidates,
        "gate_summary": [
            {
                "experiment_id": entry["experiment_id"],
                "family": entry["family"],
                "admitted": entry["admitted"],
                "conditions_met": entry["conditions_met"],
                "conditions_not_met": entry["conditions_not_met"],
                "conditions_not_evaluable": entry["conditions_not_evaluable"],
                "conditions_not_applicable": entry["conditions_not_applicable"],
            }
            for entry in gate_results
        ],
        "per_condition_rollup": {
            "warning": config.binding["admissible_candidate_exists"][
                "per_condition_rollup_is_not_the_gate"
            ],
            "rows": condition_rollup(gate_results),
            "decisive_row": decisive_row(stage, config.binding),
        },
        "stage_verdict": stage,
        "explicit_non_authorizations": config.protocol["explicit_non_authorizations"],
        "no_selection_in_this_stage": config.protocol["no_selection_in_this_stage"],
        "authorization_state_unchanged_by_this_stage": {
            "stage_4_authorized": config.preregistration["stage_4_authorized"],
            "paper_trading_authorized": config.preregistration["paper_trading_authorized"],
            "shadow_live_authorized": config.preregistration["shadow_live_authorized"],
            "live_trading_authorized": config.preregistration["live_trading_authorized"],
        },
        "live_trading_authorized": False,
    }
