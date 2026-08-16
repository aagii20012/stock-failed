"""Probe every key the Attempt 2 package builder indexes, before the builder is ever run.

The builder lives in ``src/``, which ``repo_state_id`` covers, so a KeyError discovered after the
real build cannot be fixed without invalidating the digest that build just recorded. This script
resolves each accessor the builder makes and reports MISSING rather than raising, so one pass names
every problem instead of the first one. ASCII output only.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
MISSING = object()


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


protocol = load("config/generation_2/g2_rotation_ra1_protocol.json")
criteria = load("config/generation_2/g2_gate_criteria_ra1.json")
lock = load("governance/generation_2/STAGE_1_G2_PARTITION_LOCK.json")
ev = load("reports/stage3_g2_attempt2/STAGE_3_G2_A2_DEVELOPMENT_ADMISSIBILITY.json")

problems = []


def probe(label, obj, *path):
    cur = obj
    for key in path:
        if isinstance(cur, dict):
            cur = cur.get(key, MISSING)
        elif isinstance(cur, list) and isinstance(key, int) and key < len(cur):
            cur = cur[key]
        else:
            cur = MISSING
        if cur is MISSING:
            break
    trail = "%s[%s]" % (label, "][".join(repr(p) for p in path))
    if cur is MISSING:
        problems.append(trail)
        print("  MISSING  %s" % trail)
        return MISSING
    if isinstance(cur, (dict, list)):
        shown = "%s(%d)" % (type(cur).__name__, len(cur))
    else:
        shown = str(cur).replace("\n", " ")[:80].encode("ascii", "backslashreplace").decode("ascii")
    print("  ok       %-72s %s" % (trail, shown))
    return cur


print("== protocol accessors ==")
for key in ("adaptation_disclosure_verbatim", "adaptation_disclosure_carriage_requirement",
            "attempt", "strategy_id", "candidate_index", "family", "attempt_1_ref",
            "what_this_attempt_adds_over_attempt_1", "generation_id",
            "what_makes_this_genuinely_cross_sectional", "declared_before_any_strategy_code",
            "declared_before_any_strategy_code_measurement", "hypothesis", "risk_architecture",
            "structural_consequences_declared_before_running", "explicit_non_authorizations",
            "multiple_comparisons_disclosure", "runs_per_variant", "run_span", "eligible_universe"):
    probe("protocol", protocol, key)

print()
print("== protocol nested ==")
probe("protocol", protocol, "adaptation_disclosure_carriage_requirement", "must_appear_verbatim_in")
probe("protocol", protocol, "adaptation_disclosure_carriage_requirement", "enforcement")
probe("protocol", protocol, "adaptation_disclosure_carriage_requirement", "encoding_note")
probe("protocol", protocol, "risk_architecture", "components")
probe("protocol", protocol, "risk_architecture", "combined_scalar")
probe("protocol", protocol, "risk_architecture", "frozen_before_any_variant_is_run")
probe("protocol", protocol, "risk_architecture", "not_part_of_the_grid")
probe("protocol", protocol, "risk_architecture", "why_not_gridded")
probe("protocol", protocol, "risk_architecture", "provenance")
probe("protocol", protocol, "multiple_comparisons_disclosure", "adaptive_design_note")
probe("protocol", protocol, "runs_per_variant", "labels")
probe("protocol", protocol, "run_span", "run_start")
probe("protocol", protocol, "run_span", "run_end")
probe("protocol", protocol, "eligible_universe", "universe_version")

print()
print("== criteria accessors ==")
probe("criteria", criteria, "conditions")
probe("criteria", criteria, "verdict_token_derivation", "pass_token")
probe("criteria", criteria, "verdict_token_derivation", "fail_token")
probe("criteria", criteria, "verdict_token_derivation", "fail_is_a_deliverable")
probe("criteria", criteria, "verdict_token_derivation", "constitutional_fail_result_equivalent")
print("  condition ids:", [c.get("id") for c in criteria["conditions"]])
for cond in criteria["conditions"]:
    for key in ("id", "required_verbatim"):
        if key not in cond:
            problems.append("criteria.conditions[%s].%s" % (cond.get("id"), key))
            print("  MISSING  criteria condition %s key %s" % (cond.get("id"), key))
    print("    %-8s keys=%s" % (cond.get("id"), sorted(cond)))

print()
print("== lock accessors ==")
for key in ("validation_reuse_disclosure", "partition", "generation_1_holdout_state",
            "holdout_state"):
    probe("lock", lock, key)

print()
print("== evidence accessors ==")
for key in ("stage_verdict", "selection", "determinism", "window", "reconciliation",
            "attempt_1_module_verification", "candidate_results", "grid", "risk_architecture",
            "universe", "gate_scope", "run_span_recheck", "variant_table",
            "variant_table_is_descriptive_only", "reported_for_every_variant_coverage",
            "evidence_digest", "evidence_digest_covers", "generated_utc", "artifact_id"):
    probe("ev", ev, key)

print()
print("== evidence nested ==")
probe("ev", ev, "adaptation_disclosure_carriage", "sha256_of_utf8")
probe("ev", ev, "window", "generation_2_holdout_read")
probe("ev", ev, "window", "latest_session_loaded")
probe("ev", ev, "window", "development_bound")
probe("ev", ev, "window", "enforcement")
probe("ev", ev, "reconciliation", "mismatches_total")
probe("ev", ev, "reconciliation", "vacuous_runs")
probe("ev", ev, "reconciliation", "runs_reconciled")
probe("ev", ev, "reconciliation", "single_leg_compared_total")
probe("ev", ev, "attempt_1_module_verification", "modules_that_moved")
probe("ev", ev, "attempt_1_module_verification", "module_count")
probe("ev", ev, "determinism", "fields_compared")
probe("ev", ev, "determinism", "runs_compared")
probe("ev", ev, "grid", "runs_executed")
probe("ev", ev, "selection", "variants_considered")
probe("ev", ev, "selection", "representative_variant_id")
probe("ev", ev, "selection", "return_blind_enforcement")
probe("ev", ev, "selection", "selection_note")
probe("ev", ev, "selection", "step_1", "eligible_count")
probe("ev", ev, "selection", "step_2")
probe("ev", ev, "stage_verdict", "admitted_candidates")
probe("ev", ev, "stage_verdict", "candidates_evaluated")
probe("ev", ev, "stage_verdict", "representative_exists")
probe("ev", ev, "stage_verdict", "verdict_token")

print()
print("== candidate accessors ==")
probe("ev", ev, "candidate_results", 0, "variant_id")
probe("ev", ev, "candidate_results", 0, "conditions")
probe("ev", ev, "candidate_results", 0, "stress_evaluation", "conditions")
probe("ev", ev, "candidate_results", 0, "admission_basis", "base_conditions_not_satisfied")
probe("ev", ev, "candidate_results", 0, "admission_basis", "stress_conditions_not_satisfied")
probe("ev", ev, "candidate_results", 0, "admission_basis",
      "s3_c7_stress_side_reported_not_gating")
probe("ev", ev, "candidate_results", 0, "admission_basis",
      "permissive_base_only_reading_would_give")
probe("ev", ev, "candidate_results", 0, "conditions", 2, "measured")

print()
print("== variant_table columns the evidence bullets index ==")
row = ev["variant_table"][0]
print("  columns:", sorted(row))
for key in ("base_max_drawdown", "stress_max_drawdown"):
    if key not in row:
        problems.append("variant_table[0].%s" % key)
        print("  MISSING  variant_table[0].%s" % key)

print()
print("== selection step_2 shape ==")
print(" ", json.dumps(ev["selection"]["step_2"])[:600])

print()
print("== s3_c7 non-gating marker ==")
marker = ev["candidate_results"][0]["admission_basis"]["s3_c7_stress_side_reported_not_gating"]
print("  type:", type(marker).__name__)
print(" ", json.dumps(marker)[:500])

print()
if problems:
    print("PROBLEMS (%d):" % len(problems))
    for item in problems:
        print("  -", item)
else:
    print("OK: every accessor the builder makes resolves")
