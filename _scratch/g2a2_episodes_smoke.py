"""Adversarial smoke for the Attempt 2 episode ledger (`backtest/g2_episodes_ra1.py`).

Discipline, unchanged from the engine and strategy harnesses: **no expected value below is copied
from the module under test.** Each one is either

  * quoted from `config/generation_2/g2_gate_criteria_ra1.json` (G2A2-CONFLICT-18's own probe
    numbers and the evaluation_integrity_rules), or
  * produced by the FROZEN `Portfolio` replaying the same fills, or
  * computed here from the cash arithmetic by hand.

The centrepiece is that the frozen module is not mocked. Every fixture applies its fills to a real
`stockedge100.backtest.portfolio.Portfolio` and hands the resulting `Portfolio.trades` to the ledger
as the thing to reconcile against. A test that reconciled the ledger against a hand-written trade
list would be checking my arithmetic twice and the frozen recorder not at all.

ASCII only: the console is cp1252.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys
import traceback
from decimal import Decimal

ROOT = pathlib.Path(__file__).resolve().parents[1] / "stockedge100"
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.backtest.costs import Fill  # noqa: E402
from stockedge100.backtest.engine import BacktestResult, FillRecord  # noqa: E402
from stockedge100.backtest.errors import DataIntegrityHalt, InvariantViolation  # noqa: E402
from stockedge100.backtest.metrics import profit_factor  # noqa: E402
from stockedge100.backtest.orders import BUY, SELL  # noqa: E402
from stockedge100.backtest.portfolio import Portfolio  # noqa: E402

import stockedge100.backtest.g2_episodes_ra1 as L  # noqa: E402

PASSED = 0
FAILED = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if ok:
        PASSED += 1
        print("  ok   %s" % label)
    else:
        FAILED += 1
        print("  FAIL %s %s" % (label, detail))


def halts(label: str, thunk, fragment: str = "") -> None:
    """The call must raise DataIntegrityHalt -- rule 8's 'halts evaluation'."""
    global PASSED, FAILED
    try:
        thunk()
    except DataIntegrityHalt as exc:
        if fragment and fragment not in str(exc):
            FAILED += 1
            print("  FAIL halts: %s -- raised but message lacks %r: %s" % (label, fragment, exc))
        else:
            PASSED += 1
            print("  ok   halts: %s" % label)
    except Exception as exc:  # noqa: BLE001
        FAILED += 1
        print("  FAIL halts: %s -- wrong exception %s: %s" % (label, type(exc).__name__, exc))
    else:
        FAILED += 1
        print("  FAIL halts: %s -- no exception" % label)


D = Decimal
CRITERIA = json.loads(
    (ROOT / "config/generation_2/g2_gate_criteria_ra1.json").read_text(encoding="utf-8")
)
CONFLICT_18 = [c for c in CRITERIA["conflicts_found"] if c["id"] == "G2A2-CONFLICT-18"][0]
RULES = CRITERIA["evaluation_integrity_rules"]


# -- fixtures --------------------------------------------------------------------------------------


def day(n: int) -> dt.date:
    """Session n of a synthetic January. Only ordering matters to the ledger."""
    return dt.date(2020, 1, n)


def buy(symbol: str, quantity: str, price: str, fees: str = "0.00") -> Fill:
    """A zero-slippage buy. cash_delta is negative and already includes the fees."""
    q, p, f = D(quantity), D(price), D(fees)
    gross = (q * p).quantize(D("0.01"))
    return Fill(
        symbol=symbol,
        side=BUY,
        quantity=q,
        reference_price=p,
        effective_price=p,
        gross_notional=gross,
        commission=f,
        sec_fee=D("0.00"),
        taf_fee=D("0.00"),
        cash_delta=-(gross + f),
    )


def sell(symbol: str, quantity: str, price: str, fees: str = "0.00") -> Fill:
    q, p, f = D(quantity), D(price), D(fees)
    gross = (q * p).quantize(D("0.01"))
    return Fill(
        symbol=symbol,
        side=SELL,
        quantity=q,
        reference_price=p,
        effective_price=p,
        gross_notional=gross,
        commission=f,
        sec_fee=D("0.00"),
        taf_fee=D("0.00"),
        cash_delta=gross - f,
    )


def replay(events, *, starting_cash="10000.00", max_positions=3, label="PROBE"):
    """Apply `events` to the FROZEN Portfolio and package them as a BacktestResult.

    `events` is a list of ("FILL", session, order_id, Fill) or ("DIV", session, symbol, cash).
    The returned result carries the frozen module's own trade list, so the ledger is reconciled
    against the real recorder rather than against my expectation of it.
    """
    portfolio = Portfolio(D(starting_cash), max_positions=max_positions)
    fills: list[FillRecord] = []
    dividends: list[dict[str, str]] = []
    for kind, session, a, b in events:
        if kind == "FILL":
            portfolio.apply_fill(session, b)
            fills.append(FillRecord(session=session, order_id=a, fill=b))
        elif kind == "DIV":
            portfolio.record_dividend(session, a, D(b))
            dividends.append(
                {
                    "session": session.isoformat(),
                    "symbol": a,
                    "amount_per_share": "0.00",
                    "quantity": "0",
                    "cash_credited": f"{D(b):f}",
                }
            )
        else:
            raise AssertionError(kind)
    return portfolio, BacktestResult(
        label=label,
        scenario="BASE",
        symbols=("AAA", "BBB"),
        start=day(1),
        end=day(28),
        equity_curve=[],
        fills=fills,
        rejections=[],
        trades=list(portfolio.trades),
        dividend_events=dividends,
        stale_marks=0,
        shutdown_session=None,
        starting_equity=D(starting_cash),
        final_cash=portfolio.cash,
        final_equity=portfolio.cash,
        open_positions=[],
        cost_model={},
    )


# ==================================================================================================
print("\n== 1. the seal's own probe: recorded and true P&L with opposite signs ==")

# Quoted from G2A2-CONFLICT-18.established_by, not from the module:
#   "A buy of 1 unit at 100.00, a 50 percent trim at 120.00 and a final exit at 90.00 produced
#    exactly one recorded Trade with entry_cash 50.000, exit_cash 45.00 and pnl -5.000, while the
#    account's cash rose by 5.00."
for token in ("entry_cash 50.000", "exit_cash 45.00", "pnl -5.000", "cash rose by 5.00"):
    check("seal states %r" % token, token in CONFLICT_18["established_by"])

probe_events = [
    ("FILL", day(2), "o1", buy("AAA", "1", "100.00")),
    ("FILL", day(3), "o2", sell("AAA", "0.5", "120.00")),
    ("FILL", day(4), "o3", sell("AAA", "0.5", "90.00")),
]
pf, probe = replay(probe_events)

check("frozen recorder appended exactly one Trade", len(probe.trades) == 1, str(len(probe.trades)))
t = probe.trades[0]
check("frozen entry_cash is the seal's 50.000", t.entry_cash == D("50.000"), f"{t.entry_cash:f}")
check("frozen exit_cash is the seal's 45.00", t.exit_cash == D("45.00"), f"{t.exit_cash:f}")
check("frozen pnl is the seal's -5.000", t.pnl == D("-5.000"), f"{t.pnl:f}")
cash_change = pf.cash - D("10000.00")
check("account cash actually rose by 5.00", cash_change == D("5.00"), f"{cash_change:f}")
check("recorded and true P&L have opposite signs", (t.pnl < 0) and (cash_change > 0))

ledger = L.build_episode_ledger(probe)
check("ledger built one episode", len(ledger.episodes) == 1)
ep = ledger.episodes[0]
check("episode is closed", ep.closed)
check("episode has two sale legs", ep.sale_leg_count == 2, str(ep.sale_leg_count))
check("episode entry_cash is the whole 100.00 paid", ep.entry_cash == D("100.00"), f"{ep.entry_cash:f}")
check("episode exit_cash sums both legs to 105.00", ep.exit_cash == D("105.00"), f"{ep.exit_cash:f}")
check("episode pnl equals the true cash change", ep.pnl == cash_change, f"{ep.pnl:f}")
check("trimmed proceeds are the dropped 60.00", ep.trimmed_proceeds == D("60.00"),
      f"{ep.trimmed_proceeds:f}")
check("closing leg is the last one", ep.closing_leg.session == day(4) and ep.closing_leg.closing)
check("non-closing leg is not marked closing", ep.sale_legs[0].closing is False)

r = ledger.reconciliation
check("counts agree (1 == 1)", r.counts_agree and r.closed_episodes == 1)
check("no single-leg episode was comparable", r.single_leg_compared == 0, str(r.single_leg_compared))
check("so the reconciliation is VACUOUS (rule 9)", r.vacuous)
check("and reconciled is therefore false", r.reconciled is False)
check("pnl_discrepancy is +10.00", r.pnl_discrepancy == D("10.00"), f"{r.pnl_discrepancy:f}")
check("multi_leg_episodes counted", r.multi_leg_episodes == 1)
check("max_sale_legs reported", r.max_sale_legs == 2)


# ==================================================================================================
print("\n== 2. rule 8's reduction property: single-leg episodes ARE the frozen Trade ==")

# "The same probe confirmed that with no trim the recorded Trade is exact."
check("seal claims exactness without a trim",
      "with no trim the recorded Trade is exact" in CONFLICT_18["established_by"])

single_events = [
    ("FILL", day(2), "o1", buy("AAA", "1", "100.00", fees="0.01")),
    ("FILL", day(5), "o2", sell("AAA", "1", "130.00", fees="0.02")),
    ("FILL", day(6), "o3", buy("BBB", "2", "50.00")),
    ("FILL", day(9), "o4", sell("BBB", "2", "40.00")),
]
pf2, single = replay(single_events)
led2 = L.build_episode_ledger(single)
r2 = led2.reconciliation
check("two closed episodes, two frozen trades", (r2.closed_episodes, r2.closed_trades) == (2, 2))
check("both were compared", r2.single_leg_compared == 2, str(r2.single_leg_compared))
check("no mismatches", r2.mismatches == ())
check("not vacuous", r2.vacuous is False)
check("reconciled", r2.reconciled is True)
check("pnl_discrepancy is exactly zero", r2.pnl_discrepancy == 0, f"{r2.pnl_discrepancy:f}")
check("no trimmed proceeds", r2.total_trimmed_proceeds == 0)

for i, (epi, tr) in enumerate(zip(led2.closed_episodes, single.trades)):
    for field in ("entry_cash", "exit_cash", "dividends", "pnl"):
        check("episode %d %s == frozen Trade" % (i, field),
              getattr(epi, field) == getattr(tr, field),
              "%s vs %s" % (getattr(epi, field), getattr(tr, field)))
check("rule 8 names exactly these four figures",
      all(f in RULES[7] for f in ("entry_cash", "exit_cash", "dividends", "pnl")))
check("module's RECONCILED_FIELDS matches that list",
      set(L.RECONCILED_FIELDS) == {"entry_cash", "exit_cash", "dividends", "pnl"})
check("entry_costs is NOT reconciled (frozen stores ZERO there)",
      "entry_costs" not in L.RECONCILED_FIELDS and single.trades[0].entry_costs == 0)

# hand-computed, independent of both the ledger and the frozen recorder
check("AAA pnl is 130.00-0.02-100.01 = 29.97",
      led2.closed_episodes[0].pnl == D("29.97"), f"{led2.closed_episodes[0].pnl:f}")
check("BBB pnl is 80.00-100.00 = -20.00",
      led2.closed_episodes[1].pnl == D("-20.00"), f"{led2.closed_episodes[1].pnl:f}")


# ==================================================================================================
print("\n== 3. closing order is the frozen append order, with symbols interleaved ==")

inter_events = [
    ("FILL", day(2), "a1", buy("AAA", "1", "100.00")),
    ("FILL", day(3), "b1", buy("BBB", "1", "100.00")),
    ("FILL", day(4), "b2", sell("BBB", "1", "110.00")),   # BBB closes FIRST
    ("FILL", day(5), "a2", sell("AAA", "1", "90.00")),    # AAA closes SECOND
]
pf3, inter = replay(inter_events)
led3 = L.build_episode_ledger(inter)
check("frozen trade order is BBB then AAA",
      [t.symbol for t in inter.trades] == ["BBB", "AAA"], str([t.symbol for t in inter.trades]))
check("closed_episodes follows the same order",
      [e.symbol for e in led3.closed_episodes] == ["BBB", "AAA"])
check("close_index is 0,1 in that order",
      [e.close_index for e in led3.closed_episodes] == [0, 1])
check("open_index preserves ENTRY order (AAA first)",
      [e.symbol for e in sorted(led3.episodes, key=lambda e: e.open_index)] == ["AAA", "BBB"])
check("reconciled", led3.reconciliation.reconciled)
check("pnl_by_symbol sums per instrument",
      led3.pnl_by_symbol() == {"AAA": D("-10.00"), "BBB": D("10.00")},
      str(led3.pnl_by_symbol()))
check("pnls follow closing order (+10 then -10)",
      list(led3.pnls) == [D("10.00"), D("-10.00")], str(led3.pnls))


# ==================================================================================================
print("\n== 4. dividends: attributed by replaying the engine's own ordering ==")

div_events = [
    ("FILL", day(2), "a1", buy("AAA", "1", "100.00")),
    ("DIV", day(3), "AAA", "2.00"),
    ("DIV", day(4), "AAA", "3.00"),
    ("FILL", day(5), "a2", sell("AAA", "1", "100.00")),
    ("FILL", day(6), "a3", buy("AAA", "1", "100.00")),    # a SECOND episode in the same symbol
    ("DIV", day(7), "AAA", "7.00"),
    ("FILL", day(8), "a4", sell("AAA", "1", "100.00")),
]
pf4, divs = replay(div_events)
led4 = L.build_episode_ledger(divs)
check("two episodes in one symbol", len(led4.episodes) == 2)
check("first episode took 5.00 of dividends",
      led4.closed_episodes[0].dividends == D("5.00"), f"{led4.closed_episodes[0].dividends:f}")
check("second episode took 7.00",
      led4.closed_episodes[1].dividends == D("7.00"), f"{led4.closed_episodes[1].dividends:f}")
check("frozen recorder agrees on both (it pops per close)",
      [t.dividends for t in divs.trades] == [D("5.00"), D("7.00")],
      str([f"{t.dividends:f}" for t in divs.trades]))
check("reconciled", led4.reconciliation.reconciled)
check("every dividend event was attributed",
      sum(e.dividends for e in led4.episodes) == D("12.00"))
check("pnl includes dividends: 100-100+5 = 5.00",
      led4.closed_episodes[0].pnl == D("5.00"), f"{led4.closed_episodes[0].pnl:f}")

# The ambiguous case a date-interval attribution gets wrong: one episode closes and the next opens
# on the SAME session. The engine credits dividends before it executes fills, so the credit belongs
# to the episode that is about to close. The frozen recorder is the oracle here.
same_day = [
    ("FILL", day(2), "a1", buy("AAA", "1", "100.00")),
    ("DIV", day(5), "AAA", "4.00"),                       # credited before the session's fills
    ("FILL", day(5), "a2", sell("AAA", "1", "100.00")),   # closes episode 0
    ("FILL", day(5), "a3", buy("AAA", "1", "100.00")),    # opens episode 1, same session
    ("FILL", day(9), "a4", sell("AAA", "1", "100.00")),
]
pf5, sd = replay(same_day)
led5 = L.build_episode_ledger(sd)
check("same-session close-then-open: frozen gives the dividend to the FIRST",
      [t.dividends for t in sd.trades] == [D("4.00"), D("0.00")],
      str([f"{t.dividends:f}" for t in sd.trades]))
check("ledger agrees (dividends replayed before fills)",
      [e.dividends for e in led5.closed_episodes] == [D("4.00"), D("0.00")],
      str([f"{e.dividends:f}" for e in led5.closed_episodes]))
check("and it reconciles, which is the real proof", led5.reconciliation.reconciled)
check("both episodes carry the same entry_session/exit_session shape",
      (led5.closed_episodes[0].exit_session == day(5)
       and led5.closed_episodes[1].entry_session == day(5)))


# ==================================================================================================
print("\n== 5. folding: a buy into an open position does not start a second episode ==")

fold_events = [
    ("FILL", day(2), "a1", buy("AAA", "1", "100.00")),
    ("FILL", day(3), "a2", buy("AAA", "1", "150.00")),   # adds to the SAME position
    ("FILL", day(9), "a3", sell("AAA", "2", "140.00")),
]
pf6, fold = replay(fold_events)
led6 = L.build_episode_ledger(fold)
check("frozen recorder produced ONE trade for two buys", len(fold.trades) == 1)
check("ledger produced ONE episode too", len(led6.episodes) == 1)
check("with two entry legs", len(led6.episodes[0].entry_legs) == 2)
check("multi_entry_episodes reports it", led6.reconciliation.multi_entry_episodes == 1)
check("entry_cash is the sum of both buys (250.00)",
      led6.episodes[0].entry_cash == D("250.00"), f"{led6.episodes[0].entry_cash:f}")
check("entry_session is the FIRST buy", led6.episodes[0].entry_session == day(2))
check("single_leg still true (one sale leg)", led6.episodes[0].single_leg)
check("so it reconciles against the frozen Trade exactly", led6.reconciliation.reconciled)
check("counting_identity holds: one closing event, one trade",
      "the same event" in [c for c in CRITERIA["conditions"] if c["id"] == "S3-C4"][0]
      ["counting_identity"])


# ==================================================================================================
print("\n== 6. open positions are not closed, not counted, and have no P&L ==")

open_events = [
    ("FILL", day(2), "a1", buy("AAA", "1", "100.00")),
    ("FILL", day(3), "b1", buy("BBB", "1", "100.00")),
    ("FILL", day(4), "b2", sell("BBB", "0.5", "120.00")),   # trimmed but NOT closed
    ("FILL", day(5), "a2", sell("AAA", "1", "110.00")),     # closed
]
pf7, mix = replay(open_events)
led7 = L.build_episode_ledger(mix)
check("one closed episode, one open", (len(led7.closed_episodes), len(led7.open_episodes)) == (1, 1))
check("frozen recorded one trade", len(mix.trades) == 1)
check("open episode has close_index None", led7.open_episodes[0].close_index is None)
check("open episode exit_session is None", led7.open_episodes[0].exit_session is None)
check("a trimmed-but-open position is NOT counted (S3-C4)",
      led7.reconciliation.closed_episodes == 1)
check("S3-C4 says exactly that",
      "trimmed but not closed is still open and is not counted"
      in [c for c in CRITERIA["conditions"] if c["id"] == "S3-C4"][0]["measurement"])

try:
    _ = led7.open_episodes[0].pnl
except InvariantViolation as exc:
    check("pnl on an open episode raises", "still open" in str(exc))
else:
    check("pnl on an open episode raises", False, "it returned a number")

check("to_json reports pnl null for the open one",
      led7.open_episodes[0].to_json()["pnl"] is None)
check("to_json reports a pnl string for the closed one",
      led7.closed_episodes[0].to_json()["pnl"] == "10.00")
check("pnls only covers closed episodes", len(led7.pnls) == 1)
check("pnl_by_symbol only covers closed episodes", set(led7.pnl_by_symbol()) == {"AAA"})


# ==================================================================================================
print("\n== 7. rule 8 halts; it does not report a discrepancy ==")

check("rule 8 says a failure halts evaluation",
      "halts evaluation rather than being reported as a discrepancy" in RULES[7])

# (a) count mismatch: hand the ledger a truncated trade list
bad_count = L.EpisodeLedger  # keep the name bound; we mutate the result, not the module
_, probe_b = replay(single_events)
probe_b.trades = probe_b.trades[:1]
halts("closed-count mismatch", lambda: L.build_episode_ledger(probe_b), "same event")

# (b) value mismatch on a single-leg episode: corrupt one frozen figure
_, probe_c = replay(single_events)
probe_c.trades[0].exit_cash = probe_c.trades[0].exit_cash + D("1.00")
halts("single-leg value mismatch", lambda: L.build_episode_ledger(probe_c), "exit_cash")

# (c) the two lists describing different closing events
_, probe_d = replay(single_events)
probe_d.trades = [probe_d.trades[1], probe_d.trades[0]]
halts("trade list out of closing order", lambda: L.build_episode_ledger(probe_d),
      "not\ndescribing the same closing events".replace("\n", " "))

# (d) a sale with no episode open -- the ledger is not replaying the same fills
_, probe_e = replay(single_events)
probe_e.fills.append(FillRecord(session=day(12), order_id="x", fill=sell("AAA", "1", "10.00")))
halts("sale with no open episode", lambda: L.build_episode_ledger(probe_e), "long-only")

# (e) an oversell that would take the replayed quantity negative
_, probe_f = replay(single_events)
probe_f.fills.insert(1, FillRecord(session=day(3), order_id="x", fill=sell("AAA", "2", "10.00")))
halts("oversell takes replay quantity negative", lambda: L.build_episode_ledger(probe_f),
      "negative")

# (f) a dividend credited with no position open
_, probe_g = replay(single_events)
probe_g.dividend_events.append(
    {"session": day(12).isoformat(), "symbol": "AAA", "amount_per_share": "0.00",
     "quantity": "0", "cash_credited": "1.00"}
)
halts("dividend with no episode open", lambda: L.build_episode_ledger(probe_g), "open positions")

# (g) an unknown side
_, probe_h = replay(single_events)
weird = buy("AAA", "1", "10.00")
object.__setattr__(weird, "side", "SHORT")
probe_h.fills.append(FillRecord(session=day(12), order_id="x", fill=weird))
halts("unknown fill side", lambda: L.build_episode_ledger(probe_h), "unknown fill side")

check("the clean fixture still builds after all that mutation",
      L.build_episode_ledger(replay(single_events)[1]).reconciliation.reconciled)


# ==================================================================================================
print("\n== 8. rule 9: no vacuous pass, and the counts are reported ==")

check("rule 9 requires compared > 0 before asserting agreement",
      "greater than zero before asserting that they agree" in RULES[8])
check("rule 9 requires the compared count to be reported",
      "reports the compared count alongside the mismatch count" in RULES[8])

empty_pf, empty = replay([])
led_empty = L.build_episode_ledger(empty)
re = led_empty.reconciliation
check("a run with no fills yields no episodes", led_empty.episodes == ())
check("counts agree trivially (0 == 0)", re.counts_agree)
check("but it is vacuous", re.vacuous)
check("and reconciled is FALSE", re.reconciled is False)
check("it did not raise -- 0 closed episodes is a measured FAIL for S3-C4, not a crash",
      re.closed_episodes == 0)
check("S3-C4 calls zero a measured value that fails",
      "a count of zero, which is a measured value that fails the predicate"
      in [c for c in CRITERIA["conditions"] if c["id"] == "S3-C4"][0]["not_evaluable_treatment"])
payload = re.to_json()
check("to_json reports single_leg_compared", payload["single_leg_compared"] == 0)
check("to_json reports the mismatch list", payload["mismatches"] == [])
check("to_json reports vacuous", payload["vacuous"] is True)
check("to_json reports reconciled", payload["reconciled"] is False)


# ==================================================================================================
print("\n== 9. what the gate will read: profit factor via the FROZEN metrics function ==")

# S3-C3: "The frozen metrics function is not modified and is still called for the reconciliation
# figure. Both numbers are reported: profit factor over the episode ledger, which gates, and profit
# factor over Portfolio.trades, which does not."
#
# The fixture is chosen so the two figures land on OPPOSITE SIDES of the 1.10 threshold, because a
# pair that merely differs numerically would not show what conflict 18 is about. Every number below
# is hand-computed from the cash arithmetic:
#   AAA  buy 1 @ 100.00                  -> basis 100.00, cash -100.00
#        trim 0.5 @ 160.00               -> cash +80.00; frozen rewrites basis to 100.00 * 0.5 = 50.000
#        close 0.5 @ 90.00               -> cash +45.00
#        episode  125.00 - 100.00 = +25.00        frozen  45.00 - 50.000 = -5.000
#   BBB  buy 1 @ 100.00, sell 1 @ 80.00  -> both agree at -20.00 (single leg)
#   episode PF = 25.00 / 20.00 = 1.25          frozen PF = 0 / 25.000 = 0
# So the same run is a winner under the ledger and has no winning trade at all under the recorder.
mixed = [
    ("FILL", day(2), "a1", buy("AAA", "1", "100.00")),
    ("FILL", day(3), "a2", sell("AAA", "0.5", "160.00")),   # trim: 80.00 the frozen recorder drops
    ("FILL", day(4), "a3", sell("AAA", "0.5", "90.00")),    # close
    ("FILL", day(5), "b1", buy("BBB", "1", "100.00")),
    ("FILL", day(9), "b2", sell("BBB", "1", "80.00")),      # a clean loser, single leg
]
pf8, mx = replay(mixed)
led8 = L.build_episode_ledger(mx)
episode_pnls = list(led8.pnls)
frozen_pnls = [t.pnl for t in mx.trades]
check("episode AAA pnl is 125-100 = +25.00", episode_pnls[0] == D("25.00"), f"{episode_pnls[0]:f}")
check("frozen AAA pnl is 45-50 = -5.000", frozen_pnls[0] == D("-5.000"), f"{frozen_pnls[0]:f}")
check("BBB agrees at -20.00 in both", episode_pnls[1] == frozen_pnls[1] == D("-20.00"))
pf_ledger = profit_factor(episode_pnls)
pf_frozen = profit_factor(frozen_pnls)
check("episode PF is 25.00/20.00 = 1.25", pf_ledger == D("1.25"), str(pf_ledger))
check("frozen-trade PF is 0 (no winning trade at all)", pf_frozen == 0, str(pf_frozen))
check("the gating figure clears 1.10 and the reconciliation figure does not",
      pf_ledger >= D("1.10") > pf_frozen, "%s vs %s" % (pf_ledger, pf_frozen))
check("total trimmed proceeds are the 80.00 dropped",
      led8.reconciliation.total_trimmed_proceeds == D("80.00"),
      f"{led8.reconciliation.total_trimmed_proceeds:f}")
check("episode total is 5.00, frozen total is -25.000, discrepancy 30.00",
      (led8.reconciliation.episode_pnl_total,
       led8.reconciliation.frozen_trade_pnl_total,
       led8.reconciliation.pnl_discrepancy) == (D("5.00"), D("-25.000"), D("30.00")),
      "%s / %s / %s" % (led8.reconciliation.episode_pnl_total,
                        led8.reconciliation.frozen_trade_pnl_total,
                        led8.reconciliation.pnl_discrepancy))
check("pnl_discrepancy equals that drop minus the basis rewrite",
      led8.reconciliation.pnl_discrepancy
      == led8.reconciliation.episode_pnl_total - led8.reconciliation.frozen_trade_pnl_total)
check("S3-C3 asks for both numbers",
      "profit factor over the episode ledger, which gates"
      in [c for c in CRITERIA["conditions"] if c["id"] == "S3-C3"][0]["attempt_2_note"])

# S3-C6's numerator/denominator
by_symbol = led8.pnl_by_symbol()
total = sum(episode_pnls)
check("pnl_by_symbol covers every traded symbol", set(by_symbol) == {"AAA", "BBB"})
check("per-symbol sums to the total", sum(by_symbol.values()) == total, f"{total:f}")


# ==================================================================================================
print("\n== 10. the frozen module was not touched ==")

import ast  # noqa: E402
import hashlib  # noqa: E402

FROZEN = (
    "src/stockedge100/backtest/portfolio.py",
    "src/stockedge100/backtest/metrics.py",
    "src/stockedge100/backtest/engine.py",
    "src/stockedge100/backtest/costs.py",
    "src/stockedge100/strategies/g2_rotation.py",
    "src/stockedge100/backtest/g2_engine.py",
)
# Attempt 1's own run record, at stockedge100/runs/ -- `runs/` is outside the repo_state_id
# patterns, which is exactly why it is a safe place to have pinned these digests.
run_record = ROOT / "runs/SE100-R-20260815T070924Z.json"
recorded = json.loads(run_record.read_text(encoding="utf-8"))["code_hashes"]
check("the Attempt 1 run record pins code hashes", len(recorded) > 100, str(len(recorded)))
compared = 0
for rel in FROZEN:
    check("%s is pinned by Attempt 1" % rel.rsplit("/", 1)[-1], rel in recorded)
    if rel not in recorded:
        continue
    compared += 1
    digest = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
    check("unchanged: %s" % rel, recorded[rel] == digest,
          "%s vs %s" % (recorded[rel][:12], digest[:12]))
check("every frozen module named above was actually compared", compared == len(FROZEN),
      str(compared))

# And the new module does not mutate anything it was handed. A substring search cannot tell a read
# from a write, so walk the AST: no attribute is ever an assignment target, and the frozen-dataclass
# escape hatch never appears.
tree = ast.parse((ROOT / "src/stockedge100/backtest/g2_episodes_ra1.py").read_text(encoding="utf-8"))


def root_name(node: ast.AST) -> str:
    while isinstance(node, (ast.Attribute, ast.Subscript)):
        node = node.value
    return node.id if isinstance(node, ast.Name) else "<expr>"


def mutations(scope: ast.AST) -> tuple[list[str], list[str]]:
    """(attribute-assignment roots, .append receiver roots) inside `scope`."""
    stores, appends = [], []
    for node in ast.walk(scope):
        if isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            for tgt in (node.targets if isinstance(node, ast.Assign) else [node.target]):
                for sub in ast.walk(tgt):
                    if isinstance(sub, ast.Attribute) and isinstance(sub.ctx, ast.Store):
                        stores.append(root_name(sub))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in ("append", "extend", "pop", "insert", "clear", "sort"):
                appends.append(root_name(node.func.value))
    return stores, appends


accumulator = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "_OpenEpisode"]
check("_OpenEpisode is the module's one mutable type", len(accumulator) == 1)
acc_nodes = set(map(id, ast.walk(accumulator[0]))) if accumulator else set()

all_stores, all_appends = mutations(tree)
acc_stores, acc_appends = (mutations(accumulator[0]) if accumulator else ([], []))
# Outside the accumulator: the only receivers may be locals the module built itself.
LOCALS = {"stream", "frozen", "mismatches", "episodes", "legs", "sales", "credits", "entries",
          "merged", "out", "result_episodes", "open_episodes"}
outside_stores = [s for s in all_stores if s not in ("self", "episode")]
outside_appends = [a for a in all_appends if a not in LOCALS and a != "self"]
check("attribute assignment only ever targets `self` or `episode`",
      outside_stores == [], str(outside_stores[:4]))
# ...and `episode` is only ever bound to the accumulator, so those two are accumulator writes.
episode_binds = [ast.unparse(n.value) for n in ast.walk(tree)
                 if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == "episode" for t in n.targets)]
check("`episode` is only ever bound from _OpenEpisode or a lookup of one",
      all(b.startswith("_OpenEpisode(") or b.startswith("open_by_symbol") or b.startswith("open.")
          or ".get(" in b or "[" in b for b in episode_binds), str(episode_binds))
slots = [ast.literal_eval(n.value) for n in ast.walk(accumulator[0]) if isinstance(n, ast.Assign)
         and any(isinstance(t, ast.Name) and t.id == "__slots__" for t in n.targets)]
check("the mutated field is declared in _OpenEpisode.__slots__",
      slots and "quantity" in slots[0], str(slots))
check("all of them are inside _OpenEpisode", sorted(set(acc_stores)) == ["self"],
      str(sorted(set(acc_stores))))
check("the accumulator is the only thing outside it that is mutated",
      all(a in LOCALS or a == "episode" for a in outside_appends), str(outside_appends))
FROZEN_INPUTS = {"result", "trade", "trades", "fill", "record", "portfolio", "position", "curve"}
check("no frozen input is ever an assignment target",
      not (set(all_stores) & FROZEN_INPUTS), str(set(all_stores) & FROZEN_INPUTS))
check("no frozen input is ever appended to / popped / sorted in place",
      not (set(all_appends) & FROZEN_INPUTS), str(set(all_appends) & FROZEN_INPUTS))

calls = [ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)]
check("object.__setattr__ / setattr never appear",
      not [c for c in calls if c == "setattr" or c.endswith("__setattr__")],
      str([c for c in calls if "setattr" in c]))
check("it subclasses nothing at all",
      [ast.unparse(b) for n in ast.walk(tree) if isinstance(n, ast.ClassDef) for b in n.bases] == [])

dataclasses_seen = {n.name: [ast.unparse(d) for d in n.decorator_list]
                    for n in tree.body if isinstance(n, ast.ClassDef)}
for name, decs in dataclasses_seen.items():
    if name == "_OpenEpisode":
        check("_OpenEpisode uses __slots__, not @dataclass", not any("dataclass" in d for d in decs))
        continue
    check("%s is a FROZEN dataclass" % name,
          any("dataclass" in d and "frozen=True" in d for d in decs), str(decs))


print("\n" + "=" * 90)
if FAILED:
    print("SMOKE DIRTY -- %d passed, %d FAILED" % (PASSED, FAILED))
    sys.exit(1)
print("SMOKE CLEAN -- %d passed, 0 failed" % PASSED)
