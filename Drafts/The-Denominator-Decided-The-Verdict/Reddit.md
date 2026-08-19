# I deleted one line from my risk architecture and returns went from +0.4% to +10.3%. Then I failed the gate on a condition whose denominator my own report names wrong — and on the denominator it names, I would have passed.

**Platform:** Reddit — r/algotrading (crosspost candidate: r/quant)
**Status:** DRAFT — not posted
**Series note:** third and final post on this rotation family. Same disclosure posture as the last two:
absolute development-window figures only, because this grid is now spent and the full table is in the
public decision record. No credentials, no validation reads, no holdout. Generation 2's holdout is dated
2026-08-01 → 2028-07-31 and does not exist yet in calendar time.

---

Last post ended on a question I couldn't answer from inside it:

> is a return-blind selection rule that has now chosen the worst row in the grid still doing something
> useful, or have I just proven it's uncorrelated with quality?

Attempt 2 had bolted a risk architecture onto 18 pre-registered rotation variants. It worked perfectly at
the thing it was for — 36 of 36 runs shut down in Attempt 1, 0 of 36 in Attempt 2 — and the representative
my return-blind rule selected earned **+0.42% over thirteen years**. Protection bought flatness.

So Attempt 3 changed two things, both disclosed before any code existed, both chosen from non-return
diagnostics only:

1. **RA3**: delete the −5%-from-peak de-risk tier. RA2's ladder was −5% → −8% → −10%; Generation 1's
   original ladder was 8% / 10%. The −5% tier was something I had *added*, and a 5% dip is a Tuesday. My
   throttle was running as low as 0.19× sizing with 3,166 sessions below full size on the variant that got
   picked. That's not risk management, that's being flat with extra steps.
2. **SEL-2**: replace "lowest turnover" as the selection rule with a neighborhood-stability score over
   four non-return quantities — fill count, ladder descents, lockout arms, stops filled — comparing each
   variant to its grid neighbours.

**I changed two things at once, so this attempt cannot attribute its result to either one.** I knew that
when I sealed it and did it anyway, because the alternative was two more attempts on a family I already
suspected was dead, each burning more multiplicity. That's a defensible trade and it's still a confound.
Everything below is one observation of a joint change.

## What happened

| | Attempt 1 (no RA) | Attempt 2 (RA2) | Attempt 3 (RA3 + SEL-2) |
|---|---|---|---|
| runs shut down | **36 / 36** | 0 / 36 | 0 / 36 |
| representative | none existed | `L12-K1-Q` | `L03-K2-Q` |
| base / stressed return | — | +0.42% / −0.08% | **+10.34% / +8.11%** |
| max drawdown | breached 15% | 13.97% / 14.20% | **9.94% / 9.93%** |
| gate conditions met | never evaluated | 3 of 7 | **6 of 7** |
| verdict | `NO_CANDIDATE` | `NO_CANDIDATE` | `NO_CANDIDATE` |

Three attempts, three different failure modes, same family: switched off, throttled into flatness, and
now — passing almost everything and dying on one condition.

## The tier I deleted was doing two opposite things

This is the part I did not predict. Removing the −5% tier lifted the middle and bottom of the grid: all
18 variants now finish positive, median +11.67%. But it made the grid's **best** variant worse.

| `L03-K1-MONTHLY` | under RA2 | under RA3 |
|---|---|---|
| base return | **+63.15%** | +53.41% |
| stressed return | +57.15% | +50.68% |
| max drawdown | 11.16% | 12.96% |

So the tier I removed on the theory that it was suppressing ordinary-market returns was, for the
strongest variant in the grid, net *helpful* — it was catching dips that variant would otherwise ride
down, and the drawdown got deeper without it. My reasoning for the change was right about the median and
wrong about the maximum, and if I'd only looked at the top row I'd have concluded the opposite.

## SEL-2 versus SEL-1, head to head, on the same runs

The interesting test is what the old rule would have done on the new grid. Under RA3, "lowest turnover"
picks `L12-K1-QUARTERLY` again — 195 fills, still a unique minimum, still the same variant it picked in
Attempt 2. That variant is now **dead last of 18 by return** (+1.48% / −0.08%).

SEL-2 picked `L03-K2-QUARTERLY` instead: instability score `0.215471404`, rank **11 of 18** by base
return.

Read that carefully, because there are two readings and I only get to claim the weaker one:

- **The weak claim, which I'll make:** SEL-2 stopped picking the worst row in the grid. Twice now the
  turnover tiebreak has landed on the single lowest-return variant, which is what you'd expect if low
  turnover mostly means low participation.
- **The strong claim, which I won't:** that SEL-2 detects quality. Rank 11 of 18 is exactly what a
  coin flip looks like. And the margin over the runner-up was `0.000048608` on a score of `0.2155` — a
  tie decided in the fifth decimal place. A rule that resolves at 5e-5 isn't measuring a real gap between
  those two variants; it's ordering noise deterministically. That's still better than ordering noise
  *negotiably*, which is what happens when I pick, but it isn't the same as knowing something.

## Six of seven

The representative met six of the seven sealed conditions:

- **S3-C1** return > 0 → +10.34% / +8.11% ✓
- **S3-C2** drawdown ≤ 15% → 9.94% / 9.93% ✓
- **S3-C3** profit factor ≥ 1.10 → 1.270 / 1.201 ✓
- **S3-C4** ≥ 30 closed trades → 62 / 62 ✓
- **S3-C5** best trade removed, still positive → +5.57% / +3.17% ✓
- **S3-C7** no shutdowns → 0 / 0 ✓
- **S3-C6** no instrument > 50% of profit → **0.7505 / 0.9772** ✗

`FAIL — STAGE_3_G2_ATTEMPT_3_NO_CANDIDATE`.

And before anyone gets excited about +10.34%: that's **thirteen years**, so 0.76% annualized, Sharpe 0.19.
It's a positive number and nothing more than that.

## The denominator

Here's the thing worth the post.

My research report explains S3-C6 in prose twice, and both times it says the condition measures one
instrument's share of "**gross profit**". The sealed criteria file — written before any of this ran,
byte-identical across two attempts' configs — says something different: contribution is that instrument's
episode P&L divided by **the sum over all closed episodes**. Net. The implementation matches the seal,
because the seal is what I wrote the code from: `total = sum(contributions.values())`.

Those aren't the same measurement, and on this run they aren't close:

| denominator | largest contributor's share | condition |
|---|---|---|
| net closed-episode P&L (sealed, executed) | **0.7505** base / 0.9772 stressed | **NOT MET** |
| gross profit (what the prose says) | 0.2413 base / 0.2532 stressed | MET |

**On the denominator my own report names, the gate passes.** On the denominator my own code enforces, it
fails. The two diverge that hard because 11 of the 24 instruments the strategy traded finished net-negative
(12 of 24 under cost stress) — the losers shrink the denominator, so one winner clears 50% of *net* almost
automatically while sitting at a quarter of gross.

Three things follow, and I want to be exact about which is which:

- **The verdict is correct.** The gate is decided by the sealed text, not by my paraphrase of it. The code
  and the seal agree. `FAIL` stands.
- **The report is wrong in two sentences, and I'm not fixing them.** That report is already hashed into an
  artifact manifest and a checksum record; editing it now would silently invalidate the integrity chain
  that makes the whole exercise worth anything. Disclosure in the session record is the repair. If you
  catch me quietly correcting a hashed artifact, that's a much bigger finding than a wrong noun.
- **I don't get to decide which one I meant.** I sealed "net", implemented "net", and *described* "gross" —
  so my mental model at writing time was gross and my machine has been measuring net for three attempts.
  Attempt 2's concentration figures of 2.72 and 6.88 are only possible on a net denominator. That was the
  tell, and I read straight past it for two sessions.

The deeper problem is that on a net denominator, S3-C6 is partly a **breadth** condition wearing a
concentration condition's name. It asks "is your book broadly profitable", not "is one name carrying you".
Both are reasonable things to require. They aren't the same thing — and a top-k rotation strategy with
k ∈ {1,2,3} holds at most three names at a time by construction, so it will fail a breadth test
structurally, however good the signal is. Whether that means the condition is wrong or the hypothesis
family is wrong is exactly the question I can't answer now without adapting the criteria after seeing the
result, which is the one move I've spent three sessions refusing to make.

So it stays sealed and the family stays dead.

## Multiplicity, stated plainly

Three disclosed adaptations on the same hypothesis family. **54 variants, 108 runs, no
multiple-comparisons correction applied.** The pre-registration carries a 1,507-character disclosure saying
this attempt was designed after two known failures, and the build refuses to emit a package unless that
exact string appears verbatim in every artifact referencing the result. That's the price of adapting: you
can't quote the number without quoting the caveat.

123 new tests this attempt, 1,265 total, 1,264 passing. The one red is deliberate and permanent — a sealed
contamination predicate that can never read zero again now that the module it authorized exists. Muting it
would be the violation.

## What I'd most like attacked

**Is a concentration condition on a net denominator measurable at all for a strategy that holds one to
three positions?** I think I sealed a condition a top-k rotation design cannot pass except by accident —
and I only noticed because it finally became the *last* thing standing between this family and a pass. For
two attempts it was hidden behind four other failures.

If that's right, the lesson isn't "rotation doesn't work". It's that I spent three sessions testing a
hypothesis against a gate with a structural incompatibility built into it, and my pre-registration
discipline — the thing I keep saying is the point — is what stopped me from discovering that by simply
moving the goalposts when they got in the way. The discipline held. It just held me against a wall of my
own construction.

Second thing, smaller and more practical: my prose said "gross" and my seal said "net" for three attempts,
across two generations of config, and every automated check I have passed the whole time. Checksums verify
that a file hasn't changed. They can't verify that the file's English agrees with the file's arithmetic. I
don't currently know how to test for that, and it's the failure mode that came closest to costing me a
wrong verdict.
