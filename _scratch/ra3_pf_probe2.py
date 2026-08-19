import json, pathlib, sys
ROOT = pathlib.Path(r"D:\Product\stock-trade-alpaca\stockedge100")
def out(t): sys.stdout.write(str(t).encode("ascii","backslashreplace").decode("ascii")+"\n")
EV = json.loads((ROOT/"reports/stage3_g2_attempt3/STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json").read_text(encoding="utf-8"))
R3 = "SE100-G2-S3-C3-ROTATION-RA3-L03-K2-QUARTERLY"
for r in EV["runs"]:
    if r["variant_id"] == R3 and r["scenario"] == "BASE":
        for k in sorted(r):
            if any(w in k for w in ("profit","gross","loss","win","pf")):
                out("  %s: %s" % (k, str(r[k])[:60]))
        out("  --- all keys:"); out("  " + ", ".join(sorted(r)))
out("")
out("=== candidate_results conditions block for S3-C3")
cr = EV.get("candidate_results") or []
out(json.dumps([c for c in cr], indent=1, sort_keys=True)[:200] if cr else "no candidate_results in EV")
for k in sorted(EV):
    if "gate" in k or "condition" in k: out("EV key: %s" % k)
