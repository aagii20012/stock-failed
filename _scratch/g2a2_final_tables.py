"""Emit the section 6 tables for the end-of-session report. Read-only. ASCII output only."""
import json
import pathlib

ROOT = pathlib.Path(r"D:\Product\stock-trade-alpaca\stockedge100")
A2 = json.loads((ROOT / "reports/stage3_g2_attempt2/STAGE_3_G2_A2_ROTATION_RESEARCH.json")
                .read_text(encoding="utf-8"))
A1 = json.loads((ROOT / "reports/stage3_g2/STAGE_3_G2_ROTATION_RESEARCH.json")
                .read_text(encoding="utf-8"))


def out(t):
    print(str(t).encode("ascii", "backslashreplace").decode("ascii"))


table = A2["grid_results_descriptive_only"]["table"]
rep = A2["selection"]["representative_variant_id"]


def pct(x):
    return "%+.2f%%" % (float(x) * 100)


out("| # | variant | ret(B) | ret(S) | DD(B) | DD(S) | PF(B) | PF(S) | trades(B) | trades(S) "
    "| fills | shut | ladder | lockout | stops |")
out("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for r in sorted(table, key=lambda r: r["grid_index"]):
    short = r["variant_id"].replace("SE100-G2-S3-C2-ROTATION-RA1-", "")
    mark = " **" if r["variant_id"] == rep else ""
    out("| %d | `%s`%s | %s | %s | %s | %s | %.3f | %.3f | %d | %d | %d | %d | %d | %d | %d |" % (
        r["grid_index"], short, mark,
        pct(r["base_total_return"]), pct(r["stress_total_return"]),
        pct(-abs(float(r["base_max_drawdown"]))), pct(-abs(float(r["stress_max_drawdown"]))),
        float(r["base_profit_factor"]), float(r["stress_profit_factor"]),
        r["base_closed_trades"], r["stress_closed_trades"],
        r["fill_count_both_runs"], r["research_shutdown_events"],
        r["ladder_descents_both_runs"], r["lockout_arms_both_runs"],
        r["stops_filled_both_runs"]))

out("")
out("shutdown sessions, attempt 2: %s"
    % sorted(set(str(r[k]) for r in table for k in ("base_shutdown_session", "stress_shutdown_session"))))
out("ladder descents  total %d  min %d  max %d"
    % (sum(r["ladder_descents_both_runs"] for r in table),
       min(r["ladder_descents_both_runs"] for r in table),
       max(r["ladder_descents_both_runs"] for r in table)))
out("lockout arms     total %d  min %d  max %d"
    % (sum(r["lockout_arms_both_runs"] for r in table),
       min(r["lockout_arms_both_runs"] for r in table),
       max(r["lockout_arms_both_runs"] for r in table)))
out("stops filled     total %d  min %d  max %d"
    % (sum(r["stops_filled_both_runs"] for r in table),
       min(r["stops_filled_both_runs"] for r in table),
       max(r["stops_filled_both_runs"] for r in table)))
out("recoveries blocked by lockout: total %d"
    % sum(r["base_lockout_recoveries_blocked"] + r["stress_lockout_recoveries_blocked"]
          for r in table))
out("throttle sessions breaching ceiling: total %d"
    % sum(r["base_throttle_sessions_breaching_ceiling"]
          + r["stress_throttle_sessions_breaching_ceiling"] for r in table))
out("max gross fraction observed, worst over all runs: %.6f"
    % max(max(float(r["base_max_gross_fraction_observed"]),
              float(r["stress_max_gross_fraction_observed"])) for r in table))

out("")
out("=== ATTEMPT 1 shutdown comparison ===")
a1t = A1["grid_results_descriptive_only"]["table"]
out("attempt 1 rows: %d" % len(a1t))
keys = [k for k in a1t[0] if "shutdown" in k]
out("attempt 1 shutdown keys: %s" % keys)
dates = []
for r in a1t:
    for k in keys:
        if isinstance(r[k], str) and r[k][:2] == "20":
            dates.append(r[k])
out("attempt 1 shutdown sessions recorded: %d" % len(dates))
if dates:
    out("earliest %s   latest %s   distinct %d" % (min(dates), max(dates), len(set(dates))))
    from collections import Counter
    for d, n in sorted(Counter(dates).items()):
        out("   %s x %d" % (d, n))
out("attempt 1 shutdown event totals: %s"
    % sorted(set(r.get("research_shutdown_events") for r in a1t)))
out("attempt 1 selection: exists=%s step=%s by=%s"
    % (A1["selection"].get("representative_exists"), A1["selection"].get("decided_at_step"),
       A1["selection"].get("decided_by")))
out("attempt 1 verdict: %s" % A1["verdict"])
