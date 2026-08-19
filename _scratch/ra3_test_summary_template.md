# Stage 3 (Generation 2, Attempt 3) test summary

Command: `cd stockedge100 && PYTHONIOENCODING=utf-8 python -m pytest tests -q`
The environment variable is not decoration. Two of pytest's own output lines carry U+2014,
which the console's cp1252 default encodes as byte `0x97`; the decision-package builder reads
this capture with `encoding="utf-8"` and would fail to decode it. Omitting the variable does
not raise at capture time, it raises at build time.
Raw output: [pytest_stage3_g2_attempt3_output.txt](pytest_stage3_g2_attempt3_output.txt)

**@@PASSED@@ passed, @@FAILED@@ failed, 0 skipped.**

The one failure is deliberate, pre-existing and inherited. It is not an Attempt 3 regression, it is
not weakened here, and it is not skipped.

## The failing test

```
FAILED @@FAILING@@
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

@@TABLE_COMPOSITION@@

Attempt 2 left the floor at **@@PRIOR@@** tests. Attempt 3 adds **@@NEW@@**, in @@NEW_FILE_COUNT@@ new
files, for a total of **@@TOTAL@@**. The new files are:

```
@@NEW_FILES_BLOCK@@
```

Every other file in the table is byte-identical to the state Attempt 2 left it in. That is re-hashed,
not asserted: Attempt 2's `STAGE_3_G2_A2_ARTIFACT_MANIFEST.json` recorded a SHA-256 for each of the
**@@PRIOR_FILES_VERIFIED@@** paths under `tests/` that existed when its package was built, every one
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
@@AT_COUNT_WORD@@ required adversarial tests in its own words, sealed before any of this code existed.
Its own note on why: "Declared here before the tests exist, so that the test suite is written against
a specification rather than against the implementation's behaviour. Each item is a required test, not
a suggestion." Each is quoted below with the number of tests that implement it and the file they are
in, counted from the collected ids rather than asserted:

@@LIST_AT@@

That accounts for @@AT_ATTRIBUTED@@ of the @@NEW@@ tests. The remaining @@HARNESS@@ are the controls
and the non-vacuity gates, named here from the collected ids:

@@LIST_CONTROLS@@

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
