"""Apply the two pending LEAN cross-check corrections before the baseline tag.

1. README caveat 2: state which max-drawdown number to quote (-24.75%) and why the
   harness's -22.58% is biased one trading day early.
2. README retraction: the first-pass conclusions drawn from LEAN's raw Strategy
   Equity chart, listed explicitly so none of their numbers stand uncorrected.
3. Both copies of the algorithm: the schedule comment still asserted the fill
   timing the order events disproved.

Idempotent: refuses to write if an expected block is missing or already patched.
"""

import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README = os.path.join(ROOT, "faber-lean", "README.md")
ALGO = [
    os.path.join(ROOT, "faber-lean", "faber_sector_rotation.py"),
    os.path.join(ROOT, "faber-lean", "FaberSectorRotation", "main.py"),
]

CAVEAT2_OLD = """2. The harness trades at the signal month's close; LEAN trades one trading day
   later, at the close of the first trading day of the next month (market orders
   on daily data become MarketOnClose regardless of the scheduled time). Measured
   at -1.92 pp of max drawdown and -0.158 pp of CAGR, so LEAN is the more honest
   side of this one.
"""

CAVEAT2_NEW = """2. **Quote LEAN's -24.75% max drawdown, not the harness's -22.58%.** The harness
   trades at the signal month's close; LEAN trades one trading day later, at the
   close of the first trading day of the next month (market orders on daily data
   become MarketOnClose regardless of the scheduled time), so it is late into
   every de-risking move. A controlled rerun changing **only** the fill bar moves
   max drawdown by -1.92 pp (-22.63% -> -24.55%) and CAGR by -0.158 pp: that
   covers the -1.81 pp gap against the harness at 10 bps (-24.75% vs -22.94%) and
   most of the -2.17 pp gap against it at 0 bps (-24.75% vs -22.58%). The harness
   figure is optimistic by construction rather than more accurate, so LEAN is the
   honest side of this one and -24.75% is this strategy's max drawdown.
"""

RETRACT_OLD = """Two earlier claims in this section were wrong and are corrected above, both because they
were computed on the ragged raw equity stamps rather than the reconstruction: that the
volatility difference was a daily-vs-monthly annualisation convention (it is not -- on
identical formulas the two agree at 14.8%), and that the one-day handover explained 43.9%
of the month-to-month *return* difference (that figure fell to -2.4% under a one-day
re-alignment, so no attribution figure is quoted).
"""

RETRACT_NEW = """### Retracted from the first pass

Three conclusions reached before the reconstruction are **withdrawn**, and none of their
numbers should be quoted anywhere. Two of them came from comparing against the raw
Strategy Equity stamps described above; the third came from reading the schedule instead
of the order events:

| retracted claim | why it was wrong | what stands instead |
|---|---|---|
| The volatility gap is a daily-vs-monthly annualisation convention. | An artifact of the ragged sampling, not a convention difference. | On identical formulas the two agree: 14.86% vs 14.80%. |
| The one-day handover explains **43.9%** of the month-to-month return difference. | Measured against mis-aligned stamps; re-aligning by one day collapses it to -2.4%. | No attribution figure is quoted for the *return* difference. The *drawdown* gap is attributed, from the order events, above. |
| LEAN fills at the **next month's open + 30 min**. | Inferred from reading `time_rules.after_market_open` instead of from the order events. | All 726 fills are at close(D) of their own trading day, because market orders become MarketOnClose on daily data. |

The 43.9% and the open+30min fill are the two most likely to resurface from an old note
or an earlier draft. Neither is a measurement of anything.
"""

ALGO_OLD = """        # Rebalance once a month, shortly after the open. Signals use only
        # months that have already closed, so this is not look-ahead.
"""

ALGO_NEW = """        # Rebalance once a month. This time rule sets when the method runs, not
        # when the orders fill: on daily data LEAN converts market orders to
        # MarketOnClose, so every fill lands at that day's close -- verified
        # across all 726 fills of the 2007-2026 backtest. Signals use only
        # months that have already closed, so this is not look-ahead.
"""


def patch(path, pairs):
    with io.open(path, "r", encoding="utf-8", newline="") as fh:
        text = fh.read()
    original = text
    for old, new in pairs:
        if new in text:
            print("SKIP already patched: %s" % os.path.relpath(path, ROOT))
            continue
        if old not in text:
            print("FAIL block not found in %s:" % os.path.relpath(path, ROOT))
            print(repr(old[:80]))
            sys.exit(1)
        if text.count(old) != 1:
            print("FAIL block is not unique in %s" % os.path.relpath(path, ROOT))
            sys.exit(1)
        text = text.replace(old, new)
    if text == original:
        return 0
    with io.open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print("PATCHED %s" % os.path.relpath(path, ROOT))
    return 1


changed = 0
changed += patch(README, [(CAVEAT2_OLD, CAVEAT2_NEW), (RETRACT_OLD, RETRACT_NEW)])
for p in ALGO:
    changed += patch(p, [(ALGO_OLD, ALGO_NEW)])
print("files changed: %d" % changed)
