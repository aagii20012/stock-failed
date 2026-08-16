"""Quantify the RA2-1 part_c excess before it becomes an unexplained number in a decision package.

part_b says appreciation drift between the open (where the ceiling is enforced) and the close (where
it is measured) is inevitable and is the reason the continuous throttle exists. part_c says an
observed maximum above 0.50 "by more than the declared minimum-notional slack is a defect, not a
result". The smoke run recorded 0.5155 on 2020-11-09. This measures which of the two readings the
number actually is.

ASCII output only.
"""

from __future__ import annotations

import datetime as dt
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.backtest.g2_costs import rotation_cost_model  # noqa: E402
from stockedge100.strategies import g2_runner_ra1 as R  # noqa: E402
from stockedge100.strategies.g2_rotation_ra1 import rotation_variants  # noqa: E402

variant = rotation_variants()[0]
series = R.load_grid_dataset()
run = R.run_grid(series, variants=(variant,), labels=("#BASE",), verify=False)[0]

risk = run.risk
observed = Decimal(risk["max_gross_fraction_observed"])
session = dt.date.fromisoformat(risk["max_gross_fraction_session"])
costs = rotation_cost_model(variant.top_k, "BASE")

print("variant                     %s" % variant.variant_id)
print("max_gross_fraction_observed %s" % observed)
print("on session                  %s" % session)
print("nominal ceiling             0.50")
print("excess fraction             %s" % (observed - Decimal("0.50")))

curve = {p.session: p for p in run.result.equity_curve}
point = curve[session]
equity = point.equity
excess_usd = (observed - Decimal("0.50")) * equity
print()
print("equity at that close        %s" % equity)
print("gross at that close         %s" % (observed * equity))
print("excess in dollars           %s" % excess_usd)

min_notional = getattr(costs, "min_order_notional", None)
print("min_order_notional          %s" % min_notional)
if min_notional is not None:
    print("excess / min_order_notional %s" % (excess_usd / min_notional))
    print("within one minimum lot?     %s" % (excess_usd <= min_notional))

print()
print("positions open at that close %s" % point.position_count)
print("top_k for this variant       %s" % variant.top_k)

# The hard assertion is priced at the open and did not raise, or the run would not exist.
print()
print("post-fill ceiling assertion  held on every fill (the run completed; it raises otherwise)")

print()
print("throttle activity")
for key, value in sorted(risk["throttle"].items()):
    print("  %-34s %s" % (key, value))

print()
print("sessions breaching the ceiling at the close: %s of %s (%.1f%%)" % (
    risk["throttle"]["sessions_breaching_ceiling"],
    risk["risk_state_sessions"],
    100.0 * risk["throttle"]["sessions_breaching_ceiling"] / risk["risk_state_sessions"],
))

# How large was the largest single-session appreciation of the book? If the observed excess is of
# the same order, drift explains it; if it is far larger, the throttle failed to act.
closes = []
prev = None
for p in run.result.equity_curve:
    if prev is not None and prev.equity > 0:
        closes.append(((p.equity - prev.equity) / prev.equity, p.session))
    prev = p
closes.sort(reverse=True)
print()
print("largest one-session equity moves (the drift channel):")
for move, day in closes[:5]:
    print("  %s  %s" % (day, move))
