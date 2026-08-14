"""Performance metrics, computed exactly and reported honestly.

Two decisions here are worth stating rather than burying.

**Profit factor with no losing trades is reported as ``None``.** Not infinity, not a large number,
not the sum of profits. The sealed cost model requires this, and the reason is that "profit factor
9999" reads like a measurement when it is really a division by zero wearing a number's clothes.

**Sharpe uses a 0% risk-free rate**, because Stage 1 acquired no Treasury-bill series and the
constitution permits the 0% proxy when point-in-time data are unavailable. This flatters a strategy
and penalises cash; the direction of the bias is recorded here and in the report rather than left
for a reader to work out.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Any, Sequence

from stockedge100.backtest.costs import ZERO, exact
from stockedge100.backtest.errors import InvariantViolation

ONE = Decimal(1)
DAYS_PER_YEAR = Decimal("365.25")


@exact
def total_return(start_equity: Decimal, end_equity: Decimal) -> Decimal:
    if start_equity <= ZERO:
        raise InvariantViolation(f"starting equity must be positive, got {start_equity}")
    return end_equity / start_equity - ONE


@exact
def daily_returns(equity: Sequence[Decimal]) -> list[Decimal]:
    out: list[Decimal] = []
    for previous, current in zip(equity, equity[1:]):
        if previous <= ZERO:
            raise InvariantViolation("equity reached zero; a return is undefined from there")
        out.append(current / previous - ONE)
    return out


@exact
def cagr(start_equity: Decimal, end_equity: Decimal, start: dt.date, end: dt.date) -> Decimal | None:
    """Compound annual growth rate over calendar time.

    Returns ``None`` for a window shorter than a day rather than annualising a few sessions into a
    number that would be quoted as if it meant something.
    """
    days = Decimal((end - start).days)
    if days <= ZERO:
        return None
    if start_equity <= ZERO or end_equity <= ZERO:
        return None
    years = days / DAYS_PER_YEAR
    return ((end_equity / start_equity).ln() / years).exp() - ONE


@exact
def max_drawdown(equity: Sequence[Decimal]) -> Decimal:
    """Largest peak-to-trough fall in marked equity, as a non-negative fraction."""
    if not equity:
        return ZERO
    peak = equity[0]
    worst = ZERO
    for value in equity:
        if value > peak:
            peak = value
        if peak > ZERO:
            fall = (peak - value) / peak
            if fall > worst:
                worst = fall
    return worst


@exact
def stdev(values: Sequence[Decimal]) -> Decimal | None:
    """Sample standard deviation. ``None`` below two observations."""
    n = len(values)
    if n < 2:
        return None
    mean = sum(values, ZERO) / Decimal(n)
    variance = sum(((v - mean) ** 2 for v in values), ZERO) / Decimal(n - 1)
    return variance.sqrt()


@exact
def sharpe(returns: Sequence[Decimal], *, trading_days: int, risk_free_annual: Decimal) -> Decimal | None:
    """Annualised Sharpe ratio of daily equity returns.

    ``None`` when there are too few observations or the returns never move — a constant series has
    zero volatility, and the ratio is undefined rather than infinite.
    """
    if len(returns) < 2:
        return None
    sigma = stdev(returns)
    if sigma is None or sigma == ZERO:
        return None
    periods = Decimal(trading_days)
    daily_rf = risk_free_annual / periods
    mean = sum(returns, ZERO) / Decimal(len(returns))
    return (mean - daily_rf) / sigma * periods.sqrt()


def profit_factor(pnls: Sequence[Decimal]) -> Decimal | None:
    """Gross profit over gross loss across closed round trips.

    ``None`` when there are no losing trades, per the sealed model. Also ``None`` when there are no
    trades at all: nothing divided by nothing is not 1.
    """
    if not pnls:
        return None
    gross_profit = sum((p for p in pnls if p > ZERO), ZERO)
    gross_loss = -sum((p for p in pnls if p < ZERO), ZERO)
    if gross_loss == ZERO:
        return None
    return gross_profit / gross_loss


@exact
def exposure_fraction(position_counts: Sequence[int]) -> Decimal:
    """Fraction of sessions with any position open."""
    if not position_counts:
        return ZERO
    invested = sum(1 for count in position_counts if count > 0)
    return Decimal(invested) / Decimal(len(position_counts))


def summarize(
    *,
    sessions: Sequence[dt.date],
    equity: Sequence[Decimal],
    position_counts: Sequence[int],
    trade_pnls: Sequence[Decimal],
    trading_days: int,
    risk_free_annual: Decimal,
) -> dict[str, Any]:
    """Every reported metric for one run, with ``None`` wherever a value is genuinely undefined."""
    if len(sessions) != len(equity) or len(sessions) != len(position_counts):
        raise InvariantViolation("sessions, equity, and position counts must be the same length")
    if not sessions:
        raise InvariantViolation("cannot summarise an empty equity curve")

    returns = daily_returns(equity)
    annual = cagr(equity[0], equity[-1], sessions[0], sessions[-1])
    ratio = sharpe(returns, trading_days=trading_days, risk_free_annual=risk_free_annual)
    factor = profit_factor(trade_pnls)
    volatility = stdev(returns)

    def text(value: Decimal | None) -> str | None:
        return None if value is None else f"{value:f}"

    return {
        "sessions": len(sessions),
        "start_session": sessions[0].isoformat(),
        "end_session": sessions[-1].isoformat(),
        "start_equity": f"{equity[0]:f}",
        "end_equity": f"{equity[-1]:f}",
        "total_return": text(total_return(equity[0], equity[-1])),
        "cagr": text(annual),
        "max_drawdown": text(max_drawdown(equity)),
        "daily_return_stdev": text(volatility),
        "sharpe": text(ratio),
        "sharpe_risk_free_annual": f"{risk_free_annual:f}",
        "profit_factor": text(factor),
        "profit_factor_note": (
            None if factor is not None else "undefined: no losing closed trade in this run"
        ),
        "closed_trades": len(trade_pnls),
        "exposure_fraction": f"{exposure_fraction(position_counts):f}",
    }
