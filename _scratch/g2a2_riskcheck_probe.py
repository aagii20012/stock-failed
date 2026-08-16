"""Third probe: the actual shape of risk_summary(), verify_attempt_1_modules(), and which clamp
binds on the fixture. ASCII output only."""

from __future__ import annotations

import datetime as dt
import json
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from stockedge100.backtest.g2_engine_ra1 import RotationEngineRA1  # noqa: E402
from stockedge100.strategies import g2_rotation_ra1 as rot  # noqa: E402
from stockedge100.strategies import g2_runner_ra1 as R  # noqa: E402
from stockedge100.strategies import g2_window_guard as guard  # noqa: E402

sys.path.insert(0, str(ROOT / "tests" / "adversarial"))
import test_g2_ra1_risk_architecture as T  # noqa: E402

print("== verify_attempt_1_modules() shape ==")
report = R.verify_attempt_1_modules()
print(type(report).__name__, "keys:", sorted(report)[:12])

print()
print("== risk_summary() top-level keys ==")
window = guard.generation_2_window("probe", "2009-12-01", "2011-12-31")
series = T.build_growth_series()
engine, cand, variant = T.make_engine(series, window, T.K1)
result = engine.run()
summary = engine.risk_summary()
for key in summary:
    value = summary[key]
    if isinstance(value, dict):
        print("  %-30s dict keys=%s" % (key, sorted(value)))
    elif isinstance(value, list):
        print("  %-30s list len=%d" % (key, len(value)))
    else:
        print("  %-30s %s" % (key, value))

print()
print("== clamp binding counts, K1 growth fixture ==")
print(" ", dict(engine.binding_clamp_counts))
print("  fills:", len(result.fills), " shutdown:", result.shutdown_session)

print()
print("== stop-related counters ==")
print("  stop_events:", len(engine.stop_events))
print("  suppressed_legs:", len(engine.suppressed_legs))
print("  throttle_legs_scheduled:", engine.throttle_legs_scheduled)

print()
print("== crash fixture, K1 ==")
crash = T.build_crash_series()
e2, c2, v2 = T.make_engine(crash, window, T.K1)
r2 = e2.run()
print("  fills:", len(r2.fills), " shutdown:", r2.shutdown_session)
print("  stop_events:", len(e2.stop_events))
print("  clamps:", dict(e2.binding_clamp_counts))
print("  ladder descents/ascents:", e2.ladder_descents, e2.ladder_ascents,
      " deepest:", e2.deepest_band)
if e2.stop_events:
    print("  first stop event:", json.dumps(e2.stop_events[0], default=str))
s2 = e2.risk_summary()
print("  risk_summary stop-ish keys:", [k for k in s2 if "stop" in k.lower()])

print()
print("== high budget weight forces AGGREGATE_RA2 ==")
e3, c3, v3 = T.make_engine(series, window, T.K1)
e3.budget_weight = Decimal("0.90")
r3 = e3.run()
print("  clamps:", dict(e3.binding_clamp_counts))
recs = T.exposure_report(r3, series)
peak = max(r["fraction"] for r in recs)
print("  peak post-fill fraction:", peak)

print()
print("== and with the ceiling loosened to 0.95 ==")
import dataclasses  # noqa: E402
from stockedge100.backtest.g2_engine_ra1 import load_risk_architecture  # noqa: E402
loose = dataclasses.replace(load_risk_architecture(), exposure_ceiling=Decimal("0.95"))
e4, c4, v4 = T.make_engine(series, window, T.K1, risk=loose)
e4.budget_weight = Decimal("0.90")
r4 = e4.run()
recs4 = T.exposure_report(r4, series)
print("  clamps:", dict(e4.binding_clamp_counts))
print("  peak post-fill fraction:", max(r["fraction"] for r in recs4))
print("  breaches over 0.50:", sum(
    1 for r in recs4 if r["gross_after"] > Decimal("0.50") * r["equity_before"]))
