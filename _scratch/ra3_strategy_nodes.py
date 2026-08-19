"""The nodes g2_rotation_ra1's four strategy-level verifiers dereference, in RA3's protocol.

`g2_rotation_ra3` intends to reuse those verifiers by import rather than copy.  A verifier that reads
`unchanged_from_attempt_1` off a file whose author wrote `unchanged_from_attempt_2` raises on a field
name, not on a governance fact, so check every key each one touches before relying on reuse.  Also
prints the fields `rotation_variants()` reads per variant, since a missing
`scheduled_rebalance_sessions` would be a KeyError inside a loop over eighteen.
"""

import json
import pathlib

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
P3 = json.loads((ROOT / "config/generation_2/g2_rotation_ra3_protocol.json").read_text("utf-8"))
P2 = json.loads((ROOT / "config/generation_2/g2_rotation_ra1_protocol.json").read_text("utf-8"))


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


def show(label, node3, node2, keys=None):
    print()
    print("=" * 98)
    print(label)
    keys = sorted(set(node3) | set(node2)) if keys is None else keys
    for key in keys:
        mark = " " if key in node3 and key in node2 else ("+RA3" if key in node3 else "-RA2")
        val = node3.get(key, "<ABSENT IN RA3>")
        print("  %-4s %-44s %s" % (mark, key, safe(json.dumps(val, ensure_ascii=False))[:110]))


show("eligible_universe", P3["eligible_universe"], P2["eligible_universe"])
show("family / top-level", {"family": P3["family"]}, {"family": P2["family"]})
show("execution", P3["execution"], P2["execution"])
print()
print("  order_kinds_this_attempt_may_issue:")
for entry in P3["execution"]["order_kinds_this_attempt_may_issue"]:
    print("    " + safe(json.dumps(entry, ensure_ascii=False))[:170])

show("rebalance", P3["rebalance"], P2["rebalance"])
print("  rebalance.rule: %s" % safe(P3["rebalance"]["rule"])[:300])
print("  rebalance.values: %s" % P3["rebalance"]["values"])

show("position_sizing", P3["position_sizing"], P2["position_sizing"])
print("  target_weights:        %s" % json.dumps(P3["position_sizing"].get("target_weights")))
print("  target_gross_exposure: %s" % json.dumps(P3["position_sizing"].get("target_gross_exposure")))
print("  formula: %s" % safe(P3["position_sizing"].get("target_weight_formula", ""))[:200])

show("mechanics_carried_unchanged", P3["mechanics_carried_unchanged"], P2.get("mechanics_carried_unchanged", {}))
for key, value in P3["mechanics_carried_unchanged"].items():
    print("  -- %s: %s" % (key, safe(json.dumps(value, ensure_ascii=False))[:400]))

print()
print("=" * 98)
print("grid variant entry, all fields (first two)")
for entry in P3["grid"]["variants"][:2]:
    print("  " + safe(json.dumps(entry, ensure_ascii=False)))
print("  RA2's first entry for comparison:")
print("  " + safe(json.dumps(P2["grid"]["variants"][0], ensure_ascii=False)))

print()
print("=" * 98)
print("concentration_ceiling node and window/run_span")
print("  concentration_ceiling: %s" % safe(json.dumps(P3["concentration_ceiling"], ensure_ascii=False))[:600])
print("  window:                %s" % safe(json.dumps(P3["window"], ensure_ascii=False))[:600])
print("  run_span keys:         %s" % list(P3["run_span"]))
for key in P3["run_span"]:
    print("     %-38s %s" % (key, safe(json.dumps(P3["run_span"][key], ensure_ascii=False))[:100]))
