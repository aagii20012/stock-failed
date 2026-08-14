"""Out-of-tree: which traced test names are still undefined, and which sealed rows cite them."""

import ast
import sys
from pathlib import Path

ROOT = Path(r"d:\Product\stock-trade-alpaca\stockedge100")
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.strategies import attempt2_traceability as tm

named = set(tm.all_named_tests())

defined = set()
for path in (ROOT / "tests").rglob("*.py"):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            defined.add(node.name)

missing = sorted(named - defined)
print(f"named={len(named)} defined_anywhere={len(defined)} missing={len(missing)}")
print()

want = sys.argv[1] if len(sys.argv) > 1 else ""

for name in missing:
    rows = [t for t in tm.TRACES if name in tuple(t.verified_by or ())]
    if want and want not in name:
        continue
    print(f"### {name}")
    for row in rows:
        print(f"    doc  : {row.document}")
        print(f"    path : {row.path}")
        print(f"    impl : {row.implementation}")
        if row.note:
            print(f"    note : {row.note}")
    print()
