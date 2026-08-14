"""Run the thirty declared runs, evaluate the seven conditions, and hand back the findings.

This module runs and measures. It does not decide the stage: :func:`run_all` returns the seven
condition verdicts exactly as :mod:`stockedge100.strategies.gate` computed them, and the stage token
exactly as the sealed ``verdict_token_derivation`` derives it from those verdicts. Nothing here can
turn a NOT_MET into a pass, because nothing here writes a verdict — it only collects them.

Two properties are worth stating because they are what a reader of the evidence would otherwise have
to take on trust:

**The run count is bounded by the seal, not by this code.** ``iteration_budget.total_declared_runs``
is 30 and ``revisions_permitted`` is 0. :func:`run_all` executes exactly the variants
:func:`stockedge100.strategies.runner.variant_specs` enumerates from the sealed file, checks the
total against the sealed figure, and has no branch that reruns a candidate. A failing candidate is
reported as failed.

**Every candidate is run before any of them is judged.** The gate evaluation is a pure function of a
run's outputs, so this ordering changes no number — but it makes it structurally impossible for one
candidate's result to influence how the next one is run, which is the property constitution §11 is
protecting when it says a material change after seeing a result creates a new candidate.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from stockedge100.backtest.config import load_stage2_config
from stockedge100.backtest.costs import BASE, CostModel
from stockedge100.backtest.errors import ConfigViolation
from stockedge100.backtest.window import DEVELOPMENT, development_window
from stockedge100.strategies import gate, reference
from stockedge100.strategies.config import load_stage3_config
from stockedge100.strategies.runner import (
    NEIGHBOUR,
    PRIMARY,
    load_required_dataset,
    measure,
    plan_candidate,
    run_variant,
    trade_ledger,
)

DETERMINISM_SUFFIX = "#RERUN"


def run_all() -> dict[str, Any]:
    """Every declared run, measured and judged. The body of the Stage 3 evidence file."""

    config = load_stage3_config()
    stage2 = load_stage2_config()
    costs = CostModel(stage2.cost_model, BASE)
    window = development_window()

    if window.name != DEVELOPMENT:
        raise ConfigViolation(f"Stage 3 may read the development window only; got {window.name!r}")
    declared_window = config.protocol["inputs_bound"]
    tolerance = Decimal(stage2.engine_spec["benchmark_reconciliation"]["relative_tolerance"])
    sealed_benchmarks = dict(config.protocol["benchmarks"])
    budget = dict(config.protocol["iteration_budget"])

    series = load_required_dataset(config)
    indicators = config.indicator_definitions

    candidates: list[dict[str, Any]] = []
    gate_results: list[dict[str, Any]] = []
    executed_runs = 0
    determinism: list[dict[str, Any]] = []

    for experiment in config.experiments:
        plan = plan_candidate(experiment, window, series, indicators)
        results: dict[str, Any] = {}
        for spec in plan.variants:
            results[spec.variant_id] = run_variant(
                spec, plan, series, costs, window, indicators
            )
            executed_runs += 1

        primary_spec = plan.variants[0]
        if primary_spec.role != PRIMARY:
            raise ConfigViolation(f"{plan.experiment_id}: first variant is not the primary")
        primary = results[primary_spec.variant_id]

        # A determinism re-run of the primary, with a fresh candidate object. F5 carries per-run
        # mutable state (``pending_target``), so a reused object would make this check vacuous.
        rerun = run_variant(
            primary_spec, plan, series, costs, window, indicators, label_suffix=DETERMINISM_SUFFIX
        )
        determinism.append(
            {
                "experiment_id": plan.experiment_id,
                "trades_digest": primary.trades_digest(),
                "equity_digest": primary.equity_digest(),
                "rerun_trades_digest": rerun.trades_digest(),
                "rerun_equity_digest": rerun.equity_digest(),
                "identical": (
                    primary.trades_digest() == rerun.trades_digest()
                    and primary.equity_digest() == rerun.equity_digest()
                ),
            }
        )

        neighbours = [
            (spec, results[spec.variant_id])
            for spec in plan.variants
            if spec.role == NEIGHBOUR
        ]
        verdicts = gate.evaluate_candidate(
            plan=plan, primary=primary, neighbours=neighbours, criteria=config.criteria
        )
        gate_results.append(verdicts)

        benchmarks = reference.candidate_benchmarks(
            plan, series, costs, window, stage2.cost_model, sealed_benchmarks, tolerance
        )
        primary_measure = measure(primary, costs, stage2.cost_model)

        candidates.append(
            {
                "plan": plan.to_json(),
                "runs": {
                    spec.variant_id: {
                        "role": spec.role,
                        "parameters": spec.to_json()["parameters"],
                        **measure(results[spec.variant_id], costs, stage2.cost_model),
                    }
                    for spec in plan.variants
                },
                "gate": verdicts,
                "benchmarks": benchmarks,
                "benchmark_comparison": reference.comparison(primary_measure, benchmarks),
                "primary_trade_ledger": trade_ledger(primary),
                "primary_trade_ledger_note": (
                    "The full closed-trade list for the primary run only, so S3-C3, S3-C5 and S3-C6 "
                    "can be recomputed by hand from this file. Neighbour ledgers are omitted: only "
                    "the sign of a neighbour's net return carries gate weight."
                ),
            }
        )

    stage = gate.stage_verdict(gate_results, config.criteria)

    declared = int(budget["total_declared_runs"])
    if executed_runs != declared:
        raise ConfigViolation(
            f"executed {executed_runs} runs against a sealed budget of {declared}; the protocol "
            "permits no extra run and no omitted one"
        )

    return {
        "artifact_id": "SE100-EVID-3001",
        "title": "StockEdge100 Stage 3 development admissibility evidence",
        "project": config.protocol["project"],
        "stage": 3,
        "gate_id": config.criteria["gate_id"],
        "gate_name": config.criteria["gate_name"],
        "constitution_ref": config.criteria["constitution_ref"],
        "window": {
            **window.to_json(),
            "declared": declared_window,
            "validation_and_holdout_read": False,
            "note": (
                "Every run below is bounded by the Stage 1 holdout lock through "
                "ResearchWindow.check; a read outside this window raises WindowViolation rather "
                "than returning a price."
            ),
        },
        "sealed_inputs": {
            # The pre-registration carries a ``document_id``, not an ``artifact_id`` — that spelling
            # belongs to the configuration files. Reading the wrong key recorded ``null`` here and
            # silently dropped the identity of the seal this run is bound to.
            "preregistration": config.preregistration.get("document_id"),
            "preregistration_declared_utc": config.preregistration.get("declared_utc"),
            "digests_recomputed_at_load": dict(sorted(config.digests.items())),
            "protocol_artifact_id": config.protocol["artifact_id"],
            "criteria_artifact_id": config.criteria["artifact_id"],
        },
        "cost_model": {
            "note": (
                "Base costs only. The sealed protocol runs Stage 3 under the base scenario; the "
                "stressed scenario belongs to the Gate 4 robustness work."
            ),
            **costs.to_json(),
            "starting_equity_usd": f"{costs.starting_equity:f}",
            "max_gross_exposure_fraction": f"{costs.max_gross_exposure_fraction:f}",
            "research_shutdown_drawdown": f"{costs.research_shutdown_drawdown:f}",
        },
        "iteration_budget": {
            **budget,
            "runs_executed": executed_runs,
            "candidates_evaluated": len(gate_results),
            "revisions_made": 0,
            "candidates_rerun_after_seeing_a_result": 0,
        },
        "multiple_comparisons_disclosure": config.protocol["multiple_comparisons_disclosure"],
        "determinism": {
            "condition": "each primary reproduces its own trades and equity digests on a re-run",
            "runs": determinism,
            "all_identical": all(entry["identical"] for entry in determinism),
        },
        "candidates": candidates,
        "gate_summary": [
            {
                "experiment_id": entry["experiment_id"],
                "family": entry["family"],
                "admitted": entry["admitted"],
                "conditions_not_met": entry["conditions_not_met"],
                "conditions_not_evaluable": entry["conditions_not_evaluable"],
                "conditions_not_applicable": entry["conditions_not_applicable"],
            }
            for entry in gate_results
        ],
        "stage_verdict": stage,
        "explicit_non_authorizations": config.protocol["explicit_non_authorizations"],
        "no_selection_in_this_stage": config.protocol["no_selection_in_this_stage"],
        "live_trading_authorized": False,
    }
