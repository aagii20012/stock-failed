# Stage 3 (Generation 2, Attempt 3) test summary

Command: `cd stockedge100 && PYTHONIOENCODING=utf-8 python -m pytest tests -q`
The environment variable is not decoration. Two of pytest's own output lines carry U+2014,
which the console's cp1252 default encodes as byte `0x97`; the decision-package builder reads
this capture with `encoding="utf-8"` and would fail to decode it. Omitting the variable does
not raise at capture time, it raises at build time.
Raw output: [pytest_stage3_g2_attempt3_output.txt](pytest_stage3_g2_attempt3_output.txt)

**1264 passed, 1 failed, 0 skipped.**

The one failure is deliberate, pre-existing and inherited. It is not an Attempt 3 regression, it is
not weakened here, and it is not skipped.

## The failing test

```
FAILED tests/unit/test_stage4_preregistration.py::test_no_stage_4_module_can_reach_restricted_data_or_a_broker
```

This is Generation 1's permanent red marker, recorded as `S4-CONFLICT-7` in the Stage 4
pre-registration package and inherited unchanged through Generation 2 Attempt 1 and Attempt 2 before
it reached Attempt 3. `src/stockedge100/strategies/stage4_evaluation.py` imports `load_dataset` and
the calendar module — which it must, because a validation stage has to read data — and the test
asserts that no Stage 4 module reaches restricted data at all. The two statements cannot both hold,
and the conflict was recorded rather than resolved by loosening the assertion.

Attempt 3 touches neither side of it. Editing the test would be weakening a test to make a gate look
cleaner, which the constitution forbids and this attempt does not need: the failure has nothing to do
with the Attempt 3 verdict, which is reached from the development evidence file and the sealed gate
criteria alone. It is also not this attempt's to repair — `tests/unit/test_stage4_preregistration.py`
and `src/stockedge100/strategies/stage4_evaluation.py` are both Generation 1 artifacts, closed and
read-only.

## Composition

| File | Tests | What it establishes |
| --- | ---: | --- |
| `tests/adversarial/test_g2_engine_multiposition.py` | 59 | Generation 2 Attempt 1 floor. **Unmodified.** |
| `tests/adversarial/test_g2_ra1_risk_architecture.py` | 51 | Generation 2 Attempt 2 floor. **Unmodified.** |
| `tests/adversarial/test_g2_ra3_risk_architecture.py` | 85 | **New.** RA3's five risk components and the sealed requirements `AT-A` ... `AT-H`, `AT-L` and `AT-M`, each section opening with a control and closing with an injected defect that must be caught. |
| `tests/adversarial/test_g2_sel2_selection_rule.py` | 38 | **New.** `SE100-G2-SEL-2`'s return-blindness, edge-correct neighbour identification and determinism — the sealed requirements `AT-I`, `AT-J` and `AT-K`. |
| `tests/adversarial/test_g2_selection_return_blind.py` | 97 | Generation 2 Attempt 1 floor. **Unmodified.** |
| `tests/adversarial/test_stage1_adversarial.py` | 29 | Generation 1 floor. **Unmodified.** |
| `tests/adversarial/test_stage2_defects.py` | 42 | Generation 1 floor. **Unmodified.** |
| `tests/adversarial/test_stage3_attempt2_defects.py` | 30 | Generation 1 floor. **Unmodified.** |
| `tests/adversarial/test_stage3_defects.py` | 47 | Generation 1 floor. **Unmodified.** |
| `tests/integration/test_stage1_data_foundation.py` | 33 | Generation 1 floor. **Unmodified.** |
| `tests/integration/test_stage2_backtest.py` | 37 | Generation 1 floor. **Unmodified.** |
| `tests/integration/test_stage3_attempt2_backtest.py` | 19 | Generation 1 floor. **Unmodified.** |
| `tests/unit/test_g2_cost_derivation.py` | 50 | Generation 2 Attempt 1 floor. **Unmodified.** |
| `tests/unit/test_g2_window_guard.py` | 48 | Generation 2 Attempt 1 floor. **Unmodified.** |
| `tests/unit/test_stage0_governance.py` | 27 | Generation 1 floor. **Unmodified.** |
| `tests/unit/test_stage1_calendar_partition.py` | 34 | Generation 1 floor. **Unmodified.** |
| `tests/unit/test_stage1_preregistration.py` | 17 | Generation 1 floor. **Unmodified.** |
| `tests/unit/test_stage2_engine.py` | 54 | Generation 1 floor. **Unmodified.** |
| `tests/unit/test_stage3_attempt2_implementation.py` | 51 | Generation 1 floor. **Unmodified.** |
| `tests/unit/test_stage3_attempt2_preregistration.py` | 71 | Generation 1 floor. **Unmodified.** |
| `tests/unit/test_stage3_strategies.py` | 69 | Generation 1 floor. **Unmodified.** |
| `tests/unit/test_stage4_evaluation.py` | 92 | Generation 1 floor. **Unmodified.** |
| `tests/unit/test_stage4_evidence.py` | 37 | Generation 1 floor. **Unmodified.** |
| `tests/unit/test_stage4_preregistration.py` | 148 | Generation 1 floor. **Unmodified**, including the one red marker. |
| **Total** | **1265** | 1264 passed, 1 failed by design |

Attempt 2 left the floor at **1142** tests. Attempt 3 adds **123**, in two new
files, for a total of **1265**. The new files are:

```
tests/adversarial/test_g2_ra3_risk_architecture.py    85
tests/adversarial/test_g2_sel2_selection_rule.py      38
```

Every other file in the table is byte-identical to the state Attempt 2 left it in. That is re-hashed,
not asserted: Attempt 2's `STAGE_3_G2_A2_ARTIFACT_MANIFEST.json` recorded a SHA-256 for each of the
**23** paths under `tests/` that existed when its package was built, every one
of them recomputes to its recorded digest now, and the two new files above appear in that manifest not
at all. That set includes `tests/conftest.py`, so "the shared fixtures are untouched" is a recomputed
digest here rather than a claim — Attempt 3's fixtures are defined locally in its own two modules. No
test was edited, renamed, weakened, deleted or skipped; the red marker above is carried forward rather
than silenced.

The floor is a one-way ratchet by constitution: later work adds to it and never subtracts. The
composition table above is generated from a real `pytest --collect-only -q` run grouped by file, not
transcribed, so a row cannot drift away from the suite it claims to describe.

## What the new files establish

`config/generation_2/g2_rotation_ra3_protocol.json` (`SE100-CFG-3105`) declares
thirteen required adversarial tests in its own words, sealed before any of this code existed.
Its own note on why: "Declared here before the tests exist, so that the test suite is written against
a specification rather than against the implementation's behaviour. Each item is a required test, not
a suggestion." Each is quoted below with the number of tests that implement it and the file they are
in, counted from the collected ids rather than asserted:

- **`AT-A`** — 11 tests in `test_g2_ra3_risk_architecture.py`. Sealed requirement: Aggregate exposure never exceeds 50% of equity at any session, including mid-rebalance, verified after every fill and not only at session close.
- **`AT-B`** — 6 tests in `test_g2_ra3_risk_architecture.py`. Sealed requirement: Volatility scaling reduces position size when trailing realized portfolio volatility exceeds 10% annualized, verified against a hand-constructed high-volatility equity fixture with an independently computed expected scalar.
- **`AT-C`** — 5 tests in `test_g2_ra3_risk_architecture.py`. Sealed requirement: A position breaching the 8% stop is exited at the NEXT session's open, not at the same close, and the exit is a full sell.
- **`AT-D`** — 9 tests in `test_g2_ra3_risk_architecture.py`. Sealed requirement: The de-risk ladder steps down at the declared RA3 thresholds and back up only after the declared recovery condition, verified against a hand-constructed drawdown-and-recovery fixture that visits every band in both directions. The fixture must include a drawdown that reaches 6 percent and assert that the combined ladder scalar is exactly 1 there, which is the single behavioural difference from RA2 and would otherwise be tested only by absence.
- **`AT-E`** — 4 tests in `test_g2_ra3_risk_architecture.py`. Sealed requirement: The re-entry lockout genuinely blocks a return to a higher sizing band before its cooldown elapses, verified by a fixture in which recovery is available and blocked for exactly the declared number of sessions.
- **`AT-F`** — 7 tests in `test_g2_ra3_risk_architecture.py`. Sealed requirement: Determinism: identical inputs produce identical trade, equity, ranking and risk-state digests on a clean rerun.
- **`AT-G`** — 7 tests in `test_g2_ra3_risk_architecture.py`. Sealed requirement: The Generation 2 window guard still blocks any read at or after 2021-08-01, exercised through the Attempt 3 loading path. The guard is reused, not reimplemented, and the test asserts that the module under test is the existing g2_window_guard.
- **`AT-H`** — 10 tests in `test_g2_ra3_risk_architecture.py`. Sealed requirement: No Generation 1, Attempt 1 or Attempt 2 module is modified: every one of the seventeen modules listed in prior_attempt_modules_immutable re-hashes to its recorded digest.
- **`AT-I`** — 12 tests in `test_g2_sel2_selection_rule.py`. Sealed requirement: The selection input cannot carry a performance figure: the SelectionInputV2 field tuple equals SELECTION_V2_FIELD_NAMES and the import-time assertion fires when it does not. The test also asserts that no field name matches a performance vocabulary (return, pnl, profit, drawdown, sharpe, equity, ratio, factor), so a future field named plausibly rather than obviously is also caught.
- **`AT-J`** — 9 tests in `test_g2_sel2_selection_rule.py`. Sealed requirement: Neighbour identification is correct at the grid edges: the neighbour counts are 3, 4 and 5, the partition over the eighteen variants is 8 / 8 / 2, and at least one variant of each class has its full neighbour set written out as a literal in the test and compared element by element against the computed set. The relation is also asserted symmetric, and asserted to contain no variant outside the grid and never the variant itself.
- **`AT-K`** — 12 tests in `test_g2_sel2_selection_rule.py`. Sealed requirement: SE100-G2-SEL-2 is deterministic: identical recorded statistics produce identical scores, identical component breakdowns and an identical selected variant across two independent computations in the same process and one from a round-trip through the serialised selection inputs.
- **`AT-L`** — 13 tests in `test_g2_ra3_risk_architecture.py`. Sealed requirement: The RA3 band table is the sealed one and contains no band boundary below 0.08: the loaded architecture has exactly three bands, its scalars are strictly decreasing in (0, 1], its first band starts at 0.00 with scalar 1.00, its last band is open-ended, and the absolute aggregate ceilings it induces equal 0.500000000 / 0.250000000 / 0.125000000.
- **`AT-M`** — 7 tests in `test_g2_ra3_risk_architecture.py`. Sealed requirement: The RA3 engine re-derives exactly the risk-dependent attributes it must after calling super().__init__, verified by parsing the Attempt 2 engine's __init__ for the attributes assigned from self.risk and asserting the RA3 subclass reassigns precisely that set. This is the same AST mechanism Attempt 2 used against Attempt 1's __init__.

That accounts for 112 of the 123 tests. The remaining 11 are the controls
and the non-vacuity gates, named here from the collected ids:

`test_g2_ra3_risk_architecture.py`:

- `test_control_opens_and_closes_are_disjoint_by_construction`
- `test_control_the_growth_fixture_never_engages_the_ladder`
- `test_control_the_loaded_architecture_is_ra3_and_not_ra2`
- `test_control_the_replay_reconciles_with_the_engine_it_audits`
- `test_gate_ra3_the_pointer_sets_it_compares_are_non_empty`
- `test_gate_ra3_the_prose_alias_table_is_load_bearing_in_both_directions`

`test_g2_sel2_selection_rule.py`:

- `test_control_a_clean_grid_selects_a_variant_from_that_grid`
- `test_control_the_both_zero_ambiguity_is_reported_rather_than_repaired`
- `test_control_the_dissimilarity_is_the_sealed_expression`
- `test_control_the_grid_sel_2_scores_over_is_the_declared_eighteen`
- `test_control_the_module_agrees_with_the_sealed_rule`

The sealed requirement list has one further item, `regression_floor` — "The existing suite is a
permanent regression floor. No test is weakened, skipped or deleted to make this attempt pass." That
one is a property of the session rather than a test, and its evidence is the re-hash above and the
composition table, not an assertion inside the suite.

Six properties of the two files are worth stating explicitly, because they are what make the group
something other than a restatement of the implementation:

- **Every section opens with a control and closes with an injected defect.** The control establishes
  that the assertion is not vacuous on the fixture; the injection mutates the sealed architecture —
  a loosened ceiling, a disabled stop, a flattened ladder, a zero cooldown, a reordered field tuple,
  a changed byte — and requires the test to go red. A check that cannot fail proves nothing, and the
  injections are placed where the code could actually go wrong rather than where they are easiest to
  reach.
- **The exposure assertions replay the fill stream rather than reading the engine's own summary.**
  Asking `clamp_summary()` whether the clamp worked is asking the defendant for a verdict. The replay
  reconstructs cash and quantities from the ordered fill records alone and recomputes the pre-fill
  equity each buy was sized against, sharing no line of code with `_execute_buy`.
- **`AT-D` tests this attempt's one architectural change by presence rather than by absence.** RA3
  differs from RA2 in exactly one way: the 5–8% de-risk rung is gone, so a book 6% below its peak is
  sized at full scale instead of 75%. A ladder test that only walked the surviving bands would pass
  identically against RA2, so the sealed requirement demands a fixture that reaches 6% and asserts
  the combined ladder scalar is *exactly* 1 there. That is the whole difference, asserted directly.
- **`AT-L` pins the band table's shape, not only its numbers.** Three bands, scalars strictly
  decreasing inside (0, 1], the first starting at 0.00 with scalar 1.00, the last open-ended, and no
  boundary anywhere below 0.08 — which is the structural form of "the rung RA2 added is not back".
- **`AT-M` asks its question by parsing the superclass.** RA3's engine subclasses Attempt 2's and
  overrides the band table, so any attribute Attempt 2's `__init__` derived from `self.risk` must be
  re-derived after `super().__init__` or it silently keeps RA2's value. The test parses that
  `__init__` for the attributes assigned from `self.risk` and asserts the subclass reassigns
  precisely that set — the same AST mechanism Attempt 2 used against Attempt 1's engine, pointed at
  Attempt 2's.
- **`AT-J` writes its neighbour sets out as literals.** The grid's neighbour counts are 3, 4 and 5
  over an 8 / 8 / 2 partition of the eighteen variants, and at least one variant of each class has
  its full neighbour set typed into the test and compared element by element against the computed
  one. The relation is separately asserted symmetric, closed inside the grid, and never reflexive.

Two things the selection-rule file is deliberately open about, because both are the kind of gap that
is cheaper to declare than to defend later:

- **Its fixtures are invented, and that is the point.** `SE100-G2-SEL-2` consumes four integer
  counters per variant and nothing else, so a fixture is eighteen six-field records — no price
  series, no engine, no market observation. Three shapes recur: a `gradient` where no two
  neighbourhoods agree, a `checkerboard` where every neighbour is one single-axis step away and
  therefore always the opposite parity, so every variant scores identically — the cleanest available
  proof that the score is a property of the neighbourhood rather than of the variant — and a `flat`
  grid where every score is zero and the decision falls through to the lexicographic tiebreak.
- **Step 3 of the rule is unreachable by fixture, and is tested as a mechanism instead.** The sealed
  order is shutdown screen, then instability score, then lowest turnover, then lexicographic.
  Turnover is `fill_count`, which is also one of the four scored quantities, so any fixture that
  separates two variants on turnover has already separated them on score. Rather than manufacture a
  state the rule cannot enter, the test asserts the ordering key itself — `(score, fill_count,
  variant_id)` — which is what steps 2, 3 and 4 are implemented as.

The risk-architecture fixtures are synthetic symbols on real XNYS sessions in 2010–2011 — inside
Generation 2's development window by a decade. Every open is its close minus a fixed discount, so the
set of opens and the set of closes are provably disjoint and "no fill happened at the close that
generated the signal" becomes a set-membership question rather than an argument. Nothing in either
file reads `data/` except the `AT-G` tests, which exercise the window guard through the real loading
path on purpose: asserting that a read is refused requires attempting one.

## What the suite deliberately does not cover

**The decision package.** `tests/**/*.py` is itself a `repo_state_id` pattern, so a test that
asserted the package's `repo_state_id` would invalidate the digest it asserts the moment it was
added. The package is verified by rerunning the recomputation from `_scratch/`, outside the governed
tree, not by a test inside it.

**The Attempt 3 result itself.** No test asserts a return, a drawdown, a profit factor, a stability
score or a verdict. Those are measurements, and a test that pinned them would convert a research
finding into a requirement — which is how a suite starts defending a number instead of a mechanism.
What the suite pins is the machinery that produced the measurements: the exposure ceiling, the
volatility scalar, the stop's fill timing, RA3's three bands, the lockout's cooldown, determinism of
both the engine and the selector, the window bound, the immutability of every prior-attempt module,
and the return-blindness of the selection input.

**Whether RA3 or SEL-2 is the better choice.** The suite establishes that each is implemented as
sealed. It cannot establish that removing the rung was right or that neighbourhood stability is a
better representative rule than turnover, and no test here pretends to: those are the questions the
gate answers, on evidence, once.

**Generation 2's holdout.** There is no test that reads it, because reading it is what the test would
have to do. `AT-G` asserts the opposite property — that the loading path refuses any read at or after
the development bound, and that the holdout window is declared prohibited — which is the only form
of assurance available that does not itself commit the violation.
