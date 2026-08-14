# I pre-registered my backtest's data rules and made the computer enforce the seal

**Platform:** Reddit — r/algotrading (crosspost candidate: r/quant)
**Status:** DRAFT — not posted
**Contains no strategy, no performance figures, no credentials.** There is nothing to leak yet: the
project has not tested a single strategy.

---

Everyone here knows the backtest failure modes — survivorship bias, lookahead, adjusting your
universe until the equity curve behaves. The usual advice is "be disciplined about it." I wanted to
find out what happens if you refuse to rely on discipline at all and make the tooling refuse instead.

So before downloading a single price, I wrote down every data rule I intended to follow — provider,
exact request parameters, universe eligibility, 16 validation checks with their severities, the
train/validation/holdout split arithmetic — hashed the lot, and sealed it. The seal records this
field:

```json
"raw_data_files_present_at_seal_time": 0
```

That number is measured, not asserted. Every module that touches data goes through one loader, and
that loader re-verifies the sealed digests on the way in. Edit a byte of the spec, delete a sealed
file, or remove the seal itself, and it raises instead of running. I have a test for each of those
three cases. The point isn't that I can't cheat — I own the machine — it's that I can't cheat
*quietly*, and quiet is how this kind of thing actually happens.

**Three things that fell out of this that I didn't expect:**

**1. I had assumed the wrong thing about my own data.** I was about to write "provider returns
unadjusted OHLC" into the spec. Instead I made it a measurement: pull a symbol with two known splits
(AAPL, 7:1 in 2014 and 4:1 in 2020) and look at what the price actually does across the split date.
If OHLC were as-traded, the close-to-close step would be ~0.143 and ~0.25. It was 1.016 and 1.034 —
i.e. an ordinary day. The OHLC was already split-adjusted. If I'd written down my assumption I'd
have carried a wrong adjustment convention through everything downstream, and it would have shown up
as alpha somewhere.

The consequence is a real limitation, now on the record: I don't have as-traded price levels, so any
future rule involving tick size or whole-share sizing is a *missing input*, not something to
approximate.

**2. Survivorship bias was easier to narrow than to fix.** I have no point-in-time constituent
source. Rather than pretend a 2026-assembled stock list is valid over a 1993-start window, I
prospectively restricted the universe to ETFs and banned individual stocks outright for this
generation. That does not eliminate the bias — funds that launched and closed inside the window are
still invisible to me — so it's recorded as "narrowed, disclosed, and unquantified." Writing
"unquantified" and leaving it there was harder than it sounds. The temptation to estimate a number
you have no basis for is strong.

**3. A validation battery that has only seen clean data is untested.** My 16 checks all passed on
real data, which told me approximately nothing. So I wrote a second suite that builds synthetic
series on real exchange sessions and corrupts exactly one thing at a time: a phantom Saturday
session, a duplicated day, a high below the close, a split recorded but never applied, a split with
the wrong factor, a dividend that doesn't reconcile, a gap long enough to trip the run limit but
short enough to pass the fraction limit. Each test asserts that the specific check for that defect
fires — *at its sealed severity*, not at the severity I'd prefer in hindsight. Three clean controls
sit at the top so any failure below them is attributable to the injected defect rather than to my
test harness.

Every guard fired. That's a boring result and it's the one I wanted, because until you inject the
defect you have no evidence at all that a green check means anything.

**The part I'm proudest of is a failure I kept.** One check fails on the record. The reference symbol
I used for the split measurement was fetched over a window ending in 2021, so its final adjustment
factor isn't 1.0 — and one sealed check assumes the last row is the present. The check is right; my
window was the odd one out. The tempting fix is to amend the check, since the symbol isn't even in
the research universe. Instead the record says `sealed_check_amended: false`, the failure stays
visible, and it's classified as a scope gap in the pre-registration with the reasoning attached. A
gate you're willing to edit after seeing the result isn't a gate.

Holdout is sealed: 24 months, boundaries locked before any strategy exists, opened exactly once at
the end. If I peek, the lock file's boundaries won't match and the builder exits non-zero rather than
recomputing them.

Total output so far: zero strategies tested, zero performance figures, 140 tests, and a pile of
paperwork. From the outside that looks like nothing happened. I think it's the correct amount of
progress for this stage, and I suspect the reason so many backtests are wrong is that this stage
never happens at all.

Happy to go into the partition arithmetic or the check list if anyone wants the detail.
