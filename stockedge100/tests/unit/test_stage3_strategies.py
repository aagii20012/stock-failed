"""Stage 3 — the sealed protocol, the five indicators, the thirty runs, the seven conditions.

Every number asserted below is hand-computed from the sealed rule, not read back from the code that
produced it. Where a threshold is compared, the fixture sits exactly on the boundary and one cent
either side of it, because "no worse than 15%" and "at least 1.10" are inclusive and an off-by-one
in either direction changes a verdict.

Two things this file deliberately proves that the stage's own result does not:

* **PASS is reachable.** ``test_a_synthetic_candidate_can_be_admitted`` builds a candidate that
  satisfies all seven conditions and asserts ``admitted`` is True and the stage token is the pass
  token. Stage 3's FAIL is then a finding about six strategies, not an evaluator that can only say
  no.
* **The digests are pinned independently of the freeze record.** The constants below were written
  out by hand from the sealed files. Rewriting an artifact and its ``.sha256`` record together still
  fails here.

Nothing in this module writes anywhere. The dataset is never loaded: a full Stage 3 run is thirty
backtests over three decades and belongs in the evidence file, not in a unit suite. Family behaviour
is checked on synthetic bars where the expected order is obvious by inspection.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import shutil
from decimal import Decimal
from pathlib import Path

import pytest

from stockedge100.audit import sha256_file, sha256_text_canonical_json
from stockedge100.backtest.config import load_stage2_config
from stockedge100.backtest.costs import BASE, ZERO, CostModel
from stockedge100.backtest.dataset import Bar, series_from_rows
from stockedge100.backtest.engine import DecisionContext, EquityPoint
from stockedge100.backtest.errors import ConfigViolation
from stockedge100.backtest.market import MarketView
from stockedge100.backtest.orders import BUY, SELL
from stockedge100.backtest.portfolio import Trade
from stockedge100.backtest.window import ResearchWindow, development_window
from stockedge100.reporting import stage3_evidence
from stockedge100.strategies import config as stage3_config
from stockedge100.strategies import families, gate, indicators, runner
from stockedge100.strategies.base import Candidate

# -- what was sealed, pinned by hand ---------------------------------------------------------------
#
# Written out from the sealed files, not copied from STAGE_3_PREREGISTRATION.sha256. A rewrite of an
# artifact together with its freeze record leaves these unchanged and therefore still fails.

SEALED_DIGESTS = {
    "config/stage3_gate_criteria.json":
        "310f1c978380f4a1d6b98b8c368975b1515476b032c123afb06f1dd597e3e18d",
    "config/stage3_strategy_protocol.json":
        "04dbe3fa8c6b2a9e725a66d24f5dc0a3a7e3567e70d38bfd2e96869cc6e169b6",
    "governance/STAGE_3_PREREGISTRATION.json":
        "09cfc5a89918a0baf013bc89dfc86bd9243940cefee5c2a8a93f833ceb20794b",
    "governance/STAGE_3_PREREGISTRATION.md":
        "a257e862377938d42584147d3aedb1a2ba493b0f9f1f22f079745b953314526f",
    "governance/STAGE_3_PREREGISTRATION.sha256":
        "ab97fd0718e2364947410698a58f44b5c924f74d9e7edf4ac4ce65929840f62b",
}

#: The three files ``preregistered_files`` lists, and therefore the three the loader recomputes on
#: every load. The seal record itself and its ``.sha256`` companion are deliberately absent: nothing
#: may hash itself, so those two are covered by the surrounding freeze record instead.
PREREGISTERED_FILES = {
    rel: digest
    for rel, digest in SEALED_DIGESTS.items()
    if not rel.startswith("governance/STAGE_3_PREREGISTRATION.json")
    and not rel.endswith(".sha256")
}

EVIDENCE_REL = "reports/stage3/STAGE_3_DEVELOPMENT_ADMISSIBILITY.json"
EVIDENCE_DIGEST = "561628d2f058d162c785bd30803df5b1762a4168af5037ee95d8b58bce896874"

REPORT_REL = "governance/STAGE_3_STRATEGY_RESEARCH_REPORT.md"

#: Every 64-hex value the Stage 3 report is allowed to contain. ``repo_state_id`` is not among them
#: and must never be: it covers ``governance/*.md``, so writing it into a governance report
#: invalidates it on write.
REPORT_ALLOWED_DIGESTS = set(SEALED_DIGESTS.values()) | {EVIDENCE_DIGEST}

EXPERIMENT_IDS = (
    "SE100-S3-F1-TREND-SMA200",
    "SE100-S3-F2-PULLBACK-SMA200-SMA10",
    "SE100-S3-F3-MEANREV-RSI2",
    "SE100-S3-F4-BREAKOUT-DONCHIAN-50-25",
    "SE100-S3-F5-ROTATION-DUALMOM",
    "SE100-S3-F6-DEFENSIVE-SMA200-SHY",
)

#: ``warmup_sessions`` as sealed, per experiment. ``plan_candidate`` recomputes these from the
#: parameters and refuses to plan a candidate where the two disagree; this table is the independent
#: copy that makes that check meaningful.
SEALED_WARMUP = {
    "SE100-S3-F1-TREND-SMA200": 250,
    "SE100-S3-F2-PULLBACK-SMA200-SMA10": 250,
    "SE100-S3-F3-MEANREV-RSI2": 101,
    "SE100-S3-F4-BREAKOUT-DONCHIAN-50-25": 100,
    "SE100-S3-F5-ROTATION-DUALMOM": 316,
    "SE100-S3-F6-DEFENSIVE-SMA200-SHY": 250,
}

DAY_ZERO = dt.date(2000, 1, 3)


# -- fixtures --------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def stage3():
    return stage3_config.load_stage3_config()


@pytest.fixture(scope="module")
def criteria(stage3):
    return stage3.criteria


@pytest.fixture(scope="module")
def costs() -> CostModel:
    return CostModel(load_stage2_config().cost_model, BASE)


@pytest.fixture(scope="module")
def evidence(project_root: Path):
    return json.loads((project_root / EVIDENCE_REL).read_text(encoding="utf-8"))


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


def bars(*closes: str, start: dt.date = DAY_ZERO) -> list[Bar]:
    return [bar(start + dt.timedelta(days=i), close) for i, close in enumerate(closes)]


def synthetic_series(symbol: str, closes: dict[dt.date, str]):
    rows = [
        {"session": session.isoformat(), "open": close, "close": close, "split_ratio": "1"}
        for session, close in sorted(closes.items())
    ]
    return series_from_rows(symbol, rows)


def trade(pnl: str, *, symbol: str = "SPY", index: int = 0) -> Trade:
    """A closed round trip whose P&L is exactly ``pnl``. Costs are already inside the cash legs."""

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
    shutdown: dt.date | None = None,
):
    """A :class:`BacktestResult` assembled by hand.

    The gate reads five things and nothing else: ``equity_curve``, ``starting_equity``,
    ``final_equity``, ``trades`` and ``open_positions``. Building those directly keeps a condition
    test a test of the condition rather than of the engine, which Stage 2 already covers.
    """

    from stockedge100.backtest.engine import BacktestResult

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
        shutdown_session=shutdown,
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
    """One ``(VariantSpec, BacktestResult | None)`` pair for S3-C7."""

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


# -- the seal --------------------------------------------------------------------------------------


def test_sealed_files_still_hash_to_the_pinned_values(project_root: Path):
    for rel, expected in SEALED_DIGESTS.items():
        assert sha256_file(project_root / rel) == expected, rel


def test_preregistration_records_the_ordering_that_is_the_evidence(project_root: Path):
    prereg = json.loads(
        (project_root / "governance/STAGE_3_PREREGISTRATION.json").read_text(encoding="utf-8")
    )
    assert prereg["document_id"] == "SE100-GOV-0006"
    assert prereg["record_type"] == "PRE_REGISTRATION"
    assert prereg["status"] == "SEALED"
    assert prereg["gate"]["constitutional_gate"] == 3
    assert prereg["gate"]["name"] == "development_admissibility"
    assert prereg["sealed_before_any_strategy_code"] is True
    assert prereg["strategy_modules_present_at_seal_time"] == 0
    assert len(prereg["gate"]["pass_conditions"]) == 7
    assert prereg["gate"]["fail_result"] == "STRATEGY_REJECTED_IN_DEVELOPMENT"


def test_loader_recomputes_every_sealed_digest(stage3):
    assert stage3.digests == PREREGISTERED_FILES
    assert "governance/STAGE_3_PREREGISTRATION.json" not in stage3.digests
    assert "governance/STAGE_3_PREREGISTRATION.sha256" not in stage3.digests


def test_loader_refuses_a_drifted_configuration(tmp_path: Path, monkeypatch, project_root: Path):
    """The claim Stage 3 rests on is that the parameters predate the code. Drift falsifies it."""

    for rel in SEALED_DIGESTS:
        destination = tmp_path / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(project_root / rel, destination)
    monkeypatch.setattr(stage3_config, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        stage3_config, "PREREGISTRATION_JSON", tmp_path / "governance/STAGE_3_PREREGISTRATION.json"
    )
    assert stage3_config.load_stage3_config().digests == PREREGISTERED_FILES

    protocol = tmp_path / "config/stage3_strategy_protocol.json"
    protocol.write_text(protocol.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(ConfigViolation) as excinfo:
        stage3_config.load_stage3_config()
    assert "has changed since it was sealed" in str(excinfo.value)


def test_dec_refuses_a_float():
    assert stage3_config.dec("1.1") == Decimal("1.1")
    with pytest.raises(ConfigViolation):
        stage3_config.dec(1.1)


# -- the five sealed indicators ----------------------------------------------------------------------


def test_sma_is_the_mean_of_the_last_n_closes():
    window = bars("10", "20", "30", "40")
    assert indicators.sma(window, 4) == Decimal(25)
    assert indicators.sma(window, 2) == Decimal(35)
    assert indicators.sma(window, 5) is None
    assert indicators.sma(window, 0) is None


def test_rolling_extremes_include_the_bar_at_t():
    window = bars("10", "50", "30")
    assert indicators.rolling_max_close(window, 3) == Decimal(50)
    assert indicators.rolling_min_close(window, 3) == Decimal(10)
    assert indicators.rolling_max_close(window, 2) == Decimal(50)
    assert indicators.rolling_min_close(window, 2) == Decimal(30)
    assert indicators.rolling_max_close(window, 4) is None


def test_momentum_reads_adj_close_not_close():
    """A flat ``close`` with a rising ``adj_close`` is exactly a dividend-paying instrument."""

    window = [
        bar(DAY_ZERO, "50", adj_close="100"),
        bar(DAY_ZERO + dt.timedelta(days=1), "50", adj_close="110"),
    ]
    assert indicators.momentum(window, 1) == Decimal("0.1")
    assert indicators.momentum(window, 2) is None


def test_momentum_needs_n_plus_one_bars():
    window = bars("100", "110", "121")
    assert indicators.momentum(window, 2) == Decimal("0.21")
    assert indicators.momentum(window, 3) is None


def test_wilder_rsi_boundary_values():
    assert indicators.wilder_rsi(bars("100", "101", "102"), 2, 2) == Decimal(100)
    assert indicators.wilder_rsi(bars("100", "100", "100"), 2, 2) == Decimal(50)
    assert indicators.wilder_rsi(bars("100", "99", "98"), 2, 2) == Decimal(0)


def test_wilder_rsi_seed_only():
    """closes 100,102,100 → avgGain 1, avgLoss 1 → 100 − 100/(1+1) = 50."""

    assert indicators.wilder_rsi(bars("100", "102", "100"), 2, 2) == Decimal(50)
    # closes 100,106,104 → avgGain 3, avgLoss 1 → 100 − 100/(1+3) = 75
    assert indicators.wilder_rsi(bars("100", "106", "104"), 2, 2) == Decimal(75)


def test_wilder_rsi_smoothing_branch():
    """closes 100,104,100,104 with warmup 3: seed (2, 2), then one smoothing step to (3, 1) → 75."""

    assert indicators.wilder_rsi(bars("100", "104", "100", "104"), 2, 3) == Decimal(75)


def test_wilder_rsi_is_undefined_without_the_full_seeding_distance():
    assert indicators.wilder_rsi(bars("100", "104", "100"), 2, 3) is None
    assert indicators.wilder_rsi(bars("100", "104", "100"), 3, 2) is None
    assert indicators.wilder_rsi(bars("100", "104", "100"), 0, 2) is None


# -- the thirty declared runs --------------------------------------------------------------------


def test_the_sealed_protocol_declares_exactly_six_experiments(stage3):
    assert tuple(entry["experiment_id"] for entry in stage3.experiments) == EXPERIMENT_IDS
    assert tuple(sorted(families.FAMILY_CLASSES)) == tuple(sorted(EXPERIMENT_IDS))


def test_variant_specs_enumerate_thirty_runs_and_no_more(stage3):
    total = 0
    for experiment in stage3.experiments:
        specs = runner.variant_specs(experiment)
        assert len(specs) == 5
        assert specs[0].role == runner.PRIMARY
        assert [spec.role for spec in specs[1:]] == [runner.NEIGHBOUR] * 4
        assert len({spec.variant_id for spec in specs}) == 5
        total += len(specs)
    assert total == 30
    assert stage3.protocol["iteration_budget"]["total_declared_runs"] == 30
    assert stage3.protocol["iteration_budget"]["revisions_permitted"] == 0


def test_neighbours_inherit_the_primary_parameters_they_do_not_override(stage3):
    experiment = stage3.experiment("SE100-S3-F3-MEANREV-RSI2")
    specs = runner.variant_specs(experiment)
    primary = specs[0].parameters
    for spec in specs[1:]:
        assert set(spec.parameters) == set(primary)
        differing = {k for k in primary if spec.parameters[k] != primary[k]}
        assert differing, f"{spec.variant_id} is identical to the primary"


def test_recomputed_warmup_matches_the_seal_for_every_experiment(stage3):
    definitions = stage3.indicator_definitions
    for experiment in stage3.experiments:
        specs = runner.variant_specs(experiment)
        sealed = SEALED_WARMUP[experiment["experiment_id"]]
        assert experiment["warmup_sessions"] == sealed
        assert runner.largest_lookback(specs, definitions) == sealed


def test_rotation_warmup_counts_the_bar_n_sessions_back(stage3):
    """MOM(315) consumes 316 visible bars, which is why F5's sealed warm-up is 316 and not 315."""

    definitions = stage3.indicator_definitions
    specs = runner.variant_specs(stage3.experiment("SE100-S3-F5-ROTATION-DUALMOM"))
    assert max(int(spec.parameters["momentum_lookback"]) for spec in specs) == 315
    assert runner.largest_lookback(specs, definitions) == 316


def test_rsi_warmup_is_the_seeding_distance_not_the_period(stage3):
    definitions = stage3.indicator_definitions
    specs = runner.variant_specs(stage3.experiment("SE100-S3-F3-MEANREV-RSI2"))
    assert max(int(spec.parameters["rsi_period"]) for spec in specs) == 3
    assert int(definitions["RSI"]["warmup_changes"]) == 100
    assert runner.largest_lookback(specs, definitions) == 101


def test_traded_symbols_is_narrower_than_the_declared_universe_for_the_defensive_family(stage3):
    experiment = stage3.experiment("SE100-S3-F6-DEFENSIVE-SMA200-SHY")
    assert tuple(experiment["universe"]) == ("SPY", "SHY")
    specs = runner.variant_specs(experiment)
    by_id = {spec.variant_id: spec for spec in specs}
    assert by_id["SE100-S3-F6-DEFENSIVE-SMA200-SHY#PRIMARY"].symbols == ("SHY", "SPY")
    cash_variant = [spec for spec in specs if spec.parameters.get("defensive_symbol") is None]
    assert len(cash_variant) == 1
    assert cash_variant[0].symbols == ("SPY",)


def test_run_start_is_the_latest_of_the_per_symbol_qualifying_sessions():
    window = ResearchWindow(name="test", start=dt.date(2000, 1, 1), end=dt.date(2000, 2, 1))
    early = {DAY_ZERO + dt.timedelta(days=i): "100" for i in range(10)}
    late = {DAY_ZERO + dt.timedelta(days=i): "100" for i in range(3, 13)}
    series = {
        "AAA": synthetic_series("AAA", early),
        "BBB": synthetic_series("BBB", late),
    }
    session, binding = runner.run_start_for(["AAA", "BBB"], 3, window, series)
    assert session == DAY_ZERO + dt.timedelta(days=5)
    assert binding == "BBB"

    session, binding = runner.run_start_for(["AAA"], 3, window, series)
    assert session == DAY_ZERO + dt.timedelta(days=2)
    assert binding == "AAA"


def test_run_start_counts_only_sessions_inside_the_window():
    """Sealed ``warmup_data_source``: warm-up is drawn only from inside the development window."""

    window = ResearchWindow(
        name="test", start=DAY_ZERO + dt.timedelta(days=5), end=dt.date(2000, 2, 1)
    )
    closes = {DAY_ZERO + dt.timedelta(days=i): "100" for i in range(12)}
    series = {"AAA": synthetic_series("AAA", closes)}
    session, _ = runner.run_start_for(["AAA"], 3, window, series)
    assert session == DAY_ZERO + dt.timedelta(days=7)


def test_run_start_refuses_a_symbol_with_too_little_history():
    window = ResearchWindow(name="test", start=dt.date(2000, 1, 1), end=dt.date(2000, 2, 1))
    series = {"AAA": synthetic_series("AAA", {DAY_ZERO: "100"})}
    with pytest.raises(ConfigViolation):
        runner.run_start_for(["AAA"], 3, window, series)


def test_the_protocol_names_no_excluded_symbol(stage3):
    excluded = set(stage3.protocol["excluded_symbols"])
    assert "AAPL" in excluded
    assert not set(runner.required_symbols(stage3)) & excluded


# -- the seven conditions --------------------------------------------------------------------------


def test_condition_1_positive_net_return(criteria):
    assert gate.condition_1(result(equity=["100", "101"]), criteria).verdict == gate.MET
    assert gate.condition_1(result(equity=["100", "100"]), criteria).verdict == gate.NOT_MET
    assert gate.condition_1(result(equity=["100", "99"]), criteria).verdict == gate.NOT_MET
    short = gate.condition_1(result(equity=["100"]), criteria)
    assert short.verdict == gate.NOT_EVALUABLE
    assert short.satisfied is False


def test_condition_2_is_inclusive_at_exactly_fifteen_percent(criteria):
    """(100 − 85) / 100 = 0.15 exactly. "no worse than 15%" admits the boundary."""

    at_limit = gate.condition_2(result(equity=["100", "100", "85"]), criteria)
    assert at_limit.verdict == gate.MET
    assert at_limit.measured == "0.15"
    assert at_limit.threshold == "<= 0.15"

    beyond = gate.condition_2(result(equity=["100", "100", "84.99"]), criteria)
    assert beyond.verdict == gate.NOT_MET


def test_condition_2_reports_the_research_shutdown_session(criteria):
    stop = dt.date(2001, 9, 21)
    verdict = gate.condition_2(result(equity=["100", "80"], shutdown=stop), criteria)
    assert verdict.evidence["research_shutdown_session"] == "2001-09-21"


def test_condition_3_is_inclusive_at_one_point_one(criteria):
    assert gate.condition_3(result(pnls=["11", "-10"]), criteria).verdict == gate.MET
    assert gate.condition_3(result(pnls=["109", "-100"]), criteria).verdict == gate.NOT_MET


def test_condition_3_undefined_cases(criteria):
    no_trades = gate.condition_3(result(pnls=[]), criteria)
    assert no_trades.verdict == gate.NOT_EVALUABLE
    assert no_trades.satisfied is False

    no_losses = gate.condition_3(result(pnls=["5", "3"]), criteria)
    assert no_losses.verdict == gate.MET
    assert no_losses.note.startswith("UNDEFINED_NO_LOSSES_TREATED_AS_MET")

    nothing_either_way = gate.condition_3(result(pnls=["0", "0"]), criteria)
    assert nothing_either_way.verdict == gate.NOT_EVALUABLE


def test_condition_4_counts_closed_trades_only(criteria):
    twenty_nine = gate.condition_4(result(pnls=["1"] * 29), criteria)
    assert twenty_nine.verdict == gate.NOT_MET
    assert twenty_nine.measured == "29"

    thirty = gate.condition_4(result(pnls=["1"] * 30), criteria)
    assert thirty.verdict == gate.MET
    assert thirty.evidence["exception_invoked"] is False


def test_condition_5_removes_the_best_trade_by_both_readings(criteria):
    """pnls 100, 200, 100 from 100 → multiples 2, 2, 1.25; realized 4; either removal leaves 1.5.

    The evidence strings are compared as :class:`~decimal.Decimal` rather than as text. Decimal
    carries an exponent, so the product 2 × 2 × 1.25 formats as ``"5.00"`` and the return as
    ``"4.00"``; the trailing zeros are an artifact of the ideal-exponent rule and asserting them
    would be asserting the formatter, not the rule.
    """

    verdict = gate.condition_5(result(pnls=["100", "200", "100"]), criteria)
    assert verdict.verdict == gate.MET
    assert Decimal(verdict.evidence["reconstructed_total_return"]) == Decimal(4)
    assert verdict.evidence["j1_largest_equity_multiple"]["trade_index"] == 0
    assert Decimal(verdict.evidence["j1_largest_equity_multiple"]["removed_return"]) == Decimal("1.5")
    assert verdict.evidence["j2_largest_absolute_pnl"]["trade_index"] == 1
    assert Decimal(verdict.evidence["j2_largest_absolute_pnl"]["removed_return"]) == Decimal("1.5")


def test_condition_5_fails_when_one_trade_carries_the_result(criteria):
    """pnls 150, −100 from 100 → 0.5 headline, but −0.4 once the winner is removed."""

    verdict = gate.condition_5(result(pnls=["150", "-100"]), criteria)
    assert verdict.verdict == gate.NOT_MET
    assert Decimal(verdict.evidence["reconstructed_total_return"]) == Decimal("0.5")
    assert verdict.evidence["j1_equals_j2"] is True
    assert Decimal(verdict.evidence["j1_largest_equity_multiple"]["removed_return"]) == Decimal("-0.4")


def test_condition_5_needs_at_least_two_trades(criteria):
    assert gate.condition_5(result(pnls=["50"]), criteria).verdict == gate.NOT_EVALUABLE
    assert gate.condition_5(result(pnls=[]), criteria).verdict == gate.NOT_EVALUABLE


def test_condition_5_refuses_a_reconstruction_that_reaches_zero_equity(criteria):
    verdict = gate.condition_5(result(pnls=["-100", "50"]), criteria)
    assert verdict.verdict == gate.NOT_EVALUABLE
    assert "zero or negative equity" in verdict.note


def test_condition_6_does_not_apply_to_a_single_instrument(criteria):
    verdict = gate.condition_6(result(pnls=["10", "10"]), plan(("SPY",)), criteria)
    assert verdict.verdict == gate.NOT_APPLICABLE
    assert verdict.satisfied is True


def test_condition_6_is_inclusive_at_fifty_percent(criteria):
    even = result(trades=[trade("50", symbol="SPY"), trade("50", symbol="IEF", index=1)])
    verdict = gate.condition_6(even, plan(("SPY", "IEF")), criteria)
    assert verdict.verdict == gate.MET
    assert verdict.measured == "0.5"

    lopsided = result(trades=[trade("60", symbol="SPY"), trade("40", symbol="IEF", index=1)])
    verdict = gate.condition_6(lopsided, plan(("SPY", "IEF")), criteria)
    assert verdict.verdict == gate.NOT_MET
    assert verdict.evidence["largest_contributor"] == "SPY"


def test_condition_6_is_not_evaluable_without_positive_total_profit(criteria):
    losing = result(trades=[trade("-30", symbol="SPY"), trade("10", symbol="IEF", index=1)])
    verdict = gate.condition_6(losing, plan(("SPY", "IEF")), criteria)
    assert verdict.verdict == gate.NOT_EVALUABLE
    assert verdict.satisfied is False


def test_condition_7_requires_all_four_neighbours_to_agree(criteria):
    primary = result(equity=["100", "150"])
    matching = [neighbour(i, "0.2") for i in range(1, 5)]
    verdict = gate.condition_7(primary, matching, criteria)
    assert verdict.verdict == gate.MET
    assert verdict.measured == "4/4 neighbours match"

    reversed_sign = matching[:3] + [neighbour(4, "-0.2")]
    assert gate.condition_7(primary, reversed_sign, criteria).verdict == gate.NOT_MET


def test_condition_7_treats_exact_zero_as_matching_nothing(criteria):
    primary = result(equity=["100", "150"])
    flat_neighbour = [neighbour(i, "0.2") for i in range(1, 4)] + [neighbour(4, "0")]
    assert gate.condition_7(primary, flat_neighbour, criteria).verdict == gate.NOT_MET

    flat_primary = result(equity=["100", "100"])
    verdict = gate.condition_7(flat_primary, [neighbour(i, "0") for i in range(1, 5)], criteria)
    assert verdict.verdict == gate.NOT_MET
    assert verdict.evidence["primary_sign"] == 0


def test_condition_7_counts_an_unrun_neighbour_as_a_failure(criteria):
    primary = result(equity=["100", "150"])
    with_gap = [neighbour(i, "0.2") for i in range(1, 4)] + [neighbour(4, None)]
    verdict = gate.condition_7(primary, with_gap, criteria)
    assert verdict.verdict == gate.NOT_MET
    assert verdict.evidence["neighbours_not_run"] == ["SE100-S3-TEST#N4"]


# -- combination -------------------------------------------------------------------------------------


def test_a_verdict_outside_the_sealed_four_is_refused():
    with pytest.raises(ConfigViolation):
        gate.ConditionVerdict("S3-C1", "required", "BORDERLINE")
    assert gate.VERDICT_VALUES == (
        gate.MET,
        gate.NOT_MET,
        gate.NOT_EVALUABLE,
        gate.NOT_APPLICABLE,
    )


def test_not_evaluable_is_not_a_pass():
    assert gate.ConditionVerdict("S3-C1", "r", gate.MET).satisfied is True
    assert gate.ConditionVerdict("S3-C1", "r", gate.NOT_APPLICABLE).satisfied is True
    assert gate.ConditionVerdict("S3-C1", "r", gate.NOT_EVALUABLE).satisfied is False
    assert gate.ConditionVerdict("S3-C1", "r", gate.NOT_MET).satisfied is False


def admissible_candidate():
    """Twenty wins of +2 then ten losses of −1, on a curve that never falls more than 7.2%.

    C1 0.30 > 0; C2 (140 − 130) / 140 = 0.0714…; C3 40 / 10 = 4; C4 exactly 30 trades;
    C5 1.3 / 1.02 − 1 = 0.2745…; C6 single instrument; C7 four positive neighbours.
    """

    pnls = ["2"] * 20 + ["-1"] * 10
    return result(pnls=pnls)


def test_a_synthetic_candidate_can_be_admitted(criteria):
    verdicts = gate.evaluate_candidate(
        plan=plan(("SPY",)),
        primary=admissible_candidate(),
        neighbours=[neighbour(i, "0.1") for i in range(1, 5)],
        criteria=criteria,
    )
    assert verdicts["admitted"] is True
    assert verdicts["conditions_not_met"] == []
    assert verdicts["conditions_not_evaluable"] == []
    assert verdicts["conditions_not_applicable"] == ["S3-C6"]
    assert verdicts["conditions_met"] == 6

    stage = gate.stage_verdict([verdicts], criteria)
    assert stage["verdict"] == "PASS"
    assert stage["pass_token"] == "STAGE_3_STRATEGY_ADMITTED_IN_DEVELOPMENT"
    assert stage["admitted_candidates"] == ["SE100-S3-TEST"]


def test_one_failed_condition_rejects_the_whole_candidate(criteria):
    """Gates are conjunctive; the candidate above with a single drawdown breach is rejected."""

    # The curve ends at 110, not 100: a final equity equal to the start would also fail S3-C1 and
    # the assertion below would then be satisfied by the wrong condition.
    breached = admissible_candidate()
    verdicts = gate.evaluate_candidate(
        plan=plan(("SPY",)),
        primary=result(
            trades=list(breached.trades), equity=["100", "140", "110"]
        ),
        neighbours=[neighbour(i, "0.1") for i in range(1, 5)],
        criteria=criteria,
    )
    assert verdicts["admitted"] is False
    assert verdicts["conditions_not_met"] == ["S3-C2"]


def test_the_stage_verdict_is_a_disjunction_across_candidates(criteria):
    admitted = {"experiment_id": "A", "family": "f", "admitted": True}
    rejected = {"experiment_id": "B", "family": "f", "admitted": False}
    assert gate.stage_verdict([rejected, rejected], criteria)["verdict"] == "FAIL"
    assert gate.stage_verdict([rejected, admitted], criteria)["verdict"] == "PASS"
    assert gate.stage_verdict([], criteria)["verdict"] == "FAIL"

    fail = gate.stage_verdict([rejected], criteria)
    assert fail["fail_token"] == "STAGE_3_STRATEGY_REJECTED_IN_DEVELOPMENT"
    assert fail["admitted_candidates"] == []


def test_thresholds_are_checked_against_the_seal_before_anything_is_evaluated(criteria):
    gate.check_thresholds_against_seal(criteria)
    assert gate.CONCENTRATION_MAX == Decimal("0.50")
    thresholds = criteria["frozen_gate_json_companion_verbatim"]["thresholds"]
    assert thresholds == {
        "net_return_positive": True,
        "max_drawdown_pct": 15,
        "profit_factor_min": 1.1,
        "closed_trades_min": 30,
        "best_trade_removed_return_positive": True,
    }


def test_profit_factor_threshold_never_passes_through_a_float(criteria):
    """1.1 as a binary double is 1.1000000000000000888…; the gate must compare the written 1.1."""

    assert gate._threshold(1.1) == Decimal("1.1")
    assert gate._threshold(1.1) != Decimal(1.1)
    exactly = gate.condition_3(result(pnls=["11", "-10"]), criteria)
    assert exactly.measured == "1.1"
    assert exactly.verdict == gate.MET


# -- the families on synthetic bars ------------------------------------------------------------------


def view_at(series: dict, session: dt.date) -> MarketView:
    """A view bounded at ``session``. The window is wide because it is not what is under test here;
    ``MarketView.history`` drops any bar outside it, so a narrow one would silently empty the
    synthetic series rather than fail visibly."""

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


def build(experiment_id: str, parameters: dict, universe: tuple[str, ...], costs: CostModel):
    return families.build_candidate(
        experiment_id=experiment_id,
        variant_id=f"{experiment_id}#TEST",
        universe=universe,
        parameters=parameters,
        costs=costs,
        indicator_definitions={"RSI": {"warmup_changes": 2}},
    )


def spy_series(closes: list[str]):
    return {
        "SPY": synthetic_series(
            "SPY", {DAY_ZERO + dt.timedelta(days=i): value for i, value in enumerate(closes)}
        )
    }


def test_trend_family_targets_the_symbol_only_above_its_average(costs):
    series = spy_series(["10", "20", "30", "40", "100"])
    candidate = build("SE100-S3-F1-TREND-SMA200", {"sma_long": 4}, ("SPY",), costs)
    day = DAY_ZERO + dt.timedelta(days=4)
    # SMA(4) over 20,30,40,100 = 47.5; close 100 > 47.5
    assert candidate.target(view_at(series, day), context(day)) == "SPY"

    below = spy_series(["100", "100", "100", "100", "10"])
    day = DAY_ZERO + dt.timedelta(days=4)
    assert build("SE100-S3-F1-TREND-SMA200", {"sma_long": 4}, ("SPY",), costs).target(
        view_at(below, day), context(day)
    ) is None


def test_insufficient_history_sends_the_session_to_cash(costs):
    series = spy_series(["10", "20"])
    candidate = build("SE100-S3-F1-TREND-SMA200", {"sma_long": 4}, ("SPY",), costs)
    day = DAY_ZERO + dt.timedelta(days=1)
    assert candidate.target(view_at(series, day), context(day)) is None


def test_bars_at_refuses_a_stale_tail(costs):
    """No bar at t means no close(t), and every sealed rule references close(t)."""

    series = spy_series(["10", "20", "30", "40"])
    candidate = build("SE100-S3-F1-TREND-SMA200", {"sma_long": 4}, ("SPY",), costs)
    gap = DAY_ZERO + dt.timedelta(days=10)
    view = view_at(series, gap)
    assert len(view.history("SPY", 4)) == 4
    assert candidate.bars_at(view, "SPY", gap, 4) == []
    assert candidate.target(view, context(gap)) is None


def test_pullback_family_needs_both_legs(costs):
    candidate = build(
        "SE100-S3-F2-PULLBACK-SMA200-SMA10", {"sma_long": 4, "sma_short": 2}, ("SPY",), costs
    )
    # closes 10,20,30,40,50 → SMA(4)=35, SMA(2)=45; close 50 > 35 but not < 45 → cash
    series = spy_series(["10", "20", "30", "40", "50"])
    day = DAY_ZERO + dt.timedelta(days=4)
    assert candidate.target(view_at(series, day), context(day)) is None

    # closes 10,20,30,80,40 → SMA(4)=42.5, SMA(2)=60; 40 < 42.5 → cash on the long leg
    series = spy_series(["10", "20", "30", "80", "40"])
    assert candidate.target(view_at(series, day), context(day)) is None

    # closes 10,20,30,40,44 → SMA(4)=33.5, SMA(2)=42; 44 > 33.5 but 44 > 42 → cash
    series = spy_series(["10", "20", "30", "40", "44"])
    assert candidate.target(view_at(series, day), context(day)) is None

    # closes 10,10,10,100,41 → SMA(4)=40.25, SMA(2)=70.5; 41 > 40.25 and 41 < 70.5 → SPY
    series = spy_series(["10", "10", "10", "100", "41"])
    assert candidate.target(view_at(series, day), context(day)) == "SPY"


def test_mean_reversion_branches_on_the_account_position(costs):
    candidate = build(
        "SE100-S3-F3-MEANREV-RSI2",
        {"rsi_period": 2, "rsi_entry_below": 60, "exit_sma": 2},
        ("SPY",),
        costs,
    )
    # flat, closes 100,102,100 → RSI 50 < 60 → enter
    series = spy_series(["100", "102", "100"])
    day = DAY_ZERO + dt.timedelta(days=2)
    assert candidate.target(view_at(series, day), context(day)) == "SPY"

    # holding, SMA(2) over 102,100 = 101; close 100 is not above it → keep holding
    assert candidate.target(view_at(series, day), context(day, ("SPY",))) == "SPY"

    # holding, closes 100,100,104 → SMA(2) = 102; close 104 > 102 → exit to cash
    series = spy_series(["100", "100", "104"])
    assert candidate.target(view_at(series, day), context(day, ("SPY",))) is None


def test_donchian_comparisons_are_inclusive(costs):
    candidate = build(
        "SE100-S3-F4-BREAKOUT-DONCHIAN-50-25",
        {"entry_lookback": 3, "exit_lookback": 2},
        ("SPY",),
        costs,
    )
    # flat, closes 10,20,30 → MAXCLOSE(3) = 30 and close == 30 → enter on equality
    series = spy_series(["10", "20", "30"])
    day = DAY_ZERO + dt.timedelta(days=2)
    assert candidate.target(view_at(series, day), context(day)) == "SPY"

    # holding, closes 30,20,10 → MINCLOSE(2) = 10 and close == 10 → exit on equality
    series = spy_series(["30", "20", "10"])
    assert candidate.target(view_at(series, day), context(day, ("SPY",))) is None

    # holding, closes 10,20,30 → MINCLOSE(2) = 20, close 30 > 20 → hold
    series = spy_series(["10", "20", "30"])
    assert candidate.target(view_at(series, day), context(day, ("SPY",))) == "SPY"


def test_defensive_family_reads_the_regime_from_spy_only(costs):
    parameters = {"sma_long": 2, "risk_symbol": "SPY", "defensive_symbol": "SHY"}
    candidate = build("SE100-S3-F6-DEFENSIVE-SMA200-SHY", parameters, ("SPY", "SHY"), costs)
    sessions = [DAY_ZERO + dt.timedelta(days=i) for i in range(3)]
    series = {
        "SPY": synthetic_series("SPY", dict(zip(sessions, ["100", "100", "120"]))),
        "SHY": synthetic_series("SHY", dict(zip(sessions, ["50", "50", "50"]))),
    }
    day = sessions[2]
    # SMA(2) over 100,120 = 110; close 120 > 110 → risk on
    assert candidate.target(view_at(series, day), context(day)) == "SPY"

    series["SPY"] = synthetic_series("SPY", dict(zip(sessions, ["100", "100", "80"])))
    assert candidate.target(view_at(series, day), context(day)) == "SHY"

    # the defensive leg has no bar at t → cash, never a stale defensive price
    series["SHY"] = synthetic_series("SHY", dict(zip(sessions[:2], ["50", "50"])))
    assert candidate.target(view_at(series, day), context(day)) is None

    cash_variant = build(
        "SE100-S3-F6-DEFENSIVE-SMA200-SHY",
        {**parameters, "defensive_symbol": None},
        ("SPY", "SHY"),
        costs,
    )
    assert cash_variant.target(view_at(series, day), context(day)) is None


def test_rotation_ranks_only_on_a_rebalance_session(costs):
    parameters = {
        "momentum_lookback": 1,
        "rebalance": families.MONTHLY_REBALANCE,
        "top_n": 1,
    }
    candidate = build("SE100-S3-F5-ROTATION-DUALMOM", parameters, ("AAA", "BBB"), costs)
    assert candidate.is_rebalance(dt.date(2015, 1, 30)) is True
    assert candidate.is_rebalance(dt.date(2015, 1, 29)) is False

    sessions = [dt.date(2015, 1, 29), dt.date(2015, 1, 30)]
    series = {
        "AAA": synthetic_series("AAA", dict(zip(sessions, ["100", "110"]))),
        "BBB": synthetic_series("BBB", dict(zip(sessions, ["100", "105"]))),
    }
    view = view_at(series, sessions[1])
    assert candidate.rank_target(view, context(sessions[1])) == "AAA"

    # both below zero momentum → cash, not "least bad"
    falling = {
        "AAA": synthetic_series("AAA", dict(zip(sessions, ["100", "90"]))),
        "BBB": synthetic_series("BBB", dict(zip(sessions, ["100", "95"]))),
    }
    assert candidate.rank_target(view_at(falling, sessions[1]), context(sessions[1])) is None


def test_rotation_defers_the_buy_to_the_next_flat_session(costs):
    """The sealed flat-first rule: an exit and an entry never share a session."""

    parameters = {
        "momentum_lookback": 1,
        "rebalance": families.MONTHLY_REBALANCE,
        "top_n": 1,
    }
    candidate = build("SE100-S3-F5-ROTATION-DUALMOM", parameters, ("AAA", "BBB"), costs)
    sessions = [dt.date(2015, 1, 29), dt.date(2015, 1, 30), dt.date(2015, 2, 2)]
    series = {
        "AAA": synthetic_series("AAA", dict(zip(sessions, ["100", "110", "111"]))),
        "BBB": synthetic_series("BBB", dict(zip(sessions, ["100", "105", "106"]))),
    }
    rebalance = sessions[1]
    orders = candidate.decide(view_at(series, rebalance), context(rebalance, ("BBB",)))
    assert [(order.symbol, order.side) for order in orders] == [("BBB", SELL)]
    assert candidate.pending_target == "AAA"

    later = sessions[2]
    orders = candidate.decide(view_at(series, later), context(later))
    assert [(order.symbol, order.side) for order in orders] == [("AAA", BUY)]


def test_the_shared_rules_never_emit_a_sell_and_a_buy_together(costs):
    """Both legs at once would make the outcome depend on the alphabetical order of the tickers."""

    class Rotator(Candidate):
        def target(self, view, ctx):
            return "IEF"

    candidate = Rotator(
        experiment_id="TEST",
        variant_id="TEST#1",
        universe=("SPY", "IEF"),
        parameters={},
        costs=costs,
    )
    orders = candidate.decide(None, context(DAY_ZERO, ("SPY",)))
    assert [(order.symbol, order.side) for order in orders] == [("SPY", SELL)]

    orders = candidate.decide(None, context(DAY_ZERO))
    assert [(order.symbol, order.side) for order in orders] == [("IEF", BUY)]
    assert orders[0].budget == Decimal("95.00")

    assert candidate.decide(None, context(DAY_ZERO, ("IEF",))) == []


# -- the evidence file -------------------------------------------------------------------------------


def test_evidence_digest_covers_exactly_what_the_file_says_it_covers(evidence):
    """Recomputed from the written file, following its own coverage sentence literally.

    A wrong-but-stable coverage description survives a two-run determinism check, so stability is
    not a substitute for this. Stage 2 shipped one and paid for it with a full regeneration.
    """

    assert evidence["evidence_digest"] == EVIDENCE_DIGEST
    assert evidence["evidence_digest_covers"] == stage3_evidence.DIGEST_COVERS
    recomputed = sha256_text_canonical_json(
        {
            key: value
            for key, value in evidence.items()
            if key not in stage3_evidence.EXCLUDED_FROM_DIGEST
        }
    )
    assert recomputed == EVIDENCE_DIGEST


def test_the_documented_exclusion_is_not_vacuous(evidence):
    """Negative control: if generated_utc were covered, the digest would be a different value."""

    with_timestamp = sha256_text_canonical_json(
        {key: value for key, value in evidence.items() if key != "evidence_digest"}
    )
    assert with_timestamp != EVIDENCE_DIGEST


def test_the_evidence_records_thirty_runs_and_no_revision(evidence):
    budget = evidence["iteration_budget"]
    assert budget["runs_executed"] == 30
    assert budget["total_declared_runs"] == 30
    assert budget["candidates_evaluated"] == 6
    assert budget["revisions_permitted"] == 0
    assert budget["revisions_made"] == 0
    assert budget["candidates_rerun_after_seeing_a_result"] == 0
    assert len(evidence["candidates"]) == 6
    for candidate in evidence["candidates"]:
        assert len(candidate["runs"]) == 5


def test_every_primary_reproduced_itself_on_a_rerun(evidence):
    assert evidence["determinism"]["all_identical"] is True
    assert len(evidence["determinism"]["runs"]) == 6
    for entry in evidence["determinism"]["runs"]:
        assert entry["trades_digest"] == entry["rerun_trades_digest"]
        assert entry["equity_digest"] == entry["rerun_equity_digest"]


def test_the_evidence_read_the_development_window_only(evidence):
    # ``ResearchWindow.to_json`` names the field ``window``, not ``name``. Assert what the artifact
    # says, not the spelling that reads better.
    assert evidence["window"]["window"] == development_window().name
    assert evidence["window"]["start"] == "1993-01-29"
    assert evidence["window"]["end"] == "2021-07-31"
    assert evidence["window"]["validation_and_holdout_read"] is False
    for candidate in evidence["candidates"]:
        assert candidate["plan"]["run_end"] == "2021-07-31"
        assert candidate["plan"]["run_start"] >= "1993-01-29"


def test_the_evidence_records_the_sealed_digests_it_recomputed(evidence):
    assert evidence["sealed_inputs"]["digests_recomputed_at_load"] == PREREGISTERED_FILES
    assert evidence["sealed_inputs"]["preregistration"] == "SE100-GOV-0006"


def test_the_stage_verdict_in_the_evidence_is_a_rejection(evidence):
    verdict = evidence["stage_verdict"]
    assert verdict["verdict"] == "FAIL"
    assert verdict["admitted_candidates"] == []
    assert verdict["candidates_evaluated"] == 6
    assert verdict["fail_token"] == "STAGE_3_STRATEGY_REJECTED_IN_DEVELOPMENT"
    assert all(entry["admitted"] is False for entry in evidence["gate_summary"])


def test_every_candidate_breached_the_drawdown_ceiling(evidence):
    """The dominant cause, and the one the seal anticipated: S3-C2 trips the §5.1 shutdown."""

    for entry in evidence["gate_summary"]:
        assert "S3-C2" in entry["conditions_not_met"], entry["experiment_id"]
    for candidate in evidence["candidates"]:
        primary = candidate["runs"][candidate["plan"]["experiment_id"] + "#PRIMARY"]
        assert primary["shutdown_session"] is not None
        assert Decimal(primary["max_drawdown"]) > Decimal("0.15")


def test_no_benchmark_is_gating(evidence):
    for candidate in evidence["candidates"]:
        assert candidate["benchmarks"]["gating"] is False
        assert candidate["benchmark_comparison"]["gating"] is False


def test_the_evidence_authorizes_nothing(evidence):
    assert evidence["live_trading_authorized"] is False
    assert evidence["no_selection_in_this_stage"]
    assert evidence["explicit_non_authorizations"]


# -- the report ---------------------------------------------------------------------------------------


def test_the_report_embeds_no_tree_digest(project_root: Path):
    """``repo_state_id`` covers ``governance/*.md``, so a report that carried it would invalidate
    it on write. The predicate tests for the *value*, not for the field name: Stage 1 checked the
    name and passed a file that would have failed."""

    text = (project_root / REPORT_REL).read_text(encoding="utf-8")
    assert "repo_state_id" not in text
    found = set(re.findall(r"\b[0-9a-f]{64}\b", text))
    assert found <= REPORT_ALLOWED_DIGESTS, sorted(found - REPORT_ALLOWED_DIGESTS)


def test_the_report_states_the_verdict_and_the_document_id(project_root: Path):
    text = (project_root / REPORT_REL).read_text(encoding="utf-8")
    assert "SE100-GOV-3000" in text
    assert "FAIL — STAGE_3_STRATEGY_REJECTED_IN_DEVELOPMENT" in text
    assert "live_trading_authorized" in text
