"""Stage 2 — the engine's parts, checked one at a time.

Every test here is about a property that has to hold for the engine to be worth trusting at all: a
friction that is adverse, a rounding step that is adverse, a cash balance that reconciles, a
visibility bound that cannot be widened. None of them is about a strategy, and none produces a
number anybody should act on.

Where an expected value appears, it was computed by hand and is written as a literal. A test that
recomputed the value the same way the engine does would agree with a wrong engine.
"""

from __future__ import annotations

import datetime as dt
import json
from decimal import Decimal, localcontext

import pytest

from stockedge100.backtest.config import (
    COST_MODEL_REL,
    ENGINE_SPEC_REL,
    dec,
    load_partition_bounds,
    load_stage2_config,
)
from stockedge100.backtest.costs import (
    BASE,
    BPS,
    CENT,
    CostModel,
    ENGINE_CONTEXT,
    STRESSED,
    ZERO,
    round_down_cent,
    round_up_cent,
)
from stockedge100.backtest.dataset import Bar, COLUMNS, load_series, series_from_rows
from stockedge100.backtest.errors import (
    ConfigViolation,
    DuplicateOrderError,
    FillTimingError,
    InvariantViolation,
    LookAheadError,
    WindowViolation,
)
from stockedge100.backtest.market import MarketView
from stockedge100.backtest.metrics import (
    cagr,
    daily_returns,
    exposure_fraction,
    max_drawdown,
    profit_factor,
    sharpe,
    stdev,
    total_return,
)
from stockedge100.backtest.orders import (
    BUY,
    Order,
    OrderBook,
    REASONS,
    SELL,
    make_order_id,
    next_session_after,
)
from stockedge100.backtest.portfolio import Portfolio
from stockedge100.backtest.window import HOLDOUT, ResearchWindow, VALIDATION, development_window, window_named
from stockedge100.reporting.stage2_evidence import (
    DIGEST_COVERS,
    EXCLUDED_FROM_DIGEST,
    evidence_digest,
    finalize,
)


def d(text: str) -> dt.date:
    return dt.date.fromisoformat(text)


@pytest.fixture(scope="module")
def config():
    return load_stage2_config()


@pytest.fixture(scope="module")
def base(config):
    return CostModel(config.cost_model, BASE)


@pytest.fixture(scope="module")
def stressed(config):
    return CostModel(config.cost_model, STRESSED)


# --------------------------------------------------------------------------------------------
# The sealed configuration
# --------------------------------------------------------------------------------------------


def test_the_sealed_configuration_still_matches_its_pre_registration(config):
    """The load itself is the check: :func:`load_stage2_config` refuses a drifted file."""
    assert config.digests[COST_MODEL_REL]
    assert config.digests[ENGINE_SPEC_REL]
    assert config.preregistration["document_id"] == "SE100-GOV-0005"


def test_loading_refuses_a_config_that_has_drifted_since_sealing(monkeypatch, tmp_path, config):
    """Tamper with a *copy*. The real sealed files are never written by a test."""
    from stockedge100.backtest import config as config_module

    root = tmp_path / "root"
    (root / "config").mkdir(parents=True)
    (root / "governance").mkdir(parents=True)

    tampered = dict(config.cost_model)
    tampered["frictions"] = dict(tampered["frictions"], half_spread_bps="0.0")
    (root / COST_MODEL_REL).write_text(json.dumps(tampered), encoding="utf-8")
    (root / ENGINE_SPEC_REL).write_text(json.dumps(config.engine_spec), encoding="utf-8")

    prereg = root / "governance" / "STAGE_2_PREREGISTRATION.json"
    prereg.write_text(
        json.dumps(
            {
                "document_id": "SE100-GOV-0005",
                "preregistered_files": {
                    COST_MODEL_REL: {"sha256": config.digests[COST_MODEL_REL]},
                },
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(config_module, "PROJECT_ROOT", root)
    monkeypatch.setattr(config_module, "PREREGISTRATION_JSON", prereg)
    with pytest.raises(ConfigViolation, match="has changed since it was sealed"):
        config_module.load_stage2_config()


def test_a_sealed_money_value_may_not_arrive_as_a_float():
    """0.1 is not 0.1. Refusing the float is the only way the sealed value survives."""
    with pytest.raises(ConfigViolation, match="round-trips exactly"):
        dec(0.1)
    assert dec("0.1") == Decimal("0.1")


def test_the_declared_defect_classes_cover_every_error_named_in_gate_2(config):
    ids = set(config.defect_class_ids())
    assert ids == {
        "LOOK_AHEAD", "SAME_CLOSE_FILL", "SPLIT", "DIVIDEND", "DELISTING", "STALE_PRICE",
        "CASH", "ROUNDING", "FEE", "SLIPPAGE", "REJECTED_ORDER", "DUPLICATE_ORDER",
    }


# --------------------------------------------------------------------------------------------
# Costs: every friction adverse, every rounding step adverse
# --------------------------------------------------------------------------------------------


def test_a_buy_fills_above_its_reference_and_a_sell_below_it(base):
    reference = Decimal("100.00")
    assert base.effective_buy_price(reference) > reference
    assert base.effective_sell_price(reference) < reference


def test_the_friction_is_the_half_spread_plus_slippage_on_each_side(base):
    reference = Decimal("100.00")
    expected_bps = base.half_spread_bps + base.slippage_bps
    assert base.price_friction_bps == expected_bps
    assert base.effective_buy_price(reference) == reference * (Decimal(1) + expected_bps / BPS)
    assert base.effective_sell_price(reference) == reference * (Decimal(1) - expected_bps / BPS)


def test_the_stressed_scenario_doubles_the_complete_friction_assumption(base, stressed):
    """Including the TAF cap: a stress that leaves a cap alone is cheaper than 2x for large orders."""
    two = Decimal("2.0")
    assert stressed.half_spread_bps == base.half_spread_bps * two
    assert stressed.slippage_bps == base.slippage_bps * two
    assert stressed.sec_rate == base.sec_rate * two
    assert stressed.taf_per_share == base.taf_per_share * two
    assert stressed.taf_cap == base.taf_cap * two
    assert stressed.commission == base.commission * two


def test_a_scenario_that_was_never_declared_is_refused(config):
    with pytest.raises(ConfigViolation, match="unknown cost scenario"):
        CostModel(config.cost_model, "OPTIMISTIC")


def test_a_stress_list_that_omits_a_friction_component_is_refused(config):
    """A partial stress list would silently under-stress; the model must refuse to load."""
    partial = json.loads(json.dumps(config.cost_model))
    partial["frictions"]["stress_applies_to"] = ["half_spread_bps"]
    with pytest.raises(ConfigViolation, match="stress_applies_to"):
        CostModel(partial, STRESSED)


def test_money_rounds_in_the_direction_that_costs_the_account():
    assert round_up_cent(Decimal("1.001")) == Decimal("1.01")
    assert round_down_cent(Decimal("1.009")) == Decimal("1.00")
    assert round_up_cent(Decimal("1.00")) == Decimal("1.00")
    assert round_down_cent(Decimal("1.00")) == Decimal("1.00")


def test_a_buy_pays_the_rounded_up_notional_and_a_sell_receives_the_rounded_down_one(base):
    buy = base.buy_fill("X", Decimal("0.333333333"), Decimal("10.00"))
    assert buy.gross_notional == round_up_cent(buy.quantity * buy.effective_price)
    assert buy.gross_notional >= buy.quantity * buy.effective_price

    sell = base.sell_fill("X", Decimal("0.333333333"), Decimal("10.00"))
    assert sell.gross_notional == round_down_cent(sell.quantity * sell.effective_price)
    assert sell.gross_notional <= sell.quantity * sell.effective_price


def test_a_quantity_rounds_down_never_up(base):
    assert base.round_quantity(Decimal("0.9999999999")) == Decimal("0.999999999")
    assert base.round_quantity(Decimal("1.0000000004")) == Decimal("1.000000000")


def test_sizing_never_spends_more_than_the_budget(base):
    """Including after the notional rounds up: that is what the safety margin is for."""
    for budget in ("1.00", "10.00", "37.77", "94.99", "95.00"):
        b = Decimal(budget)
        price = base.effective_buy_price(Decimal("123.45"))
        quantity = base.solve_buy_quantity(b, price)
        fill = base.buy_fill("X", quantity, Decimal("123.45"))
        assert -fill.cash_delta <= b


def test_regulatory_fees_are_charged_on_sales_only(base):
    buy = base.buy_fill("X", Decimal("1"), Decimal("100.00"))
    assert buy.sec_fee == ZERO and buy.taf_fee == ZERO
    sell = base.sell_fill("X", Decimal("1"), Decimal("100.00"))
    assert sell.sec_fee > ZERO and sell.taf_fee > ZERO


def test_the_taf_is_capped(base):
    """A quantity far past the cap still pays only the cap, rounded up to the cent."""
    huge = base.taf_cap / base.taf_per_share * Decimal("10")
    fill = base.sell_fill("X", huge, Decimal("100.00"))
    assert fill.taf_fee == round_up_cent(base.taf_cap)


def test_a_dividend_credit_rounds_down(base):
    assert base.dividend_cash(Decimal("0.949425287"), Decimal("0.50")) == Decimal("0.47")


def test_the_engine_context_is_pinned_and_survives_a_hostile_caller(base):
    """A caller who narrows the global context must not be able to change a fill price."""
    reference = Decimal("100.00")
    expected = base.effective_buy_price(reference)
    with localcontext() as ctx:
        ctx.prec = 4
        assert base.effective_buy_price(reference) == expected
    assert ENGINE_CONTEXT.prec == 34


# --------------------------------------------------------------------------------------------
# Portfolio: the ledger reconciles after every movement
# --------------------------------------------------------------------------------------------


def test_cash_is_reconciled_against_the_ledger_after_every_movement(base):
    p = Portfolio(Decimal("100.00"))
    p.credit(d("2015-01-02"), "TEST", Decimal("1.00"))
    p.debit(d("2015-01-05"), "TEST", Decimal("0.50"))
    assert p.cash == Decimal("100.50")
    assert p.starting_cash + sum(e.amount for e in p.ledger) == p.cash


def test_a_cash_movement_that_bypasses_the_ledger_is_caught():
    """The invariant exists precisely because a bare balance cannot notice this."""
    p = Portfolio(Decimal("100.00"))
    p.cash = Decimal("150.00")
    with pytest.raises(InvariantViolation, match="CASH_CONSERVATION"):
        p.check_invariants("tampered")


def test_cash_may_not_go_negative():
    p = Portfolio(Decimal("100.00"))
    with pytest.raises(InvariantViolation, match="CASH_NON_NEGATIVE"):
        p.debit(d("2015-01-02"), "TEST", Decimal("100.01"))


def test_cash_is_always_a_whole_number_of_cents():
    p = Portfolio(Decimal("100.00"))
    with pytest.raises(InvariantViolation, match="CASH_IS_WHOLE_CENTS"):
        p.credit(d("2015-01-02"), "TEST", Decimal("0.001"))


def test_a_buy_that_would_overdraw_the_account_leaves_no_position_behind(base):
    p = Portfolio(Decimal("10.00"))
    fill = base.buy_fill("X", Decimal("1"), Decimal("100.00"))
    with pytest.raises(InvariantViolation, match="CASH_NON_NEGATIVE"):
        p.apply_fill(d("2015-01-02"), fill)
    assert p.positions == {}
    assert p.cash == Decimal("10.00")


def test_selling_more_than_is_held_is_refused(base):
    p = Portfolio(Decimal("100.00"))
    p.apply_fill(d("2015-01-02"), base.buy_fill("X", Decimal("0.5"), Decimal("100.00")))
    with pytest.raises(InvariantViolation, match="INSUFFICIENT_POSITION"):
        p.apply_fill(d("2015-01-05"), base.sell_fill("X", Decimal("0.6"), Decimal("100.00")))


def test_a_second_simultaneous_position_is_refused_at_the_sealed_limit(base):
    p = Portfolio(Decimal("100.00"), max_positions=1)
    p.apply_fill(d("2015-01-02"), base.buy_fill("X", Decimal("0.1"), Decimal("100.00")))
    with pytest.raises(InvariantViolation, match="MAX_POSITIONS"):
        p.apply_fill(d("2015-01-02"), base.buy_fill("Y", Decimal("0.1"), Decimal("100.00")))


def test_a_closed_trade_carries_its_dividends_and_both_legs_costs(base):
    p = Portfolio(Decimal("100.00"))
    p.apply_fill(d("2015-01-07"), base.buy_fill("X", Decimal("0.5"), Decimal("100.00")))
    p.record_dividend(d("2015-01-08"), "X", Decimal("0.25"))
    p.apply_fill(d("2015-01-09"), base.sell_fill("X", Decimal("0.5"), Decimal("120.00")))
    trade = p.trades[0]
    assert trade.dividends == Decimal("0.25")
    assert trade.pnl == trade.exit_cash + trade.dividends - trade.entry_cash
    assert p.positions == {}


def test_equity_refuses_to_value_a_position_it_was_given_no_mark_for(base):
    p = Portfolio(Decimal("100.00"))
    p.apply_fill(d("2015-01-02"), base.buy_fill("X", Decimal("0.5"), Decimal("100.00")))
    with pytest.raises(InvariantViolation, match="no mark supplied"):
        p.equity({})


def test_a_mark_is_never_rounded(base):
    """Rounding a mark would invent a precision loss that never happened."""
    p = Portfolio(Decimal("100.00"))
    p.apply_fill(d("2015-01-02"), base.buy_fill("X", Decimal("0.333333333"), Decimal("30.00")))
    equity = p.equity({"X": Decimal("33.333333")})
    assert equity != equity.quantize(CENT)


# --------------------------------------------------------------------------------------------
# Orders: a fill is never on the decision session
# --------------------------------------------------------------------------------------------


def test_an_order_cannot_be_constructed_to_fill_at_its_own_decision_close():
    with pytest.raises(FillTimingError, match="not strictly after"):
        Order(
            order_id="x", symbol="X", side=BUY,
            decision_session=d("2015-01-06"), fill_session=d("2015-01-06"),
            budget=Decimal("10"),
        )


def test_an_order_cannot_be_constructed_to_fill_before_it_was_decided():
    with pytest.raises(FillTimingError):
        Order(
            order_id="x", symbol="X", side=BUY,
            decision_session=d("2015-01-06"), fill_session=d("2015-01-05"),
            budget=Decimal("10"),
        )


def test_a_buy_carries_a_budget_and_a_sell_does_not():
    with pytest.raises(ValueError, match="needs a budget"):
        Order(order_id="x", symbol="X", side=BUY,
              decision_session=d("2015-01-06"), fill_session=d("2015-01-07"))
    with pytest.raises(ValueError, match="does not take a budget"):
        Order(order_id="x", symbol="X", side=SELL,
              decision_session=d("2015-01-06"), fill_session=d("2015-01-07"),
              budget=Decimal("10"))


def test_the_next_session_comes_from_the_exchange_calendar_not_the_price_file():
    assert next_session_after(d("2015-01-02")) == d("2015-01-05")     # over a weekend
    assert next_session_after(d("2014-12-24")) == d("2014-12-26")     # over Christmas
    assert next_session_after(d("2012-10-26")) == d("2012-10-31")     # over Hurricane Sandy


def test_the_same_order_id_cannot_be_admitted_twice():
    book = OrderBook(decision_session=d("2015-01-06"))
    order = Order(order_id="dup", symbol="X", side=BUY,
                  decision_session=d("2015-01-06"), fill_session=d("2015-01-07"),
                  budget=Decimal("10"))
    book.submit(order)
    with pytest.raises(DuplicateOrderError, match="already admitted"):
        book.submit(order)


def test_one_symbol_may_have_only_one_live_order_per_session():
    book = OrderBook(decision_session=d("2015-01-06"))
    book.submit(Order(order_id="a", symbol="X", side=BUY,
                      decision_session=d("2015-01-06"), fill_session=d("2015-01-07"),
                      budget=Decimal("10")))
    with pytest.raises(DuplicateOrderError, match="already has a live order"):
        book.submit(Order(order_id="b", symbol="X", side=SELL,
                          decision_session=d("2015-01-06"), fill_session=d("2015-01-07")))


def test_an_order_id_is_built_only_from_the_orders_own_facts():
    """No counter, no clock, no address — so a rerun produces the same ids."""
    first = make_order_id(d("2015-01-06"), "SPY", BUY)
    second = make_order_id(d("2015-01-06"), "SPY", BUY)
    assert first == second == "2015-01-06-SPY-BUY"
    assert make_order_id(d("2015-01-06"), "SPY", SELL, "SHUTDOWN") == "2015-01-06-SPY-SELL-SHUTDOWN"


def test_the_rejection_reason_set_is_closed():
    assert len(set(REASONS)) == len(REASONS)
    assert "MIN_NOTIONAL" in REASONS and "DUPLICATE_ORDER" in REASONS


# --------------------------------------------------------------------------------------------
# Market view: the visibility bound cannot be widened
# --------------------------------------------------------------------------------------------


@pytest.fixture
def tiny_series():
    return {
        "X": series_from_rows(
            "X",
            [
                {"session": "2015-01-05", "open": "10", "close": "10"},
                {"session": "2015-01-06", "open": "11", "close": "11"},
                {"session": "2015-01-07", "open": "12", "close": "12"},
            ],
        )
    }


@pytest.fixture
def tiny_window():
    return ResearchWindow(name="development", start=d("2015-01-01"), end=d("2015-12-31"))


def test_a_view_refuses_a_session_after_its_bound(tiny_series, tiny_window):
    view = MarketView(tiny_series, d("2015-01-06"), tiny_window)
    assert view.close("X", d("2015-01-06")) == Decimal("11")
    with pytest.raises(LookAheadError, match="bounded at"):
        view.bar("X", d("2015-01-07"))


def test_the_visibility_bound_cannot_be_rebound(tiny_series, tiny_window):
    """A bound that can be moved is not a bound."""
    view = MarketView(tiny_series, d("2015-01-06"), tiny_window)
    with pytest.raises(LookAheadError, match="immutable"):
        view._as_of = d("2015-01-07")
    assert view.as_of == d("2015-01-06")


def test_history_and_latest_bar_stop_at_the_bound(tiny_series, tiny_window):
    view = MarketView(tiny_series, d("2015-01-06"), tiny_window)
    assert [bar.session for bar in view.history("X", 10)] == [d("2015-01-05"), d("2015-01-06")]
    assert view.latest_bar("X").session == d("2015-01-06")


def test_a_retained_older_view_sees_less_not_more(tiny_series, tiny_window):
    old = MarketView(tiny_series, d("2015-01-05"), tiny_window)
    MarketView(tiny_series, d("2015-01-07"), tiny_window)
    with pytest.raises(LookAheadError):
        old.bar("X", d("2015-01-06"))


# --------------------------------------------------------------------------------------------
# Window: validation is LOCKED and holdout is SEALED
# --------------------------------------------------------------------------------------------


def test_the_development_window_comes_from_the_stage_1_lock():
    bounds = load_partition_bounds()
    window = development_window()
    assert window.start == d(bounds["development_start"])
    assert window.end == d(bounds["development_end"])


def test_the_development_window_refuses_a_validation_or_holdout_session():
    window = development_window()
    for name in (VALIDATION, HOLDOUT):
        forbidden = window_named(name)
        with pytest.raises(WindowViolation, match="LOCKED"):
            window.check(forbidden.start)


def test_an_unknown_window_name_is_refused():
    with pytest.raises(WindowViolation, match="unknown research window"):
        window_named("everything")


# --------------------------------------------------------------------------------------------
# Dataset: exact decimals, and a schema that must match
# --------------------------------------------------------------------------------------------


def test_prices_are_parsed_as_exact_decimals_not_floats():
    series = series_from_rows("X", [{"session": "2015-01-05", "open": "0.1", "close": "0.3"}])
    bar = series.bars[d("2015-01-05")]
    assert isinstance(bar.close, Decimal)
    assert bar.open * 3 == bar.close        # true of Decimal, false of float
    assert 0.1 * 3 != 0.3


def test_a_normalized_file_with_the_wrong_schema_is_refused(tmp_path):
    path = tmp_path / "X.csv"
    path.write_text("session,open,close\n2015-01-05,1,1\n", encoding="utf-8")
    from stockedge100.backtest.errors import BacktestError

    with pytest.raises(BacktestError, match="unexpected normalized schema"):
        load_series("X", directory=tmp_path)
    assert COLUMNS[0] == "session"


def test_a_bar_reports_its_corporate_actions():
    bar = Bar(
        session=d("2015-01-05"), open=Decimal(1), high=Decimal(1), low=Decimal(1),
        close=Decimal(1), adj_close=Decimal(1), volume=0,
        dividend=Decimal("0.5"), split_ratio=Decimal("2"),
    )
    assert bar.has_dividend and bar.has_split
    plain = Bar(
        session=d("2015-01-05"), open=Decimal(1), high=Decimal(1), low=Decimal(1),
        close=Decimal(1), adj_close=Decimal(1), volume=0,
        dividend=Decimal("0"), split_ratio=Decimal("0"),
    )
    assert not plain.has_dividend and not plain.has_split


# --------------------------------------------------------------------------------------------
# Metrics: undefined stays undefined
# --------------------------------------------------------------------------------------------


def test_total_return_and_drawdown_against_hand_values():
    assert total_return(Decimal("100"), Decimal("150")) == Decimal("0.5")
    assert max_drawdown([Decimal(x) for x in ("100", "120", "90", "150")]) == Decimal("0.25")
    assert max_drawdown([Decimal("100"), Decimal("110")]) == ZERO


def test_profit_factor_is_none_rather_than_infinity_when_nothing_lost():
    assert profit_factor([Decimal("5"), Decimal("3")]) is None
    assert profit_factor([]) is None
    assert profit_factor([Decimal("6"), Decimal("-3")]) == Decimal("2")


def test_sharpe_is_undefined_for_a_flat_curve_rather_than_infinite():
    assert sharpe([ZERO] * 10, trading_days=252, risk_free_annual=ZERO) is None
    assert sharpe([Decimal("0.01")], trading_days=252, risk_free_annual=ZERO) is None


def test_daily_returns_and_stdev_against_hand_values():
    equity = [Decimal("100"), Decimal("110"), Decimal("99")]
    assert daily_returns(equity) == [Decimal("0.1"), Decimal("-0.1")]
    # Sample stdev of (1, 3): mean 2, squared deviations 1 and 1, variance 2/(2−1), so √2. The
    # literal is √2 to 32 places; comparing against Decimal("2").sqrt() would inherit whatever
    # precision the ambient context happened to have.
    assert abs(stdev([Decimal("1"), Decimal("3")]) - Decimal("1.41421356237309504880168872420970")) < Decimal("1e-30")
    assert stdev([Decimal("1")]) is None


def test_cagr_doubles_over_a_year_and_is_undefined_over_no_time():
    rate = cagr(Decimal("100"), Decimal("200"), d("2015-01-01"), d("2016-01-01"))
    assert Decimal("0.99") < rate < Decimal("1.01")
    assert cagr(Decimal("100"), Decimal("200"), d("2015-01-01"), d("2015-01-01")) is None


def test_exposure_is_the_fraction_of_sessions_holding_anything():
    assert exposure_fraction([0, 1, 1, 0]) == Decimal("0.5")
    assert exposure_fraction([]) == ZERO


# --------------------------------------------------------------------------------------------
# The evidence file's self-digest covers exactly what it says it covers
# --------------------------------------------------------------------------------------------
#
# These run on a synthetic body, never on the real evidence file: nothing here reads or writes
# reports/. The first version of the writer appended the coverage description *after* taking the
# digest, so a reader recomputing the digest from the file as documented got a different value —
# caught by performing the recomputation, which is the only thing that catches it.


def test_the_evidence_digest_recomputes_from_the_sealed_body():
    sealed = finalize({"finding": "x", "all_conditions_met": True}, "2020-01-01T00:00:00Z")
    assert evidence_digest(sealed) == sealed["evidence_digest"]
    assert sealed["evidence_digest_covers"] == DIGEST_COVERS


def test_the_evidence_digest_ignores_the_timestamp_and_nothing_else():
    early = finalize({"finding": "x"}, "2020-01-01T00:00:00Z")
    late = finalize({"finding": "x"}, "2026-08-09T11:58:56Z")
    assert early["generated_utc"] != late["generated_utc"]
    assert early["evidence_digest"] == late["evidence_digest"]

    # ... and a real change to a finding must move it, or equality above would prove nothing.
    changed = finalize({"finding": "y"}, "2020-01-01T00:00:00Z")
    assert changed["evidence_digest"] != early["evidence_digest"]


def test_every_field_outside_the_two_exclusions_is_covered_by_the_digest():
    sealed = finalize({"finding": "x"}, "2020-01-01T00:00:00Z")
    for field in sealed:
        if field in EXCLUDED_FROM_DIGEST:
            continue
        tampered = dict(sealed)
        tampered[field] = "tampered"
        assert evidence_digest(tampered) != sealed["evidence_digest"], field
