"""Enumerate the exact key names the Attempt 3 report emitter will index.

Nothing here is assumed from Attempt 2's schema. ASCII output only.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
EV = json.loads((ROOT / "reports/stage3_g2_attempt3/STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json")
                .read_text(encoding="utf-8"))


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


def dump(label, obj):
    print("=== %s" % label)
    if isinstance(obj, dict):
        for k in obj:
            v = obj[k]
            kind = type(v).__name__
            if isinstance(v, (dict, list)):
                print("  %-52s %s(%d)" % (k, kind, len(v)))
            else:
                print("  %-52s %s = %s" % (k, kind, safe(v)[:110]))
    elif isinstance(obj, list):
        print("  list len %d" % len(obj))
        if obj and isinstance(obj[0], dict):
            for k in obj[0]:
                print("    %-50s %s" % (k, type(obj[0][k]).__name__))
    print()


dump("variant_table[0]", EV["variant_table"][0])
dump("candidate_results[0]", EV["candidate_results"][0])
print("=== candidate_results[0] top-level condition ids")
for c in EV["candidate_results"][0]["conditions"]:
    print("  %-10s keys=%s" % (c.get("id"), sorted(c)))
print()
dump("candidate_results[0].stress_evaluation", EV["candidate_results"][0]["stress_evaluation"])
dump("gate", EV["gate"])
dump("gate_scope", EV["gate_scope"])
dump("gate_evaluation_scope", EV["gate_evaluation_scope"])
dump("stage_verdict", EV["stage_verdict"])
dump("grid", EV["grid"])
dump("window", EV["window"])
dump("window.run_span", EV["window"]["run_span"])
dump("universe", EV["universe"])
dump("sealed_inputs", EV["sealed_inputs"])
dump("determinism", EV["determinism"])
dump("reconciliation", EV["reconciliation"])
dump("selection_determinism", EV["selection_determinism"])
dump("ladder_engagement_comparison", EV["ladder_engagement_comparison"])
dump("ladder_engagement_comparison.per_statistic",
     EV["ladder_engagement_comparison"]["per_statistic"])
dump("risk_architecture", EV["risk_architecture"])
dump("prior_attempt_module_verification", EV["prior_attempt_module_verification"])
dump("prior_attempt_modules_immutable", EV["prior_attempt_modules_immutable"])
dump("multiple_comparisons_disclosure", EV["multiple_comparisons_disclosure"])
dump("adaptation_disclosure_carriage", EV["adaptation_disclosure_carriage"])
dump("attempt_1_ref", EV["attempt_1_ref"])
dump("attempt_2_ref", EV["attempt_2_ref"])
dump("runs[0]", EV["runs"][0])
dump("reported_for_every_variant_coverage", EV["reported_for_every_variant_coverage"])
dump("run_span_recheck", EV["run_span_recheck"])
dump("representative_selection_rule", EV["representative_selection_rule"])
dump("structural_consequences_declared_before_running",
     EV["structural_consequences_declared_before_running"])
dump("mechanics_carried_unchanged", EV["mechanics_carried_unchanged"])
dump("conflicts_declared_in_the_gate_criteria", EV["conflicts_declared_in_the_gate_criteria"])
dump("variant_table_is_descriptive_only[0]", EV["variant_table_is_descriptive_only"][0]
     if isinstance(EV["variant_table_is_descriptive_only"][0], dict)
     else {"value": EV["variant_table_is_descriptive_only"][0]})
print("=== variant_table_is_descriptive_only raw first 2")
for item in EV["variant_table_is_descriptive_only"][:2]:
    print("  %s" % safe(item)[:200])
print()
print("=== explicit_non_authorizations (%d)" % len(EV["explicit_non_authorizations"]))
for item in EV["explicit_non_authorizations"]:
    print("  - %s" % safe(item)[:160])
