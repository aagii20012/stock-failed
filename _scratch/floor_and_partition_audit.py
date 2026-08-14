"""Re-extract the two claims the evaluation test summary makes, so neither is typed from memory:

1. every tests/**/*.py entry recorded in the Attempt 2 design run record still hashes to its recorded
   value, and which files are additions;
2. no test module names a validation- or holdout-dated literal.

Nothing here is part of the repository state.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(r"d:\Product\stock-trade-alpaca\stockedge100")
sys.path.insert(0, str(ROOT / "src"))
from stockedge100.audit import sha256_file  # noqa: E402

run = json.loads((ROOT / "runs/SE100-R-20260810T131107Z.json").read_text(encoding="utf-8"))
recorded = {k: v for k, v in run["code_hashes"].items() if k.startswith("tests/")}
live = {
    p.relative_to(ROOT).as_posix(): sha256_file(p)
    for p in sorted(ROOT.glob("tests/**/*.py"))
}

unchanged = [k for k, v in recorded.items() if live.get(k) == v]
changed = [k for k, v in recorded.items() if k in live and live[k] != v]
missing = [k for k in recorded if k not in live]
added = [k for k in live if k not in recorded]

print("=== tests/**/*.py against runs/SE100-R-20260810T131107Z.json code_hashes ===")
print(f"  recorded  {len(recorded)}")
print(f"  unchanged {len(unchanged)}")
print(f"  changed   {len(changed)} {changed}")
print(f"  missing   {len(missing)} {missing}")
print(f"  live      {len(live)}")
print(f"  added     {len(added)}")
for name in added:
    print(f"    + {name}")

src_recorded = {k: v for k, v in run["code_hashes"].items() if k.startswith("src/")}
src_live = {
    p.relative_to(ROOT).as_posix(): sha256_file(p) for p in sorted(ROOT.glob("src/**/*.py"))
}
src_changed = [k for k, v in src_recorded.items() if k in src_live and src_live[k] != v]
src_missing = [k for k in src_recorded if k not in src_live]
src_added = [k for k in src_live if k not in src_recorded]
print("\n=== src/**/*.py against the same record ===")
print(f"  recorded {len(src_recorded)}  live {len(src_live)}")
print(f"  changed  {len(src_changed)}")
for name in src_changed:
    print(f"    ~ {name}")
print(f"  missing  {len(src_missing)} {src_missing}")
print(f"  added    {len(src_added)}")
for name in src_added:
    print(f"    + {name}")

print(f"\n=== total code_hashes entries in the design run record: {len(run['code_hashes'])} ===")

# --- restricted-partition audit -----------------------------------------------------------------
lock = json.loads((ROOT / "governance/STAGE_1_HOLDOUT_LOCK.json").read_text(encoding="utf-8"))
print("\n=== window bounds as read from the lock ===")
print(json.dumps({k: v for k, v in lock.items() if "window" in k or "partition" in k}, indent=2)[:900])

DATE = re.compile(r"\b(20(?:2[1-9]|[3-9]\d))-(\d{2})-(\d{2})\b")
print("\n=== any 2021-2099 date literal in tests/, with its line ===")
hits = 0
for path in sorted(ROOT.glob("tests/**/*.py")):
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        for match in DATE.finditer(line):
            text = match.group(0)
            if text <= "2021-07-31":
                continue
            hits += 1
            print(f"  {path.relative_to(ROOT).as_posix()}:{lineno}  {text}  |  {line.strip()[:120]}")
print(f"  total: {hits}")
