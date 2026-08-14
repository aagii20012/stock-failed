# Stage 3 Attempt 2 — Strategy Research Pre-registration

**Document ID:** `SE100-GOV-0007`
**Project:** StockEdge100
**Generation:** 1
**Stage:** 3 — gate 3, development admissibility. Second attempt, pre-registration written before any
strategy code for its candidates existed.
**Attempt ID:** `SE100-S3-A2`
**Declared (UTC):** 2026-08-10T11:37Z — the authoritative timestamp and the digest of every
pre-registered file are in `governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.json`, which is generated
after this document and therefore cannot be quoted inside it.
**Status of this document:** pre-registration. It constrains Stage 3 Attempt 2. It does not modify,
supersede, reinterpret, or extend `SE100-GOV-0001`, and it does not modify, supersede, repair, or
re-run any Attempt 1 artifact.

> **Document numbering.** `SE100-GOV-0004` is unused across the whole tree. This document takes
> `0007`, the next number after the highest in use, rather than filling a gap whose reason is not
> recorded anywhere on disk.

---

## 1. Why this document exists

Attempt 1 pre-registered six candidates, one per authorised strategy family, sealed the specification
before any strategy code existed, ran thirty variants over the development window, and rejected all
six. The verdict is on disk as `FAIL — STAGE_3_STRATEGY_REJECTED_IN_DEVELOPMENT`, run
`SE100-R-20260810T101622Z`. Every candidate breached the same condition: maximum drawdown had to be
at or below 15%.

That failure is a deliverable, not an accident to be tidied away. Constitution §2 item 8:

> **Negative results are deliverables.** Rejected strategies are recorded and not silently recycled.

So the question this attempt exists to answer is not "how do I make one of those six pass". That
question has only bad answers, and the constitution closes each of them: §2 item 3 states

> **No result-driven rule changes.** A failed gate cannot be weakened after results are observed.

The 15% ceiling is therefore fixed, the six rejected candidates are permanently rejected as
specified, and no parameter of any of them may be moved now that its result is known.

What is left is a different and legitimate question, and it is the one this document pre-registers:

> **Can structurally lower-risk, economically intelligible strategies remain meaningfully profitable
> after costs while satisfying the unchanged 15% maximum-drawdown ceiling of Gate 3 and every other
> frozen Gate 3 condition?**

The distinction between that question and a retune is the whole substance of this document, and it is
thinner than it sounds. Attempt 1's results are known. Choosing to build risk control into new
candidates *because* the first six blew through the ceiling is an adaptation, and pretending
otherwise would be the dishonest move available here. §8 below discloses it rather than burying it.
What makes this an attempt rather than a repair is that the risk control is declared as structure in
a new specification, before any code for it exists, and is not a dial turned on a candidate whose
equity curve has already been seen.

At the moment this document is sealed there is no strategy module, no signal, no equity curve, no
trade list, and no result artifact for any Attempt 2 candidate. That is verified by measurement, not
asserted — see §10 — and the sealing program refuses to run otherwise.

---

## 2. Pre-registered files

| File | Content |
|---|---|
| `config/stage3_attempt2_strategy_protocol.json` | `SE100-CFG-3003`: the §8 experiment specifications for three candidates — hypothesis, economic rationale, distinction from Attempt 1, universe, exclusions, eligibility, timing, features, parameters, permitted grid, entry/exit/sizing/conflict rules, holding period, loss control, re-entry, robustness neighbours, iteration budget, cumulative experiment count, shared rules, indicator definitions, the shared risk architecture, benchmarks, and the recorded interpretations |
| `config/stage3_attempt2_gate_criteria_binding.json` | `SE100-CFG-3004`: binds Gate 3's sealed measurement spec by digest, re-derives only its two candidate-set-specific enumerations, and freezes the `admissible_candidate_exists` rule, the neighbour status, the shutdown behaviour, and the rerun policy |
| `governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.md` | this document |
| `governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.json` | authoritative declaration timestamp, digests of the three files above, upstream input digests, and the measured contamination state at sealing |
| `governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.sha256` | checksum record covering the four files above |

The checksum record uses **project-root-relative** paths, matching the Stage 1, Stage 2, and
Attempt 1 convention and differing deliberately from `STAGE_0_FREEZE.sha256`, which records bare
filenames:

```bash
cd stockedge100 && sha256sum -c governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.sha256
```

Neither record contains its own digest; nothing hashes itself. No digest appears in this document at
all — the values live in the JSON, and this prose points there.

Attempt 1's files are untouched. `config/stage3_strategy_protocol.json` and
`config/stage3_gate_criteria.json` keep the digests they had before this session, and this document
adds files rather than editing any.

---

## 3. Whether a second attempt is permitted at all

This was settled from on-disk frozen governance before any candidate was designed, because if the
answer were no then the correct output of this session would have been a blocker and no
pre-registration. The prompt authorising the session was not treated as authority for it.

**Answer: yes** — by a new pre-registration declaring new candidates, sealed before any code for them
exists. No erratum, no new project generation, and no separate human written approval is required at
this gate. The full determination with all citations is in `SE100-CFG-3003`
`authorization_determination`. The load-bearing parts:

**The mechanism.** Constitution §11 defines materiality and its consequence:

> A change that affects universe, timing, cost, signal, parameter range, metric, threshold, or data
> partition is material.

> A material change after seeing validation results creates a new candidate and restarts at Gate 3.

The scope gap is stated rather than glossed: that second clause is triggered by seeing **validation**
results, and Attempt 1's results are development-only, so it does not literally cover this case. It
is relied on *a fortiori*. If a material change made after seeing the more strongly protected
validation results is permitted and costs no more than restarting at Gate 3, a material change made
after seeing only development results cannot require more — and Gate 3 is exactly where Attempt 2
begins. The constitution states no stricter consequence for the development case, and this attempt
does not read that silence as permission for anything beyond restarting at Gate 3.

**The most directly on-point clause,** also §11:

> Safety thresholds may be tightened without promoting a failed strategy, but the change must still
> be versioned.

Attempt 2 tightens safety and promotes no failed strategy. F1 through F6 are not re-run, not edited,
not superseded, and not carried forward. The versioning requirement is met with a new artifact ID at
version 1.0.0, not an edit to `SE100-CFG-3001`.

**Attempt 1 anticipated this.** `governance/STAGE_3_STRATEGY_RESEARCH_REPORT.md` §19:

> A further attempt at Gate 3 requires a new pre-registration declaring new candidates, sealed before
> any code for them exists, under the same prohibition on revising a specification because of a
> result it produced.

and §15:

> A future generation of candidates is a new pre-registration and a new Gate 3, not an amendment to
> this one.

**No attempt limit exists.** `STAGE_0_CONSTITUTION.json`'s gate entry with `id: 3` carries a
`fail_result` and no once-only clause, no attempt cap, and no `manual_written_approval_required`
flag; the only gate carrying that flag set true is gate 9. Attempt 1's own §7 item 8 bars a seventh
candidate "in this session" — a bar scoped to that session, which this one does not reach, and
Attempt 2 adds no candidate to Attempt 1's set.

**Not all six families again.** Constitution §3's scope table reads that the six families "may be
researched separately". The modal verb is permissive. §8's "Strategy families must first be tested
independently" is a precondition on *combining* strategies — its own next sentence is "Combining
strategies is prohibited until each component has an independent verdict" — not a requirement to
re-test six families in every attempt. Attempt 2 combines nothing.

---

## 4. Three candidates, not six

| ID | Family | Universe | Signal | Max hold |
|---|---|---|---|---|
| `SE100-S3A2-C1-PULLBACK-RA1` | pullback | SPY | long when `close > SMA(200)` and `close < SMA(10)` | 20 sessions |
| `SE100-S3A2-C2-MEANREV-RA1` | mean reversion | SPY | enter when `RSI(2) < 10`; exit when `close > SMA(5)` | 10 sessions |
| `SE100-S3A2-C3-DEFENSIVE-RA1` | defensive regime logic | SPY, SHY | SPY when `close(SPY) > SMA(200)(SPY)`, else SHY, else cash | 252 sessions |

Three is the smallest set that can answer the research question. Attempt 1 demonstrated that six
candidates is six parameterisations, not six families, and paid for the demonstration. Adding
candidates here would buy no additional coverage of the question — which is about the *risk
architecture*, shared identically across all three — while multiplying the multiple-testing burden
declared in §8.

Three retained families, and the reason each is retained: pullback and mean reversion are the two
Attempt 1 families that traded often enough to have a credible closed-trade count under a
30-trade floor, and defensive regime logic is retained so that at least one candidate declares more
than one instrument and Gate 3's concentration condition is live rather than not-applicable for the
whole attempt.

**Three families excluded prospectively, on structural grounds recorded before any Attempt 2 result
exists:** trend/momentum, breakout, and ETF rotation. Their Attempt 1 counterparts closed 15, 13,
and 6 trades respectively against a floor of 30. That is a property of how often those rule forms
change position, not of the parameters chosen: a lower fixed exposure and an earlier exit make a
position smaller and shorter, they do not make a slow-moving trend rule trade more often. Under a
risk architecture that only ever reduces exposure, none of the three has a credible route to 30
closed trades, so running them would spend three of the attempt's variants on a condition already
known to be structurally out of reach. The trade counts are the only Attempt 1 numbers used
anywhere in the design, they are used only for this frequency argument, and no parameter anywhere in
Attempt 2 was chosen from an Attempt 1 return, drawdown, profit factor, or equity path.

The consequence is accepted and recorded: Attempt 2 cannot say anything about whether trend,
breakout, or rotation strategies can satisfy Gate 3 under a lower-risk architecture. That question
stays open.

**No combination.** Constitution §8 permits combining only once each component has an independent
verdict, and assembling a combination now — after seeing which components failed — would be a
post-result construction of exactly the kind §2 item 3 forbids. Generation 1 also holds at most one
risky position at a time, which makes simultaneous multi-strategy allocation impossible in any case.

---

## 5. The risk architecture, and why it is not a stop at 14.99%

All three candidates share one risk architecture, `RA1`. Sharing it is deliberate: it is the object
under test, and specifying it once means its degrees of freedom are counted once rather than three
times.

| Mechanism | Rule |
|---|---|
| `RA1-1` fixed exposure ceiling | `f_base = 0.50` of equity, against Generation 1's permitted 95% |
| `RA1-2` volatility targeting | entry only: `f = min(f_cap, 0.10 / VOL20)`, floor `0.05`; never increases exposure |
| `RA1-3` per-position loss control | exit when the position is `0.08` below its entry decision close |
| `RA1-4` maximum holding period | per candidate: 20, 10, and 252 decision sessions |
| `RA1-5` account de-risking ladder | entry-only `f_cap`: `0.50` below 8% drawdown, `0.25` from 8% to 10%, `0.125` at or above 10% |
| `RA1-6` re-entry delay | 5 decision sessions after a loss-control or max-hold exit, per symbol |
| `RA1-7` flat-first | an exit and an entry never share a fill session |
| `RA1-8` all-or-nothing | a position is opened in full or not at all |

**Where the numbers come from.** Constitution §5.2 sets an account-level soft risk halt at 8% below
the live high-water mark and a hard risk halt at 10%. Those two distances, and only those, supply
every drawdown-shaped constant in `RA1`: the ladder's two rungs are 8% and 10% verbatim, and `RA1-3`
adopts the 8% figure at the position level. Taking the numbers from a frozen artifact rather than
choosing them keeps them out of the search space. `f_base = 0.50` then follows: with `L = 0.08`, the
worst nominal single-position cost to the account is `0.50 x 0.08 = 0.040` — half the soft-halt
distance and 40% of the hard-halt distance, so no single position can, at its declared limit, carry
the account through a halt rung by itself.

Two things are the researcher's own choice and are declared as such: adopting an account-level halt
distance at the position level, and halving the exposure multiplier at each rung. The second is
probed indirectly by the `f_base` neighbour in every candidate. Note also that §5.2's halts govern
the live phase, whereas Attempt 2 runs in development — the numbers are borrowed for their
provenance, not applied in their original operational role.

**Why this is structural and not a mechanical stop just under the ceiling.** No rule in `RA1`
references 15%, references the shutdown state, or references the distance to either. The deepest
level any rule reacts to is 10%. The 15% ceiling is enforced by the engine, and no candidate rule can
see it. The prohibition on a rule that stops mechanically at 14.99% is honoured by construction, not
by intention.

What the architecture does instead is change the arithmetic of getting into trouble. Re-derived from
the sealed parameters, a run of consecutive maximum-loss round trips proceeds:

| Round trip | `f` | loss | equity | drawdown |
|---|---|---|---|---|
| 1 | 0.50 | 4.0% | 0.960000 | 4.0000% |
| 2 | 0.50 | 4.0% | 0.921600 | 7.8400% |
| 3 | 0.50 | 4.0% | 0.884736 | 11.5264% |
| 4 | 0.125 | 1.0% | 0.875889 | 12.4111% |
| 5 | 0.125 | 1.0% | 0.867130 | 13.2870% |
| 6 | 0.125 | 1.0% | 0.858458 | 14.1542% |
| 7 | 0.125 | 1.0% | 0.849874 | **15.0126% — breach** |

Seven consecutive maximum-loss round trips are required to breach the ceiling; six leave drawdown at
14.15%. Under Attempt 1's 95% exposure and no loss control, no such floor existed. Note that the
ladder's middle rung is skipped on this particular path — trade 3 carries drawdown from 7.84% to
11.53% in one step — which is a real property of a discrete ladder and not an error in the table.

**Five caveats travel with that table,** and they are in `SE100-CFG-3003` in full. In short: it
assumes every loss is exactly a maximum-loss round trip, ignores gaps through the loss-control level,
ignores costs, ignores the possibility that drawdown accumulates from many small adverse moves
rather than from discrete round trips, and says nothing about whether the ceiling is *met* on real
data. It is a floor on how many things must go wrong, not a prediction. §5.2's own words apply:

> Stops are risk tools, not guarantees; overnight gaps may exceed intended losses.

**The architecture has disclosed costs, declared before any result.** Halving exposure roughly halves
gross return before costs; the sell-side regulatory fee rounds *up* to the cent, so a smaller
position pays a proportionally larger fee — roughly 2 bps at 95% exposure against roughly 16 bps at
12.5%; `flat_first_rule` charges one full session out of the market at every switch; the loss control
and the max-hold both cut positions that might have recovered; and the ladder reduces size precisely
when a recovery would help most. All five are in `SE100-CFG-3003`
`risk_architecture.disclosed_costs_of_the_architecture`. If the candidates fail on return rather
than on drawdown, these are the reasons, and they were written down first.

**One new indicator,** `VOL20`: 21 visible adjusted-close bars, 20 simple returns, sample variance
with denominator 19, annualised by `sqrt(252)`. Zero volatility yields no entry rather than an
infinite position. It contributes 21 sessions to warm-up and therefore lengthens no candidate's
warm-up, all three being 101 or more.

---

## 6. Gate 3, unchanged

Every applicable Gate 3 condition is preserved exactly. `SE100-CFG-3004` binds
`config/stage3_gate_criteria.json` **by digest** rather than copying it, which is what makes "no
criterion was changed for Attempt 2" checkable by recomputing one hash instead of by comparing two
documents by eye. A copy could drift; a digest cannot.

The ceiling: `max_drawdown <= 0.15`, inclusive boundary, measured as the largest peak-to-trough
decline of the daily closing equity curve as a fraction of the running peak. Unchanged. Attempt 2
lowers the risk taken to meet the ceiling; it does not raise the ceiling to meet the risk.

**Two re-derivations, neither of which changes a rule.** Both are recorded in `SE100-CFG-3004`
`rederivations`.

1. **S3-C6's applicability.** The sealed field states a rule — candidates whose declared universe
   contains more than one instrument — and then names its two outputs for Attempt 1's candidate set.
   Read as a literal list against Attempt 2's candidates the enumeration is empty, which would
   silently excuse a two-instrument candidate from a concentration test. Applying the sealed *rule*
   instead of the sealed *output* is the reading that changes nothing: S3-C6 applies to
   `SE100-S3A2-C3-DEFENSIVE-RA1` and is `NOT_APPLICABLE_BY_CONDITION_TEXT` for C1 and C2, with the
   declared instrument count recorded as the evidence in each case.
2. **S3-C7's declaring artifact.** The sealed text says each candidate declares exactly four
   robustness neighbours in `SE100-CFG-3001`. That file is Attempt 1's and cannot declare neighbours
   for candidates that did not exist when it was sealed; for Attempt 2 the declaring artifact is
   `SE100-CFG-3003`. The count of four, the requirement that they be chosen before any result, the
   sign-match predicate, and the selection prohibition are all unchanged.

**One new conflict recorded, not repaired.** `SE100-CFG-3001` states that position size is not a
research variable "in this stage", which on a broad reading would prohibit `RA1-2` outright. It is
recorded as `S3-CONFLICT-4-ATTEMPT-2` and as interpretation `A2-INTERP-1`, with the rejected broad
reading written out alongside the adopted narrow one so a reader can disagree on the record rather
than by inference. `SE100-CFG-3001` is not edited and remains permanently true of its own six
candidates. The constitutional route for a sizing change is §11: it is material, and it creates a new
candidate that restarts at Gate 3. Generation 1's exposure ceiling is unchanged at 95% gross with a
5% cash buffer; Attempt 2 asks for less. Attempt 1's three recorded conflicts carry forward unchanged
and unrepaired.

**The rule that decides the gate,** frozen here and quoted from the sealed derivation:

> At least one pre-registered candidate satisfies EVERY hard condition of Gate 3.

Conjunctive **within** a candidate; disjunctive **across** candidates. One admissible candidate
suffices, and no more than one is required. `satisfied` means `MET` or
`NOT_APPLICABLE_BY_CONDITION_TEXT`; `NOT_MET`, `NOT_EVALUABLE`, `NOT_RUN`, `UNKNOWN`, and missing
evidence are never a pass.

A per-condition rollup row aggregates satisfaction across candidates and therefore means only "at
least one candidate satisfied this". It settles nothing. Each row must carry `met_by`, `not_met_by`,
and `not_applicable_for` as separate lists, and the conditions table must carry the
`admissible_candidate_exists` row, which alone decides the gate. Aggregating a row on `verdict ==
MET` rather than on satisfaction produced a false `FAIL` for S3-C6 in Attempt 1's first rollup; that
defect is recorded in `SE100-CFG-3004` so a fresh implementation does not reintroduce it.

**The shutdown.** Constitution §5.1's research shutdown fires at 15% below the running high-water
mark — the same number as S3-C2, on the same session-close series. So **S3-C2 is met if and only if
the shutdown never fires.** A breach liquidates at the next open, blocks all further entries, and
never re-arms; the equity curve is flat from that point on. All six Attempt 1 candidates tripped it,
the earliest in October 1997. That equivalence is what `RA1` exists to address, and it is emphatically
not a licence to treat a shutdown as anything other than a failure.

**No reruns.** Once a variant completes a valid run over its full declared window under the sealed
cost model, that result is the result. Every rule is deterministic and `random_seeds` is null, so a
rerun of an unchanged variant must reproduce byte-identical output — a rerun that produced a
*different* number would be a determinism defect and a blocker, not a better result. A run that did
not reach the window end is `NOT_RUN` and is re-run in full; a software defect discovered after a
result exists invalidates that result under §10 and forces a full re-run of everything affected.
Selectively re-running the variants whose numbers were disliked is prohibited.

---

## 7. What the robustness neighbours are for

Each candidate declares exactly four neighbours, one primary plus four variants, five runs per
candidate and fifteen in total. Their single gating purpose is S3-C7: the **sign** of each
neighbour's net return must match its primary's. Magnitudes are irrelevant to the condition, and zero
matches nothing.

**A neighbour is never promoted.** Not to primary, not to representative of its candidate, not to a
candidate in its own right. A candidate whose primary fails while all four of its neighbours pass is
a **failed** candidate; its neighbour metrics are reported as diagnostics and nothing else.
Substituting the neighbour would be selection on an observed outcome, and under §11 it would be a
material change creating a new candidate that restarts at Gate 3. This keeps the number of
admissibility trials at three, not fifteen — though all fifteen still count as searches in §8's
disclosure. A neighbour that fails to run is `NOT_RUN`, which is not a pass, and its candidate is
therefore not admissible.

Each candidate's neighbours probe two signal parameters and two risk parameters. C2's risk pair
differs from the others' deliberately: it varies the loss control rather than `f_base`, because
Attempt 1's mean-reversion specification states in its own sealed text that it has no stop, so the
loss control is the single most consequential thing being added to that rule form and a stability
test that did not probe it would be testing the wrong thing. The value chosen, `0.12`, **loosens** the
control rather than tightening it, so the neighbour cannot flatter its primary.

The permitted parameter grid for each candidate is exactly the primary value plus the neighbour
values for each key it names, with single-value keys recorded as explicit pins. No search, sweep, or
optimisation over any grid is performed at any point; the grid is a declared boundary so that a later
session cannot run a sixth variant, find it inside a broad grid, and call it pre-registered.

---

## 8. Nine candidates against one dataset — the disclosure that belongs before the result

**This attempt is adaptive, and every part of that is disclosed here rather than concealed behind new
strategy identifiers.**

Attempt 1's results are known to whoever designed Attempt 2. Specifically: all six candidates
produced positive total returns; all six breached the 15% drawdown ceiling; three missed the
30-closed-trade floor; two failed the concentration limit; one failed best-trade removal. The
development data are therefore **no longer pristine** for the broad fact that a first set of
candidates in these families, at 95% exposure and without loss controls, had excessive drawdown.
Nothing can restore that, and no new strategy identifier changes it.

This raises researcher degrees of freedom and false-discovery risk. Accordingly:

| | Attempt 1 | Attempt 2 | Cumulative |
|---|---|---|---|
| Candidates | 6 | 3 | **9** |
| Gating variants | 30 | 15 | **45** |
| Total runs | 30 | 18 | **48** |

Attempt 2's 18 runs are its 15 gating variants plus 3 non-gating stressed-cost runs. Distinct signal
*forms* across both attempts remains 6, because all three Attempt 2 candidates hold their entry and
exit signal in the same form as a rejected Attempt 1 candidate — deliberately, so that what varies is
the risk architecture and not everything at once. Distinct *specifications* is 9.

The cumulative figures, not Attempt 2's alone, are the ones any later statistical interpretation must
use. `revisions_permitted` is 0.

Four consequences stated plainly:

1. **No Attempt 2 result may be described as independent confirmation of anything** merely because
   its code is new. It is the second look at the same development window by the same researcher.
2. **A passing development result authorizes only the next frozen evaluation step.** It is not
   evidence of a trading edge, not a selection, and not a claim about markets.
3. **Validation and holdout protections are unchanged.** The validation window remains locked and the
   holdout sealed and unread. Neither was consulted in designing this attempt.
4. **The adaptation is admitted where it is thinnest.** The reason a loss control and a time exit are
   declared at all is that Attempt 1 showed unstopped, untimed rules breaching the ceiling. Adding
   them *to* a rejected candidate would be the prohibited post-result repair; declaring them
   prospectively in a new candidate that restarts at Gate 3 is the route §11 provides. The
   distinction is real, it is thin, and `SE100-CFG-3003` records it in the candidate it bears on
   rather than glossing it here.

One further limit on comparability, declared now. The sealed warm-up rule is adopted unchanged —
each candidate declares a warm-up equal to the largest lookback used by its primary parameterisation
or by any of its neighbours — but the neighbour sets differ between attempts, so the derived warm-ups
differ. `F2` and `F6` each declared a 250-session `sma_long` neighbour and therefore a 250-session
warm-up; `C1` and `C3` declare neighbour sets topping out at 200 and therefore a 200-session warm-up.
The signal lookback itself is unchanged at `SMA(200)`. What differs is the run window: `C1` and `C3`
start roughly fifty sessions earlier in the development window than their Attempt 1 counterparts did.

Two consequences, both disclosed rather than argued away. No Attempt 2 candidate is a matched-window
controlled comparison against any Attempt 1 candidate, so differences between the attempts cannot be
attributed to the risk architecture alone. And a slightly longer run window is a difference in
Attempt 2's favour on the closed-trade count that S3-C4 measures — small against a window of some
twenty-eight years, but not zero, and not a neutral change. It follows from applying the sealed rule
to a smaller neighbour set, not from choosing a shorter warm-up to obtain a longer run.

---

## 9. Explicit non-authorizations, restated for this attempt

Sealing this document does not authorize, and this session has not performed:

- any read of validation-window or holdout-window data, for any purpose;
- any backtest, simulation, parameter sweep, optimisation, or performance calculation;
- any implementation of an Attempt 2 strategy module, including empty placeholders;
- any modification, re-run, re-parameterisation, or supersession of any Attempt 1 artifact;
- any change to the 15% drawdown ceiling or to any Gate 3 acceptance criterion;
- any download, purchase, subscription, or account creation;
- any machine learning, and any use of fundamental, earnings, or intraday data;
- any combination of one candidate with another;
- any credential access or read of a secret value;
- any order, paper or live, any Alpaca connection for trading, and no unattended scheduling;
- any selection of a winning strategy, and any claim of expected income;
- any entry to Stage 4, which remains locked pending an admitted candidate.

`live_trading_authorized` remains `false`.

---

## 10. Pre-freeze disclosure and contamination assessment

**What this session read before writing anything.** The frozen Stage 0 constitution and its
machine-readable companion; the Stage 0 freeze record, verified from `governance/`; the Stage 1 and
Stage 2 decision records and freeze records; Attempt 1's complete pre-registration, decision record,
run record, artifact manifest, checksum records, and research report; the sealed cost model, universe,
holdout lock, and Gate 3 criteria; and the source of the Gate 2 validated engine and its gate
evaluator, to establish that the declared rules are expressible without an engine change. Every
checksum record was verified from its intended working directory and every entry passed. The
canonical `repo_state_id` was recomputed independently and reproduced the value Attempt 1 recorded.
The holdout is `SEALED`, and the development, validation, and holdout boundaries are unchanged.

**Attempt 1 results reviewed.** Already-exposed Attempt 1 performance evidence was reviewed, as §3 of
the operating prompt permits. Of it, only the six per-candidate closed-trade counts were carried into
the design, and only to support the frequency argument for excluding three families in §4. No
Attempt 1 return, drawdown, profit factor, or equity path appears anywhere in `SE100-CFG-3003`, and
no Attempt 2 parameter was chosen by reverse-engineering an observed Attempt 1 path.

**No Attempt 2 performance was generated or inspected**, because none could be: no strategy module
for any Attempt 2 candidate exists.

**Contamination, measured rather than asserted.** Attempt 1 could record
`strategy_modules_present_at_seal_time: 0` and `strategy_output_files_present_at_seal_time: 0`
because `src/stockedge100/strategies/` was empty and no result artifact existed anywhere. Both
literal predicates are unavailable now: that directory holds nine modules, and Attempt 1's results
are on disk under `reports/stage3/`. None of them may be deleted, so counting to zero over the same
paths is not the available test. Five Attempt-2-specific predicates are measured instead. Attempt 1
recorded its two counts as bare integers with no definition attached; each of these five carries its
definition in the JSON, so a reader can check what was counted rather than trusting the count:

1. Python files under `src/stockedge100/` outside `reporting/` whose normalised path contains
   `attempt2`;
2. Python files under `strategies/` whose text contains any declared Attempt 2 candidate ID;
3. files under `reports/` whose path contains `attempt2`;
4. `runs/` records mentioning an Attempt 2 candidate ID or an `ATTEMPT_2` token;
5. Attempt 1 immutability, by verifying `governance/STAGE_3_PREREGISTRATION.sha256` and
   `reports/stage3/STAGE_3_STRATEGY_RESEARCH.sha256` from the project root.

A tree-wide case-insensitive search for Attempt 2 identifiers before any file was written returned
nothing outside retrospective write-ups. The measured values at sealing are in
`governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.json`; the sealing program refuses to write if any of
the first four is non-zero or if Attempt 1's records do not verify.

**One correction made during authoring, recorded because the file is evidence.** A first draft of
`SE100-CFG-3003` declared a neighbour varying C2's loss control but omitted that parameter from C2's
permitted grid, contradicting the file's own statement of what a grid contains. It was found by
checking the invariant rather than by reading, and was corrected before anything was sealed or
hashed. The grid invariant is now stated once at attempt level and holds for all three candidates.
Two citation defects found the same way were also repaired: a quotation that capitalised a modal verb
the source writes in lower case, and a §11 citation that did not flag that its clause is triggered by
validation results rather than development results.

**No timestamp in this document was hand-typed.** The system clock was read and the value pasted; the
authoritative declaration timestamp is emitted by the sealing program into the JSON.
