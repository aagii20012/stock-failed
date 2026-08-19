"""Fourteenth pass: assert every dereference the Attempt 3 package module intends to make.

Cheaper than discovering a KeyError inside the dry-run, and it prints the short values so the
prose can quote instead of recall. ASCII-laundered: the console is cp1252.
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

NODES = {"EV": EV, "PROT": PROT, "CRIT": CRIT, "LOCK": LOCK}

PATHS = [
    # ---- PROT ------------------------------------------------------------------------------
    "PROT.attempt",
    "PROT.strategy_id",
    "PROT.candidate_index",
    "PROT.family",
    "PROT.generation_id",
    "PROT.attempt_1_ref",
    "PROT.attempt_2_ref",
    "PROT.what_this_attempt_adds_over_attempt_1",
    "PROT.what_this_attempt_changes_from_attempt_2",
    "PROT.what_makes_this_genuinely_cross_sectional",
    "PROT.declared_before_any_strategy_code",
    "PROT.declared_before_any_strategy_code_measurement",
    "PROT.hypothesis",
    "PROT.structural_consequences_declared_before_running",
    "PROT.eligible_universe.universe_version",
    "PROT.run_span.run_start",
    "PROT.run_span.run_end",
    "PROT.runs_per_variant.labels",
    "PROT.multiple_comparisons_disclosure.adaptive_design_note",
    "PROT.explicit_non_authorizations",
    "PROT.adaptation_disclosure_verbatim",
    "PROT.adaptation_disclosure_carriage_requirement.enforcement",
    "PROT.adaptation_disclosure_carriage_requirement.encoding_note",
    "PROT.adaptation_disclosure_carriage_requirement.attempt_3_encoding_addendum",
    "PROT.adaptation_disclosure_carriage_requirement.must_appear_verbatim_in",
    "PROT.risk_architecture.id",
    "PROT.risk_architecture.components",
    "PROT.risk_architecture.combined_scalar",
    "PROT.risk_architecture.frozen_before_any_variant_is_run",
    "PROT.risk_architecture.not_part_of_the_grid",
    "PROT.risk_architecture.why_not_gridded",
    "PROT.risk_architecture.provenance",
    "PROT.risk_architecture.single_difference_from_ra2",
    "PROT.representative_selection_rule.id",
    "PROT.representative_selection_rule.steps",
    "PROT.representative_selection_rule.return_blind",
    "PROT.representative_selection_rule.structural_enforcement",
    "PROT.representative_selection_rule.no_reselection",
    "PROT.representative_selection_rule.why_it_changes",
    "PROT.representative_selection_rule.retrospective_check_disclosure",
    "PROT.representative_selection_rule.replaces",
    "PROT.mechanics_carried_unchanged",
    "PROT.concentration_ceiling",
    # ---- CRIT ------------------------------------------------------------------------------
    "CRIT.verdict_token_derivation.pass_token",
    "CRIT.verdict_token_derivation.fail_token",
    "CRIT.verdict_token_derivation.prior_attempt_tokens_are_not_available_here",
    "CRIT.verdict_token_derivation.constitutional_fail_result_equivalent",
    "CRIT.verdict_token_derivation.fail_is_a_deliverable",
    "CRIT.conditions",
    # ---- LOCK ------------------------------------------------------------------------------
    "LOCK.validation_reuse_disclosure",
    "LOCK.partition",
    "LOCK.generation_1_holdout_state",
    "LOCK.holdout_state",
    # ---- EV --------------------------------------------------------------------------------
    "EV.artifact_id",
    "EV.evidence_digest",
    "EV.evidence_digest_covers",
    "EV.generated_utc",
    "EV.grid.runs_executed",
    "EV.grid.variants_declared",
    "EV.grid.axes",
    "EV.window.latest_session_loaded",
    "EV.window.development_bound",
    "EV.window.enforcement",
    "EV.window.validation_read",
    "EV.window.generation_1_holdout_read",
    "EV.window.generation_2_holdout_read",
    "EV.run_span_recheck",
    "EV.universe",
    "EV.selection.outcome",
    "EV.selection.result.eligible_count",
    "EV.selection.result.selected_variant_id",
    "EV.selection.result.ineligible_variants",
    "EV.selection.result.decided_at_step",
    "EV.selection.decided_at_step",
    "EV.selection.steps",
    "EV.selection.rule_id",
    "EV.selection.rule_source",
    "EV.selection.return_blind",
    "EV.selection.note",
    "EV.selection.selected_score.instability_score",
    "EV.selection.selected_score.neighbours",
    "EV.selection.selected_score.neighbour_count",
    "EV.selection.selected_score.per_quantity_mean_dissimilarity",
    "EV.selection.selected_score.own_quantities",
    "EV.selection.neighbour_scores",
    "EV.selection.scored_quantities",
    "EV.selection.selection_input_fields",
    "EV.selection_determinism.all_identical",
    "EV.determinism.all_identical",
    "EV.determinism.runs_compared",
    "EV.determinism.fields_compared",
    "EV.determinism.mismatched_runs",
    "EV.reconciliation.runs_reconciled",
    "EV.reconciliation.single_leg_compared_total",
    "EV.reconciliation.mismatches_total",
    "EV.reconciliation.vacuous_runs",
    "EV.prior_attempt_module_verification.module_count",
    "EV.prior_attempt_module_verification.modules_that_moved",
    "EV.prior_attempt_module_verification.attempt_1_module_count",
    "EV.prior_attempt_module_verification.attempt_2_module_count",
    "EV.prior_attempt_module_verification.digest_source",
    "EV.prior_attempt_module_verification.requirement",
    "EV.prior_attempt_modules_immutable",
    "EV.ladder_engagement_comparison.at_least_one_statistic_differs",
    "EV.ladder_engagement_comparison.per_statistic",
    "EV.ladder_engagement_comparison.requirement",
    "EV.risk_architecture",
    "EV.gate_scope",
    "EV.gate",
    "EV.candidate_results",
    "EV.stage_verdict.verdict",
    "EV.stage_verdict.verdict_token",
    "EV.stage_verdict.admitted_candidates",
    "EV.stage_verdict.candidates_evaluated",
    "EV.stage_verdict.representative_exists",
    "EV.stage_verdict.prior_attempt_tokens_withheld",
    "EV.stage_verdict.fail_route",
    "EV.variant_table",
    "EV.variant_table_is_descriptive_only",
    "EV.reported_for_every_variant_coverage",
    "EV.multiple_comparisons_disclosure",
    "EV.adaptation_disclosure_carriage.sha256_of_utf8",
    "EV.mechanics_carried_unchanged",
    "EV.conflicts_declared_in_the_gate_criteria",
]

missing = []
for spec in PATHS:
    parts = spec.split(".")
    node = NODES[parts[0]]
    ok = True
    for part in parts[1:]:
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            ok = False
            break
    if not ok:
        missing.append(spec)
        print("MISSING  %s" % spec)
    else:
        rendered = safe(json.dumps(node, default=str))
        print("ok       %-72s %s" % (spec, rendered[:110]))

print("=" * 100)
print("MISSING TOTAL: %d" % len(missing))
for spec in missing:
    print("   %s" % spec)

print("=" * 100)
print("PROT top-level keys (%d):" % len(PROT))
for key in sorted(PROT):
    print("   %s" % key)
print("EV top-level keys (%d):" % len(EV))
for key in sorted(EV):
    print("   %s" % key)
