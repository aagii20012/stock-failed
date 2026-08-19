"""The exact sub-keys g2_rotation_ra1's sizing/grid/evidence functions dereference, in RA3's protocol.

`target_weight` reads `position_sizing.{target_weight_formula,changed_from_attempt_1,target_weights,
target_gross_exposure}`; `attempt_1_weight_comparison` additionally reads `position_sizing.
attempt_1_formula`; `attempt_1_grid_agreement` reads `grid.unchanged_from_attempt_1`.  Any of those
that RA3 renamed is a KeyError inside a loop over eighteen variants, so measure before reusing.
"""

import json
import pathlib

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
P3 = json.loads((ROOT / "config/generation_2/g2_rotation_ra3_protocol.json").read_text("utf-8"))
P2 = json.loads((ROOT / "config/generation_2/g2_rotation_ra1_protocol.json").read_text("utf-8"))


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


for label, node3, node2 in (
    ("position_sizing", P3["position_sizing"], P2["position_sizing"]),
    ("grid (minus variants)", {k: v for k, v in P3["grid"].items() if k != "variants"},
     {k: v for k, v in P2["grid"].items() if k != "variants"}),
):
    print("=" * 98)
    print(label)
    for key in sorted(set(node3) | set(node2)):
        mark = "    " if key in node3 and key in node2 else ("+RA3" if key in node3 else "-RA2")
        val = node3.get(key, "<ABSENT IN RA3>")
        print("  %s %-40s %s" % (mark, key, safe(json.dumps(val, ensure_ascii=False))[:150]))

print()
print("=" * 98)
print("keys g2_rotation_ra1 dereferences, present/absent in RA3")
CHECKS = [
    ("position_sizing", "target_weight_formula"),
    ("position_sizing", "changed_from_attempt_1"),
    ("position_sizing", "target_weights"),
    ("position_sizing", "target_gross_exposure"),
    ("position_sizing", "attempt_1_formula"),
    ("grid", "unchanged_from_attempt_1"),
    ("grid", "unchanged_from_attempt_2"),
    ("grid", "variant_id_format"),
    ("grid", "size"),
    ("grid", "axes"),
    ("eligible_universe", "unchanged_from_attempt_1"),
    ("rebalance", "unchanged_from_attempt_1"),
]
for parent, key in CHECKS:
    node = P3.get(parent, {})
    print("  %-24s . %-30s %s" % (parent, key, "PRESENT" if key in node else "ABSENT"))

print()
print("=" * 98)
print("does anything else in the tree name attempt_1_formula?")
def walk(node, path=""):
    if isinstance(node, dict):
        for k, v in node.items():
            if "attempt_1_formula" in k or "attempt_2_formula" in k:
                print("  %s/%s = %s" % (path, k, safe(json.dumps(v, ensure_ascii=False))[:120]))
            walk(v, path + "/" + k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk(v, path + "[%d]" % i)
walk(P3)
