# Stage 3 Attempt 2 evaluation test summary

Command: `cd stockedge100 && python -m pytest tests -q`
Collection: `cd stockedge100 && python -m pytest tests --collect-only -q`
Raw output: [pytest_stage3_attempt2_evaluation_output.txt](pytest_stage3_attempt2_evaluation_output.txt)

**560 passed, 0 failed, 0 skipped, 0 errors — 560 tests collected.**

The counts in the decision record are parsed from that capture at build time, never typed in: a
missing capture, a single failure, a single error, or a collection count that does not reconcile with
`passed + failed + skipped` refuses to write the package.

The capture holds exactly two command blocks for the same reason. The parser reads the *last* summary
line and the *last* collection line in the file, so appending a narrower run — the three new modules
on their own, say — would silently redefine the recorded counts as that narrower run's. Per-module
figures below therefore come from `--collect-only` and are stated as collection counts; the passing
status of every one of them comes from the single whole-suite run above.

## Why the broad command was run this time

The design session could not run `pytest tests -q`: it was forbidden to load market observations, and
[test_stage1_data_foundation.py:73](../../tests/integration/test_stage1_data_foundation.py#L73) reads
every normalised CSV while
[test_stage2_backtest.py:373](../../tests/integration/test_stage2_backtest.py#L373) calls
`load_dataset(("SPY",))` and drives the engine over it. This session is the authorised implementation
and development evaluation on the development window, so both reads are in scope and the whole suite
runs — which is the stronger claim, and the one the floor deserves.

What remains out of scope is the validation window and the final holdout, and the distinction is
narrower than "does anything open a CSV". The normalised files are one series per symbol spanning the
whole acquired history through the Stage 1 usable cutoff, and Gate 1 hashes them whole, so a
file-level read necessarily brings post-development rows into memory. What may not happen is a
*price* from such a row entering a computation, a comparison, or a report. It does not:

- The three frozen Stage 1 tests that hold a whole frame assert on the **schema and the session-key
  column only** — column names (`test_normalized_schema_matches_the_sealed_specification`), every
  session key being a real XNYS trading day, the first and last session keys re-deriving the locked
  partition, and the last session key being the recorded `usable_cutoff_session`. Dates, not prices.
- The Stage 2 benchmark reconciliation computes over `2005-01-03 → 2009-12-31` and
  `2015-01-02 → 2016-12-30`, both wholly inside the development window.
- Every Attempt 2 run is bounded structurally, not by convention: `BacktestEngine.__init__` calls
  `window.check` on both bounds and raises `WindowViolation`, and each decision builds a
  `MarketView` that raises `LookAheadError` for any bar past the decision session.

A textual sweep of `tests/**/*.py` for a date literal later than `2021-07-31` finds **25**, and every
one is calendar arithmetic: 24 in `tests/unit/test_stage1_calendar_partition.py`, which computes
partition boundaries from dates and reads no file, and one at
[test_stage1_adversarial.py:316](../../tests/adversarial/test_stage1_adversarial.py#L316), where
`"2025-01-01"` is written into an in-memory copy of the holdout lock so the guard that refuses a moved
boundary can be shown to fire. No test names a validation or holdout **observation**.

## The floor did not fall

| File | Tests | What it establishes |
| --- | ---: | --- |
| `tests/unit/test_stage0_governance.py` | 27 | Stage 0 regression floor. **Unmodified.** |
| `tests/unit/test_stage1_calendar_partition.py` | 34 | Stage 1 floor. **Unmodified.** |
| `tests/unit/test_stage1_preregistration.py` | 17 | Stage 1 floor. **Unmodified.** |
| `tests/integration/test_stage1_data_foundation.py` | 33 | Stage 1 floor. **Unmodified.** |
| `tests/adversarial/test_stage1_adversarial.py` | 29 | Stage 1 floor. **Unmodified.** |
| `tests/unit/test_stage2_engine.py` | 54 | Stage 2 floor. **Unmodified.** |
| `tests/adversarial/test_stage2_defects.py` | 42 | Stage 2 floor. **Unmodified.** |
| `tests/integration/test_stage2_backtest.py` | 37 | Stage 2 floor. **Unmodified.** |
| `tests/unit/test_stage3_strategies.py` | 69 | Stage 3 Attempt 1 floor. **Unmodified.** |
| `tests/adversarial/test_stage3_defects.py` | 47 | Stage 3 Attempt 1 floor. **Unmodified.** |
| `tests/unit/test_stage3_attempt2_preregistration.py` | 71 | Attempt 2 design floor — the seal, its four contamination predicates in both directions, Attempt 1 immutability, the unchanged Gate 3 criteria, candidate completeness, the adaptation disclosure, partitions and authorisation, MD/JSON agreement. **Unmodified.** |
| `tests/unit/test_stage3_attempt2_implementation.py` | 51 | **New.** Traceability, identifiers, parameters, indicators, the seven Gate 3 predicates and the combination rule. |
| `tests/adversarial/test_stage3_attempt2_defects.py` | 30 | **New.** RA1-1 … RA1-8 driven one session at a time, one injected defect per test. |
| `tests/integration/test_stage3_attempt2_backtest.py` | 19 | **New.** The real engine, planner and candidates end to end on synthetic series. |
| **Total** | **560** | |

Stage 0 contributed 27, Stage 1 brought the total to 140, Stage 2 to 273, Stage 3 Attempt 1 to 389,
and the Attempt 2 design session to 460. This evaluation session adds **100**. Nothing was weakened,
skipped, `xfail`ed, or removed; the floor only rises.

"**Unmodified.**" is asserted by digest as well as by the green run. Every `tests/**/*.py` entry in the
Attempt 2 design run record `runs/SE100-R-20260810T131107Z.json` was recomputed against disk:
**12 recorded, 12 unchanged, 0 changed, 0 missing**, against 15 live files — the three additions being
the three new modules above. The same record's `src/**/*.py` entries were recomputed the same way:
**49 recorded, 0 changed, 0 missing**, against 58 live files, the nine additions being this session's
seven `strategies/attempt2_*.py` modules and two `reporting/` modules. So the claim that this session
only added code is falsifiable independently of the suite passing, and a weakened or deleted test
would appear as a changed or missing entry rather than as a quieter run.

`tests/conftest.py` was not touched; it is one of the 12 verified entries. Every fixture the three new
modules need is defined locally in them. No test writes into `data/`, `governance/`, `config/`, or
`reports/`; the new modules build synthetic trees and series under `tmp_path`, and
`attempt2_harness.run_all` is never called from a test — the 18 declared runs happen exactly once, in
the evaluation step.

## §12 coverage, requirement by requirement

`impl` = `tests/unit/test_stage3_attempt2_implementation.py`, `adv` =
`tests/adversarial/test_stage3_attempt2_defects.py`, `int` =
`tests/integration/test_stage3_attempt2_backtest.py`.

| Required area | Where |
| --- | --- |
| Candidate-to-pre-registration traceability | impl `test_the_traceability_map_resolves_every_sealed_rule`, `test_the_three_new_test_modules_define_every_traced_test_name` |
| Exact candidate and variant identifiers | impl `test_exactly_three_candidate_ids_are_implemented`, `test_an_unregistered_experiment_id_is_refused`, `test_four_neighbours_per_candidate_exactly_as_registered`, `test_variant_count_is_checked_against_the_seal`, `test_declared_run_counts_are_checked_against_the_seal` |
| Exact parameters | impl `test_primary_parameters_match_the_seal_exactly`, `test_every_parameter_comes_from_the_digest_verified_seal`, `test_variant_specs_reproduce_the_sealed_universe`, `test_c3_defensive_null_neighbour_keeps_the_declared_universe`, `test_no_fitted_model_and_no_undeclared_parameter`, `test_ra1_parameters_have_no_defaults` |
| Signal timing | impl `test_signal_target_rule_c1` / `_c2` / `_c3`, `test_warmup_reproduces_the_sealed_derivation`; int `test_decision_reads_no_bar_after_the_decision_session`, `test_one_decision_per_session_and_no_same_close_fill` |
| Entry and exit rules | adv `test_entry_emits_one_order_sized_by_ra1_2`, `test_exit_precedence_is_loss_control_then_max_hold_then_signal`, `test_sizing_is_read_at_entry_only`, `test_attempt_1_entry_order_default_is_unreachable` |
| Maximum holding periods | adv `test_max_hold_counts_decision_sessions_inclusively` |
| 50% exposure ceiling (RA1-1) | adv `test_no_entry_fraction_exceeds_f_base`, `test_no_entry_fraction_exceeds_f_base_guard_fires_when_the_cap_is_tampered_with`, `test_a_clean_entry_fixture_emits_one_buy_at_the_ceiling_fraction` |
| 10% volatility target (RA1-2) | impl `test_vol20_follows_the_sealed_six_step_procedure`, `test_vol20_is_undefined_below_twenty_one_bars`, `test_vol20_uses_adj_close_not_close`; adv `test_volatility_floor_blocks_entry_below_five_percent`, `test_zero_volatility_blocks_entry_before_any_division`, `test_insufficient_history_blocks_the_entry_and_holds_cash` |
| 8% per-position loss control (RA1-3) | adv `test_loss_control_triggers_at_exactly_eight_percent`, `test_loss_control_reference_is_the_decision_close`, `test_unfilled_entry_discards_its_reference_price` |
| Account de-risk ladder (RA1-5) | impl `test_ladder_rungs_are_threshold_inclusive`; adv `test_ladder_never_blocks_an_entry`, `test_hwm_updates_every_decision_session_whether_flat_or_not` |
| Re-entry lockout (RA1-6) | adv `test_lockout_lasts_five_decision_sessions_after_a_risk_exit`, `test_signal_exit_creates_no_lockout`, `test_lockout_blocks_entry_without_substitution` |
| Flat-first conflict handling (RA1-7) | adv `test_flat_first_emits_only_the_sell_on_a_switch` |
| All-or-nothing positioning (RA1-8) | adv `test_positions_are_all_or_nothing`, `test_at_most_one_open_position_and_no_short`, `test_defensive_leg_gets_no_carve_out` |
| Cash accounting | adv `test_size_floor_blocks_entry_below_one_dollar`; int `test_cash_is_the_residual_and_the_buffer_holds` |
| Costs and execution assumptions | int `test_stale_marks_follow_the_gate_2_engine`, `test_one_decision_per_session_and_no_same_close_fill`; impl `test_stress_run_is_never_passed_to_the_gate`, `test_stress_fragile_flag_changes_no_verdict` |
| Drawdown calculation | impl `test_s3_c2_matches_the_sealed_predicate`, `test_the_fifteen_percent_ceiling_is_unchanged`, `test_no_ra1_constant_references_the_fifteen_percent_ceiling`; int `test_s3_c2_is_met_if_and_only_if_the_shutdown_never_fires` |
| Profit-factor calculation | impl `test_s3_c3_matches_the_sealed_predicate` |
| Closed-trade counting | impl `test_s3_c4_matches_the_sealed_predicate` |
| Best-trade removal | impl `test_s3_c5_matches_the_sealed_predicate` |
| Concentration calculation | impl `test_s3_c6_matches_the_sealed_predicate` |
| Neighbour-sign stability | impl `test_s3_c7_matches_the_sealed_predicate`, `test_a_missing_neighbour_makes_s3_c7_fail_not_pass`, `test_no_neighbour_is_ever_promoted` |
| Gate conjunction and disjunction | impl `test_conjunction_within_candidate_and_disjunction_across`, `test_candidates_are_never_combined`, `test_all_seven_conditions_are_evaluated_for_every_candidate`, `test_not_evaluable_and_not_run_are_never_satisfied`, `test_rollup_aggregates_on_satisfaction_not_on_met`, `test_rollup_carries_three_separate_lists`, `test_the_conditions_table_carries_the_decisive_row`, `test_tokens_are_read_from_the_sealed_derivation` |
| Shutdown liquidation and permanent deactivation | int `test_shutdown_liquidates_and_never_rearms`; adv `test_candidate_emits_nothing_while_shutdown_is_active` |
| Missing and invalid data | adv `test_missing_bar_for_a_target_falls_through_to_cash`, `test_non_positive_adjusted_close_traps_rather_than_imputes`; int `test_no_price_is_imputed_or_repaired`, `test_a_run_short_of_the_window_end_is_refused` |
| Deterministic reproduction | int `test_a_rerun_reproduces_both_digests`, `test_no_variant_is_run_twice_for_its_result`; impl `test_no_rule_depends_on_dictionary_or_file_order`, `test_no_float_in_any_signal_sizing_or_risk_path`, `test_random_seeds_are_null_and_recorded_as_null` |
| Restricted-partition rejection | int `test_validation_bounds_are_refused`, `test_no_excluded_symbol_is_ever_loaded`, `test_only_daily_bars_are_loaded`, `test_warmup_history_comes_from_inside_the_development_window`, `test_run_start_requires_warmup_for_every_declared_symbol` |
| Holdout non-access | int `test_holdout_bounds_are_refused`, plus `governance/STAGE_1_HOLDOUT_LOCK.json` re-read and asserted still `SEALED` in the Attempt 2 design module |
| No broker or live authorisation | `tests/unit/test_stage3_attempt2_preregistration.py:738-761` (the sealed protocol's `live_trading_authorized is False`), `tests/adversarial/test_stage3_defects.py:736` (an evidence body mutated to `live_trading_authorized=True` must be refused), `tests/unit/test_stage1_preregistration.py:140`, and `tests/integration/test_stage1_data_foundation.py:358` (broker eligibility still `UNVERIFIED`) |
| Manifest and checksum verification | impl `test_sealed_files_still_hash_to_the_pinned_values`; the eleven checksum records are re-verified at build time from the working directory each one's own path convention requires |

The last row is the one place where nothing new was written: the four existing tests already assert
the negative in the frozen floor, and duplicating them in a new module would have added a line, not a
guarantee. What this session added instead is measured rather than asserted — a scan of `src/**/*.py`
finds **0** occurrences of `socket`, `urllib`, `httpx`, `http.client`, `ALPACA`, `API_KEY` or
`SECRET`; the only `alpaca` strings anywhere in `src/` are `authorization_state` keys whose value is
`LOCKED`; and the sole provider client in the tree, `yfinance`, is imported inside two function bodies
of the Stage 1 acquisition module and is on no Attempt 2 code path.

## The three new modules

**impl — the sealed specification, read rather than restated.** Every assertion traces to a rule in
`SE100-CFG-3003`, `SE100-CFG-3004` or `SE100-CFG-3002`, and where a docstring paraphrases, the
assertion reads the file. Parameters come from the digest-verified seal, so a changed sealed value
fails here instead of silently propagating; the verdict tokens are taken from the sealed
`verdict_token_derivation` rather than from a literal; the 15% ceiling is asserted still 15% on the
same session-close equity series, and separately asserted **not** to appear in any RA1 constant, which
is what keeps RA1 from degenerating into a "stop just under the ceiling" device. The seven Gate 3
predicates are each tested `MET` on evidence that satisfies them and `NOT_MET` on evidence that does
not, because a predicate wired to one answer passes a one-sided test. Three properties of the rollup
are pinned directly: it aggregates on **satisfaction** and not on `verdict == "MET"`, it carries
`met_by`, `not_met_by` and `not_applicable_for` as three separate lists, and the conditions table
carries the decisive `admissible_candidate_exists` row. All three matter for this stage's actual
result: S3-C6 is `NOT_APPLICABLE_BY_CONDITION_TEXT` for two candidates and `NOT_MET` for the third, so
an aggregation on `MET` would have reported a false gate failure on a row that no candidate met and
two satisfied. Secondary metrics, benchmarks and the stressed-cost runs are each asserted to be
reportable and never gating, in both directions — including that a `fragile` stress flag changes no
verdict.

No test in this module loads a market observation: the gate predicates run on synthetic
`BacktestResult` values built by hand, and the signal rules on synthetic `PriceSeries` values whose
numbers were computed by hand.

**adv — RA1 one session at a time, one defect per test.** The module drives `Ra1Candidate.decide`
over synthetic paths and injects exactly one defect per test. Three clean controls come first: a clean
entry fixture emits one buy at the ceiling fraction, a clean hold fixture emits nothing, and — the
control that matters most on a stage that can reject everything — a synthetic candidate meeting every
threshold *is* admitted with stage verdict `PASS`. Attempt 1 rejected all six of its candidates; an
evaluator that refuses everything would be indistinguishable from a correct one without that third
control.

Three properties hold across the whole module. No market observation is read — nothing calls
`load_dataset` or `load_series`. The window is local: `view_at` builds a throwaway `ResearchWindow`
named `"test"` spanning 1990–2030, so no assertion here depends on the real partition and none of them
probes it. And RA1 constants are read out of the seal rather than restated — `SEALED_RA1` is C1's own
`primary_parameters`; only the signal lookbacks (`SCAFFOLD_SMA`, and `max_hold` in a few ordering
tests) are overridden, each documented at its use as scaffolding, and neither is a gate input.

**int — the real engine, synthetic series.** This module runs the actual `BacktestEngine`, planner and
candidates end to end: window enforcement at construction, the warm-up rule against the real exchange
calendar, staleness accounting, the cash residual, the §5.1 research shutdown, and the determinism of
both digests. Its three controls establish that the scaffold runs the whole planned window, that a
clean series never trips the shutdown, and that the development window is the one the engine accepts —
so a refusal below them is the guard firing and not a mis-specified fixture. **No test here loads a
normalised CSV**; `load_dataset` is monkeypatched where the loader path itself is under test. The
validation and holdout windows appear at two lines only, `window_named` fetched purely to assert that
`WindowViolation` is raised and that the session is `not WINDOW.contains(...)` — bounds, never bars.

## Three defects, all found before any result existed

Every one was found and corrected before the first valid completed evaluation, which is the only point
at which §7 permits a correction at all.

| # | Defect | Caught by |
| --- | --- | --- |
| 1 | `stress_evidence` probed a `stress['cost_model']['stress_multiplier']` key that does not exist | the stressed-cost run raising on its first call, before any gating run |
| 2 | `decisive_row` emitted the condition *prose* under the key `gate_verdict_token` | reading the assembled row against the sealed `verdict_token_derivation` |
| 3 | `attempt2_config.py` mentioned the literal `require_seal=False` in a docstring | the frozen guard [test_stage3_defects.py:324](../../tests/adversarial/test_stage3_defects.py#L324), a lexical scan of `src/**/*.py` |

Defect 3 is the instructive one. The frozen guard is a text scan, not a call-graph analysis, so a
docstring mention tripped it — and the fix was to delete the dead parameter the docstring was
describing, not to add an exemption to the guard. The suite went `1 failed, 559 passed` →
`560 passed`. No frozen test was weakened, skipped or exempted to reach that.

A fourth finding was a fixture-design error in mine rather than a defect in the code: an early
integration assertion required the 5% cash buffer to hold at every equity point. It does not, and the
engine is right — the buffer is a **pre-trade** constraint, so a position that appreciates can leave
the realised cash fraction below 5% (the lowest observed is 0.0412). The assertion was corrected to
the sealed rule, not the engine to the assertion, and the characteristic is disclosed as a limitation
in the decision record.

## What the suite deliberately does not cover

**The decision package.** `tests/**/*.py` is one of the patterns `repo_state_id` is computed over, so a
test asserting that digest would invalidate the value it asserts the moment it was written. The
package is verified by re-running the recomputation — the eleven checksum records from their own
working directories, the evidence self-digest with a control in each direction of its own coverage
sentence, and the ending `repo_state_id` — not by a test.

**Whether the admitted candidates work.** Nothing here measures whether a return is real. The suite
establishes that the implementation is the sealed specification, that the gate predicates are the
sealed predicates applied in both directions, and that the partitions held. Development admissibility
is a screening result on data that Attempt 1 already saw; it is not evidence of an edge, and no test
in this file claims otherwise.
