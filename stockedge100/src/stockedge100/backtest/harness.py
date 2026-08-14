"""The Gate 2 evidence harness.

Every claim the Stage 2 report makes about the engine is produced here, by running the engine, and
written to ``reports/stage2/`` as JSON. Nothing in the report is asserted from reading the code.

The four gate conditions map onto the four groups below:

* :func:`determinism_evidence` — identical trades and equity curves on rerun
* :func:`defect_evidence` — the twelve defect classes, each detected by a test
* :func:`fixture_evidence` — hand-calculated fixtures matched exactly
* :func:`benchmark_evidence` — the two SPY total-return methods reconciled

:func:`look_ahead_truncation_evidence` is extra: it deletes every bar after the run end and checks
the results are byte-identical. An engine that peeks cannot pass that, whatever its code looks like.
"""

from __future__ import annotations

import ast
import datetime as dt
from decimal import Decimal
from typing import Any

from stockedge100.backtest import benchmarks as bm
from stockedge100.backtest import fixtures as fx
from stockedge100.backtest.config import PROJECT_ROOT, Stage2Config, load_stage2_config
from stockedge100.backtest.costs import BASE, CostModel, SCENARIOS, STRESSED, ZERO
from stockedge100.backtest.dataset import PriceSeries, load_dataset
from stockedge100.backtest.engine import BacktestEngine, BacktestResult
from stockedge100.backtest.errors import InvariantViolation
from stockedge100.backtest.metrics import summarize
from stockedge100.backtest.probes import AlwaysCashProbe, BuyAndHoldProbe, DECLARED_PROBES
from stockedge100.backtest.window import ResearchWindow, development_window

BENCHMARK_SYMBOL = "SPY"


# ---------------------------------------------------------------------------------------------
# runs
# ---------------------------------------------------------------------------------------------


def _fixt_run(config: Stage2Config, scenario: str) -> BacktestResult:
    costs = CostModel(config.cost_model, scenario)
    sessions = fx.fixt_sessions(config)
    engine = BacktestEngine(
        {fx.FIXT: fx.fixt_series(config)},
        costs,
        fx.fixt_window(),
        fx.fixt_probe(costs.starting_equity),
        start=sessions[0],
        end=sessions[-1],
        label=f"FIXT_{scenario}",
    )
    return engine.run()


def _buy_and_hold_run(
    series: dict[str, PriceSeries], costs: CostModel, window: ResearchWindow
) -> BacktestResult:
    return BacktestEngine(
        series, costs, window, BuyAndHoldProbe(BENCHMARK_SYMBOL, costs.starting_equity),
        label="PROBE_BUY_AND_HOLD_SPY",
    ).run()


def _always_cash_run(
    series: dict[str, PriceSeries], costs: CostModel, window: ResearchWindow
) -> BacktestResult:
    return BacktestEngine(series, costs, window, AlwaysCashProbe(), label="PROBE_ALWAYS_CASH").run()


# ---------------------------------------------------------------------------------------------
# gate condition 1: determinism
# ---------------------------------------------------------------------------------------------


def determinism_evidence(
    config: Stage2Config, series: dict[str, PriceSeries], window: ResearchWindow
) -> dict[str, Any]:
    """Rerun every declared probe and compare the digests of trades and equity curve."""
    costs = CostModel(config.cost_model, BASE)
    cases: list[dict[str, Any]] = []

    def compare(label: str, first: BacktestResult, second: BacktestResult) -> dict[str, Any]:
        return {
            "case": label,
            "trades_digest_run_1": first.trades_digest(),
            "trades_digest_run_2": second.trades_digest(),
            "equity_digest_run_1": first.equity_digest(),
            "equity_digest_run_2": second.equity_digest(),
            "identical": (
                first.trades_digest() == second.trades_digest()
                and first.equity_digest() == second.equity_digest()
            ),
        }

    for scenario in SCENARIOS:
        cases.append(
            compare(f"FIXT_{scenario}", _fixt_run(config, scenario), _fixt_run(config, scenario))
        )
    cases.append(
        compare(
            "PROBE_BUY_AND_HOLD_SPY_development",
            _buy_and_hold_run(series, costs, window),
            _buy_and_hold_run(series, costs, window),
        )
    )
    cases.append(
        compare(
            "PROBE_ALWAYS_CASH_development",
            _always_cash_run(series, costs, window),
            _always_cash_run(series, costs, window),
        )
    )

    # Same data, different dict insertion order. A result that depends on iteration order is not
    # deterministic even though it reruns identically in the same process.
    reordered = {symbol: series[symbol] for symbol in reversed(list(series))}
    cases.append(
        compare(
            "PROBE_BUY_AND_HOLD_SPY_symbols_supplied_in_reverse_order",
            _buy_and_hold_run(series, costs, window),
            _buy_and_hold_run(reordered, costs, window),
        )
    )

    return {
        "condition": "deterministic reruns produce identical trades and equity curves",
        "declared_probes": list(DECLARED_PROBES),
        "cases": cases,
        "all_identical": all(case["identical"] for case in cases),
    }


def look_ahead_truncation_evidence(
    config: Stage2Config, series: dict[str, PriceSeries], window: ResearchWindow
) -> dict[str, Any]:
    """Delete every bar after the run end and check nothing changes.

    This is the empirical form of the look-ahead check. The structural form is
    :class:`~stockedge100.backtest.market.MarketView`, which refuses the request; this one would
    catch a leak that bypassed the view entirely.
    """
    costs = CostModel(config.cost_model, BASE)
    end = dt.date(2000, 12, 29)
    short = ResearchWindow(name=window.name, start=window.start, end=end)

    full = BacktestEngine(
        series, costs, short, BuyAndHoldProbe(BENCHMARK_SYMBOL, costs.starting_equity),
        end=end, label="truncation_full_data",
    ).run()

    truncated_series = {
        symbol: PriceSeries(
            symbol=symbol,
            bars={day: bar for day, bar in s.bars.items() if day <= end},
            sessions=tuple(day for day in s.sessions if day <= end),
        )
        for symbol, s in series.items()
    }
    truncated = BacktestEngine(
        truncated_series, costs, short, BuyAndHoldProbe(BENCHMARK_SYMBOL, costs.starting_equity),
        end=end, label="truncation_future_deleted",
    ).run()

    return {
        "check": "deleting every bar after the run end changes no result",
        "run_end": end.isoformat(),
        "bars_removed": sum(len(series[s]) - len(truncated_series[s]) for s in series),
        "trades_digest_full": full.trades_digest(),
        "trades_digest_truncated": truncated.trades_digest(),
        "equity_digest_full": full.equity_digest(),
        "equity_digest_truncated": truncated.equity_digest(),
        "identical": (
            full.trades_digest() == truncated.trades_digest()
            and full.equity_digest() == truncated.equity_digest()
        ),
    }


# ---------------------------------------------------------------------------------------------
# gate condition 3: hand-calculated fixtures
# ---------------------------------------------------------------------------------------------


def _fixture_case(config: Stage2Config, scenario: str) -> dict[str, Any]:
    result = _fixt_run(config, scenario)
    sealed = fx.expected(scenario, config)
    by_session = {point.session: point for point in result.equity_curve}
    entry = next(f for f in result.fills if f.fill.side == "BUY")
    exit_ = next(f for f in result.fills if f.fill.side == "SELL")
    dividend = result.dividend_events[0]

    checks = [
        ("entry_fill_session", entry.session.isoformat(),
         config.engine_spec["hand_calculated_fixtures"]["instrument"]["expected_entry_fill_session"]),
        ("exit_fill_session", exit_.session.isoformat(),
         config.engine_spec["hand_calculated_fixtures"]["instrument"]["expected_exit_fill_session"]),
        ("entry_effective_price", entry.fill.effective_price, sealed["entry"]["effective_price"]),
        ("entry_quantity", entry.fill.quantity, sealed["entry"]["quantity"]),
        ("entry_charged_notional", entry.fill.gross_notional, sealed["entry"]["charged_notional"]),
        ("cash_after_entry", by_session[entry.session].cash, sealed["entry"]["cash_after"]),
        ("equity_2015_01_07", by_session[dt.date(2015, 1, 7)].equity,
         sealed["mark_2015_01_07_close"]["equity"]),
        ("dividend_cash_credited", dividend["cash_credited"],
         sealed["dividend_2015_01_08"]["cash_credited"]),
        ("cash_after_dividend", by_session[dt.date(2015, 1, 8)].cash,
         sealed["dividend_2015_01_08"]["cash_after"]),
        ("equity_2015_01_08", by_session[dt.date(2015, 1, 8)].equity,
         sealed["mark_2015_01_08_close"]["equity"]),
        ("exit_effective_price", exit_.fill.effective_price, sealed["exit"]["effective_price"]),
        ("exit_gross_proceeds", exit_.fill.gross_notional, sealed["exit"]["gross_proceeds"]),
        ("exit_sec_fee", exit_.fill.sec_fee, sealed["exit"]["sec_section_31_fee"]),
        ("exit_taf_fee", exit_.fill.taf_fee, sealed["exit"]["finra_taf"]),
        ("exit_net_proceeds", exit_.fill.cash_delta, sealed["exit"]["net_proceeds"]),
        ("final_cash", result.final_cash, sealed["final"]["final_cash"]),
        ("final_equity", result.final_equity, sealed["final"]["final_equity"]),
        ("total_return", result.total_return(), sealed["final"]["total_return"]),
        ("closed_trades", len(result.trades), sealed["final"]["closed_trades"]),
    ]
    if "trade_pnl" in sealed["final"]:
        checks.append(("trade_pnl", result.trades[0].pnl, sealed["final"]["trade_pnl"]))

    rows = []
    for name, produced, sealed_value in checks:
        # Compared numerically, not textually: Decimal("119.220") and Decimal("119.22") are the same
        # amount of money, and a test that called them different would be testing the formatter.
        if isinstance(produced, Decimal):
            matches = produced == Decimal(str(sealed_value))
            shown = f"{produced:f}"
        else:
            matches = str(produced) == str(sealed_value)
            shown = str(produced)
        rows.append({"value": name, "engine": shown, "sealed": str(sealed_value), "matches": matches})

    return {
        "scenario": scenario,
        "checks": rows,
        "all_match": all(row["matches"] for row in rows),
    }


def fixture_evidence(config: Stage2Config) -> dict[str, Any]:
    cases = [_fixture_case(config, scenario) for scenario in SCENARIOS]
    return {
        "condition": "independent hand-calculated fixtures match engine output",
        "instrument": "FIXT (synthetic; not a research instrument)",
        "cases": cases,
        "all_match": all(case["all_match"] for case in cases),
    }


# ---------------------------------------------------------------------------------------------
# gate condition 4: benchmark reconciliation
# ---------------------------------------------------------------------------------------------


def benchmark_evidence(
    config: Stage2Config, series: dict[str, PriceSeries], window: ResearchWindow
) -> dict[str, Any]:
    costs = CostModel(config.cost_model, BASE)
    spec = config.engine_spec["benchmark_reconciliation"]
    tolerance = Decimal(spec["relative_tolerance"])

    index = bm.spy_total_return(series[BENCHMARK_SYMBOL], window)
    sessions = len([d for d in series[BENCHMARK_SYMBOL].sessions if window.contains(d)])
    cash = bm.cash_benchmark(sessions, Decimal(config.cost_model["benchmarks"]["cash_benchmark_annual_rate"]))
    nothing = bm.do_nothing_benchmark(sessions)

    tradable = bm.tradable_spy_buy_and_hold(series, costs, window)
    tradable_open = bm.tradable_spy_buy_and_hold(
        series, costs, window, enforce_research_shutdown=False
    )

    always_cash = _always_cash_run(series, costs, window)
    flat = {point.equity for point in always_cash.equity_curve}

    return {
        "condition": "benchmark calculations reconcile",
        "spy_total_return": index.to_json(),
        "relative_tolerance": f"{tolerance:f}",
        "reconciles": index.reconciles(tolerance),
        "cash_benchmark": cash.to_json(),
        "cash_benchmark_returns_exactly_zero": cash.total_return == ZERO,
        "do_nothing_benchmark": nothing.to_json(),
        "do_nothing_benchmark_returns_exactly_zero": nothing.total_return == ZERO,
        "always_cash_probe_equity_is_flat": flat == {costs.starting_equity},
        "always_cash_probe_trades": len(always_cash.trades),
        "tradable_spy_buy_and_hold": {
            "note": (
                "A real USD 100 cash account, not an index. Two variants are reported because "
                "constitution §5.1 places the 15% research shutdown on a strategy and this run is a "
                "benchmark; the sealed check passes under both readings, so the ambiguity does not "
                "affect the gate."
            ),
            "with_research_shutdown": {
                "label": tradable.label,
                "total_return": f"{tradable.total_return():f}",
                "final_equity": f"{tradable.final_equity:f}",
                "research_shutdown_session": (
                    None if tradable.shutdown_session is None
                    else tradable.shutdown_session.isoformat()
                ),
                "fills": len(tradable.fills),
                "strictly_less_than_index": tradable.total_return() < index.method_a,
            },
            "without_research_shutdown": {
                "label": tradable_open.label,
                "total_return": f"{tradable_open.total_return():f}",
                "final_equity": f"{tradable_open.final_equity:f}",
                "fills": len(tradable_open.fills),
                "dividend_events": len(tradable_open.dividend_events),
                "open_positions": tradable_open.open_positions,
                "strictly_less_than_index": tradable_open.total_return() < index.method_a,
                "shortfall_explanation": [
                    "only 94.99 of the 100.00 is ever invested: the sealed 5% cash buffer and the "
                    "budget safety margin are never deployed",
                    "dividends are credited to cash and never reinvested; a re-entry rule would be a "
                    "strategy decision and Stage 2 has no authority to make one",
                    "execution friction: 5 bps each way plus adverse rounding and the sell-side fees",
                ],
            },
        },
        "additional_checks_all_pass": (
            index.reconciles(tolerance)
            and cash.total_return == ZERO
            and nothing.total_return == ZERO
            and flat == {costs.starting_equity}
            and tradable.total_return() < index.method_a
            and tradable_open.total_return() < index.method_a
        ),
    }


# ---------------------------------------------------------------------------------------------
# gate condition 2: the defect classes, and the invariants
# ---------------------------------------------------------------------------------------------


DEFECT_TEST_FILE = "tests/adversarial/test_stage2_defects.py"


def _defect_test_names() -> list[str]:
    """Every ``test_`` function actually defined in the defect probe file, in file order."""
    path = PROJECT_ROOT / DEFECT_TEST_FILE
    if not path.exists():
        raise InvariantViolation(f"the defect probe file {DEFECT_TEST_FILE} does not exist")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [node.name for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")]


def defect_evidence(config: Stage2Config) -> dict[str, Any]:
    """The declared defect classes and where each one is detected.

    The detection itself is a test, not a harness run: a defect probe injects the mutation and
    asserts the engine refuses. This function records the mapping so the report cannot claim a class
    is covered without naming the test that covers it.

    The test names are read out of the file rather than composed from the class id. A composed name
    is a claim about a test; a parsed one is the test. Any class left without a test raises here, so
    the evidence cannot be written with a hole in it.
    """
    classes = config.engine_spec["defect_classes"]["classes"]
    names = _defect_test_names()
    entries = []
    for entry in classes:
        prefix = f"test_{entry['id'].lower()}_"
        matched = [f"{DEFECT_TEST_FILE}::{name}" for name in names if name.startswith(prefix)]
        if not matched:
            raise InvariantViolation(
                f"defect class {entry['id']} has no test in {DEFECT_TEST_FILE}; a declared class "
                "with no probe is an untested claim"
            )
        entries.append({
            "id": entry["id"],
            "mutation": entry["mutation"],
            "detector": entry["detector"],
            "tests": matched,
        })
    controls = [f"{DEFECT_TEST_FILE}::{name}" for name in names if name.startswith("test_control_")]
    return {
        "condition": (
            "tests detect look-ahead, same-close fill, split/dividend, delisting, stale-price, cash, "
            "rounding, fee, slippage, rejected-order, and duplicate-order errors"
        ),
        "declared_class_count": len(classes),
        "classes": entries,
        "clean_controls": controls,
        "control_note": (
            "the sealed standard is that a class is satisfied only if the clean engine passes AND "
            "the mutated engine is caught, so the controls are part of the evidence"
        ),
        "every_class_has_a_test": True,
    }


def invariant_evidence(config: Stage2Config) -> dict[str, Any]:
    return {
        "declared_invariant_count": len(config.engine_spec["invariants"]["list"]),
        "invariants": config.engine_spec["invariants"]["list"],
        "enforcement": (
            "asserted inside the engine on every event, not checked once at the end; the portfolio "
            "reconciles its cash against its ledger after every single movement"
        ),
    }


# ---------------------------------------------------------------------------------------------
# the whole thing
# ---------------------------------------------------------------------------------------------


def run_all(symbols: tuple[str, ...] = (BENCHMARK_SYMBOL,)) -> dict[str, Any]:
    config = load_stage2_config()
    window = development_window()
    series = load_dataset(symbols)
    costs = CostModel(config.cost_model, BASE)

    buy_and_hold = _buy_and_hold_run(series, costs, window)
    metrics_cfg = config.cost_model["metrics"]

    determinism = determinism_evidence(config, series, window)
    truncation = look_ahead_truncation_evidence(config, series, window)
    fixtures = fixture_evidence(config)
    benchmarks = benchmark_evidence(config, series, window)

    return {
        "artifact_id": "SE100-EVID-2001",
        "title": "Stage 2 backtest engine validation evidence",
        "stage": "STAGE_2_BACKTEST_ENGINE",
        "constitution_gate": 2,
        "window": window.to_json(),
        "symbols": list(series),
        "engine_spec_version": config.engine_spec["version"],
        "cost_model_version": config.cost_model["version"],
        "gate_2_conditions": config.engine_spec["gate_2_conditions"],
        "determinism": determinism,
        "look_ahead_truncation": truncation,
        "defect_classes": defect_evidence(config),
        "invariants": invariant_evidence(config),
        "hand_calculated_fixtures": fixtures,
        "benchmarks": benchmarks,
        "reference_run_metrics": {
            "note": (
                "A probe run reported for completeness. It is an engine exercise, not a research "
                "result, and nothing in this stage draws a conclusion from it."
            ),
            "label": buy_and_hold.label,
            **summarize(
                sessions=[p.session for p in buy_and_hold.equity_curve],
                equity=[p.equity for p in buy_and_hold.equity_curve],
                position_counts=[p.position_count for p in buy_and_hold.equity_curve],
                trade_pnls=[t.pnl for t in buy_and_hold.trades],
                trading_days=int(metrics_cfg["trading_days_per_year"]),
                risk_free_annual=Decimal(metrics_cfg["sharpe_risk_free_annual_rate"]),
            ),
            "research_shutdown_session": (
                None if buy_and_hold.shutdown_session is None
                else buy_and_hold.shutdown_session.isoformat()
            ),
        },
        "all_conditions_met": (
            determinism["all_identical"]
            and truncation["identical"]
            and fixtures["all_match"]
            and benchmarks["reconciles"]
            and benchmarks["additional_checks_all_pass"]
        ),
    }
