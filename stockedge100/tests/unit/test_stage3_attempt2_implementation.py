"""Stage 3 Attempt 2 — unit and property tests for the sealed implementation.

Every assertion here traces to a sealed rule in `SE100-CFG-3003`
(`config/stage3_attempt2_strategy_protocol.json`), `SE100-CFG-3004`
(`config/stage3_attempt2_gate_criteria_binding.json`) or `SE100-CFG-3002`
(`config/stage3_gate_criteria.json`, adopted unchanged by Attempt 2). The sealed artifact
governs: where a docstring paraphrases, the assertion reads the file.

No test in this module loads a market observation, so nothing here can expose real
performance. The gate predicates are exercised on synthetic `BacktestResult` values built by
hand, and the signal rules on synthetic `PriceSeries` values whose numbers were computed by
hand. Nothing writes outside `tmp_path`.
"""

from __future__ import annotations

import ast
import copy
import datetime as dt
import inspect
import json
import shutil
from decimal import Decimal, localcontext
from pathlib import Path

import pytest

from stockedge100.audit import sha256_file
from stockedge100.backtest.config import load_stage2_config
from stockedge100.backtest.costs import BASE, ENGINE_CONTEXT, STRESSED, ZERO, CostModel
from stockedge100.backtest.dataset import Bar, series_from_rows
from stockedge100.backtest.engine import BacktestResult, DecisionContext, EquityPoint
from stockedge100.backtest.errors import ConfigViolation
from stockedge100.backtest.market import MarketView
from stockedge100.backtest.portfolio import Trade
from stockedge100.backtest.window import ResearchWindow
from stockedge100.strategies import (
    attempt2_candidates,
    attempt2_config,
    attempt2_harness,
    attempt2_indicators,
    attempt2_risk,
    attempt2_runner,
    attempt2_traceability,
    gate,
    indicators,
    runner,
)
from stockedge100.strategies.attempt2_config import load_attempt2_config

# -- pinned sealed digests -----------------------------------------------------------------------

#: Written out from the sealed files themselves, not copied from
#: ``STAGE_3_ATTEMPT_2_PREREGISTRATION.sha256``. A rewrite of an artifact together with its freeze
#: record leaves these unchanged and therefore still fails.
PINNED_DIGESTS: dict[str, str] = {
    "config/stage3_attempt2_strategy_protocol.json":
        "77f1451c20e37640bd2843ff86d69eb54cbc0ebb592a696972fbdea6e05b5433",
    "config/stage3_attempt2_gate_criteria_binding.json":
        "a482f499173c0d7e2b0ca158b2edf7cb2e25a516ac2eb361e1441b2964006c8e",
    "config/stage3_gate_criteria.json":
        "310f1c978380f4a1d6b98b8c368975b1515476b032c123afb06f1dd597e3e18d",
    "config/stage3_strategy_protocol.json":
        "04dbe3fa8c6b2a9e725a66d24f5dc0a3a7e3567e70d38bfd2e96869cc6e169b6",
    "governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.md":
        "d9e34b3ce61f5998fe91c0b7b551a29a778fdb410330e60d6919c0a94ec447c6",
    "governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.json":
        "9a92dbdf88c2cc6e3a9a9ee80debba6bdcd9f70a45b50e8c5bbe127455afaca6",
    "governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.sha256":
        "ef9a0c6e7d59cf43565f9049729e898d560b4a025d4e74c11b87fe320760b543",
}

#: The eight paths ``load_attempt2_config`` verifies by digest. The pre-registration JSON and its
#: ``.sha256`` are deliberately absent: nothing hashes itself, so those two are hashed above
#: instead.
DIGEST_VERIFIED = (
    "config/stage2_cost_model.json",
    "config/stage3_attempt2_gate_criteria_binding.json",
    "config/stage3_attempt2_strategy_protocol.json",
    "config/stage3_gate_criteria.json",
    "config/stage3_strategy_protocol.json",
    "governance/STAGE_1_HOLDOUT_LOCK.json",
    "governance/STAGE_1_UNIVERSE.json",
    "governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.md",
)

#: Counts recomputed from ``attempt2_traceability.verify()`` at implementation time.
TRACEABILITY_COUNTS = {
    "rows": 127,
    "sealed_paths_required": 118,
    "implementation_references": 74,
    "tests_named": 90,
}

#: The seven condition ids, in sealed order.
CONDITION_IDS = tuple(f"S3-C{index}" for index in range(1, 8))

#: The RA1 keys every sealed variant carries, and the signal keys the three families use.
RA1_KEYS = frozenset(
    {
        "f_base",
        "vol_target",
        "vol_floor_fraction",
        "loss_control",
        "max_hold",
        "reentry_delay",
        "ladder_rungs",
    }
)
SIGNAL_KEYS = frozenset(
    {"sma_long", "sma_short", "rsi_period", "rsi_entry_below", "exit_sma",
     "risk_symbol", "defensive_symbol"}
)

#: The six Attempt 2 implementation modules, for the source-level scans.
ATTEMPT_2_MODULES = (
    attempt2_config,
    attempt2_indicators,
    attempt2_risk,
    attempt2_candidates,
    attempt2_runner,
    attempt2_harness,
)

#: The three test modules this stage adds, for the traceability cross-check.
TEST_MODULE_NAMES = (
    "tests/unit/test_stage3_attempt2_implementation.py",
    "tests/adversarial/test_stage3_attempt2_defects.py",
    "tests/integration/test_stage3_attempt2_backtest.py",
)

CONFIG = load_attempt2_config()
COSTS = CostModel(load_stage2_config().cost_model, BASE)

#: A sealed-shaped RA1 block for a synthetic candidate. Values are C1's, so no test invents one.
RA1 = {
    "f_base": "0.50",
    "vol_target": "0.10",
    "vol_floor_fraction": "0.05",
    "loss_control": "0.08",
    "max_hold": 20,
    "reentry_delay": 5,
    "ladder_rungs": [["0.08", "0.25"], ["0.10", "0.125"]],
}

DAY_ZERO = dt.date(2000, 1, 3)


# -- fixtures ------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def config() -> attempt2_config.Attempt2Config:
    return CONFIG


@pytest.fixture(scope="module")
def criteria() -> dict:
    return CONFIG.criteria


@pytest.fixture(scope="module")
def costs() -> CostModel:
    return COSTS


# -- synthetic factories -------------------------------------------------------------------------


def bar(session: dt.date, close: str, *, adj_close: str | None = None) -> Bar:
    value = Decimal(close)
    return Bar(
        session=session,
        open=value,
        high=value,
        low=value,
        close=value,
        adj_close=value if adj_close is None else Decimal(adj_close),
        volume=1_000,
        dividend=ZERO,
        split_ratio=Decimal(1),
    )


def synthetic_series(symbol: str, closes, *, start: dt.date = DAY_ZERO):
    """A ``PriceSeries`` over consecutive calendar days. ``split_ratio`` must be given: the
    ``series_from_rows`` default is ``"0"``, which no real normalized row carries."""

    rows = [
        {
            "session": (start + dt.timedelta(days=offset)).isoformat(),
            "open": str(close),
            "close": str(close),
            "split_ratio": "1",
        }
        for offset, close in enumerate(closes)
    ]
    return series_from_rows(symbol, rows)


def view_at(series: dict, session: dt.date) -> MarketView:
    """A ``MarketView`` for a signal test. The window is a local synthetic one, not a partition:
    no dataset is loaded here, so this reads nothing but the rows the test built."""

    window = ResearchWindow(name="test", start=dt.date(1990, 1, 1), end=dt.date(2030, 12, 31))
    return MarketView(series, session, window)


def context(session: dt.date, held: tuple[str, ...] = ()) -> DecisionContext:
    return DecisionContext(
        session=session,
        cash=Decimal(100),
        equity=Decimal(100),
        open_symbols=held,
        shutdown_active=False,
    )


def build(experiment_id: str, parameters: dict, universe: tuple[str, ...]):
    return attempt2_candidates.build_candidate(
        experiment_id=experiment_id,
        variant_id=f"{experiment_id}#TEST",
        universe=universe,
        parameters=parameters,
        costs=COSTS,
        rsi_warmup_changes=CONFIG.rsi_warmup_changes,
    )


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
    pnls=None,
    equity=None,
    starting: str = "100",
    symbols: tuple[str, ...] = ("SPY",),
    trades=None,
    shutdown: dt.date | None = None,
) -> BacktestResult:
    if trades is None:
        trades = [trade(value, index=position) for position, value in enumerate(pnls or [])]
    if equity is None:
        equity = [starting]
        running = Decimal(starting)
        for item in trades:
            running += item.pnl
            equity.append(f"{running:f}")
    points = [
        EquityPoint(
            session=DAY_ZERO + dt.timedelta(days=offset),
            cash=Decimal(value),
            equity=Decimal(value),
            stale_mark=False,
            position_count=0,
        )
        for offset, value in enumerate(equity)
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
        shutdown_session=shutdown,
        starting_equity=Decimal(starting),
        final_cash=Decimal(equity[-1]),
        final_equity=Decimal(equity[-1]),
        open_positions=[],
        cost_model={},
    )


def measured(
    total_return: str,
    *,
    max_drawdown: str = "0.05",
    closed_trades: int = 40,
    shutdown_session: str | None = None,
    scenario: str = BASE,
) -> dict[str, object]:
    """The four keys ``stress_evidence`` reads from a ``measure_variant`` record, plus ``scenario``.

    Deliberately not the whole record: the point of the pair of stress tests is that the evidence
    writer copies these through and reaches no verdict, so a fixture carrying only what it reads
    makes an added read fail loudly rather than silently pick up a default.
    """

    return {
        "scenario": scenario,
        "total_return": total_return,
        "max_drawdown": max_drawdown,
        "closed_trades": closed_trades,
        "shutdown_session": shutdown_session,
    }


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


def four_neighbours(*returns):
    return [neighbour(position + 1, value) for position, value in enumerate(returns)]


def cond(condition_id: str, verdict: str) -> dict:
    return gate.ConditionVerdict(condition_id, "sealed condition text", verdict).to_json()


def candidate(name: str, verdicts) -> dict:
    conditions = [cond(CONDITION_IDS[offset], verdicts[offset]) for offset in range(7)]
    return {
        "experiment_id": name,
        "family": "synthetic",
        "admitted": all(row["satisfied"] for row in conditions),
        "conditions": conditions,
    }


def sealed_copy(tmp_path: Path, root: Path) -> Path:
    """Copy the nine sealed inputs into ``tmp_path`` so a tamper test never touches the repo."""

    target = tmp_path / "sealed"
    for rel in set(DIGEST_VERIFIED) | {"governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.json"}:
        destination = target / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / rel, destination)
    return target


def module_sources() -> dict[str, str]:
    return {module.__name__.rsplit(".", 1)[-1]: inspect.getsource(module)
            for module in ATTEMPT_2_MODULES}


# -- the seal itself -----------------------------------------------------------------------------


def test_sealed_files_still_hash_to_the_pinned_values(project_root: Path) -> None:
    for rel, digest in PINNED_DIGESTS.items():
        assert sha256_file(project_root / rel) == digest, rel


def test_every_parameter_comes_from_the_digest_verified_seal(
    config, project_root: Path, tmp_path: Path, monkeypatch
) -> None:
    assert tuple(sorted(config.digests)) == DIGEST_VERIFIED
    for rel, digest in config.digests.items():
        assert digest == sha256_file(project_root / rel), rel
        if rel in PINNED_DIGESTS:
            assert digest == PINNED_DIGESTS[rel], rel

    # Every bound input's digest is recorded inside the sealed protocol, so the parameters the
    # engine reads are the parameters the seal names.
    bound = config.protocol["inputs_bound"]
    for key, rel in attempt2_config.BOUND_INPUTS.items():
        assert attempt2_config.bound_digest(bound, key) == config.digests[rel], key

    # A single altered byte in the protocol refuses to load at all.
    tampered_root = sealed_copy(tmp_path, project_root)
    protocol = tampered_root / attempt2_config.PROTOCOL_REL
    protocol.write_text(protocol.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    monkeypatch.setattr(attempt2_config, "PROJECT_ROOT", tampered_root)
    monkeypatch.setattr(
        attempt2_config,
        "PREREGISTRATION_JSON",
        tampered_root / "governance" / "STAGE_3_ATTEMPT_2_PREREGISTRATION.json",
    )
    with pytest.raises(ConfigViolation) as raised:
        load_attempt2_config()
    assert "has changed since it was sealed" in str(raised.value)
    assert attempt2_config.PROTOCOL_REL in str(raised.value)


def test_the_three_new_test_modules_define_every_traced_test_name(project_root: Path) -> None:
    """The traceability map names its verifying tests by string. This is what makes the map
    falsifiable: a renamed or deleted test shows up here, not as silent lost coverage."""

    defined: set[str] = set()
    for rel in TEST_MODULE_NAMES:
        tree = ast.parse((project_root / rel).read_text(encoding="utf-8"))
        defined.update(
            node.name for node in tree.body if isinstance(node, ast.FunctionDef)
        )
    named = set(attempt2_traceability.all_named_tests())
    assert not named - defined, sorted(named - defined)


def test_the_traceability_map_resolves_every_sealed_rule(config) -> None:
    report = attempt2_traceability.verify(config)
    assert report["missing_coverage"] == []
    assert report["duplicate_rows"] == []
    assert report["all_rows_resolve"] is True
    for key, expected in TRACEABILITY_COUNTS.items():
        assert report[key] == expected, key
    assert report["documents"] == {
        "SE100-CFG-3003": 110,
        "SE100-CFG-3004": 8,
        "SE100-CFG-3002": 9,
    }


# -- candidates, variants and parameters ---------------------------------------------------------


def test_exactly_three_candidate_ids_are_implemented(config) -> None:
    assert attempt2_candidates.ATTEMPT_2_EXPERIMENT_IDS == (
        "SE100-S3A2-C1-PULLBACK-RA1",
        "SE100-S3A2-C2-MEANREV-RA1",
        "SE100-S3A2-C3-DEFENSIVE-RA1",
    )
    assert config.experiment_ids == attempt2_candidates.ATTEMPT_2_EXPERIMENT_IDS
    assert config.iteration_budget["candidates"] == 3
    assert [entry["family"] for entry in config.experiments] == [
        "pullback",
        "mean reversion",
        "defensive regime logic",
    ]
    for experiment in config.experiments:
        candidate_object = build(
            experiment["experiment_id"],
            experiment["primary_parameters"],
            tuple(experiment["universe"]),
        )
        assert candidate_object.family == experiment["family"]
        assert candidate_object.experiment_id == experiment["experiment_id"]


def test_an_unregistered_experiment_id_is_refused() -> None:
    with pytest.raises(ConfigViolation) as raised:
        build("SE100-S3A2-C4-MOMENTUM-RA1", dict(RA1, sma_long=200, sma_short=10), ("SPY",))
    message = str(raised.value)
    assert "no implementation registered" in message
    for experiment_id in attempt2_candidates.ATTEMPT_2_EXPERIMENT_IDS:
        assert experiment_id in message


def test_four_neighbours_per_candidate_exactly_as_registered(config) -> None:
    for experiment in config.experiments:
        specs = attempt2_runner.variant_specs(experiment)
        assert len(experiment["robustness_neighbours"]) == 4
        assert len(specs) == 5
        assert [spec.role for spec in specs] == [runner.PRIMARY] + [runner.NEIGHBOUR] * 4
        assert [spec.index for spec in specs] == [0, 1, 2, 3, 4]
        experiment_id = experiment["experiment_id"]
        assert [spec.variant_id for spec in specs] == [
            f"{experiment_id}#PRIMARY",
            f"{experiment_id}#N1",
            f"{experiment_id}#N2",
            f"{experiment_id}#N3",
            f"{experiment_id}#N4",
        ]
        # Each neighbour differs from the primary in exactly the sealed override keys.
        primary = specs[0].parameters
        for position, overrides in enumerate(experiment["robustness_neighbours"], start=1):
            changed = {
                key for key in specs[position].parameters
                if specs[position].parameters[key] != primary.get(key)
            }
            assert changed == set(overrides) - {"universe"}


def test_variant_count_is_checked_against_the_seal(config) -> None:
    for experiment in config.experiments:
        extra = json.loads(json.dumps(experiment))
        extra["robustness_neighbours"].append({"sma_long": 123})
        with pytest.raises(ConfigViolation) as raised:
            attempt2_runner.variant_specs(extra)
        assert "enumerated 6 variants" in str(raised.value)

        short = json.loads(json.dumps(experiment))
        short["robustness_neighbours"].pop()
        with pytest.raises(ConfigViolation) as raised:
            attempt2_runner.variant_specs(short)
        assert "enumerated 4 variants" in str(raised.value)
        assert "no omitted one" in str(raised.value)


def test_declared_run_counts_are_checked_against_the_seal(config) -> None:
    budget = config.iteration_budget
    gating = sum(len(attempt2_runner.variant_specs(entry)) for entry in config.experiments)
    assert gating == budget["total_declared_gating_variants"] == 15
    assert budget["gating_variants_per_candidate"] == 5
    assert budget["max_variants_per_candidate"] == 5
    assert budget["total_declared_non_gating_stress_runs"] == len(config.experiments) == 3
    assert budget["total_declared_runs"] == 18
    assert gating + budget["total_declared_non_gating_stress_runs"] == budget["total_declared_runs"]
    assert budget["revisions_permitted"] == 0

    source = inspect.getsource(attempt2_harness.run_all)
    for key in (
        "total_declared_gating_variants",
        "total_declared_non_gating_stress_runs",
        "total_declared_runs",
    ):
        assert key in source, key


def test_primary_parameters_match_the_seal_exactly(config) -> None:
    expected = {
        "SE100-S3A2-C1-PULLBACK-RA1": {
            "sma_long": 200, "sma_short": 10, "f_base": "0.50", "vol_target": "0.10",
            "vol_floor_fraction": "0.05", "loss_control": "0.08", "max_hold": 20,
            "reentry_delay": 5, "ladder_rungs": [["0.08", "0.25"], ["0.10", "0.125"]],
        },
        "SE100-S3A2-C2-MEANREV-RA1": {
            "rsi_period": 2, "rsi_entry_below": 10, "exit_sma": 5, "f_base": "0.50",
            "vol_target": "0.10", "vol_floor_fraction": "0.05", "loss_control": "0.08",
            "max_hold": 10, "reentry_delay": 5,
            "ladder_rungs": [["0.08", "0.25"], ["0.10", "0.125"]],
        },
        "SE100-S3A2-C3-DEFENSIVE-RA1": {
            "sma_long": 200, "risk_symbol": "SPY", "defensive_symbol": "SHY", "f_base": "0.50",
            "vol_target": "0.10", "vol_floor_fraction": "0.05", "loss_control": "0.08",
            "max_hold": 252, "reentry_delay": 5,
            "ladder_rungs": [["0.08", "0.25"], ["0.10", "0.125"]],
        },
    }
    for experiment_id, parameters in expected.items():
        assert config.experiment(experiment_id)["primary_parameters"] == parameters

    neighbours = {
        "SE100-S3A2-C1-PULLBACK-RA1": [
            {"sma_long": 150}, {"sma_short": 20}, {"vol_target": "0.08"}, {"f_base": "0.35"}],
        "SE100-S3A2-C2-MEANREV-RA1": [
            {"rsi_entry_below": 5}, {"exit_sma": 10}, {"vol_target": "0.08"},
            {"loss_control": "0.12"}],
        "SE100-S3A2-C3-DEFENSIVE-RA1": [
            {"sma_long": 150}, {"defensive_symbol": None}, {"vol_target": "0.08"},
            {"f_base": "0.35"}],
    }
    for experiment_id, declared in neighbours.items():
        assert config.experiment(experiment_id)["robustness_neighbours"] == declared


def test_variant_specs_reproduce_the_sealed_universe(config) -> None:
    for experiment in config.experiments:
        declared = tuple(experiment["universe"])
        for spec in attempt2_runner.variant_specs(experiment):
            assert spec.universe == declared
            assert set(spec.symbols) <= set(declared)
    assert tuple(config.experiment("SE100-S3A2-C1-PULLBACK-RA1")["universe"]) == ("SPY",)
    assert tuple(config.experiment("SE100-S3A2-C2-MEANREV-RA1")["universe"]) == ("SPY",)
    assert tuple(config.experiment("SE100-S3A2-C3-DEFENSIVE-RA1")["universe"]) == ("SPY", "SHY")
    assert config.experiment("SE100-S3A2-C3-DEFENSIVE-RA1")["declared_instrument_count"] == 2


def test_c3_defensive_null_neighbour_keeps_the_declared_universe(config) -> None:
    """Sealed ``run_start_rule``: a neighbour that drops a symbol still runs over the same window
    as its primary, because the rule reads the DECLARED universe."""

    experiment = config.experiment("SE100-S3A2-C3-DEFENSIVE-RA1")
    specs = attempt2_runner.variant_specs(experiment)
    null_leg = specs[2]
    assert null_leg.variant_id.endswith("#N2")
    assert null_leg.parameters["defensive_symbol"] is None
    assert null_leg.universe == ("SPY", "SHY")
    assert null_leg.symbols == ("SPY",)
    assert specs[0].symbols == ("SPY", "SHY")
    assert attempt2_candidates.traded_symbols(
        "SE100-S3A2-C3-DEFENSIVE-RA1", ("SPY", "SHY"), null_leg.parameters
    ) == ("SPY",)


def test_warmup_reproduces_the_sealed_derivation(config) -> None:
    assert config.rsi_warmup_changes == 100
    expected = {
        "SE100-S3A2-C1-PULLBACK-RA1": 200,
        "SE100-S3A2-C2-MEANREV-RA1": 101,
        "SE100-S3A2-C3-DEFENSIVE-RA1": 200,
    }
    for experiment in config.experiments:
        specs = attempt2_runner.variant_specs(experiment)
        derived = attempt2_runner.largest_lookback(specs, config.rsi_warmup_changes)
        sealed = int(experiment["warmup_sessions"])
        assert sealed == expected[experiment["experiment_id"]]
        assert derived == sealed, experiment["experiment_id"]
    # VOL20's 21 bars are the floor and are dominated by every candidate's signal lookback.
    assert attempt2_runner.largest_lookback((), 0) == attempt2_indicators.VOL20_BARS == 21
    assert "21 bars" in config.vol20["lookback_contribution_to_warmup"]


def test_no_neighbour_is_ever_promoted(config, criteria) -> None:
    status = config.binding["neighbour_status"]
    assert status["can_a_neighbour_become_the_representative_of_its_candidate"]["answer"] == (
        "No. Never. Under no result."
    )
    assert status["is_a_neighbour_separately_admissible_at_gate_3"]["answer"].startswith(
        "No. A neighbour is not a candidate."
    )
    assert status["are_neighbours_diagnostic_or_independently_selectable"]["answer"] == (
        "Diagnostic only."
    )

    # Behaviourally: a losing primary with four winning neighbours still fails S3-C1. The
    # neighbours' numbers never become the candidate's.
    losing = result(pnls=["-1"] * 30)
    specs_and_results = four_neighbours("0.20", "0.30", "0.40", "0.50")
    entry = gate.evaluate_candidate(
        plan=plan(), primary=losing, neighbours=specs_and_results, criteria=criteria
    )
    rows = {row["id"]: row for row in entry["conditions"]}
    assert rows["S3-C1"]["verdict"] == gate.NOT_MET
    assert entry["admitted"] is False
    assert gate.stage_verdict([entry], criteria)["admitted_candidates"] == []


def test_the_grid_is_declared_but_never_searched(config) -> None:
    semantics = config.protocol["permitted_parameter_grid_semantics"]
    assert "No search, sweep, or optimisation over any grid is performed at any point." in (
        semantics["no_search"]
    )
    for experiment in config.experiments:
        primary = experiment["primary_parameters"]
        overrides = experiment["robustness_neighbours"]
        for key, declared in experiment["permitted_parameter_grid"].items():
            reachable = {json.dumps(primary[key])}
            reachable.update(
                json.dumps(entry[key]) for entry in overrides if key in entry
            )
            assert {json.dumps(value) for value in declared} == reachable, key
    # No implementation module reads the grid at all, which is what "never searched" means here.
    for name, source in module_sources().items():
        assert "permitted_parameter_grid" not in source, name


def test_no_fitted_model_and_no_undeclared_parameter(config) -> None:
    for experiment in config.experiments:
        for spec in attempt2_runner.variant_specs(experiment):
            keys = set(spec.parameters)
            assert keys & RA1_KEYS == RA1_KEYS, spec.variant_id
            assert keys <= RA1_KEYS | SIGNAL_KEYS, sorted(keys - (RA1_KEYS | SIGNAL_KEYS))
    shared = config.shared_rules["adopted_unchanged"]
    assert "no_machine_learning" in shared
    assert "no_combination" in shared


def test_random_seeds_are_null_and_recorded_as_null(config) -> None:
    repro = config.protocol["reproducibility_requirements"]
    assert repro["random_seeds"] is None
    assert "null rather than absent" in repro["random_seeds_note"]
    assert "no candidate, indicator, sizing rule, or risk rule" in repro["no_randomness"].lower()
    source = inspect.getsource(attempt2_harness.run_all)
    assert "random_seeds" in source
    assert "random_seeds_note" in source
    for name, module_source in module_sources().items():
        assert "import random" not in module_source, name
        assert "numpy.random" not in module_source, name


# -- indicators ----------------------------------------------------------------------------------


def test_vol20_follows_the_sealed_six_step_procedure(config) -> None:
    """The sealed procedure, verbatim in six steps, with a 19 denominator and 252 annualisation."""

    procedure = config.vol20["procedure"]
    assert len(procedure) == 6
    assert "21 visible adj_close" in procedure[0]
    assert "/ 19" in procedure[3]
    assert attempt2_indicators.VOL20_BARS == 21
    assert attempt2_indicators.VOL20_RETURNS == 20
    assert attempt2_indicators.VOL20_VARIANCE_DENOMINATOR == 19
    assert attempt2_indicators.TRADING_DAYS_PER_YEAR == 252
    assert "denominator is 19" in config.vol20["denominator_note"]

    # 21 bars whose adj_close alternates x1.1 then x0.9, so every |r| is 0.1 and the sample
    # variance is exactly 0.2 / 19.
    adjusted = [Decimal(100)]
    for step in range(20):
        adjusted.append(adjusted[-1] * (Decimal("1.1") if step % 2 == 0 else Decimal("0.9")))
    history = [
        bar(DAY_ZERO + dt.timedelta(days=offset), "50", adj_close=f"{value:f}")
        for offset, value in enumerate(adjusted)
    ]
    measured = attempt2_indicators.vol20(history)
    with localcontext(ENGINE_CONTEXT):
        closed_form = (Decimal("0.2") / 19).sqrt() * Decimal(252).sqrt()
    assert measured == closed_form
    assert measured == Decimal("1.628690142091910747576743174462970")
    # The rejected denominator would give a different number, so the choice is observable.
    with localcontext(ENGINE_CONTEXT):
        assert measured != (Decimal("0.2") / 20).sqrt() * Decimal(252).sqrt()


def test_vol20_is_undefined_below_twenty_one_bars(config) -> None:
    flat = [bar(DAY_ZERO + dt.timedelta(days=offset), "100") for offset in range(21)]
    assert attempt2_indicators.vol20(flat[:20]) is None
    assert attempt2_indicators.vol20([]) is None
    # 21 identical adjusted closes give exactly zero, not None: the sealed zero_case is a
    # separate rule and is not conflated with insufficient history.
    assert attempt2_indicators.vol20(flat) == ZERO
    assert "Undefined if fewer than 21 visible bars exist." in config.vol20["procedure"][0]
    assert "the target for that session is cash" in config.vol20["insufficient_history_case"]
    assert "NO_ENTRY_ZERO_VOLATILITY" in config.vol20["zero_case"]
    assert "not floored, clipped, or replaced by a constant" in config.vol20["zero_case"]


def test_vol20_uses_adj_close_not_close(config) -> None:
    assert "adj_close is used, not close" in config.vol20["price_series_note"]
    assert "annualised standard deviation" in config.vol20["definition"]
    assert "adj_close" in config.vol20["procedure"][0]

    moving = [
        bar(DAY_ZERO + dt.timedelta(days=offset), "100", adj_close=f"{100 + offset}")
        for offset in range(21)
    ]
    frozen_adjusted = [
        bar(DAY_ZERO + dt.timedelta(days=offset), f"{100 + offset}", adj_close="100")
        for offset in range(21)
    ]
    assert attempt2_indicators.vol20(moving) > ZERO
    assert attempt2_indicators.vol20(frozen_adjusted) == ZERO
    assert "never selects a symbol, never generates an entry" in config.vol20["purpose"]


def test_sma_and_rsi_are_the_sealed_attempt_1_implementations(config) -> None:
    definitions = config.indicator_definitions
    assert definitions["adopted_unchanged"] == ["arithmetic", "visible_bars", "SMA", "RSI"]
    assert list(definitions["added"]) == ["VOL20"]
    assert "SE100-CFG-3001" in json.dumps(definitions)
    assert attempt2_candidates.sma is indicators.sma
    assert attempt2_candidates.wilder_rsi is indicators.wilder_rsi


def test_unused_indicators_are_not_called_by_attempt_2(config) -> None:
    not_used = json.dumps(config.indicator_definitions["not_used_by_attempt_2"])
    for name in ("ROLLING_MAX", "ROLLING_MIN", "MOMENTUM"):
        assert name in not_used, name
    for module_name, source in module_sources().items():
        for symbol in ("rolling_max_close", "rolling_min_close", "momentum("):
            assert symbol not in source, f"{module_name} references {symbol}"


# -- RA1 parameters ------------------------------------------------------------------------------


def test_ra1_parameters_have_no_defaults() -> None:
    complete = attempt2_risk.Ra1Parameters.from_parameters(dict(RA1))
    assert complete.max_hold == 20
    assert complete.reentry_delay == 5
    for key in sorted(RA1_KEYS):
        short = {name: value for name, value in RA1.items() if name != key}
        with pytest.raises(ConfigViolation) as raised:
            attempt2_risk.Ra1Parameters.from_parameters(short)
        message = str(raised.value)
        assert key in message, key
        assert "RA1 has no defaults" in message


def test_ladder_rungs_are_threshold_inclusive(config) -> None:
    ra1 = attempt2_risk.Ra1Parameters.from_parameters(dict(RA1))
    assert ra1.ladder_rungs == (
        (Decimal("0.08"), Decimal("0.25")),
        (Decimal("0.10"), Decimal("0.125")),
    )
    # Inclusive at each sealed threshold: exactly 8% is already the first rung.
    assert ra1.f_cap(Decimal("0.0799")) == ra1.f_base
    assert ra1.f_cap(Decimal("0.08")) == Decimal("0.25")
    assert ra1.f_cap(Decimal("0.0999")) == Decimal("0.25")
    assert ra1.f_cap(Decimal("0.10")) == Decimal("0.125")
    assert ra1.f_cap(Decimal("0.1499")) == Decimal("0.125")
    rule = "\n".join(config.risk_architecture["RA1-5"]["rule"])
    assert "dd < 0.08: f_cap = 0.50." in rule
    assert "0.08 <= dd < 0.10: f_cap = 0.25." in rule
    assert "dd >= 0.10: f_cap = 0.125." in rule

    misshapen = dict(RA1, ladder_rungs=[["0.08", "0.25", "extra"]])
    with pytest.raises(ConfigViolation) as raised:
        attempt2_risk.Ra1Parameters.from_parameters(misshapen)
    assert "is not a (threshold, f_cap) pair" in str(raised.value)

    descending = dict(RA1, ladder_rungs=[["0.10", "0.125"], ["0.08", "0.25"]])
    with pytest.raises(ConfigViolation) as raised:
        attempt2_risk.Ra1Parameters.from_parameters(descending)
    assert "not strictly ascending" in str(raised.value)


def test_no_ra1_constant_references_the_fifteen_percent_ceiling(config) -> None:
    """Sealed ``no_candidate_reads_the_ceiling``: no RA1 rule and no candidate rule references
    0.15, the shutdown state, or the distance to it as an input to sizing or signalling."""

    sealed = config.risk_architecture["engine_shutdown_relationship"]
    assert "No RA1 rule and no candidate rule references 0.15" in (
        sealed["no_candidate_reads_the_ceiling"]
    )
    risk_source = inspect.getsource(attempt2_risk)
    candidate_source = inspect.getsource(attempt2_candidates)
    for forbidden in ("0.15", "0.1499", "0.149", "14.99"):
        assert forbidden not in risk_source, forbidden
        assert forbidden not in candidate_source, forbidden
    # The ladder tops out at the sealed 10% rung and never reaches for the ceiling.
    ra1 = attempt2_risk.Ra1Parameters.from_parameters(dict(RA1))
    assert max(threshold for threshold, _ in ra1.ladder_rungs) == Decimal("0.10")
    assert config.thresholds["max_drawdown_pct"] == 15


def test_no_rule_depends_on_dictionary_or_file_order(config) -> None:
    ordering = config.protocol["reproducibility_requirements"]["ordering"]
    assert "ascending ASCII symbol order" in ordering
    assert "No rule depends on dictionary, file, or filesystem order." in ordering
    symbols = attempt2_runner.required_symbols(config)
    assert symbols == tuple(sorted(symbols))
    assert symbols == ("SHY", "SPY")
    # The ladder is read in order, so a file-order-dependent ladder is refused outright.
    with pytest.raises(ConfigViolation):
        attempt2_risk.Ra1Parameters.from_parameters(
            dict(RA1, ladder_rungs=[["0.10", "0.125"], ["0.08", "0.25"]])
        )


def test_no_float_in_any_signal_sizing_or_risk_path() -> None:
    assert attempt2_config.dec("0.50") == Decimal("0.50")
    assert attempt2_config.dec(20) == Decimal(20)
    assert attempt2_config.dec(Decimal("0.1")) == Decimal("0.1")
    with pytest.raises(ConfigViolation) as raised:
        attempt2_config.dec(0.5)
    assert "refusing to build a Decimal from the float" in str(raised.value)
    for name, source in module_sources().items():
        assert "float(" not in source, name


# -- the seven gate conditions ------------------------------------------------------------------


def spec_for(criteria: dict, condition_id: str) -> dict:
    for entry in criteria["conditions"]:
        if entry["id"] == condition_id:
            return entry
    raise AssertionError(condition_id)


def test_s3_c1_matches_the_sealed_predicate(criteria) -> None:
    spec = spec_for(criteria, "S3-C1")
    assert spec["predicate"] == "total_return > 0"
    assert gate.condition_1(result(equity=["100", "110"]), criteria).verdict == gate.MET
    assert gate.condition_1(result(equity=["100", "90"]), criteria).verdict == gate.NOT_MET
    # Strictly positive: exactly break-even is not a pass.
    assert gate.condition_1(result(equity=["100", "100"]), criteria).verdict == gate.NOT_MET
    empty = gate.condition_1(result(equity=["100"]), criteria)
    assert empty.verdict == gate.NOT_EVALUABLE
    assert empty.satisfied is False
    met = gate.condition_1(result(equity=["100", "110"]), criteria)
    assert met.measured == "0.1"
    assert met.threshold == "> 0"
    assert met.required_verbatim == spec["required_verbatim"]


def test_s3_c2_matches_the_sealed_predicate(criteria) -> None:
    spec = spec_for(criteria, "S3-C2")
    assert spec["predicate"] == "max_drawdown <= 0.15"
    # Exactly 15% is inclusive, per the sealed boundary.
    at_limit = gate.condition_2(result(equity=["100", "85"]), criteria)
    assert at_limit.verdict == gate.MET
    assert at_limit.measured == "0.15"
    assert at_limit.threshold == "<= 0.15"
    assert at_limit.note == spec["boundary"]
    beyond = gate.condition_2(result(equity=["100", "84.99"]), criteria)
    assert beyond.verdict == gate.NOT_MET
    assert gate.condition_2(result(equity=["100", "110"]), criteria).verdict == gate.MET
    # The drawdown is measured from the running high-water mark, not from the starting equity: a
    # curve that ends 70% up still records the 15% fall from its peak.
    from_peak = gate.condition_2(result(equity=["100", "200", "170"]), criteria)
    assert from_peak.measured == "0.15"
    assert from_peak.verdict == gate.MET
    assert gate.condition_2(result(equity=["100", "200", "169"]), criteria).verdict == gate.NOT_MET
    assert at_limit.evidence["granularity"] == "session close"


def test_s3_c3_matches_the_sealed_predicate(criteria) -> None:
    spec = spec_for(criteria, "S3-C3")
    assert spec["predicate"] == "profit_factor >= 1.10"
    at_limit = gate.condition_3(result(pnls=["110", "-100"]), criteria)
    assert at_limit.verdict == gate.MET
    assert at_limit.measured == "1.1"
    assert at_limit.threshold == ">= 1.1"
    assert gate.condition_3(result(pnls=["100", "-100"]), criteria).verdict == gate.NOT_MET
    no_trades = gate.condition_3(result(pnls=[]), criteria)
    assert no_trades.verdict == gate.NOT_EVALUABLE
    assert no_trades.note == spec["undefined_cases"]["no_closed_trades"]
    winners_only = gate.condition_3(result(pnls=["5", "5"]), criteria)
    assert winners_only.verdict == gate.MET
    assert winners_only.note.startswith("UNDEFINED_NO_LOSSES_TREATED_AS_MET:")
    assert spec["undefined_cases"]["no_losing_trades"] in winners_only.note


def test_s3_c4_matches_the_sealed_predicate(criteria) -> None:
    spec = spec_for(criteria, "S3-C4")
    assert spec["predicate"] == "closed_trades >= 30"
    assert spec["exception_invoked"] is False
    at_limit = gate.condition_4(result(pnls=["1"] * 30), criteria)
    assert at_limit.verdict == gate.MET
    assert at_limit.measured == "30"
    assert at_limit.threshold == ">= 30"
    assert at_limit.evidence["exception_invoked"] is False
    assert gate.condition_4(result(pnls=["1"] * 29), criteria).verdict == gate.NOT_MET
    assert gate.condition_4(result(pnls=[]), criteria).verdict == gate.NOT_MET


def test_s3_c5_matches_the_sealed_predicate(criteria) -> None:
    spec = spec_for(criteria, "S3-C5")
    assert spec["predicate"] == "best_trade_removed_return > 0 for BOTH removals"
    survives = gate.condition_5(result(pnls=["10", "10", "10"]), criteria)
    assert survives.verdict == gate.MET
    assert survives.threshold == "> 0 for BOTH removals"
    assert survives.evidence["j1_equals_j2"] is True
    # One trade carries the whole result: removing it turns the return negative.
    fragile = gate.condition_5(result(pnls=["50", "-5"]), criteria)
    assert fragile.verdict == gate.NOT_MET
    assert fragile.evidence["j2_largest_absolute_pnl"]["trade_index"] == 0
    assert Decimal(fragile.evidence["j1_largest_equity_multiple"]["removed_return"]) < ZERO
    one_trade = gate.condition_5(result(pnls=["10"]), criteria)
    assert one_trade.verdict == gate.NOT_EVALUABLE
    assert one_trade.note == spec["not_evaluable_treatment"]


def test_s3_c6_matches_the_sealed_predicate(criteria) -> None:
    spec = spec_for(criteria, "S3-C6")
    assert spec["predicate"] == "max instrument contribution <= 0.50"
    assert gate.CONCENTRATION_MAX == Decimal("0.50")
    concentrated = result(
        trades=[trade("60", symbol="SPY", index=0), trade("40", symbol="SHY", index=1)],
        symbols=("SPY", "SHY"),
    )
    verdict = gate.condition_6(concentrated, plan(("SPY", "SHY")), criteria)
    assert verdict.verdict == gate.NOT_MET
    assert verdict.measured == "0.6"
    assert verdict.evidence["largest_contributor"] == "SPY"
    # Exactly 0.50 is inclusive.
    even = result(
        trades=[trade("50", symbol="SPY", index=0), trade("50", symbol="SHY", index=1)],
        symbols=("SPY", "SHY"),
    )
    at_limit = gate.condition_6(even, plan(("SPY", "SHY")), criteria)
    assert at_limit.verdict == gate.MET
    assert at_limit.measured == "0.5"
    # A single-instrument candidate is not applicable by the condition's own text.
    single = gate.condition_6(result(pnls=["10"]), plan(("SPY",)), criteria)
    assert single.verdict == gate.NOT_APPLICABLE
    assert single.satisfied is True
    assert single.note == spec["scope_interpretation"]["rationale"]
    assert single.evidence["declared_instrument_count"] == 1
    # Non-positive total closed-trade P&L leaves the share undefined.
    losing = result(
        trades=[trade("-10", symbol="SPY", index=0), trade("-10", symbol="SHY", index=1)],
        symbols=("SPY", "SHY"),
    )
    undefined = gate.condition_6(losing, plan(("SPY", "SHY")), criteria)
    assert undefined.verdict == gate.NOT_EVALUABLE
    assert undefined.satisfied is False


def test_s3_c7_matches_the_sealed_predicate(criteria) -> None:
    spec = spec_for(criteria, "S3-C7")
    assert spec["predicate"] == (
        "sign(neighbour total_return) == sign(primary total_return) for all four neighbours, "
        "where sign is positive, negative, or zero and zero matches nothing"
    )
    primary = result(equity=["100", "120"])
    all_match = gate.condition_7(
        primary, four_neighbours("0.10", "0.20", "0.05", "0.30"), criteria
    )
    assert all_match.verdict == gate.MET
    assert all_match.measured == "4/4 neighbours match"
    assert all_match.threshold == "all four match, zero matches nothing"
    assert all_match.note == spec["selection_prohibition"]

    one_flips = gate.condition_7(
        primary, four_neighbours("0.10", "-0.20", "0.05", "0.30"), criteria
    )
    assert one_flips.verdict == gate.NOT_MET
    assert one_flips.measured == "3/4 neighbours match"

    # Zero matches nothing, including another zero.
    one_zero = gate.condition_7(primary, four_neighbours("0.10", "0", "0.05", "0.30"), criteria)
    assert one_zero.verdict == gate.NOT_MET

    # A negative primary with negative neighbours is sign-stable: the condition tests stability,
    # not profitability.
    losing = result(equity=["100", "80"])
    stable_loss = gate.condition_7(
        losing, four_neighbours("-0.10", "-0.20", "-0.05", "-0.30"), criteria
    )
    assert stable_loss.verdict == gate.MET

    with pytest.raises(ConfigViolation) as raised:
        gate.condition_7(primary, four_neighbours("0.10", "0.20", "0.05"), criteria)
    assert "expects exactly four sealed neighbours; 3 were supplied" in str(raised.value)


def test_all_seven_conditions_are_evaluated_for_every_candidate(config, criteria) -> None:
    assert [entry["id"] for entry in criteria["conditions"]] == list(CONDITION_IDS)
    entry = gate.evaluate_candidate(
        plan=plan(),
        primary=result(pnls=["1"] * 30),
        neighbours=four_neighbours("0.10", "0.20", "0.05", "0.30"),
        criteria=criteria,
    )
    assert [row["id"] for row in entry["conditions"]] == list(CONDITION_IDS)
    for experiment in config.experiments:
        applied = json.dumps(experiment["gate_3_conditions_applied"])
        for condition_id in CONDITION_IDS:
            assert condition_id in applied, (experiment["experiment_id"], condition_id)


def test_not_evaluable_and_not_run_are_never_satisfied(config, criteria) -> None:
    rule = config.binding["admissible_candidate_exists"]
    assert rule["not_satisfied_values"] == [
        "NOT_MET", "NOT_EVALUABLE", "NOT_RUN", "UNKNOWN", "MISSING_EVIDENCE", "absent"
    ]
    assert gate.ConditionVerdict("S3-C1", "x", gate.MET).satisfied is True
    assert gate.ConditionVerdict("S3-C1", "x", gate.NOT_APPLICABLE).satisfied is True
    assert gate.ConditionVerdict("S3-C1", "x", gate.NOT_MET).satisfied is False
    assert gate.ConditionVerdict("S3-C1", "x", gate.NOT_EVALUABLE).satisfied is False
    # NOT_RUN is not even representable as a condition verdict; it is a variant status.
    for invalid in ("NOT_RUN", "UNKNOWN", "MISSING_EVIDENCE", "PASS"):
        with pytest.raises(ConfigViolation):
            gate.ConditionVerdict("S3-C1", "x", invalid)
    # A NOT_EVALUABLE condition sinks its candidate.
    entry = gate.evaluate_candidate(
        plan=plan(),
        primary=result(equity=["100"]),
        neighbours=four_neighbours("0.10", "0.20", "0.05", "0.30"),
        criteria=criteria,
    )
    assert "S3-C1" in entry["conditions_not_evaluable"]
    assert entry["admitted"] is False


def test_conjunction_within_candidate_and_disjunction_across(config, criteria) -> None:
    rule = config.binding["admissible_candidate_exists"]
    assert "CONJUNCTIVE" in rule["within_candidate"]
    assert "DISJUNCTIVE" in rule["across_candidates"]
    required = rule["how_many_admissible_candidates_are_required"]
    assert required["answer"] == "Exactly one."
    assert "does not rank them" in required["and_no_more_than_one_is_needed"]

    admitted = gate.evaluate_candidate(
        plan=plan(),
        primary=result(pnls=["1"] * 30),
        neighbours=four_neighbours("0.10", "0.20", "0.05", "0.30"),
        criteria=criteria,
    )
    rejected = gate.evaluate_candidate(
        plan=plan(),
        primary=result(pnls=["1"] * 29),
        neighbours=four_neighbours("0.10", "0.20", "0.05", "0.30"),
        criteria=criteria,
    )
    assert admitted["admitted"] is True
    assert rejected["admitted"] is False
    assert rejected["conditions_not_met"] == ["S3-C4"]

    stage = gate.stage_verdict([rejected, admitted], criteria)
    assert stage["verdict"] == "PASS"
    assert stage["admitted_candidates"] == [admitted["experiment_id"]]
    assert stage["candidates_evaluated"] == 2
    assert gate.stage_verdict([rejected], criteria)["verdict"] == "FAIL"
    assert gate.stage_verdict([rejected, rejected], criteria)["admitted_candidates"] == []


def test_candidates_are_never_combined(criteria) -> None:
    """The union of conditions satisfied across two candidates covers all seven, and the gate
    still fails. Conjunction applies within a candidate only."""

    fails_c7 = gate.evaluate_candidate(
        plan=plan(),
        primary=result(pnls=["1"] * 30),
        neighbours=four_neighbours("0.10", "0.20", "0.05", "-0.30"),
        criteria=criteria,
    )
    fails_c1 = gate.evaluate_candidate(
        plan=plan(),
        primary=result(pnls=["1"] * 29 + ["-40"]),
        neighbours=four_neighbours("-0.10", "-0.20", "-0.05", "-0.30"),
        criteria=criteria,
    )
    satisfied_union: set[str] = set()
    for entry in (fails_c7, fails_c1):
        satisfied_union.update(row["id"] for row in entry["conditions"] if row["satisfied"])
    assert satisfied_union == set(CONDITION_IDS)
    assert fails_c7["conditions_not_met"] == ["S3-C7"]
    assert "S3-C1" in fails_c1["conditions_not_met"]
    assert fails_c7["admitted"] is False
    assert fails_c1["admitted"] is False
    stage = gate.stage_verdict([fails_c7, fails_c1], criteria)
    assert stage["verdict"] == "FAIL"
    assert stage["admitted_candidates"] == []


def test_rollup_aggregates_on_satisfaction_not_on_met() -> None:
    """The recorded Attempt 1 failure mode: aggregating S3-C6 on ``verdict == MET`` produced a
    false FAIL for a condition two candidates satisfied by not applying."""

    all_met = [gate.MET] * 7
    rows = attempt2_harness.condition_rollup([
        candidate("C1", all_met[:5] + [gate.NOT_APPLICABLE, gate.MET]),
        candidate("C2", all_met[:5] + [gate.NOT_APPLICABLE, gate.MET]),
        candidate("C3", all_met[:5] + [gate.NOT_MET, gate.MET]),
    ])
    concentration = {row["id"]: row for row in rows}["S3-C6"]
    assert concentration["met_by"] == []
    assert concentration["not_applicable_for"] == ["C1", "C2"]
    assert concentration["not_met_by"] == ["C3"]
    assert concentration["satisfied_by_at_least_one_candidate"] is True
    assert "MET or NOT_APPLICABLE_BY_CONDITION_TEXT" in concentration["aggregated_on"]
    with pytest.raises(ConfigViolation):
        attempt2_harness.condition_rollup([])


def test_rollup_carries_three_separate_lists() -> None:
    rows = attempt2_harness.condition_rollup([
        candidate("C1", [gate.MET] * 7),
        candidate("C2", [gate.NOT_MET] + [gate.MET] * 5 + [gate.NOT_EVALUABLE]),
        candidate("C3", [gate.MET] * 5 + [gate.NOT_APPLICABLE, gate.MET]),
    ])
    assert [row["id"] for row in rows] == list(CONDITION_IDS)
    for row in rows:
        assert set(row) >= {
            "id", "aggregated_on", "satisfied_by_at_least_one_candidate",
            "met_by", "not_met_by", "not_applicable_for", "verdict_by_candidate", "settles",
        }
        overlap = set(row["met_by"]) & set(row["not_met_by"]) & set(row["not_applicable_for"])
        assert overlap == set()
    by_id = {row["id"]: row for row in rows}
    assert by_id["S3-C1"]["met_by"] == ["C1", "C3"]
    assert by_id["S3-C1"]["not_met_by"] == ["C2"]
    assert by_id["S3-C6"]["not_applicable_for"] == ["C3"]
    # A NOT_EVALUABLE verdict appears in none of the three lists, and satisfies nothing.
    assert by_id["S3-C7"]["verdict_by_candidate"]["C2"] == gate.NOT_EVALUABLE
    assert "C2" not in by_id["S3-C7"]["met_by"]
    assert "C2" not in by_id["S3-C7"]["not_applicable_for"]


def test_the_conditions_table_carries_the_decisive_row(config, criteria) -> None:
    rule = config.binding["admissible_candidate_exists"]
    assert "per_condition_rollup_is_not_the_gate" in rule
    rejected = candidate("C1", [gate.NOT_MET] + [gate.MET] * 6)
    stage = gate.stage_verdict([rejected], criteria)
    row = attempt2_harness.decisive_row(stage, config.binding)
    assert row["id"] == "admissible_candidate_exists"
    assert row["decides_the_gate"] is True
    assert row["value"] is False
    assert row["gate_verdict"] == "FAIL"
    derivation = criteria["verdict_token_derivation"]
    assert row["gate_verdict_token"] == derivation["fail_token"]
    assert row["gate_verdict_condition"] == derivation["fail_condition"]
    assert row["frozen_rule"] == rule["frozen_rule"]
    assert row["within_candidate"] == rule["within_candidate"]

    admitted_row = attempt2_harness.decisive_row(
        gate.stage_verdict([candidate("C1", [gate.MET] * 7)], criteria), config.binding
    )
    assert admitted_row["value"] is True
    assert admitted_row["admitted_candidates"] == ["C1"]
    assert admitted_row["gate_verdict_token"] == derivation["pass_token"]


def test_tokens_are_read_from_the_sealed_derivation(criteria) -> None:
    derivation = criteria["verdict_token_derivation"]
    assert "Conjunction applies WITHIN a candidate" in derivation["conjunctive_note"]
    assert "fail_is_a_deliverable" in derivation
    tampered = copy.deepcopy(criteria)
    tampered["verdict_token_derivation"]["pass_token"] = "SENTINEL_PASS"
    tampered["verdict_token_derivation"]["fail_token"] = "SENTINEL_FAIL"
    stage = gate.stage_verdict([candidate("C1", [gate.MET] * 7)], tampered)
    assert stage["pass_token"] == "SENTINEL_PASS"
    assert stage["fail_token"] == "SENTINEL_FAIL"
    # The real derivation is read the same way, never from a literal in the evaluator.
    real = gate.stage_verdict([candidate("C1", [gate.MET] * 7)], criteria)
    assert real["pass_token"] == derivation["pass_token"]
    assert real["fail_token"] == derivation["fail_token"]
    assert real["combination_rule"] == derivation["conjunctive_note"]


def test_the_fifteen_percent_ceiling_is_unchanged(config, criteria) -> None:
    assert config.thresholds == {
        "net_return_positive": True,
        "max_drawdown_pct": 15,
        "profit_factor_min": 1.1,
        "closed_trades_min": 30,
        "best_trade_removed_return_positive": True,
    }
    gate.check_thresholds_against_seal(criteria)
    for key, value in (
        ("max_drawdown_pct", 20),
        ("profit_factor_min", 1.0),
        ("closed_trades_min", 10),
        ("net_return_positive", False),
    ):
        tampered = copy.deepcopy(criteria)
        tampered["frozen_gate_json_companion_verbatim"]["thresholds"][key] = value
        with pytest.raises(ConfigViolation) as raised:
            gate.check_thresholds_against_seal(tampered)
        assert key in str(raised.value)
    assert config.binding["bound_artifact"]["adoption"] == "ADOPTED_UNCHANGED"
    assert config.preregistration["gate"]["criteria_changed_for_attempt_2"] is False


def test_a_missing_neighbour_makes_s3_c7_fail_not_pass(config, criteria) -> None:
    spec = spec_for(criteria, "S3-C7")
    rule = config.protocol["partial_or_failed_run_rule"]
    assert rule["neighbour_fails_to_run"].startswith("NOT_RUN")
    assert "S3-C7 fails for that candidate" in rule["neighbour_fails_to_run"]
    assert "never replaced by a different candidate" in rule["no_substitution"]
    assert "one of its own neighbours" in rule["no_substitution"]

    verdict = gate.condition_7(
        result(equity=["100", "120"]),
        four_neighbours("0.10", None, "0.05", "0.30"),
        criteria,
    )
    assert verdict.verdict == gate.NOT_MET
    assert verdict.satisfied is False
    assert verdict.evidence["neighbours_not_run"] == ["SE100-S3-TEST#N2"]
    assert spec["not_evaluable_treatment"] in verdict.note
    assert spec["selection_prohibition"] in verdict.note


# -- non-gating evidence stays non-gating --------------------------------------------------------


def test_secondary_metrics_are_reported_and_never_gating(config, criteria) -> None:
    secondary = config.protocol["secondary_metrics"]
    reported = secondary["reported_never_gating"]
    assert len(reported) == 6
    assert "cannot affect admission" in secondary["note"]
    for fragment in (
        "EXIT_LOSS_CONTROL",
        "NO_ENTRY_ZERO_VOLATILITY",
        "realised exposure fraction",
        "ladder rung",
        "four decimal places",
    ):
        assert fragment in json.dumps(reported), fragment
    assert len(criteria["reported_but_not_gating"]) == 4
    # None of the non-gating names is a gate condition id.
    gating_ids = {entry["id"] for entry in criteria["conditions"]}
    assert gating_ids == set(CONDITION_IDS)


def test_no_benchmark_becomes_a_gate_condition(config, criteria) -> None:
    benchmarks = config.protocol["benchmarks"]
    assert sorted(benchmarks) == [
        "beating_spy_not_mandatory",
        "cash",
        "constitution_ref",
        "do_nothing",
        "no_benchmark_becomes_a_gate",
        "spy_total_return",
        "spy_tradable_buy_and_hold",
    ]
    text = json.dumps(criteria["conditions"])
    for word in ("benchmark", "SPY total return", "buy-and-hold"):
        assert word not in text, word
    assert "gate" in benchmarks["no_benchmark_becomes_a_gate"].lower()


def test_stress_run_is_never_passed_to_the_gate(config, criteria) -> None:
    treatment = config.protocol["cost_stress_treatment"]
    assert treatment["gating"] is False
    assert "2x the complete base trading-friction assumption" in treatment["attempt_2_rule"]

    signature = inspect.signature(gate.evaluate_candidate)
    assert list(signature.parameters) == ["plan", "primary", "neighbours", "criteria"]
    for parameter in signature.parameters.values():
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY

    for experiment in config.experiments:
        for spec in attempt2_runner.variant_specs(experiment):
            assert attempt2_runner.STRESS_SUFFIX not in spec.variant_id
            assert attempt2_runner.DETERMINISM_SUFFIX not in spec.variant_id

    evidence = attempt2_runner.stress_evidence(
        measured("0.30", max_drawdown="0.05"),
        measured("0.05", max_drawdown="0.07", scenario=STRESSED),
        Decimal(2),
    )
    assert evidence["gating"] is False
    assert evidence["stress_multiplier"] == "2"
    assert evidence["scenario"] == STRESSED
    assert evidence["flags"] == []


def test_stress_fragile_flag_changes_no_verdict(config, criteria) -> None:
    fragile = attempt2_runner.stress_evidence(
        measured("0.30", max_drawdown="0.05"),
        measured("-0.02", max_drawdown="0.09", scenario=STRESSED),
        Decimal(2),
    )
    assert fragile["flags"] == [attempt2_runner.STRESS_FRAGILE]
    assert fragile["gating"] is False
    assert "never gating" in fragile["flag_semantics"]
    assert fragile["base_total_return_positive"] is True
    assert fragile["stressed_total_return_positive"] is False

    # The gate reads the base primary only, so the flag cannot move a verdict either way.
    admitted = gate.evaluate_candidate(
        plan=plan(),
        primary=result(pnls=["1"] * 30),
        neighbours=four_neighbours("0.10", "0.20", "0.05", "0.30"),
        criteria=criteria,
    )
    assert admitted["admitted"] is True
    assert gate.stage_verdict([admitted], criteria)["verdict"] == "PASS"
    assert config.protocol["cost_stress_treatment"]["gating"] is False


# -- signal rules --------------------------------------------------------------------------------


def test_signal_target_rule_c1(config) -> None:
    """Sealed rule: SPY if close(t) > SMA(200)(t) AND close(t) < SMA(10)(t), else cash."""

    experiment = config.experiment("SE100-S3A2-C1-PULLBACK-RA1")
    assert "close(t) > SMA(sma_long)(t)" in experiment["signal_target_rule"]
    parameters = experiment["primary_parameters"]
    candidate_object = build(experiment["experiment_id"], parameters, ("SPY",))

    def target_for(last: str) -> str | None:
        closes = ["100"] * 190 + ["130"] * 9 + [last]
        series = {"SPY": synthetic_series("SPY", closes)}
        session = DAY_ZERO + dt.timedelta(days=len(closes) - 1)
        return candidate_object.target(view_at(series, session), context(session))

    # close 120 > SMA200 101.45 and < SMA10 129 -> a pullback inside an uptrend.
    assert target_for("120") == "SPY"
    # close 101 < SMA200 101.355 -> the long-term regime has failed.
    assert target_for("101") is None
    # close 135 > SMA10 130.5 -> already recovered, so no entry and an EXIT_SIGNAL if held.
    assert target_for("135") is None

    short_history = {"SPY": synthetic_series("SPY", ["100"] * 199)}
    session = DAY_ZERO + dt.timedelta(days=198)
    assert candidate_object.target(view_at(short_history, session), context(session)) is None


def test_signal_target_rule_c2(config) -> None:
    """Sealed rule: flat -> SPY if RSI(2)(t) < 10; holding -> cash if close(t) > SMA(5)(t)."""

    experiment = config.experiment("SE100-S3A2-C2-MEANREV-RA1")
    assert "If flat" in experiment["signal_target_rule"]
    assert "If holding SPY" in experiment["signal_target_rule"]
    candidate_object = build(
        experiment["experiment_id"], experiment["primary_parameters"], ("SPY",)
    )

    falling = {"SPY": synthetic_series("SPY", [str(200 - step) for step in range(101)])}
    rising = {"SPY": synthetic_series("SPY", [str(100 + step) for step in range(101)])}
    session = DAY_ZERO + dt.timedelta(days=100)

    # Strictly falling: RSI(2) is 0, below the sealed threshold of 10, and close 100 < SMA5 102.
    assert candidate_object.target(view_at(falling, session), context(session)) == "SPY"
    assert candidate_object.target(
        view_at(falling, session), context(session, held=("SPY",))
    ) == "SPY"
    # Strictly rising: RSI(2) is 100, and close 200 > SMA5 198, so a holder exits.
    assert candidate_object.target(view_at(rising, session), context(session)) is None
    assert candidate_object.target(
        view_at(rising, session), context(session, held=("SPY",))
    ) is None

    short_history = {"SPY": synthetic_series("SPY", [str(200 - step) for step in range(100)])}
    short_session = DAY_ZERO + dt.timedelta(days=99)
    assert candidate_object.target(
        view_at(short_history, short_session), context(short_session)
    ) is None


def test_signal_target_rule_c3(config) -> None:
    """Sealed rule: the regime is read from the risk symbol only; the defensive leg is a
    destination, never a signal."""

    experiment = config.experiment("SE100-S3A2-C3-DEFENSIVE-RA1")
    assert "never a signal" in experiment["signal_target_rule"]
    parameters = experiment["primary_parameters"]
    candidate_object = build(experiment["experiment_id"], parameters, ("SPY", "SHY"))
    session = DAY_ZERO + dt.timedelta(days=199)
    shy = synthetic_series("SHY", ["50"] * 200)

    def target_for(last: str, *, defensive=shy):
        series = {"SPY": synthetic_series("SPY", ["100"] * 199 + [last])}
        if defensive is not None:
            series["SHY"] = defensive
        return candidate_object.target(view_at(series, session), context(session))

    # close 120 > SMA200 100.1 -> risk on.
    assert target_for("120") == "SPY"
    # close 80 < SMA200 99.9 -> defensive, and the defensive leg has a visible bar.
    assert target_for("80") == "SHY"
    # No visible SHY bar at t -> cash, never a stale price and never the risk leg.
    assert target_for("80", defensive=synthetic_series("SHY", ["50"] * 199)) is None

    null_leg = build(
        experiment["experiment_id"], dict(parameters, defensive_symbol=None), ("SPY", "SHY")
    )
    series = {"SPY": synthetic_series("SPY", ["100"] * 199 + ["80"]), "SHY": shy}
    assert null_leg.target(view_at(series, session), context(session)) is None
