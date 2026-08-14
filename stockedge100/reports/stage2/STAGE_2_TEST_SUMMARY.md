# Stage 2 test summary

Command: `cd stockedge100 && python -m pytest tests -q`
Raw output: [pytest_stage2_output.txt](pytest_stage2_output.txt)

**273 passed, 0 failed, 0 skipped.**

## Composition

| File | Tests | What it establishes |
| --- | ---: | --- |
| `tests/unit/test_stage0_governance.py` | 27 | Stage 0 regression floor. **Unmodified.** |
| `tests/unit/test_stage1_calendar_partition.py` | 34 | Stage 1 floor. **Unmodified.** |
| `tests/unit/test_stage1_preregistration.py` | 17 | Stage 1 floor. **Unmodified.** |
| `tests/integration/test_stage1_data_foundation.py` | 33 | Stage 1 floor. **Unmodified.** |
| `tests/adversarial/test_stage1_adversarial.py` | 29 | Stage 1 floor. **Unmodified.** |
| `tests/unit/test_stage2_engine.py` | 54 | The parts: the sealed config loader, exact-decimal cost arithmetic and adverse rounding, the portfolio ledger, the order book and its fill-timing rule, the market view's visibility bound, the window guard, bar parsing, the metric formulae against hand values, and the evidence file's self-digest. |
| `tests/adversarial/test_stage2_defects.py` | 42 | Each of the twelve declared defect classes injected one at a time, and caught. |
| `tests/integration/test_stage2_backtest.py` | 37 | The whole engine, and the four Gate 2 conditions asserted both directly and through the harness the report quotes. |
| **Total** | **273** | |

Stage 0 contributed 27 and Stage 1 brought the total to 140. Stage 2 adds 133. Nothing was weakened,
skipped, `xfail`ed, or removed; the floor only rises.

The last three of the 54 unit tests were added after the first evidence build, in response to a
defect found by post-build verification rather than by the suite: the writer appended the field
describing what the digest covers *after* taking the digest, so the file asserted a coverage it did
not have, and a reader recomputing the digest exactly as documented got a different value. The fix
seals the description before hashing; the tests recompute the digest from the sealed body, vary only
the timestamp and require the digest not to move, then tamper with every non-excluded field in turn
and require that it does. They run on a synthetic body and never touch `reports/`.

`tests/conftest.py` was not touched. Every Stage 2 fixture is defined locally in the file that uses
it. No test writes into `data/`, `governance/`, `config/`, or `reports/`; the two tests that need a
different file layout redirect `harness.PROJECT_ROOT` onto `tmp_path` with `monkeypatch`.

## The twelve defect classes

`config/stage2_engine_spec.json` was sealed before any engine code existed. It declares twelve defect
classes, each with the mutation that introduces it and the detector that must catch it. The standard
it sets is deliberately two-sided: a class counts as covered only if the **clean** engine passes and
the **mutated** engine is caught. Three clean controls sit at the top of the adversarial file — the
clean fixture run, a correctly applied split, a correctly applied dividend — so a failure below them
is attributable to the injected defect rather than to the harness.

| Class | Injected | Caught by |
| --- | --- | --- |
| `LOOK_AHEAD` | a probe reads the bar at or after the session following its decision | `LookAheadError` from the market view, whose bound cannot be widened by the caller |
| `SAME_CLOSE_FILL` | an order fills at its own decision close | `FillTimingError` at construction, and again at execution |
| `SPLIT` | share count multiplied by the recorded ratio on the split session | the value-continuity check across every corporate-action session; `CorporateActionError` |
| `DIVIDEND` | credited a session late; credited twice; credited at the wrong amount | the per-event cash assertion, and the benchmark reconciliation |
| `DELISTING` | a position carried past its symbol's final bar | forced liquidation at the last available close; `DelistingError` if one survives |
| `STALE_PRICE` | a bar removed while the exchange calendar still reports a session | `STALE_PRICE` rejection, a flagged equity point, and `DataIntegrityHalt` past the sealed run limit |
| `CASH` | an order larger than the balance; a debit that never reaches the ledger | cash conservation reconciled after every single movement |
| `ROUNDING` | quantity rounded up; buy notional rounded down | the adverse-rounding invariant, plus the `MIN_NOTIONAL` rejection |
| `FEE` | every fee zeroed; sell-side fees charged on a buy | per-component fixture equality, and the strictly-positive-cost invariant |
| `SLIPPAGE` | a buy filled below its reference, a sell above | the adverse-price invariant, asserted at the fill and not only inside the price function |
| `REJECTED_ORDER` | a rejected order's cash and position effect applied anyway | cash, position, and equity asserted byte-identical to the pre-order state |
| `DUPLICATE_ORDER` | the same order submitted twice in one session | `DuplicateOrderError` on a repeated id and on a second live order in one symbol |

Two mutations are worth singling out because they are the ones a careless guard would miss.
`test_split_a_series_that_is_not_actually_split_adjusted_is_caught` is the mutation that matters for
this dataset specifically: Stage 1 established the provider returns split-adjusted OHLC, so a split
must **not** change the share count, and the guard has to fire on a series where it does.
`test_slippage_a_replaced_price_function_is_still_caught_at_the_fill` exists because a guard living
in the same function as the code it guards is removed by the same mutation that introduces the
defect — the assertion is deliberately placed at the fill, downstream of the price function it
checks.

## The four Gate 2 conditions

Constitution §9, gate 2. Each condition is asserted twice: directly against the engine, and against
`backtest/harness.py`, which is what [STAGE_2_ENGINE_VALIDATION.json](STAGE_2_ENGINE_VALIDATION.json)
and the stage report quote. The second form matters because a summary boolean that was true only
because the harness never compared anything would be worse than no evidence at all — so every
harness assertion reaches past the flag to the digests, counts, and differences underneath it.

**Deterministic reruns.** `test_a_rerun_of_the_fixture_produces_identical_trades_and_equity` and
`test_the_harness_determinism_evidence_compares_real_digests`. The digests are SHA-256 over canonical
JSON of the trade and equity payloads and carry no run id, no label, and no timestamp — checked by
`test_the_digest_carries_no_run_identity`, without which two runs could never compare equal for an
uninteresting reason. `test_the_digest_discriminates_between_runs_that_really_differ` supplies the
other half: base and stressed costs must **not** produce the same digest, or the equality above would
be unfalsifiable. Symbol insertion order is also asserted not to matter.

**Look-ahead.** Structural, then empirical. Structurally the market view is constructed with a hard
visibility bound and refuses a later session. Empirically,
`test_deleting_every_bar_after_the_run_end_changes_nothing` deletes every bar past the run end and
requires both digests to be unchanged; `test_the_harness_truncation_check_actually_removed_bars`
asserts the harness's own truncation actually removed bars, since a truncation that deleted nothing
would pass against an engine that peeks.

**Hand-calculated fixtures.** FIXT is a synthetic eight-session instrument whose entry, mark,
dividend, exit, fee components, and final equity were written into the sealed spec — with their
derivations — before the engine existed. Both cost scenarios are compared line by line, nineteen to
twenty values each, not just on the final equity, which two compensating errors would satisfy.

**Benchmark reconciliation.** SPY total return computed two ways that are an arithmetic identity
under the adjustment convention Stage 1 measured: the adjusted-close ratio, and explicit share
accumulation that never consults an adjusted close. Over the development window they agree to a
relative difference of 2.2e-7 against a sealed tolerance of 1e-6, across 115 dividends.
`test_the_identity_holds_on_a_sub_window_as_well_as_the_whole_series` checks two shorter windows,
because the post-window adjustment factors cancel in the ratio and so the identity must hold there
too; that test states the sealed 1e-6 on the growth factors rather than on the returns, and says why
in its docstring — over five years the return is 0.0246, so dividing by it measures how short the
window is rather than whether the engine reconciles.

## What the suite deliberately does not cover

The decision package. `tests/**/*.py` is one of the patterns `repo_state_id` is computed over, so a
test asserting the recorded `repo_state_id` would invalidate the value it asserts the moment it was
written. The package is verified by re-running the recomputation, not by a test.
