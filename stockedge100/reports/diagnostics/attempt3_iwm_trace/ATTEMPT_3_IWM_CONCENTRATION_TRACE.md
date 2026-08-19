# Attempt 3 — where IWM's 75% concentration came from

**Diagnostic id** `SE100-DIAG-A3-IWM-TRACE`  
**Subject** `SE100-G2-S3-C3-ROTATION-RA3-L03-K2-QUARTERLY#BASE` — the Generation 2 Stage 3 Attempt 3 representative, `BASE` cost scenario  
**Status** read-only diagnostic. **Not a governance artifact.**

This report carries **no verdict token, no gate condition, no checksum record and no artifact manifest**, and it is not an attempt at any gate. It explains an already-closed result. The Attempt 3 package at `reports/stage3_g2_attempt3/` is sealed and hashed; nothing in it was read for any purpose but comparison, and nothing was written into it. Attempt 3's recorded verdict — S3-C6 `NOT_MET`, concentration `0.7505030181086519114688128772635815` against `<= 0.50` — is unchanged and uncontested by this document.

Everything below lives in `reports/diagnostics/attempt3_iwm_trace/`, which is outside every `repo_state_id` pattern, so producing it perturbed no governance digest.

---

## 1. The reproduction is exact (this section gates every later one)

The detail in sections 2–5 is worth reading only if the run it came from is the sealed run. The trace imports the sealed strategy, engine, ledger and runner modules and calls `g2_runner_ra3.run_one` — nothing is reimplemented — then compares **43 values** against `reports/stage3_g2_attempt3/STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json` before emitting anything. The script exits without writing if any check disagrees.

**Result: 43/43 agree. Disagreements: none.**

The four determinism digests are the strongest of those checks, because two runs can agree on an equity curve while disagreeing about a ranking tie or a band transition that never reached an order:

| digest | sealed value | reproduced |
| --- | --- | --- |
| `trades_digest` | `90770d732cd1955234583686101f3844964eeada68ba8480db0c902f71a1dd50` | match |
| `equity_digest` | `6d184533a945a4d10a4fca54aa1e45e506fabfca2629e6da51806ff0e2d75a46` | match |
| `ranking_digest` | `2881c0f6011b5d87f30920446551fae82500207b3d0291d091271abeac79b01b` | match |
| `risk_state_digest` | `85e551b3c17fb6d25a55bb69f6669836cdc3feca64a8ff92a293960997842905` | match |

And the aggregates the operating instruction named specifically:

| quantity | sealed | reproduced |
| --- | --- | --- |
| total return | `0.10337843028513874006` | match |
| starting equity | `100.00` | match |
| final equity | `110.3378430285138740060` | match |
| fills | `150` | match |
| closed trades | `62` | match |
| closed episodes | `62` | match |
| open episodes at end | `2` | match |
| net closed-episode P&L | `9.94` | match |
| gross profit | `46.70` | match |
| gross loss | `36.76` | match |
| multi-leg episodes | `11` | match |
| distinct symbols traded | `24` | match |
| **IWM total contribution** | `7.46` | match |
| **IWM share of net** (S3-C6 measured) | `0.7505030181086519114688128772635815` | match |
| shutdown session | `None` | match |

All 24 per-symbol contributions in the sealed `pnl_by_instrument` were compared individually and all 24 agree; they are the remaining rows of `reproduction_checks` in the JSON.

### How the momentum values were recovered without touching anything sealed

The momentum reading that decided each entry is **not** recorded in the sealed evidence. The selection log keeps sessions, ranked symbols, exclusions, exits and entries — it does not keep the ranking *values*, which survive only inside `ranking_digest`. Rather than recompute the signal (which would be a reimplementation, and would prove nothing about what the sealed run actually saw), the trace observes it:

- `build_candidate` is wrapped **in this process only**, so the candidate's bound `rank` method is shadowed by a closure that calls the sealed method and records what it returned. The sealed method's inputs, outputs and side effects are untouched; the wrapper adds no computation.
- `RotationEngineRA3` is wrapped the same way and purely to keep a reference to the instance, so its per-session risk-state lines (`session|band|lockout|vol_scalar|combined_scalar`) can be read back. The class is not subclassed and no method of it is wrapped.

Neither wrapper is *argued* to be harmless — it is **measured**. All four sealed digests, including `ranking_digest` and `risk_state_digest`, are byte-identical with the wrappers installed. 53 rebalances were observed against a sealed `scheduled_rebalance_sessions` of 53.

Before running anything, the trace also re-ran the runner's own `verify_prior_attempt_modules()`: `module_count` 17, `modules_verified` 17, `modules_that_moved` `[]`.

No file under `governance/`, `config/`, `src/`, `tests/` or any `reports/stage3_g2*/` directory was written. Neither holdout partition was read. No broker, credential or order path was touched, and no live-trading authorization was implied or altered.

---

## 2. IWM, episode by episode

IWM was entered **4 separate times** and closed all 4 times. There is no single long holding period: each episode ran exactly one quarter, entry fill to exit fill.

| # | entry fill | exit fill | cal. days | sessions | gap since prior IWM exit (cal. days) | entry rank | entry signal (trailing 3-mo total return) | entry notional | closed P&L | return on entry capital | IWM running total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2011-01-04 | 2011-04-04 | 90 | 62 | — | 2 of 34 | 17.83% | 25.85 | 1.48 | 5.73% | 1.48 |
| 2 | 2012-01-04 | 2012-04-03 | 90 | 62 | 275 | 2 of 34 | 23.52% | 12.50 | 1.52 | 12.16% | 3.00 |
| 3 | 2017-01-04 | 2017-04-04 | 90 | 62 | 1737 | 2 of 34 | 9.90% | 12.60 | -0.03 | -0.24% | 2.97 |
| 4 | 2021-01-05 | 2021-04-05 | 90 | 61 | 1372 | 2 of 34 | 26.99% | 26.06 | 4.49 | 17.23% | 7.46 |

Reading the columns that matter:

- **Duration.** Every episode is 90 calendar days (61–62 sessions) — one full quarterly interval, entered on the fill after one rebalance and sold on the fill after the next. IWM was held for 247 of the run's 3276 sessions, i.e. 7.54% of the time.
- **Gaps.** The gaps between consecutive IWM episodes are 275, 1737, 1372 calendar days. These are not brief interruptions in a continuous holding; they are years. IWM left the book entirely and came back.
- **Justification at entry.** Every entry was at rank 2/2/2/2 of 34 ranked members, on a positive trailing 3-month total return of 17.83%, 23.52%, 9.90%, 26.99%. None was a marginal or artefactual pick.
- **P&L shape.** The running total is not steady. Episode 4 alone contributed `4.49` — 60.19% of IWM's `7.46`, and 45.17% of the whole run's net `9.94`. The first three episodes together contributed `2.97`.
- **Hit rate.** 3 of 4 episodes were profitable and 1 lost money — episode 3 at `-0.03`, essentially flat.

### Why two of the four entries were half the size of the others

The entry notionals split cleanly in two: `25.85` and `26.06` against `12.50` and `12.60`. This is not cash starvation and not an equity collapse — cash on hand at each decision was ample and equity was near 100 every time. It is the RA3-4 de-risk ladder, and the run's own risk-state lines say so:

| # | decision session | equity | cash | drawdown from HWM | ladder band | combined risk scalar | unscaled target | scaled target | actual entry |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2011-01-03 | 103.3724 | 76.56 | 6.5119% | 0 | 1.000000000 | 25.8431 | 25.8431 | **25.85** |
| 2 | 2012-01-03 | 100.0673 | 99.35 | 9.5010% | 1 | 0.500000000 | 25.0168 | 12.5084 | **12.50** |
| 3 | 2017-01-03 | 100.8380 | 87.47 | 8.8040% | 1 | 0.500000000 | 25.2095 | 12.6047 | **12.60** |
| 4 | 2021-01-04 | 104.3671 | 76.64 | 5.6124% | 0 | 1.000000000 | 26.0918 | 26.0918 | **26.06** |

The target weight per position is the constant `0.250000000` of equity for this variant, so the only thing that can vary the budget is the combined risk scalar. The sealed RA3-4 band table the engine loaded:

| band | drawdown from | drawdown to (exclusive) | scalar |
| --- | --- | --- | --- |
| 0 | 0.00 | 0.08 | 1.00 |
| 1 | 0.08 | 0.10 | 0.50 |
| 2 | 0.10 | — (no upper bound) | 0.25 |

Episodes 2 and 3 were decided while the account sat in band 1, so the position budget was halved; episodes 1 and 4 were decided in band 0 at full size. The `scaled target` column predicts the `actual entry` column to the cent in all four cases. **The risk architecture was reducing IWM's concentration, not producing it.**

One consequence, stated as arithmetic and not as a recommendation: at full size, episode 2's 12.16% return on capital would have produced roughly double its `1.52`, which would have **raised** IWM's measured share, not lowered it.

### Was each pick a genuinely strong reading? IWM's rank at all 53 rebalances

IWM entered the top 2 at only 4 of 53 rebalances (7.55%). Its best rank across the whole run was 2 and its worst 33 — it was never the top-ranked member. At the rebalance immediately after each entry it had already fallen out of the top 2, which is why every episode lasted exactly one quarter:

| entry decision | rank | signal | next rebalance | rank then | signal then |
| --- | --- | --- | --- | --- | --- |
| 2011-01-03 | 2 | 17.83% | 2011-04-01 | 4 | 8.28% |
| 2012-01-03 | 2 | 23.52% | 2012-04-02 | 8 | 14.02% |
| 2017-01-03 | 2 | 9.90% | 2017-04-03 | 32 | 0.67% |
| 2021-01-04 | 2 | 26.99% | 2021-04-01 | 5 | 14.33% |

The full 53-row rank history, with the top of each ranking, is in `episode_ledger.json` under `iwm.rank_at_every_rebalance`.

One pattern is visible, and is recorded here as an observation rather than a conclusion: all four top-2 appearances fall on the **early-January** rebalance. Four observations support no inference, and no test of seasonality was performed — see section 7.

---

## 3. Comparison — the other 23 traded symbols

62 closed episodes across 24 symbols, plus 2 still open at the run end (IEF, entered 2011-10-04, VNQ, entered 2021-07-02 — neither is IWM). Episode counts and duration statistics only, as instructed; the full per-episode detail for all 24 symbols is in the JSON.

| symbol | episodes closed | total cal. days held | mean | median | min | max | total P&L | share of net | best ep. | worst ep. | winners | mean entry rank |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **IWM** | 4 | 360 | 90 | 90.0 | 90 | 90 | **7.46** | 0.7505 | 4.49 | -0.03 | 3/4 | 2 |
| VWO | 2 | 184 | 92 | 92.0 | 92 | 92 | 5.00 | 0.5030 | 4.09 | 0.91 | 2/2 | 1.5 |
| IYR | 2 | 182 | 91 | 91.0 | 87 | 95 | 3.53 | 0.3551 | 2.86 | 0.67 | 2/2 | 2 |
| XLK | 3 | 210 | 70 | 91 | 24 | 95 | 3.20 | 0.3219 | 2.68 | -2.13 | 2/3 | 1.67 |
| EEM | 4 | 365 | 91.2 | 92.0 | 89 | 92 | 2.86 | 0.2877 | 2.09 | -0.70 | 3/4 | 1.5 |
| TLT | 10 | 1022 | 102.2 | 92.5 | 9 | 185 | 2.55 | 0.2565 | 2.85 | -1.99 | 5/10 | 1.2 |
| VNQ | 3 | 194 | 64.7 | 91 | 8 | 95 | 2.50 | 0.2515 | 3.05 | -2.30 | 2/3 | 1.25 |
| VGK | 2 | 183 | 91.5 | 91.5 | 90 | 93 | 1.53 | 0.1539 | 0.77 | 0.76 | 2/2 | 1.5 |
| XLE | 3 | 357 | 119 | 91 | 84 | 182 | 1.29 | 0.1298 | 2.73 | -2.02 | 2/3 | 1 |
| IEF | 1 | 94 | 94 | 94 | 94 | 94 | 0.55 | 0.0553 | 0.55 | 0.55 | 1/1 | 2 |
| SHY | 2 | 156 | 78 | 78.0 | 65 | 91 | 0.40 | 0.0402 | 0.43 | -0.03 | 1/2 | 1.5 |
| XLP | 1 | 91 | 91 | 91 | 91 | 91 | 0.05 | 0.0050 | 0.05 | 0.05 | 1/1 | 2 |
| EFA | 1 | 91 | 91 | 91 | 91 | 91 | 0.00 | 0.0000 | 0.00 | 0.00 | 0/1 | 2 |
| MDY | 1 | 92 | 92 | 92 | 92 | 92 | -0.01 | -0.0010 | -0.01 | -0.01 | 0/1 | 2 |
| TIP | 2 | 156 | 78 | 78.0 | 65 | 91 | -0.51 | -0.0513 | -0.13 | -0.38 | 0/2 | 1.5 |
| DVY | 3 | 185 | 61.7 | 88 | 5 | 92 | -1.00 | -0.1006 | 0.64 | -2.19 | 2/3 | 1.67 |
| DIA | 1 | 90 | 90 | 90 | 90 | 90 | -1.10 | -0.1107 | -1.10 | -1.10 | 0/1 | 2 |
| LQD | 1 | 64 | 64 | 64 | 64 | 64 | -1.77 | -0.1781 | -1.77 | -1.77 | 0/1 | 2 |
| XLF | 2 | 138 | 69 | 69.0 | 46 | 92 | -2.09 | -0.2103 | 0.25 | -2.34 | 1/2 | 2 |
| QQQ | 6 | 403 | 67.2 | 79.5 | 14 | 93 | -2.15 | -0.2163 | 1.28 | -1.88 | 3/6 | 2 |
| XLB | 1 | 23 | 23 | 23 | 23 | 23 | -2.21 | -0.2223 | -2.21 | -2.21 | 0/1 | 1 |
| XLU | 1 | 35 | 35 | 35 | 35 | 35 | -2.49 | -0.2505 | -2.49 | -2.49 | 0/1 | 2 |
| XLI | 4 | 248 | 62 | 67.5 | 22 | 91 | -3.59 | -0.3612 | 0.55 | -2.38 | 2/4 | 1.5 |
| XLV | 2 | 83 | 41.5 | 41.5 | 29 | 54 | -4.06 | -0.4085 | -1.64 | -2.42 | 0/2 | 1 |

What this puts in context:

- **IWM's trading pattern is unremarkable.** Its 4 closed episodes sit against a per-symbol median of 2 and a maximum of 10 (TLT). Its 90-day holds are at the whole-ledger median of 91 calendar days. Nothing about how often IWM was traded, or how long it was held, is an outlier.
- **What is exceptional is the P&L, not the exposure.** IWM's `7.46` against a net of `9.94` leaves `2.48` for the other 23 symbols combined — 12 of the 24 net positive, 11 net negative.
- **The denominator is what makes the share large.** Gross profit over closed episodes is `46.70` and gross loss `36.76`; they nearly cancel, leaving `9.94`. IWM's share of *gross profit* is `0.1597430406852248394004282655246253` — 15.97%. S3-C6's sealed basis divides by the **net** sum over all closed episodes, which is smaller by a factor of 4.70.
- **A second symbol also exceeds the ceiling on the same basis.** VWO's share of net is `0.5030181086519114688128772635814889`. S3-C6 measures the largest contributor, so IWM is what the gate reported — but the concentration failure was not a near miss caused by one instrument.

For completeness on the basis, quoted verbatim from the Attempt 3 evidence's own S3-C6 record:

> For each instrument, contribution = sum of pnl over that instrument's closed EPISODES, divided by the sum of pnl over all closed episodes.

---

## 4. Cross-check against the sealed `pnl_by_instrument`

The four IWM episode P&L values are `1.48`, `1.52`, `-0.03`, `4.49`, summing to `7.46`. The sealed `pnl_by_instrument['IWM']` is `7.46`.

**They agree exactly. There is no discrepancy to report.** The share recomputes to `0.7505030181086519114688128772635815`, identical to the sealed measured value `0.7505030181086519114688128772635815` — including its trailing digits, which match only when the division runs inside the engine's 34-digit decimal context rather than at the default precision.

The episode ledger also reconciled against the frozen `Portfolio.trades` on all of `entry_cash`, `exit_cash`, `dividends`, `pnl`, across 62 closed episodes and 62 closed trades, with 0 mismatches. The two *totals* differ — episodes `9.94` against trades `8.72346822944634573880906138223998`, a gap of `1.21653177055365426119093861776002` — because the frozen `Portfolio` credits a `Trade` only on the sale that zeroes a position, so `52.98` of partial-trim proceeds across 11 multi-leg episodes never reaches the trade ledger. That is the already-recorded `G2A2-CONFLICT-18`, and it is exactly why S3-C6's declared basis is the episode ledger and not the trade ledger. Nothing in this diagnostic depends on the trade-ledger total.

---

## 5. The question, answered plainly

> Was IWM's dominance driven by one long holding period, or by the strategy repeatedly and separately re-selecting it based on genuinely strong momentum readings at multiple different points in time?

**The *selection* was repeated and genuine. The *dominance* rests on one of those four selections.** Both halves of that sentence are needed; either alone misdescribes the run.

1. **It was not one long holding period, and not close to one.** IWM was bought and sold four separate times — in 2011, 2012, 2017, 2021 — each time for exactly one quarter, with gaps of 275, 1737, 1372 calendar days between them. It was out of the book for the large majority of the run (7.54% of sessions held).
2. **Each of the four entries was justified by a genuinely strong reading, not an artefact.** IWM ranked 2/2/2/2 of 34 at the four decisions, on trailing 3-month total returns of 17.83%, 23.52%, 9.90%, 26.99%. Across all 53 rebalances it reached the top 2 only those four times, never ranked first, and had fallen to rank 4/8/32/5 by the following rebalance — which is what sold it. The signal was not quietly favouring IWM; it picked it rarely and dropped it as soon as it faded.
3. **But the dollar dominance is concentrated inside those four episodes.** `4.49` of IWM's `7.46` — 60.19% — came from the single 2021-01-05 → 2021-04-05 episode, which is by itself 45.17% of the entire run's net result. Two of the remaining three contributed about `1.5` each and one contributed `-0.03`. So the concentration is not the product of a strategy that kept finding IWM; it is the product of one quarter in early 2021 being the strategy's best single quarter, in an instrument the strategy had selected on merit four times in thirteen years.

There is a fourth fact that frames the other three, and it is arguably the more important one:

- The run's equity high-water mark is `110.5728220150692044628`, set on `2009-12-28` — about seventeen months into a thirteen-year run — and final equity is `110.3378430285138740060`, which is **below it**. The strategy spent 1491 of 3276 sessions in ladder band 1 (8–10% below the mark) and never made a new high after 2009-12.
- Net closed-episode P&L is `9.94` out of `46.70` gross profit and `36.76` gross loss. The denominator S3-C6 divides by is small because almost everything the strategy earned, it also gave back.

Read together: IWM does not dominate because it was over-selected or over-held. It dominates because it produced one large win in a book whose other 23 instruments netted `2.48` between them over thirteen years. A concentration measure with a net denominator reports that as an instrument-selection problem; what the trace shows is a **thin-net** problem.

---

## 6. Findings offered for human review (nothing here has been applied)

Per the operating instruction, none of the following has been used to change any parameter. The drafted Attempt 4 pre-registration has **not** been edited, and was not consulted in order to tune anything. These are observations for a human to weigh.

1. **A forced rotation cap constrains holding duration or repeat selection, and neither is what produced this failure.** Each IWM episode lasted a single rebalance interval — already the minimum a quarterly variant can hold — and IWM was never re-selected consecutively: its gaps were 275, 1737, 1372 calendar days. On this representative, a cap of that kind would not have bound on any of the four episodes, and S3-C6 would have failed identically. That does not make the cap wrong; it was chosen as a general mechanism and may be right for reasons outside this variant. It is raised here as a design question for a human, precisely because it must not be resolved by retuning against these dates.
2. **Two of 24 symbols exceed the 0.50 ceiling on the sealed basis** — IWM `0.7505030181086519114688128772635815` and VWO `0.5030181086519114688128772635814889`. With a net of `9.94` across 62 episodes, *any* single instrument clearing about `4.97` fails the condition. The binding constraint is the size of the net, not the behaviour of any one instrument. A strategy family that keeps producing a thin net will keep failing S3-C6 however its selection is capped.
3. **The risk architecture was working against the concentration, not for it.** The de-risk ladder halved two of IWM's four entries. Any future architecture that de-risks *less* would, all else equal, tend to **increase** measured concentration on a run like this one — which is the opposite of the direction Attempts 2 and 3 were moving. Worth stating because RA3 already is RA2 minus one de-risk tier.
4. **A note in the repository's own guidance appears to label a denominator it is not using.** `CLAUDE.md` contrasts IWM's `0.7505` of net with `0.2413` of gross. On this run, IWM over **gross episode profit** (`46.70`) is `0.1597430406852248394004282655246253`. The `0.2413` figure reproduces exactly as IWM over the **sum of positive per-symbol contributions** (`30.92`): `0.2412677878395860284605433376455369`. Both are far below `0.50`, so the lesson the note draws is unaffected and the sealed verdict is unaffected — but they are different quantities, and a future reader could take the wrong one for "gross". Flagged, not edited.

---

## 7. What this trace could not determine

Stated as limits, rather than guessed at:

- **Why all four top-2 appearances fall in early January.** The pattern is real in the data and it is four observations. No seasonality test was run and none is implied; testing it would be a new research question needing its own pre-registration, not a diagnostic finding.
- **The intra-episode path of any position.** The engine records portfolio cash and equity per session, not a per-symbol mark, so a symbol's value inside an episode is not separable from the book while more than one position is open. *Where* in the quarter episode 4's `4.49` accrued is therefore not answerable from this run's records.
- **Whether IWM's dominance holds under the stress cost scenario.** Only the base-cost run `#BASE` was reproduced, as instructed. The sealed evidence carries a separate `stress_evaluation`; this trace neither reproduced nor re-derived it, and says nothing about it.
- **Anything about the other Attempt 3 variants.** Only the representative was run. Every per-symbol, duration and rank statistic here describes this one variant.
- **Whether a different lookback, `top_k` or rebalance frequency would concentrate less.** That is a grid question, the Attempt 3 grid is spent, and running it here would be a new search rather than a diagnostic.
- **The counterfactual P&L of the two half-sized entries.** Section 2 gives the arithmetic of doubling episode 2's return on capital, which is division, not a simulation. What the run would actually have done at full size — different cash, different clamps, different subsequent bands — was not simulated and is not claimed.
- **The exact decision session for an entry whose rebalance adjacency fails.** None occurred: every entry fill in the ledger was immediately preceded in the run's own session index by a rebalance session, so every `entry_momentum` in the JSON carries a real value. The trace is written to emit `null` with a note rather than a nearest guess if that ever stops being true.

---

## 8. Files and provenance

| role | path |
| --- | --- |
| this report | `reports/diagnostics/attempt3_iwm_trace/ATTEMPT_3_IWM_CONCENTRATION_TRACE.md` |
| supporting JSON — full ledger (64 episodes), 53-rebalance rank history, all 43 checks | `reports/diagnostics/attempt3_iwm_trace/episode_ledger.json` |
| sealed evidence compared against (read-only) | `reports/stage3_g2_attempt3/STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json` |
| trace script, outside the governed tree | `_scratch/a3_iwm_trace.py` |
| sizing addendum, outside the governed tree | `_scratch/a3_iwm_sizing.py` |
| this report's generator, outside the governed tree | `_scratch/a3_iwm_report.py` |

Run executed by `stockedge100.strategies.g2_runner_ra3.run_one`; ledger built by `stockedge100.backtest.g2_episodes_ra1.build_episode_ledger`; attribution taken from `EpisodeLedger.pnl_by_symbol() -- the same call condition_6_ra1 makes`. Sealed modules were imported and not modified on disk.

Entry-to-decision mapping rule, verbatim from the JSON: *An episode's entry_session is the fill session. The decision session is the latest rebalance session strictly before it, required to be the immediately preceding session in the run's own session index; when that adjacency does not hold, the momentum value is reported as null rather than guessed.*

**No verdict is issued by this document.** It is a diagnostic. Attempt 3's `FAIL` on S3-C6 stands exactly as sealed, and no gate, freeze record, manifest or `repo_state_id` was touched to produce it.

