"""Correct the unpublished Reddit draft: fill mechanism and the cost caveat.

The draft says LEAN "trades at the next month's open" (wrong: all 726 fills are
at the close of their own trading day) and calls 10 bps "optimistic" (wrong,
and inverted: LEAN's real commissions are ~1.5 bps of notional, so 10 bps is
~6.7x conservative). Both would go public if the draft is approved.

Read/write as utf-8 explicitly and validate before writing -- an earlier edit
in this session wrote cp1252 bytes into this file and corrupted it.
"""
import pathlib

p = pathlib.Path("Drafts/Faber-Rotation-Zero-Of-48/Reddit.md")
txt = p.read_text(encoding="utf-8")

OLD3 = """3. I trusted my own harness's drawdown. Cross-running the same logic through LEAN's
   engine gave **-24.7% instead of -22.6%** — because the harness trades at the signal
   month's close while LEAN trades at the next month's open, i.e. late into every
   de-risking move. If you backtest monthly strategies at month-end closes you are
   understating drawdown by a couple of points. (The upside: both implementations agreed
   on all 236 rebalances and all 83 trend-filter skips exactly, so the signal logic
   itself is verified.)
"""

NEW3 = """3. I trusted my own harness's drawdown. Cross-running the same logic through LEAN's
   engine gave **-24.7% instead of -22.6%**. The cause is one trading day: my harness
   fills at the signal month's close, while LEAN's `month_start` schedule fills at the
   close of the month's *first* trading day — on daily data LEAN turns market orders
   into MarketOnClose, so all 726 fills landed exactly on close(D) of their own day.
   (`after_market_open` sets when the scheduled *method* runs, not when the order
   fills — that tripped me up.) Rerunning with only the fill bar changed and everything
   else fixed moves max drawdown by -1.92pp, which accounts for the whole gap. If you
   backtest monthly strategies at month-end closes you are understating drawdown by
   about two points. (The upside: both implementations agreed on all 236 rebalances and
   all 83 trend-filter skips exactly, and daily returns correlate 0.9919, so the signal
   logic itself is verified.)
"""

OLD_CAV = "computed on adjusted levels); 10bps is an optimistic cost assumption; the 9-sector universe"
NEW_CAV = ("computed on adjusted levels); 10bps turned out to be ~6.7x *more* conservative than\nLEAN's actual commissions of ~1.5bps of notional, so the net figures above are a floor\nrather than a best case; the 9-sector universe")

for needle in (OLD3, OLD_CAV):
    if needle not in txt:
        raise SystemExit("anchor not found: %r" % needle[:60])

txt = txt.replace(OLD3, NEW3, 1).replace(OLD_CAV, NEW_CAV, 1)

body = txt.encode("utf-8")
body.decode("utf-8")  # validate BEFORE writing
p.write_bytes(body)
print("patched OK, %d bytes" % len(body))
