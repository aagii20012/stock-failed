import json, pathlib, sys
ROOT = pathlib.Path(r"D:\Product\stock-trade-alpaca\stockedge100")
DEC = json.loads((ROOT/"reports/stage3_g2_attempt3/STAGE_3_G2_A3_ROTATION_RESEARCH.json").read_text(encoding="utf-8"))
EV  = json.loads((ROOT/"reports/stage3_g2_attempt3/STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json").read_text(encoding="utf-8"))
def out(t): sys.stdout.write(str(t).encode("ascii","backslashreplace").decode("ascii")+"\n")
for k in ("tests","reconciliation","multiple_comparisons_disclosure","risk_architecture","determinism"):
    out("=== DEC[%s]" % k); out(json.dumps(DEC[k], indent=1, sort_keys=True)[:2200]); out("")
for k in ("attempt_1_ref","attempt_2_ref","what_this_attempt_changes_from_attempt_2"):
    out("=== EV[%s]" % k); out(json.dumps(EV[k], indent=1, sort_keys=True)[:1600]); out("")
