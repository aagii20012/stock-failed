"""Stage 3 — one injected defect per guard, and the guard that must catch it.

The Stage 3 result is a FAIL, and a FAIL is the cheapest verdict for a broken evaluator to produce
by accident. So the burden here runs in both directions: the controls at the top prove the clean
path admits a candidate and loads a clean seal, and every test below them injects exactly one defect
and asserts exactly the guard the sealed rule names. A file that only did the second half would pass
against an evaluator that refuses everything, which is precisely the failure mode a rejecting stage
cannot otherwise rule out.

Defects are injected three ways, and never in place:

* into a ``copy.deepcopy`` of a loaded sealed dict, so ``config/`` is never written;
* into a copy of the sealed tree under ``tmp_path``, with ``stage3_config.PROJECT_ROOT`` and
  ``stage3_config.PREREGISTRATION_JSON`` both redirected — both, because the second is an absolute
  module constant and redirecting only the first leaves the loader reading the real seal;
* through ``monkeypatch`` on a module attribute.

Nothing here loads the price dataset. Every guard tested below fires before the data is read, which
is the property that makes them worth having: a run that is going to be refused is refused before it
spends thirty backtests earning the right to be refused.
"""

from __future__ import annotations

import copy
import datetime as dt
import shutil
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from stockedge100.backtest.config import load_stage2_config
from stockedge100.backtest.costs import BASE, ZERO, CostModel
from stockedge100.backtest.dataset import series_from_rows
from stockedge100.backtest.engine import BacktestResult, EquityPoint
from stockedge100.backtest.errors import ConfigViolation, LookAheadError, WindowViolation
from stockedge100.backtest.market import MarketView
from stockedge100.backtest.portfolio import Trade
from stockedge100.backtest.window import ResearchWindow
from stockedge100.reporting import stage3_evidence
from stockedge100.strategies import config as stage3_config
from stockedge100.strategies import families, gate, harness, runner

MONTHLY_REBALANCE = "last XNYS session of each calendar month"

#: The three files the seal lists, and therefore the three the loader recomputes. The seal record
#: itself is absent because nothing may hash itself.
SEALED_RELS = (
    "config/stage3_gate_criteria.json",
    "config/stage3_strategy_protocol.json",
    "governance/STAGE_3_PREREGISTRATION.md",
)

SEAL_RELS = (
    "governance/STAGE_3_PREREGISTRATION.json",
    "governance/STAGE_3_PREREGISTRATION.sha256",
)

DAY_ZERO = dt.date(2000, 1, 3)

WIDE = ResearchWindow(name="test", start=dt.date(1990, 1, 1), end=dt.date(2030, 12, 31))


# -- fixtures and hand-built objects ---------------------------------------------------------------


@pytest.fixture(scope="module")
def stage3():
    return stage3_config.load_stage3_config()


@pytest.fixture(scope="module")
def criteria(stage3):
    return stage3.criteria


@pytest.fixture(scope="module")
def costs() -> CostModel:
    return CostModel(load_stage2_config().cost_model, BASE)


@pytest.fixture
def sealed_tree(tmp_path: Path, monkeypatch, project_root: Path) -> Path:
    """A byte-for-byte copy of the sealed tree, with the loader pointed at it.

    Both module constants are redirected. ``PREREGISTRATION_JSON`` is resolved at import time from
    the real ``PROJECT_ROOT``, so redirecting the root alone would leave every test below comparing a
    copied file against the genuine seal — which passes for the wrong reason.
    """

    for rel in SEALED_RELS + SEAL_RELS:
        destination = tmp_path / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(project_root / rel, destination)
    monkeypatch.setattr(stage3_config, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        stage3_config, "PREREGISTRATION_JSON", tmp_path / "governance/STAGE_3_PREREGISTRATION.json"
    )
    return tmp_path


def trade(pnl: str, *, symbol: str = "SPY", index: int = 0) -> Trade:
    entry = Decimal(100)
    return Trade(
        symbol=symbol,
        entry_session=DAY_ZERO + dt.timedelta(days=2 * index),
        exit_session=DAY_ZERO + dt.timedelta(days=2 * index + 1),
        quantity=Decimal(1),
        entry_cash=entry,
        exit_cash=entry + Decimal(pnl),
        dividends=ZERO,
        entry_costs=ZERO,
        exit_costs=ZERO,
    )


def result(
    *,
    pnls: list[str] | None = None,
    equity: list[str] | None = None,
    starting: str = "100",
    symbols: tuple[str, ...] = ("SPY",),
    trades: list[Trade] | None = None,
) -> BacktestResult:
    """A :class:`BacktestResult` assembled by hand — the five fields the gate reads, and no engine."""

    if trades is None:
        trades = [trade(value, index=i) for i, value in enumerate(pnls or [])]
    if equity is None:
        equity = [starting]
        running = Decimal(starting)
        for item in trades:
            running += item.pnl
            equity.append(f"{running:f}")
    points = [
        EquityPoint(
            session=DAY_ZERO + dt.timedelta(days=i),
            cash=Decimal(value),
            equity=Decimal(value),
            stale_mark=False,
            position_count=0,
        )
        for i, value in enumerate(equity)
    ]
    return BacktestResult(
        label="synthetic",
        scenario=BASE,
        symbols=symbols,
        start=points[0].session,
        end=points[-1].session,
        equity_curve=points,
        fills=[],
        rejections=[],
        trades=list(trades),
        dividend_events=[],
        stale_marks=0,
        shutdown_session=None,
        starting_equity=Decimal(starting),
        final_cash=Decimal(equity[-1]),
        final_equity=Decimal(equity[-1]),
        open_positions=[],
        cost_model={},
    )


def plan(universe: tuple[str, ...] = ("SPY",)) -> runner.CandidatePlan:
    return runner.CandidatePlan(
        experiment_id="SE100-S3-TEST",
        family="test",
        declared_universe=universe,
        warmup_sessions=1,
        effective_warmup=1,
        run_start=DAY_ZERO,
        run_end=DAY_ZERO + dt.timedelta(days=10),
        binding_symbol=universe[0],
        variants=(),
        all_symbols=universe,
    )


def neighbour(index: int, total_return: str | None):
    spec = runner.VariantSpec(
        experiment_id="SE100-S3-TEST",
        variant_id=f"SE100-S3-TEST#N{index}",
        role=runner.NEIGHBOUR,
        index=index,
        universe=("SPY",),
        parameters={"sma_long": 100 + index},
        symbols=("SPY",),
    )
    if total_return is None:
        return spec, None
    final = Decimal(100) * (Decimal(1) + Decimal(total_return))
    return spec, result(equity=["100", f"{final:f}"])


def admissible() -> BacktestResult:
    """Twenty wins of +2 then ten losses of -1, one instrument.

    Return 0.30; drawdown 10/140 = 0.0714; profit factor 40/10 = 4; thirty closed trades; removing
    the best trade still leaves 1.3/1.02 - 1 > 0 ; a single instrument makes S3-C6 not applicable.
    """

    return result(pnls=["2"] * 20 + ["-1"] * 10)


def synthetic_series(symbol: str, closes: dict[dt.date, str]):
    rows = [
        {"session": session.isoformat(), "open": close, "close": close, "split_ratio": "1"}
        for session, close in sorted(closes.items())
    ]
    return series_from_rows(symbol, rows)


# == controls ======================================================================================
#
# Three clean paths. A failure anywhere below is attributable to the injected defect only if these
# pass first.


def test_control_the_sealed_configuration_loads_and_recomputes_three_digests(sealed_tree: Path):
    config = stage3_config.load_stage3_config()
    assert sorted(config.digests) == sorted(SEALED_RELS)
    assert gate.check_thresholds_against_seal(config.criteria) is None


def test_control_a_clean_candidate_is_admitted(criteria):
    verdicts = gate.evaluate_candidate(
        plan=plan(),
        primary=admissible(),
        neighbours=[neighbour(i, "0.2") for i in range(1, 5)],
        criteria=criteria,
    )
    assert verdicts["admitted"] is True
    assert verdicts["conditions_not_met"] == []
    assert verdicts["conditions_not_evaluable"] == []
    assert gate.stage_verdict([verdicts], criteria)["verdict"] == "PASS"


def test_control_every_sealed_experiment_builds(stage3, costs):
    for experiment in stage3.experiments:
        for spec in runner.variant_specs(experiment):
            candidate = families.build_candidate(
                experiment_id=spec.experiment_id,
                variant_id=spec.variant_id,
                universe=spec.universe,
                parameters=spec.parameters,
                costs=costs,
                indicator_definitions=stage3.indicator_definitions,
            )
            assert candidate.variant_id == spec.variant_id


# == the seal ======================================================================================


def test_a_tampered_sealed_parameter_file_is_refused(sealed_tree: Path):
    """One byte inside the criteria file. The claim Stage 3 rests on is that the parameters predate
    the code; a single altered digit falsifies it exactly as a rewritten file would."""

    path = sealed_tree / "config/stage3_gate_criteria.json"
    text = path.read_text(encoding="utf-8")
    assert '"profit_factor_min": 1.1' in text
    path.write_text(text.replace('"profit_factor_min": 1.1', '"profit_factor_min": 1.0'), "utf-8")

    with pytest.raises(ConfigViolation) as excinfo:
        stage3_config.load_stage3_config()
    assert "has changed since it was sealed" in str(excinfo.value)
    assert "config/stage3_gate_criteria.json" in str(excinfo.value)


def test_a_tampered_sealed_prose_file_is_refused(sealed_tree: Path):
    """The Markdown is sealed too. A loader that only recomputed the JSONs would let the human-read
    statement of the protocol drift away from the machine-read one."""

    path = sealed_tree / "governance/STAGE_3_PREREGISTRATION.md"
    path.write_text(path.read_text(encoding="utf-8").replace("Stage 3", "Stage 3 "), "utf-8")

    with pytest.raises(ConfigViolation) as excinfo:
        stage3_config.load_stage3_config()
    assert "governance/STAGE_3_PREREGISTRATION.md" in str(excinfo.value)


def test_a_deleted_sealed_file_is_drift_not_a_silent_skip(sealed_tree: Path):
    (sealed_tree / "governance/STAGE_3_PREREGISTRATION.md").unlink()

    with pytest.raises(ConfigViolation) as excinfo:
        stage3_config.load_stage3_config()
    assert "governance/STAGE_3_PREREGISTRATION.md: MISSING" in str(excinfo.value)


def test_an_unsealed_parameter_file_cannot_be_used(sealed_tree: Path, monkeypatch):
    """The file loads and parses; it is simply not the one that was sealed."""

    unsealed = sealed_tree / "config/stage3_strategy_protocol_v2.json"
    shutil.copy2(sealed_tree / "config/stage3_strategy_protocol.json", unsealed)
    monkeypatch.setattr(stage3_config, "PROTOCOL_REL", "config/stage3_strategy_protocol_v2.json")

    with pytest.raises(ConfigViolation) as excinfo:
        stage3_config.load_stage3_config()
    assert "is not listed in STAGE_3_PREREGISTRATION.json" in str(excinfo.value)
    assert "cannot be used to produce Gate 3 evidence" in str(excinfo.value)


def test_a_missing_parameter_file_stops_the_run(sealed_tree: Path):
    (sealed_tree / "config/stage3_strategy_protocol.json").unlink()

    with pytest.raises(ConfigViolation) as excinfo:
        stage3_config.load_stage3_config()
    assert "sealed Stage 3 configuration is missing" in str(excinfo.value)


def test_strategy_code_will_not_run_without_the_seal(sealed_tree: Path):
    (sealed_tree / "governance/STAGE_3_PREREGISTRATION.json").unlink()

    with pytest.raises(ConfigViolation) as excinfo:
        stage3_config.load_stage3_config()
    assert "pre-registration record is missing" in str(excinfo.value)
    assert "may not run without the seal that fixes its parameters" in str(excinfo.value)


def test_nothing_that_produces_evidence_bypasses_the_seal(project_root: Path):
    """``require_seal=False`` exists for tooling that predates the seal. Its only occurrence must be
    its own definition — any caller passing it would be producing Gate 3 evidence from parameters
    nobody committed to in advance."""

    offenders = [
        path.relative_to(project_root).as_posix()
        for path in sorted((project_root / "src").rglob("*.py"))
        if "require_seal=False" in path.read_text(encoding="utf-8")
        and path.name != "config.py"
    ]
    assert offenders == []


# == threshold drift in the evaluator ==============================================================
#
# ``check_thresholds_against_seal`` is the guard that stops the evaluator from applying a constant
# the seal no longer carries. It runs first inside ``evaluate_candidate``, so each defect below is
# asserted through the full evaluation, not against the checker in isolation.


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("profit_factor_min", 1.2),
        ("max_drawdown_pct", 20),
        ("closed_trades_min", 10),
        ("net_return_positive", False),
        ("best_trade_removed_return_positive", False),
    ],
)
def test_a_drifted_threshold_refuses_to_evaluate_anything(criteria, key, value):
    drifted = copy.deepcopy(criteria)
    drifted["frozen_gate_json_companion_verbatim"]["thresholds"][key] = value

    with pytest.raises(ConfigViolation) as excinfo:
        gate.evaluate_candidate(
            plan=plan(),
            primary=admissible(),
            neighbours=[neighbour(i, "0.2") for i in range(1, 5)],
            criteria=drifted,
        )
    assert f"sealed threshold {key}=" in str(excinfo.value)
    assert "the seal governs, so stop and report it" in str(excinfo.value)


def test_a_loosened_concentration_predicate_is_refused(criteria):
    """S3-C6's 0.50 lives only in the sealed prose, so the evaluator's constant is checked against
    the predicate string. Loosening the prose without loosening the constant must not pass."""

    drifted = copy.deepcopy(criteria)
    for entry in drifted["conditions"]:
        if entry["id"] == "S3-C6":
            entry["predicate"] = entry["predicate"].replace("0.50", "0.75")

    with pytest.raises(ConfigViolation) as excinfo:
        gate.check_thresholds_against_seal(drifted)
    assert "does not carry the concentration limit 0.50" in str(excinfo.value)


def test_the_lower_frequency_exception_may_not_be_switched_on(criteria):
    """S3-C4's thirty-trade floor has a sealed exception recorded as not invoked. Flipping that flag
    is the cheapest way to admit a candidate with too few trades, so it is refused outright."""

    drifted = copy.deepcopy(criteria)
    for entry in drifted["conditions"]:
        if entry["id"] == "S3-C4":
            entry["exception_invoked"] = True

    with pytest.raises(ConfigViolation) as excinfo:
        gate.check_thresholds_against_seal(drifted)
    assert "lower-frequency exception is recorded as invoked; it is not" in str(excinfo.value)


def test_a_deleted_condition_is_not_a_condition_that_passes(criteria):
    """Six of seven is not a gate. Removing a condition's spec must stop the evaluation rather than
    leave the candidate judged on what remains."""

    drifted = copy.deepcopy(criteria)
    drifted["conditions"] = [e for e in drifted["conditions"] if e["id"] != "S3-C2"]

    with pytest.raises(ConfigViolation) as excinfo:
        gate.evaluate_candidate(
            plan=plan(),
            primary=admissible(),
            neighbours=[neighbour(i, "0.2") for i in range(1, 5)],
            criteria=drifted,
        )
    assert "sealed criteria carry no condition 'S3-C2'" in str(excinfo.value)


# == the gate's own combination rule ===============================================================


def test_a_fifth_verdict_value_cannot_be_constructed():
    """"There is no fifth value and no borderline value.""" ""

    with pytest.raises(ConfigViolation) as excinfo:
        gate.ConditionVerdict("S3-C1", "verbatim", "BORDERLINE")
    assert "is not one of the four sealed verdict values" in str(excinfo.value)


def test_one_injected_failure_rejects_the_whole_candidate(criteria):
    """Conjunction within a candidate. The primary below differs from :func:`admissible` in one
    respect only — the ten losses are -3 rather than -1, so the drawdown is 30/140 = 0.2143 instead
    of 10/140 — and S3-C2 is the only condition that changes. Ten losses of -2 would *not* do: that
    is 20/140 = 0.1429, still inside the ceiling.

    Everything else still holds, which is what makes the failure attributable: the return is
    110/100 - 1 = 0.10, the profit factor is 40/30 = 1.33, there are still thirty closed trades, and
    removing the best trade leaves 1.10/1.02 - 1 > 0.
    """

    injected = result(pnls=["2"] * 20 + ["-3"] * 10)
    verdicts = gate.evaluate_candidate(
        plan=plan(),
        primary=injected,
        neighbours=[neighbour(i, "0.2") for i in range(1, 5)],
        criteria=criteria,
    )
    assert verdicts["conditions_not_met"] == ["S3-C2"]
    assert verdicts["admitted"] is False
    assert gate.stage_verdict([verdicts], criteria)["verdict"] == "FAIL"


def test_a_candidate_that_never_traded_is_refused_not_excused(criteria):
    """Constitution §9: "NOT_RUN, UNKNOWN, or missing evidence is not a pass."

    A rule whose entry condition never fires produces no drawdown, and a gate that read silence as
    success would admit it on S3-C2 alone. Three conditions are undefined here rather than failed —
    a one-point equity curve, no closed trades, fewer than two trades to remove one from — and each
    is recorded as NOT_EVALUABLE and counted against the candidate.
    """

    verdicts = gate.evaluate_candidate(
        plan=plan(),
        primary=result(pnls=[]),
        neighbours=[neighbour(i, "0.2") for i in range(1, 5)],
        criteria=criteria,
    )
    assert verdicts["conditions_not_evaluable"] == ["S3-C1", "S3-C3", "S3-C5"]
    assert verdicts["conditions_not_met"] == ["S3-C4", "S3-C7"]
    assert verdicts["conditions_met"] == 1  # S3-C2: a flat curve has no drawdown.
    assert verdicts["admitted"] is False


def test_no_losing_trade_is_met_by_the_seal_not_undefined(criteria):
    """The severity the seal states, not the one that reads better. An undefined profit factor with
    positive gross profit is sealed as MET — "UNDEFINED_NO_LOSSES_TREATED_AS_MET" — and asserting
    NOT_EVALUABLE here because it feels more rigorous would be asserting a rule nobody sealed."""

    verdict = gate.condition_3(result(pnls=["2"] * 30), criteria)
    assert verdict.verdict == gate.MET
    assert verdict.measured is None
    assert verdict.note.startswith("UNDEFINED_NO_LOSSES_TREATED_AS_MET: ")


def test_an_unrun_neighbour_cannot_be_quietly_dropped(criteria):
    """A neighbour that did not run is the missing evidence §9 names. It fails S3-C7 and is listed
    by name, so the omission is visible in the evidence rather than absorbed into a 3/4."""

    verdict = gate.condition_7(
        admissible(),
        [neighbour(1, "0.2"), neighbour(2, "0.2"), neighbour(3, "0.2"), neighbour(4, None)],
        criteria,
    )
    assert verdict.verdict == gate.NOT_MET
    assert verdict.evidence["neighbours_not_run"] == ["SE100-S3-TEST#N4"]
    assert verdict.measured == "3/4 neighbours match"


@pytest.mark.parametrize("count", [3, 5])
def test_a_neighbour_count_other_than_four_is_refused(criteria, count):
    """The seal declares four neighbours per candidate. Three would weaken the sign-stability
    condition; five would mean a variant was added after the seal."""

    with pytest.raises(ConfigViolation) as excinfo:
        gate.condition_7(
            admissible(), [neighbour(i, "0.2") for i in range(1, count + 1)], criteria
        )
    assert f"S3-C7 expects exactly four sealed neighbours; {count} were supplied" in str(excinfo.value)


# == the iteration budget ==========================================================================


def test_an_extra_neighbour_breaks_the_sealed_run_count(stage3):
    """``total_declared_runs`` is 30 and ``revisions_permitted`` is 0. The harness compares the runs
    it executed against that figure, so an experiment that grew a variant is caught by arithmetic
    rather than by anyone noticing."""

    declared = int(stage3.protocol["iteration_budget"]["total_declared_runs"])
    experiments = copy.deepcopy(stage3.experiments)
    assert sum(len(runner.variant_specs(e)) for e in experiments) == declared

    experiments[0]["robustness_neighbours"].append({"sma_long": 175})
    assert sum(len(runner.variant_specs(e)) for e in experiments) == declared + 1


# == the run window ================================================================================


def test_the_harness_refuses_any_window_but_development(monkeypatch):
    """Gate 3 is a development-window stage. The refusal happens before the dataset is loaded, so a
    misconfigured window costs nothing and cannot leave a partially-read validation series behind."""

    monkeypatch.setattr(
        harness,
        "development_window",
        lambda: ResearchWindow(name="validation", start=dt.date(2021, 8, 1), end=dt.date(2023, 12, 29)),
    )
    with pytest.raises(ConfigViolation) as excinfo:
        harness.run_all()
    assert "may read the development window only" in str(excinfo.value)
    assert "'validation'" in str(excinfo.value)


def test_a_view_cannot_be_built_outside_its_window():
    series = {"SPY": synthetic_series("SPY", {dt.date(2000, 1, 3): "100"})}
    window = ResearchWindow(name="development", start=dt.date(1993, 1, 29), end=dt.date(2021, 7, 31))

    with pytest.raises(WindowViolation):
        MarketView(series, dt.date(2021, 8, 2), window)


def test_a_session_inside_the_bound_but_outside_the_window_raises():
    """Two guards sit in front of a price, and this defect passes the first one. The session is in
    the past relative to the visibility bound, so it is not look-ahead; it is outside the window,
    which is what the holdout lock exists to refuse."""

    series = {
        "SPY": synthetic_series(
            "SPY", {dt.date(1993, 1, 4): "100", dt.date(1993, 2, 1): "101"}
        )
    }
    window = ResearchWindow(name="development", start=dt.date(1993, 1, 29), end=dt.date(2021, 7, 31))
    view = MarketView(series, dt.date(1993, 2, 1), window)

    assert view.close("SPY", dt.date(1993, 2, 1)) == Decimal(101)
    with pytest.raises(WindowViolation):
        view.close("SPY", dt.date(1993, 1, 4))


def test_reading_past_the_visibility_bound_raises():
    series = {
        "SPY": synthetic_series("SPY", {dt.date(2000, 1, 3): "100", dt.date(2000, 1, 4): "110"})
    }
    view = MarketView(series, dt.date(2000, 1, 3), WIDE)

    assert view.close("SPY", dt.date(2000, 1, 3)) == Decimal(100)
    with pytest.raises(LookAheadError):
        view.close("SPY", dt.date(2000, 1, 4))


def test_a_view_refuses_to_have_its_bound_moved():
    """The bound is the whole guarantee. Rebinding it would be the one edit that turns every later
    read from look-ahead into a legal one."""

    series = {"SPY": synthetic_series("SPY", {dt.date(2000, 1, 3): "100"})}
    view = MarketView(series, dt.date(2000, 1, 3), WIDE)

    with pytest.raises(LookAheadError):
        view._as_of = dt.date(2020, 1, 3)


# == planning a candidate ==========================================================================


def test_a_warmup_that_disagrees_with_the_seal_stops_the_plan(stage3):
    experiment = copy.deepcopy(stage3.experiment("SE100-S3-F1-TREND-SMA200"))
    experiment["warmup_sessions"] = 200

    with pytest.raises(ConfigViolation) as excinfo:
        runner.plan_candidate(experiment, WIDE, {}, stage3.indicator_definitions)
    assert "sealed warmup_sessions=200" in str(excinfo.value)
    assert "consumes 250 visible bars" in str(excinfo.value)
    assert "report the discrepancy rather than adjusting either" in str(excinfo.value)


def test_warmup_reads_the_neighbours_not_only_the_primary(stage3):
    """F1's primary uses SMA(200); its widest neighbour uses SMA(250), and the sealed warm-up is
    250. Dropping that neighbour is the defect a primary-only reading of the warm-up rule would not
    notice — and it would silently start every F1 run fifty sessions early."""

    experiment = copy.deepcopy(stage3.experiment("SE100-S3-F1-TREND-SMA200"))
    assert runner.largest_lookback(
        runner.variant_specs(experiment), stage3.indicator_definitions
    ) == 250

    experiment["robustness_neighbours"] = [
        n for n in experiment["robustness_neighbours"] if n.get("sma_long") != 250
    ]
    assert runner.largest_lookback(
        runner.variant_specs(experiment), stage3.indicator_definitions
    ) == 225
    with pytest.raises(ConfigViolation):
        runner.plan_candidate(experiment, WIDE, {}, stage3.indicator_definitions)


def test_run_start_refuses_a_symbol_whose_series_was_not_loaded():
    series = {"SPY": synthetic_series("SPY", {DAY_ZERO: "100"})}

    with pytest.raises(ConfigViolation) as excinfo:
        runner.run_start_for(["SPY", "EFA"], 1, WIDE, series)
    assert "run start needs EFA but its series was not loaded" in str(excinfo.value)


def test_run_start_refuses_a_universe_with_too_little_history():
    closes = {DAY_ZERO + dt.timedelta(days=i): "100" for i in range(3)}
    series = {"SPY": synthetic_series("SPY", closes)}

    assert runner.run_start_for(["SPY"], 3, WIDE, series)[0] == DAY_ZERO + dt.timedelta(days=2)
    with pytest.raises(ConfigViolation) as excinfo:
        runner.run_start_for(["SPY"], 4, WIDE, series)
    assert "SPY has only 3 sessions inside test; 4 are required" in str(excinfo.value)


def test_run_start_refuses_an_empty_universe():
    with pytest.raises(ConfigViolation) as excinfo:
        runner.run_start_for([], 1, WIDE, {})
    assert "run start requested for an empty universe" in str(excinfo.value)


def test_an_excluded_symbol_cannot_be_pulled_back_into_the_run(stage3):
    """The seal excludes AAPL by name and no experiment requires it, so the overlap is empty. Adding
    a required symbol to the exclusion list makes the protocol self-contradictory, and a loader that
    resolved the contradiction either way would be choosing for the seal."""

    protocol = copy.deepcopy(stage3.protocol)
    assert "SPY" in runner.required_symbols(stage3)
    protocol["excluded_symbols"]["SPY"] = "injected defect"

    with pytest.raises(ConfigViolation) as excinfo:
        runner.load_required_dataset(replace(stage3, protocol=protocol))
    assert "sealed protocol both requires and excludes ['SPY']" in str(excinfo.value)


# == the family implementations ====================================================================


def test_an_experiment_with_no_implementation_is_refused(costs, stage3):
    with pytest.raises(ConfigViolation) as excinfo:
        families.build_candidate(
            experiment_id="SE100-S3-F7-NEURAL-NET",
            variant_id="SE100-S3-F7-NEURAL-NET#PRIMARY",
            universe=("SPY",),
            parameters={},
            costs=costs,
            indicator_definitions=stage3.indicator_definitions,
        )
    assert "no implementation registered for sealed experiment" in str(excinfo.value)


def test_rotation_refuses_to_hold_more_than_one_risky_position(costs, stage3):
    """Constitution §3 permits one open risky position. ``top_n`` is the single parameter that would
    breach it, and it is refused at construction rather than at the second order."""

    with pytest.raises(ConfigViolation) as excinfo:
        families.build_candidate(
            experiment_id="SE100-S3-F5-ROTATION-DUALMOM",
            variant_id="SE100-S3-F5-ROTATION-DUALMOM#INJECTED",
            universe=("SPY", "MDY", "EFA", "IEF"),
            parameters={
                "momentum_lookback": 252,
                "rebalance": MONTHLY_REBALANCE,
                "top_n": 2,
            },
            costs=costs,
            indicator_definitions=stage3.indicator_definitions,
        )
    assert "top_n=2 exceeds the sealed cost model's one open risky position" in str(excinfo.value)


def test_rotation_refuses_a_rebalance_rule_it_does_not_implement(costs, stage3):
    """The calendar is what makes the rebalance date free of look-ahead. A rule this class cannot
    honour is refused rather than approximated by the monthly one."""

    with pytest.raises(ConfigViolation) as excinfo:
        families.build_candidate(
            experiment_id="SE100-S3-F5-ROTATION-DUALMOM",
            variant_id="SE100-S3-F5-ROTATION-DUALMOM#INJECTED",
            universe=("SPY", "MDY", "EFA", "IEF"),
            parameters={
                "momentum_lookback": 252,
                "rebalance": "whenever the ranking changes",
                "top_n": 1,
            },
            costs=costs,
            indicator_definitions=stage3.indicator_definitions,
        )
    assert "unsupported sealed rebalance rule" in str(excinfo.value)


# == the evidence file =============================================================================


@pytest.fixture(scope="module")
def evidence(project_root: Path):
    import json

    path = project_root / "reports/stage3/STAGE_3_DEVELOPMENT_ADMISSIBILITY.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_control_the_written_evidence_recomputes_to_its_own_digest(evidence):
    assert stage3_evidence.evidence_digest(evidence) == evidence["evidence_digest"]


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(lambda b: b["stage_verdict"].update(verdict="PASS"), id="stage-verdict"),
        pytest.param(lambda b: b.update(live_trading_authorized=True), id="live-authorization"),
        pytest.param(
            lambda b: b["candidates"][0]["gate"]["conditions"][1].update(verdict="MET", satisfied=True),
            id="one-condition-verdict",
        ),
        pytest.param(
            lambda b: b["gate_summary"][0].update(admitted=True, conditions_not_met=[]),
            id="gate-summary",
        ),
        pytest.param(
            lambda b: b["sealed_inputs"]["digests_recomputed_at_load"].update(
                **{"config/stage3_gate_criteria.json": "0" * 64}
            ),
            id="recorded-seal-digest",
        ),
    ],
)
def test_a_tampered_finding_changes_the_evidence_digest(evidence, mutate):
    """Every one of these is an edit that would turn a rejection into an admission on the page. The
    digest covers the findings, so none of them survives a recomputation."""

    tampered = copy.deepcopy(evidence)
    mutate(tampered)
    assert stage3_evidence.evidence_digest(tampered) != evidence["evidence_digest"]


def test_restamping_the_evidence_does_not_change_its_digest(evidence):
    """The negative control for the test above. ``generated_utc`` is excluded by name, so a rerun at
    a different clock time produces the same digest — which is what makes a *changed* digest mean a
    changed finding rather than a changed minute."""

    restamped = copy.deepcopy(evidence)
    restamped["generated_utc"] = "1970-01-01T00:00:00Z"
    assert stage3_evidence.evidence_digest(restamped) == evidence["evidence_digest"]
