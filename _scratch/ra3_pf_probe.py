import json, pathlib, sys
ROOT = pathlib.Path(r"D:\Product\stock-trade-alpaca\stockedge100")
def out(t): sys.stdout.write(str(t).encode("ascii","backslashreplace").decode("ascii")+"\n")
DEC = json.loads((ROOT/"reports/stage3_g2_attempt3/STAGE_3_G2_A3_ROTATION_RESEARCH.json").read_text(encoding="utf-8"))
EV  = json.loads((ROOT/"reports/stage3_g2_attempt3/STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json").read_text(encoding="utf-8"))
for cid in ("S3-C3","S3-C5","S3-C7"):
    r = DEC["gate_conditions"][cid]
    out("=== %s" % cid)
    for k in ("required_verbatim","predicate","measured","threshold","source","note","measurement_source"):
        if k in r: out("  %s: %s" % (k, json.dumps(r[k])[:600]))
    out("")
out("=== candidate_results")
out(json.dumps(DEC["candidate_results"], indent=1, sort_keys=True)[:2500])
