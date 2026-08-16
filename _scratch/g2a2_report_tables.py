"""Emit the Markdown tables for the Attempt 2 research report, from the grid outputs on disk.

Nothing here is hand-typed: every figure is read from reports/stage3_g2_attempt2/*.json and
formatted. ASCII output only apart from the minus sign, which is written as '-'.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
OUT = ROOT / "reports" / "stage3_g2_attempt2"

rows = json.loads((OUT / "grid_results.json").read_text(encoding="utf-8"))
selection = json.loads((OUT / "selection_record.json").read_text(encoding="utf-8"))
gate = json.loads((OUT / "gate_record.json").read_text(encoding="utf-8"))
verdict = json.loads((OUT / "stage_verdict.json").read_text(encoding="utf-8"))

PREFIX = "SE100-G2-S3-C2-ROTATION-RA1-"


def short(variant_id: str) -> str:
    return variant_id[len(PREFIX):]


def num(value, places: int = 4, sign: bool = False) -> str:
    d = Decimal(str(value)).quantize(Decimal(1).scaleb(-places))
    text = format(d, "f")
    if sign and not text.startswith("-"):
        text = "+" + text
    return text


base = [r for r in rows if r["label"] == "#BASE"]
stress = [r for r in rows if r["label"] == "#STRESS"]
base.sort(key=lambda r: r["grid_index"])
stress.sort(key=lambda r: r["grid_index"])

print("### `#BASE` runs")
print()
print("| # | Variant | Return | Max DD | Profit factor | Closed trades | Closed episodes | "
      "Distinct symbols | Shutdowns |")
print("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
for r in base:
    print("| %d | `%s` | %s | %s | %s | %d | %d | %d | %d |" % (
        r["grid_index"], short(r["variant_id"]), num(r["total_return"], 4, sign=True),
        num(r["max_drawdown"]), num(r["profit_factor"]), r["closed_trades"],
        r["closed_episodes"], r["distinct_symbols_traded"], r["research_shutdown_events"]))

print()
print("### `#STRESS` runs (2x frictions)")
print()
print("| # | Variant | Return | Max DD | Profit factor | Closed trades | Closed episodes | "
      "Fills | Shutdowns |")
print("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
for r in stress:
    print("| %d | `%s` | %s | %s | %s | %d | %d | %d | %d |" % (
        r["grid_index"], short(r["variant_id"]), num(r["total_return"], 4, sign=True),
        num(r["max_drawdown"]), num(r["profit_factor"]), r["closed_trades"],
        r["closed_episodes"], r["fills"], r["research_shutdown_events"]))

print()
print("### Risk-architecture activity, `#BASE` runs")
print()
print("| # | Variant | Ladder descents | Ladder ascents | Deepest band | Lockout arms | "
      "Recoveries blocked | Stops triggered | Stops filled | Stops pre-empted |")
print("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
for r in base:
    print("| %d | `%s` | %d | %d | %s | %d | %d | %d | %d | %d |" % (
        r["grid_index"], short(r["variant_id"]), r["ladder_descents"], r["ladder_ascents"],
        num(r["ladder_deepest_band"], 2), r["lockout_arms"], r["lockout_recoveries_blocked"],
        r["stops_triggered"], r["stops_filled"], r["stops_preempted_by_signal_exit"]))

print()
print("### Risk-architecture activity, `#STRESS` runs")
print()
print("| # | Variant | Ladder descents | Ladder ascents | Deepest band | Lockout arms | "
      "Recoveries blocked | Stops triggered | Stops filled | Stops pre-empted |")
print("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
for r in stress:
    print("| %d | `%s` | %d | %d | %s | %d | %d | %d | %d | %d |" % (
        r["grid_index"], short(r["variant_id"]), r["ladder_descents"], r["ladder_ascents"],
        num(r["ladder_deepest_band"], 2), r["lockout_arms"], r["lockout_recoveries_blocked"],
        r["stops_triggered"], r["stops_filled"], r["stops_preempted_by_signal_exit"]))

print()
print("### Exposure throttle and combined scalar, `#BASE` runs")
print()
print("| # | Variant | Throttle legs | Legs below min notional | Sessions breaching ceiling | "
      "Max gross fraction | On session | Combined scalar min | Combined scalar mean | "
      "Sessions scalar < 1 |")
print("| --- | --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |")
for r in base:
    print("| %d | `%s` | %d | %d | %d | %s | %s | %s | %s | %d |" % (
        r["grid_index"], short(r["variant_id"]), r["throttle_legs_scheduled"],
        r["throttle_legs_below_min_notional"], r["throttle_sessions_breaching_ceiling"],
        num(r["max_gross_fraction_observed"]), r["max_gross_fraction_session"],
        num(r["combined_scalar_minimum"]), num(r["combined_scalar_mean"]),
        r["combined_scalar_sessions_below_one"]))

print()
print("### Turnover (fills summed across both declared runs)")
print()
by_variant: dict[str, int] = {}
for r in rows:
    by_variant[short(r["variant_id"])] = by_variant.get(short(r["variant_id"]), 0) + r["fills"]
print("| Variant | Fills (both runs) |")
print("|---|---:|")
for name, fills in sorted(by_variant.items(), key=lambda kv: (kv[1], kv[0])):
    print("| `%s` | %d |" % (name, fills))

print()
print("### Gate 3 conditions on the representative")
print()
print("representative:", selection["representative_variant_id"])
print("decided_at_step:", selection["decided_at_step"])
print()
print("| Condition | Required (verbatim) | `#BASE` verdict | measured | threshold | "
      "`#STRESS` verdict | measured |")
print("|---|---|---|---|---|---|---|")
stress_by_id = {c["id"]: c for c in gate["stress_evaluation"]["conditions"]}
for c in gate["base_evaluation"]["conditions"]:
    s = stress_by_id[c["id"]]
    print("| `%s` | %s | `%s` | %s | %s | `%s` | %s |" % (
        c["id"], c["required_verbatim"], c["verdict"], c["measured"], c["threshold"],
        s["verdict"], s["measured"]))

print()
print("=== verdict block ===")
print(json.dumps(verdict, indent=2)[:2000])

print()
print("=== combined admission basis ===")
basis = gate["combined"]["admission_basis"]
for key in ("conflict_ref", "resolution", "evaluated_on", "both_gate",
            "base_all_seven_satisfied", "stress_first_six_satisfied",
            "base_conditions_not_satisfied", "stress_conditions_not_satisfied",
            "permissive_base_only_reading_would_give"):
    print("  %-42s %s" % (key, basis[key]))

print()
print("=== selection note / return-blind enforcement ===")
for key in ("variants_considered", "representative_exists", "representative_variant_id",
            "decided_at_step", "selection_note"):
    print("  %-30s %s" % (key, selection[key]))
for key in sorted(selection):
    if key.startswith("step_"):
        print("  %-30s %s" % (key, json.dumps(selection[key])[:400]))
print("  other keys:", [k for k in selection if not k.startswith("step_")])
