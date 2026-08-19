"""Extract the two tables the end-of-session report must carry, off disk.

Table 1: all eighteen variants with RA3's ladder / lockout / stop statistics alongside the return,
drawdown and profit-factor figures (descriptive only -- none of them informed selection).
Table 2: the winner's instability score and its four neighbours' scores, traced to SEL-2's recorded
per-quantity computation rather than asserted.

Reads only. ASCII output.
"""

import json
import pathlib
import sys
from decimal import Decimal

ROOT = pathlib.Path(r"D:\Product\stock-trade-alpaca\stockedge100")
DEC = json.loads((ROOT / "reports/stage3_g2_attempt3/STAGE_3_G2_A3_ROTATION_RESEARCH.json")
                 .read_text(encoding="utf-8"))
EVID = json.loads((ROOT / "reports/stage3_g2_attempt3/STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json")
                  .read_text(encoding="utf-8"))
SEL = DEC["selection"]
WINNER = SEL["selected_variant_id"]


def out(t):
    sys.stdout.write(str(t).encode("ascii", "backslashreplace").decode("ascii") + "\n")


def pct(s, places=2):
    return "%+*.*f%%" % (0, places, Decimal(s) * 100)


def short(vid):
    # SE100-G2-S3-C3-ROTATION-RA3-L03-K2-QUARTERLY -> L03-K2-Q
    tail = vid.split("-RA3-")[1]
    return tail.replace("-QUARTERLY", "-Q").replace("-MONTHLY", "-M")


runs = EVID["runs"]
by = {}
for r in runs:
    by.setdefault(r["variant_id"], {})[r["scenario"]] = r
assert len(by) == 18, len(by)
assert all(set(v) == {"BASE", "STRESSED"} for v in by.values())

order = sorted(by, key=lambda v: by[v]["BASE"]["grid_index"])

out("=== TABLE 1: eighteen variants, RA3 (descriptive only -- none of it informed selection)")
out("descriptive-only flag on record: %s" % EVID["variant_table_is_descriptive_only"])
out("")
hdr = ("%-11s | %8s %8s | %7s %7s | %5s %5s | %4s | %4s %4s | %4s %4s | %4s %4s | %3s"
       % ("variant", "ret B", "ret S", "mdd B", "mdd S", "pf B", "pf S", "trd",
          "lad B", "lad S", "lck B", "lck S", "stp B", "stp S", "sd"))
out(hdr)
out("-" * len(hdr))
tot = {k: 0 for k in ("ladder_descents", "lockout_arms", "stops_filled", "fills",
                      "research_shutdown_events", "lockout_recoveries_blocked")}
for vid in order:
    b, s = by[vid]["BASE"], by[vid]["STRESSED"]
    out("%-11s | %8s %8s | %7s %7s | %5.2f %5.2f | %4d | %4d %4d | %4d %4d | %4d %4d | %3d"
        % (short(vid), pct(b["total_return"]), pct(s["total_return"]),
           pct(b["max_drawdown"]).lstrip("+"), pct(s["max_drawdown"]).lstrip("+"),
           Decimal(b["profit_factor"]), Decimal(s["profit_factor"]), b["closed_trades"],
           b["ladder_descents"], s["ladder_descents"], b["lockout_arms"], s["lockout_arms"],
           b["stops_filled"], s["stops_filled"],
           b["research_shutdown_events"] + s["research_shutdown_events"]))
    for k in tot:
        tot[k] += b[k] + s[k]
out("-" * len(hdr))
out("36-run totals: %s" % json.dumps(tot, sort_keys=True))
out("winner: %s (%s)" % (WINNER, short(WINNER)))
out("")

out("=== ladder engagement vs Attempt 2 (the required difference check)")
out(json.dumps(EVID["ladder_engagement_comparison"], indent=2, sort_keys=True)[:2600])
out("")

out("=== TABLE 2: SEL-2's recorded computation for the winner and its four neighbours")
ss = SEL["selected_score"]
out("rule: %s   decided at step %s   outcome: %s"
    % (SEL["rule_id"], SEL["decided_at_step"], SEL["outcome"]))
out("scored quantities: %s" % (SEL["scored_quantities"],))
out("")
rows = [ss] + list(SEL["neighbour_scores"])
qs = list(ss["per_quantity_mean_dissimilarity"].keys())
h2 = "%-11s | %-13s | %2s | %s" % ("variant", "instability", "nb",
                                   " ".join("%-13s" % q for q in qs))
out(h2)
out("-" * len(h2))
for r in rows:
    tag = short(r["variant_id"]) + (" *" if r["variant_id"] == WINNER else "")
    out("%-11s | %-13s | %2d | %s"
        % (tag, r["instability_score"], r["neighbour_count"],
           " ".join("%-13s" % r["per_quantity_mean_dissimilarity"][q] for q in qs)))
out("-" * len(h2))
out("* the winner. Its neighbours are: %s" % [short(n) for n in ss["neighbours"]])
out("")
allsc = SEL["result"]["all_scores"]
ranked = sorted(allsc.items(), key=lambda kv: Decimal(kv[1]["instability_score"]))
out("=== all eighteen instability scores, lowest first (step-2 ranking)")
for i, (vid, e) in enumerate(ranked, 1):
    out("%2d. %-11s %-13s nb=%d%s"
        % (i, short(vid), e["instability_score"], e["neighbour_count"],
           "   <-- selected" if vid == WINNER else ""))
out("")
out("margin over runner-up: %s vs %s"
    % (ranked[0][1]["instability_score"], ranked[1][1]["instability_score"]))
out("")
out("=== the failing condition")
for cid, row in DEC["gate_conditions"].items():
    if cid == "admissible_candidate_exists":
        out("ROLLUP %s satisfied=%s verdict=%s" % (cid, row.get("satisfied"), row.get("verdict")))
        out("   %s" % json.dumps(row)[:700])
        continue
    if not row.get("satisfied"):
        out("%s NOT satisfied: %s" % (cid, json.dumps(row)[:900]))
out("")
out("=== verdict")
out("stage_verdict: %s" % DEC["stage_verdict"])
out("verdict: %s" % json.dumps(DEC["verdict"])[:600])
out("gate_passed: %s" % DEC["gate_passed"])
