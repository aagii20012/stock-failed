# The concentration condition wasn't measuring concentration

**Platform:** Reddit — r/algotrading (crosspost candidate: r/quant)
**Status:** DRAFT — not posted
**Length:** long-form self post
**Relation to prior posts:** direct follow-up to *"I deleted one line from my risk architecture..."*
(also unposted). That post ended on an open question. This one answers it with a read-only audit, and
the answer is not the one I expected.

---

## Title

**My strategy failed a concentration gate because one ETF was 75% of the result. I audited it, and the
ETF wasn't concentrated at all — my net was thin. The fix I'd already drafted wouldn't have touched it.**

---

## Body

Last post I described failing a sealed gate condition on concentration: one instrument, IWM, accounted
for `0.7505` of my net closed-episode P&L against a ceiling of `0.50`. Sealed criteria, so the `FAIL`
stood. I closed that post asking whether a concentration condition on a *net* denominator is measurable
at all for a strategy that holds one to three positions.

I've now spent a session answering it — as a **read-only diagnostic**, not a new attempt. No new gate,
no new pre-registration, no verdict token, nothing written into the sealed package. The output is one
report and one JSON ledger in a `reports/diagnostics/` directory that no checksum record covers, because
it isn't evidence for anything.

The headline: **the failure had almost nothing to do with IWM.**

### The question I actually needed answered

There are two very different stories that both produce a 75% share:

1. The strategy fell in love with one instrument, held it for years, and rode it. That's a real
   concentration problem and the gate is right to catch it.
2. The strategy picked it a handful of times on merit, and everything else it did netted to roughly
   nothing. That's a *thin net* problem wearing a concentration problem's clothes.

You cannot tell these apart from the aggregate. The sealed evidence records per-symbol contributions;
it does not record *episodes*. So I rebuilt the episode ledger — entry fill through the sale that zeroes
the position — and looked.

### Instrumenting a sealed run without invalidating it

This is the part I think generalises, so it goes first.

The momentum value that decided each entry **is not in the sealed evidence.** The selection log keeps
sessions, ranked symbols, exclusions, exits, entries — not the ranking *values*. Those survive only
inside a `ranking_digest`.

The tempting move is to recompute the signal. That's wrong: a reimplementation proves something about
my new code, not about what the sealed run saw. What I did instead was **observe** it. In-process only,
the candidate's bound `rank` method gets shadowed by a closure that calls the sealed method and records
what it returned. Same for the engine class, purely to keep a reference so I could read back its
per-session risk-state lines. No subclassing, no added computation, no method of the engine wrapped.

Then — and this is the actual point — I did not *argue* that the wrapper was harmless. I **measured**
it. All four sealed digests, including `ranking_digest` and `risk_state_digest`, came out byte-identical
with the instrumentation installed. 53 observed rebalances against a sealed count of 53. 43 of 43
reproduction checks agreeing, right down to `total_return 0.10337843028513874006` and IWM's share to
34 decimal places — which only matches if the division runs inside the engine's fixed decimal context
rather than at Python's default precision.

If your harmlessness claim is an argument, it's a hope. If it's a digest comparison, it's a fact.

### What the trace found: four episodes, thirteen years apart

IWM was bought and sold **four separate times.** Not once, long.

| # | entry | exit | cal. days | gap since prior IWM exit | entry rank | entry signal | entry notional | closed P&L |
|---|---|---|---|---|---|---|---|---|
| 1 | 2011-01-04 | 2011-04-04 | 90 | — | 2 of 34 | +17.83% | 25.85 | +1.48 |
| 2 | 2012-01-04 | 2012-04-03 | 90 | 275 | 2 of 34 | +23.52% | 12.50 | +1.52 |
| 3 | 2017-01-04 | 2017-04-04 | 90 | 1737 | 2 of 34 | +9.90% | 12.60 | −0.03 |
| 4 | 2021-01-05 | 2021-04-05 | 90 | 1372 | 2 of 34 | +26.99% | 26.06 | **+4.49** |

Every episode is exactly one quarterly interval — the minimum a quarterly-rebalance variant can hold.
The gaps between them are 275, 1737 and 1372 calendar days. IWM was in the book for 247 of 3276
sessions: **7.54% of the run.**

Every entry was rank 2 of 34 ranked members on a solidly positive trailing 3-month return. Across all
53 rebalances IWM reached the top 2 exactly those four times (7.55%), was **never** ranked first, and
had already fallen to rank 4 / 8 / 32 / 5 by the following rebalance — which is what sold it. The signal
was not quietly favouring IWM. It picked it rarely and dropped it the moment it faded.

So story (1) is dead. Selection was repeated, sparse, and justified.

But the dollars are lopsided *inside* those four episodes: `+4.49` of IWM's `7.46` — 60.19% — came from
the single 2021 quarter, which is by itself **45.17% of the entire run's net.** The other three
contributed about `1.5`, `1.5`, and `−0.03`.

### The risk architecture was reducing the concentration, not causing it

Look at the notional column again: `25.85`, `12.50`, `12.60`, `26.06`. Two entries are half the size of
the other two.

That isn't cash starvation — cash was ample at every decision, and equity was near 100 every time. It's
the de-risk ladder, and the run's own risk-state lines say so to the cent:

| # | decision session | drawdown from HWM | ladder band | risk scalar | unscaled target | scaled target | actual entry |
|---|---|---|---|---|---|---|---|
| 1 | 2011-01-03 | 6.5119% | 0 | 1.000 | 25.8431 | 25.8431 | **25.85** |
| 2 | 2012-01-03 | 9.5010% | 1 | 0.500 | 25.0168 | 12.5084 | **12.50** |
| 3 | 2017-01-03 | 8.8040% | 1 | 0.500 | 25.2095 | 12.6047 | **12.60** |
| 4 | 2021-01-04 | 5.6124% | 0 | 1.000 | 26.0918 | 26.0918 | **26.06** |

Band 1 is an 8–10% drawdown and halves the position budget. Episodes 2 and 3 were decided inside it.
The scaled-target column predicts the actual entry to the cent in all four rows.

The uncomfortable arithmetic: at full size, episode 2's +12.16% return on capital would have roughly
doubled its `1.52`. **The risk architecture made the measured concentration smaller.** Which means any
future architecture that de-risks *less* would tend to make it larger — and my last two attempts were
both moving in exactly that direction. That's not a conclusion I went looking for.

### What was actually wrong: the denominator, and my whole book

Here is the framing fact I'd somehow never looked at directly.

The run's equity **high-water mark was set on 2009-12-28** — about seventeen months into a thirteen-year
run — and final equity is *below it.* The strategy spent 1491 of 3276 sessions sitting 8–10% under that
mark and never made a new high again.

Gross profit over closed episodes: `46.70`. Gross loss: `36.76`. Net: **`9.94`.** IWM's `7.46` leaves
`2.48` for the other 23 instruments *combined*, over thirteen years. Twelve net positive, eleven net
negative, and they nearly cancel.

So the concentration ratio is large because the denominator is tiny. Two consequences:

- **A second symbol also breaches the ceiling on the same basis.** VWO is `0.5030` of net. The gate
  measures the single largest contributor, so IWM is what got reported — but this was never a
  one-instrument near-miss.
- With a net of `9.94`, **any** instrument clearing roughly `4.97` fails the condition. The binding
  constraint is the size of the net, not the behaviour of any name in it. A strategy family that keeps
  producing a thin net will keep failing this condition however its selection is capped.

For scale: IWM over *gross profit* is `0.1597` — 15.97%. Same instrument, same run, same trades. The
sealed basis divides by net, and net is smaller by a factor of 4.70.

That answers the question I posted last time, and the answer is yes-with-a-correction: the condition is
measurable, it just wasn't measuring what its name says. It's a **breadth-of-profit** condition. On a
book whose winners and losers nearly cancel, it becomes arithmetically unpassable by anything that makes
money.

### The finding that cost me something

I had already drafted the next adaptation before running this trace: a **forced rotation cap** — a
mechanism to stop the strategy leaning on one name.

The trace says it would not have bound on a single one of the four IWM episodes. Each lasted one
rebalance interval, already the minimum. IWM was never re-selected consecutively; the gaps were years.
Cap holding duration or repeat selection however you like — the condition fails identically.

My operating constraints for this session said, in as many words, that I must not use the diagnostic's
findings to retune the drafted adaptation, because the cap was chosen as a general mechanism and not
against IWM's specific dates. So the draft **stands exactly as written**, and this goes into the report
as a finding for human review instead.

That constraint felt pedantic when I wrote it and correct when it bit. The alternative — quietly
reshaping the next attempt around four dates I'd just finished staring at — is precisely the overfitting
loop the whole governance apparatus exists to prevent. Finding out your planned fix is aimed at the
wrong target is a *result*. Silently re-aiming it is contamination.

### And the smaller thing I said I couldn't test

Last post's second open question was that my prose said "gross" where my seal said "net", for three
attempts, and every automated check passed the whole time. Checksums verify bytes, not whether a file's
English agrees with its arithmetic.

I still can't test that. But the trace turned up *why* it happened, and it's dumber and more instructive
than I expected: **"gross" named three different quantities in the same paragraph of my own notes.**

- IWM / net closed-episode P&L = `7.46 / 9.94` = **`0.7505`** ← what the seal measures, what failed
- IWM / gross episode profit = `7.46 / 46.70` = **`0.1597`**
- IWM / sum of positive per-symbol contributions = `7.46 / 30.92` = **`0.2413`**

All three are real numbers about the same run. My notes had quoted the third one and called it "gross".
It's below the ceiling, so the lesson survived and the verdict was never in danger — but a future reader
would have taken the wrong quantity for the right one.

The rule I've adopted, and the only automatable part of this: **write the arithmetic beside any share
you quote.** `7.46 / 9.94`, not "75% of gross". A bare percentage with an adjective in front of it does
not identify its own denominator, and adjectives are what checksums can't check.

### Disclosure, as always

Development-window figures only. The grid this representative came from is spent — 54 cumulative
variants across 108 runs on the same hypothesis family, three disclosed adaptations, **no
multiple-comparisons correction applied.** The sealed `FAIL` is unchanged and the decision record is
public.

Neither holdout was read. The relevant one opened on 2026-08-01 and is nineteen days into a twenty-four
month window; it stays sealed and unread until that window closes, which is the entire point of having
locked it before the search started.

Nothing in this session produced a governance artifact. The content digest over every governed file was
recomputed and asserted byte-identical before staging, after staging, after commit and after push. A
diagnostic that moves the digest isn't a diagnostic.

### What I'd most like attacked

**Was writing a concentration condition on a net denominator a design error, or is the thin net the real
finding and the condition simply reported it in an unhelpful unit?** I lean toward the second, which is
the answer that gives me the least room to feel good: the gate said "one name is carrying you", the
truth was "nothing is carrying you, and one name happened to be the least bad", and both of those are
reasons not to trade the thing.

Secondary, and more practical: does anyone have a genuine technique for **testing that a document's
prose agrees with its own numbers?** Not "did the file change" — I have that. Something closer to
extracting every quantitative claim in the English and re-deriving it from the artifact it cites. I'd
build it. I just don't know what it looks like beyond "quote the arithmetic and never the adjective".

---

## Notes for posting (not part of the post)

- Sequencing: **must go out after** `The-Denominator-Decided-The-Verdict`, which is still unposted and
  sets up the open question this one answers. Space them by at least several hours; a day is better,
  since this one reads as a reply to the comments on that one.
- Do not merge the two. The prior post is the result; this is the autopsy. Merged, the autopsy buries
  the verdict.
- If the prior post gets the "your condition is unpassable by construction" comment, this draft's
  thin-net section is the reply, and can be posted as a comment there instead of as its own thread.
- Gate/condition identifiers were left out of the body deliberately; they mean nothing to a reader
  outside this repo and the prior posts already carry them.
