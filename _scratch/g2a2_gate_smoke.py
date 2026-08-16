"""Adversarial smoke for the Attempt 2 gate (`strategies/g2_gate_ra1.py`).

Same discipline as the engine, strategy and ledger harnesses: **no expected value below is copied
from the module under test.** Each expectation is either quoted from
`config/generation_2/g2_gate_criteria_ra1.json`, produced by the FROZEN `Portfolio` replaying the
same fills, or computed here from the arithmetic by hand.

The module lives in `src/`, a `repo_state_id` pattern, so a defect found after the decision package
is built cannot be repaired without invalidating the digest that package recorded. This runs first.

ASCII only: the console is cp1252.
"""

from __future__ import annotations

import copy
import datetime as dt
import json
import pathlib
import sys
from decimal import Decimal

ROOT = pathlib.Path(__file__).resolve().parents[1] / "stockedge100"
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.backtest.costs import Fill  # noqa: E402
from stockedge100.backtest.engine import BacktestResult, EquityPoint, FillRecord  # noqa: E402
from stockedge100.backtest.errors import ConfigViolation, DataIntegrityHalt  # noqa: E402
from stockedge100.backtest.g2_episodes_ra1 import build_episode_ledger  # noqa: E402
from stockedge100.backtest.metrics import profit_factor  # noqa: E402
from stockedge100.backtest.orders import BUY, SELL  # noqa: E402
from stockedge100.backtest.portfolio import Portfolio  # noqa: E402

import stockedge100.strategies.g2_gate_ra1 as G  # noqa: E402

PASSED = 0
FAILED = 0
D = Decimal


def check(label: str, ok: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if ok:
        PASSED += 1
        print("  ok   %s" % label)
    else:
        FAILED += 1
        print("  FAIL %s   %s" % (label, detail))


def raises(label: str, thunk, exc_type, fragment: str = "") -> None:
    global PASSED, FAILED
    try:
        thunk()
    except exc_type as exc:
        if fragment and fragment not in str(exc):
            FAILED += 1
            print("  FAIL raises: %s -- raised but message lacks %r: %s" % (label, fragment, exc))
        else:
            PASSED += 1
            print("  ok   raises: %s" % label)
    except Exception as exc:  # noqa: BLE001
        FAILED += 1
        print("  FAIL raises: %s -- wrong exception %s: %s" % (label, type(exc).__name__, exc))
    else:
        FAILED += 1
        print("  FAIL raises: %s -- no exception" % label)


CRITERIA_TEXT = (ROOT / "config/generation_2/g2_gate_criteria_ra1.json").read_text(encoding="utf-8")
SEAL = json.loads(CRITERIA_TEXT)
CONDS = {c["id"]: c for c in SEAL["conditions"]}
A1_SEAL = json.loads((ROOT / "config/generation_2/g2_gate_criteria.json").read_text(encoding="utf-8"))
PROTOCOL = json.loads(
    (ROOT / "config/generation_2/g2_rotation_ra1_protocol.json").read_text(encoding="utf-8")
)


# -- fixtures ------------------------------------------------------------------------------------


def day(n: int) -> dt.date:
    return dt.date(2020, 1, 1) + dt.timedelta(days=n)


def buy(symbol: str, quantity: str, price: str) -> Fill:
    q, p = D(quantity), D(price)
    gross = (q * p).quantize(D("0.01"))
    return Fill(symbol=symbol, side=BUY, quantity=q, reference_price=p, effective_price=p,
                gross_notional=gross, commission=D("0.00"), sec_fee=D("0.00"), taf_fee=D("0.00"),
                cash_delta=-gross)


def sell(symbol: str, quantity: str, price: str) -> Fill:
    q, p = D(quantity), D(price)
    gross = (q * p).quantize(D("0.01"))
    return Fill(symbol=symbol, side=SELL, quantity=q, reference_price=p, effective_price=p,
                gross_notional=gross, commission=D("0.00"), sec_fee=D("0.00"), taf_fee=D("0.00"),
                cash_delta=gross)


def replay(events, curve, *, starting_equity="100.00", final_equity=None, shutdown=None,
           label="PROBE"):
    """Apply fills to the FROZEN Portfolio; package with a hand-built equity curve.

    `curve` is [(session_index, equity_string), ...]. The gate reads the curve for S3-C1, S3-C2 and
    S3-C5's entry bases, and reads the frozen `Portfolio.trades` for the reconciliation.
    """
    portfolio = Portfolio(D("1000000.00"), max_positions=10)
    fills: list[FillRecord] = []
    for kind, session, oid, payload in events:
        if kind == "FILL":
            portfolio.apply_fill(session, payload)
            fills.append(FillRecord(session=session, order_id=oid, fill=payload))
        else:
            raise AssertionError(kind)
    points = [
        EquityPoint(session=day(n), cash=D(e), equity=D(e), stale_mark=False, position_count=0)
        for n, e in curve
    ]
    final = D(final_equity) if final_equity is not None else (points[-1].equity if points else D(starting_equity))
    return BacktestResult(
        label=label, scenario="BASE", symbols=("AAA", "BBB", "CCC"), start=day(0), end=day(60),
        equity_curve=points, fills=fills, rejections=[], trades=list(portfolio.trades),
        dividend_events=[], stale_marks=0, shutdown_session=shutdown,
        starting_equity=D(starting_equity), final_cash=portfolio.cash, final_equity=final,
        open_positions=[], cost_model={},
    )


def flat_result(total_return: str, label="NB"):
    """A minimal result whose only interesting property is the sign of its total return."""
    start = D("100.00")
    final = (start * (D(1) + D(total_return))).quantize(D("0.0001"))
    return BacktestResult(
        label=label, scenario="BASE", symbols=(), start=day(0), end=day(1),
        equity_curve=[
            EquityPoint(session=day(0), cash=start, equity=start, stale_mark=False, position_count=0),
            EquityPoint(session=day(1), cash=final, equity=final, stale_mark=False, position_count=0),
        ],
        fills=[], rejections=[], trades=[], dividend_events=[], stale_marks=0,
        shutdown_session=None, starting_equity=start, final_cash=final, final_equity=final,
        open_positions=[], cost_model={},
    )


# ==================================================================================================
print("\n== 1. the seal loads, and the seal checks are not decorative ==")

criteria = G.load_criteria()
check("artifact_id is the Attempt 2 criteria file", criteria["artifact_id"] == "SE100-CFG-3104",
      criteria["artifact_id"])
check("generation/stage/attempt are 2/3/2",
      (criteria["generation"], criteria["stage"], criteria["attempt"]) == (2, 3, 2))

# Tamper copies in memory. The files on disk are frozen and are never written by this harness.
bad = copy.deepcopy(criteria)
bad["conditions"] = [
    dict(c, measurement=dict(c["measurement"], axis_orderings={"lookback_months": [3, 6, 12],
                                                              "top_k": [3, 2, 1],
                                                              "rebalance_frequency": ["MONTHLY", "QUARTERLY"]}))
    if c["id"] == "S3-C7" else c
    for c in bad["conditions"]
]
raises("reordered top_k axis is rejected", lambda: G._check_axes_agree(bad), ConfigViolation,
       "two seals disagree")

bad2 = copy.deepcopy(criteria)
bad2["verdict_token_derivation"]["fail_token"] = A1_SEAL["verdict_token_derivation"]["fail_token"]
raises("an Attempt 1 token in the derivation is rejected",
       lambda: G._check_tokens_are_attempt_2s_own(bad2), ConfigViolation, "Attempt 1 is closed")

bad3 = copy.deepcopy(criteria)
bad3["verdict_token_derivation"]["attempt_1_tokens_are_not_available_here"] = "nothing withheld"
raises("prose that does not name Attempt 1's tokens is rejected",
       lambda: G._check_tokens_are_attempt_2s_own(bad3), ConfigViolation, "do not agree")

# Rule 10's threshold seal check, proved non-vacuous on a tampered copy.
from stockedge100.strategies.gate import check_thresholds_against_seal  # noqa: E402
for field, value in [("profit_factor_min", 1.05), ("max_drawdown_pct", 20), ("closed_trades_min", 5)]:
    bad4 = copy.deepcopy(criteria)
    bad4["frozen_gate_json_companion_verbatim"]["thresholds"][field] = value
    raises("rule 10 rejects a loosened %s" % field,
           lambda b=bad4: check_thresholds_against_seal(b), Exception)

a1_pass, a1_fail = G.attempt_1_tokens()
check("Attempt 1's tokens are read from Attempt 1's file",
      (a1_pass, a1_fail) == (A1_SEAL["verdict_token_derivation"]["pass_token"],
                             A1_SEAL["verdict_token_derivation"]["fail_token"]))
ours = (criteria["verdict_token_derivation"]["pass_token"],
        criteria["verdict_token_derivation"]["fail_token"])
check("Attempt 2's tokens are disjoint from Attempt 1's", not (set(ours) & {a1_pass, a1_fail}),
      "%s vs %s" % (ours, (a1_pass, a1_fail)))
check("pass token is the sealed one",
      ours[0] == "STAGE_3_G2_ATTEMPT_2_STRATEGY_ADMITTED_IN_DEVELOPMENT", ours[0])
check("fail token is the sealed one",
      ours[1] == "STAGE_3_G2_ATTEMPT_2_NO_CANDIDATE", ours[1])


# ==================================================================================================
print("\n== 2. the plan, entirely from the seals ==")

plan = G.build_plan()
run = PROTOCOL["run_span"]
check("run_start from the protocol", plan.run_start.isoformat() == run["run_start"])
check("run_end from the protocol", plan.run_end.isoformat() == run["run_end"])
check("sessions from the protocol", plan.sessions == run["sessions"], str(plan.sessions))
check("binding symbol from the protocol", plan.binding_symbol == run["binding_symbol"])
check("declared universe is the 34-member frozen list", len(plan.declared_universe) == 34,
      str(len(plan.declared_universe)))
check("risk architecture id is carried", bool(plan.risk_architecture_id), plan.risk_architecture_id)
check("plan.to_json is JSON-serialisable", isinstance(json.dumps(plan.to_json()), str))
check("no warmup_derivation was invented (Attempt 1's run_span key is absent here)",
      "derivation" not in run and "derivation" not in plan.to_json())


# ==================================================================================================
print("\n== 3. S3-C7 neighbours: the sealed count rule, recomputed independently ==")

variants = {v.variant_id: v for v in G.rotation_variants()}
axes = PROTOCOL["grid"]["axes"]
counts = {}
neighbour_map = {}
for vid, v in variants.items():
    nb = G.neighbours_of(v, criteria)
    neighbour_map[vid] = {m.variant_id for m in nb}
    counts[vid] = len(nb)
    # Recomputed here from the axis orderings, not read back from the module.
    expected = 0
    for axis, value in (("lookback_months", v.lookback_months), ("top_k", v.top_k),
                        ("rebalance_frequency", v.frequency)):
        order = axes[axis]
        i = order.index(value)
        expected += (1 if i > 0 else 0) + (1 if i < len(order) - 1 else 0)
    if len(nb) != expected:
        check("neighbour count for %s" % vid, False, "%d vs %d" % (len(nb), expected))

check("every variant's neighbour count matches the independent recount",
      all(counts[vid] == G.expected_neighbour_count(variants[vid], criteria) for vid in variants))
check("every count is in {3,4,5}", set(counts.values()) <= {3, 4, 5}, str(sorted(set(counts.values()))))
# The sealed rule: "3 when ... endpoint of both the lookback and the k axis; 5 when it is interior
# on both; 4 otherwise." Both-endpoint variants: lookback in {3,12} and k in {1,3} -> 2*2*2 = 8.
# Both-interior: lookback 6 and k 2 -> 1*1*2 = 2. Remainder 8.
dist = {n: sum(1 for c in counts.values() if c == n) for n in (3, 4, 5)}
check("8 variants sit at both endpoints (3 neighbours)", dist[3] == 8, str(dist))
check("2 variants are interior on both (5 neighbours)", dist[5] == 2, str(dist))
check("the other 8 have 4 neighbours", dist[4] == 8, str(dist))
check("total neighbour links = 8*3 + 8*4 + 2*5 = 66", sum(counts.values()) == 66,
      str(sum(counts.values())))
check("no variant is its own neighbour",
      all(vid not in neighbour_map[vid] for vid in variants))
check("the neighbour relation is symmetric",
      all(a in neighbour_map[b] for a in variants for b in neighbour_map[a]))
check("neighbours are returned in grid-index order",
      all([m.index for m in G.neighbours_of(v, criteria)]
          == sorted(m.index for m in G.neighbours_of(v, criteria)) for v in variants.values()))


# ==================================================================================================
print("\n== 4. rule 9: vacuity halts when something closed, and does not when nothing did ==")

# The seal's own G2A2-CONFLICT-18 probe: one closed episode, two sale legs, so nothing single-leg.
probe = replay(
    [("FILL", day(2), "o1", buy("AAA", "1", "100.00")),
     ("FILL", day(3), "o2", sell("AAA", "0.5", "120.00")),
     ("FILL", day(4), "o3", sell("AAA", "0.5", "90.00"))],
    [(1, "100.00"), (4, "105.00")],
)
probe_ledger = build_episode_ledger(probe)
check("probe closed exactly one episode", len(probe_ledger.closed_episodes) == 1)
check("probe has no single-leg episode", probe_ledger.reconciliation.single_leg_compared == 0)
raises("rule 9 halts: episodes closed, none single-leg",
       lambda: G.assert_reconciliation_non_vacuous(probe_ledger), DataIntegrityHalt,
       "asserted about nothing")

# Nothing closed: an open buy and no sale. Vacuous, but there was nothing to reconcile.
open_only = replay([("FILL", day(2), "o1", buy("AAA", "1", "100.00"))],
                   [(1, "100.00"), (4, "90.00")])
open_ledger = build_episode_ledger(open_only)
check("nothing closed", len(open_ledger.closed_episodes) == 0)
report = G.assert_reconciliation_non_vacuous(open_ledger)
check("rule 9 does not halt when nothing closed", report["nothing_closed"] is True)
check("the report carries the compared count beside the mismatch count",
      report["single_leg_compared"] == 0 and report["mismatch_count"] == 0)
c3_empty = G.condition_3_ra1(open_only, open_ledger, criteria)
c4_empty = G.condition_4_ra1(open_only, open_ledger, criteria)
check("...and S3-C3 is NOT_EVALUABLE, which is not a pass",
      c3_empty.verdict == "NOT_EVALUABLE" and not c3_empty.satisfied, c3_empty.verdict)
check("...and S3-C4 measures 0 against the floor of 30",
      c4_empty.verdict == "NOT_MET" and c4_empty.measured == "0", c4_empty.measured)


# ==================================================================================================
print("\n== 5. S3-C3: the gating figure is the ledger's, the reconciliation figure is the frozen one ==")

# Three closed episodes, entered against three different equity levels.
#   AAA  buy d2 @100, sell d3 @110  -> pnl +10.00
#   BBB  buy d10 @100, sell d11 @120 -> pnl +20.00
#   CCC  buy d12 @100, sell d13 @50  -> pnl -50.00
mixed_events = [
    ("FILL", day(2), "a1", buy("AAA", "1", "100.00")),
    ("FILL", day(3), "a2", sell("AAA", "1", "110.00")),
    ("FILL", day(10), "b1", buy("BBB", "1", "100.00")),
    ("FILL", day(11), "b2", sell("BBB", "1", "120.00")),
    ("FILL", day(12), "c1", buy("CCC", "1", "100.00")),
    ("FILL", day(13), "c2", sell("CCC", "1", "50.00")),
]
mixed_curve = [(1, "100.00"), (2, "100.00"), (3, "110.00"), (9, "1000.00"), (10, "1000.00"),
               (11, "500.00"), (12, "500.00"), (13, "450.00")]
mixed = replay(mixed_events, mixed_curve, final_equity="450.00")
mixed_ledger = build_episode_ledger(mixed)
check("three episodes closed", len(mixed_ledger.closed_episodes) == 3)
check("episode P&Ls, computed by hand from the cash arithmetic",
      [f"{p:f}" for p in mixed_ledger.pnls] == ["10.00", "20.00", "-50.00"],
      str([f"{p:f}" for p in mixed_ledger.pnls]))

c3 = G.condition_3_ra1(mixed, mixed_ledger, criteria)
# gross profit 30.00, gross loss 50.00 -> 0.6, below the sealed 1.10
check("S3-C3 measures 0.6 by hand and is NOT_MET",
      c3.verdict == "NOT_MET" and D(c3.measured) == D("0.6"), "%s %s" % (c3.verdict, c3.measured))
check("S3-C3 threshold is the sealed 1.10", c3.threshold == ">= 1.1", c3.threshold)
check("S3-C3 reports the frozen-trade figure beside it",
      c3.evidence["reconciliation"]["profit_factor_over_portfolio_trades"] is not None)
check("both figures agree when no position was trimmed",
      D(c3.evidence["reconciliation"]["profit_factor_over_portfolio_trades"]) == D(c3.measured))

# No losing episode: the raw null is preserved, never replaced by infinity.
wins_events = mixed_events[:4]
wins = replay(wins_events, [(1, "100.00"), (2, "100.00"), (3, "110.00"), (9, "1000.00"),
                            (10, "1000.00"), (11, "1030.00")], final_equity="1030.00")
wins_ledger = build_episode_ledger(wins)
c3w = G.condition_3_ra1(wins, wins_ledger, criteria)
check("no losing episode -> MET", c3w.verdict == "MET", c3w.verdict)
check("...with the raw null preserved, not a number", c3w.measured is None and
      c3w.evidence["profit_factor_raw"] is None)
check("...and the sealed treatment named in the note",
      "UNDEFINED_NO_LOSSES_TREATED_AS_MET" in c3w.note)
check("frozen profit_factor agrees that it is None", profit_factor(list(wins_ledger.pnls)) is None)


# ==================================================================================================
print("\n== 6. S3-C4: the counting identity, and the floor of 30 ==")

c4 = G.condition_4_ra1(mixed, mixed_ledger, criteria)
check("S3-C4 measures 3 and is NOT_MET against 30",
      c4.verdict == "NOT_MET" and c4.measured == "3", "%s %s" % (c4.verdict, c4.measured))
check("S3-C4 threshold is the sealed 30", c4.threshold == ">= 30", c4.threshold)
check("closed episodes and closed trades agree", c4.evidence["counts_agree"] is True)
check("the sealed exception is not invoked", c4.evidence["exception_invoked"] is False)

# Boundary: 29 fails, 30 passes.
for n, want in ((29, "NOT_MET"), (30, "MET")):
    evs = []
    for i in range(n):
        evs.append(("FILL", day(2 * i + 1), "b%d" % i, buy("AAA", "1", "100.00")))
        evs.append(("FILL", day(2 * i + 2), "s%d" % i, sell("AAA", "1", "101.00")))
    r = replay(evs, [(0, "100.00"), (2 * n + 2, "200.00")], final_equity="200.00")
    led = build_episode_ledger(r)
    v = G.condition_4_ra1(r, led, criteria)
    check("S3-C4 at %d closed episodes is %s" % (n, want),
          v.verdict == want and v.measured == str(n), "%s %s" % (v.verdict, v.measured))

raises("the counting identity is asserted, not assumed",
       lambda: G.condition_4_ra1(mixed, wins_ledger, criteria), DataIntegrityHalt,
       "counting_identity")


# ==================================================================================================
print("\n== 7. S3-C5: j1 is the largest multiple, j2 the largest SIGNED dollar P&L ==")

# Bases read off the curve at the close BEFORE each entry:
#   AAA entered d2 -> base = equity(d1)  = 100   -> multiple 1 + 10/100  = 1.10
#   BBB entered d10 -> base = equity(d9) = 1000  -> multiple 1 + 20/1000 = 1.02
#   CCC entered d12 -> base = equity(d11)= 500   -> multiple 1 - 50/500  = 0.90
bases = G.entry_equity_bases(mixed, mixed_ledger)
check("entry bases are the preceding session's close",
      [f"{b:f}" for b in bases] == ["100.00", "1000.00", "500.00"],
      str([f"{b:f}" for b in bases]))

c5 = G.condition_5_ra1(mixed, mixed_ledger, criteria)
check("j1 is BBB? no -- j1 is the largest multiple, AAA at 1.10",
      c5.evidence["j1_largest_equity_multiple"]["symbol"] == "AAA",
      c5.evidence["j1_largest_equity_multiple"]["symbol"])
check("j2 is BBB, the largest signed P&L (+20), NOT CCC whose abs is 50",
      c5.evidence["j2_largest_absolute_pnl"]["symbol"] == "BBB",
      c5.evidence["j2_largest_absolute_pnl"]["symbol"])
check("j1 and j2 are genuinely different episodes here", c5.evidence["j1_equals_j2"] is False)
# 1.10*1.02*0.90 = 1.0098 -> 0.0098 ; excluding AAA: 1.02*0.90 = 0.918 -> -0.082 (negative)
check("reconstructed total return is 0.0098 by hand",
      D(c5.evidence["reconstructed_total_return"]) == D("0.0098"),
      c5.evidence["reconstructed_total_return"])
check("S3-C5 is NOT_MET because removing j1 leaves -0.082",
      c5.verdict == "NOT_MET" and D(c5.evidence["j1_largest_equity_multiple"]["removed_return"]) == D("-0.082"),
      "%s %s" % (c5.verdict, c5.evidence["j1_largest_equity_multiple"]["removed_return"]))
check("the reconstruction gap is disclosed, not reconciled away",
      "reconstruction_gap" in c5.evidence and "equity_curve_total_return" in c5.evidence)

# Both removals positive -> MET.
met_events = [
    ("FILL", day(2), "a1", buy("AAA", "1", "100.00")),
    ("FILL", day(3), "a2", sell("AAA", "1", "110.00")),
    ("FILL", day(10), "b1", buy("BBB", "1", "100.00")),
    ("FILL", day(11), "b2", sell("BBB", "1", "120.00")),
    ("FILL", day(12), "c1", buy("CCC", "1", "100.00")),
    ("FILL", day(13), "c2", sell("CCC", "1", "105.00")),
]
met_curve = [(1, "100.00"), (2, "100.00"), (3, "110.00"), (9, "1000.00"), (10, "1000.00"),
             (11, "1020.00"), (12, "1020.00"), (13, "1025.00")]
met_r = replay(met_events, met_curve, final_equity="1025.00")
met_l = build_episode_ledger(met_r)
c5m = G.condition_5_ra1(met_r, met_l, criteria)
# multiples 1.10, 1.02, 1 + 5/1020 ; removing either winner leaves a positive product
check("S3-C5 MET when both removals stay positive", c5m.verdict == "MET", c5m.verdict)

one = replay([("FILL", day(2), "a1", buy("AAA", "1", "100.00")),
              ("FILL", day(3), "a2", sell("AAA", "1", "110.00"))],
             [(1, "100.00"), (3, "110.00")], final_equity="110.00")
c5o = G.condition_5_ra1(one, build_episode_ledger(one), criteria)
check("fewer than two closed episodes is NOT_EVALUABLE and fails",
      c5o.verdict == "NOT_EVALUABLE" and not c5o.satisfied, c5o.verdict)


# ==================================================================================================
print("\n== 8. S3-C6: attribution over episodes, inclusive at exactly 50% ==")

c6 = G.condition_6_ra1(mixed, mixed_ledger, plan, criteria)
# total = 10 + 20 - 50 = -20, not strictly positive
check("S3-C6 is NOT_EVALUABLE when total profit is not positive",
      c6.verdict == "NOT_EVALUABLE" and not c6.satisfied, c6.verdict)

c6w = G.condition_6_ra1(wins, wins_ledger, plan, criteria)
# AAA +10, BBB +20, total 30 -> BBB 0.666... > 0.50
check("S3-C6 NOT_MET at 2/3 concentration", c6w.verdict == "NOT_MET", c6w.verdict)
check("...the largest contributor is named", c6w.evidence["largest_contributor"] == "BBB",
      c6w.evidence["largest_contributor"])
check("...and the frozen-trade attribution is reported beside it",
      "pnl_by_instrument_over_portfolio_trades" in c6w.evidence["reconciliation"])

even = replay([("FILL", day(2), "a1", buy("AAA", "1", "100.00")),
               ("FILL", day(3), "a2", sell("AAA", "1", "110.00")),
               ("FILL", day(4), "b1", buy("BBB", "1", "100.00")),
               ("FILL", day(5), "b2", sell("BBB", "1", "110.00"))],
              [(1, "100.00"), (5, "120.00")], final_equity="120.00")
c6e = G.condition_6_ra1(even, build_episode_ledger(even), plan, criteria)
check("S3-C6 MET at exactly 50%: the predicate is <= 0.50, inclusive",
      c6e.verdict == "MET" and D(c6e.measured) == D("0.5"), "%s %s" % (c6e.verdict, c6e.measured))
check("S3-C6 applies unconditionally: the declared universe has 34 members",
      c6e.evidence["declared_instrument_count"] == 34)
check("...and applicability is decided by the DECLARED universe, not the 2 symbols traded",
      c6e.evidence["distinct_symbols_traded"] == 2)


# ==================================================================================================
print("\n== 9. S3-C7: zero matches nothing, NOT_RUN is not a pass ==")

rep = variants["G2-S3-RA1-V07"] if "G2-S3-RA1-V07" in variants else list(variants.values())[6]
required = G.neighbours_of(rep, criteria)
primary_pos = flat_result("0.20")

all_pos = [(m, flat_result("0.10")) for m in required]
c7 = G.condition_7_ra1(primary_pos, all_pos, criteria, variant=rep)
check("S3-C7 MET when every neighbour shares the sign", c7.verdict == "MET", c7.verdict)

flipped = [(m, flat_result("-0.10" if i == 0 else "0.10")) for i, m in enumerate(required)]
c7f = G.condition_7_ra1(primary_pos, flipped, criteria, variant=rep)
check("S3-C7 NOT_MET on one sign reversal", c7f.verdict == "NOT_MET", c7f.verdict)

zeroed = [(m, flat_result("0.00" if i == 0 else "0.10")) for i, m in enumerate(required)]
c7z = G.condition_7_ra1(primary_pos, zeroed, criteria, variant=rep)
check("S3-C7 NOT_MET on an exactly-flat neighbour: zero matches nothing",
      c7z.verdict == "NOT_MET", c7z.verdict)

primary_zero = flat_result("0.00")
c7pz = G.condition_7_ra1(primary_zero, all_pos, criteria, variant=rep)
check("...and a flat representative matches nothing either", c7pz.verdict == "NOT_MET", c7pz.verdict)

notrun = [(m, None if i == 0 else flat_result("0.10")) for i, m in enumerate(required)]
c7n = G.condition_7_ra1(primary_pos, notrun, criteria, variant=rep)
check("S3-C7 NOT_MET when a neighbour did not run", c7n.verdict == "NOT_MET", c7n.verdict)
check("...and the NOT_RUN neighbour is named",
      c7n.evidence["neighbours_not_run"] == [required[0].variant_id],
      str(c7n.evidence["neighbours_not_run"]))

subset = all_pos[:-1]
raises("a hand-picked neighbour subset is rejected",
       lambda: G.condition_7_ra1(primary_pos, subset, criteria, variant=rep), ConfigViolation,
       "grid position requires")
wrong = all_pos[:-1] + [(next(v for v in variants.values() if v not in required and v is not rep),
                         flat_result("0.10"))]
raises("a substituted non-neighbour is rejected",
       lambda: G.condition_7_ra1(primary_pos, wrong, criteria, variant=rep), ConfigViolation)


# ==================================================================================================
print("\n== 10. combination and the stage verdict ==")

evaluation = G.evaluate_representative_ra1(
    variant=rep, primary=mixed, neighbours=all_pos, criteria=criteria, ledger=mixed_ledger, plan=plan)
check("seven conditions were evaluated", len(evaluation["conditions"]) == 7,
      str(len(evaluation["conditions"])))
check("the representative is not admitted", evaluation["admitted"] is False)
check("the non-vacuity report is carried into the evaluation",
      evaluation["non_vacuity_check"]["single_leg_compared"] > 0)
check("evaluation is JSON-serialisable", isinstance(json.dumps(evaluation), str))

fail_v = G.stage_verdict_ra1([evaluation], criteria, representative_exists=True,
                             selection_note="probe")
check("FAIL when the representative fails a condition", fail_v["verdict"] == "FAIL")
check("...token is Attempt 2's fail token", fail_v["verdict_token"] == ours[1], fail_v["verdict_token"])
check("...route is REPRESENTATIVE_FAILED_AT_LEAST_ONE_CONDITION",
      fail_v["route"] == "REPRESENTATIVE_FAILED_AT_LEAST_ONE_CONDITION", fail_v["route"])

none_v = G.stage_verdict_ra1([], criteria, representative_exists=False,
                             selection_note="all eighteen recorded a shutdown")
check("FAIL when no representative exists", none_v["verdict"] == "FAIL")
check("...same token, different route", none_v["verdict_token"] == ours[1]
      and none_v["route"] == "NO_REPRESENTATIVE_EXISTS", none_v["route"])

passing = dict(evaluation, admitted=True)
pass_v = G.stage_verdict_ra1([passing], criteria, representative_exists=True, selection_note="probe")
check("PASS emits Attempt 2's pass token", pass_v["verdict_token"] == ours[0], pass_v["verdict_token"])
check("no verdict ever emits an Attempt 1 token",
      all(v["verdict_token"] not in (a1_pass, a1_fail) for v in (fail_v, none_v, pass_v)))
check("both withheld tokens are recorded on the verdict",
      set(pass_v["attempt_1_tokens_withheld"]) == {a1_pass, a1_fail})

raises("evaluating two candidates against Gate 3 is refused",
       lambda: G.stage_verdict_ra1([evaluation, evaluation], criteria, representative_exists=True,
                                   selection_note="x"), ConfigViolation, "section 7")
raises("an admitted candidate with no representative is refused",
       lambda: G.stage_verdict_ra1([passing], criteria, representative_exists=False,
                                   selection_note="x"), ConfigViolation, "cannot both be true")
raises("a representative with nothing evaluated is refused",
       lambda: G.stage_verdict_ra1([], criteria, representative_exists=True,
                                   selection_note="x"), ConfigViolation, "no candidate result")


# ==================================================================================================
print("\n== 11. neither frozen module was called ==")

import stockedge100.strategies.gate as G1  # noqa: E402
import stockedge100.strategies.g2_gate as A1  # noqa: E402

# A substring search cannot distinguish an import from a sentence in a docstring, and this file is
# full of sentences about the modules it must not call. Walk the AST instead: it reports exactly
# what is bound and exactly what is dereferenced, and nothing that is merely mentioned.
import ast  # noqa: E402

tree = ast.parse(pathlib.Path(G.__file__).read_text(encoding="utf-8"))
imported: dict[str, set[str]] = {}
plain_imports: set[str] = set()
for node in ast.walk(tree):
    if isinstance(node, ast.ImportFrom) and node.module:
        imported.setdefault(node.module, set()).update(a.name for a in node.names)
    elif isinstance(node, ast.Import):
        plain_imports.update(a.name for a in node.names)

attribute_reads = {
    "%s.%s" % (n.value.id, n.attr)
    for n in ast.walk(tree)
    if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
}

check("Attempt 1's g2_gate is not imported, in any form",
      "stockedge100.strategies.g2_gate" not in imported
      and "stockedge100.strategies.g2_gate" not in plain_imports,
      str(sorted(imported)))
from_gen1 = imported.get("stockedge100.strategies.gate", set())
check("exactly condition_1 and condition_2 are imported from Generation 1's gate",
      {n for n in from_gen1 if n.startswith("condition_")} == {"condition_1", "condition_2"},
      str(sorted(n for n in from_gen1 if n.startswith("condition_"))))
check("Generation 1's condition_5 is not bound anywhere", "condition_5" not in from_gen1)
check("Generation 1's condition_7 is not bound anywhere", "condition_7" not in from_gen1)
check("nor is any of condition_3/4/6",
      not ({"condition_3", "condition_4", "condition_6"} & from_gen1))
check("no gate function is reached by attribute access either",
      not any(a.endswith((".condition_3", ".condition_4", ".condition_5", ".condition_6",
                          ".condition_7", ".evaluate_representative", ".stage_verdict_g2"))
              for a in attribute_reads),
      str(sorted(a for a in attribute_reads if ".condition_" in a)))
check("the five reused Generation 1 helpers are the only other gate imports",
      from_gen1 - {"condition_1", "condition_2"}
      == {"CONCENTRATION_MAX", "MET", "NOT_APPLICABLE", "NOT_EVALUABLE", "NOT_MET",
          "ConditionVerdict", "_condition", "_sign", "_threshold", "check_thresholds_against_seal"},
      str(sorted(from_gen1)))

print("\n%s\npassed %d, FAILED %d\n" % ("=" * 60, PASSED, FAILED))
sys.exit(1 if FAILED else 0)
