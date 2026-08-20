"""Shrink the sweep-draft update block: the detail already lives in the
mistakes and caveats sections, so the table only needs a pointer."""

import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRAFT = os.path.join(ROOT, "Drafts", "Faber-Rotation-Zero-Of-48", "Reddit.md")

OLD = """**Update, before anyone quotes those numbers back at me.** I since rebuilt the same
strategy in QuantConnect LEAN and reconciled the two engines against each other. The
signal logic matched *exactly* -- same 236 rebalances, same 708 slots, same 83 skips,
same per-sector breakdown -- so everything below about selection skill stands. Two of
the numbers in that table do not:

- **The drawdown is optimistic.** My harness trades at the signal month's close; LEAN
  trades one trading day later, because on daily data market orders become
  MarketOnClose. Isolating only that difference costs -1.9pp of max drawdown. The
  honest figure is **-24.75%**, not -22.6%. Being one bar early flatters you on exactly
  the moves the trend filter exists to catch.
- **The 10bps cost model is ~6.7x too harsh.** LEAN's actual commissions came to $4,248
  on $28.3M of traded notional -- 1.50bps. So the "net of 10bps" row over-charges by
  roughly 0.7pp of CAGR, and realistic is ~9.3%. The sweep gradient is unaffected (every
  config paid the same toll), but read "0 of 48 beat SPY" knowing SPY buy-and-hold pays
  almost no turnover cost, so that comparison was tilted against the strategy.
"""

NEW = """Two numbers in that table are known to be wrong in my favour, both found by rebuilding
the strategy in QuantConnect LEAN afterwards: **the real max drawdown is -24.75%**, not
-22.6% (my harness trades one bar early), and 10bps is ~6.7x harsher than LEAN's actual
commissions, so the net row is a floor rather than a best case. Details in the mistakes
and caveats sections below. The signal logic reconciled exactly across both engines --
same 236 rebalances, same 83 trend-filter skips -- so everything about selection skill
stands.
"""


def main():
    with io.open(DRAFT, "r", encoding="utf-8", newline="") as fh:
        text = fh.read()
    if NEW in text:
        print("SKIP already patched")
        return
    if text.count(OLD) != 1:
        print("FAIL block missing or not unique (count=%d)" % text.count(OLD))
        sys.exit(1)
    with io.open(DRAFT, "w", encoding="utf-8", newline="") as fh:
        fh.write(text.replace(OLD, NEW))
    print("PATCHED sweep draft (trimmed)")


main()
