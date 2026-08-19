"""Nineteenth pass, narrow: the variant_table row keys the package's evidence bullets read."""

import json
import pathlib
from decimal import Decimal

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


EV = json.loads(
    (ROOT / "reports/stage3_g2_attempt3/STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json")
    .read_text(encoding="utf-8")
)

rows = EV["variant_table"]
print("variant_table len = %d  type=%s" % (len(rows), type(rows).__name__))
row = rows[0]
print("row keys (%d):" % len(row))
for k in sorted(row):
    v = row[k]
    shown = safe(json.dumps(v, default=str))
    if len(shown) > 70:
        shown = shown[:70] + "..."
    print("   %-52s %-6s %s" % (k, type(v).__name__, shown))

print("-" * 100)
for k in ("base_total_return", "base_max_drawdown", "base_profit_factor",
          "base_closed_episodes", "base_best_trade_removed_return",
          "stress_total_return", "stress_max_drawdown",
          "base_combined_scalar_minimum", "base_research_shutdown_events",
          "research_shutdown_events"):
    print("%-38s %s" % (k, safe(json.dumps(row.get(k, "<absent>"), default=str))[:120]))

print("-" * 100)
for field in ("base_total_return", "stress_total_return", "base_max_drawdown",
              "stress_max_drawdown", "base_profit_factor"):
    if field not in row:
        print("%-24s ABSENT" % field)
        continue
    vals = [Decimal(str(r[field])) for r in rows]
    print("%-24s min=%s max=%s  positive=%d/%d"
          % (field, min(vals), max(vals), sum(1 for v in vals if v > 0), len(vals)))

print("-" * 100)
print("shutdown sum = %s"
      % sum(int(r["research_shutdown_events"]) for r in rows if "research_shutdown_events" in r))
print("-" * 100)
sel = EV["selection"]
print("EV.selection.result keys: %s" % safe(sorted(sel["result"])))
print(safe(json.dumps({k: v for k, v in sel["result"].items()
                       if k not in ("scores", "ranking")}, indent=1, default=str))[:1500])
print("-" * 100)
print("EV.grid keys: %s" % safe(sorted(EV["grid"])))
print("EV.runs type=%s len=%s" % (type(EV["runs"]).__name__, len(EV["runs"])))
print("EV.prior_attempt_module_verification keys: %s"
      % safe(sorted(EV["prior_attempt_module_verification"])))
print("EV.window keys: %s" % safe(sorted(EV["window"])))
print("EV.universe keys: %s" % safe(sorted(EV["universe"])))
print("EV.run_span_recheck keys: %s" % safe(sorted(EV["run_span_recheck"])))
print("EV.sealed_inputs keys: %s" % safe(sorted(EV["sealed_inputs"])))
print("EV.explicit_non_authorizations type=%s"
      % type(EV["explicit_non_authorizations"]).__name__)
print("EV.mechanics_carried_unchanged type=%s"
      % type(EV["mechanics_carried_unchanged"]).__name__)
print("EV.conflicts_declared_in_the_gate_criteria type=%s len=%s"
      % (type(EV["conflicts_declared_in_the_gate_criteria"]).__name__,
         len(EV["conflicts_declared_in_the_gate_criteria"])))
print("EV.representative_selection_rule type=%s"
      % type(EV["representative_selection_rule"]).__name__)
print("EV.gate keys/val: %s" % safe(json.dumps(EV["gate"], default=str))[:300])
print("EV.stage: %s" % safe(json.dumps(EV["stage"], default=str))[:200])
print("EV.command: %s" % safe(json.dumps(EV["command"], default=str))[:300])
print("EV.live_trading_authorized: %s" % safe(json.dumps(EV["live_trading_authorized"])))
