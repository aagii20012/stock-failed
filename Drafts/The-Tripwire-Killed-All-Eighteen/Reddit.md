# My best variant returned 28.7% with a 2.68 profit factor. My own pre-registered rule deleted it without reading that number.

**Platform:** Reddit — r/algotrading (crosspost candidate: r/quant)
**Status:** DRAFT — not posted
**Note on figures:** unlike my earlier posts in this series, this one quotes absolute development-window
returns. That's deliberate and it costs nothing: the whole grid is dead, the repo is public, and the
full 18-row table is already sitting in the decision record on GitHub. There is no surviving edge here
to protect. No credentials, no validation-window results, no holdout data — the holdout for this
generation is dated 2026-08-01 → 2028-07-31 and doesn't exist yet in calendar time.

---

Context: my previous strategy passed a development gate, went to validation, and failed — Sharpe 0.20
against a sealed 0.50 floor, 7 of 12 folds positive against a 70% requirement. Post-mortem turned up
something worse than the failure. The "strategy" had 34 ETFs available and, in practice, only ever
traded one of them. It was a single-symbol mean-reversion system wearing a universe as a costume.

So I opened a second research generation to change exactly one variable: make the selection genuinely
cross-sectional. Same data provider, same 34-ETF universe, same account model, same cost model, same
constitution. Only the hypothesis moved — relative-strength rotation, hold the top *k* names, rebalance
on a fixed calendar.

I pre-registered 18 variants before running any of them: lookback ∈ {3, 6, 12} months × top-k ∈ {1, 2,
3} × rebalance ∈ {monthly, quarterly}. Each runs twice, base costs and 2× stressed costs, so 36 declared
runs. Entry at the next session's open, never the close that generated the ranking. Exit only when a
name drops out of top-k at a *scheduled* rebalance. Selection rule frozen in advance: **the variant with
zero research-shutdown events wins; tiebreak lowest turnover.**

## All 18 tripped the shutdown. In both runs.

Not "most." Not "the aggressive ones." Every single variant, in its base run and again under cost
stress. The selection rule's first step produced an empty set, the turnover tiebreak was never reached,
and the seven hard gate conditions were never evaluated at all — they're recorded `NOT_RUN`, because
there was nothing to evaluate them against.

The research shutdown is a constitutional tripwire: 15% below the running high-water mark and the run
liquidates at the next open and blocks further entries. It is a **risk control**, not a performance
metric. Which is exactly why the selection rule is allowed to read it and not allowed to read returns.

And that's how a variant returning 28.7% with a profit factor of 2.68 got deleted by my own rule
without the rule ever loading that field. Same for the 25.3%, the 24.0%, the 22.6%. The rule reads
`research_shutdown_events`, `fill_count`, and `variant_id`. That's the entire input set — it's asserted
by tests that check the selection block contains no performance field to leak.

Reverse the sign of every return in my evidence and the answer is identical. That's the property.

## The obvious move, and why I didn't make it

A long-only strategy holding one to three equity ETFs, run over 2008–2021, is going to draw down more
than 15%. Of course it is. The latest shutdown recorded anywhere in the grid is dated **2020-03-12** —
you don't need me to tell you what that is.

So the temptation writes itself: *the threshold is mis-specified for this strategy class. A 15% ceiling
is a single-instrument mean-reversion number. Rotation needs room to breathe. Raise it to 25% and re-run.*

I think that argument is **partly correct**, and I still didn't get to make it. The pre-registration I
sealed before running anything contains an explicit `no_candidate_path` saying that if every variant is
eliminated, the grid is not loosened, the threshold is not raised, the screen is not narrowed to the
base run, and the rule is not revised post hoc. I wrote that clause specifically so that the version of
me holding 18 dead backtests couldn't negotiate with it.

Because notice what "the threshold is wrong for this strategy class" actually is, when it arrives *after*
you've seen the results: it's a free parameter. If I'd gotten a survivor at 15% I would never have
questioned the number. The threshold only looks mis-specified because it killed things. That asymmetry
is the entire tell.

The honest version is that I mis-specified the *experiment*, not the threshold — I inherited a risk
control calibrated for one strategy family and pointed it at another without re-deriving whether it was
the right control. That's a real error and it belongs in the failure record, which is where I put it.
The repair is a new pre-registration with the tripwire justified for the strategy class *before* the
runs, not an amendment to this one. This grid is spent.

Verdict on disk: `FAIL — STAGE_3_G2_NO_CANDIDATE`. Second generation, second failure, nothing admitted.

## What this cost and what it bought

Cost: about 254 new tests, a multi-position backtest engine with adversarial tests for position-count,
gross-exposure and concentration ceilings, and a full decision package — for zero admitted strategies.

Bought: I know that the entire relative-strength rotation family, over this universe and this window,
cannot clear a 15% intraperiod drawdown tripwire. That is a genuine, reusable negative result. It cost
me one development window and no validation reads — the validation window is untouched and the holdout
is still sealed. Compare that to the counterfactual where I loosen the threshold, get a survivor, spend
a one-shot validation read on it, and learn the same thing more expensively.

One implementation detail that might be the most useful thing here: I added a **window guard** that
makes it a programmatic error for any of this stage's code to read a bar dated 2021-08-01 or later,
with its own test file. Not a convention, not a comment — a guard. The verification sweep afterwards
walks every date-valued field in the decision record and evidence file and asserts that anything past
the boundary is one of the six declared partition boundaries rather than a session date. A bare regex
for "dates after the cutoff" flags the partition definitions themselves and reports violations that
aren't there; a check that can't tell a session from a declared boundary isn't a check.

## What I don't know

Whether relative-strength rotation works. I've established that *this* parameterisation of it, over
*this* universe, gets switched off by *this* risk control before it can be evaluated — which is not the
same claim and I'm trying not to let it drift into being one.

The part I'd most like attacked: **is a drawdown tripwire that fires during a market-wide crash a
strategy filter at all, or just a beta detector?** Every one of these variants is long-only equity. In
March 2020 they went down because everything went down. Filtering on "did you breach 15%" over a window
containing 2008, 2018 Q4 and 2020 arguably selects for nothing except low net exposure — which would
mean my selection rule is return-blind *and* close to information-free, and I'd have built an elaborate
machine for rejecting things on market beta. I don't have a clean answer. The reversal property makes
it non-arbitrary; it doesn't make it informative.
