"""Exactly which of the 13 'carried unchanged' blocks differ from CFG-3103, and how.

CFG-3105's `mechanics_carried_unchanged.method` claims "Only grid.variant_id_format and
grid.variants[].variant_id differ".  A whole-block comparison says three blocks differ, not one, so
either the claim is narrower than it reads or it is wrong.  Print the pointer-level difference so the
RA3 module's verifier can encode the true predicate rather than the claimed one -- and so any
overstatement gets a conflict number instead of being quietly implemented around.
"""

import json
import pathlib

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
P3 = json.loads((ROOT / "config/generation_2/g2_rotation_ra3_protocol.json").read_text("utf-8"))
P2 = json.loads((ROOT / "config/generation_2/g2_rotation_ra1_protocol.json").read_text("utf-8"))


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


def flatten(node, prefix=""):
    out = {}
    if isinstance(node, dict):
        for key, value in node.items():
            out.update(flatten(value, prefix + "/" + str(key)))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            out.update(flatten(value, prefix + "[%d]" % index))
    else:
        out[prefix] = node
    return out


print("=" * 100)
print("mechanics_carried_unchanged.method, verbatim")
print("  " + safe(P3["mechanics_carried_unchanged"]["method"]))
print()
print("why_this_matters")
print("  " + safe(P3["mechanics_carried_unchanged"]["why_this_matters"]))

for block in ("run_span", "grid", "gate_evaluation_scope"):
    a, b = flatten(P3[block]), flatten(P2[block])
    print()
    print("=" * 100)
    print("%s  --  pointer-level difference" % block)
    only3 = sorted(set(a) - set(b))
    only2 = sorted(set(b) - set(a))
    changed = sorted(p for p in set(a) & set(b) if a[p] != b[p])
    print("  pointers only in RA3: %d   only in RA2: %d   present in both but changed: %d"
          % (len(only3), len(only2), len(changed)))
    for pointer in only3[:12]:
        print("   +RA3 %-46s %s" % (pointer, safe(json.dumps(a[pointer], ensure_ascii=False))[:110]))
    if len(only3) > 12:
        print("   ... and %d more RA3-only pointers" % (len(only3) - 12))
    for pointer in only2[:12]:
        print("   -RA2 %-46s %s" % (pointer, safe(json.dumps(b[pointer], ensure_ascii=False))[:110]))
    shown = 0
    for pointer in changed:
        if pointer.startswith("/variants[") and pointer.endswith("/variant_id"):
            shown += 1
            continue
        print("   !CHG %-46s" % pointer)
        print("         RA2: %s" % safe(json.dumps(b[pointer], ensure_ascii=False))[:150])
        print("         RA3: %s" % safe(json.dumps(a[pointer], ensure_ascii=False))[:150])
    if shown:
        print("   !CHG /variants[*]/variant_id  x %d  (expected: the id segment changes by design)" % shown)
