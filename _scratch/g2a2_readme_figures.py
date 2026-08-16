"""Extract every figure the README's Attempt 2 paragraphs will quote. ASCII output only."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "stockedge100"
ev = json.loads((ROOT / "reports/stage3_g2_attempt2/STAGE_3_G2_A2_DEVELOPMENT_ADMISSIBILITY.json")
                .read_text(encoding="utf-8"))
a1 = json.loads((ROOT / "reports/stage3_g2/STAGE_3_G2_DEVELOPMENT_ADMISSIBILITY.json")
                .read_text(encoding="utf-8"))

vt = ev["variant_table"]
sv = ev["stage_verdict"]
print("verdict token        : %s - %s" % (sv["verdict"], sv["verdict_token"]))
print("route                :", sv["route"])
print("variants / runs      :", len(vt), ev["grid"]["runs_executed"])
print("A2 shutdown events   :", sum(r["research_shutdown_events"] for r in vt))
print("A1 shutdown runs     :", sum(1 for r in a1["variant_table"]
                                    for k in ("base_shutdown_session", "stress_shutdown_session")
                                    if r[k]))

sel = ev["selection"]
print("representative       :", sel["representative_variant_id"])
print("selection step       :", sel["decided_at_step"])
print("decided by           :", str(sel["decided_by"])[:160])
print("step_1               :", str(sel["step_1"])[:160])
print("step_2               :", str(sel["step_2"])[:200])

rep = ev["candidate_results"][0]
print("candidates evaluated :", len(ev["candidate_results"]))
print("admitted             :", rep["admitted"])
print("conditions_not_met   :", rep["conditions_not_met"])
print("stress not met       :", rep["stress_evaluation"].get("conditions_not_met"))

base_dd = [float(r["base_max_drawdown"]) for r in vt]
a1_dd = [float(r["base_max_drawdown"]) for r in a1["variant_table"]]
print("A2 base drawdown     : %.4f - %.4f" % (min(base_dd), max(base_dd)))
print("A1 base drawdown     : %.4f - %.4f" % (min(a1_dd), max(a1_dd)))

best = max(vt, key=lambda r: float(r["base_total_return"]))
print("best by base return  : %s %+.2f%%" % (best["variant_id"], 100 * float(best["base_total_return"])))
rep_row = [r for r in vt if r["variant_id"] == sel["representative_variant_id"]][0]
print("rep fills base/stress:", rep_row["base_fill_count"], rep_row["stress_fill_count"])
print("rep base return      : %+.2f%%" % (100 * float(rep_row["base_total_return"])))
print("rep base drawdown    : %.4f" % float(rep_row["base_max_drawdown"]))
print("rep row keys         :", [k for k in rep_row if "fill" in k or "trade" in k])
