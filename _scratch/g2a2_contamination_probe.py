"""Print the Attempt 2 protocol's sealed contamination block in full. ASCII output only."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "stockedge100"
P = json.loads((ROOT / "config/generation_2/g2_rotation_ra1_protocol.json")
               .read_text(encoding="utf-8"))
cm = P["contamination_measurement"]

print("keys:", list(cm))
print()
for k, v in cm.items():
    if isinstance(v, dict):
        print("%s: <dict, %d keys>" % (k, len(v)))
        for kk, vv in v.items():
            s = str(vv)
            print("    %-42s = %s" % (kk, s if len(s) < 90 else s[:87] + "..."))
    elif isinstance(v, list):
        print("%s: <list, %d entries>" % (k, len(v)))
        for item in v[:3]:
            s = str(item)
            print("    %s" % (s if len(s) < 100 else s[:97] + "..."))
        if len(v) > 3:
            print("    ... %d more" % (len(v) - 3))
    else:
        s = str(v)
        print("%-46s = %s" % (k, s if len(s) < 110 else s[:107] + "..."))

print()
numeric = {k: v for k, v in cm.items() if isinstance(v, int) and not isinstance(v, bool)}
boolean = {k: v for k, v in cm.items() if isinstance(v, bool)}
print("top-level integer counts (%d): %s" % (len(numeric), sorted(numeric)))
print("top-level booleans      (%d): %s" % (len(boolean), sorted(boolean)))

# Attempt 1's protocol, for the contrast the README draws.
A1 = json.loads((ROOT / "config/generation_2/g2_rotation_protocol.json")
                .read_text(encoding="utf-8"))
a1cm = A1.get("contamination_measurement") or A1.get("contamination_counts") or {}
print()
print("A1 contamination keys:", list(a1cm))
for k, v in a1cm.items():
    if not isinstance(v, (dict, list)):
        print("    %-42s = %s" % (k, v))
