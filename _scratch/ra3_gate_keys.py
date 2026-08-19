"""Which of Attempt 2's gate evaluator can be reused against Attempt 3's criteria file.

`condition_3_ra1` .. `condition_6_ra1` all take `criteria` as a parameter, so they are reusable iff
every key they dereference exists in CFG-3107 with the same shape.  `condition_7_ra1` is already known
not to be reusable -- it resolves neighbours in `g2_rotation_ra1`'s grid, so an RA3 representative
would be compared against Attempt 2's variant ids -- but measure that too rather than asserting it.

Also dump the token derivation and the counterpart keys, since Attempt 3 has *two* closed predecessors
where Attempt 2 had one, and the withheld-token check has to cover both.
"""

import json
import pathlib
import re

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
C3 = json.loads((ROOT / "config/generation_2/g2_gate_criteria_ra3.json").read_text("utf-8"))
C2 = json.loads((ROOT / "config/generation_2/g2_gate_criteria_ra1.json").read_text("utf-8"))
GATE_SRC = (ROOT / "src/stockedge100/strategies/g2_gate_ra1.py").read_text("utf-8")


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


def conditions_of(doc):
    return {c["id"]: c for c in doc["conditions"]}


print("=" * 100)
print("top-level keys")
for key in sorted(set(C3) | set(C2)):
    mark = "    " if key in C3 and key in C2 else ("+RA3" if key in C3 else "-RA2")
    print("  %s %s" % (mark, key))

print()
print("=" * 100)
print("artifact identity")
for key in ("artifact_id", "generation", "stage", "attempt", "declared_before_any_strategy_code"):
    print("  %-38s RA3=%-24s RA2=%s" % (key, safe(C3.get(key, "<ABSENT>")), safe(C2.get(key, "<ABSENT>"))))

print()
print("=" * 100)
print("conditions present")
K3, K2 = conditions_of(C3), conditions_of(C2)
print("  RA3: %s" % sorted(K3))
print("  RA2: %s" % sorted(K2))
print("  same set: %s" % (sorted(K3) == sorted(K2)))

print()
print("=" * 100)
print("per-condition key structure (RA3 vs RA2), including nested 'measurement'")
for cid in sorted(set(K3) | set(K2)):
    a, b = K3.get(cid, {}), K2.get(cid, {})
    only3, only2 = sorted(set(a) - set(b)), sorted(set(b) - set(a))
    print("  %-8s keys=%-3d  only-RA3=%-28s only-RA2=%s"
          % (cid, len(a), only3 or "-", only2 or "-"))
    for sub in ("measurement", "evidence_requirements"):
        if isinstance(a.get(sub), dict) or isinstance(b.get(sub), dict):
            sa, sb = set(a.get(sub, {})), set(b.get(sub, {}))
            d3, d2 = sorted(sa - sb), sorted(sb - sa)
            if d3 or d2:
                print("       .%-22s only-RA3=%s  only-RA2=%s" % (sub, d3 or "-", d2 or "-"))

print()
print("=" * 100)
print("every criteria subscript literal appearing in g2_gate_ra1.py, resolved against RA3")
# spec["x"], spec["measurement"]["y"], criteria["z"], criteria["z"]["w"]
missing = []
for var, node3 in (("criteria", C3),):
    for match in sorted(set(re.findall(r'criteria\[\s*"([a-z0-9_]+)"\s*\](?:\[\s*"([a-z0-9_]+)"\s*\])?', GATE_SRC))):
        top, sub = match
        ok_top = top in node3
        detail = "PRESENT" if ok_top else "*** ABSENT ***"
        if ok_top and sub:
            ok_sub = isinstance(node3[top], dict) and sub in node3[top]
            detail = "PRESENT" if ok_sub else "*** ABSENT (sub) ***"
            if not ok_sub:
                missing.append("criteria[%r][%r]" % (top, sub))
        elif not ok_top:
            missing.append("criteria[%r]" % top)
        print("  criteria[%-46s %s" % ('"%s"]%s' % (top, '["%s"]' % sub if sub else ""), detail))

print()
print("spec[...] literals, resolved against every RA3 condition that a condition_N reads")
spec_keys = sorted(set(re.findall(r'spec\[\s*"([a-z0-9_]+)"\s*\]', GATE_SRC)))
spec_measure = sorted(set(re.findall(r'spec\["measurement"\]\[\s*"([a-z0-9_]+)"\s*\]', GATE_SRC)))
print("  spec keys read anywhere:        %s" % spec_keys)
print("  spec['measurement'] keys read:  %s" % spec_measure)
for cid in sorted(K3):
    absent = [k for k in spec_keys if k not in K3[cid]]
    print("  %-8s missing top-level spec keys: %s" % (cid, absent or "-"))

print()
print("=" * 100)
print("verdict_token_derivation")
for doc, label in ((C3, "RA3"), (C2, "RA2")):
    d = doc.get("verdict_token_derivation", {})
    print("  %s keys: %s" % (label, sorted(d)))
    for key in sorted(d):
        print("     %-52s %s" % (key, safe(json.dumps(d[key], ensure_ascii=False))[:96]))
    print()

print("=" * 100)
print("counterpart / relationship keys in RA3")
for key in sorted(C3):
    if "counterpart" in key or key.startswith("relationship_to") or "prior" in key:
        print("  %-46s %s" % (key, safe(json.dumps(C3[key], ensure_ascii=False))[:110]))

print()
print("=" * 100)
print("MISSING SUBSCRIPTS: %d" % len(missing))
for item in missing:
    print("   %s" % item)
