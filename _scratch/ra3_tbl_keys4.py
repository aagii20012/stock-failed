"""Fourth pass: candidate_results[0] container keys, A3/A2 variant_table shapes, A1 shutdown months."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
EV = json.loads((ROOT / "reports/stage3_g2_attempt3/STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json")
                .read_text(encoding="utf-8"))
A2 = json.loads((ROOT / "reports/stage3_g2_attempt2/STAGE_3_G2_A2_DEVELOPMENT_ADMISSIBILITY.json")
                .read_text(encoding="utf-8"))
A1 = json.loads((ROOT / "reports/stage3_g2/STAGE_3_G2_DEVELOPMENT_ADMISSIBILITY.json")
                .read_text(encoding="utf-8"))


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


def keys(label, obj, width=150):
    print("=== %s" % label)
    if isinstance(obj, dict):
        for k, v in obj.items():
            tag = "%s(%d)" % (type(v).__name__, len(v)) if isinstance(v, (dict, list)) else type(v).__name__
            print("  %-46s %-11s %s" % (k, tag, safe(v)[:width]))
    else:
        print("  %s" % safe(obj)[:width])
    print()


cand = EV["candidate_results"][0]
keys("EV.candidate_results[0]", cand)

for k in cand:
    if isinstance(cand[k], list) and cand[k] and isinstance(cand[k][0], dict):
        print("--- cand[%r] list(%d), [0] keys: %s" % (k, len(cand[k]), sorted(cand[k][0])))
print()

keys("EV.gate_scope", EV["gate_scope"])
keys("EV.ladder_engagement_comparison", EV["ladder_engagement_comparison"], 200)
keys("EV.risk_architecture (evidence copy)", EV["risk_architecture"], 200)
keys("EV.representative_selection_rule", EV["representative_selection_rule"], 200)
keys("EV.gate_evaluation_scope", EV["gate_evaluation_scope"], 200)
keys("EV.structural_consequences_declared_before_running", EV["structural_consequences_declared_before_running"], 200)
keys("EV.prior_attempt_modules_immutable", EV["prior_attempt_modules_immutable"], 200)
keys("EV.what_this_attempt_adds_over_attempt_1_carriage-ish", {
    "what_this_attempt_adds_over_attempt_1": EV["what_this_attempt_adds_over_attempt_1"],
    "what_this_attempt_changes_from_attempt_2": EV["what_this_attempt_changes_from_attempt_2"],
    "refs_reverified": EV["refs_reverified"],
    "hypothesis": EV["hypothesis"],
    "evidence_digest_covers": EV["evidence_digest_covers"],
    "command": EV["command"],
}, 300)

print("=== EV.variant_table[0] keys (%d)" % len(EV["variant_table"][0]))
for k, v in EV["variant_table"][0].items():
    print("  %-50s %-11s %s" % (k, type(v).__name__, safe(v)[:70]))
print()

print("=== A2.variant_table[0] keys (%d)" % len(A2["variant_table"][0]))
for k, v in A2["variant_table"][0].items():
    print("  %-50s %-11s %s" % (k, type(v).__name__, safe(v)[:70]))
print()

print("=== A1 shutdown months (from A1.variant_table)")
from collections import Counter
c = Counter()
for r in A1["variant_table"]:
    for side in ("base_shutdown_session", "stress_shutdown_session"):
        s = r.get(side)
        if s:
            c[s[:7]] += 1
for month in sorted(c):
    print("  %s  %d" % (month, c[month]))
print("  total runs with a shutdown session: %d" % sum(c.values()))
print()

print("=== A1.stage_verdict")
keys("A1.stage_verdict", A1["stage_verdict"], 200)
print("=== A2.stage_verdict")
keys("A2.stage_verdict", A2["stage_verdict"], 200)
