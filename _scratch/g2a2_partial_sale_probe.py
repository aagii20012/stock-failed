"""Measure what the frozen Portfolio records when a position is trimmed before it is closed.

Attempt 2's de-risk ladder and aggregate throttle both reduce an existing position without
closing it. Every trade-based Gate 3 condition (S3-C3, S3-C4, S3-C5, S3-C6) reads
Portfolio.trades. This script establishes, by measurement rather than by reading the source,
what that list contains after a buy / trim / exit sequence. ASCII output only.
"""
from __future__ import annotations

import datetime as dt
import pathlib
import sys
from decimal import Decimal

ROOT = pathlib.Path(__file__).resolve().parents[1] / "stockedge100"
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.backtest.costs import Fill  # noqa: E402
from stockedge100.backtest.portfolio import Portfolio  # noqa: E402

D = Decimal
S1 = dt.date(2010, 1, 4)
S2 = dt.date(2010, 2, 1)
S3 = dt.date(2010, 3, 1)


def fill(side: str, qty: str, price: str, cash: str) -> Fill:
    return Fill(
        symbol="XLK", side=side, quantity=D(qty),
        reference_price=D(price), effective_price=D(price),
        gross_notional=abs(D(cash)), commission=D("0.00"),
        sec_fee=D("0.00"), taf_fee=D("0.00"), cash_delta=D(cash),
    )


p = Portfolio(D("1000.00"), max_positions=3)
p.apply_fill(S1, fill("BUY", "1", "100.00", "-100.00"))
print("after entry:      trades=%d  qty=%s  basis=%s"
      % (len(p.trades), p.positions["XLK"].quantity, p.positions["XLK"].cost_basis))

p.apply_fill(S2, fill("SELL", "0.5", "120.00", "60.00"))
print("after 50%% trim:   trades=%d  qty=%s  basis=%s"
      % (len(p.trades), p.positions["XLK"].quantity, p.positions["XLK"].cost_basis))

p.apply_fill(S3, fill("SELL", "0.5", "90.00", "45.00"))
print("after full exit:  trades=%d" % len(p.trades))

t = p.trades[0]
print("\nrecorded Trade:   entry_cash=%s exit_cash=%s dividends=%s pnl=%s"
      % (t.entry_cash, t.exit_cash, t.dividends, t.pnl))

paid = D("100.00")
received = D("60.00") + D("45.00")
true_pnl = received - paid
print("true episode:     paid=%s received=%s pnl=%s" % (paid, received, true_pnl))

print("\ncash moved:       start=1000.00 end=%s  delta=%s" % (p.cash, p.cash - D("1000.00")))

print("\n--- findings ---")
print("A) a partial sale appends no Trade:                      %s"
      % ("CONFIRMED" if len(p.trades) == 1 else "NOT CONFIRMED"))
print("B) recorded pnl differs from the true episode pnl:       %s (recorded %s, true %s)"
      % ("CONFIRMED" if t.pnl != true_pnl else "NOT CONFIRMED", t.pnl, true_pnl))
print("C) the difference is a SIGN REVERSAL, not a rounding:    %s"
      % ("CONFIRMED" if (t.pnl < 0) != (true_pnl < 0) else "NOT CONFIRMED"))
print("D) the equity ledger is nonetheless correct:             %s (cash delta %s == true pnl %s)"
      % ("CONFIRMED" if (p.cash - D("1000.00")) == true_pnl else "NOT CONFIRMED",
         p.cash - D("1000.00"), true_pnl))

# The control: with no trim, the sealed Trade is exact. This is what must keep holding.
q = Portfolio(D("1000.00"), max_positions=3)
q.apply_fill(S1, fill("BUY", "1", "100.00", "-100.00"))
q.apply_fill(S3, fill("SELL", "1", "90.00", "90.00"))
print("E) with no trim the sealed Trade is exact:               %s (pnl %s == cash delta %s)"
      % ("CONFIRMED" if q.trades[0].pnl == q.cash - D("1000.00") else "NOT CONFIRMED",
         q.trades[0].pnl, q.cash - D("1000.00")))
