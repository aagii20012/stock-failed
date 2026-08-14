# Stage 0 — Test Summary

**Project:** StockEdge100 · **Generation:** 1 · **Stage:** 0
**Command:** `python -m pytest tests -v --tb=short`
**Raw output:** `reports/stage0/pytest_stage0_output.txt`
**Interpreter:** CPython 3.10.6 · **pytest:** 8.4.2 · **Platform:** Windows 11 (win32)

## Totals

| Result | Count |
|---|---|
| Passed | 27 |
| Failed | 0 |
| Errored | 0 |
| Skipped | 0 |
| xfail / xpass | 0 |
| **Total collected** | **27** |

Wall time: 0.09 s.

## Coverage of Gate 0 conditions

| # | Test | Gate 0 condition exercised |
|---|---|---|
| 1–3 | `test_required_stage0_artifact_exists[3 files]` | required artifacts exist and are non-empty |
| 4 | `test_freeze_record_covers_both_constitution_files` | the freeze record covers exactly the two constitution files |
| 5 | `test_freeze_record_paths_are_relative_to_governance_dir` | pins the working directory the record implies, so a wrong-directory check is not misread as an integrity failure |
| 6–7 | `test_file_matches_freeze_record[md, json]` | recorded hashes verify |
| 8–9 | `test_file_matches_independently_pinned_digest[md, json]` | digests also match values pinned separately in the test file, so rewriting the constitution *and* its freeze record together would still be caught |
| 10 | `test_constitution_json_is_valid_and_identifies_itself` | machine-readable validation passes |
| 11 | `test_gate_ids_are_complete_and_unique` | gates 0–9 present exactly once each |
| 12 | `test_every_gate_declares_a_failure_or_default_result` | no gate can be silently passed for lack of a failure token |
| 13 | `test_scope_rules_agree` | long-only, cash account, 1 position, 95% exposure, fractional, USD 100 |
| 14 | `test_prohibited_product_list_agrees` | all 10 prohibited products present in both documents |
| 15 | `test_risk_thresholds_agree` | 15% research / 8% soft / 10% hard |
| 16 | `test_time_partition_agrees` | 24-month holdout, 36-month validation, 5-year minimum development, computed before results |
| 17 | `test_cost_policy_agrees` | spread, slippage, fees required; 2× stressed multiplier |
| 18 | `test_gate3_development_thresholds_agree` | MDD ≤15%, PF ≥1.10, ≥30 trades, best-trade-removal |
| 19 | `test_gate4_validation_thresholds_agree` | Sharpe ≥0.50, PF ≥1.15, ≥70% positive folds |
| 20 | `test_gate5_holdout_thresholds_agree` | MDD ≤12%, PF ≥1.15, ≥20 trades, `INSUFFICIENT_HOLDOUT_EVIDENCE` outcome preserved |
| 21 | `test_gate7_paper_thresholds_agree` | 90/180 calendar days, 30 closed trades, MDD ≤10% |
| 22 | `test_gate8_shadow_thresholds_agree` | 60 days or 20 round trips, whichever is longer |
| 23 | `test_live_trading_default_is_locked` | Gate 9 default `LIVE_TRADING_LOCKED`, manual approval required |
| 24 | `test_no_live_authorization_artifact_exists` | no live-authorization artifact exists on disk |
| 25 | `test_constitution_declares_stage0_pass` | declared Stage 0 verdict matches in both documents |
| 26 | `test_next_authorized_activity_is_stage1` | next authorized activity is Stage 1 |
| 27 | `test_no_secret_material_in_governance_or_source` | no credential-shaped material in tracked text files |

## Not covered by tests, and why

- **That the freeze predates any strategy result.** Not provable from the filesystem. Accepted as
  declared in `SE100-GOV-0001` §9 and recorded as a limitation, not as a verified fact.
- **JSON Schema validation against the declared `$schema` URL.** The URL was not fetched; adding a
  network dependency to governance verification would make integrity checking fail when offline.
  Structural assertions are used instead.
- **Data, engine, strategy, execution, and broker behaviour.** No such code exists yet. Stage 1
  onward will add unit, integration, adversarial, and regression suites.

## Standing rule

These 27 tests are a permanent regression floor for Generation 1. If a later stage finds any of
them failing, that stage stops: it is evidence that a frozen artifact changed. They may be added to
but not weakened or deleted.
