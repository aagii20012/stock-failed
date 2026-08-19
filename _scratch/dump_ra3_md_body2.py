"""Blocks CFG-3105 needs restated in sections 5 and 9 to 17 of the Attempt 3 Markdown."""

import json
import pathlib

proto = json.loads(
    pathlib.Path("config/generation_2/g2_rotation_ra3_protocol.json").read_text(encoding="utf-8"))


def show(label, obj):
    print("\n===== %s" % label)
    print(json.dumps(obj, indent=2, ensure_ascii=False).encode(
        "ascii", "backslashreplace").decode("ascii"))


for key in ("risk_architecture", "representative_selection_rule",
            "structural_consequences_declared_before_running",
            "adversarial_test_requirements", "explicit_non_authorizations",
            "prior_attempt_modules_immutable",
            "declared_before_any_strategy_code_measurement",
            "multiple_comparisons_disclosure",
            "adaptation_disclosure_carriage_requirement",
            "gate_evaluation_scope", "reproducibility_requirements",
            "post_seal_defect_rule", "conflicts_declared_in_the_gate_criteria",
            "reported_for_every_variant_but_not_gating", "refs_reverified",
            "gate_criteria_sha256_not_recorded_here", "serialisation"):
    show(key, proto.get(key, "<<ABSENT>>"))
