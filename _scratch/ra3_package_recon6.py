"""Sixth pass: the eighteen-row descriptive table, printed from the measured flat column names.

variant_table rows are FLAT with base_/stress_ prefixes; there is no `per_run` sub-dict. This
prints the columns the end-of-session report has to carry, for both runs, so the table is
transcribed from a measurement rather than assembled from memory.
"""

import json
import pathlib
import re

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")

EV = json.loads((ROOT / "reports/stage3_g2_attempt3/"
                 "STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json").read_text(encoding="utf-8"))


def pct(value, places=2):
    if value is None:
        return "-"
    if isinstance(value, dict):
        # best_trade_removed_return is a condition row, not a scalar: it carries
        # "min(a, b)" in `measured`. Take the first number, which is the min.
        value = re.search(r"[-+]?\d*\.?\d+", value["measured"]).group(0)
    return "%+.*f%%" % (places, float(value) * 100.0)


def num(value, places=3):
    if value is None:
        return "-"
    return "%.*f" % (places, float(value))


HDR = ("%-17s %-6s %9s %8s %7s %6s %9s %5s %6s %6s %6s %6s %6s %6s %6s %7s %7s"
       % ("variant", "run", "return", "maxDD", "PF", "closed", "btr", "shut",
          "fills", "desc", "asc", "lockArm", "blkd", "stopT", "stopF", "scalMin", "maxGross"))
print(HDR)
print("-" * len(HDR))
for row in EV["variant_table"]:
    vid = row["variant_id"].replace("SE100-G2-S3-C3-ROTATION-RA3-", "")
    for label, prefix in (("#BASE", "base_"), ("#STRESS", "stress_")):
        print("%-17s %-6s %9s %8s %7s %6s %9s %5s %6s %6s %6s %6s %6s %6s %6s %7s %7s"
              % (vid if label == "#BASE" else "",
                 label,
                 pct(row[prefix + "total_return"]),
                 pct(row[prefix + "max_drawdown"]),
                 num(row[prefix + "profit_factor"]),
                 row[prefix + "closed_episodes"],
                 pct(row[prefix + "best_trade_removed_return"]),
                 row[prefix + "research_shutdown_events"],
                 row[prefix + "fills"],
                 row[prefix + "ladder_descents"],
                 row[prefix + "ladder_ascents"],
                 row[prefix + "lockout_arms"],
                 row[prefix + "lockout_recoveries_blocked"],
                 row[prefix + "stops_triggered"],
                 row[prefix + "stops_filled"],
                 num(row[prefix + "combined_scalar_minimum"]),
                 num(row[prefix + "max_gross_fraction_observed"])))

print()
print("SELECTION-INPUT columns (both-runs sums) and the SEL-2 score:")
print("%-17s %6s %8s %8s %8s %8s %14s"
      % ("variant", "shut", "fills", "desc", "lockArm", "stopF", "instability"))
for row in EV["variant_table"]:
    print("%-17s %6s %8s %8s %8s %8s %14s"
          % (row["variant_id"].replace("SE100-G2-S3-C3-ROTATION-RA3-", ""),
             row["research_shutdown_events"], row["fill_count_both_runs"],
             row["ladder_descents_both_runs"], row["lockout_arms_both_runs"],
             row["stops_filled_both_runs"], row["selection_score"]["instability_score"]))

print()
print("scalar min/mean across all 36 runs:")
mins = sorted(float(r["combined_scalar_minimum"]) for r in EV["runs"])
means = sorted(float(r["combined_scalar_mean"]) for r in EV["runs"])
below = sum(int(r["combined_scalar_sessions_below_one"]) for r in EV["runs"])
print("   combined_scalar_minimum  lowest=%s highest=%s" % (mins[0], mins[-1]))
print("   combined_scalar_mean     lowest=%s highest=%s" % (means[0], means[-1]))
print("   sessions_below_one total across 36 runs = %d" % below)
