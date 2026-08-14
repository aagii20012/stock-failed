"""Dump requested keys of any sealed Stage 4 artifact verbatim."""
import json
import pathlib
import sys

ROOT = pathlib.Path(r"D:\Product\stock-trade-alpaca\stockedge100")
FILES = {
    "seal": "governance/STAGE_4_PREREGISTRATION.json",
    "protocol": "config/stage4_validation_protocol.json",
    "criteria": "config/stage4_gate_criteria.json",
    "selection": "config/stage4_representative_selection.json",
}

which = sys.argv[1]
doc = json.loads((ROOT / FILES[which]).read_text(encoding="utf-8"))
if len(sys.argv) == 2:
    print("== top-level keys of " + FILES[which] + " ==")
    for k in doc:
        print("  " + k)
else:
    for key in sys.argv[2:]:
        print("== " + which + "." + key + " ==")
        print(json.dumps(doc[key], indent=2))
        print("")
