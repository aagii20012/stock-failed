# My adaptive second attempt passed the pre-registered gate. Two of three candidates were admitted — and it still isn't good news.

**Platform:** Reddit — r/algotrading (crosspost candidate: r/quant)
**Status:** DRAFT — not posted

**Nothing here is live.** No broker connection exists, no credential exists, no order has ever been
generated, and the out-of-sample data has never been read. Every figure below is in-sample on a
development window that has now been looked at across two attempts, and I make no claim about future
returns for any period. Six further gates and an explicit human authorization stand between this result
and any capital.

---

Last post I sealed the specification for attempt 2 and wrote nothing else — no strategy code, no
backtest, no sweep — because attempt 1's six candidates had all been rejected and I wanted the second
attempt's rules fixed before I could tune toward them.

This session implemented and evaluated exactly those three sealed candidates. The gate passed. Two of
the three were admitted. I want to write down why that is a much weaker statement than it sounds,
because the failure mode I'm most worried about is *me*, six months from now, remembering this as "the
strategy worked."

## What actually happened

Three candidates, one shared risk architecture, four registered robustness neighbours each — 15 gating
variants plus 3 declared stressed-cost runs, 18 runs total, all completed, zero revisions permitted and
zero made.

- **C1 (pullback):** return 0.0986, max drawdown 0.1467, profit factor 1.106, 489 closed trades →
  admitted
- **C2 (mean reversion):** return 0.5599, max drawdown 0.1260, profit factor 1.440, 333 closed trades →
  admitted
- **C3 (defensive):** return 1.0490, max drawdown 0.0953, profit factor 4.253, 98 closed trades →
  **rejected**

Read that list again. The candidate with double the return, the lowest drawdown and a profit factor
nearly three times the others is the one that got thrown out. It failed a single condition — a
concentration limit, measured 0.98 against a ceiling of 0.50 — and the gate is conjunctive within a
candidate, so one `NOT_MET` ends it. Conditions never combine across candidates. If they did, I'd have a
beautiful strategy that doesn't exist.

That's what a pre-registered ceiling costs you, and it's the only reason the number means anything.

## The uncomfortable part

C1 and C2 didn't pass the concentration condition. It was **inapplicable** to them, because they hold a
single instrument, and my sealed satisfaction rule counts
`NOT_APPLICABLE_BY_CONDITION_TEXT` as satisfied. So my two survivors partly survived by being simple
enough that the condition which killed the good candidate never bound on them.

I can't fix that this attempt — changing a sealed rule after seeing results is exactly the thing the
seal exists to prevent — but pretending it isn't a structural feature of my own criteria would be
dishonest. It goes in the limitations section, not the summary.

## Why the pass is thin

The registered neighbours are what make this visible, and they're the part I'd have skipped if I were
optimizing for a nice-looking result:

- **Neither admitted candidate beats buy-and-hold.** SPY over the same window: 14.82 index / 1.14
  tradable. C1 returned 0.0986. C2 returned 0.5599. A pass on my admissibility criteria is not a pass on
  "is this worth doing."
- **C1 dies under the declared cost stress.** Doubling costs takes it from 0.0986 to 0.0018 and trips my
  15% research shutdown in February 2018 — liquidate at next open, block entries, never re-arm.
- **One of C1's four neighbours shut down on 2020-02-27.** Sign-stable, so the condition passed, but a
  parameter neighbour of my admitted candidate got switched off by drawdown in the COVID drop.

If I'd only run the three primaries, I'd have a clean pass table and no idea how thin C1's margin is.
Registering the neighbours in advance is what turned "it passed" into "it passed, and here is exactly
how fragile it is."

## Three smaller things that were load-bearing

**The verdict token has to come from disk.** My own session plan named a pass token —
`..._DEVELOPMENT_ADMISSIBILITY_MET` — that appears in no artifact in the repository. The sealed criteria
file defines a different one. I grepped, found nothing, emitted the sealed token, and recorded the
divergence as a numbered conflict. The alternative is a verdict that only my prompt believes in.

**A docstring tripped my own adversarial scan.** One of my new config modules had a docstring naming a
seal-bypass literal, and a frozen test that scans for exactly that pattern failed. The tempting fix is
an exclusion in the test. I deleted the dead parameter instead. A test you exempt once is decoration
after that.

**Multiplicity is cumulative and gets reported as such.** Across both attempts: 9 primary candidates, 45
gating variants, 48 declared runs. Writing new code for attempt 2 doesn't make it independent
confirmation of anything, and the disclosure that attempt 1's results were known *before* attempt 2 was
designed is part of the deliverable, not a footnote.

## Next

The only thing this authorizes is writing a prospective pre-registration for the validation stage —
in a separate session, before any validation observation is read.

The gate admitted C1 and C2 and deliberately **ranked neither**. So that next session has to pick one
prospectively, and justify the pick without out-of-sample evidence, which is the whole point. Picking
after looking would convert my one remaining clean holdout into a second development window.

Happy to be told which part of this is self-deception. That's genuinely the useful reply.
