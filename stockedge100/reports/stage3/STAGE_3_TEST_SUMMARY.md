# Stage 3 test summary

Command: `cd stockedge100 && python -m pytest tests -q`
Raw output: [pytest_stage3_output.txt](pytest_stage3_output.txt)

**389 passed, 0 failed, 0 skipped.**

## Composition

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
| `tests/unit/test_stage3_strategies.py` | 69 | The seal and its three pinned digests, the five sealed indicators against hand values, the thirty declared runs, each of the seven conditions in both directions, the combination rule, the six families on synthetic bars, the evidence file's self-digest, and the report's own constraints. |
| `tests/adversarial/test_stage3_defects.py` | 47 | Defects injected one at a time — a tampered seal, a drifted threshold, a loosened predicate, a missing run, a look-ahead read — each caught, behind three clean controls. |
| **Total** | **389** | |

Stage 0 contributed 27, Stage 1 brought the total to 140, Stage 2 to 273. Stage 3 adds **116**.
Nothing was weakened, skipped, `xfail`ed, or removed; the floor only rises.

`tests/conftest.py` was not touched. Every Stage 3 fixture is defined locally in the file that uses
it. No test writes into `data/`, `governance/`, `config/`, or `reports/` — the tests that need a
different file layout build one under `tmp_path` and redirect the loader's `PROJECT_ROOT` onto it
with `monkeypatch`.

## The unit file

**The seal.** The three sealed digests are pinned as literals in the test file, written out
independently of `STAGE_3_PREREGISTRATION.sha256`, so that rewriting an artifact *and* its freeze
record together still fails the suite. `PREREGISTERED_FILES` is three, not five: the seal record and
its `.sha256` companion are covered by the surrounding checksum record, because nothing hashes
itself. The tests also assert what the seal claims about its own ordering —
`sealed_before_any_strategy_code`, and the two counts (`strategy_modules_present_at_seal_time`,
`strategy_output_files_present_at_seal_time`) that make the claim falsifiable rather than
self-reported.

**The five sealed indicators.** SMA, Wilder RSI, rolling close high and low, and total-return
momentum, each asserted against values worked out from the protocol's own textual definition rather
than from the implementation — including the boundaries those definitions turn on: that the rolling
extremes include the bar at `t`, that momentum reads `adj_close` and not `close`, that it needs
`n+1` bars rather than `n`, and that Wilder RSI is undefined without the full seeding distance.
Everything is exact `Decimal` under the pinned 34-digit context, and `test_dec_refuses_a_float`
asserts no `float` can enter the signal path at all.

**The thirty declared runs.** That `variant_specs` enumerates exactly 30 from the sealed file, that
the first variant of each candidate is its primary, that each candidate declares exactly four
neighbours, and that warm-up is the largest lookback used by the primary **or any neighbour** — the
last of these is what stops a neighbour being advantaged by a different run start.

**The seven conditions, in both directions.** Every condition is asserted to be `MET` on evidence
that satisfies it and `NOT_MET` on evidence that does not, because a predicate that always returns
`NOT_MET` would pass a one-sided test on this stage's data. S3-C5 is tested on both sealed removals —
largest equity multiple and largest absolute P&L — including the case where they select different
trades, which no candidate in this stage exhibited. S3-C3 asserts the *sealed* treatment of an
undefined profit factor with positive gross profit: `MET`, with the note prefix
`UNDEFINED_NO_LOSSES_TREATED_AS_MET:`. Asserting the treatment that reads better rather than the one
that was sealed is how the first draft of that test was wrong.

**Combination.** That a single `NOT_MET` rejects the whole candidate, that `NOT_EVALUABLE` is never a
pass, that `NOT_APPLICABLE_BY_CONDITION_TEXT` is satisfied without being met, and that the stage
verdict is the disjunction over candidates with the two tokens taken from the sealed
`verdict_token_derivation` rather than from a literal in the code.

**The six families on synthetic bars.** Each family is driven over hand-built series where the
intended trade sequence is known by construction, so the entry, exit, and sizing rules are checked
against the sealed text rather than against whatever the real data happened to produce.

**The evidence file.** Its digest recomputes from the written file following its own
`evidence_digest_covers` sentence literally; re-stamping it at a different `generated_utc` does not
move the digest; tampering with any non-excluded field does.

**The report.** That it names its document id and verdict token, and that it carries no 64-hex string
outside the four it is allowed to quote. The predicate tests for the **value**, not the field name:
Stage 1 checked the field name and would have passed a report that carried the digest.

## The adversarial file

Three clean controls sit at the top — the sealed configuration loads and recomputes all three
digests, a synthetic candidate meeting every threshold is admitted with the stage verdict `PASS`, and
all thirty sealed variants build. A failing stage needs those more than a passing one would: without
them, 47 rejections are equally consistent with an evaluator that rejects everything. A fourth
control guards the evidence file, and each defect below is injected one at a time.

| Injected | Caught by |
| --- | --- |
| a byte changed in a sealed parameter file; a byte changed in the sealed prose | `ConfigViolation` naming the file that moved |
| a sealed file deleted | drift, not a silent skip |
| a parameter file that is not in the seal at all; the seal itself missing | refusal to load, refusal to run |
| `require_seal=False` passed anywhere in `src/` | a scan of the source tree; its only permitted occurrence is its own definition |
| each of the five sealed thresholds moved | `check_thresholds_against_seal`, asserted through the full evaluation rather than against the checker alone |
| the concentration predicate loosened; the lower-frequency exception switched on | refusal to evaluate |
| a condition deleted from the criteria; a fifth verdict value constructed | refusal — there is no fifth value and no borderline value |
| one condition forced to fail on an otherwise-clean candidate | the whole candidate rejected |
| a candidate that never traded; a candidate with no losing trade | refused, and met-by-the-seal, respectively — not excused |
| a neighbour that did not run; a neighbour count other than four; a thirty-first run | refusal, and the sealed run-count check |
| a window other than development handed to the harness | `ConfigViolation` |
| a view built outside its window; a session inside the bound but outside the window; a read past the visibility bound; the bound itself reassigned | `WindowViolation`, `LookAheadError`, and an immutable bound |
| a warm-up that disagrees with the seal; a warm-up read from the primary only | the plan stops |
| a symbol whose series was not loaded; a universe with too little history; an empty universe; an excluded symbol pulled back in | run-start refusal |
| an experiment with no implementation; `top_n` above the one open risky position; an unsupported rebalance rule | `ConfigViolation` |
| a tampered evidence field; the evidence re-stamped | the digest moves, and does not move, respectively |

## What the suite deliberately does not cover

The decision package. `tests/**/*.py` is one of the patterns the repository-state digest is computed
over, so a test asserting that digest would invalidate the value it asserts the moment it was
written. The package is verified by re-running the recomputation, not by a test.
