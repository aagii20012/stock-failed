"""Holding more than one risky position is new engine capability, tested as new capability.

``config/generation_2/g2_rotation_protocol.json`` seals the requirement in its own words:

    "Holding more than one risky position is new engine capability. It is tested as new capability,
    not assumed to work because the single-position engine worked. Each item below must have at
    least one test that FAILS if the engine regresses on it."

and lists six properties:

1. the engine never holds more than k positions at once
2. combined gross exposure across the k positions never exceeds 95% of equity
3. no single position ever exceeds 50% of equity at a rebalance
4. no order is bought or sold at the close that generated the ranking signal
5. tomorrow's bar cannot enter today's ranking
6. identical inputs on a clean rerun produce identical results

Each has a section below, each section opens with a clean control and closes with an injected
defect, and each injection is placed where the engine could actually go wrong rather than where it
is easiest to reach.

**The fixture.** Five synthetic symbols over the 252 real XNYS sessions of 2010. Closes are whole
units; every open is its close minus 0.25, so the set of opens and the set of closes are provably
disjoint — which turns "no fill happened at a ranking close" from an argument into a set-membership
test. Each symbol's per-session growth rate rotates month by month with a per-symbol phase offset,
so the trailing-return ordering genuinely churns and the exit path is exercised, while no rate is
ever negative, so the 15% research shutdown never fires and a ceiling test stays a ceiling test.
2010 is inside Generation 2's development window by more than a decade; nothing here reads ``data/``.

**Why the ceiling assertions replay the fill stream.** Asserting the ceilings from
``engine.clamp_summary()`` would be asking the clamp whether the clamp worked. The replay in
:func:`ceiling_report` reconstructs cash and quantities from the ordered fill records alone — the
fixture has no dividends and no splits, so nothing else moves them — and recomputes the pre-fill
equity each buy was sized against. It shares no line of code with ``_execute_buy``.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from stockedge100.backtest.costs import BASE, STRESSED, ZERO
from stockedge100.backtest.dataset import series_from_rows
from stockedge100.backtest.engine import DecisionContext, OrderRequest
from stockedge100.backtest.errors import (
    FillTimingError,
    InvariantViolation,
    LookAheadError,
)
from stockedge100.backtest.g2_costs import concentration_ceiling, rotation_cost_model
from stockedge100.backtest.g2_engine import CLAMP_NAMES, RotationEngine
from stockedge100.backtest.market import MarketView
from stockedge100.backtest.orders import BUY, Order, next_session_after
from stockedge100.data.calendar import sessions_between
from stockedge100.strategies import g2_rotation as rot
from stockedge100.strategies import g2_window_guard as guard

# -- the fixture ----------------------------------------------------------------------------------

SYMBOLS = ("AAA", "BBB", "CCC", "DDD", "EEE")
RATES = (4, 3, 2, 1, 0)                       # price units added per session; never negative
FIRST = dt.date(2010, 1, 4)
LAST = dt.date(2010, 12, 31)
OPEN_DISCOUNT = Decimal("0.25")

MAX_GROSS = Decimal("0.95")
CONCENTRATION = Decimal("0.50")               # hand-written; the module reads it from the seal


def build_series(first=FIRST, last=LAST, *, symbols=SYMBOLS, bump=None):
    """Five symbols on real XNYS sessions, with an optional single-bar perturbation.

    ``bump`` is ``(symbol, session, delta)`` and shifts one close (and its open with it). It exists
    so a determinism test can prove its digest is not a constant, and so a look-ahead test can show
    that a bar *before* the decision date does change the ranking.
    """
    sessions = sessions_between(first, last)
    months: list[tuple[int, int]] = []
    for day in sessions:
        key = (day.year, day.month)
        if key not in months:
            months.append(key)

    series = {}
    for index, symbol in enumerate(symbols):
        close = Decimal(200 + 10 * index)
        rows = []
        for day in sessions:
            close += RATES[(index + months.index((day.year, day.month))) % len(RATES)]
            value = close
            if bump is not None and bump[0] == symbol and bump[1] == day:
                value = close + Decimal(bump[2])
            rows.append(
                {
                    "session": day.isoformat(),
                    "open": f"{value - OPEN_DISCOUNT}",
                    "high": f"{value}",
                    "low": f"{value - OPEN_DISCOUNT}",
                    "close": f"{value}",
                }
            )
        series[symbol] = series_from_rows(symbol, rows)
    return series


@pytest.fixture(scope="module")
def series():
    return build_series()


@pytest.fixture(scope="module")
def window():
    return guard.generation_2_window("g2_engine_fixture", "2009-12-01", "2011-01-31")


def make_engine(series, window, variant_id, *, budget_weight="sealed", probe=None, end=None):
    """One engine, wired the way :mod:`stockedge100.strategies.g2_runner` wires it."""
    variant = rot.variant_by_id(variant_id)
    costs = rotation_cost_model(variant.top_k, BASE)
    candidate = probe or rot.RotationCandidate(variant, costs, universe=SYMBOLS)
    weight = getattr(candidate, "weight", None) if budget_weight == "sealed" else budget_weight
    sessions = series[SYMBOLS[0]].sessions
    engine = RotationEngine(
        series,
        costs,
        window,
        candidate,
        start=sessions[0],
        end=end or sessions[-1],
        label=variant_id,
        budget_weight=weight,
    )
    return engine, candidate, variant


def run(series, window, variant_id, **kwargs):
    engine, candidate, variant = make_engine(series, window, variant_id, **kwargs)
    return engine.run(), engine, candidate, variant


K1 = "SE100-G2-S3-C1-ROTATION-L03-K1-MONTHLY"
K2 = "SE100-G2-S3-C1-ROTATION-L03-K2-MONTHLY"
K3 = "SE100-G2-S3-C1-ROTATION-L03-K3-MONTHLY"
K2Q = "SE100-G2-S3-C1-ROTATION-L03-K2-QUARTERLY"


# -- the independent replay ------------------------------------------------------------------------


def ceiling_report(result, series):
    """Re-derive, from the fill stream alone, what every buy did to the two ceilings.

    Returns one record per BUY fill: the pre-fill equity measured at that session's open, the value
    of the bought position immediately afterwards, and the value of the whole book. No engine
    counter, clamp, or invariant is consulted.
    """
    cash = result.starting_equity
    quantities: dict[str, Decimal] = {}
    records = []

    for record in result.fills:
        fill = record.fill
        session = record.session
        marks = {s: series[s].bars[session].open for s in quantities}
        equity_before = cash + sum((quantities[s] * marks[s] for s in quantities), ZERO)

        cash += fill.cash_delta
        held = quantities.get(fill.symbol, ZERO)
        held = held + fill.quantity if fill.side == BUY else held - fill.quantity
        if held == ZERO:
            quantities.pop(fill.symbol, None)
        else:
            quantities[fill.symbol] = held

        if fill.side != BUY:
            continue
        after = dict(marks)
        after[fill.symbol] = fill.reference_price
        book = sum((quantities[s] * after[s] for s in quantities), ZERO)
        records.append(
            {
                "session": session,
                "symbol": fill.symbol,
                "equity_before": equity_before,
                "position_value": quantities[fill.symbol] * fill.reference_price,
                "book_value": book,
                "open_positions": len(quantities),
            }
        )

    assert cash == result.final_cash, "the replay disagrees with the engine about final cash"
    return records


def test_the_replay_reconciles_with_the_engine_it_is_supposed_to_audit(series, window):
    """Control for the auditor: if the replay could not reproduce the engine's cash, nothing below
    it would mean anything. It is asserted here once, loudly, rather than only inside the helper."""
    result, _, _, _ = run(series, window, K3)

    records = ceiling_report(result, series)
    assert records, "the fixture produced no purchases; every ceiling test below would be vacuous"
    assert result.final_cash == result.starting_equity + sum(
        (r.fill.cash_delta for r in result.fills), ZERO
    )


def test_the_fixture_separates_opens_from_closes(series):
    """Control: the premise property 4 leans on."""
    opens = {bar.open for one in series.values() for bar in one.bars.values()}
    closes = {bar.close for one in series.values() for bar in one.bars.values()}

    assert opens and closes
    assert not (opens & closes)
    assert len(series[SYMBOLS[0]].sessions) == 252


# ==================================================================================================
# 1. the engine never holds more than k positions at once
# ==================================================================================================


@pytest.mark.parametrize("variant_id, k", [(K1, 1), (K2, 2), (K3, 3), (K2Q, 2)])
def test_the_book_never_exceeds_the_variants_position_count(series, window, variant_id, k):
    result, engine, _, variant = run(series, window, variant_id)

    assert variant.top_k == k
    assert engine.costs.max_open_risky_positions == k
    assert max(point.position_count for point in result.equity_curve) <= k
    assert all(record["open_positions"] <= k for record in ceiling_report(result, series))


@pytest.mark.parametrize("variant_id, k", [(K1, 1), (K2, 2), (K3, 3)])
def test_the_book_actually_reaches_k_so_the_bound_is_not_vacuous(series, window, variant_id, k):
    """A ceiling nothing ever approaches is not evidence the ceiling works."""
    result, _, _, _ = run(series, window, variant_id)

    assert max(point.position_count for point in result.equity_curve) == k


class GreedyProbe:
    """Asks for more positions than the variant permits, on every scheduled rebalance.

    This is the injection for property 1: a strategy that requests `k + extra` entries at once. The
    engine must refuse the surplus rather than open them, and it must refuse them by the declared
    ``MAX_POSITIONS`` reason rather than by running out of cash, which would pass the position test
    for the wrong reason.
    """

    name = "greedy-probe"
    experiment_id = "GREEDY"

    def __init__(self, symbols):
        self.symbols = tuple(symbols)
        self.requested = 0

    def decide(self, view: MarketView, context: DecisionContext) -> list[OrderRequest]:
        if context.session.day > 7 or context.shutdown_active:
            return []
        self.requested += len(self.symbols)
        return [
            OrderRequest(symbol=symbol, side=BUY, budget=Decimal("10.00"), tag=self.experiment_id)
            for symbol in self.symbols
        ]


@pytest.mark.parametrize("k", [1, 2, 3])
def test_a_probe_asking_for_more_than_k_positions_is_refused_by_the_declared_reason(
    series, window, k
):
    variant_id = {1: K1, 2: K2, 3: K3}[k]
    probe = GreedyProbe(SYMBOLS)
    result, engine, _, _ = run(series, window, variant_id, probe=probe, budget_weight=None)

    assert probe.requested > 0
    refused = [r for r in result.rejections if r.reason == "MAX_POSITIONS"]
    assert refused, f"k={k}: no MAX_POSITIONS rejection, so the surplus was never refused"
    assert max(point.position_count for point in result.equity_curve) == k
    assert engine.portfolio.max_positions == k
    assert all(record["open_positions"] <= k for record in ceiling_report(result, series))


def test_the_portfolio_refuses_the_surplus_even_if_the_engine_check_were_removed(series, window):
    """The second of the two layers, exercised on its own.

    ``_execute_buy`` rejects a surplus entry before it reaches the book, so in a normal run
    ``Portfolio``'s own ``MAX_POSITIONS`` invariant never fires. That makes it exactly the guard
    most likely to rot unnoticed, so it is driven directly: fill the book to k through the public
    settle path, then settle one more.
    """
    costs = rotation_cost_model(2, BASE)
    engine, _, _ = make_engine(series, window, K2)
    session = series[SYMBOLS[0]].sessions[0]

    for symbol in SYMBOLS[:2]:
        reference = series[symbol].bars[session].open
        quantity = costs.solve_buy_quantity(Decimal("20.00"), costs.effective_buy_price(reference))
        engine.portfolio.apply_fill(session, costs.buy_fill(symbol, quantity, reference))
    assert len(engine.portfolio.open_symbols()) == 2

    third = SYMBOLS[2]
    reference = series[third].bars[session].open
    quantity = costs.solve_buy_quantity(Decimal("20.00"), costs.effective_buy_price(reference))
    with pytest.raises(InvariantViolation, match="MAX_POSITIONS: opening CCC"):
        engine.portfolio.apply_fill(session, costs.buy_fill(third, quantity, reference))


def test_the_engine_invariant_reports_a_book_wider_than_the_limit(series, window):
    """The third layer: ``_assert_ceilings_hold`` compares the settled book to the live limit.

    The limit is lowered rather than the book corrupted, because the book cannot be corrupted
    through any public path — and comparing the two is the whole of what the assertion does, so
    moving either side of the comparison is a fair test of it.
    """
    result, engine, _, _ = run(series, window, K3)
    held = engine.portfolio.open_symbols()
    assert len(held) == 3, "the fixture must end holding three positions for this to mean anything"

    session = result.equity_curve[-1].session
    marks = {s: series[s].bars[session].open for s in held}
    generous = Decimal("1000000")
    engine.costs.max_open_risky_positions = 2
    try:
        with pytest.raises(InvariantViolation, match="MAX_POSITIONS: 3 positions are open"):
            engine._assert_ceilings_hold(session, held[0], marks[held[0]], marks, generous)
    finally:
        engine.costs.max_open_risky_positions = 3


# ==================================================================================================
# 2. combined gross exposure never exceeds 95% of equity
# ==================================================================================================


@pytest.mark.parametrize("variant_id", [K1, K2, K3, K2Q])
def test_the_whole_book_stays_inside_the_sealed_gross_cap(series, window, variant_id):
    result, engine, _, _ = run(series, window, variant_id)

    assert engine.costs.max_gross_exposure_fraction == MAX_GROSS
    records = ceiling_report(result, series)
    assert records
    for record in records:
        assert record["book_value"] <= MAX_GROSS * record["equity_before"], (
            f"{record['symbol']} on {record['session']}: book {record['book_value']} exceeds "
            f"{MAX_GROSS} of equity {record['equity_before']}"
        )


def test_an_oversized_request_at_k_3_is_clamped_by_the_aggregate_ceiling(series, window):
    """Injection for property 2: three simultaneous 50%-of-equity requests, against a 95% cap.

    A single-position engine would size each buy as if the book were empty and let the third one
    through. The aggregate clamp exists precisely to subtract what is already held.
    """
    result, engine, _, _ = run(series, window, K3, budget_weight=Decimal("0.50"))

    counts = engine.clamp_summary()["binding_clamp_counts"]
    assert counts["AGGREGATE"] > 0, "the aggregate ceiling never bound; the injection did not bite"
    for record in ceiling_report(result, series):
        assert record["book_value"] <= MAX_GROSS * record["equity_before"]


def test_the_engine_invariant_reports_a_book_over_the_gross_cap(series, window):
    """The assertion layer for property 2, driven directly.

    A small ``equity`` argument is the honest injection here: the invariant's statement is "the
    settled book is inside 95% of the equity the clamps were sized against", so handing it an
    equity the book is not inside must raise. The concentration branch is kept clear by asserting
    against a symbol whose own value is under half of the equity passed in.
    """
    result, engine, _, _ = run(series, window, K3)
    held = engine.portfolio.open_symbols()
    session = result.equity_curve[-1].session
    marks = {s: series[s].bars[session].open for s in held}
    book = sum((engine.portfolio.quantity_of(s) * marks[s] for s in held), ZERO)

    # Just under what the book needs: 95% of this equity is a shade below the book's value, while
    # 50% of it still exceeds any single holding.
    equity = (book / MAX_GROSS) - Decimal("0.01")
    with pytest.raises(InvariantViolation, match="MAX_GROSS_EXPOSURE: positions are worth"):
        engine._assert_ceilings_hold(session, held[0], marks[held[0]], marks, equity)


def test_the_clamp_labels_are_the_declared_ones(series, window):
    _, engine, _, _ = run(series, window, K3)
    summary = engine.clamp_summary()

    assert tuple(summary["binding_clamp_counts"]) == CLAMP_NAMES
    assert CLAMP_NAMES == ("REQUESTED_BUDGET", "AGGREGATE", "CASH_FLOOR", "CONCENTRATION")
    assert summary["max_gross_exposure_fraction"] == "0.95"
    assert summary["concentration_ceiling"] == "0.50"
    assert summary["open_stale_marks"] == 0


# ==================================================================================================
# 3. no single position ever exceeds 50% of equity at a rebalance
# ==================================================================================================


@pytest.mark.parametrize("variant_id", [K1, K2, K3, K2Q])
def test_no_purchase_leaves_its_position_above_the_concentration_ceiling(series, window, variant_id):
    """The ceiling is a constraint on *buying*, which is what "at a rebalance" means.

    §4 of the sealed protocol declares equal weight at entry with no trim and no top-up, and says in
    terms that "drift caused purely by price appreciation is not an order and is not trimmed". So a
    continuing holding may legitimately appreciate past 50% between rebalances; what may never
    happen is a purchase that leaves the bought position above the line. That is the statement
    asserted here, from the replay.
    """
    result, _, _, _ = run(series, window, variant_id)

    assert concentration_ceiling() == CONCENTRATION
    records = ceiling_report(result, series)
    assert records
    for record in records:
        assert record["position_value"] <= CONCENTRATION * record["equity_before"], (
            f"{record['symbol']} on {record['session']}: position {record['position_value']} "
            f"exceeds {CONCENTRATION} of equity {record['equity_before']}"
        )


def test_an_oversized_request_at_k_1_is_clamped_by_the_concentration_ceiling(series, window):
    """Injection for property 3, at the one breadth where only this ceiling can catch it.

    At k=1 a 95% request is inside the aggregate cap and inside the cash floor. Nothing but the
    concentration ceiling stands between it and a 95% single position — which is exactly why
    Generation 1's cost model needed no such field and Generation 2 does.
    """
    result, engine, _, _ = run(series, window, K1, budget_weight=Decimal("0.95"))

    counts = engine.clamp_summary()["binding_clamp_counts"]
    assert counts["CONCENTRATION"] > 0, "the concentration ceiling never bound"
    records = ceiling_report(result, series)
    assert records
    for record in records:
        assert record["position_value"] <= CONCENTRATION * record["equity_before"]


def test_the_engine_invariant_reports_a_position_over_the_concentration_ceiling(series, window):
    result, engine, _, _ = run(series, window, K3)
    held = engine.portfolio.open_symbols()
    session = result.equity_curve[-1].session
    marks = {s: series[s].bars[session].open for s in held}
    symbol = held[0]
    value = engine.portfolio.quantity_of(symbol) * marks[symbol]

    equity = (value / CONCENTRATION) - Decimal("0.01")
    with pytest.raises(InvariantViolation, match="CONCENTRATION_CEILING: buying"):
        engine._assert_ceilings_hold(session, symbol, marks[symbol], marks, equity)


def test_a_holding_left_out_of_the_marks_is_a_halt_not_a_smaller_sum(series, window):
    """A ceiling checked against a partial book would always pass. It must refuse instead."""
    result, engine, _, _ = run(series, window, K3)
    held = engine.portfolio.open_symbols()
    session = result.equity_curve[-1].session
    marks = {s: series[s].bars[session].open for s in held[1:]}

    with pytest.raises(InvariantViolation, match="was not marked at the open"):
        engine._assert_ceilings_hold(session, held[1], marks[held[1]], marks, Decimal("1000000"))


def test_the_ceiling_is_read_from_the_seal_and_not_from_the_caller(series, window):
    """``RotationEngine.__init__`` takes no ceiling argument, on purpose."""
    engine, _, _ = make_engine(series, window, K2)

    assert engine.concentration_ceiling == concentration_ceiling() == CONCENTRATION
    with pytest.raises(TypeError):
        RotationEngine(
            series,
            rotation_cost_model(2, BASE),
            window,
            rot.RotationCandidate(rot.variant_by_id(K2), rotation_cost_model(2, BASE), universe=SYMBOLS),
            concentration_ceiling=Decimal("0.95"),
        )


# ==================================================================================================
# 4. no order is bought or sold at the close that generated the ranking signal
# ==================================================================================================


def decision_session_of(order_id: str) -> dt.date:
    """``make_order_id`` puts the decision session first, in ISO form, by construction."""
    return dt.date.fromisoformat(order_id[:10])


@pytest.mark.parametrize("variant_id", [K1, K2, K3, K2Q])
def test_every_fill_happens_strictly_after_the_session_that_decided_it(series, window, variant_id):
    result, _, _, _ = run(series, window, variant_id)

    assert result.fills
    for record in result.fills:
        decided = decision_session_of(record.order_id)
        assert record.session > decided
        assert record.session == next_session_after(decided)


@pytest.mark.parametrize("variant_id", [K1, K2, K3, K2Q])
def test_no_fill_was_priced_at_any_close_in_the_dataset(series, window, variant_id):
    """The set-membership form. Opens and closes are disjoint in this fixture, so a reference price
    that is any close at all — today's or another symbol's — is a fill at a close."""
    result, _, _, _ = run(series, window, variant_id)
    closes = {bar.close for one in series.values() for bar in one.bars.values()}

    assert result.fills
    for record in result.fills:
        fill = record.fill
        assert fill.reference_price not in closes
        assert fill.reference_price == series[fill.symbol].bars[record.session].open


def test_an_order_that_would_fill_at_its_own_decision_close_cannot_be_constructed():
    """The structural half: the frozen ``Order`` contract refuses it before any engine sees it."""
    session = dt.date(2010, 3, 15)
    with pytest.raises(FillTimingError, match="cannot execute at that same close"):
        Order(
            order_id="probe",
            symbol="AAA",
            side=BUY,
            decision_session=session,
            fill_session=session,
            budget=Decimal("10.00"),
        )


def test_an_order_that_would_fill_before_its_decision_close_cannot_be_constructed():
    session = dt.date(2010, 3, 15)
    with pytest.raises(FillTimingError):
        Order(
            order_id="probe",
            symbol="AAA",
            side=BUY,
            decision_session=session,
            fill_session=session - dt.timedelta(days=1),
            budget=Decimal("10.00"),
        )


def test_a_scheduled_order_executed_on_the_wrong_session_is_an_invariant_violation(series, window):
    """Injection: a well-formed order handed to ``_execute_one`` on a session it was not scheduled
    for. The engine must refuse rather than reprice it at whatever bar it finds."""
    engine, _, _ = make_engine(series, window, K1)
    sessions = series[SYMBOLS[0]].sessions
    order = Order(
        order_id="probe",
        symbol="AAA",
        side=BUY,
        decision_session=sessions[0],
        fill_session=sessions[1],
        budget=Decimal("10.00"),
    )

    with pytest.raises(InvariantViolation, match="scheduled for .* but executed on"):
        engine._execute_one(sessions[2], order)


# ==================================================================================================
# 5. tomorrow's bar cannot enter today's ranking
# ==================================================================================================


DECISION = dt.date(2010, 9, 30)


def view_at(series, window, session):
    return MarketView(series, session, window)


def test_the_ranking_is_unchanged_when_every_future_bar_is_removed(series, window):
    """Truncation invariance: the strongest form of the property.

    If the ranking on 2010-09-30 is byte-identical whether or not the dataset holds any bar after
    that date, no future bar can have entered it. This subsumes "we called ``history``, which
    filters" — it tests the outcome rather than the mechanism.
    """
    variant = rot.variant_by_id(K3)
    costs = rotation_cost_model(variant.top_k, BASE)
    truncated = build_series(FIRST, DECISION)

    full_rank = rot.RotationCandidate(variant, costs, universe=SYMBOLS).rank(
        view_at(series, window, DECISION), DECISION
    )
    short_rank = rot.RotationCandidate(variant, costs, universe=SYMBOLS).rank(
        view_at(truncated, window, DECISION), DECISION
    )

    assert full_rank == short_rank
    assert full_rank[0], "the ranking is empty; the invariance would be vacuous"


def test_the_ranking_is_unchanged_when_the_future_is_replaced_by_a_different_future(series, window):
    """The complement of truncation: a future that exists but disagrees violently."""
    variant = rot.variant_by_id(K3)
    costs = rotation_cost_model(variant.top_k, BASE)
    divergent = build_series(bump=("AAA", dt.date(2010, 10, 1), 5000))

    baseline = rot.RotationCandidate(variant, costs, universe=SYMBOLS).rank(
        view_at(series, window, DECISION), DECISION
    )
    perturbed = rot.RotationCandidate(variant, costs, universe=SYMBOLS).rank(
        view_at(divergent, window, DECISION), DECISION
    )

    assert baseline == perturbed


def test_a_bar_the_decision_can_see_does_change_the_ranking(series, window):
    """Non-vacuity for the two tests above: the ranking is sensitive to data it may see.

    Without this, a ``rank`` that returned a constant would pass every invariance test in this
    section. The bump lands on the decision session's own close, which is the near endpoint of the
    sealed lookback — see the test below for why an interior bar would not have served.
    """
    variant = rot.variant_by_id(K3)
    costs = rotation_cost_model(variant.top_k, BASE)
    perturbed = build_series(bump=("BBB", DECISION, 900))

    baseline = rot.RotationCandidate(variant, costs, universe=SYMBOLS).rank(
        view_at(series, window, DECISION), DECISION
    )
    changed = rot.RotationCandidate(variant, costs, universe=SYMBOLS).rank(
        view_at(perturbed, window, DECISION), DECISION
    )

    assert baseline != changed
    assert baseline[0][-1][1] == "BBB", "BBB should start last, so the flip is unambiguous"
    assert changed[0][0][1] == "BBB", "the perturbed symbol should now rank first"


def test_an_interior_bar_is_invisible_to_the_ranking_by_the_sealed_formula(series, window):
    """A property of the signal, recorded here so it is never mistaken for a defect.

    §4 defines the signal as "N-month total return", which the implementation reads as the two
    endpoint bars — the decision close and the close N months back — and nothing between them. A
    bar strictly inside the lookback therefore cannot move the ranking. That is the declared
    formula, not an oversight, but it is also the reason the invariance tests above had to bump an
    *endpoint* to demonstrate their own non-vacuity: an interior bump would have left the ranking
    identical whether or not the guard worked.
    """
    variant = rot.variant_by_id(K3)
    costs = rotation_cost_model(variant.top_k, BASE)
    interior = dt.date(2010, 9, 29)
    assert DECISION > interior > rot.month_offset(DECISION, -3)

    baseline = rot.RotationCandidate(variant, costs, universe=SYMBOLS).rank(
        view_at(series, window, DECISION), DECISION
    )
    unmoved = rot.RotationCandidate(variant, costs, universe=SYMBOLS).rank(
        view_at(build_series(bump=("EEE", interior, 900)), window, DECISION), DECISION
    )

    assert baseline == unmoved


def test_a_symbol_without_enough_history_is_excluded_rather_than_scored_zero(series, window):
    """The early rebalances rank nothing at all, and that is the sealed meaning of ``None``.

    ``total_return`` returns ``None`` for a symbol whose lookback reaches before its first bar. If
    that were ever read as a zero return, such a symbol would outrank every loser in the universe
    and the strategy would systematically buy the youngest listing available.
    """
    variant = rot.variant_by_id(K3)
    costs = rotation_cost_model(variant.top_k, BASE)
    early = dt.date(2010, 2, 1)

    scored, excluded = rot.RotationCandidate(variant, costs, universe=SYMBOLS).rank(
        view_at(series, window, early), early
    )

    assert scored == []
    assert list(excluded) == sorted(SYMBOLS)
    assert all(rot.total_return(view_at(series, window, early), s, early, 3) is None for s in SYMBOLS)


def test_history_never_returns_a_bar_after_the_visibility_bound(series, window):
    view = view_at(series, window, DECISION)

    for symbol in SYMBOLS:
        bars = view.history(symbol, 10_000)
        assert bars
        assert bars[-1].session <= DECISION
        assert all(bar.session <= DECISION for bar in bars)


def test_asking_the_view_for_a_future_bar_raises(series, window):
    view = view_at(series, window, DECISION)
    tomorrow = next_session_after(DECISION)

    assert tomorrow is not None and tomorrow > DECISION
    with pytest.raises(LookAheadError):
        view.bar("AAA", tomorrow)


def test_the_visibility_bound_cannot_be_moved_after_construction(series, window):
    view = view_at(series, window, DECISION)

    with pytest.raises(LookAheadError, match="immutable"):
        view._as_of = dt.date(2010, 12, 31)
    assert view.as_of == DECISION


def test_a_signal_measured_to_a_future_session_is_not_scored(series, window):
    """``total_return`` returns ``None`` — excluded from the ranking — rather than raising.

    Asserted as the behaviour it actually has: ``_bars_back_to`` filters silently through
    ``history``, so the run to a future session simply has no bar ending on it. ``None`` is the
    sealed meaning of "cannot be ranked", and it is never read as zero.
    """
    view = view_at(series, window, DECISION)
    tomorrow = next_session_after(DECISION)

    assert rot.total_return(view, "AAA", tomorrow, 3) is None
    assert rot.total_return(view, "AAA", DECISION, 3) is not None


def test_a_whole_run_is_unchanged_by_data_after_its_end(window):
    """The end-to-end form: the run's own future cannot reach back into it."""
    short = build_series(FIRST, dt.date(2010, 9, 30))
    long = build_series(FIRST, LAST)
    end = dt.date(2010, 9, 30)

    a, _, ca, _ = run(short, window, K3, end=end)
    b, _, cb, _ = run(long, window, K3, end=end)

    assert a.trades_digest() == b.trades_digest()
    assert a.equity_digest() == b.equity_digest()
    assert ca.ranking_digest == cb.ranking_digest
    assert a.final_equity == b.final_equity


# ==================================================================================================
# 6. identical inputs on a clean rerun produce identical results
# ==================================================================================================


@pytest.mark.parametrize("variant_id", [K1, K2, K3, K2Q])
def test_a_clean_rerun_reproduces_the_run_exactly(series, window, variant_id):
    first, _, candidate_a, _ = run(series, window, variant_id)
    second, _, candidate_b, _ = run(series, window, variant_id)

    assert first.trades_digest() == second.trades_digest()
    assert first.equity_digest() == second.equity_digest()
    assert candidate_a.ranking_digest == candidate_b.ranking_digest
    assert len(first.fills) == len(second.fills)
    assert first.final_equity == second.final_equity
    assert first.final_cash == second.final_cash
    assert first.shutdown_session == second.shutdown_session


def test_a_rerun_from_a_freshly_built_dataset_reproduces_the_run(window):
    """Not the same objects: the series is rebuilt from scratch, so nothing is shared but the rule."""
    first, _, ca, _ = run(build_series(), window, K3)
    second, _, cb, _ = run(build_series(), window, K3)

    assert first.trades_digest() == second.trades_digest()
    assert ca.ranking_digest == cb.ranking_digest


def test_the_symbol_insertion_order_of_the_dataset_does_not_change_the_result(series, window):
    """The sealed tie-break is ``(-signal, symbol)``, so a reversed dict must change nothing.

    A ranking that fell back on dict order would pass every other test in this section, because
    every other test builds the dataset the same way twice.
    """
    reversed_series = {symbol: series[symbol] for symbol in reversed(SYMBOLS)}
    assert list(reversed_series) == list(reversed(SYMBOLS))

    first, _, ca, _ = run(series, window, K3)
    second, _, cb, _ = run(reversed_series, window, K3)

    assert first.trades_digest() == second.trades_digest()
    assert first.equity_digest() == second.equity_digest()
    assert ca.ranking_digest == cb.ranking_digest


def test_the_stressed_scenario_is_deterministic_too_and_differs_from_the_base_one(series, window):
    variant = rot.variant_by_id(K3)
    digests = []
    for _ in range(2):
        costs = rotation_cost_model(variant.top_k, STRESSED)
        candidate = rot.RotationCandidate(variant, costs, universe=SYMBOLS)
        sessions = series[SYMBOLS[0]].sessions
        engine = RotationEngine(
            series, costs, window, candidate,
            start=sessions[0], end=sessions[-1], label="stress",
            budget_weight=candidate.weight,
        )
        digests.append(engine.run().trades_digest())

    assert digests[0] == digests[1]
    base, _, _, _ = run(series, window, K3)
    assert base.trades_digest() != digests[0], "stressed frictions changed nothing; check the model"


def test_one_perturbed_bar_changes_the_digest(series, window):
    """Non-vacuity for the whole section: the digest is a function of the input, not a constant.

    The bump lands on 2010-06-01 — a scheduled rebalance, and an endpoint of the lookback measured
    there — on the symbol that ranks last that day. It therefore reorders the top-k and changes the
    orders the engine places. An interior bar would not have; see the look-ahead section.
    """
    perturbed = build_series(bump=("AAA", dt.date(2010, 6, 1), 900))

    first, _, ca, _ = run(series, window, K3)
    second, _, cb, _ = run(perturbed, window, K3)

    assert first.trades_digest() != second.trades_digest()
    assert ca.ranking_digest != cb.ranking_digest


def test_the_digests_cover_decisions_and_not_only_the_curve(series, window):
    """Two runs can agree on the equity curve while disagreeing about a rank that never traded.

    The ranking digest exists for that case, so it must be a genuine function of the rankings.
    """
    variant = rot.variant_by_id(K3)
    costs = rotation_cost_model(variant.top_k, BASE)
    empty = rot.RotationCandidate(variant, costs, universe=SYMBOLS)
    before = empty.ranking_digest

    empty.rank(view_at(series, window, DECISION), DECISION)
    assert empty.ranking_digest == before, "rank() alone must not fold into the digest"

    _, _, ran, _ = run(series, window, K3)
    assert ran.ranking_digest != before
    assert len(ran.ranking_digest) == 64
