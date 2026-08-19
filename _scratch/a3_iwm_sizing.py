"""Addendum to a3_iwm_trace.py: why two of IWM's four entries were half-notional.

Read-only. Re-runs the same sealed variant, re-verifies the same four digests, and reports the
equity / cash context at each IWM decision session plus the buy fill itself. Writes nothing.
"""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

REPO = Path(r"D:\Product\stock-trade-alpaca\stockedge100")
sys.path.insert(0, str(REPO / "src"))

from stockedge100.strategies import g2_runner_ra3 as R  # noqa: E402
from stockedge100.strategies.g2_rotation_ra3 import load_protocol, variant_by_id  # noqa: E402

VARIANT_ID = "SE100-G2-S3-C3-ROTATION-RA3-L03-K2-QUARTERLY"
LABEL = "#BASE"

SEALED = {
    "trades_digest": "90770d732cd1955234583686101f3844964eeada68ba8480db0c902f71a1dd50",
    "equity_digest": "6d184533a945a4d10a4fca54aa1e45e506fabfca2629e6da51806ff0e2d75a46",
    "ranking_digest": "2881c0f6011b5d87f30920446551fae82500207b3d0291d091271abeac79b01b",
    "risk_state_digest": "85e551b3c17fb6d25a55bb69f6669836cdc3feca64a8ff92a293960997842905",
}

# entry fill session -> the rebalance session that decided it (from the trace)
IWM_ENTRIES = {
    "2011-01-04": "2011-01-03",
    "2012-01-04": "2012-01-03",
    "2017-01-04": "2017-01-03",
    "2021-01-05": "2021-01-04",
}

protocol = load_protocol()
series = R.load_grid_dataset()

# Capture the engine instance. The class is not subclassed and no method is wrapped: the factory
# returns exactly what the sealed constructor returns, and the four digests below prove it.
CAPTURED = []
_real_engine = R.RotationEngineRA3


def capturing_engine(*a, **kw):
    engine = _real_engine(*a, **kw)
    CAPTURED.append(engine)
    return engine


R.RotationEngineRA3 = capturing_engine
try:
    run = R.run_one(variant_by_id(VARIANT_ID), LABEL, series, protocol=protocol)
finally:
    R.RotationEngineRA3 = _real_engine
assert len(CAPTURED) == 1, len(CAPTURED)
engine = CAPTURED[0]

report = R.grid_report([run], selection=None)
rows = report["rows"] if isinstance(report, dict) else report
assert len(rows) == 1, len(rows)
row = rows[0]
for key, want in SEALED.items():
    got = row[key]
    assert got == want, f"{key} moved: {got} != {want}"
print("digests re-verified (4/4) -- observation is non-perturbing")

weight = run.variant.target_weight
print(f"target_weight per position = {weight}")

by_session = {p.session.isoformat(): p for p in run.result.equity_curve}

print()
hdr = ("decision", "eq@decision", "cash@decision", "pos", "w*eq", "fill", "eq@fill", "cash@fill",
       "qty", "price", "notional")
print("  " + " ".join(f"{h:>13s}" for h in hdr))
for fill_session, decision_session in IWM_ENTRIES.items():
    d = by_session[decision_session]
    f = by_session[fill_session]
    buys = [
        fr for fr in run.result.fills
        if fr.session.isoformat() == fill_session and fr.fill.symbol == "IWM"
    ]
    assert len(buys) == 1, f"{fill_session}: {len(buys)} IWM fills"
    fill = buys[0].fill
    row_v = (
        decision_session, f"{d.equity:f}", f"{d.cash:f}", d.position_count,
        f"{(weight * d.equity):.4f}", fill_session, f"{f.equity:f}", f"{f.cash:f}",
        f"{fill.quantity:f}", f"{fill.reference_price:f}", f"{fill.gross_notional:f}",
    )
    print("  " + " ".join(f"{str(v):>13s}" for v in row_v))

print()
print("positions held into each IWM decision session (from the prior session's marks):")
for fill_session, decision_session in IWM_ENTRIES.items():
    d = by_session[decision_session]
    invested = d.equity - d.cash
    print(f"  {decision_session}: equity={d.equity:f} cash={d.cash:f} invested={invested:f} "
          f"positions={d.position_count} cash_share={(d.cash / d.equity):.4f}")

print()
print("equity at the four IWM exits:")
for exit_session in ("2011-04-04", "2012-04-03", "2017-04-04", "2021-04-05"):
    p = by_session[exit_session]
    print(f"  {exit_session}: equity={p.equity:f} cash={p.cash:f} positions={p.position_count}")

print()
print("min/max equity over the run:")
eq = [(p.equity, p.session.isoformat()) for p in run.result.equity_curve]
lo, hi = min(eq), max(eq)
print(f"  min {lo[0]:f} at {lo[1]}    max {hi[0]:f} at {hi[1]}")
print(f"  first {run.result.equity_curve[0].equity:f}  last {run.result.equity_curve[-1].equity:f}")

print()
print("== recorded risk evidence (shapes) ==")
print("  run.risk keys   :", list(run.risk))
print("  run.clamps keys :", list(run.clamps))
for k, v in run.risk.items():
    if isinstance(v, list):
        print(f"  risk[{k}] list len={len(v)} first={v[0] if v else None}")
    else:
        print(f"  risk[{k}] = {v if not isinstance(v, dict) else list(v)}")

print()
print("== sealed per-session risk state at IWM's decisions and fills ==")
trace = {}
for line in engine.risk_state_payload().splitlines():
    session, band, lockout, vol, combined = line.split("|")
    trace[session] = {"band": int(band), "lockout": int(lockout), "vol": vol, "combined": combined}
print(f"  risk trace sessions = {len(trace)} (run.risk['risk_state_sessions'] = "
      f"{run.risk['risk_state_sessions']})")
bands = engine.risk.bands
print("  sealed ladder bands:")
for b in bands:
    print("   ", b)

hwm = None
peak = {}
for p_ in run.result.equity_curve:
    hwm = p_.equity if hwm is None or p_.equity > hwm else hwm
    peak[p_.session.isoformat()] = hwm

print()
hdr2 = ("session", "role", "equity", "hwm", "dd", "band", "vol_scalar", "combined", "lockout")
print("  " + " ".join(f"{h:>12s}" for h in hdr2))
for fill_session, decision_session in IWM_ENTRIES.items():
    for session, role in ((decision_session, "decision"), (fill_session, "fill")):
        t = trace[session]
        p_ = by_session[session]
        dd = (peak[session] - p_.equity) / peak[session]
        row_v = (session, role, f"{p_.equity:.4f}", f"{peak[session]:.4f}", f"{dd:.4%}",
                 t["band"], t["vol"], t["combined"], t["lockout"])
        print("  " + " ".join(f"{str(v):>12s}" for v in row_v))

print()
print("  ladder band occupancy over the run:", run.risk["ladder"]["sessions_in_band"])
print("  deepest band:", run.risk["ladder"]["deepest_band"], " final band:",
      run.risk["ladder"]["final_band"])
print("  volatility scalar:", run.risk["volatility_scalar"])
print("  combined scalar  :", run.risk["combined_scalar"])
