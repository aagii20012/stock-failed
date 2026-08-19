"""Everything in CFG-3105 the first two dumps did not cover."""

import json
import pathlib

proto = json.loads(
    pathlib.Path("config/generation_2/g2_rotation_ra3_protocol.json").read_text(encoding="utf-8"))

SEEN = {
    "document", "strategy_id", "candidate_index", "attempt", "family",
    "live_trading_authorized", "declaration_note", "hypothesis",
    "candidate_index_note", "what_this_attempt_changes_from_attempt_2",
    "what_this_attempt_adds_over_attempt_1",
    "what_makes_this_genuinely_cross_sectional", "attempt_1_ref", "attempt_2_ref",
    "mechanics_carried_unchanged", "eligible_universe", "ranking_signal",
    "ranking_rule", "position_count", "position_sizing", "concentration_ceiling",
    "rebalance", "runs_per_variant", "execution", "window", "run_span",
    "risk_architecture", "representative_selection_rule",
    "structural_consequences_declared_before_running",
    "adversarial_test_requirements", "explicit_non_authorizations",
    "prior_attempt_modules_immutable",
    "declared_before_any_strategy_code_measurement",
    "multiple_comparisons_disclosure", "adaptation_disclosure_carriage_requirement",
    "gate_evaluation_scope", "reproducibility_requirements", "post_seal_defect_rule",
    "conflicts_declared_in_the_gate_criteria", "reported_for_every_variant_but_not_gating",
    "refs_reverified", "gate_criteria_sha256_not_recorded_here", "serialisation",
    "adaptation_disclosure_verbatim",
}


def a(s):
    return s.encode("ascii", "backslashreplace").decode("ascii")


print("########## ALL TOP-LEVEL KEYS (%d)" % len(proto))
for i, k in enumerate(proto, 1):
    print("  %2d. %-58s %s" % (i, k, "" if k in SEEN else "<-- NOT YET DUMPED"))

print("\n\n########## conflicts_found")
cf = proto["conflicts_found"]
print("type=%s len=%d" % (type(cf).__name__, len(cf)))
items = cf.items() if isinstance(cf, dict) else enumerate(cf)
for key, val in items:
    print("\n-- %s" % key)
    if isinstance(val, dict):
        for kk, vv in val.items():
            print("   %-34s %s" % (kk, a(json.dumps(vv, ensure_ascii=False))))
    else:
        print("   %s" % a(json.dumps(val, ensure_ascii=False)))

print("\n\n########## grid")
grid = proto["grid"]
for k, v in grid.items():
    if k == "variants":
        continue
    print("  %-34s %s" % (k, a(json.dumps(v, ensure_ascii=False))))
print("\n  variants (%d):" % len(grid["variants"]))
for row in grid["variants"]:
    print("   %s" % a(json.dumps(row, ensure_ascii=False, sort_keys=True)))

print("\n\n########## remaining undumped keys")
for k, v in proto.items():
    if k in SEEN or k in ("conflicts_found", "grid"):
        continue
    print("\n===== %s" % k)
    print(a(json.dumps(v, indent=2, ensure_ascii=False)))
