"""The five sealed indicators, computed in exact decimal arithmetic.

Each function is a transcription of one entry in ``indicator_definitions`` of
``config/stage3_strategy_protocol.json``. The sealed text is quoted in each docstring so that a
reader can check the code against the seal without holding two files open, and so that a later
divergence between the two is visible on one screen.

Two properties are structural rather than incidental:

* **No float appears anywhere in a signal path.** Every intermediate is a :class:`~decimal.Decimal`
  evaluated under ``ENGINE_CONTEXT`` via the ``@exact`` decorator, the same context the cost model
  and the engine use.
* **An indicator that cannot be computed returns ``None``**, never a substituted value, never a
  shortened window. The sealed ``insufficient_history_rule`` then applies at the call site: "If any
  indicator a rule requires cannot be computed from the visible history, the target for that session
  is cash." Returning a best-effort number instead would silently convert a warm-up shortfall into a
  trading signal.

Every function takes ``bars`` oldest-first, ending at the decision session *t*. Slicing from the end
is therefore always slicing the most recent history.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Sequence

from stockedge100.backtest.costs import ZERO, exact
from stockedge100.backtest.dataset import Bar

ONE = Decimal(1)
HUNDRED = Decimal(100)
FIFTY = Decimal(50)


@exact
def sma(bars: Sequence[Bar], n: int) -> Decimal | None:
    """``SMA(n)(t)`` — "the arithmetic mean of the last n visible closes including the close at t.

    Undefined, and therefore not tradable, if fewer than n visible bars exist."
    """

    if n <= 0 or len(bars) < n:
        return None
    window = bars[-n:]
    total = ZERO
    for bar in window:
        total += bar.close
    return total / Decimal(n)


@exact
def rolling_max_close(bars: Sequence[Bar], n: int) -> Decimal | None:
    """``ROLLING_MAX(n)(t)`` / ``MAXCLOSE(n)(t)`` — "the largest close among the last n visible bars,
    the bar at t included."
    """

    if n <= 0 or len(bars) < n:
        return None
    return max(bar.close for bar in bars[-n:])


@exact
def rolling_min_close(bars: Sequence[Bar], n: int) -> Decimal | None:
    """``ROLLING_MIN(n)(t)`` / ``MINCLOSE(n)(t)`` — "the smallest close among the last n visible bars,
    the bar at t included."
    """

    if n <= 0 or len(bars) < n:
        return None
    return min(bar.close for bar in bars[-n:])


@exact
def momentum(bars: Sequence[Bar], n: int) -> Decimal | None:
    """``MOM(n)(t) = adj_close(t) / adj_close(t-n) - 1``, "where t-n is the n-th visible bar before t.

    Undefined if fewer than n+1 visible bars exist."

    ``adj_close`` rather than ``close`` is what the seal says, and it is the right column: a
    momentum ranking compares total-return paths across instruments, so the dividend-inclusive
    series is the one being ranked.
    """

    if n <= 0 or len(bars) < n + 1:
        return None
    past = bars[-(n + 1)].adj_close
    if past == ZERO:
        return None
    return bars[-1].adj_close / past - ONE


@exact
def wilder_rsi(bars: Sequence[Bar], period: int, warmup_changes: int) -> Decimal | None:
    """``RSI(period)(t)`` by Wilder's smoothing, over exactly ``warmup_changes`` price changes.

    The sealed procedure, followed step for step:

    1. "Take the last ``warmup_changes + 1`` visible closes ending at t, oldest first: c[0] .. c[W]
       where W = warmup_changes. Undefined if fewer exist."
    2. "For i in 1..W: gain[i] = max(c[i] - c[i-1], 0); loss[i] = max(c[i-1] - c[i], 0)."
    3. "Seed: avgGain = mean(gain[1..p]), avgLoss = mean(loss[1..p]) where p = period."
    4. "For i in p+1..W: avgGain = (avgGain * (p-1) + gain[i]) / p; avgLoss likewise."
    5. "If avgLoss == 0 and avgGain > 0, RSI = 100. If both are 0, RSI = 50. Otherwise
       RSI = 100 - 100 / (1 + avgGain / avgLoss)."

    A fixed ``warmup_changes`` is what makes the value path-independent: Wilder's average is an
    infinite-memory recursion, so an RSI seeded at a run's first bar and one seeded ten years
    earlier are different numbers. Pinning the seeding distance makes ``RSI(2)`` at a given session
    the same value in every run that reaches that session.
    """

    window = warmup_changes
    if period <= 0 or window < period or len(bars) < window + 1:
        return None
    closes = [bar.close for bar in bars[-(window + 1) :]]

    gains: list[Decimal] = [ZERO]
    losses: list[Decimal] = [ZERO]
    for i in range(1, window + 1):
        change = closes[i] - closes[i - 1]
        gains.append(change if change > ZERO else ZERO)
        losses.append(-change if change < ZERO else ZERO)

    p = Decimal(period)
    avg_gain = ZERO
    avg_loss = ZERO
    for i in range(1, period + 1):
        avg_gain += gains[i]
        avg_loss += losses[i]
    avg_gain /= p
    avg_loss /= p

    for i in range(period + 1, window + 1):
        avg_gain = (avg_gain * (p - ONE) + gains[i]) / p
        avg_loss = (avg_loss * (p - ONE) + losses[i]) / p

    if avg_loss == ZERO:
        return HUNDRED if avg_gain > ZERO else FIFTY
    return HUNDRED - HUNDRED / (ONE + avg_gain / avg_loss)
