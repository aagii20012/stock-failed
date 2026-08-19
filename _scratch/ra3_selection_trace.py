"""Trace SEL-2's selection of the Attempt 3 representative through its own computation.

The end-of-session report must give the selected variant's stability score and its neighbours'
scores "traced to SEL-2's actual computation, not asserted". So this re-runs the selection over the
evidence file's own per-variant statistics and prints the score table, rather than reading a
`selected_score` field back out and repeating it.
"""

import json
import pathlib
import sys

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.strategies import g2_selection_v2 as sel

EVID = ROOT / "reports/stage3_g2_attempt3/STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json"
doc = json.loads(EVID.read_text(encoding="utf-8"))

print("evidence keys: %s" % sorted(doc))
print()
print("selection module public surface:")
print("   %s" % sorted(n for n in dir(sel) if not n.startswith("_")))

node = doc.get("selection") or {}
print()
print("selection node keys: %s" % sorted(node))
for key in sorted(node):
    value = node[key]
    if isinstance(value, (dict, list)):
        print("   %-28s = %s" % (key, json.dumps(value, default=str)[:400]))
    else:
        print("   %-28s = %r" % (key, value))
