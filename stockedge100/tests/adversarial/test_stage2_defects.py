"""Stage 2 — one injected defect per sealed error class, and the detector that must catch it.

The sealed spec sets the standard these tests are written to:

    "A class is only satisfied if the clean engine passes AND the mutated engine is caught."

So each test does two things: it runs the clean engine and asserts the correct result, then injects
exactly the mutation the sealed class names and asserts exactly the detector the sealed class names.
A test that only did the second half would pass against an engine that raises on everything.

The three controls at the top exist so a failure below them is attributable to the injected defect
rather than to the fixture. Every mutation is applied to a local object or through ``monkeypatch``;
nothing here writes to `config/`, `data/`, `governance/`, or `reports/`.
"""

from __future__ import annotations

import copy
import datetime as dt
from dataclasses import replace
from decimal import ROUND_CEILING, Decimal

import pytest

from stockedge100.backtest import engine as engine_module
from stockedge100.backtest.config import load_stage2_config
from stockedge100.backtest.costs import BASE, CostModel, ZERO, round_down_cent, round_up_cent
from stockedge100.backtest.dataset import series_from_rows
from stockedge100.backtest.engine import BacktestEngine, DecisionContext, OrderRequest
from stockedge100.backtest.errors import (
    CorporateActionError,
    DataIntegrityHalt,
    DelistingError,
    DuplicateOrderError,
    FillTimingError,
    InvariantViolation,
    LookAheadError,
)
from stockedge100.backtest.fixtures import (
    ENTRY_DECISION,
    EXIT_DECISION,
    FIXT,
    expected,
    fixt_probe,
    fixt_series,
    fixt_window,
)
from stockedge100.backtest.market import MarketView
from stockedge100.backtest.orders import BUY, Order, OrderBook, SELL, make_order_id
from stockedge100.backtest.portfolio import Portfolio
from stockedge100.backtest.probes import FixedScheduleProbe

FIRST = dt.date(2015, 1, 2)
LAST = dt.date(2015, 1, 13)


def d(text: str) -> dt.date:
    return dt.date.fromisoformat(text)


@pytest.fixture(scope="module")
def config():
    return load_stage2_config()


@pytest.fixture(scope="module")
def costs(config):
    return CostModel(config.cost_model, BASE)


@pytest.fixture
def series(config):
    return {FIXT: fixt_series(config)}


@pytest.fixture
def sealed(config):
    return expected(BASE, config)


def run_fixt(series, costs, *, probe=None, start=FIRST, end=LAST, **kwargs):
    engine = BacktestEngine(
        series,
        costs,
        fixt_window(),
        probe or fixt_probe(costs.starting_equity),
        start=start,
        end=end,
        label="DEFECT_PROBE",
        **kwargs,
    )
    return engine.run()


def mutated_rows(config, session: str, **changes) -> list[dict]:
    """The sealed FIXT bars with one session's fields changed. The sealed file is never touched."""
    rows = [dict(row) for row in config.engine_spec["hand_calculated_fixtures"]["instrument"]["sessions"]]
    for row in rows:
        if row["session"] == session:
            row.update(changes)
    return rows


# --------------------------------------------------------------------------------------------
# Controls — the clean engine, before anything is broken
# --------------------------------------------------------------------------------------------


def test_control_the_clean_fixture_run_matches_the_hand_calculation(series, costs, sealed):
    result = run_fixt(series, costs)
    assert result.final_cash == Decimal(sealed["final"]["final_cash"])
    assert result.final_equity == Decimal(sealed["final"]["final_equity"])
    assert len(result.trades) == sealed["final"]["closed_trades"] == 1
    assert result.trades[0].pnl == Decimal(sealed["final"]["trade_pnl"])
    assert result.rejections == []


def test_control_a_correctly_applied_split_leaves_the_share_count_alone(config, costs):
    """The sealed price space is SPLIT_ADJUSTED, so a split session is a non-event for shares."""
    rows = mutated_rows(config, "2015-01-08", split_ratio="2.00")
    result = run_fixt({FIXT: series_from_rows(FIXT, rows)}, costs)
    assert result.final_cash == Decimal(expected(BASE, config)["final"]["final_cash"])


def test_control_a_correctly_applied_dividend_is_credited_once_on_its_ex_date(series, costs, sealed):
    result = run_fixt(series, costs)
    credits = [e for e in result.dividend_events if e["session"] == "2015-01-08"]
    assert len(credits) == 1
    assert credits[0]["cash_credited"] == sealed["dividend_2015_01_08"]["cash_credited"]
    assert [e["session"] for e in result.dividend_events] == ["2015-01-08"]


# --------------------------------------------------------------------------------------------
# LOOK_AHEAD
# --------------------------------------------------------------------------------------------


class PeekingProbe:
    """A probe that asks for the bar it is not allowed to have seen yet."""

    name = "PROBE_PEEKING"

    def __init__(self, symbol: str, peek_at: dt.date) -> None:
        self.symbol = symbol
        self.peek_at = peek_at

    def decide(self, view: MarketView, context: DecisionContext) -> list[OrderRequest]:
        view.bar(self.symbol, self.peek_at)      # the mutation
        return []

    def to_json(self) -> dict[str, str]:
        return {"probe": self.name}


def test_look_ahead_a_probe_reading_tomorrows_bar_is_stopped_by_the_market_view(series, costs):
    probe = PeekingProbe(FIXT, d("2015-01-09"))
    with pytest.raises(LookAheadError, match="bounded at"):
        run_fixt(series, costs, probe=probe)


def test_look_ahead_the_bound_cannot_be_widened_by_the_caller(series):
    view = MarketView(series, d("2015-01-06"), fixt_window())
    with pytest.raises(LookAheadError, match="immutable"):
        view._as_of = d("2015-01-13")
    with pytest.raises(LookAheadError):
        view.bar(FIXT, d("2015-01-07"))


# --------------------------------------------------------------------------------------------
# SAME_CLOSE_FILL
# --------------------------------------------------------------------------------------------


def test_same_close_fill_an_order_filling_at_its_own_decision_close_cannot_be_built():
    with pytest.raises(FillTimingError, match="not strictly after"):
        Order(
            order_id="same", symbol=FIXT, side=BUY,
            decision_session=ENTRY_DECISION, fill_session=ENTRY_DECISION,
            budget=Decimal("95.00"),
        )


def test_same_close_fill_the_engine_refuses_to_execute_one_that_reached_it_anyway(series, costs):
    """Belt and braces: the constructor guard is bypassed, and the loop still catches it."""
    engine = BacktestEngine(series, costs, fixt_window(), fixt_probe(costs.starting_equity),
                            start=FIRST, end=LAST, label="DEFECT_PROBE")
    order = Order(
        order_id="x", symbol=FIXT, side=BUY,
        decision_session=ENTRY_DECISION, fill_session=d("2015-01-07"), budget=Decimal("10.00"),
    )
    object.__setattr__(order, "fill_session", ENTRY_DECISION)      # the mutation
    with pytest.raises(InvariantViolation, match="FILL_AFTER_DECISION"):
        engine._execute_one(ENTRY_DECISION, order)


def test_same_close_fill_the_real_entry_fills_at_the_next_sessions_open(series, costs, config):
    result = run_fixt(series, costs)
    instrument = config.engine_spec["hand_calculated_fixtures"]["instrument"]
    assert result.fills[0].session == d(instrument["expected_entry_fill_session"])
    assert result.fills[0].session > ENTRY_DECISION
    assert result.fills[-1].session == d(instrument["expected_exit_fill_session"])
    assert result.fills[-1].session > EXIT_DECISION


# --------------------------------------------------------------------------------------------
# SPLIT
# --------------------------------------------------------------------------------------------


def test_split_multiplying_the_share_count_on_a_split_session_is_caught(config, costs, monkeypatch):
    """The sealed mutation: share count multiplied by the recorded ratio on an adjusted series."""
    rows = mutated_rows(config, "2015-01-08", split_ratio="2.00")
    series = {FIXT: series_from_rows(FIXT, rows)}

    original = engine_module.BacktestEngine._credit_dividends

    def apply_the_split_twice(self, session):
        original(self, session)
        bar = self.series[FIXT].get(session)
        if bar is not None and bar.has_split and FIXT in self.portfolio.positions:
            position = self.portfolio.positions[FIXT]
            self.portfolio.positions[FIXT] = replace(
                position, quantity=position.quantity * bar.split_ratio
            )

    monkeypatch.setattr(engine_module.BacktestEngine, "_credit_dividends", apply_the_split_twice)
    with pytest.raises(CorporateActionError, match="applies the same event twice"):
        run_fixt(series, costs)


def test_split_a_series_that_is_not_actually_split_adjusted_is_caught(config, costs):
    """A close that halves across a 2:1 split session contradicts the sealed price space."""
    rows = mutated_rows(config, "2015-01-08", split_ratio="2.00", open="55.00", high="56.00",
                        low="54.00", close="55.00")
    series = {FIXT: series_from_rows(FIXT, rows)}
    with pytest.raises(CorporateActionError, match="not\n?\\s*split-adjusted"):
        run_fixt(series, costs)


# --------------------------------------------------------------------------------------------
# DIVIDEND
# --------------------------------------------------------------------------------------------


def cash_on(result, session: dt.date) -> Decimal:
    return next(point.cash for point in result.equity_curve if point.session == session)


def test_dividend_the_ex_date_cash_credit_matches_the_hand_calculation(series, costs, sealed):
    """The per-event cash-credit assertion the sealed detector names, on the clean run."""
    result = run_fixt(series, costs)
    assert cash_on(result, d("2015-01-08")) == Decimal(sealed["dividend_2015_01_08"]["cash_after"])
    point = next(p for p in result.equity_curve if p.session == d("2015-01-08"))
    assert point.equity == Decimal(sealed["mark_2015_01_08_close"]["equity"])


def test_dividend_crediting_on_the_session_after_the_ex_date_is_caught(config, costs, monkeypatch):
    """The credit arrives a session late. Final cash is unchanged; the equity curve is not.

    Worth being precise about why this is the assertion. On this fixture the position is the same
    size on both sessions and is sold after the late credit lands, so the *final* cash comes out
    identical — a check on the closing balance alone would pass a demonstrably wrong engine. The
    ex-date cash balance is what actually moved.
    """
    original = engine_module.BacktestEngine._credit_dividends

    def credit_one_session_late(self, session):
        prior = self.series[FIXT].prior_session(session)
        if prior is not None:
            original(self, prior)                     # the mutation: wrong session
        return None

    monkeypatch.setattr(engine_module.BacktestEngine, "_credit_dividends", credit_one_session_late)
    result = run_fixt({FIXT: fixt_series(config)}, costs)
    sealed = expected(BASE, config)
    assert cash_on(result, d("2015-01-08")) != Decimal(sealed["dividend_2015_01_08"]["cash_after"])
    assert cash_on(result, d("2015-01-08")) == Decimal(sealed["entry"]["cash_after"])


def test_dividend_crediting_twice_is_caught_by_the_per_event_cash_assertion(config, costs, monkeypatch):
    original = engine_module.BacktestEngine._credit_dividends

    def credit_twice(self, session):
        original(self, session)
        original(self, session)                       # the mutation

    monkeypatch.setattr(engine_module.BacktestEngine, "_credit_dividends", credit_twice)
    result = run_fixt({FIXT: fixt_series(config)}, costs)
    sealed = expected(BASE, config)
    credited = sum(Decimal(e["cash_credited"]) for e in result.dividend_events)
    assert credited == Decimal(sealed["dividend_2015_01_08"]["cash_credited"]) * 2
    assert result.final_cash != Decimal(sealed["final"]["final_cash"])


def test_dividend_a_wrong_amount_shows_up_in_the_benchmark_reconciliation(config):
    """The second sealed detector: the two SPY total-return methods stop agreeing."""
    from stockedge100.backtest.benchmarks import spy_total_return
    from stockedge100.backtest.window import ResearchWindow

    rows = [
        {"session": "2015-01-05", "open": "100", "high": "100", "low": "100", "close": "100",
         "adj_close": "99.50", "dividend": "0.00", "split_ratio": "0.00"},
        {"session": "2015-01-06", "open": "100", "high": "100", "low": "100", "close": "100",
         "adj_close": "99.50", "dividend": "0.00", "split_ratio": "0.00"},
        # Provider says the adjustment used 0.50; the dividend column claims 5.00.
        {"session": "2015-01-07", "open": "100", "high": "100", "low": "100", "close": "100",
         "adj_close": "100.00", "dividend": "5.00", "split_ratio": "0.00"},
    ]
    window = ResearchWindow(name="development", start=d("2015-01-01"), end=d("2015-12-31"))
    reconciliation = spy_total_return(series_from_rows("SPY", rows), window)
    tolerance = Decimal(config.engine_spec["benchmark_reconciliation"]["relative_tolerance"])
    assert not reconciliation.reconciles(tolerance)


# --------------------------------------------------------------------------------------------
# DELISTING
# --------------------------------------------------------------------------------------------


def test_delisting_the_engine_liquidates_at_the_last_available_close(config, costs):
    """A hold with no exit, run past the symbol's final session: the position must not survive it."""
    probe = FixedScheduleProbe(FIXT, ENTRY_DECISION, None, costs.starting_equity)
    result = run_fixt({FIXT: fixt_series(config)}, costs, probe=probe, end=d("2015-01-20"))
    assert result.open_positions == []
    assert result.fills[-1].order_id.endswith("SELL-DELIST")
    assert result.fills[-1].session == LAST


def test_delisting_a_position_carried_past_its_own_final_bar_raises(config, costs, monkeypatch):
    """The sealed mutation: extend the run while holding, without liquidating."""
    monkeypatch.setattr(engine_module.BacktestEngine, "_handle_delistings", lambda self, session: None)
    probe = FixedScheduleProbe(FIXT, ENTRY_DECISION, None, costs.starting_equity)
    with pytest.raises(DelistingError, match="could not have been traded"):
        run_fixt({FIXT: fixt_series(config)}, costs, probe=probe, end=d("2015-01-20"))


def test_delisting_an_order_past_the_symbols_final_bar_is_rejected_as_delisted(config, costs):
    """Not STALE_PRICE: a stale price is one that will be refreshed, and this one never will be."""
    probe = FixedScheduleProbe(FIXT, d("2015-01-13"), None, costs.starting_equity)
    result = run_fixt({FIXT: fixt_series(config)}, costs, probe=probe, end=d("2015-01-20"))
    assert result.fills == []
    assert [r.reason for r in result.rejections] == ["DELISTED"]


# --------------------------------------------------------------------------------------------
# STALE_PRICE
# --------------------------------------------------------------------------------------------


def test_stale_price_a_fill_on_a_session_with_no_bar_is_rejected(config, costs):
    """The sealed mutation: remove a bar while the exchange calendar still reports a session."""
    rows = [row for row in config.engine_spec["hand_calculated_fixtures"]["instrument"]["sessions"]
            if row["session"] != "2015-01-07"]
    result = run_fixt({FIXT: series_from_rows(FIXT, rows)}, costs)
    reasons = [r.reason for r in result.rejections]
    assert "STALE_PRICE" in reasons
    assert result.fills == []


def test_stale_price_an_equity_point_marked_on_an_old_close_is_flagged(config, costs):
    rows = [row for row in config.engine_spec["hand_calculated_fixtures"]["instrument"]["sessions"]
            if row["session"] != "2015-01-08"]
    result = run_fixt({FIXT: series_from_rows(FIXT, rows)}, costs)
    stale_points = [p for p in result.equity_curve if p.stale_mark]
    assert [p.session for p in stale_points] == [d("2015-01-08")]
    assert result.stale_marks == 1


def test_stale_price_a_stale_run_past_the_sealed_limit_halts_the_run(config, costs):
    limit = costs.max_consecutive_stale
    keep = {"2015-01-02", "2015-01-13"}
    rows = [row for row in config.engine_spec["hand_calculated_fixtures"]["instrument"]["sessions"]
            if row["session"] in keep]
    assert limit < 6      # the gap below — 01-05 through 01-12 — is 6 sessions wide
    with pytest.raises(DataIntegrityHalt, match="consecutive exchange sessions with no bar"):
        run_fixt({FIXT: series_from_rows(FIXT, rows)}, costs)


# --------------------------------------------------------------------------------------------
# CASH
# --------------------------------------------------------------------------------------------


def test_cash_an_order_larger_than_the_balance_cannot_create_a_position(costs):
    portfolio = Portfolio(Decimal("10.00"))
    fill = costs.buy_fill(FIXT, Decimal("1"), Decimal("100.00"))
    with pytest.raises(InvariantViolation, match="CASH_NON_NEGATIVE"):
        portfolio.apply_fill(FIRST, fill)
    assert portfolio.positions == {} and portfolio.cash == Decimal("10.00")


def test_cash_a_debit_that_never_reached_the_ledger_is_caught(costs):
    """The sealed mutation: skip the cash debit on a fill. Conservation notices the gap."""
    portfolio = Portfolio(Decimal("100.00"))
    fill = costs.buy_fill(FIXT, Decimal("0.5"), Decimal("100.00"))
    portfolio.apply_fill(FIRST, fill)
    portfolio.ledger.pop()                                   # the mutation
    with pytest.raises(InvariantViolation, match="CASH_CONSERVATION"):
        portfolio.check_invariants("after a skipped debit")


def test_cash_conservation_holds_across_the_whole_clean_run(series, costs, sealed):
    engine = BacktestEngine(series, costs, fixt_window(), fixt_probe(costs.starting_equity),
                            start=FIRST, end=LAST, label="DEFECT_PROBE")
    result = engine.run()
    entries = sum(e.amount for e in engine.portfolio.ledger)
    assert costs.starting_equity + entries == result.final_cash
    assert result.final_cash == Decimal(sealed["final"]["final_cash"])
    engine.portfolio.check_invariants("end of the clean run")


# --------------------------------------------------------------------------------------------
# ROUNDING
# --------------------------------------------------------------------------------------------


def test_rounding_a_quantity_rounded_up_buys_shares_the_budget_does_not_cover(costs):
    """The sealed mutation: round the share quantity up instead of down."""
    budget = Decimal("95.00")
    price = costs.effective_buy_price(Decimal("100.00"))
    usable = budget - costs.commission - costs.budget_safety_margin
    exact_quantity = usable / price

    honest = costs.round_quantity(exact_quantity)                                     # ROUND_FLOOR
    generous = exact_quantity.quantize(costs.share_quantum, rounding=ROUND_CEILING)   # the mutation

    assert generous > honest
    assert honest * price <= usable          # the account can pay for every share it got
    assert generous * price > usable         # it cannot, and the difference is a free lunch


def test_rounding_a_buy_notional_rounded_down_favours_the_account(costs):
    quantity = Decimal("0.949425287")
    fill = costs.buy_fill(FIXT, quantity, Decimal("100.00"))
    exact_notional = quantity * fill.effective_price
    assert fill.gross_notional >= exact_notional
    assert round_down_cent(exact_notional) < exact_notional <= round_up_cent(exact_notional)


def test_rounding_every_fill_in_the_clean_run_rounds_adversely(series, costs):
    result = run_fixt(series, costs)
    for record in result.fills:
        fill = record.fill
        exact_notional = fill.quantity * fill.effective_price
        if fill.side == BUY:
            assert fill.gross_notional >= exact_notional
        else:
            assert fill.gross_notional <= exact_notional


def test_rounding_an_order_below_the_minimum_notional_is_rejected_not_rounded_up(config, costs):
    tiny = costs.min_order_notional / Decimal("2")
    probe = FixedScheduleProbe(FIXT, ENTRY_DECISION, EXIT_DECISION, tiny)
    result = run_fixt({FIXT: fixt_series(config)}, costs, probe=probe)
    assert "MIN_NOTIONAL" in [r.reason for r in result.rejections]
    assert result.fills == []


# --------------------------------------------------------------------------------------------
# FEE
# --------------------------------------------------------------------------------------------


def test_fee_each_component_matches_the_hand_calculation(series, costs, sealed):
    result = run_fixt(series, costs)
    entry, exit_ = result.fills[0].fill, result.fills[-1].fill
    assert entry.commission == Decimal(sealed["entry"]["commission"])
    assert entry.sec_fee == ZERO and entry.taf_fee == ZERO
    assert exit_.sec_fee == Decimal(sealed["exit"]["sec_section_31_fee"])
    assert exit_.taf_fee == Decimal(sealed["exit"]["finra_taf"])
    assert exit_.commission == Decimal(sealed["exit"]["commission"])


def test_fee_zeroing_every_fee_changes_the_answer(config, series, sealed):
    """The sealed mutation: set every fee to zero. Free is a different, and wrong, number."""
    free = copy.deepcopy(config.cost_model)
    free["frictions"].update(commission_per_order_usd="0.00", half_spread_bps="0.0",
                             slippage_bps="0.0")
    free["frictions"]["regulatory"].update(sec_section_31_fee_rate="0.0",
                                           finra_taf_per_share_usd="0.0")
    model = CostModel(free, BASE)
    result = run_fixt(series, model)
    assert result.final_cash > Decimal(sealed["final"]["final_cash"])


def test_fee_the_sell_side_fees_are_never_charged_on_a_buy(series, costs):
    result = run_fixt(series, costs)
    for record in result.fills:
        if record.fill.side == BUY:
            assert record.fill.sec_fee == ZERO
            assert record.fill.taf_fee == ZERO


def test_fee_every_fill_carries_a_strictly_positive_total_cost(series, costs):
    result = run_fixt(series, costs)
    assert result.fills
    for record in result.fills:
        assert record.fill.total_cost > ZERO


# --------------------------------------------------------------------------------------------
# SLIPPAGE
# --------------------------------------------------------------------------------------------


def test_slippage_the_favourable_direction_is_refused_inside_the_price_function(costs, monkeypatch):
    """The sealed mutation: fill a buy below the reference and a sell above it."""
    monkeypatch.setattr(costs, "slippage_bps", -costs.slippage_bps - costs.half_spread_bps * 2)
    with pytest.raises(InvariantViolation, match="ADVERSE_PRICE"):
        costs.effective_buy_price(Decimal("100.00"))
    with pytest.raises(InvariantViolation, match="ADVERSE_PRICE"):
        costs.effective_sell_price(Decimal("100.00"))


def test_slippage_a_replaced_price_function_is_still_caught_at_the_fill(costs, monkeypatch):
    """Replacing the price function takes its own guard with it. The fill-level one remains."""
    monkeypatch.setattr(costs, "effective_buy_price", lambda reference: reference * Decimal("0.99"))
    monkeypatch.setattr(costs, "effective_sell_price", lambda reference: reference * Decimal("1.01"))
    with pytest.raises(InvariantViolation, match="ADVERSE_PRICE"):
        costs.buy_fill(FIXT, Decimal("1"), Decimal("100.00"))
    with pytest.raises(InvariantViolation, match="ADVERSE_PRICE"):
        costs.sell_fill(FIXT, Decimal("1"), Decimal("100.00"))


def test_slippage_omitting_it_entirely_changes_the_fill_price(config):
    frictionless = copy.deepcopy(config.cost_model)
    frictionless["frictions"].update(half_spread_bps="0.0", slippage_bps="0.0")
    model = CostModel(frictionless, BASE)
    assert model.effective_buy_price(Decimal("100.00")) == Decimal("100.00")
    assert CostModel(config.cost_model, BASE).effective_buy_price(Decimal("100.00")) > Decimal("100.00")


def test_slippage_every_fill_in_the_clean_run_is_priced_adversely(series, costs):
    result = run_fixt(series, costs)
    assert result.fills
    for record in result.fills:
        fill = record.fill
        if fill.side == BUY:
            assert fill.effective_price > fill.reference_price
        else:
            assert fill.effective_price < fill.reference_price


# --------------------------------------------------------------------------------------------
# REJECTED_ORDER
# --------------------------------------------------------------------------------------------


def test_rejected_order_a_rejection_leaves_cash_position_and_equity_untouched(config, costs):
    """The sealed mutation is applying a rejected order's effect; the assertion is that nothing moved."""
    probe = FixedScheduleProbe(FIXT, ENTRY_DECISION, EXIT_DECISION,
                               costs.min_order_notional / Decimal("2"))
    result = run_fixt({FIXT: fixt_series(config)}, costs, probe=probe)
    assert result.rejections
    assert result.fills == []
    assert result.final_cash == costs.starting_equity
    assert result.open_positions == []
    assert {p.equity for p in result.equity_curve} == {costs.starting_equity}


def test_rejected_order_every_rejection_carries_a_declared_reason_code(config, costs):
    from stockedge100.backtest.orders import REASONS

    probe = FixedScheduleProbe(FIXT, ENTRY_DECISION, EXIT_DECISION,
                               costs.min_order_notional / Decimal("2"))
    result = run_fixt({FIXT: fixt_series(config)}, costs, probe=probe)
    for rejection in result.rejections:
        assert rejection.reason in REASONS
        assert rejection.detail


def test_rejected_order_an_order_with_nowhere_to_fill_is_recorded_rather_than_dropped(series, costs):
    """No session remains for this order to fill on, and it still has to appear with a reason.

    Reached by calling the scheduler directly: the loop skips the decision on its own final session,
    so this branch is defensive, and a defensive branch that is never exercised is not evidence.
    """
    engine = BacktestEngine(series, costs, fixt_window(), fixt_probe(costs.starting_equity),
                            start=FIRST, end=LAST, label="DEFECT_PROBE")
    engine._schedule(LAST, [OrderRequest(symbol=FIXT, side=BUY, budget=Decimal("50.00"))],
                     forced=False)
    assert [r.reason for r in engine._rejections] == ["NO_ELIGIBLE_SESSION"]
    assert engine._rejections[0].order.order_id == make_order_id(LAST, FIXT, BUY)
    assert engine.portfolio.cash == costs.starting_equity


# --------------------------------------------------------------------------------------------
# DUPLICATE_ORDER
# --------------------------------------------------------------------------------------------


def test_duplicate_order_the_identical_order_submitted_twice_is_refused():
    book = OrderBook(decision_session=ENTRY_DECISION)
    order = Order(order_id=make_order_id(ENTRY_DECISION, FIXT, BUY), symbol=FIXT, side=BUY,
                  decision_session=ENTRY_DECISION, fill_session=d("2015-01-07"),
                  budget=Decimal("95.00"))
    book.submit(order)
    with pytest.raises(DuplicateOrderError, match="already admitted"):
        book.submit(order)


def test_duplicate_order_a_probe_asking_twice_in_one_session_is_caught(config, costs):
    class DoubleOrderProbe:
        name = "PROBE_DOUBLE_ORDER"

        def decide(self, view, context):
            if context.session != ENTRY_DECISION:
                return []
            request = OrderRequest(symbol=FIXT, side=BUY, budget=Decimal("50.00"))
            return [request, request]                        # the mutation

        def to_json(self):
            return {"probe": self.name}

    with pytest.raises(DuplicateOrderError):
        run_fixt({FIXT: fixt_series(config)}, costs, probe=DoubleOrderProbe())


def test_duplicate_order_two_live_orders_in_one_symbol_on_one_session_are_refused():
    book = OrderBook(decision_session=ENTRY_DECISION)
    book.submit(Order(order_id="a", symbol=FIXT, side=BUY, decision_session=ENTRY_DECISION,
                      fill_session=d("2015-01-07"), budget=Decimal("50.00")))
    with pytest.raises(DuplicateOrderError, match="already has a live order"):
        book.submit(Order(order_id="b", symbol=FIXT, side=SELL, decision_session=ENTRY_DECISION,
                          fill_session=d("2015-01-07")))


def test_duplicate_order_the_clean_run_admits_no_duplicates(series, costs):
    result = run_fixt(series, costs)
    ids = [record.order_id for record in result.fills]
    assert len(ids) == len(set(ids))
