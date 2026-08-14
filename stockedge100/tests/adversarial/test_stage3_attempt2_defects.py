"""Stage 3 Attempt 2 — adversarial tests: boundary values and ambiguous event ordering.

The operating prompt requires "adversarial tests for boundary values and ambiguous event ordering".
This module supplies them for RA1, the shared risk architecture, by driving
:meth:`stockedge100.strategies.attempt2_risk.Ra1Candidate.decide` one decision session at a time
over synthetic price paths whose every number was computed in advance and is asserted here.

Three properties of this module matter for the governance boundary:

* **No market observation is read.** Every series is built in memory by :func:`prices` from string
  literals. Nothing calls ``load_dataset`` or ``load_series``, so no test here can expose real
  performance, and none of them depends on which partition is unlocked.
* **The window is local.** :func:`view_at` builds a throwaway :class:`ResearchWindow` named
  ``"test"`` spanning 1990–2030. It is not the development partition and not any other; it exists so
  that :class:`MarketView`'s look-ahead guard still applies to the synthetic rows.
* **RA1 constants are read out of the seal, never restated.** :data:`SEALED_RA1` is C1's own
  ``primary_parameters`` block. The only overridden values are *signal* lookbacks
  (:data:`SCAFFOLD_SMA`) and, in a few ordering tests, ``max_hold`` — both documented at each use as
  scaffolding that shortens a synthetic fixture and neither of which is a gate input.

Every test that injects a defect injects exactly one, and the three clean controls at the top of the
file establish that the harness admits a correct path. The last control is the one
``.claude/rules/tests.md`` calls mandatory: a synthetic candidate meeting every threshold *is*
admitted with stage verdict ``PASS``, so a stage that rejects everything is distinguishable from an
evaluator that rejects everything.
"""

from __future__ import annotations

import ast
import datetime as dt
import inspect
from decimal import Decimal, DivisionByZero, localcontext

import pytest

from stockedge100.backtest.config import load_stage2_config
from stockedge100.backtest.costs import BASE, ENGINE_CONTEXT, ZERO, CostModel
from stockedge100.backtest.dataset import series_from_rows
from stockedge100.backtest.engine import BacktestResult, DecisionContext, EquityPoint
from stockedge100.backtest.errors import ConfigViolation, InvariantViolation
from stockedge100.backtest.market import MarketView
from stockedge100.backtest.orders import BUY, SELL
from stockedge100.backtest.portfolio import Trade
from stockedge100.backtest.window import ResearchWindow
from stockedge100.strategies import (
    attempt2_candidates,
    attempt2_harness,
    attempt2_indicators,
    attempt2_risk,
    gate,
    runner,
)
from stockedge100.strategies.attempt2_config import load_attempt2_config

CONFIG = load_attempt2_config()
COSTS = CostModel(load_stage2_config().cost_model, BASE)

RA1_BLOCK = CONFIG.risk_architecture

#: C1's sealed parameter block, read from the frozen protocol. No RA1 constant is written here.
SEALED_RA1 = next(
    experiment["primary_parameters"]
    for experiment in CONFIG.experiments
    if experiment["experiment_id"] == attempt2_candidates.C1
)
RA1 = attempt2_risk.Ra1Parameters.from_parameters(SEALED_RA1)

#: A three-session moving average. Not sealed: the sealed lookbacks are 200, 5 and 10 sessions, and
#: a synthetic fixture long enough to warm one of those would obscure the boundary being tested.
#: The signal lookback is not a gate input and no assertion in this file reads it as one.
SCAFFOLD_SMA = 3

DAY_ZERO = dt.date(2000, 1, 3)


def day(index: int) -> dt.date:
    return DAY_ZERO + dt.timedelta(days=index)


def prices(symbol: str, closes, *, adj=None, opens=None):
    """A ``PriceSeries`` over consecutive calendar days from in-memory rows.

    ``split_ratio`` is passed explicitly because :func:`series_from_rows` defaults it to ``"0"``,
    which no real normalized row carries. ``high`` and ``low`` bracket ``open`` and ``close`` so no
    bar is internally inconsistent, even though RA1 reads neither.
    """

    rows = []
    for offset, close in enumerate(closes):
        opening = close if opens is None else opens[offset]
        rows.append(
            {
                "session": day(offset).isoformat(),
                "open": str(opening),
                "high": str(max(Decimal(str(opening)), Decimal(str(close)))),
                "low": str(min(Decimal(str(opening)), Decimal(str(close)))),
                "close": str(close),
                "adj_close": str(close if adj is None else adj[offset]),
                "volume": "1000",
                "split_ratio": "1",
            }
        )
    return series_from_rows(symbol, rows)


def alternating(count: int, low: str = "100", high: str = "101") -> list[str]:
    """A two-value adjusted-close path. Over any 21-bar window this is always ten up moves and ten
    down moves, so VOL20 is identical at every decision session of a fixture built from it."""

    return [low if index % 2 == 0 else high for index in range(count)]


def ramp(count: int, first: int = 80) -> list[str]:
    """A strictly rising close path, so a ``close > SMA`` signal fires on every session."""

    return [str(first + index) for index in range(count)]


def descending(count: int, first: int = 100) -> list[str]:
    """A strictly falling close path, so a ``close > SMA`` signal never fires."""

    return [str(first - index) for index in range(count)]


def market(*series) -> dict:
    return {item.symbol: item for item in series}


def view_at(series: dict, session: dt.date) -> MarketView:
    window = ResearchWindow(name="test", start=dt.date(1990, 1, 1), end=dt.date(2030, 12, 31))
    return MarketView(series, session, window)


def candidate(*, defensive: str | None = "SHY", **overrides):
    """A C3 candidate carrying the sealed RA1 block plus scaffolded signal parameters.

    C3 is used throughout because it is the only sealed candidate whose ``target`` can return two
    different symbols or ``None``, which is what the flat-first, substitution and missing-bar
    orderings need. ``build_candidate`` performs no sealed-value validation, so a scaffolded lookback
    is legal; the RA1 half of the block is the sealed one in every case.
    """

    parameters = dict(SEALED_RA1)
    parameters.pop("sma_short", None)
    parameters.update(
        {
            "sma_long": SCAFFOLD_SMA,
            "risk_symbol": "SPY",
            "defensive_symbol": defensive,
        }
    )
    parameters.update(overrides)
    universe = ("SPY",) if defensive is None else ("SPY", defensive)
    return attempt2_candidates.build_candidate(
        experiment_id=attempt2_candidates.C3,
        variant_id=f"{attempt2_candidates.C3}#TEST",
        universe=universe,
        parameters=parameters,
        costs=COSTS,
        rsi_warmup_changes=CONFIG.rsi_warmup_changes,
    )


EQUITY = Decimal(100)


def run(subject, series: dict, indexes, *, held=None, equity=None, shutdown=None):
    """Call ``decide`` once per decision session and return the orders emitted at each.

    One call per session is what the engine does: it evaluates fills for session ``t`` before calling
    ``decide`` at ``t``, so ``held`` is the position state the engine would present, supplied by the
    test rather than simulated.
    """

    emitted = []
    for position, index in enumerate(indexes):
        session = day(index)
        value = EQUITY if equity is None else Decimal(equity[position])
        context = DecisionContext(
            session=session,
            cash=value,
            equity=value,
            open_symbols=() if held is None else held[position],
            shutdown_active=False if shutdown is None else shutdown[position],
        )
        emitted.append(subject.decide(view_at(series, session), context))
    return emitted


# -- gate-level factories, for the mandatory clean control ---------------------------------------


def trade(pnl: str, *, symbol: str = "SPY", index: int = 0) -> Trade:
    entry = Decimal(100)
    return Trade(
        symbol=symbol,
        entry_session=day(2 * index),
        exit_session=day(2 * index + 1),
        quantity=Decimal(1),
        entry_cash=entry,
        exit_cash=entry + Decimal(pnl),
        dividends=ZERO,
        entry_costs=ZERO,
        exit_costs=ZERO,
    )


def result(*, pnls=None, equity=None, starting: str = "100",
           symbols: tuple[str, ...] = ("SPY",), shutdown: dt.date | None = None) -> BacktestResult:
    trades = [trade(value, index=position) for position, value in enumerate(pnls or [])]
    if equity is None:
        equity = [starting]
        running = Decimal(starting)
        for item in trades:
            running += item.pnl
            equity.append(f"{running:f}")
    points = [
        EquityPoint(session=day(offset), cash=Decimal(value), equity=Decimal(value),
                    stale_mark=False, position_count=0)
        for offset, value in enumerate(equity)
    ]
    return BacktestResult(
        label="synthetic", scenario=BASE, symbols=symbols,
        start=points[0].session, end=points[-1].session, equity_curve=points,
        fills=[], rejections=[], trades=trades, dividend_events=[], stale_marks=0,
        shutdown_session=shutdown, starting_equity=Decimal(starting),
        final_cash=Decimal(equity[-1]), final_equity=Decimal(equity[-1]),
        open_positions=[], cost_model={},
    )


def plan(universe: tuple[str, ...] = ("SPY",)) -> runner.CandidatePlan:
    return runner.CandidatePlan(
        experiment_id="SE100-S3A2-CONTROL", family="control", declared_universe=universe,
        warmup_sessions=1, effective_warmup=1, run_start=day(0), run_end=day(80),
        binding_symbol=universe[0], variants=(), all_symbols=universe,
    )


def four_neighbours(*returns):
    rows = []
    for position, value in enumerate(returns):
        spec = runner.VariantSpec(
            experiment_id="SE100-S3A2-CONTROL", variant_id=f"SE100-S3A2-CONTROL#N{position + 1}",
            role=runner.NEIGHBOUR, index=position + 1, universe=("SPY",),
            parameters={"sma_long": 100 + position}, symbols=("SPY",),
        )
        final = Decimal(100) * (Decimal(1) + Decimal(value))
        rows.append((spec, result(equity=["100", f"{final:f}"])))
    return rows


def condition_row(condition_id: str, verdict: str) -> dict:
    """A condition row whose ``satisfied`` flag always agrees with the sealed definition, because it
    comes from :class:`gate.ConditionVerdict` rather than being written by hand."""

    return gate.ConditionVerdict(condition_id, "sealed condition text", verdict).to_json()


# -- clean controls -------------------------------------------------------------------------------


def test_a_clean_entry_fixture_emits_one_buy_at_the_ceiling_fraction():
    """Control. A rising close path with a moderate adjusted-close path enters at the RA1-1 ceiling.

    VOL20 over the alternating 100/101 adjusted path is 0.16206…, so ``f_vol = 0.10 / 0.16206 =
    0.61704…`` and ``f = min(0.50, 0.61704) = f_base``. Every blocking test below differs from this
    fixture in exactly one number.
    """

    subject = candidate(defensive=None)
    series = market(prices("SPY", ramp(21), adj=alternating(21)))
    emitted = run(subject, series, [20])

    assert len(emitted[0]) == 1
    order = emitted[0][0]
    assert order.side == BUY
    assert order.symbol == "SPY"
    assert order.budget == RA1.f_base * EQUITY
    assert subject.entry_fractions == [RA1.f_base]
    assert sum(subject.blocked_entries.values()) == 0


def test_a_clean_hold_fixture_emits_nothing():
    """Control. A held position with no exit condition true emits no order at all.

    The close path keeps rising, so the loss control is far away, the scaffolded holding period is
    not reached, and the signal still names the held symbol. All three exit tests below flip exactly
    one of those.
    """

    subject = candidate(defensive=None)
    series = market(prices("SPY", ramp(22), adj=alternating(22)))
    emitted = run(subject, series, [20, 21], held=[(), ("SPY",)])

    assert len(emitted[0]) == 1
    assert emitted[1] == []
    assert subject.exit_reasons == {reason: 0 for reason in attempt2_risk.EXIT_PRECEDENCE}


def test_a_synthetic_candidate_meeting_every_threshold_is_admitted():
    """Control. All seven conditions satisfied by one candidate gives ``admitted`` and stage ``PASS``.

    Mandatory under ``.claude/rules/tests.md``: without it, a stage that rejects every real candidate
    is indistinguishable from an evaluator that rejects everything. The synthetic evidence is 40
    closed trades in blocks of three +2 winners and one -1 loser, over a single declared instrument:

    * S3-C1 total return ``0.50 > 0``
    * S3-C2 worst close-to-close drawdown ``1/106 = 0.0094 <= 0.15``
    * S3-C3 profit factor ``60/10 = 6.0 >= 1.10``
    * S3-C4 ``40 >= 30`` closed trades
    * S3-C5 both removals leave ``1.5/1.02 - 1 = 0.47 > 0``
    * S3-C6 ``NOT_APPLICABLE_BY_CONDITION_TEXT`` — one declared instrument, satisfied without being
      met, which is the sealed distinction this control also exercises
    * S3-C7 four neighbours all positive, matching the primary's sign
    """

    primary = result(pnls=["2", "2", "2", "-1"] * 10)
    evaluated = gate.evaluate_candidate(
        plan=plan(("SPY",)),
        primary=primary,
        neighbours=four_neighbours("0.40", "0.55", "0.30", "0.60"),
        criteria=CONFIG.criteria,
    )

    assert evaluated["admitted"] is True
    assert evaluated["conditions_not_met"] == []
    assert evaluated["conditions_not_evaluable"] == []
    assert evaluated["conditions_not_applicable"] == ["S3-C6"]
    not_applicable = next(row for row in evaluated["conditions"] if row["id"] == "S3-C6")
    assert not_applicable["verdict"] == gate.NOT_APPLICABLE
    assert not_applicable["satisfied"] is True

    stage = gate.stage_verdict([evaluated], CONFIG.criteria)
    derivation = CONFIG.criteria["verdict_token_derivation"]
    assert stage["verdict"] == "PASS"
    assert stage["pass_token"] == derivation["pass_token"]
    assert stage["admitted_candidates"] == ["SE100-S3A2-CONTROL"]
    attempt2_harness._refuse_incoherent(stage, [evaluated], CONFIG.binding)


# -- RA1-1 and RA1-2: entry sizing ---------------------------------------------------------------


def test_entry_emits_one_order_sized_by_ra1_2():
    """RA1-2: ``budget = f * equity`` with ``f = min(f_cap, f_vol)``, and RA1-8: one order.

    The sealed rule's last line reserves the engine's own cap, cash buffer, safety margin and share
    rounding for later — the candidate's job is the budget, and this asserts the budget.
    """

    subject = candidate(defensive=None)
    series = market(prices("SPY", ramp(21), adj=alternating(21)))
    emitted = run(subject, series, [20])

    sigma = attempt2_indicators.vol20(
        [series["SPY"].bars[session] for session in series["SPY"].sessions]
    )
    with localcontext(ENGINE_CONTEXT):
        expected = min(RA1.f_cap(ZERO), RA1.vol_target / sigma)
    assert len(emitted[0]) == 1
    assert emitted[0][0].budget == expected * EQUITY
    assert subject.entry_fractions == [expected]
    assert "at entry only" == RA1_BLOCK["RA1-2"]["applies"]


def test_no_entry_fraction_exceeds_f_base():
    """RA1-2 ``cannot_increase_exposure``: "f = min(f_cap, f_vol), so volatility targeting can only
    reduce exposure below the RA1-1 ceiling. It can never raise it."

    A very low volatility drives ``f_vol`` far above ``f_base``, and the emitted fraction is still
    ``f_base``. The guard that would catch a defective ``min`` is then fired directly by injecting an
    ``f_cap`` above the ceiling, which is the only way ``fraction > f_base`` is reachable at all.
    """

    subject = candidate(defensive=None)
    calm = market(prices("SPY", ramp(21), adj=alternating(21, "100", "100.0001")))
    emitted = run(subject, calm, [20])

    sigma = attempt2_indicators.vol20(
        [calm["SPY"].bars[session] for session in calm["SPY"].sessions]
    )
    with localcontext(ENGINE_CONTEXT):
        assert RA1.vol_target / sigma > RA1.f_base
    assert len(emitted[0]) == 1
    assert subject.entry_fractions == [RA1.f_base]
    assert emitted[0][0].budget == RA1.f_base * EQUITY

    assert RA1_BLOCK["RA1-2"]["cannot_increase_exposure"].startswith("f = min(f_cap, f_vol)")


def test_no_entry_fraction_exceeds_f_base_guard_fires_when_the_cap_is_tampered_with(monkeypatch):
    """The RA1-1 ceiling assertion is a real guard, not dead code.

    Injected defect: a ladder that returns 0.90 instead of the sealed 0.50. On the clean fixture
    ``f_vol`` is 0.617, so ``min(0.90, 0.617) = 0.617 > f_base`` and the invariant must refuse rather
    than size above RA1-1's ceiling.
    """

    subject = candidate(defensive=None)
    series = market(prices("SPY", ramp(21), adj=alternating(21)))
    monkeypatch.setattr(
        attempt2_risk.Ra1Parameters, "f_cap", lambda self, drawdown: Decimal("0.90")
    )

    with pytest.raises(InvariantViolation) as raised:
        run(subject, series, [20])
    assert "above the RA1-1 ceiling" in str(raised.value)


def test_volatility_floor_blocks_entry_below_five_percent():
    """RA1-2: "If f < f_floor = 0.05: no entry that session, reason NO_ENTRY_VOLATILITY_FLOOR."

    The sealed ``f_floor_rationale`` says the floor "binds only when sigma exceeds sigma_target /
    f_floor = 2.00, that is 200% annualised". The 100/200 adjusted path gives sigma 12.2, above that
    boundary; the clean 100/101 control gives 0.162, below it. Both halves are asserted so the test
    fails if the floor moves in either direction.
    """

    assert RA1.vol_target / RA1.vol_floor_fraction == Decimal(2)
    assert "sigma_target / f_floor = 2.00" in RA1_BLOCK["RA1-2"]["f_floor_rationale"]

    wild = market(prices("SPY", ramp(21), adj=alternating(21, "100", "200")))
    sigma = attempt2_indicators.vol20(
        [wild["SPY"].bars[session] for session in wild["SPY"].sessions]
    )
    assert sigma > Decimal(2)

    subject = candidate(defensive=None)
    emitted = run(subject, wild, [20])
    assert emitted[0] == []
    assert subject.blocked_entries[attempt2_risk.NO_ENTRY_VOLATILITY_FLOOR] == 1
    assert subject.entry_fractions == []

    calm = market(prices("SPY", ramp(21), adj=alternating(21)))
    control = candidate(defensive=None)
    assert attempt2_indicators.vol20(
        [calm["SPY"].bars[session] for session in calm["SPY"].sessions]
    ) < Decimal(2)
    assert len(run(control, calm, [20])[0]) == 1
    assert control.blocked_entries[attempt2_risk.NO_ENTRY_VOLATILITY_FLOOR] == 0


def test_zero_volatility_blocks_entry_before_any_division():
    """RA1-2: "If sigma == 0: no entry, reason NO_ENTRY_ZERO_VOLATILITY."

    The ordering is the point. ``f_vol = sigma_target / sigma`` traps ``DivisionByZero`` under
    ENGINE_CONTEXT, so the zero test must run first. That the volatility-floor counter stays at zero
    is the evidence that it did: a reordered implementation would raise, and one that returned a
    quiet infinity would have incremented the floor counter instead.
    """

    subject = candidate(defensive=None)
    series = market(prices("SPY", ramp(21), adj=["100"] * 21))
    emitted = run(subject, series, [20])

    assert emitted[0] == []
    assert subject.blocked_entries[attempt2_risk.NO_ENTRY_ZERO_VOLATILITY] == 1
    assert subject.blocked_entries[attempt2_risk.NO_ENTRY_VOLATILITY_FLOOR] == 0

    with localcontext(ENGINE_CONTEXT):
        with pytest.raises(DivisionByZero):
            RA1.vol_target / ZERO


def test_size_floor_blocks_entry_below_one_dollar():
    """RA1-2: "If budget < min_order_notional_usd = 1.00 from SE100-CFG-2001 sizing: no entry,
    reason NO_ENTRY_SIZE_FLOOR."

    The comparison is strict, so a budget of exactly ``min_order_notional`` is not blocked. At
    ``f = 0.50`` an equity of 1 gives 0.50 (blocked) and an equity of 2 gives exactly 1.00
    (permitted), which brackets the boundary from both sides.
    """

    assert COSTS.min_order_notional == Decimal("1.00")

    series = market(prices("SPY", ramp(21), adj=alternating(21)))

    blocked = candidate(defensive=None)
    assert run(blocked, series, [20], equity=["1"])[0] == []
    assert blocked.blocked_entries[attempt2_risk.NO_ENTRY_SIZE_FLOOR] == 1

    permitted = candidate(defensive=None)
    emitted = run(permitted, series, [20], equity=["2"])
    assert len(emitted[0]) == 1
    assert emitted[0][0].budget == COSTS.min_order_notional
    assert permitted.blocked_entries[attempt2_risk.NO_ENTRY_SIZE_FLOOR] == 0


def test_insufficient_history_blocks_the_entry_and_holds_cash():
    """The shared ``insufficient_history_rule``: "the target for that session is cash. Never a hold,
    never a guess, never a carried-forward value."

    VOL20 needs 21 visible bars. With 20 the fixture's signal still fires — close 99 exceeds the
    three-session mean 98 — so the *only* reason no order is emitted is the undefined indicator.
    """

    subject = candidate(defensive=None)
    series = market(prices("SPY", ramp(20), adj=alternating(20)))
    emitted = run(subject, series, [19])

    assert attempt2_indicators.VOL20_BARS == 21
    assert subject.target(view_at(series, day(19)), DecisionContext(
        session=day(19), cash=EQUITY, equity=EQUITY, open_symbols=(), shutdown_active=False
    )) == "SPY"
    assert emitted[0] == []
    assert subject.blocked_entries[attempt2_risk.NO_ENTRY_INSUFFICIENT_HISTORY] == 1
    assert CONFIG.shared_rule_texts["insufficient_history_rule"].endswith(
        "A missing indicator never produces a hold, a guess, or a carried-forward value."
    )


# -- RA1-5: the account de-risk ladder -----------------------------------------------------------


def test_ladder_never_blocks_an_entry():
    """RA1-5 ``never_blocks_entry``: "The ladder reduces size. It never blocks an entry and never
    sets f_cap to zero. This is deliberate and is the correction of a rejected earlier formulation."

    Three flat decision sessions at equities 100, 91 and 89 against a high-water mark of 100 put
    drawdown in each of the three sealed bands — 0, 0.09 and 0.11 — and every one of them emits an
    order. The fractions are the sealed rungs in order and no blocking counter moves.
    """

    subject = candidate(defensive=None)
    series = market(prices("SPY", ramp(23), adj=alternating(23)))
    emitted = run(subject, series, [20, 21, 22], equity=["100", "91", "89"])

    assert [len(orders) for orders in emitted] == [1, 1, 1]
    assert subject.entry_fractions == [Decimal("0.50"), Decimal("0.25"), Decimal("0.125")]
    assert [order[0].budget for order in emitted] == [
        Decimal("50.00"), Decimal("22.75"), Decimal("11.125")
    ]
    assert subject.ladder_sessions == {
        "dd<0.08": 1, "0.08<=dd<0.10": 1, "dd>=0.10": 1
    }
    assert sum(subject.blocked_entries.values()) == 0
    assert all(RA1.f_cap(Decimal(value)) > ZERO for value in ("0", "0.08", "0.10", "0.50", "0.99"))


def test_hwm_updates_every_decision_session_whether_flat_or_not():
    """RA1-5: "hwm is the running maximum of context.equity over the decision sessions of the run,
    seeded at the first decision session's equity and updated on every decision session whether the
    account is flat or not."

    The held scenario is the discriminating one. Equity rises to 130 on a session the candidate is
    holding, then falls to 110: drawdown is ``20/130 = 0.1538``, the deepest sealed band. An
    implementation that froze the high-water mark while a position was open would compute
    ``(100 - 110) / 100 = -0.10`` and tally the shallowest band instead, so the two tallies differ.
    """

    flat = candidate(defensive=None)
    series = market(prices("SPY", ramp(23), adj=alternating(23)))
    run(flat, series, [20, 21, 22], equity=["100", "120", "90"])
    assert flat.ladder_sessions == {"dd<0.08": 2, "0.08<=dd<0.10": 0, "dd>=0.10": 1}

    while_held = candidate(defensive=None)
    run(while_held, series, [20, 21, 22], held=[(), ("SPY",), ("SPY",)],
        equity=["100", "130", "110"])
    assert while_held.ladder_sessions == {"dd<0.08": 2, "0.08<=dd<0.10": 0, "dd>=0.10": 1}
    assert "whether the account is flat or not" in " ".join(RA1_BLOCK["RA1-5"]["rule"])


def test_sizing_is_read_at_entry_only():
    """RA1-2 ``applies``: "at entry only", for the sealed ``entry_only_reason`` — "Re-sizing an open
    position would require a partial exit the accounting does not model."

    A held session whose drawdown has crossed into the 0.125 rung emits nothing: no re-size, no
    partial exit, and no second entry fraction. The AST check is the structural half — every call
    site of the sizing routine is inside the entry path, so no other path could re-size.
    """

    subject = candidate(defensive=None)
    series = market(prices("SPY", ramp(22), adj=alternating(22)))
    emitted = run(subject, series, [20, 21], held=[(), ("SPY",)], equity=["100", "89"])

    assert len(emitted[0]) == 1
    assert emitted[1] == []
    assert len(subject.entry_fractions) == 1
    assert subject.entry_fractions_filled == [RA1.f_base]

    tree = ast.parse(inspect.getsource(attempt2_risk))
    callers = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for inner in ast.walk(node):
                if (isinstance(inner, ast.Call) and isinstance(inner.func, ast.Attribute)
                        and inner.func.attr == "_entry_budget"):
                    callers.add(node.name)
    assert callers == {"_entry_decision"}
    assert "at entry only" in RA1_BLOCK["RA1-5"]["read"]


# -- RA1-3: per-position loss control ------------------------------------------------------------


def test_loss_control_triggers_at_exactly_eight_percent():
    """RA1-3: "if close(symbol, t) <= P_ref * (1 - L), emit a full exit, reason EXIT_LOSS_CONTROL."

    The comparison is inclusive, so ``P_ref = 100`` triggers at exactly 92.00 and does not trigger at
    92.01. The control uses a defensive symbol of ``None`` so that a close below the moving average
    resolves to cash and the exit that does fire is attributable to the signal, not to the boundary.
    """

    assert Decimal("92.00") == Decimal(100) * (Decimal(1) - RA1.loss_control)

    triggered = candidate(defensive=None)
    at_boundary = market(prices("SPY", ramp(21) + ["92"], adj=alternating(22)))
    emitted = run(triggered, at_boundary, [20, 21], held=[(), ("SPY",)])
    assert len(emitted[1]) == 1
    assert emitted[1][0].side == SELL
    assert triggered.exit_reasons[attempt2_risk.EXIT_LOSS_CONTROL] == 1

    control = candidate(defensive=None)
    above = market(prices("SPY", ramp(21) + ["92.01"], adj=alternating(22)))
    emitted = run(control, above, [20, 21], held=[(), ("SPY",)])
    assert len(emitted[1]) == 1
    assert control.exit_reasons[attempt2_risk.EXIT_LOSS_CONTROL] == 0
    assert control.exit_reasons[attempt2_risk.EXIT_SIGNAL] == 1


def test_loss_control_reference_is_the_decision_close():
    """RA1-3: "P_ref = close of the DECISION session on which the entry order was scheduled", and
    ``why_decision_close_and_not_fill_price`` — "The fill price is the next session's open and is not
    exposed to the candidate at decision time."

    The exit session opens at 50 and closes at 92. Under the sealed reading ``P_ref`` is the previous
    decision close of 100, so ``92 <= 92.00`` triggers. Under a fill-price reading the reference
    would be an open of 50 and the threshold 46.00, which 92 clears comfortably — so the two readings
    disagree on this bar and the assertion picks out the sealed one.
    """

    subject = candidate(defensive=None)
    series = market(prices("SPY", ramp(21) + ["92"], adj=alternating(22), opens=ramp(21) + ["50"]))
    emitted = run(subject, series, [20, 21], held=[(), ("SPY",)])

    assert subject.exit_reasons[attempt2_risk.EXIT_LOSS_CONTROL] == 1
    assert len(emitted[1]) == 1
    assert Decimal("92") > Decimal("50") * (Decimal(1) - RA1.loss_control)
    assert "not exposed to the candidate at decision time" in (
        RA1_BLOCK["RA1-3"]["why_decision_close_and_not_fill_price"]
    )


def test_unfilled_entry_discards_its_reference_price():
    """RA1-3: "A pending P_ref is discarded if the symbol is absent from context.open_symbols at the
    next decision session, because the entry was not filled."

    Session 0 schedules an entry at a close of 100. Session 1 finds the account still flat — the
    order did not fill — and schedules a fresh entry at a close of 120. Session 2 holds the position
    at a close of 100: that is a 16.7% decline from 120 and triggers, but only a 0% decline from the
    discarded 100 and would not. Two fractions were offered; one was filled.
    """

    subject = candidate(defensive=None)
    closes = ramp(21) + ["120", "100"]
    series = market(prices("SPY", closes, adj=alternating(23)))
    emitted = run(subject, series, [20, 21, 22], held=[(), (), ("SPY",)])

    assert [len(orders) for orders in emitted[:2]] == [1, 1]
    assert emitted[0][0].side == BUY and emitted[1][0].side == BUY
    assert len(emitted[2]) == 1
    assert subject.exit_reasons[attempt2_risk.EXIT_LOSS_CONTROL] == 1
    assert Decimal("100") <= Decimal("120") * (Decimal(1) - RA1.loss_control)
    assert Decimal("100") > Decimal("100") * (Decimal(1) - RA1.loss_control)
    assert len(subject.entry_fractions) == 2
    assert len(subject.entry_fractions_filled) == 1


# -- RA1-4 and exit precedence -------------------------------------------------------------------


def test_max_hold_counts_decision_sessions_inclusively():
    """RA1-4: "sessions_held counts the decision sessions on which the symbol has appeared in
    context.open_symbols, the current session included. If sessions_held >= H, emit a full exit."

    ``max_hold`` is scaffolded to 2 so that a synthetic fixture can reach the boundary; the sealed
    horizons are 20, 10 and 252 sessions and none of them is asserted as a number here. The first
    held session has ``sessions_held == 1`` and emits nothing; the second has 2 and exits.
    """

    subject = candidate(defensive=None, max_hold=2)
    series = market(prices("SPY", ramp(23), adj=alternating(23)))
    emitted = run(subject, series, [20, 21, 22], held=[(), ("SPY",), ("SPY",)])

    assert emitted[1] == []
    assert len(emitted[2]) == 1
    assert subject.exit_reasons[attempt2_risk.EXIT_MAX_HOLD] == 1
    rule = " ".join(RA1_BLOCK["RA1-4"]["rule"])
    assert "the current session included" in rule
    assert "sessions_held >= H" in rule


def test_exit_precedence_is_loss_control_then_max_hold_then_signal():
    """``exit_precedence``: "When more than one exit condition is true on the same decision session,
    the position is closed once and the attributed reason is the highest-precedence condition."

    Three drives over the same held session, each making a different set of conditions true:

    * close 85 with ``H = 1`` — all three true, attributed ``EXIT_LOSS_CONTROL``
    * close 95 with ``H = 1`` — loss control false, attributed ``EXIT_MAX_HOLD``
    * close 95 with ``H = 5`` — only the signal, attributed ``EXIT_SIGNAL``

    Exactly one order is emitted in each case, which is the sealed ``purpose`` — "Reason attribution
    only. The precedence changes no exit decision."
    """

    assert attempt2_risk.EXIT_PRECEDENCE == tuple(RA1_BLOCK["exit_precedence"]["order"])
    assert RA1_BLOCK["exit_precedence"]["purpose"].startswith("Reason attribution only.")

    outcomes = []
    for close, horizon in (("85", 1), ("95", 1), ("95", 5)):
        subject = candidate(defensive=None, max_hold=horizon)
        series = market(prices("SPY", ramp(21) + [close], adj=alternating(22)))
        emitted = run(subject, series, [20, 21], held=[(), ("SPY",)])
        assert len(emitted[1]) == 1
        outcomes.append({
            reason: count for reason, count in subject.exit_reasons.items() if count
        })

    assert outcomes == [
        {attempt2_risk.EXIT_LOSS_CONTROL: 1},
        {attempt2_risk.EXIT_MAX_HOLD: 1},
        {attempt2_risk.EXIT_SIGNAL: 1},
    ]


# -- RA1-6 and RA1-7: lockout and conflict resolution --------------------------------------------


def test_lockout_lasts_five_decision_sessions_after_a_risk_exit():
    """RA1-6: "the candidate may not re-enter that same symbol for R = 5 decision sessions counted
    from the decision session that scheduled the exit."

    The exit is scheduled at decision index 1, so indexes 2, 3, 4, 5 and 6 are locked out — five
    sessions — and index 7 may enter again. Releasing one session earlier would give four and
    contradict RA1-7's "a switch that follows a risk exit costs at least six sessions out of the
    market"; the signal fires on every one of those sessions, so the block is the only explanation.
    """

    assert RA1.reentry_delay == 5
    assert "R = 5 decision sessions" in RA1_BLOCK["RA1-6"]["rule"]
    assert "at least six sessions out of the market" in RA1_BLOCK["RA1-7"]["rule"]

    subject = candidate(defensive=None, max_hold=1)
    series = market(prices("SPY", ramp(28), adj=alternating(28)))
    emitted = run(subject, series, list(range(20, 28)),
                  held=[(), ("SPY",), (), (), (), (), (), ()])

    assert subject.exit_reasons[attempt2_risk.EXIT_MAX_HOLD] == 1
    assert [len(orders) for orders in emitted] == [1, 1, 0, 0, 0, 0, 0, 1]
    assert subject.blocked_entries[attempt2_risk.NO_ENTRY_LOCKOUT] == 5
    assert emitted[7][0].side == BUY


def test_signal_exit_creates_no_lockout():
    """RA1-6: "An exit with reason EXIT_SIGNAL creates no lockout."

    The held session's close of 95 falls below the moving average, so the exit is a signal exit; the
    next session's close of 105 rises back above it and enters immediately. One session out of the
    market under RA1-7, not six.
    """

    subject = candidate(defensive=None, max_hold=5)
    series = market(prices("SPY", ramp(21) + ["95", "105"], adj=alternating(23)))
    emitted = run(subject, series, [20, 21, 22], held=[(), ("SPY",), ()])

    assert subject.exit_reasons[attempt2_risk.EXIT_SIGNAL] == 1
    assert subject.exit_reasons[attempt2_risk.EXIT_LOSS_CONTROL] == 0
    assert subject.exit_reasons[attempt2_risk.EXIT_MAX_HOLD] == 0
    assert len(emitted[2]) == 1
    assert emitted[2][0].side == BUY
    assert subject.blocked_entries[attempt2_risk.NO_ENTRY_LOCKOUT] == 0


def test_lockout_blocks_entry_without_substitution():
    """RA1-6 blocks the locked-out symbol; it does not redirect the budget somewhere else.

    Same drive as the lockout test, but with the sealed two-symbol universe available. The signal
    names SPY on every locked-out session, and the candidate holds cash rather than entering SHY.
    A substitution would be an unsealed rule — the sealed target rule names one symbol per session.
    """

    subject = candidate(defensive="SHY", max_hold=1)
    series = market(
        prices("SPY", ramp(28), adj=alternating(28)),
        prices("SHY", ["50"] * 28, adj=alternating(28)),
    )
    emitted = run(subject, series, list(range(20, 28)),
                  held=[(), ("SPY",), (), (), (), (), (), ()])

    assert [len(orders) for orders in emitted] == [1, 1, 0, 0, 0, 0, 0, 1]
    assert subject.blocked_entries[attempt2_risk.NO_ENTRY_LOCKOUT] == 5
    assert not any(order.symbol == "SHY" for orders in emitted for order in orders)


def test_flat_first_emits_only_the_sell_on_a_switch():
    """The shared ``flat_first_rule``: "If it holds H and its target is T with T not equal to H, it
    emits only SELL H. It emits BUY T only on a session on which the account is already flat."

    Session 0 is flat with SPY below its average, so the target is the defensive leg and SHY is
    bought. Session 1 sees SPY gap to 200, which puts the target back on SPY while SHY is held: the
    candidate emits one order, the sale, and no purchase.
    """

    subject = candidate(defensive="SHY")
    series = market(
        prices("SPY", descending(21) + ["200"], adj=alternating(22)),
        prices("SHY", ["50"] * 22, adj=alternating(22)),
    )
    emitted = run(subject, series, [20, 21], held=[(), ("SHY",)])

    assert len(emitted[0]) == 1
    assert emitted[0][0].side == BUY and emitted[0][0].symbol == "SHY"
    assert len(emitted[1]) == 1
    assert emitted[1][0].side == SELL and emitted[1][0].symbol == "SHY"
    assert not any(order.side == BUY for order in emitted[1])
    assert subject.exit_reasons[attempt2_risk.EXIT_SIGNAL] == 1
    assert "It emits BUY T only on a session on which the account is already flat." in (
        CONFIG.shared_rule_texts["flat_first_rule"]
    )


def test_positions_are_all_or_nothing():
    """RA1-8: "Entries and exits are for the full position. No partial entry, no partial exit, no
    scaling in, no scaling out, no averaging down, no pyramiding."

    An ``OrderRequest`` cannot express a partial position under Attempt 2: the buy names a budget and
    leaves quantity to the engine, and the sell names neither, which the sealed exit path documents as
    "the engine sells all of it".
    """

    subject = candidate(defensive="SHY")
    series = market(
        prices("SPY", descending(21) + ["200"], adj=alternating(22)),
        prices("SHY", ["50"] * 22, adj=alternating(22)),
    )
    emitted = run(subject, series, [20, 21], held=[(), ("SHY",)])

    buy = emitted[0][0]
    assert buy.side == BUY and buy.budget is not None and buy.quantity is None
    sell = emitted[1][0]
    assert sell.side == SELL and sell.quantity is None and sell.budget is None
    assert RA1_BLOCK["RA1-8"]["rule"].startswith("Entries and exits are for the full position.")


def test_at_most_one_open_position_and_no_short():
    """The shared ``long_only`` rule: "No short sale, no leverage, no margin, no averaging down, no
    pyramiding. One open risky position at a time, per the sealed cost model
    max_open_risky_positions of 1."

    Structural on two counts. No decision session emits more than one order and no held session emits
    a buy, so the candidate cannot open a second position; and RA1 imports only ``BUY`` from the
    order module, so a short sale is not expressible in the sizing path at all.
    """

    assert COSTS.max_open_risky_positions == 1

    subject = candidate(defensive="SHY")
    series = market(
        prices("SPY", descending(21) + ["200"], adj=alternating(22)),
        prices("SHY", ["50"] * 22, adj=alternating(22)),
    )
    held = [(), ("SHY",)]
    emitted = run(subject, series, [20, 21], held=held)

    assert all(len(orders) <= 1 for orders in emitted)
    for position, orders in enumerate(emitted):
        if held[position]:
            assert not any(order.side == BUY for order in orders)

    imported = set()
    for node in ast.walk(ast.parse(inspect.getsource(attempt2_risk))):
        if isinstance(node, ast.ImportFrom) and node.module == "stockedge100.backtest.orders":
            imported.update(alias.name for alias in node.names)
    assert imported == {"BUY"}


# -- data and boundary handling ------------------------------------------------------------------


def test_missing_bar_for_a_target_falls_through_to_cash():
    """``missing_or_invalid_data_rule.missing_bar_for_a_target``: "If a target symbol has no visible
    bar at the decision session, it cannot be the target. C3's defensive leg falls through to cash by
    its own target_rule when SHY has no visible bar."

    SPY is below its average, so the defensive leg would be the target — but the SHY series stops one
    session short. The target resolves to ``None`` and no blocking counter moves, because this is a
    signal outcome rather than a rejected entry.
    """

    subject = candidate(defensive="SHY")
    series = market(
        prices("SPY", descending(21), adj=alternating(21)),
        prices("SHY", ["50"] * 20, adj=alternating(20)),
    )
    view = view_at(series, day(20))
    context = DecisionContext(session=day(20), cash=EQUITY, equity=EQUITY,
                             open_symbols=(), shutdown_active=False)

    assert view.has_data("SPY", day(20)) is True
    assert view.has_data("SHY", day(20)) is False
    assert subject.target(view, context) is None
    assert run(subject, series, [20]) == [[]]
    assert sum(subject.blocked_entries.values()) == 0
    assert "it cannot be the target" in CONFIG.protocol["missing_or_invalid_data_rule"][
        "missing_bar_for_a_target"
    ]


def test_defensive_leg_gets_no_carve_out():
    """RA1-1 ``applies_to_defensive_leg`` is ``true``, and ``defensive_leg_note``: "No
    instrument-specific carve-out is granted, because a per-instrument exposure exemption would be a
    discretionary rule."

    Two drives with identical volatility on whichever symbol is entered — one entering the risk leg,
    one entering the defensive leg — produce the same fraction. The source check is the structural
    half: the sizing routine names no symbol, so it cannot special-case one.
    """

    assert RA1_BLOCK["RA1-1"]["applies_to_defensive_leg"] is True
    assert "No instrument-specific carve-out is granted" in RA1_BLOCK["RA1-1"]["defensive_leg_note"]

    risk_leg = candidate(defensive="SHY")
    rising = market(
        prices("SPY", ramp(21), adj=alternating(21)),
        prices("SHY", ["50"] * 21, adj=["50"] * 21),
    )
    risk_orders = run(risk_leg, rising, [20])

    defensive_leg = candidate(defensive="SHY")
    falling = market(
        prices("SPY", descending(21), adj=["100"] * 21),
        prices("SHY", ["50"] * 21, adj=alternating(21)),
    )
    defensive_orders = run(defensive_leg, falling, [20])

    assert risk_orders[0][0].symbol == "SPY"
    assert defensive_orders[0][0].symbol == "SHY"
    assert risk_leg.entry_fractions == [RA1.f_base]
    assert defensive_leg.entry_fractions == [RA1.f_base]

    source = inspect.getsource(attempt2_risk.Ra1Candidate._entry_budget)
    assert "SPY" not in source and "SHY" not in source


def test_non_positive_adjusted_close_traps_rather_than_imputes():
    """``missing_or_invalid_data_rule``: "If it were reachable, VOL20 would be undefined under
    ENGINE_CONTEXT trapping", and ``data_repair_prohibited`` — "No price is imputed, interpolated,
    back-filled, forward-filled, winsorised, or corrected by this attempt."

    A zero adjusted close inside the 21-bar window makes one return a division by zero. The trapped
    exception propagates out of both the indicator and ``decide``: a silent repair, a shortened
    window or a quiet ``None`` would all be unsealed interpretations, and the sealed
    ``partial_or_failed_run_rule`` governs a trapped run instead.
    """

    adj = alternating(21)
    adj[5] = "0"
    series = market(prices("SPY", ramp(21), adj=adj))
    bars = [series["SPY"].bars[session] for session in series["SPY"].sessions]

    with pytest.raises(DivisionByZero):
        attempt2_indicators.vol20(bars)

    subject = candidate(defensive=None)
    with pytest.raises(DivisionByZero):
        run(subject, series, [20])

    rule = CONFIG.protocol["missing_or_invalid_data_rule"]
    assert "VOL20 would be undefined under ENGINE_CONTEXT trapping" in rule[
        "non_positive_adjusted_close"
    ]
    assert rule["data_repair_prohibited"].startswith("No price is imputed")


# -- shutdown and the Attempt 1 default ----------------------------------------------------------


def test_candidate_emits_nothing_while_shutdown_is_active():
    """``engine_shutdown_relationship.candidate_behaviour``: "A candidate emits no order on any
    decision session where context.shutdown_active is true."

    Both states are driven on the same fixture so the difference is attributable to the flag alone.
    Bookkeeping still advances — the sealed rule suppresses emission, not the state a later session
    would depend on — and ``no_candidate_reads_the_ceiling`` is checked structurally: the literal
    0.15 appears in neither module, and the sizing path never reads the shutdown flag.
    """

    series = market(prices("SPY", ramp(22), adj=alternating(22)))

    halted = candidate(defensive=None)
    assert run(halted, series, [20], shutdown=[True]) == [[]]
    assert halted.decision_sessions == 1
    assert halted.decision_sessions_shutdown_active == 1

    control = candidate(defensive=None)
    assert len(run(control, series, [20], shutdown=[False])[0]) == 1
    assert control.decision_sessions_shutdown_active == 0

    while_held = candidate(defensive=None)
    emitted = run(while_held, series, [20, 21], held=[(), ("SPY",)], shutdown=[False, True])
    assert len(emitted[0]) == 1
    assert emitted[1] == []
    assert while_held.decision_sessions_shutdown_active == 1

    assert "0.15" not in inspect.getsource(attempt2_risk)
    assert "0.15" not in inspect.getsource(attempt2_candidates)
    assert "shutdown" not in inspect.getsource(attempt2_candidates)
    assert "shutdown_active" not in inspect.getsource(attempt2_risk.Ra1Candidate._entry_budget)
    assert RA1_BLOCK["engine_shutdown_relationship"]["no_candidate_reads_the_ceiling"].startswith(
        "No RA1 rule and no candidate rule references 0.15"
    )


def test_attempt_1_entry_order_default_is_unreachable():
    """``shared_rules.replaced.sizing_rule``: Attempt 1's "fixed budget of 95% of account equity" is
    replaced by RA1-1, RA1-2 and RA1-5, "Downward only".

    The inherited method is removed rather than shadowed, so any path that reaches it says so. No
    Attempt 2 module calls it, which is the structural half of the same claim.
    """

    subject = candidate(defensive=None)
    context = DecisionContext(session=day(20), cash=EQUITY, equity=EQUITY,
                              open_symbols=(), shutdown_active=False)

    with pytest.raises(InvariantViolation) as raised:
        subject.entry_order("SPY", context)
    message = str(raised.value)
    assert "RA1-2" in message
    assert "95%" in message

    for module in (attempt2_risk, attempt2_candidates, attempt2_harness):
        for node in ast.walk(ast.parse(inspect.getsource(module))):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr != "entry_order"

    replaced = CONFIG.shared_rules["replaced"]["sizing_rule"]
    assert replaced["direction_of_change"].startswith("Downward only.")


# -- the sealed refusal list ----------------------------------------------------------------------


def test_each_incoherent_combination_is_refused():
    """``binding.admissible_candidate_exists.incoherent_combinations_refused``, all five entries.

    Refusals 1, 2 and 3 are checkable against the list itself and each gets one injected defect.
    Refusal 4 — a PASS reached by aggregating rollup rows instead of evaluating conjunction within a
    candidate — is prevented by construction, so what is injected here is the property that error
    would violate: a candidate marked admitted while one of its own conditions is unsatisfied, and
    the mirror case of a candidate marked not admitted while all of them are. Refusal 5 — a verdict
    written into a package the evidence does not reach — belongs to the decision-package builder's
    guard, not to this harness, and is not exercised here.

    The clean control comes first so a failure below it is attributable to the injected defect.
    """

    rule = CONFIG.binding["admissible_candidate_exists"]
    refused = rule["incoherent_combinations_refused"]
    assert len(refused) == 5

    satisfied = [condition_row(f"S3-C{index}", gate.MET) for index in range(1, 8)]

    def stage(verdict: str, admitted: list[str]) -> dict:
        return {"verdict": verdict, "admitted_candidates": admitted, "candidates_evaluated": 1}

    def entry(admitted: bool, conditions=None) -> dict:
        return {
            "experiment_id": attempt2_candidates.C1,
            "admitted": admitted,
            "conditions": satisfied if conditions is None else conditions,
        }

    # Control: coherent evidence and a coherent verdict.
    attempt2_harness._refuse_incoherent(
        stage("PASS", [attempt2_candidates.C1]), [entry(True)], CONFIG.binding
    )

    # 1. A PASS with zero admissible candidates.
    unsatisfied = [condition_row("S3-C1", gate.NOT_MET)] + satisfied[1:]
    with pytest.raises(ConfigViolation) as first:
        attempt2_harness._refuse_incoherent(
            stage("PASS", []), [entry(False, unsatisfied)], CONFIG.binding
        )
    assert refused[0] in str(first.value)

    # 2. A FAIL with at least one admissible candidate.
    with pytest.raises(ConfigViolation) as second:
        attempt2_harness._refuse_incoherent(
            stage("FAIL", [attempt2_candidates.C1]), [entry(True)], CONFIG.binding
        )
    assert refused[1] in str(second.value)

    # 3. A PASS reached by treating a non-satisfied verdict as satisfied.
    for verdict in (gate.NOT_MET, gate.NOT_EVALUABLE):
        rows = satisfied[:6] + [condition_row("S3-C7", verdict)]
        with pytest.raises(ConfigViolation) as third:
            attempt2_harness._refuse_incoherent(
                stage("PASS", [attempt2_candidates.C1]), [entry(True, rows)], CONFIG.binding
            )
        assert refused[2] in str(third.value)

    # 4's property, in both directions: the candidate flag must equal its own conjunction.
    with pytest.raises(ConfigViolation) as fourth:
        attempt2_harness._refuse_incoherent(
            stage("FAIL", []), [entry(False)], CONFIG.binding
        )
    assert rule["within_candidate"] in str(fourth.value)

    # And a satisfied flag that disagrees with the sealed satisfied_definition.
    tampered = dict(satisfied[0])
    tampered["satisfied"] = False
    with pytest.raises(ConfigViolation) as fifth:
        attempt2_harness._refuse_incoherent(
            stage("FAIL", []), [entry(False, [tampered] + satisfied[1:])], CONFIG.binding
        )
    assert rule["satisfied_definition"] in str(fifth.value)
