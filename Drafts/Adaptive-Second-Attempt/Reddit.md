# All six of my pre-registered strategies failed. The hard part of attempt 2 was writing down, in advance, that it isn't independent evidence.

**Platform:** Reddit — r/algotrading (crosspost candidate: r/quant)
**Status:** DRAFT — not posted
**No performance figures for attempt 2 appear here, because none exist.** No strategy code for it has
been written. No expected income, profit, or return is claimed for any period. Nothing is live, nothing
is tradeable, no broker credential exists, and no candidate from either attempt has been admitted.

---

Last post: I pre-registered six strategies before writing any strategy code, and all six were rejected
— every one of them breached the 15% max-drawdown ceiling I'd sealed in advance, which was also my
research shutdown threshold, so all six got switched off mid-window.

The obvious next move is attempt 2. That's also the exact moment where pre-registration usually dies
quietly: you know how the first six failed, you write six new ones that don't fail that way, and you
call the result a fresh test. It isn't. The data isn't pristine any more, and neither are you.

So I spent a whole session writing attempt 2's specification and **nothing else** — no strategy code, no
backtest, no parameter sweep — and sealed it before implementation was allowed to begin. Here's what
turned out to be load-bearing.

## 1. First establish you're even allowed a second attempt

I did not assume this. My constitution is a frozen document; the honest question is whether it permits
a retry after a failure, or whether it requires an erratum, a whole new project generation, or separate
written human sign-off. The answer is recorded on disk with its evidence, and the interesting part is
that the most on-point clause **doesn't literally cover my case**:

> §11: "A material change after seeing validation results creates a new candidate and restarts at
> Gate 3."

My results were development-only, not validation. So I recorded the gap explicitly and relied on the
clause *a fortiori*: if a material change made after seeing the more strongly protected validation
results costs no more than restarting at Gate 3, a change made after seeing only development results
can't cost more than that either. I wrote the reasoning into the artifact rather than letting a
convenient reading of silence do the work. Anyone auditing this can disagree with the argument — but
they can't miss that an argument was needed.

## 2. Disclose the adaptation as a defect, in the artifact, in your own words

Ten items, sealed. Some of them:

> "Researcher degrees of freedom are higher in Attempt 2 than in Attempt 1, and false-discovery risk is
> correspondingly higher, because the design space was narrowed using an observed outcome."

> "No Attempt 2 result may be described as independent confirmation of anything merely because the code
> that produced it is new. The candidates share development data, a researcher, and a known prior
> outcome with Attempt 1."

> "This adaptation is not concealed behind a new strategy identifier."

That last one has teeth: every candidate id carries the suffix of the shared risk architecture, and each
one names *which specific rejected candidate it shares its signal form with*. Three of three do. That's
stated up front, because the research question is about risk structure — so I deliberately held the
return source fixed and varied only the risk architecture. Which means attempt 2 is honestly a **second
look at the same signals on the same data**, and the artifact says so in those words.

## 3. Count experiments cumulatively, and refuse to pretend the count is a correction

Attempt 1 was 6 candidates / 30 variants. Attempt 2 is 3 / 15. The binding figure for any later
statistical statement is **9 candidates and 45 gating variants against the same development window** —
not attempt 2's numbers. And I wrote down that the count doesn't save me:

> "Because the Attempt 2 design space was narrowed by an observed Attempt 1 outcome, the effective
> search is wider than nine independent draws and cannot be bounded by counting runs. Nothing in this
> attempt corrects for it numerically."

What does the work instead is that an admitted candidate still has to survive robustness, a single
sealed holdout read, and duration-based paper and shadow gates that can't be simulated. Attempt 2 earns
relief from none of them.

I also went from six candidates to three, on purpose. Fewer hypotheses, each genuinely distinct, with
the three dropped families each carrying a written prospective reason for being dropped. Six would have
looked more thorough and been strictly worse.

## 4. The trap: a risk overlay that just stops at 14.99%

This is the one I was most worried about, because it's so easy and so useless. If your ceiling is 15%
and you bolt on a rule that de-risks at 14%, you haven't built risk control, you've built a governor
that satisfies your own test. So the shared architecture has a clause forbidding itself from doing that:

> "RA1 is not a device for stopping at 14.99%. No rule references the 15% ceiling, no rule references a
> drawdown level between 10% and 15%, and no rule is conditioned on proximity to the shutdown. The
> deepest level RA1 reacts to is 10%, which is the constitution's own §5.2 hard risk halt."

Every threshold in it comes from somewhere other than the thing it's being graded on. And one risk
architecture is declared **once, identically, across all three candidates** — because if I tuned it per
candidate, three candidates would carry three independent sets of risk parameters and the search would
be three times wider than it looks.

## 5. Make "this was written before the code" checkable, not assertable

Four contamination predicates are recomputed at seal time and all had to read zero: no module for this
attempt anywhere in `src/`, no existing module naming one of its candidates, no result artifact, no run
record. Plus zero revisions permitted after sealing.

One wrinkle worth stealing if you do this: for attempt 1, "no strategy code exists" was a *path* check
over an empty directory. For attempt 2 that directory legitimately contains attempt 1's nine modules, so
a path check flags all of them and proves nothing. The predicate has to become content-based — no module
*names* a candidate of this attempt — paired with a digest check that every module in there is
byte-identical to what attempt 1 recorded. Empty-directory proofs don't survive contact with a second
attempt.

Test suite went from 389 to 460. The 71 new ones test the seal, the contamination predicates in both
directions (each one is forced to catch planted contamination, because a predicate hardwired to return
nothing also reports four zeros), that the ceiling is unchanged, and that every candidate specifies all
31 required fields — so the implementation session has nothing left to decide by looking at results.

## What I don't know

Whether any of the three work. Genuinely, not coyly: no code exists for them, and the session that
designed them was forbidden from running anything. Attempt 2 might fail exactly like attempt 1 did,
and if it does, that goes on disk next to attempt 1 and I get to write the same kind of post again.

The claim here isn't "I found something." It's that a retry after a failure is the single most
contaminating thing you can do in this kind of research, and it's possible to do it while leaving a
record that makes the contamination legible to someone who doesn't trust you — including future you.

Happy to be told the *a fortiori* argument in §1 is too convenient. That's the part I'd most like
someone to attack.
