"""The four sealed benchmarks, computed over each candidate's own run window.

Sealed ``benchmarks.beating_spy_not_mandatory``: "Neither benchmark is a Gate 3 hard condition; both
are reported for every candidate." So nothing here feeds :mod:`stockedge100.strategies.gate` — these
numbers are context for a reader, and the seven conditions are decided without them.

Each candidate has its own run start, so each gets its own benchmark window. Comparing F5 — which
starts in 2003 because EFA's history binds its 316-session warm-up — against a SPY figure measured
from 1993 would be comparing a rule against a different decade, which is the same error the sealed
neighbour rule avoids by holding every variant of a candidate to one window.

Everything below reuses the Gate 2 validated calculations rather than reimplementing them:
:func:`stockedge100.backtest.benchmarks.spy_total_return`, which reconciles two independent methods
to 1e-6, and :func:`~stockedge100.backtest.benchmarks.tradable_spy_buy_and_hold`, which pays the
same base cost model the candidates pay.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Any

from stockedge100.backtest import benchmarks as bm
from stockedge100.backtest.costs import CostModel, ZERO
from stockedge100.backtest.dataset import PriceSeries
from stockedge100.backtest.errors import InvariantViolation
from stockedge100.backtest.window import ResearchWindow
from stockedge100.strategies.runner import CandidatePlan

BENCHMARK_SYMBOL = "SPY"


def candidate_window(plan: CandidatePlan, window: ResearchWindow) -> ResearchWindow:
    """The candidate's run span as a window object, for the index calculation only.

    This narrower window is never handed to a :class:`BacktestEngine`. Doing so would truncate the
    warm-up history the run start exists to guarantee; see the module docstring of
    :mod:`stockedge100.strategies.runner`. It is used solely by ``spy_total_return``, which reads a
    price series directly and takes the window as the span to measure over.
    """

    if not (window.contains(plan.run_start) and window.contains(plan.run_end)):
        raise InvariantViolation(
            f"{plan.experiment_id}: run span {plan.run_start}..{plan.run_end} is not inside "
            f"{window.name} {window.start}..{window.end}"
        )
    return ResearchWindow(
        name=f"{window.name}@{plan.experiment_id}", start=plan.run_start, end=plan.run_end
    )


def _tradable(
    series: dict[str, PriceSeries],
    costs: CostModel,
    window: ResearchWindow,
    plan: CandidatePlan,
    *,
    enforce_research_shutdown: bool,
) -> dict[str, Any]:
    result = bm.tradable_spy_buy_and_hold(
        series,
        costs,
        window,
        start=plan.run_start,
        end=plan.run_end,
        enforce_research_shutdown=enforce_research_shutdown,
    )
    return {
        "label": result.label,
        "start": result.start.isoformat(),
        "end": result.end.isoformat(),
        "sessions": len(result.equity_curve),
        "total_return": f"{result.total_return():f}",
        "final_equity": f"{result.final_equity:f}",
        "fills": len(result.fills),
        "closed_trades": len(result.trades),
        "research_shutdown_session": (
            None if result.shutdown_session is None else result.shutdown_session.isoformat()
        ),
        "open_positions_at_end": len(result.open_positions),
    }


def candidate_benchmarks(
    plan: CandidatePlan,
    series: dict[str, PriceSeries],
    costs: CostModel,
    window: ResearchWindow,
    cost_model_raw: dict[str, Any],
    sealed_benchmarks: dict[str, str],
    tolerance: Decimal,
) -> dict[str, Any]:
    """All four sealed benchmarks over one candidate's run window."""

    if BENCHMARK_SYMBOL not in series:
        raise InvariantViolation("SPY is not loaded; the sealed benchmarks cannot be computed")

    span = candidate_window(plan, window)
    index = bm.spy_total_return(series[BENCHMARK_SYMBOL], span)
    sessions = len([day for day in series[BENCHMARK_SYMBOL].sessions if span.contains(day)])
    rate = Decimal(str(cost_model_raw["benchmarks"]["cash_benchmark_annual_rate"]))
    cash = bm.cash_benchmark(sessions, rate)
    nothing = bm.do_nothing_benchmark(sessions)

    return {
        "note": sealed_benchmarks["beating_spy_not_mandatory"],
        "gating": False,
        "window": span.to_json(),
        "spy_total_return": {
            "declared": sealed_benchmarks["spy_total_return"],
            **index.to_json(),
            "relative_tolerance": f"{tolerance:f}",
            "reconciles": index.reconciles(tolerance),
        },
        "spy_tradable_buy_and_hold": {
            "declared": sealed_benchmarks["spy_tradable_buy_and_hold"],
            "reference_account_not_an_index": True,
            "with_research_shutdown": _tradable(
                series, costs, window, plan, enforce_research_shutdown=True
            ),
            "without_research_shutdown": _tradable(
                series, costs, window, plan, enforce_research_shutdown=False
            ),
        },
        "cash": {"declared": sealed_benchmarks["cash"], **cash.to_json()},
        "do_nothing": {"declared": sealed_benchmarks["do_nothing"], **nothing.to_json()},
    }


def comparison(candidate_measure: dict[str, Any], benchmarks: dict[str, Any]) -> dict[str, Any]:
    """How the candidate sits against each benchmark. Reported, never gating.

    The constitution's §4 sentence — "beating SPY is not mandatory if a strategy materially reduces
    drawdown, but passing requires positive after-cost performance and better risk-adjusted
    performance than cash" — is quoted in the sealed benchmark block, and the two clauses it makes
    gating (positive after-cost return, and beating a 0.00% cash rate) are already S3-C1. So these
    fields add information without adding a threshold.
    """

    total = Decimal(candidate_measure["total_return"])
    index = Decimal(benchmarks["spy_total_return"]["method_a_adj_close_ratio"])
    tradable = Decimal(
        benchmarks["spy_tradable_buy_and_hold"]["with_research_shutdown"]["total_return"]
    )
    return {
        "candidate_total_return": f"{total:f}",
        "spy_index_total_return": f"{index:f}",
        "spy_tradable_total_return": f"{tradable:f}",
        "beats_spy_index": total > index,
        "beats_spy_tradable_with_shutdown": total > tradable,
        "beats_cash_zero_percent": total > ZERO,
        "beats_do_nothing": total > ZERO,
        "candidate_max_drawdown": candidate_measure["max_drawdown"],
        "gating": False,
    }
