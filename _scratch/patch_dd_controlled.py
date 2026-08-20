"""Add the controlled fill-timing experiment to the drawdown bullet.

dd_attribution.py reruns the same engine twice changing ONLY the fill bar and
holding quantization, cash buffer and IB fees fixed. That is a controlled test
rather than the regression that was discarded, and it accounts for the gap.
"""
import pathlib

p = pathlib.Path("faber-lean/README.md")
txt = p.read_text(encoding="utf-8")

ANCHOR = """  schedule fires on the first trading day of the month, so LEAN trades one trading day
  after the harness's signal-month close and is late into every de-risking move. Note
  `time_rules.after_market_open` sets when the scheduled *method* runs, not when the
  order fills.
"""

ADD = """
  Confirmed by a controlled rerun that changes **only** the fill bar and holds the
  whole-share quantization, 0.25% cash buffer and IB fee model fixed: filling at
  close(D-1) (harness timing) gives -22.63%, filling at close(D) (LEAN timing) gives
  -24.55%. Timing alone is worth -1.92 pp of drawdown and -0.158 pp of CAGR, which
  accounts for the observed -1.81 pp gap. It is the same episode in every variant
  (peak 2010-04-23 -> trough 2010-08-26), so the comparison is apples to apples.
"""

if ANCHOR not in txt:
    raise SystemExit("anchor not found")

txt = txt.replace(ANCHOR, ANCHOR + ADD, 1)

# the discarded-attribution note refers only to month-to-month return variance;
# make that scope explicit now that the drawdown IS attributed.
OLD_NOTE = "of the month-to-month return difference (that figure fell to -2.4% under a one-day"
NEW_NOTE = "of the month-to-month *return* difference (that figure fell to -2.4% under a one-day"
txt = txt.replace(OLD_NOTE, NEW_NOTE, 1)

body = txt.encode("utf-8")
body.decode("utf-8")
p.write_bytes(body)
print("patched OK, %d bytes, non-ascii=%d" % (len(body), sum(1 for b in body if b > 127)))
