"""Re-verify every figure the README's new limitation bullets assert. ASCII output only.

Each check either resolves to a value on disk or fails loudly. Nothing here is typed from memory:
the expected values are the ones now in README.md, and the script's job is to disagree with them.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "stockedge100"
ev = json.loads((ROOT / "reports/stage3_g2_attempt2/STAGE_3_G2_A2_DEVELOPMENT_ADMISSIBILITY.json")
                .read_text(encoding="utf-8"))
crit = json.loads((ROOT / "config/generation_2/g2_gate_criteria.json").read_text(encoding="utf-8"))
readme = (ROOT / "README.md").read_text(encoding="utf-8")
report = (ROOT / "governance/generation_2/STAGE_3_G2_ROTATION_RA1_RESEARCH_REPORT.md").read_text(
    encoding="utf-8")

fails = []


def claim(label, ok, detail):
    print("%-4s %-46s %s" % ("OK" if ok else "FAIL", label, detail))
    if not ok:
        fails.append(label)


vt = ev["variant_table"]
sel = ev["selection"]
rep_id = sel["representative_variant_id"]
rep = [r for r in vt if r["variant_id"] == rep_id][0]
cand = ev["candidate_results"][0]

# --- shutdown contrast --------------------------------------------------------------------------
a2_events = sum(r["research_shutdown_events"] for r in vt)
runs = ev["grid"]["runs_executed"]
claim("0 shutdown events across 36 runs", (a2_events, runs) == (0, 36),
      "events=%d runs=%d" % (a2_events, runs))

# --- the representative -------------------------------------------------------------------------
fills = rep["fill_count_both_runs"] if "fill_count_both_runs" in rep else rep["base_fills"]
all_fills = sorted(r.get("fill_count_both_runs", r.get("base_fills")) for r in vt)
claim("189 fills, unique minimum",
      fills == 189 and all_fills.count(189) == 1 and min(all_fills) == 189,
      "fills=%s min=%s count_at_min=%d" % (fills, all_fills[0], all_fills.count(all_fills[0])))

trade_keys = [k for k in rep if "trade" in k]
print("     rep trade-ish keys: %s" % trade_keys)
trades = rep.get("base_closed_trades", rep.get("base_trade_count"))
claim("representative closes 36 trades", trades == 36, "trades=%s" % trades)

ret = float(rep["base_total_return"])
claim("representative base return +0.42%", abs(ret - 0.0042) < 5e-5, "return=%.6f" % ret)

# --- the three failed conditions ------------------------------------------------------------------
not_met = cand["conditions_not_met"]
names = {}
for c in crit["conditions"] if isinstance(crit.get("conditions"), list) else []:
    names[c.get("id")] = c.get("name") or c.get("metric") or c.get("statement", "")[:70]
claim("three base conditions not met", len(not_met) == 3, "%s" % not_met)
for cid in not_met:
    print("       %-8s %s" % (cid, str(names.get(cid, "(name not in criteria list)"))[:88]))

# --- figures quoted from the report ---------------------------------------------------------------
for needle in ("**+63.15%**", "0.1116", "1.9341", "105 closed trades", "0.5043", "0.5184",
               "`G2A2-CONFLICT-27`", "`SC-4`"):
    claim("report carries %s" % needle, needle.replace("**", "") in report.replace("**", ""),
          "quoted in section 17")

# --- the README does not contradict itself --------------------------------------------------------
claim("README states nine limitation sets", "Nine sets now" in readme, "counted paragraph")
claim("README no longer says eight", "Eight sets now" not in readme, "stale count removed")
claim("README links the attempt 2 report", "STAGE_3_G2_ROTATION_RA1_RESEARCH_REPORT.md" in readme,
      "link present")
claim("README carries no 64-hex tree digest",
      not re.search(r"\b[0-9a-f]{64}\b", readme), "no bare digest in a repo_state_id pattern file")

print()
print("FAILED CHECKS: %s" % (", ".join(fails) if fails else "none"))
