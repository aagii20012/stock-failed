"""Adversarial tests AT-I, AT-J and AT-K for ``SE100-G2-SEL-2``.

``SE100-CFG-3105.adversarial_test_requirements`` declares these three before the rule was run:

    AT-I  The selection input cannot carry a performance figure: the SelectionInputV2 field tuple
          equals SELECTION_V2_FIELD_NAMES and the import-time assertion fires when it does not. The
          test also asserts that no field name matches a performance vocabulary (return, pnl,
          profit, drawdown, sharpe, equity, ratio, factor), so a future field named plausibly rather
          than obviously is also caught.
    AT-J  Neighbour identification is correct at the grid edges: the neighbour counts are 3, 4 and
          5, the partition over the eighteen variants is 8 / 8 / 2, and at least one variant of each
          class has its full neighbour set written out as a literal in the test and compared element
          by element against the computed set. The relation is also asserted symmetric, and asserted
          to contain no variant outside the grid and never the variant itself.
    AT-K  SE100-G2-SEL-2 is deterministic: identical recorded statistics produce identical scores,
          identical component breakdowns and an identical selected variant across two independent
          computations in the same process and one from a round-trip through the serialised
          selection inputs.

**The fixtures are invented, and that is the point.** SEL-2 consumes four integer counters per
variant and nothing else, so a fixture is eighteen six-field records — no price series, no engine,
no market observation. Every score asserted below was measured from these exact records before the
assertion was typed (``_scratch/ra3_sel2_preflight.py``), because none of them exists anywhere on
disk to be looked up. Three shapes recur:

``gradient``
    counters that rise with the variant's declared index, so no two neighbourhoods agree and the
    score has to discriminate.
``checkerboard``
    two turnover levels assigned by the parity of the variant's position on the three axes. Every
    neighbour is one single-axis step away and therefore always the opposite parity, so *every*
    variant sees the same dissimilarity and every score is identical. It is the cleanest available
    proof that the score is a property of the neighbourhood rather than of the variant.
``flat``
    every counter identical, so every score is zero and the decision falls all the way through to
    the lexicographic tiebreak.

**On step 3.** The sealed step order is shutdown screen, then instability score, then lowest
turnover, then lexicographic. Steps 1, 2 and 4 are each reached by a fixture below. Step 3 is not,
and cannot be: turnover is ``fill_count``, which is also one of the four *scored* quantities, so any
fixture that separates two variants on turnover has already separated them on score. Rather than
manufacture an unreachable state, ``test_at_k_the_ranking_is_ordered_by_the_declared_step_sequence``
asserts the ordering key itself — ``(score, fill_count, variant_id)`` — which is the mechanism steps
2, 3 and 4 are implemented as.

Nothing here writes, and nothing here reads ``data/``.
"""

from __future__ import annotations

import dataclasses
import json
import sys
import types
from decimal import Decimal
from pathlib import Path

import pytest

from stockedge100.backtest.costs import BASE
from stockedge100.backtest.errors import ConfigViolation
from stockedge100.strategies import g2_rotation_ra3 as rot
from stockedge100.strategies import g2_runner_ra3 as runner
from stockedge100.strategies import g2_selection_v2 as sel

PREFIX = "SE100-G2-S3-C3-ROTATION-RA3-"

# Hand-written from the sealed AT-I text, not imported. The module's own list is longer and the
# runner's is shorter; the three are compared against each other in
# test_at_i_the_three_vocabularies_disagree_and_the_gap_is_recorded rather than reconciled.
SEALED_AT_I_VOCABULARY = (
    "return",
    "pnl",
    "profit",
    "drawdown",
    "sharpe",
    "equity",
    "ratio",
    "factor",
)

LOOKBACKS = (3, 6, 12)
TOP_KS = (1, 2, 3)
FREQUENCIES = ("MONTHLY", "QUARTERLY")


def variants():
    return rot.rotation_variants()


def ids():
    return [variant.variant_id for variant in variants()]


def gradient(*, shutdown_for=()):
    """Counters that rise with the declared variant index. Measured selection: L12-K3-MONTHLY."""
    return tuple(
        sel.SelectionInputV2(
            variant_id=variant.variant_id,
            shutdown_events=1 if variant.variant_id in shutdown_for else 0,
            fill_count=100 + index,
            ladder_descents=10 * index,
            lockout_arms=10 * index,
            stops_filled=index % 4,
        )
        for index, variant in enumerate(variants(), start=1)
    )


def _parity(variant):
    return (
        LOOKBACKS.index(variant.lookback_months)
        + TOP_KS.index(variant.top_k)
        + FREQUENCIES.index(variant.frequency)
    ) % 2


def checkerboard(low=100, high=120):
    """Turnover alternating by axis parity, every other counter constant."""
    return tuple(
        sel.SelectionInputV2(
            variant_id=variant.variant_id,
            shutdown_events=0,
            fill_count=low if _parity(variant) == 0 else high,
            ladder_descents=7,
            lockout_arms=7,
            stops_filled=2,
        )
        for variant in variants()
    )


def flat(value=100, *, counters=(7, 7, 2)):
    descents, arms, stops = counters
    return tuple(
        sel.SelectionInputV2(
            variant_id=variant.variant_id,
            shutdown_events=0,
            fill_count=value,
            ladder_descents=descents,
            lockout_arms=arms,
            stops_filled=stops,
        )
        for variant in variants()
    )


# ---------------------------------------------------------------------------------------------
# Clean controls. A guard that fires on everything is not a guard, so these run first.
# ---------------------------------------------------------------------------------------------


def test_control_the_grid_sel_2_scores_over_is_the_declared_eighteen():
    declared = ids()
    assert len(declared) == 18
    assert len(set(declared)) == 18
    assert all(variant_id.startswith(PREFIX) for variant_id in declared)


def test_control_the_module_agrees_with_the_sealed_rule():
    """``check_seal_agreement`` reads the sealed rule off disk; the module's constants are in code.

    Asserting they agree is the fourth structural guard the module's own docstring claims, exercised
    rather than trusted.
    """
    agreement = sel.check_seal_agreement()
    assert agreement["rule_id"] == sel.SELECTION_RULE_ID == "SE100-G2-SEL-2"
    assert tuple(agreement["field_names"]) == sel.SELECTION_V2_FIELD_NAMES
    assert tuple(agreement["quantities"]) == sel.QUANTITIES
    assert agreement["dissimilarity"] == "abs(a - b) / max(abs(a), abs(b), 1)"
    assert agreement["score_decimals"] == sel.SCORE_DECIMALS == 9


def test_control_a_clean_grid_selects_a_variant_from_that_grid():
    result = sel.select_representative_v2(gradient())
    assert result.selected in ids()
    assert len(result.eligible) == 18
    assert result.ineligible == () or list(result.ineligible) == []
    assert set(result.scores) == set(ids()), "every variant is scored, selectable or not"


def test_control_the_dissimilarity_is_the_sealed_expression():
    """Four hand-computed points, including both branches of the ``max(..., 1)`` floor.

    ``d(3, 7)`` is written to the module's own 34-digit context rather than rounded, so a change of
    working precision inside the module would show here and not only in a ninth decimal place.
    """
    assert sel.dissimilarity(3, 7) == Decimal("0.5714285714285714285714285714285714")
    assert sel.dissimilarity(0, 5) == Decimal(1)
    assert sel.dissimilarity(5, 5) == Decimal(0)
    assert sel.dissimilarity(0, 0) == Decimal(0), "the sealed floor, not repaired here"


def test_control_the_both_zero_ambiguity_is_reported_rather_than_repaired():
    """``G2A3-CONFLICT-32``. A variant whose counters are all zero scores a perfect 0.

    The formula is sealed and stays sealed. What the module adds is the count of neighbour pairs
    that were zero on both sides, so the reader can tell agreement from absence. The three-neighbour
    variant below must report three such pairs for each of the four quantities — a score of zero
    backed by nothing at all.
    """
    zeros = tuple(
        sel.SelectionInputV2(
            variant_id=variant.variant_id,
            shutdown_events=0,
            fill_count=0,
            ladder_descents=0,
            lockout_arms=0,
            stops_filled=0,
        )
        for variant in variants()
    )
    scored = sel.score_neighbourhood(zeros)
    corner = scored[PREFIX + "L03-K1-MONTHLY"]
    assert corner.score == Decimal(0)
    assert len(corner.neighbours) == 3
    assert corner.per_quantity_both_zero == {quantity: 3 for quantity in sel.QUANTITIES}

    # The contrast that makes the count informative: identical *non*-zero counters also score 0,
    # but report no both-zero pairs at all.
    identical = sel.score_neighbourhood(flat())
    assert identical[PREFIX + "L03-K1-MONTHLY"].score == Decimal(0)
    assert identical[PREFIX + "L03-K1-MONTHLY"].per_quantity_both_zero == {
        quantity: 0 for quantity in sel.QUANTITIES
    }


# ---------------------------------------------------------------------------------------------
# AT-I. The selection input cannot carry a performance figure.
# ---------------------------------------------------------------------------------------------


def test_at_i_the_field_tuple_is_the_sealed_one_in_order():
    actual = tuple(field.name for field in dataclasses.fields(sel.SelectionInputV2))
    assert actual == sel.SELECTION_V2_FIELD_NAMES
    assert actual == (
        "variant_id",
        "shutdown_events",
        "fill_count",
        "ladder_descents",
        "lockout_arms",
        "stops_filled",
    )
    assert tuple(sel.check_seal_agreement()["field_names"]) == actual


def test_at_i_no_field_name_matches_the_performance_vocabulary():
    """Against the sealed AT-I list *and* the module's own longer one.

    Both are checked because they are different claims: the sealed list is what the protocol
    promised a reader, and the module's list is what actually runs at import.
    """
    names = [field.name for field in dataclasses.fields(sel.SelectionInputV2)]
    for name in names:
        for word in SEALED_AT_I_VOCABULARY:
            assert word not in name.lower(), f"{name!r} names the performance term {word!r}"
        for word in sel.FORBIDDEN_FIELD_SUBSTRINGS:
            assert word not in name.lower(), f"{name!r} names the performance term {word!r}"


def test_at_i_the_three_vocabularies_disagree_and_the_gap_is_recorded():
    """``G2A3-CONFLICT-41``, disclosed rather than repaired.

    Three lists of banned substrings exist and no two are equal: the seal's AT-I text names eight
    words, ``g2_selection_v2.FORBIDDEN_FIELD_SUBSTRINGS`` enforces fourteen, and the runner's
    ``_assert_selection_surface`` enforces seven. In particular ``ratio`` and ``factor`` are named
    in the seal's prose and enforced by neither implementation, so a field called
    ``profit_factor_rank`` would be caught by ``profit`` and a field called ``information_ratio``
    would not be caught at all.

    Widening either implemented list to match the prose would edit a sealed artifact's behaviour to
    match a prompt, which is the one repair this project forbids. The test therefore asserts the
    disagreement exactly as it stands, so that it cannot drift unnoticed and cannot be mistaken for
    an oversight.
    """
    module_list = set(sel.FORBIDDEN_FIELD_SUBSTRINGS)
    runner_list = {"return", "drawdown", "profit", "sharpe", "equity", "pnl", "p_l"}
    sealed = set(SEALED_AT_I_VOCABULARY)

    assert len(sel.FORBIDDEN_FIELD_SUBSTRINGS) == 14
    assert len(runner_list) == 7
    assert len(sealed) == 8

    assert sealed - module_list == {"ratio", "factor"}
    assert sealed - runner_list == {"ratio", "factor"}
    assert runner_list - module_list == {"p_l"}, "the runner bans one form the module does not"
    assert module_list & sealed == {"return", "pnl", "profit", "drawdown", "sharpe", "equity"}

    # And the practical consequence, stated as an executable claim rather than as prose.
    assert not any(word in "information_ratio" for word in module_list | runner_list)
    assert any(word in "profit_factor_rank" for word in module_list)


def test_at_i_a_counter_that_is_not_a_plain_int_is_refused():
    """The third structural guard: the one that stops a return figure arriving positionally.

    Field names being clean is not enough if a ``Decimal`` return can be passed into ``fill_count``.
    ``bool`` is rejected too, because ``True`` is an ``int`` to ``isinstance`` and a bug to a reader.
    """
    common = dict(
        variant_id=PREFIX + "L03-K1-MONTHLY",
        shutdown_events=0,
        ladder_descents=0,
        lockout_arms=0,
        stops_filled=0,
    )
    for bad in (Decimal("0.0042"), 0.0042, True, "12"):
        with pytest.raises(ConfigViolation):
            sel.SelectionInputV2(fill_count=bad, **common)

    assert sel.SelectionInputV2(fill_count=12, **common).fill_count == 12


def test_at_i_an_empty_variant_id_is_refused():
    with pytest.raises(ConfigViolation):
        sel.SelectionInputV2(
            variant_id="",
            shutdown_events=0,
            fill_count=1,
            ladder_descents=0,
            lockout_arms=0,
            stops_filled=0,
        )


def _exec_as_module(source: str, source_path: Path, name: str) -> dict:
    """Execute module source under a real, registered module object, and unregister it afterwards.

    A bare ``exec`` into a plain dict is not enough. ``@dataclass`` resolves string annotations
    through ``sys.modules.get(cls.__module__)``, so a namespace whose ``__name__`` names no
    registered module makes ``dataclasses._is_type`` dereference ``None`` and raises
    ``AttributeError`` from inside the standard library — which looks like a defect in the module
    under test and is not one. This is Attempt 2's mechanism, unchanged.
    """
    module = types.ModuleType(name)
    module.__file__ = str(source_path)
    sys.modules[name] = module
    try:
        exec(compile(source, str(source_path), "exec"), module.__dict__)
        return module.__dict__
    finally:
        sys.modules.pop(name, None)


DATACLASS_BODY = (
    "    variant_id: str\n"
    "    shutdown_events: int\n"
    "    fill_count: int\n"
    "    ladder_descents: int\n"
    "    lockout_arms: int\n"
    "    stops_filled: int\n"
)

FIELD_NAME_TUPLE = (
    "SELECTION_V2_FIELD_NAMES = (\n"
    '    "variant_id",\n'
    '    "shutdown_events",\n'
    '    "fill_count",\n'
    '    "ladder_descents",\n'
    '    "lockout_arms",\n'
    '    "stops_filled",\n'
    ")\n"
)


def test_at_i_the_unmutated_source_executes_cleanly():
    """Control for the two injections below, so neither can pass for the wrong reason."""
    source_path = Path(sel.__file__)
    namespace = _exec_as_module(
        source_path.read_text(encoding="utf-8"), source_path, "g2_selection_v2_at_i_control"
    )
    assert namespace["SELECTION_V2_FIELD_NAMES"] == sel.SELECTION_V2_FIELD_NAMES
    assert namespace["SELECTION_RULE_ID"] == sel.SELECTION_RULE_ID


def test_at_i_the_import_time_guard_fires_when_a_field_is_added():
    """Injection one: a sixth counter, benign in name, added to the dataclass only.

    The first guard compares the class's field tuple against the module constant, so this fires
    without any vocabulary being involved. Nothing on disk is touched — the source text is read,
    mutated in memory, and executed under a throwaway module name.
    """
    source_path = Path(sel.__file__)
    source = source_path.read_text(encoding="utf-8")
    assert source.count(DATACLASS_BODY) == 1, "the dataclass body was not found verbatim"

    mutated = source.replace(DATACLASS_BODY, DATACLASS_BODY + "    extra_counter: int\n")
    assert mutated != source

    with pytest.raises(ConfigViolation) as caught:
        _exec_as_module(mutated, source_path, "g2_selection_v2_at_i_added_field")
    message = str(caught.value)
    assert "extra_counter" in message
    assert "the selector can see" in message


def test_at_i_the_import_time_guard_fires_when_a_field_names_a_return():
    """Injection two: a field renamed to carry performance vocabulary, in *both* places.

    The constant is edited alongside the dataclass precisely so the first guard passes — which is
    how a real edit would look, since an author adding a field would naturally update both. Only the
    second guard, which inspects the names themselves, can catch it.
    """
    source_path = Path(sel.__file__)
    source = source_path.read_text(encoding="utf-8")
    assert source.count(DATACLASS_BODY) == 1
    assert source.count(FIELD_NAME_TUPLE) == 1

    mutated = source.replace(
        DATACLASS_BODY, DATACLASS_BODY.replace("stops_filled: int", "stops_filled_pnl: int")
    ).replace(FIELD_NAME_TUPLE, FIELD_NAME_TUPLE.replace('"stops_filled"', '"stops_filled_pnl"'))
    assert mutated != source

    with pytest.raises(ConfigViolation) as caught:
        _exec_as_module(mutated, source_path, "g2_selection_v2_at_i_named_field")
    message = str(caught.value)
    assert "stops_filled_pnl" in message
    assert "pnl" in message
    assert "return-blind" in message


def test_at_i_the_runner_carries_its_own_copy_of_the_guard():
    """The consumption site guards too, and its guard passes on the real dataclass.

    ``g2_selection_v2`` guards at its own import, but the runner is what *populates* the dataclass,
    so a guard living only in the callee cannot fire before the caller has already built the object.
    """
    assert runner._assert_selection_surface() is None
    assert runner.SELECTION_V2_FIELD_NAMES == sel.SELECTION_V2_FIELD_NAMES


def _stub_run(variant, label, *, fills, shutdown, descents, arms, stops_filled):
    """One ``GridRunRA3`` with a stand-in result, built without running an engine.

    AT-I's claim is about the *projection* — which fields survive the trip from a completed run into
    the selection input — so driving eighteen real backtests would test the engine instead and take
    minutes doing it. ``selection_inputs`` reads exactly five things off a run; this supplies those
    five and leaves the rest of the record populated but inert.
    """
    result = types.SimpleNamespace(
        fills=tuple(range(fills)),
        shutdown_session="2010-06-15" if shutdown else None,
    )
    return runner.GridRunRA3(
        variant=variant,
        label=label,
        scenario=runner.scenario_for_label(label),
        result=result,
        measurement={"total_return": "0.9999", "max_drawdown": "0.1234"},
        strategy_evidence={"sharpe": "2.5"},
        clamps={},
        risk={
            "ladder": {"descents": descents},
            "lockout": {"arms": arms},
            "stops": {"filled": stops_filled},
        },
        trades=[],
        ledger=[],
        reconciliation={},
    )


def test_at_i_the_projection_from_completed_runs_exposes_only_the_six_fields():
    """End to end through ``selection_inputs``, with performance figures deliberately present.

    The stub runs carry a total return, a max drawdown and a Sharpe ratio in their measurement and
    evidence dictionaries. If the projection leaked any part of a run into the selection input, one
    of those would appear in the serialised payload. None may.
    """
    runs = [
        _stub_run(
            variant,
            label,
            fills=40 + index,
            shutdown=False,
            descents=3 * index,
            arms=3 * index,
            stops_filled=index % 3,
        )
        for index, variant in enumerate(variants(), start=1)
        for label in runner.run_labels()
    ]
    inputs = runner.selection_inputs(runs)
    assert len(inputs) == 18

    payload = json.dumps([dataclasses.asdict(entry) for entry in inputs])
    for word in ("0.9999", "0.1234", "2.5", "total_return", "max_drawdown", "sharpe"):
        assert word not in payload
    for entry in inputs:
        assert set(dataclasses.asdict(entry)) == set(sel.SELECTION_V2_FIELD_NAMES)

    # Both runs are summed into one record per variant, which is what makes the screen a screen.
    first = next(entry for entry in inputs if entry.variant_id == variants()[0].variant_id)
    assert first.fill_count == (40 + 1) * 2
    assert first.ladder_descents == 3 * 2
    assert first.shutdown_events == 0


def test_at_i_a_variant_missing_a_run_is_refused_rather_than_screened_on_half():
    runs = [
        _stub_run(variant, label, fills=10, shutdown=False, descents=1, arms=1, stops_filled=0)
        for variant in variants()
        for label in runner.run_labels()
    ]
    with pytest.raises(ConfigViolation) as caught:
        runner.selection_inputs(runs[:-1])
    assert "the seal declares exactly" in str(caught.value)


def test_at_i_a_partial_grid_is_refused():
    """A grid short of eighteen variants cannot be scored: the missing ones are somebody's
    neighbours, so their absence would silently change the surviving variants' scores."""
    runs = [
        _stub_run(variant, label, fills=10, shutdown=False, descents=1, arms=1, stops_filled=0)
        for variant in variants()[:-1]
        for label in runner.run_labels()
    ]
    with pytest.raises(ConfigViolation) as caught:
        runner.selection_inputs(runs)
    assert "incomplete" in str(caught.value)

    with pytest.raises(ConfigViolation) as caught:
        sel.score_neighbourhood(gradient()[:4])
    assert "eighteen declared variants" in str(caught.value)


# ---------------------------------------------------------------------------------------------
# AT-J. Neighbour identification at the grid edges.
# ---------------------------------------------------------------------------------------------

# Written out by hand from the axis definition — a lookback corner has no lower lookback, a k=1
# corner has no lower k, and the frequency axis always contributes exactly one. Compared element by
# element below against what the module computes.
NEIGHBOURS_OF_A_CORNER = (
    PREFIX + "L03-K1-QUARTERLY",
    PREFIX + "L03-K2-MONTHLY",
    PREFIX + "L06-K1-MONTHLY",
)
NEIGHBOURS_OF_AN_EDGE = (
    PREFIX + "L03-K1-MONTHLY",
    PREFIX + "L03-K2-QUARTERLY",
    PREFIX + "L03-K3-MONTHLY",
    PREFIX + "L06-K2-MONTHLY",
)
NEIGHBOURS_OF_THE_INTERIOR = (
    PREFIX + "L03-K2-MONTHLY",
    PREFIX + "L06-K1-MONTHLY",
    PREFIX + "L06-K2-QUARTERLY",
    PREFIX + "L06-K3-MONTHLY",
    PREFIX + "L12-K2-MONTHLY",
)


@pytest.mark.parametrize(
    "variant_id, expected",
    [
        (PREFIX + "L03-K1-MONTHLY", NEIGHBOURS_OF_A_CORNER),
        (PREFIX + "L03-K2-MONTHLY", NEIGHBOURS_OF_AN_EDGE),
        (PREFIX + "L06-K2-MONTHLY", NEIGHBOURS_OF_THE_INTERIOR),
    ],
    ids=["corner-3", "edge-4", "interior-5"],
)
def test_at_j_one_variant_of_each_class_matches_a_hand_written_neighbour_set(variant_id, expected):
    computed = sel.neighbours_of(variant_id)
    assert computed == expected
    for index, (got, want) in enumerate(zip(computed, expected)):
        assert got == want, f"neighbour {index} of {variant_id}"
    assert len(computed) == len(expected)


def test_at_j_the_partition_over_the_eighteen_is_eight_eight_two():
    """The sealed partition, and the keys it is reported under.

    The seal records that a hand count of this partition was wrong on the first pass, which is why
    the module computes it. The count classes are integers in process; a JSON round trip would turn
    them into strings and quietly change what the assertion means.
    """
    structure = sel.check_neighbourhood_structure()
    assert structure["variant_count"] == 18
    assert structure["partition"] == {3: 8, 4: 8, 5: 2}
    assert all(isinstance(key, int) for key in structure["partition"])
    assert sum(structure["partition"].values()) == 18
    assert set(structure["counts"].values()) == {3, 4, 5}
    assert structure["instruction_conflict_ref"] == "G2A3-CONFLICT-27"


def test_at_j_the_relation_is_symmetric_and_totals_sixty_six_directed_pairs():
    structure = sel.check_neighbourhood_structure()
    assert structure["symmetric"] is True
    assert structure["total_directed_pairs"] == 66
    assert 66 == 8 * 3 + 8 * 4 + 2 * 5

    # Recomputed here rather than read, so the module's own symmetry flag is not the only evidence.
    for variant_id in ids():
        for neighbour in sel.neighbours_of(variant_id):
            assert variant_id in sel.neighbours_of(neighbour), (
                f"{variant_id} lists {neighbour} but not the reverse"
            )


def test_at_j_no_variant_is_its_own_neighbour_and_none_is_outside_the_grid():
    grid = set(ids())
    for variant_id in ids():
        neighbours = sel.neighbours_of(variant_id)
        assert variant_id not in neighbours
        assert set(neighbours) <= grid
        assert len(set(neighbours)) == len(neighbours), "duplicate neighbour"
        assert list(neighbours) == sorted(neighbours), "neighbours are returned sorted"


def test_at_j_an_ordered_axis_steps_to_the_adjacent_position_only():
    """A 3-month lookback neighbours 6 and not 12. The axis is ordered, not categorical.

    Without this the 3-neighbour class would not exist at all and the partition would be 18 × 5.
    """
    corner = sel.neighbours_of(PREFIX + "L03-K1-MONTHLY")
    assert not any("L12-" in neighbour for neighbour in corner)
    assert not any("K3-" in neighbour for neighbour in corner)

    middle = sel.neighbours_of(PREFIX + "L06-K2-MONTHLY")
    assert any("L03-" in neighbour for neighbour in middle)
    assert any("L12-" in neighbour for neighbour in middle)


def test_at_j_injected_defect_a_variant_outside_the_grid_is_refused():
    """The enumeration is keyed on the declared grid, so an unknown id must not return an empty
    neighbourhood — that would score as perfectly stable."""
    with pytest.raises(ConfigViolation) as caught:
        sel.neighbours_of(PREFIX + "L99-K9-MONTHLY")
    assert "eighteen declared variants" in str(caught.value)


def test_at_j_injected_defect_a_two_axis_reading_would_produce_the_wrong_partition():
    """The check that the 8/8/2 assertion is not vacuous.

    If the frequency axis were treated as a third *ordered* axis with two positions it would still
    contribute one neighbour and nothing would change; the failure mode worth catching is dropping
    it. Recomputing the partition with the frequency neighbour removed must give 2/3/4 — a different
    partition entirely — so the assertion above is discriminating between real alternatives.
    """
    without_frequency = {}
    for variant_id in ids():
        kept = [
            neighbour
            for neighbour in sel.neighbours_of(variant_id)
            if neighbour.rsplit("-", 1)[0] != variant_id.rsplit("-", 1)[0]
        ]
        without_frequency[variant_id] = len(kept)
    partition = {}
    for count in without_frequency.values():
        partition[count] = partition.get(count, 0) + 1
    assert partition == {2: 8, 3: 8, 4: 2}
    assert partition != sel.check_neighbourhood_structure()["partition"]


# ---------------------------------------------------------------------------------------------
# AT-K. Determinism of SE100-G2-SEL-2.
# ---------------------------------------------------------------------------------------------


def test_at_k_the_gradient_fixture_scores_as_measured():
    """The anchor. Every other determinism test below compares against a recomputation; this one
    compares against values measured before the assertions were written, so a change in the scoring
    arithmetic that is *consistently* wrong still fails here.

    The score is also recomputed from its own components, which is what makes it a mean rather than
    an assertion that the module agrees with itself.
    """
    scores = sel.score_neighbourhood(gradient())
    corner = scores[PREFIX + "L03-K1-MONTHLY"]

    assert corner.own_quantities == {
        "fill_count": 101,
        "ladder_descents": 10,
        "lockout_arms": 10,
        "stops_filled": 1,
    }
    assert corner.per_quantity_mean == {
        "fill_count": Decimal("0.028432055"),
        "ladder_descents": Decimal("0.674603175"),
        "lockout_arms": Decimal("0.674603175"),
        "stops_filled": Decimal("0.611111111"),
    }
    assert corner.score == Decimal("0.497187379")

    total = sum(corner.per_quantity_mean.values(), Decimal(0))
    assert total / len(sel.QUANTITIES) == corner.score

    result = sel.select_representative_v2(gradient())
    assert result.selected == PREFIX + "L12-K3-MONTHLY"
    assert result.decided_at_step == 2
    assert result.scores[result.selected].score == Decimal("0.246872630")


def test_at_k_two_independent_computations_in_one_process_agree():
    """Two fixtures built from scratch, scored twice, selected twice. Nothing is reused between
    them except the variant grid, so a cached score or a mutated input would show."""
    first_inputs, second_inputs = gradient(), gradient()
    assert first_inputs is not second_inputs

    first = sel.select_representative_v2(first_inputs)
    second = sel.select_representative_v2(second_inputs)

    assert first.selected == second.selected
    assert first.decided_at_step == second.decided_at_step
    assert first.ranking == second.ranking
    assert set(first.scores) == set(second.scores)
    for variant_id in first.scores:
        left, right = first.scores[variant_id], second.scores[variant_id]
        assert left.score == right.score
        assert left.per_quantity_mean == right.per_quantity_mean
        assert left.per_quantity_both_zero == right.per_quantity_both_zero
        assert left.neighbours == right.neighbours


def test_at_k_a_round_trip_through_the_serialised_inputs_agrees():
    """The third computation AT-K requires, through JSON rather than through Python objects.

    The counters are integers by construction, so the round trip is lossless — but that is the
    claim, not the assumption: if a counter had ever become a ``Decimal`` it would arrive back as a
    string and ``__post_init__`` would refuse it, which is itself the guard working.
    """
    inputs = gradient()
    direct = sel.select_representative_v2(inputs)

    payload = json.dumps([dataclasses.asdict(entry) for entry in inputs])
    restored = tuple(sel.SelectionInputV2(**entry) for entry in json.loads(payload))
    assert restored == inputs, "the dataclass is frozen and compares by value"

    round_tripped = sel.select_representative_v2(restored)
    assert round_tripped.selected == direct.selected
    assert round_tripped.decided_at_step == direct.decided_at_step
    assert round_tripped.ranking == direct.ranking
    for variant_id in direct.scores:
        assert round_tripped.scores[variant_id].score == direct.scores[variant_id].score
        assert (
            round_tripped.scores[variant_id].per_quantity_mean
            == direct.scores[variant_id].per_quantity_mean
        )


def test_at_k_the_checkerboard_gives_every_variant_the_same_score():
    """A structural determinism claim rather than a repetition one.

    Every neighbour is exactly one single-axis step away, so under a two-level turnover assignment
    keyed on axis parity every variant's neighbours all sit at the opposite level. If the score were
    a function of the variant rather than of its neighbourhood, the eighteen would not agree.
    """
    scores = sel.score_neighbourhood(checkerboard())
    distinct = {entry.score for entry in scores.values()}
    assert distinct == {Decimal("0.041666667")}

    result = sel.select_representative_v2(checkerboard())
    assert result.decided_at_step == 4, "scores tie, and both turnover levels have nine variants"
    assert result.selected == min(ids())


def test_at_k_the_flat_fixture_falls_through_to_the_lexicographic_tiebreak():
    result = sel.select_representative_v2(flat())
    assert all(entry.score == Decimal(0) for entry in result.scores.values())
    assert result.decided_at_step == 4
    assert result.selected == min(ids()) == PREFIX + "L03-K1-MONTHLY"


def test_at_k_the_ranking_is_ordered_by_the_declared_step_sequence():
    """All four sealed steps as one ordering key: eligibility, score, turnover, variant id.

    The ranking is the rule made inspectable — sorting by that tuple is *how* the four steps are
    implemented, so asserting the key covers the order in which they apply, not merely their names.

    Step 3 has no reachable fixture of its own. Turnover is ``fill_count``, which is also one of the
    four scored quantities, so any two variants separated on turnover have already been separated at
    step 2. That is a property of the sealed rule rather than a gap here, and manufacturing a
    step-3 state would mean feeding the scorer counters it could never receive. The key carries the
    claim instead, asserted over four fixtures with different tie structures — one all-distinct, one
    all-tied on score with turnover split nine/nine, one tied on everything, and one with the
    eligibility key actually engaged — so a key that happened to be right on one of them is not
    enough.
    """
    assert sel.EXPECTED_STEP_CRITERIA == {
        1: "zero_research_shutdown_events",
        2: "lowest_neighbourhood_instability_score",
        3: "lowest_turnover",
        4: "lexicographic_variant_id",
    }
    sealed_steps = sel.check_seal_agreement()["steps"]
    assert {int(key): value for key, value in sealed_steps.items()} == sel.EXPECTED_STEP_CRITERIA

    screened = gradient(shutdown_for=(PREFIX + "L03-K1-MONTHLY", PREFIX + "L03-K3-QUARTERLY"))
    for fixture in (gradient(), checkerboard(), flat(), screened):
        result = sel.select_representative_v2(fixture)
        keys = [
            (
                not row["eligible"],
                Decimal(row["instability_score"]),
                row["fill_count"],
                row["variant_id"],
            )
            for row in result.ranking
        ]
        assert keys == sorted(keys)
        assert len(result.ranking) == 18
        assert result.ranking[0]["variant_id"] == result.selected

    # The eligibility key is not redundant with the score key: dropping it reorders the screened
    # fixture. Without this the assertion above would also pass on a rule that never screened.
    screened_result = sel.select_representative_v2(screened)
    without_eligibility = [
        (Decimal(row["instability_score"]), row["fill_count"], row["variant_id"])
        for row in screened_result.ranking
    ]
    assert without_eligibility != sorted(without_eligibility)


def test_at_k_the_shutdown_screen_runs_before_the_score():
    """Step 1. Two variants are knocked out; both keep their scores, neither can be selected.

    The module's docstring is explicit that neighbours are structural — an ineligible neighbour is
    still part of the parameter region and still contributes to its neighbours' scores. So the
    knocked-out pair must still appear in ``scores`` while being absent from ``eligible`` and from
    the ranking.
    """
    knocked = (PREFIX + "L03-K1-MONTHLY", PREFIX + "L03-K3-QUARTERLY")
    result = sel.select_representative_v2(gradient(shutdown_for=knocked))

    assert sorted(result.ineligible) == sorted(knocked)
    assert len(result.eligible) == 16
    assert set(result.scores) == set(ids()), "an ineligible neighbour is still scored"
    assert result.selected not in knocked

    # The knocked-out pair stays in the ranking, flagged and demoted, rather than vanishing from it.
    # That is the more useful shape: a reader can see what was screened out and what it would have
    # scored, which is exactly what an audit of the screen needs.
    assert len(result.ranking) == 18
    flags = [row["eligible"] for row in result.ranking]
    assert flags == [True] * 16 + [False] * 2
    for row in result.ranking[-2:]:
        assert row["variant_id"] in knocked
        assert row["shutdown_events"] == 1

    # And the demotion is doing real work rather than agreeing with the score order by luck: the
    # better-scoring of the two screened variants would have placed twelfth on score alone, ahead of
    # six variants that now outrank it purely because they survived the screen.
    demoted = Decimal(result.ranking[-2]["instability_score"])
    it_beats = [row for row in result.ranking[:16] if Decimal(row["instability_score"]) > demoted]
    assert len(it_beats) == 6

    # And the scores themselves are untouched by eligibility.
    clean = sel.score_neighbourhood(gradient())
    for variant_id in ids():
        assert result.scores[variant_id].score == clean[variant_id].score


def test_at_k_a_single_survivor_decides_at_step_one():
    survivors = ids()[:1]
    result = sel.select_representative_v2(gradient(shutdown_for=tuple(ids()[1:])))
    assert result.decided_at_step == 1
    assert list(result.eligible) == survivors
    assert result.selected == survivors[0]


def test_at_k_no_survivor_yields_no_candidate():
    """The path Attempt 1 took on all eighteen. It must be a clean ``None``, not an exception and
    not a fallback pick: the sealed no-candidate verdict is a *stage* outcome, not an error."""
    result = sel.select_representative_v2(gradient(shutdown_for=tuple(ids())))
    assert result.selected is None
    assert len(result.eligible) == 0
    assert len(result.ineligible) == 18
    assert sel.check_seal_agreement()["no_candidate_verdict"].endswith(
        "STAGE_3_G2_ATTEMPT_3_NO_CANDIDATE"
    )


def test_at_k_injected_defect_one_perturbed_counter_moves_the_selection():
    """The determinism assertions above would all pass on a rule that ignored its inputs entirely.

    Perturbing a single counter on a single variant must move something. The perturbation is applied
    to the variant the clean fixture selects, so the change has to reach the decision and not merely
    some unread corner of the score table.
    """
    clean = sel.select_representative_v2(gradient())
    perturbed = tuple(
        dataclasses.replace(entry, ladder_descents=entry.ladder_descents + 500)
        if entry.variant_id == clean.selected
        else entry
        for entry in gradient()
    )
    moved = sel.select_representative_v2(perturbed)

    assert moved.scores[clean.selected].score != clean.scores[clean.selected].score
    assert moved.selected != clean.selected
    assert moved.ranking != clean.ranking


def test_at_k_injected_defect_a_reordered_input_sequence_changes_nothing():
    """The mirror of the test above: order is not an input.

    A rule that read its inputs in the order supplied would be deterministic per call and still
    wrong, because the grid is assembled by iteration order upstream.
    """
    forward = gradient()
    reversed_inputs = tuple(reversed(forward))
    assert [entry.variant_id for entry in reversed_inputs] != [
        entry.variant_id for entry in forward
    ]

    first = sel.select_representative_v2(forward)
    second = sel.select_representative_v2(reversed_inputs)
    assert first.selected == second.selected
    assert first.ranking == second.ranking
    assert first.decided_at_step == second.decided_at_step


def test_at_k_the_cost_scenario_constant_is_not_a_selection_input():
    """A guard against the one axis SEL-2 must not see, asserted where it would be introduced.

    The selection input is summed across both cost scenarios before it arrives. If a scenario label
    ever reached the dataclass it would be a fifth quantity in everything but name.
    """
    assert BASE == "BASE"
    assert "scenario" not in sel.SELECTION_V2_FIELD_NAMES
    assert not any("label" in name for name in sel.SELECTION_V2_FIELD_NAMES)
