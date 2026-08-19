"""Eighth pass: the exact scalars the Attempt 3 builder pastes into evidence/limitations/run notes.

Every number that appears in g2_stage3_attempt3_package.py prose must be either dereferenced live
from the evidence at build time or measured here first. Nothing is recalled.
"""

import json
import pathlib

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


def dump(label, node, limit=2400):
    print("=" * 100)
    print(label)
    print(safe(json.dumps(node, indent=1, default=str))[:limit])


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


EV = load("reports/stage3_g2_attempt3/STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json")
P = load("config/generation_2/g2_rotation_ra3_protocol.json")

dump("EV.selection.selected_score", EV["selection"]["selected_score"], 2000)
dump("EV.selection.neighbour_scores", EV["selection"]["neighbour_scores"], 2400)
dump("EV.selection note/no_reselection/outcome",
     {k: EV["selection"][k] for k in ("note", "no_reselection", "outcome", "decided_at_step",
                                      "return_blind", "rule_id", "rule_source",
                                      "selected_variant_id")}, 3000)
print("   selection.result keys:", sorted(EV["selection"]["result"]))
print("   eligible_count:", EV["selection"]["result"]["eligible_count"])
print("   ineligible:", EV["selection"]["result"]["ineligible_variants"])
print("   ranking[0..2]:", safe(json.dumps(EV["selection"]["result"]["ranking"][:3])))

dump("EV.risk_architecture (minus as_loaded)",
     {k: v for k, v in EV["risk_architecture"].items() if k != "as_loaded"}, 2600)
print("   as_loaded keys:", sorted(EV["risk_architecture"]["as_loaded"]))
dump("EV.risk_architecture.as_loaded", EV["risk_architecture"]["as_loaded"], 2600)

print("=" * 100)
print("PROTOCOL.risk_architecture keys:", sorted(P["risk_architecture"]))
for k in sorted(P["risk_architecture"]):
    v = P["risk_architecture"][k]
    print("   %-42s %s" % (k, safe(json.dumps(v, default=str))[:220]))

dump("EV.universe", EV["universe"], 1400)
dump("EV.gate_scope", EV["gate_scope"], 1800)
dump("EV.gate_evaluation_scope", EV["gate_evaluation_scope"], 1400)
dump("EV.candidate_results[0].admission_basis", EV["candidate_results"][0]["admission_basis"], 2600)

print("=" * 100)
print("candidate conditions (#BASE):")
for row in EV["candidate_results"][0]["conditions"]:
    print("   %-8s %-28s satisfied=%-6s measured=%s"
          % (row["id"], row["verdict"], row["satisfied"], safe(str(row["measured"]))[:70]))
print("candidate conditions (#STRESS):")
for row in EV["candidate_results"][0]["stress_evaluation"]["conditions"]:
    print("   %-8s %-28s satisfied=%-6s measured=%s"
          % (row["id"], row["verdict"], row["satisfied"], safe(str(row["measured"]))[:70]))
print("   condition row keys:", sorted(EV["candidate_results"][0]["conditions"][0]))

dump("EV.ladder_engagement_comparison.per_statistic",
     EV["ladder_engagement_comparison"]["per_statistic"], 3000)
dump("EV.ladder_engagement_comparison.sessions_at_full_sizing",
     EV["ladder_engagement_comparison"]["sessions_at_full_sizing"], 1400)

dump("EV.prior_attempt_module_verification (minus modules_verified)",
     {k: v for k, v in EV["prior_attempt_module_verification"].items()
      if k != "modules_verified"}, 2000)

dump("EV.reported_for_every_variant_coverage", EV["reported_for_every_variant_coverage"], 2000)
dump("EV.multiple_comparisons_disclosure", EV["multiple_comparisons_disclosure"], 2600)
dump("EV.determinism (minus run_digests)",
     {k: v for k, v in EV["determinism"].items() if k != "run_digests"}, 1800)
dump("EV.reconciliation", EV["reconciliation"], 1600)
dump("EV.run_span_recheck", EV["run_span_recheck"], 1600)
dump("EV.window", EV["window"], 1600)
dump("EV.grid", EV["grid"], 1200)
dump("EV.sealed_inputs", EV["sealed_inputs"], 2600)
dump("EV.variant_table_is_descriptive_only[0]", EV["variant_table_is_descriptive_only"][0], 900)
dump("EV.mechanics_carried_unchanged", EV["mechanics_carried_unchanged"], 1600)
dump("EV.conflicts_declared_in_the_gate_criteria",
     EV["conflicts_declared_in_the_gate_criteria"], 2000)
dump("EV.structural_consequences_declared_before_running",
     EV["structural_consequences_declared_before_running"], 3000)

print("=" * 100)
print("max drawdowns across the 18 rows:")
print("   base   max = %s" % max(r["base_max_drawdown"] for r in EV["variant_table"]))
print("   stress max = %s" % max(r["stress_max_drawdown"] for r in EV["variant_table"]))
print("   base   min = %s" % min(r["base_max_drawdown"] for r in EV["variant_table"]))
gross = [float(r["base_max_gross_fraction_observed"]) for r in EV["variant_table"]]
gross += [float(r["stress_max_gross_fraction_observed"]) for r in EV["variant_table"]]
print("   max_gross_fraction observed across 36 runs: %.4f .. %.4f" % (min(gross), max(gross)))
pos = [r for r in EV["variant_table"] if float(r["base_total_return"]) > 0]
print("   variants with positive base total_return: %d of 18" % len(pos))
print("   best base total_return: %s" % max(float(r["base_total_return"]) for r in EV["variant_table"]))

print("=" * 100)
print("PROTOCOL.representative_selection_rule:")
for k in sorted(P["representative_selection_rule"]):
    print("   %-42s %s" % (k, safe(json.dumps(P["representative_selection_rule"][k],
                                              default=str))[:260]))
print()
print("PROTOCOL.what_this_attempt_changes_from_attempt_2:")
print("   " + safe(P["what_this_attempt_changes_from_attempt_2"])[:1600])
print()
print("PROTOCOL.attempt_2_ref keys:", sorted(P["attempt_2_ref"]))
print("PROTOCOL.attempt_1_ref keys:", sorted(P["attempt_1_ref"]))
print("PROTOCOL.declared_before_any_strategy_code_measurement keys:",
      sorted(P["declared_before_any_strategy_code_measurement"]))
print("PROTOCOL.explicit_non_authorizations:", len(P["explicit_non_authorizations"]))
print("PROTOCOL.adversarial_test_requirements keys:", sorted(P["adversarial_test_requirements"]))
