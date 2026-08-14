"""Stage 3 Attempt 2 — integration tests on synthetic fixtures.

These tests drive the real `BacktestEngine`, the real planner and the real Attempt 2 candidates
end to end, so they cover the wiring that the unit module cannot: window enforcement at engine
construction, the warm-up rule against the real exchange calendar, staleness accounting, the
cash residual, the section 5.1 research shutdown, and determinism of the two recorded digests.

Every price series is built in memory by `series_from_rows`. **No test here loads a normalised
CSV**, so nothing here can expose the real performance of a sealed candidate — the sealed
lookbacks are replaced by a deliberately tiny `sma_long` on a synthetic ramp whose only purpose
is to make the candidate trade at a known session. `load_dataset` is monkeypatched where the
loader path itself is under test, and `attempt2_harness.run_all` is never called: the declared
runs happen exactly once, in the evaluation step, not in the suite.

Fixture arithmetic was computed against the real implementation before it was written down here.
Nothing writes outside `tmp_path`; `tests/conftest.py` is frozen and supplies nothing this module
needs.
"""

from __future__ import annotations

import ast
import copy
import dataclasses
import datetime as dt
import inspect
import textwrap
from decimal import Decimal

import pytest

from stockedge100.backtest.config import load_stage2_config
from stockedge100.backtest.costs import BASE, CostModel
from stockedge100.backtest.dataset import Bar, series_from_rows
from stockedge100.backtest.engine import (
    BacktestEngine,
    BacktestResult,
    EquityPoint,
    OrderRequest,
)
from stockedge100.backtest.errors import (
    ConfigViolation,
    DataIntegrityHalt,
    LookAheadError,
    WindowViolation,
)
from stockedge100.backtest.market import MarketView
from stockedge100.backtest.orders import BUY, SELL
from stockedge100.backtest import dataset as dataset_module
from stockedge100.data.calendar import sessions_between
from stockedge100.strategies import attempt2_candidates, attempt2_harness, attempt2_runner, gate
from stockedge100.strategies.attempt2_config import load_attempt2_config
from stockedge100.strategies.runner import PRIMARY, CandidatePlan, VariantSpec, run_start_for
from stockedge100.backtest.window import (
    HOLDOUT,
    VALIDATION,
    development_window,
    window_named,
)

# -- sealed inputs -------------------------------------------------------------------------------

CONFIG = load_attempt2_config()
COSTS = CostModel(load_stage2_config().cost_model, BASE)
WINDOW = development_window()

#: The C1 primary parameters, used only as the source of the sealed RA1 block. The scaffold below
#: overrides the lookbacks so that no test measures a sealed parameterisation on real prices.
SEALED_RA1 = next(
    experiment["primary_parameters"]
    for experiment in CONFIG.experiments
    if experiment["experiment_id"] == attempt2_candidates.C1
)

#: Deliberately far below any sealed lookback. A three-session moving average on a synthetic ramp
#: trades on a session this module chooses; the sealed 200/50/20-session lookbacks never appear.
SCAFFOLD_SMA = 3

#: Real XNYS sessions, so the calendar under test is the frozen one. The span is comfortably
#: inside the development window and comfortably short of the validation boundary.
SESSIONS = sessions_between(dt.date(2000, 1, 3), dt.date(2000, 6, 30))
COUNT = 45
RUN_START = SESSIONS[20]
RUN_END = SESSIONS[COUNT - 1]


# -- synthetic market helpers --------------------------------------------------------------------


def prices(
    symbol: str,
    closes: list[str],
    *,
    adj: list[str] | None = None,
    opens: list[str] | None = None,
    skip: tuple[int, ...] = (),
    sessions: list[dt.date] | None = None,
):
    """A bar per session from in-memory rows.

    ``split_ratio`` is written explicitly as ``"1"``: `series_from_rows` defaults it to ``"0"``,
    which `Bar.has_split` reads as a split and which would engage the engine's corporate-action
    continuity check on a fixture that has no corporate action.
    """
    days = SESSIONS if sessions is None else sessions
    rows = []
    for index, close in enumerate(closes):
        if index in skip:
            continue
        open_ = close if opens is None else opens[index]
        high = max(Decimal(open_), Decimal(close))
        low = min(Decimal(open_), Decimal(close))
        rows.append(
            {
                "session": days[index].isoformat(),
                "open": str(open_),
                "high": f"{high:f}",
                "low": f"{low:f}",
                "close": str(close),
                "adj_close": str(close if adj is None else adj[index]),
                "volume": "1000",
                "dividend": "0",
                "split_ratio": "1",
            }
        )
    return series_from_rows(symbol, rows)


def ramp(count: int, first: int = 80) -> list[str]:
    return [str(first + index) for index in range(count)]


def alternating(count: int, low: str = "100", high: str = "101") -> list[str]:
    return [high if index % 2 else low for index in range(count)]


def scaffold(*, universe=("SPY", "SHY"), last: int = COUNT - 1, **overrides):
    """A C3-shaped variant on synthetic prices with a three-session trend filter.

    The RA1 block is the sealed one, verbatim: the point of an integration fixture is to exercise
    the real risk architecture. Only the lookback and the symbol roles are scaffolding.
    """
    parameters = dict(SEALED_RA1)
    parameters.pop("sma_short", None)
    parameters.update(
        {"sma_long": SCAFFOLD_SMA, "risk_symbol": "SPY", "defensive_symbol": "SHY"}
    )
    parameters.update(overrides)
    symbols = tuple(sorted({symbol for symbol in universe if symbol}))
    spec = VariantSpec(
        experiment_id=attempt2_candidates.C3,
        variant_id=f"{attempt2_candidates.C3}#SCAFFOLD",
        role=PRIMARY,
        index=0,
        universe=universe,
        parameters=parameters,
        symbols=symbols,
    )
    plan = CandidatePlan(
        experiment_id=attempt2_candidates.C3,
        family="DEFENSIVE_REGIME",
        declared_universe=universe,
        warmup_sessions=21,
        effective_warmup=21,
        run_start=RUN_START,
        run_end=SESSIONS[last],
        binding_symbol="SPY",
        variants=(spec,),
        all_symbols=symbols,
    )
    return spec, plan


def market(skip: tuple[int, ...] = ()):
    """A rising risk asset and a flat defensive asset.

    ``close`` ramps so the three-session trend filter is satisfied from the first decision;
    ``adj_close`` alternates so the return series the RA1 volatility estimate consumes is not
    degenerate.
    """
    return {
        "SPY": prices("SPY", ramp(COUNT), adj=alternating(COUNT), skip=skip),
        "SHY": prices("SHY", ["50"] * COUNT, adj=["50"] * COUNT),
    }


def run_scaffold(series=None, *, spec=None, plan=None, **kwargs):
    built_spec, built_plan = scaffold()
    return attempt2_runner.run_variant(
        spec or built_spec,
        plan or built_plan,
        market() if series is None else series,
        COSTS,
        WINDOW,
        CONFIG.rsi_warmup_changes,
        **kwargs,
    )


class Greedy:
    """Requests a full-size entry on every session it is flat.

    Re-requesting matters for the shutdown test: a probe that orders once has no blocked entry to
    be rejected, so the ``RESEARCH_SHUTDOWN`` rejection would never appear.
    """

    def __init__(self, symbol: str, budget: Decimal) -> None:
        self.name = "TEST-GREEDY"
        self.symbol = symbol
        self.budget = budget
        self.decisions: list[dt.date] = []

    def decide(self, view, context):
        self.decisions.append(context.session)
        if context.open_symbols:
            return []
        return [OrderRequest(symbol=self.symbol, side=BUY, budget=self.budget, tag="TEST")]


def engine_for(strategy, series, **kwargs):
    kwargs.setdefault("start", RUN_START)
    kwargs.setdefault("end", RUN_END)
    return BacktestEngine(series, COSTS, WINDOW, strategy, **kwargs)


def synthetic_result(equities: list[str]) -> BacktestResult:
    """A hand-built result, for asserting a gate predicate at a boundary the engine cannot reach."""
    curve = [
        EquityPoint(
            session=SESSIONS[index],
            cash=Decimal(equity),
            equity=Decimal(equity),
            stale_mark=False,
            position_count=0,
        )
        for index, equity in enumerate(equities)
    ]
    return BacktestResult(
        label="SYNTHETIC",
        scenario="baseline",
        symbols=("SPY",),
        start=curve[0].session,
        end=curve[-1].session,
        equity_curve=curve,
        fills=[],
        rejections=[],
        trades=[],
        dividend_events=[],
        stale_marks=0,
        shutdown_session=None,
        starting_equity=Decimal(equities[0]),
        final_cash=Decimal(equities[-1]),
        final_equity=Decimal(equities[-1]),
        open_positions={},
        cost_model=COSTS.to_json(),
    )


# -- clean controls ------------------------------------------------------------------------------
#
# Per `.claude/rules/tests.md`: a battery that has only seen defects is as untested as one that has
# only seen clean data. A failure below these three is attributable to the injected defect rather
# than to the harness.


def test_control_the_scaffold_runs_the_whole_planned_window() -> None:
    """The scaffold completes, trades, and reaches the planned end with no rejection."""
    run = run_scaffold()
    result = run.result
    assert (result.start, result.end) == (RUN_START, RUN_END)
    assert len(result.equity_curve) == len(sessions_between(RUN_START, RUN_END)) == 25
    assert result.rejections == []
    assert result.stale_marks == 0
    assert result.shutdown_session is None
    assert len(result.fills) == 2 and len(result.trades) == 1
    assert result.fills[0].fill.symbol == "SPY" and result.fills[0].fill.side == BUY
    assert result.fills[0].session == SESSIONS[21]


def test_control_a_clean_series_never_trips_the_research_shutdown() -> None:
    """A monotone ramp produces no drawdown of consequence, so section 5.1 stays dormant."""
    result = engine_for(Greedy("SPY", Decimal("50")), {"SPY": prices("SPY", ramp(COUNT))}).run()
    assert result.shutdown_session is None
    verdict = gate.condition_2(result, CONFIG.criteria)
    assert verdict.verdict == "MET"
    assert verdict.evidence["research_shutdown_session"] is None


def test_control_the_development_window_is_the_one_the_engine_accepts() -> None:
    """Both scaffold bounds are inside the sealed development window, by the window's own check."""
    assert (WINDOW.name, WINDOW.start, WINDOW.end) == (
        "development",
        dt.date(1993, 1, 29),
        dt.date(2021, 7, 31),
    )
    assert WINDOW.check(RUN_START) == RUN_START
    assert WINDOW.check(RUN_END) == RUN_END
    assert CONFIG.preregistration["authorized_windows"] == ["development"]


# -- partition enforcement -----------------------------------------------------------------------


def test_validation_bounds_are_refused() -> None:
    """A run bound inside the LOCKED validation window is refused at engine construction.

    The refusal is structural and happens before any session is iterated: `BacktestEngine`
    `window.check`s both bounds in `__init__`. The sealed pre-registration records the validation
    window as LOCKED, and this session's only authorized window is `development`.
    """
    assert CONFIG.preregistration["validation_window_state"] == "LOCKED"
    validation = window_named(VALIDATION)
    series = {"SPY": prices("SPY", ramp(COUNT))}

    for bound in ({"start": validation.start}, {"end": validation.end}):
        with pytest.raises(WindowViolation) as raised:
            engine_for(Greedy("SPY", Decimal("50")), series, **bound)
        assert "outside the authorized development window" in str(raised.value)

    # And the window object itself refuses an observation-level read of either boundary.
    for session in (validation.start, validation.end):
        with pytest.raises(WindowViolation):
            WINDOW.check(session)
        assert not WINDOW.contains(session)


def test_holdout_bounds_are_refused() -> None:
    """A run bound inside the SEALED holdout window is refused the same way.

    Nothing in this test reads a holdout observation: it reads the holdout *boundaries*, which
    the sealed protocol classes as previously permitted integrity metadata, and asserts that the
    engine will not accept either of them as a run bound.
    """
    assert CONFIG.preregistration["holdout_window_state"] == "SEALED"
    holdout = window_named(HOLDOUT)
    series = {"SPY": prices("SPY", ramp(COUNT))}

    for bound in ({"start": holdout.start}, {"end": holdout.end}):
        with pytest.raises(WindowViolation) as raised:
            engine_for(Greedy("SPY", Decimal("50")), series, **bound)
        assert "the holdout is SEALED" in str(raised.value)

    for session in (holdout.start, holdout.end):
        with pytest.raises(WindowViolation):
            WINDOW.check(session)
        assert not WINDOW.contains(session)

    prohibited = " ".join(CONFIG.protocol["partitions"]["prohibited"])
    assert "holdout window - SEALED, no observation read" in prohibited


def test_no_excluded_symbol_is_ever_loaded() -> None:
    """The loader asks for the required symbols only, and refuses an excluded one outright.

    AAPL has a normalised price file because Stage 1 measured the split convention against it, and
    the sealed protocol excludes it from every candidate. Two assertions: the symbol list the
    loader is handed is exactly the sealed requirement, and a universe that names AAPL raises
    before any file is opened.
    """
    assert "AAPL" in CONFIG.excluded_symbols
    assert "Constitution section 3" in CONFIG.excluded_symbols["AAPL"]

    required = attempt2_runner.required_symbols(CONFIG)
    assert required == ("SHY", "SPY")
    assert "AAPL" not in required

    asked: list[tuple[str, ...]] = []

    def spy_on_load(symbols):
        asked.append(tuple(symbols))
        return {symbol: prices(symbol, ramp(COUNT)) for symbol in symbols}

    original = attempt2_runner.load_dataset
    attempt2_runner.load_dataset = spy_on_load
    try:
        loaded = attempt2_runner.load_required_dataset(CONFIG)
    finally:
        attempt2_runner.load_dataset = original
    assert asked == [required]
    assert set(loaded) == set(required)

    class ConfigShim:
        """Just enough of `Attempt2Config` for the loader, with AAPL injected into a universe."""

        def __init__(self, experiments, excluded):
            self.experiments = experiments
            self.excluded_symbols = excluded

    tampered = copy.deepcopy(CONFIG.experiments)
    tampered[0]["universe"] = list(tampered[0]["universe"]) + ["AAPL"]
    shim = ConfigShim(tampered, dict(CONFIG.excluded_symbols))

    attempt2_runner.load_dataset = spy_on_load
    try:
        with pytest.raises(ConfigViolation) as raised:
            attempt2_runner.load_required_dataset(shim)
    finally:
        attempt2_runner.load_dataset = original
    assert str(raised.value) == "sealed protocol both requires and excludes ['AAPL']"
    assert asked == [required], "the excluded symbol was refused before any load"


def test_only_daily_bars_are_loaded() -> None:
    """There is no intraday field to load, and one bar per session is the only shape available.

    The sealed rule: "Every signal is computed from daily closes. No intraday data exists in this
    project and none is approximated."
    """
    assert (
        CONFIG.shared_rule_texts["no_intraday"]
        == "Every signal is computed from daily closes. No intraday data exists in this project "
        "and none is approximated."
    )

    intraday = ("time", "timestamp", "minute", "hour", "datetime", "intraday", "bar_size")
    field_names = [field.name for field in dataclasses.fields(Bar)]
    assert field_names == [
        "session",
        "open",
        "high",
        "low",
        "close",
        "adj_close",
        "volume",
        "dividend",
        "split_ratio",
    ]
    for token in intraday:
        assert not any(token in name for name in field_names)
        assert not any(token in column for column in dataset_module.COLUMNS)

    series = prices("SPY", ramp(COUNT))
    assert len(series.bars) == len(series.sessions) == COUNT
    for session in series.sessions:
        assert isinstance(session, dt.date) and not isinstance(session, dt.datetime)
    assert len(set(series.sessions)) == COUNT, "a session cannot carry two bars"


def test_decision_reads_no_bar_after_the_decision_session() -> None:
    """A view bounded at `t` refuses `t+1`, and the refusal propagates out of the run.

    This is the second structural guard the sealed protocol names: `MarketView` raises
    `LookAheadError` rather than returning a bar the strategy could not have seen.
    """
    enforcement = CONFIG.protocol["partitions"]["enforcement"]
    assert "MarketView raises LookAheadError on any read past the decision session" in enforcement
    assert "Attempt 2 adds no code path that could bypass them." in enforcement

    series = {"SPY": prices("SPY", ramp(COUNT))}

    class Peeker:
        name = "TEST-PEEKER"

        def decide(self, view, context):
            view.bar("SPY", context.session + dt.timedelta(days=7))
            return []

    with pytest.raises(LookAheadError) as raised:
        engine_for(Peeker(), series).run()
    assert "Nothing after the decision session exists yet." in str(raised.value)

    view = MarketView(series, RUN_START, WINDOW)
    assert view.as_of == RUN_START
    assert view.bar("SPY", RUN_START) is not None
    with pytest.raises(LookAheadError):
        view.bar("SPY", SESSIONS[21])
    # History is clipped at the bound too, not merely refused on request.
    assert [bar.session for bar in view.history("SPY", 3)] == SESSIONS[18:21]


# -- the warm-up and run-start rules -------------------------------------------------------------


def test_warmup_history_comes_from_inside_the_development_window() -> None:
    """Warm-up counts in-window sessions only, even when earlier bars exist in the file.

    The sealed rule: "Warm-up history is drawn only from sessions inside the development window."
    XNYS sessions exist from 1990-01-02, so a series straddling the 1993-01-29 window start has
    real bars that must not count. The naive twenty-first bar of the file is outside the window
    entirely.
    """
    assert (
        CONFIG.shared_rule_texts["warmup_data_source"]
        == "Warm-up history is drawn only from sessions inside the development window."
    )

    span = sessions_between(dt.date(1992, 11, 2), dt.date(1993, 4, 30))
    series = {"SPY": prices("SPY", ramp(len(span)), sessions=span)}
    inside = [session for session in series["SPY"].sessions if WINDOW.contains(session)]
    assert inside[0] == WINDOW.start == dt.date(1993, 1, 29)
    assert len(inside) < len(span), "the fixture must straddle the window start"

    start, binding = run_start_for(("SPY",), 21, WINDOW, series)
    assert (start, binding) == (inside[20], "SPY")

    naive = series["SPY"].sessions[20]
    assert not WINDOW.contains(naive)
    assert naive < start, "counting from the first bar in the file would start the run early"


def test_run_start_requires_warmup_for_every_declared_symbol() -> None:
    """The latest-qualifying symbol binds the run start, and a short symbol refuses the run.

    The sealed rule makes the *declared* universe govern, so the run cannot begin until every
    declared symbol is evaluable.
    """
    assert "EVERY symbol in its DECLARED universe" in CONFIG.shared_rule_texts["run_start_rule"]

    late = 8
    two = {
        "SPY": prices("SPY", ramp(COUNT)),
        "SHY": prices("SHY", ["50"] * (COUNT - late), sessions=SESSIONS[late:]),
    }
    assert run_start_for(("SPY",), 5, WINDOW, two) == (SESSIONS[4], "SPY")
    assert run_start_for(("SPY", "SHY"), 5, WINDOW, two) == (SESSIONS[late + 4], "SHY")

    with pytest.raises(ConfigViolation) as raised:
        run_start_for(("SPY",), 5, WINDOW, {"SPY": prices("SPY", ramp(3))})
    assert str(raised.value) == (
        "SPY has only 3 sessions inside development; 5 are required by the sealed warm-up rule"
    )

    with pytest.raises(ConfigViolation) as raised:
        run_start_for(("SPY", "IEF"), 5, WINDOW, two)
    assert str(raised.value) == "run start needs IEF but its series was not loaded"


def test_a_run_short_of_the_window_end_is_refused() -> None:
    """A result that stopped early is refused rather than patched.

    Under the current engine the guard is defensive: `BacktestEngine.run` returns the very bounds
    `run_variant` window-checked and handed it, so the mismatch cannot arise through the normal
    path. The defect is therefore injected at the engine boundary — the only place it could ever
    come from — so that the sealed `partial_or_failed_run_rule` is shown to be enforced and not
    merely written down.
    """
    rule = CONFIG.protocol["partial_or_failed_run_rule"]
    assert rule["partial_completion"] == (
        "A run that did not reach the development window end is not a result. It is recorded as "
        "NOT_RUN with its failure reason and is re-run in full, never patched or extended."
    )

    spec, plan = scaffold()
    truncated = dataclasses.replace(run_scaffold().result, end=SESSIONS[COUNT - 5])
    original = BacktestEngine.run
    BacktestEngine.run = lambda self: truncated
    try:
        with pytest.raises(ConfigViolation) as raised:
            attempt2_runner.run_variant(
                spec, plan, market(), COSTS, WINDOW, CONFIG.rsi_warmup_changes
            )
    finally:
        BacktestEngine.run = original

    message = str(raised.value)
    assert f"ran {SESSIONS[20]}..{SESSIONS[COUNT - 5]}" in message
    assert f"against the planned {RUN_START}..{RUN_END}" in message
    assert "NOT_RUN, never a patched result" in message


# -- data integrity ------------------------------------------------------------------------------


def test_no_price_is_imputed_or_repaired() -> None:
    """A missing bar stays missing: the engine marks the session stale instead of inventing a price.

    The series deliberately keeps its gap after the run — nothing back-fills the loaded data — and
    the equity point for the gap session carries the stale mark with the position still open.
    """
    gap = 30
    series = market(skip=(gap,))
    assert series["SPY"].get(SESSIONS[gap]) is None

    result = run_scaffold(series).result
    assert result.stale_marks == 1
    stale = [point for point in result.equity_curve if point.stale_mark]
    assert [point.session for point in stale] == [SESSIONS[gap]]
    assert stale[0].position_count == 1, "the stale mark applies to a held position"

    assert series["SPY"].get(SESSIONS[gap]) is None, "the loaded series was not repaired"
    assert SESSIONS[gap] not in series["SPY"].bars
    assert SESSIONS[gap] in sessions_between(RUN_START, RUN_END), "the exchange did trade that day"


def test_stale_marks_follow_the_gate_2_engine() -> None:
    """The sealed staleness limit is the Gate 2 engine's, and it halts rather than degrades.

    `max_consecutive_stale` is 5: five consecutive missing sessions complete the run with five
    stale marks, and a sixth raises `DataIntegrityHalt`. The limit is read from the cost model,
    never restated as a literal here.
    """
    limit = COSTS.max_consecutive_stale
    assert limit == 5

    within = tuple(range(25, 25 + limit))
    result = engine_for(
        Greedy("SPY", Decimal("50")), {"SPY": prices("SPY", ramp(COUNT), skip=within)}
    ).run()
    assert result.stale_marks == limit
    assert result.shutdown_session is None

    beyond = tuple(range(25, 25 + limit + 1))
    with pytest.raises(DataIntegrityHalt) as raised:
        engine_for(
            Greedy("SPY", Decimal("50")), {"SPY": prices("SPY", ramp(COUNT), skip=beyond)}
        ).run()
    message = str(raised.value)
    assert f"{limit + 1} consecutive exchange sessions with no bar" in message
    assert f"The sealed limit is {limit}." in message


# -- accounting ----------------------------------------------------------------------------------


def test_cash_is_the_residual_and_the_buffer_holds() -> None:
    """Cash is the exact residual of the fills, and the buffer binds the entry that creates it.

    The buffer is a *pre-trade* constraint: the engine sizes an entry against the equity it can
    see at that moment (`cash - min_cash_buffer_fraction * equity`). It is not a post-trade
    invariant, and this test does not assert one — once the position appreciates, cash is fixed
    while equity grows, so the cash *fraction* legitimately falls below five percent later in the
    curve. What is asserted is the constraint where it actually applies, plus the residual
    identity across the whole run.
    """
    assert COSTS.min_cash_buffer_fraction == Decimal("0.05")
    assert COSTS.max_gross_exposure_fraction == Decimal("0.95")

    probe = Greedy("SPY", Decimal("1000"))
    result = engine_for(probe, {"SPY": prices("SPY", ramp(COUNT))}).run()

    entry = result.fills[0]
    # The account was flat when the entry was sized, so the equity the engine saw was the
    # starting equity exactly.
    base = result.starting_equity
    assert base == COSTS.starting_equity == Decimal("100.00")
    assert entry.fill.gross_notional <= COSTS.max_gross_exposure_fraction * base
    assert -entry.fill.cash_delta <= base - COSTS.min_cash_buffer_fraction * base

    at_entry = next(point for point in result.equity_curve if point.session == entry.session)
    assert at_entry.cash >= COSTS.min_cash_buffer_fraction * base

    cash_moved = sum((record.fill.cash_delta for record in result.fills), Decimal(0))
    dividends = sum(
        (Decimal(event["cash_credited"]) for event in result.dividend_events), Decimal(0)
    )
    assert result.final_cash == result.starting_equity + cash_moved + dividends

    flat = [point for point in result.equity_curve if point.position_count == 0]
    assert flat, "the fixture must contain at least one flat session"
    assert all(point.cash == point.equity for point in flat)


def test_one_decision_per_session_and_no_same_close_fill() -> None:
    """One decision per session, and never a fill at the close that decided it.

    The sealed rule: a decision is taken at the close of session `t` from data at or before `t`,
    and the engine fills at the open of the next exchange session. The engine takes no decision on
    the final session, since there is no next session inside the run to fill at.
    """
    assert (
        "the engine fills at the open of the next exchange session and refuses any earlier fill"
        in CONFIG.shared_rule_texts["one_decision_per_session"]
    )

    probe = Greedy("SPY", Decimal("1000"))
    engine = engine_for(probe, {"SPY": prices("SPY", ramp(COUNT))})
    engine.run()

    span = sessions_between(RUN_START, RUN_END)
    assert probe.decisions == span[:-1]
    assert len(probe.decisions) == len(set(probe.decisions)) == 24

    books = engine._books
    for session, book in books.items():
        assert book.decision_session == session
        for order in book.orders:
            assert order.decision_session == session
            assert order.fill_session > order.decision_session

    fills = {record.fill.symbol: record for record in engine.run().fills}
    assert fills, "the fixture must produce a fill to constrain"


# -- section 5.1 research shutdown ---------------------------------------------------------------


#: The first session of the crash, and therefore the session the breach is recognised on: the
#: engine marks the open position at that close, sees equity below the threshold, and shuts down.
CRASH_AT = 30


def _crash_series() -> dict:
    """A ramp, a crash deep enough to breach 15% of the high-water mark, then a full recovery."""
    closes = ramp(CRASH_AT) + ["87.2000"] * 5 + ramp(COUNT - CRASH_AT - 5, first=140)
    return {"SPY": prices("SPY", closes)}


def test_shutdown_liquidates_and_never_rearms() -> None:
    """The shutdown liquidates at the next open, blocks every later entry, and never re-arms.

    The sealed action is `LIQUIDATE_AT_NEXT_OPEN_AND_BLOCK_ENTRIES`. The probe re-requests an
    entry on every flat session, so "blocked" is observable as a rejection rather than inferred
    from the absence of a fill; and the fixture recovers to a new high after the crash, so a
    re-arming implementation would show a second shutdown or a post-shutdown fill.
    """
    sealed_action = CONFIG.protocol["known_prior_evidence"]["design_target_derived_from_it"]
    assert "the sealed action is LIQUIDATE_AT_NEXT_OPEN_AND_BLOCK_ENTRIES" in sealed_action

    probe = Greedy("SPY", Decimal("1000"))
    engine = engine_for(probe, _crash_series(), label="CRASH")
    result = engine.run()

    assert result.shutdown_session == SESSIONS[CRASH_AT] == dt.date(2000, 2, 15)

    forced = [
        (session, order)
        for session, book in engine._books.items()
        for order in book.orders
        if order.tag == "SHUTDOWN"
    ]
    assert len(forced) == 1
    session, order = forced[0]
    assert session == result.shutdown_session
    assert order.side == SELL
    assert order.fill_session > session

    liquidations = [record for record in result.fills if record.fill.side == SELL]
    assert len(liquidations) == 1
    assert liquidations[0].session == order.fill_session

    assert {rejection.reason for rejection in result.rejections} == {"RESEARCH_SHUTDOWN"}
    after = [
        rejection
        for rejection in result.rejections
        if rejection.order.decision_session >= result.shutdown_session
    ]
    assert after, "every post-shutdown entry attempt must be refused"
    assert all("entries are blocked" in rejection.detail for rejection in after)

    assert not [
        record
        for record in result.fills
        if record.fill.side == BUY and record.session > result.shutdown_session
    ]
    assert len(result.open_positions) == 0, "the account is flat after liquidation"
    assert engine._high_water > result.final_equity, "the fixture did recover to a new high"


def test_s3_c2_is_met_if_and_only_if_the_shutdown_never_fires() -> None:
    """S3-C2 and the section 5.1 shutdown are the same 15% of the same series.

    The two boundaries meet exactly: the engine fires on strict `<` below the threshold, so equity
    at exactly 85% of the high-water mark does not shut down, and the gate is inclusive at 0.15,
    so a drawdown of exactly 0.15 is MET. Both directions are asserted, on synthetic curves for
    the boundary and on real runs for the equivalence.
    """
    limit = Decimal(
        str(CONFIG.criteria["frozen_gate_json_companion_verbatim"]["thresholds"]["max_drawdown_pct"])
    ) / Decimal(100)
    assert limit == COSTS.research_shutdown_drawdown == Decimal("0.15")

    at_boundary = gate.condition_2(synthetic_result(["100", "85", "90"]), CONFIG.criteria)
    assert (at_boundary.verdict, at_boundary.measured) == ("MET", "0.15")
    just_past = gate.condition_2(synthetic_result(["100", "84.99", "90"]), CONFIG.criteria)
    assert (just_past.verdict, just_past.measured) == ("NOT_MET", "0.1501")

    probe = BacktestEngine(
        {"SPY": prices("SPY", ramp(COUNT))},
        COSTS,
        WINDOW,
        Greedy("SPY", Decimal("50")),
        start=RUN_START,
        end=RUN_END,
    )
    probe._high_water = Decimal(100)
    assert probe._check_risk(SESSIONS[21], Decimal("85.00")) is False
    assert probe._shutdown_session is None
    assert probe._check_risk(SESSIONS[22], Decimal("84.99")) is True
    assert probe._shutdown_session == SESSIONS[22]

    crashed = engine_for(Greedy("SPY", Decimal("1000")), _crash_series(), label="CRASH").run()
    crashed_verdict = gate.condition_2(crashed, CONFIG.criteria)
    assert crashed.shutdown_session is not None
    assert crashed_verdict.verdict == "NOT_MET"
    assert Decimal(crashed_verdict.measured) > limit
    assert crashed_verdict.evidence["research_shutdown_session"] == (
        crashed.shutdown_session.isoformat()
    )

    clean = engine_for(Greedy("SPY", Decimal("50")), {"SPY": prices("SPY", ramp(COUNT))}).run()
    clean_verdict = gate.condition_2(clean, CONFIG.criteria)
    assert clean.shutdown_session is None
    assert clean_verdict.verdict == "MET"
    assert Decimal(clean_verdict.measured) <= limit
    assert clean_verdict.evidence["research_shutdown_session"] is None


# -- determinism and the run budget --------------------------------------------------------------


def test_a_rerun_reproduces_both_digests() -> None:
    """The same variant run twice reproduces the trade and equity digests exactly.

    The rerun builds a fresh candidate object, so this covers strategy state as well as engine
    state: a candidate leaking state across runs would change the second digest.
    """
    first = run_scaffold()
    second = run_scaffold(gating=False, label_suffix=attempt2_harness.DETERMINISM_SUFFIX)

    assert first.candidate is not second.candidate
    assert first.result.trades_digest() == second.result.trades_digest()
    assert first.result.equity_digest() == second.result.equity_digest()
    assert second.label == first.label + "#RERUN"
    assert first.gating is True and second.gating is False

    entry = attempt2_harness._determinism_entry(first, second)
    assert entry["identical"] is True
    assert entry["trades_digest"] == entry["rerun_trades_digest"]
    assert entry["equity_digest"] == entry["rerun_equity_digest"]
    assert entry["variant_id"] == first.spec.variant_id
    assert len(entry["trades_digest"]) == 64


def test_no_variant_is_run_twice_for_its_result() -> None:
    """Only the gating call contributes a result; the rerun and the stress run are non-gating.

    `run_all` is inspected rather than executed: executing it would perform the eighteen declared
    runs, and the sealed budget permits them exactly once, in the evaluation step. The three call
    sites are the gating pass over `plan.variants`, the determinism rerun and the cost-stress run,
    and only the first carries `gating=True`.
    """
    budget = CONFIG.iteration_budget
    assert budget["total_declared_gating_variants"] == 15
    assert budget["total_declared_non_gating_stress_runs"] == 3
    assert budget["total_declared_runs"] == 18
    assert budget["revisions_permitted"] == 0
    assert (
        budget["gating_variants_per_candidate"] * budget["candidates"]
        == budget["total_declared_gating_variants"]
    )
    assert (
        budget["total_declared_gating_variants"] + budget["total_declared_non_gating_stress_runs"]
        == budget["total_declared_runs"]
    )

    tree = ast.parse(textwrap.dedent(inspect.getsource(attempt2_harness.run_all)))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and getattr(node.func, "id", getattr(node.func, "attr", None)) == "run_variant"
    ]
    assert len(calls) == 3
    keywords = [{kw.arg: ast.unparse(kw.value) for kw in call.keywords} for call in calls]
    gating = [kw for kw in keywords if kw.get("gating") == "True"]
    non_gating = [kw for kw in keywords if kw.get("gating") == "False"]
    assert len(gating) == 1 and len(non_gating) == 2
    assert {kw["label_suffix"] for kw in non_gating} == {
        "DETERMINISM_SUFFIX",
        "STRESS_SUFFIX",
    }
    assert (attempt2_harness.DETERMINISM_SUFFIX, attempt2_harness.STRESS_SUFFIX) == (
        "#RERUN",
        "#STRESS",
    )

    # A non-gating run is labelled apart from the result it must not become.
    stressed = run_scaffold(gating=False, label_suffix=attempt2_harness.STRESS_SUFFIX)
    assert stressed.gating is False
    assert stressed.label.endswith("#STRESS")
    assert stressed.label != run_scaffold().label
