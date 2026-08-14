# Stage 3 — Strategy Research Pre-registration

**Document ID:** `SE100-GOV-0006`
**Project:** StockEdge100
**Generation:** 1
**Stage:** 3 — baselines and strategy-family research (pre-registration, written before any strategy
code existed)
**Declared (UTC):** 2026-08-09T13:22Z — the authoritative timestamp and the digest of every
pre-registered file are in `governance/STAGE_3_PREREGISTRATION.json`, which is generated after this
document and therefore cannot be quoted inside it.
**Status of this document:** pre-registration. It constrains Stage 3; it does not modify, supersede,
reinterpret, or extend `SE100-GOV-0001`.

---

## 1. Why this document exists

Stage 2 sealed the costs before an engine existed, because a cost assumption chosen after seeing a
result is not an assumption but a dial. Stage 3 has the same problem in a much sharper form. A
strategy is *nothing but* dials. Lookback, threshold, entry rule, exit rule, universe membership,
rebalance date, warm-up length — every one of them is a free parameter, and every one of them can be
moved a little after a disappointing result and moved back after a good one. Nothing in the output
distinguishes a rule that was specified from a rule that was found. The equity curve looks the same
either way, and it looks better every time the dial is turned.

Constitution §8 is the answer to that, and it is unusually specific: each strategy experiment
requires a signed specification created *before* execution, containing an immutable experiment ID and
hypothesis, the eligible universe and exclusions, signal timing, features, parameters and the
permitted parameter grid, entry, exit, sizing, ranking and conflict rules, cost assumptions and
benchmarks, the data partition permitted, the primary metric and all pass/fail gates, the maximum
number of research iterations, and the code and configuration hashes.

Every one of those elements, for all six candidates, is in
`config/stage3_strategy_protocol.json`. How each Gate 3 condition will be *measured* — not merely
what its threshold is — is in `config/stage3_gate_criteria.json`. Both are sealed by this document.

At the moment this document is sealed, `src/stockedge100/strategies/` contains **no files**. There is
no strategy, no signal, no equity curve produced by any rule with a parameter in it, and no
`reports/stage3/` directory. That fact is verified by the sealing program, which refuses to run
otherwise, and is recorded in the JSON.

---

## 2. Pre-registered files

| File | Content |
|---|---|
| `config/stage3_strategy_protocol.json` | the six §8 experiment specifications: hypothesis, universe, exclusions, timing, features, parameters, permitted grid, entry/exit/sizing/ranking/conflict rules, robustness neighbours, iteration budget, benchmarks, shared rules, indicator definitions |
| `config/stage3_gate_criteria.json` | Gate 3's seven conditions with the measurement method fixed for each, the undefined and not-evaluable treatments, the derived verdict tokens, and three recorded conflicts against the frozen constitution |
| `governance/STAGE_3_PREREGISTRATION.md` | this document |
| `governance/STAGE_3_PREREGISTRATION.json` | authoritative declaration timestamp and digests of the three files above |
| `governance/STAGE_3_PREREGISTRATION.sha256` | checksum record covering the four files above |

`STAGE_3_PREREGISTRATION.sha256` records **project-root-relative** paths, matching the Stage 1 and
Stage 2 convention and differing deliberately from `STAGE_0_FREEZE.sha256`, which records bare
filenames:

```bash
cd stockedge100 && sha256sum -c governance/STAGE_3_PREREGISTRATION.sha256
```

Neither record contains its own digest; nothing hashes itself.

---

## 3. Six candidates, one per family, tested independently

Constitution §3 names six strategy families that may be researched separately for Generation 1:
trend/momentum, pullback, mean reversion, breakout, ETF rotation, and defensive regime logic. Stage 3
declares exactly one candidate per family:

| ID | Family | Universe | Primary parameters |
|---|---|---|---|
| `SE100-S3-F1-TREND-SMA200` | trend/momentum | SPY | SMA 200 |
| `SE100-S3-F2-PULLBACK-SMA200-SMA10` | pullback | SPY | SMA 200 long, SMA 10 short |
| `SE100-S3-F3-MEANREV-RSI2` | mean reversion | SPY | Wilder RSI 2 below 10, exit above SMA 5 |
| `SE100-S3-F4-BREAKOUT-DONCHIAN-50-25` | breakout | SPY | 50-session closing high in, 25-session closing low out |
| `SE100-S3-F5-ROTATION-DUALMOM` | ETF rotation | SPY, MDY, EFA, IEF | 252-session momentum, monthly, top 1, positive-only |
| `SE100-S3-F6-DEFENSIVE-SMA200-SHY` | defensive regime logic | SPY, SHY | SMA 200 on SPY, SHY otherwise |

These are the textbook parameterisations of each family, chosen for exactly that reason. A round
number that has been in print for thirty years is a weaker fit to this particular sample than a
number this project selected, and the point of Gate 3 is to reject fitted candidates. **No search over
the permitted grid is performed.** The grid exists to bound what a *later* stage could legitimately
consider; it is not a space to be optimised over here, and nothing in this stage reads more than one
parameterisation per candidate as its primary.

**Nothing is combined.** §8 prohibits combining strategies until each component has an independent
verdict, and no candidate here references another. Six specifications, six independent verdicts.

**No machine learning.** §8 forbids it for Generation 1 outright. Nothing in this stage fits, trains,
cross-validates, or optimises anything against any outcome.

---

## 4. Three structural rules that cost the candidates money

Three consequences of the sealed cost model and the validated engine bind every candidate. Each one
makes results worse, each is charged uniformly, and each is written here so it cannot later be
described as an artefact and modelled away.

**One position, and the exit strictly precedes the entry.** The sealed cost model permits one open
risky position. Within a single fill session the engine executes orders sorted by
`(symbol, side, order_id)`, so an entry whose symbol sorts before the exit's would execute first and
be rejected `MAX_POSITIONS`; the order book also refuses two orders in one symbol on one session. So
a switch is always two sessions: sell today, buy at the next flat session's following open. Every
rotation and every regime switch therefore spends **one full session out of the market**, at whatever
the market does that day. This is the conservative construction and it is charged to all six.

**Signals are computed at a close and filled at the next open.** No candidate may act on the close it
used to decide. That is §3's execution assumption and the engine raises `FillTimingError` rather than
trusting a strategy to respect it.

**The research shutdown is enforced, and it is the same number as the gate.** §5.1 puts a research
shutdown at 15% below the running high-water mark; Gate 3 requires maximum drawdown no worse than
15%. A candidate that trips the shutdown is liquidated at the next open, permanently blocked from new
entries, and its equity curve is flat thereafter — and it has already breached the drawdown
condition by construction. The shutdown is not disabled for any candidate. It is disabled only for
the explicitly labelled SPY benchmark reference account, exactly as Stage 2 reported it, and both
variants of that benchmark are reported side by side.

A fourth rule is not a cost but a boundary: **each candidate's run starts on the first
development-window session on which every symbol in its universe has at least its declared warm-up of
visible bars, and ends at the development window end.** Warm-up lengths are set to the largest
lookback used by the primary *or any neighbour*, so no variant of a candidate is advantaged by a
different start. This means F5 and F6 run over roughly eighteen years while F1–F4 run over roughly
twenty-eight; their results are not comparable to each other on equal samples, and Stage 3 does not
compare them to each other in any case.

---

## 5. What the robustness neighbours are for, and what they must never be used for

Gate 3's seventh condition asks that reasonable neighbouring parameter values not reverse the sign of
net return. Each candidate therefore declares exactly four neighbours, fixed in the protocol before
any result exists, run over the same window under the same costs.

Only the **sign** of each neighbour's net return is read. Their other metrics are recorded for the
file and carry no gate weight.

A neighbour is never promoted to primary. If a neighbour outperforms its primary, that is recorded
and nothing else happens. Under §11 a change to universe, timing, cost, signal, parameter range,
metric, threshold, or data partition is material, and a material change creates a **new** candidate
that restarts at Gate 3 — it does not repair the one that disappointed. The iteration budget in the
protocol is therefore one primary run per candidate and **zero revisions**.

Two neighbours deliberately vary something other than a number: F5 drops EFA from its universe, and
F6 replaces its defensive leg with cash. A rotation whose profitability depends on the presence of
one member is exactly as fragile as one whose profitability depends on a lookback, and the
constitution's condition is about the sign of net return under reasonable neighbouring values, not
about lookbacks alone.

---

## 6. Where the frozen gate text and its JSON companion disagree

Three findings are recorded in `stage3_gate_criteria.json` and repeated here so they are visible in
prose. **None of them is repaired.** `SE100-GOV-0001` is frozen; a defect in it is reported, never
edited.

1. **The JSON companion for gate 3 is incomplete.** It carries five thresholds; the Markdown carries
   seven conditions — the same five plus the profit-concentration condition and the
   neighbouring-parameter condition. The Markdown is authoritative and is the more restrictive text.
   All seven are evaluated and all seven must pass. This is the same defect class Stages 1 and 2 each
   recorded against their own gates.
2. **Gate 3 has no `pass_result`.** The affirmative token is derived by negating the stated
   `fail_result`, as Stages 1 and 2 derived theirs: `STRATEGY_REJECTED_IN_DEVELOPMENT` negates to
   `STRATEGY_ADMITTED_IN_DEVELOPMENT`. **Both tokens are fixed before any result**, so the outcome
   cannot shape the vocabulary used to describe it.
3. **The drawdown gate and the research shutdown are the same 15%.** Not a contradiction, but a
   coupling worth stating before results rather than discovering in them — see §4 above.

One interpretation also has to be fixed in advance, because reading it either way after the fact
would be indefensible. The profit-concentration condition says "for a multi-instrument strategy". It
is evaluated for F5 and F6 and recorded as `NOT_APPLICABLE_BY_CONDITION_TEXT` for the four
single-instrument candidates, with the instrument count as evidence. A universal reading would have a
single-instrument candidate contribute 100% of its own profit and fail automatically, which would
make four of the six families §3 explicitly authorises untestable at this gate. That cannot be the
intent of a clause whose purpose is to detect concentration *across* instruments. The reasoning is
recorded here, before any candidate's concentration is known.

---

## 7. Rules that bind the rest of the stage

1. **A candidate may not be edited to pass.** The parameters in `stage3_strategy_protocol.json` are
   sealed by this document. If a candidate fails, it is reported as failed. Changing a lookback,
   moving a threshold, adding a stop, adding or removing a universe member, or shifting a run start
   after seeing a result is prohibited, whichever direction it would move the number.
2. **Development-window data only.** Validation and holdout are `LOCKED` and `SEALED`. The window
   guard raises `WindowViolation` structurally and `MarketView` raises `LookAheadError` on any read
   past the decision session; neither depends on a strategy behaving well.
3. **AAPL is excluded from every candidate.** A price file for it exists because Stage 1 measured the
   split convention against two AAPL split events. It is not a member of the frozen universe, and §3
   records individual stocks as prohibited for Generation 1.
4. **Every condition verdict is produced by a program that reads the engine's own outputs.** No
   condition verdict is typed by hand into a report. Each is `MET`, `NOT_MET`, `NOT_EVALUABLE`, or
   `NOT_APPLICABLE_BY_CONDITION_TEXT`; there is no fifth value and no borderline value, and
   `NOT_EVALUABLE` never counts as `MET`.
5. **Decimal arithmetic throughout the signal path.** No floating-point value enters an indicator, a
   comparison against a threshold, or a cash computation. This is what makes reruns bit-identical.
6. **Tests are added, never subtracted.** The suite stands at 273 passing tests at the moment this
   document is sealed. Stage 3 adds to it. Weakening or deleting a test to make a gate pass is
   prohibited.
7. **Stage 3 selects nothing.** Gate 3 is admissibility. Every candidate meeting every hard condition
   is recorded as admitted; the stage does not rank admitted candidates, name a winner, or carry a
   preference forward.
8. **A stage verdict of `FAIL — STAGE_3_STRATEGY_REJECTED_IN_DEVELOPMENT` is a legitimate
   deliverable.** It is recorded, kept on disk, and does not license a seventh candidate in this
   session.

---

## 8. Six candidates against one dataset — the disclosure that belongs before the result

Six specifications are tested against the same development data. A criterion calibrated for one
specification is not family-wise for six: the probability that at least one of six passes by chance
exceeds the probability that any single pre-specified one does. This is stated here, before any
result, rather than in a footnote afterwards.

Stage 3 applies no numerical multiple-comparisons correction, and it would be dishonest to imply that
declaring six candidates in advance makes the problem go away — pre-registration removes the freedom
to *choose* the six after the fact, not the arithmetic of testing six. The correction the constitution
actually relies on is structural: an admitted candidate still has to survive Gate 4 robustness and a
single sealed holdout read, and §12 prohibits selecting a winner from holdout results at all.

What a passed Gate 3 will mean is therefore narrow. It will mean that a pre-specified rule, run on
development data under declared costs with a next-open fill and an enforced shutdown, cleared seven
minimum-quality conditions. It will not mean the rule works, that it will work out of sample, that
the declared costs match real trading costs — they remain the Stage 2 proxy and cannot be validated
before paper trading — or that any figure it produced is achievable. **No expected income, profit, or
return is claimed for any period, past or future, anywhere in this stage.**

---

## 9. Explicit non-authorizations, restated for this stage

Stage 3 does not authorize, and this stage will not perform:

- any read of validation-window or holdout-window data, for any purpose;
- any download, purchase, subscription, or account creation — every price used comes from the Stage 1
  normalized dataset already on disk;
- any machine learning, optimiser, grid search, or fit of any kind;
- any combination of one candidate with another;
- any credential access, or any read of a secret value;
- any order, paper or live, and no unattended scheduling;
- any selection of a winning strategy, and any claim of expected income;
- any modification of a frozen Stage 0, Stage 1, or Stage 2 artifact.

`live_trading_authorized` remains `false`.

---

## 10. Pre-freeze disclosure

Before this document was written, this session read the Stage 0 constitution, the Stage 1 and Stage 2
artifacts and their freeze records, the normalized data schema, the validated engine's source, and
the existing 273-test suite, and ran that suite to establish a clean baseline.

Two measurements were taken against the price data, and both are disclosed because both touched the
development window:

1. **Availability only.** For every symbol on disk, the first and last session, the count of missing
   sessions inside the development window, and the longest missing run were measured. All were zero
   missing. This determined the run-start rule and confirmed that loading multiple symbols cannot
   trigger a `DataIntegrityHalt`. No return, no price level, and no summary statistic of returns was
   computed or inspected for any symbol.
2. **Timing only.** `MarketView.history` was timed to decide whether strategies could read prices
   through the look-ahead-safe accessor on every call rather than keeping internal rolling state. It
   can, and they do. The values returned were not examined.

No backtest of any rule with a parameter in it was run. No equity curve, trade list, or performance
figure exists for any candidate, any neighbour, or any variant. The two configuration files sealed
here were authored in this session with no result available to consult.
