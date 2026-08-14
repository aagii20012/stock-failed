"""Stage 2 — the engine end to end, and the four Gate 2 conditions as tests rather than as claims.

The unit file checks the parts and the adversarial file checks that a broken part is caught. This
file runs the whole engine and asserts the sealed conditions:

1. deterministic reruns produce identical trades and equity curves
2. the twelve defect classes each name a test that exists in the file supposed to hold it
3. independent hand-calculated fixtures match engine output
4. benchmark calculations reconcile

Conditions 1, 3 and 4 are asserted twice over: once directly against the engine, and once against
:mod:`stockedge100.backtest.harness`, which is what the Stage 2 report will quote. The second form
matters because the report must not be allowed to quote a boolean that was true only because the
harness never actually compared anything — so every harness assertion below reaches past the summary
flag to the digests, counts, and differences underneath it.

The sealed expectations are read from ``config/stage2_engine_spec.json`` rather than restated. That
file was written and sealed before any engine code existed and its digest is checked on load, so it
*is* the hand calculation; a literal copied out of it here would only be a second chance to typo it.
Nothing in this file writes to `config/`, `data/`, `governance/`, or `reports/`.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from stockedge100.backtest import benchmarks as bm
from stockedge100.backtest import harness as harness_module
from stockedge100.backtest.config import load_stage2_config
from stockedge100.backtest.costs import BASE, CostModel, SCENARIOS, STRESSED, ZERO
from stockedge100.backtest.dataset import PriceSeries, load_dataset, series_from_rows
from stockedge100.backtest.engine import BacktestEngine, DecisionContext, OrderRequest
from stockedge100.backtest.errors import InvariantViolation
from stockedge100.backtest.fixtures import (
    ENTRY_DECISION,
    EXIT_DECISION,
    FIXT,
    expected,
    fixt_probe,
    fixt_series,
    fixt_sessions,
    fixt_window,
)
from stockedge100.backtest.harness import (
    DEFECT_TEST_FILE,
    defect_evidence,
    fixture_evidence,
    run_all,
)
from stockedge100.backtest.orders import BUY, Order, REASONS, SELL, make_order_id
from stockedge100.backtest.probes import AlwaysCashProbe, DECLARED_PROBES
from stockedge100.backtest.window import ResearchWindow, development_window

FIRST = dt.date(2015, 1, 2)
LAST = dt.date(2015, 1, 13)
OTHER = "FIXU"


def d(text: str) -> dt.date:
    return dt.date.fromisoformat(text)


@pytest.fixture(scope="module")
def config():
    return load_stage2_config()


@pytest.fixture(scope="module")
def evidence():
    """One full harness run, shared by every test that quotes it.

    It takes about fourteen seconds, because it runs the engine over twenty-eight years of SPY
    several times over. Running it once per test would make the suite unpleasant enough to stop
    being run, and a suite nobody runs is not a regression floor.
    """
    return run_all()


def sealed_rows(config) -> list[dict]:
    return [dict(row) for row in config.engine_spec["hand_calculated_fixtures"]["instrument"]["sessions"]]


def rows_priced(config, price_by_session: dict[str, str]) -> list[dict]:
    """The sealed FIXT bars with named sessions flattened to one price. The sealed file is untouched.

    Flattening also clears the dividend on that session: these variants exist to move equity, and a
    dividend left in would move it for a second reason.
    """
    rows = []
    for row in sealed_rows(config):
        price = price_by_session.get(row["session"])
        if price is not None:
            row.update(open=price, high=price, low=price, close=price, dividend="0.00")
        rows.append(row)
    return rows


def fixt_run(config, scenario: str, *, probe=None, series=None, start=FIRST, end=LAST, **kwargs):
    costs = CostModel(config.cost_model, scenario)
    engine = BacktestEngine(
        series if series is not None else {FIXT: fixt_series(config)},
        costs,
        fixt_window(),
        probe if probe is not None else fixt_probe(costs.starting_equity),
        start=start,
        end=end,
        label=f"INTEGRATION_{scenario}",
        **kwargs,
    )
    return engine.run()


class ScriptedProbe:
    """Submits exactly what a table says, on exactly the sessions the table names.

    A probe that decided anything from a price would make the run a strategy, and Stage 2 has no
    authority to produce one. This one cannot: it never looks at the market view it is handed.
    """

    name = "PROBE_FIXED_SCHEDULE"

    def __init__(self, script: dict[dt.date, list[OrderRequest]]) -> None:
        self.script = script

    def decide(self, view, context: DecisionContext) -> list[OrderRequest]:
        return list(self.script.get(context.session, []))


def fills_by_side(result, side: str):
    return [record for record in result.fills if record.fill.side == side]


def equity_on(result, session: dt.date):
    return next(point for point in result.equity_curve if point.session == session)


# --------------------------------------------------------------------------------------------
# Gate 2 condition 3 — the hand calculation, line by line
# --------------------------------------------------------------------------------------------


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_the_fixture_run_matches_the_sealed_hand_calculation_line_by_line(config, scenario):
    """Every number the sealed spec commits to, against the number the engine produced.

    The sealed file carries a derivation for each of these — ``94.99 / 100.05`` rounded down to nine
    places, and so on. Asserting only the final equity would let two compensating errors through.
    """
    sealed = expected(scenario, config)
    instrument = config.engine_spec["hand_calculated_fixtures"]["instrument"]
    result = fixt_run(config, scenario)

    assert result.scenario == sealed["cost_scenario"] == scenario
    assert result.starting_equity == Decimal(sealed["starting_equity"])

    entry = fills_by_side(result, BUY)
    exit_ = fills_by_side(result, SELL)
    assert len(entry) == len(exit_) == 1
    assert entry[0].session == d(instrument["expected_entry_fill_session"])
    assert exit_[0].session == d(instrument["expected_exit_fill_session"])

    e, se = entry[0].fill, sealed["entry"]
    assert e.reference_price == Decimal(se["reference_price"])
    assert e.effective_price == Decimal(se["effective_price"])
    assert e.quantity == Decimal(se["quantity"])
    assert e.gross_notional == Decimal(se["charged_notional"])
    assert -e.cash_delta == Decimal(se["charged_notional"])
    assert equity_on(result, entry[0].session).cash == Decimal(se["cash_after"])
    assert equity_on(result, d("2015-01-07")).equity == Decimal(
        sealed["mark_2015_01_07_close"]["equity"]
    )

    div, sd = result.dividend_events, sealed["dividend_2015_01_08"]
    assert len(div) == 1 and div[0]["session"] == "2015-01-08"
    assert Decimal(div[0]["cash_credited"]) == Decimal(sd["cash_credited"])
    assert equity_on(result, d("2015-01-08")).cash == Decimal(sd["cash_after"])
    assert equity_on(result, d("2015-01-08")).equity == Decimal(
        sealed["mark_2015_01_08_close"]["equity"]
    )

    x, sx = exit_[0].fill, sealed["exit"]
    assert x.reference_price == Decimal(sx["reference_price"])
    assert x.effective_price == Decimal(sx["effective_price"])
    assert x.quantity == Decimal(se["quantity"])  # the whole position leaves; no dust is retained
    if "quantity" in sx:  # BASE restates it on the exit line; STRESSED carries it once, on the entry
        assert x.quantity == Decimal(sx["quantity"])
    assert x.gross_notional == Decimal(sx["gross_proceeds"])
    assert x.sec_fee == Decimal(sx["sec_section_31_fee"])
    assert x.taf_fee == Decimal(sx["finra_taf"])
    assert x.cash_delta == Decimal(sx["net_proceeds"])
    assert equity_on(result, exit_[0].session).cash == Decimal(sx["cash_after"])

    final = sealed["final"]
    assert result.final_cash == Decimal(final["final_cash"])
    assert result.final_equity == Decimal(final["final_equity"])
    assert result.total_return() == Decimal(final["total_return"])
    assert len(result.trades) == final["closed_trades"]
    assert result.open_positions == []
    assert result.rejections == []


def test_the_entry_pays_no_regulatory_fee_and_the_exit_pays_both(config):
    """Section 31 and the TAF are sell-side charges; a buy that paid them would be over-costed."""
    sealed = expected(BASE, config)
    result = fixt_run(config, BASE)
    entry = fills_by_side(result, BUY)[0].fill
    assert entry.sec_fee == entry.taf_fee == Decimal(sealed["entry"]["regulatory_fees"]) == ZERO
    assert entry.commission == Decimal(sealed["entry"]["commission"])
    exit_ = fills_by_side(result, SELL)[0].fill
    assert exit_.sec_fee > ZERO and exit_.taf_fee > ZERO


def test_the_stressed_scenario_leaves_the_account_worse_off_than_the_base_one(config):
    """A stress that changed nothing would be a stress in name only."""
    base = fixt_run(config, BASE)
    stressed = fixt_run(config, STRESSED)
    assert stressed.final_equity < base.final_equity
    assert stressed.final_equity == Decimal(expected(STRESSED, config)["final"]["final_cash"])
    # Same schedule, same sessions: only the cost assumption differs.
    assert [f.session for f in stressed.fills] == [f.session for f in base.fills]


def test_the_closed_trade_reconciles_against_its_own_legs(config):
    """The sealed derivation is ``113.85 + 0.47 − 94.99``; the trade must agree with its own parts."""
    sealed = expected(BASE, config)
    trade = fixt_run(config, BASE).trades[0]
    assert trade.entry_session == d("2015-01-07")
    assert trade.exit_session == d("2015-01-09")
    assert trade.entry_cash == Decimal(sealed["entry"]["charged_notional"])
    assert trade.exit_cash == Decimal(sealed["exit"]["net_proceeds"])
    assert trade.dividends == Decimal(sealed["dividend_2015_01_08"]["cash_credited"])
    assert trade.pnl == trade.exit_cash + trade.dividends - trade.entry_cash
    assert trade.pnl == Decimal(sealed["final"]["trade_pnl"])


def test_a_decision_never_fills_on_its_own_session(config):
    """The sealed schedule decides at two closes and fills at the two following opens."""
    result = fixt_run(config, BASE)
    sessions = [f.session for f in result.fills]
    assert sessions == [d("2015-01-07"), d("2015-01-09")]
    assert ENTRY_DECISION not in sessions and EXIT_DECISION not in sessions
    # The decision session is the first ten characters of the order id, by construction.
    assert all(f.session > d(f.order_id[:10]) for f in result.fills)


def test_the_equity_curve_covers_every_exchange_session_in_the_window(config):
    """One point per session, in order, with no gap and no duplicate."""
    result = fixt_run(config, BASE)
    sessions = [point.session for point in result.equity_curve]
    assert sessions == sorted(sessions) == list(fixt_sessions(config))
    assert len(set(sessions)) == len(sessions) == 8
    assert result.stale_marks == 0


# --------------------------------------------------------------------------------------------
# Gate 2 condition 1 — determinism
# --------------------------------------------------------------------------------------------


def test_a_rerun_of_the_fixture_produces_identical_trades_and_equity(config):
    first, second = fixt_run(config, BASE), fixt_run(config, BASE)
    assert first.trades_digest() == second.trades_digest()
    assert first.equity_digest() == second.equity_digest()
    assert first.trades_payload() == second.trades_payload()
    assert first.equity_payload() == second.equity_payload()


def test_the_digest_discriminates_between_runs_that_really_differ(config):
    """A digest that came out equal for everything would make the rerun check unfalsifiable."""
    base, stressed = fixt_run(config, BASE), fixt_run(config, STRESSED)
    assert base.trades_digest() != stressed.trades_digest()
    assert base.equity_digest() != stressed.equity_digest()


def test_the_digest_carries_no_run_identity(config):
    """No label, no path, no timestamp — otherwise two identical runs would never compare equal."""
    payload = repr(fixt_run(config, BASE).trades_payload())
    assert "INTEGRATION" not in payload
    assert dt.date.today().isoformat() not in payload


def test_the_result_does_not_depend_on_the_order_the_symbols_were_supplied_in(config):
    """Two symbols, same data, opposite insertion order. Iteration order is not a trading fact."""
    series = fixt_series(config)
    other = series_from_rows(OTHER, sealed_rows(config))
    forward = fixt_run(config, BASE, series={FIXT: series, OTHER: other})
    reverse = fixt_run(config, BASE, series={OTHER: other, FIXT: series})
    assert forward.trades_digest() == reverse.trades_digest()
    assert forward.equity_digest() == reverse.equity_digest()
    assert forward.symbols == reverse.symbols == (FIXT, OTHER)


def test_deleting_every_bar_after_the_run_end_changes_nothing(config):
    """The empirical look-ahead check: data the engine never legitimately sees cannot matter.

    The market view refuses a forward read structurally. This would catch a leak that went round it.
    """
    end = d("2015-01-09")
    full = fixt_series(config)
    truncated = PriceSeries(
        symbol=FIXT,
        bars={day: bar for day, bar in full.bars.items() if day <= end},
        sessions=tuple(day for day in full.sessions if day <= end),
    )
    assert len(full) - len(truncated) == 2

    with_future = fixt_run(config, BASE, series={FIXT: full}, end=end)
    without = fixt_run(config, BASE, series={FIXT: truncated}, end=end)
    assert with_future.trades_digest() == without.trades_digest()
    assert with_future.equity_digest() == without.equity_digest()


def test_the_harness_determinism_evidence_compares_real_digests(evidence):
    """Reach past ``all_identical`` to the digests it was computed from."""
    determinism = evidence["determinism"]
    assert determinism["declared_probes"] == list(DECLARED_PROBES)
    assert len(determinism["cases"]) >= len(SCENARIOS) + 3
    for case in determinism["cases"]:
        assert len(case["trades_digest_run_1"]) == 64
        assert len(case["equity_digest_run_1"]) == 64
        assert case["trades_digest_run_1"] == case["trades_digest_run_2"], case["case"]
        assert case["equity_digest_run_1"] == case["equity_digest_run_2"], case["case"]
        assert case["identical"] is True
    assert determinism["all_identical"] is True
    # Distinct runs must not collapse to one digest, or the comparison proves nothing.
    assert len({case["trades_digest_run_1"] for case in determinism["cases"]}) > 1


def test_the_harness_truncation_check_actually_removed_bars(evidence):
    """A truncation check that deleted nothing would pass against an engine that peeks."""
    truncation = evidence["look_ahead_truncation"]
    assert truncation["bars_removed"] > 0
    assert truncation["trades_digest_full"] == truncation["trades_digest_truncated"]
    assert truncation["equity_digest_full"] == truncation["equity_digest_truncated"]
    assert truncation["identical"] is True


# --------------------------------------------------------------------------------------------
# Gate 2 condition 4 — benchmark reconciliation
# --------------------------------------------------------------------------------------------


def test_the_two_spy_total_return_methods_agree_within_the_sealed_tolerance(config, evidence):
    index = evidence["benchmarks"]["spy_total_return"]
    tolerance = Decimal(config.engine_spec["benchmark_reconciliation"]["relative_tolerance"])
    assert Decimal(index["relative_difference"]) <= tolerance
    assert evidence["benchmarks"]["reconciles"] is True
    # Both methods must have done real work. A window with no dividends and no growth would
    # reconcile trivially and would mean nothing.
    assert index["dividend_count"] > 100
    assert Decimal(index["method_a_adj_close_ratio"]) > Decimal(1)
    assert Decimal(index["final_shares_per_one_initial"]) > Decimal(1)


def test_the_identity_holds_on_a_sub_window_as_well_as_the_whole_series(config):
    """The factors for ex-dates after the window end cancel in the ratio, so it has to.

    A reconciliation that only ever held on one window would be consistent with a constant that
    happened to fit that window.

    The identity is between the two *growth factors* — ``shares · close_end/close_start`` and
    ``adj_end/adj_start`` — and this test is stated on those, deliberately. The sealed condition
    divides by the return instead, and over the full window, where the return is about 16, the two
    framings are within a rounding of each other. Over five years, where the return is 0.0246, that
    denominator is forty times smaller than the quantity actually being compared, so the same
    agreement reads as a forty-times-larger relative difference. Dividing by the return would be
    measuring how short the window is, not whether the engine reconciles. The sealed 1e-6 is applied
    unchanged; only the denominator is the one the identity is about.
    """
    series = load_dataset(("SPY",))["SPY"]
    tolerance = Decimal(config.engine_spec["benchmark_reconciliation"]["relative_tolerance"])
    for start, end in ((d("2005-01-03"), d("2009-12-31")), (d("2015-01-02"), d("2016-12-30"))):
        sub = ResearchWindow(name=development_window().name, start=start, end=end)
        index = bm.spy_total_return(series, sub)
        growth_a, growth_b = Decimal(1) + index.method_a, Decimal(1) + index.method_b
        difference = abs(growth_a - growth_b) / growth_a
        assert difference <= tolerance, f"{start}..{end}: {difference:E}"
        assert index.dividend_count > 0
        assert index.final_shares > Decimal(1)


def test_the_flat_benchmarks_return_exactly_zero_not_approximately_zero(evidence):
    assert Decimal(evidence["benchmarks"]["cash_benchmark"]["total_return"]) == ZERO
    assert Decimal(evidence["benchmarks"]["do_nothing_benchmark"]["total_return"]) == ZERO
    assert evidence["benchmarks"]["cash_benchmark_returns_exactly_zero"] is True
    assert evidence["benchmarks"]["do_nothing_benchmark_returns_exactly_zero"] is True


def test_a_probe_that_never_trades_leaves_the_equity_curve_flat(config):
    """The control for the whole engine: no order, no cost, no movement of any kind."""
    result = fixt_run(config, BASE, probe=AlwaysCashProbe())
    starting = CostModel(config.cost_model, BASE).starting_equity
    assert {point.equity for point in result.equity_curve} == {starting}
    assert {point.cash for point in result.equity_curve} == {starting}
    assert result.fills == [] and result.trades == [] and result.rejections == []


def test_a_tradable_hundred_dollar_account_stays_below_the_index_under_both_readings(evidence):
    """Costs, the cash buffer, and un-reinvested dividends can only subtract from the index."""
    tradable = evidence["benchmarks"]["tradable_spy_buy_and_hold"]
    for variant in ("with_research_shutdown", "without_research_shutdown"):
        assert tradable[variant]["strictly_less_than_index"] is True, variant
        assert Decimal(tradable[variant]["total_return"]) > ZERO, variant
    assert tradable["with_research_shutdown"]["research_shutdown_session"] is not None
    assert evidence["benchmarks"]["additional_checks_all_pass"] is True


# --------------------------------------------------------------------------------------------
# Gate 2 condition 2 — the defect evidence names tests that exist
# --------------------------------------------------------------------------------------------


def test_every_declared_defect_class_names_tests_that_exist(config):
    """The report may not claim a class is covered without naming the test that covers it.

    The names are read out of the adversarial file, so a renamed or deleted test fails here instead
    of leaving the evidence quoting a node id nobody runs.
    """
    body = defect_evidence(config)
    declared = {entry["id"] for entry in config.engine_spec["defect_classes"]["classes"]}
    assert {entry["id"] for entry in body["classes"]} == declared
    assert body["declared_class_count"] == len(declared) == 12

    source = (harness_module.PROJECT_ROOT / DEFECT_TEST_FILE).read_text(encoding="utf-8")
    for entry in body["classes"]:
        assert entry["tests"], entry["id"]
        for node in entry["tests"]:
            path, _, name = node.partition("::")
            assert path == DEFECT_TEST_FILE
            assert f"def {name}(" in source, node
    assert body["clean_controls"], "the sealed standard requires the clean engine to pass as well"


def test_the_defect_evidence_refuses_to_report_a_class_with_no_test(config, tmp_path, monkeypatch):
    """A declared class with no probe is an untested claim, and must not be writable as evidence."""
    (tmp_path / "stub_defects.py").write_text(
        "def test_look_ahead_only_this_one():\n    pass\n", encoding="utf-8"
    )
    monkeypatch.setattr(harness_module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(harness_module, "DEFECT_TEST_FILE", "stub_defects.py")
    with pytest.raises(InvariantViolation, match="has no test"):
        defect_evidence(config)


def test_the_defect_evidence_refuses_a_missing_test_file(config, tmp_path, monkeypatch):
    monkeypatch.setattr(harness_module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(harness_module, "DEFECT_TEST_FILE", "not_written_yet.py")
    with pytest.raises(InvariantViolation, match="does not exist"):
        defect_evidence(config)


# --------------------------------------------------------------------------------------------
# The sealed rejection catalogue, reached through a real run
# --------------------------------------------------------------------------------------------


def test_every_sealed_rejection_reason_is_in_the_closed_reason_set(config):
    """The sealed catalogue and the code's closed set must not drift apart in either direction."""
    cases = config.engine_spec["hand_calculated_fixtures"]["FIXT_REJECTIONS"]["cases"]
    for case in cases:
        assert case["expected_reason"] in REASONS, case["case"]
    assert len(cases) == 7


def test_an_entry_in_a_second_symbol_is_rejected_at_the_sealed_position_limit(config):
    """MAX_POSITIONS: constitution §5 allows one open risky position, and the engine holds to it."""
    series = {FIXT: fixt_series(config), OTHER: series_from_rows(OTHER, sealed_rows(config))}
    probe = ScriptedProbe({
        ENTRY_DECISION: [OrderRequest(symbol=FIXT, side=BUY, budget=Decimal("100.00"))],
        d("2015-01-07"): [OrderRequest(symbol=OTHER, side=BUY, budget=Decimal("100.00"))],
    })
    result = fixt_run(config, BASE, probe=probe, series=series)
    assert [r.reason for r in result.rejections] == ["MAX_POSITIONS"]
    assert [f.fill.symbol for f in result.fills] == [FIXT]
    # The rejection changed nothing: the account is where the single entry left it.
    assert equity_on(result, d("2015-01-08")).cash == Decimal(
        expected(BASE, config)["dividend_2015_01_08"]["cash_after"]
    )


def test_a_second_entry_in_the_held_symbol_is_rejected_for_cash(config):
    """INSUFFICIENT_CASH: the sealed 5% buffer already exceeds the 5.48 left after the first entry."""
    probe = ScriptedProbe({
        ENTRY_DECISION: [OrderRequest(symbol=FIXT, side=BUY, budget=Decimal("100.00"))],
        d("2015-01-07"): [OrderRequest(symbol=FIXT, side=BUY, budget=Decimal("100.00"), tag="AGAIN")],
    })
    result = fixt_run(config, BASE, probe=probe)
    assert [r.reason for r in result.rejections] == ["INSUFFICIENT_CASH"]
    assert len(fills_by_side(result, BUY)) == 1


def test_an_entry_smaller_than_the_sealed_minimum_notional_is_rejected(config):
    """MIN_NOTIONAL: a trade too small to carry its own fees is refused, not rounded up to fit."""
    costs = CostModel(config.cost_model, BASE)
    tiny = costs.min_order_notional / Decimal(2)
    probe = ScriptedProbe({ENTRY_DECISION: [OrderRequest(symbol=FIXT, side=BUY, budget=tiny)]})
    result = fixt_run(config, BASE, probe=probe)
    assert [r.reason for r in result.rejections] == ["MIN_NOTIONAL"]
    assert result.fills == []
    assert result.final_cash == result.final_equity == costs.starting_equity


def test_selling_a_symbol_that_is_not_held_is_rejected(config):
    """INSUFFICIENT_POSITION: a sale with nothing behind it would create cash out of nowhere."""
    probe = ScriptedProbe({ENTRY_DECISION: [OrderRequest(symbol=FIXT, side=SELL)]})
    result = fixt_run(config, BASE, probe=probe)
    assert [r.reason for r in result.rejections] == ["INSUFFICIENT_POSITION"]
    assert result.final_cash == CostModel(config.cost_model, BASE).starting_equity


def test_a_fill_session_with_no_bar_is_rejected_as_stale(config):
    """STALE_PRICE: the exchange calendar says the session existed, so a missing bar is a data fact."""
    rows = [row for row in sealed_rows(config) if row["session"] != "2015-01-07"]
    result = fixt_run(config, BASE, series={FIXT: series_from_rows(FIXT, rows)})
    assert result.rejections[0].reason == "STALE_PRICE"
    assert result.rejections[0].order.fill_session == d("2015-01-07")
    assert fills_by_side(result, BUY) == []
    assert result.final_cash == CostModel(config.cost_model, BASE).starting_equity


def test_the_research_shutdown_liquidates_and_blocks_every_later_entry(config):
    """RESEARCH_SHUTDOWN: constitution §5.1, reached by a real drawdown rather than by a flag.

    The account enters at 100.05, the price falls to 80.00, and equity crosses the sealed 15%
    drawdown threshold on 2015-01-08. The engine liquidates at the next open and refuses every entry
    after that, whatever the probe asks for.
    """
    costs = CostModel(config.cost_model, BASE)
    collapsed = rows_priced(config, {
        "2015-01-07": "100.00",
        "2015-01-08": "80.00",
        "2015-01-09": "80.00",
        "2015-01-12": "80.00",
        "2015-01-13": "80.00",
    })
    probe = ScriptedProbe({
        ENTRY_DECISION: [OrderRequest(symbol=FIXT, side=BUY, budget=costs.starting_equity)],
        d("2015-01-09"): [
            OrderRequest(symbol=FIXT, side=BUY, budget=costs.starting_equity, tag="RETRY")
        ],
        d("2015-01-12"): [
            OrderRequest(symbol=FIXT, side=BUY, budget=costs.starting_equity, tag="RETRY2")
        ],
    })
    result = fixt_run(config, BASE, probe=probe, series={FIXT: series_from_rows(FIXT, collapsed)})

    assert result.shutdown_session == d("2015-01-08")
    threshold = costs.starting_equity * (Decimal(1) - costs.research_shutdown_drawdown)
    assert equity_on(result, d("2015-01-07")).equity > threshold
    assert equity_on(result, d("2015-01-08")).equity < threshold

    # The liquidation is not a probe decision: it happens whatever the probe wanted.
    liquidation = fills_by_side(result, SELL)
    assert len(liquidation) == 1 and liquidation[0].session == d("2015-01-09")
    assert liquidation[0].order_id.endswith("SELL-SHUTDOWN")
    assert [r.reason for r in result.rejections] == ["RESEARCH_SHUTDOWN", "RESEARCH_SHUTDOWN"]
    assert result.open_positions == []


def test_an_entry_that_reached_execution_after_a_shutdown_is_still_refused(config):
    """The same rule's second gate, checked by calling it directly.

    ``run`` blocks entries at scheduling time, so this branch of ``_execute_buy`` is not reachable
    through the loop; it is defence in depth against a future caller that schedules by another
    route. A defensive branch that is never exercised is not evidence, so it is exercised here.
    """
    costs = CostModel(config.cost_model, BASE)
    engine = BacktestEngine(
        {FIXT: fixt_series(config)}, costs, fixt_window(), fixt_probe(costs.starting_equity),
        start=FIRST, end=LAST, label="SHUTDOWN_SECOND_GATE",
    )
    engine._shutdown_session = ENTRY_DECISION
    order = Order(
        order_id=make_order_id(ENTRY_DECISION, FIXT, BUY),
        symbol=FIXT,
        side=BUY,
        decision_session=ENTRY_DECISION,
        fill_session=d("2015-01-07"),
        budget=costs.starting_equity,
    )
    engine._execute_buy(d("2015-01-07"), order, Decimal("100.00"))

    assert [r.reason for r in engine._rejections] == ["RESEARCH_SHUTDOWN"]
    assert engine.portfolio.cash == costs.starting_equity
    assert engine.portfolio.open_symbols() == ()


# --------------------------------------------------------------------------------------------
# The harness as a whole — what the Stage 2 report will quote
# --------------------------------------------------------------------------------------------


def test_the_evidence_reports_all_four_gate_2_conditions_met(config, evidence):
    assert evidence["artifact_id"] == "SE100-EVID-2001"
    assert evidence["constitution_gate"] == 2
    assert evidence["gate_2_conditions"] == config.engine_spec["gate_2_conditions"]
    assert evidence["engine_spec_version"] == config.engine_spec["version"]
    assert evidence["determinism"]["all_identical"] is True
    assert evidence["look_ahead_truncation"]["identical"] is True
    assert evidence["hand_calculated_fixtures"]["all_match"] is True
    assert evidence["benchmarks"]["reconciles"] is True
    assert evidence["all_conditions_met"] is True


def test_the_summary_flag_is_the_conjunction_of_the_conditions(evidence):
    """``all_conditions_met`` has to follow from the parts; a hardcoded True would prove nothing."""
    assert evidence["all_conditions_met"] == (
        evidence["determinism"]["all_identical"]
        and evidence["look_ahead_truncation"]["identical"]
        and evidence["hand_calculated_fixtures"]["all_match"]
        and evidence["benchmarks"]["reconciles"]
        and evidence["benchmarks"]["additional_checks_all_pass"]
    )


def test_the_fixture_evidence_checks_every_sealed_line_rather_than_the_total(evidence):
    """The harness must be comparing the individual sealed values, not just the final equity."""
    cases = evidence["hand_calculated_fixtures"]["cases"]
    assert {case["scenario"] for case in cases} == set(SCENARIOS)
    for case in cases:
        assert len(case["checks"]) >= 18, case["scenario"]
        assert all(row["matches"] for row in case["checks"])
        assert {row["value"] for row in case["checks"]} >= {
            "entry_fill_session", "entry_quantity", "cash_after_dividend", "exit_taf_fee",
            "final_equity", "total_return",
        }


def test_the_fixture_evidence_is_reproducible_on_a_second_call(config, evidence):
    """The harness is a function of the sealed config, not of when it happened to be called."""
    assert fixture_evidence(config) == evidence["hand_calculated_fixtures"]


def test_the_reference_run_is_labelled_a_probe_and_not_a_result(evidence):
    """Stage 2 has no authority to produce a research result; the evidence says so on its face."""
    reference = evidence["reference_run_metrics"]
    assert reference["label"] == "PROBE_BUY_AND_HOLD_SPY"
    assert "not a research result" in reference["note"]
    assert evidence["hand_calculated_fixtures"]["instrument"].startswith("FIXT (synthetic;")


def test_the_declared_invariants_are_reported_with_their_enforcement(config, evidence):
    invariants = evidence["invariants"]
    assert invariants["declared_invariant_count"] == len(config.engine_spec["invariants"]["list"])
    assert invariants["declared_invariant_count"] > 0
    assert invariants["invariants"] == config.engine_spec["invariants"]["list"]


def test_the_evidence_window_is_the_locked_development_window(evidence):
    """Stage 2 never touches validation or holdout data, and the window it ran on is on the record."""
    window, locked = evidence["window"], development_window()
    assert window["window"] == locked.name == "development"
    assert window["start"] == locked.start.isoformat()
    assert window["end"] == locked.end.isoformat()
