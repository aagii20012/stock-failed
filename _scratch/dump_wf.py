"""Dump the sealed walk-forward fold construction and the seven Gate 4 conditions verbatim."""
import json
import pathlib

ROOT = pathlib.Path(r"D:\Product\stock-trade-alpaca\stockedge100")
crit = json.loads((ROOT / "config/stage4_gate_criteria.json").read_text(encoding="utf-8"))

print("== top-level keys ==")
print(list(crit.keys()))
print("")
print("== walk_forward_fold_construction ==")
print(json.dumps(crit["walk_forward_fold_construction"], indent=2))
