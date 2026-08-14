"""Resolve the four keys the first probe could not find. ASCII-only: the console is cp1252."""
import json
import pathlib
import sys

ROOT = pathlib.Path(r"D:\Product\stock-trade-alpaca\stockedge100")


def out(text):
    sys.stdout.write(str(text).encode("ascii", "backslashreplace").decode("ascii") + "\n")


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


ev = load("reports/stage4/STAGE_4_VALIDATION_EVIDENCE.json")
proto = load("config/stage4_validation_protocol.json")
lock = load("governance/STAGE_1_HOLDOUT_LOCK.json")
sel = load("config/stage4_representative_selection.json")

out("== single_validation_read ==")
for key, value in ev["single_validation_read"].items():
    out("  %-30s %s" % (key, json.dumps(value, default=str)[:150]))
out("")

out("== holdout_unreachability_proof ==")
for key, value in ev["holdout_unreachability_proof"].items():
    out("  %-30s %s" % (key, json.dumps(value, default=str)[:150]))
out("")

out("== protocol.runs_declared ==")
for key, value in proto["runs_declared"].items():
    out("  %-38s %s" % (key, json.dumps(value, default=str)[:130]))
out("")

out("== protocol keys mentioning session / rerun / read ==")
for key in sorted(proto):
    if any(word in key for word in ("session", "rerun", "re_run", "read", "load", "failed")):
        out("  %-44s %s" % (key, json.dumps(proto[key], default=str)[:150]))
out("")

out("== holdout lock ==")
for key, value in lock.items():
    out("  %-30s %s" % (key, json.dumps(value, default=str)[:150]))
out("")

out("== representative selection ==")
for key, value in sel.items():
    out("  %-30s %s" % (key, json.dumps(value, default=str)[:150]))
