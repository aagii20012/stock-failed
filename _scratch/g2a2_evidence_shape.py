"""Dump the sub-keys of the evidence sections the Attempt 2 package builder will index.

ASCII output only. Long strings are truncated; the adaptation disclosure is never printed.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
body = json.loads(
    (ROOT / "reports" / "stage3_g2_attempt2" / "STAGE_3_G2_A2_DEVELOPMENT_ADMISSIBILITY.json")
    .read_text(encoding="utf-8")
)


def show(label, obj, depth=1, width=100):
    pad = "  " * depth
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, dict):
                print("%s%s: dict(%d) %s" % (pad, key, len(value), sorted(value)[:12]))
            elif isinstance(value, list):
                head = json.dumps(value[0])[:70] if value else ""
                print("%s%s: list(%d) %s" % (pad, key, len(value), head))
            else:
                text = str(value).replace("\n", " ")
                if len(text) > width:
                    text = text[:width] + "..."
                print("%s%s: %s" % (pad, key, text))
    else:
        print("%s%r" % (pad, obj))


for section in ("attempt_1_module_verification", "gate_scope", "reconciliation", "selection",
                "run_span_recheck"):
    print("== %s ==" % section)
    show(section, body[section])
    print()

print("== candidate_results[0] ==")
cand = body["candidate_results"][0]
show("cand", cand)
print()
print("  -- admission_basis --")
show("basis", cand["admission_basis"], depth=2)
print()
print("  -- base_evaluation keys --", sorted(cand["base_evaluation"]))
print("  -- one base condition --")
show("c", cand["base_evaluation"]["conditions"][0], depth=2)

print()
print("== stage_verdict (full) ==")
show("sv", body["stage_verdict"])

print()
print("== variant_table[0] columns ==")
print(" ", sorted(body["variant_table"][0]))

print()
print("== selection['step_1'] / ['step_2'] / ['step_3'] ==")
for key in ("step_1", "step_2", "step_3"):
    print("  %s: %s" % (key, json.dumps(body["selection"][key])[:500]))
