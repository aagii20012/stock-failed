# StockEdge100 — Stage 3 strategy research report

| | |
| --- | --- |
| Document id | `SE100-GOV-3000` |
| Project | StockEdge100, Generation 1 |
| Stage | Prompt Stage 3 — baselines and strategy-family research. Constitution **gate 3, development_admissibility**. |
| Governing document | `SE100-GOV-0001` v1.0.0, FROZEN, unmodified by this stage |
| Pre-registration | `SE100-GOV-0006`, sealed 2026-08-09T13:25:21Z, before any strategy module existed |
| Evidence | `SE100-EVID-3001`, generated 2026-08-09T14:37:30Z |
| Authored (UTC) | 2026-08-09T14:59:47Z |
| Verdict | **FAIL — STAGE_3_STRATEGY_REJECTED_IN_DEVELOPMENT** |
| `live_trading_authorized` | `false` |

`run_id` and the repository-state digest for this stage are **not** written here: that digest covers
`governance/*.md`, so a copy embedded in this file would be invalidated the moment the file was
saved. Both values live in
[reports/stage3/STAGE_3_STRATEGY_RESEARCH.json](../reports/stage3/STAGE_3_STRATEGY_RESEARCH.json) and
in the append-only record under [runs/](../runs/).

---

## 1. The result, stated first

Six pre-registered candidates — one per strategy family constitution §3 authorises for Generation 1 —
were run over the development window under sealed base costs. **None of them satisfies every hard
condition of Gate 3.** No candidate is admitted, no candidate is carried forward, and nothing in this
stage proceeds to Gate 4.

| Candidate | Family | Conditions not met | Admitted |
| --- | --- | --- | :---: |
| `SE100-S3-F1-TREND-SMA200` | trend / momentum | S3-C2, S3-C4 | no |
| `SE100-S3-F2-PULLBACK-SMA200-SMA10` | pullback | S3-C2 | no |
| `SE100-S3-F3-MEANREV-RSI2` | mean reversion | S3-C2 | no |
| `SE100-S3-F4-BREAKOUT-DONCHIAN-50-25` | breakout | S3-C2, S3-C4, S3-C5 | no |
| `SE100-S3-F5-ROTATION-DUALMOM` | ETF rotation | S3-C2, S3-C4, S3-C6 | no |
| `SE100-S3-F6-DEFENSIVE-SMA200-SHY` | defensive regime logic | S3-C2, S3-C6 | no |

This outcome was declared a legitimate deliverable **before** any candidate ran
(`STAGE_3_PREREGISTRATION.md` §7.8, `stage3_gate_criteria.json` → `verdict_token_derivation.
fail_is_a_deliverable`). It is recorded, kept on disk, and does not license a seventh candidate in
this session. No parameter was changed, no threshold was moved, and no candidate was re-run after its
result was seen.

## 2. What this stage was allowed to do

Research six strategy families on development data and judge each against a gate whose thresholds and
**measurement methods** were fixed in advance. Nothing else.

The validation window was not read. The holdout remains `SEALED` and was not opened, sampled, or
counted. Every one of the 36 runs in this stage (30 declared + 6 determinism re-runs) is bounded by
the Stage 1 holdout lock, 1993-01-29 → 2021-07-31, and a read outside it raises `WindowViolation`
rather than returning a price.

Nothing frozen was edited. No data was downloaded, purchased, or acquired — every price comes from
the Stage 1 normalized dataset already on disk. No credential was read and no credential presence was
even tested. No order, paper or live, exists. No machine learning, optimiser, grid search, or fit of
any kind was performed, and no candidate was combined with any other.

**Stage 3 selects nothing.** Gate 3 is admissibility. Had a candidate been admitted, this stage would
still not have ranked it, named it a winner, or carried a preference forward.

## 3. The order things happened in, and why it is the whole argument

A strategy is *nothing but* dials. Lookback, threshold, entry rule, exit rule, universe membership,
rebalance date, warm-up length — every one is a free parameter, and nothing in an equity curve
distinguishes a rule that was specified from a rule that was found. So the order is the evidence, and
it was:

1. **Seal the six §8 experiment specifications.** `config/stage3_strategy_protocol.json`
   (`SE100-CFG-3001` v1.0.0) — hypothesis, eligible universe and exclusions, signal timing, features,
   parameters and permitted grid, entry / exit / sizing / ranking / conflict rules, robustness
   neighbours, iteration budget, benchmarks, indicator definitions.
2. **Seal how each condition will be measured**, not merely its threshold.
   `config/stage3_gate_criteria.json` (`SE100-CFG-3002` v1.0.0) fixes the definition of maximum
   drawdown, of profit factor, of "removing the single best trade", of instrument contribution, and
   of the not-evaluable and undefined treatments — plus the pass and fail tokens and the three
   recorded conflicts against the frozen constitution.
3. **Record both digests in governance.** `governance/STAGE_3_PREREGISTRATION.json` records
   `sealed_before_any_strategy_code: true` and, as the check that makes the claim falsifiable,
   `strategy_modules_present_at_seal_time: 0` and `strategy_output_files_present_at_seal_time: 0`.
4. **Then write the strategies**, against a loader that refuses a config whose digest has drifted.

The sealed digests are:

| Sealed file | SHA-256 |
| --- | --- |
| `config/stage3_strategy_protocol.json` | `04dbe3fa8c6b2a9e725a66d24f5dc0a3a7e3567e70d38bfd2e96869cc6e169b6` |
| `config/stage3_gate_criteria.json` | `310f1c978380f4a1d6b98b8c368975b1515476b032c123afb06f1dd597e3e18d` |
| `governance/STAGE_3_PREREGISTRATION.md` | `a257e862377938d42584147d3aedb1a2ba493b0f9f1f22f079745b953314526f` |

`stockedge100.strategies.config.load_stage3_config()` recomputes all three on every load and raises
`ConfigViolation` on any drift, naming the file that moved. It also refuses to load a parameter file
that is not listed in the seal at all, and refuses to run if the seal itself is missing — an unsealed
parameter file cannot produce Gate 3 evidence. Nothing in `src/` calls the loader with the seal check
disabled; a test asserts that by scanning the source tree.

Neither record hashes itself. `STAGE_3_PREREGISTRATION.json` and its `.sha256` companion are covered
by the checksum record, which uses project-root-relative paths:

```bash
cd stockedge100 && sha256sum -c governance/STAGE_3_PREREGISTRATION.sha256
```

## 4. Six candidates, one per family, tested independently

| ID | Family | Universe | Primary parameters | Warm-up |
| --- | --- | --- | --- | ---: |
| `SE100-S3-F1-TREND-SMA200` | trend / momentum | SPY | SMA 200 | 250 |
| `SE100-S3-F2-PULLBACK-SMA200-SMA10` | pullback | SPY | SMA 200 long, SMA 10 short | 250 |
| `SE100-S3-F3-MEANREV-RSI2` | mean reversion | SPY | Wilder RSI 2 below 10, exit above SMA 5 | 101 |
| `SE100-S3-F4-BREAKOUT-DONCHIAN-50-25` | breakout | SPY | 50-session closing high in, 25-session closing low out | 100 |
| `SE100-S3-F5-ROTATION-DUALMOM` | ETF rotation | SPY, MDY, EFA, IEF | 252-session momentum, monthly, top 1, positive-only | 316 |
| `SE100-S3-F6-DEFENSIVE-SMA200-SHY` | defensive regime logic | SPY, SHY | SMA 200 on SPY, SHY otherwise | 250 |

These are the textbook parameterisations of each family, chosen for exactly that reason: a round
number that has been in print for thirty years is a weaker fit to this particular sample than a
number this project selected. **No search over the permitted grid was performed** — the grid bounds
what a later stage could legitimately consider; it is not a space that was optimised over here.
Nothing was combined, and no machine learning was used; §8 forbids both for Generation 1.

Each candidate's run starts on the first development-window session on which every symbol in its
universe has at least its declared warm-up of visible bars, and ends at the window end. Warm-ups are
set to the largest lookback used by the primary *or any neighbour*, so no variant is advantaged by a
different start — F1's warm-up is 250 rather than 200 because a neighbour uses SMA 250. F5 and F6
therefore run over roughly eighteen years while F1–F4 run over roughly twenty-eight; their results
are **not comparable to each other**, and this stage does not compare them.

## 5. Three structural rules that cost every candidate money

Each was declared in the pre-registration before any result existed, each makes results worse, and
each is charged uniformly, so that none can now be described as an artefact and modelled away.

**One position, and the exit strictly precedes the entry.** The sealed cost model permits one open
risky position, so no candidate may rotate by swapping in a single decision. The sealed rule makes
the deferral explicit: on a rebalance the candidate records the target as `pending_target`, emits
**only** the exit, and issues the buy on the next session on which the account is flat. Every
rotation and every regime switch therefore spends **one full session out of the market**. Order
execution inside a fill session is separately deterministic, sorted by `(symbol, side, order_id)`.

**Signals are computed at a close and filled at the next open.** No candidate acts on the close it
used to decide; the engine raises `FillTimingError` rather than trusting a strategy to respect it.

**The research shutdown is enforced, and it is the same number as the gate.** §5.1 puts a permanent
research shutdown at 15% below the running high-water mark. It was enforced for all six. It is the
single most consequential fact in this report and §7 is about it.

## 6. What the six candidates did

All figures are from the primary run of each candidate, base costs, USD 100 starting equity, read out
of [reports/stage3/STAGE_3_DEVELOPMENT_ADMISSIBILITY.json](../reports/stage3/STAGE_3_DEVELOPMENT_ADMISSIBILITY.json).
No number below was typed by hand into this report; each is quoted from the evidence file, which a
program wrote by reading the engine's own outputs.

| Candidate | Run window | Sessions | Total return | Max DD | Profit factor | Closed trades | Exposure | Shutdown |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| F1 TREND | 1994-01-24 → 2021-07-31 | 6929 | `0.9488` | `0.15373` | `5.2835` | 15 | `0.1489` | 1998-10-28 |
| F2 PULLBACK | 1994-01-24 → 2021-07-31 | 6929 | `0.5037` | `0.15087` | `1.5007` | 141 | `0.0697` | 2000-05-25 |
| F3 MEANREV | 1993-06-23 → 2021-07-31 | 7078 | `0.7122` | `0.15771` | `1.9541` | 109 | `0.0541` | 2001-09-21 |
| F4 BREAKOUT | 1993-06-22 → 2021-07-31 | 7079 | `0.2326` | `0.17804` | `1.9728` | 13 | `0.0851` | 1997-10-27 |
| F5 ROTATION | 2003-10-28 → 2021-07-31 | 4470 | `0.2094` | `0.15060` | `7.7767` | 6 | `0.1458` | 2006-06-13 |
| F6 DEFENSIVE | 2003-07-25 → 2021-07-31 | 4536 | `0.3323` | `0.17729` | `2.0106` | 48 | `0.3807` | 2010-08-11 |

Reported and **not gating**: CAGR `0.0245 / 0.0149 / 0.0193 / 0.0074 / 0.0107 / 0.0160`; Sharpe at a
0.00% risk-free rate `0.4723 / 0.3078 / 0.3817 / 0.2291 / 0.2432 / 0.2852`; win rate `0.20 / 0.70 /
0.73 / 0.54 / 0.67 / 0.35`. Every candidate ended flat — `open_positions_at_end` is 0 for all six —
and no candidate produced a single stale mark.

Two columns deserve reading together. The **exposure fraction** is the share of the run spent holding
anything: the largest is F6 at 38%, and F3 spent 95% of twenty-eight years in cash. The **longest
flat streak** is 5726, 5328, 4998, 5978, 3809 and 2761 sessions respectively. These are not descriptions
of selective strategies. They are descriptions of strategies that were switched off — which is what
the shutdown column means, and what §7 explains.

## 7. Why every candidate failed S3-C2, and why that is one finding rather than six

All six breach the 15% maximum-drawdown condition. All six tripped the §5.1 research shutdown. These
are the same event, and the pre-registration said so before any of them ran (`S3-CONFLICT-3`): the
gate threshold and the shutdown threshold are the same 15%, so **any candidate that trips the
shutdown has by construction already breached S3-C2**.

What the shutdown then does is what makes the rest of the table look the way it does. It liquidates
at the next open and **permanently blocks new entries** — it never re-arms. So the equity curve is
flat from the liquidation onward, and every later entry signal is refused. The refusals are counted:

| Candidate | Shutdown | Rejected orders | All reason | Fills |
| --- | --- | ---: | --- | ---: |
| F1 | 1998-10-28 | 4119 | `RESEARCH_SHUTDOWN` | 30 |
| F2 | 2000-05-25 | 1244 | `RESEARCH_SHUTDOWN` | 282 |
| F3 | 2001-09-21 | 473 | `RESEARCH_SHUTDOWN` | 218 |
| F4 | 1997-10-27 | 887 | `RESEARCH_SHUTDOWN` | 26 |
| F5 | 2006-06-13 | 3808 | `RESEARCH_SHUTDOWN` | 12 |
| F6 | 2010-08-11 | 2760 | `RESEARCH_SHUTDOWN` | 96 |

F1 tripped in its fifth year and spent the remaining twenty-two in cash; its 15 closed trades and
its S3-C4 failure are consequences of that, not independent observations. The same is true of F5's 6
trades and F4's 13. **The 15% drawdown breach is the primary finding of this stage**, and S3-C4 and
S3-C5 failures downstream of a 1997 or 1998 shutdown should be read as its shadow rather than as
separate evidence.

Two things this does **not** license. It does not license disabling or relaxing the shutdown for a
research run: §5.1 is a constitutional control on a USD 100 account, and a candidate whose result
depends on removing it is a candidate that has not passed. And it does not license moving S3-C2, which
would be loosening a gate threshold after seeing the result it judges — prohibited outright.

It is worth being precise about how close three of them were. F5 measures `0.15060`, F2 `0.15087`,
F1 `0.15373` — breaches of 0.06, 0.09 and 0.37 percentage points against an **inclusive** 15%
boundary sealed in advance. They are failures. That they are narrow is a fact about this sample, not
a reason to reconsider the threshold, and the boundary was written as inclusive before anyone knew
which side of it anything would land on.

## 8. Condition by condition

Every verdict below was produced by `stockedge100.strategies.gate`, which reads the engine's own
outputs and compares them against the sealed criteria as exact `Decimal`s. There is no fifth value,
no borderline value, and `NOT_EVALUABLE` never counts as `MET` — the type refuses to construct a
verdict outside the four sealed values. The gate also verifies, before evaluating anything, that the
five sealed thresholds still read `net_return_positive: true`, `max_drawdown_pct: 15`,
`profit_factor_min: 1.1`, `closed_trades_min: 30`, `best_trade_removed_return_positive: true`, and
halts if any has moved.

| | S3-C1 return > 0 | S3-C2 DD ≤ 15% | S3-C3 PF ≥ 1.10 | S3-C4 ≥ 30 trades | S3-C5 best trade removed | S3-C6 ≤ 50% one instrument | S3-C7 neighbour signs |
| --- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| F1 | MET | **NOT_MET** | MET | **NOT_MET** | MET | n/a | MET |
| F2 | MET | **NOT_MET** | MET | MET | MET | n/a | MET |
| F3 | MET | **NOT_MET** | MET | MET | MET | n/a | MET |
| F4 | MET | **NOT_MET** | MET | **NOT_MET** | **NOT_MET** | n/a | MET |
| F5 | MET | **NOT_MET** | MET | **NOT_MET** | MET | **NOT_MET** | MET |
| F6 | MET | **NOT_MET** | MET | MET | MET | **NOT_MET** | MET |

No condition anywhere in this stage was recorded `NOT_EVALUABLE`. Every failure is a measured value
on the wrong side of a sealed threshold, not an absence of evidence.

**S3-C4** failed for F1 (15), F4 (13) and F5 (6). The lower-frequency exception was **not** invoked by
any candidate, and could not have been: the exception permits a *longer* evidence requirement, not a
smaller trade count. That was recorded in the sealed criteria before results precisely so a
low-frequency candidate could not be argued into it once its trade count was known.

**S3-C5** failed for F4 alone, and it is the condition doing the most interesting work in this stage.
F4's headline return is `0.2326` from 13 closed trades; remove the single best one and the
reconstruction gives `-0.00148` — negative. One trade out of thirteen is the difference between a
profitable breakout candidate and an unprofitable one, which is exactly the dependence the condition
exists to detect. The sealed method computes **two** removals and requires both to stay positive: the
trade with the largest equity multiple and the trade with the largest absolute P&L. For all six
candidates the two coincided (`j1_equals_j2: true`), so the stricter reading changed no verdict here
— but it was fixed in advance, so it could not have been chosen after seeing which reading a
candidate survived.

**S3-C6** applies only to the two multi-instrument candidates, and both failed it. F5's profit is
`EFA 12.38` and `MDY 8.56` of `20.94` total, so EFA contributes `0.5912`. F6's is `SPY 26.45` and
`SHY 6.78` of `33.23`, so SPY contributes `0.7960`. Neither is a marginal breach. For the four
single-instrument candidates the condition is recorded `NOT_APPLICABLE_BY_CONDITION_TEXT` with the
instrument count as evidence — see §9.

**S3-C7** passed for all six: 4 of 4 neighbours match the sign of their primary's net return in every
case. Every primary and every neighbour returned positive.

## 9. The one interpretation that had to be fixed in advance

S3-C6 reads "no single instrument contributes more than 50% of total strategy profit **for a
multi-instrument strategy**". A universal reading would make a single-instrument candidate contribute
100% of its own profit and fail automatically, which would render four of the six families §3
explicitly authorises untestable at this gate. That cannot be the intent of a clause whose stated
purpose is to detect concentration *across* instruments.

So the condition is evaluated for F5 and F6 and recorded `NOT_APPLICABLE_BY_CONDITION_TEXT` for
F1–F4, with the declared instrument count as the evidence. **This was sealed in
`stage3_gate_criteria.json` and stated in the pre-registration before any concentration figure
existed**, and it is surfaced here rather than buried, because a scope interpretation chosen after
seeing which candidates it would rescue is not an interpretation.

It changed no verdict in this stage. Every candidate it exempted failed on other conditions anyway.

## 10. The robustness neighbours

Each candidate declared exactly four neighbours in the sealed protocol, run over the **same** window
under the same base costs with the shutdown enforced. Only the **sign** of each neighbour's net
return is read; every other metric is recorded for the file and carries no gate weight.

| Candidate | Neighbour variations | Neighbour total returns |
| --- | --- | --- |
| F1 | SMA 150 / 175 / 225 / 250 | `0.5549`, `0.5374`, `1.1952`, `0.9350` |
| F2 | (150,10) / (250,10) / (200,5) / (200,20) | `0.2627`, `0.8977`, `0.1792`, `0.4026` |
| F3 | entry<5 / entry<15 / RSI 3 / exit SMA 10 | `0.6320`, `0.7323`, `0.2449`, `0.9150` |
| F4 | (20,10) / (100,50) / (50,10) / (50,50) | `0.4583`, `0.3940`, `0.3229`, `0.3850` |
| F5 | lookback 126 / 189 / 315 / universe without EFA | `0.3191`, `0.2604`, `0.2313`, `0.8656` |
| F6 | SMA 150 / SMA 250 / defensive IEF / defensive cash | `3.0437`, `0.4205`, `0.2728`, `0.3465` |

Two neighbours deliberately vary something other than a number — F5 drops EFA from its universe and
F6 replaces its defensive leg with cash — because a rotation whose profitability depends on the
presence of one member is exactly as fragile as one whose profitability depends on a lookback.

**No neighbour was promoted, and none may be.** F6's SMA-150 neighbour returned `3.0437` against its
primary's `0.3323`, and F1's SMA-225 neighbour returned `1.1952` against `0.9488`. Under §11 a change
to a parameter after seeing a result is material, and a material change creates a **new** candidate
that restarts at Gate 3 — it does not repair the one that disappointed. Those two numbers are
recorded here and nothing else happens to them. They are also, on their face, the kind of dispersion
across neighbours (`0.26`–`3.04` for F6) that argues against reading any single parameterisation's
result as a property of the family.

## 11. Determinism

Each primary was re-run from a fresh candidate object and compared on SHA-256 digests of canonical
JSON over the trade list and the equity curve. **All six identical.**

| Candidate | Trades digest | Equity digest | Identical |
| --- | --- | --- | :---: |
| F1 | `20da5c2c…c290` | `ab2532bd…ae3a` | yes |
| F2 | `e38c1081…2785` | `ac002f98…df50` | yes |
| F3 | `04e12f8d…e992` | `66506a82…51b5` | yes |
| F4 | `b0c08034…dc60` | `a653b345…e3ed` | yes |
| F5 | `27d747dc…489b` | `77b5b4cd…5d30` | yes |
| F6 | `05823f46…316d` | `1b0fac3a…6331` | yes |

The re-run constructs a **new** candidate object rather than reusing the one that produced the first
result. F5 carries per-run mutable state (`pending_target`), so a reused object would make this check
vacuous — it would compare a run against itself. The digests carry no run id, no timestamp, no label
and no path, a property Stage 2 established and its tests still assert.

All arithmetic in the signal path is `Decimal` under the pinned 34-digit context; no floating-point
value enters an indicator, a threshold comparison, or a cash computation. That is what makes these
digests reproducible rather than approximately equal.

## 12. Benchmarks, which do not gate this stage

Constitution §4 requires better risk-adjusted performance than cash, and does not require beating SPY
where drawdown is materially reduced. Neither is among Gate 3's seven hard conditions, so neither
gates this stage; both are reported for every candidate so a later gate reads them from evidence
rather than re-deriving them.

| Candidate | Candidate return | SPY index over the same window | Tradable SPY, shutdown enforced | Beats index | Beats tradable | Beats cash |
| --- | ---: | ---: | ---: | :---: | :---: | :---: |
| F1 | `0.9488` | `14.4383` | `1.0979` | no | no | yes |
| F2 | `0.5037` | `14.4383` | `1.0979` | no | no | yes |
| F3 | `0.7122` | `15.6909` | `1.2440` | no | no | yes |
| F4 | `0.2326` | `15.5389` | `1.2300` | no | no | yes |
| F5 | `0.2094` | `4.9210` | `0.3157` | no | no | yes |
| F6 | `0.3323` | `5.2290` | `0.3752` | no | no | yes |

The index column is the Gate 2 validated two-method total-return calculation, which reconciled on
every candidate's window inside the sealed `1e-6` tolerance. The tradable column is a real USD 100
cash account under the same base costs — an account, not an index — and it also trips the research
shutdown, which is why it is an order of magnitude below the index. Cash pays 0.00% because no T-bill
series was acquired at Stage 1; that makes the cash hurdle **easier** to beat, so "beats cash" is the
weakest of these columns, not the strongest.

Every candidate underperformed both readings of SPY. Under §4 that would not by itself disqualify a
candidate that materially reduced drawdown — but none of them reduced drawdown below 15% either, so
the question does not arise.

## 13. Six candidates against one dataset

Six specifications were tested against the same development data. A per-candidate criterion is not a
family-wise one: the probability that at least one of six passes by chance exceeds the probability
that any single pre-specified one does. This was disclosed in the pre-registration before any result,
and it is restated here rather than in a footnote.

Stage 3 applies no numerical multiple-comparisons correction, and pre-registration does not make the
arithmetic go away — it removes the freedom to *choose* the six after the fact, not the fact that six
were tried. The correction the constitution relies on is structural: an admitted candidate must still
survive Gate 4 robustness and a single sealed holdout read, and §12 prohibits selecting a winner from
holdout results at all.

In this stage the disclosure cuts the other way and is worth stating plainly: **six independent
chances at a pre-specified gate produced zero passes.** That is a stronger negative result than one
candidate failing would have been.

## 14. Conflicts found between frozen artifacts

Three, all recorded in the sealed criteria before any result, all reported and **none repaired**.
`SE100-GOV-0001` is frozen; a defect in it is reported, never edited.

**S3-CONFLICT-1 — the JSON companion for gate 3 is incomplete.** It carries five thresholds; the
frozen Markdown carries seven conditions — the same five plus profit concentration and neighbouring
parameter stability. The Markdown is authoritative and more restrictive, so all seven were evaluated
and all seven had to pass. This is the same defect class Stage 1 and Stage 2 each recorded against
their own gates.

**S3-CONFLICT-2 — gate 3 has no `pass_result`.** The affirmative token does not exist anywhere in the
constitution, so it was derived by negating the stated `fail_result`, as Stages 1 and 2 derived
theirs: `STRATEGY_REJECTED_IN_DEVELOPMENT` negates to `STRATEGY_ADMITTED_IN_DEVELOPMENT`, carrying the
stage prefix Stage 0 established with `STAGE_0_CONSTITUTION_VERIFIED`. **Both tokens were fixed before
any result**, which is what makes it defensible that this stage now issues the fail one.

**S3-CONFLICT-3 — the drawdown gate and the research shutdown are the same 15%.** Not a contradiction
but a coupling, stated before results rather than discovered in them. It turned out to be the
mechanism behind every rejection in this stage; see §7.

## 15. What this FAIL means, and what it does not

It means: six pre-specified rules, run on development data under declared costs with a next-open
fill and an enforced §5.1 shutdown, did not clear seven minimum-quality conditions. Every one of them
breached a 15% drawdown ceiling that is simultaneously a hard risk control on the account.

It does not mean any of these families cannot work, that the parameterisations tested are the best
available, or that a different specification would fail. Nor does it mean the reverse — nothing here
supports the claim that some other specification *would* pass, and searching for one on this same
development data is precisely the fitting this gate exists to prevent.

**No expected income, profit, or return is claimed for any period, past or future, anywhere in this
stage.** The figures above are historical simulations under a proxy cost model that has never been
validated against a real fill, and the largest of them belongs to a candidate that spent 83% of its
window switched off.

What follows from this verdict, under the constitution rather than by choice: no candidate proceeds
to Gate 4. A future generation of candidates is a new pre-registration and a new Gate 3, not an
amendment to this one. The observation in §7 — that the risk control and the quality gate are the same
number, so any candidate volatile enough to trip one has failed the other — is the most useful thing
this stage produced, and it belongs to whoever writes the next pre-registration.

## 16. Limitations that survive this stage

Every Stage 1 data limitation and every Stage 2 engine limitation is inherited whole; a research
result cannot be more trustworthy than the engine, and the engine cannot be more trustworthy than its
inputs. The twelve engine limitations are in
[STAGE_2_BACKTEST_ENGINE_REPORT.md](STAGE_2_BACKTEST_ENGINE_REPORT.md) §11 and the data limitations in
[STAGE_1_DATA_FOUNDATION_REPORT.md](STAGE_1_DATA_FOUNDATION_REPORT.md) §9. Additionally, specific to
this stage:

1. **One parameterisation per family is not a test of the family.** Six candidates were run; six
   families were not evaluated. F6's neighbours alone span `0.27` to `3.04`, which shows how much of
   a candidate's result is the particular number chosen.
2. **The results are not comparable across candidates.** F5 and F6 run over ~18 years, F1–F4 over
   ~28, on different market regimes. No ranking is implied and none was computed.
3. **Every candidate was switched off before its window ended**, between 1997 and 2010. Metrics
   computed over the full window — CAGR, Sharpe, exposure — are therefore descriptions of a live
   period followed by a long dead one, and none of them should be read as a property of the rule.
4. **Base costs only.** The stressed scenario (×2 on the complete assumption) belongs to the Gate 4
   robustness work and was not run here. Results under base costs are the optimistic case.
5. **The cost model remains a proxy**, not a measurement, and cannot be validated before paper
   trading at gate 7.
6. **Single-provider price data** with unquantified residual fund-closure bias, split-adjusted prices
   only, and no as-traded price levels. A systematic provider error would pass every check in this
   stage undetected.
7. **The drawdown measurement is session-close granularity.** The project holds no intraday data and
   none was imputed, so an intraday excursion past 15% that closed above it is invisible to S3-C2 —
   the measured figures are therefore lower bounds on true drawdown.
8. **No statistical significance test was performed on any result**, and none was pre-registered. The
   gate is a set of minimum-quality thresholds, not an inference procedure.

## 17. Tests

**389 passed, 0 failed, 0 skipped.** The 273 tests standing at pre-registration — 27 from Stage 0,
113 from Stage 1, 133 from Stage 2 — are unmodified; Stage 3 adds **116**: 69 unit and 47 adversarial.
Detail: [reports/stage3/STAGE_3_TEST_SUMMARY.md](../reports/stage3/STAGE_3_TEST_SUMMARY.md). Raw
output: [reports/stage3/pytest_stage3_output.txt](../reports/stage3/pytest_stage3_output.txt).

No test was weakened, skipped, `xfail`ed, or removed to make this gate reach a verdict.
`tests/conftest.py` was not touched; every Stage 3 fixture is defined locally. No test writes into
`data/`, `governance/`, `config/`, or `reports/`.

A failing stage carries a burden a passing one does not: it has to prove the evaluator **can** say
yes. Three clean controls sit at the top of the adversarial file — the sealed configuration loads and
recomputes all three digests, a synthetic candidate meeting every threshold is admitted with the
stage verdict PASS, and all thirty sealed variants build — so that every failure below them is
attributable to the injected defect and not to a harness that rejects everything. The 47 adversarial
tests then inject exactly one defect at a time: a tampered sealed byte, a deleted sealed file, an
unsealed parameter file, a missing seal, each of the five thresholds moved in the sealed file, a
loosened concentration limit, the lower-frequency exception falsely marked invoked, a deleted
condition, a fifth verdict value, a neighbour that did not run, a wrong neighbour count, a
thirty-first run, a validation-window window object, a look-ahead read, a mutated visibility bound, a
short warm-up, a missing symbol, an insufficient history, an unregistered experiment, `top_n` above
the one-position limit, an unsupported rebalance rule, and a tampered evidence field.

The evidence is reproducible and its self-digest was verified in both directions required by the
project's own rule. The recorded digest is
`561628d2f058d162c785bd30803df5b1762a4168af5037ee95d8b58bce896874`; recomputing it from the written
file, following the file's own `evidence_digest_covers` sentence literally, reproduces it exactly. The
negative control — recomputing with `generated_utc` **included** — gives a different value, so the
exclusion is not vacuous. And a fresh in-process run at a different timestamp produced the identical
digest, so the findings are a function of code and data only. Two-run stability alone would not have
been enough: a wrong-but-consistent coverage is stable, which is the defect that cost Stage 2 a full
regeneration.

## 18. Gate 3 assessment

Gates are conjunctive **within** a candidate; every hard condition must pass, and `NOT_RUN`,
`UNKNOWN`, or missing evidence is not a pass. Across candidates the stage verdict is a disjunction,
because Gate 3 asks whether a candidate worth carrying forward exists — not whether every candidate
tried is good. That rule was sealed in `verdict_token_derivation` before any result.

| Constitution §9 gate 3 condition | Verdict | Basis |
| --- | --- | --- |
| total return is positive | PASS for all six | `0.9488 / 0.5037 / 0.7122 / 0.2326 / 0.2094 / 0.3323` after base costs (§6) |
| maximum drawdown is no worse than 15% | **FAIL for all six** | `0.15373 / 0.15087 / 0.15771 / 0.17804 / 0.15060 / 0.17729`; all six tripped the §5.1 research shutdown (§7) |
| profit factor is at least 1.10 | PASS for all six | `5.2835 / 1.5007 / 1.9541 / 1.9728 / 7.7767 / 2.0106` over closed trades (§8) |
| at least 30 closed trades exist, unless a lower-frequency protocol predeclared a longer evidence requirement before results | **FAIL for F1, F4, F5** | 15, 13 and 6 closed trades; the exception was not invoked by any candidate and could not lower the floor (§8) |
| removing the single best trade leaves total return above 0% | **FAIL for F4** | `-0.00148` on both sealed removals, which coincided; the other five stay positive (§8) |
| no single instrument contributes more than 50% of total strategy profit for a multi-instrument strategy | **FAIL for F5, F6** | EFA `0.5912` of F5's profit, SPY `0.7960` of F6's; `NOT_APPLICABLE_BY_CONDITION_TEXT` for the four single-instrument candidates under the interpretation sealed in advance (§9) |
| reasonable neighboring parameter values do not reverse the sign of net return | PASS for all six | 4/4 neighbours match the primary's sign in every case; 24 neighbour runs, all positive (§10) |

**No candidate satisfies every hard condition. The stage fails.**

## 19. Authorization state after this stage

| Activity | State |
| --- | --- |
| Strategy research | **UNLOCKED — development window only** (1993-01-29 → 2021-07-31) |
| Backtesting | **UNLOCKED — validated engine, development window only** |
| Gate 4 robustness | **NOT REACHED** — no candidate was admitted |
| Validation window | LOCKED |
| Final holdout | **SEALED — not opened, not sampled, not counted** |
| Alpaca paper trading | LOCKED |
| Shadow live | LOCKED |
| Alpaca live trading | LOCKED |
| Capital or risk expansion | LOCKED |

`live_trading_authorized` remains `false`. No live order, cancel, replace, liquidation, or unattended
scheduling is authorized by anything in this stage.

There is no next authorized stage on the current line of work: Gate 4 requires an admitted candidate
and none exists. A further attempt at Gate 3 requires a **new** pre-registration declaring new
candidates, sealed before any code for them exists, under the same prohibition on revising a
specification because of a result it produced.

---

## Verdict

**FAIL — STAGE_3_STRATEGY_REJECTED_IN_DEVELOPMENT**

Six pre-registered candidates, one per authorised strategy family, were run over the development
window under sealed base costs, and none satisfies every hard condition of Gate 3. All six breach the
15% maximum-drawdown condition and all six trip the constitution §5.1 research shutdown, which is the
same threshold; three additionally fail the closed-trade floor, two the profit-concentration limit,
and one the best-trade-removal test. No candidate was revised, re-run, or promoted from a neighbour
after a result was seen, and no candidate proceeds to Gate 4.
