"""Every node check_ladder_provenance() will index, printed from the file rather than recalled.

CFG-3105 line 333 names `risk_architecture.RA1-1.rule` as the source of f_base = 0.50, while the
ladder itself was found at `risk_architecture.RA1-5`.  Both paths must be confirmed to exist before
the sealer indexes them with bare [] subscripts: a KeyError inside build() lands after the JSON is
already on disk, where the seal-once guard then refuses to repair it.
"""

import json
import pathlib

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
G1 = json.loads((ROOT / "config/stage3_attempt2_strategy_protocol.json").read_text("utf-8"))
P3 = json.loads((ROOT / "config/generation_2/g2_rotation_ra3_protocol.json").read_text("utf-8"))

print("=" * 92)
print("Generation 1 risk_architecture: direct children")
for key, value in G1["risk_architecture"].items():
    kind = type(value).__name__
    inner = list(value) if isinstance(value, dict) else ""
    print("  %-14s %-6s %s" % (key, kind, inner))

for name in ("RA1-1", "RA1-5"):
    node = G1["risk_architecture"].get(name)
    print()
    print("-- G1 %s " % name + "-" * 76)
    if node is None:
        print("  ABSENT")
        continue
    for key, value in node.items():
        if isinstance(value, list):
            print("  %s:" % key)
            for item in value:
                print("      %s" % item)
        else:
            print("  %-24s %s" % (key, str(value)[:150]))

print()
print("=" * 92)
print("CFG-3105: the nodes that carry the provenance claim")
for path in (("risk_architecture", "provenance"),
             ("risk_architecture", "single_difference_from_ra2"),
             ("risk_architecture", "derived_from"),
             ("risk_architecture", "components", "RA3-4", "provenance"),
             ("risk_architecture", "combined_scalar", "range")):
    node = P3
    ok = True
    for part in path:
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            ok = False
            break
    label = ".".join(path)
    if not ok:
        print("  %-52s ABSENT" % label)
        continue
    print()
    print("-- %s " % label + "-" * max(2, 78 - len(label)))
    print(json.dumps(node, indent=2, ensure_ascii=False)[:3200])
