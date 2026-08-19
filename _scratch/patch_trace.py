"""Patch a3_iwm_trace.py: capture the engine, and attach the run's own sizing/risk state to
every episode row plus a top-level risk_context block. Idempotent-ish: asserts every anchor."""

from pathlib import Path

P = Path(r"D:\Product\stock-trade-alpaca\_scratch\a3_iwm_trace.py")
s = P.read_text(encoding="utf-8")

Q = '"""'

# -- 1. capture the engine instance --------------------------------------------------------------
A1 = "R.build_candidate = observing_build\ntry:\n"
N1 = """# The engine is captured the same way and for the same reason: RA3 writes one risk-state line per
# session (session|band|lockout|vol_scalar|combined_scalar) whose digest is one of the four sealed
# digests, but the runner does not surface the lines themselves. The class is not subclassed and no
# method is wrapped -- the factory returns exactly what the sealed constructor returns, and the four
# digest checks below are what prove the observation changed nothing.
ENGINES: list[object] = []
_real_engine = R.RotationEngineRA3


def capturing_engine(*a, **kw):
    engine = _real_engine(*a, **kw)
    ENGINES.append(engine)
    return engine


R.build_candidate = observing_build
R.RotationEngineRA3 = capturing_engine
try:
"""
assert s.count(A1) == 1
s = s.replace(A1, N1, 1)

A2 = "finally:\n    R.build_candidate = _real_build\n"
N2 = """finally:
    R.build_candidate = _real_build
    R.RotationEngineRA3 = _real_engine
assert len(ENGINES) == 1, len(ENGINES)
engine = ENGINES[0]
"""
assert s.count(A2) == 1
s = s.replace(A2, N2, 1)

# -- 2. equity / high-water mark / per-session risk state ----------------------------------------
A3 = "# -- 5. the full ledger export"
N3 = """# -- 4b. equity, high-water mark and the run's own per-session risk state -----------------------

EQUITY = {p.session.isoformat(): p for p in result.equity_curve}
HWM: dict[str, Decimal] = {}
_peak = None
for _p in result.equity_curve:
    _peak = _p.equity if _peak is None or _p.equity > _peak else _peak
    HWM[_p.session.isoformat()] = _peak
HWM_PEAK = max((p.equity, p.session.isoformat()) for p in result.equity_curve)

RISK_STATE: dict[str, dict[str, object]] = {}
for _line in engine.risk_state_payload().splitlines():
    _sess, _band, _lock, _vol, _comb = _line.split("|")
    RISK_STATE[_sess] = {"band": int(_band), "lockout_remaining": int(_lock),
                         "volatility_scalar": _vol, "combined_scalar": _comb}
assert len(RISK_STATE) == run.risk["risk_state_sessions"], (
    len(RISK_STATE), run.risk["risk_state_sessions"])
TARGET_WEIGHT = variant.target_weight


def sizing_at(decision_session):
    {Q}What the risk architecture allowed this entry to be, read off the run's own records.

    Nothing here is recomputed from the sealed band table: the band and the combined scalar are the
    lines the sealed engine wrote. Only the drawdown is derived from the equity curve, and only so
    that the band is readable next to it.
    {Q}
    if decision_session is None:
        return {"decision_session": None,
                "note": "no rebalance session immediately precedes this entry fill"}
    point = EQUITY[decision_session]
    state = RISK_STATE[decision_session]
    peak = HWM[decision_session]
    return {
        "decision_session": decision_session,
        "equity": s(point.equity),
        "cash": s(point.cash),
        "position_count": point.position_count,
        "high_water_mark": s(peak),
        "drawdown_from_high_water_mark": s(share(peak - point.equity, peak)),
        "risk_ladder_band": state["band"],
        "volatility_scalar": state["volatility_scalar"],
        "combined_risk_scalar": state["combined_scalar"],
        "target_weight_per_position": s(TARGET_WEIGHT),
        "unscaled_target_notional": s(TARGET_WEIGHT * point.equity),
        "scaled_target_notional": s(
            TARGET_WEIGHT * Decimal(state["combined_scalar"]) * point.equity),
    }


# -- 5. the full ledger export"""
assert s.count(A3) == 1
s = s.replace(A3, N3.replace("{Q}", Q), 1)

# -- 3. per-episode sizing + return on capital ---------------------------------------------------
A4 = '        "pnl": s(ep.pnl) if ep.closed else None,\n    })\n'
N4 = '''        "pnl": s(ep.pnl) if ep.closed else None,
        "return_on_entry_cash": (s(share(ep.pnl, ep.entry_cash))
                                 if ep.closed and ep.entry_cash > ZERO else None),
        "entry_sizing": sizing_at(mom.get("decision_session")),
    })
'''
assert s.count(A4) == 1
s = s.replace(A4, N4, 1)

# -- 4. the risk_context block -------------------------------------------------------------------
A5 = '    "per_symbol_context": per_symbol,\n'
N5 = '''    "risk_context": {
        "why_this_is_here": (
            "Two of IWM's four entries were filled at roughly half the notional of the other two. "
            "The target weight is a constant 0.25 of equity, so the difference is the RA3-4 de-risk "
            "ladder's combined risk scalar at those decision sessions -- read off the engine's own "
            "per-session risk state, not recomputed from the band table."
        ),
        "target_weight_per_position": s(TARGET_WEIGHT),
        "sealed_ladder_bands": [
            {"band": b.band, "dd_from": s(b.dd_from),
             "dd_to_exclusive": None if b.dd_to_exclusive is None else s(b.dd_to_exclusive),
             "scalar": s(b.scalar)}
            for b in engine.risk.bands
        ],
        "equity_high_water_mark": s(HWM_PEAK[0]),
        "equity_high_water_mark_session": HWM_PEAK[1],
        "final_equity": s(result.equity_curve[-1].equity),
        "ladder": run.risk["ladder"],
        "volatility_scalar": run.risk["volatility_scalar"],
        "combined_scalar": run.risk["combined_scalar"],
        "combined_scalar_minimum": run.risk["combined_scalar_minimum"],
        "max_gross_fraction_observed": run.risk["max_gross_fraction_observed"],
        "risk_state_sessions": run.risk["risk_state_sessions"],
        "risk_state_digest": run.risk["risk_state_digest"],
    },
    "per_symbol_context": per_symbol,
'''
assert s.count(A5) == 1
s = s.replace(A5, N5, 1)

P.write_text(s, encoding="utf-8")
print("patched", P)
