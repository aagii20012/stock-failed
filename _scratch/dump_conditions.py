"""Dump the seven Gate 4 conditions and the surrounding decision rules verbatim (ASCII-safe)."""
import json
import pathlib
import sys

ROOT = pathlib.Path(r"D:\Product\stock-trade-alpaca\stockedge100")
crit = json.loads((ROOT / "config/stage4_gate_criteria.json").read_text(encoding="utf-8"))

for what in sys.argv[1:] or ["conditions"]:
    text = "== " + what + " ==\n" + json.dumps(crit[what], indent=2)
    sys.stdout.write(text.encode("ascii", "backslashreplace").decode("ascii") + "\n\n")
