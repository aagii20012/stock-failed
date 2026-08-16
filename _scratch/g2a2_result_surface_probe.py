"""Second half of the surface probe: BacktestResult, the fill record, the candidate. ASCII only."""

from __future__ import annotations

import dataclasses
import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
sys.path.insert(0, str(ROOT / "src"))

import stockedge100.backtest.engine as eng  # noqa: E402
import stockedge100.backtest.orders as orders  # noqa: E402
from stockedge100.strategies import g2_rotation_ra1 as rot  # noqa: E402

print("== backtest.engine exports ==")
print([n for n in dir(eng) if n[0].isupper()])

for name in ("BacktestResult", "FillRecord", "Fill", "TradeRecord"):
    obj = getattr(eng, name, None) or getattr(orders, name, None)
    if obj is None:
        print("MISSING", name)
        continue
    try:
        print("%-16s %s" % (name, [f.name for f in dataclasses.fields(obj)]))
    except Exception as exc:  # noqa: BLE001
        print("%-16s not a dataclass: %s" % (name, exc))

print()
print("== orders exports ==")
print([n for n in dir(orders) if not n.startswith("_")])

print()
print("== candidate surface ==")
variant = rot.rotation_variants()[0]
cand = rot.RotationCandidateRA1(variant, rot.rotation_cost_model(variant.top_k, "BASE"),
                                universe=("AAA", "BBB", "CCC", "DDD", "EEE"))
print("weight              ", getattr(cand, "weight", "MISSING"))
print("evidence sig        ", inspect.signature(cand.evidence))
print("public attrs        ", [n for n in dir(cand) if not n.startswith("_")])

print()
print("== variant 0 / 4 / 8 ids ==")
for v in rot.rotation_variants():
    print("  %2d %s k=%s freq=%s target_weight=%s" % (
        v.index, v.variant_id, v.top_k, v.frequency, v.target_weight))
