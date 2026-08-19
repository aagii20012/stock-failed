"""Eleventh pass: the two carriage nodes, the five carrier paths, and the leftover EV nodes."""

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


def dump(label, node, limit=2400):
    print("=" * 100)
    print(label)
    print(safe(json.dumps(node, indent=1, default=str))[:limit])


print("=" * 100)
print("must_appear_verbatim_in (the five carriers):")
for rel in PROT["adaptation_disclosure_carriage_requirement"]["must_appear_verbatim_in"]:
    print("   %s" % rel)

dump("PROT.what_this_attempt_adds_over_attempt_1_carriage",
     PROT["what_this_attempt_adds_over_attempt_1_carriage"], 2000)
print("   PROT.what_this_attempt_adds_over_attempt_1 length=%d"
      % len(PROT["what_this_attempt_adds_over_attempt_1"]))
dump("EV.what_this_attempt_adds_over_attempt_1_carriage",
     EV["what_this_attempt_adds_over_attempt_1_carriage"], 2000)

dump("CRIT.adaptation_disclosure_carried", CRIT["adaptation_disclosure_carried"], 1400)

print("=" * 100)
print("PROT.representative_selection_rule.id = %s" % PROT["representative_selection_rule"]["id"])
print("PROT.representative_selection_rule.return_blind =")
print(safe(json.dumps(PROT["representative_selection_rule"]["return_blind"], indent=1))[:1200])
print("PROT.representative_selection_rule.no_reselection =")
print(safe(json.dumps(PROT["representative_selection_rule"]["no_reselection"], indent=1))[:900])

dump("EV.gate", EV["gate"], 900)
dump("EV.gate_evaluation_scope", EV["gate_evaluation_scope"], 1400)
print("=" * 100)
print("EV.sealed_inputs keys: %s" % safe(sorted(EV["sealed_inputs"])))
print(safe(json.dumps(EV["sealed_inputs"], indent=1, default=str))[:2400])
print("=" * 100)
print("EV.mechanics_carried_unchanged keys: %s" % safe(sorted(EV["mechanics_carried_unchanged"])))
print("EV.runs type=%s" % type(EV["runs"]).__name__)
print(safe(json.dumps(EV["runs"], indent=1, default=str))[:900])
print("=" * 100)
print("EV.selection keys: %s" % safe(sorted(EV["selection"])))
print("EV.selection.outcome =")
print(safe(json.dumps(EV["selection"]["outcome"], indent=1, default=str))[:1200])
print("EV.selection.return_blind =")
print(safe(json.dumps(EV["selection"]["return_blind"], indent=1, default=str))[:1400])
print("EV.selection.note =")
print(safe(json.dumps(EV["selection"]["note"], indent=1, default=str))[:1200])
print("=" * 100)
print("EV.selection.inputs type=%s len=%s"
      % (type(EV["selection"]["inputs"]).__name__, len(EV["selection"]["inputs"])))
print(safe(json.dumps(EV["selection"]["inputs"][0] if isinstance(EV["selection"]["inputs"], list)
                      else EV["selection"]["inputs"], indent=1, default=str))[:700])
print("=" * 100)
print("EV.risk_architecture.attempt_2_counterparts =")
print(safe(json.dumps(EV["risk_architecture"]["attempt_2_counterparts"], indent=1))[:1200])
print("EV.risk_architecture.generation_1_provenance =")
print(safe(json.dumps(EV["risk_architecture"]["generation_1_provenance"], indent=1))[:1200])
print("=" * 100)
print("EV.ladder_engagement_comparison.sessions_at_full_sizing =")
print(safe(json.dumps(EV["ladder_engagement_comparison"]["sessions_at_full_sizing"], indent=1))[:900])
print("EV.ladder_engagement_comparison.requirement = %s"
      % safe(EV["ladder_engagement_comparison"]["requirement"])[:300])
print("EV.ladder_engagement_comparison.at_least_one_statistic_differs = %s"
      % EV["ladder_engagement_comparison"]["at_least_one_statistic_differs"])
print("=" * 100)
print("variant_table[0] keys: %s" % safe(sorted(EV["variant_table"][0])))
