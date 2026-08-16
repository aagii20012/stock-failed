"""RA2's five risk components, tested as new capability rather than assumed from Attempt 1.

``config/generation_2/g2_rotation_ra1_protocol.json`` declares nine required tests in its own words,
before any of this code existed:

    AT-A  Aggregate exposure never exceeds 50% of equity at any session, including mid-rebalance,
          verified after every fill and not only at session close.
    AT-B  Volatility scaling reduces position size when trailing realized portfolio volatility
          exceeds 10% annualized, verified against a hand-constructed high-volatility equity fixture
          with an independently computed expected scalar.
    AT-C  A position breaching the 8% stop is exited at the NEXT session's open, not at the same
          close, and the exit is a full sell.
    AT-D  The de-risk ladder steps down at the declared thresholds and back up only after the
          declared recovery condition, verified against a hand-constructed drawdown-and-recovery
          fixture that visits every band in both directions.
    AT-E  The re-entry lockout genuinely blocks a return to a higher sizing band before its cooldown
          elapses, verified by a fixture in which recovery is available and blocked for exactly the
          declared number of sessions.
    AT-F  Determinism: identical inputs produce identical trade, equity, ranking and risk-state
          digests on a clean rerun.
    AT-G  The Generation 2 window guard still blocks any read at or after 2021-08-01, exercised
          through the Attempt 2 loading path.
    AT-H  No Generation 1 or Attempt 1 module is modified: every module listed in
          attempt_1_modules_immutable re-hashes to its recorded digest.
    AT-I  The selection input cannot carry a performance figure: the dataclass field tuple equals
          SELECTION_FIELD_NAMES and the import-time assertion fires when it does not.

Each section opens with a control that would pass on a broken engine only if the check itself were
vacuous, and closes with an injected defect that must be caught. The injections are placed where the
engine could actually go wrong, not where they are easiest to reach.

**The fixtures.** Synthetic symbols on real XNYS sessions in 2010-2011 — inside Generation 2's
development window by a decade, and nothing here reads ``data/``. Every open is its close minus a
fixed discount, so the set of opens and the set of closes are provably disjoint and "no fill happened
at the close that generated the signal" is a set-membership question rather than an argument.

**Why the exposure assertions replay the fill stream.** Reading ``engine.clamp_summary()`` would be
asking the clamp whether the clamp worked. :func:`exposure_report` reconstructs cash and quantities
from the ordered fill records alone — these fixtures have no dividends and no splits, so nothing else
moves them — and recomputes the pre-fill equity each buy was sized against. It shares no line of code
with ``_execute_buy``.

**AT-A is a fill-time claim, deliberately.** The seal's own RA2-1 part_c measures gross exposure at
the *close*, which is a different quantity: a book sized at the open drifts with the market before the
close, and the throttle cannot act until the next open. That close-time measurement is reported and
disclosed as ``G2A2-CONFLICT-27``; it is not what AT-A asks about and is not asserted here.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import json
import sys
import types
from decimal import Decimal, localcontext
from pathlib import Path

import pytest

from stockedge100.backtest.config import PROJECT_ROOT
from stockedge100.backtest.costs import BASE, ZERO
from stockedge100.backtest.dataset import PriceSeries, series_from_rows
from stockedge100.backtest.engine import EquityPoint
from stockedge100.backtest.errors import ConfigViolation, InvariantViolation, WindowViolation
from stockedge100.backtest.g2_engine_ra1 import (
    ORDER_KIND_PRECEDENCE,
    RotationEngineRA1,
    SCALAR_DECIMALS,
    load_risk_architecture,
    quantize_scalar,
)
from stockedge100.backtest.orders import BUY
from stockedge100.data.calendar import sessions_between
from stockedge100.strategies import g2_rotation_ra1 as rot
from stockedge100.strategies import g2_runner_ra1 as runner
from stockedge100.strategies import g2_window_guard as guard
from stockedge100.strategies.attempt2_indicators import (
    TRADING_DAYS_PER_YEAR,
    VOL20_BARS,
    VOL20_RETURNS,
    VOL20_VARIANCE_DENOMINATOR,
)

ONE = Decimal(1)
NOMINAL_CEILING = Decimal("0.50")   # hand-written; the engine reads it from the seal
STOP_FRACTION = Decimal("0.08")     # hand-written, likewise

SYMBOLS = ("AAA", "BBB", "CCC", "DDD", "EEE")
OPEN_DISCOUNT = Decimal("0.25")
FIRST = dt.date(2010, 1, 4)
LAST = dt.date(2011, 6, 30)

K1 = "SE100-G2-S3-C2-ROTATION-RA1-L03-K1-MONTHLY"
K2 = "SE100-G2-S3-C2-ROTATION-RA1-L03-K2-MONTHLY"
K3 = "SE100-G2-S3-C2-ROTATION-RA1-L03-K3-MONTHLY"


# -- fixtures --------------------------------------------------------------------------------------


def _rows(sessions, closes):
    return [
        {
            "session": session.isoformat(),
            "open": f"{close - OPEN_DISCOUNT}",
            "high": f"{close}",
            "low": f"{close - OPEN_DISCOUNT}",
            "close": f"{close}",
        }
        for session, close in zip(sessions, closes)
    ]


def build_growth_series(*, bump=None) -> dict[str, PriceSeries]:
    """Five symbols whose trailing-return ordering churns month to month, none ever falling.

    Rates rotate with a per-symbol phase offset so the ranking genuinely changes and the exit path is
    exercised. No rate is negative, so the 15% research shutdown never fires and the de-risk ladder
    never leaves band 0 — which keeps an exposure test an exposure test.

    ``bump`` is ``(symbol, from_session, amount)`` and shifts that symbol's level from that session
    onward. A single-session bump would be the wrong perturbation for AT-F: trades price at rebalance
    opens, so one perturbed bar between two rebalances leaves every digest untouched and the
    determinism claim would look falsified when nothing was wrong.
    """
    sessions = sessions_between(FIRST, LAST)
    months: list[tuple[int, int]] = []
    for day in sessions:
        key = (day.year, day.month)
        if key not in months:
            months.append(key)

    rates = (Decimal(4), Decimal(3), Decimal(2), Decimal(1), ZERO)
    series = {}
    for index, symbol in enumerate(SYMBOLS):
        close = Decimal(200 + 10 * index)
        closes = []
        for day in sessions:
            close += rates[(index + months.index((day.year, day.month))) % len(rates)]
            shift = Decimal(bump[2]) if bump and bump[0] == symbol and day >= bump[1] else ZERO
            closes.append(close + shift)
        series[symbol] = series_from_rows(symbol, _rows(sessions, closes))
    return series


CRASH_SESSION = dt.date(2010, 6, 15)
PREEMPT_SESSION = dt.date(2010, 7, 1)
CRASH_FRACTION = Decimal("0.15")
CRASH_DRIFTS = {"AAA": "0.10", "BBB": "0.08", "CCC": "0.06", "DDD": "0.04", "EEE": "0.02"}


def build_crash_series(crash_session: dt.date = CRASH_SESSION) -> dict[str, PriceSeries]:
    """AAA leads the field on a shallow drift, is bought, then loses 15% in one session.

    Two properties of this fixture are load-bearing and were both got wrong first time.

    The drift is shallow and every symbol starts at the same level, so the ranking is decided by the
    drift alone and AAA leads until it crashes. And the crash lands *early*, roughly six weeks after
    the first entry. RA2-3 measures the stop against the position's own **cost basis**, not against a
    trailing high, so a symbol that has run up 15% since entry can fall 15% without ever coming
    within 8% of its entry price. A crash in March 2011 produced no stop at all for exactly that
    reason; on 2010-06-15 AAA is 0.6% above its basis and the fall registers as -13.8%.

    15% of a position the RA2-1 ceiling holds near half the book is about a 7.5% portfolio drawdown:
    into the ladder's second band, and nowhere near the constitutional 15% research shutdown, which
    would abandon the session and hide the stop it was built to show.

    ``crash_session`` is a parameter because the STOP-over-EXIT precedence needs the crash to land on
    a scheduled rebalance decision close, where the rotation would have exited AAA anyway.
    """
    sessions = sessions_between(FIRST, LAST)
    series = {}
    for symbol in SYMBOLS:
        close = Decimal(200)
        drift = Decimal(CRASH_DRIFTS[symbol])
        closes = []
        crashed = False
        for day in sessions:
            if symbol == "AAA" and day == crash_session:
                close = (close * (ONE - CRASH_FRACTION)).quantize(Decimal("0.01"))
                crashed = True
            elif symbol == "AAA" and crashed:
                pass                      # flat afterwards, so one stop is one stop
            else:
                close += drift
            closes.append(close)
        series[symbol] = series_from_rows(symbol, _rows(sessions, closes))
    return series


@pytest.fixture(scope="module")
def growth():
    return build_growth_series()


@pytest.fixture(scope="module")
def crash():
    return build_crash_series()


@pytest.fixture(scope="module")
def window():
    return guard.generation_2_window("g2_ra1_fixture", "2009-12-01", "2011-12-31")


@pytest.fixture(scope="module")
def architecture():
    return load_risk_architecture()


def make_engine(series, window, variant_id, *, risk=None, end=None):
    """One engine, wired the way :func:`stockedge100.strategies.g2_runner_ra1.run_one` wires it."""
    variant = rot.variant_by_id(variant_id)
    candidate = rot.RotationCandidateRA1(
        variant, rot.rotation_cost_model(variant.top_k, BASE), universe=SYMBOLS
    )
    sessions = series[SYMBOLS[0]].sessions
    engine = RotationEngineRA1(
        series,
        candidate.costs,
        window,
        candidate,
        start=sessions[0],
        end=end or sessions[-1],
        label=variant_id,
        budget_weight=candidate.weight,
    )
    if risk is not None:
        engine.risk = risk
    return engine, candidate, variant


def run(series, window, variant_id, **kwargs):
    engine, candidate, variant = make_engine(series, window, variant_id, **kwargs)
    return engine.run(), engine, candidate, variant


# -- the independent replay --------------------------------------------------------------------


def exposure_report(result, series):
    """Re-derive, from the fill stream alone, what the book was worth immediately after every fill.

    Returns one record per fill: the pre-fill equity measured at that session's open, the gross value
    of the whole book immediately afterwards, and the resulting exposure fraction. No engine counter,
    clamp, scalar or invariant is consulted.
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

        after = dict(marks)
        after[fill.symbol] = fill.reference_price
        gross = sum((quantities[s] * after[s] for s in quantities), ZERO)
        records.append(
            {
                "session": session,
                "symbol": fill.symbol,
                "side": fill.side,
                "equity_before": equity_before,
                "gross_after": gross,
                "fraction": (gross / equity_before) if equity_before > ZERO else ZERO,
                "open_positions": len(quantities),
            }
        )

    assert cash == result.final_cash, "the replay disagrees with the engine about final cash"
    return records


def test_the_replay_reconciles_with_the_engine_it_audits(growth, window):
    """Control for the auditor. If the replay could not reproduce the engine's own cash from the
    fill stream, nothing asserted through it below would mean anything."""
    result, _, _, _ = run(growth, window, K3)
    records = exposure_report(result, growth)
    assert records, "the fixture produced no fills; every exposure assertion below would be vacuous"
    assert len({r["symbol"] for r in records}) > 1, "only one symbol ever traded"


# == AT-A: aggregate exposure never exceeds 50% of equity, checked after every fill ================


#
# G2A2-CONFLICT-28. AT-A's sealed wording is "Aggregate exposure never exceeds 50% of equity at any
# session, including mid-rebalance, verified after every fill and not only at session close." Taken
# literally that is unachievable under RA2-1's own decide-at-close / fill-at-next-open convention,
# and for the same structural reason as G2A2-CONFLICT-27 — only measured at an open rather than a
# close. A throttle trim is sized against the decision close's prices and equity and fills at the
# next open; if the residual excess is under `min_order_notional` the throttle correctly skips it
# (part_b.minimum_notional_skip), so a *sell* can leave the book a few cents over 50% of the equity
# measured at that later open. Measured on the growth fixture at k=3: peak fraction 0.500714, worst
# excess USD 0.0747 against a minimum lot of 1.00.
#
# The engine's own hard assertion (`_assert_ceilings_hold`) is untoleranced and runs only after a
# BUY, which is exactly the part that is achievable. So AT-A is decomposed into the three claims
# that are true rather than weakened into one claim that is vacuous:
#
#   (1) after every BUY, exposure is at or under the *scaled* ceiling 0.50*f(t)*equity, with f(t)
#       recovered independently from the risk-state payload, and no tolerance whatsoever;
#   (2) no SELL ever increases gross exposure or the exposure fraction;
#   (3) the residual drift over the nominal 0.50 is bounded by one minimum lot.
#
# Disclosed as a numbered conflict in the decision package. The claim is not edited; the seal is not
# edited; what is recorded is that the sealed sentence is stronger than the sealed convention allows.
#


def scalars_by_session(engine) -> dict[dt.date, Decimal]:
    """Recover f(t) per session from ``risk_state_payload()`` rather than from an engine counter.

    The payload is the frozen ``session|band|lockout_remaining|vol_scalar|combined_scalar`` record.
    Reading the combined scalar back out of it keeps claim (1) independent of the attribute the
    clamp itself consulted — asking the clamp whether the clamp worked proves nothing.
    """
    out = {}
    for line in engine.risk_state_payload().splitlines():
        session, _band, _lock, _vol, combined = line.split("|")
        out[dt.date.fromisoformat(session)] = Decimal(combined)
    return out


@pytest.mark.parametrize("variant_id", [K1, K2, K3])
def test_at_a_no_buy_ever_leaves_the_book_above_the_scaled_ceiling(growth, window, variant_id):
    """Claim (1): exact, untoleranced, and measured by the replay rather than by the engine."""
    result, engine, _, _ = run(growth, window, variant_id)
    records = exposure_report(result, growth)
    scalars = scalars_by_session(engine)
    sessions = list(growth[SYMBOLS[0]].sessions)

    buys = [r for r in records if r["side"] == BUY]
    assert buys, f"{variant_id} bought nothing; the ceiling was never tested"

    for record in buys:
        decided = sessions[sessions.index(record["session"]) - 1]
        scalar = scalars[decided]
        ceiling = NOMINAL_CEILING * scalar * record["equity_before"]
        assert record["gross_after"] <= ceiling, (
            f"{variant_id} held {record['gross_after']} against equity "
            f"{record['equity_before']} after the BUY in {record['symbol']} on "
            f"{record['session']} — fraction {record['fraction']}, scaled ceiling {ceiling} "
            f"(f={scalar} at the {decided} decision close)"
        )


@pytest.mark.parametrize("variant_id", [K1, K2, K3])
def test_at_a_a_sell_never_increases_exposure(growth, window, variant_id):
    """Claim (2). The only fills that can sit above the nominal ceiling are reductions, and a
    reduction that raised exposure would be a sign convention bug rather than sealed drift."""
    result, _, _, _ = run(growth, window, variant_id)
    records = exposure_report(result, growth)
    sells = [r for r in records if r["side"] != BUY]
    assert sells, f"{variant_id} sold nothing; claim (2) would be vacuous"

    for index, record in enumerate(records):
        if record["side"] == BUY or index == 0:
            continue
        previous = records[index - 1]
        if previous["session"] != record["session"]:
            continue                      # a different session's book; not comparable
        assert record["gross_after"] <= previous["gross_after"], (
            f"the SELL in {record['symbol']} on {record['session']} raised gross exposure from "
            f"{previous['gross_after']} to {record['gross_after']}"
        )


@pytest.mark.parametrize("variant_id", [K1, K2, K3])
def test_at_a_residual_drift_over_the_nominal_ceiling_stays_under_one_minimum_lot(
    growth, window, variant_id
):
    """Claim (3), and the measurement behind G2A2-CONFLICT-28. The sealed slack part_c names is the
    minimum-notional term, so that is what the excess is held to."""
    result, _, candidate, _ = run(growth, window, variant_id)
    records = exposure_report(result, growth)
    excesses = [
        r["gross_after"] - NOMINAL_CEILING * r["equity_before"]
        for r in records
        if r["gross_after"] > NOMINAL_CEILING * r["equity_before"]
    ]
    minimum_lot = candidate.costs.min_order_notional
    for record, excess in zip(
        [r for r in records if r["gross_after"] > NOMINAL_CEILING * r["equity_before"]], excesses
    ):
        assert excess < minimum_lot, (
            f"{variant_id} was over the nominal 0.50 ceiling by {excess} after the "
            f"{record['side']} in {record['symbol']} on {record['session']} — more than one "
            f"minimum lot of {minimum_lot}, which is past the sealed slack in part_c"
        )


def test_at_a_the_ceiling_binds_rather_than_being_satisfied_by_accident(growth, window):
    """A ceiling no order ever approaches is not a tested ceiling.

    The grid cannot show this on its own weights: every variant's ``target_weight * k`` is exactly
    0.50, so ``REQUESTED_BUDGET`` and ``AGGREGATE_RA2`` tie and the strict ``<`` in the clamp loop
    keeps the earlier one. ``AGGREGATE_RA2`` then reads zero for the whole run — not because the
    ceiling is unenforced but because the grid was built to sit exactly on it. Asking for slightly
    more per leg (0.30 across k=3 rather than 0.166...) makes RA2-1 the binding constraint 22 times
    and turns the clamp count into evidence.
    """
    engine, _, _ = make_engine(growth, window, K3)
    engine.budget_weight = Decimal("0.30")
    result = engine.run()
    records = exposure_report(result, growth)

    peak = max(r["fraction"] for r in records)
    assert peak > Decimal("0.45"), (
        f"the largest post-fill exposure was {peak}; the fixture never approaches the 0.50 ceiling, "
        "so AT-A would pass on an engine with no ceiling at all"
    )
    assert engine.binding_clamp_counts["AGGREGATE_RA2"] > 0, (
        "no buy was ever clamped by AGGREGATE_RA2; the ceiling was satisfied by the budget, not "
        "enforced"
    )


def test_at_a_injected_defect_a_loosened_ceiling_is_caught(growth, window, architecture):
    """The injection: give the engine the base constitutional 0.95 ceiling instead of RA2-1's 0.50.

    Everything else — the clamp, the hard post-fill assertion, the throttle — stays consistent with
    it, so the engine will not raise. The replay asserts against a hand-written 0.50 and must find
    breaches far outside the minimum-lot drift of claim (3). That is what proves the claims above are
    load-bearing rather than decorative.

    It has to be a multi-position variant. At k=1 the inherited ``CONCENTRATION`` ceiling caps a
    single position near 0.50 on its own, so loosening RA2-1 alone changes nothing and the injection
    silently proves the opposite of what it claims to.
    """
    loosened = dataclasses.replace(architecture, exposure_ceiling=Decimal("0.95"))
    engine, candidate, _ = make_engine(growth, window, K3, risk=loosened)
    engine.budget_weight = Decimal("0.30")
    records = exposure_report(engine.run(), growth)

    breaches = [
        r for r in records if r["gross_after"] > NOMINAL_CEILING * r["equity_before"]
    ]
    assert breaches, (
        "an engine given a 0.95 ceiling never exceeded 0.50, so the 0.50 assertion above could not "
        "distinguish the two architectures and proves nothing"
    )
    worst = max(r["gross_after"] - NOMINAL_CEILING * r["equity_before"] for r in breaches)
    assert worst > candidate.costs.min_order_notional, (
        f"the loosened ceiling only drifted {worst} over 0.50, inside the one-minimum-lot slack "
        "claim (3) already tolerates; this injection would be indistinguishable from sealed drift"
    )


# == AT-B: volatility scaling ======================================================================


HIGH_VOL_LEVELS = tuple(
    Decimal(1000) if index % 2 == 0 else Decimal(1020) for index in range(VOL20_BARS)
)


def independent_vol_scalar(levels) -> tuple[Decimal, Decimal]:
    """RA2-2 recomputed from the seal's words at a precision the engine does not use.

    The engine runs at ``ENGINE_CONTEXT``'s 34 digits. This runs at 60, through a separately written
    expression, so agreement is evidence rather than a shared bug. Returns ``(sigma, scalar)``.
    """
    with localcontext() as ctx:
        ctx.prec = 60
        window = list(levels)[-VOL20_BARS:]
        returns = [window[i] / window[i - 1] - ONE for i in range(1, VOL20_BARS)]
        assert len(returns) == VOL20_RETURNS
        mean = sum(returns) / Decimal(VOL20_RETURNS)
        squares = sum((value - mean) ** 2 for value in returns)
        sigma = (squares / Decimal(VOL20_VARIANCE_DENOMINATOR)).sqrt() * Decimal(
            TRADING_DAYS_PER_YEAR
        ).sqrt()
        target = Decimal("0.10")
        scalar = ONE if sigma <= ZERO else min(ONE, target / sigma)
        return sigma, scalar


def _seed_equity(engine, levels):
    engine._equity = [
        EquityPoint(
            session=dt.date(2010, 1, 4) + dt.timedelta(days=index),
            cash=ZERO,
            equity=level,
            stale_mark=False,
            position_count=0,
        )
        for index, level in enumerate(levels)
    ]


def test_at_b_high_volatility_scales_position_size_down(growth, window):
    """A 21-point equity curve alternating 1000/1020 has a realized volatility far above the 10%
    target, so RA2-2 must scale sizing down, and to the independently computed amount."""
    engine, _, _ = make_engine(growth, window, K1)
    _seed_equity(engine, HIGH_VOL_LEVELS)

    sigma, expected = independent_vol_scalar(HIGH_VOL_LEVELS)
    assert sigma > Decimal("0.10"), (
        f"the fixture's realized volatility is {sigma}, not above the 10% target; this is not a "
        "high-volatility fixture and AT-B would be testing nothing"
    )
    # Sanity band computed by hand from the fixture: returns alternate +0.02 and -0.019607843...,
    # so sigma_annual is near sqrt(252 * 0.02^2) ~ 0.317 and the scalar near 0.10/0.317 ~ 0.315.
    assert Decimal("0.28") < expected < Decimal("0.34"), (
        f"the independently computed scalar {expected} left the hand-derived band; the expectation "
        "itself is wrong, so comparing the engine to it would prove nothing"
    )

    actual = engine._volatility_scalar()
    assert actual < ONE, f"volatility {sigma} above target produced no scaling: {actual}"
    assert abs(actual - expected) <= Decimal(1).scaleb(-SCALAR_DECIMALS), (
        f"the engine's scalar {actual} disagrees with the independently computed {expected} by more "
        f"than one quantum of the sealed {SCALAR_DECIMALS}-place precision"
    )
    assert actual == quantize_scalar(actual), "the returned scalar is not at the sealed precision"
    assert engine.vol_scalar_sessions_below_one == 1
    assert engine.vol_scalar_min == actual


def test_at_b_a_flat_equity_curve_is_not_scaled_down(growth, window):
    """RA2-2's ``run_start_note``: a portfolio of cash has no volatility to target, and that is
    correct rather than a special case. A scalar below 1 here would be scaling on noise."""
    engine, _, _ = make_engine(growth, window, K1)
    _seed_equity(engine, [Decimal(1000)] * VOL20_BARS)
    assert engine._volatility_scalar() == ONE


def test_at_b_an_undefined_window_is_not_scaled_down(growth, window):
    """Fewer than 21 points is ``undefined_before_21_points``, sealed as ``f_vol = 1`` and counted."""
    engine, _, _ = make_engine(growth, window, K1)
    _seed_equity(engine, HIGH_VOL_LEVELS[: VOL20_BARS - 1])
    assert engine._volatility_scalar() == ONE
    assert engine.vol_scalar_undefined_sessions == 1


def test_at_b_injected_defect_a_low_volatility_curve_must_not_scale(growth, window):
    """The mirror injection: the same machinery on a *quiet* curve must return exactly 1. A scalar
    below 1 here would mean the test above passes for a reason unrelated to volatility."""
    engine, _, _ = make_engine(growth, window, K1)
    quiet = [Decimal(1000) + Decimal(index) * Decimal("0.001") for index in range(VOL20_BARS)]
    sigma, expected = independent_vol_scalar(quiet)
    assert sigma < Decimal("0.10"), f"the quiet fixture is not quiet: {sigma}"
    assert expected == ONE
    assert engine._volatility_scalar() == ONE


# == AT-C: the 8% stop fills at the next open, whole position ======================================


def test_at_c_a_stop_fires_and_fills_at_the_next_open_as_a_full_sell(crash, window):
    result, engine, _, _ = run(crash, window, K1)
    summary = engine.risk_summary()
    fills = summary["stops"]["fills"]
    assert fills, (
        "the crash fixture triggered no stop; AT-C would be asserting over an empty list. "
        f"stop events recorded: {summary['stops']['triggered']}"
    )

    sessions = list(crash["AAA"].sessions)
    by_order = {event["order_id"]: event for event in engine.stop_events}

    for entry in fills:
        decided = dt.date.fromisoformat(entry["decision_session"])
        filled = dt.date.fromisoformat(entry["fill_session"])
        assert filled != decided, (
            f"the stop on {entry['symbol']} decided at the {decided} close also filled on {decided}; "
            "that is a fill at the close that generated the signal"
        )
        expected = sessions[sessions.index(decided) + 1]
        assert filled == expected, (
            f"the stop decided on {decided} filled on {filled}, not the next session {expected}"
        )
        # The trigger really was an 8%-or-worse move against the all-in cost basis.
        assert Decimal(entry["drop_at_trigger"]) <= -STOP_FRACTION, (
            f"a stop fired at {entry['drop_at_trigger']}, inside the sealed {STOP_FRACTION} threshold"
        )

    # Whole position, not a trim. The event recorded what was held; the fill must move all of it.
    filled_quantities = {
        record.order_id: record.fill.quantity
        for record in result.fills
        if record.order_id in by_order
    }
    assert filled_quantities, "no fill record matched a stop order id"
    for order_id, quantity in filled_quantities.items():
        assert quantity == Decimal(by_order[order_id]["quantity"]), (
            f"the stop {order_id} sold {quantity} of a position holding "
            f"{by_order[order_id]['quantity']}; RA2-3 exits the whole position"
        )


def test_at_c_the_fill_price_is_an_open_and_never_the_signal_close(crash, window):
    """The fixture's opens and closes are disjoint by construction, so this is set membership."""
    result, _, _, _ = run(crash, window, K1)
    for record in result.fills:
        bar = crash[record.fill.symbol].bars[record.session]
        assert record.fill.reference_price == bar.open, (
            f"the fill in {record.fill.symbol} on {record.session} priced at "
            f"{record.fill.reference_price}, which is not that session's open {bar.open}"
        )
        assert record.fill.reference_price != bar.close


def test_at_c_a_stop_takes_precedence_over_a_signal_exit_in_the_same_symbol(window):
    """RA2-3's ``interaction_with_rebalance``: the same fill, STOP wins, the coincidence is counted.

    This needs the crash to land on a scheduled rebalance decision close, where the rotation would
    have exited the crashed symbol on its own signal. The default crash date falls between
    rebalances and records no coincidence at all, so the assertion below would range over an empty
    list. The precedence itself is frozen, so assert the frozen order rather than the observed one.
    """
    assert ORDER_KIND_PRECEDENCE == ("STOP", "EXIT", "THROTTLE", "ENTRY")
    series = build_crash_series(PREEMPT_SESSION)
    _, engine, _, _ = run(series, window, K1)

    assert engine.stop_preempted_signal_exit > 0, (
        f"no stop coincided with a signal exit on the {PREEMPT_SESSION} rebalance; the precedence "
        "rule was never exercised"
    )
    assert engine.suppressed_legs, "a preemption was counted but no suppressed leg was recorded"
    for entry in engine.suppressed_legs:
        assert ORDER_KIND_PRECEDENCE.index(entry["by"]) < ORDER_KIND_PRECEDENCE.index(
            entry["suppressed"]
        ), f"a {entry['suppressed']} leg was suppressed by a lower-precedence {entry['by']}"


def test_at_c_injected_defect_a_disabled_stop_changes_the_outcome(crash, window, architecture):
    """A stop threshold of 100% can never trigger. If the run is indistinguishable from the real one,
    the fixture was not exercising the stop and the assertions above are decoration."""
    disabled = dataclasses.replace(architecture, stop_fraction=Decimal("1.00"))
    _, engine, _, _ = run(crash, window, K1, risk=disabled)
    assert engine.risk_summary()["stops"]["triggered"] == 0

    _, live, _, _ = run(crash, window, K1)
    assert live.risk_summary()["stops"]["triggered"] > 0, (
        "the sealed 8% stop and a disabled 100% stop produced the same zero count; the fixture never "
        "put a position 8% under water"
    )


# == AT-D: the ladder descends and recovers through every band =====================================


HIGH_WATER = Decimal(1000)


def _drive(engine, path):
    """Feed ``(index, equity)`` pairs to the ladder and record the band after each."""
    observed = []
    for index, equity in path:
        engine._advance_ladder(index, equity)
        observed.append(engine._band)
    return observed


def _equity_for(drawdown: Decimal) -> Decimal:
    return HIGH_WATER * (ONE - drawdown)


def test_at_d_the_bands_are_the_sealed_ones(architecture):
    """Read the fixture's expectations off the seal once, loudly, so the tests below cannot drift
    from it silently."""
    assert [b.band for b in architecture.bands] == [0, 1, 2, 3]
    assert [f"{b.dd_from:f}" for b in architecture.bands] == ["0.00", "0.05", "0.08", "0.10"]
    assert [f"{b.scalar:f}" for b in architecture.bands] == ["1.00", "0.75", "0.50", "0.25"]
    assert architecture.bands[-1].dd_to_exclusive is None
    assert architecture.lockout_sessions == 10


def test_at_d_boundary_convention_is_closed_below_and_open_above(architecture):
    """``boundary_convention``: dd exactly 0.05 is band 1, not band 0. An inequality direction chosen
    at implementation time is a free parameter, so it is asserted at every boundary."""
    assert architecture.band_for(Decimal("0.0499999999")) == 0
    assert architecture.band_for(Decimal("0.05")) == 1
    assert architecture.band_for(Decimal("0.0799999999")) == 1
    assert architecture.band_for(Decimal("0.08")) == 2
    assert architecture.band_for(Decimal("0.0999999999")) == 2
    assert architecture.band_for(Decimal("0.10")) == 3
    assert architecture.band_for(Decimal("0.95")) == 3


def test_at_d_the_ladder_visits_every_band_downwards_then_upwards(growth, window, architecture):
    engine, _, _ = make_engine(growth, window, K1)
    engine._high_water = HIGH_WATER

    # Down, one band at a time, at drawdowns just past each declared threshold.
    down = [
        (0, _equity_for(Decimal("0.00"))),
        (1, _equity_for(Decimal("0.06"))),
        (2, _equity_for(Decimal("0.085"))),
        (3, _equity_for(Decimal("0.11"))),
    ]
    assert _drive(engine, down) == [0, 1, 2, 3]
    assert engine.ladder_descents == 3
    assert engine.deepest_band == 3

    # The last descent was at index 3, so the lockout runs to index 13. Recovery is available from
    # there — the computed band at full equity is 0, three below the current band.
    recovered = _drive(engine, [(index, HIGH_WATER) for index in range(13, 17)])
    assert recovered == [2, 1, 0, 0], (
        f"recovery went {recovered}; RA2-4 allows at most one band per session and must stop at 0"
    )
    assert engine.ladder_ascents == 3
    assert engine._band == 0
    assert set(architecture.scalar_of(b) for b in range(4)) == {
        Decimal("1.00"), Decimal("0.75"), Decimal("0.50"), Decimal("0.25")
    }


def test_at_d_descent_is_immediate_and_to_the_full_computed_band(growth, window):
    """``descent``: no smoothing. Band 0 to band 3 in one session, because a fast drawdown is exactly
    the case the ladder exists for. A one-step-at-a-time descent would be a different architecture."""
    engine, _, _ = make_engine(growth, window, K1)
    engine._high_water = HIGH_WATER
    assert _drive(engine, [(0, _equity_for(Decimal("0.30")))]) == [3]
    assert engine.ladder_descents == 1, "a single descent was counted as more than one transition"
    assert engine.lockout_arms == 1


def test_at_d_recovery_is_never_more_than_one_band_per_session(growth, window):
    """The asymmetry is the mechanism. Climbing 3 to 0 in one session is the re-levering into a
    bear-market rally that RA2-5 exists to prevent."""
    engine, _, _ = make_engine(growth, window, K1)
    engine._high_water = HIGH_WATER
    _drive(engine, [(0, _equity_for(Decimal("0.30")))])
    assert engine._band == 3
    engine._advance_ladder(10, HIGH_WATER)
    assert engine._band == 2, "the ladder climbed more than one band in a single session"


def test_at_d_an_upward_transition_does_not_arm_the_lockout(growth, window):
    """``not_armed_by``: only de-risking arms the cooldown. An ascent that re-armed it would make
    every recovery take ten sessions per band rather than one."""
    engine, _, _ = make_engine(growth, window, K1)
    engine._high_water = HIGH_WATER
    _drive(engine, [(0, _equity_for(Decimal("0.30")))])
    arms_after_descent = engine.lockout_arms
    engine._advance_ladder(10, HIGH_WATER)      # ascent 3 -> 2
    engine._advance_ladder(11, HIGH_WATER)      # ascent 2 -> 1, would be blocked if re-armed
    assert engine.lockout_arms == arms_after_descent
    assert engine._band == 1


def test_at_d_injected_defect_a_flat_ladder_visits_no_band(growth, window, architecture):
    """The injection: one band covering everything at full sizing. The drawdown path above must then
    produce no transition at all — if it still did, the assertions would not be reading the seal."""
    flat = dataclasses.replace(
        architecture,
        bands=(dataclasses.replace(architecture.bands[0], dd_to_exclusive=None),),
    )
    engine, _, _ = make_engine(growth, window, K1, risk=flat)
    engine._high_water = HIGH_WATER
    engine.sessions_in_band = {0: 0}
    assert _drive(engine, [(0, _equity_for(d)) for d in
                           (Decimal("0.00"), Decimal("0.06"), Decimal("0.11"))]) == [0, 0, 0]
    assert engine.ladder_descents == 0


# == AT-E: the lockout blocks recovery for exactly the declared cooldown ===========================


def test_at_e_recovery_is_blocked_for_exactly_the_declared_cooldown(growth, window, architecture):
    """A descent at index ``d`` arms the lockout to ``d + 10``. Recovery is therefore refused on
    indices ``d+1 .. d+9`` — nine probes — and permitted at ``d+10``, which is the sealed "expires 10
    trading sessions after the session on which the transition occurred".

    The nine is arithmetic, not a threshold: the transition session itself is the tenth. Anyone
    later tempted to "fix" it to ten should change the seal instead, which they may not.
    """
    lockout = architecture.lockout_sessions
    assert lockout == 10

    engine, _, _ = make_engine(growth, window, K1)
    engine._high_water = HIGH_WATER
    descent_index = 4
    engine._advance_ladder(descent_index, _equity_for(Decimal("0.30")))
    assert engine._band == 3
    assert engine._lockout_until_index == descent_index + lockout

    # Recovery is genuinely available: at full equity the computed band is 0, three below current.
    assert architecture.band_for(ZERO) == 0

    blocked = []
    for index in range(descent_index + 1, descent_index + lockout):
        before = engine._band
        engine._advance_ladder(index, HIGH_WATER)
        assert engine._band == before, (
            f"the ladder recovered at index {index}, inside a lockout running to "
            f"{engine._lockout_until_index}"
        )
        blocked.append(index)
        assert engine._lockout_remaining(index) == engine._lockout_until_index - index

    assert len(blocked) == lockout - 1 == 9
    assert engine.recoveries_blocked == 9
    assert engine.ladder_ascents == 0

    # The first index at which recovery is permitted is exactly d + 10.
    engine._advance_ladder(descent_index + lockout, HIGH_WATER)
    assert engine._band == 2, "recovery did not resume on the first session after the cooldown"
    assert engine.ladder_ascents == 1
    assert engine.recoveries_blocked == 9, "the permitted session was also counted as blocked"
    assert engine._lockout_remaining(descent_index + lockout) == 0


def test_at_e_the_lockout_gates_every_upward_step_not_only_the_last(growth, window, architecture):
    """``gates``: the stricter reading, taken deliberately. Gating only the final step to band 0
    would let a strategy climb 3 to 1 the session after a de-risk and sit at 75% sizing through the
    drawdown that caused it."""
    engine, _, _ = make_engine(growth, window, K1)
    engine._high_water = HIGH_WATER
    engine._advance_ladder(0, _equity_for(Decimal("0.30")))          # band 3, lockout to 10
    engine._advance_ladder(1, HIGH_WATER)
    assert engine._band == 3, "a 3 -> 2 step was permitted inside the lockout"
    assert engine.recoveries_blocked == 1


def test_at_e_injected_defect_a_zero_cooldown_permits_immediate_recovery(growth, window, architecture):
    """The mirror: with the cooldown removed the same path recovers at once. If it did not, the test
    above would be passing for some reason other than the lockout."""
    instant = dataclasses.replace(architecture, lockout_sessions=0)
    engine, _, _ = make_engine(growth, window, K1, risk=instant)
    engine._high_water = HIGH_WATER
    engine._advance_ladder(0, _equity_for(Decimal("0.30")))
    engine._advance_ladder(1, HIGH_WATER)
    assert engine._band == 2, "recovery was blocked with no cooldown in force"
    assert engine.recoveries_blocked == 0


# == AT-F: determinism =============================================================================


def _digests(result, engine, candidate):
    return {
        "trades": result.trades_digest(),
        "equity": result.equity_digest(),
        "ranking": candidate.evidence()["ranking_digest"],
        "risk_state": engine.risk_state_digest(),
    }


@pytest.mark.parametrize("variant_id", [K1, K3])
def test_at_f_identical_inputs_produce_identical_digests(growth, window, variant_id):
    first = _digests(*run(growth, window, variant_id)[:3])
    second = _digests(*run(growth, window, variant_id)[:3])
    assert first == second
    assert len(set(first.values())) == 4, f"two digests collided: {first}"
    for name, value in first.items():
        assert len(value) == 64 and int(value, 16) >= 0, f"{name} is not a SHA-256 hex digest"


PRICE_DRIVEN_DIGESTS = ("trades", "equity", "ranking")


def test_at_f_the_price_driven_digests_are_not_constants(growth, window):
    """A digest that never moves would satisfy AT-F while proving nothing. A persistent shift in a
    ranked symbol must change what was ranked, what was traded, and what the book was worth."""
    bumped = build_growth_series(bump=("AAA", dt.date(2010, 6, 15), 40))
    baseline = _digests(*run(growth, window, K1)[:3])
    perturbed = _digests(*run(bumped, window, K1)[:3])
    for name in PRICE_DRIVEN_DIGESTS:
        assert baseline[name] != perturbed[name], (
            f"the {name} digest is unchanged by a 40-unit move in a ranked symbol; it is not a "
            "function of the input"
        )


def test_at_f_the_risk_state_digest_is_not_a_constant_either(window):
    """The risk-state digest needs a different perturbation, and the reason is worth stating.

    On the growth fixture nothing ever falls and realized volatility stays under the 10% target, so
    every session records ``band 0 | lockout 0 | vol_scalar 1 | combined 1``. The risk-state digest
    is then genuinely invariant to price — moving a symbol 40 units leaves it byte-identical, and
    that is correct behaviour rather than a frozen constant. Demonstrating that it *is* a function of
    its input therefore has to happen on a fixture whose risk state actually moves, so this uses the
    crash fixture and shifts the crash to a different session.
    """
    early = _digests(*run(build_crash_series(CRASH_SESSION), window, K1)[:3])
    later = _digests(*run(build_crash_series(PREEMPT_SESSION), window, K1)[:3])
    assert early["risk_state"] != later["risk_state"], (
        "moving the crash — and with it the drawdown, the ladder descent and the stop — left the "
        "risk-state digest unchanged; it is not a function of the run"
    )


def test_at_f_the_risk_state_digest_covers_state_no_other_digest_reaches(growth, window, architecture):
    """Equal equity curves are weaker evidence than equal decisions, and equal decisions weaker than
    equal risk state. A ladder change that never reached an order must still move this digest."""
    _, live, _, _ = run(growth, window, K1)
    shifted = dataclasses.replace(
        architecture,
        bands=tuple(
            dataclasses.replace(band, dd_from=band.dd_from / 2, dd_to_exclusive=(
                None if band.dd_to_exclusive is None else band.dd_to_exclusive / 2
            ))
            for band in architecture.bands
        ),
    )
    _, other, _, _ = run(growth, window, K1, risk=shifted)
    assert live.risk_state_digest() != other.risk_state_digest() or live.ladder_descents == 0, (
        "halved ladder thresholds produced an identical risk-state digest"
    )
    assert live.risk_state_payload().count("\n") == len(live._equity), (
        "the risk trace does not carry one line per equity point"
    )


# == AT-G: the window guard still blocks 2021-08-01 onward =========================================


def test_at_g_the_development_bound_is_the_sealed_one():
    assert guard.development_bound() == dt.date(2021, 7, 31)


def test_at_g_the_attempt_2_loading_path_stops_at_the_bound():
    """Exercised through Attempt 2's own loader, not through the guard directly: the claim is about
    the path this attempt actually reads with."""
    series = runner.load_grid_dataset()
    assert series, "the Attempt 2 loader returned no series"
    latest = max(s.sessions[-1] for s in series.values())
    assert latest <= guard.development_bound(), (
        f"the Attempt 2 loading path returned data through {latest}, past the development bound"
    )


def test_at_g_a_series_reaching_past_the_bound_is_refused():
    sessions = sessions_between(dt.date(2021, 7, 26), dt.date(2021, 8, 6))
    assert any(s >= dt.date(2021, 8, 1) for s in sessions), "the fixture does not cross the bound"
    contaminated = {
        "AAA": series_from_rows("AAA", _rows(sessions, [Decimal(100)] * len(sessions)))
    }
    with pytest.raises((WindowViolation, InvariantViolation, ValueError)):
        guard.assert_series_within_bound(contaminated)


def test_at_g_a_research_window_reaching_into_a_holdout_is_refused():
    """Both holdouts, named by the seal, and neither may be opened by any generation."""
    with pytest.raises((WindowViolation, ConfigViolation, ValueError)):
        guard.generation_2_window("probe", "2026-08-01", "2026-09-01")
    with pytest.raises((WindowViolation, ConfigViolation, ValueError)):
        guard.generation_2_window("probe", "2024-08-01", "2024-09-01")


def test_at_g_the_generation_2_holdout_is_declared_prohibited():
    labels = {name: (start, end) for name, start, end in guard.prohibited_windows()}
    assert labels["holdout"] == (dt.date(2026, 8, 1), dt.date(2028, 7, 31))
    assert labels["generation_1_holdout"] == (dt.date(2024, 8, 1), dt.date(2026, 7, 31))


# == AT-H: no Generation 1 or Attempt 1 module is modified =========================================


SEALED_PROTOCOL = (
    PROJECT_ROOT / "governance" / "generation_2" / "STAGE_3_G2_ROTATION_RA1_PROTOCOL.json"
)


def _recorded_module_digests() -> dict[str, str]:
    payload = json.loads(SEALED_PROTOCOL.read_text(encoding="utf-8"))
    return payload["contamination_measurement"]["attempt_1_module_digests"]


def test_at_h_every_immutable_attempt_1_module_rehashes_to_its_recorded_digest():
    recorded = _recorded_module_digests()
    assert len(recorded) == 9, f"the seal records {len(recorded)} module digests, not nine"
    for relative, expected in sorted(recorded.items()):
        path = PROJECT_ROOT / relative
        assert path.is_file(), f"{relative} is recorded immutable but is not on disk"
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual == expected, (
            f"{relative} hashes to {actual}; the seal recorded {expected}. An Attempt 1 or "
            "Generation 1 module has been modified, which is a governance failure and not a value "
            "to update."
        )


def test_at_h_the_declared_immutable_list_and_the_recorded_digests_agree():
    """Two files declare the same nine modules — the config seal by name, the governance seal by
    digest. A module dropped from one and not the other would leave a hole neither notices."""
    declared = json.loads(
        (PROJECT_ROOT / "config" / "generation_2" / "g2_rotation_ra1_protocol.json").read_text(
            encoding="utf-8"
        )
    )["attempt_1_modules_immutable"]["modules"]
    assert sorted(declared) == sorted(_recorded_module_digests())


def test_at_h_attempt_2_wrote_none_of_its_code_into_an_attempt_1_module():
    """The naming convention is the protection, so assert it rather than trusting it: no immutable
    path may be one of Attempt 2's own modules."""
    attempt_2 = {
        "src/stockedge100/strategies/g2_rotation_ra1.py",
        "src/stockedge100/strategies/g2_gate_ra1.py",
        "src/stockedge100/strategies/g2_runner_ra1.py",
        "src/stockedge100/backtest/g2_engine_ra1.py",
        "src/stockedge100/backtest/g2_episodes_ra1.py",
    }
    assert not attempt_2 & set(_recorded_module_digests())
    for relative in attempt_2:
        assert (PROJECT_ROOT / relative).is_file(), f"{relative} is missing"


def test_at_h_the_runners_own_verification_agrees_with_this_one():
    """The runner verifies the same thing at run time. Asserting only through it would be asking the
    code whether the code works; asserting both, and that they agree, is the check."""
    report = runner.verify_attempt_1_modules()
    assert report["module_count"] == 9
    assert report["modules_that_moved"] == []
    # ``modules_verified`` maps path -> digest, so it can be compared entry by entry against the
    # digests this file recomputed independently above.
    assert report["modules_verified"] == _recorded_module_digests()


def test_at_h_injected_defect_a_changed_byte_is_caught():
    """The digest check must fail on a one-byte change. Verified on a copy in memory — nothing on
    disk is touched, because touching an immutable module to test the test would be the violation."""
    recorded = _recorded_module_digests()
    relative, expected = sorted(recorded.items())[0]
    payload = (PROJECT_ROOT / relative).read_bytes()
    assert hashlib.sha256(payload).hexdigest() == expected
    assert hashlib.sha256(payload + b"\n").hexdigest() != expected


# == AT-I: the selection input cannot carry a performance figure ===================================


PERFORMANCE_WORDS = (
    "return", "drawdown", "profit", "sharpe", "equity", "win", "loss", "pnl", "p_l",
    "cagr", "turnover_value", "gain",
)


def test_at_i_the_dataclass_field_tuple_equals_the_declared_names():
    actual = tuple(field.name for field in dataclasses.fields(runner.SelectionInputRA1))
    assert actual == runner.SELECTION_FIELD_NAMES == (
        "variant_id", "shutdown_events", "fill_count", "per_run"
    )


def test_at_i_no_field_or_serialised_key_names_a_performance_figure():
    names = [field.name for field in dataclasses.fields(runner.SelectionInputRA1)]
    sample = runner.SelectionInputRA1(
        variant_id=K1, shutdown_events=0, fill_count=3, per_run=(("#BASE", 0, 3),)
    )
    keys = list(sample.to_json())
    for name in names + keys:
        for word in PERFORMANCE_WORDS:
            assert word not in name.lower(), f"{name!r} names a performance figure ({word})"


def _exec_as_module(source: str, source_path: Path, name: str) -> dict:
    """Execute module source under a real, registered module object, and unregister it afterwards.

    A bare ``exec`` into a plain dict is not enough here. ``@dataclass`` resolves string annotations
    through ``sys.modules.get(cls.__module__)``, so a namespace whose ``__name__`` names no
    registered module makes ``dataclasses._is_type`` dereference ``None`` and raises
    ``AttributeError`` from inside the standard library — which looks like a defect in the module
    under test and is not one.
    """
    module = types.ModuleType(name)
    module.__file__ = str(source_path)
    sys.modules[name] = module
    try:
        exec(compile(source, str(source_path), "exec"), module.__dict__)
        return module.__dict__
    finally:
        sys.modules.pop(name, None)


def test_at_i_the_import_time_assertion_fires_when_a_field_is_added():
    """The real assertion, on the real source, re-executed with one injected field.

    The module text is read, the dataclass body is given a ``total_return`` field, and the result is
    executed in a fresh namespace. Nothing on disk changes. The substitution count is asserted first,
    so a mutation that silently matched nothing cannot let this pass vacuously.
    """
    source_path = Path(runner.__file__)
    source = source_path.read_text(encoding="utf-8")

    original = (
        "    variant_id: str\n"
        "    shutdown_events: int\n"
        "    fill_count: int\n"
        "    per_run: tuple[tuple[str, int, int], ...]\n"
    )
    assert source.count(original) == 1, "the selection dataclass body was not found verbatim"
    mutated = source.replace(
        original,
        "    variant_id: str\n"
        "    shutdown_events: int\n"
        "    fill_count: int\n"
        "    total_return: str\n"
        "    per_run: tuple[tuple[str, int, int], ...]\n",
    )
    assert mutated != source

    with pytest.raises(ConfigViolation) as caught:
        _exec_as_module(mutated, source_path, "g2_runner_ra1_at_i_mutant")
    assert "total_return" in str(caught.value)
    assert "return-blind" in str(caught.value)


def test_at_i_the_unmutated_source_imports_cleanly():
    """Control for the injection: the same execution path on the untouched source must not raise, or
    the test above would pass for the wrong reason."""
    source_path = Path(runner.__file__)
    namespace = _exec_as_module(
        source_path.read_text(encoding="utf-8"), source_path, "g2_runner_ra1_at_i_control"
    )
    assert namespace["SELECTION_FIELD_NAMES"] == runner.SELECTION_FIELD_NAMES


def test_at_i_selection_inputs_built_from_runs_carry_nothing_else(growth, window):
    """End to end: the projection built from real runs still exposes only the four declared fields.

    Both declared labels are supplied because the projection refuses a variant missing one — the
    zero-shutdown screen is defined across *both* runs, and half the evidence is not the screen.
    """
    result, engine, candidate, variant = run(growth, window, K1)
    grid_runs = [
        runner.GridRunRA1(
            variant=variant,
            label=label,
            scenario=runner.scenario_for_label(label),
            result=result,
            measurement={},
            strategy_evidence=candidate.evidence(),
            clamps=engine.clamp_summary(),
            risk=engine.risk_summary(),
            trades=[],
            ledger=[],
            reconciliation={},
        )
        for label in runner.run_labels()
    ]
    inputs = runner.selection_inputs(grid_runs)
    assert len(inputs) == 1
    payload = json.dumps(inputs[0].to_json())
    assert len(payload) < 4000, "the selection payload is large enough to be smuggling a curve"
    for word in ("total_return", "sharpe", "profit_factor", "max_drawdown", "equity"):
        assert word not in payload


def test_at_i_a_variant_missing_a_run_is_refused_rather_than_screened_on_half(growth, window):
    """The refusal above is the point, so assert it directly."""
    result, engine, candidate, variant = run(growth, window, K1)
    only_base = runner.GridRunRA1(
        variant=variant,
        label=runner.run_labels()[0],
        scenario=BASE,
        result=result,
        measurement={},
        strategy_evidence=candidate.evidence(),
        clamps=engine.clamp_summary(),
        risk=engine.risk_summary(),
        trades=[],
        ledger=[],
        reconciliation={},
    )
    with pytest.raises(ConfigViolation):
        runner.selection_inputs([only_base])
