import json, pathlib, sys
ROOT = pathlib.Path(r"D:\Product\stock-trade-alpaca\stockedge100")
DEC = json.loads((ROOT/"reports/stage3_g2_attempt3/STAGE_3_G2_A3_ROTATION_RESEARCH.json").read_text(encoding="utf-8"))
EV  = json.loads((ROOT/"reports/stage3_g2_attempt3/STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json").read_text(encoding="utf-8"))
def out(t): sys.stdout.write(str(t).encode("ascii","backslashreplace").decode("ascii")+"\n")

out("=== the six satisfied conditions")
for cid, row in DEC["gate_conditions"].items():
    if cid == "admissible_candidate_exists" or not row.get("satisfied"): continue
    out("%-7s %-11s met_by=%s n/a=%s measured=%s"
        % (cid, row.get("verdict"), row.get("met_by"), row.get("not_applicable_for"),
           json.dumps(row.get("measured"))[:150]))
out("")
out("=== artifacts written (from the decision record)")
for k in ("artifacts","artifacts_written","files_written","artifact_manifest"):
    if k in DEC: out("%s: %s" % (k, json.dumps(DEC[k])[:1800]))
out("")
out("=== keys of the decision record")
out(sorted(DEC.keys()))
out("")
out("=== prior attempt comparison keys in evidence")
for k in sorted(EV.keys()):
    if "attempt" in k or "prior" in k or "compar" in k: out("  "+k)
