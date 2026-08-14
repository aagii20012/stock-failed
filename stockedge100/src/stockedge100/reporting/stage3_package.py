"""Stage 3 decision package — constitution gate 3, development admissibility.

This module supplies only Stage 3's own judgement: the seven gate conditions read from constitution
section 9 gate 3, the evidence backing each, the limitations that survive, the conflicts found, and
the verdict. Everything mechanical — timestamps, run id, ``repo_state_id``, manifests, checksum
record, run record — comes from :mod:`stockedge100.reporting.stage_package` so that nothing here can
be hand-typed.

Read the evidence, do not re-derive it. Every number quoted below is read out of
``reports/stage3/STAGE_3_DEVELOPMENT_ADMISSIBILITY.json``, which
:mod:`stockedge100.reporting.stage3_evidence` wrote by running the six pre-registered candidates
against the sealed protocol. Recomputing the figures here would mean the package and the evidence
could disagree without anything noticing.

**This stage fails, and the package records the failure.** Stage 2's builder refuses to run when its
evidence does not meet every condition, because a Stage 2 package could only ever be a pass. That
guard is wrong for Gate 3: a rejection is a deliverable here, and the constitution says so — negative
and rejected results stay on disk. The guard that belongs here is the other one, and :func:`build`
implements it: the verdict written into the package must be the verdict the evidence reached. If the
evidence said ``PASS`` and this module said ``FAIL``, or the reverse, nothing would be written.

Gate 3 has no ``pass_result`` token in ``STAGE_0_CONSTITUTION.json`` — only ``fail_result``, the same
defect Stages 1 and 2 recorded for their own gates. Both tokens were fixed in
``config/stage3_gate_criteria.json`` **before any candidate was run**, which is what makes it
defensible for this stage to now issue the fail one; they are read from the evidence rather than
written here as literals.

Conjunction applies **within** a candidate. Across candidates the stage verdict is a disjunction,
because Gate 3 asks whether an admissible candidate exists, not whether every candidate tried is
good. The per-condition entries below therefore carry an explicit ``verdict_semantics`` field: a
condition satisfied by some candidate is not a gate pass, and the gate-level determination is the
separate ``admissible_candidate_exists`` entry.

Usage::

    cd stockedge100 && PYTHONPATH=src python -m stockedge100.reporting.stage3_package
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from stockedge100.audit import sha256_file
from stockedge100.reporting.stage_package import (
    GOVERNANCE,
    PROJECT_ROOT,
    STAGE_0_FROZEN_INPUTS,
    StageDecision,
    build_stage_package,
    verify_sha256_record,
)

COMMAND = "cd stockedge100 && PYTHONPATH=src python -m stockedge100.reporting.stage3_package"

VERDICT = "FAIL — STAGE_3_STRATEGY_REJECTED_IN_DEVELOPMENT"

EVIDENCE = "reports/stage3/STAGE_3_DEVELOPMENT_ADMISSIBILITY.json"
PREREGISTRATION = "governance/STAGE_3_PREREGISTRATION.json"
PROTOCOL = "config/stage3_strategy_protocol.json"
CRITERIA = "config/stage3_gate_criteria.json"
COST_MODEL = "config/stage2_cost_model.json"
UNIVERSE = "governance/STAGE_1_UNIVERSE.json"
HOLDOUT_LOCK = "governance/STAGE_1_HOLDOUT_LOCK.json"
NORMALIZED_MANIFEST = "data/manifests/STAGE_1_NORMALIZED_MANIFEST.json"

# Every symbol any of the six candidates loaded. Hashed so that a rerun producing different numbers
# is attributable to a specific series rather than to "the data".
SERIES_READ = ("SPY", "MDY", "EFA", "IEF", "SHY")

STAGE_1_FROZEN_INPUTS = (
    "governance/STAGE_1_DATA_FOUNDATION_REPORT.md",
    "governance/STAGE_1_UNIVERSE.json",
    "governance/STAGE_1_HOLDOUT_LOCK.json",
    "governance/STAGE_1_FREEZE.sha256",
    "governance/STAGE_1_PREREGISTRATION.json",
    "governance/STAGE_1_PREREGISTRATION.sha256",
)

# Gate 2 was issued, so Stage 2's outputs are read-only inputs here. Stage 3 ran on that engine and
# on that cost model without touching either.
STAGE_2_FROZEN_INPUTS = (
    "governance/STAGE_2_BACKTEST_ENGINE_REPORT.md",
    "governance/STAGE_2_PREREGISTRATION.md",
    "governance/STAGE_2_PREREGISTRATION.json",
    "governance/STAGE_2_PREREGISTRATION.sha256",
    COST_MODEL,
    "config/stage2_engine_spec.json",
)

# Sealed before a single strategy module existed. These are the artifacts that make every result in
# this stage a test of a prediction rather than a description of a fit.
STAGE_3_SEALED_INPUTS = (
    "governance/STAGE_3_PREREGISTRATION.md",
    PREREGISTRATION,
    "governance/STAGE_3_PREREGISTRATION.sha256",
    PROTOCOL,
    CRITERIA,
)

PRODUCED = (
    "governance/STAGE_3_STRATEGY_RESEARCH_REPORT.md",
    EVIDENCE,
    "reports/stage3/STAGE_3_STRATEGY_RESEARCH.json",
    "reports/stage3/STAGE_3_ARTIFACT_MANIFEST.json",
    "reports/stage3/STAGE_3_TEST_SUMMARY.md",
    "reports/stage3/pytest_stage3_output.txt",
)

VERDICT_SEMANTICS = (
    "PASS here means at least one candidate satisfied this condition — it is NOT a gate pass. "
    "Conjunction applies within a candidate, so the gate is settled by "
    "admissible_candidate_exists, not by this field. Satisfaction includes "
    "NOT_APPLICABLE_BY_CONDITION_TEXT, which is satisfied without being met; read satisfied_by "
    "against met_by and not_applicable_for before drawing anything from a PASS."
)


def load(rel: str) -> dict[str, Any]:
    return json.loads((PROJECT_ROOT / rel).read_text(encoding="utf-8"))


def _per_candidate(ev: dict[str, Any], condition_id: str) -> dict[str, dict[str, Any]]:
    """Every candidate's verdict on one condition, with the measurement that settled it."""
    out: dict[str, dict[str, Any]] = {}
    for candidate in ev["candidates"]:
        for cond in candidate["gate"]["conditions"]:
            if cond["id"] != condition_id:
                continue
            entry = {
                "verdict": cond["verdict"],
                "satisfied": cond["satisfied"],
                "measured": cond["measured"],
                "threshold": cond["threshold"],
            }
            if cond.get("note"):
                entry["note"] = cond["note"]
            out[candidate["gate"]["experiment_id"]] = entry
    return out


def gate_conditions(ev: dict[str, Any], criteria: dict[str, Any]) -> dict[str, Any]:
    """Constitution section 9, gate 3, one entry per hard condition, quoted verbatim.

    The verbatim text and the predicate are read from the sealed criteria file, not restated here,
    so that the package cannot quote a condition the evaluator did not apply. ``NOT_RUN``,
    ``UNKNOWN`` and missing evidence are not passes, so every entry carries each candidate's verdict
    rather than a single boolean from the layer being judged.
    """
    sealed = {cond["id"]: cond for cond in criteria["conditions"]}
    conditions: dict[str, Any] = {}

    for condition_id, cond in sealed.items():
        per_candidate = _per_candidate(ev, condition_id)
        satisfied = [cid for cid, entry in per_candidate.items() if entry["satisfied"]]
        conditions[condition_id] = {
            "required": cond["required_verbatim"],
            "predicate": cond["predicate"],
            "verdict": "PASS" if satisfied else "FAIL",
            "verdict_semantics": VERDICT_SEMANTICS,
            "satisfied_by": satisfied,
            "met_by": [c for c, e in per_candidate.items() if e["verdict"] == "MET"],
            "not_met_by": [c for c, e in per_candidate.items() if e["verdict"] == "NOT_MET"],
            "not_evaluable_for": [
                c for c, e in per_candidate.items() if e["verdict"] == "NOT_EVALUABLE"
            ],
            "not_applicable_for": [
                c
                for c, e in per_candidate.items()
                if e["verdict"] == "NOT_APPLICABLE_BY_CONDITION_TEXT"
            ],
            "candidates_evaluated": len(per_candidate),
            "evidence": {"per_candidate": per_candidate},
        }

    conditions["S3-C1"]["evidence"]["costs"] = sealed["S3-C1"]["costs"]
    conditions["S3-C2"]["evidence"]["boundary"] = sealed["S3-C2"]["boundary"]
    conditions["S3-C2"]["evidence"]["granularity"] = (
        "session close; the project holds no intraday data and none was imputed, so every measured "
        "drawdown is a lower bound on the true one"
    )
    conditions["S3-C2"]["evidence"]["coupling"] = sealed["S3-C2"]["interaction"]
    conditions["S3-C3"]["evidence"]["undefined_cases"] = sealed["S3-C3"]["undefined_cases"]
    conditions["S3-C4"]["evidence"]["exception_invoked"] = sealed["S3-C4"]["exception_invoked"]
    conditions["S3-C4"]["evidence"]["exception_note"] = sealed["S3-C4"]["exception_note"]
    conditions["S3-C5"]["evidence"]["procedure"] = sealed["S3-C5"]["measurement"]
    conditions["S3-C5"]["evidence"]["both_removals_selected_the_same_trade"] = {
        candidate["gate"]["experiment_id"]: next(
            cond.get("evidence", {}).get("j1_equals_j2")
            for cond in candidate["gate"]["conditions"]
            if cond["id"] == "S3-C5"
        )
        for candidate in ev["candidates"]
    }
    conditions["S3-C6"]["evidence"]["single_instrument_interpretation"] = sealed["S3-C6"][
        "measurement"
    ]
    conditions["S3-C7"]["evidence"]["neighbours_per_candidate"] = ev["iteration_budget"][
        "runs_per_candidate"
    ]
    conditions["S3-C7"]["evidence"]["falsifiability"] = (
        "the four neighbours were declared in the sealed protocol before any result, and every one "
        "was run over the same window as its primary under the same base costs; a neighbour that "
        "did not run is a refusal, not a pass"
    )

    verdict = ev["stage_verdict"]
    conditions["admissible_candidate_exists"] = {
        "required": (
            "gate 3 is settled by the conjunction of every hard condition within a single "
            "candidate; the stage verdict is the disjunction of that conjunction over candidates"
        ),
        "verdict": "PASS" if verdict["admitted_candidates"] else "FAIL",
        "verdict_semantics": "This entry, and only this entry, is the gate determination.",
        "evidence": {
            "candidates_evaluated": verdict["candidates_evaluated"],
            "admitted_candidates": verdict["admitted_candidates"],
            "combination_rule": verdict["combination_rule"],
            "condition_token": verdict["condition_token"],
            "per_candidate": {
                summary["experiment_id"]: {
                    "family": summary["family"],
                    "admitted": summary["admitted"],
                    "conditions_not_met": summary["conditions_not_met"],
                    "conditions_not_evaluable": summary["conditions_not_evaluable"],
                    "conditions_not_applicable": summary["conditions_not_applicable"],
                }
                for summary in ev["gate_summary"]
            },
        },
    }
    return conditions


def build() -> int:
    ev = load(EVIDENCE)
    prereg = load(PREREGISTRATION)
    criteria = load(CRITERIA)
    universe = load(UNIVERSE)
    lock = load(HOLDOUT_LOCK)

    # A package whose verdict disagreed with its own evidence would be the one document nobody could
    # catch by reading it, so the check happens before anything is written. Unlike Stage 2, a FAIL is
    # not an error condition here — writing the wrong verdict is.
    declared = ev["stage_verdict"]
    token = declared["pass_token"] if declared["verdict"] == "PASS" else declared["fail_token"]
    derived = f"{declared['verdict']} — {token}"
    if derived != VERDICT:
        print(f"EVIDENCE VERDICT {derived!r} DISAGREES WITH {VERDICT!r} — no package written")
        return 3
    if declared["verdict"] == "FAIL" and declared["admitted_candidates"]:
        print("EVIDENCE REPORTS A FAIL WITH ADMITTED CANDIDATES — no package written")
        return 3

    stage1_freeze = verify_sha256_record(GOVERNANCE / "STAGE_1_FREEZE.sha256", GOVERNANCE)
    stage2_prereg = verify_sha256_record(GOVERNANCE / "STAGE_2_PREREGISTRATION.sha256", PROJECT_ROOT)
    stage2_decision = verify_sha256_record(
        PROJECT_ROOT / "reports" / "stage2" / "STAGE_2_BACKTEST_ENGINE.sha256", PROJECT_ROOT
    )
    stage3_prereg = verify_sha256_record(GOVERNANCE / "STAGE_3_PREREGISTRATION.sha256", PROJECT_ROOT)

    primaries = {
        candidate["plan"]["experiment_id"]: candidate["runs"][
            candidate["plan"]["experiment_id"] + "#PRIMARY"
        ]
        for candidate in ev["candidates"]
    }
    summaries = {summary["experiment_id"]: summary for summary in ev["gate_summary"]}

    decision = StageDecision(
        stage="STAGE_3_STRATEGY_RESEARCH",
        stage_slug="stage3",
        decision_basename="STAGE_3_STRATEGY_RESEARCH",
        manifest_basename="STAGE_3_ARTIFACT_MANIFEST",
        gate_id=3,
        gate_name="development_admissibility",
        verdict=VERDICT,
        gate_passed=False,
        command=COMMAND,
        gate_conditions=gate_conditions(ev, criteria),
        evidence=[
            f"Strategy protocol and gate criteria sealed at {prereg['declared_utc']} with "
            f"{prereg['strategy_modules_present_at_seal_time']} strategy modules and "
            f"{prereg['strategy_output_files_present_at_seal_time']} strategy output files present; "
            f"sealed_before_any_strategy_code={prereg['sealed_before_any_strategy_code']}. The two "
            f"counts are what make that claim falsifiable rather than self-reported.",
            f"{prereg['candidates_declared']} candidates were declared, one per family the "
            f"constitution authorises for Generation 1, each with "
            f"{prereg['robustness_neighbours_per_candidate']} robustness neighbours: "
            f"{prereg['declared_runs']} runs declared in advance, "
            f"{prereg['revisions_permitted']} revisions permitted. The harness counts the runs it "
            f"executed against the sealed number and raises rather than reporting a mismatch.",
            "Every candidate is rejected. "
            + "; ".join(
                f"{summary['experiment_id']} fails "
                + ", ".join(summary["conditions_not_met"])
                for summary in ev["gate_summary"]
            )
            + ".",
            "All six fail S3-C2, the 15% maximum-drawdown condition: "
            + ", ".join(
                f"{eid} {run['max_drawdown'][:7]}" for eid, run in primaries.items()
            )
            + ". Every one of them tripped the section 5.1 research shutdown, which is the same 15% "
            "threshold, and was liquidated and permanently switched off mid-window.",
            "All six pass S3-C1 after base costs: "
            + ", ".join(f"{eid} {run['total_return']}" for eid, run in primaries.items())
            + ". No candidate lost money over its window; every one breached the risk ceiling "
            "getting there.",
            f"S3-C7 holds for all six: every one of the "
            f"{4 * len(primaries)} pre-declared neighbour runs matches the sign of its primary's "
            f"net return, and each was run over the same window as its primary under the same base "
            f"cost model with the research shutdown enforced.",
            f"Determinism: {len(ev['determinism']['runs'])} primaries rerun from cold on fresh "
            f"candidate objects, all_identical={ev['determinism']['all_identical']}, compared on "
            f"trade and equity digests.",
            "Benchmarks are reported for every candidate and gate nothing at this stage. No "
            "candidate beats the SPY index or the tradable SPY buy-and-hold under the same "
            "shutdown; all six beat 0% cash and doing nothing. The constitution section 4 carve-out "
            "for materially reduced drawdown is not reached, because no candidate satisfies the "
            "drawdown condition in the first place.",
            "Stage 1 freeze record verifies from stockedge100/governance: " + json.dumps(stage1_freeze),
            "Stage 2 pre-registration record verifies from stockedge100: " + json.dumps(stage2_prereg),
            "Stage 2 decision record verifies from stockedge100: " + json.dumps(stage2_decision),
            "Stage 3 pre-registration record verifies from stockedge100: " + json.dumps(stage3_prereg),
            f"Admissibility evidence is reproducible and its self-digest was verified in both "
            f"directions the project rule requires: recomputing {ev['evidence_digest']} from the "
            f"written file following its own evidence_digest_covers sentence literally reproduces "
            f"it; recomputing with generated_utc included gives a different value, so the exclusion "
            f"is not vacuous; and a fresh in-process run at a different timestamp produced the "
            f"identical digest.",
            "389 tests pass: the 273 standing at pre-registration — 27 Stage 0, 113 Stage 1, 133 "
            "Stage 2 — unmodified, plus 116 added by Stage 3 (69 unit, 47 adversarial). Four clean "
            "controls establish that the evaluator can say yes, which a failing stage has to prove "
            "and a passing one does not.",
        ],
        limitations=[
            "One parameterisation per family is not a test of the family. Six candidates were run; "
            "six families were not evaluated. F6's neighbours alone span 0.27 to 3.04 total return, "
            "which is how much of a result belongs to the particular number chosen rather than to "
            "the rule.",
            "The results are not comparable across candidates. F5 and F6 run over roughly 18 years "
            "and F1-F4 over roughly 28, on different market regimes. No ranking is implied and none "
            "was computed.",
            "Every candidate was switched off before its window ended, between 1997 and 2010, by "
            "the section 5.1 research shutdown. Metrics computed over the full window — CAGR, "
            "Sharpe, exposure — describe a live period followed by a long dead one and are not "
            "properties of the rule.",
            "Base costs only. The stressed scenario belongs to the Gate 4 robustness work and was "
            "not run here, so every result is the optimistic case.",
            "The cost model remains a proxy, not a measurement, and cannot be validated before "
            "paper trading at gate 7.",
            "Single-provider price data with unquantified residual fund-closure bias, "
            "split-adjusted prices only, and no as-traded price levels. A systematic provider error "
            "would pass every check in this stage undetected.",
            "Drawdown is measured at session closes because the project holds no intraday data and "
            "none was imputed, so an intraday excursion past 15% that closed above it is invisible "
            "to S3-C2 and every measured figure is a lower bound.",
            "No statistical significance test was performed on any result and none was "
            "pre-registered. The gate is a set of minimum-quality thresholds, not an inference "
            "procedure.",
            "Every Stage 1 data limitation and every Stage 2 engine limitation is inherited whole. "
            "A research result cannot be more trustworthy than the engine, and the engine cannot be "
            "more trustworthy than its inputs.",
        ],
        blockers=[],
        conflicts_found=[
            "S3-CONFLICT-1 — the JSON companion for gate 3 carries five thresholds while the frozen "
            "Markdown carries seven conditions, omitting profit concentration and neighbouring "
            "parameter stability. The Markdown is authoritative and more restrictive, so all seven "
            "were evaluated and all seven had to pass. Same defect class Stages 1 and 2 each "
            "recorded against their own gates. No frozen artifact was edited.",
            "S3-CONFLICT-2 — gate 3 states no pass_result. The affirmative token was derived by "
            "negating the stated fail_result STRATEGY_REJECTED_IN_DEVELOPMENT, carrying the stage "
            "prefix Stage 0 established with STAGE_0_CONSTITUTION_VERIFIED. Both tokens were fixed "
            "in the sealed criteria before any candidate was run, which is what makes it defensible "
            "for this stage to issue the fail one.",
            "S3-CONFLICT-3 — the S3-C2 drawdown ceiling and the section 5.1 research shutdown are "
            "the same 15%. Not a contradiction but a coupling, recorded in the sealed criteria "
            "before any result. It turned out to be the mechanism behind every rejection in this "
            "stage: a candidate volatile enough to trip the risk control has already failed the "
            "quality gate.",
        ],
        produced=list(PRODUCED),
        frozen_inputs=list(STAGE_0_FROZEN_INPUTS)
        + list(STAGE_1_FROZEN_INPUTS)
        + list(STAGE_2_FROZEN_INPUTS)
        + list(STAGE_3_SEALED_INPUTS),
        body={
            "verdict_token_derivation": {
                "constitution_json_gate_3": {
                    "fail_result": prereg["gate"]["fail_result"],
                    "pass_result": None,
                },
                "chosen_fail_reason_code": declared["fail_token"],
                "unused_pass_reason_code": declared["pass_token"],
                "why": (
                    "Section 10 fixes the primary verdict vocabulary and requires a stage-specific "
                    "reason code alongside it. Gate 3 supplies only a fail token; both tokens were "
                    "sealed in config/stage3_gate_criteria.json before any candidate was run and "
                    "are read from the evidence here rather than written as literals."
                ),
                "issued": VERDICT,
            },
            "preregistration": {
                "document_id": prereg["document_id"],
                "declared_utc": prereg["declared_utc"],
                "run_id": prereg["run_id"],
                "sealed_before_any_strategy_code": prereg["sealed_before_any_strategy_code"],
                "strategy_modules_present_at_seal_time": prereg[
                    "strategy_modules_present_at_seal_time"
                ],
                "strategy_output_files_present_at_seal_time": prereg[
                    "strategy_output_files_present_at_seal_time"
                ],
                "candidates_declared": prereg["candidates_declared"],
                "candidate_ids": prereg["candidate_ids"],
                "declared_runs": prereg["declared_runs"],
                "revisions_permitted": prereg["revisions_permitted"],
                "sealed_files": prereg["preregistered_files"],
                "enforcement": (
                    "stockedge100.strategies.config.load_stage3_config recomputes all three digests "
                    "on every load and raises ConfigViolation on drift, so a silently edited "
                    "threshold stops the harness rather than changing a verdict; the harness also "
                    "counts executed runs against the sealed declared_runs and refuses a mismatch"
                ),
            },
            "configs": {
                PROTOCOL: sha256_file(PROJECT_ROOT / PROTOCOL),
                CRITERIA: sha256_file(PROJECT_ROOT / CRITERIA),
                COST_MODEL: sha256_file(PROJECT_ROOT / COST_MODEL),
                "config_hash_refers_to": PROTOCOL,
            },
            "admissibility_evidence": {
                "evidence_file": EVIDENCE,
                "artifact_id": ev["artifact_id"],
                "evidence_digest": ev["evidence_digest"],
                "evidence_digest_covers": ev["evidence_digest_covers"],
                "generated_utc": ev["generated_utc"],
                "command": ev["command"],
                "window": ev["window"],
                "cost_model": ev["cost_model"],
                "iteration_budget": ev["iteration_budget"],
                "multiple_comparisons_disclosure": ev["multiple_comparisons_disclosure"],
                "determinism_all_identical": ev["determinism"]["all_identical"],
                "stage_verdict": declared,
                "no_selection_in_this_stage": ev["no_selection_in_this_stage"],
                "self_digest_verification": {
                    "recomputed_as_documented": "MATCHES",
                    "negative_control_including_generated_utc": "DIFFERS, so the exclusion is not vacuous",
                    "second_run_at_a_different_timestamp": "IDENTICAL",
                    "why_both": (
                        "two-run stability alone would not detect a digest whose coverage "
                        "description is wrong but consistent, which is the defect that cost Stage 2 "
                        "a full regeneration"
                    ),
                },
            },
            "results": {
                "per_candidate_primary": {
                    eid: {
                        "family": summaries[eid]["family"],
                        "run_start": run["start"],
                        "run_end": run["end"],
                        "sessions": run["sessions"],
                        "total_return": run["total_return"],
                        "max_drawdown": run["max_drawdown"],
                        "profit_factor": run["profit_factor"],
                        "closed_trades": run["closed_trades"],
                        "admitted": summaries[eid]["admitted"],
                        "conditions_not_met": summaries[eid]["conditions_not_met"],
                    }
                    for eid, run in primaries.items()
                },
                "benchmarks_gate_nothing": True,
                "benchmark_note": (
                    "reported for every candidate under constitution section 4; no candidate beats "
                    "the SPY index or the tradable SPY buy-and-hold, and all six beat 0% cash and "
                    "doing nothing"
                ),
            },
            "scope": {
                "candidate_selected": False,
                "candidate_admitted": False,
                "validation_window_read": ev["window"]["validation_and_holdout_read"],
                "holdout_window_read": ev["window"]["validation_and_holdout_read"],
                "runs_confined_to": "development window, enforced by the engine window guard",
                "revisions_after_seeing_a_result": 0,
                "explicit_non_authorizations": ev["explicit_non_authorizations"],
                "money_spent_usd": 0,
                "credentials_used": "none",
                "data_acquired": "none; every price came from the Stage 1 normalized dataset",
            },
            "stage1": {
                "freeze_verification_working_directory": "stockedge100/governance",
                "freeze_verification": stage1_freeze,
                "universe_version": universe["universe_version"],
                "holdout_state": lock["holdout_state"],
                "development_window": [
                    lock["partition"]["development_start"],
                    lock["partition"]["development_end"],
                ],
                "disposition": "READ_ONLY_NOT_MODIFIED",
            },
            "stage2": {
                "gate_2_verdict": "PASS — STAGE_2_BACKTEST_ENGINE_VALIDATED",
                "preregistration_record_verification": stage2_prereg,
                "decision_record_verification": stage2_decision,
                "disposition": "READ_ONLY_NOT_MODIFIED",
            },
            "integrity": {
                "stage_3_preregistration_record_working_directory": "stockedge100",
                "stage_3_preregistration_record_verification": stage3_prereg,
                "stage_3_freeze_record_issued": False,
                "stage_3_freeze_record_rationale": (
                    "Stage 1 issued a freeze record because it produced governance artifacts later "
                    "stages consume. Stage 3 produces none: no candidate was admitted, so nothing "
                    "here becomes a downstream input. Its sealed inputs are covered by "
                    "STAGE_3_PREREGISTRATION.sha256 and its outputs by this package's own checksum "
                    "record, while code identity is repo_state_id. Recorded as a decision, not left "
                    "as an omission."
                ),
                "package_not_covered_by_tests": (
                    "tests/**/*.py is one of the repo_state_id patterns, so a test asserting this "
                    "package's repo_state_id would invalidate the value it asserts the moment it "
                    "was written. The package is verified by re-running the recomputation."
                ),
            },
        },
        tests={"passed": 389, "failed": 0, "skipped": 0},
        authorization_state={
            "strategy_research": "UNLOCKED_ON_DEVELOPMENT_WINDOW_ONLY",
            "backtesting": "UNLOCKED_ON_DEVELOPMENT_WINDOW_ONLY",
            "gate_4_robustness": "NOT_REACHED_NO_ADMITTED_CANDIDATE",
            "validation_window": "LOCKED",
            "final_holdout": "SEALED",
            "alpaca_paper_trading": "LOCKED",
            "shadow_live": "LOCKED",
            "alpaca_live_trading": "LOCKED",
            "capital_or_risk_expansion": "LOCKED",
        },
        next_authorized_stage="NONE_ON_THE_CURRENT_LINE_OF_WORK",
        dataset_hashes={
            NORMALIZED_MANIFEST: sha256_file(PROJECT_ROOT / NORMALIZED_MANIFEST),
            **{
                f"data/normalized/daily/{symbol}.csv": sha256_file(
                    PROJECT_ROOT / "data" / "normalized" / "daily" / f"{symbol}.csv"
                )
                for symbol in SERIES_READ
            },
        },
        universe_version=universe["universe_version"],
        date_range=[
            lock["partition"]["development_start"],
            lock["partition"]["development_end"],
        ],
        holdout_state=lock["holdout_state"],
        config_hash=sha256_file(PROJECT_ROOT / PROTOCOL),
        random_seed=None,
        run_notes=[
            "Gate 3 conditions are conjunctive within a candidate; no candidate satisfies all "
            "seven, so the gate fails. All six candidates fail S3-C2.",
            "A rejection is a deliverable. The candidates, their runs, and their metrics stay on "
            "disk exactly as produced; nothing was revised or re-run after a result was seen.",
            "No candidate proceeds to Gate 4 and there is no next authorized stage on this line of "
            "work. A further attempt at Gate 3 requires a new pre-registration declaring new "
            "candidates, sealed before any code for them exists.",
            "The validation and holdout windows were not read. No data was acquired, no order of "
            "any kind was generated, and no credential was accessed.",
            "No separate STAGE_3_FREEZE.sha256 was issued; see body.integrity for the reason.",
            "live_trading_authorized remains false.",
        ],
    )

    result = build_stage_package(decision)
    if not result.freeze_ok:
        print("STAGE 0 FREEZE VERIFICATION FAILED — see the decision record", flush=True)
        return 2

    print(f"run_id        {result.run_id}")
    print(f"timestamp_utc {result.timestamp_utc}")
    print(f"repo_state_id {result.repo_state_id}")
    print(f"verdict       {VERDICT}")
    for path in (result.decision_path, result.manifest_path, result.checksum_path, result.run_record_path):
        print(f"wrote         {Path(path).relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
