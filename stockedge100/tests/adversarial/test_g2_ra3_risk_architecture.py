"""RA3's five risk components, tested against the seal rather than against Attempt 2's behaviour.

``config/generation_2/g2_rotation_ra3_protocol.json`` (``SE100-CFG-3105``) declares its required
tests in its own words, before any of this code existed. Its own note on the point:

    "Declared here before the tests exist, so that the test suite is written against a specification
    rather than against the implementation's behaviour. Each item is a required test, not a
    suggestion."

The requirements this module covers, verbatim from that node:

    AT-A  Aggregate exposure never exceeds 50% of equity at any session, including mid-rebalance,
          verified after every fill and not only at session close.
    AT-B  Volatility scaling reduces position size when trailing realized portfolio volatility
          exceeds 10% annualized, verified against a hand-constructed high-volatility equity fixture
          with an independently computed expected scalar.
    AT-C  A position breaching the 8% stop is exited at the NEXT session's open, not at the same
          close, and the exit is a full sell.
    AT-D  The de-risk ladder steps down at the declared RA3 thresholds and back up only after the
          declared recovery condition, verified against a hand-constructed drawdown-and-recovery
          fixture that visits every band in both directions. The fixture must include a drawdown
          that reaches 6 percent and assert that the combined ladder scalar is exactly 1 there,
          which is the single behavioural difference from RA2 and would otherwise be tested only by
          absence.
    AT-E  The re-entry lockout genuinely blocks a return to a higher sizing band before its cooldown
          elapses, verified by a fixture in which recovery is available and blocked for exactly the
          declared number of sessions.
    AT-F  Determinism: identical inputs produce identical trade, equity, ranking and risk-state
          digests on a clean rerun.
    AT-G  The Generation 2 window guard still blocks any read at or after 2021-08-01, exercised
          through the Attempt 3 loading path. The guard is reused, not reimplemented, and the test
          asserts that the module under test is the existing g2_window_guard.
    AT-H  No Generation 1, Attempt 1 or Attempt 2 module is modified: every one of the seventeen
          modules listed in prior_attempt_modules_immutable re-hashes to its recorded digest.
    AT-L  The RA3 band table is the sealed one and contains no band boundary below 0.08: the loaded
          architecture has exactly three bands, its scalars are strictly decreasing in (0, 1], its
          first band starts at 0.00 with scalar 1.00, its last band is open-ended, and the absolute
          aggregate ceilings it induces equal 0.500000000 / 0.250000000 / 0.125000000.
    AT-M  The RA3 engine re-derives exactly the risk-dependent attributes it must after calling
          super().__init__, verified by parsing the Attempt 2 engine's __init__ for the attributes
          assigned from self.risk and asserting the RA3 subclass reassigns precisely that set. This
          is the same AST mechanism Attempt 2 used against Attempt 1's __init__.

AT-I, AT-J and AT-K are the selection rule's, and live in
``tests/adversarial/test_g2_sel2_selection_rule.py``. The sealed ``regression_floor`` item — "The
existing suite is a permanent regression floor. No test is weakened, skipped or deleted to make this
attempt pass." — is a property of the session, not a test, and is evidenced in the stage report.

Each section opens with a control and closes with an injected defect that must be caught.

**The fixtures.** Synthetic symbols on real XNYS sessions in 2010-2011 — inside Generation 2's
development window by a decade, and nothing here reads ``data/`` except the one AT-G test that
deliberately exercises the loader. Every open is its close minus a fixed discount, so the set of
opens and the set of closes are provably disjoint and "no fill happened at the close that generated
the signal" is a set-membership question rather than an argument.

**Why the exposure assertions replay the fill stream.** Reading ``engine.clamp_summary()`` would be
asking the clamp whether the clamp worked. :func:`exposure_report` reconstructs cash and quantities
from the ordered fill records alone — these fixtures have no dividends and no splits, so nothing else
moves them — and recomputes the pre-fill equity each buy was sized against. It shares no line of code
with ``_execute_buy``.

**AT-A is a fill-time claim, deliberately.** The seal's own RA3-1 measures gross exposure at the
*close*, which is a different quantity: a book sized at the open drifts with the market before the
close, and the throttle cannot act until the next open. That close-time measurement is disclosed as
``G2A3-CONFLICT-27``; it is not what AT-A asks about and is not asserted here. The decomposition of
AT-A into three achievable claims is ``G2A3-CONFLICT-28``, restated at that section's head.

**Three claims inherited from Attempt 2's equivalent module do not carry to RA3, and are restated
from measurement rather than copied.** They are called out where they occur: the ladder's descent
path under the same drawdowns (RA2 ``[0, 1, 2, 3]``, RA3 ``[0, 0, 1, 2]``), the crash fixture's
effect on the ladder (RA2 reached its second band, RA3 never leaves band 0), and the
``AGGREGATE_RA2`` clamp count on the grid's own weights (RA2 read zero throughout, RA3 reads 9 at
k=3 and 11 at k=2, and zero only at k=1). Copying any of the three would have produced an assertion
that was true of a different architecture.

**The clamp keeps its RA2 name under RA3.** ``binding_clamp_counts`` is keyed by
``CLAMP_NAMES_RA2``, because RA3 subclasses Attempt 2's engine and changes only the ladder; the
aggregate-ceiling clamp is byte-identical code. The name is a provenance record, not a claim that
RA2 is in force, and renaming it would have modified a closed Attempt 2 module.
"""

from __future__ import annotations

import copy
import dataclasses
import datetime as dt
import hashlib
import json
import sys
import types
from decimal import Decimal, localcontext
from pathlib import Path

import pytest

from stockedge100.backtest import g2_engine_ra3 as eng3
from stockedge100.backtest.config import PROJECT_ROOT
from stockedge100.backtest.costs import BASE, ZERO
from stockedge100.backtest.dataset import PriceSeries, series_from_rows
from stockedge100.backtest.engine import EquityPoint
from stockedge100.backtest.errors import ConfigViolation, InvariantViolation, WindowViolation
from stockedge100.backtest.g2_engine_ra1 import (
    ORDER_KIND_PRECEDENCE,
    SCALAR_DECIMALS,
    RotationEngineRA1,
    load_risk_architecture,
    quantize_scalar,
)
from stockedge100.backtest.g2_engine_ra3 import (
    DELETED_RA2_TIER,
    RA3_BAND_COUNT,
    RA3_SHALLOWEST_ENGAGEMENT,
    RISK_DERIVED_ATTRIBUTES,
    RotationEngineRA3,
    attributes_derived_from_risk,
    check_generation_1_provenance,
    check_single_difference_from_ra2,
    load_risk_architecture_ra3,
)
from stockedge100.backtest.orders import BUY
from stockedge100.data.calendar import sessions_between
from stockedge100.strategies import g2_gate_ra3 as gate
from stockedge100.strategies import g2_rotation_ra3 as rot
from stockedge100.strategies import g2_runner_ra3 as runner
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
SHALLOWEST_ENGAGEMENT = Decimal("0.08")  # hand-written; RA3's single difference from RA2

SYMBOLS = ("AAA", "BBB", "CCC", "DDD", "EEE")
OPEN_DISCOUNT = Decimal("0.25")
FIRST = dt.date(2010, 1, 4)
LAST = dt.date(2011, 6, 30)

K1 = "SE100-G2-S3-C3-ROTATION-RA3-L03-K1-MONTHLY"
K2 = "SE100-G2-S3-C3-ROTATION-RA3-L03-K2-MONTHLY"
K3 = "SE100-G2-S3-C3-ROTATION-RA3-L03-K3-MONTHLY"

GOVERNANCE_SEAL = (
    PROJECT_ROOT / "governance" / "generation_2" / "STAGE_3_G2_ROTATION_RA3_PROTOCOL.json"
)
CONFIG_SEAL = PROJECT_ROOT / "config" / "generation_2" / "g2_rotation_ra3_protocol.json"


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
    never leaves band 0 — which keeps an exposure test an exposure test. Under RA3 that is doubly
    true: the ladder's shallowest engagement is 8% rather than RA2's 5%.

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

    Two properties of this fixture are load-bearing and were both got wrong first time in Attempt 2.

    The drift is shallow and every symbol starts at the same level, so the ranking is decided by the
    drift alone and AAA leads until it crashes. And the crash lands *early*, roughly six weeks after
    the first entry. RA3-3 measures the stop against the position's own **cost basis**, not against a
    trailing high, so a symbol that has run up 15% since entry can fall 15% without ever coming
    within 8% of its entry price. A crash in March 2011 produced no stop at all for exactly that
    reason; on 2010-06-15 AAA is 0.6% above its basis and the fall registers as -13.8%.

    **The one claim Attempt 2 made here that does not carry.** Attempt 2's copy of this docstring
    said the resulting portfolio drawdown lands "into the ladder's second band". Under RA3 it does
    not: 15% of a position the RA3-1 ceiling holds near half the book is about a 7.5% portfolio
    drawdown, which is *inside* RA3's full-sizing band and outside RA2's. Measured on this fixture,
    ``ladder_descents`` is 0 under RA3 and the ladder never leaves band 0. That is the single
    behavioural difference from RA2 showing up in a fixture built before it, and it is asserted
    under AT-D rather than left as an unremarked change. It remains nowhere near the constitutional
    15% research shutdown, which would abandon the session and hide the stop this exists to show.

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
    return guard.generation_2_window("g2_ra3_fixture", "2009-12-01", "2011-12-31")


@pytest.fixture(scope="module")
def architecture():
    return load_risk_architecture_ra3()


@pytest.fixture(scope="module")
def architecture_ra2():
    """Attempt 2's architecture, loaded read-only. Every "single difference" claim is asserted
    against the thing it claims to differ from, not against a remembered description of it."""
    return load_risk_architecture()


def make_engine(series, window, variant_id, *, risk=None, end=None):
    """One engine, wired the way :func:`stockedge100.strategies.g2_runner_ra3.run_one` wires it."""
    variant = rot.variant_by_id(variant_id)
    candidate = rot.RotationCandidateRA3(
        variant, rot.rotation_cost_model(variant.top_k, BASE), universe=SYMBOLS
    )
    sessions = series[SYMBOLS[0]].sessions
    engine = RotationEngineRA3(
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


# == controls ======================================================================================


def test_control_the_replay_reconciles_with_the_engine_it_audits(growth, window):
    """Control for the auditor. If the replay could not reproduce the engine's own cash from the
    fill stream, nothing asserted through it below would mean anything."""
    result, _, _, _ = run(growth, window, K3)
    records = exposure_report(result, growth)
    assert records, "the fixture produced no fills; every exposure assertion below would be vacuous"
    assert len({r["symbol"] for r in records}) > 1, "only one symbol ever traded"


def test_control_the_growth_fixture_never_engages_the_ladder(growth, window):
    """Control for the exposure section. Nothing in the growth fixture ever falls, so the combined
    scalar must be exactly 1 at every session. If it were not, the AT-A ceiling assertions would be
    measuring a throttled book and could pass on an engine whose ceiling did nothing."""
    _, engine, _, _ = run(growth, window, K3)
    distinct = {value for value in scalars_by_session(engine).values()}
    assert distinct == {Decimal("1.000000000")}, (
        f"the growth fixture produced combined scalars {sorted(distinct)}; it is supposed to leave "
        "the risk architecture entirely at rest"
    )
    assert engine.ladder_descents == 0


def test_control_opens_and_closes_are_disjoint_by_construction(growth):
    """Control for every "the fill priced at an open, not at the signal close" claim below. The
    property is arithmetic, so assert it once rather than restating it as prose each time."""
    for symbol in SYMBOLS:
        series = growth[symbol]
        opens = {bar.open for bar in series.bars.values()}
        closes = {bar.close for bar in series.bars.values()}
        assert opens & closes == set(), f"{symbol} has a bar whose open equals some bar's close"


def test_control_the_loaded_architecture_is_ra3_and_not_ra2(architecture, architecture_ra2):
    """Control for the whole module: the object under test is the new architecture. A test suite
    that silently loaded RA2 would pass most of what follows and prove nothing about Attempt 3."""
    assert architecture.architecture_id == "RA3"
    assert architecture_ra2.architecture_id == "RA2"
    assert len(architecture.bands) == RA3_BAND_COUNT == 3
    assert len(architecture_ra2.bands) == 4
    assert architecture.bands != architecture_ra2.bands


# == AT-A: aggregate exposure never exceeds 50% of equity, checked after every fill ================


#
# G2A3-CONFLICT-28. AT-A's sealed wording is "Aggregate exposure never exceeds 50% of equity at any
# session, including mid-rebalance, verified after every fill and not only at session close." Taken
# literally that is unachievable under RA3-1's own decide-at-close / fill-at-next-open convention,
# and for the same structural reason as G2A3-CONFLICT-27 — only measured at an open rather than a
# close. A throttle trim is sized against the decision close's prices and equity and fills at the
# next open; if the residual excess is under `min_order_notional` the throttle correctly skips it,
# so a *sell* can leave the book a few cents over 50% of the equity measured at that later open.
# Measured on the growth fixture under RA3: peak fraction 0.500714 at k=3 with a 0.30 leg weight,
# worst excess USD 0.0747 against a minimum lot of 1.00; every one of the over-nominal fills at
# every k is a SELL.
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
    """Claim (3), and the measurement behind G2A3-CONFLICT-28. The sealed slack RA3-1 names is the
    minimum-notional term, so that is what the excess is held to."""
    result, _, candidate, _ = run(growth, window, variant_id)
    records = exposure_report(result, growth)
    over = [r for r in records if r["gross_after"] > NOMINAL_CEILING * r["equity_before"]]
    minimum_lot = candidate.costs.min_order_notional

    for record in over:
        excess = record["gross_after"] - NOMINAL_CEILING * record["equity_before"]
        assert excess < minimum_lot, (
            f"{variant_id} was over the nominal 0.50 ceiling by {excess} after the "
            f"{record['side']} in {record['symbol']} on {record['session']} — more than one "
            f"minimum lot of {minimum_lot}, which is past the sealed slack"
        )
        assert record["side"] != BUY, (
            f"a BUY left the book over the nominal ceiling on {record['session']}; claim (3) "
            "tolerates drift only on reductions"
        )


def test_at_a_the_ceiling_binds_rather_than_being_satisfied_by_accident(growth, window):
    """A ceiling no order ever approaches is not a tested ceiling.

    **This is one of the three claims Attempt 2's module made that does not carry to RA3.** Attempt
    2 recorded that ``AGGREGATE_RA2`` read zero for the whole run on the grid's own weights, because
    every variant's ``target_weight * k`` is exactly 0.50 and the strict ``<`` in the clamp loop
    keeps ``REQUESTED_BUDGET`` on the tie. Measured under RA3 that is true only at k=1, where the
    inherited ``CONCENTRATION`` ceiling binds first: the counts are 0 at k=1, 11 at k=2 and 9 at
    k=3. The cause is not asserted here — only the measurement, and the consequence, which is that
    the injection below must use a multi-position variant.

    Asking for slightly more per leg (0.30 across k=3 rather than 0.166...) makes RA3-1 the binding
    constraint 22 times and turns the clamp count into evidence at the point where the ceiling is
    unambiguously the only thing holding the book down.
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
        "no buy was ever clamped by the aggregate ceiling; it was satisfied by the budget, not "
        "enforced"
    )

    single, _, _ = make_engine(growth, window, K1)
    single.run()
    assert single.binding_clamp_counts["AGGREGATE_RA2"] == 0, (
        "the k=1 variant now reports aggregate clamping; the note above — and the choice of k=3 "
        "for the injection below — was written against a measurement that no longer holds"
    )


def test_at_a_injected_defect_a_loosened_ceiling_is_caught(growth, window, architecture):
    """The injection: give the engine the base constitutional 0.95 ceiling instead of RA3-1's 0.50.

    Everything else — the clamp, the hard post-fill assertion, the throttle — stays consistent with
    it, so the engine will not raise. The replay asserts against a hand-written 0.50 and must find
    breaches far outside the minimum-lot drift of claim (3). That is what proves the claims above are
    load-bearing rather than decorative.

    It has to be a multi-position variant. Measured under RA3, the same injection at k=1 produces
    zero breaches and a worst excess of zero — the inherited ``CONCENTRATION`` ceiling caps a single
    position near 0.50 on its own, so loosening RA3-1 alone changes nothing there and the injection
    would silently prove the opposite of what it claims to.
    """
    loosened = dataclasses.replace(architecture, exposure_ceiling=Decimal("0.95"))
    engine, candidate, _ = make_engine(growth, window, K3, risk=loosened)
    engine.budget_weight = Decimal("0.30")
    records = exposure_report(engine.run(), growth)

    breaches = [r for r in records if r["gross_after"] > NOMINAL_CEILING * r["equity_before"]]
    assert breaches, (
        "an engine given a 0.95 ceiling never exceeded 0.50, so the 0.50 assertion above could not "
        "distinguish the two architectures and proves nothing"
    )
    worst = max(r["gross_after"] - NOMINAL_CEILING * r["equity_before"] for r in breaches)
    assert worst > candidate.costs.min_order_notional, (
        f"the loosened ceiling only drifted {worst} over 0.50, inside the one-minimum-lot slack "
        "claim (3) already tolerates; this injection would be indistinguishable from sealed drift"
    )

    inert, _, _ = make_engine(growth, window, K1, risk=loosened)
    inert_records = exposure_report(inert.run(), growth)
    inert_breaches = [
        r for r in inert_records if r["gross_after"] > NOMINAL_CEILING * r["equity_before"]
    ]
    assert not inert_breaches, (
        "the same injection now breaches at k=1 too; the docstring's account of why the injection "
        "must use a multi-position variant was written against a measurement that has moved"
    )


# == AT-B: volatility scaling ======================================================================


HIGH_VOL_LEVELS = tuple(
    Decimal(1000) if index % 2 == 0 else Decimal(1020) for index in range(VOL20_BARS)
)


def independent_vol_scalar(levels) -> tuple[Decimal, Decimal]:
    """RA3-2 recomputed from the seal's words at a precision the engine does not use.

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
            session=FIRST + dt.timedelta(days=index),
            cash=ZERO,
            equity=level,
            stale_mark=False,
            position_count=0,
        )
        for index, level in enumerate(levels)
    ]


def test_at_b_high_volatility_scales_position_size_down(growth, window):
    """A 21-point equity curve alternating 1000/1020 has a realized volatility far above the 10%
    target, so RA3-2 must scale sizing down, and to the independently computed amount."""
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


def test_at_b_the_volatility_component_is_unchanged_from_attempt_2(architecture, architecture_ra2):
    """RA3's ``single_difference_from_ra2`` is the ladder alone. If the volatility target had moved
    too, this attempt would be testing two changes at once and could not attribute either."""
    assert architecture.volatility_target == architecture_ra2.volatility_target == Decimal("0.10")
    assert architecture.exposure_ceiling == architecture_ra2.exposure_ceiling == NOMINAL_CEILING
    assert architecture.stop_fraction == architecture_ra2.stop_fraction == STOP_FRACTION
    assert architecture.lockout_sessions == architecture_ra2.lockout_sessions == 10


def test_at_b_a_flat_equity_curve_is_not_scaled_down(growth, window):
    """RA3-2's ``run_start_note``: a portfolio of cash has no volatility to target, and that is
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


def test_at_b_injected_defect_the_target_is_load_bearing(growth, window, architecture):
    """The target itself must be what decides the scalar. Widened to 1.00 the same high-volatility
    curve must not scale at all; tightened to 0.05 it must scale twice as hard. A scalar that
    ignored the target would pass the sealed-value test above by coincidence."""
    sealed, _, _ = make_engine(growth, window, K1)
    _seed_equity(sealed, HIGH_VOL_LEVELS)
    at_seal = sealed._volatility_scalar()

    loose = dataclasses.replace(architecture, volatility_target=Decimal("1.00"))
    widened, _, _ = make_engine(growth, window, K1, risk=loose)
    _seed_equity(widened, HIGH_VOL_LEVELS)
    assert widened._volatility_scalar() == Decimal("1.000000000")
    assert widened.vol_scalar_sessions_below_one == 0

    tight = dataclasses.replace(architecture, volatility_target=Decimal("0.05"))
    tightened, _, _ = make_engine(growth, window, K1, risk=tight)
    _seed_equity(tightened, HIGH_VOL_LEVELS)
    assert tightened._volatility_scalar() < at_seal < ONE, (
        "halving the target did not halve the sizing; the scalar is not a function of the target"
    )


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
            f"{by_order[order_id]['quantity']}; RA3-3 exits the whole position"
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


def test_at_c_the_stop_fires_without_the_ladder_moving(crash, window):
    """Under RA3 the crash fixture's drawdown lands inside the full-sizing band, so the stop is the
    *only* risk mechanism that acts. That makes AT-C's evidence cleaner than Attempt 2's, where a
    ladder descent happened at the same time — and it is asserted rather than assumed, because it is
    a change in what the fixture does."""
    _, engine, _, _ = run(crash, window, K1)
    assert engine.risk_summary()["stops"]["triggered"] > 0
    assert engine.ladder_descents == 0, (
        f"the crash fixture descended the RA3 ladder {engine.ladder_descents} times; the drawdown "
        "it produces was measured to stay inside the 8% full-sizing band, and AT-D's account of the "
        "single behavioural difference from RA2 rests on that measurement"
    )
    assert engine.lockout_arms == 0


def test_at_c_a_stop_takes_precedence_over_a_signal_exit_in_the_same_symbol(window):
    """RA3-3's ``interaction_with_rebalance``: the same fill, STOP wins, the coincidence is counted.

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
    assert engine.stop_events == []

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
    assert [b.band for b in architecture.bands] == [0, 1, 2]
    assert [f"{b.dd_from:f}" for b in architecture.bands] == ["0.00", "0.08", "0.10"]
    assert [f"{b.scalar:f}" for b in architecture.bands] == ["1.00", "0.50", "0.25"]
    assert architecture.bands[-1].dd_to_exclusive is None
    assert architecture.lockout_sessions == 10


def test_at_d_boundary_convention_is_closed_below_and_open_above(architecture):
    """``boundary_convention``: dd exactly 0.08 is band 1, not band 0. An inequality direction chosen
    at implementation time is a free parameter, so it is asserted at every boundary."""
    assert architecture.band_for(Decimal("0.0799999999")) == 0
    assert architecture.band_for(Decimal("0.08")) == 1
    assert architecture.band_for(Decimal("0.0999999999")) == 1
    assert architecture.band_for(Decimal("0.10")) == 2
    assert architecture.band_for(Decimal("0.95")) == 2


def test_at_d_a_six_percent_drawdown_leaves_ra3_at_full_sizing(architecture, architecture_ra2):
    """The seal's own named requirement inside AT-D:

        "The fixture must include a drawdown that reaches 6 percent and assert that the combined
        ladder scalar is exactly 1 there, which is the single behavioural difference from RA2 and
        would otherwise be tested only by absence."

    Asserted against RA2 at the same drawdown, because "unchanged from RA2 everywhere else" is only
    meaningful if the one place it *is* changed is shown to differ.
    """
    six = Decimal("0.06")
    assert architecture.band_for(six) == 0
    assert architecture.scalar_of(architecture.band_for(six)) == Decimal("1.00")

    assert architecture_ra2.band_for(six) == 1, (
        "RA2 no longer engages its ladder at a 6% drawdown; the difference this whole attempt rests "
        "on has moved, and that is a governance finding rather than a test to update"
    )
    assert architecture_ra2.scalar_of(architecture_ra2.band_for(six)) == Decimal("0.75")

    # And across the whole width of the tier RA3 deleted, not only at 6%.
    for drawdown in ("0.05", "0.055", "0.06", "0.07", "0.0799"):
        value = Decimal(drawdown)
        assert architecture.scalar_of(architecture.band_for(value)) == Decimal("1.00")
        assert architecture_ra2.scalar_of(architecture_ra2.band_for(value)) == Decimal("0.75")


def test_at_d_the_ladder_visits_every_band_downwards_then_upwards(growth, window, architecture):
    """**The second claim from Attempt 2's module that does not carry.** The same four drawdowns
    that walked RA2 through ``[0, 1, 2, 3]`` walk RA3 through ``[0, 0, 1, 2]``: the 6% step is now
    absorbed by the full-sizing band. The path is restated from measurement, not copied.
    """
    engine, _, _ = make_engine(growth, window, K1)
    engine._high_water = HIGH_WATER

    down = [
        (0, _equity_for(Decimal("0.00"))),
        (1, _equity_for(Decimal("0.06"))),
        (2, _equity_for(Decimal("0.09"))),
        (3, _equity_for(Decimal("0.12"))),
    ]
    assert _drive(engine, down) == [0, 0, 1, 2], "the RA3 ladder did not absorb the 6% drawdown"
    assert engine.ladder_descents == 2
    assert engine.deepest_band == 2
    assert engine.lockout_arms == 2

    # The last descent was at index 3, so the lockout runs to index 13. Nine probes are refused,
    # recovery resumes at 13, and the ladder climbs at most one band per session thereafter.
    recovered = _drive(engine, [(index, HIGH_WATER) for index in range(4, 26)])
    assert recovered == [2] * 9 + [1] + [0] * 12, (
        f"recovery went {recovered}; RA3-4 allows at most one band per session, refuses any step "
        "inside the cooldown, and must stop at 0"
    )
    assert engine.ladder_ascents == 2
    assert engine.recoveries_blocked == 9
    assert engine._band == 0
    assert engine.sessions_in_band == {0: 14, 1: 2, 2: 10}
    assert {architecture.scalar_of(b) for b in range(RA3_BAND_COUNT)} == {
        Decimal("1.00"), Decimal("0.50"), Decimal("0.25")
    }


def test_at_d_descent_is_immediate_and_to_the_full_computed_band(growth, window):
    """``descent``: no smoothing. Band 0 to band 2 in one session, because a fast drawdown is exactly
    the case the ladder exists for. A one-step-at-a-time descent would be a different architecture."""
    engine, _, _ = make_engine(growth, window, K1)
    engine._high_water = HIGH_WATER
    assert _drive(engine, [(0, _equity_for(Decimal("0.30")))]) == [2]
    assert engine.ladder_descents == 1, "a single descent was counted as more than one transition"
    assert engine.lockout_arms == 1


def test_at_d_recovery_is_never_more_than_one_band_per_session(growth, window):
    """The asymmetry is the mechanism. Climbing 2 to 0 in one session is the re-levering into a
    bear-market rally that RA3-5 exists to prevent."""
    engine, _, _ = make_engine(growth, window, K1)
    engine._high_water = HIGH_WATER
    _drive(engine, [(0, _equity_for(Decimal("0.30")))])
    assert engine._band == 2
    engine._advance_ladder(10, HIGH_WATER)
    assert engine._band == 1, "the ladder climbed more than one band in a single session"


def test_at_d_an_upward_transition_does_not_arm_the_lockout(growth, window):
    """``not_armed_by``: only de-risking arms the cooldown. An ascent that re-armed it would make
    every recovery take ten sessions per band rather than one."""
    engine, _, _ = make_engine(growth, window, K1)
    engine._high_water = HIGH_WATER
    _drive(engine, [(0, _equity_for(Decimal("0.30")))])
    arms_after_descent = engine.lockout_arms
    engine._advance_ladder(10, HIGH_WATER)      # ascent 2 -> 1
    engine._advance_ladder(11, HIGH_WATER)      # ascent 1 -> 0, would be blocked if re-armed
    assert engine.lockout_arms == arms_after_descent
    assert engine._band == 0


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
                           (Decimal("0.00"), Decimal("0.09"), Decimal("0.12"))]) == [0, 0, 0]
    assert engine.ladder_descents == 0


def test_at_d_injected_defect_ra2_s_deleted_tier_reinstated_changes_the_path(growth, window):
    """The mirror of the 6% assertion, driven through the engine rather than through ``band_for``.
    Under RA2's four-band ladder the same path descends at 6% and reaches band 3; under RA3 it does
    not. If both produced the same path, nothing in this attempt would have changed."""
    engine_ra2, _, _ = make_engine(growth, window, K1, risk=load_risk_architecture())
    engine_ra2._high_water = HIGH_WATER
    engine_ra2.sessions_in_band = {index: 0 for index in range(4)}
    path = [
        (0, _equity_for(Decimal("0.00"))),
        (1, _equity_for(Decimal("0.06"))),
        (2, _equity_for(Decimal("0.09"))),
        (3, _equity_for(Decimal("0.12"))),
    ]
    assert _drive(engine_ra2, path) == [0, 1, 2, 3]
    assert engine_ra2.ladder_descents == 3, (
        "RA2 descended fewer than three times on the path RA3 descends twice on; the comparison "
        "this attempt's whole rationale rests on is not what it was measured to be"
    )


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
    assert engine._band == 2
    assert engine._lockout_until_index == descent_index + lockout == 14

    # Recovery is genuinely available: at full equity the computed band is 0, two below current.
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
    assert engine._band == 1, "recovery did not resume on the first session after the cooldown"
    assert engine.ladder_ascents == 1
    assert engine.recoveries_blocked == 9, "the permitted session was also counted as blocked"
    assert engine._lockout_remaining(descent_index + lockout) == 0


def test_at_e_the_lockout_gates_every_upward_step_not_only_the_last(growth, window, architecture):
    """``gates``: the stricter reading, taken deliberately. Gating only the final step to band 0
    would let a strategy climb 2 to 1 the session after a de-risk and sit at 50% sizing through the
    drawdown that caused it."""
    engine, _, _ = make_engine(growth, window, K1)
    engine._high_water = HIGH_WATER
    engine._advance_ladder(0, _equity_for(Decimal("0.30")))          # band 2, lockout to 10
    engine._advance_ladder(1, HIGH_WATER)
    assert engine._band == 2, "a 2 -> 1 step was permitted inside the lockout"
    assert engine.recoveries_blocked == 1


def test_at_e_the_cooldown_is_the_one_ra3_inherited(architecture, architecture_ra2):
    """RA3-5 is untouched by this attempt. A cooldown that had also changed would make the ladder
    comparison against Attempt 2 uninterpretable."""
    assert architecture.lockout_sessions == architecture_ra2.lockout_sessions == 10


def test_at_e_injected_defect_a_zero_cooldown_permits_immediate_recovery(growth, window, architecture):
    """The mirror: with the cooldown removed the same path recovers at once. If it did not, the test
    above would be passing for some reason other than the lockout."""
    instant = dataclasses.replace(architecture, lockout_sessions=0)
    engine, _, _ = make_engine(growth, window, K1, risk=instant)
    engine._high_water = HIGH_WATER
    engine._advance_ladder(0, _equity_for(Decimal("0.30")))
    engine._advance_ladder(1, HIGH_WATER)
    assert engine._band == 1, "recovery was blocked with no cooldown in force"
    assert engine.recoveries_blocked == 0


# == AT-F: determinism =============================================================================


def _digests(result, engine, candidate):
    return {
        "trades": result.trades_digest(),
        "equity": result.equity_digest(),
        "ranking": candidate.evidence()["ranking_digest"],
        "risk_state": engine.risk_state_digest(),
    }


@pytest.mark.parametrize("variant_id", [K1, K2, K3])
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
    assert baseline["risk_state"] == perturbed["risk_state"], (
        "the risk-state digest moved on a fixture where nothing ever falls; under RA3 every session "
        "of the growth fixture records band 0 with a unit scalar, so a change here means the trace "
        "is carrying something other than risk state"
    )


def test_at_f_the_risk_state_digest_is_not_a_constant_either(window):
    """The risk-state digest needs a different perturbation, and the reason is worth stating.

    On the growth fixture nothing ever falls and realized volatility stays under the 10% target, so
    every session records ``band 0 | lockout 0 | vol_scalar 1 | combined 1``. The risk-state digest
    is then genuinely invariant to price — the 40-unit bump above leaves it byte-identical, and that
    is correct behaviour rather than a frozen constant. Demonstrating that it *is* a function of its
    input therefore has to happen on a fixture whose risk state actually moves, so this uses the
    crash fixture and shifts the crash to a different session.
    """
    early = _digests(*run(build_crash_series(CRASH_SESSION), window, K1)[:3])
    later = _digests(*run(build_crash_series(PREEMPT_SESSION), window, K1)[:3])
    assert early["risk_state"] != later["risk_state"], (
        "moving the crash — and with it the drawdown, the stop and the realized volatility that "
        "follows it — left the risk-state digest unchanged; it is not a function of the run"
    )
    for name in PRICE_DRIVEN_DIGESTS:
        assert early[name] != later[name]


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


def test_at_f_the_risk_trace_is_one_line_per_session_and_parses(growth, window):
    """The trace is what claim (1) of AT-A reads f(t) out of. If its shape drifted, that whole
    section would be asserting against a misparse rather than against the engine."""
    _, engine, _, _ = run(growth, window, K3)
    lines = engine.risk_state_payload().splitlines()
    assert len(lines) == len(engine._equity)
    for line in lines:
        parts = line.split("|")
        assert len(parts) == 5, f"the risk trace line {line!r} is not the sealed five fields"
        dt.date.fromisoformat(parts[0])
        assert int(parts[1]) in range(RA3_BAND_COUNT)
        assert int(parts[2]) >= 0
        assert Decimal(parts[3]) > ZERO and Decimal(parts[4]) > ZERO


# == AT-G: the window guard still blocks 2021-08-01 onward =========================================


def test_at_g_the_guard_is_reused_and_not_reimplemented():
    """The seal's own words: "The guard is reused, not reimplemented, and the test asserts that the
    module under test is the existing g2_window_guard."

    Identity is asserted three ways, because the strongest of them is the cheapest: the runner's
    ``guard`` name is this very module object; the module's file is one of AT-H's seventeen
    immutable paths; and it re-hashes to the digest the governance seal recorded before Attempt 3
    began. A reimplementation could satisfy the first only by aliasing, and cannot satisfy the third
    at all.
    """
    assert runner.guard is guard, (
        "the Attempt 3 runner is not using the existing window guard module"
    )
    relative = Path(guard.__file__).resolve().relative_to(PROJECT_ROOT).as_posix()
    recorded = _recorded_module_digests()
    assert relative in recorded, (
        f"{relative} is not one of the seventeen immutable prior-attempt modules; the guard would "
        "then be free to change under Attempt 3"
    )
    actual = hashlib.sha256(Path(guard.__file__).read_bytes()).hexdigest()
    assert actual == recorded[relative]


def test_at_g_the_development_bound_is_the_sealed_one():
    assert guard.development_bound() == dt.date(2021, 7, 31)
    assert guard.PARTITION_LOCK_ID == "SE100-GOV-2002"


def test_at_g_the_attempt_3_loading_path_stops_at_the_bound():
    """Exercised through Attempt 3's own loader, not through the guard directly: the claim is about
    the path this attempt actually reads with."""
    series = runner.load_grid_dataset()
    assert series, "the Attempt 3 loader returned no series"
    latest = max(s.sessions[-1] for s in series.values())
    assert latest <= guard.development_bound(), (
        f"the Attempt 3 loading path returned data through {latest}, past the development bound"
    )


def test_at_g_a_series_reaching_past_the_bound_is_refused():
    sessions = sessions_between(dt.date(2021, 7, 26), dt.date(2021, 8, 6))
    assert any(s >= dt.date(2021, 8, 1) for s in sessions), "the fixture does not cross the bound"
    contaminated = {
        "AAA": series_from_rows("AAA", _rows(sessions, [Decimal(100)] * len(sessions)))
    }
    with pytest.raises((WindowViolation, InvariantViolation, ValueError)):
        guard.assert_series_within_bound(contaminated)

    clean_sessions = sessions_between(dt.date(2021, 7, 26), dt.date(2021, 7, 30))
    clean = {"AAA": series_from_rows("AAA", _rows(clean_sessions, [Decimal(100)] * len(clean_sessions)))}
    assert guard.assert_series_within_bound(clean)      # control: the refusal is not unconditional


def test_at_g_the_bound_is_enforced_by_the_series_audit_and_not_by_the_window_constructor():
    """A measured property of the guard that matters for how AT-G may be read.

    ``generation_2_window`` refuses only intersection with the two prohibited holdouts; a research
    window whose end lies past the development bound constructs cleanly. The bound is enforced
    separately, by ``assert_series_within_bound`` on what was actually loaded. That is why the
    loader truncates as it parses and then re-audits, and it is why the test above exercises the
    loading path rather than the window object.

    Asserted rather than described, because a reader who assumed the constructor enforced the bound
    would conclude that a passing window construction was sufficient evidence of partition safety.
    It is not.
    """
    permissive = guard.generation_2_window("probe", "2021-01-04", "2021-08-02")
    assert permissive.end == dt.date(2021, 8, 2) > guard.development_bound()

    sessions = sessions_between(dt.date(2021, 7, 26), dt.date(2021, 8, 2))
    with pytest.raises((WindowViolation, InvariantViolation, ValueError)):
        guard.assert_series_within_bound(
            {"AAA": series_from_rows("AAA", _rows(sessions, [Decimal(100)] * len(sessions)))}
        )


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
    assert set(guard.PROHIBITED_LABELS) == set(labels)


# == AT-H: no Generation 1, Attempt 1 or Attempt 2 module is modified ==============================


def _recorded_module_digests() -> dict[str, str]:
    payload = json.loads(GOVERNANCE_SEAL.read_text(encoding="utf-8"))
    return payload["contamination_measurement"]["prior_attempt_module_digests"]


def _declared_immutable() -> dict:
    return json.loads(CONFIG_SEAL.read_text(encoding="utf-8"))["prior_attempt_modules_immutable"]


def test_at_h_every_immutable_module_rehashes_to_its_recorded_digest():
    recorded = _recorded_module_digests()
    assert len(recorded) == 17, f"the seal records {len(recorded)} module digests, not seventeen"
    for relative, expected in sorted(recorded.items()):
        path = PROJECT_ROOT / relative
        assert path.is_file(), f"{relative} is recorded immutable but is not on disk"
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual == expected, (
            f"{relative} hashes to {actual}; the seal recorded {expected}. A Generation 1, Attempt "
            "1 or Attempt 2 module has been modified, which is a governance failure and not a value "
            "to update."
        )


def test_at_h_the_declared_immutable_list_and_the_recorded_digests_agree():
    """Two files declare the same seventeen modules — the config seal by name, the governance seal by
    digest. A module dropped from one and not the other would leave a hole neither notices."""
    declared = _declared_immutable()
    attempt_1 = list(declared["attempt_1_modules"])
    attempt_2 = list(declared["attempt_2_modules"])
    assert len(attempt_1) == 9 and len(attempt_2) == 8
    assert declared["count"] == 17 == len(attempt_1) + len(attempt_2)
    assert not set(attempt_1) & set(attempt_2), "a module is listed under both attempts"
    assert sorted(attempt_1 + attempt_2) == sorted(_recorded_module_digests())


def test_at_h_attempt_3_wrote_none_of_its_code_into_a_prior_attempt_module():
    """The naming convention is the protection, so assert it rather than trusting it: no immutable
    path may be one of Attempt 3's own modules."""
    attempt_3 = {
        "src/stockedge100/strategies/g2_rotation_ra3.py",
        "src/stockedge100/strategies/g2_gate_ra3.py",
        "src/stockedge100/strategies/g2_runner_ra3.py",
        "src/stockedge100/strategies/g2_selection_v2.py",
        "src/stockedge100/backtest/g2_engine_ra3.py",
    }
    assert not attempt_3 & set(_recorded_module_digests())
    for relative in attempt_3:
        assert (PROJECT_ROOT / relative).is_file(), f"{relative} is missing"


def test_at_h_the_runners_own_verification_agrees_with_this_one():
    """The runner verifies the same thing at run time. Asserting only through it would be asking the
    code whether the code works; asserting both, and that they agree, is the check."""
    report = runner.verify_prior_attempt_modules()
    assert report["requirement"] == "AT-H"
    assert report["module_count"] == 17
    assert report["attempt_1_module_count"] == 9
    assert report["attempt_2_module_count"] == 8
    assert report["modules_that_moved"] == []
    assert report["modules_verified"] == _recorded_module_digests()


def _patch_seals(monkeypatch, *, governance=None, config=None):
    """Redirect the runner's two seal readers at in-memory copies. Nothing on disk is touched —
    modifying a sealed artifact to test the test would be the violation the test exists to catch."""
    gov = copy.deepcopy(json.loads(GOVERNANCE_SEAL.read_text(encoding="utf-8")))
    cfg = copy.deepcopy(json.loads(CONFIG_SEAL.read_text(encoding="utf-8")))
    if governance is not None:
        governance(gov)
    if config is not None:
        config(cfg["prior_attempt_modules_immutable"])
    monkeypatch.setattr(runner, "_governance_protocol", lambda: gov)
    monkeypatch.setattr(runner, "load_protocol", lambda: cfg)


def test_at_h_the_seal_patching_harness_is_transparent(monkeypatch):
    """Control for the four injections below. If routing the runner through in-memory copies changed
    the outcome on its own, every raise underneath would be attributable to the harness."""
    _patch_seals(monkeypatch)
    report = runner.verify_prior_attempt_modules()
    assert report["module_count"] == 17
    assert report["modules_that_moved"] == []


def test_at_h_injected_defect_a_changed_byte_is_caught():
    """The digest check must fail on a one-byte change. Verified on a copy in memory — nothing on
    disk is touched, because touching an immutable module to test the test would be the violation."""
    recorded = _recorded_module_digests()
    relative, expected = sorted(recorded.items())[0]
    payload = (PROJECT_ROOT / relative).read_bytes()
    assert hashlib.sha256(payload).hexdigest() == expected
    assert hashlib.sha256(payload + b"\n").hexdigest() != expected


def test_at_h_injected_defect_an_altered_recorded_digest_is_refused(monkeypatch):
    """A digest that no longer matches the file must raise, and must name the file. Altering the
    *record* rather than the file is the injection that matters: it is what a well-meaning repair
    would look like."""
    def tamper(gov):
        node = gov["contamination_measurement"]["prior_attempt_module_digests"]
        node[sorted(node)[0]] = "0" * 64

    _patch_seals(monkeypatch, governance=tamper)
    with pytest.raises(ConfigViolation) as excinfo:
        runner.verify_prior_attempt_modules()
    assert "AT-H" in str(excinfo.value)
    assert "digest_changed" in str(excinfo.value)


def test_at_h_injected_defect_a_module_listed_under_both_attempts_is_refused(monkeypatch):
    """A duplicate would make the union smaller than the declared count while the concatenation
    still looked complete — the failure mode a bare ``len()`` check cannot see."""
    def duplicate(declared):
        declared["attempt_2_modules"] = list(declared["attempt_2_modules"])
        declared["attempt_1_modules"] = list(declared["attempt_1_modules"])
        declared["attempt_2_modules"][0] = declared["attempt_1_modules"][0]

    _patch_seals(monkeypatch, config=duplicate)
    with pytest.raises(ConfigViolation) as excinfo:
        runner.verify_prior_attempt_modules()
    assert "share" in str(excinfo.value)


def test_at_h_injected_defect_a_miscounted_declaration_is_refused(monkeypatch):
    _patch_seals(monkeypatch, config=lambda d: d.__setitem__("count", int(d["count"]) + 1))
    with pytest.raises(ConfigViolation) as excinfo:
        runner.verify_prior_attempt_modules()
    assert "18" in str(excinfo.value) and "17" in str(excinfo.value)


def test_at_h_injected_defect_a_module_missing_from_the_governance_seal_is_refused(monkeypatch):
    """The two seals must cover the same set. A module named by the config seal but carrying no
    recorded digest is unprotected, and silence there would be the worst possible outcome."""
    def drop(gov):
        node = gov["contamination_measurement"]["prior_attempt_module_digests"]
        node.pop(sorted(node)[0])

    _patch_seals(monkeypatch, governance=drop)
    with pytest.raises(ConfigViolation) as excinfo:
        runner.verify_prior_attempt_modules()
    assert "does not record" in str(excinfo.value)


# == AT-L: the band table is the sealed one and engages nowhere below 8% ===========================


def test_at_l_the_architecture_has_exactly_three_bands(architecture):
    assert len(architecture.bands) == RA3_BAND_COUNT == 3
    assert [band.band for band in architecture.bands] == [0, 1, 2]


def test_at_l_no_band_boundary_lies_below_the_shallowest_engagement(architecture):
    """The sealed claim in its own words: "contains no band boundary below 0.08". Zero is the
    exception the seal itself names — the full-sizing band has to start somewhere."""
    assert RA3_SHALLOWEST_ENGAGEMENT == SHALLOWEST_ENGAGEMENT == Decimal("0.08")
    boundaries = []
    for band in architecture.bands:
        boundaries.append(band.dd_from)
        if band.dd_to_exclusive is not None:
            boundaries.append(band.dd_to_exclusive)
    assert boundaries, "the band table declares no boundaries at all"
    for value in boundaries:
        assert value == ZERO or value >= SHALLOWEST_ENGAGEMENT, (
            f"the RA3 ladder has a boundary at {value}, below the 8% engagement this attempt's "
            "single change consists of"
        )


def test_at_l_the_scalars_are_strictly_decreasing_within_zero_to_one(architecture):
    scalars = [band.scalar for band in architecture.bands]
    for value in scalars:
        assert ZERO < value <= ONE, f"the scalar {value} is outside (0, 1]"
    assert scalars == sorted(scalars, reverse=True) and len(set(scalars)) == len(scalars), (
        f"the scalars {scalars} are not strictly decreasing; a ladder that does not de-risk "
        "monotonically is not a ladder"
    )


def test_at_l_the_first_band_starts_at_zero_at_full_sizing_and_the_last_is_open_ended(architecture):
    first, last = architecture.bands[0], architecture.bands[-1]
    assert first.dd_from == ZERO
    assert first.scalar == Decimal("1.00")
    assert first.dd_to_exclusive == SHALLOWEST_ENGAGEMENT
    assert last.dd_to_exclusive is None, (
        "the deepest band is bounded above; a drawdown past its top would fall through the table"
    )


def test_at_l_the_induced_absolute_ceilings_are_the_declared_ones(architecture):
    """The sealed figures, quoted: "the absolute aggregate ceilings it induces equal 0.500000000 /
    0.250000000 / 0.125000000". Recomputed from ceiling times scalar at the sealed precision rather
    than read from a field, because the induced product is the quantity that binds a book."""
    induced = [
        f"{quantize_scalar(architecture.exposure_ceiling * band.scalar):f}"
        for band in architecture.bands
    ]
    assert induced == ["0.500000000", "0.250000000", "0.125000000"]


def test_at_l_the_ladder_is_generation_1_s_ladder_restored(architecture):
    """RA3's stated provenance: the ladder reverts to Generation 1's original spacing. The module
    checks this against the Generation 1 protocol on disk; the test asserts the check's verdict and
    the rung table it compared, so a check that quietly stopped comparing would be visible."""
    provenance = check_generation_1_provenance(architecture)
    assert provenance["ladders_are_identical"] is True
    assert provenance["generation_1_states_it_twice_and_they_agree"] is True
    assert provenance["generation_1_protocol"] == "stage3_attempt2_strategy_protocol.json"
    assert provenance["generation_1_ladder_from_ra1_5_prose"] == [
        ["0", "0.08", "0.5"], ["0.08", "0.1", "0.25"], ["0.1", None, "0.125"]
    ]
    assert provenance["ra3_bands_as_absolute_caps"] == (
        provenance["generation_1_ladder_from_ra1_5_prose"]
    )
    assert provenance["exposure_ceiling_used_to_convert"] == "0.5"


def test_at_l_the_only_difference_from_ra2_is_the_deleted_tier(architecture):
    difference = check_single_difference_from_ra2(architecture)
    assert difference["attempt_2_protocol"] == "g2_rotation_ra1_protocol.json"
    assert len(difference["ra2_bands"]) == 4 and len(difference["ra3_bands"]) == 3
    assert difference["deleted_tier"] == ["0.05", "0.08", "0.75"]
    assert tuple(Decimal(v) for v in difference["deleted_tier"]) == DELETED_RA2_TIER
    assert difference["bands_added_by_ra3"] == [["0.00", "0.08", "1.00"]]
    assert difference["bands_removed_from_ra2"] == [
        ["0.00", "0.05", "1.00"], ["0.05", "0.08", "0.75"]
    ]
    assert difference["bands_at_or_beyond_the_deleted_tier_unchanged"] is True


def test_at_l_injected_defect_a_four_band_ladder_is_refused(architecture):
    """The injection that matters most: reinstating the tier RA3 deleted. Four bands is RA2 under a
    new name, and it must not load as RA3."""
    document = _protocol_copy()
    bands = _ladder_bands(document)
    bands[0]["dd_to_exclusive"] = "0.05"
    bands.insert(1, {"band": 1, "dd_from": "0.05", "dd_to_exclusive": "0.08", "scalar": "0.75"})
    for index, band in enumerate(bands):
        band["band"] = index

    with pytest.raises(ConfigViolation) as excinfo:
        load_risk_architecture_ra3(document)
    assert "4 bands" in str(excinfo.value)


def test_at_l_injected_defect_a_shallower_engagement_is_refused():
    """The whole of this attempt's change is that no step engages below 8%. A band ending at 6% is a
    different attempt, and the loader must say so rather than run it."""
    document = _protocol_copy()
    bands = _ladder_bands(document)
    bands[0]["dd_to_exclusive"] = "0.06"
    bands[1]["dd_from"] = "0.06"

    with pytest.raises(ConfigViolation) as excinfo:
        load_risk_architecture_ra3(document)
    assert "0.06" in str(excinfo.value)


def test_at_l_injected_defect_a_lost_rung_is_refused():
    """The mirror of the four-band injection: two bands has dropped a rung Generation 1 sealed. The
    band count is pinned in both directions, not merely capped."""
    document = _protocol_copy()
    bands = _ladder_bands(document)
    del bands[1]
    bands[0]["dd_to_exclusive"] = "0.10"
    bands[1]["band"] = 1

    with pytest.raises(ConfigViolation) as excinfo:
        load_risk_architecture_ra3(document)
    assert "2 bands" in str(excinfo.value)


def test_at_l_injected_defect_the_identity_and_freeze_flags_are_refused_when_flipped():
    """Three separate guards, each of which would let a differently-provenanced architecture through
    if it were missing: the id, the pre-freeze assertion, and the not-a-grid-axis assertion."""
    relabelled = _protocol_copy()
    relabelled["risk_architecture"]["id"] = "RA2"
    with pytest.raises(ConfigViolation) as excinfo:
        load_risk_architecture_ra3(relabelled)
    assert "not RA3" in str(excinfo.value)

    unfrozen = _protocol_copy()
    unfrozen["risk_architecture"]["frozen_before_any_variant_is_run"] = False
    with pytest.raises(ConfigViolation) as excinfo:
        load_risk_architecture_ra3(unfrozen)
    assert "frozen" in str(excinfo.value)

    gridded = _protocol_copy()
    gridded["risk_architecture"]["not_part_of_the_grid"] = False
    with pytest.raises(ConfigViolation) as excinfo:
        load_risk_architecture_ra3(gridded)
    assert "grid" in str(excinfo.value)


def test_at_l_the_loader_does_not_bound_the_exposure_ceiling_and_at_a_is_what_does(architecture):
    """Stated because it was measured, not because it is comfortable.

    The first draft of this test asserted the loader *ignored* a widened ceiling, on the strength of
    a preflight injection that set ``ceiling_fraction_of_equity``. That key exists nowhere in the
    sealed document, so the injection mutated nothing and the "it loads unchanged" reading was
    vacuous. The loader reads ``components["RA3-1"]["value"]``, and a document widened there loads
    *changed*: 0.60 in, 0.60 out. What it never does is bound the magnitude — 1.00 loads too.

    So the ceiling is carried, not validated. What actually holds it at 0.50 is AT-A — the replayed
    post-fill exposure assertions, written against a hand-typed 0.50 rather than against whatever
    the document said, and whose own injection (a widening to 0.95) is caught there.

    The loader is not inert at ``RA3-1`` either, and the honest form of this test says what it does
    pin: the clamp-name tuple. Dropping one name raises, which is the injection this test carries.
    """
    widened = _protocol_copy()
    widened["risk_architecture"]["components"]["RA3-1"]["value"] = "0.60"
    assert load_risk_architecture_ra3(widened).exposure_ceiling == Decimal("0.60"), (
        "the loader no longer carries the ceiling from RA3-1.value; the docstring above and the "
        "package's account of what pins the ceiling must be rewritten, not this assertion"
    )

    unbounded = _protocol_copy()
    unbounded["risk_architecture"]["components"]["RA3-1"]["value"] = "1.00"
    assert load_risk_architecture_ra3(unbounded).exposure_ceiling == ONE, (
        "the loader has grown a magnitude bound on the exposure ceiling; that is a strengthening, "
        "but AT-A's independent 0.50 is what this suite relies on and the disclosure is now stale"
    )

    stripped = _protocol_copy()
    clamp = stripped["risk_architecture"]["components"]["RA3-1"]["enforcement"]["part_a_entry_clamp"]
    clamp["clamp_names"] = list(clamp["clamp_names"])[:-1]
    with pytest.raises(ConfigViolation) as caught:
        load_risk_architecture_ra3(stripped)
    assert "clamp names" in str(caught.value)

    assert architecture.exposure_ceiling == NOMINAL_CEILING
    assert _protocol_copy()["risk_architecture"]["components"]["RA3-1"]["value"] == "0.50"


def _protocol_copy() -> dict:
    return json.loads(eng3.PROTOCOL_PATH.read_text(encoding="utf-8"))


def _ladder_bands(document: dict) -> list:
    """Locate the ladder component by the field that identifies it rather than by its key.

    The ladder is ``RA3-4``, but hard-coding that was got wrong once already during preflight; the
    component carrying ``bands`` is the definition, and a seal that renumbered its components should
    fail on a band assertion rather than on a ``KeyError``.
    """
    components = document["risk_architecture"]["components"]
    keys = [name for name, node in components.items() if "bands" in node]
    assert keys == ["RA3-4"], f"the ladder is not the single component RA3-4: {keys}"
    return components[keys[0]]["bands"]


def test_at_l_the_protocol_the_loader_reads_is_attempt_3s(tmp_path, monkeypatch):
    """Identity is checked from the file, not from the argument: passing a document that declares
    ``attempt: 2`` through the ``protocol=`` parameter loads, because that parameter exists for
    in-memory injection. Reading a file that declares it must not."""
    from stockedge100.backtest.g2_engine_ra3 import load_ra3_protocol

    document = _protocol_copy()
    assert document["attempt"] == 3 and document["artifact_id"] == eng3.PROTOCOL_ID

    document["attempt"] = 2
    path = tmp_path / "g2_rotation_ra3_protocol.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setattr(eng3, "PROTOCOL_PATH", path)
    with pytest.raises(ConfigViolation) as excinfo:
        load_ra3_protocol()
    assert "attempt=2" in str(excinfo.value)

    monkeypatch.setattr(eng3, "PROTOCOL_PATH", tmp_path / "absent.json")
    with pytest.raises(ConfigViolation) as excinfo:
        load_ra3_protocol()
    assert "missing" in str(excinfo.value)


# == AT-M: the RA3 engine re-derives exactly the attributes it must ================================


RISK_ATTRIBUTE_LITERAL = 'RISK_DERIVED_ATTRIBUTES = frozenset({"risk", "sessions_in_band"})'
ENGINE_SOURCE_PATH = Path(eng3.__file__)


def _exec_as_module(source: str, name: str) -> dict:
    """Execute a candidate source as a throwaway module so an import-time guard can be observed.

    The guard under test runs at import. Reimporting the real module would either hit the import
    cache or replace the module every other test in this file holds a reference to, so the mutated
    source is executed into a private namespace that is discarded either way.
    """
    module = types.ModuleType(name)
    module.__file__ = str(ENGINE_SOURCE_PATH)
    sys.modules[name] = module
    try:
        exec(compile(source, str(ENGINE_SOURCE_PATH), "exec"), module.__dict__)
        return module.__dict__
    finally:
        sys.modules.pop(name, None)


def test_at_m_the_declared_set_is_what_attempt_2s_init_actually_derives():
    """The AST measurement, in the direction the seal specifies: parse Attempt 2's ``__init__`` for
    the attributes it assigns from ``self.risk``, and require the declared constant to equal it."""
    measured = attributes_derived_from_risk(RotationEngineRA1)
    assert measured == RISK_DERIVED_ATTRIBUTES == frozenset({"risk", "sessions_in_band"})
    assert attributes_derived_from_risk() == measured, (
        "the default argument no longer measures Attempt 2's engine"
    )


def test_at_m_the_ra3_subclass_reassigns_that_set_and_names_what_it_adds():
    """The seal says the subclass "reassigns precisely that set". Measured, RA3's ``__init__``
    assigns four attributes from the architecture: the two required, plus two provenance records.

    Rather than read "precisely" as satisfied by a superset without comment, the extras are named
    and their nature asserted — both are dicts produced by the two provenance checks, so they are
    records written for the report rather than sizing parameters. The guard the module actually
    enforces (``G2A3-CONFLICT-31``) compares the *declared* set against Attempt 2's measured set,
    which is the comparison that can go wrong silently; this test pins the subclass side.
    """
    subclass = attributes_derived_from_risk(RotationEngineRA3)
    assert subclass >= RISK_DERIVED_ATTRIBUTES, (
        f"RA3 fails to re-derive {sorted(RISK_DERIVED_ATTRIBUTES - subclass)} after super().__init__; "
        "a variant would then run with an RA2-shaped attribute under an RA3 ladder"
    )
    extras = subclass - RISK_DERIVED_ATTRIBUTES
    assert extras == {"generation_1_provenance", "single_difference_from_ra2"}, (
        f"RA3's __init__ now derives {sorted(extras)} from the risk architecture beyond the two the "
        "seal requires; anything new here is a sizing input until shown otherwise"
    )


def test_at_m_the_extras_are_provenance_records_rather_than_sizing_inputs(growth, window):
    engine, _, _ = make_engine(growth, window, K1)
    assert isinstance(engine.generation_1_provenance, dict)
    assert isinstance(engine.single_difference_from_ra2, dict)
    assert engine.generation_1_provenance["ladders_are_identical"] is True
    assert engine.single_difference_from_ra2["deleted_tier"] == ["0.05", "0.08", "0.75"]


def test_at_m_the_clean_source_imports_and_the_literal_occurs_once():
    """Control for the two injections. The replacement below is textual, so a second occurrence of
    the literal would mutate something other than the declaration and the injection would be
    testing an unknown edit."""
    source = ENGINE_SOURCE_PATH.read_text(encoding="utf-8")
    assert source.count(RISK_ATTRIBUTE_LITERAL) == 1, (
        "the declared-attributes literal no longer occurs exactly once in the engine source"
    )
    namespace = _exec_as_module(source, "_ra3_engine_clean_probe")
    assert namespace["RISK_DERIVED_ATTRIBUTES"] == RISK_DERIVED_ATTRIBUTES


def test_at_m_the_guard_raises_rather_than_asserting():
    """``python -O`` strips ``assert``. A structural guard written as an assertion would vanish in
    exactly the configuration where nobody was watching."""
    source = ENGINE_SOURCE_PATH.read_text(encoding="utf-8")
    marker = "if _MEASURED != RISK_DERIVED_ATTRIBUTES:"
    assert marker in source, "the AT-M guard is no longer where this test expects it"
    tail = source[source.index(marker) : source.index(marker) + 400]
    assert "raise ConfigViolation(" in tail
    assert "G2A3-CONFLICT-31" in tail


def test_at_m_injected_defect_a_narrowed_declaration_fires_the_import_time_guard():
    source = ENGINE_SOURCE_PATH.read_text(encoding="utf-8")
    narrowed = source.replace(
        RISK_ATTRIBUTE_LITERAL, 'RISK_DERIVED_ATTRIBUTES = frozenset({"risk"})'
    )
    assert narrowed != source
    with pytest.raises(ConfigViolation) as excinfo:
        _exec_as_module(narrowed, "_ra3_engine_narrowed_probe")
    assert "sessions_in_band" in str(excinfo.value)
    assert "G2A3-CONFLICT-31" in str(excinfo.value)


def test_at_m_injected_defect_a_widened_declaration_fires_it_too():
    """The injection in the other direction, which the seal does not ask for and which is the more
    likely mistake: declaring an attribute RA3 re-derives that Attempt 2 never derived from risk at
    all would make the AST measurement and the declaration disagree in the silent direction."""
    source = ENGINE_SOURCE_PATH.read_text(encoding="utf-8")
    widened = source.replace(
        RISK_ATTRIBUTE_LITERAL,
        'RISK_DERIVED_ATTRIBUTES = frozenset({"risk", "sessions_in_band", "budget_weight"})',
    )
    assert widened != source
    with pytest.raises(ConfigViolation) as excinfo:
        _exec_as_module(widened, "_ra3_engine_widened_probe")
    assert "budget_weight" in str(excinfo.value)


# == the gate adapter's own guards =================================================================


def test_gate_ra3_the_prose_alias_table_is_load_bearing_in_both_directions():
    """``g2_gate_ra3`` renames two prose pointers from Attempt 2's criteria to Attempt 3's, and
    checks that the renames are exactly the declared ones. A table that could be widened or narrowed
    without complaint would let a condition read a pointer nobody declared, or silently stop
    following one that still exists. G2A3-CONFLICT-40.
    """
    criteria = gate.load_criteria_ra3()
    assert gate._check_prose_renames_are_as_declared(criteria) is None

    widened = gate.PROSE_ALIASES + (("S3-C1", (), "attempt_2_note", "attempt_3_note"),)
    with pytest.raises(ConfigViolation):
        _with_aliases(widened, criteria)

    narrowed = gate.PROSE_ALIASES[:1]
    assert len(narrowed) < len(gate.PROSE_ALIASES)
    with pytest.raises(ConfigViolation):
        _with_aliases(narrowed, criteria)


def _with_aliases(table, criteria):
    saved = gate.PROSE_ALIASES
    gate.PROSE_ALIASES = table
    try:
        return gate._check_prose_renames_are_as_declared(criteria)
    finally:
        gate.PROSE_ALIASES = saved


def test_gate_ra3_the_pointer_sets_it_compares_are_non_empty():
    """Both sides of the rename check are computed sets. Either one silently emptying would make the
    comparison vacuously true, so the counts are asserted rather than the verdict alone."""
    read = gate._keys_the_frozen_evaluators_read()
    dropped = gate._pointers_dropped_since_attempt_2()
    assert len(read) == 45, f"the frozen evaluators now read {len(read)} pointers, not 45"
    assert len(dropped) == 10, f"{len(dropped)} pointers are recorded dropped, not 10"
    assert gate.CONFLICT_PROSE_RENAME == "G2A3-CONFLICT-40"
    assert gate.CONFLICT_NEIGHBOUR_COUNT == "G2A3-CONFLICT-27"
