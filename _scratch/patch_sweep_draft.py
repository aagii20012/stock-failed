"""Add the post-reconciliation update block to the unposted sweep draft."""

import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRAFT = os.path.join(ROOT, "Drafts", "Faber-Rotation-Zero-Of-48", "Reddit.md")

ANCHOR = """at a cost of ~135bps/yr of CAGR. That's a defensible trade! It is also a completely
different product from the one "momentum sector rotation" implies.
"""

ADDENDUM = ANCHOR + """
**Update, before anyone quotes those numbers back at me.** I since rebuilt the same
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


def main():
    with io.open(DRAFT, "r", encoding="utf-8", newline="") as fh:
        text = fh.read()
    if "Update, before anyone quotes" in text:
        print("SKIP already patched")
        return
    if text.count(ANCHOR) != 1:
        print("FAIL anchor missing or not unique (count=%d)" % text.count(ANCHOR))
        sys.exit(1)
    with io.open(DRAFT, "w", encoding="utf-8", newline="") as fh:
        fh.write(text.replace(ANCHOR, ADDENDUM))
    print("PATCHED sweep draft")


main()
