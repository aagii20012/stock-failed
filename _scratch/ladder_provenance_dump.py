"""The exact nodes check_ladder_provenance() will read, from all three configs.

The provenance claim this attempt makes -- "RA3's ladder is Generation 1's original RA1 ladder, and
the single change from RA2 is the deletion of the [0.05, 0.08) tier" -- is checkable rather than
assertable, but only if the three sources are read rather than remembered.  Dump them.
"""

import json
import pathlib

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
P3 = json.loads((ROOT / "config/generation_2/g2_rotation_ra3_protocol.json").read_text("utf-8"))
P2 = json.loads((ROOT / "config/generation_2/g2_rotation_ra1_protocol.json").read_text("utf-8"))
G1 = json.loads((ROOT / "config/stage3_attempt2_strategy_protocol.json").read_text("utf-8"))

print("=" * 90)
print("CFG-3105 risk_architecture top-level keys")
for k, v in P3["risk_architecture"].items():
    print("  %-42s %s" % (k, type(v).__name__ if isinstance(v, (dict, list)) else repr(v)[:70]))

print()
print("CFG-3105 risk_architecture.components keys, in JSON order")
print("  %s" % list(P3["risk_architecture"]["components"]))

print()
for name in ("RA3-1", "RA3-2", "RA3-3", "RA3-5"):
    c = P3["risk_architecture"]["components"][name]
    print("  %-8s name=%-24s value=%-10s unit=%s"
          % (name, c.get("name"), c.get("value"), c.get("unit")))

print()
print("=" * 90)
print("any provenance-shaped node under CFG-3105")
for k in sorted(P3):
    if "provenance" in k or "ladder" in k or "change" in k or "ra2" in k.lower():
        print("  TOP  %s -> %s" % (k, type(P3[k]).__name__))
for k in sorted(P3["risk_architecture"]):
    if "provenance" in k or "change" in k or "attempt_2" in k or "generation_1" in k:
        print("  RA   %s" % k)
        print(json.dumps(P3["risk_architecture"][k], indent=2, ensure_ascii=False)[:3000])

print()
print("=" * 90)
print("CFG-3103 RA2-4 bands (the four-band predecessor)")
print(json.dumps(P2["risk_architecture"]["components"]["RA2-4"]["bands"], indent=2))
print("CFG-3103 RA2-1 value: %s" % P2["risk_architecture"]["components"]["RA2-1"]["value"])

print()
print("=" * 90)
print("Generation 1 RA1-5, the original ladder")
ra1 = None
for exp in G1.get("risk_architecture", {}).get("components", {}).items():
    pass
comp = G1.get("risk_architecture", {}).get("components", {})
print("  G1 components keys: %s" % list(comp))
if "RA1-5" in comp:
    print(json.dumps(comp["RA1-5"], indent=2, ensure_ascii=False)[:2400])
print()
print("  G1 experiments ladder_rungs:")
for exp in G1.get("experiments", []):
    print("    %-30s %s" % (exp.get("experiment_id", "?"),
                            exp.get("primary_parameters", {}).get("ladder_rungs")))
if "RA1-1" in comp:
    print("  G1 RA1-1 value: %s" % comp["RA1-1"].get("value"))
