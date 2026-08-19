"""Thirteenth pass: the exact key spellings and short values the package will interpolate.

Everything printed here is pasted into g2_stage3_attempt3_package.py rather than recalled, per
CLAUDE.md 'Quote the file or drop the claim'. ASCII-laundered: the console is cp1252.
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


def line(label, value, limit=900):
    print("%-58s %s" % (label, safe(json.dumps(value, default=str))[:limit]))


print("=" * 100)
print("variant_table[0] keys containing 'drawdown' / 'profit' / 'gross' / 'return':")
row = EV["variant_table"][0]
for key in sorted(row):
    if any(w in key for w in ("drawdown", "profit", "gross", "return", "scalar")):
        line("   " + key, row[key], 120)

print("=" * 100)
print("PROT.adaptation_disclosure_carriage_requirement keys: %s"
      % safe(sorted(PROT["adaptation_disclosure_carriage_requirement"])))
for key in sorted(PROT["adaptation_disclosure_carriage_requirement"]):
    if key == "must_appear_verbatim_in":
        continue
    line("   " + key, PROT["adaptation_disclosure_carriage_requirement"][key], 700)

print("=" * 100)
print("EV.selection.result keys: %s" % safe(sorted(EV["selection"]["result"])))
line("EV.selection.result", EV["selection"]["result"], 1200)
line("EV.selection.steps", EV["selection"]["steps"], 1600)
line("EV.selection.decided_at_step", EV["selection"]["decided_at_step"], 400)
line("EV.selection.scored_quantities", EV["selection"]["scored_quantities"], 400)
line("EV.selection.selection_input_fields", EV["selection"]["selection_input_fields"], 400)
line("EV.selection.rule_id", EV["selection"]["rule_id"], 200)
line("EV.selection.rule_source", EV["selection"]["rule_source"], 400)
line("EV.selection.frozen_before_any_variant_is_run",
     EV["selection"]["frozen_before_any_variant_is_run"], 500)
print("EV.selection.selected_score keys: %s" % safe(sorted(EV["selection"]["selected_score"]))
      if isinstance(EV["selection"]["selected_score"], dict) else EV["selection"]["selected_score"])
line("EV.selection.selected_score", EV["selection"]["selected_score"], 900)
print("EV.selection.neighbour_scores type=%s len=%s"
      % (type(EV["selection"]["neighbour_scores"]).__name__,
         len(EV["selection"]["neighbour_scores"])))

print("=" * 100)
cand = EV["candidate_results"][0]
print("candidate_results[0] keys: %s" % safe(sorted(cand)))
print("base condition ids in order:   %s" % safe([c["id"] for c in cand["conditions"]]))
print("stress condition ids in order: %s"
      % safe([c["id"] for c in cand["stress_evaluation"]["conditions"]]))
print("candidate.admission_basis keys: %s" % safe(sorted(cand["admission_basis"])))
line("candidate.non_vacuity_check", cand.get("non_vacuity_check"), 700)
for c in cand["conditions"]:
    if c["id"] == "S3-C3":
        line("base S3-C3.measured", c["measured"], 200)
line("candidate.variant_id", cand["variant_id"], 200)

print("=" * 100)
line("EV.gate_scope", EV["gate_scope"], 900)
line("EV.refs_reverified", EV["refs_reverified"], 700)
line("EV.variant_table_is_descriptive_only", EV["variant_table_is_descriptive_only"], 700)
line("EV.reported_for_every_variant_coverage", EV["reported_for_every_variant_coverage"], 900)
print("EV.universe keys: %s" % safe(sorted(EV["universe"])))
print("EV.multiple_comparisons_disclosure keys: %s" % safe(sorted(EV["multiple_comparisons_disclosure"])))
line("EV.multiple_comparisons_disclosure", EV["multiple_comparisons_disclosure"], 1400)

print("=" * 100)
print("EV.prior_attempt_module_verification keys: %s"
      % safe(sorted(EV["prior_attempt_module_verification"])))
line("EV.prior_attempt_module_verification", EV["prior_attempt_module_verification"], 1400)

print("=" * 100)
print("EV.ladder_engagement_comparison keys: %s" % safe(sorted(EV["ladder_engagement_comparison"])))
print("EV.ladder_engagement_comparison.per_statistic type=%s"
      % type(EV["ladder_engagement_comparison"]["per_statistic"]).__name__)
line("per_statistic", EV["ladder_engagement_comparison"]["per_statistic"], 1800)

print("=" * 100)
print("EV.risk_architecture keys: %s" % safe(sorted(EV["risk_architecture"])))
line("EV.risk_architecture.sealed", EV["risk_architecture"].get("sealed"), 700)
line("PROT.risk_architecture.single_difference_from_ra2",
     PROT["risk_architecture"]["single_difference_from_ra2"], 900)
print("PROT.risk_architecture keys: %s" % safe(sorted(PROT["risk_architecture"])))

print("=" * 100)
print("PROT top-level keys with 'attempt' or 'change':")
for key in sorted(PROT):
    if "attempt" in key or "change" in key:
        line("   " + key, PROT[key], 300)
print("PROT.multiple_comparisons_disclosure keys: %s"
      % safe(sorted(PROT["multiple_comparisons_disclosure"])))
print("PROT.representative_selection_rule keys: %s"
      % safe(sorted(PROT["representative_selection_rule"])))
print("LOCK.validation_reuse_disclosure length=%d" % len(LOCK["validation_reuse_disclosure"]))
print("PROT.adaptation_disclosure_verbatim length=%d" % len(PROT["adaptation_disclosure_verbatim"]))

print("=" * 100)
print("EV.determinism keys: %s" % safe(sorted(EV["determinism"])))
print("EV.window keys: %s" % safe(sorted(EV["window"])))
print("EV.grid keys: %s" % safe(sorted(EV["grid"])))
line("EV.grid", {k: v for k, v in EV["grid"].items() if k != "variants"}, 1200)
