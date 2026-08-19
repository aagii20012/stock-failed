"""Dump the CFG-3105 / CFG-3106 blocks the Markdown must restate, ASCII-safe."""

import json
import pathlib

proto = json.loads(
    pathlib.Path("config/generation_2/g2_rotation_ra3_protocol.json").read_text(encoding="utf-8"))
crit = json.loads(
    pathlib.Path("config/generation_2/g2_gate_criteria_ra3.json").read_text(encoding="utf-8"))


def show(label, obj, width=100000):
    text = json.dumps(obj, indent=2, ensure_ascii=False)[:width]
    print("\n===== %s" % label)
    print(text.encode("ascii", "backslashreplace").decode("ascii"))


print("TOP-LEVEL KEYS OF CFG-3105:")
print(json.dumps(list(proto), indent=1))

for key in [
    "family", "hypothesis", "candidate_index", "attempt", "constitution_ref", "charter_ref",
    "partition_lock_ref", "gate_criteria_ref",
]:
    print("  %-34s %s" % (key, json.dumps(proto.get(key), ensure_ascii=False)[:300]))

show("risk_architecture", proto["risk_architecture"])
show("representative_selection_rule", proto["representative_selection_rule"])
show("structural_consequences_declared_before_running",
     proto["structural_consequences_declared_before_running"])
show("adversarial_test_requirements", proto["adversarial_test_requirements"])
show("conflicts_found (protocol)", proto["conflicts_found"])
show("explicit_non_authorizations", proto["explicit_non_authorizations"])
show("prior_attempt_modules_immutable", proto["prior_attempt_modules_immutable"])
show("declared_before_any_strategy_code_measurement",
     proto["declared_before_any_strategy_code_measurement"])
show("multiple_comparisons_disclosure", proto["multiple_comparisons_disclosure"])
show("adaptation_disclosure_carriage_requirement",
     proto["adaptation_disclosure_carriage_requirement"])
show("gate_evaluation_scope", proto.get("gate_evaluation_scope"))
show("reproducibility_requirements", proto.get("reproducibility_requirements"))
show("post_seal_defect_rule", proto.get("post_seal_defect_rule"))
show("attempt_1_ref", proto["attempt_1_ref"])
show("attempt_2_ref", proto["attempt_2_ref"])
