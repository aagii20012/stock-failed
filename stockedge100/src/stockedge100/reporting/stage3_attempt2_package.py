"""Stage 3 Attempt 2 design-session decision package — a seal, not a gate 3 determination.

This module records what a *design* session produced: a prospective, sealed pre-registration for a
second gate 3 attempt. It evaluates nothing about any candidate's behaviour, because no candidate has
been implemented. Everything mechanical — timestamp, run id, ``repo_state_id``, manifest, checksum
record, run record — comes from :mod:`stockedge100.reporting.stage_package`.

Three things distinguish it from :mod:`stockedge100.reporting.stage3_package`.

**The conditions are seal conditions, not gate conditions.** ``A2D-C1`` … ``A2D-C9`` are the
conditions for a legitimate seal, and they are recomputed here from the artifacts rather than read
out of an evidence file, because a design session has no evidence file: the artifacts *are* the
evidence. The gate 3 determination is carried as a separate ``gate_3_admissible_candidate_exists``
entry whose verdict is ``NOT_RUN``, so this package cannot be misread as a gate 3 result. Its rule is
quoted from the sealed binding rather than restated.

**The guard is the portable one.** Stage 2's builder refuses to write unless every condition is met,
which would suppress the deliverable if a design session legitimately turned out not to be sealable.
The guard in :func:`build` instead requires the verdict written into the package to be the verdict
the conditions reached — a package that disagreed with its own conditions is the one document nobody
could catch by reading it. A ``BLOCKED`` outcome stays writable.

**The verdict token is neither gate 3 token.** ``config/stage3_gate_criteria.json`` derives
``STAGE_3_STRATEGY_ADMITTED_IN_DEVELOPMENT`` and ``STAGE_3_STRATEGY_REJECTED_IN_DEVELOPMENT``. This
session may issue neither: it did not run a candidate, so it can neither admit nor reject one. The
tokens are read from the sealed derivation and asserted to differ from this session's, rather than
this claim being left as prose.

``gate_passed`` is ``False`` and therefore the shared builder derives ``exit_status`` of
``GATE_NOT_PASSED`` for the ``runs/`` record. That is correct and is recorded in the run notes: gate 3
is not passed by sealing a design for it.

Usage::

    cd stockedge100 && PYTHONPATH=src python -m stockedge100.reporting.stage3_attempt2_package
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from stockedge100.audit import sha256_file
from stockedge100.reporting.stage_package import (
    GOVERNANCE,
    PROJECT_ROOT,
    STAGE_0_FROZEN_INPUTS,
    StageDecision,
    build_stage_package,
    repo_state,
    verify_sha256_record,
    verify_stage0_freeze,
)

COMMAND = (
    "cd stockedge100 && PYTHONPATH=src python -m stockedge100.reporting.stage3_attempt2_package"
)

PASS_VERDICT = "PASS — STAGE_3_ATTEMPT_2_PREREGISTRATION_FROZEN"
NOT_SEALABLE_VERDICT = "BLOCKED — STAGE_3_ATTEMPT_2_PREREGISTRATION_NOT_SEALABLE"
GATE_PASSED = False

SEAL = "governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.json"
PREREG_MD = "governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.md"
PREREG_RECORD = "governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.sha256"
PROTOCOL = "config/stage3_attempt2_strategy_protocol.json"
BINDING = "config/stage3_attempt2_gate_criteria_binding.json"
CRITERIA = "config/stage3_gate_criteria.json"
DESIGN_REPORT = "governance/STAGE_3_ATTEMPT_2_DESIGN_REPORT.md"
HOLDOUT_LOCK = "governance/STAGE_1_HOLDOUT_LOCK.json"
UNIVERSE = "governance/STAGE_1_UNIVERSE.json"
ATTEMPT_1_RUN = "runs/SE100-R-20260810T101622Z.json"

# (record, working directory the record's paths are relative to, entry count the design report
# claims). Recording expected against actual makes a drift in either the record or the report
# visible instead of silently agreeing with whichever was written last.
CHECKSUM_RECORDS = (
    ("governance/STAGE_0_FREEZE.sha256", "governance", 2),
    ("governance/STAGE_1_FREEZE.sha256", "governance", 2),
    ("governance/STAGE_1_PREREGISTRATION.sha256", "root", 4),
    ("governance/STAGE_2_PREREGISTRATION.sha256", "root", 4),
    ("governance/STAGE_3_PREREGISTRATION.sha256", "root", 4),
    ("reports/stage0/STAGE_0_VERIFICATION.sha256", "root", 8),
    ("reports/stage1/STAGE_1_DATA_READINESS.sha256", "root", 19),
    ("reports/stage2/STAGE_2_BACKTEST_ENGINE.sha256", "root", 20),
    ("reports/stage3/STAGE_3_STRATEGY_RESEARCH.sha256", "root", 26),
    (PREREG_RECORD, "root", 4),
)

STAGE_1_FROZEN_INPUTS = (
    "governance/STAGE_1_DATA_FOUNDATION_REPORT.md",
    UNIVERSE,
    HOLDOUT_LOCK,
    "governance/STAGE_1_FREEZE.sha256",
    "governance/STAGE_1_PREREGISTRATION.json",
    "governance/STAGE_1_PREREGISTRATION.sha256",
)

STAGE_2_FROZEN_INPUTS = (
    "governance/STAGE_2_BACKTEST_ENGINE_REPORT.md",
    "governance/STAGE_2_PREREGISTRATION.md",
    "governance/STAGE_2_PREREGISTRATION.json",
    "governance/STAGE_2_PREREGISTRATION.sha256",
    "config/stage2_cost_model.json",
    "config/stage2_engine_spec.json",
)

# Attempt 1 is closed. Its pre-registration, its protocol, its criteria and its research report are
# read-only inputs here: the criteria file is adopted unchanged by Attempt 2, and the report is the
# source of the prior evidence Attempt 2 discloses knowing.
ATTEMPT_1_FROZEN_INPUTS = (
    "governance/STAGE_3_PREREGISTRATION.md",
    "governance/STAGE_3_PREREGISTRATION.json",
    "governance/STAGE_3_PREREGISTRATION.sha256",
    "config/stage3_strategy_protocol.json",
    CRITERIA,
    "governance/STAGE_3_STRATEGY_RESEARCH_REPORT.md",
)

# Sealed by this session, before any Attempt 2 strategy module existed. Inputs to the package, not
# outputs of it: they were written and hashed before the builder ran and are not touched by it.
ATTEMPT_2_SEALED_INPUTS = (PREREG_MD, SEAL, PREREG_RECORD, PROTOCOL, BINDING)

PRODUCED = (
    DESIGN_REPORT,
    "reports/stage3_attempt2/STAGE_3_ATTEMPT_2_DESIGN.json",
    "reports/stage3_attempt2/STAGE_3_ATTEMPT_2_ARTIFACT_MANIFEST.json",
    "reports/stage3_attempt2/STAGE_3_ATTEMPT_2_TEST_SUMMARY.md",
    "reports/stage3_attempt2/pytest_stage3_attempt2_output.txt",
)

# Must stay identical to REQUIRED_CANDIDATE_FIELDS in
# tests/unit/test_stage3_attempt2_preregistration.py. Every field a later implementation session must
# not be free to choose on an observed result. A candidate may declare more; it may not declare fewer.
REQUIRED_CANDIDATE_FIELDS = (
    "experiment_id",
    "family",
    "family_authorised_by",
    "hypothesis",
    "economic_rationale",
    "distinction_from_attempt_1",
    "required_inputs",
    "universe",
    "exclusions",
    "eligibility_rules",
    "warmup_sessions",
    "signal_timing",
    "primary_parameters",
    "entry_rule",
    "exit_rule",
    "maximum_holding_period",
    "position_sizing_rule",
    "maximum_exposure",
    "cash_allocation_rule",
    "stop_or_shutdown_rule",
    "reentry_rule_after_a_stop",
    "conflict_rule",
    "permitted_parameter_grid",
    "robustness_neighbours",
    "max_variants",
    "primary_metric",
    "secondary_metrics",
    "gate_3_conditions_applied",
    "rejection_conditions",
    "not_evaluable_conditions",
    "retrospective_change_prohibited",
)

# Values that must appear in both the pre-registration Markdown and its JSON seal for the two to
# materially agree. Deliberately excluded: declared_utc, "LOCKED", and every digest — the Markdown is
# written before the seal exists and cannot quote values the seal computes over it.
AGREEMENT_TOKENS = ("SE100-S3-A2", "0.15", "SEALED", "RA1", "SE100-GOV-0007")

VERDICT_SEMANTICS = (
    "MET here is a statement about the seal, not about any candidate's behaviour. No condition in "
    "this table measures a return, a drawdown, a trade count or an equity value, because none exists "
    "for any Attempt 2 candidate. The gate 3 determination is the separate "
    "gate_3_admissible_candidate_exists entry, whose verdict is NOT_RUN."
)

# Copied from section 18 of governance/STAGE_3_ATTEMPT_2_DESIGN_REPORT.md so the two can be diffed.
REQUIREMENTS = {
    "A2D-C1": (
        "Stage 0 freeze (both halves), Stage 1 freeze, and the Stage 1/2/3 pre-registration and "
        "decision checksum records all verify from their intended working directories before any "
        "artifact is authored"
    ),
    "A2D-C2": (
        "Frozen on-disk governance permits a further gate 3 attempt by new pre-registration, with "
        "the determination resting on quoted frozen text and not on the operating prompt"
    ),
    "A2D-C3": (
        "All four contamination predicates read 0 at sealing and Attempt 1's records verify; each "
        "predicate is tested in both directions and wired to refusal"
    ),
    "A2D-C4": (
        "Criteria adopted by digest, 7 conditions, ceiling 0.15 unchanged, conjunction logic "
        "unchanged; two re-derivations apply sealed rules to a new candidate set and change no "
        "threshold, predicate, measurement, or token"
    ),
    "A2D-C5": (
        "Ten-item disclosure recorded, each item asserted individually through eleven required "
        "substrings; cumulative count 9 candidates / 45 gating variants / 48 runs; no result may be "
        "called independent confirmation because its code is new"
    ),
    "A2D-C6": (
        "3 candidates, each carrying all 31 required fields (39, 39, 41 declared); attempt-level "
        "content complete; grid invariant holds; no discretionary choice is left to an "
        "implementation session"
    ),
    "A2D-C7": (
        "Checksum record verifies 4/4 from the project root; MD and JSON materially agree; "
        "serialisation deterministic and all three JSON artifacts ASCII-only in fact; manifest "
        "self-reference policy followed; no tree digest written inside a covered file"
    ),
    "A2D-C8": (
        "Development window only authorised; validation LOCKED; holdout SEALED; enforcement "
        "structural through ResearchWindow / MarketView; no boundary changed"
    ),
    "A2D-C9": (
        "460 collected, up from 389; targeted selection 115 passed / 0 failed / 0 skipped; 11 of 11 "
        "recorded test-file digests unchanged; nothing weakened, skipped, xfailed, or deleted"
    ),
}

HEX64 = re.compile(r"\b[0-9a-f]{64}\b")


def load(rel: str) -> dict[str, Any]:
    return json.loads((PROJECT_ROOT / rel).read_text(encoding="utf-8"))


def read_text(rel: str) -> str:
    return (PROJECT_ROOT / rel).read_text(encoding="utf-8")


def _condition(condition_id: str, met: bool, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "required": REQUIREMENTS[condition_id],
        "verdict": "MET" if met else "NOT_MET",
        "verdict_semantics": VERDICT_SEMANTICS,
        "evidence": evidence,
    }


def _c1_frozen_governance() -> dict[str, Any]:
    """Every upstream checksum record, verified from the directory its paths are relative to."""
    freeze_ok, freeze_detail = verify_stage0_freeze()
    records: dict[str, Any] = {}
    all_ok = freeze_ok
    for rel, where, expected_entries in CHECKSUM_RECORDS:
        root = GOVERNANCE if where == "governance" else PROJECT_ROOT
        results = verify_sha256_record(PROJECT_ROOT / rel, root)
        statuses = sorted(set(results.values()))
        ok = statuses == ["OK"]
        all_ok = all_ok and ok and len(results) == expected_entries
        records[rel] = {
            "verify_from": "stockedge100/governance" if where == "governance" else "stockedge100",
            "entries": len(results),
            "entries_expected": expected_entries,
            "statuses": statuses,
            "all_ok": ok,
        }
    return _condition(
        "A2D-C1",
        all_ok,
        {
            "records": records,
            "stage_0_freeze_verified": freeze_ok,
            "stage_0_freeze_detail": freeze_detail,
            "working_directory_note": (
                "records listing bare filenames verify from stockedge100/governance; records "
                "listing project-root-relative paths verify from stockedge100. A mismatch reported "
                "from the other directory is an operator error, not an integrity failure."
            ),
            "frozen_artifacts_modified": False,
        },
    )


def _c2_second_attempt_permitted(protocol: dict[str, Any]) -> dict[str, Any]:
    determination = protocol["authorization_determination"]
    answer = determination["answer"]
    met = answer.lstrip().startswith("Yes") and len(determination["evidence"]) >= 5
    return _condition(
        "A2D-C2",
        met,
        {
            "question": determination["question"],
            "answer": answer,
            "evidence_items": len(determination["evidence"]),
            "evidence": determination["evidence"],
            "not_relied_on": determination["not_relied_on"],
            "families_requirement": determination["families_requirement"],
            "determined_from": (
                "on-disk frozen governance, quoted; not from the operating prompt and not from any "
                "conversational claim"
            ),
        },
    )


def _c3_prospective(seal: dict[str, Any]) -> dict[str, Any]:
    predicates = seal["contamination_predicates"]
    counts = {
        key: predicates[key]
        for key in (
            "attempt_2_strategy_modules",
            "modules_naming_an_attempt_2_candidate",
            "attempt_2_report_artifacts",
            "attempt_2_run_records",
        )
    }
    met = (
        all(value == 0 for value in counts.values())
        and predicates["attempt_1_records_verify"] is True
        and seal["sealed_before_any_attempt_2_strategy_code"] is True
    )
    return _condition(
        "A2D-C3",
        met,
        {
            "counts_at_sealing": counts,
            "definitions": predicates["definitions"],
            "attempt_1_records_verify": predicates["attempt_1_records_verify"],
            "why_not_attempt_1_predicates": predicates["why_not_attempt_1_predicates"],
            "sealed_before_any_attempt_2_strategy_code": seal[
                "sealed_before_any_attempt_2_strategy_code"
            ],
            "sealed_utc": seal["declared_utc"],
            "movable_after_sealing": [
                "attempt_2_run_records becomes 1: the seal writes its own run record, whose stage "
                "token contains ATTEMPT_2 by construction",
                "attempt_2_report_artifacts becomes non-zero: this design session's test summary, "
                "pytest output, decision record, manifest and checksum record live under "
                "reports/stage3_attempt2/",
            ],
            "movable_note": (
                "both moves are anticipated in the sealed definitions, which say the counts must be "
                "0 at sealing. Neither file is strategy code and neither is a performance result."
            ),
        },
    )


def _c4_gate_3_unchanged(seal: dict[str, Any], criteria: dict[str, Any], binding: dict[str, Any]) -> dict[str, Any]:
    gate = seal["gate"]
    recomputed = sha256_file(PROJECT_ROOT / CRITERIA)
    drawdown = next(cond for cond in criteria["conditions"] if cond["id"] == "S3-C2")
    met = (
        recomputed == gate["criteria_sha256"]
        and gate["criteria_adoption"] == "ADOPTED_UNCHANGED"
        and gate["criteria_changed_for_attempt_2"] is False
        and gate["max_drawdown_ceiling"] == "0.15"
        and gate["max_drawdown_ceiling_changed"] is False
        and gate["conditions_evaluated"] == len(criteria["conditions"]) == 7
        and gate["within_candidate"] == "CONJUNCTIVE"
        and gate["across_candidates"] == "DISJUNCTIVE"
        and len(gate["rederivations"]) == 2
        and binding["drawdown_ceiling_is_unchanged"]["value"] == "0.15"
    )
    return _condition(
        "A2D-C4",
        met,
        {
            "criteria_source": gate["criteria_source"],
            "criteria_sha256_recorded": gate["criteria_sha256"],
            "criteria_sha256_recomputed": recomputed,
            "criteria_adoption": gate["criteria_adoption"],
            "criteria_changed_for_attempt_2": gate["criteria_changed_for_attempt_2"],
            "conditions_in_criteria_file": [cond["id"] for cond in criteria["conditions"]],
            "conditions_evaluated_declared": gate["conditions_evaluated"],
            "max_drawdown_ceiling": gate["max_drawdown_ceiling"],
            "max_drawdown_ceiling_changed": gate["max_drawdown_ceiling_changed"],
            "drawdown_condition_verbatim": drawdown["required_verbatim"],
            "drawdown_measurement": drawdown["measurement"],
            "drawdown_predicate": drawdown["predicate"],
            "drawdown_boundary": drawdown["boundary"],
            "drawdown_interaction": drawdown["interaction"],
            "within_candidate": gate["within_candidate"],
            "across_candidates": gate["across_candidates"],
            "admissible_candidates_required": gate["admissible_candidates_required"],
            "rederivations": gate["rederivations"],
            "rederivation_note": gate["rederivation_note"],
            "rederivation_detail": binding["rederivations"],
            "nothing_else_changed": binding["nothing_else_changed"],
            "drawdown_ceiling_is_unchanged": binding["drawdown_ceiling_is_unchanged"],
        },
    )


def _c5_adaptation_disclosed(protocol: dict[str, Any], seal: dict[str, Any]) -> dict[str, Any]:
    disclosure = protocol["adaptive_research_disclosure"]
    cumulative = seal["cumulative_experiment_count"]
    binding_number = str(cumulative["binding_number_for_interpretation"])
    split = protocol["cumulative_experiment_count"]
    met = (
        len(disclosure["items"]) == 10
        and cumulative["cumulative_candidates"] == 9
        and cumulative["cumulative_gating_variants"] == 45
        and cumulative["cumulative_total_runs"] == 48
        and split["attempt_1_candidates"] + split["attempt_2_candidates"]
        == cumulative["cumulative_candidates"]
        and split["attempt_1_gating_variants"] + split["attempt_2_gating_variants"]
        == cumulative["cumulative_gating_variants"]
        and split["attempt_1_total_runs"] + split["attempt_2_total_runs"]
        == cumulative["cumulative_total_runs"]
        and "9" in binding_number
        and "45" in binding_number
    )
    return _condition(
        "A2D-C5",
        met,
        {
            "disclosure_items": len(disclosure["items"]),
            "disclosure": disclosure,
            "cumulative_experiment_count": cumulative,
            "cumulative_experiment_count_full": protocol["cumulative_experiment_count"],
            "multiple_comparisons_disclosure": protocol["multiple_comparisons_disclosure"],
            "adaptation_is_prospective_with_respect_to_attempt_1": False,
            "adaptation_note": (
                "Attempt 1's results are known. The adaptation is disclosed rather than hidden "
                "behind new candidate identifiers: it is recorded in the disclosure items, in the "
                "cumulative count, in the family-exclusion reasoning, and in each candidate's "
                "distinction_from_attempt_1 block."
            ),
        },
    )


def _c6_specification_complete(protocol: dict[str, Any], seal: dict[str, Any]) -> dict[str, Any]:
    experiments = protocol["experiments"]
    per_candidate: dict[str, Any] = {}
    met = len(experiments) == seal["candidates_declared"] == 3
    for experiment in experiments:
        missing = [f for f in REQUIRED_CANDIDATE_FIELDS if not experiment.get(f)]
        grid = experiment["permitted_parameter_grid"]
        offending: list[str] = []
        for neighbour in experiment["robustness_neighbours"]:
            for key, value in neighbour.items():
                if key not in grid or value not in grid[key]:
                    offending.append(f"{key}={value!r}")
        per_candidate[experiment["experiment_id"]] = {
            "family": experiment["family"],
            "declared_fields": len(experiment),
            "required_fields_present": len(REQUIRED_CANDIDATE_FIELDS) - len(missing),
            "required_fields_missing": missing,
            "robustness_neighbours": len(experiment["robustness_neighbours"]),
            "max_variants": experiment["max_variants"],
            "grid_keys": sorted(grid),
            "neighbours_outside_the_grid": offending,
        }
        met = met and not missing and not offending
    attempt_level = [
        key
        for key in (
            "research_question",
            "known_prior_evidence",
            "adaptive_research_disclosure",
            "partitions",
            "iteration_budget",
            "cumulative_experiment_count",
            "multiple_comparisons_disclosure",
            "shared_rules",
            "risk_architecture",
            "primary_decision_rule",
            "secondary_metrics",
            "benchmarks",
            "cost_stress_treatment",
            "attempt_level_abandonment_rule",
            "missing_or_invalid_data_rule",
            "post_seal_defect_rule",
            "partial_or_failed_run_rule",
            "reproducibility_requirements",
            "no_retuning_rule",
            "stage_4_remains_prohibited_conditions",
            "explicit_non_authorizations",
        )
        if not protocol.get(key)
    ]
    met = met and not attempt_level
    return _condition(
        "A2D-C6",
        met,
        {
            "candidates_declared": seal["candidates_declared"],
            "candidate_ids": seal["candidate_ids"],
            "required_field_count": len(REQUIRED_CANDIDATE_FIELDS),
            "per_candidate": per_candidate,
            "attempt_level_keys_missing": attempt_level,
            "grid_invariant": protocol["permitted_parameter_grid_semantics"],
            "no_retuning_rule": protocol["no_retuning_rule"],
            "iteration_budget": protocol["iteration_budget"],
            "discretion_left_to_implementation": (
                "none on any parameter, threshold, lookback, symbol, sizing rule, risk rule, "
                "benchmark or neighbour: every one is a declared value in the sealed protocol"
            ),
        },
    )


def _c7_sealing_integrity(seal: dict[str, Any], repo_state_id: str) -> dict[str, Any]:
    record = verify_sha256_record(PROJECT_ROOT / PREREG_RECORD, PROJECT_ROOT)
    digests = {
        rel: {"recorded": entry["sha256"], "recomputed": sha256_file(PROJECT_ROOT / rel)}
        for rel, entry in seal["preregistered_files"].items()
    }
    prereg_md = read_text(PREREG_MD)
    agreement = {token: token in prereg_md for token in AGREEMENT_TOKENS}
    for candidate_id in seal["candidate_ids"]:
        agreement[candidate_id] = candidate_id in prereg_md
    for family in list(seal["families_retained"]) + list(seal["families_excluded"]):
        agreement[family] = family in prereg_md
    ascii_only = {rel: read_text(rel).isascii() for rel in (PROTOCOL, BINDING, SEAL)}
    tree_digest_in = {
        rel: (repo_state_id in read_text(rel)) for rel in (DESIGN_REPORT, PREREG_MD)
    }
    met = (
        sorted(set(record.values())) == ["OK"]
        and len(record) == 4
        and all(pair["recorded"] == pair["recomputed"] for pair in digests.values())
        and all(agreement.values())
        and all(ascii_only.values())
        and not any(tree_digest_in.values())
    )
    return _condition(
        "A2D-C7",
        met,
        {
            "checksum_record": {
                "path": PREREG_RECORD,
                "path_convention": seal["checksum_record"]["path_convention"],
                "verify_from": seal["checksum_record"]["verify_from"],
                "command": seal["checksum_record"]["command"],
                "entries": len(record),
                "results": record,
            },
            "preregistered_file_digests": digests,
            "markdown_json_agreement": agreement,
            "agreement_exclusions": (
                "declared_utc, the string LOCKED, and every digest are deliberately absent from the "
                "Markdown: it is written before the seal exists and cannot quote values the seal "
                "computes over it. It points at the JSON for them instead."
            ),
            "json_artifacts_ascii_only_in_fact": ascii_only,
            "ascii_note": (
                "measured with text.isascii(), not read off the declared encoding field. The "
                "pre-registration Markdown and this design report are UTF-8 and carry em dashes and "
                "section signs like every other governance document here; their digests are pinned, "
                "so their encoding cannot drift silently either."
            ),
            "tree_digest_written_into_a_covered_file": tree_digest_in,
            "self_reference_policy": (
                "nothing hashes itself: the artifact manifest excludes its own entry and the "
                "checksum record covers it instead; the pre-registration checksum record does not "
                "name itself; and no repo_state_id is written into any file the digest is computed "
                "over, which is why both governance Markdown documents are searched for the value "
                "rather than for the field name"
            ),
            "seal_is_unrepeatable": (
                "the sealing program returns exit 2 when its record already exists, so the seal "
                "cannot be silently rewritten"
            ),
        },
    )


def _c8_partitions_unchanged(seal: dict[str, Any], binding: dict[str, Any], lock: dict[str, Any]) -> dict[str, Any]:
    windows = binding["windows"]
    met = (
        seal["authorized_windows"] == ["development"]
        and windows["authorized"] == ["development"]
        and seal["validation_window_state"] == windows["validation"] == "LOCKED"
        and seal["holdout_window_state"] == windows["holdout"] == "SEALED"
        and lock["holdout_state"] == "SEALED"
        and lock["status"] == "LOCKED"
    )
    return _condition(
        "A2D-C8",
        met,
        {
            "authorized_windows": seal["authorized_windows"],
            "validation_window_state": seal["validation_window_state"],
            "holdout_window_state": seal["holdout_window_state"],
            "binding_windows": windows,
            "holdout_lock": {
                "path": HOLDOUT_LOCK,
                "artifact_id": lock["artifact_id"],
                "status": lock["status"],
                "holdout_state": lock["holdout_state"],
                "sha256": sha256_file(PROJECT_ROOT / HOLDOUT_LOCK),
                "binding_rules": lock["binding_rules"],
                "read_for": "integrity metadata only; no holdout observation was read",
                "boundary_dates_restated_in_any_attempt_2_artifact": False,
                "boundary_dates_note": (
                    "the lock has no separate validation-state field; the validation window's "
                    "LOCKED state rests on its binding rule that no parameter, threshold, symbol or "
                    "rule may be chosen using any value inside the validation or holdout windows. "
                    "Attempt 2 binds the lock by digest and reads the bounds at run time rather "
                    "than restating them, which is why date_range is null in this package."
                ),
            },
            "enforcement": windows["enforcement"],
            "unchanged_by_this_attempt": windows["unchanged_by_this_attempt"],
        },
    )


def _c9_test_floor(attempt_1_run: dict[str, Any]) -> dict[str, Any]:
    recorded = {
        path: digest
        for path, digest in attempt_1_run["code_hashes"].items()
        if path.startswith("tests/")
    }
    unchanged, changed, missing = [], [], []
    for path, digest in sorted(recorded.items()):
        target = PROJECT_ROOT / path
        if not target.is_file():
            missing.append(path)
        elif sha256_file(target) == digest:
            unchanged.append(path)
        else:
            changed.append(path)
    live = sorted(
        str(p.relative_to(PROJECT_ROOT)).replace("\\", "/")
        for p in PROJECT_ROOT.glob("tests/**/*.py")
    )
    added = [path for path in live if path not in recorded]
    met = (
        not changed
        and not missing
        and len(unchanged) == len(recorded) == 11
        and len(live) == 12
        and added == ["tests/unit/test_stage3_attempt2_preregistration.py"]
    )
    return _condition(
        "A2D-C9",
        met,
        {
            "collected_before": 389,
            "collected_now": 460,
            "selection_command": (
                "cd stockedge100 && python -m pytest tests/unit/test_stage0_governance.py "
                "tests/unit/test_stage1_preregistration.py "
                "tests/unit/test_stage3_attempt2_preregistration.py -q"
            ),
            "selection_result": {"passed": 115, "failed": 0, "skipped": 0},
            "new_file_alone": {"passed": 71, "failed": 0, "skipped": 0},
            "broad_command_not_run": (
                "python -m pytest tests -q was deliberately not run: two integration modules read "
                "the normalised dataset and drive the engine over it, which this session may not do"
            ),
            "recorded_test_files": len(recorded),
            "unchanged": unchanged,
            "changed": changed,
            "missing": missing,
            "live_test_files": len(live),
            "added_this_session": added,
            "unmodified_asserted_by": (
                "digest recomputation against Attempt 1's run record, not by a green run of the "
                "whole suite. A weakened or deleted test would appear here as changed or missing."
            ),
            "attempt_1_run_record": ATTEMPT_1_RUN,
            "nothing_weakened_skipped_xfailed_or_deleted": True,
        },
    )


def gate_conditions(
    seal: dict[str, Any],
    protocol: dict[str, Any],
    binding: dict[str, Any],
    criteria: dict[str, Any],
    lock: dict[str, Any],
    attempt_1_run: dict[str, Any],
    repo_state_id: str,
) -> dict[str, Any]:
    """The nine seal conditions, plus the gate 3 row that settles nothing because nothing was run."""
    conditions: dict[str, Any] = {
        "A2D-C1": _c1_frozen_governance(),
        "A2D-C2": _c2_second_attempt_permitted(protocol),
        "A2D-C3": _c3_prospective(seal),
        "A2D-C4": _c4_gate_3_unchanged(seal, criteria, binding),
        "A2D-C5": _c5_adaptation_disclosed(protocol, seal),
        "A2D-C6": _c6_specification_complete(protocol, seal),
        "A2D-C7": _c7_sealing_integrity(seal, repo_state_id),
        "A2D-C8": _c8_partitions_unchanged(seal, binding, lock),
        "A2D-C9": _c9_test_floor(attempt_1_run),
    }
    admissible = binding["admissible_candidate_exists"]
    conditions["gate_3_admissible_candidate_exists"] = {
        "required": admissible["frozen_rule"],
        "verdict": "NOT_RUN",
        "verdict_semantics": (
            "This entry, and only this entry, is the gate 3 determination. NOT_RUN is not a pass and "
            "is not a fail: no Attempt 2 candidate was implemented or evaluated, so the disjunction "
            "has no terms. This entry exists so that this package cannot be read as a gate 3 result."
        ),
        "evidence": {
            "candidates_implemented": 0,
            "candidates_evaluated": 0,
            "admitted_candidates": [],
            "satisfied_definition": admissible["satisfied_definition"],
            "not_satisfied_values": admissible["not_satisfied_values"],
            "admissible_candidates_required": seal["gate"]["admissible_candidates_required"],
            "neighbour_status": binding["neighbour_status"],
            "shutdown_behaviour": binding["shutdown_behaviour"],
            "rerun_policy": binding["rerun_policy"],
        },
    }
    return conditions


def build() -> int:
    seal = load(SEAL)
    protocol = load(PROTOCOL)
    binding = load(BINDING)
    criteria = load(CRITERIA)
    lock = load(HOLDOUT_LOCK)
    universe = load(UNIVERSE)
    attempt_1_run = load(ATTEMPT_1_RUN)

    # Computed before the build so that the "no tree digest inside a covered file" check runs against
    # the same value the build will record. The builder writes only into reports/ and runs/, neither
    # of which is a repo_state_id pattern, so the two values are the same by construction.
    _, repo_state_id = repo_state()

    conditions = gate_conditions(
        seal, protocol, binding, criteria, lock, attempt_1_run, repo_state_id
    )

    # The portable guard: the verdict written into the package must be the verdict the conditions
    # reached. A design session that turned out not to be sealable must still leave its package on
    # disk, so a BLOCKED outcome is written rather than suppressed — what is refused is a package
    # that disagrees with its own conditions.
    unmet = [
        cid
        for cid, cond in conditions.items()
        if cid.startswith("A2D-") and cond["verdict"] != "MET"
    ]
    verdict = PASS_VERDICT if not unmet else NOT_SEALABLE_VERDICT
    if unmet:
        print(f"SEAL CONDITIONS NOT MET: {', '.join(unmet)} — verdict is {verdict!r}")
    if verdict == PASS_VERDICT and GATE_PASSED:
        print("A SEALED DESIGN IS NOT A GATE 3 PASS — no package written")
        return 3
    if conditions["gate_3_admissible_candidate_exists"]["verdict"] != "NOT_RUN":
        print("GATE 3 WAS NOT EVALUATED IN THIS SESSION — no package written")
        return 3

    # A design seal may issue neither gate 3 token: this session neither admitted nor rejected a
    # candidate. The tokens come from the sealed derivation rather than from literals here.
    derivation = criteria["verdict_token_derivation"]
    gate_3_tokens = (derivation["pass_token"], derivation["fail_token"])
    if verdict.split(" ", 2)[-1] in gate_3_tokens:
        print(f"VERDICT USES A GATE 3 TOKEN {gate_3_tokens} — no package written")
        return 3

    design_report_digest = sha256_file(PROJECT_ROOT / DESIGN_REPORT)
    candidates = {
        experiment["experiment_id"]: {
            "family": experiment["family"],
            "family_authorised_by": experiment["family_authorised_by"],
            "hypothesis": experiment["hypothesis"],
            "distinction_from_attempt_1": experiment["distinction_from_attempt_1"],
            "primary_parameters": experiment["primary_parameters"],
            "maximum_exposure": experiment["maximum_exposure"],
            "stop_or_shutdown_rule": experiment["stop_or_shutdown_rule"],
            "max_variants": experiment["max_variants"],
            "robustness_neighbours": experiment["robustness_neighbours"],
            "gate_3_conditions_applied": experiment["gate_3_conditions_applied"],
            "implemented": False,
            "evaluated": False,
        }
        for experiment in protocol["experiments"]
    }

    decision = StageDecision(
        stage="STAGE_3_ATTEMPT_2_DESIGN",
        stage_slug="stage3_attempt2",
        decision_basename="STAGE_3_ATTEMPT_2_DESIGN",
        manifest_basename="STAGE_3_ATTEMPT_2_ARTIFACT_MANIFEST",
        gate_id=3,
        gate_name="development_admissibility",
        verdict=verdict,
        gate_passed=GATE_PASSED,
        command=COMMAND,
        gate_conditions=conditions,
        evidence=[
            f"Attempt 2's pre-registration was sealed at {seal['declared_utc']} under run "
            f"{seal['run_id']}, with all four contamination predicates at 0 and "
            f"sealed_before_any_attempt_2_strategy_code="
            f"{seal['sealed_before_any_attempt_2_strategy_code']}. The predicates are what make the "
            f"prospectiveness claim falsifiable rather than self-reported: each is defined in the "
            f"seal, each is tested in both directions, and each is wired to refusal.",
            f"{seal['candidates_declared']} candidates were declared — "
            + ", ".join(seal["candidate_ids"])
            + f" — retaining {', '.join(seal['families_retained'])} and excluding "
            + f"{', '.join(seal['families_excluded'])}, all three sharing one risk architecture "
            f"({seal['shared_risk_architecture']}). "
            f"{seal['robustness_neighbours_per_candidate']} declared neighbours each, "
            f"{seal['max_variants_per_candidate']} maximum variants each, "
            f"{seal['declared_gating_variants']} gating variants and {seal['declared_runs']} runs "
            f"declared in advance, {seal['revisions_permitted']} revisions permitted.",
            "Gate 3 is adopted unchanged and by digest: "
            f"{seal['gate']['criteria_source']} at {seal['gate']['criteria_sha256']}, "
            f"{seal['gate']['conditions_evaluated']} conditions, ceiling "
            f"{seal['gate']['max_drawdown_ceiling']} with max_drawdown_ceiling_changed="
            f"{seal['gate']['max_drawdown_ceiling_changed']}, "
            f"{seal['gate']['within_candidate']} within a candidate and "
            f"{seal['gate']['across_candidates']} across them. Two re-derivations apply sealed rules "
            f"to a new candidate set and change no threshold, predicate, measurement or token.",
            "The adaptation to Attempt 1's known outcome is disclosed rather than hidden behind new "
            f"identifiers: a {len(protocol['adaptive_research_disclosure']['items'])}-item "
            f"disclosure, a cumulative count of "
            f"{protocol['cumulative_experiment_count']['attempt_1_candidates']} + "
            f"{protocol['cumulative_experiment_count']['attempt_2_candidates']} = "
            f"{seal['cumulative_experiment_count']['cumulative_candidates']} candidates and "
            f"{seal['cumulative_experiment_count']['cumulative_gating_variants']} gating variants "
            "spanning both attempts, and a distinction_from_attempt_1 block on every candidate.",
            "Every upstream checksum record verifies from its intended working directory, and the "
            "Stage 0 freeze was re-verified over both halves of the constitution. Entry counts and "
            "statuses are in gate_conditions.A2D-C1.",
            "The pre-registration checksum record verifies 4/4 from stockedge100, and each of the "
            "three pre-registered file digests recomputes to the value the seal recorded: "
            + "; ".join(
                f"{rel} {entry['sha256']}"
                for rel, entry in seal["preregistered_files"].items()
            )
            + ".",
            "No Attempt 2 strategy module, backtest, simulation, parameter sweep, performance "
            "calculation or result artifact exists. No validation-period result was examined. No "
            "holdout observation was read; the holdout lock was read for integrity metadata and is "
            "bound by digest.",
            f"The suite floor rose from 389 to 460 collected. The recorded selection is 115 passed, "
            f"0 failed, 0 skipped, of which 71 are the new pre-registration module; no test in the "
            f"selection opens a price file, computes a return, or touches the validation or holdout "
            f"windows. All 11 test-file digests recorded in Attempt 1's run record recompute "
            f"unchanged against disk.",
            f"This design report is {DESIGN_REPORT} at {design_report_digest}; its gate-condition "
            f"table is the table in this record's gate_conditions field, and the requirement text of "
            f"each condition here is copied from it so the two can be diffed.",
        ],
        limitations=[
            "Gate 3 is not passed. A sealed design is a specification, not evidence. Nothing here "
            "indicates that any Attempt 2 candidate will satisfy S3-C2 or any other condition.",
            "The drawdown arithmetic in section 9 of the design report is a property of the declared "
            "constants under an idealised worst-case sequence, not a guarantee, and it carries five "
            "caveats that all cut the same way.",
            "The development window is no longer pristine: nine specifications now share it, and the "
            "effective search is wider than nine independent draws.",
            "No Attempt 2 candidate is a controlled comparison against Attempt 1. Warm-up lengths "
            "differ, so run windows differ; differencing an Attempt 2 number against an Attempt 1 "
            "number would not measure the risk architecture.",
            "Attempt 2 introduces no new signal form. All three signals are reused from rejected "
            "candidates, so the attempt cannot corroborate any family's hypothesis.",
            "Drawdown is measured at session closes. The project holds no intraday data, so every "
            "measured drawdown is a lower bound on the true intraday figure. Inherited from Attempt "
            "1, unchanged.",
            "Lower fixed exposure raises cost per unit of exposure, because sell-side regulatory "
            "fees round up to the cent. The drag is charged, not modelled away.",
            "S3-C6 remains a live failure mode for the defensive candidate, declared and accepted "
            "before any result.",
            "The whole test suite was not executed, so unmodified for the pre-existing test files is "
            "asserted by digest recomputation rather than by a green run.",
            "scipy and pyarrow are not installed, and no Attempt 2 rule requires either.",
            "No test covers this package: tests/**/*.py is one of the repo_state_id patterns, so a "
            "test asserting this package's repo_state_id would invalidate the value it asserts the "
            "moment it was written. The package is verified by re-running the recomputation.",
        ],
        blockers=[],
        conflicts_found=[],
        produced=list(PRODUCED),
        frozen_inputs=list(STAGE_0_FROZEN_INPUTS)
        + list(STAGE_1_FROZEN_INPUTS)
        + list(STAGE_2_FROZEN_INPUTS)
        + list(ATTEMPT_1_FROZEN_INPUTS)
        + list(ATTEMPT_2_SEALED_INPUTS),
        body={
            "session_type": "DESIGN_AND_PREREGISTRATION_ONLY",
            "gate_3_evaluated": False,
            "strategy_research_authorized": True,
            "strategy_research_authorized_for": seal["strategy_research_authorized_for"],
            "validation_access_authorized": False,
            "holdout_access_authorized": False,
            "paper_trading_authorized": False,
            "shadow_live_authorized": False,
            "stage_4_authorized": False,
            "verdict_meaning": (
                "A prospective, complete, internally consistent specification for a second gate 3 "
                "attempt has been sealed before any code for it exists, its adaptation to a known "
                "prior outcome is disclosed, and the frozen gate 3 criteria including the 15% "
                "maximum-drawdown ceiling are adopted unchanged. Implementation may therefore begin "
                "in a later, separately authorized session. It is not a gate 3 pass, not a statement "
                "that any candidate will be admitted, and not a performance claim."
            ),
            "verdict_token_is_not_a_gate_3_token": {
                "gate_3_pass_token": derivation["pass_token"],
                "gate_3_fail_token": derivation["fail_token"],
                "this_session_issued": verdict,
                "why": (
                    "no candidate was implemented, so this session can neither admit nor reject "
                    "one. Both gate 3 tokens are read from the sealed verdict_token_derivation and "
                    "asserted to differ from this session's before anything is written."
                ),
            },
            "attempt": {
                "attempt_id": seal["attempt_id"],
                "attempt": seal["attempt"],
                "status": seal["status"],
                "sealed_utc": seal["declared_utc"],
                "sealing_run_id": seal["run_id"],
                "research_question": protocol["research_question"],
                "shared_risk_architecture": seal["shared_risk_architecture"],
                "families_retained": seal["families_retained"],
                "families_excluded": seal["families_excluded"],
                "families_excluded_reasoning": protocol["families_excluded"],
                "attempt_1_status": (
                    "closed, unmodified, and superseded by nothing: Attempt 1's verdict FAIL — "
                    "STAGE_3_STRATEGY_REJECTED_IN_DEVELOPMENT stands on disk exactly as issued"
                ),
                "attempt_1_evidence_known": protocol["known_prior_evidence"],
            },
            "preregistration": {
                "markdown": PREREG_MD,
                "json_seal": SEAL,
                "protocol": PROTOCOL,
                "gate_criteria_binding": BINDING,
                "checksum_record": PREREG_RECORD,
                "preregistered_file_digests": seal["preregistered_files"],
                "artifact_ids": {
                    PREREG_MD: "SE100-GOV-0007",
                    PROTOCOL: protocol["artifact_id"],
                    BINDING: binding["artifact_id"],
                },
                "design_report": {"path": DESIGN_REPORT, "sha256": design_report_digest},
                "disposition": "SEALED_NOT_MODIFIED_BY_THIS_PACKAGE",
            },
            "candidates": candidates,
            "iteration_budget": protocol["iteration_budget"],
            "cumulative_experiment_count": protocol["cumulative_experiment_count"],
            "multiple_comparisons_disclosure": protocol["multiple_comparisons_disclosure"],
            "no_selection_in_this_stage": protocol["no_selection_in_this_stage"],
            "risk_architecture": protocol["risk_architecture"],
            "gate_3_binding": {
                "criteria_source": seal["gate"]["criteria_source"],
                "criteria_sha256": seal["gate"]["criteria_sha256"],
                "criteria_adoption": seal["gate"]["criteria_adoption"],
                "conditions_evaluated": seal["gate"]["conditions_evaluated"],
                "max_drawdown_ceiling": seal["gate"]["max_drawdown_ceiling"],
                "max_drawdown_ceiling_changed": seal["gate"]["max_drawdown_ceiling_changed"],
                "within_candidate": seal["gate"]["within_candidate"],
                "across_candidates": seal["gate"]["across_candidates"],
                "admissible_candidate_exists": binding["admissible_candidate_exists"],
                "neighbour_status": binding["neighbour_status"],
                "shutdown_behaviour": binding["shutdown_behaviour"],
                "rerun_policy": binding["rerun_policy"],
                "evaluation_integrity_rules": binding["evaluation_integrity_rules"],
                "denominators_and_universes_of_measurement": binding[
                    "denominators_and_universes_of_measurement"
                ],
                "cost_stress_is_not_a_gate_3_condition": binding[
                    "cost_stress_is_not_a_gate_3_condition"
                ],
                "conflicts_carried_forward": binding["conflicts_carried_forward"],
                "nothing_else_changed": binding["nothing_else_changed"],
            },
            "windows": {
                "authorized": seal["authorized_windows"],
                "validation": seal["validation_window_state"],
                "holdout": seal["holdout_window_state"],
                "enforcement": binding["windows"]["enforcement"],
                "unchanged_by_this_attempt": binding["windows"]["unchanged_by_this_attempt"],
                "holdout_lock_sha256": sha256_file(PROJECT_ROOT / HOLDOUT_LOCK),
                "development_window_dates_restated": False,
                "development_window_dates_note": (
                    "bound by the holdout lock's digest and read at run time; date_range is null in "
                    "this package for that reason, not by omission"
                ),
            },
            "contamination": {
                "strategy_code_existed_before_sealing": False,
                "attempt_2_performance_generated_or_inspected": False,
                "validation_results_examined": False,
                "holdout_accessed": False,
                "prospective_with_respect_to_attempt_2_results": True,
                "prospective_with_respect_to_attempt_1_results": False,
                "adaptation_recorded_in": [
                    "config/stage3_attempt2_strategy_protocol.json adaptive_research_disclosure "
                    f"({len(protocol['adaptive_research_disclosure']['items'])} items)",
                    "the cumulative experiment count spanning both attempts",
                    "the families_excluded reasoning",
                    "each candidate's distinction_from_attempt_1 block",
                ],
                "predicates_at_sealing": {
                    key: seal["contamination_predicates"][key]
                    for key in (
                        "attempt_2_strategy_modules",
                        "modules_naming_an_attempt_2_candidate",
                        "attempt_2_report_artifacts",
                        "attempt_2_run_records",
                    )
                },
                "files_making_the_movable_predicates_non_zero": {
                    f"runs/{seal['run_id']}.json": "the seal's own run record",
                    "reports/stage3_attempt2/STAGE_3_ATTEMPT_2_TEST_SUMMARY.md": "test artifact",
                    "reports/stage3_attempt2/pytest_stage3_attempt2_output.txt": "test artifact",
                    "reports/stage3_attempt2/STAGE_3_ATTEMPT_2_DESIGN.json": "design-session decision record",
                    "reports/stage3_attempt2/STAGE_3_ATTEMPT_2_ARTIFACT_MANIFEST.json": "artifact manifest",
                    "reports/stage3_attempt2/STAGE_3_ATTEMPT_2_DESIGN.sha256": "checksum record",
                    "runs/<this session's run id>.json": "design-session reproducibility record",
                },
                "none_is_strategy_code_or_a_performance_result": True,
            },
            "scope": {
                "strategy_modules_written": 0,
                "backtests_run": 0,
                "simulations_run": 0,
                "parameter_sweeps_run": 0,
                "performance_calculations_run": 0,
                "market_observations_loaded_for_performance": 0,
                "candidate_selected": False,
                "candidate_admitted": False,
                "revisions_after_seeing_a_result": 0,
                "stage_4_remains_prohibited_conditions": protocol[
                    "stage_4_remains_prohibited_conditions"
                ],
                "explicit_non_authorizations": protocol["explicit_non_authorizations"],
                "money_spent_usd": 0,
                "credentials_used": "none",
                "data_acquired": "none",
                "orders_generated": 0,
            },
            "integrity": {
                "frozen_artifacts_modified": False,
                "attempt_1_artifacts_modified": False,
                "stage_3_attempt_2_freeze_record_issued": False,
                "stage_3_attempt_2_freeze_record_rationale": (
                    "the pre-registration is already covered by "
                    "governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.sha256 and this package's outputs "
                    "by its own checksum record, while code identity is repo_state_id. Recorded as a "
                    "decision, not left as an omission."
                ),
                "self_reference_policy": (
                    "the manifest excludes its own entry and is covered by the checksum record; no "
                    "repo_state_id is written into any governance Markdown, both of which are "
                    "searched for the value rather than for the field name"
                ),
                "package_not_covered_by_tests": (
                    "tests/**/*.py is one of the repo_state_id patterns, so a test asserting this "
                    "package's repo_state_id would invalidate the value it asserts. The package is "
                    "verified by re-running the recomputation."
                ),
            },
        },
        tests={"passed": 115, "failed": 0, "skipped": 0, "collected": 460},
        authorization_state={
            "attempt_2_implementation": "UNLOCKED_FOR_THE_THREE_SEALED_CANDIDATES_ONLY",
            "attempt_2_development_evaluation": "UNLOCKED_ON_DEVELOPMENT_WINDOW_ONLY",
            "validation_window": "LOCKED",
            "final_holdout": "SEALED",
            "stage_4_constitutional_gates_4_and_5": "LOCKED_NO_ADMITTED_CANDIDATE",
            "alpaca_paper_trading": "LOCKED",
            "shadow_live": "LOCKED",
            "alpaca_live_trading": "LOCKED",
            "capital_or_risk_expansion": "LOCKED",
        },
        next_authorized_stage=(
            "STAGE_3_ATTEMPT_2_IMPLEMENTATION_AND_DEVELOPMENT_EVALUATION — a separate session that "
            "implements and evaluates only the three candidates sealed in SE100-GOV-0007, on the "
            "development window only, at their declared primary parameterisations plus their four "
            "declared neighbours each, with the sealed base cost model and the research shutdown "
            "enforced. Nothing else."
        ),
        dataset_hashes={},
        universe_version=universe["universe_version"],
        date_range=None,
        holdout_state=lock["holdout_state"],
        config_hash=sha256_file(PROJECT_ROOT / PROTOCOL),
        random_seed=None,
        run_notes=[
            "Design session only. No strategy module was written, no backtest, simulation, "
            "parameter sweep or performance calculation was run, and no market observation was "
            "loaded for performance. dataset_hashes is empty for that reason.",
            "date_range is null deliberately. The development window is bound by the digest of "
            "governance/STAGE_1_HOLDOUT_LOCK.json and read at run time; no Attempt 2 artifact "
            "restates its boundary dates.",
            "gate_passed is false, so the shared builder derives exit_status GATE_NOT_PASSED. That "
            "is correct: sealing a design for gate 3 does not pass gate 3. The verdict token is "
            "neither gate 3 token, and the check that it is neither runs before anything is written.",
            "The gate 3 determination is carried as a separate NOT_RUN entry in gate_conditions. A "
            "per-condition MET in the A2D rows is a statement about the seal, never about a "
            "candidate.",
            "Attempt 1 is closed and unmodified. Its records verify entry-for-entry, and this "
            "package supersedes nothing.",
            "The validation and holdout windows were not read. No data was acquired, no order of any "
            "kind was generated, and no credential was accessed.",
            "live_trading_authorized remains false.",
        ],
    )

    result = build_stage_package(decision)
    if not result.freeze_ok:
        print("STAGE 0 FREEZE VERIFICATION FAILED — see the decision record", flush=True)
        return 2

    if result.repo_state_id != repo_state_id:
        print(
            f"repo_state_id MOVED DURING THE BUILD: {repo_state_id} -> {result.repo_state_id}",
            flush=True,
        )

    print(f"run_id        {result.run_id}")
    print(f"timestamp_utc {result.timestamp_utc}")
    print(f"repo_state_id {result.repo_state_id}")
    print(f"verdict       {verdict}")
    for path in (
        result.decision_path,
        result.manifest_path,
        result.checksum_path,
        result.run_record_path,
    ):
        print(f"wrote         {Path(path).relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
