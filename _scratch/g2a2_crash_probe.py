"""Fifth probe: find a crash date that actually trips the 8% stop, and one that collides with a
scheduled rebalance so the STOP-over-EXIT precedence is exercised. ASCII output only.

The stop reference is cost_basis/quantity, so what matters is (gain since entry) - (crash), not the
crash alone. The previous fixture let AAA drift +15% before crashing 15%.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "tests" / "adversarial"))

from stockedge100.data.calendar import sessions_between  # noqa: E402
from stockedge100.strategies import g2_window_guard as guard  # noqa: E402

import test_g2_ra1_risk_architecture as T  # noqa: E402

window = guard.generation_2_window("probe", "2009-12-01", "2011-12-31")

print("== when does K1 actually trade on the growth fixture? ==")
growth = T.build_growth_series()
e0, _, _ = T.make_engine(growth, window, T.K1)
r0 = e0.run()
for rec in r0.fills[:8]:
    print("   %s %-4s %s qty=%s" % (rec.session, rec.fill.side, rec.fill.symbol,
                                    rec.fill.quantity))

print()
print("== parametric crash sweep ==")


def build(crash_session, *, base="200", drifts=None):
    drifts = drifts or T.CRASH_DRIFTS
    sessions = sessions_between(T.FIRST, T.LAST)
    from stockedge100.backtest.dataset import series_from_rows
    out = {}
    for symbol in T.SYMBOLS:
        close = Decimal(base)
        drift = Decimal(drifts[symbol])
        closes = []
        crashed = False
        for day in sessions:
            if symbol == "AAA" and day == crash_session:
                close = (close * (Decimal(1) - T.CRASH_FRACTION)).quantize(Decimal("0.01"))
                crashed = True
            elif symbol == "AAA" and crashed:
                pass
            else:
                close += drift
            closes.append(close)
        out[symbol] = series_from_rows(symbol, T._rows(sessions, closes))
    return out


for crash in (dt.date(2010, 5, 14), dt.date(2010, 6, 15), dt.date(2010, 7, 15),
              dt.date(2010, 9, 15), dt.date(2011, 3, 15)):
    series = build(crash)
    e, _, _ = T.make_engine(series, window, T.K1)
    r = e.run()
    print("  crash=%s fills=%2d stops=%d preempt=%d shutdown=%s deepest=%d held_at_crash=%s" % (
        crash, len(r.fills), len(e.stop_events), e.stop_preempted_signal_exit,
        r.shutdown_session, e.deepest_band,
        sorted({f.fill.symbol for f in r.fills if f.session <= crash})))
    for ev in e.stop_events[:2]:
        print("       ", json.dumps(ev, default=str))

print()
print("== which sessions are monthly rebalance DECISION closes? (from fill sessions - 1) ==")
series = build(dt.date(2010, 6, 15))
e, _, _ = T.make_engine(series, window, T.K1)
r = e.run()
fill_sessions = sorted({rec.session for rec in r.fills})
allsess = sessions_between(T.FIRST, T.LAST)
idx = {s: i for i, s in enumerate(allsess)}
decisions = [allsess[idx[s] - 1] for s in fill_sessions if idx[s] > 0]
print("  first 10 decision closes:", [str(d) for d in decisions[:10]])

print()
print("== crash landing exactly on a decision close (STOP vs EXIT precedence) ==")
for d in decisions[1:8]:
    series = build(d)
    e2, _, _ = T.make_engine(series, window, T.K1)
    r2 = e2.run()
    print("  decision=%s fills=%2d stops=%d preempt=%d suppressed=%d" % (
        d, len(r2.fills), len(e2.stop_events), e2.stop_preempted_signal_exit,
        len(e2.suppressed_legs)))
