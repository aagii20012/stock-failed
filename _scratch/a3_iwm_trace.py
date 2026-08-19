"""Read-only diagnostic: the closed-episode ledger of Attempt 3's representative, and IWM in it.

Not a governance artifact. Writes only under reports/diagnostics/attempt3_iwm_trace/, which is
outside every repo_state_id pattern and outside every sealed package directory.

The run is produced by the sealed modules themselves: stockedge100.strategies.g2_runner_ra3.run_one
executes it, stockedge100.backtest.g2_episodes_ra1.build_episode_ledger builds the ledger, and
EpisodeLedger.pnl_by_symbol() is the same call the gate's condition_6_ra1 makes. Nothing is
reimplemented.

The one thing the sealed run does not record is the *value* of the momentum signal at each
rebalance -- RotationCandidate.selection_log stores targets and entries but not the scores, and the
scores survive only inside the ranking hash. So build_candidate is wrapped (in this process only)
with an observer that calls the real RotationCandidateRA3.rank and records what it returned. The
wrapper adds no computation to the run; that it perturbed nothing is checked by requiring the
ranking digest, the trades digest, the equity digest and the risk-state digest to equal the sealed
values byte for byte.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import statistics
import sys
from decimal import Decimal
from pathlib import Path

REPO = Path(r"D:\Product\stock-trade-alpaca\stockedge100")
sys.path.insert(0, str(REPO / "src"))

OUT = REPO / "reports" / "diagnostics" / "attempt3_iwm_trace"
SEALED = REPO / "reports" / "stage3_g2_attempt3" / "STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json"

VARIANT_ID = "SE100-G2-S3-C3-ROTATION-RA3-L03-K2-QUARTERLY"
LABEL = "#BASE"
FOCUS = "IWM"

from stockedge100.backtest.costs import ENGINE_CONTEXT  # noqa: E402
from decimal import localcontext  # noqa: E402
from stockedge100.strategies import g2_runner_ra3 as R  # noqa: E402
from stockedge100.strategies.g2_rotation_ra3 import (  # noqa: E402
    check_mechanics_carried_unchanged,
    load_protocol,
    variant_by_id,
)

ZERO = Decimal(0)


def s(value) -> str:
    return f"{value:f}" if isinstance(value, Decimal) else str(value)


def share(numerator: Decimal, denominator: Decimal) -> Decimal:
    """A ratio under the engine's own decimal context.

    The gate computes every share inside ``@exact``, i.e. under ENGINE_CONTEXT. Dividing at the
    default 28-digit context produces a value that agrees to 28 digits and then stops, which reads
    as a mismatch against the sealed string. The context is the sealed one, not a choice made here.
    """
    with localcontext(ENGINE_CONTEXT):
        return numerator / denominator


# -- 0. the sealed anchors, read off disk -------------------------------------------------------

sealed = json.loads(SEALED.read_text(encoding="utf-8"))
cand = sealed["candidate_results"][0]
assert cand["variant_id"] == VARIANT_ID, cand["variant_id"]
sealed_digests = sealed["determinism"]["run_digests"][f"{VARIANT_ID}{LABEL}"]
c6 = cand["conditions"][5]["evidence"]
c3 = cand["conditions"][2]["evidence"]
c4 = cand["conditions"][3]["evidence"]
c1 = cand["conditions"][0]["evidence"]
c5 = cand["conditions"][4]["evidence"]

print("== sealed anchors ==")
for k, v in sorted(sealed_digests.items()):
    print("   %-18s %s" % (k, v))
print("   %-18s %s" % ("closed_episodes", c4["closed_episodes"]))
print("   %-18s %s" % ("total_ep_pnl", c6["total_closed_episode_pnl"]))
print("   %-18s %s" % ("IWM pnl", c6["pnl_by_instrument"][FOCUS]))
print("   %-18s %s" % ("IWM share", c6["share_by_instrument"][FOCUS]))
print("   %-18s %s" % ("symbols_traded", c6["distinct_symbols_traded"]))

# -- 1. module immutability and the span, before running anything --------------------------------

print("\n== prior-attempt module verification (AT-H) ==")
mods = R.verify_prior_attempt_modules()
print("   module_count       =", mods["module_count"])
print("   modules_verified   =", len(mods["modules_verified"]))
print("   modules_that_moved =", mods["modules_that_moved"])
assert not mods["modules_that_moved"], mods["modules_that_moved"]
protocol = load_protocol()
mech = check_mechanics_carried_unchanged(protocol)
print("   mechanics blocks compared =", len(mech["blocks_compared"]),
      "pointers_removed =", mech["pointers_removed"])

print("\n== dataset ==")
series = R.load_grid_dataset()
print("   symbols loaded =", len(series))
span = R.recheck_run_span(series, protocol=protocol, write=False)
print("   span keys      =", sorted(span)[:12])
print("   span diffs     =", span.get("differences"), span.get("mismatches"))
print("   run_start/end  =", protocol["run_span"]["run_start"], protocol["run_span"]["run_end"])

# -- 2. run the variant, observing the rankings -------------------------------------------------

RANKINGS: dict[str, list[tuple[str, str]]] = {}
EXCLUDED: dict[str, list[str]] = {}

_real_build = R.build_candidate


def observing_build(variant, scenario, **kw):
    candidate = _real_build(variant, scenario, **kw)
    real_rank = candidate.rank  # bound method of the sealed class

    def rank(view, session):
        scored, excluded = real_rank(view, session)
        key = session.isoformat()
        RANKINGS[key] = [(sym, f"{val:f}") for val, sym in scored]
        EXCLUDED[key] = list(excluded)
        return scored, excluded

    candidate.rank = rank
    return candidate


# The engine is captured the same way and for the same reason: RA3 writes one risk-state line per
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
    variant = variant_by_id(VARIANT_ID)
    print("\n== running %s%s ==" % (VARIANT_ID, LABEL))
    run = R.run_one(variant, LABEL, series, protocol=protocol)
finally:
    R.build_candidate = _real_build
    R.RotationEngineRA3 = _real_engine
assert len(ENGINES) == 1, len(ENGINES)
engine = ENGINES[0]

result = run.result
ledger = run.ledger
row = R.grid_report([run])[0]
print("   fills=%d closed_trades=%d total_return=%s" % (
    len(result.fills), len(result.trades), s(result.total_return())))
print("   rebalance sessions observed =", len(RANKINGS))

# -- 3. reproduction check against the seal -----------------------------------------------------

checks: list[tuple[str, str, str, bool]] = []


def check(name, got, expected):
    got, expected = str(got), str(expected)
    ok = got == expected
    checks.append((name, got, expected, ok))
    print("   [%s] %-22s %s" % ("OK" if ok else "MISMATCH", name, got if ok else
                                "got %s expected %s" % (got, expected)))
    return ok


print("\n== reproduction vs sealed evidence ==")
for field in ("trades_digest", "equity_digest", "ranking_digest", "risk_state_digest",
              "fills", "closed_trades", "total_return", "shutdown_session"):
    check(field, row[field], sealed_digests[field])
check("starting_equity", s(result.starting_equity), c1["starting_equity"])
check("final_equity", s(result.final_equity), c1["final_equity"])
closed = ledger.closed_episodes
check("closed_episodes", len(closed), c4["closed_episodes"])
check("open_episodes_at_end", len(ledger.open_episodes), c4["open_episodes_at_end"])
contributions = ledger.pnl_by_symbol()
total_net = sum(contributions.values(), ZERO)
check("total_closed_ep_pnl", s(total_net), c6["total_closed_episode_pnl"])
check("distinct_symbols", len(contributions), c6["distinct_symbols_traded"])
check("IWM_pnl", s(contributions[FOCUS]), c6["pnl_by_instrument"][FOCUS])
check("IWM_share", s(share(contributions[FOCUS], total_net)), c6["share_by_instrument"][FOCUS])
check("gross_profit", s(sum((e.pnl for e in closed if e.pnl > ZERO), ZERO)), c3["gross_profit"])
check("gross_loss", s(-sum((e.pnl for e in closed if e.pnl < ZERO), ZERO)), c3["gross_loss"])
check("multi_leg_episodes", ledger.reconciliation.multi_leg_episodes, c5["multi_leg_episodes"])
for sym, val in sorted(contributions.items()):
    check("pnl[%s]" % sym, s(val), c6["pnl_by_instrument"][sym])

REPRODUCED = all(ok for _, _, _, ok in checks)
print("\n   REPRODUCTION %s (%d/%d checks agree)" % (
    "EXACT" if REPRODUCED else "FAILED", sum(1 for c in checks if c[3]), len(checks)))
if not REPRODUCED:
    print("   Refusing to emit detail from a run that does not reproduce the seal.")
    sys.exit(1)

# -- 4. sessions, and the decision session behind each entry ------------------------------------

sessions = [p.session for p in result.equity_curve]
index_of = {d: i for i, d in enumerate(sessions)}
rebalance_sessions = sorted(dt.date.fromisoformat(k) for k in RANKINGS)
# the candidate's own selection_log is not on GridRunRA3; rebuild targets/entries from RANKINGS+k
# is not safe, so read entries off the fills instead: every BUY fill is an entry leg.
entry_sessions_by_symbol: dict[str, list[dt.date]] = {}
for ep in ledger.episodes:
    entry_sessions_by_symbol.setdefault(ep.symbol, []).append(ep.entry_session)


def decision_session_for(fill_session: dt.date) -> dt.date | None:
    """The rebalance session whose orders filled at ``fill_session``'s open.

    Orders are decided at a session close and filled at the next session's open, so the decision
    session is the latest rebalance session strictly before the fill session. Returned as None if
    no rebalance session qualifies, which is reported rather than guessed.
    """
    prior = [d for d in rebalance_sessions if d < fill_session]
    if not prior:
        return None
    candidate_session = prior[-1]
    # require adjacency in the session index: the fill must be the very next session
    if index_of.get(candidate_session) is None or index_of.get(fill_session) is None:
        return None
    if index_of[fill_session] - index_of[candidate_session] != 1:
        return None
    return candidate_session


def momentum_at(fill_session: dt.date, symbol: str) -> dict[str, object]:
    d = decision_session_for(fill_session)
    if d is None:
        return {"decision_session": None, "signal": None, "rank": None, "ranked_universe": None,
                "note": "no rebalance session immediately precedes this entry fill"}
    ranked = RANKINGS[d.isoformat()]
    pos = next((i + 1 for i, (sym, _) in enumerate(ranked) if sym == symbol), None)
    val = next((v for sym, v in ranked if sym == symbol), None)
    return {
        "decision_session": d.isoformat(),
        "signal": val,
        "rank": pos,
        "ranked_universe": len(ranked),
        "excluded_count": len(EXCLUDED[d.isoformat()]),
        "top_of_ranking": [{"symbol": sym, "signal": v} for sym, v in ranked[:3]],
    }


# -- 4b. equity, high-water mark and the run's own per-session risk state -----------------------

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
    """What the risk architecture allowed this entry to be, read off the run's own records.

    Nothing here is recomputed from the sealed band table: the band and the combined scalar are the
    lines the sealed engine wrote. Only the drawdown is derived from the equity curve, and only so
    that the band is readable next to it.
    """
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


# -- 5. the full ledger export ------------------------------------------------------------------

def calendar_days(a: dt.date, b: dt.date) -> int:
    return (b - a).days


def trading_sessions(a: dt.date, b: dt.date) -> int | None:
    if a in index_of and b in index_of:
        return index_of[b] - index_of[a]
    return None


ledger_rows = []
for ep in ledger.episodes:
    mom = momentum_at(ep.entry_session, ep.symbol)
    ledger_rows.append({
        "symbol": ep.symbol,
        "open_index": ep.open_index,
        "close_index": ep.close_index,
        "closed": ep.closed,
        "entry_session": ep.entry_session.isoformat(),
        "exit_session": None if ep.exit_session is None else ep.exit_session.isoformat(),
        "holding_calendar_days": (None if ep.exit_session is None
                                  else calendar_days(ep.entry_session, ep.exit_session)),
        "holding_trading_sessions": (None if ep.exit_session is None
                                     else trading_sessions(ep.entry_session, ep.exit_session)),
        "entry_momentum": mom,
        "entry_cash": s(ep.entry_cash),
        "exit_cash": s(ep.exit_cash),
        "dividends": s(ep.dividends),
        "trimmed_proceeds": s(ep.trimmed_proceeds),
        "sale_legs": ep.sale_leg_count,
        "single_leg": ep.single_leg,
        "pnl": s(ep.pnl) if ep.closed else None,
        "return_on_entry_cash": (s(share(ep.pnl, ep.entry_cash))
                                 if ep.closed and ep.entry_cash > ZERO else None),
        "entry_sizing": sizing_at(mom.get("decision_session")),
    })

by_close = sorted((r for r in ledger_rows if r["closed"]), key=lambda r: r["close_index"])
running = ZERO
for r in by_close:
    running += Decimal(r["pnl"])
    r["running_total_pnl_all_symbols"] = s(running)

# -- 6. IWM specifically ------------------------------------------------------------------------

iwm = [r for r in ledger_rows if r["symbol"] == FOCUS]
iwm.sort(key=lambda r: r["entry_session"])
running = ZERO
prev_exit = None
for r in iwm:
    if r["closed"]:
        running += Decimal(r["pnl"])
        r["iwm_running_total_pnl"] = s(running)
    r["gap_from_previous_iwm_exit_calendar_days"] = (
        None if prev_exit is None else calendar_days(prev_exit, dt.date.fromisoformat(r["entry_session"])))
    r["gap_from_previous_iwm_exit_trading_sessions"] = (
        None if prev_exit is None
        else trading_sessions(prev_exit, dt.date.fromisoformat(r["entry_session"])))
    if r["exit_session"]:
        prev_exit = dt.date.fromisoformat(r["exit_session"])

iwm_closed = [r for r in iwm if r["closed"]]
iwm_pnls = [Decimal(r["pnl"]) for r in iwm_closed]

# how often was IWM in the top-k at a rebalance, whether or not that started an episode
K = variant.top_k
iwm_in_topk = []
for d in rebalance_sessions:
    ranked = RANKINGS[d.isoformat()]
    top = [sym for sym, _ in ranked[:K]]
    if FOCUS in top:
        iwm_in_topk.append({
            "session": d.isoformat(),
            "rank": next(i + 1 for i, (sym, _) in enumerate(ranked) if sym == FOCUS),
            "signal": next(v for sym, v in ranked if sym == FOCUS),
        })

iwm_rank_history = [
    {"session": d.isoformat(),
     "rank": next((i + 1 for i, (sym, _) in enumerate(RANKINGS[d.isoformat()]) if sym == FOCUS), None),
     "signal": next((v for sym, v in RANKINGS[d.isoformat()] if sym == FOCUS), None)}
    for d in rebalance_sessions
]

# -- 7. every other symbol, for context ---------------------------------------------------------

per_symbol = []
for sym in sorted({r["symbol"] for r in ledger_rows}):
    rows = [r for r in ledger_rows if r["symbol"] == sym]
    cl = [r for r in rows if r["closed"]]
    durs = [r["holding_calendar_days"] for r in cl]
    tdurs = [r["holding_trading_sessions"] for r in cl]
    ranks = [r["entry_momentum"]["rank"] for r in rows if r["entry_momentum"]["rank"]]
    per_symbol.append({
        "symbol": sym,
        "episodes_total": len(rows),
        "episodes_closed": len(cl),
        "episodes_open_at_end": len(rows) - len(cl),
        "total_pnl": s(contributions.get(sym, ZERO)),
        "share_of_net": s(share(contributions.get(sym, ZERO), total_net)),
        "total_calendar_days_held": sum(durs) if durs else 0,
        "total_trading_sessions_held": sum(t for t in tdurs if t is not None),
        "mean_calendar_days": (round(statistics.mean(durs), 1) if durs else None),
        "median_calendar_days": (statistics.median(durs) if durs else None),
        "min_calendar_days": (min(durs) if durs else None),
        "max_calendar_days": (max(durs) if durs else None),
        "best_episode_pnl": (s(max(Decimal(r["pnl"]) for r in cl)) if cl else None),
        "worst_episode_pnl": (s(min(Decimal(r["pnl"]) for r in cl)) if cl else None),
        "winning_episodes": sum(1 for r in cl if Decimal(r["pnl"]) > ZERO),
        "mean_entry_rank": (round(statistics.mean(ranks), 2) if ranks else None),
        "best_entry_rank": (min(ranks) if ranks else None),
        "worst_entry_rank": (max(ranks) if ranks else None),
    })

# -- 8. write ------------------------------------------------------------------------------------

OUT.mkdir(parents=True, exist_ok=True)

payload = {
    "diagnostic_id": "SE100-DIAG-A3-IWM-TRACE",
    "not_a_governance_artifact": (
        "Explanatory analysis of the closed Attempt 3 result. No verdict, no gate, no hash record, "
        "no manifest. Produces nothing any stage may cite as evidence and modifies nothing sealed."
    ),
    "variant_id": VARIANT_ID,
    "run_label": LABEL,
    "scenario": run.scenario,
    "focus_symbol": FOCUS,
    "sealed_source": {
        "evidence_file": "reports/stage3_g2_attempt3/STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json",
        "anchors": {
            **{k: str(v) for k, v in sealed_digests.items()},
            "closed_episodes": c4["closed_episodes"],
            "total_closed_episode_pnl": c6["total_closed_episode_pnl"],
            "pnl_IWM": c6["pnl_by_instrument"][FOCUS],
            "share_IWM": c6["share_by_instrument"][FOCUS],
            "distinct_symbols_traded": c6["distinct_symbols_traded"],
        },
    },
    "reproduction_checks": [
        {"field": n, "reproduced": g, "sealed": e, "agrees": ok} for n, g, e, ok in checks
    ],
    "reproduction_exact": REPRODUCED,
    "observation_method": {
        "run_executed_by": "stockedge100.strategies.g2_runner_ra3.run_one",
        "ledger_built_by": "stockedge100.backtest.g2_episodes_ra1.build_episode_ledger",
        "attribution_call": "EpisodeLedger.pnl_by_symbol() -- the same call condition_6_ra1 makes",
        "momentum_capture": (
            "g2_runner_ra3.build_candidate was wrapped in this process only, so that the value "
            "returned by the sealed RotationCandidateRA3.rank could be recorded. The wrapper adds "
            "no computation. Non-perturbation is proved by the four digests above."
        ),
        "entry_to_decision_mapping": (
            "An episode's entry_session is the fill session. The decision session is the latest "
            "rebalance session strictly before it, required to be the immediately preceding session "
            "in the run's own session index; when that adjacency does not hold, the momentum value "
            "is reported as null rather than guessed."
        ),
        "modules_verified_immutable": mods.get("modules_checked", mods.get("count")),
    },
    "run_shape": {
        "sessions": len(sessions),
        "first_session": sessions[0].isoformat(),
        "last_session": sessions[-1].isoformat(),
        "top_k": K,
        "lookback_months": variant.lookback_months,
        "rebalance_frequency": variant.frequency,
        "scheduled_rebalance_sessions": int(sealed["candidate_results"][0]["variant"]
                                            ["scheduled_rebalance_sessions"]),
        "executed_rebalances_observed": len(RANKINGS),
        "episodes_total": len(ledger.episodes),
        "episodes_closed": len(closed),
        "episodes_open_at_end": len(ledger.open_episodes),
        "total_net_closed_episode_pnl": s(total_net),
    },
    "iwm": {
        "episode_count_total": len(iwm),
        "episode_count_closed": len(iwm_closed),
        "total_pnl": s(contributions[FOCUS]),
        "share_of_net": s(share(contributions[FOCUS], total_net)),
        "largest_episode_pnl": s(max(iwm_pnls)) if iwm_pnls else None,
        "largest_episode_share_of_iwm": s(share(max(iwm_pnls), contributions[FOCUS])) if iwm_pnls else None,
        "largest_episode_share_of_net": s(share(max(iwm_pnls), total_net)) if iwm_pnls else None,
        "winning_episodes": sum(1 for p in iwm_pnls if p > ZERO),
        "losing_episodes": sum(1 for p in iwm_pnls if p < ZERO),
        "flat_episodes": sum(1 for p in iwm_pnls if p == ZERO),
        "episodes": iwm,
        "rank_at_every_rebalance": iwm_rank_history,
        "rebalances_with_iwm_in_top_k": iwm_in_topk,
        "rebalance_count": len(rebalance_sessions),
    },
    "risk_context": {
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
    "full_episode_ledger": ledger_rows,
    "closed_episodes_in_closing_order_with_running_total": by_close,
    "reconciliation": ledger.reconciliation.to_json(),
}

(OUT / "episode_ledger.json").write_text(
    json.dumps(payload, indent=1, sort_keys=False) + "\n", encoding="utf-8")
print("\nwrote %s" % (OUT / "episode_ledger.json"))

# -- 9. console summary the report is written from ----------------------------------------------

print("\n== IWM episodes (%d) ==" % len(iwm))
print("%-3s %-11s %-11s %5s %5s %6s %8s %9s %9s %9s" % (
    "#", "entry", "exit", "cald", "sess", "rank", "signal", "pnl", "cum", "gap_d"))
for i, r in enumerate(iwm, 1):
    m = r["entry_momentum"]
    print("%-3d %-11s %-11s %5s %5s %6s %8s %9s %9s %9s" % (
        i, r["entry_session"], r["exit_session"] or "OPEN",
        r["holding_calendar_days"], r["holding_trading_sessions"],
        m["rank"], m["signal"][:8] if m["signal"] else "-",
        r["pnl"] or "-", r.get("iwm_running_total_pnl", "-"),
        r["gap_from_previous_iwm_exit_calendar_days"]))

print("\n== per-symbol context ==")
print("%-5s %4s %4s %6s %8s %6s %6s %6s %6s %6s %6s" % (
    "sym", "eps", "cls", "days", "pnl", "share", "mean", "med", "min", "max", "rank"))
for p in sorted(per_symbol, key=lambda x: -Decimal(x["total_pnl"])):
    print("%-5s %4d %4d %6d %8s %6s %6s %6s %6s %6s %6s" % (
        p["symbol"], p["episodes_total"], p["episodes_closed"], p["total_calendar_days_held"],
        p["total_pnl"], p["share_of_net"][:6], p["mean_calendar_days"], p["median_calendar_days"],
        p["min_calendar_days"], p["max_calendar_days"], p["mean_entry_rank"]))

print("\n== IWM rank at every rebalance ==")
for h in iwm_rank_history:
    print("   %s rank=%-3s signal=%s" % (h["session"], h["rank"],
                                         (h["signal"] or "-")[:12]))

print("\n== totals ==")
print("   episodes closed          =", len(closed))
print("   net closed-episode P&L   =", s(total_net))
print("   gross profit / gross loss=", c3["gross_profit"], "/", c3["gross_loss"])
print("   IWM P&L / share of net   =", s(contributions[FOCUS]), "/",
      s(share(contributions[FOCUS], total_net)))
print("   IWM share of gross profit=", s(share(contributions[FOCUS], Decimal(c3["gross_profit"]))))
print("   symbols with net > 0     =", sum(1 for v in contributions.values() if v > ZERO))
print("   symbols with net < 0     =", sum(1 for v in contributions.values() if v < ZERO))
