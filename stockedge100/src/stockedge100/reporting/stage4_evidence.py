"""Stage 4 validation evidence — the one authorized read, executed once, written down.

A writer, not a judge, exactly as :mod:`stockedge100.reporting.attempt2_evidence` was for Gate 3.
Every metric comes from :func:`stockedge100.strategies.runner.measure` by way of the Stage 4
harness, and every condition verdict from :mod:`stockedge100.strategies.stage4_gate`, which reads
the sealed criteria file. Nothing in this module can change a verdict; it sequences the session,
records what happened, and seals the result with its own digest.

**Order is the specification here, not a style choice.** The sealed
``single_validation_read_rule`` is "one session, one load, the two declared runs", and the sealed
``reproducibility_requirements.recheck_rule`` is "recompute each digest *after* the evaluation".
So this module:

1. refuses if its own output already exists, or if a validation evaluation run record already
   exists — either would mean this is a second read of a partition that is read once;
2. verifies the Stage 0 freeze, loads the seal (which recomputes all thirteen sealed digests),
   runs the thirteen-artifact recheck and the Gate 3 strategy-invariance comparison, **before**
   touching an observation, so that a seal failure stops the session with the read unspent;
3. loads the declared universe exactly once;
4. executes the two declared runs, in declared order, against that one load;
5. measures the twelve sealed folds from the BASE run;
6. recomputes the thirteen-artifact recheck *after* the runs, which is the recheck S4-C7 reads;
7. writes its ``runs/`` record — before the gate is evaluated, because S4-C7's second clause counts
   that record and a count taken before the record existed would be a prediction;
8. counts the validation evaluation run records and requires exactly one;
9. evaluates the seven conditions conjunctively and derives the verdict token from the seal;
10. writes the evidence file.

**Every exit writes a ``runs/`` record**, including a refusal and a crash, because the sealed
``partial_or_failed_run_rule.no_silent_retry`` reads "Every attempt, including a failed one, gets a
runs/ record with its exit status. A failed attempt that leaves no record on disk is itself a
governance failure."

That rule and S4-C7's "exactly one validation evaluation run record" pull in opposite directions if
a failed attempt is recorded the same way a completed one is. They are separated by ``strategy_id``:
a record for an attempt that extracted no result carries ``strategy_id: null`` and a distinct
``stage`` value, so it is on disk as a failed *attempt* rather than as an *evaluation*. That reading
is disclosed in the decision package rather than assumed; it is the only reading under which both
sealed sentences can hold at once.

This module reads no dataset directly and imports no data layer: the single load happens inside
:func:`stockedge100.strategies.stage4_evaluation.load_validation_series`. That keeps the Stage 4
contamination predicate's count of source modules touching restricted data at exactly one, which is
the count the pre-registration recorded.

The evidence lands in ``reports/``, which is outside the ``repo_state_id`` patterns, so writing it
does not perturb the digest recorded here or the one the decision package will record later.

Usage::

    cd stockedge100 && PYTHONPATH=src python -m stockedge100.reporting.stage4_evidence
"""

from __future__ import annotations

import json
import time
import traceback
from typing import Any

from stockedge100.audit import (
    RunRecord,
    dependency_versions,
    sha256_file,
    sha256_text_canonical_json,
    utc_now_iso,
)
from stockedge100.reporting.stage_package import (
    TRACKED_DEPENDENCIES,
    new_run_id,
    repo_state,
    verify_stage0_freeze,
)
from stockedge100.strategies.stage4_evaluation import (
    BASE,
    CRITERIA_REL,
    PREREG_JSON_REL,
    PREREG_MD_REL,
    PROJECT_ROOT,
    PROTOCOL_REL,
    REPRESENTATIVE,
    RUNS_DIR,
    SELECTION_REL,
    STRESSED,
    Stage4Config,
    assert_holdout_unreachable,
    base_gate_evidence,
    dataset_digests,
    evaluation_window,
    execute_registered_runs,
    fold_returns,
    holdout_window,
    invariance_gate_evidence,
    load_stage4_config,
    load_validation_series,
    recheck_table,
    run_by_scenario,
    sealed_folds,
    stage4_plan,
    stress_gate_evidence,
    strategy_invariance,
    validation_evaluation_run_records,
    validation_window,
)
from stockedge100.strategies.stage4_gate import evaluate_gate4

EVIDENCE_REL = "reports/stage4/STAGE_4_VALIDATION_EVIDENCE.json"
EVIDENCE_ARTIFACT_ID = "SE100-EVID-4001"

UNIVERSE_REL = "governance/STAGE_1_UNIVERSE.json"
HOLDOUT_LOCK_REL = "governance/STAGE_1_HOLDOUT_LOCK.json"
NORMALIZED_MANIFEST_REL = "data/manifests/STAGE_1_NORMALIZED_MANIFEST.json"

COMMAND = "cd stockedge100 && PYTHONPATH=src python -m stockedge100.reporting.stage4_evidence"

#: The ``stage`` value of the one record S4-C7 counts, and of the records it must not count.
EVALUATION_STAGE = "STAGE_4_VALIDATION_EVALUATION"
FAILED_ATTEMPT_STAGE = "STAGE_4_VALIDATION_EVALUATION_FAILED_ATTEMPT"

EXCLUDED_FROM_DIGEST = ("generated_utc", "evidence_digest")
DIGEST_COVERS = (
    "every field of this file except generated_utc and evidence_digest, as canonical JSON"
)


# -- sealing ------------------------------------------------------------------------------------


def evidence_digest(body: dict[str, Any]) -> str:
    """The digest of the findings, with the two non-finding fields removed."""

    return sha256_text_canonical_json(
        {key: value for key, value in body.items() if key not in EXCLUDED_FROM_DIGEST}
    )


def finalize(body: dict[str, Any], generated_utc: str) -> dict[str, Any]:
    """Add the three fields the evaluation does not produce, then seal the body with its own digest.

    The order matters and is why this is a function rather than three assignments at the call site:
    every field the digest covers has to be in place before the digest is taken, **including
    ``evidence_digest_covers`` itself**. Stage 2 added that description afterwards and left a file
    asserting a coverage it did not have; the repair cost a full package regeneration.
    """

    body = dict(body)
    body["generated_utc"] = generated_utc
    body["command"] = COMMAND
    body["evidence_digest_covers"] = DIGEST_COVERS
    body["evidence_digest"] = evidence_digest(body)
    return body


# -- the runs/ record ----------------------------------------------------------------------------


def _read_json(rel: str) -> dict[str, Any]:
    return json.loads((PROJECT_ROOT / rel).read_text(encoding="utf-8"))


def unique_run_id() -> tuple[str, str]:
    """A ``(run_id, timestamp)`` pair whose record does not already exist on disk.

    ``runs/`` is append-only, but :meth:`~stockedge100.audit.RunRecord.write` opens its target for
    writing unconditionally, and :func:`~stockedge100.reporting.stage_package.new_run_id` is
    second-resolution — it strips the separators out of an ISO timestamp. Two records stamped inside
    the same second therefore carry the same id and the second silently destroys the first. This
    module can legitimately write two records in quick succession (an evaluation record, then a
    refusal on a later invocation), and ``runs/`` already holds records from every earlier stage that
    a collision would take with it.

    Re-reading the clock until the id is free keeps both invariants: the naming convention is
    unchanged, and no record is ever overwritten. The frozen ``audit`` module is not touched.
    """

    for _ in range(60):
        timestamp = utc_now_iso()
        run_id = new_run_id(timestamp)
        if not (RUNS_DIR / f"{run_id}.json").exists():
            return run_id, timestamp
        time.sleep(0.1)
    raise RuntimeError(
        "could not obtain a free run id: every second-resolution id for the last six seconds is "
        "already present in runs/. Writing anyway would overwrite an append-only record."
    )


def write_run_record(
    *,
    stage: str,
    exit_status: str,
    repo_state_id: str,
    code_hashes: dict[str, str],
    strategy_id: str | None,
    dataset_hashes: dict[str, str],
    date_range: list[str] | None,
    notes: list[str],
) -> str:
    """Write one append-only ``runs/`` record and return its id.

    ``holdout_state`` and ``universe_version`` are read from the frozen Stage 1 artifacts rather
    than restated, so a record can never claim a holdout state the lock does not carry.
    ``config_hash`` is the sealed validation protocol, which is the configuration that governed the
    attempt.

    ``output_artifact_hashes`` is empty by construction. The evidence file this session produces is
    written *after* this record — S4-C7 counts these records, so the count has to be taken with the
    record already on disk — and ``runs/`` is append-only, so there is no second pass in which a
    digest could be added. The evidence digest is recorded in the decision package's artifact
    manifest and checksum record instead. Writing a digest here for a file that does not yet exist
    would be a prediction in an evidence field.
    """

    run_id, timestamp = unique_run_id()
    lock = _read_json(HOLDOUT_LOCK_REL)
    universe = _read_json(UNIVERSE_REL)
    record = RunRecord(
        run_id=run_id,
        stage=stage,
        command=COMMAND,
        timestamp_utc=timestamp,
        repo_state_id=repo_state_id,
        code_hashes=code_hashes,
        config_hash=sha256_file(PROJECT_ROOT / PROTOCOL_REL),
        dataset_hashes=dataset_hashes,
        universe_version=universe["universe_version"],
        date_range=date_range,
        holdout_state=lock["holdout_state"],
        strategy_id=strategy_id,
        random_seed=None,
        dependency_versions=dependency_versions(TRACKED_DEPENDENCIES),
        exit_status=exit_status,
        output_artifact_hashes={},
        notes=notes,
    )
    record.write(RUNS_DIR)
    return record.run_id


# -- the session ---------------------------------------------------------------------------------


def _sealed_inputs(config: Stage4Config, repo_state_id: str) -> dict[str, Any]:
    """The identity of everything the session was bound by, as digests rather than as names."""

    return {
        "repo_state_id_at_evaluation": repo_state_id,
        "artifact_ids": {
            PROTOCOL_REL: config.protocol["artifact_id"],
            CRITERIA_REL: config.criteria["artifact_id"],
            SELECTION_REL: config.selection["artifact_id"],
        },
        "sealed_digests_verified_at_load": dict(config.digests),
        "sealed_digest_count": len(config.digests),
        "strategy_module": config.strategy_module_rel,
        "preregistration_files": [PREREG_MD_REL, PREREG_JSON_REL],
        "stage_0_freeze_verified": True,
    }


def _read_footprint(config: Stage4Config, window: Any, plan: Any) -> dict[str, Any]:
    """Exactly which observations the session was able to see, and which it could not."""

    validation = validation_window()
    holdout = holdout_window()
    return {
        "validation_partition": {
            "start": validation.start.isoformat(),
            "end": validation.end.isoformat(),
        },
        "engine_visibility_window": {
            "name": window.name,
            "start": window.start.isoformat(),
            "end": window.end.isoformat(),
            "note": (
                "A visibility bound, not a run bound. The leading segment is the sealed "
                f"{config.warmup_sessions}-session development tail that "
                "partitions.development.use_in_the_evaluation_session authorises for indicator "
                "computation only; no order may be placed in it because the run does not begin "
                "until the validation start."
            ),
        },
        "run_bounds": {
            "start": plan.run_start.isoformat(),
            "end": plan.run_end.isoformat(),
        },
        "holdout_partition": {
            "start": holdout.start.isoformat(),
            "end": holdout.end.isoformat(),
            "state": "SEALED",
            "sessions_read": 0,
        },
        "validation_dataset_loads": 1,
        "validation_reading_sessions": 1,
        "validation_window_engine_runs": config.declared_run_count,
    }


def run_session() -> dict[str, Any]:
    """Execute the authorized session and return the evidence body, unsealed.

    Split out from :func:`build` so that the whole path can be exercised against synthetic series
    in a dry run without writing anything into the tree.
    """

    frozen_ok, frozen_detail = verify_stage0_freeze()
    if not frozen_ok:
        failed = sorted(name for name, row in frozen_detail.items() if row["match"] != "True")
        raise RuntimeError(
            "the Stage 0 freeze does not verify; a frozen artifact changed: " + ", ".join(failed)
        )

    config = load_stage4_config()
    code_hashes, repo_state_id = repo_state()

    # Both of these run before a single observation is loaded, so a seal failure stops the session
    # with the one authorized read unspent.
    recheck_before = recheck_table(config)
    invariance = strategy_invariance(config)
    if not all(bool(row["equal"]) for row in recheck_before):
        broken = sorted(str(row["artifact"]) for row in recheck_before if not row["equal"])
        raise RuntimeError(
            "a sealed digest does not recompute before the validation load; the specification "
            "changed after sealing: " + ", ".join(broken)
        )
    if not bool(invariance["all_equal"]):
        raise RuntimeError(
            "the representative is not identical to its Gate 3 implementation: "
            + json.dumps({k: v for k, v in invariance.items() if v is False})
        )

    # -- the single load ------------------------------------------------------------------------
    series = load_validation_series(config)
    window = evaluation_window(series, config)
    plan = stage4_plan(config, window)
    holdout_facts = assert_holdout_unreachable(window, plan.run_end)

    executed = execute_registered_runs(config, series, window, plan)
    base_run = run_by_scenario(executed, BASE)
    stress_run = run_by_scenario(executed, STRESSED)

    folds = sealed_folds(config)
    fold_rows = fold_returns(
        base_run.result, folds, starting_equity=base_run.result.starting_equity
    )

    # The sealed recheck_rule measures S4-C7 *after* the evaluation, so this is the table the gate
    # reads; recheck_before is kept as evidence that the seal already held going in.
    recheck_after = recheck_table(config)

    base_evidence = base_gate_evidence(config, base_run)
    stress_evidence = stress_gate_evidence(config, stress_run)

    return {
        "config": config,
        "repo_state_id": repo_state_id,
        "code_hashes": code_hashes,
        "window": window,
        "plan": plan,
        "holdout_facts": holdout_facts,
        "executed": executed,
        "base_run": base_run,
        "stress_run": stress_run,
        "fold_rows": fold_rows,
        "recheck_before": recheck_before,
        "recheck_after": recheck_after,
        "invariance": invariance,
        "base_evidence": base_evidence,
        "stress_evidence": stress_evidence,
        "dataset_hashes": {
            NORMALIZED_MANIFEST_REL: sha256_file(PROJECT_ROOT / NORMALIZED_MANIFEST_REL),
            **dataset_digests(series),
        },
        "symbols_loaded": sorted(series),
    }


def assemble(session: dict[str, Any], run_record_id: str, run_records: list[str]) -> dict[str, Any]:
    """Turn an executed session into the evidence body, gate included.

    Called only after the ``runs/`` record is on disk, because ``run_records`` is a count of what is
    on disk and S4-C7 reads it.
    """

    config: Stage4Config = session["config"]
    base_run = session["base_run"]
    stress_run = session["stress_run"]

    invariance_evidence = invariance_gate_evidence(
        config,
        digest_rows=session["recheck_after"],
        invariance=session["invariance"],
        run_records=run_records,
        engine_runs=len(session["executed"]),
    )

    gate = evaluate_gate4(
        config.criteria,
        representative=REPRESENTATIVE,
        base=session["base_evidence"],
        stress=session["stress_evidence"],
        folds=session["fold_rows"],
        invariance=invariance_evidence,
    )

    protocol = config.protocol
    body: dict[str, Any] = {
        "artifact_id": EVIDENCE_ARTIFACT_ID,
        "title": "StockEdge100 Stage 4 sealed validation evidence",
        "project": protocol["project"],
        "generation": protocol["generation"],
        "stage": protocol["stage"],
        "gate_id": protocol["gate_id"],
        "gate_name": protocol["gate_name"],
        "constitution_ref": protocol["constitution_ref"],
        "representative": {
            "experiment_id": REPRESENTATIVE,
            "family": config.sealed_representative["family"],
            "declared_universe": list(config.declared_universe),
            "declared_warmup_sessions": config.warmup_sessions,
            "parameters": config.parameters,
            "selection_rule": config.selection["artifact_id"],
            "identifier_unchanged_from_gate_3": bool(
                session["invariance"]["identifier_unchanged_from_gate_3"]
            ),
        },
        "sealed_inputs": _sealed_inputs(config, session["repo_state_id"]),
        "single_validation_read": {
            "rule": protocol["single_validation_read_rule"]["rule"],
            **_read_footprint(config, session["window"], session["plan"]),
            "run_record": run_record_id,
            "command": COMMAND,
        },
        "holdout_unreachability_proof": session["holdout_facts"],
        "datasets": {
            "symbols_loaded": session["symbols_loaded"],
            "digests": session["dataset_hashes"],
        },
        "runs": [
            {
                "run_label": entry.run_label,
                "scenario": entry.scenario,
                "declared_order": index + 1,
                "gates_conditions": list(entry.gates_conditions),
                "cost_multiplier_declared": entry.declared.get("cost_multiplier"),
                "cost_model_in_force": entry.result.cost_model,
                "measure": entry.measure,
            }
            for index, entry in enumerate(session["executed"])
        ],
        "gate_evidence": {
            "base": _jsonable(session["base_evidence"]),
            "stress": _jsonable(session["stress_evidence"]),
            "invariance": _jsonable(invariance_evidence),
        },
        "folds": {
            "construction_id": config.fold_construction["id"],
            "rule": config.fold_construction["test_folds"]["rule"],
            "declared_test_folds": config.fold_construction["test_folds"]["count"],
            "declared_train_folds": config.fold_construction["train_folds"]["count"],
            "expected_completed_count": config.fold_construction["completed_fold_definition"][
                "expected_completed_count"
            ],
            "rows": session["fold_rows"],
            "completed": len([row for row in session["fold_rows"] if row["completed"]]),
            "positive": len([row for row in session["fold_rows"] if row["positive"]]),
        },
        "strategy_invariance": {
            "recheck_before_validation_load": session["recheck_before"],
            "recheck_after_evaluation": session["recheck_after"],
            "recheck_rule": config.protocol["reproducibility_requirements"]["recheck_rule"],
            "gate_3_comparison": session["invariance"],
        },
        "determinism": {
            "random_seed": None,
            "random_seed_note": config.protocol["reproducibility_requirements"][
                "random_seed_note"
            ],
            "digests": {
                entry.run_label: {
                    "trades_digest": entry.measure["trades_digest"],
                    "equity_digest": entry.measure["equity_digest"],
                }
                for entry in session["executed"]
            },
        },
        # The gate carries Decimal-valued evidence because the sealed predicates compare exactly.
        # JSON has no exact decimal, so the file carries the decimal strings measure() produced; the
        # comparison already happened on the Decimal, above this line.
        "gate": _jsonable(gate),
        "stage_verdict": {
            "gate_passed": gate["gate_passed"],
            "verdict_token": gate["verdict_token"],
            "verdict_token_source": gate["verdict_token_source"],
            "within_candidate": gate["within_candidate"],
            "across_candidates": gate["across_candidates"],
        },
        "explicit_non_authorizations": protocol["explicit_non_authorizations"],
        "authorization_state_unchanged_by_this_stage": {
            "final_holdout": "SEALED",
            "stage_5_paper_trading": "NOT_AUTHORIZED",
            "alpaca_paper_trading": "LOCKED",
            "shadow_live": "LOCKED",
            "alpaca_live_trading": "LOCKED",
            "capital_or_risk_expansion": "LOCKED",
            "broker_connection_attempted": False,
            "broker_credential_accessed": False,
            "orders_generated": 0,
        },
        "live_trading_authorized": False,
    }
    return body


def _jsonable(value: Any) -> Any:
    """Decimal-to-string, recursively.

    The gate evidence carries ``Decimal`` objects because the sealed predicates compare exactly and
    a float would round at the boundary. JSON has no exact decimal, so the *file* carries the
    decimal strings ``measure`` produced; the comparison already happened on the ``Decimal``.
    """

    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if value is None or isinstance(value, (bool, int, str)):
        return value
    return f"{value:f}" if hasattr(value, "as_tuple") else value


# -- entry point ---------------------------------------------------------------------------------


def _refuse(reason: str, detail: str) -> int:
    """Refuse to open the session, and leave the refusal on disk as the seal requires."""

    print(f"refusing to run: {reason}")
    print(detail)
    try:
        code_hashes, repo_state_id = repo_state()
        run_id = write_run_record(
            stage=FAILED_ATTEMPT_STAGE,
            exit_status="REFUSED_NO_VALIDATION_OBSERVATION_READ",
            repo_state_id=repo_state_id,
            code_hashes=code_hashes,
            strategy_id=None,
            dataset_hashes={},
            date_range=None,
            notes=[
                f"Refused before any validation observation was read: {reason}",
                detail,
                "strategy_id is null and the stage is the failed-attempt stage because this "
                "attempt extracted no result. S4-C7 counts validation evaluation records; a "
                "refusal is not one. The record exists because partial_or_failed_run_rule."
                "no_silent_retry requires every attempt to leave one.",
            ],
        )
        print(f"run record        {run_id}")
    except Exception as exc:  # noqa: BLE001 - the refusal is the point; report, do not mask
        print(f"could not write the refusal run record: {exc!r}")
    return 4


def build() -> int:
    path = PROJECT_ROOT / EVIDENCE_REL
    if path.exists():
        return _refuse(
            f"{EVIDENCE_REL} already exists",
            "The validation partition is read exactly once. A second write would either repeat a "
            "valid completed evaluation, which SE100-CFG-4001 single_validation_read_rule "
            "prohibits, or replace its numbers with a later set. If the existing file records a "
            "partial or invalid run, that is resolved under the sealed partial_or_failed_run_rule, "
            "which is a governance decision and not something this module may take on itself.",
        )

    existing = validation_evaluation_run_records()
    if existing:
        return _refuse(
            f"{len(existing)} validation evaluation run record(s) already exist",
            "runs/ already carries " + ", ".join(existing) + ". S4-C7 requires exactly one "
            "validation evaluation run record; running again would create a second and fail the "
            "condition it is supposed to measure.",
        )

    try:
        session = run_session()
    except Exception as exc:  # noqa: BLE001 - every attempt leaves a record, then the error stands
        detail = traceback.format_exc()
        try:
            code_hashes, repo_state_id = repo_state()
            run_id = write_run_record(
                stage=FAILED_ATTEMPT_STAGE,
                exit_status="FAILED",
                repo_state_id=repo_state_id,
                code_hashes=code_hashes,
                strategy_id=None,
                dataset_hashes={},
                date_range=None,
                notes=[
                    f"The attempt failed: {exc!r}",
                    "No result was extracted, so this attempt is not scored and its conditions "
                    "are NOT_EVALUABLE per SE100-CFG-4001 partial_or_failed_run_rule.",
                    "strategy_id is null and the stage is the failed-attempt stage so that S4-C7's "
                    "count of validation evaluation records is unaffected. The record exists "
                    "because no_silent_retry requires every attempt to leave one.",
                    detail.strip().replace("\n", " | "),
                ],
            )
            print(f"run record        {run_id}")
        except Exception as inner:  # noqa: BLE001
            print(f"could not write the failed-attempt run record: {inner!r}")
        raise

    config: Stage4Config = session["config"]
    validation = validation_window()
    reached = bool(
        session["base_evidence"]["reached_window_end"]
        and session["stress_evidence"]["reached_window_end"]
    )

    run_record_id = write_run_record(
        stage=EVALUATION_STAGE,
        exit_status="OK" if reached else "RUN_DID_NOT_REACH_THE_VALIDATION_END",
        repo_state_id=session["repo_state_id"],
        code_hashes=session["code_hashes"],
        strategy_id=REPRESENTATIVE,
        dataset_hashes=session["dataset_hashes"],
        date_range=[validation.start.isoformat(), validation.end.isoformat()],
        notes=[
            f"The single authorized validation-reading session: one dataset load, "
            f"{config.declared_run_count} declared runs in declared order "
            f"({', '.join(config.run_labels)}), no third engine run and no diagnostic query.",
            f"date_range is the validation partition. The engine window additionally spanned the "
            f"sealed {config.warmup_sessions}-session development tail preceding it, which "
            f"partitions.development.use_in_the_evaluation_session authorises for indicator "
            f"computation only; the run itself began at {validation.start.isoformat()}.",
            "exit_status describes the execution, not the gate: OK means both declared runs "
            "reached the frozen validation end. The Gate 4 verdict is in the decision package.",
            "output_artifact_hashes is empty because the evidence file is written after this "
            "record. S4-C7 counts these records, so the count must be taken with the record "
            "already on disk, and runs/ is append-only. The evidence digest is recorded in the "
            "decision package's artifact manifest and checksum record.",
            "The holdout was not read. Both the engine window and the run end precede the sealed "
            "holdout start, so no holdout bar was addressable by any probe.",
            "No broker was contacted, no credential was accessed and no order was generated. "
            "live_trading_authorized remains false.",
        ],
    )

    run_records = validation_evaluation_run_records()
    body = finalize(assemble(session, run_record_id, run_records), utc_now_iso())

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    gate = body["gate"]
    print(f"generated_utc     {body['generated_utc']}")
    print(f"evidence_digest   {body['evidence_digest']}")
    print(f"run record        {run_record_id}")
    print(f"validation loads  {body['single_validation_read']['validation_dataset_loads']}")
    print(f"runs executed     {len(body['runs'])}")
    for entry in body["runs"]:
        measured = entry["measure"]
        print(
            f"  {entry['run_label']:<44} return={measured['total_return']} "
            f"sharpe={measured['sharpe']} dd={measured['max_drawdown']}"
        )
    print(f"folds completed   {body['folds']['completed']}/12 positive={body['folds']['positive']}")
    for entry in gate["conditions"]:
        measured = entry["measured"] if entry["measured"] is not None else "-"
        literal = entry["evidence"].get("sealed_predicate_literal") or "-"
        print(f"  {entry['id']:<7} {entry['verdict']:<14} measured={measured:<24} vs {literal}")
    print(f"gate_passed       {gate['gate_passed']}")
    print(f"verdict_token     {gate['verdict_token']}")
    print(f"wrote             {EVIDENCE_REL}")

    # A Gate 4 failure is a finding and exits clean: the pre-registration disclosed that failure is
    # the expected outcome, and an evidence writer that returned non-zero on it would make a
    # legitimate negative result look like a broken run. What must never exit clean is a session
    # that did not do what it said.
    if len(run_records) != 1 or len(body["runs"]) != config.declared_run_count:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
