"""VOL20 — the one indicator Attempt 2 adds, computed in exact decimal arithmetic.

Attempt 2 adopts SMA and RSI from SE100-CFG-3001 unchanged; those live in
:mod:`stockedge100.strategies.indicators` and are imported, not re-implemented. A second copy of a
sealed indicator is eventually the copy that is wrong. ROLLING_MAX, ROLLING_MIN and MOMENTUM are
recorded in the seal as ``not_used_by_attempt_2`` and are never called from Attempt 2 code.

The sealed ``purpose`` bounds what this file may be used for: "It is an input to position sizing
only. It never selects a symbol, never generates an entry, and never generates an exit." Nothing in
:mod:`stockedge100.strategies.attempt2_candidates` reads VOL20 in a ``target`` computation.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Sequence

from stockedge100.backtest.costs import ZERO, exact
from stockedge100.backtest.dataset import Bar

ONE = Decimal(1)

#: Step 1 of the sealed procedure: 21 visible bars yield the 20 returns of steps 2–4.
VOL20_BARS = 21
#: Step 2–4 denominators, fixed by the seal: 20 returns, sample variance over 19.
VOL20_RETURNS = 20
VOL20_VARIANCE_DENOMINATOR = 19
#: Step 6, the annualisation factor. 252 is the sealed ``metrics.trading_days_per_year``.
TRADING_DAYS_PER_YEAR = 252


@exact
def vol20(bars: Sequence[Bar]) -> Decimal | None:
    """``VOL20(s)`` at session *t* — "the annualised standard deviation of the 20 most recent simple
    daily total returns of symbol s."

    The sealed procedure, followed step for step:

    1. "Take the last 21 visible adj_close values of s, a[0..20], oldest first. Undefined if fewer
       than 21 visible bars exist."
    2. "For i = 1..20: r[i] = a[i] / a[i-1] - 1."
    3. "mean = (sum of r[1..20]) / 20."
    4. "var = (sum over i = 1..20 of (r[i] - mean) squared) / 19."
    5. "sigma_daily = var.sqrt()."
    6. "VOL20 = sigma_daily * Decimal(252).sqrt()."

    Three sealed notes govern the details, and each is a choice that was fixed before any Attempt 2
    number existed rather than after:

    * ``denominator_note`` — "The sample variance denominator is 19, fixed here so that the choice
      between 19 and 20 cannot be made after seeing a result."
    * ``price_series_note`` — ``adj_close`` is used, not ``close``, "because VOL20 estimates a
      total-return volatility".
    * ``insufficient_history_case`` — fewer than 21 visible bars leaves VOL20 undefined, and the
      shared ``insufficient_history_rule`` then applies at the call site: the target for that session
      is cash. This function returns ``None``; it never shortens the window.

    A zero ``a[i-1]`` is deliberately not special-cased. The seal's only zero rule is ``zero_case``,
    which is about VOL20 itself being zero, and it states the posture for the other divisions too:
    "ENGINE_CONTEXT traps DivisionByZero rather than producing an infinity." A non-positive adjusted
    close is a data defect, and a trapped run is the honest outcome under
    ``partial_or_failed_run_rule``. Adding an unsealed ``None`` branch here would be choosing an
    interpretation the protocol did not pre-register.
    """

    if len(bars) < VOL20_BARS:
        return None
    prices = [bar.adj_close for bar in bars[-VOL20_BARS:]]

    returns: list[Decimal] = []
    for i in range(1, VOL20_BARS):
        returns.append(prices[i] / prices[i - 1] - ONE)

    total = ZERO
    for value in returns:
        total += value
    mean = total / Decimal(VOL20_RETURNS)

    squares = ZERO
    for value in returns:
        deviation = value - mean
        squares += deviation * deviation
    variance = squares / Decimal(VOL20_VARIANCE_DENOMINATOR)

    sigma_daily = variance.sqrt()
    return sigma_daily * Decimal(TRADING_DAYS_PER_YEAR).sqrt()
