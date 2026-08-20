"""Correct the fill-mechanism claim in faber-lean/README.md.

The committed section says LEAN trades "~30 min after the next month's open".
fill_forensics.py measured all 726 order events: every fill equals close(D) of
its own trading day. Replace the inferred mechanism with the measured one, add
the holdings-integrity result, and disclose the correction in place.
"""
import pathlib

p = pathlib.Path("faber-lean/README.md")
txt = p.read_text(encoding="utf-8")

OLD_COUNT = "Two things the cross-check surfaced:"
NEW_COUNT = "Three things the cross-check surfaced:"

OLD = """- **The harness understates drawdown by 2.1pp.** LEAN trades ~30 min after the next
  month's open; the harness trades at the signal month's close. LEAN is therefore late
  into every de-risking move, and -24.70% is the more honest figure. Execution lag is a
  real cost, not a rounding difference.
"""

NEW = """- **The harness understates drawdown by 2.1pp, and the cause is a one-trading-day
  handover.** Measured from LEAN's own 726 order events rather than inferred: every
  fill matches the *close* of its own trading day (726/726 exact, median
  |fill / close(D) - 1| = 0.0e+00), because LEAN converts market orders to
  MarketOnClose on daily data. The schedule fires on the first trading day of the
  month, so LEAN trades at that day's close while the harness trades at the previous
  month's close -- exactly one trading day earlier. Regressing the monthly return
  difference on that gap gives corr = +0.67 and explains 43.9% of its variance (diff
  stdev 0.90pp -> 0.68pp once the gap is removed), so the handover is the largest
  single driver but not the whole story. LEAN is late into every de-risking move, so
  -24.70% is the more honest drawdown.

  An earlier version of this section said LEAN trades "~30 min after the next month's
  open". That was wrong: `after_market_open` sets when the *scheduled method* runs, not
  when the order fills. On daily data the fill lands at that same day's close.

- **Whole-share rounding never changed which assets were held.** Reconstructing every
  rebalance from the fills, realized holdings match the intended set in 227/227 months.
  Weight error is small -- L1 median 0.45%, worst 2.53% (2020-03) -- which is the
  expected floor from whole shares plus the 0.25% cash buffer, not a logic defect.
"""

for needle in (OLD_COUNT, OLD):
    if needle not in txt:
        raise SystemExit("anchor not found, aborting: %r" % needle[:60])

txt = txt.replace(OLD_COUNT, NEW_COUNT, 1).replace(OLD, NEW, 1)

# validate as utf-8 before writing (the failure mode from earlier this session)
body = txt.encode("utf-8")
body.decode("utf-8")
p.write_bytes(body)
print("patched OK, %d bytes" % len(body))
print("non-ascii bytes:", sum(1 for b in body if b > 127))
