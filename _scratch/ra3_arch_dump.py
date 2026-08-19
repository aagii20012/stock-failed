"""Every node the RA3 loader will index, printed from CFG-3105.

The loader is going to be a near-copy of the RA2 loader, and a near-copy is exactly where a key that
moved between the two configs turns into a KeyError at run time -- 36 runs in, or worse, in one
variant out of eighteen.  Read the shape first.  Also diffs RA3's component nodes against RA2's, so
that any *sub-field* the RA2 loader validates but RA3 dropped is visible before it is relied on.
"""

import json
import pathlib

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
P3 = json.loads((ROOT / "config/generation_2/g2_rotation_ra3_protocol.json").read_text("utf-8"))
P2 = json.loads((ROOT / "config/generation_2/g2_rotation_ra1_protocol.json").read_text("utf-8"))


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


A3, A2 = P3["risk_architecture"], P2["risk_architecture"]

print("=" * 96)
print("top-level identity fields the loader checks")
for field in ("artifact_id", "generation", "stage", "attempt", "strategy_id",
              "declared_before_any_strategy_code", "live_trading_authorized"):
    print("  %-42s RA3=%-34s RA2=%s"
          % (field, safe(repr(P3.get(field, "<ABSENT>")))[:34], safe(repr(P2.get(field, "<ABSENT>")))[:40]))

print()
print("=" * 96)
print("risk_architecture keys: RA3 vs RA2")
for key in sorted(set(A3) | set(A2)):
    mark = "both" if key in A3 and key in A2 else ("RA3-only" if key in A3 else "RA2-only")
    print("  %-46s %s" % (key, mark))

print()
print("  RA3 id=%r  frozen=%r  not_part_of_the_grid=%r"
      % (A3.get("id"), A3.get("frozen_before_any_variant_is_run"), A3.get("not_part_of_the_grid")))

print()
print("=" * 96)
print("combined_scalar: the three predicates the RA2 loader asserts on the formula")
for label, node in (("RA3", A3.get("combined_scalar")), ("RA2", A2.get("combined_scalar"))):
    if node is None:
        print("  %s: ABSENT" % label)
        continue
    formula = node.get("formula", "")
    print("  %s keys: %s" % (label, list(node)))
    print("    formula: %s" % safe(formula)[:200])
    print("    has 'f_vol(t) * f_ladder(t)': %s" % ("f_vol(t) * f_ladder(t)" in formula))
    print("    has 'nine decimal places':    %s" % ("nine decimal places" in formula))
    print("    has 'ROUND_DOWN':             %s" % ("ROUND_DOWN" in formula))
    dna = node.get("does_not_apply_to", [])
    print("    does_not_apply_to entries:    %d, mentions research shutdown: %s"
          % (len(dna), any("research shutdown" in i for i in dna)))

print()
print("=" * 96)
print("components, field by field")
c3, c2 = A3["components"], A2["components"]
print("  RA3 component keys: %s" % list(c3))
print("  RA2 component keys: %s" % list(c2))

PAIRS = (("RA3-1", "RA2-1"), ("RA3-2", "RA2-2"), ("RA3-3", "RA2-3"),
         ("RA3-4", "RA2-4"), ("RA3-5", "RA2-5"))
for new, old in PAIRS:
    n, o = c3.get(new, {}), c2.get(old, {})
    print()
    print("-- %s vs %s " % (new, old) + "-" * 60)
    for key in sorted(set(n) | set(o)):
        mark = " " if key in n and key in o else ("+" if key in n else "-")
        val = n.get(key, o.get(key))
        print("   %s %-32s %s" % (mark, key, safe(json.dumps(val, ensure_ascii=False))[:110]))

print()
print("=" * 96)
print("the exact sub-fields the RA2 loader dereferences, checked present in RA3")
CHECKS = [
    ("RA3-1", ["enforcement", "part_a_entry_clamp", "clamp_names"]),
    ("RA3-1", ["value"]),
    ("RA3-2", ["measured_on"]),
    ("RA3-2", ["value"]),
    ("RA3-3", ["reference_price"]),
    ("RA3-3", ["value"]),
    ("RA3-4", ["bands"]),
    ("RA3-5", ["value"]),
    ("RA3-5", ["counted_in_sessions_not_days"]),
]
for comp, path in CHECKS:
    node = c3.get(comp)
    ok = True
    for part in path:
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            ok = False
            break
    label = "%s.%s" % (comp, ".".join(path))
    print("  %-52s %s  %s" % (label, "PRESENT" if ok else "ABSENT ",
                              safe(json.dumps(node, ensure_ascii=False))[:70] if ok else ""))

print()
print("-- RA3-4 bands, verbatim " + "-" * 70)
print(json.dumps(c3["RA3-4"]["bands"], indent=2))
print("-- RA2-4 bands, verbatim (the four-band predecessor) " + "-" * 42)
print(json.dumps(c2["RA2-4"]["bands"], indent=2))
