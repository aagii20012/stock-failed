"""Exact values of the structured sub-objects the Markdown generator must lay out
as tables.  Key names alone are not enough for these; the layout depends on the
values.  ASCII-escaped so the cp1252 console cannot kill the sweep."""

import json
import pathlib

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
proto = json.loads(
    (ROOT / "config/generation_2/g2_rotation_ra3_protocol.json").read_text(encoding="utf-8"))


def a(obj):
    return json.dumps(obj, indent=2, ensure_ascii=False).encode(
        "ascii", "backslashreplace").decode("ascii")


ra = proto["risk_architecture"]
comp = ra["components"]

for path, node in [
    ("risk_architecture.components.RA3-4.bands", comp["RA3-4"]["bands"]),
    ("risk_architecture.components.RA3-4.provenance", comp["RA3-4"]["provenance"]),
    ("risk_architecture.components.RA3-4.relationship_to_the_shutdown_threshold",
     comp["RA3-4"]["relationship_to_the_shutdown_threshold"]),
    ("risk_architecture.components.RA3-1.enforcement", comp["RA3-1"]["enforcement"]),
    ("risk_architecture.components.RA3-2.self_reference", comp["RA3-2"]["self_reference"]),
    ("risk_architecture.components.RA3-3.reference_price_definition",
     comp["RA3-3"]["reference_price_definition"]),
    ("representative_selection_rule.steps", proto["representative_selection_rule"]["steps"]),
    ("window.prohibited", proto["window"]["prohibited"]),
    ("execution.order_kinds_this_attempt_may_issue",
     proto["execution"]["order_kinds_this_attempt_may_issue"]),
    ("mechanics_carried_unchanged", proto["mechanics_carried_unchanged"]),
    ("serialisation", proto["serialisation"]),
    ("reproducibility_requirements", proto["reproducibility_requirements"]),
    ("gate_evaluation_scope", proto["gate_evaluation_scope"]),
    ("post_seal_defect_rule", proto["post_seal_defect_rule"]),
    ("conflicts_declared_in_the_gate_criteria", proto["conflicts_declared_in_the_gate_criteria"]),
    ("reported_for_every_variant_but_not_gating",
     proto["reported_for_every_variant_but_not_gating"]),
]:
    print("=" * 78)
    print("### %s" % path)
    print("=" * 78)
    print(a(node))
    print()
