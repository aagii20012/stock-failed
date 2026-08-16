# I asked last time whether my drawdown tripwire was a strategy filter or just a beta detector. I built the experiment that answers it. It's a beta detector.

**Platform:** Reddit — r/algotrading (crosspost candidate: r/quant)
**Status:** DRAFT — not posted
**Series note:** direct sequel to "the tripwire killed all eighteen." Same disclosure posture: absolute
development-window figures, because this grid is dead too and the full table is in the public decision
record. No credentials, no validation reads, no holdout. Generation 2's holdout is dated 2026-08-01 →
2028-07-31 and does not exist yet in calendar time.

---

Last post: 18 pre-registered rotation variants, all 18 tripped a 15% research-shutdown tripwire in both
their base and stressed runs, my return-blind selection rule got an empty set, and the gate conditions
were never evaluated. I ended it by saying the thing I most wanted attacked was whether that tripwire
was doing any work at all:

> is a drawdown tripwire that fires during a market-wide crash a strategy filter at all, or just a beta
> detector? [...] Filtering on "did you breach 15%" over a window containing 2008, 2018 Q4 and 2020
> arguably selects for nothing except low net exposure.

I ran the experiment. If the tripwire is a beta detector, then attacking net exposure directly — without
touching the signal at all — should make the shutdowns disappear. That is exactly what happened, and the
result is more damning than I expected.

## The setup: fix exposure, don't touch the signal

Same 34-ETF universe, same 18-variant grid (lookback 3/6/12 × top-k 1/2/3 × monthly/quarterly), same
cost model, same next-open execution, same development window ending 2021-07-31. **The ranking logic is
byte-for-byte the same idea.** What I added was a risk architecture, frozen in the pre-registration and
deliberately **not grid-searched** — five mechanisms with hand-picked constants, so that nothing here is
a fitted parameter:

- aggregate gross exposure ceiling: 50%
- volatility target: 10% annualized
- per-position stop: 8%, evaluated at the close, exit at the next open
- de-risk ladder off the equity high-water mark: −5% → 75% scale, −8% → 50%, −10% → 25%, re-normalizing
  on recovery
- re-entry lockout: 10 sessions after a ladder descent

Then the same pre-registered, return-blind selection rule: zero research-shutdown events, tiebreak
lowest turnover.

**This pre-registration was written after I saw Attempt 1's failure.** That's an adaptation and it makes
this attempt weaker evidence than a clean prospective test. I wrote an 842-character disclosure saying
so and the build refuses to produce a package unless that exact string appears verbatim in every
artifact that references the result. Five carriers. If I'm going to adapt after seeing an outcome, the
minimum price is that nobody can quote the result without also quoting the adaptation.

## Result: 36 of 36 shutdowns became 0 of 36

| | Attempt 1 | Attempt 2 |
|---|---|---|
| runs shut down | **36 / 36** | **0 / 36** |
| shutdown dates | 18 distinct, 2008-10-24 → 2020-03-12 | none exist |
| representative | none — step 1 emptied the set | selected at step 2 |

Not "fewer." Zero. The thing that annihilated the entire previous grid — including through October 2008
and March 2020 — stopped firing completely, and the signal never changed. The ladder descended 1,605
times across the 36 runs and blocked 6,133 attempted re-entries while lockouts were active. Drawdown,
the condition that killed Attempt 1, became the condition Attempt 2 passes most comfortably: **13.97%
base / 14.20% stress against a 15% ceiling.**

So: beta detector. You can satisfy that tripwire without improving a strategy in any respect, purely by
holding less. I built an elaborate machine for rejecting things on market exposure and called it a risk
control. That question from last post is answered and the answer is not flattering.

## And it bought nothing

The selection rule reached step 2 for the first time in this generation and picked
`L12-K1-QUARTERLY` on lowest turnover — 189 total fills, a unique minimum, so the lexicographic
tiebreak was never needed. Its performance over thirteen years:

**+0.42% base. −0.08% stressed.** Not annualized — total.

It missed four of seven gate conditions:

- **S3-C1** total return > 0 — stressed run is negative
- **S3-C3** profit factor ≥ 1.10 — got 1.073 / 1.030
- **S3-C5** remove the single best trade, return still > 0 — goes to −1.1% / −1.9%
- **S3-C6** no instrument > 50% of profit — got **2.72 and 6.88**

That last one deserves a beat. A concentration *ratio above 1.0* means one instrument's profit exceeds
the strategy's entire net profit — the rest of the book is net negative and one name is carrying it. At
6.88 under cost stress, this is a single-symbol strategy wearing a universe as a costume, which is the
**exact** pathology that made me open Generation 2 in the first place. I added a whole risk architecture
and rediscovered my original disease.

Verdict on disk: `FAIL — STAGE_3_G2_ATTEMPT_2_NO_CANDIDATE`.

## The part where the rule earns its keep

`L03-K1-MONTHLY` returned **+63.15%** with a 1.93 profit factor. It was sitting right there in the same
table as the variant I selected. It was never eligible to be chosen, because the rule doesn't read
returns — every variant had zero shutdowns, so the tiebreak went to turnover, and the winner was one of
the *worst* rows in the grid.

I want to be precise about what that does and doesn't prove. It does **not** prove the rule is wise. It
proves the rule is not negotiable by me, which is the only property I can actually verify. The version
of me looking at +63.15% and a dead attempt has an obvious argument available — *turnover is a poor
proxy, we should be selecting on risk-adjusted return* — and that argument arrives strictly after I've
seen which variant it would promote. Same asymmetry as last time. The tell is always the timing.

## What I'm now fairly confident of

The relative-strength rotation family, over this universe and this window, fails Gate 3 **both
unprotected and protected**. Attempt 1 failed by being switched off. Attempt 2 failed by being throttled
into flatness. Two different failure modes, same family, and the risk architecture moved the failure
without removing it. That is information about the hypothesis family, not about the risk architecture —
and it's the kind of negative result that's cheap now and expensive later.

Cumulative multiplicity across both attempts is 36 variants and 72 runs with no multiple-comparisons
correction applied. Disclosed, uncorrected, and it's a real limitation on everything above.

## Two things I'd get wrong again if I hadn't checked

**The exposure ceiling doesn't hold.** Observed gross exposure ran 0.5043–0.5184 against a "50%"
ceiling. It binds at fill open, and open-to-close drift on positions already held carries the book past
it before the next session's throttle acts. Fixing it needs intra-session trading my execution
convention forbids. So it's disclosed as a numbered conflict rather than quietly rounded — the sealed
constant says 0.50 and the runs say 0.5184, and a report that prints "50% ceiling enforced" would be
false.

**A green verification sweep is mostly a test of your predicates.** My post-build sweep is 186 checks
and three of them failed on the first real run. All three were bugs *in the checks*: one looked for a
snake_case token in prose that spells it out in English, one flagged two digests as unexplained that
were the seal-time tree hash and the universe identity, one demanded a paragraph that is deliberately a
pointer to the disclosure rather than a copy of it. Every failing check has to be diagnosed as either a
package defect or a predicate defect *before* you touch it, because the lazy repair — widen the
allow-list until it's green — turns a detector into a rubber stamp and looks identical in the output to
an undisclosed rewrite.

51 new tests this attempt, 1,142 total, 1,141 passing. The one red is deliberate and permanent: a sealed
contamination predicate that can never read zero again now that the module it authorized exists. It's
left failing as the disclosure mechanism. Muting it would be the actual violation.

## What I don't know

Whether *any* risk overlay can preserve the returns it protects, or whether that's the trade in general
and I just met it head-on. The de-risk ladder scaled me down to 25% of target sizing 1,605 times, and I
have no way to separate "correctly avoided drawdowns" from "sold every dip into the recovery" — the
6,133 blocked re-entries are the same number under both readings.

The thing I'd most like attacked this time: **is a return-blind selection rule that has now chosen the
worst row in the grid still doing something useful, or have I just proven it's uncorrelated with
quality?** Zero shutdowns admitted all 18, so the entire decision fell to a turnover tiebreak I've never
defended as an edge proxy — I chose it because it's cheap and unfakeable, not because low turnover
predicts anything. A rule that can't be gamed and also can't discriminate is not obviously better than
no rule.
