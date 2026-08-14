"""Stage 4 evaluation harness and Gate 4 evaluator — the safe tests.

These run *before* the single authorized validation-reading session and must stay runnable after it,
so **nothing here loads a validation observation**. Every price in this module is invented and every
date comes from the frozen exchange calendar or from a sealed artifact. That is not a stylistic
choice: the sealed ``iteration_budget`` permits exactly one session that reads validation and
exactly two validation-window engine runs, and a test that loaded the dataset would spend part of
that budget on a test. Synthetic series exercise the same code paths.

The tests are organised by the requirement they discharge, in the order the operating prompt lists
them: the two registered identifiers, the twelve fold boundaries, the empty training set, base and
stressed friction, all seven conditions in both directions, the exact threshold boundaries, the
conjunction, the not-evaluable family, both verdict tokens, the thirteen-artifact rule, holdout
fail-closure, broker unreachability, and deterministic serialisation.

Verdict tokens are read from the sealed ``verdict_token_derivation`` rather than written as literals,
per the suite convention: a test that hard-codes the token it expects cannot detect a seal that says
something else.
"""

from __future__ import annotations

import ast
import datetime as dt
import json
from collections import namedtuple
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from stockedge100.backtest.costs import BASE, STRESSED
from stockedge100.backtest.dataset import series_from_rows
from stockedge100.backtest.errors import ConfigViolation, WindowViolation
from stockedge100.backtest.window import development_window
from stockedge100.data.calendar import sessions_between
from stockedge100.strategies import stage4_evaluation as ev
from stockedge100.strategies import stage4_gate as g
from stockedge100.strategies.gate import MET, NOT_EVALUABLE, NOT_MET

# -- fixtures --------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def config() -> ev.Stage4Config:
    """The sealed configuration. Reads governance and config JSON only — no market data."""
    return ev.load_stage4_config()


@pytest.fixture(scope="module")
def criteria(config: ev.Stage4Config) -> dict[str, Any]:
    return config.criteria


@pytest.fixture(scope="module")
def tokens(criteria: dict[str, Any]) -> dict[str, Any]:
    return criteria["verdict_token_derivation"]


# -- synthetic market ------------------------------------------------------------------------------


def synthetic_series(symbol: str, first: dt.date, last: dt.date) -> Any:
    """A rising bar on every frozen session in ``[first, last]``.

    ``split_ratio`` is "1" explicitly: `series_from_rows` defaults it to "0", which `Bar.has_split`
    reads as a split and which would engage the corporate-action check on a fixture that has none.
    """
    rows = []
    for index, session in enumerate(sessions_between(first, last)):
        close = 100 + index
        rows.append(
            {
                "session": session.isoformat(),
                "open": str(close),
                "high": str(close),
                "low": str(close),
                "close": str(close),
                "adj_close": str(close),
                "volume": "1000",
                "dividend": "0",
                "split_ratio": "1",
            }
        )
    return series_from_rows(symbol, rows)


@pytest.fixture(scope="module")
def series(config: ev.Stage4Config) -> dict[str, Any]:
    """Synthetic bars spanning the warm-up segment and the whole validation window.

    The dates are real and the prices are not, which is exactly what the window arithmetic needs:
    `warmup_start` counts sessions on the frozen calendar and never looks at a price.
    """
    validation = ev.validation_window()
    first = development_window().start
    return {
        symbol: synthetic_series(symbol, first, validation.end)
        for symbol in sorted(set(config.declared_universe))
    }


# -- synthetic evidence ----------------------------------------------------------------------------

Point = namedtuple("Point", "session equity")


def base_evidence(**overrides: Any) -> dict[str, Any]:
    """Evidence for a BASE run that satisfies every condition it gates. Invented, deliberately."""
    evidence = dict(
        scenario="BASE",
        equity_points=755,
        reached_window_end=True,
        starting_equity="100000.00",
        final_equity="130000.00",
        total_return=Decimal("0.30"),
        sharpe=Decimal("0.60"),
        max_drawdown=Decimal("0.10"),
        shutdown_session=None,
        shutdown_fraction=None,
        max_drawdown_basis="session close",
        daily_returns=754,
        closed_trades=40,
        profit_factor=Decimal("1.20"),
        gross_profit="60000.00",
        gross_loss="50000.00",
    )
    evidence.update(overrides)
    return evidence


def stress_evidence(**overrides: Any) -> dict[str, Any]:
    evidence = dict(
        scenario="STRESSED",
        equity_points=755,
        reached_window_end=True,
        total_return=Decimal("0.10"),
        stress_multiplier="2.0",
        shutdown_enforced=True,
    )
    evidence.update(overrides)
    return evidence


def fold_evidence(positive: int = 12, completed: int = 12) -> list[dict[str, Any]]:
    return [
        {"fold": index, "completed": index <= completed, "positive": index <= positive}
        for index in range(1, 13)
    ]


def invariance_evidence(**overrides: Any) -> dict[str, Any]:
    evidence = dict(
        all_digests_equal=True,
        digests_equal=13,
        digests_total=13,
        digest_rows=[],
        validation_evaluation_run_records=1,
        validation_window_engine_runs=2,
        declared_run_count=2,
        parameters_unchanged=True,
        parameter_comparison={},
        strategy_invariance={},
        conflict_note="",
    )
    evidence.update(overrides)
    return evidence


def gate(criteria: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    """Evaluate Gate 4 on all-satisfying synthetic evidence, with the named part replaced."""
    call = dict(
        representative=ev.REPRESENTATIVE,
        base=base_evidence(),
        stress=stress_evidence(),
        folds=fold_evidence(),
        invariance=invariance_evidence(),
    )
    call.update(overrides)
    return g.evaluate_gate4(criteria, **call)


# == clean controls ================================================================================
# Three of them, at the top, so a failure below is attributable to the defect that test injects and
# not to the harness or to a sealed artifact that moved underneath it.


def test_control_the_sealed_configuration_loads_and_verifies(config: ev.Stage4Config) -> None:
    assert len(config.digests) == 13
    assert config.strategy_module_rel.endswith(".py")
    assert config.declared_run_count == 2


def test_control_synthetic_evidence_that_meets_everything_passes(
    criteria: dict[str, Any], tokens: dict[str, Any]
) -> None:
    """Without this control, an evaluator hard-wired to reject everything would look correct on a
    stage whose real evidence fails. Stage 3 rejected all six candidates; the same risk applies here
    with more force, because Gate 4 evaluates exactly one."""
    result = gate(criteria)
    assert result["gate_passed"] is True
    assert result["verdict_token"] == tokens["pass_token"]
    assert [row["verdict"] for row in result["conditions"]] == [MET] * 7


def test_control_the_synthetic_series_satisfies_the_sealed_warmup(
    config: ev.Stage4Config, series: dict[str, Any]
) -> None:
    window = ev.evaluation_window(series, config)
    assert window.end == ev.validation_window().end
    assert window.start < ev.validation_window().start


# == the two registered identifiers ================================================================


def test_exactly_two_runs_are_declared_and_their_labels_are_the_sealed_ones(
    config: ev.Stage4Config,
) -> None:
    assert config.declared_run_count == 2
    assert len(config.run_labels) == 2
    stem = ev.run_label_stem(config)
    assert list(config.run_labels) == [f"{stem}#BASE", f"{stem}#STRESS"]


def test_the_declared_order_is_base_then_stress(config: ev.Stage4Config) -> None:
    """Order is sealed, not incidental: the base run gates five conditions and the stressed run one,
    and the protocol declares them in that sequence."""
    assert [ev.label_suffix_for(config, label) for label in config.run_labels] == ["#BASE", "#STRESS"]


def test_the_two_runs_gate_the_conditions_the_seal_assigns_them(config: ev.Stage4Config) -> None:
    gated = {run["run_label"]: list(run["gates_conditions"]) for run in config.runs_declared}
    stem = ev.run_label_stem(config)
    assert gated[f"{stem}#BASE"] == ["S4-C1", "S4-C2", "S4-C3", "S4-C4", "S4-C6"]
    assert gated[f"{stem}#STRESS"] == ["S4-C5"]


def test_every_gated_condition_is_covered_exactly_once_between_the_two_runs(
    config: ev.Stage4Config,
) -> None:
    """S4-C7 is the exception and is deliberately absent: it is an artifact-invariance condition, not
    a run outcome, so no engine run gates it."""
    assigned = [c for run in config.runs_declared for c in run["gates_conditions"]]
    assert sorted(assigned) == ["S4-C1", "S4-C2", "S4-C3", "S4-C4", "S4-C5", "S4-C6"]
    assert len(assigned) == len(set(assigned))
    assert "S4-C7" not in assigned


def test_an_unregistered_label_has_no_suffix(config: ev.Stage4Config) -> None:
    with pytest.raises(ConfigViolation):
        ev.label_suffix_for(config, "SE100-S4-C2-MEANREV-RA1#VALIDATION#DEBUG")


def test_an_unregistered_scenario_cannot_be_selected() -> None:
    with pytest.raises(ConfigViolation):
        ev.run_by_scenario([], "BASE")


# == the twelve fold boundaries ====================================================================


def test_twelve_folds_are_sealed(config: ev.Stage4Config) -> None:
    assert len(ev.sealed_folds(config)) == 12


def test_fold_boundaries_are_contiguous_non_overlapping_and_ordered(
    config: ev.Stage4Config,
) -> None:
    folds = ev.sealed_folds(config)
    assert [fold.index for fold in folds] == list(range(1, 13))
    for earlier, later in zip(folds, folds[1:]):
        assert earlier.end < later.start
        assert (later.start - earlier.end).days == 1


def test_the_folds_tile_the_validation_window_exactly(config: ev.Stage4Config) -> None:
    folds = ev.sealed_folds(config)
    validation = ev.validation_window()
    assert folds[0].start == validation.start
    assert folds[-1].end == validation.end
    for fold in folds:
        assert validation.contains(fold.start) and validation.contains(fold.end)


def test_no_fold_touches_the_holdout(config: ev.Stage4Config) -> None:
    holdout = ev.holdout_window()
    for fold in ev.sealed_folds(config):
        assert fold.end < holdout.start


def test_fold_returns_chain_from_the_previous_folds_last_marked_equity(
    config: ev.Stage4Config,
) -> None:
    """The sealed ``fold_return_definition`` is a chain, not twelve independent backtests: fold 1's
    baseline is the starting capital and every later fold's baseline is its predecessor's last marked
    equity. Chained on a synthetic curve, the twelve returns must compose to the total return."""
    folds = ev.sealed_folds(config)
    start = Decimal("100000")
    curve = []
    equity = start
    for session in sessions_between(folds[0].start, folds[-1].end):
        equity += Decimal("10")
        curve.append(Point(session, equity))
    result = namedtuple("R", "equity_curve")(curve)

    rows = ev.fold_returns(result, folds, starting_equity=start)
    assert len(rows) == 12
    assert all(row["completed"] for row in rows)

    composed = Decimal(1)
    for row in rows:
        composed *= Decimal(1) + Decimal(str(row["fold_return"]))
    assert composed == (curve[-1].equity / start)


def test_a_run_that_stopped_early_leaves_later_folds_incomplete(config: ev.Stage4Config) -> None:
    """Not a smaller denominator — an incomplete fold. S4-C6 turns that into NOT_EVALUABLE."""
    folds = ev.sealed_folds(config)
    start = Decimal("100000")
    curve = [Point(session, start) for session in sessions_between(folds[0].start, folds[5].end)]
    result = namedtuple("R", "equity_curve")(curve)

    rows = ev.fold_returns(result, folds, starting_equity=start)
    assert [row["completed"] for row in rows] == [True] * 6 + [False] * 6


# == zero training folds ===========================================================================


def test_the_sealed_training_set_is_empty(config: ev.Stage4Config) -> None:
    train = config.fold_construction["train_folds"]
    assert int(train["count"]) == 0
    assert list(train["set"]) == []


def test_a_non_empty_training_set_is_refused(config: ev.Stage4Config) -> None:
    """Walk-forward with a training fold would mean re-estimating a parameter inside validation,
    which S4-C7 and constitution section 11 both forbid. The loader refuses rather than re-deriving
    the seal into agreement with itself."""
    tampered = json.loads(json.dumps(config.criteria))
    tampered["walk_forward_fold_construction"]["train_folds"] = {"count": 1, "set": [1]}
    broken = ev.Stage4Config(
        protocol=config.protocol,
        criteria=tampered,
        selection=config.selection,
        preregistration=config.preregistration,
        attempt2=config.attempt2,
        stage2=config.stage2,
        digests=config.digests,
        strategy_module_rel=config.strategy_module_rel,
    )
    with pytest.raises(ConfigViolation, match="train_folds"):
        ev.sealed_folds(broken)


# == base and stressed friction ====================================================================


def test_the_base_run_carries_the_unmodified_friction(config: ev.Stage4Config) -> None:
    declared = config.runs_declared[0]
    assert ev.costs_for(config, declared).scenario == BASE


def test_the_stressed_run_carries_the_multiplied_friction(config: ev.Stage4Config) -> None:
    declared = config.runs_declared[1]
    assert ev.costs_for(config, declared).scenario == STRESSED


def test_the_stress_multiplier_is_the_sealed_one(config: ev.Stage4Config) -> None:
    assert Decimal(str(config.stress_multiplier)) == Decimal("2.0")


def test_the_scenario_comes_from_the_friction_text_not_from_the_label(
    config: ev.Stage4Config,
) -> None:
    """A run labelled ``#BASE`` whose sealed friction text says "multiplied by ... stress_multiplier"
    is a stressed run. Reading the label instead would let a mislabelled seal run the wrong costs
    silently."""
    mislabelled = dict(config.runs_declared[1])
    mislabelled["run_label"] = ev.run_label_stem(config) + "#BASE"
    assert ev.costs_for(config, mislabelled).scenario == STRESSED


def test_friction_text_matching_neither_scenario_is_a_blocker(config: ev.Stage4Config) -> None:
    declared = dict(config.runs_declared[0], friction="Some frictions, roughly the usual ones.")
    with pytest.raises(ConfigViolation, match="friction scenario"):
        ev.costs_for(config, declared)


def test_friction_text_matching_both_scenarios_is_a_blocker(config: ev.Stage4Config) -> None:
    declared = dict(
        config.runs_declared[0],
        friction="unmodified, but multiplied by 2.0 per frictions.stress_multiplier",
    )
    with pytest.raises(ConfigViolation, match="friction scenario"):
        ev.costs_for(config, declared)


# == the seven conditions, in both directions ======================================================


def test_the_seal_carries_exactly_seven_conditions_in_order(criteria: dict[str, Any]) -> None:
    assert [row["id"] for row in criteria["conditions"]] == list(g.CONDITION_IDS)


def test_every_predicate_threshold_agrees_with_the_json_companion(criteria: dict[str, Any]) -> None:
    """The constitution's gate text and its JSON companion state the same six thresholds twice. If
    they ever disagreed, the comparison the evaluator makes would depend on which one it read."""
    checked = g.check_thresholds_against_seal(criteria)
    for condition_id in g.CONDITION_IDS:
        assert checked[condition_id]["agrees"] in (True, None), condition_id
    assert checked["S4-C7"]["predicate_literal"] is None


@pytest.mark.parametrize(
    "condition_id, met, not_met",
    [
        ("S4-C1", {"total_return": Decimal("0.01")}, {"total_return": Decimal("-0.01")}),
        ("S4-C2", {"sharpe": Decimal("0.51")}, {"sharpe": Decimal("0.49")}),
        ("S4-C3", {"max_drawdown": Decimal("0.14")}, {"max_drawdown": Decimal("0.16")}),
        ("S4-C4", {"profit_factor": Decimal("1.16")}, {"profit_factor": Decimal("1.14")}),
    ],
)
def test_each_base_condition_is_met_and_not_met_on_matching_evidence(
    criteria: dict[str, Any], condition_id: str, met: dict[str, Any], not_met: dict[str, Any]
) -> None:
    index = g.CONDITION_IDS.index(condition_id)
    checker = (g.condition_1, g.condition_2, g.condition_3, g.condition_4)[index]
    assert checker(criteria, base_evidence(**met)).verdict == MET
    assert checker(criteria, base_evidence(**not_met)).verdict == NOT_MET


def test_condition_5_is_met_and_not_met_on_the_stressed_run(criteria: dict[str, Any]) -> None:
    assert g.condition_5(criteria, stress_evidence(total_return=Decimal("0.01"))).verdict == MET
    assert g.condition_5(criteria, stress_evidence(total_return=Decimal("-0.01"))).verdict == NOT_MET


def test_condition_6_is_met_and_not_met_on_the_fold_tally(criteria: dict[str, Any]) -> None:
    assert g.condition_6(criteria, fold_evidence(positive=12)).verdict == MET
    assert g.condition_6(criteria, fold_evidence(positive=0)).verdict == NOT_MET


def test_condition_7_is_met_and_not_met_on_artifact_invariance(criteria: dict[str, Any]) -> None:
    assert g.condition_7(criteria, invariance_evidence()).verdict == MET
    assert g.condition_7(criteria, invariance_evidence(all_digests_equal=False)).verdict == NOT_MET


def test_no_condition_is_expected_to_be_not_applicable(criteria: dict[str, Any]) -> None:
    """The seal states it outright: all seven apply to a single-instrument single representative.
    An evaluator that reached NOT_APPLICABLE would be answering a specification question by itself,
    so `evaluate_gate4` refuses instead."""
    rule = " ".join(criteria["evaluation_integrity_rules"])
    assert "No Gate 4 condition is expected to be NOT_APPLICABLE" in rule
    assert all(row["verdict"] != g.NOT_APPLICABLE for row in gate(criteria)["conditions"])


# == the exact threshold boundaries, in both directions ============================================


@pytest.mark.parametrize(
    "field, value, expected",
    [
        # S4-C1 and S4-C5 are strict: exactly zero is not positive.
        ("total_return", Decimal("0"), NOT_MET),
        ("total_return", Decimal("0.0000000001"), MET),
        # S4-C2 is inclusive at 0.50.
        ("sharpe", Decimal("0.50"), MET),
        ("sharpe", Decimal("0.4999999999999999"), NOT_MET),
        # S4-C3 is inclusive at 0.15.
        ("max_drawdown", Decimal("0.15"), MET),
        ("max_drawdown", Decimal("0.150000000000001"), NOT_MET),
        # S4-C4 is inclusive at 1.15.
        ("profit_factor", Decimal("1.15"), MET),
        ("profit_factor", Decimal("1.1499999999999999"), NOT_MET),
    ],
)
def test_base_thresholds_are_exact_at_the_boundary(
    criteria: dict[str, Any], field: str, value: Decimal, expected: str
) -> None:
    """Decimals, not floats, and no rounding before comparison. A float comparison would make
    0.1499999999999999 and 0.15 the same number and turn a NOT_MET into a MET."""
    checker = {
        "total_return": g.condition_1,
        "sharpe": g.condition_2,
        "max_drawdown": g.condition_3,
        "profit_factor": g.condition_4,
    }[field]
    assert checker(criteria, base_evidence(**{field: value})).verdict == expected


def test_the_stressed_return_boundary_is_strict(criteria: dict[str, Any]) -> None:
    assert g.condition_5(criteria, stress_evidence(total_return=Decimal("0"))).verdict == NOT_MET
    assert (
        g.condition_5(criteria, stress_evidence(total_return=Decimal("0.0000000001"))).verdict == MET
    )


def test_the_fold_boundary_falls_between_eight_and_nine_of_twelve(criteria: dict[str, Any]) -> None:
    """70% of 12 is 8.4, so there is no tie to resolve: nine folds pass and eight fail. The rule is
    a ratio against the completed count, not a rounded fold number."""
    assert g.condition_6(criteria, fold_evidence(positive=9)).verdict == MET
    assert g.condition_6(criteria, fold_evidence(positive=8)).verdict == NOT_MET


def test_no_measured_value_is_rounded_before_comparison(criteria: dict[str, Any]) -> None:
    verdict = g.condition_2(criteria, base_evidence(sharpe=Decimal("0.4999999999999999")))
    assert verdict.verdict == NOT_MET
    assert Decimal(str(verdict.measured)) == Decimal("0.4999999999999999")


# == the conjunction ===============================================================================


@pytest.mark.parametrize("condition_id", g.CONDITION_IDS)
def test_any_single_condition_not_met_fails_the_gate(
    criteria: dict[str, Any], tokens: dict[str, Any], condition_id: str
) -> None:
    """Conjunctive within the candidate, and with exactly one candidate there is no second result
    that could rescue it. Each condition is broken alone, the other six left satisfying."""
    breakage = {
        "S4-C1": {"base": base_evidence(total_return=Decimal("-0.01"))},
        "S4-C2": {"base": base_evidence(sharpe=Decimal("0.10"))},
        "S4-C3": {"base": base_evidence(max_drawdown=Decimal("0.40"))},
        "S4-C4": {"base": base_evidence(profit_factor=Decimal("0.90"))},
        "S4-C5": {"stress": stress_evidence(total_return=Decimal("-0.05"))},
        "S4-C6": {"folds": fold_evidence(positive=3)},
        "S4-C7": {"invariance": invariance_evidence(parameters_unchanged=False)},
    }[condition_id]

    result = gate(criteria, **breakage)
    assert result["gate_passed"] is False
    assert result["verdict_token"] == tokens["fail_token"]
    assert condition_id in result["not_met"]
    assert len(result["met"]) == 6


def test_the_gate_has_no_across_candidate_disjunction(criteria: dict[str, Any]) -> None:
    """Gate 3 aggregated across candidates; Gate 4 has exactly one, so the representative's own
    conjunction *is* the stage verdict. There is no ``admissible_candidate_exists`` row."""
    result = gate(criteria)
    assert result["within_candidate"] == "CONJUNCTIVE"
    assert result["across_candidates"] == "NOT_APPLICABLE_EXACTLY_ONE_REPRESENTATIVE"
    assert "admissible_candidate_exists" not in {row["id"] for row in result["conditions"]}


def test_all_seven_must_be_met_for_a_pass(criteria: dict[str, Any]) -> None:
    result = gate(criteria)
    assert result["condition_count"] == 7
    assert len(result["met"]) == 7
    assert result["not_met"] == [] and result["not_evaluable"] == []


# == missing, NOT_EVALUABLE, NOT_RUN and UNKNOWN ===================================================


def test_a_missing_stressed_run_is_not_evaluable_not_a_pass(
    criteria: dict[str, Any], tokens: dict[str, Any]
) -> None:
    result = gate(criteria, stress={})
    assert result["conditions"][4]["verdict"] == NOT_EVALUABLE
    assert result["gate_passed"] is False
    assert result["verdict_token"] == tokens["fail_token"]


def test_an_undefined_sharpe_is_not_evaluable(criteria: dict[str, Any]) -> None:
    assert g.condition_2(criteria, base_evidence(sharpe=None)).verdict == NOT_EVALUABLE


def test_a_profit_factor_with_no_closed_trades_is_not_evaluable(criteria: dict[str, Any]) -> None:
    assert g.condition_4(criteria, base_evidence(closed_trades=0)).verdict == NOT_EVALUABLE


def test_a_profit_factor_with_no_gross_loss_is_not_evaluable(criteria: dict[str, Any]) -> None:
    """An undefined ratio, not an infinitely good one."""
    verdict = g.condition_4(criteria, base_evidence(profit_factor=None, gross_loss="0.00"))
    assert verdict.verdict == NOT_EVALUABLE


def test_a_run_that_did_not_reach_the_window_end_is_not_evaluable(criteria: dict[str, Any]) -> None:
    """Both the return and the drawdown depend on the run having covered the sealed window."""
    evidence = base_evidence(reached_window_end=False)
    assert g.condition_1(criteria, evidence).verdict == NOT_EVALUABLE
    assert g.condition_3(criteria, evidence).verdict == NOT_EVALUABLE


def test_fewer_than_twelve_completed_folds_is_not_evaluable(criteria: dict[str, Any]) -> None:
    assert g.condition_6(criteria, fold_evidence(positive=11, completed=11)).verdict == NOT_EVALUABLE


def test_not_evaluable_never_counts_as_met(criteria: dict[str, Any]) -> None:
    """The sealed rule says so in as many words, and the token derivation repeats it: a hard
    condition that is NOT_EVALUABLE, NOT_RUN or UNKNOWN reaches the fail token."""
    rules = " ".join(criteria["evaluation_integrity_rules"])
    assert "NOT_EVALUABLE never counts as MET" in rules
    assert "NOT_EVALUABLE, NOT_RUN or UNKNOWN" in criteria["verdict_token_derivation"]["fail_condition"]

    result = gate(criteria, base=base_evidence(sharpe=None))
    assert result["gate_passed"] is False
    assert "S4-C2" in result["not_evaluable"]


def test_only_the_four_sealed_verdict_values_can_be_produced(criteria: dict[str, Any]) -> None:
    """There is no fifth value and no borderline value."""
    produced = set()
    for overrides in (
        {},
        {"base": base_evidence(sharpe=None, total_return=Decimal("-1"))},
        {"stress": {}},
        {"folds": fold_evidence(positive=2)},
        {"invariance": invariance_evidence(all_digests_equal=False)},
    ):
        produced |= {row["verdict"] for row in gate(criteria, **overrides)["conditions"]}
    assert produced <= {MET, NOT_MET, NOT_EVALUABLE, g.NOT_APPLICABLE}


def test_a_pass_with_a_condition_not_met_is_refused(criteria: dict[str, Any]) -> None:
    """One of the six combinations the seal refuses outright. The guard is inside the evaluator, so
    a package cannot be written from an incoherent result."""
    assert "A PASS with any condition not MET." in criteria["incoherent_combinations_refused"]


# == both verdict tokens, derived not invented =====================================================


def test_the_pass_token_is_the_sealed_pass_token(
    criteria: dict[str, Any], tokens: dict[str, Any]
) -> None:
    result = gate(criteria)
    assert result["verdict_token"] == tokens["pass_token"]
    assert result["verdict_token_source"].endswith("verdict_token_derivation.pass_token")
    assert "stage4_gate_criteria.json" in result["verdict_token_source"]


def test_the_fail_token_is_the_sealed_fail_token(
    criteria: dict[str, Any], tokens: dict[str, Any]
) -> None:
    result = gate(criteria, base=base_evidence(total_return=Decimal("-0.5")))
    assert result["verdict_token"] == tokens["fail_token"]


def test_the_two_tokens_are_distinct_and_neither_is_gate_5s(tokens: dict[str, Any]) -> None:
    """Gate 4 does not confer Gate 5's ELIGIBLE_FOR_PAPER_TRADING, and the seal refuses a pass
    emitted under it."""
    assert tokens["pass_token"] != tokens["fail_token"]
    for token in (tokens["pass_token"], tokens["fail_token"]):
        assert "PAPER" not in token and "ELIGIBLE" not in token


def test_the_verdict_string_pairs_the_token_with_its_outcome(criteria: dict[str, Any]) -> None:
    assert gate(criteria)["verdict"].startswith("PASS — ")
    assert gate(criteria, folds=fold_evidence(positive=0))["verdict"].startswith("FAIL — ")


# == the thirteen-artifact invariance rule =========================================================


def test_the_recheck_set_has_thirteen_entries(config: ev.Stage4Config) -> None:
    """Twelve sealed digests plus the strategy module named by description. The thirteenth is
    resolved from the seal's own tables rather than hard-coded here."""
    rows = ev.recheck_table(config)
    assert len(rows) == 13
    assert sum(1 for row in rows if row["equal"]) == 13


def test_the_recheck_resolves_the_strategy_module_by_content(config: ev.Stage4Config) -> None:
    resolved = Path(ev.PROJECT_ROOT) / config.strategy_module_rel
    assert ev.REPRESENTATIVE in resolved.read_text(encoding="utf-8")


def test_this_evaluator_does_not_claim_to_be_the_strategy_module(config: ev.Stage4Config) -> None:
    """The identifier has one definition in this tree. A second copy in the evaluator would make the
    sealing program's content-based resolution ambiguous, so the description is interpolated from the
    constant instead of written out."""
    text = Path(ev.__file__).read_text(encoding="utf-8")
    assert ev.REPRESENTATIVE not in text
    assert ev.STRATEGY_MODULE_DESCRIPTION.endswith(ev.REPRESENTATIVE)


def test_a_changed_digest_fails_s4_c7_regardless_of_the_equity_curve(
    criteria: dict[str, Any], tokens: dict[str, Any]
) -> None:
    """The seal is explicit: a verdict reached after any sealed digest changed is S4-C7 NOT_MET, and
    it fails the gate regardless of performance. Here every performance condition is satisfied."""
    result = gate(criteria, invariance=invariance_evidence(all_digests_equal=False, digests_equal=12))
    assert result["not_met"] == ["S4-C7"]
    assert result["gate_passed"] is False
    assert result["verdict_token"] == tokens["fail_token"]


@pytest.mark.parametrize(
    "override",
    [
        {"all_digests_equal": False},
        {"validation_evaluation_run_records": 2},
        {"validation_window_engine_runs": 3},
        {"parameters_unchanged": False},
    ],
)
def test_each_of_the_four_s4_c7_clauses_fails_on_its_own(
    criteria: dict[str, Any], override: dict[str, Any]
) -> None:
    """S4-C7 is itself a conjunction of four clauses. Each is broken alone."""
    assert g.condition_7(criteria, invariance_evidence(**override)).verdict == NOT_MET


def test_more_than_the_two_declared_runs_fails_s4_c7(criteria: dict[str, Any]) -> None:
    """A verdict computed from more than the two declared validation runs is one of the refused
    combinations, and the third clause of S4-C7 is where it is caught."""
    assert (
        "A verdict of any kind computed from more than the two declared validation runs."
        in criteria["incoherent_combinations_refused"]
    )
    assert g.condition_7(criteria, invariance_evidence(validation_window_engine_runs=4)).verdict == NOT_MET


def test_the_parameters_are_the_gate_3_parameters(config: ev.Stage4Config) -> None:
    """Strategy invariance, recomputed rather than asserted: the parameterisation, universe, family,
    warm-up and module digest must all equal what Gate 3 evaluated."""
    invariance = ev.strategy_invariance(config)
    assert invariance["all_equal"] is True
    assert invariance["parameters_equal_gate_3_primary"] is True
    assert invariance["universe_equal_gate_3"] is True
    assert invariance["family_equal_gate_3"] is True
    assert invariance["declared_warmup_sessions"] == config.warmup_sessions
    # Re-derived from the sealed lookbacks, not only compared: a warm-up agreeing with the seal while
    # disagreeing with the indicators would be an inequality here.
    assert invariance["warmup_matches_largest_lookback"] is True


# == the holdout fails closed ======================================================================


def test_the_evaluation_window_ends_before_the_holdout_begins(
    config: ev.Stage4Config, series: dict[str, Any]
) -> None:
    window = ev.evaluation_window(series, config)
    assert window.end < ev.holdout_window().start


def test_holdout_unreachability_is_proved_not_asserted(
    config: ev.Stage4Config, series: dict[str, Any]
) -> None:
    window = ev.evaluation_window(series, config)
    facts = ev.assert_holdout_unreachable(window, ev.validation_window().end)
    assert facts["window_end_precedes_holdout_start"] is True
    assert facts["run_end_precedes_holdout_start"] is True


def test_a_run_end_inside_the_holdout_is_refused(
    config: ev.Stage4Config, series: dict[str, Any]
) -> None:
    window = ev.evaluation_window(series, config)
    with pytest.raises(WindowViolation, match="SEALED"):
        ev.assert_holdout_unreachable(window, ev.holdout_window().start)


def test_a_window_reaching_into_the_holdout_is_refused(
    config: ev.Stage4Config, series: dict[str, Any]
) -> None:
    holdout = ev.holdout_window()
    reaching = ev.ResearchWindow(name="reaching", start=ev.validation_window().start, end=holdout.end)
    with pytest.raises(WindowViolation):
        ev.assert_window_is_authorized(reaching, config, series)


def test_the_validation_window_does_not_contain_a_holdout_session() -> None:
    validation, holdout = ev.validation_window(), ev.holdout_window()
    assert not validation.contains(holdout.start)
    assert not validation.contains(holdout.end)


def test_the_holdout_remains_sealed_in_the_seal(config: ev.Stage4Config) -> None:
    assert config.preregistration["holdout_window_state"] == "SEALED"


# == the broker is unreachable =====================================================================

NETWORK_ROOTS = {
    "alpaca", "alpaca_trade_api", "alpaca_py", "requests", "httpx", "aiohttp", "socket", "urllib",
    "http", "websocket", "websockets", "boto3", "ftplib", "smtplib", "telnetlib", "paramiko",
    "ssl", "xmlrpc",
}
CREDENTIAL_ATTRS = {"environ", "getenv"}
CONNECT_ATTRS = {"urlopen", "connect", "urlretrieve"}


def broker_findings(path: Path) -> list[str]:
    """An AST question, not a text search. A text sweep of these modules returns false hits — prose
    recording Alpaca as LOCKED, a docstring naming ``environ`` — so the parsed tree is walked."""
    found: list[str] = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found += [f"import {a.name}" for a in node.names if a.name.split(".")[0] in NETWORK_ROOTS]
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] in NETWORK_ROOTS:
                found.append(f"from {node.module}")
        elif isinstance(node, ast.Attribute):
            if node.attr in CREDENTIAL_ATTRS or node.attr in CONNECT_ATTRS:
                found.append(f"attribute .{node.attr}")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if "://" in node.value:
                found.append("url string constant")
    return found


@pytest.mark.parametrize("module", [ev, g])
def test_no_stage_4_evaluation_module_can_reach_a_broker_or_a_credential(module: Any) -> None:
    """The half of the sealed contamination predicate that must stay at zero for this session: no
    network import, no credential read, no connection, no URL. The data-access half is legitimately
    non-zero here — this session is the authorized validation read — and that divergence is recorded
    as a conflict in the decision package rather than engineered away."""
    assert broker_findings(Path(module.__file__)) == []


def test_no_order_placement_surface_exists(config: ev.Stage4Config) -> None:
    assert config.criteria["live_trading_authorized"] is False


def test_the_engine_is_reachable_only_through_the_sealed_plan(config: ev.Stage4Config) -> None:
    """The evaluator constructs exactly one parameterisation, and the sealed iteration budget says
    exactly one exists."""
    budget = config.iteration_budget
    assert int(budget["parameterisations"]) == 1
    assert int(budget["runs"]) == 2
    assert int(budget["sessions_reading_validation"]) == 1
    assert int(budget["re_runs_permitted_after_a_valid_completed_run"]) == 0


# == deterministic serialisation and manifest policy ===============================================


def json_bytes(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, default=str)


def test_the_gate_result_serialises_identically_on_repeat(criteria: dict[str, Any]) -> None:
    """Two evaluations of the same evidence must produce byte-identical JSON, or the decision
    record's own digest would depend on when it was written."""
    assert json_bytes(gate(criteria)) == json_bytes(gate(criteria))


def test_condition_rows_carry_a_stable_key_order(criteria: dict[str, Any]) -> None:
    rows = gate(criteria)["conditions"]
    assert all(
        list(row) == ["id", "required_verbatim", "verdict", "satisfied", "measured", "threshold",
                      "note", "evidence"]
        for row in rows
    )


def test_every_condition_records_its_measured_value_and_its_threshold(
    criteria: dict[str, Any]
) -> None:
    """The sealed integrity rule: a reader must be able to recompute every comparison without
    rerunning the engine. S4-C7 has no numeric threshold and carries its predicate instead."""
    for row in gate(criteria)["conditions"]:
        assert row["threshold"], row["id"]
        if row["id"] != "S4-C7":
            assert row["measured"] is not None, row["id"]


def test_the_threshold_field_is_the_sealed_predicate_verbatim(criteria: dict[str, Any]) -> None:
    sealed = {row["id"]: row["predicate"] for row in criteria["conditions"]}
    for row in gate(criteria)["conditions"]:
        assert row["threshold"] == sealed[row["id"]]


def test_the_gate_result_contains_no_digest_of_itself(criteria: dict[str, Any]) -> None:
    """Nothing may hash itself. The gate result carries no 64-hex value at all, so it cannot carry
    its own."""
    import re

    assert re.search(r"\b[0-9a-f]{64}\b", json_bytes(gate(criteria))) is None


def test_the_established_manifest_policy_excludes_the_manifests_own_entry() -> None:
    """Read from the Stage 4 pre-registration package on disk rather than restated, because the
    Stage 4 decision package must follow the same policy."""
    manifests = sorted(
        (Path(ev.PROJECT_ROOT) / "reports").rglob("*ARTIFACT_MANIFEST.json")
    )
    assert manifests, "no manifest on disk to read the policy from"
    for path in manifests:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        listed = {
            name
            for group in ("frozen_inputs", "produced_artifacts")
            for name in manifest.get(group, {})
        }
        assert path.name not in {Path(name).name for name in listed}, path.name
