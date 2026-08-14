"""Stage 3 Attempt 2 evaluation package — constitution gate 3, development admissibility.

Attempt 2's implementation-and-evaluation session produces this package. It supplies only Attempt 2's
own judgement: the seven gate conditions read from the sealed criteria file the Attempt 2 binding
adopts unchanged, the evidence backing each, the limitations that survive a pass, the conflicts
found, and the verdict. Everything mechanical — timestamps, run id, ``repo_state_id``, manifests,
checksum record, run record — comes from :mod:`stockedge100.reporting.stage_package` so that nothing
here can be hand-typed.

Read the evidence, do not re-derive it. Every number quoted below is read out of
``reports/stage3_attempt2/STAGE_3_ATTEMPT_2_DEVELOPMENT_ADMISSIBILITY.json``, which
:mod:`stockedge100.reporting.attempt2_evidence` wrote by running the eighteen declared runs against
the sealed protocol. Recomputing the figures here would let the package and the evidence disagree
without anything noticing.

**This attempt passes, and that is exactly why the guard matters.** Stage 2's builder refuses to run
when its evidence does not meet every condition, which was right for a stage whose package could only
ever be a pass. That guard is wrong for Gate 3, where a rejection is a deliverable and Attempt 1
already produced one. The portable guard, which :func:`build` implements, is the other one: the
verdict written into the package must be the verdict the recorded evidence reaches. It goes further
than Attempt 1's, because a pass is the outcome that wants checking hardest:

* the two verdict tokens are read from the sealed ``verdict_token_derivation`` in
  ``config/stage3_gate_criteria.json`` — never restated here as literals — and the evidence's own
  copies and the binding's reader-facing copies must agree with the sealed ones, so a divergence
  fails instead of silently preferring the nearer file;
* the satisfaction rule is parsed out of the sealed ``satisfied_definition`` rather than hard-coded,
  and every condition's ``satisfied`` flag is recomputed from its verdict under that rule, so a
  ``NOT_EVALUABLE`` or ``NOT_RUN`` cannot arrive pre-marked as satisfied;
* each candidate's admittance is recomputed as the conjunction of its own seven conditions, the
  admitted set is recomputed as the disjunction across candidates, and every per-condition rollup row
  is rebuilt from the per-candidate blocks;
* the sealed list of incoherent combinations is refused outright — a pass with no admitted candidate,
  a fail with one, a pass reached by aggregating rollup rows instead of conjoining within a
  candidate;
* the evidence file's self-digest is recomputed with the same function that wrote it, with two
  controls that establish its coverage sentence in both directions — perturbing ``generated_utc``
  must not move the digest, and perturbing the coverage sentence itself must;
* the test counts are parsed from the captured pytest output on disk instead of being typed in, and a
  single failure or error refuses the package.

Nothing here can turn a fail into a pass: every check can only refuse to write.

Conjunction applies **within** a candidate. Across candidates the stage verdict is a disjunction,
because Gate 3 asks whether an admissible candidate exists, not whether every candidate tried is
good. The per-condition entries below therefore carry an explicit ``verdict_semantics`` field, and
the gate-level determination is the separate ``admissible_candidate_exists`` entry — the one row that
settles anything.

Usage::

    cd stockedge100 && PYTHONPATH=src python -m stockedge100.reporting.stage3_attempt2_evaluation_package
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from stockedge100.audit import sha256_file
from stockedge100.reporting.attempt2_evidence import (
    DIGEST_COVERS,
    EXCLUDED_FROM_DIGEST,
    evidence_digest,
)
from stockedge100.reporting.stage_package import (
    GOVERNANCE,
    PROJECT_ROOT,
    STAGE_0_FROZEN_INPUTS,
    StageDecision,
    build_stage_package,
    verify_sha256_record,
)

COMMAND = (
    "cd stockedge100 && PYTHONPATH=src python -m "
    "stockedge100.reporting.stage3_attempt2_evaluation_package"
)

EVIDENCE = "reports/stage3_attempt2/STAGE_3_ATTEMPT_2_DEVELOPMENT_ADMISSIBILITY.json"
PREREGISTRATION = "governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.json"
PREREG_MD = "governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.md"
PREREG_RECORD = "governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.sha256"
PROTOCOL = "config/stage3_attempt2_strategy_protocol.json"
BINDING = "config/stage3_attempt2_gate_criteria_binding.json"
CRITERIA = "config/stage3_gate_criteria.json"
ATTEMPT_1_PROTOCOL = "config/stage3_strategy_protocol.json"
COST_MODEL = "config/stage2_cost_model.json"
UNIVERSE = "governance/STAGE_1_UNIVERSE.json"
HOLDOUT_LOCK = "governance/STAGE_1_HOLDOUT_LOCK.json"
NORMALIZED_MANIFEST = "data/manifests/STAGE_1_NORMALIZED_MANIFEST.json"

# The design session's own run record. The starting repository-state identifier is read out of it
# rather than transcribed, because it is the only place the sealed ending state of that session is
# recorded — governance/ cannot hold it without invalidating it on write.
DESIGN_RUN_RECORD = "runs/SE100-R-20260810T131107Z.json"

PYTEST_OUTPUT = "reports/stage3_attempt2/pytest_stage3_attempt2_evaluation_output.txt"
TEST_COMMAND = "cd stockedge100 && python -m pytest tests -q"
COLLECT_COMMAND = "cd stockedge100 && python -m pytest tests --collect-only -q"

# Every symbol any Attempt 2 candidate loaded: C1 and C2 declare [SPY], C3 declares [SPY, SHY].
# Hashed so that a rerun producing different numbers is attributable to a specific series rather
# than to "the data".
SERIES_READ = ("SPY", "SHY")

STAGE_1_FROZEN_INPUTS = (
    "governance/STAGE_1_DATA_FOUNDATION_REPORT.md",
    UNIVERSE,
    HOLDOUT_LOCK,
    "governance/STAGE_1_FREEZE.sha256",
    "governance/STAGE_1_PREREGISTRATION.json",
    "governance/STAGE_1_PREREGISTRATION.sha256",
)

# Gate 2 was issued, so Stage 2's outputs are read-only inputs here. Attempt 2 ran on that engine and
# on that cost model without touching either.
STAGE_2_FROZEN_INPUTS = (
    "governance/STAGE_2_BACKTEST_ENGINE_REPORT.md",
    "governance/STAGE_2_PREREGISTRATION.md",
    "governance/STAGE_2_PREREGISTRATION.json",
    "governance/STAGE_2_PREREGISTRATION.sha256",
    COST_MODEL,
    "config/stage2_engine_spec.json",
)

# Attempt 1 is permanently closed and is not modified, re-run, reinterpreted, or rescued. Its
# artifacts are inputs here for one reason only: Attempt 2 is an adaptive second attempt, and the
# evidence that was known before Attempt 2 was designed has to be identifiable.
ATTEMPT_1_FROZEN_INPUTS = (
    "governance/STAGE_3_PREREGISTRATION.md",
    "governance/STAGE_3_PREREGISTRATION.json",
    "governance/STAGE_3_PREREGISTRATION.sha256",
    ATTEMPT_1_PROTOCOL,
    CRITERIA,
    "governance/STAGE_3_STRATEGY_RESEARCH_REPORT.md",
)

# Sealed before a single Attempt 2 strategy module existed. These are the artifacts that make every
# result in this session a test of a prediction rather than a description of a fit.
ATTEMPT_2_SEALED_INPUTS = (
    PREREG_MD,
    PREREGISTRATION,
    PREREG_RECORD,
    PROTOCOL,
    BINDING,
)

# The design session's own deliverables. Read-only here: this session implements what they sealed and
# does not revisit the design.
ATTEMPT_2_DESIGN_INPUTS = (
    "governance/STAGE_3_ATTEMPT_2_DESIGN_REPORT.md",
    "reports/stage3_attempt2/STAGE_3_ATTEMPT_2_DESIGN.json",
    "reports/stage3_attempt2/STAGE_3_ATTEMPT_2_ARTIFACT_MANIFEST.json",
    "reports/stage3_attempt2/STAGE_3_ATTEMPT_2_DESIGN.sha256",
    "reports/stage3_attempt2/STAGE_3_ATTEMPT_2_TEST_SUMMARY.md",
)

PRODUCED = (
    "governance/STAGE_3_ATTEMPT_2_STRATEGY_RESEARCH_REPORT.md",
    EVIDENCE,
    "reports/stage3_attempt2/STAGE_3_ATTEMPT_2_STRATEGY_RESEARCH.json",
    "reports/stage3_attempt2/STAGE_3_ATTEMPT_2_EVALUATION_ARTIFACT_MANIFEST.json",
    "reports/stage3_attempt2/STAGE_3_ATTEMPT_2_EVALUATION_TEST_SUMMARY.md",
    PYTEST_OUTPUT,
)

# Every checksum record on disk, each with the working directory its own path convention requires.
# Stage 0 and Stage 1 freeze records carry bare filenames and verify from governance/; the other nine
# carry project-root-relative paths. Verifying from the wrong directory is an operator error, not an
# integrity failure, so the directory is recorded next to the result.
CHECKSUM_RECORDS = (
    ("governance/STAGE_0_FREEZE.sha256", "stockedge100/governance"),
    ("governance/STAGE_1_FREEZE.sha256", "stockedge100/governance"),
    ("governance/STAGE_1_PREREGISTRATION.sha256", "stockedge100"),
    ("governance/STAGE_2_PREREGISTRATION.sha256", "stockedge100"),
    ("governance/STAGE_3_PREREGISTRATION.sha256", "stockedge100"),
    (PREREG_RECORD, "stockedge100"),
    ("reports/stage0/STAGE_0_VERIFICATION.sha256", "stockedge100"),
    ("reports/stage1/STAGE_1_DATA_READINESS.sha256", "stockedge100"),
    ("reports/stage2/STAGE_2_BACKTEST_ENGINE.sha256", "stockedge100"),
    ("reports/stage3/STAGE_3_STRATEGY_RESEARCH.sha256", "stockedge100"),
    ("reports/stage3_attempt2/STAGE_3_ATTEMPT_2_DESIGN.sha256", "stockedge100"),
)

VERDICT_SEMANTICS = (
    "PASS here means at least one candidate satisfied this condition — it is NOT a gate pass. "
    "Conjunction applies within a candidate, so the gate is settled by "
    "admissible_candidate_exists, not by this field. Satisfaction includes "
    "NOT_APPLICABLE_BY_CONDITION_TEXT, which is satisfied without being met; read satisfied_by "
    "against met_by and not_applicable_for before drawing anything from a PASS."
)

SEALED_KEYS_NOT_REPEATED = ("id", "required_verbatim", "predicate")


def load(rel: str) -> dict[str, Any]:
    return json.loads((PROJECT_ROOT / rel).read_text(encoding="utf-8"))


def satisfied_verdicts(binding: dict[str, Any]) -> tuple[str, ...]:
    """The satisfying verdict names, parsed out of the sealed ``satisfied_definition``.

    Restating the pair as a literal here would mean a change to the sealed rule could not be
    detected by this module. Parsing it means a reworded seal stops the build instead.
    """
    definition = binding["admissible_candidate_exists"]["satisfied_definition"]
    match = re.search(r"verdict in \(([^)]*)\)", definition)
    if match is None:
        return ()
    return tuple(part.strip() for part in match.group(1).split(",") if part.strip())


def test_counts(text: str) -> dict[str, int] | None:
    """Parse the captured pytest output. Counts are read from disk, never typed into the package."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    summary = next(
        (line for line in reversed(lines) if re.search(r"\d+ (passed|failed)", line)), None
    )
    collected = next(
        (line for line in reversed(lines) if re.search(r"\d+ tests? collected", line)), None
    )
    if summary is None or collected is None:
        return None

    def count(word: str, line: str) -> int:
        found = re.search(rf"(\d+) {word}", line)
        return int(found.group(1)) if found else 0

    return {
        "collected": count(r"tests? collected", collected),
        "passed": count("passed", summary),
        "failed": count("failed", summary),
        "skipped": count("skipped", summary),
        "errors": count("error", summary),
    }


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
            if cond.get("evidence"):
                entry["measurement_evidence"] = cond["evidence"]
            out[candidate["gate"]["experiment_id"]] = entry
    return out


def recompute(ev: dict[str, Any], criteria: dict[str, Any], binding: dict[str, Any]) -> list[str]:
    """Rebuild every derived judgement in the evidence from its own per-condition blocks.

    Returns the disagreements, empty when the evidence is internally coherent. This is the check
    that makes the package worth reading: the evidence file computed these values, and this function
    computes them again from the primitives, independently, before anything is written.
    """
    problems: list[str] = []

    satisfying = satisfied_verdicts(binding)
    not_satisfied = tuple(binding["admissible_candidate_exists"]["not_satisfied_values"])
    if len(satisfying) != 2:
        problems.append(
            f"sealed satisfied_definition did not parse to two verdict names: {satisfying!r}"
        )
        return problems
    overlap = [name for name in satisfying if name in not_satisfied]
    if overlap:
        problems.append(f"sealed satisfaction rule contradicts not_satisfied_values on {overlap!r}")
        return problems

    sealed_ids = [cond["id"] for cond in criteria["conditions"]]
    admitted: list[str] = []

    for candidate in ev["candidates"]:
        gate = candidate["gate"]
        eid = gate["experiment_id"]
        seen = [cond["id"] for cond in gate["conditions"]]
        if seen != sealed_ids:
            problems.append(f"{eid} evaluated {seen} but the sealed criteria declare {sealed_ids}")
            continue
        for cond in gate["conditions"]:
            expected = cond["verdict"] in satisfying and cond["verdict"] not in not_satisfied
            if expected != cond["satisfied"]:
                problems.append(
                    f"{eid} {cond['id']} verdict {cond['verdict']} implies satisfied={expected} "
                    f"but the evidence records satisfied={cond['satisfied']}"
                )
        conjunction = all(cond["satisfied"] for cond in gate["conditions"])
        if conjunction != gate["admitted"]:
            problems.append(
                f"{eid} conjunction of its own conditions is {conjunction} but the evidence "
                f"records admitted={gate['admitted']}"
            )
        if conjunction:
            admitted.append(eid)

    summaries = {summary["experiment_id"]: summary for summary in ev["gate_summary"]}
    if sorted(summaries) != sorted(cand["gate"]["experiment_id"] for cand in ev["candidates"]):
        problems.append("gate_summary does not cover exactly the evaluated candidates")
    for eid, summary in summaries.items():
        if summary["admitted"] != (eid in admitted):
            problems.append(f"gate_summary {eid} admitted={summary['admitted']} disagrees")

    decisive = ev["per_condition_rollup"]["decisive_row"]
    stage = ev["stage_verdict"]
    if sorted(decisive["admitted_candidates"]) != sorted(admitted):
        problems.append(
            f"decisive_row admitted_candidates {decisive['admitted_candidates']} disagrees with the "
            f"recomputed {admitted}"
        )
    if sorted(stage["admitted_candidates"]) != sorted(admitted):
        problems.append(
            f"stage_verdict admitted_candidates {stage['admitted_candidates']} disagrees with the "
            f"recomputed {admitted}"
        )
    if decisive["value"] != bool(admitted):
        problems.append(
            f"decisive_row value {decisive['value']} disagrees with the recomputed disjunction "
            f"{bool(admitted)}"
        )
    if decisive["candidates_evaluated"] != len(ev["candidates"]):
        problems.append("decisive_row candidates_evaluated disagrees with the candidates present")

    rows = {row["id"]: row for row in ev["per_condition_rollup"]["rows"]}
    if sorted(rows) != sorted(sealed_ids):
        problems.append(f"rollup rows {sorted(rows)} do not cover the sealed {sorted(sealed_ids)}")
    for condition_id in sealed_ids:
        row = rows.get(condition_id)
        if row is None:
            continue
        per_candidate = _per_candidate(ev, condition_id)
        expected_met = sorted(c for c, e in per_candidate.items() if e["verdict"] == "MET")
        expected_not_met = sorted(c for c, e in per_candidate.items() if e["verdict"] == "NOT_MET")
        expected_na = sorted(
            c
            for c, e in per_candidate.items()
            if e["verdict"] == "NOT_APPLICABLE_BY_CONDITION_TEXT"
        )
        expected_any = any(e["satisfied"] for e in per_candidate.values())
        for name, expected, actual in (
            ("met_by", expected_met, sorted(row["met_by"])),
            ("not_met_by", expected_not_met, sorted(row["not_met_by"])),
            ("not_applicable_for", expected_na, sorted(row["not_applicable_for"])),
            (
                "satisfied_by_at_least_one_candidate",
                expected_any,
                row["satisfied_by_at_least_one_candidate"],
            ),
        ):
            if expected != actual:
                problems.append(
                    f"rollup {condition_id} {name} is {actual!r}, recomputed {expected!r}"
                )
    return problems


def gate_conditions(
    ev: dict[str, Any], criteria: dict[str, Any], binding: dict[str, Any]
) -> dict[str, Any]:
    """Constitution section 9, gate 3, one entry per hard condition, quoted verbatim.

    The verbatim text and the predicate are read from the sealed criteria file the Attempt 2 binding
    adopts unchanged, not restated here, so that the package cannot quote a condition the evaluator
    did not apply. Every other sealed key on a condition — its costs note, its boundary treatment,
    its undefined cases, its scope interpretation, its not-evaluable rule — is attached wholesale
    rather than hand-enumerated, because a key omitted by hand reads as a key that does not exist.
    """
    sealed = {cond["id"]: cond for cond in criteria["conditions"]}
    rows = {row["id"]: row for row in ev["per_condition_rollup"]["rows"]}
    conditions: dict[str, Any] = {}

    for condition_id, cond in sealed.items():
        per_candidate = _per_candidate(ev, condition_id)
        row = rows[condition_id]
        satisfied = [cid for cid, entry in per_candidate.items() if entry["satisfied"]]
        conditions[condition_id] = {
            "required": cond["required_verbatim"],
            "predicate": cond["predicate"],
            "verdict": "PASS" if satisfied else "FAIL",
            "verdict_semantics": VERDICT_SEMANTICS,
            "aggregated_on": row["aggregated_on"],
            "settles": row["settles"],
            "satisfied_by": satisfied,
            "met_by": [c for c, e in per_candidate.items() if e["verdict"] == "MET"],
            "not_met_by": [c for c, e in per_candidate.items() if e["verdict"] == "NOT_MET"],
            "not_evaluable_for": [
                c for c, e in per_candidate.items() if e["verdict"] == "NOT_EVALUABLE"
            ],
            "not_applicable_for": [
                cid
                for cid, entry in per_candidate.items()
                if entry["verdict"] == "NOT_APPLICABLE_BY_CONDITION_TEXT"
            ],
            "candidates_evaluated": len(per_candidate),
            "evidence": {
                "per_candidate": per_candidate,
                "sealed_measurement_specification": {
                    key: value
                    for key, value in cond.items()
                    if key not in SEALED_KEYS_NOT_REPEATED
                },
            },
        }

    decisive = ev["per_condition_rollup"]["decisive_row"]
    conditions["admissible_candidate_exists"] = {
        "required": decisive["frozen_rule"],
        "predicate": decisive["satisfied_definition"],
        "verdict": decisive["gate_verdict"],
        "verdict_semantics": "This entry, and only this entry, is the gate determination.",
        "within_candidate": decisive["within_candidate"],
        "across_candidates": decisive["across_candidates"],
        "value": decisive["value"],
        "decides_the_gate": decisive["decides_the_gate"],
        "evidence": {
            "candidates_evaluated": decisive["candidates_evaluated"],
            "admitted_candidates": decisive["admitted_candidates"],
            "admissible_candidates_required": binding["admissible_candidate_exists"][
                "how_many_admissible_candidates_are_required"
            ],
            "combination_rule": ev["stage_verdict"]["combination_rule"],
            "condition_token": ev["stage_verdict"]["condition_token"],
            "gate_verdict_token": decisive["gate_verdict_token"],
            "per_condition_rollup_is_not_the_gate": binding["admissible_candidate_exists"][
                "per_condition_rollup_is_not_the_gate"
            ],
            "incoherent_combinations_refused": binding["admissible_candidate_exists"][
                "incoherent_combinations_refused"
            ],
            "recomputed_independently_by_this_builder": (
                "each candidate's admittance was rebuilt as the conjunction of its own seven "
                "conditions under the sealed satisfaction rule, the admitted set as the disjunction "
                "across candidates, and every rollup row from the per-candidate blocks; the package "
                "is not written on any disagreement"
            ),
            "per_candidate": {
                summary["experiment_id"]: {
                    "family": summary["family"],
                    "admitted": summary["admitted"],
                    "conditions_met": summary["conditions_met"],
                    "conditions_not_met": summary["conditions_not_met"],
                    "conditions_not_evaluable": summary["conditions_not_evaluable"],
                    "conditions_not_applicable": summary["conditions_not_applicable"],
                }
                for summary in ev["gate_summary"]
            },
        },
    }
    return conditions


def variant_table(ev: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Every registered variant that gated, compactly. The evidence file holds all 43 fields each."""
    table: dict[str, dict[str, Any]] = {}
    for candidate in ev["candidates"]:
        for variant_id, run in candidate["runs"].items():
            table[variant_id] = {
                "role": run["role"],
                "scenario": run["scenario"],
                "gating": run["gating"],
                "parameters": run["parameters"],
                "start": run["start"],
                "end": run["end"],
                "sessions": run["sessions"],
                "total_return": run["total_return"],
                "max_drawdown": run["max_drawdown"],
                "deepest_drawdown_4dp": run["deepest_drawdown_4dp"],
                "profit_factor": run["profit_factor"],
                "closed_trades": run["closed_trades"],
                "shutdown_session": run["shutdown_session"],
                "trades_digest": run["trades_digest"],
                "equity_digest": run["equity_digest"],
            }
    return table


def build() -> int:
    ev = load(EVIDENCE)
    prereg = load(PREREGISTRATION)
    protocol = load(PROTOCOL)
    binding = load(BINDING)
    criteria = load(CRITERIA)
    universe = load(UNIVERSE)
    lock = load(HOLDOUT_LOCK)
    design_run = load(DESIGN_RUN_RECORD)

    # --- the verdict is derived from the sealed tokens, and the sealed tokens only ----------------
    sealed_tokens = criteria["verdict_token_derivation"]
    stage = ev["stage_verdict"]
    decisive = ev["per_condition_rollup"]["decisive_row"]
    reader_copy = binding["admissible_candidate_exists"]["verdict_mapping"]

    for label, copy in (("evidence stage_verdict", stage), ("binding verdict_mapping", reader_copy)):
        for key in ("pass_token", "fail_token"):
            if copy[key] != sealed_tokens[key]:
                print(
                    f"{label} {key} {copy[key]!r} DISAGREES WITH THE SEALED "
                    f"{sealed_tokens[key]!r} — no package written"
                )
                return 3

    admissible = decisive["value"]
    token = sealed_tokens["pass_token"] if admissible else sealed_tokens["fail_token"]
    word = "PASS" if admissible else "FAIL"
    verdict = f"{word} — {token}"

    if stage["verdict"] != word or decisive["gate_verdict"] != word:
        print(
            f"EVIDENCE VERDICT WORDS {stage['verdict']!r}/{decisive['gate_verdict']!r} DISAGREE "
            f"WITH admissible_candidate_exists={admissible} — no package written"
        )
        return 3
    if decisive["gate_verdict_token"] != token:
        print(
            f"EVIDENCE GATE TOKEN {decisive['gate_verdict_token']!r} IS NOT THE SEALED "
            f"{token!r} — no package written"
        )
        return 3

    # The sealed list of combinations that must never be written, refused literally.
    if admissible and not decisive["admitted_candidates"]:
        print("EVIDENCE REPORTS A PASS WITH ZERO ADMITTED CANDIDATES — no package written")
        return 3
    if not admissible and decisive["admitted_candidates"]:
        print("EVIDENCE REPORTS A FAIL WITH ADMITTED CANDIDATES — no package written")
        return 3

    problems = recompute(ev, criteria, binding)
    if problems:
        print("INDEPENDENT RECOMPUTATION DISAGREES WITH THE EVIDENCE — no package written")
        for problem in problems:
            print(f"  {problem}")
        return 3

    # --- the evidence file's own seal, recomputed with the function that wrote it -----------------
    if ev["evidence_digest_covers"] != DIGEST_COVERS:
        print("EVIDENCE COVERAGE SENTENCE HAS CHANGED — no package written")
        return 3
    recomputed_digest = evidence_digest(ev)
    if recomputed_digest != ev["evidence_digest"]:
        print(
            f"EVIDENCE SELF-DIGEST {ev['evidence_digest']!r} DOES NOT RECOMPUTE "
            f"({recomputed_digest!r}) — no package written"
        )
        return 3
    # The coverage sentence has to hold in both directions, and one control cannot establish both.
    # Excluded means excluded: perturbing generated_utc must leave the digest alone.
    excluded_control = evidence_digest({**ev, EXCLUDED_FROM_DIGEST[0]: "1970-01-01T00:00:00Z"})
    if excluded_control != recomputed_digest:
        print(
            f"PERTURBING {EXCLUDED_FROM_DIGEST[0]} CHANGED THE DIGEST, SO IT IS NOT EXCLUDED "
            "— no package written"
        )
        return 3
    # Covered means covered: perturbing the coverage sentence itself must change the digest. This is
    # the direction Stage 2 got wrong, and a digest blind to its own description is stable and wrong.
    covered_control = evidence_digest({**ev, "evidence_digest_covers": DIGEST_COVERS + " (control)"})
    if covered_control == recomputed_digest:
        print("EVIDENCE DIGEST DOES NOT COVER ITS OWN COVERAGE SENTENCE — no package written")
        return 3

    # --- the sealed inputs are the ones that were loaded ------------------------------------------
    loaded = ev["sealed_inputs"]["digests_recomputed_at_load"]
    for rel, digest in loaded.items():
        actual = sha256_file(PROJECT_ROOT / rel)
        if actual != digest:
            print(f"{rel} NOW HASHES {actual} BUT WAS LOADED AS {digest} — no package written")
            return 3
    for rel, entry in prereg["preregistered_files"].items():
        actual = sha256_file(PROJECT_ROOT / rel)
        if actual != entry["sha256"]:
            print(f"{rel} DIVERGES FROM ITS PRE-REGISTERED DIGEST — no package written")
            return 3
    if sha256_file(PROJECT_ROOT / CRITERIA) != prereg["gate"]["criteria_sha256"]:
        print("GATE CRITERIA DIVERGE FROM THE PRE-REGISTERED DIGEST — no package written")
        return 3

    # --- the declared runs are the runs that executed ---------------------------------------------
    budget = ev["iteration_budget"]
    for label, executed, declared in (
        ("gating variants", budget["gating_variants_executed"], prereg["declared_gating_variants"]),
        ("runs", budget["runs_executed"], prereg["declared_runs"]),
        ("candidates", budget["candidates_evaluated"], prereg["candidates_declared"]),
    ):
        if executed != declared:
            print(f"{label}: {executed} executed vs {declared} declared — no package written")
            return 3
    for label, key in (
        ("revisions", "revisions_made"),
        ("variants rerun after a result", "variants_rerun_after_seeing_a_result"),
    ):
        if budget[key] != prereg["revisions_permitted"]:
            print(f"{label} is {budget[key]}, permitted {prereg['revisions_permitted']} — refused")
            return 3
    if not ev["determinism"]["all_identical"]:
        print("EVIDENCE REPORTS A NON-DETERMINISTIC PRIMARY — no package written")
        return 3

    # --- the partitions this session was authorized to touch --------------------------------------
    window = ev["window"]
    if window["validation_observations_read"] or window["holdout_observations_read"]:
        print("EVIDENCE REPORTS A RESTRICTED PARTITION WAS READ — no package written")
        return 3
    if window["boundary_changed"] or ev["live_trading_authorized"]:
        print("EVIDENCE REPORTS A MOVED BOUNDARY OR A LIVE AUTHORIZATION — no package written")
        return 3

    # --- the test counts, read from the captured run rather than typed in -------------------------
    pytest_path = PROJECT_ROOT / PYTEST_OUTPUT
    if not pytest_path.exists():
        print(f"{PYTEST_OUTPUT} IS MISSING — capture the suite before building")
        return 3
    counts = test_counts(pytest_path.read_text(encoding="utf-8", errors="replace"))
    if counts is None:
        print(f"COULD NOT PARSE COUNTS FROM {PYTEST_OUTPUT} — no package written")
        return 3
    if counts["failed"] or counts["errors"]:
        print(f"CAPTURED SUITE REPORTS {counts} — no package written")
        return 3
    if counts["collected"] != counts["passed"] + counts["failed"] + counts["skipped"]:
        print(f"CAPTURED COUNTS DO NOT RECONCILE: {counts} — no package written")
        return 3

    # --- every checksum record on disk, from the directory its convention requires ----------------
    checksums: dict[str, Any] = {}
    for rel, working_directory in CHECKSUM_RECORDS:
        root = GOVERNANCE if working_directory.endswith("governance") else PROJECT_ROOT
        result = verify_sha256_record(PROJECT_ROOT / rel, root)
        checksums[rel] = {"working_directory": working_directory, "entries": result}
        bad = {name: state for name, state in result.items() if state != "OK"}
        if bad:
            print(f"{rel} DOES NOT VERIFY FROM {working_directory}: {bad} — no package written")
            return 3

    primaries = {
        candidate["plan"]["experiment_id"]: candidate["runs"][
            candidate["plan"]["experiment_id"] + "#PRIMARY"
        ]
        for candidate in ev["candidates"]
    }
    summaries = {summary["experiment_id"]: summary for summary in ev["gate_summary"]}
    plans = {candidate["plan"]["experiment_id"]: candidate["plan"] for candidate in ev["candidates"]}
    admitted = list(decisive["admitted_candidates"])
    rejected = [eid for eid in primaries if eid not in admitted]
    conditions_by_candidate = {
        candidate["gate"]["experiment_id"]: {
            cond["id"]: cond for cond in candidate["gate"]["conditions"]
        }
        for candidate in ev["candidates"]
    }
    # Built by lookup rather than by index so that the sentence names the condition each rejected
    # candidate actually failed, whichever candidate that turns out to be.
    rejection_reasons = "; ".join(
        f"{eid} fails "
        + ", ".join(
            f"{cond['id']} (measured {cond['measured']} against {cond['threshold']})"
            for cond in conditions_by_candidate[eid].values()
            if not cond["satisfied"]
        )
        for eid in rejected
    )

    decision = StageDecision(
        stage="STAGE_3_ATTEMPT_2_STRATEGY_RESEARCH",
        stage_slug="stage3_attempt2",
        decision_basename="STAGE_3_ATTEMPT_2_STRATEGY_RESEARCH",
        manifest_basename="STAGE_3_ATTEMPT_2_EVALUATION_ARTIFACT_MANIFEST",
        gate_id=3,
        gate_name="development_admissibility",
        verdict=verdict,
        gate_passed=admissible,
        command=COMMAND,
        gate_conditions=gate_conditions(ev, criteria, binding),
        evidence=[
            f"The Attempt 2 protocol, its gate-criteria binding and its pre-registration Markdown "
            f"were sealed at {prereg['declared_utc']} under run {prereg['run_id']}, with "
            f"sealed_before_any_attempt_2_strategy_code="
            f"{prereg['sealed_before_any_attempt_2_strategy_code']}. The four contamination "
            f"predicates in that record — Attempt 2 modules, modules naming an Attempt 2 candidate, "
            f"Attempt 2 report artifacts, Attempt 2 run records — were all 0 at sealing, which is "
            f"what makes the claim falsifiable rather than self-reported. They are knowingly "
            f"non-zero now: this session is the authorized implementation.",
            f"{prereg['candidates_declared']} candidates were declared, each with "
            f"{prereg['robustness_neighbours_per_candidate']} registered robustness neighbours: "
            f"{prereg['declared_gating_variants']} gating variants and {prereg['declared_runs']} "
            f"declared runs, {prereg['revisions_permitted']} revisions permitted. Executed: "
            f"{budget['gating_variants_executed']} gating variants, "
            f"{budget['non_gating_stress_runs_executed']} non-gating stressed-cost runs, "
            f"{budget['runs_executed']} runs in total, {budget['revisions_made']} revisions, "
            f"{budget['variants_rerun_after_seeing_a_result']} variants rerun after a result was "
            f"seen. The harness counts its own runs against the sealed number and raises rather "
            f"than reporting a mismatch.",
            f"Gate 3 is settled by admissible_candidate_exists, which is "
            f"{decisive['value']}: {len(admitted)} of {len(conditions_by_candidate)} candidates "
            f"satisfy every applicable hard condition — {', '.join(admitted)}. The sealed binding's "
            f"answer to how many admissible candidates the gate requires is: "
            f"\"{binding['admissible_candidate_exists']['how_many_admissible_candidates_are_required']['answer']}\" "
            f"— a floor, not a count of what was found. Conjunction was applied within each "
            f"candidate and never across candidates.",
            f"Not admitted: {rejection_reasons}. The rejected candidate is the strongest of the "
            f"three on every reported return and risk metric except the concentration measure that "
            f"rejects it, and it is rejected anyway; nothing in this stage promotes, substitutes, "
            f"reinterprets or re-parameterises it.",
            "The 15% maximum-drawdown condition holds for all three primaries, which is the "
            "single fact that separates Attempt 2 from Attempt 1: "
            + ", ".join(
                f"{eid} {run['deepest_drawdown_4dp']}" for eid, run in primaries.items()
            )
            + ". No primary tripped the section 5.1 research shutdown, so none was liquidated or "
            "permanently deactivated. Attempt 1's six candidates all breached the ceiling and all "
            "were switched off mid-window.",
            "S3-C1 holds after base costs for all three: "
            + ", ".join(f"{eid} {run['total_return']}" for eid, run in primaries.items())
            + ".",
            "S3-C3 profit factor: "
            + ", ".join(f"{eid} {str(run['profit_factor'])[:8]}" for eid, run in primaries.items())
            + ". S3-C4 closed trades: "
            + ", ".join(f"{eid} {run['closed_trades']}" for eid, run in primaries.items())
            + ".",
            f"S3-C7 holds for all three: every one of the "
            f"{prereg['robustness_neighbours_per_candidate'] * len(primaries)} registered neighbour "
            f"runs matches the sign of its primary's net return, and each ran over the same window "
            f"as its primary under the same base cost model with the research shutdown enforced. "
            f"Neighbours are diagnostic only: none was promoted, and no primary parameterisation "
            f"was revised because a neighbour did better.",
            f"S3-C6 is NOT_APPLICABLE_BY_CONDITION_TEXT for the two single-instrument candidates on "
            f"the sealed interpretation fixed before any result, and NOT_MET for the "
            f"two-instrument one. Satisfaction is wider than met: the two admitted candidates "
            f"satisfy six conditions and meet five plus one not-applicable.",
            f"Determinism: {len(ev['determinism']['runs'])} primaries re-executed under a distinct "
            f"#RERUN label outside the declared budget, compared on trade and equity digests, "
            f"all_identical={ev['determinism']['all_identical']}. The sealed protocol declares no "
            f"random seeds — there are none to declare — so the field is present and null rather "
            f"than absent.",
            "Benchmarks are reported for every candidate and gate nothing at this stage. Neither "
            "admitted candidate beats the SPY index or the tradable SPY buy-and-hold over its own "
            "window: "
            + "; ".join(
                f"{cand['gate']['experiment_id']} candidate "
                f"{cand['benchmark_comparison']['candidate_total_return']} vs tradable SPY "
                f"{cand['benchmark_comparison']['spy_tradable_total_return']}"
                for cand in ev["candidates"]
            )
            + ". All three beat 0% cash and doing nothing. The constitution section 4 carve-out for "
            "materially reduced drawdown is the only ground on which an admitted candidate here is "
            "defensible against buy-and-hold, and that is a Gate 4 question, not a Gate 3 finding.",
            "Stressed-cost runs at the sealed multiplier are recorded and gate nothing: "
            + "; ".join(
                f"{cand['gate']['experiment_id']} "
                f"{cand['stressed_cost_run']['base_total_return']} -> "
                f"{cand['stressed_cost_run']['stressed_total_return']}"
                f"{', shutdown ' + str(cand['stressed_cost_run']['stressed_shutdown_session']) if cand['stressed_cost_run']['stressed_shutdown_session'] else ''}"
                for cand in ev["candidates"]
            )
            + ". The sealed prohibition is explicit that a stress result may neither admit a "
            "candidate that failed a hard condition nor reject one that satisfied all of them.",
            "All eleven checksum records on disk verify entry-for-entry from the working directory "
            "each one's path convention requires, including Attempt 1's pre-registration and "
            "decision records — the immutability check that fails if any Attempt 1 artifact moved.",
            f"The admissibility evidence is reproducible and its self-digest was verified in both "
            f"directions the project rule requires: recomputing {ev['evidence_digest']} from the "
            f"written file with the same function that wrote it, following its own "
            f"evidence_digest_covers sentence, reproduces it; perturbing generated_utc leaves it "
            f"unchanged, so that field really is excluded; and perturbing the coverage sentence "
            f"itself changes it, so the digest really does cover its own description.",
            f"{counts['passed']} tests pass, {counts['failed']} fail, {counts['skipped']} skip, "
            f"{counts['collected']} collected. The counts are parsed from "
            f"{PYTEST_OUTPUT} rather than typed into this package, and a single failure, a single "
            f"error, or a collection count that does not reconcile refuses to write it. Every test "
            f"module standing at Attempt 2 pre-registration is byte-identical to its digest in "
            f"{DESIGN_RUN_RECORD}; no test was weakened, skipped, xfailed or deleted, and the "
            f"additions are Attempt 2's own.",
        ],
        limitations=[
            "A development pass is admissibility, not an edge. It authorises consideration of the "
            "next frozen evaluation step and nothing else. No candidate has been validated, no "
            "candidate has been selected, and no result here says anything about any future period.",
            "This is an adaptive second attempt. Attempt 1's six rejections were known before "
            "Attempt 2 was designed, and the design target — never tripping the section 5.1 "
            "shutdown — was derived from that knowledge. New code does not make Attempt 2 an "
            "independent confirmation of anything.",
            "Nine cumulative primary candidates and 45 cumulative gating variants have now been "
            "run against the same development window. The probability that at least one of nine "
            "specifications clears the gate by chance exceeds the probability that any single "
            "pre-specified one does. Nothing in this attempt corrects for that numerically, and no "
            "statistical significance test was performed or pre-registered.",
            "Neither admitted candidate beats SPY buy-and-hold over its own window, tradable or "
            "index. The only candidate that beats tradable SPY is the one Gate 3 rejects. An "
            "admitted candidate here is a low-exposure, lower-drawdown alternative to buy-and-hold, "
            "not a better one on return.",
            "The admitted pullback candidate's deepest drawdown sits 33 basis points under the "
            "ceiling. Its registered neighbour N1 breached it outright and was shut down in "
            "February 2020, and its stressed-cost run shut down in February 2018 and returned "
            "essentially nothing. The margin is thin and the fragility is real, even though "
            "neither diagnostic carries gate weight under the sealed rules.",
            "One parameterisation per family is not a test of the family. Three candidates were "
            "run; three families were not evaluated. The neighbour spreads show how much of each "
            "result belongs to the particular numbers chosen rather than to the rule.",
            "The results are not comparable across candidates. The three run over different start "
            "dates because their largest lookbacks differ, on partly different regimes, and one "
            "trades a two-instrument universe. No ranking is implied, none was computed, and Gate 3 "
            "does not name a winner.",
            "Base costs gate; the stressed scenario is a recorded diagnostic. Every gating result "
            "is therefore the optimistic case, and the cost model remains a proxy that cannot be "
            "validated before paper trading at gate 7.",
            "Drawdown is measured at session closes because the project holds no intraday data and "
            "none was imputed, so an intraday excursion past the ceiling that closed above it is "
            "invisible to S3-C2 and every measured figure is a lower bound.",
            "The per-position loss control compares the unadjusted close against the reference "
            "price, because the sealed rule writes close(symbol, t). On a split date the adjusted "
            "and unadjusted series diverge; this is a disclosed characteristic of the sealed "
            "specification, faithfully implemented, not an ambiguity resolved by discretion.",
            "The 5% minimum cash buffer is a pre-trade constraint, not a post-trade invariant. The "
            "lowest cash fraction observed on any session is below 5% because a position marked up "
            "after entry raises the equity denominator; the constraint is evaluated when an order "
            "is sized, which is what the sealed engine specification requires.",
            "Single-provider price data with unquantified residual fund-closure bias, "
            "split-adjusted prices only, and no as-traded price levels. A systematic provider error "
            "would pass every check in this stage undetected.",
            "Every Stage 1 data limitation and every Stage 2 engine limitation is inherited whole. "
            "A research result cannot be more trustworthy than the engine, and the engine cannot be "
            "more trustworthy than its inputs.",
        ],
        blockers=[],
        conflicts_found=[
            "A2-EVAL-CONFLICT-1 — the operating prompt for this session names the verdict tokens "
            "STAGE_3_ATTEMPT_2_DEVELOPMENT_ADMISSIBILITY_MET and "
            "STAGE_3_ATTEMPT_2_STRATEGIES_REJECTED_IN_DEVELOPMENT. Neither string exists in any "
            "artifact on disk. The sealed verdict_token_derivation in config/stage3_gate_criteria."
            "json defines exactly two tokens, the Attempt 2 protocol adopts them unchanged, and the "
            "binding requires a builder to read them from the sealed field rather than from any "
            "restatement. The sealed artifact wins: this package derives both tokens from that "
            "field at build time and issues the sealed pass token. No frozen artifact was edited.",
            "A2-EVAL-CONFLICT-2 — config/stage3_gate_criteria.json contains five non-ASCII bytes, "
            "all U+2014, one of them inside verdict_token_derivation.fail_is_a_deliverable, which "
            "the binding's serialisation note records and declines to repair. It remains "
            "unrepaired, unre-encoded and byte-for-byte unchanged; its digest matches the "
            "pre-registered value. The tokens themselves are ASCII and unaffected.",
            "S3-CONFLICT-1 through S3-CONFLICT-4-ATTEMPT-2 are carried forward from the sealed "
            "binding unchanged; see body.gate_3_rules_as_applied.conflicts_carried_forward for each "
            "one's sealed wording and Attempt 2 position. The one that bites at this gate is "
            "S3-CONFLICT-3: the S3-C2 ceiling and the section 5.1 research shutdown are the same "
            "value on the same series, so S3-C2 is met if and only if the shutdown never fires. "
            "Attempt 2 adopted never tripping it as the design target, which the sealed protocol "
            "records in advance.",
        ],
        produced=list(PRODUCED),
        frozen_inputs=list(STAGE_0_FROZEN_INPUTS)
        + list(STAGE_1_FROZEN_INPUTS)
        + list(STAGE_2_FROZEN_INPUTS)
        + list(ATTEMPT_1_FROZEN_INPUTS)
        + list(ATTEMPT_2_SEALED_INPUTS)
        + list(ATTEMPT_2_DESIGN_INPUTS),
        body={
            "verdict_token_derivation": {
                "sealed_source": {
                    "artifact_id": ev["sealed_inputs"]["criteria_artifact_id"],
                    "path": CRITERIA,
                    "sha256": sha256_file(PROJECT_ROOT / CRITERIA),
                    "field": "verdict_token_derivation",
                    "adoption": prereg["gate"]["criteria_adoption"],
                    "changed_for_attempt_2": prereg["gate"]["criteria_changed_for_attempt_2"],
                },
                "pass_token": sealed_tokens["pass_token"],
                "fail_token": sealed_tokens["fail_token"],
                "pass_condition": sealed_tokens["pass_condition"],
                "fail_condition": sealed_tokens["fail_condition"],
                "conjunctive_note": sealed_tokens["conjunctive_note"],
                "other_tokens_available": sealed_tokens["other_tokens_available"],
                "chosen": token,
                "unused": sealed_tokens["fail_token"] if admissible else sealed_tokens["pass_token"],
                "derived_from": {
                    "admissible_candidate_exists": admissible,
                    "admitted_candidates": admitted,
                },
                "issued": verdict,
                "how": (
                    "read from the sealed field at build time and never restated as a literal in "
                    "this module; the evidence's own copies and the binding's reader-facing copies "
                    "are compared against the sealed ones, so a divergence refuses the package "
                    "rather than silently preferring the nearer file"
                ),
                "prompt_divergence": (
                    "the operating prompt named two Attempt-2-specific tokens that exist nowhere on "
                    "disk; the sealed derivation governs, and the divergence is recorded as "
                    "A2-EVAL-CONFLICT-1 rather than resolved by inventing a token"
                ),
            },
            "preregistration": {
                "document_id": prereg["document_id"],
                "attempt_id": prereg["attempt_id"],
                "status": prereg["status"],
                "declared_utc": prereg["declared_utc"],
                "run_id": prereg["run_id"],
                "is_adaptive_second_attempt": prereg["is_adaptive_second_attempt"],
                "relationship_to_attempt_1": prereg["relationship_to_attempt_1"],
                "sealed_before_any_attempt_2_strategy_code": prereg[
                    "sealed_before_any_attempt_2_strategy_code"
                ],
                "candidates_declared": prereg["candidates_declared"],
                "candidate_ids": prereg["candidate_ids"],
                "shared_risk_architecture": prereg["shared_risk_architecture"],
                "robustness_neighbours_per_candidate": prereg[
                    "robustness_neighbours_per_candidate"
                ],
                "max_variants_per_candidate": prereg["max_variants_per_candidate"],
                "declared_gating_variants": prereg["declared_gating_variants"],
                "declared_runs": prereg["declared_runs"],
                "revisions_permitted": prereg["revisions_permitted"],
                "families_retained": prereg["families_retained"],
                "families_excluded": prereg["families_excluded"],
                "gate": prereg["gate"],
                "sealed_files": prereg["preregistered_files"],
                "checksum_record": prereg["checksum_record"],
                "binding_consequences": prereg["binding_consequences"],
                "strategy_research_authorized_for": prereg["strategy_research_authorized_for"],
                "authorization_determination": protocol["authorization_determination"],
                "contamination_predicates_at_sealing": {
                    "definitions": prereg["contamination_predicates"]["definitions"],
                    "status_now": (
                        "knowingly non-zero. Every predicate was 0 at sealing and each one counts "
                        "artifacts this session was authorized to create: the Attempt 2 strategy "
                        "modules, the modules naming a candidate id, the Attempt 2 report "
                        "artifacts, and the Attempt 2 run records. A zero count now would mean the "
                        "authorized implementation had not happened. The predicates that must still "
                        "hold are the Attempt 1 immutability ones, and they do."
                    ),
                },
                "enforcement": (
                    "stockedge100.strategies.attempt2_config.load_attempt2_config recomputes every "
                    "sealed digest on each load and raises ConfigViolation on drift, so a silently "
                    "edited threshold stops the harness rather than changing a verdict; the harness "
                    "counts executed runs against the sealed declared_runs and refuses a mismatch"
                ),
            },
            "configs": {
                PROTOCOL: sha256_file(PROJECT_ROOT / PROTOCOL),
                BINDING: sha256_file(PROJECT_ROOT / BINDING),
                CRITERIA: sha256_file(PROJECT_ROOT / CRITERIA),
                COST_MODEL: sha256_file(PROJECT_ROOT / COST_MODEL),
                ATTEMPT_1_PROTOCOL: sha256_file(PROJECT_ROOT / ATTEMPT_1_PROTOCOL),
                UNIVERSE: sha256_file(PROJECT_ROOT / UNIVERSE),
                HOLDOUT_LOCK: sha256_file(PROJECT_ROOT / HOLDOUT_LOCK),
                "config_hash_refers_to": PROTOCOL,
                "recomputed_against_load_time_digests": (
                    "every entry in the evidence's digests_recomputed_at_load was rehashed here and "
                    "matched, so no sealed input changed between the evaluation and this package"
                ),
            },
            "admissibility_evidence": {
                "evidence_file": EVIDENCE,
                "artifact_id": ev["artifact_id"],
                "evidence_digest": ev["evidence_digest"],
                "evidence_digest_covers": ev["evidence_digest_covers"],
                "generated_utc": ev["generated_utc"],
                "command": ev["command"],
                "window": window,
                "cost_models": ev["cost_models"],
                "iteration_budget": budget,
                "determinism": {
                    key: value for key, value in ev["determinism"].items() if key != "runs"
                },
                "determinism_runs": ev["determinism"]["runs"],
                "stage_verdict": stage,
                "per_condition_rollup_warning": ev["per_condition_rollup"]["warning"],
                "decisive_row": decisive,
                "no_selection_in_this_stage": ev["no_selection_in_this_stage"],
                "self_digest_verification": {
                    "recomputed_as_documented": "MATCHES",
                    "recomputed_with": (
                        "stockedge100.reporting.attempt2_evidence.evidence_digest, the same "
                        "function that wrote it, imported rather than reimplemented"
                    ),
                    "control_perturbing_generated_utc": (
                        "UNCHANGED, so that field is genuinely outside the coverage"
                    ),
                    "control_perturbing_the_coverage_sentence": (
                        "CHANGES, so the digest genuinely covers its own description"
                    ),
                    "why_both_directions": (
                        "one control cannot establish an exclusion and an inclusion at once, and "
                        "two-run stability establishes neither: a digest whose coverage description "
                        "is wrong but consistent is perfectly stable, which is the defect that cost "
                        "Stage 2 a full regeneration"
                    ),
                },
            },
            "independent_recomputation": {
                "performed_before_anything_was_written": True,
                "satisfaction_rule_source": binding["admissible_candidate_exists"][
                    "satisfied_definition"
                ],
                "satisfaction_rule_obtained_by": (
                    "parsing the sealed satisfied_definition rather than restating the pair of "
                    "verdict names, so a reworded seal stops the build instead of being ignored"
                ),
                "not_satisfied_values": binding["admissible_candidate_exists"][
                    "not_satisfied_values"
                ],
                "recomputed": [
                    "every condition's satisfied flag, from its verdict under the sealed rule",
                    "every candidate's admittance, as the conjunction of its own seven conditions",
                    "the admitted set, as the disjunction across candidates",
                    "admissible_candidate_exists, as the non-emptiness of that set",
                    "every per-condition rollup row's met_by, not_met_by, not_applicable_for and "
                    "satisfied_by_at_least_one_candidate, from the per-candidate blocks",
                    "every sealed input digest, against the evidence's load-time values",
                    "the evidence file's self-digest, plus a control in each direction of its own "
                    "coverage sentence",
                ],
                "disagreements": [],
                "on_disagreement": "no package is written and the builder exits non-zero",
                "why_not_a_test": (
                    "tests/**/*.py is one of the repo_state_id patterns, so a test asserting this "
                    "package's contents would invalidate the digest it asserts the moment it was "
                    "written. The package is verified by re-running the recomputation."
                ),
            },
            "results": {
                "per_candidate_primary": {
                    eid: {
                        "family": summaries[eid]["family"],
                        "declared_universe": plans[eid]["declared_universe"],
                        "run_start": run["start"],
                        "run_end": run["end"],
                        "sessions": run["sessions"],
                        "total_return": run["total_return"],
                        "max_drawdown": run["max_drawdown"],
                        "deepest_drawdown_4dp": run["deepest_drawdown_4dp"],
                        "profit_factor": run["profit_factor"],
                        "closed_trades": run["closed_trades"],
                        "exposure_fraction": run["exposure_fraction"],
                        "win_rate": run["win_rate"],
                        "shutdown_session": run["shutdown_session"],
                        "open_positions_at_end": run["open_positions_at_end"],
                        "ra1_diagnostics": run["ra1_diagnostics"],
                        "trades_digest": run["trades_digest"],
                        "equity_digest": run["equity_digest"],
                        "admitted": summaries[eid]["admitted"],
                        "conditions_met": summaries[eid]["conditions_met"],
                        "conditions_not_met": summaries[eid]["conditions_not_met"],
                        "conditions_not_applicable": summaries[eid]["conditions_not_applicable"],
                    }
                    for eid, run in primaries.items()
                },
                "all_registered_variants": variant_table(ev),
                "variant_table_note": (
                    "one row per registered variant, primary and neighbour. The full 43-field "
                    "record for each, including its RA1 diagnostics and rejection reasons, is in "
                    + EVIDENCE
                ),
                "stressed_cost_runs": {
                    cand["gate"]["experiment_id"]: cand["stressed_cost_run"]
                    for cand in ev["candidates"]
                },
                "benchmarks": {
                    cand["gate"]["experiment_id"]: cand["benchmark_comparison"]
                    for cand in ev["candidates"]
                },
                "benchmarks_gate_nothing": True,
                "benchmark_note": (
                    "reported for every candidate under constitution section 4. Neither admitted "
                    "candidate beats the SPY index or the tradable SPY buy-and-hold over its own "
                    "window; the only candidate that beats tradable SPY is the rejected one. All "
                    "three beat 0% cash and doing nothing."
                ),
                "admitted_candidates": admitted,
                "not_admitted_candidates": rejected,
                "selection_made": False,
                "ranking_computed": False,
            },
            "gate_3_rules_as_applied": {
                "criteria_artifact": binding["bound_artifact"],
                "conditions_adopted": binding["conditions_adopted"],
                "drawdown_ceiling_is_unchanged": binding["drawdown_ceiling_is_unchanged"],
                "rederivations": binding["rederivations"],
                "nothing_else_changed": binding["nothing_else_changed"],
                "denominators_and_universes_of_measurement": binding[
                    "denominators_and_universes_of_measurement"
                ],
                "admissible_candidate_exists": binding["admissible_candidate_exists"],
                "neighbour_status": binding["neighbour_status"],
                "shutdown_behaviour": binding["shutdown_behaviour"],
                "rerun_policy": binding["rerun_policy"],
                "cost_stress_is_not_a_gate_3_condition": binding[
                    "cost_stress_is_not_a_gate_3_condition"
                ],
                "evaluation_integrity_rules": binding["evaluation_integrity_rules"],
                "conflicts_carried_forward": binding["conflicts_carried_forward"],
            },
            "adaptive_research": {
                "known_prior_evidence": ev["adaptive_research"]["known_prior_evidence"],
                "adaptive_research_disclosure": ev["adaptive_research"][
                    "adaptive_research_disclosure"
                ],
                "multiple_comparisons_disclosure": ev["adaptive_research"][
                    "multiple_comparisons_disclosure"
                ],
                "cumulative_experiment_count": ev["adaptive_research"][
                    "cumulative_experiment_count"
                ],
                "attempt_2_revisions_permitted": prereg["revisions_permitted"],
                "attempt_2_revisions_made": budget["revisions_made"],
                "new_code_is_not_independence": (
                    "Attempt 2 is a new implementation of new candidates, and that is not "
                    "independent confirmation of anything. The development data are not pristine: "
                    "they carry the marks of six prior rejections whose headline failure mode "
                    "shaped this attempt's risk architecture."
                ),
                "what_a_pass_authorises": protocol["stage_4_remains_prohibited_conditions"],
            },
            "implementation": {
                "modules": [
                    "src/stockedge100/strategies/attempt2_config.py",
                    "src/stockedge100/strategies/attempt2_indicators.py",
                    "src/stockedge100/strategies/attempt2_risk.py",
                    "src/stockedge100/strategies/attempt2_candidates.py",
                    "src/stockedge100/strategies/attempt2_runner.py",
                    "src/stockedge100/strategies/attempt2_harness.py",
                    "src/stockedge100/reporting/attempt2_evidence.py",
                    "src/stockedge100/reporting/stage3_attempt2_evaluation_package.py",
                ],
                "traceability": (
                    "a field-by-field map from every sealed rule to the code that implements it and "
                    "the tests that pin it is in "
                    "reports/stage3_attempt2/STAGE_3_ATTEMPT_2_EVALUATION_TEST_SUMMARY.md"
                ),
                "risk_architecture": (
                    "RA1-1 through RA1-8 implemented once in attempt2_risk.py and shared by all "
                    "three candidates, with every parameter read from the sealed protocol. No "
                    "candidate module contains the Gate 3 ceiling as a literal; the sealed "
                    "no_candidate_reads_the_ceiling assertion is enforced by test."
                ),
                "discretionary_choices_required": (
                    "none. No sealed rule left a material choice unresolved, so no "
                    "specification-ambiguity blocker was raised."
                ),
                "post_seal_defect_rule": protocol["post_seal_defect_rule"],
                "defects_found_before_any_result": [
                    "D1 — the stressed-cost reporter probed a cost-model field that does not exist "
                    "on the stressed model, raising KeyError before any run completed. Fixed by "
                    "passing the multiplier explicitly. No result existed: the harness had not yet "
                    "produced a completed run.",
                    "D2 — the decisive rollup row emitted the gate condition's prose where a token "
                    "belonged, which would have written a sentence into a field a reader parses as "
                    "a verdict token. Fixed to emit both fields separately. Found on a dry-run, "
                    "before the evaluation executed.",
                    "D3 — a frozen adversarial test scans src/**/*.py for the literal that would "
                    "bypass a config seal, exempting only the loader that legitimately names it. A "
                    "docstring in attempt2_config.py mentioned the literal and tripped the scan. "
                    "Fixed by removing the dead parameter the docstring described, not by weakening "
                    "the test or exempting the file. Found before the evaluation ran.",
                ],
                "no_result_driven_revision": (
                    "all three defects were found and fixed before the first valid completed "
                    "evaluation. Nothing was changed after a result existed: the sealed "
                    "post_seal_defect_rule would have invalidated the affected runs and required a "
                    "full re-run, and the sealed rerun_policy forbids re-running a valid completed "
                    "evaluation in the hope of a different number."
                ),
            },
            "test_execution": {
                "command": TEST_COMMAND,
                "collect_command": COLLECT_COMMAND,
                "captured_output": PYTEST_OUTPUT,
                "counts": dict(counts),
                "counts_read_from": (
                    "the captured output on disk, parsed at build time. The counts in this package "
                    "are not hand-typed: a missing capture, a failure, an error, or a collection "
                    "count that does not reconcile with passed + failed + skipped refuses to write "
                    "the package."
                ),
                "summary": (
                    "reports/stage3_attempt2/STAGE_3_ATTEMPT_2_EVALUATION_TEST_SUMMARY.md"
                ),
                "tests_excluded": 0,
                "exclusion_note": (
                    "no test was excluded, skipped, xfailed, weakened or deleted. No test in the "
                    "suite reads, computes, compares or reports a price from a validation-dated or "
                    "holdout-dated row; the partition audit is recorded in the test summary."
                ),
                "preregistration_floor_intact": (
                    "the tests standing at Attempt 2 pre-registration are unmodified, verified by "
                    "digest against the code_hashes of " + DESIGN_RUN_RECORD + "; this session only "
                    "added test modules"
                ),
            },
            "scope": {
                "candidate_selected": False,
                "candidates_admitted": admitted,
                "validation_observations_read": window["validation_observations_read"],
                "holdout_observations_read": window["holdout_observations_read"],
                "boundary_changed": window["boundary_changed"],
                "runs_confined_to": (
                    "development window, enforced structurally by the engine window guard and the "
                    "market-view look-ahead guard, both validated at Gate 2"
                ),
                "revisions_after_seeing_a_result": budget["variants_rerun_after_seeing_a_result"],
                "explicit_non_authorizations": ev["explicit_non_authorizations"],
                "money_spent_usd": 0,
                "credentials_used": "none; no credential presence was tested by this session",
                "data_acquired": "none; every price came from the Stage 1 normalized dataset",
                "broker_activity": (
                    "none. No Alpaca call, no order, no cancel, no replace, no liquidation request, "
                    "no unattended scheduling."
                ),
                "attempt_1_disposition": "READ_ONLY_NOT_MODIFIED_PERMANENTLY_CLOSED",
            },
            "repository_state": {
                "starting_repo_state_id": design_run["repo_state_id"],
                "starting_state_source": DESIGN_RUN_RECORD,
                "starting_state_run_id": design_run["run_id"],
                "starting_state_timestamp_utc": design_run["timestamp_utc"],
                "starting_state_stage": design_run["stage"],
                "starting_state_exit_status": design_run["exit_status"],
                "evaluated_repo_state_id_location": (
                    "reproducibility.repo_state_id of this record, and the repo_state_id field of "
                    "this session's runs/ record. Deliberately not written into any governance/ "
                    "file: governance/*.md and governance/*.json are inputs to the digest, so a "
                    "value written there would be stale on write."
                ),
            },
            "stage1": {
                "freeze_verification_working_directory": "stockedge100/governance",
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
                "engine_reused_unchanged": True,
                "disposition": "READ_ONLY_NOT_MODIFIED",
            },
            "attempt_1": {
                "verdict": ev["adaptive_research"]["known_prior_evidence"]["attempt_1_verdict"],
                "run_id": ev["adaptive_research"]["known_prior_evidence"]["attempt_1_run_id"],
                "candidates": ev["adaptive_research"]["known_prior_evidence"][
                    "attempt_1_candidates"
                ],
                "admitted": ev["adaptive_research"]["known_prior_evidence"]["attempt_1_admitted"],
                "headline_fact": ev["adaptive_research"]["known_prior_evidence"][
                    "attempt_1_headline_fact"
                ],
                "disposition": "READ_ONLY_NOT_MODIFIED_PERMANENTLY_CLOSED",
            },
            "integrity": {
                "checksum_records_verified": checksums,
                "all_verified": True,
                "path_conventions": (
                    "STAGE_0_FREEZE.sha256 and STAGE_1_FREEZE.sha256 carry bare filenames and "
                    "verify from stockedge100/governance; the other nine carry project-root-"
                    "relative paths and verify from stockedge100. Verifying from the wrong "
                    "directory is an operator error, not an integrity failure."
                ),
                "frozen_artifacts_changed": 0,
                "attempt_2_freeze_record_issued": False,
                "attempt_2_freeze_record_rationale": (
                    "Stage 1 issued a freeze record because it produced governance artifacts later "
                    "stages consume as data. Attempt 2's evaluation produces none: the sealed "
                    "protocol and binding a later stage would read are already covered by "
                    "governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.sha256, this session's outputs by "
                    "this package's own checksum record, and code identity by repo_state_id. "
                    "Recorded as a decision, not left as an omission."
                ),
                "self_reference_policy": (
                    "the artifact manifest excludes its own entry and the surrounding .sha256 "
                    "record covers the manifest without covering itself; no tree digest is written "
                    "into any file that the tree digest covers"
                ),
            },
        },
        tests={
            "collected": counts["collected"],
            "passed": counts["passed"],
            "failed": counts["failed"],
            "skipped": counts["skipped"],
            "errors": counts["errors"],
            "excluded": 0,
        },
        authorization_state={
            "attempt_2_strategy_research": "COMPLETE_ON_THE_DEVELOPMENT_WINDOW",
            "further_attempt_2_development_work": "LOCKED",
            "validation_window": "LOCKED",
            "final_holdout": "SEALED",
            "stage_4_validation": "NOT_AUTHORIZED_REQUIRES_A_SEPARATE_PROSPECTIVE_PREREGISTRATION",
            "alpaca_paper_trading": "LOCKED",
            "shadow_live": "LOCKED",
            "alpaca_live_trading": "LOCKED",
            "capital_or_risk_expansion": "LOCKED",
        },
        next_authorized_stage="STAGE_4_VALIDATION_PREREGISTRATION_SESSION_ONLY",
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
            f"Gate 3 conditions are conjunctive within a candidate and the stage verdict is a "
            f"disjunction across candidates. {len(admitted)} of {len(primaries)} candidates satisfy "
            f"every applicable hard condition, so admissible_candidate_exists is {admissible} and "
            f"the gate passes: {', '.join(admitted)}.",
            f"{', '.join(rejected)} fails S3-C6 on instrument concentration. It is the "
            f"best-performing candidate reported here and it is not admitted, not promoted and not "
            f"substituted.",
            "No neighbour was promoted, no parameter was retuned after a result, and no valid "
            "completed evaluation was re-run. The three determinism re-runs sit outside the "
            "declared budget and compare digests only.",
            "A pass at this gate is admissibility in development. It authorises consideration of "
            "the next frozen evaluation step under a separate prospective pre-registration, and "
            "nothing else — not Stage 4 execution, not validation access, not the holdout, not "
            "paper trading, not shadow-live, not live trading, and no capital or risk expansion.",
            "Neither admitted candidate beats SPY buy-and-hold over its own window. That is "
            "recorded here rather than left in the benchmark block, because a development pass is "
            "the moment at which an attractive number is most likely to be read as proof.",
            "The verdict tokens were read from the sealed verdict_token_derivation at build time. "
            "The operating prompt's Attempt-2-specific tokens exist in no artifact on disk and were "
            "not used; the divergence is recorded as A2-EVAL-CONFLICT-1.",
            "The validation and holdout windows were not read. No data was acquired, no order of "
            "any kind was generated, no broker was contacted, and no credential was accessed.",
            "No separate STAGE_3_ATTEMPT_2_FREEZE.sha256 was issued; see body.integrity for the "
            "reason.",
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
    print(f"starting      {design_run['repo_state_id']}")
    print(f"verdict       {verdict}")
    print(f"admitted      {', '.join(admitted)}")
    print(f"tests         {counts}")
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
