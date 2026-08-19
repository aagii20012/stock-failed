"""Prove the test floor only rose: recompute every tests/**/*.py digest the previous run record
carried, against disk, and report recorded / unchanged / changed / missing plus what is new."""

import hashlib
import json
import pathlib

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
RUNS = ROOT / "runs"

records = sorted(RUNS.glob("SE100-R-*.json"))
prior = records[-1]
doc = json.loads(prior.read_text(encoding="utf-8"))
print("previous run record: %s" % prior.name)


def find_hashes(node):
    """The code-hash map is nested differently across generations; find it by shape."""
    if isinstance(node, dict):
        keys = list(node)
        if keys and all(isinstance(v, str) and len(v) == 64 for v in node.values()):
            if any(k.endswith(".py") for k in keys):
                return node
        for value in node.values():
            found = find_hashes(value)
            if found is not None:
                return found
    return None


hashes = find_hashes(doc)
recorded = {k: v for k, v in hashes.items() if k.startswith("tests/") and k.endswith(".py")}
print("recorded tests/**/*.py entries: %d" % len(recorded))

unchanged = changed = 0
for rel, digest in sorted(recorded.items()):
    path = ROOT / rel
    if not path.exists():
        print("   MISSING  %s" % rel)
        continue
    live = hashlib.sha256(path.read_bytes()).hexdigest()
    if live == digest:
        unchanged += 1
    else:
        changed += 1
        print("   CHANGED  %s" % rel)

on_disk = sorted(p.relative_to(ROOT).as_posix() for p in ROOT.glob("tests/**/*.py"))
new = [p for p in on_disk if p not in recorded]

print()
print("unchanged = %d" % unchanged)
print("changed   = %d   (any non-zero is a weakened or rewritten test)" % changed)
print("missing   = %d   (any non-zero is a deleted test)" % (len(recorded) - unchanged - changed))
print("on disk   = %d" % len(on_disk))
print("new this session:")
for path in new:
    print("   + %s" % path)
