import json, pathlib, sys
ROOT = pathlib.Path(r"D:\Product\stock-trade-alpaca\stockedge100")
def out(t): sys.stdout.write(str(t).encode("ascii","backslashreplace").decode("ascii")+"\n")
A1 = json.loads((ROOT/"reports/stage3_g2/STAGE_3_G2_DEVELOPMENT_ADMISSIBILITY.json").read_text(encoding="utf-8"))
A2 = json.loads((ROOT/"reports/stage3_g2_attempt2/STAGE_3_G2_A2_DEVELOPMENT_ADMISSIBILITY.json").read_text(encoding="utf-8"))
for tag, D in (("A1", A1), ("A2", A2)):
    out("=== %s runs summary" % tag)
    runs = D.get("runs") or []
    sd = sum(r.get("research_shutdown_events", 0) for r in runs)
    vids = {r["variant_id"] for r in runs}
    shut = {r["variant_id"] for r in runs if r.get("research_shutdown_events", 0)}
    out("  runs=%d variants=%d shutdown_events_total=%d variants_with_a_shutdown=%d"
        % (len(runs), len(vids), sd, len(shut)))
    sess = sorted({r.get("shutdown_session") for r in runs if r.get("shutdown_session")})
    if sess: out("  shutdown sessions span %s .. %s (n=%d distinct)" % (sess[0], sess[-1], len(sess)))
    out("  ladder totals: descents=%s stops_filled=%s lockout_arms=%s"
        % tuple(sum(r.get(k,0) for r in runs) for k in ("ladder_descents","stops_filled","lockout_arms")))
out("")
A2D = json.loads((ROOT/"reports/stage3_g2_attempt2/STAGE_3_G2_A2_ROTATION_RESEARCH.json").read_text(encoding="utf-8"))
A1D = json.loads((ROOT/"reports/stage3_g2/STAGE_3_G2_ROTATION_RESEARCH.json").read_text(encoding="utf-8"))
for tag, D in (("A1", A1D), ("A2", A2D)):
    sv = D.get("stage_verdict", {})
    out("=== %s verdict: %s / route=%s rep=%s" % (tag, sv.get("verdict_token"), sv.get("fail_route") or sv.get("route"), sv.get("selection_note","")[:120]))
    gc = D.get("gate_conditions", {})
    ns = [c for c,r in gc.items() if c!="admissible_candidate_exists" and not r.get("satisfied")]
    out("   conditions not satisfied: %s" % ns)
    rep = (D.get("selection") or {}).get("selected_variant_id")
    out("   representative: %s" % rep)
    if rep:
        for r in (A1["runs"] if tag=="A1" else A2["runs"]):
            if r["variant_id"]==rep:
                out("     %-9s ret=%s mdd=%s pf=%s trd=%s shut=%s"
                    % (r["scenario"], r["total_return"][:12], r["max_drawdown"][:10],
                       r["profit_factor"][:6], r["closed_trades"], r.get("research_shutdown_events")))
