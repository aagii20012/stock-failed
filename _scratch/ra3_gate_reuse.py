"""Per-condition, per-function: exactly which sealed keys each reusable evaluator dereferences.

The whole-file key sweep conflates the seven conditions -- `spec["undefined_cases"]` is read by
condition_3 and not by condition_5, so a flat "missing from S3-C5" list says nothing.  Walk each
function's AST instead, resolve the `_condition(criteria, "S3-CN")` it binds `spec` to, and check that
condition's node in CFG-3106.

A single miss is a KeyError inside a gate evaluation, which is the worst place to find one.
"""

import ast
import json
import pathlib

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
C3 = json.loads((ROOT / "config/generation_2/g2_gate_criteria_ra3.json").read_text("utf-8"))
BY_ID = {c["id"]: c for c in C3["conditions"]}

SOURCES = {
    "g2_gate_ra1.py": ROOT / "src/stockedge100/strategies/g2_gate_ra1.py",
    "gate.py": ROOT / "src/stockedge100/strategies/gate.py",
}


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


def const(node):
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def chain(node):
    """['spec', 'measurement', 'basis'] for spec["measurement"]["basis"]."""
    parts = []
    while isinstance(node, ast.Subscript):
        key = const(node.slice)
        if key is None:
            return None
        parts.append(key)
        node = node.value
    if not isinstance(node, ast.Name):
        return None
    return [node.id] + list(reversed(parts))


problems = []

for filename, path in SOURCES.items():
    tree = ast.parse(path.read_text("utf-8"))
    for fn in [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
        # which condition does this function bind `spec` to?
        cond_id = None
        for call in [n for n in ast.walk(fn) if isinstance(n, ast.Call)]:
            if isinstance(call.func, ast.Name) and call.func.id == "_condition" and len(call.args) == 2:
                cond_id = const(call.args[1])
        reads = {}
        for sub in [n for n in ast.walk(fn) if isinstance(n, ast.Subscript)]:
            parts = chain(sub)
            if not parts or parts[0] not in ("spec", "criteria") or len(parts) < 2:
                continue
            reads.setdefault(parts[0], set()).add(tuple(parts[1:]))
        if not reads:
            continue

        print("=" * 100)
        print("%s :: %s   (spec bound to %s)" % (filename, fn.name, cond_id or "<none>"))

        for root_name, paths in sorted(reads.items()):
            base = BY_ID.get(cond_id) if root_name == "spec" else C3
            for parts in sorted(paths):
                node, ok, where = base, True, []
                if base is None:
                    ok, where = False, ["<condition %s absent>" % cond_id]
                else:
                    for part in parts:
                        where.append(part)
                        if isinstance(node, dict) and part in node:
                            node = node[part]
                        else:
                            ok = False
                            break
                label = "%s[%s]" % (root_name, "][".join(repr(p) for p in parts))
                if ok:
                    print("   ok   %-58s %s" % (label, safe(json.dumps(node, ensure_ascii=False))[:40]))
                else:
                    print("   MISS %-58s stopped at %r" % (label, where[-1]))
                    problems.append("%s::%s  %s  (condition %s)" % (filename, fn.name, label, cond_id))

print()
print("=" * 100)
print("PROBLEMS: %d" % len(problems))
for item in problems:
    print("   %s" % item)

print()
print("=" * 100)
print("what CFG-3106's S3-C3 actually carries")
for key in sorted(BY_ID["S3-C3"]):
    print("   %-28s %s" % (key, safe(json.dumps(BY_ID["S3-C3"][key], ensure_ascii=False))[:92]))

print()
print("S3-C7 measurement, the two RA3-only keys")
for key in ("shared_with_selection", "neighbour_count_conflict", "neighbour_count", "neighbour_definition"):
    value = BY_ID["S3-C7"]["measurement"].get(key, "<ABSENT>")
    print("   %-28s %s" % (key, safe(value)[:220]))
