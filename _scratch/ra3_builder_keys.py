"""Seventh pass: exactly the nodes the Attempt 3 BUILDER dereferences, and nothing else.

Everything printed here is pasted into g2_stage3_attempt3_package.py by key name. Anything not
printed here must not appear in that module.
"""

import json
import pathlib

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


def dump(label, node, limit=2000):
    print("=" * 100)
    print(label)
    print(safe(json.dumps(node, indent=1, default=str))[:limit])


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


EV = load("reports/stage3_g2_attempt3/STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json")
PROT = load("config/generation_2/g2_rotation_ra3_protocol.json")
CRIT = load("config/generation_2/g2_gate_criteria_ra3.json")
LOCK = load("governance/generation_2/STAGE_1_G2_PARTITION_LOCK.json")

print("PROTOCOL top-level keys (%d):" % len(PROT))
for key, value in PROT.items():
    if isinstance(value, dict):
        print("   %-52s dict %s" % (key, sorted(value)))
    elif isinstance(value, list):
        print("   %-52s list[%d]" % (key, len(value)))
    else:
        print("   %-52s %s" % (key, safe(repr(value))[:110]))

print()
print("PARTITION LOCK top-level keys (%d): %s" % (len(LOCK), sorted(LOCK)))

dump("PROTOCOL.runs_per_variant", PROT.get("runs_per_variant"), 600)
dump("PROTOCOL.run_span", PROT.get("run_span"), 800)
dump("PROTOCOL.eligible_universe keys", sorted(PROT.get("eligible_universe", {})), 600)
dump("PROTOCOL.adaptation_disclosure_carriage_requirement",
     {k: v for k, v in PROT["adaptation_disclosure_carriage_requirement"].items()
      if k != "source"}, 2400)
print("   must_appear_verbatim_in:")
for rel in PROT["adaptation_disclosure_carriage_requirement"]["must_appear_verbatim_in"]:
    path = ROOT / rel
    print("      %-78s exists=%s" % (rel, path.is_file()))

dump("EVIDENCE.selection.result", EV["selection"]["result"], 2400)
print("   selection top-level keys: %s" % sorted(EV["selection"]))
dump("EVIDENCE.selection.steps", EV["selection"]["steps"], 1600)
dump("EVIDENCE.selection.note+no_reselection",
     {k: EV["selection"][k] for k in ("note", "no_reselection", "rule_id", "rule_source",
                                      "return_blind", "frozen_before_any_variant_is_run",
                                      "decided_at_step", "outcome", "selected_variant_id")}, 2600)
dump("EVIDENCE.selection.selection_input_fields+scored_quantities",
     {k: EV["selection"][k] for k in ("selection_input_fields", "scored_quantities")}, 900)

dump("EVIDENCE.stage_verdict", EV["stage_verdict"], 3200)
dump("EVIDENCE.candidate_results[0].admission_basis",
     EV["candidate_results"][0]["admission_basis"], 2600)
dump("EVIDENCE.window", EV["window"], 1600)
dump("EVIDENCE.grid", EV["grid"], 1200)
dump("EVIDENCE.risk_architecture", EV["risk_architecture"], 2400)
dump("EVIDENCE.gate_scope", EV["gate_scope"], 1600)
dump("EVIDENCE.universe", EV["universe"], 1200)
dump("EVIDENCE.selection_determinism", EV["selection_determinism"], 1600)
dump("EVIDENCE.prior_attempt_module_verification",
     {k: v for k, v in EV["prior_attempt_module_verification"].items()
      if k != "modules_verified"}, 2000)
dump("EVIDENCE.prior_attempt_modules_immutable", EV["prior_attempt_modules_immutable"], 1600)
dump("EVIDENCE.ladder_engagement_comparison keys",
     {k: (sorted(v) if isinstance(v, dict) else v)
      for k, v in EV["ladder_engagement_comparison"].items()}, 2000)
dump("EVIDENCE.adaptation_disclosure_carriage",
     {k: v for k, v in EV["adaptation_disclosure_carriage"].items()
      if k != "must_appear_verbatim_in"}, 2400)
print("   evidence carriage must_appear_verbatim_in: %s"
      % EV["adaptation_disclosure_carriage"]["must_appear_verbatim_in"])
dump("EVIDENCE.variant_table_is_descriptive_only", EV["variant_table_is_descriptive_only"], 2200)
dump("EVIDENCE.reported_for_every_variant_coverage",
     EV["reported_for_every_variant_coverage"], 1400)
dump("EVIDENCE.multiple_comparisons_disclosure", EV["multiple_comparisons_disclosure"], 2400)
dump("EVIDENCE.gate_evaluation_scope", EV["gate_evaluation_scope"], 1400)
dump("EVIDENCE.refs_reverified", EV["refs_reverified"], 1800)
dump("EVIDENCE.conflicts_declared_in_the_gate_criteria",
     EV["conflicts_declared_in_the_gate_criteria"], 1600)
dump("EVIDENCE.mechanics_carried_unchanged", EV["mechanics_carried_unchanged"], 1400)

print("=" * 100)
print("CRITERIA.conflicts_found (%d) ids and first words:" % len(CRIT["conflicts_found"]))
for row in CRIT["conflicts_found"]:
    if isinstance(row, dict):
        print("   %-22s %s" % (row.get("id"), safe(str(row.get("conflict", row)))[:150]))
    else:
        print("   %s" % safe(str(row))[:160])
