"""Second README correction: the gap-attribution figure was alignment-dependent.

fill_forensics.py regressed the monthly return difference on the month-boundary
gap using LEAN's raw equity stamps and got corr=+0.67 / 43.9% of variance.
lag_check.py then showed LEAN's Strategy Equity series is stamped one day late
(best daily-return alignment is shift +1: corr +0.634 vs +0.556 at shift 0).
Redone on the aligned series the same regression gives corr=+0.34 and -2.4% of
variance -- i.e. the attribution does not survive, so it is not a finding.

What does survive alignment: the fill convention (a direct measurement from 726
order events), the drawdown gap, and the CAGR reconciliation.
"""
import pathlib

p = pathlib.Path("faber-lean/README.md")
txt = p.read_text(encoding="utf-8")

OLD_ATTR = """Regressing the monthly return
  difference on that gap gives corr = +0.67 and explains 43.9% of its variance (diff
  stdev 0.90pp -> 0.68pp once the gap is removed), so the handover is the largest
  single driver but not the whole story. LEAN is late into every de-risking move, so
  -24.70% is the more honest drawdown.
"""

NEW_ATTR = """LEAN is late into every de-risking move, so
  -24.70% is the more honest drawdown. The drawdown gap holds under either alignment
  of the two equity curves (-24.70% raw, -24.68% aligned; see below), so it is a real
  difference and not a plotting artifact.

  How much of the *month-to-month* return difference that one-day lag accounts for is
  **not** settled, and an earlier draft of this section overstated it. Regressed on
  LEAN's raw equity stamps the gap looked like corr = +0.67 and 43.9% of variance;
  redone on the day-aligned series the same regression gives corr = +0.34 and -2.4%
  of variance -- removing the gap makes the residual marginally worse. A number that
  flips that far under a one-day alignment choice is not evidence of anything, so no
  attribution figure is quoted here.
"""

OLD_VOL = "| annualised vol | 14.78% daily-ann, 12.13% monthly-ann | 12.30% | convention, not a gap |"
NEW_VOL = "| annualised vol | 14.78% daily-ann, 12.13% monthly-ann | 12.30% reported, 14.58% recomputed from the aligned curve | convention, not a gap |"

TAIL_ANCHOR = """LEAN also recorded 726 orders and 1.84% portfolio turnover, consistent with 3 slots
over 236 rebalances.
"""

TAIL_ADD = """
**LEAN's equity series is stamped one day late.** For a daily-resolution algorithm the
Strategy Equity chart samples after the bar it summarizes, and the stamps are not even
a single time of day (4:00 and 5:00 appear 7,171 times, 20:00 and 21:00 2,899 times).
Aligning by best daily-return correlation picks shift +1 (corr +0.634, vs +0.556
unshifted). Anything that compares the two curves day by day has to do that shift
first; anything that only reads endpoints or the drawdown minimum does not care.
Note the shift and the trading lag are not separable by this test -- shifting the curve
to maximise correlation can absorb a genuine one-day execution lag, which is exactly
why the attribution above is left open.
"""

for needle in (OLD_ATTR, OLD_VOL, TAIL_ANCHOR):
    if needle not in txt:
        raise SystemExit("anchor not found, aborting: %r" % needle[:70])

txt = txt.replace(OLD_ATTR, NEW_ATTR, 1)
txt = txt.replace(OLD_VOL, NEW_VOL, 1)
txt = txt.replace(TAIL_ANCHOR, TAIL_ANCHOR + TAIL_ADD, 1)

body = txt.encode("utf-8")
body.decode("utf-8")
p.write_bytes(body)
print("patched OK, %d bytes, non-ascii=%d" % (len(body), sum(1 for b in body if b > 127)))
