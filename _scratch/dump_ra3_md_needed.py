"""Dump exactly the CFG-3105 / CFG-3106 blocks the Attempt 3 Markdown must restate."""

import json
import pathlib

proto = json.loads(
    pathlib.Path("config/generation_2/g2_rotation_ra3_protocol.json").read_text(encoding="utf-8"))
crit = json.loads(
    pathlib.Path("config/generation_2/g2_gate_criteria_ra3.json").read_text(encoding="utf-8"))


def show(label, obj):
    print("\n===== %s" % label)
    print(json.dumps(obj, indent=2, ensure_ascii=False).encode(
        "ascii", "backslashreplace").decode("ascii"))


for key in ("risk_architecture", "representative_selection_rule",
            "structural_consequences_declared_before_running", "ranking_signal", "ranking_rule",
            "execution", "position_sizing", "concentration_ceiling", "window",
            "gate_evaluation_scope", "post_seal_defect_rule", "eligible_universe",
            "rebalance", "position_count", "grid", "runs_per_variant", "serialisation",
            "declaration_note", "what_this_attempt_adds_over_attempt_1",
            "what_makes_this_genuinely_cross_sectional", "refs_reverified"):
    show(key, proto.get(key))

print("\n===== conflicts_found (protocol) short form")
for c in proto["conflicts_found"]:
    print("\n-- %s" % c["id"])
    for k in ("title", "summary", "conflict", "resolution", "carried_from", "supersedes_in_scope"):
        if k in c:
            print("   %-20s %s" % (k, str(c[k]).encode("ascii", "backslashreplace").decode("ascii")))

print("\n===== conflicts_found (criteria) short form")
for c in crit["conflicts_found"]:
    print("\n-- %s" % c["id"])
    for k in ("title", "summary", "conflict", "resolution", "carried_from"):
        if k in c:
            print("   %-20s %s" % (k, str(c[k]).encode("ascii", "backslashreplace").decode("ascii")))

show("criteria.conditions", crit["conditions"])
show("criteria.evaluation_integrity_rules", crit.get("evaluation_integrity_rules"))
show("criteria.verdict_token_derivation", crit["verdict_token_derivation"])
