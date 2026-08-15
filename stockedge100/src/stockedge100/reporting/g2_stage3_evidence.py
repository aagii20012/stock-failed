"""Generation 2 Stage 3 development evidence — run the declared grid, write what it did.

A writer, not a judge. Every figure comes from :mod:`stockedge100.strategies.g2_runner`, every
condition verdict from :mod:`stockedge100.strategies.g2_gate`, and the representative — if one
exists — from the sealed three-step rule in ``config/generation_2/g2_rotation_protocol.json``.
Nothing in this module can change a verdict.

The ordering below is load-bearing and mirrors the seal:

  1. load the development dataset through the Generation 2 window guard;
  2. run all thirty-six declared runs unconditionally — none is conditional on another's outcome;
  3. project them to the return-blind ``SelectionInput`` records;
  4. apply the frozen selection rule;
  5. only then evaluate Gate 3, and only on the variant step 4 produced.

Steps 4 and 5 are in that order by construction rather than by convention: the selection is decided
from records carrying no performance figure at all, so no return computed in step 2 can reach it.
The descriptive eighteen-variant table is built last, after the verdict is already settled, for the
same reason — the seal requires it to be reported for every variant and to gate nothing.

``generated_utc`` is read from the system clock at write time and never hand-typed.
``evidence_digest`` covers the body with ``generated_utc`` and ``evidence_digest`` themselves
removed, and :func:`finalize` puts every covered field in place — **including
``evidence_digest_covers`` itself** — before taking the digest. Generation 1 learned that the hard
way: Stage 2 added the coverage sentence after digesting and left the file asserting a coverage it
did not have, which cost a full package regeneration. Two-run stability does not catch it, because a
wrong-but-consistent coverage is perfectly stable; recomputing from the written file while following
its own coverage sentence literally is what catches it.

The evidence lands in ``reports/``, outside the ``repo_state_id`` patterns, so writing it does not
perturb the digest the decision package will later record.

Usage::

    cd stockedge100 && PYTHONPATH=src python -m stockedge100.reporting.g2_stage3_evidence
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from stockedge100.audit import sha256_file, sha256_text_canonical_json, utc_now_iso
from stockedge100.strategies import g2_gate as gate
from stockedge100.strategies import g2_runner as runner
from stockedge100.strategies import g2_window_guard as guard

PROJECT_ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_REL = "reports/stage3_g2/STAGE_3_G2_DEVELOPMENT_ADMISSIBILITY.json"

COMMAND = "cd stockedge100 && PYTHONPATH=src python -m stockedge100.reporting.g2_stage3_evidence"

# Generation 2's identifiers carry a 1 in the series position, the same convention the sealed
# config artifacts use: SE100-CFG-3101 and SE100-CFG-3102 are Generation 2's Stage 3 configs, where
# Generation 1's evidence was SE100-EVID-3001.
ARTIFACT_ID = "SE100-EVID-3101"

PROTOCOL_REL = "config/generation_2/g2_rotation_protocol.json"
CRITERIA_REL = "config/generation_2/g2_gate_criteria.json"
COST_MODEL_REL = "config/generation_2/g2_cost_model.json"
PARTITION_LOCK_REL = "governance/generation_2/STAGE_1_G2_PARTITION_LOCK.json"
CHARTER_REL = "governance/generation_2/STAGE_10_GENERATION_2_CHARTER.md"

EXCLUDED_FROM_DIGEST = ("generated_utc", "evidence_digest")

DIGEST_COVERS = (
    "every field of this file except generated_utc and evidence_digest, as canonical JSON"
)


def evidence_digest(body: dict[str, Any]) -> str:
    """The digest of the findings, with the two non-finding fields removed."""

    return sha256_text_canonical_json(
        {key: value for key, value in body.items() if key not in EXCLUDED_FROM_DIGEST}
    )


def finalize(body: dict[str, Any], generated_utc: str) -> dict[str, Any]:
    """Add the three fields the run does not produce, then seal the body with its own digest."""

    body = dict(body)
    body["generated_utc"] = generated_utc
    body["command"] = COMMAND
    body["evidence_digest_covers"] = DIGEST_COVERS
    body["evidence_digest"] = evidence_digest(body)
    return body


def _run_digests(run: runner.GridRun) -> dict[str, Any]:
    """The identity of one run, as three digests and three scalars.

    Digests alone would not catch a run that produced the same trades from a different ranking, and
    scalars alone would not catch a reordering, so both are recorded.
    """
    return {
        "trades_digest": run.result.trades_digest(),
        "equity_digest": run.result.equity_digest(),
        "ranking_digest": run.strategy_evidence["ranking_digest"],
        "fill_count": run.fill_count,
        "final_equity": run.measurement["final_equity"],
        "shutdown_session": (
            None if run.result.shutdown_session is None
            else run.result.shutdown_session.isoformat()
        ),
    }


def variant_table(runs: tuple[runner.GridRun, ...]) -> list[dict[str, Any]]:
    """The eighteen-variant descriptive table the seal requires and the gate ignores.

    One row per variant, with both declared runs side by side. Built after the verdict is settled;
    nothing here is an input to anything. ``research_shutdown_events`` is the sum across the two
    runs, which is the figure step 1 of the selection rule screens on — it is repeated here so a
    reader can check the selection against the table without recomputing it.
    """
    by_variant: dict[str, dict[str, runner.GridRun]] = {}
    for run in runs:
        by_variant.setdefault(run.variant.variant_id, {})[run.label] = run

    rows: list[dict[str, Any]] = []
    for variant_id in sorted(by_variant, key=lambda v: by_variant[v]["#BASE"].variant.index):
        pair = by_variant[variant_id]
        base = pair["#BASE"]
        row: dict[str, Any] = {
            "grid_index": base.variant.index,
            "variant_id": variant_id,
            "lookback_months": base.variant.lookback_months,
            "top_k": base.variant.top_k,
            "rebalance_frequency": base.variant.frequency,
            "research_shutdown_events": sum(1 for r in pair.values() if r.shutdown_fired),
            "fill_count_both_runs": sum(r.fill_count for r in pair.values()),
        }
        for label, run in sorted(pair.items()):
            short = label.lstrip("#").lower()
            row[f"{short}_total_return"] = run.measurement["total_return"]
            row[f"{short}_max_drawdown"] = run.measurement["max_drawdown"]
            row[f"{short}_profit_factor"] = run.measurement["profit_factor"]
            row[f"{short}_closed_trades"] = run.measurement["closed_trades"]
            row[f"{short}_fills"] = run.fill_count
            row[f"{short}_shutdown_session"] = (
                None if run.result.shutdown_session is None
                else run.result.shutdown_session.isoformat()
            )
            row[f"{short}_distinct_symbols_targeted"] = run.strategy_evidence[
                "distinct_symbols_targeted"
            ]
        rows.append(row)
    return rows


def run_all_g2() -> dict[str, Any]:
    """Execute the stage and assemble the body. No field here is hand-typed."""

    protocol = runner.load_protocol()
    criteria = gate.load_criteria()
    window = guard.stage_3_window()
    bound = guard.development_bound()

    series = runner.load_grid_dataset()
    latest = max(one.sessions[-1] for one in series.values())
    if latest > bound:
        raise guard.WindowViolation(
            f"a bar dated {latest} survived the guarded load; the development bound is {bound}"
        )

    runs = runner.run_grid(series)
    inputs = runner.selection_inputs(runs)
    selection = runner.select_representative(inputs)

    candidate_results: list[dict[str, Any]] = []
    gate_scope: dict[str, Any] | None = None
    if selection["representative_exists"]:
        scope = runner.gate_inputs(runs, selection["representative_variant_id"], criteria=criteria)
        gate_scope = {
            "variant_id": scope["variant"].variant_id,
            "evaluated_on": scope["evaluated_on"],
            "stress_run_treatment": scope["stress_run_treatment"],
            "not_a_disjunction": scope["not_a_disjunction"],
            "neighbours": [member.variant_id for member, _ in scope["neighbours"]],
        }
        candidate_results.append(
            gate.evaluate_representative(
                variant=scope["variant"],
                primary=scope["primary"],
                neighbours=scope["neighbours"],
                criteria=criteria,
            )
        )

    verdict = gate.stage_verdict_g2(
        candidate_results,
        criteria,
        representative_exists=selection["representative_exists"],
        selection_note=selection["selection_note"],
    )

    # Determinism is claimed for the whole grid, not for a sample: the dataset is reloaded from disk
    # and every run repeated on fresh strategy objects. Comparing only the surviving representative
    # would leave the claim untested exactly where this stage spent its evidence.
    replay = runner.run_grid(runner.load_grid_dataset())
    first = {run.run_id: _run_digests(run) for run in runs}
    second = {run.run_id: _run_digests(run) for run in replay}
    mismatched = sorted(key for key in first if first[key] != second[key])

    return {
        "artifact_id": ARTIFACT_ID,
        "project": "StockEdge100",
        "generation": 2,
        "generation_id": protocol["generation_id"],
        "stage": "STAGE_3_G2_ROTATION_DEVELOPMENT",
        "gate": {"constitution_gate_id": 3, "name": "development_admissibility"},
        "strategy_id": protocol["strategy_id"],
        "sealed_inputs": {
            "protocol": PROTOCOL_REL,
            "protocol_artifact_id": protocol["artifact_id"],
            "protocol_sha256": sha256_file(PROJECT_ROOT / PROTOCOL_REL),
            "criteria": CRITERIA_REL,
            "criteria_artifact_id": criteria["artifact_id"],
            "criteria_sha256": sha256_file(PROJECT_ROOT / CRITERIA_REL),
            "cost_model": COST_MODEL_REL,
            "cost_model_sha256": sha256_file(PROJECT_ROOT / COST_MODEL_REL),
            "partition_lock": PARTITION_LOCK_REL,
            "partition_lock_sha256": sha256_file(PROJECT_ROOT / PARTITION_LOCK_REL),
            "charter": CHARTER_REL,
            "charter_sha256": sha256_file(PROJECT_ROOT / CHARTER_REL),
            "declared_before_any_strategy_code": protocol["declared_before_any_strategy_code"],
        },
        "window": {
            "name": window.name,
            "start": window.start.isoformat(),
            "end": window.end.isoformat(),
            "development_bound": bound.isoformat(),
            "run_span": protocol["run_span"],
            "latest_session_loaded": latest.isoformat(),
            "validation_read": False,
            "generation_1_holdout_read": False,
            "generation_2_holdout_read": False,
            "enforcement": (
                "load_grid_dataset truncates at the development bound and then audits the loaded "
                "bars separately, so a session dated 2021-08-01 or later would have to survive both "
                "a truncating loader and an independent check of its output"
            ),
        },
        "universe": {
            "universe_version": protocol["eligible_universe"]["universe_version"],
            "universe_identity_sha256": protocol["eligible_universe"]["universe_identity_sha256"],
            "symbols_declared": protocol["eligible_universe"]["member_count"],
            "symbols_loaded": len(series),
            "symbols_missing": sorted(
                set(protocol["eligible_universe"]["members"]) - set(series)
            ),
            "re_check": protocol["eligible_universe"]["re_check"],
            "excluded_symbols": protocol["eligible_universe"]["excluded_symbols"],
        },
        "grid": {
            "axes": protocol["grid"]["axes"],
            "variants_declared": protocol["grid"]["size"],
            "runs_per_variant": protocol["runs_per_variant"],
            "runs_executed": len(runs),
            "all_declared_runs_executed": len(runs)
            == int(protocol["runs_per_variant"]["total_runs"]),
            "revisions_after_seeing_a_result": 0,
        },
        "runs": [run.to_json() for run in runs],
        "selection_inputs": [entry.to_json() for entry in inputs],
        "selection": selection,
        "gate_scope": gate_scope,
        "candidate_results": candidate_results,
        "stage_verdict": verdict,
        "determinism": {
            "method": (
                "the dataset was reloaded from disk and all thirty-six runs repeated on fresh "
                "strategy objects; each run is compared on its trade digest, equity digest, ranking "
                "digest, fill count, final equity and shutdown session"
            ),
            "runs_compared": len(first),
            "all_identical": not mismatched,
            "mismatched_runs": mismatched,
            "run_digests": first,
        },
        "variant_table": variant_table(runs),
        "variant_table_is_descriptive_only": protocol[
            "reported_for_every_variant_but_not_gating"
        ],
        "multiple_comparisons_disclosure": protocol["multiple_comparisons_disclosure"],
        "representative_selection_rule": protocol["representative_selection_rule"],
        "gate_evaluation_scope": protocol["gate_evaluation_scope"],
        "explicit_non_authorizations": protocol["explicit_non_authorizations"],
        "live_trading_authorized": False,
    }


def build() -> int:
    body = finalize(run_all_g2(), utc_now_iso())

    path = PROJECT_ROOT / EVIDENCE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    print(f"generated_utc     {body['generated_utc']}")
    print(f"evidence_digest   {body['evidence_digest']}")
    print(f"runs_executed     {body['grid']['runs_executed']}")
    print(f"determinism       {body['determinism']['all_identical']}")
    print(f"representative    {body['selection']['representative_variant_id']}")
    print(f"decided_at_step   {body['selection']['decided_at_step']}")
    for row in body["variant_table"]:
        print(
            f"  {row['variant_id']:<44} shutdowns={row['research_shutdown_events']} "
            f"fills={row['fill_count_both_runs']:<5} base_return={row['base_total_return']}"
        )
    print(f"stage_verdict     {body['stage_verdict']['verdict']} {body['stage_verdict']['verdict_token']}")
    print(f"wrote             {EVIDENCE_REL}")

    # The stage verdict is a finding, not an error. A FAIL here is the outcome the sealed
    # no_candidate_path anticipated, and the file is the deliverable either way.
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
