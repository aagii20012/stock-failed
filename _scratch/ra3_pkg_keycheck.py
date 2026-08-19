"""Seventeenth pass: existence check for exactly the keys g2_stage3_attempt3_package.py will read.

Cheaper than a dry-run KeyError, and the module is about to be written against this list.
"""

import json
import pathlib

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


EV = load("reports/stage3_g2_attempt3/STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json")
PROT = load("config/generation_2/g2_rotation_ra3_protocol.json")
CRIT = load("config/generation_2/g2_gate_criteria_ra3.json")
LOCK = load("governance/generation_2/STAGE_1_G2_PARTITION_LOCK.json")

MISSING = []


def probe(label, node, *path):
    cur = node
    for key in path:
        try:
            cur = cur[key]
        except (KeyError, IndexError, TypeError):
            MISSING.append("%s%s" % (label, list(path)))
            print("MISSING  %s%s" % (label, list(path)))
            return None
    kind = type(cur).__name__
    shown = safe(json.dumps(cur, default=str))
    if len(shown) > 110:
        shown = shown[:110] + "..."
    extra = ""
    if isinstance(cur, dict):
        extra = "  keys=%s" % safe(sorted(cur))[:180]
    print("ok  %-58s %-6s %s%s" % ("%s.%s" % (label, ".".join(str(p) for p in path)),
                                   kind, shown, extra))
    return cur


print("=" * 110)
print("EV.stage_verdict")
for k in ("verdict", "verdict_token", "admitted_candidates", "representative_exists",
          "candidates_evaluated", "fail_route", "prior_attempt_tokens_withheld",
          "constitutional_equivalent"):
    probe("EV", EV, "stage_verdict", k)

print("=" * 110)
print("EV.selection")
probe("EV", EV, "selection", "outcome")
probe("EV", EV, "selection", "return_blind")
probe("EV", EV, "selection", "selection_input_fields")
probe("EV", EV, "selection", "decided_at_step")
probe("EV", EV, "selection", "rule_id")
probe("EV", EV, "selection", "result", "eligible_count")
probe("EV", EV, "selection", "result", "selected_variant_id")
probe("EV", EV, "selection", "result", "decided_at_step")
probe("EV", EV, "selection", "steps")
probe("EV", EV, "selection", "selected_score", "instability_score")
probe("EV", EV, "selection", "selected_score", "neighbour_count")
probe("EV", EV, "selection", "selected_score", "per_quantity_mean_dissimilarity")
probe("EV", EV, "selection", "selected_score", "own_quantities")
probe("EV", EV, "selection", "runner_up")
probe("EV", EV, "selection", "all_scores")
probe("EV", EV, "selection", "neighbour_scores")
probe("EV", EV, "selection", "selection_note")
probe("EV", EV, "selection", "note")
print("   selection keys: %s" % safe(sorted(EV["selection"])))

print("=" * 110)
for path in (("grid", "variants_declared"), ("grid", "runs_executed"),
             ("prior_attempt_module_verification", "module_count"),
             ("prior_attempt_module_verification", "modules_that_moved"),
             ("determinism", "all_identical"), ("determinism", "runs_compared"),
             ("determinism", "fields_compared"),
             ("selection_determinism", "all_identical"),
             ("ladder_engagement_comparison", "at_least_one_statistic_differs"),
             ("ladder_engagement_comparison", "runs_compared"),
             ("ladder_engagement_comparison", "attempt_2_source"),
             ("window", "validation_read"), ("window", "generation_1_holdout_read"),
             ("window", "generation_2_holdout_read"), ("window", "latest_session_loaded"),
             ("window", "development_bound"), ("window", "enforcement"),
             ("reconciliation", "runs_reconciled"),
             ("reconciliation", "single_leg_compared_total"),
             ("reconciliation", "mismatches_total"), ("reconciliation", "vacuous_runs"),
             ("adaptation_disclosure_carriage", "sha256_of_utf8"),
             ("artifact_id",), ("evidence_digest",), ("evidence_digest_covers",),
             ("generated_utc",), ("universe",), ("run_span_recheck",),
             ("risk_architecture", "as_loaded"),
             ("risk_architecture", "single_difference_from_ra2"),
             ("variant_table_is_descriptive_only",),
             ("reported_for_every_variant_coverage",), ("refs_reverified",),
             ("multiple_comparisons_disclosure", "cumulative_variants_this_hypothesis_family"),
             ("multiple_comparisons_disclosure", "cumulative_runs_this_hypothesis_family"),
             ("multiple_comparisons_disclosure", "adaptive_design_note"),
             ("generation_1_provenance",)):
    probe("EV", EV, *path)

print("=" * 110)
print("PROT")
for path in (("attempt",), ("strategy_id",), ("candidate_index",), ("family",),
             ("generation_id",), ("artifact_id",),
             ("runs_per_variant", "labels"),
             ("representative_selection_rule", "id"),
             ("representative_selection_rule", "structural_enforcement", "mechanism"),
             ("prior_attempt_modules_immutable",),
             ("adaptation_disclosure_carriage_requirement", "enforcement"),
             ("adaptation_disclosure_carriage_requirement", "encoding_note"),
             ("adaptation_disclosure_carriage_requirement", "must_appear_verbatim_in"),
             ("risk_architecture", "components"),
             ("risk_architecture", "combined_scalar"),
             ("risk_architecture", "frozen_before_any_variant_is_run"),
             ("risk_architecture", "not_part_of_the_grid"),
             ("risk_architecture", "why_not_gridded"),
             ("risk_architecture", "provenance"),
             ("risk_architecture", "single_change_from_ra2"),
             ("eligible_universe", "universe_version"),
             ("run_span", "run_start"), ("run_span", "run_end"),
             ("explicit_non_authorizations",),
             ("multiple_comparisons_disclosure", "adaptive_design_note"),
             ("hypothesis",), ("declared_before_any_strategy_code",),
             ("declared_before_any_strategy_code_measurement",),
             ("concentration_ceiling",),
             ("attempt_1_ref",), ("attempt_2_ref",), ("prior_attempts_ref",),
             ("what_this_attempt_changes_from_attempt_2",),
             ("what_this_attempt_adds_over_attempt_2",),
             ("structural_consequences_declared_before_running",),
             ("generation_1_provenance",)):
    probe("PROT", PROT, *path)
print("   PROT keys: %s" % safe(sorted(PROT)))

print("=" * 110)
print("CRIT")
for path in (("verdict_token_derivation", "pass_token"),
             ("verdict_token_derivation", "fail_token"),
             ("verdict_token_derivation", "fail_is_a_deliverable"),
             ("verdict_token_derivation", "constitutional_fail_result_equivalent"),
             ("verdict_token_derivation", "prior_attempt_tokens_are_not_available_here"),
             ("verdict_token_derivation", "fail_routes"),
             ("conditions",), ("artifact_id",)):
    probe("CRIT", CRIT, *path)
print("   CRIT keys: %s" % safe(sorted(CRIT)))

print("=" * 110)
print("LOCK")
for path in (("validation_reuse_disclosure",), ("partition",),
             ("generation_1_holdout_state",), ("holdout_state",)):
    probe("LOCK", LOCK, *path)

print("=" * 110)
print("MISSING TOTAL: %d" % len(MISSING))
for m in MISSING:
    print("   %s" % m)
