import json, pathlib, sys, collections
ROOT = pathlib.Path(r"D:\Product\stock-trade-alpaca\stockedge100")
def out(t): sys.stdout.write(str(t).encode("ascii","backslashreplace").decode("ascii")+"\n")
A1 = json.loads((ROOT/"reports/stage3_g2/STAGE_3_G2_DEVELOPMENT_ADMISSIBILITY.json").read_text(encoding="utf-8"))
sess = [r["shutdown_session"] for r in A1["runs"] if r.get("shutdown_session")]
out("A1 shutdown sessions, %d of 36 runs:" % len(sess))
out("  by year: %s" % dict(sorted(collections.Counter(s[:4] for s in sess).items())))
out("  sorted: %s" % sorted(sess))
out("")
A2 = json.loads((ROOT/"reports/stage3_g2_attempt2/STAGE_3_G2_A2_DEVELOPMENT_ADMISSIBILITY.json").read_text(encoding="utf-8"))
REP = "SE100-G2-S3-C2-ROTATION-RA1-L12-K1-QUARTERLY"
out("A2 representative %s:" % REP)
for r in A2["runs"]:
    if r["variant_id"] == REP:
        out("  %-9s ret=%s mdd=%s pf=%s trd=%s lad=%s lck=%s stp=%s scalar_min=%s"
            % (r["scenario"], r["total_return"][:13], r["max_drawdown"][:10], r["profit_factor"][:6],
               r["closed_trades"], r.get("ladder_descents"), r.get("lockout_arms"),
               r.get("stops_filled"), str(r.get("combined_scalar_minimum"))[:8]))
A3 = json.loads((ROOT/"reports/stage3_g2_attempt3/STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json").read_text(encoding="utf-8"))
R3 = "SE100-G2-S3-C3-ROTATION-RA3-L03-K2-QUARTERLY"
out("")
out("A3 representative %s:" % R3)
for r in A3["runs"]:
    if r["variant_id"] == R3:
        out("  %-9s ret=%s mdd=%s pf=%s trd=%s lad=%s lck=%s stp=%s scalar_min=%s scalar_mean=%s below1=%s"
            % (r["scenario"], r["total_return"][:13], r["max_drawdown"][:10], r["profit_factor"][:6],
               r["closed_trades"], r.get("ladder_descents"), r.get("lockout_arms"),
               r.get("stops_filled"), str(r.get("combined_scalar_minimum"))[:8],
               str(r.get("combined_scalar_mean"))[:8], r.get("combined_scalar_sessions_below_one")))
out("")
out("A3 combined-scalar minima across 36 runs: min=%s max=%s" % (
    min(str(r.get("combined_scalar_minimum")) for r in A3["runs"]),
    max(str(r.get("combined_scalar_minimum")) for r in A3["runs"])))
