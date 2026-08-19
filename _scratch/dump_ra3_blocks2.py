"""Second half of the CFG-3105 dump."""

import json
import pathlib

proto = json.loads(
    pathlib.Path("config/generation_2/g2_rotation_ra3_protocol.json").read_text(encoding="utf-8"))


def show(label, obj):
    print("\n===== %s" % label)
    print(json.dumps(obj, indent=2, ensure_ascii=False).encode(
        "ascii", "backslashreplace").decode("ascii"))


show("adversarial_test_requirements", proto["adversarial_test_requirements"])
show("conflicts_found", proto["conflicts_found"])
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
show("conflicts_declared_in_the_gate_criteria", proto["conflicts_declared_in_the_gate_criteria"])
show("declaration_note", proto["declaration_note"])
show("hypothesis", proto["hypothesis"])
show("what_this_attempt_changes_from_attempt_2", proto["what_this_attempt_changes_from_attempt_2"])
show("attempt_1_ref", proto["attempt_1_ref"])
show("attempt_2_ref", proto["attempt_2_ref"])
show("mechanics_carried_unchanged", proto["mechanics_carried_unchanged"])
show("reported_for_every_variant_but_not_gating", proto["reported_for_every_variant_but_not_gating"])
show("run_span", proto["run_span"])
show("candidate_index_note", proto["candidate_index_note"])
show("refs_reverified", proto["refs_reverified"])
show("gate_criteria_sha256_not_recorded_here", proto["gate_criteria_sha256_not_recorded_here"])
