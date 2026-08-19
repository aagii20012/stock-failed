"""Triage the four key misses: which are RA3 renames, which are dead code, which are pre-existing.

`gate.py::condition_3` reads `undefined_cases['no_closed_trades']`, absent from CFG-3106.  That is only
an Attempt 3 problem if the RA3 evaluator would ever *call* it -- `evaluate_representative_ra1` swaps
in `condition_3_ra1` for exactly this family of reasons.  Resolve the call list from the AST rather
than from memory, and check the same keys against CFG-3104 so a pre-existing shape is not reported as
a regression I introduced.
"""

import ast
import json
import pathlib

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
C3 = json.loads((ROOT / "config/generation_2/g2_gate_criteria_ra3.json").read_text("utf-8"))
C2 = json.loads((ROOT / "config/generation_2/g2_gate_criteria_ra1.json").read_text("utf-8"))
K3 = {c["id"]: c for c in C3["conditions"]}
K2 = {c["id"]: c for c in C2["conditions"]}
GATE = ROOT / "src/stockedge100/strategies/g2_gate_ra1.py"


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


print("=" * 100)
print("1. which condition callables does evaluate_representative_ra1 actually invoke?")
tree = ast.parse(GATE.read_text("utf-8"))
for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
           and n.name == "evaluate_representative_ra1"]:
    for node in ast.walk(fn):
        if isinstance(node, (ast.List, ast.Tuple)):
            names = [e.id for e in node.elts if isinstance(e, ast.Name)]
            if len(names) == 7 and all(n.startswith("condition_") for n in names):
                print("   %s" % names)
                from_gate = [n for n in names if not n.endswith("_ra1")]
                print("   inherited from the frozen gate.py: %s" % from_gate)
                print("   condition_3 (gate.py) invoked here: %s" % ("condition_3" in names))

print()
print("=" * 100)
print("2. undefined_cases in S3-C3 -- RA3 vs Attempt 2 vs what gate.py::condition_3 wants")
for label, node in (("RA3 (CFG-3106)", K3["S3-C3"]), ("Att2 (CFG-3104)", K2["S3-C3"])):
    print("   %-18s undefined_cases keys: %s" % (label, sorted(node["undefined_cases"])))
print("   gate.py::condition_3 wants: ['no_closed_trades', 'no_losing_trades']")
print("   -> present in Attempt 2's file too? %s"
      % all(k in K2["S3-C3"]["undefined_cases"] for k in ("no_closed_trades", "no_losing_trades")))

print()
print("=" * 100)
print("3. S3-C6 scope_interpretation -- the second rename")
for label, node in (("RA3 (CFG-3106)", K3["S3-C6"]), ("Att2 (CFG-3104)", K2["S3-C6"])):
    print("   %-18s %s" % (label, sorted(node["scope_interpretation"])))
only3 = sorted(set(K3["S3-C6"]["scope_interpretation"]) - set(K2["S3-C6"]["scope_interpretation"]))
only2 = sorted(set(K2["S3-C6"]["scope_interpretation"]) - set(K3["S3-C6"]["scope_interpretation"]))
print("   only-RA3=%s   only-Att2=%s" % (only3, only2))
for key in only3:
    print()
    print("   RA3 %s:" % key)
    print("      %s" % safe(K3["S3-C6"]["scope_interpretation"][key]))

print()
print("=" * 100)
print("4. the two renamed keys, RA3 values in full (these are the prose the evidence must carry)")
print("   S3-C3.attempt_3_note:")
print("      %s" % safe(K3["S3-C3"]["attempt_3_note"]))
print()
print("   S3-C3.attempt_3_status:")
print("      %s" % safe(K3["S3-C3"]["attempt_3_status"]))

print()
print("=" * 100)
print("5. exact call sites of the four missing lookups")
src = GATE.read_text("utf-8").splitlines()
for i, line in enumerate(src, 1):
    if "attempt_2_note" in line or "attempt_2_significance" in line:
        print("   g2_gate_ra1.py:%d  %s" % (i, safe(line.strip())))

print()
print("=" * 100)
print("6. every 'attempt_2'/'attempt_3' key name across all seven conditions, both files")
for cid in sorted(K3):
    a = sorted(k for k in K3[cid] if "attempt_" in k)
    b = sorted(k for k in K2[cid] if "attempt_" in k)
    nested3 = sorted("scope_interpretation.%s" % k for k in K3[cid].get("scope_interpretation", {})
                     if "attempt_" in k)
    nested2 = sorted("scope_interpretation.%s" % k for k in K2[cid].get("scope_interpretation", {})
                     if "attempt_" in k)
    print("   %-8s RA3=%s  Att2=%s" % (cid, a + nested3, b + nested2))
