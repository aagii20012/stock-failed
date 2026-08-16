"""Fourth probe: does the reworked crash fixture actually stop, and does a K3 injection breach?

Every question here was already answered wrong once by guessing. ASCII output only.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "tests" / "adversarial"))

from stockedge100.backtest.g2_engine_ra1 import load_risk_architecture  # noqa: E402
from stockedge100.strategies import g2_window_guard as guard  # noqa: E402

import test_g2_ra1_risk_architecture as T  # noqa: E402

window = guard.generation_2_window("probe", "2009-12-01", "2011-12-31")

print("== risk_state_payload() shape ==")
growth = T.build_growth_series()
e0, _, _ = T.make_engine(growth, window, T.K1)
e0.run()
payload = e0.risk_state_payload()
print("  type:", type(payload).__name__)
text = payload if isinstance(payload, str) else json.dumps(payload, default=str)
for line in text.splitlines()[:4]:
    print("   |", line)
print("   ... total lines:", len(text.splitlines()))

print()
print("== reworked crash fixture, K1 ==")
crash = T.build_crash_series()
e1, _, _ = T.make_engine(crash, window, T.K1)
r1 = e1.run()
print("  fills:", len(r1.fills), " shutdown:", r1.shutdown_session)
print("  stop_events:", len(e1.stop_events))
print("  preempted_signal_exit:", e1.stop_preempted_signal_exit)
print("  ladder descents/ascents:", e1.ladder_descents, e1.ladder_ascents,
      " deepest:", e1.deepest_band)
for event in e1.stop_events[:3]:
    print("   event:", json.dumps(event, default=str))
print("  symbols traded:", sorted({f.fill.symbol for f in r1.fills}))

print()
print("== crash fixture K2/K3 for good measure ==")
for vid, name in ((T.K2, "K2"), (T.K3, "K3")):
    e, _, _ = T.make_engine(crash, window, vid)
    r = e.run()
    print("  %s fills=%d stops=%d shutdown=%s deepest_band=%d" % (
        name, len(r.fills), len(e.stop_events), r.shutdown_session, e.deepest_band))

print()
print("== AT-A injection candidates: K3, loosened ceiling, various budget weights ==")
arch = load_risk_architecture()
loose = dataclasses.replace(arch, exposure_ceiling=Decimal("0.95"))
for vid, name in ((T.K3, "K3"), (T.K2, "K2")):
    for weight in ("0.30", "0.31", "0.45"):
        e, _, _ = T.make_engine(growth, window, vid, risk=loose)
        e.budget_weight = Decimal(weight)
        r = e.run()
        recs = T.exposure_report(r, growth)
        peak = max(x["fraction"] for x in recs)
        breaches = sum(1 for x in recs
                       if x["gross_after"] > Decimal("0.50") * x["equity_before"])
        print("  %s w=%s peak=%.6f breaches=%d clamps=%s" % (
            name, weight, peak, breaches, dict(e.binding_clamp_counts)))

print()
print("== control: same weights at the SEALED 0.50 ceiling must not breach ==")
for vid, name in ((T.K3, "K3"), (T.K2, "K2")):
    e, _, _ = T.make_engine(growth, window, vid)
    e.budget_weight = Decimal("0.30")
    r = e.run()
    recs = T.exposure_report(r, growth)
    buys = [x for x in recs if x["side"] == "BUY"]
    over = sum(1 for x in recs if x["gross_after"] > Decimal("0.50") * x["equity_before"])
    print("  %s w=0.30 peak=%.6f over_nominal=%d clamps=%s" % (
        name, max(x["fraction"] for x in recs), over, dict(e.binding_clamp_counts)))
    if over:
        worst = max((x["gross_after"] - Decimal("0.50") * x["equity_before"]) for x in recs)
        print("      worst excess usd:", worst, " min_order_notional:",
              e.costs.min_order_notional)

print()
print("== AT-F: is a PERSISTENT bump enough to move the digests? ==")
bumped = T.build_growth_series(bump=("AAA", __import__("datetime").date(2010, 6, 15), 40))
eb, cb, _ = T.make_engine(bumped, window, T.K1)
rb = eb.run()
ea, ca, _ = T.make_engine(growth, window, T.K1)
ra = ea.run()
print("  base  trades:", ra.trades_digest()[:16], " equity:", ra.equity_digest()[:16])
print("  bumped trades:", rb.trades_digest()[:16], " equity:", rb.equity_digest()[:16])
print("  differ:", ra.trades_digest() != rb.trades_digest(),
      ra.equity_digest() != rb.equity_digest())
