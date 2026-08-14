# I pre-registered six strategies before writing any strategy code. All six failed. Keeping the failure is the point.

**Platform:** Reddit — r/algotrading (crosspost candidate: r/quant)
**Status:** DRAFT — not posted
**Contains historical simulation figures under an unvalidated proxy cost model.** No expected income,
profit, or return is claimed for any period, past or future. Nothing here is live, nothing is
tradeable, no broker credential exists, and every candidate discussed was rejected.

---

Two earlier posts covered sealing the data rules and then validating the backtest engine against a
spec written before the engine existed. This is the part where I finally ran strategies. Six of them,
one per family I'd authorised in advance. All six were rejected. I want to write up the rejection
carefully, because "my backtest failed" is normally where people quietly start over, and the whole
design of this project was an attempt to make that impossible.

**The ordering is the evidence.** Before a single line of strategy code existed, I sealed two files:
the strategy protocol (indicator definitions in prose, entry/exit rules, position sizing, warm-up
rules) and the gate criteria (seven conditions, each with a threshold and a predicate). The seal
record carries this:

```json
"strategy_modules_present_at_seal_time": 0,
"strategy_output_files_present_at_seal_time": 0
```

Measured, not asserted. The loader recomputes the digests on every read and refuses to run on drift.
That number is what makes "I didn't tune this after seeing results" a falsifiable claim rather than a
promise.

Six candidates, thirty runs total — each candidate ran once as its primary parameterisation plus four
pre-declared parameter neighbours. Development window only: 1993-01-29 to 2021-07-31. Validation
window locked, holdout sealed and unread.

**The results, and why they don't mean what they look like:**

| Candidate | Total return | Max drawdown | Profit factor | Closed trades |
|---|---|---|---|---|
| Trend, SMA200 | 0.949 | 15.4% | 5.28 | 15 |
| Pullback, SMA200 + SMA10 | 0.504 | 15.1% | 1.50 | 141 |
| Mean reversion, RSI(2) | 0.712 | 15.8% | 1.95 | 109 |
| Breakout, Donchian 50/25 | 0.233 | 17.8% | 1.97 | 13 |
| Dual momentum rotation | 0.209 | 15.1% | 7.78 | 6 |
| Defensive, SMA200 + SHY | 0.332 | 17.7% | 2.01 | 48 |

Every one is profitable. Every one has a profit factor above the 1.10 floor. Every one was rejected,
and all six on the same condition: maximum drawdown had to be at or below 15%.

Three of them also missed the 30-closed-trade floor. Two failed a profit-concentration limit. One
failed the "remove the single best trade and it must still be profitable" test — which is the
condition I'd expected to do most of the work and which only caught one candidate.

**Here's the part I didn't anticipate.** That 15% ceiling is also the account's research shutdown
threshold: the governing document says research stops permanently if equity falls 15% below its
high-water mark, and it never re-arms. Those are the same number. So a candidate that breaches the
gate has, by construction, already killed the account it was trading. Every one of the six was
liquidated and permanently switched off mid-window — the earliest in October 1997, the latest in
August 2010.

Which means the returns in that table are almost entirely fictitious as descriptions of the rules.
The trend candidate's 0.949 was earned by October 1998 and then sat frozen for the next twenty-two
years and nine months.
Any metric computed over the full window — CAGR, Sharpe, exposure — is describing a short live period
followed by a very long dead one. I recorded that as a limitation rather than quietly reporting
annualised figures over a window the strategy wasn't alive for.

**Three things I'd tell my earlier self:**

**1. Test every gate condition in both directions.** I wrote a test asserting each condition returns
MET on evidence that satisfies it *and* NOT_MET on evidence that doesn't. That felt like busywork
until I noticed the failure mode it protects against: a predicate hard-wired to reject everything
passes a one-sided test perfectly, and on a stage where the real data fails everything, one-sided is
all you'd ever see. Same reason I put clean controls at the top of the adversarial file — a synthetic
candidate that meets every threshold *must* be admitted. Without it, "six rejections and 47 caught
defects" is indistinguishable from an evaluator that says no to everything.

**2. Satisfied and met are different things, and conflating them cost me a wrong answer.** One
condition is written so that it doesn't apply to candidates holding a single position at a time. Four
candidates came back NOT_APPLICABLE_BY_CONDITION_TEXT — satisfied without being met. My first rollup
counted only MET and reported that condition as a blanket failure, which was wrong in a way that
happened to point in the safe direction and would not have next time.

Related: a per-condition summary row is a disjunction across candidates ("at least one satisfied
this") while the gate itself is a conjunction *within* a candidate. Reading the summary table as the
verdict is the natural mistake, and it flatters. The only row that decides anything is "does an
admissible candidate exist." Answer: no. Zero.

**3. One parameterisation is not a test of a family.** I ran six candidates, not six families, and
the difference is enormous. The four neighbour runs for a single candidate span 0.27 to 3.04 total
return. That's how much of any of these numbers belongs to the specific integer I picked rather than
to the rule itself. I get one shot at a holdout and I'm not spending it on a number I chose by feel.

**What I did not do:** revise anything after seeing a result, re-run a candidate with better
parameters, relax a threshold, add a seventh family, or touch the holdout. The rejected results are
on disk with digests over them, including the ones that make the project look unproductive. The
governing document says negative and rejected results are deliverables, and this is what honouring
that actually costs — there's no admitted candidate, so there's no next stage on this line of work.
A further attempt needs a fresh pre-registration sealed before any code for its new candidates
exists.

**Caveats that travel with all of the above,** since they're the reason none of this is a claim about
markets: single unofficial data provider with no cross-check; survivorship bias narrowed to ETFs but
disclosed and unquantified; spread is a flat 2.5 bps constant across thirty years rather than a
measurement; base costs only; drawdown measured at session closes because I have no intraday data, so
every drawdown above is a lower bound and every return is the optimistic case. The cost model can't
be validated at all until paper trading.

Total after this stage: 389 tests, zero admitted strategies, and a documented dead end. I'd rather
have that than a seventh family and a story about why the eighth one will work.

Happy to go into the gate conditions or the pre-registration mechanics if there's interest.
