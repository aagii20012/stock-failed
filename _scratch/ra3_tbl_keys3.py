"""Third pass: EV["selection"], and the Attempt 1 / Attempt 2 sources the three-way table needs.

Nothing is assumed about where Attempt 1's and Attempt 2's per-variant returns live. ASCII only.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
EV = json.loads((ROOT / "reports/stage3_g2_attempt3/STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json")
                .read_text(encoding="utf-8"))


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


def dump(label, obj, width=220):
    print("=== %s" % label)
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                print("  %-44s %s(%d) %s" % (k, type(v).__name__, len(v), safe(v)[:width]))
            else:
                print("  %-44s %s" % (k, safe(v)[:width]))
    elif isinstance(obj, list):
        print("  list(%d)" % len(obj))
        if obj and isinstance(obj[0], dict):
            for k, v in obj[0].items():
                print("    [0] %-40s %s = %s" % (k, type(v).__name__, safe(v)[:width]))
        else:
            for item in obj[:6]:
                print("    %s" % safe(item)[:width])
    else:
        print("  %s" % safe(obj)[:width])
    print()


print("=== EV top-level keys (%d)" % len(EV))
for k in EV:
    v = EV[k]
    print("  %-52s %s%s" % (k, type(v).__name__,
                            "(%d)" % len(v) if isinstance(v, (dict, list)) else ""))
print()

sel = EV["selection"]
dump("selection", sel)
dump("selection.result", sel["result"])
print("=== selection.result.ranking (first 6 + last)")
rk = sel["result"]["ranking"]
print("  len %d, type %s" % (len(rk), type(rk[0]).__name__))
for item in rk[:6] + rk[-1:]:
    print("  %s" % safe(item)[:260])
print()
print("=== selection.result.all_scores")
allsc = sel["result"]["all_scores"]
print("  type %s len %d" % (type(allsc).__name__, len(allsc)))
if isinstance(allsc, dict):
    for k in list(allsc)[:3]:
        print("  %-52s %s" % (k, safe(allsc[k])[:220]))
else:
    for item in allsc[:3]:
        print("  %s" % safe(item)[:260])
print()
print("=== selection.neighbour_scores")
ns = sel.get("neighbour_scores")
print("  type %s len %s" % (type(ns).__name__, len(ns) if ns is not None else "-"))
if isinstance(ns, list):
    for item in ns:
        print("  %s" % safe(item)[:400])
elif isinstance(ns, dict):
    for k, v in ns.items():
        print("  %-52s %s" % (k, safe(v)[:300]))
print()
for key in ("note", "steps", "rule_id", "structural_enforcement"):
    if key in sel:
        dump("selection.%s" % key, sel[key], 400)

# --- the prior attempts' per-variant sources ------------------------------------------------------
for rel in ("reports/stage3_g2/grid_results.json",
            "reports/stage3_g2_attempt2/grid_results.json",
            "reports/stage3_g2/STAGE_3_G2_DEVELOPMENT_ADMISSIBILITY.json",
            "reports/stage3_g2_attempt2/STAGE_3_G2_A2_DEVELOPMENT_ADMISSIBILITY.json"):
    path = ROOT / rel
    print("=== %s exists=%s" % (rel, path.exists()))
    if not path.exists():
        print()
        continue
    obj = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(obj, list):
        print("  list(%d); [0] keys:" % len(obj))
        for k, v in obj[0].items():
            print("    %-46s %s = %s" % (k, type(v).__name__, safe(v)[:90]))
    else:
        print("  dict(%d) keys: %s" % (len(obj), sorted(obj)[:40]))
    print()

print("=== A1 evidence variant_table[0] keys (if present)")
a1 = ROOT / "reports/stage3_g2/STAGE_3_G2_DEVELOPMENT_ADMISSIBILITY.json"
if a1.exists():
    obj = json.loads(a1.read_text(encoding="utf-8"))
    for name in ("variant_table", "runs", "grid_rows"):
        if name in obj and isinstance(obj[name], list) and obj[name]:
            print("  %s list(%d); [0] keys:" % (name, len(obj[name])))
            for k, v in obj[name][0].items():
                print("    %-46s %s = %s" % (k, type(v).__name__, safe(v)[:90]))
            break
print()
