"""Tenth pass: assert every key path g2_stage3_attempt3_package.py intends to dereference.

Prints PRESENT/MISSING for each path rather than raising, so one run lists every gap instead of
stopping at the first. Short values are shown ASCII-laundered; long ones are summarised.
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

SOURCES = {"EV": EV, "PROT": PROT, "CRIT": CRIT, "LOCK": LOCK}

PATHS = [
    # ---- criteria: token derivation ----
    "CRIT.verdict_token_derivation",
    "CRIT.verdict_token_derivation.pass_token",
    "CRIT.verdict_token_derivation.fail_token",
    "CRIT.verdict_token_derivation.constitutional_fail_result_equivalent",
    "CRIT.verdict_token_derivation.fail_is_a_deliverable",
    "CRIT.verdict_token_derivation.prior_attempt_tokens_are_not_available_here",
    "CRIT.conditions",
    # ---- protocol: identity / preregistration ----
    "PROT.attempt",
    "PROT.strategy_id",
    "PROT.candidate_index",
    "PROT.family",
    "PROT.generation_id",
    "PROT.attempt_1_ref",
    "PROT.attempt_2_ref",
    "PROT.what_this_attempt_changes_from_attempt_2",
    "PROT.declared_before_any_strategy_code",
    "PROT.declared_before_any_strategy_code_measurement",
    "PROT.hypothesis",
    "PROT.structural_consequences_declared_before_running",
    "PROT.explicit_non_authorizations",
    "PROT.eligible_universe.universe_version",
    "PROT.run_span.run_start",
    "PROT.run_span.run_end",
    "PROT.runs_per_variant.labels",
    "PROT.multiple_comparisons_disclosure",
    "PROT.multiple_comparisons_disclosure.adaptive_design_note",
    "PROT.multiple_comparisons_disclosure.third_attempt_note",
    "PROT.adaptation_disclosure_verbatim",
    "PROT.adaptation_disclosure_carriage_requirement.must_appear_verbatim_in",
    "PROT.adaptation_disclosure_carriage_requirement.enforcement",
    "PROT.adaptation_disclosure_carriage_requirement.encoding_note",
    "PROT.adaptation_disclosure_carriage_requirement.attempt_3_encoding_addendum",
    "PROT.prior_attempt_modules_immutable",
    # ---- protocol: risk architecture ----
    "PROT.risk_architecture.components",
    "PROT.risk_architecture.combined_scalar",
    "PROT.risk_architecture.frozen_before_any_variant_is_run",
    "PROT.risk_architecture.not_part_of_the_grid",
    "PROT.risk_architecture.why_not_gridded",
    "PROT.risk_architecture.provenance",
    "PROT.risk_architecture.single_difference_from_ra2",
    # ---- protocol: selection rule ----
    "PROT.representative_selection_rule",
    "PROT.representative_selection_rule.rule_id",
    "PROT.representative_selection_rule.steps",
    "PROT.representative_selection_rule.replaces",
    "PROT.representative_selection_rule.why_it_changes",
    "PROT.representative_selection_rule.structural_enforcement",
    "PROT.representative_selection_rule.retrospective_check_disclosure",
    "PROT.representative_selection_rule.no_candidate_path",
    "PROT.representative_selection_rule.second_fail_path",
    # ---- evidence: top-level nodes the body copies ----
    "EV.artifact_id",
    "EV.generated_utc",
    "EV.evidence_digest",
    "EV.evidence_digest_covers",
    "EV.command",
    "EV.universe",
    "EV.grid",
    "EV.grid.runs_executed",
    "EV.grid.variants_declared",
    "EV.gate_scope",
    "EV.variant_table",
    "EV.variant_table_is_descriptive_only",
    "EV.reported_for_every_variant_coverage",
    "EV.run_span_recheck",
    "EV.window",
    "EV.window.latest_session_loaded",
    "EV.window.development_bound",
    "EV.window.enforcement",
    "EV.window.validation_read",
    "EV.window.generation_1_holdout_read",
    "EV.window.generation_2_holdout_read",
    "EV.determinism",
    "EV.determinism.all_identical",
    "EV.determinism.runs_compared",
    "EV.determinism.fields_compared",
    "EV.reconciliation",
    "EV.reconciliation.runs_reconciled",
    "EV.reconciliation.single_leg_compared_total",
    "EV.reconciliation.mismatches_total",
    "EV.reconciliation.vacuous_runs",
    "EV.risk_architecture",
    "EV.risk_architecture.as_loaded",
    "EV.risk_architecture.sealed",
    "EV.ladder_engagement_comparison",
    "EV.ladder_engagement_comparison.per_statistic",
    "EV.prior_attempt_module_verification",
    "EV.prior_attempt_module_verification.module_count",
    "EV.prior_attempt_module_verification.modules_that_moved",
    "EV.prior_attempt_module_verification.attempt_1_module_count",
    "EV.prior_attempt_module_verification.attempt_2_module_count",
    "EV.selection",
    "EV.selection.result.eligible_count",
    "EV.selection.result.selected_variant_id",
    "EV.selection.result.decided_at_step",
    "EV.selection.steps",
    "EV.selection.selection_input_fields",
    "EV.selection.scored_quantities",
    "EV.selection.selected_score",
    "EV.selection.neighbour_scores",
    "EV.selection_determinism",
    "EV.selection_determinism.all_identical",
    "EV.selection_determinism.inputs_replayed",
    "EV.adaptation_disclosure_carriage.sha256_of_utf8",
    "EV.multiple_comparisons_disclosure",
    "EV.conflicts_declared_in_the_gate_criteria",
    "EV.refs_reverified",
    "EV.candidate_results",
    "EV.stage_verdict.verdict",
    "EV.stage_verdict.verdict_token",
    "EV.stage_verdict.admitted_candidates",
    "EV.stage_verdict.candidates_evaluated",
    "EV.stage_verdict.representative_exists",
    "EV.stage_verdict.selection_note",
    "EV.stage_verdict.fail_route",
    "EV.stage_verdict.prior_attempt_tokens_withheld",
    # ---- candidate ----
    "EV.candidate_results.0.variant_id",
    "EV.candidate_results.0.conditions",
    "EV.candidate_results.0.stress_evaluation.conditions",
    "EV.candidate_results.0.admission_basis.base_conditions_not_satisfied",
    "EV.candidate_results.0.admission_basis.stress_conditions_not_satisfied",
    "EV.candidate_results.0.admission_basis.permissive_base_only_reading_would_give",
    "EV.candidate_results.0.admission_basis.s3_c7_stress_side_reported_not_gating.id",
    "EV.candidate_results.0.non_vacuity_check",
    # ---- partition lock ----
    "LOCK.validation_reuse_disclosure",
    "LOCK.partition",
    "LOCK.generation_1_holdout_state",
    "LOCK.holdout_state",
]


def walk(path):
    parts = path.split(".")
    node = SOURCES[parts[0]]
    for part in parts[1:]:
        if isinstance(node, list):
            idx = int(part)
            if idx >= len(node):
                raise KeyError(part)
            node = node[idx]
        else:
            node = node[part]
    return node


missing = []
for path in PATHS:
    try:
        value = walk(path)
    except (KeyError, TypeError, ValueError) as exc:
        missing.append(path)
        print("MISSING  %-72s (%s: %s)" % (path, type(exc).__name__, safe(exc)))
        continue
    if isinstance(value, (dict, list)):
        kind = "dict[%d]" % len(value) if isinstance(value, dict) else "list[%d]" % len(value)
        extra = sorted(value)[:9] if isinstance(value, dict) else ""
        print("ok       %-72s %s %s" % (path, kind, safe(extra)))
    else:
        print("ok       %-72s %s" % (path, safe(json.dumps(value, default=str))[:130]))

print("=" * 100)
print("MISSING COUNT: %d" % len(missing))
for path in missing:
    print("   %s" % path)

print("=" * 100)
print("EV top-level keys:")
print("   %s" % safe(sorted(EV)))
print("PROT top-level keys:")
print("   %s" % safe(sorted(PROT)))
print("CRIT top-level keys:")
print("   %s" % safe(sorted(CRIT)))
