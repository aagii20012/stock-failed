"""Read the last controlling Stage 4 artifacts the pre-access sweep has not yet displayed.

ASCII-only output: the console is cp1252 and a U+2192 in a report kills the script mid-sweep.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(r"D:\Product\stock-trade-alpaca\stockedge100")


def out(text):
    sys.stdout.write(text.encode("ascii", "backslashreplace").decode("ascii") + "\n")


dec = json.loads(
    (ROOT / "reports/stage4/STAGE_4_VALIDATION_PREREGISTRATION.json").read_text(encoding="utf-8")
)
out("== decision record top-level keys ==")
for k, v in dec.items():
    size = len(v) if isinstance(v, (list, dict, str)) else ""
    out("  %-34s %-6s %s" % (k, type(v).__name__, size))
out("")
out("== decision.gate_conditions keys ==")
out("  " + ", ".join(dec["gate_conditions"]))
out("")
for key in ("reproducibility", "tests", "verdict", "gate_passed", "gate_id", "gate_name",
            "stage", "run_id", "generated_utc", "command"):
    if key in dec:
        out("== decision.%s ==" % key)
        out(json.dumps(dec[key], indent=2)[:2500])
        out("")

out("=" * 78)
out("runs/SE100-R-20260813T140121Z.json  (the Gate 3 Attempt 2 evaluation / sealing run)")
out("=" * 78)
run = json.loads((ROOT / "runs/SE100-R-20260813T140121Z.json").read_text(encoding="utf-8"))
for k, v in run.items():
    if k == "code_hashes":
        out("  code_hashes: %d entries (suppressed)" % len(v))
        continue
    out("  %s: %s" % (k, json.dumps(v, indent=2)[:1800]))
