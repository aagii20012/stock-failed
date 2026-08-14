"""Benchmarks, and the reconciliation that makes one of them a test rather than a report line.

SPY total return is computed two ways that *must* agree exactly, and the reason they must is worth
being precise about, because it is the difference between a real check and a tolerance chosen to make
a check pass.

Stage 1 measured the provider's adjustment convention:

    adj_t = close_t · Π over later ex-dates s of (1 − D_s / close_{s−1})

Method A takes the ratio of two adjusted closes. Method B accumulates shares explicitly, buying more
at each ex-date. Ask what reinvestment price makes B reproduce A, and the algebra answers:

    shares ← shares · close_{s−1} / (close_{s−1} − D_s)   ⇒   reinvest at close_{s−1} − D_s

That is not a modelling choice and it was not fitted; it is forced. So the two methods are an
arithmetic identity over any window, and any disagreement between them is a defect in the engine or
in the data. The 1e-6 relative tolerance in the sealed config is there to absorb nothing more than
decimal representation, and in practice the two agree to far more digits than that.

Note also that the adjustment factors for ex-dates *after* the window end appear in both adjusted
closes and cancel in the ratio, so the identity holds on a sub-window of the series and not only on
the whole of it.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from stockedge100.backtest.costs import BASE, CostModel, ZERO, exact
from stockedge100.backtest.dataset import PriceSeries
from stockedge100.backtest.engine import BacktestEngine, BacktestResult
from stockedge100.backtest.errors import InvariantViolation
from stockedge100.backtest.probes import BuyAndHoldProbe
from stockedge100.backtest.window import ResearchWindow

ONE = Decimal(1)


@dataclass(frozen=True)
class SpyTotalReturn:
    start_session: dt.date
    end_session: dt.date
    start_close: Decimal
    end_close: Decimal
    start_adj_close: Decimal
    end_adj_close: Decimal
    dividend_count: int
    final_shares: Decimal
    method_a: Decimal
    method_b: Decimal

    @property
    @exact
    def relative_difference(self) -> Decimal:
        scale = abs(self.method_a)
        if scale == ZERO:
            return abs(self.method_b)
        return abs(self.method_a - self.method_b) / scale

    def reconciles(self, tolerance: Decimal) -> bool:
        return self.relative_difference <= tolerance

    def to_json(self) -> dict[str, Any]:
        return {
            "symbol": "SPY",
            "start_session": self.start_session.isoformat(),
            "end_session": self.end_session.isoformat(),
            "start_close": f"{self.start_close:f}",
            "end_close": f"{self.end_close:f}",
            "start_adj_close": f"{self.start_adj_close:f}",
            "end_adj_close": f"{self.end_adj_close:f}",
            "dividend_count": self.dividend_count,
            "final_shares_per_one_initial": f"{self.final_shares:f}",
            "method_a_adj_close_ratio": f"{self.method_a:f}",
            "method_b_explicit_reinvestment": f"{self.method_b:f}",
            "relative_difference": f"{self.relative_difference:E}",
        }


@exact
def spy_total_return(series: PriceSeries, window: ResearchWindow) -> SpyTotalReturn:
    """Both methods over the window's visible sessions, computed independently of each other."""
    sessions = [day for day in series.sessions if window.contains(day)]
    if len(sessions) < 2:
        raise InvariantViolation(
            f"{series.symbol}: {len(sessions)} session(s) inside {window.name}; a total return needs "
            "at least two"
        )
    start, end = sessions[0], sessions[-1]
    first, last = series.bars[start], series.bars[end]

    if first.adj_close <= ZERO or last.adj_close <= ZERO:
        raise InvariantViolation(f"{series.symbol}: non-positive adjusted close at a window boundary")

    method_a = last.adj_close / first.adj_close - ONE

    # Method B never consults an adjusted close. If it did, the reconciliation would be comparing a
    # number with itself.
    shares = ONE
    dividends = 0
    for session in sessions[1:]:
        bar = series.bars[session]
        if not bar.has_dividend:
            continue
        previous = series.prior_session(session)
        if previous is None:
            raise InvariantViolation(
                f"{series.symbol}: dividend on {session.isoformat()} has no prior session to price "
                "the reinvestment against"
            )
        prior_close = series.bars[previous].close
        price = prior_close - bar.dividend
        if price <= ZERO:
            raise InvariantViolation(
                f"{series.symbol} {session.isoformat()}: dividend {bar.dividend} is not less than the "
                f"prior close {prior_close}; the reinvestment price would be non-positive"
            )
        shares = shares * prior_close / price
        dividends += 1

    method_b = shares * last.close / first.close - ONE

    return SpyTotalReturn(
        start_session=start,
        end_session=end,
        start_close=first.close,
        end_close=last.close,
        start_adj_close=first.adj_close,
        end_adj_close=last.adj_close,
        dividend_count=dividends,
        final_shares=shares,
        method_a=method_a,
        method_b=method_b,
    )


@dataclass(frozen=True)
class FlatBenchmark:
    """A benchmark that does nothing, and returns exactly nothing for doing it."""

    name: str
    annual_rate: Decimal
    sessions: int
    total_return: Decimal
    trades: int
    note: str

    def to_json(self) -> dict[str, Any]:
        return {
            "benchmark": self.name,
            "annual_rate": f"{self.annual_rate:f}",
            "sessions": self.sessions,
            "total_return": f"{self.total_return:f}",
            "trades": self.trades,
            "note": self.note,
        }


def cash_benchmark(sessions: int, annual_rate: Decimal) -> FlatBenchmark:
    if annual_rate != ZERO:
        raise InvariantViolation(
            f"the sealed cash benchmark rate is 0.00; got {annual_rate}. A non-zero rate needs a "
            "point-in-time Treasury series, which Stage 1 did not acquire."
        )
    return FlatBenchmark(
        name="CASH",
        annual_rate=annual_rate,
        sessions=sessions,
        total_return=ZERO,
        trades=0,
        note=(
            "0% conservative proxy: no T-bill series was acquired in Stage 1. This makes the cash "
            "hurdle easier to beat, so it is conservative for judging cash and generous for judging "
            "a strategy."
        ),
    )


def do_nothing_benchmark(sessions: int) -> FlatBenchmark:
    return FlatBenchmark(
        name="DO_NOTHING",
        annual_rate=ZERO,
        sessions=sessions,
        total_return=ZERO,
        trades=0,
        note="Flat equity at starting capital, zero trades, zero costs.",
    )


def tradable_spy_buy_and_hold(
    series: dict[str, PriceSeries],
    cost_model: CostModel,
    window: ResearchWindow,
    *,
    start: dt.date | None = None,
    end: dt.date | None = None,
    enforce_research_shutdown: bool = True,
) -> BacktestResult:
    """A real account buying SPY once and holding it, under the full cost model.

    Reported next to the index figure and never confused with it: this one pays a spread, a
    commission, and the rounding, and it starts a session late because a decision at a close fills at
    the next open.

    ``enforce_research_shutdown`` exists because the sealed rule set contains a 15% research shutdown
    that a 28-year hold of SPY does trip, in August 1998. Both variants are run and both are
    reported; see :func:`stockedge100.backtest.harness.benchmark_evidence`.
    """
    if "SPY" not in series:
        raise InvariantViolation("SPY is not loaded; the tradable benchmark cannot run")
    suffix = "" if enforce_research_shutdown else "_NO_SHUTDOWN"
    probe = BuyAndHoldProbe("SPY", cost_model.starting_equity)
    engine = BacktestEngine(
        {"SPY": series["SPY"]},
        cost_model,
        window,
        probe,
        start=start,
        end=end,
        label=f"BENCHMARK_TRADABLE_SPY_BUY_AND_HOLD{suffix}",
        enforce_research_shutdown=enforce_research_shutdown,
    )
    return engine.run()
