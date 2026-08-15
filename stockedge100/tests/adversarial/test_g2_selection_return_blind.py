"""The representative-selection rule cannot see a return, and this is how that is demonstrated.

``config/generation_2/g2_rotation_protocol.json`` seals the requirement in its own words:

    "the representative-selection rule is return-blind: permuting every variant's returns while
    holding shutdown counts and fill counts fixed does not change which variant is selected"

The permutation is the whole test. A rule that read a return figure would, under a permutation that
moves the best return from one variant to another, select a different variant — unless the
permutation happened to be the identity, which is why the permutations below are checked to be
non-trivial before they are used.

**Why the runs here are stubs.** ``selection_inputs`` is the single place a completed run is touched
on the way to a selection, and it reads three attributes off each one. Feeding it duck-typed records
lets the returns be set to whatever the test needs, including values no real backtest would produce,
and lets shutdown and fill counts be pinned exactly while they move. Driving 36 real backtests
instead would fix the returns to whatever the fixture happened to produce and make the permutation
impossible to perform. The projection is verified against the real :class:`GridRun` contract
separately, by asserting the attribute names this file relies on are the ones that class exposes.

The negative half matters as much: §6 of this file shows that the selection *is* a function of the
two counts it is allowed to read, so "nothing changed the answer" is a statement about returns
specifically and not about a rule that ignores its inputs altogether.
"""

from __future__ import annotations

import dataclasses
import json
from dataclasses import fields

import pytest

from stockedge100.backtest.errors import ConfigViolation
from stockedge100.strategies.g2_runner import (
    SELECTION_FIELD_NAMES,
    GridRun,
    SelectionInput,
    run_labels,
    sealed_steps,
    select_representative,
    selection_inputs,
)
from stockedge100.strategies.g2_rotation import load_protocol, rotation_variants

#: A value no real run could produce, attached to every stub as its "return". If any of it reached
#: the selection record, the substring search in :func:`test_no_stub_return_reaches_the_record`
#: would find it.
SENTINEL = "9999999.999999"

LABELS = ("#BASE", "#STRESS")


class StubRun:
    """A completed run, as far as ``selection_inputs`` is concerned — plus loud performance figures.

    The three attributes the projection reads are real. Everything else on this object is a return
    figure of some kind, placed here so that a selection which reached for one would have something
    to find. ``selection_inputs`` performs no isinstance check, so this is a faithful stand-in.
    """

    def __init__(self, variant_id, label, *, shutdown, fills, ret):
        self.variant = _Variant(variant_id)
        self.label = label
        self.shutdown_fired = bool(shutdown)
        self.fill_count = int(fills)
        # None of the following is readable through SelectionInput.
        self.total_return = ret
        self.net_return_fraction = ret
        self.profit_factor = ret
        self.max_drawdown = ret
        self.sharpe = ret
        self.final_equity = f"{SENTINEL}"
        self.measurement = {"net_return_fraction": ret, "sentinel": SENTINEL}
        self.result = None

    @property
    def run_id(self):
        return f"{self.variant.variant_id}{self.label}"


class _Variant:
    def __init__(self, variant_id):
        self.variant_id = variant_id


VARIANT_IDS = tuple(sorted(variant.variant_id for variant in rotation_variants()))


def build_runs(shutdowns, fills, returns):
    """36 stub runs: one per variant per declared label.

    ``shutdowns`` and ``fills`` are keyed by variant id and apply per label; ``returns`` is keyed by
    variant id and is the thing being permuted.
    """
    runs = []
    for variant_id in VARIANT_IDS:
        for index, label in enumerate(LABELS):
            runs.append(
                StubRun(
                    variant_id,
                    label,
                    shutdown=shutdowns[variant_id][index],
                    fills=fills[variant_id][index],
                    ret=returns[variant_id],
                )
            )
    return runs


def rotate(values, by):
    return values[by:] + values[:by]


def returns_rotated_by(by):
    """A deterministic permutation of the return figures. No randomness, so it replays exactly."""
    magnitudes = [f"{-0.5 + index * 0.137:.6f}" for index in range(len(VARIANT_IDS))]
    return dict(zip(VARIANT_IDS, rotate(magnitudes, by)))


# The default grid: three variants shut down, and among the rest one has a uniquely lowest fill
# count, so the selection is decided at step 2 — the step most exposed to a return leak, because it
# is the one that ranks eligible variants against each other.
SHUTDOWN_VARIANTS = (VARIANT_IDS[0], VARIANT_IDS[7], VARIANT_IDS[17])


def default_shutdowns():
    return {
        variant_id: ((1, 0) if variant_id in SHUTDOWN_VARIANTS else (0, 0))
        for variant_id in VARIANT_IDS
    }


def default_fills():
    counts = {}
    for index, variant_id in enumerate(VARIANT_IDS):
        counts[variant_id] = (40 + index * 3, 41 + index * 3)
    # VARIANT_IDS[1] is eligible and given a uniquely lowest total.
    counts[VARIANT_IDS[1]] = (10, 11)
    return counts


def selection_for(returns, *, shutdowns=None, fills=None):
    runs = build_runs(shutdowns or default_shutdowns(), fills or default_fills(), returns)
    inputs = selection_inputs(runs)
    return inputs, select_representative(inputs)


def canonical(record):
    return json.dumps(record, sort_keys=True, default=str)


# ==================================================================================================
# 1. clean controls
# ==================================================================================================


def test_the_stub_matches_the_contract_of_the_class_it_stands_in_for():
    """If ``GridRun`` renamed any of these, the stubs would silently stop being faithful."""
    for attribute in ("variant", "label", "shutdown_fired", "fill_count", "run_id"):
        assert hasattr(GridRun, attribute) or attribute in {
            field.name for field in fields(GridRun)
        }, f"GridRun no longer exposes {attribute!r}; the stubs in this file are stale"

    stub = StubRun(VARIANT_IDS[0], "#BASE", shutdown=False, fills=7, ret="0.1")
    assert stub.variant.variant_id == VARIANT_IDS[0]
    assert stub.shutdown_fired is False and stub.fill_count == 7


def test_the_declared_labels_and_grid_are_what_this_file_assumes():
    assert run_labels() == LABELS
    assert len(VARIANT_IDS) == 18
    assert len(build_runs(default_shutdowns(), default_fills(), returns_rotated_by(0))) == 36


def test_the_baseline_selection_is_well_formed_and_decided_at_step_2():
    inputs, record = selection_for(returns_rotated_by(0))

    assert len(inputs) == 18
    assert record["representative_exists"] is True
    assert record["representative_variant_id"] == VARIANT_IDS[1]
    assert record["decided_at_step"] == 2
    assert record["decided_by"] == "lowest_turnover"
    assert record["step_1"]["eligible_count"] == 15
    assert sorted(record["step_1"]["ineligible"], key=lambda e: e["variant_id"]) == [
        {"variant_id": variant_id, "research_shutdown_events": 1}
        for variant_id in sorted(SHUTDOWN_VARIANTS)
    ]
    assert record["step_2"]["lowest_fill_count"] == 21


# ==================================================================================================
# 2. the sealed property: permuting the returns changes nothing
# ==================================================================================================


def test_the_permutations_used_below_really_do_move_the_returns():
    """Non-vacuity for the whole section. An identity permutation would prove nothing."""
    baseline = returns_rotated_by(0)

    for by in range(1, len(VARIANT_IDS)):
        permuted = returns_rotated_by(by)
        assert permuted != baseline
        moved = [v for v in VARIANT_IDS if permuted[v] != baseline[v]]
        assert len(moved) == len(VARIANT_IDS), f"rotation {by} left a variant's return in place"
        assert sorted(permuted.values()) == sorted(baseline.values()), "a rotation is a permutation"


@pytest.mark.parametrize("by", list(range(1, 18)))
def test_permuting_every_return_leaves_the_selection_byte_identical(by):
    _, baseline = selection_for(returns_rotated_by(0))
    _, permuted = selection_for(returns_rotated_by(by))

    assert canonical(permuted) == canonical(baseline)


@pytest.mark.parametrize("by", list(range(1, 18)))
def test_permuting_every_return_leaves_the_projection_byte_identical(by):
    """The projection is where a leak would have to happen; the selection only sees its output."""
    baseline, _ = selection_for(returns_rotated_by(0))
    permuted, _ = selection_for(returns_rotated_by(by))

    assert [entry.to_json() for entry in permuted] == [entry.to_json() for entry in baseline]
    assert permuted == baseline


def test_a_return_aware_ordering_would_have_moved_under_those_same_permutations():
    """The counterfactual, stated explicitly.

    Without this, "the selection did not change" is consistent with the permutations having been
    too weak to change anything. Ranking the same variants by the same permuted returns produces a
    different winner under every rotation — so the permutations are strong enough, and the reason
    the selection held still is that it never read them.
    """
    def best_by_return(returns):
        return max(VARIANT_IDS, key=lambda v: (float(returns[v]), v))

    baseline_winner = best_by_return(returns_rotated_by(0))
    moved = {best_by_return(returns_rotated_by(by)) for by in range(1, 18)}

    assert len(moved) == 17
    assert baseline_winner not in moved or len(moved | {baseline_winner}) > 1
    _, record = selection_for(returns_rotated_by(0))
    assert record["representative_variant_id"] != baseline_winner, (
        "the return-blind rule happens to agree with the return-greedy one; rebuild the fixture so "
        "that agreement cannot mask a leak"
    )


def test_extreme_returns_do_not_move_the_selection_either():
    """Not a permutation but the same claim at its limit: one variant made overwhelmingly best."""
    _, baseline = selection_for(returns_rotated_by(0))

    for target in (VARIANT_IDS[0], VARIANT_IDS[5], VARIANT_IDS[17]):
        skewed = {v: "-0.900000" for v in VARIANT_IDS}
        skewed[target] = "12.000000"
        _, record = selection_for(skewed)
        assert canonical(record) == canonical(baseline)


def test_no_stub_return_reaches_the_record():
    """A substring search, because a leak need not change the winner to be a leak."""
    inputs, record = selection_for(returns_rotated_by(0))

    blob = canonical(record)
    assert SENTINEL not in blob
    for entry in inputs:
        assert SENTINEL not in json.dumps(entry.to_json(), sort_keys=True)
        assert set(entry.to_json()) == {
            "variant_id",
            "research_shutdown_events",
            "fill_count",
            "per_run",
        }


# ==================================================================================================
# 3. the projection is structurally incapable of carrying a return
# ==================================================================================================


def test_selection_input_carries_exactly_the_declared_fields():
    assert tuple(field.name for field in fields(SelectionInput)) == SELECTION_FIELD_NAMES
    assert SELECTION_FIELD_NAMES == ("variant_id", "shutdown_events", "fill_count", "per_run")


def test_no_declared_field_names_a_performance_figure():
    vocabulary = (
        "return", "drawdown", "profit", "sharpe", "equity", "pnl", "p_l", "win",
        "gain", "loss", "alpha", "cagr", "yield",
    )

    for name in SELECTION_FIELD_NAMES:
        assert not any(word in name.lower() for word in vocabulary), name


def test_selection_input_is_frozen_so_a_figure_cannot_be_attached_afterwards():
    entry = SelectionInput(
        variant_id=VARIANT_IDS[0], shutdown_events=0, fill_count=5, per_run=(("#BASE", 0, 5),)
    )

    assert dataclasses.is_dataclass(entry)
    with pytest.raises(dataclasses.FrozenInstanceError):
        entry.fill_count = 6
    with pytest.raises(dataclasses.FrozenInstanceError):
        entry.total_return = "0.5"


def test_the_record_states_its_own_enforcement_in_terms_of_that_projection():
    _, record = selection_for(returns_rotated_by(0))

    assert record["return_blind"] is True
    assert "SelectionInput" in record["return_blind_enforcement"]
    for name in SELECTION_FIELD_NAMES:
        assert name in record["return_blind_enforcement"]
    assert record["return_blind_statement"] == (
        load_protocol()["representative_selection_rule"]["return_blind_statement"]
    )


# ==================================================================================================
# 4. the screen reads both declared runs, not the convenient one
# ==================================================================================================


def test_a_shutdown_in_the_stressed_run_alone_still_disqualifies():
    """A screen that looked only at ``#BASE`` would pass this variant, and the seal forbids that."""
    shutdowns = default_shutdowns()
    shutdowns[VARIANT_IDS[1]] = (0, 1)

    _, record = selection_for(returns_rotated_by(0), shutdowns=shutdowns)

    assert VARIANT_IDS[1] not in record["step_1"]["eligible"]
    assert record["representative_variant_id"] != VARIANT_IDS[1]


def test_a_variant_missing_its_stressed_run_is_refused_rather_than_screened_on_half():
    runs = [
        run
        for run in build_runs(default_shutdowns(), default_fills(), returns_rotated_by(0))
        if not (run.variant.variant_id == VARIANT_IDS[1] and run.label == "#STRESS")
    ]

    with pytest.raises(ConfigViolation, match="screens across BOTH declared runs"):
        selection_inputs(runs)


def test_a_run_supplied_twice_is_refused():
    runs = build_runs(default_shutdowns(), default_fills(), returns_rotated_by(0))
    runs.append(StubRun(VARIANT_IDS[0], "#BASE", shutdown=False, fills=1, ret="0.1"))

    with pytest.raises(ConfigViolation, match="was supplied more than once"):
        selection_inputs(runs)


def test_an_undeclared_run_label_is_refused():
    runs = build_runs(default_shutdowns(), default_fills(), returns_rotated_by(0))
    runs.append(StubRun(VARIANT_IDS[0], "#EXTRA", shutdown=False, fills=1, ret="0.1"))

    with pytest.raises(ConfigViolation, match="unexpected=\\['#EXTRA'\\]"):
        selection_inputs(runs)


def test_a_partial_grid_is_refused():
    inputs, _ = selection_for(returns_rotated_by(0))

    with pytest.raises(ConfigViolation, match="the selection runs over the complete declared grid"):
        select_representative(inputs[:12])


def test_duplicate_variant_ids_in_the_inputs_are_refused():
    inputs, _ = selection_for(returns_rotated_by(0))
    doubled = list(inputs) + [inputs[0]]

    with pytest.raises(ConfigViolation, match="duplicate variant ids"):
        select_representative(doubled, require_full_grid=False)


# ==================================================================================================
# 5. the three declared steps, each decided in turn
# ==================================================================================================


def test_step_1_decides_when_exactly_one_variant_survives_the_screen():
    survivor = VARIANT_IDS[9]
    shutdowns = {v: ((0, 0) if v == survivor else (1, 1)) for v in VARIANT_IDS}
    fills = {v: (900, 900) for v in VARIANT_IDS}  # the survivor has the *highest* turnover

    _, record = selection_for(returns_rotated_by(0), shutdowns=shutdowns, fills=fills)

    assert record["representative_variant_id"] == survivor
    assert record["decided_at_step"] == 1
    assert record["decided_by"] == "zero_research_shutdown_events"
    assert record["step_2"]["reached"] is False
    assert record["step_3"]["reached"] is False


def test_step_3_decides_a_tie_lexicographically():
    tied = (VARIANT_IDS[3], VARIANT_IDS[11])
    shutdowns = {v: ((0, 0) if v in tied else (1, 0)) for v in VARIANT_IDS}
    fills = {v: ((5, 5) if v in tied else (99, 99)) for v in VARIANT_IDS}

    _, record = selection_for(returns_rotated_by(0), shutdowns=shutdowns, fills=fills)

    assert record["decided_at_step"] == 3
    assert record["decided_by"] == "lexicographic_variant_id"
    assert sorted(record["step_2"]["tied_at_lowest"]) == sorted(tied)
    assert record["representative_variant_id"] == min(tied)


@pytest.mark.parametrize("by", list(range(1, 18)))
def test_the_tiebreak_is_return_blind_too(by):
    """Step 3 is where a return would be most tempting to consult, and most invisible if it were."""
    tied = (VARIANT_IDS[3], VARIANT_IDS[11])
    shutdowns = {v: ((0, 0) if v in tied else (1, 0)) for v in VARIANT_IDS}
    fills = {v: ((5, 5) if v in tied else (99, 99)) for v in VARIANT_IDS}

    _, baseline = selection_for(returns_rotated_by(0), shutdowns=shutdowns, fills=fills)
    _, permuted = selection_for(returns_rotated_by(by), shutdowns=shutdowns, fills=fills)

    assert canonical(permuted) == canonical(baseline)
    assert baseline["representative_variant_id"] == min(tied)


def test_no_candidate_when_every_variant_shut_down_at_least_once():
    shutdowns = {v: (1, 0) for v in VARIANT_IDS}

    _, record = selection_for(returns_rotated_by(0), shutdowns=shutdowns)

    assert record["representative_exists"] is False
    assert record["representative_variant_id"] is None
    assert record["decided_at_step"] is None
    assert record["decided_by"] == "no_candidate_path"
    assert record["step_2"] is None and record["step_3"] is None
    assert "the grid is not loosened" in record["selection_note"]
    assert record["no_candidate_path"] == (
        load_protocol()["representative_selection_rule"]["no_candidate_path"]
    )


@pytest.mark.parametrize("by", list(range(1, 18)))
def test_the_no_candidate_path_is_return_blind_too(by):
    """The best return in the grid must not rescue a variant the screen rejected."""
    shutdowns = {v: (1, 0) for v in VARIANT_IDS}

    _, baseline = selection_for(returns_rotated_by(0), shutdowns=shutdowns)
    _, permuted = selection_for(returns_rotated_by(by), shutdowns=shutdowns)

    assert canonical(permuted) == canonical(baseline)
    assert permuted["representative_exists"] is False


# ==================================================================================================
# 6. the negative half: the rule is a function of what it *is* allowed to read
# ==================================================================================================


def test_moving_a_shutdown_event_changes_the_selection():
    """If it did not, §2's stability would be the stability of a rule that ignores everything."""
    _, baseline = selection_for(returns_rotated_by(0))
    assert baseline["representative_variant_id"] == VARIANT_IDS[1]

    shutdowns = default_shutdowns()
    shutdowns[VARIANT_IDS[1]] = (1, 0)
    _, changed = selection_for(returns_rotated_by(0), shutdowns=shutdowns)

    assert changed["representative_variant_id"] != baseline["representative_variant_id"]
    assert VARIANT_IDS[1] in [e["variant_id"] for e in changed["step_1"]["ineligible"]]


def test_moving_a_fill_count_changes_the_selection():
    _, baseline = selection_for(returns_rotated_by(0))

    fills = default_fills()
    fills[VARIANT_IDS[1]] = (500, 500)
    fills[VARIANT_IDS[4]] = (1, 1)
    _, changed = selection_for(returns_rotated_by(0), fills=fills)

    assert changed["representative_variant_id"] == VARIANT_IDS[4]
    assert changed["decided_by"] == "lowest_turnover"


def test_the_turnover_measure_sums_both_runs_rather_than_reading_one():
    """A variant cheap in ``#BASE`` and expensive in ``#STRESS`` must not win on the base run."""
    fills = default_fills()
    fills[VARIANT_IDS[1]] = (30, 30)   # 60 total
    fills[VARIANT_IDS[4]] = (1, 300)   # cheapest base run, 301 total

    _, record = selection_for(returns_rotated_by(0), fills=fills)

    assert record["step_2"]["fill_counts"][VARIANT_IDS[4]] == 301
    assert record["representative_variant_id"] != VARIANT_IDS[4]


# ==================================================================================================
# 7. the steps come from the seal, and disagreement halts
# ==================================================================================================


def test_the_sealed_steps_are_the_three_this_module_implements():
    rule = load_protocol()["representative_selection_rule"]
    steps = sealed_steps(rule)

    assert sorted(steps) == [1, 2, 3]
    assert [steps[order]["name"] for order in (1, 2, 3)] == [
        "zero_research_shutdown_events",
        "lowest_turnover",
        "lexicographic_variant_id",
    ]
    assert rule["return_blind"] is True
    assert rule["frozen_before_any_variant_is_run"] is True


def test_a_renamed_sealed_step_halts_rather_than_being_reinterpreted():
    rule = json.loads(json.dumps(load_protocol()["representative_selection_rule"]))
    rule["steps"][1]["name"] = "highest_return"

    with pytest.raises(ConfigViolation, match="this module implements 'lowest_turnover'"):
        sealed_steps(rule)


def test_a_sealed_step_declared_twice_halts():
    rule = json.loads(json.dumps(load_protocol()["representative_selection_rule"]))
    rule["steps"].append(dict(rule["steps"][0]))

    with pytest.raises(ConfigViolation, match="declares order 1 twice"):
        sealed_steps(rule)


def test_a_missing_sealed_step_halts():
    rule = json.loads(json.dumps(load_protocol()["representative_selection_rule"]))
    rule["steps"] = [step for step in rule["steps"] if int(step["order"]) != 3]

    with pytest.raises(ConfigViolation, match=r"declares steps \[1, 2\]"):
        sealed_steps(rule)


def test_a_fourth_sealed_step_halts_rather_than_being_ignored():
    """A step this module does not implement is a divergence, not a no-op."""
    rule = json.loads(json.dumps(load_protocol()["representative_selection_rule"]))
    extra = dict(rule["steps"][0])
    extra["order"] = 4
    extra["name"] = "highest_net_return"
    rule["steps"].append(extra)

    with pytest.raises(ConfigViolation, match="declares steps"):
        sealed_steps(rule)


def test_the_protocol_on_disk_still_states_the_sealed_return_blind_requirement():
    """Asserted against the artifact's own wording, so a reworded seal is caught here."""
    tests = load_protocol()["adversarial_test_requirements"]

    assert (
        "the representative-selection rule is return-blind: permuting every variant's returns "
        "while holding shutdown counts and fill counts fixed does not change which variant is "
        "selected"
    ) in tests["additional"]
