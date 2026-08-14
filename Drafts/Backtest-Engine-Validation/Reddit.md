# My backtest engine passed 270 tests. The file certifying that had a bug in its own hash.

**Platform:** Reddit — r/algotrading (crosspost candidate: r/ExperiencedDevs for the digest half)
**Status:** DRAFT — not posted
**Contains no strategy and no performance figures.** Still zero strategies tested. The only numbers
here are engine-validation figures.

---

Follow-up to my earlier post about sealing data rules before downloading any data. This stage was
building the actual backtest engine, under one rule: **write down what "correct" means, hash it, and
only then write the code.** The acceptance spec records the field

```json
"engine_modules_present_at_seal_time": 0
```

measured, not asserted. So the hand-calculated fixtures the engine is checked against could not have
been reverse-engineered from the engine's own output, because there was no engine.

Four things that came out of it, the last of which is the reason I'm posting.

**1. A defect class list is worthless unless the standard is two-sided.** The spec declares twelve
error classes — look-ahead, same-close fill, split, dividend, delisting, stale price, cash, rounding,
fee, slippage, rejected order, duplicate order. A class counts as covered only if the **clean** engine
passes *and* the **mutated** engine gets caught. One-sided coverage is how you end up with a green
suite that proves your guards can't tell anything apart.

Two mutations are the ones a careless guard would sail through:

- **The split mutation is dataset-specific.** Last stage I measured that my provider returns
  already-split-adjusted OHLC. So the correct behaviour is that a split does **not** change the share
  count, and the guard has to fire on a series where it does. If I'd written the generic "did you
  apply the split?" test I'd have been testing the opposite of my own data.
- **A guard living inside the function it guards is removed by the same mutation that introduces the
  defect.** My slippage check started out inside the price function. Mutate the price function and
  the check goes with it — the test passes and proves nothing. The assertion now sits at the fill,
  downstream of the thing it checks.

**2. Look-ahead is worth testing empirically, not just structurally.** Structurally the market view
is constructed with a hard visibility bound and refuses any later session. Empirically: delete every
single bar after the run's end date — 6,437 of them — rerun, and require the trade digest and equity
digest to be byte-identical. Plus a companion test asserting the truncation *actually removed bars*,
because a truncation that deleted nothing passes beautifully against an engine that peeks.

**3. Reconcile a benchmark two ways that are forced to agree.** SPY total return computed as the
adjusted-close ratio, and again by explicit share accumulation that never touches an adjusted close.
Under the adjustment convention I measured last stage these are an arithmetic identity —
`adj_t = close_t × Π_{s>t}(1 − D_s/close_{s−1})` forces reinvestment at `close_{s−1} − D_s` — so any
gap is my arithmetic, not the market's. They agree to a relative difference of 2.2e-7 against the
1e-6 I'd sealed in advance, across 115 dividend events. The residual is accumulated decimal rounding.

Also: my hand-calculated fixtures are compared line by line — entry, mark, dividend, exit, each fee
component, final equity — not on final equity alone, which any two compensating errors will satisfy.

**4. The part worth your time: my integrity check had an integrity bug.**

The engine validation writes an evidence file containing a self-digest, plus a field describing what
that digest covers:

```json
"evidence_digest_covers": "every field of this file except generated_utc and evidence_digest"
```

After building the whole decision package I ran the verification I'd promised myself I'd run —
recompute the digest from the written file, following that description literally. It didn't match.

The writer was appending the coverage description *after* taking the digest. So the recorded digest
excluded three fields while the description named two. Every finding in the file was correct. What
was wrong is that the file **asserted a coverage it did not have** — which is precisely the class of
discrepancy the digest exists to expose, occurring in the digest itself.

Two things about this I keep chewing on:

**270 passing tests said nothing.** Not because the suite was lazy — it injects twelve defect classes
one at a time — but because no test recomputed the digest. The only thing that finds this is doing
the arithmetic the document claims you can do.

**The two-run stability check passed the whole time, and it was a weaker claim than I thought.** I
was rerunning the writer and confirming the digest was identical across different timestamps. That
does prove the findings depend on code and data only. It does *not* prove the digest covers what it
says it covers. Those are different properties and I'd been reading the first as evidence for the
second.

The fix is boring — one `finalize()` function whose entire job is to assemble every covered field
*before* hashing — plus three tests: recompute from the sealed body, vary only the timestamp and
require no movement, then tamper with each non-excluded field in turn and require movement. That last
one is the one I should have had from the start.

It cost a full regeneration of the stage's decision package, because the repair touched `src/` and
`tests/`, and both feed the content hash that identifies the repo state. The run log is append-only,
so the superseded run is still sitting there naming what replaced it. That's the intended behaviour
and it still stings.

**The generalisable version, for anyone building self-describing artifacts:** if your file says what
its hash covers, that sentence is part of what the hash covers. And a verification step you've
written down but never executed is not a verification step. Run the recomputation on the real file,
early — mine was cheap to fix before the package existed and expensive afterwards.

Running total: zero strategies tested, zero performance figures, 273 tests, one engine validated
inside twelve explicitly recorded limitations. Strategy work is the next stage, on the development
window only; the holdout is still sealed and has never been opened.

Happy to go into the defect class list, the cost model, or the fixture arithmetic if anyone wants it.
