# Stage 4 — validation pre-registration decision report

| Field | Value |
| --- | --- |
| Document id | `SE100-GOV-4000` |
| Project | StockEdge100 |
| Stage | Prompt stage 4 — constitutional gate 4 (validation robustness). Pre-registration only. |
| Session type | Representative selection and prospective pre-registration. No validation read, no engine run, no evaluator code. |
| Governing document | `SE100-GOV-0001` — `governance/STAGE_0_CONSTITUTION.md`, FROZEN, v1.0.0 |
| Pre-registration sealed | `SE100-GOV-0008` — `governance/STAGE_4_PREREGISTRATION.{md,json}`, sealed `2026-08-13T14:01:21Z` |
| Gate 3 record | `SE100-GOV-3002` — `PASS — STAGE_3_STRATEGY_ADMITTED_IN_DEVELOPMENT`, two candidates admitted, neither ranked. Unmodified. |
| Evidence | `config/stage4_validation_protocol.json` (`SE100-CFG-4001`), `config/stage4_gate_criteria.json` (`SE100-CFG-4002`), `config/stage4_representative_selection.json` (`SE100-CFG-4003`) |
| Authored (UTC) | 2026-08-14T10:31:42Z |
| Verdict | `PASS — STAGE_4_VALIDATION_PREREGISTRATION_FROZEN` |
| Gate 4 evaluated | **No.** No validation observation was read in this session and no Stage 4 evaluator exists. |
| Gate 4 passed | **No.** |
| `live_trading_authorized` | `false` |

The `run_id` of this design session and the repository-state digest are deliberately **not** written
into this file. `repo_state_id` is computed over `governance/*.md` among other patterns, so writing a
tree digest here would invalidate it on write. Both values live in
`reports/stage4/STAGE_4_VALIDATION_PREREGISTRATION.json` and in the append-only `runs/` record for
this session, which are outside the digest's patterns. Individual **file** digests are quoted below,
because a file digest is not a digest of the tree that contains this file.

The seal record `governance/STAGE_4_PREREGISTRATION.json` omits `repo_state_id` for the same reason
and says so on its own record; the binding value for the seal is the `repo_state_id` field of
`runs/SE100-R-20260813T140121Z.json`. That value describes the tree **as it stood at the seal**. The
test module, this report, the package builder, and the decision package were all written afterwards,
so the current tree does not match it and is not supposed to. What the seal fixes is the digest of
each pre-registered file, and those are unchanged.

---

## 1. What this session was for, and what it was not

Gate 3 Attempt 2 admitted two candidates — `SE100-S3A2-C1-PULLBACK-RA1` and
`SE100-S3A2-C2-MEANREV-RA1` — and ranked neither. `reports/stage3_attempt2/STAGE_3_ATTEMPT_2_DEVELOPMENT_ADMISSIBILITY.json`
records `selection_made` `false` and `ranking_computed` `false`. Constitutional gate 4 evaluates a
strategy on the locked validation window, and the validation window may be read once. Two admitted
candidates and one read is not a situation the frozen governance resolves on its own, so this session
had to resolve it prospectively or stop.

It did exactly three things. It selected one representative from the two admitted candidates by a
rule that reads no return. It wrote the full Stage 4 validation procedure and the seven gate 4
conditions down — measurements, thresholds, boundaries, verdict tokens, fold construction, run
budget, failure handling — and sealed them before any validation observation existed. Then it built
this decision package.

It did **not** read a validation row, read a validation price, compute a validation-period indicator,
count a validation-period trade, inspect validation coverage beyond the boundary dates that
`SE100-GOV-1005` publishes as frozen metadata, run the representative on validation data, run any
exploratory query against the validation partition, inspect the holdout, run another development
backtest, implement any part of the Stage 4 evaluator, or contact a broker. Nothing in this report
states how the representative performs on validation, because nothing in this session could find
out. Every performance figure quoted below is a **development** figure already on the record from
Gate 3.

## 2. Integrity verification performed before anything was written

Every check below is read-only and was run before the first Stage 4 artifact was authored. Freeze
records that use bare filenames were verified from `stockedge100/governance/`; records that use
project-root-relative paths were verified from `stockedge100/`. Running them from the wrong working
directory is an operator error, not an integrity failure, so the directory is recorded with each.

| Record | Verify from | Entries | Result |
| --- | --- | ---: | --- |
| `governance/STAGE_0_FREEZE.sha256` | `governance/` | 2 | all OK |
| `governance/STAGE_1_FREEZE.sha256` | `governance/` | 2 | all OK |
| `governance/STAGE_1_PREREGISTRATION.sha256` | project root | 4 | all OK |
| `governance/STAGE_2_PREREGISTRATION.sha256` | project root | 4 | all OK |
| `governance/STAGE_3_PREREGISTRATION.sha256` | project root | 4 | all OK |
| `governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.sha256` | project root | 4 | all OK |
| `reports/stage0/STAGE_0_VERIFICATION.sha256` | project root | 8 | all OK |
| `reports/stage1/STAGE_1_DATA_READINESS.sha256` | project root | 19 | all OK |
| `reports/stage2/STAGE_2_BACKTEST_ENGINE.sha256` | project root | 20 | all OK |
| `reports/stage3/STAGE_3_STRATEGY_RESEARCH.sha256` | project root | 26 | all OK |
| `reports/stage3_attempt2/STAGE_3_ATTEMPT_2_DESIGN.sha256` | project root | 31 | all OK |
| `reports/stage3_attempt2/STAGE_3_ATTEMPT_2_STRATEGY_RESEARCH.sha256` | project root | 37 | all OK |

The Stage 0 freeze was additionally verified digest-for-digest rather than only by `sha256sum -c`,
and both halves match:

| Frozen artifact | sha256 recorded and computed |
| --- | --- |
| `governance/STAGE_0_CONSTITUTION.md` | `b6f20176b6538722e45ae34e6f8b55a818a6e50057a23e9ddd097e0ce73ce1e5` |
| `governance/STAGE_0_CONSTITUTION.json` | `af45fda6b37bed50768d5f3d01d4a91175da93e708c9daf1b630e35a981e2ff5` |

The sealing program re-ran all twelve record checks itself and refuses to write with exit 4 if any
entry fails, so the table above is not a claim about a check performed once by hand — it is a
precondition of the seal existing at all. The two records that establish Gate 3 Attempt 2's
immutability (`governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.sha256` and
`reports/stage3_attempt2/STAGE_3_ATTEMPT_2_STRATEGY_RESEARCH.sha256`) are recorded separately in the
seal under `gate_3_attempt_2_immutability_records`, because this stage reads Gate 3's evidence and a
reader is entitled to know that the evidence it read had not moved.

Nothing was repaired. No frozen artifact was opened for writing at any point in this session.

Nine artifacts adopted by digest were recomputed from disk and compared against the values the Stage
4 configs bind them to. All nine match, and the sealing program refuses with exit 6 on any drift:

| Adopted artifact | artifact id | sha256 |
| --- | --- | --- |
| `governance/STAGE_0_CONSTITUTION.md` | `SE100-GOV-0001` | `b6f20176b6538722e45ae34e6f8b55a818a6e50057a23e9ddd097e0ce73ce1e5` |
| `governance/STAGE_0_CONSTITUTION.json` | `SE100-GOV-0001` | `af45fda6b37bed50768d5f3d01d4a91175da93e708c9daf1b630e35a981e2ff5` |
| `governance/STAGE_1_UNIVERSE.json` | `SE100-GOV-1004` | `01601a60fa950a2429f72a2e9f627ec5af4c1853d1b47ffab35e81debc7eb67a` |
| `governance/STAGE_1_HOLDOUT_LOCK.json` | `SE100-GOV-1005` | `9696161c4c5612fc7f6b3e5a3410917f20ad5707cb9b89b8bcc39cb70831dfb3` |
| `config/stage2_cost_model.json` | `SE100-CFG-2001` | `f62d98436445cfc436463765ff6006dd234a3082ddf429992296645e697586e2` |
| `config/stage2_engine_spec.json` | `SE100-CFG-2002` | `c376d12b2392eb2558092a6ad245481b88e36123e7e087522374dd28b218ed21` |
| `config/stage3_gate_criteria.json` | `SE100-CFG-3002` | `310f1c978380f4a1d6b98b8c368975b1515476b032c123afb06f1dd597e3e18d` |
| `config/stage3_attempt2_strategy_protocol.json` | `SE100-CFG-3003` | `77f1451c20e37640bd2843ff86d69eb54cbc0ebb592a696972fbdea6e05b5433` |
| `config/stage3_attempt2_gate_criteria_binding.json` | `SE100-CFG-3004` | `a482f499173c0d7e2b0ca158b2edf7cb2e25a516ac2eb361e1441b2964006c8e` |

## 3. Whether a Stage 4 validation evaluation is authorized at all

This was settled from frozen text before anything was designed, because designing a validation
procedure that governance does not permit would have been the wrong deliverable.

Gate 3 is passed. What a Gate 3 pass authorises is stated by Gate 3's own sealed artifact rather than
by this stage: `config/stage3_attempt2_strategy_protocol.json` `stage_4_remains_prohibited_conditions`
holds that validation-window access remains prohibited until the frozen gate that authorises it,
regardless of any development result. So a Gate 3 pass authorises the writing and sealing of a
prospective Stage 4 pre-registration, and nothing that executes.

The Stage 4 criteria themselves were not invented from the Gate 3 criteria. Gate 4 exists in the
frozen constitution with all seven of its conditions and six of its thresholds already written down
(§11 below). What did not exist anywhere on disk was a definition of a walk-forward fold, and §14
records the single authority under which that one measurement was specified prospectively.

Consequently:

| Question | Answer |
| --- | --- |
| `validation_evaluation_authorized` | `true` — for exactly the two declared runs of exactly the sealed representative under exactly this frozen procedure, in exactly one future session |
| `validation_access_authorized_in_this_session` | `false` |
| `holdout_access_authorized` | `false` |
| `authorized_windows_in_this_session` | `[]` — the empty set. This session ran no engine. |

Five things would void that forward authorization, and they are recorded in
`SE100-CFG-4001` `authorization_determination.what_would_void_the_authorization`: any change to a
sealed digest, any run beyond the two declared, any second session reading the validation window, any
parameter/rule/feature/universe change to the representative, and any substitution of the other
admitted candidate, a neighbour, or a combination.

## 4. Why a representative had to be selected

`SE100-CFG-4003` `why_a_selection_is_needed` states the reasoning, and the middle two clauses are the
load-bearing ones:

> The validation window may be read once. Running both candidates on it would make the reported
> result a maximum over two draws, and the candidate carried to the holdout would then have been
> chosen on a validation outcome. That is selection on the out-of-sample window, which is the failure
> mode the three-partition design exists to prevent.

> Combining, averaging, or forming a portfolio of C1 and C2 creates a third strategy that no gate has
> evaluated. Under constitution section 11 it is a new candidate and restarts at Gate 3.

So exactly one of the two admitted candidates had to be selected, by a rule that is prospectively
defensible and that reads no validation observation. The eligible set is two candidates and four
exclusions, each exclusion carrying its own frozen ground:

| Excluded | Ground |
| --- | --- |
| `SE100-S3A2-C3-DEFENSIVE-RA1` | Rejected at Gate 3 on S3-C6. **Ineligible and not reconsidered.** |
| Any robustness neighbour of C1 or C2 | `SE100-CFG-3004` `neighbour_status`, verbatim: a neighbour may never become its candidate's representative, under any result |
| Any Gate 3 Attempt 1 candidate | All six rejected; every one failed S3-C2 with a development maximum drawdown above 15%, per `results.per_candidate_primary` of `reports/stage3/STAGE_3_STRATEGY_RESEARCH.json`. Not revisited. |
| Any combination, average, portfolio or ensemble of C1 and C2 | A new candidate under constitution §11, restarting at Gate 3. Not authorized. |

## 5. The search for a mandatory constitutional selection rule, and what it found

The first move was not to design a rule. It was to look for one that already binds, because a
mandatory rule on disk would outrank anything authored here. `SE100-CFG-4003`
`search_for_a_mandatory_constitutional_selection_rule` records the question, the locations searched,
and the answer.

Locations searched: constitution §§4, 5, 9 and 11; the Gate 3 criteria and the Attempt 2 binding
(`SE100-CFG-3002`, `SE100-CFG-3004`); the Gate 3 Attempt 2 evidence and report; `governance/*.md`
and `governance/*.json` generally; and `config/*.json` generally.

The recorded result begins:

> No mandatory selection rule exists.

and continues that the constitution says nothing about choosing among candidates that pass. The
recorded consequence is the important half:

> …section 8 permits it…must not be a rationalisation of a preferred outcome.

One constraint *was* found, and it is a prohibition rather than a rule of choice. `SE100-CFG-3004`
`neighbour_status` was asked whether a robustness neighbour may become its candidate's
representative. Its answer, verbatim: **"No. Never. Under no result."** The effect is that the
eligible set is exactly the two admitted PRIMARY candidates and nothing adjacent to them.

Because no mandatory rule exists, the rule below had to be authored — and the alternative, had it
failed to decide, was to stop. `SE100-CFG-4003` `application.outcome.if_the_rule_had_not_decided`
records that alternative verbatim, and it was written into the artifact before the rule was applied:

> The stage would have stopped with a BLOCKED verdict and referred the selection to a human, rather
> than reaching for a second criterion. A tie-break invented after the first rule failed would be a
> retrospective rule wearing a prospective rule's clothes.

## 6. The selection rule

`SE100-CFG-4003-R1`, "Declared-variant research-shutdown screen". Statement, verbatim:

> Eliminate any Gate 3 admitted candidate for which ANY of its declared runs — the PRIMARY
> parameterisation, any of its four declared robustness neighbours, or its section 7 required
> stressed-cost run — tripped the section 5.1 research shutdown on development data. If exactly one
> candidate survives, it is the representative. If both survive or neither survives, the rule does
> not decide and the stage stops for human selection.

It is applied to development-window evidence only — already authorized, already read. Its output per
declared run is one boolean: did the sealed risk rule fire. `reads_no_return` and
`reads_no_risk_adjusted_metric` are both `true` in the sealed artifact, and the property is checkable
by reading the predicate rather than by trusting the author.

Every term of the rule is bound to a frozen or sealed artifact. `provenance.terms` carries five
entries; three cite a whole file by digest and two cite a specific sealed field:

| Term | Source |
| --- | --- |
| "declared runs" — the PRIMARY parameterisation plus four declared robustness neighbours | `config/stage3_attempt2_strategy_protocol.json` (`SE100-CFG-3003`) @ `77f1451c20e37640bd2843ff86d69eb54cbc0ebb592a696972fbdea6e05b5433` |
| the section 5.1 research shutdown, and its 15% level | `governance/STAGE_0_CONSTITUTION.md` §5.1 @ `b6f20176b6538722e45ae34e6f8b55a818a6e50057a23e9ddd097e0ce73ce1e5`, with the measurement basis from `config/stage2_cost_model.json` @ `f62d98436445cfc436463765ff6006dd234a3082ddf429992296645e697586e2` |
| the stressed-cost run at 2× friction | `config/stage3_attempt2_gate_criteria_binding.json` (`SE100-CFG-3004`) @ `a482f499173c0d7e2b0ca158b2edf7cb2e25a516ac2eb361e1441b2964006c8e` |
| the two remaining terms | cite the specific sealed field they rely on rather than a whole-file digest |

Six reasons are recorded for why the rule is prospectively defensible. Two of them carry the
argument and the rest support it. The fifth is the one that can be checked rather than believed:

> It would have eliminated the same candidate under reversed returns. The predicate is a function of
> shutdown events only, so if C1's returns had exceeded C2's at every variant, C1 would still be
> eliminated and C2 would still be selected. This is the property that distinguishes a prospective
> rule from a retrospective one, and it is checkable by reading the predicate rather than by trusting
> the author.

And the sixth states the direction the rule cuts:

> It is stricter than a performance rule would be. A performance rule would have admitted C1 had its
> return been higher. This rule does not, because a shutdown is not offset by a return.

## 7. The application, in full, to both eligible candidates

The evidence source is `reports/stage3_attempt2/STAGE_3_ATTEMPT_2_STRATEGY_RESEARCH.json` @
`26eecacfe96420878ce647b86f68da8ed8a17fea1338d85ee982b190645ed466`, fields
`results.all_registered_variants[label].shutdown_session` and `.max_drawdown`, and
`results.stressed_cost_runs[candidate].stressed_shutdown_session` and `.stressed_max_drawdown` —
development window only. It is corroborated independently by
`governance/STAGE_3_ATTEMPT_2_STRATEGY_RESEARCH_REPORT.md` @
`21471f53b45b09ac990b849bd6ac8d3389232deb3393e0bba8bc97bd50ecb5a5`, whose §20 items 2 and 3 state
both C1 shutdown events on the record independently of the JSON.

Both candidates' full declared variant sets are recorded, including every run that did **not** trip,
so a reader can recount rather than trust the count. Development maximum drawdowns are shown to four
decimal places here; the sealed artifact carries them at full `Decimal` precision.

`SE100-S3A2-C1-PULLBACK-RA1` — pullback family, Gate 3 ADMITTED (6 conditions met, S3-C6 not
applicable by condition text):

| Declared run | Kind | Shutdown | Max drawdown |
| --- | --- | --- | ---: |
| `#PRIMARY` | primary | — | 0.1467 |
| `#N1` | neighbour, `sma_long` 200 → 150 | **tripped 2020-02-27** | 0.1544 |
| `#N2` | neighbour, `sma_short` 10 → 20 | — | 0.0997 |
| `#N3` | neighbour, `vol_target` 0.10 → 0.08 | — | 0.1293 |
| `#N4` | neighbour, `f_base` 0.50 → 0.35 | — | 0.0942 |
| `#PRIMARY#STRESS` | §7 stressed cost, 2× | **tripped 2018-02-05** | 0.1530 |

6 declared runs, **2 shutdown trips** → **ELIMINATED**. "The screen eliminates on any trip."

`SE100-S3A2-C2-MEANREV-RA1` — mean-reversion family, Gate 3 ADMITTED (6 conditions met, S3-C6 not
applicable by condition text):

| Declared run | Kind | Shutdown | Max drawdown |
| --- | --- | --- | ---: |
| `#PRIMARY` | primary | — | 0.1260 |
| `#N1` | neighbour | — | 0.1439 |
| `#N2` | neighbour | — | 0.1466 |
| `#N3` | neighbour | — | 0.1265 |
| `#N4` | neighbour | — | 0.1332 |
| `#PRIMARY#STRESS` | §7 stressed cost, 2× | — | 0.1269 |

6 declared runs, **0 shutdown trips** → **SURVIVES**.

Survivor count 1. The rule decides. `human_selection_required` is `false`, and the representative is
`SE100-S3A2-C2-MEANREV-RA1`.

**The margin is qualified rather than left to be discovered.** `SE100-CFG-4003`
`honest_qualification_of_the_margin` records that C2's largest non-breaching development drawdown is
`#N2` at 0.1466 — **34 basis points** below the 15% shutdown level — and `#N1` at 0.1439 is 61 basis
points below it. The screen is binary and neither tripped, so the rule's output is unaffected. The
consequence is stated before any validation observation exists:

> S4-C3's ceiling is the same 15% on the same series (S4-CONFLICT-3). A representative whose
> development neighbours sat 34 basis points from that level has no margin to spare on a fresh
> window, and the drawdown condition is a real risk of failure, not a formality.

C2 is the survivor of this screen. It is not a candidate with comfortable risk headroom.

## 8. What the rule is not, and its honest limitation

Four things the rule is not, from `what_the_rule_is_not`, condensed: it is not a ranking (it produces
a survivor set, not an order); it is not a claim that C1 is a bad strategy (C1 satisfied every hard
Gate 3 condition and remains a Gate 3 admitted candidate on the record); it is not a repair of C1
(repairing C1's cost sensitivity would be a parameter change creating a new candidate under §11, and
is explicitly not authorized); and it is not a rule about magnitudes.

The limitation is recorded rather than argued away, and it is the honest statement of what
return-blindness does and does not buy:

> The rule was authored in a session in which Gate 3 development evidence was lawfully visible.
> Return-blindness makes the rule's OUTPUT independent of the returns; it does not make the CHOICE of
> predicate independent of the researcher's knowledge of the evidence. A different return-blind
> predicate — say, one screening on neighbour dispersion — might have selected differently. That
> residual freedom is disclosed here and in config/stage4_validation_protocol.json
> adaptive_research_disclosure rather than argued away. What limits it is that the predicate has no
> tunable part: once 'shutdown trip over the declared variant set' is chosen, the answer is fixed by
> the evidence and cannot be nudged.

Five mitigations are recorded, and the fourth and fifth are the ones that matter: the surviving
candidate's narrowest margin is recorded rather than left to be discovered (§7), and the rule's
return-blindness is stated as a checkable property of the predicate rather than as an assurance about
the author's state of mind. The adaptation is also not concealed behind a new identifier — the
representative keeps its Gate 3 experiment id, so it stays traceable to the evidence that admitted it
and to the two-attempt search that produced it.

## 9. Corroboration recorded but not used in the decision

The operating instruction for this stage observed that the Gate 3 evidence appears to favour C2, and
required that observation to be independently verified and never allowed to override the
constitution. It was verified, it does point the same way, and it decided nothing.
`SE100-CFG-4003` `corroboration_not_used_in_the_decision` is marked `NOT_DECISIVE` and states why it
is recorded at all:

> The screen decided on shutdown trips alone. These figures are recorded to show that the rule was
> not reverse-engineered from a preferred answer: every rule constructible from a FROZEN threshold
> points the same way, and none points at C1.

All four checks are against **frozen** Gate 4 thresholds from
`governance/STAGE_0_CONSTITUTION.json`, and all four are **development** figures:

| Check, against the frozen Gate 4 threshold | C1 | C2 |
| --- | --- | --- |
| Profit factor vs `profit_factor_min` 1.15 | 1.1058 — below | 1.4402 — above |
| Sharpe at the sealed 0% cash rate vs `sharpe_min` 0.50 | 0.1285 | 0.4202 |
| Stressed-cost total return vs `stressed_cost_return_positive` | +0.0018, with the shutdown having fired 2018-02-05 | +0.3311 |
| Primary max drawdown headroom vs `max_drawdown_pct` 15% | 0.1467 — 33 bp of headroom | 0.1260 — 240 bp |

The second row is the one that does not flatter the selected candidate, and it is recorded in the
same list rather than omitted: **neither candidate reaches 0.50 on development data.** The sealed
`agreement_statement` says so explicitly. The third row is why the screen eliminates on the trip
rather than on the return — C1's stressed run technically stayed positive, and it did so while
breaching the risk rule.

None of these comparisons appears in `selection_rule.statement`, and none was needed to reach the
outcome.

## 10. The sealed representative

`SE100-S3A2-C2-MEANREV-RA1`, family mean reversion, declared universe `["SPY"]`, declared warm-up 101
sessions, risk architecture `RA1`. The parameterisation is sealed at
`governance/STAGE_4_PREREGISTRATION.md` §4.5 and is not restated in full here; it is ten parameters
plus a two-rung ladder, and no value in it may change.

The strategy module was resolved **by content**, not named by hand:
`src/stockedge100/strategies/attempt2_candidates.py` @
`86563afe7fd2d6ca1594739c4cf4b67f42ce0cdb70fe1e2138c1e7bafeb56a2d`. Exactly one module under
`src/stockedge100/strategies/` names the sealed representative, and the sealing program refuses with
exit 8 if that resolution is not unique — so the seal cannot silently point at the wrong file.

Seven prohibitions take effect at the seal (`prohibited_after_this_seal`), and the first is
unconditional: changing the representative **for any reason, including a Gate 4 FAIL**. The others
forbid substituting C1 after a C2 result exists or running it as a comparison, substituting any
neighbour of C2, changing any parameter, adding any rule absent from the sealed specification,
reinterpreting the selection rule or applying a different return-blind rule after a result exists,
and reconsidering C3.

## 11. Gate 4, extracted rather than invented

The gate text was flattened out of the frozen constitution — `governance/STAGE_0_CONSTITUTION.md`
lines 193–203 @ `b6f20176b6538722e45ae34e6f8b55a818a6e50057a23e9ddd097e0ce73ce1e5`, with the
flattening rule recorded ("No word is added, removed, or reordered; only the Markdown bullet markers,
bold markers and line breaks are dropped"):

> Pass only if, on the locked validation/walk-forward period: after-cost total return is positive;
> annualized Sharpe ratio is at least 0.50 using daily equity returns and a documented cash rate;
> maximum drawdown is no worse than 15%; profit factor is at least 1.15; stressed-cost total return
> remains positive; at least 70% of completed walk-forward test folds have positive after-cost
> return; no material rule, feature, universe, or parameter change is made in response to validation
> results. Fail verdict: STRATEGY_REJECTED_IN_VALIDATION.

Seven conditions, seven declared, all seven gating. Each carries the frozen phrase it implements, a
measurement, a `Decimal` predicate, and an explicit boundary treatment:

| Id | Frozen requirement (verbatim) | Predicate | Boundary |
| --- | --- | --- | --- |
| S4-C1 | after-cost total return is positive | `total_return > Decimal('0')` | **Strict.** Exactly zero is not positive. |
| S4-C2 | annualized Sharpe ratio is at least 0.50 using daily equity returns and a documented cash rate | `sharpe >= Decimal('0.50')` | Inclusive. Admits exactly 0.50. |
| S4-C3 | maximum drawdown is no worse than 15% | `max_drawdown <= Decimal('0.15')` | Inclusive. Admits exactly 15%. |
| S4-C4 | profit factor is at least 1.15 | `profit_factor >= Decimal('1.15')` | Inclusive. Admits exactly 1.15. |
| S4-C5 | stressed-cost total return remains positive | `stressed_total_return > Decimal('0')` | **Strict.** Exactly zero is not positive. |
| S4-C6 | at least 70% of completed walk-forward test folds have positive after-cost return | `positive_fold_count / completed_fold_count >= Decimal('0.70')` | Inclusive. With twelve completed folds the smallest passing count is **9**. |
| S4-C7 | no material rule, feature, universe, or parameter change is made in response to validation results | exact equality of every sealed digest, plus exactly one evaluation run record, exactly 2 validation runs, and no parameter differing from the sealed parameterisation | Exact. "There is no tolerance and no immaterial change." |

Six of the seven **measurements** are adopted by digest from artifacts sealed before Gate 3 was
evaluated, rather than restated — "a restatement can drift and a digest cannot". The one exception is
the fold construction (§14).

Two boundary points are deliberately **not harmonised** with Gate 5. Gate 5's corresponding threshold
is `stressed_cost_return_nonnegative`, which is looser than S4-C5's strict positivity, and Gate 5 —
not Gate 4 — is where "removing the single best trade" is a threshold. `SE100-CFG-4002` records both
differences as preserved rather than smoothed away.

The combination rule: conjunctive within the candidate, and there is **no disjunction across
candidates** because there is exactly one representative
(`across_candidates: NOT_APPLICABLE_EXACTLY_ONE_REPRESENTATIVE`). Every condition verdict is one of
`MET`, `NOT_MET`, `NOT_EVALUABLE`, or `NOT_APPLICABLE_BY_CONDITION_TEXT`; there is no fifth value and
no borderline value; and **no Gate 4 condition is expected to be `NOT_APPLICABLE`** — all seven apply
to a single-instrument single representative. `NOT_EVALUABLE` never counts as `MET`. Comparisons are
exact `Decimal`, never floating point, and no result is rounded before comparison.

Six incoherent combinations are refused outright, including a `PASS` reached by treating
`NOT_EVALUABLE`, `NOT_RUN`, `UNKNOWN`, or missing evidence as satisfied; a `FAIL` followed by a
retune, a substitution, or a second validation read; and a verdict of any kind reached after a sealed
digest changed — "That is S4-C7 NOT_MET, and it fails the gate regardless of the equity curve."

Thirteen quantities are reported but do **not** gate, and one of them closes a constitutional loop
worth naming: §4 requires better risk-adjusted performance than cash, and against the sealed 0%
zero-volatility cash series that is satisfied by any strictly positive Sharpe — so S4-C2's floor of
0.50 subsumes it. It is recorded as subsumed rather than added as an eighth condition. Beating SPY is
reported and does not gate; §4 itself states beating SPY is not mandatory where drawdown is
materially reduced. Neither Gate 3 admitted candidate beat SPY on either benchmark series in
development.

## 12. The five recorded conflicts, and the verdict tokens one of them forces

All five are **reported, not repaired**. No frozen artifact was edited.

| Id | Conflict | Resolution |
| --- | --- | --- |
| S4-CONFLICT-1 | The constitution's Markdown states **seven** Gate 4 conditions; its JSON companion carries **six** thresholds. The missing one is the seventh: no material change in response to validation results. | The Markdown is authoritative and more restrictive, so all seven are evaluated. Mirrors S3-CONFLICT-1, resolved the same way. |
| S4-CONFLICT-2 | The JSON companion supplies `fail_result` for gate 4 but has **no `pass_result` key**. Gate 3 had the same defect; gate 5 does not. | The pass token is derived by mechanical negation, following the derivation already sealed for Gate 3. See below. |
| S4-CONFLICT-3 | The Gate 4 drawdown ceiling and the §5.1 research shutdown are the **same 15%** on the running high-water mark of the **same** daily-closing equity series. | Adopted unchanged: **S4-C3 is MET if and only if the research shutdown never fires during the validation run.** A candidate that trips the shutdown has by construction breached S4-C3. It also fixes the treatment of post-shutdown folds. |
| S4-CONFLICT-4 | **New.** The constitution requires "at least 70% of completed walk-forward test folds" but nowhere defines a fold — no count, no length, no train/test split, no definition of "completed". A repository-wide search for `walk_forward`, `walk-forward` and `walkforward` returns only restatements of the constitution's own sentence. | Constitution §8's requirement of a signed specification created before execution is the authority under which the construction is fixed prospectively. It is the **one** Gate 4 measurement this stage authors. |
| S4-CONFLICT-5 | **New.** "Walk-forward" implies periodic re-estimation on a training segment, but Gate 4's own seventh condition forbids any parameter change in response to validation results, and §11 makes such a change a new candidate. Re-fitting is prohibited by the same gate that names walk-forward folds. | The gate text constrains only "test folds" and names no train fold. `train_folds` is declared as the **empty set**, with the reason on the record. This is the more restrictive reading: it gives the candidate no opportunity to adapt within the window. |

The tokens, from `SE100-CFG-4002` `verdict_token_derivation`:

| | Token |
| --- | --- |
| Fail | `STAGE_4_STRATEGY_REJECTED_IN_VALIDATION` |
| Pass | `STAGE_4_STRATEGY_ADMITTED_IN_VALIDATION` |

The derivation is recorded verbatim in the sealed artifact and ends: *"Neither token is invented and
neither is taken from an operating prompt."* The fail token is the constitution's gate 4 `fail_result`
prefixed with the stage, exactly as `SE100-CFG-3002` prefixed gate 3's; the pass token replaces
`REJECTED` with `ADMITTED`, exactly as `SE100-CFG-3002` derived gate 3's absent `pass_result`. The
repository was searched for a pre-existing Gate 4 pass token before one was derived; none exists in
`governance/`, `config/`, `src/`, `tests/` or `reports/`.

**One conflict with the operating prompt is recorded here.** The prompt for this stage named
pass/fail tokens that exist in no artifact on disk. The sealed derivation governs, and the sealed
tokens are the two above. This follows the same resolution the Stage 3 Attempt 2 session recorded for
the same class of divergence.

And Gate 5's token is explicitly **not** borrowed:

> Gate 5's `pass_result` `ELIGIBLE_FOR_PAPER_TRADING` is NOT Gate 4's pass token. Passing Gate 4
> authorises only the holdout gate. It does not make anything eligible for paper trading, and a Stage
> 4 package that emitted `ELIGIBLE_FOR_PAPER_TRADING` would be claiming a gate it did not evaluate.

Neither Gate 4 token appears as the verdict of *this* session either. This is a pre-registration, not
an evaluation; §21 states the design-session reason code and why it is deliberately distinct from
both.

## 13. What may be read, and how often

| Window | Range | State at the end of this session |
| --- | --- | --- |
| Development | 1993-01-29 to 2021-07-31 | read, no longer pristine |
| Validation | 2021-08-01 to 2024-07-31 | **LOCKED** |
| Final holdout | 2024-08-01 to 2026-07-31 | **SEALED** |

Boundaries are read from `governance/STAGE_1_HOLDOUT_LOCK.json` @
`9696161c4c5612fc7f6b3e5a3410917f20ad5707cb9b89b8bcc39cb70831dfb3` and are not recomputed, widened,
narrowed, or shifted. The single-read rule, verbatim:

> The validation partition is read exactly once, in exactly one authorized session, from exactly one
> dataset load, with both declared runs executed inside that session against that load.

Its basis is `SE100-GOV-1005` `binding_rules` and constitution §9's treatment of the locked
validation period: the holdout's "read exactly once" discipline is applied to the validation window
as the **stricter** reading, since nothing in the lock authorises repeated validation reads. Five
things are prohibited under it, and the third and fourth are the ones a later session is most likely
to want: no third engine run of any kind including a diagnostic, debug, or shutdown-disabled run; and
no re-run after a valid completed evaluation — `SE100-CFG-3004` `rerun_policy` answers "No.", and a
re-run producing a different number would be a determinism defect and a blocker, not a better result.
Also prohibited: reading validation rows to check the data are suitable before running. Suitability
is established by the frozen Stage 1 readiness evidence or not at all.

A 101-session warm-up tail from the **development** window precedes the first validation session.
That is a read of already-authorized development data and it is not look-ahead, because the warm-up
is strictly earlier than the first validation session. It is recorded as interpretation `S4-INTERP-3`
rather than left implicit. `S4-INTERP-2` records that the §7 stressed run is part of the same single
read, defined at the session-and-load level rather than the run level.

Enforcement is structural rather than procedural: `stockedge100.backtest.window.ResearchWindow`
raises `WindowViolation` on any session outside the window authorized for the run, and `MarketView`
raises `LookAheadError` on any read past the decision session. Neither depends on a strategy behaving
well. §17 records that both were exercised on **dates alone**.

## 14. The one measurement this stage authors: the walk-forward fold construction

`SE100-CFG-4002-WF1`. No fold definition exists anywhere on disk (S4-CONFLICT-4), so S4-C6 is
unmeasurable without one, and a fold count chosen after seeing a validation equity curve would be
exactly the fitting Gate 4 exists to rule out. The authority is constitution §8. The construction is
derived from the frozen validation boundaries alone:

> The validation window is partitioned into consecutive, non-overlapping, calendar-aligned blocks of
> exactly three calendar months each, beginning at the validation window start. The window spans 36
> calendar months exactly, so twelve blocks tile it with no remainder and no discarded tail.

12 test folds, 0 train folds, boundaries inclusive, anchored on **2021-08-01** rather than on natural
calendar quarters — 2021-08-01 is not a quarter boundary, and anchoring on the frozen boundary keeps
the construction a function of `SE100-GOV-1005` alone and leaves no discretion. Fold 1 is
2021-08-01 → 2021-10-31; fold 12 is 2024-05-01 → 2024-07-31. The twelve folds are enumerated in the
sealed artifact; §17 records that a test recomputes the tiling from the frozen boundaries and checks
adjacency and exact coverage rather than reading the list back.

`derived_only_from` is recorded on the artifact: "No trading-session count, no price, no indicator
value and no coverage statistic from the validation partition was read to construct these folds."
The folds partition the validation window; they do not redefine it.

Arithmetic that follows and was fixed before any fold return exists: with 12 completed folds the 70%
threshold requires **9** positive folds; 8 of 12 fails. Fewer than 12 completed folds is
`NOT_EVALUABLE`, not a proportion computed on a shrunken denominator — `SE100-CFG-4001`
`partial_or_failed_run_rule` `no_partial_scoring` prohibits scoring a run on the folds it completed
before crashing. And exactly zero is not positive, consistent with S4-C1 and S4-C5.

## 15. The two declared runs, and the run budget

| Run label | Cost basis | Conditions gated |
| --- | --- | --- |
| `SE100-S4-C2-MEANREV-RA1#VALIDATION#BASE` | complete base friction from `SE100-CFG-2001` | S4-C1, S4-C2, S4-C3, S4-C4, S4-C6 |
| `SE100-S4-C2-MEANREV-RA1#VALIDATION#STRESS` | exactly 2× the complete base friction, including the FINRA TAF per-order cap | S4-C5 |

Both are gating, both are the sealed representative, both cover 2021-08-01 → 2024-07-31 with the same
101-session development warm-up. Together with S4-C7 — which is a governance condition rather than a
run condition — the two runs cover all seven conditions and nothing is left unassigned.
`runs_declared.count` is 2 and `count_is_a_hard_limit` is `true`.

The research shutdown is "Enforced identically. It is never disabled for a gating run." No neighbour
runs are declared, and the artifact argues the absence rather than passing over it: Gate 4 states no
neighbour condition, so four extra runs on a once-readable window would gate nothing while
multiplying the draws taken from it — "not a gap in the evidence".

Budget: 1 parameterisation, 2 runs, 1 session reading validation, **0** re-runs after a valid
completed run. The sealed note is the honest framing: *"There is no search at Gate 4. The budget is
not a limit on exploration; it is the statement that no exploration is authorized."*

**Stressed cost changes status at this gate.** At Gate 3 it was non-gating and `SE100-CFG-3004` said
so explicitly — a `STRESS_FRAGILE` flag could not reject a candidate that satisfied every hard
condition. At Gate 4 the frozen gate text makes "stressed-cost total return remains positive" one of
the seven pass conditions. That is not a decision of this stage; it is the frozen text, and the later
gate `SE100-CFG-3004` was putting the number on disk for is this one. The 2.0 multiplier is bound by
digest from `SE100-CFG-2001` and is not re-chosen here.

Three failure modes are pre-committed rather than left to judgement. A run that crashes or does not
reach 2024-07-31 produces no valid evidence, scores nothing, and its conditions are `NOT_EVALUABLE`;
the fix is made outside the validation window and the full evaluation re-run from the start within the
same authorized session, which is one read because nothing was extracted from the failed attempt. If
it cannot complete in that session the outcome is `BLOCKED_BY_INFRASTRUCTURE` and a second session is
**not** self-authorized. An unusable validation partition is `BLOCKED_BY_DATA` and the read is not
spent. And a defect discovered after any validation observation has been read may **not** be repaired
by changing a sealed specification: the outcome is `INVALIDATED`, which is neither a pass nor a fail.
The reason that last rule is absolute is recorded:

> The alternative — allowing a 'clearly unrelated' repair after seeing the numbers — requires someone
> to judge relatedness while holding the result. That judgement cannot be made disinterestedly, so it
> is removed.

## 16. Sealing — measured, not asserted

Four files were sealed at one timestamp, `2026-08-13T14:01:21Z`, under run id
`SE100-R-20260813T140121Z`:

| Pre-registered file | sha256 |
| --- | --- |
| `config/stage4_validation_protocol.json` | `2c9eeb7cf1123430e2d9b1163478d6923879c68fdc17e44b45b5910137a0acea` |
| `config/stage4_gate_criteria.json` | `2191e905121b5fcaf768224fd79577dee3f8b3d5653836843fa1a3514e2c4c0d` |
| `config/stage4_representative_selection.json` | `fb4f3eb506989a80a08dda752f83d390589f1f3126effece91257e43f899d3dc` |
| `governance/STAGE_4_PREREGISTRATION.md` | `952897926fa281b85ee11eefde825e04a7d9cd483d22aef2fee568c5b5672fd1` |

None of those four carries the digest of another, and the seal says why: a file cannot contain the
digest of a file that contains its own. They reference each other by artifact id and path, and
`governance/STAGE_4_PREREGISTRATION.sha256` carries every digest. That record covers the four files
plus the seal JSON — five entries, project-root-relative paths, verified with
`cd stockedge100 && sha256sum -c governance/STAGE_4_PREREGISTRATION.sha256`, all OK. It does not name
itself, because nothing hashes itself.

The same principle governs the S4-C7 recheck set. The declared set is **13** artifacts; the seal
records **12**. The thirteenth is the seal record itself, and its digest is carried by the `.sha256`
record instead. The recheck rule has no tolerance: "Recompute each digest after the evaluation and
require equality with the value recorded in the Stage 4 pre-registration record. Any inequality is
S4-C7 NOT_MET."

Six sealing predicates were measured rather than asserted, each carrying its own definition in the
seal. Stage 3 Attempt 2's `attempt2` marker is now legitimately all over `src/stockedge100/strategies/`
and `reports/stage3_attempt2/`, and those files may not be deleted, so it says nothing about Stage 4
— the predicates here are new:

| Predicate | Value at sealing |
| --- | ---: |
| `stage_4_evaluator_or_result_modules` — `.py` files under `src/stockedge100/` whose path contains `stage4`, excluding exactly this sealing program (one named file, not a whole directory, so an evaluator anywhere — including under `reporting/` — is still counted) | 0 |
| `modules_naming_a_stage_4_run_label` — `.py` files under `src/stockedge100/` whose text contains any declared run label; catches an evaluator grafted into an existing module | 0 |
| `stage_4_report_artifacts` — files under `reports/` whose path contains `stage4`. Must be 0 **at sealing** | 0 |
| `stage_4_run_records` — files under `runs/` whose text contains `STAGE_4` or any declared run label, measured **before** this seal wrote its own run record | 0 |
| `stage_4_modules_touching_restricted_data_or_a_broker` — files under `src/stockedge100/` whose path contains `stage4`, **this sealing program included**, whose parsed syntax tree contains a data-layer import, a dataset-loader call, a network or broker import, an attribute access used to read an environment variable or open a connection, or a string constant containing a URL scheme | 0 |
| `gate_3_attempt_2_records_verify` — both Gate 3 Attempt 2 records verify entry-for-entry from the project root | `true` |

The fifth is the fail-closed proof, and it is an **AST** question rather than a text search for a
stated reason: "a text search would match the words of this very definition". Three of the counts move
after the seal, and the distinction between them is recorded rather than blurred.

Two moves were anticipated in the sealed definitions rather than discovered afterwards.
`stage_4_run_records` becomes 1 because the seal writes a run record carrying `STAGE_4` by
construction, and `stage_4_report_artifacts` becomes non-zero because this session's own test summary,
pytest output, decision record, manifest, and checksum record live under `reports/stage4/`. The sealed
definition of the latter says in so many words that the recorded value "is the count that existed
before this seal".

The third move was **not** anticipated, and it is disclosed here rather than dodged.
`stage_4_evaluator_or_result_modules` becomes 1 the moment this session writes its decision-package
builder at `src/stockedge100/reporting/stage4_package.py`, because the sealed definition excludes
exactly one named file — the sealing program — and says of everything else that "a Stage 4 evaluator
placed anywhere - including under `reporting/` - is still counted". A package builder is not an
evaluator: it reads governance artifacts, recomputes digests, and writes a decision record, and it
computes no return, no metric, and no fold. But the predicate is a path marker, and a marker evaded by
renaming the file is no longer a marker, so the file keeps the name its stage implies and the count is
reported as what it is. Two things stand behind the claim that it is not an evaluator, neither of them
prose: the fifth predicate includes the builder in its own scope by construction — same `stage4` path
marker, no exclusion list — and reads empty over it, so the builder cannot reach a validation or
holdout observation or a broker; and `modules_naming_a_stage_4_run_label` stays 0, so no declared
Stage 4 run label appears anywhere in `src/`. Both are recomputed at build time and recorded in the
decision record's `S4D-C3` evidence, alongside the three moved counts and the files that moved them.
§18 enumerates every such file.

The seal also records a zeroed restricted-data posture — `validation_rows_read`,
`validation_prices_read`, `validation_indicators_computed`, `validation_trades_counted`,
`holdout_observations_read`, `dataset_loads_in_this_session`, all `0` — and states how that is known:
structurally, from the AST predicate above, not by assertion.

The sealing program refuses to run a second time; re-invoking it returns exit 2 because the record
already exists, which is what makes the seal unrepeatable. It also refuses with a distinct exit code
for each way the seal could be illegitimate: 5 if a pre-registered file is missing, 3 on any
contamination predicate, 4 if an upstream record fails, 6 on bound-digest drift, 8 if the
representative does not resolve to exactly one strategy module, and 7 if the Markdown and the JSON
disagree. §17 records that every one of those refusals is exercised by a test that also asserts
nothing was written.

All four Stage 4 JSON artifacts are ASCII-only **in fact**, verified by `text.isascii()` rather than
declared, so their digests are stable under any reader's codec. The pre-registration Markdown is
UTF-8; its digest is pinned in the seal, so its encoding cannot drift silently either.

## 17. Tests

Command, verbatim:

```
cd stockedge100 && python -m pytest tests/unit/test_stage0_governance.py tests/unit/test_stage1_preregistration.py tests/unit/test_stage3_attempt2_preregistration.py tests/unit/test_stage4_preregistration.py -q
```

**263 passed, 0 failed, 0 skipped.** The new file alone is **148 passed, 0 failed, 0 skipped**. Raw
output: `reports/stage4/pytest_stage4_output.txt`. Full detail:
`reports/stage4/STAGE_4_VALIDATION_PREREGISTRATION_TEST_SUMMARY.md`.

The broad command `python -m pytest tests -q` was **not** run, and deliberately: two integration
modules read the normalised dataset and drive the engine over it, which this session may not do. The
recorded command is a four-file selection that reads only governance documents, `config/` JSON, `src/`
text, `runs/` records, and trees the tests build themselves under `tmp_path`. **No test in the
selection opens a price file, computes a return, or touches the validation or holdout windows.** The
three pre-existing files are controls rather than coverage — Stage 0's tests re-verify the
constitution and its freeze record, and Stage 1's and Stage 3 Attempt 2's re-verify pre-registration
seals of the same shape — so a failure among the new 148 is attributable to the new file.

The suite floor rose from 560 to **708** collected (`python -m pytest tests --collect-only -q`, which
imports every module but executes no body). Because the whole suite was deliberately not executed,
"unmodified" is asserted by digest instead of by a green run: every `tests/**/*.py` entry in **both**
Gate 3 Attempt 2 run records was recomputed against disk — 15 recorded, 15 unchanged, 0 changed, 0
missing, against 16 live files, the one addition being
`tests/unit/test_stage4_preregistration.py`. A weakened or deleted test would appear there as changed
or missing. `tests/conftest.py` is one of the 15 verified entries and was not touched. No test wrote
outside `tmp_path`: `runs/` still held exactly 15 records and `reports/` still held only the five
pre-existing stage directories after the run.

What the new tests establish, in outline. The seal parses and declares itself sealed, and the five
pinned digests recompute — written out **independently** of `governance/STAGE_4_PREREGISTRATION.sha256`,
so rewriting an artifact together with its checksum record still fails this module. The checksum
record covers five files and not itself; no hit of a 64-hex sweep over the seal resolves to a tree
digest or to the file's own; `repo_state_id` is absent from the seal and the run record agrees with it
field for field. The selection is exercised as a **rule** rather than a conclusion: the eligible set
is two, C3 is excluded and recorded as not reconsidered, the search for a mandatory rule came back
empty, the one constraint that did apply is the neighbour prohibition, the rule is return-blind, its
provenance resolves, and the screen arithmetic is **re-derived from `declared_runs`** — C1 two trips
including `#STRESS`, C2 zero — rather than read back from `screen_results`. Each of the seven Gate 4
conditions quotes its frozen phrase; each sealed threshold predicate is evaluated in **both**
directions exactly at its boundary; the strict/inclusive difference against Gate 5 is asserted as
preserved; the tokens are derived from the constitution's JSON companion rather than pinned as
literals, and each of `NOT_MET`, `NOT_EVALUABLE`, `NOT_RUN` and `UNKNOWN` is shown to fail the gate,
as is a missing condition. The twelve folds are recomputed from the frozen boundaries with
day-level adjacency and three-month arithmetic, and 9/12 is shown to pass where 8/12 fails.

Three clean controls sit at the top of the file, and one of them matters most: a synthetic evidence
table in which all seven conditions are `MET` **does** yield the sealed pass token. A gate predicate
hard-wired to fail would be indistinguishable from a correct one without it — and on a stage whose
own disclosure says a `FAIL` is a likely outcome, that is exactly the failure mode that would go
unnoticed.

The fail-closed section proves the pre-registration path cannot reach a restricted observation, and
it does so on **dates alone** — a test that proves a module cannot read validation data may not read
one either. A `MarketView` cannot be constructed at a validation `as_of` even with no series
supplied, because the refusal happens on the date before any observation is involved; the development
window refuses validation and holdout dates; `window_named()` bounds equal the lock partition with
`holdout_state == "SEALED"`; the AST predicate reads empty over the live tree and the sealing program
is itself in that predicate's scope. All six sealing predicates are then exercised in both directions
over a synthetic tree, a parametrised test forces each of five predicates non-empty in turn and
requires exit 3 with **nothing written**, and each remaining refusal exit — 2, 4, 5, 6, 7, 8 — has its
own test. One row of the AST table is a deliberate control: a URL assembled at runtime is not
claimed as a violation. And one test exists because the sealing program's first dry-run failed on it —
the URL marker table is **composed** from schemes rather than written literally, so the predicate does
not flag the file that defines it.

No test covers the decision package, and none can: `tests/**/*.py` is one of the patterns
`repo_state_id` is computed over, so a test asserting that digest would invalidate the value it
asserts the moment it was written. The package is verified by re-running the recomputation.

## 18. Contamination assessment

| Question | Finding |
| --- | --- |
| Was any validation observation read, at any point, for any purpose? | **No.** `validation_rows_read`, `validation_prices_read`, `validation_indicators_computed`, `validation_trades_counted` and `dataset_loads_in_this_session` are all `0`, and that is known structurally: no module on the pre-registration path imports the data layer or calls a dataset loader, which is the AST predicate recorded as 0 and exercised in both directions. The only validation-partition facts in any Stage 4 artifact are the boundary dates, which `SE100-GOV-1005` publishes as frozen metadata, and calendar arithmetic on them. |
| Was the holdout accessed? | **No.** `holdout_observations_read` is `0`; the window state is `SEALED`. `STAGE_1_HOLDOUT_LOCK.json` was read for its lock state and bound by digest. |
| Was any Stage 4 evaluator or result file created? | **No.** Two independent predicates — a path-based one over `src/stockedge100/` and a content-based one over declared run labels — both read 0, both tested in the negative direction and both wired to refusal. No empty or placeholder evaluator or result file was created; `SE100-CFG-4001` `explicit_non_authorizations` names creating one as unauthorized. |
| Was any development backtest, re-run, or re-measurement performed? | **No.** No engine was invoked in this session. Every development figure quoted in this report or in any Stage 4 artifact was read from Gate 3 Attempt 2's sealed evidence file, which was itself verified by checksum record before it was read. |
| Was a broker, credential, or network reached? | **No**, and this is an AST finding rather than a `grep` finding: no forbidden import root, no forbidden attribute access, and no string constant containing a URL scheme anywhere in the Stage 4 module scope, the sealing program included. |
| Is the **gate design** prospective with respect to validation results? | **Yes.** Every threshold, boundary treatment, measurement, verdict token, fold boundary, run label, and failure rule was written and sealed before any validation observation existed — and six of the seven measurements are adopted by digest from artifacts sealed before Gate 3 was even evaluated. |
| Is the **selection** independent of the evidence that motivated it? | **No, and this is disclosed, not claimed.** Gate 3's development results were lawfully visible. The rule's *output* is return-blind and would be unchanged under reversed returns; the *choice* of predicate was made by a researcher who had read the evidence. §8 records the limitation and the five mitigations verbatim rather than arguing it away. |

Files created by this session that move a sealing predicate after the seal, each classified. §16
separates the two anticipated moves from the one that was not:

| Path | Class |
| --- | --- |
| `runs/SE100-R-20260813T140121Z.json` | the seal's own run record — anticipated in the predicate definition |
| `tests/unit/test_stage4_preregistration.py` | test module (not under `reports/`; recorded here for completeness) |
| `governance/STAGE_4_VALIDATION_PREREGISTRATION_REPORT.md` | this report |
| `src/stockedge100/reporting/stage4_package.py` | decision-package builder |
| `reports/stage4/STAGE_4_VALIDATION_PREREGISTRATION_TEST_SUMMARY.md` | test artifact |
| `reports/stage4/pytest_stage4_output.txt` | test artifact |
| `reports/stage4/STAGE_4_VALIDATION_PREREGISTRATION.json` | design-session decision record |
| `reports/stage4/STAGE_4_VALIDATION_PREREGISTRATION_ARTIFACT_MANIFEST.json` | artifact manifest |
| `reports/stage4/STAGE_4_VALIDATION_PREREGISTRATION.sha256` | checksum record |
| `runs/<this session's run id>.json` | design-session reproducibility record |

None is strategy code. None is a Stage 4 evaluator. None is a performance result. None contains a
return, a drawdown, a trade count, a fold return, or an equity value for the validation window,
because no such value exists.

Two authoring facts are recorded rather than smoothed over. The sealing program's **first dry-run
failed its own AST predicate**, because a literal URL scheme in a predicate definition is a string
constant containing a URL scheme; the fix was to compose the marker table from schemes, and a test
now pins that composition. And the operating prompt for this stage named Gate 4 pass/fail tokens that
exist in no artifact on disk; the sealed derivation governs, and the divergence is recorded in §12
rather than resolved by editing anything. No timestamp in any Stage 4 artifact was hand-typed.

## 19. Design-session gate conditions

Gate 4 itself was **not** evaluated in this session. The conditions below are the conditions for a
legitimate seal, and they are what the decision record carries. Each is recomputed from the written
artifacts at build time rather than loaded from a results file, because a pre-registration session has
no evidence file — its artifacts *are* its evidence.

| Condition | Requirement | Verdict |
| --- | --- | --- |
| `S4D-C1` frozen governance verified | Stage 0 freeze verified digest-for-digest on both halves; twelve upstream checksum records verify entry-for-entry from their intended working directories, before any Stage 4 artifact was authored | MET |
| `S4D-C2` validation evaluation permitted | Frozen on-disk governance authorises a prospective Stage 4 pre-registration and nothing executable, with the determination resting on quoted frozen text rather than on the operating prompt | MET |
| `S4D-C3` no restricted observation read | Zeroed restricted-data posture across all six counters, established structurally by an AST predicate whose scope includes every Stage 4 module — the sealing program and this package builder both — recomputed at build time and empty; no declared run label anywhere in `src/`; Gate 3 Attempt 2 records still verify; the three predicates that moved after the seal reported with the files that moved them | MET |
| `S4D-C4` selection lawful and prospectively defensible | Mandatory-rule search recorded and empty; eligible set exactly the two admitted PRIMARY candidates; rule return-blind, parameter-free, applied in full to both candidates; survivor count 1; the stop-for-human alternative recorded before application | MET |
| `S4D-C5` Gate 4 extracted, not invented | Seven conditions from the frozen Markdown; six thresholds derived from the constitution's JSON companion; both tokens derived from the sealed derivation with neither taken from a prompt; six of seven measurements adopted by digest | MET |
| `S4D-C6` the one authored measurement is disclosed and derived | The fold construction is the single measurement this stage authors; derived from the frozen partition boundaries alone; recorded as S4-CONFLICT-4 with its §8 authority; `train_folds` empty per S4-CONFLICT-5 | MET |
| `S4D-C7` adaptation disclosed | The selection is disclosed as adaptive, with the residual freedom stated and five mitigations recorded; the narrowest margin of the survivor recorded; the cumulative development experiment count not reset — 24 development runs across both Gate 3 attempts, plus this stage's 2 | MET |
| `S4D-C8` specification complete | Two runs declared with a hard limit, one parameterisation, zero re-runs; every condition assigned to a run or to S4-C7; failure, defect, and unusable-data outcomes pre-committed; no discretionary choice left to the evaluation session | MET |
| `S4D-C9` sealing integrity | Checksum record verifies 5/5 from the project root; Markdown and JSON materially agree; all four JSON artifacts ASCII-only in fact; S4-C7 set 13 declared / 12 recorded with the omission being the record itself; no tree digest written inside a covered file; the sealer refuses a second run | MET |
| `S4D-C10` partitions unchanged | No window authorized in this session; validation `LOCKED`; holdout `SEALED`; enforcement structural through `ResearchWindow` / `MarketView`; the folds partition the validation window without redefining it; no boundary moved | MET |
| `S4D-C11` test floor rose | 708 collected, up from 560; four-file selection 263 passed / 0 failed / 0 skipped, the new module 148; 15 of 15 recorded test-file digests unchanged; nothing weakened, skipped, `xfail`ed, or deleted | MET |
| `gate_4_admissible_candidate_exists` | Whether the representative satisfies all seven Gate 4 conditions on the validation window | **NOT_RUN.** No validation observation was read and no Stage 4 evaluator exists. This row exists so that this package cannot be read as a Gate 4 determination. |

## 20. Limitations

- **Gate 4 is not passed, and not evaluated.** A sealed pre-registration is a specification, not
  evidence. Nothing here indicates that the representative will satisfy S4-C2 or any other condition.
- **A `FAIL` is a live and arguably likely outcome, and it is recorded as an expectation.** Neither
  Gate 3 admitted candidate reached S4-C2's frozen Sharpe floor of 0.50 on development data at the
  same sealed 0% cash rate. `SE100-CFG-4001` `adaptive_research_disclosure` states this before any
  validation observation exists, precisely so that a later session cannot treat a fail as a defect to
  be worked around.
- **The selected representative has little drawdown headroom.** Its largest non-breaching development
  neighbour sat 34 basis points below the 15% level that is simultaneously the §5.1 shutdown and
  S4-C3's ceiling. S4-C3 is a real risk of failure, not a formality.
- **The selection is adaptive.** Return-blindness constrains the rule's output, not the choice of
  predicate. A different return-blind predicate might have selected differently.
- **The 0% documented cash rate makes S4-C2 easier to pass** than a real short-rate series would. It
  was sealed in `SE100-CFG-2001` before Gate 3 was evaluated and is not chosen here, but any Gate 4
  pass must travel with that qualification.
- **The fold construction is authored in this session.** It is derived from frozen boundaries and
  fixed before any fold return exists, but it is the one Gate 4 measurement that is not adopted by
  digest from a pre-existing artifact.
- **No multiplicity correction is applied.** Gate 4 specifies none and this protocol invents none.
  The cumulative count for any later statistical interpretation is 24 development runs across both
  Gate 3 attempts plus this stage's 2, and this stage does not reset it.
- **One validation window is one window.** Three years, one instrument, one macro regime, evaluated
  once. It is the strongest evidence this design can produce at this stage and it is not a
  demonstration that an edge exists.
- **Drawdown is measured at session closes.** The project holds no intraday data, so every measured
  drawdown is a lower bound on the true intraday figure. Inherited unchanged.
- **The whole test suite was not executed**, so "unmodified" for the 15 pre-existing test files is
  asserted by digest recomputation rather than by a green run.
- **`scipy` and `pyarrow` are not installed**, and no Stage 4 rule requires either.

## 21. Authorization state

| Activity | State |
| --- | --- |
| Stage 4 validation evaluation — exactly the two sealed runs of `SE100-S3A2-C2-MEANREV-RA1` | **UNLOCKED** for a later, separately authorized session. Nothing else. |
| Validation-window access in this session | **LOCKED.** `validation_access_authorized_in_this_session = false`. |
| Validation-window access in that later session | **AUTHORIZED_FOR_EXACTLY_ONE_READ** — one session, one dataset load, two runs, zero re-runs |
| Evaluating the other Gate 3 admitted candidate on validation | **PROHIBITED**, before or after any C2 result |
| Final holdout | **SEALED**, regardless of the Gate 4 verdict. Read once, at Gate 5, after a separate authorization recorded there. |
| Stage 5 / constitutional gate 5 | **LOCKED.** Requires a Gate 4 pass, which does not exist. |
| Alpaca paper trading | **LOCKED.** Gate 5's `ELIGIBLE_FOR_PAPER_TRADING` is reachable only from Gate 5. |
| Shadow-live | **LOCKED** |
| Alpaca live trading | **LOCKED.** `live_trading_authorized = false`. |
| Capital or risk expansion | **LOCKED** |

Nine forward-authorization flags are `false` in every Stage 4 artifact:
`validation_access_authorized_in_this_session`, `holdout_access_authorized`, `gate_4_evaluated`,
`gate_4_passed`, `stage_5_authorized`, `paper_trading_authorized`, `shadow_live_authorized`,
`capital_or_risk_expansion_authorized`, `live_trading_authorized`. `gate_3_passed` is `true` and
`validation_evaluation_authorized` is `true` — the latter scoped, in the sealed record's own words, to
"Exactly one evaluation of SE100-S3A2-C2-MEANREV-RA1 on the locked validation window, in a later
separately authorized session, under config/stage4_validation_protocol.json and
config/stage4_gate_criteria.json exactly as sealed here. Nothing else."

Stage 5 remains prohibited on the nine conditions listed in `SE100-CFG-4001`
`stage_5_remains_prohibited_conditions`, and seven `explicit_non_authorizations` in the same file each
open "This protocol does not authorize" — covering reading the validation window in the session that
wrote it, implementing the evaluator, creating empty or placeholder evaluator or result files, any
development backtest or re-measurement, acquiring any new data source including a Treasury-bill
series, any Alpaca or broker interaction or credential read or network access, and a second Gate 4
attempt. Two of those nine conditions are worth stating in full here: **no order-submitting code
exists in this repository and none is written by this stage**, and **StockEdge100 is not trade-ready
and may not be described as trade-ready.**

**On the verdict token.** The primary verdict `PASS` is one of the seven in constitution §10. The
reason code `STAGE_4_VALIDATION_PREREGISTRATION_FROZEN` is a design-session reason code, following
the precedent of `STAGE_3_ATTEMPT_2_PREREGISTRATION_FROZEN`, which the Stage 3 Attempt 2 design
session minted for the same purpose. It is deliberately **neither** of Gate 4's own tokens. Emitting
`STAGE_4_STRATEGY_ADMITTED_IN_VALIDATION` here would claim a gate this session did not evaluate, and
emitting `STAGE_4_STRATEGY_REJECTED_IN_VALIDATION` would record a rejection on evidence that does not
exist. Both belong to the evaluation session and to no other. The package builder asserts this rather
than trusting it.

## 22. Next authorized action

Exactly one: **a separate session that evaluates only `SE100-S3A2-C2-MEANREV-RA1`, only on the
validation window 2021-08-01 → 2024-07-31, in exactly the two runs declared in `SE100-GOV-0008`** —
one at the sealed base friction and one at exactly 2× it — from one dataset load, at the sealed
parameterisation, with the §5.1 research shutdown enforced in both, scored against the seven sealed
Gate 4 conditions and the twelve sealed folds, emitting one of the two sealed Gate 4 tokens.

No parameter may be changed. No neighbour may be run. The other admitted candidate may not be run,
before or after. There is no third run, no re-run after a valid completed run, and no second session.
The holdout stays sealed either way.

## Verdict

`PASS — STAGE_4_VALIDATION_PREREGISTRATION_FROZEN`

The verdict means one thing and nothing more: a single representative has been selected from the two
Gate 3 admitted candidates by a return-blind, parameter-free rule applied in full to both and recorded
with its limitation; the frozen gate 4 conditions — all seven, including the one the constitution's
JSON companion omits — have been extracted from frozen text, adopted by digest where they already
existed, and specified prospectively in the single place where they did not; and the whole procedure
was sealed before any validation observation was read, which is measured rather than asserted. It is
**not** a gate 4 pass, **not** a gate 4 evaluation, **not** a statement that the representative will
be admitted, **not** a performance claim of any kind, and **not** an authorization for holdout access,
stage 5, paper trading, shadow-live, or live trading. `live_trading_authorized` remains `false`.
StockEdge100 is not trade-ready.
