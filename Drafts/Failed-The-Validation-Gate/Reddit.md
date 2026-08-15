# My pre-registered strategy failed its validation gate. I got one read of the data, I spent it, and the candidate is finished.

**Platform:** Reddit — r/algotrading (crosspost candidate: r/quant)
**Status:** DRAFT — not posted

**Nothing here is live.** No broker connection exists, no credential exists, no order has ever been
generated. The final holdout has still never been read — zero reading sessions, and it stays that way.
This post is a negative result, which is the entire reason it exists.

---

Six posts ago I started pre-registering an algorithmic trading project against a frozen constitution:
seal the rules before you can see the results, one stage per session, never weaken a test to make a gate
pass. Last post, attempt 2 cleared the development gate and admitted two candidates, and I wrote at
length about why that was a much weaker statement than it sounded.

This session executed the validation stage. **The gate failed.** Here is what that cost and what I
learned from spending it.

## The setup, all of it fixed before I could see anything

One representative: `C2`, a mean-reversion candidate. It was selected **return-blind** — the rule that
eliminated the other admitted candidate looked only at whether its declared variants tripped my
research-shutdown threshold, never at their returns. Twelve walk-forward folds, zero training folds, one
parameterization, two registered runs (base cost, then double cost), and **one** authorized read of the
validation window. No rerun after a valid completed run. Ever.

Seven conditions, conjunctive. All thresholds frozen months earlier.

I also pre-registered the *expectation of failure*: C2 hadn't reached the 0.50 Sharpe floor in
development either, and I wrote that down so I couldn't later claim I'd been surprised.

## What came back

| Condition | Required | Measured | |
|---|---|---|---|
| After-cost return | > 0 | **0.0215** | met |
| Sharpe | ≥ 0.50 | **0.2025** | **missed** |
| Max drawdown | ≤ 0.15 | **0.0316** | met |
| Profit factor | ≥ 1.15 | **1.1965** | met |
| Stressed return (2× costs) | > 0 | **0.0015** | met |
| Folds positive | ≥ 70% | **7 of 12 (58%)** | **missed** |
| No change in response to results | — | 13/13 digests equal | met |

Five of seven. One `NOT_MET` ends it, and I had two.

**`FAIL — STAGE_4_STRATEGY_REJECTED_IN_VALIDATION`**

The thing I want to point at is the shape of the failure. This is not a blowup. It made money. It
survived doubled costs. Its worst drawdown out-of-sample was 3.2% against a 15% ceiling — better than
its 12.6% in development. There is nothing dramatic to tell a story about.

It just isn't good enough. Development return 0.5599 → validation return **0.0215**. Development profit
factor 1.440 → 1.1965. A real but tiny edge, positive on 7 of 12 folds, that would have looked like a
promising strategy to anyone willing to squint at it in-sample.

That's the honest failure mode, and it's the one a pre-registered threshold is actually for. A blowup I
would have caught anyway. *This* is the one I'd have talked myself into.

## The consequence was written down in advance, and it isn't "iterate"

The seal says a fail authorizes exactly one thing: **record the fail as a deliverable and stop.**

Not retune C2. Not substitute the other admitted candidate — that decision was made prospectively and
reopening it now would be selection on the outcome I just observed. Not reopen attempt 2. Not touch the
holdout.

Any further work on this idea is a **new candidate restarting at the development gate**, disclosed as
adaptive, and the validation window is now permanently compromised for it, because I've seen it. That's
the real price of the read: not the failed result, but that I can never get that window back.

I think this is the part that's genuinely hard to internalize. The whole gravitational pull of a bad
out-of-sample result is toward "okay, but what if I just—". The rule has to exist before the result,
because afterwards there's always a reason.

## The test I left failing on purpose

Best engineering problem of the session, and I still don't love the resolution.

I'd sealed a contamination predicate: *no module named `stage4*` may load a dataset, import a network
or broker package, read an environment variable, open a connection, or contain a URL.* Its purpose was
to prove the **pre-registration** couldn't peek at restricted data. It measured 0. Good.

Then the pre-registration authorized me to write the evaluator. The evaluator's entire job is to load a
price series. It is, necessarily, a `stage4*` module that loads a dataset.

**The predicate cannot survive authorizing the work it gates.** Once the evaluator exists it can never
read 0 again.

Four ways to make it green were available:

1. Rename the evaluator out of the `stage4` path — hides a real dataset load from a predicate written
   to find it, and corrupts a second predicate too
2. Weaken, skip, `xfail` or delete the test — forbidden outright
3. Edit the seal — forbidden after a validation read, whatever the intent
4. Restructure so a differently-named module holds the loader call — that's #1 in a costume

I refused all four and **left the test red**, as the disclosure mechanism. The suite reports
`836 passed, 1 failed` and the failure is documented in three places as deliberate.

The half of the predicate that guards against a broker, a network call, a credential read or a URL
**still measures 0**, and that's the half the safety claim actually rests on. But "the number is
nonzero and here is exactly why" is a worse-looking, more honest artifact than a green suite, and I'd
rather ship the ugly one.

There's a second-order lesson in there about writing predicates whose scope is wider than their purpose.
I don't have a clean general fix.

## Two smaller things that were load-bearing

**Publishing a hash-governed repo to git nearly destroyed it.** This project's identity is a SHA-256
over every tracked file. `git init` on Windows defaults to `core.autocrlf=true`, which rewrites LF to
CRLF in the working tree **on the next checkout** — changing the hash of every file and silently
invalidating every freeze record and manifest from the first stage onward, with nothing having been
"edited". It printed 160 warnings and I nearly scrolled past them. `* -text` in `.gitattributes`, and I
recomputed the digest before and after to prove it hadn't moved.

**Two of my own verification checks were wrong about a package that was fine.** One asserted a sealed
set had 13 entries when it correctly has 12 — the thirteenth is the file doing the declaring, and
nothing hashes itself. The other compared against a list that turned out to be empty, so it passed
vacuously; `all()` over nothing is `True`. Any check whose output could be produced by *finding
nothing* is not a check. When your sweep and a checksum record disagree, the record is right.

## Where this leaves it

Gates 0 through 3 passed. Gate 4 evaluated and failed. The holdout has never been read. Nothing is
authorized, nothing is trade-ready, and there is no next stage.

I've put the whole thing on GitHub — the constitution, every sealed pre-registration, the failing
result, the red test, the conflicts I couldn't resolve. Including the parts that make me look bad,
because a governance framework you only publish when it says PASS isn't one.

Repo: https://github.com/aagii20012/stock-failed

The genuinely useful reply here isn't "have you tried a different lookback". It's: which of these rules
would you expect me to quietly break first?
