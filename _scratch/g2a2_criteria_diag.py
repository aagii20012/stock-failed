"""Diagnose the five failures: enumerate the real key sets before rewriting any predicate."""
from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1] / "stockedge100"
A1 = json.loads((ROOT / "config/generation_2/g2_gate_criteria.json").read_text(encoding="utf-8"))
NEW = json.loads((ROOT / "config/generation_2/g2_gate_criteria_ra1.json").read_text(encoding="utf-8"))
CONST = json.loads((ROOT / "governance/STAGE_0_CONSTITUTION.json").read_text(encoding="utf-8"))

gate3 = None


def walk(node):
    global gate3
    if isinstance(node, dict):
        if node.get("id") == 3 and node.get("name") == "development_admissibility":
            gate3 = node
        for v in node.values():
            walk(v)
    elif isinstance(node, list):
        for v in node:
            walk(v)


walk(CONST)
print("--- constitution gate 3 object ---")
print("keys:", sorted(gate3))
for k, v in gate3.items():
    s = json.dumps(v)
    print("  %-16s %s" % (k, s if len(s) < 200 else s[:200] + " ...(%d)" % len(s)))

print("\n--- where does the gate 3 PROSE live in the constitution JSON? ---")
needle = "This gate rejects obviously weak"
found = []


def hunt(node, path="$"):
    if isinstance(node, dict):
        for k, v in node.items():
            hunt(v, "%s.%s" % (path, k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            hunt(v, "%s[%d]" % (path, i))
    elif isinstance(node, str) and needle in node:
        found.append((path, len(node)))


hunt(CONST)
print("hits:", found if found else "NONE -- prose is not in the JSON companion")

print("\n--- Attempt 1 condition field sets vs Attempt 2 ---")
a1c = {c["id"]: c for c in A1["conditions"]}
n2c = {c["id"]: c for c in NEW["conditions"]}
for cid in ["S3-C%d" % i for i in range(1, 8)]:
    a, n = set(a1c[cid]), set(n2c[cid])
    print("%s" % cid)
    print("   A1 : %s" % sorted(a))
    print("   A2 : %s" % sorted(n))
    print("   dropped=%s  added=%s" % (sorted(a - n), sorted(n - a)))
    print("   'NOT_EVALUABLE' anywhere in A1 body: %s | in A2 body: %s"
          % ("NOT_EVALUABLE" in json.dumps(a1c[cid]), "NOT_EVALUABLE" in json.dumps(n2c[cid])))

print("\n--- S3-C5 attempt_2_status text ---")
print(repr(n2c["S3-C5"]["attempt_2_status"]))
