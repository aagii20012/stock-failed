"""Pure signal logic for the Faber sector rotation, extracted for live use.

This is the same rule set as ``faber_sector_rotation.py`` (LEAN) and
``local_backtest.py`` (pandas harness), verified identical over 236 rebalances
at tag ``baseline-v1-faber-verified``:

    top-3 of 9 SPDR sector ETFs by 12-month momentum, each slot held only while
    that sector's last completed monthly close is above its own 10-month SMA;
    a slot failing the trend test is routed to SHY.

No network, no broker, no clock of its own -- everything comes in as arguments
so ``test_signal_parity.py`` can replay the tagged decision log through it.
Nothing in here may change without re-running that parity test.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional

import pandas as pd

SECTORS = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB"]
DEFENSIVE = "SHY"
UNIVERSE = SECTORS + [DEFENSIVE]

TOP_N = 3
MOM_LOOKBACK = 12   # completed monthly bars
SMA_LENGTH = 10     # completed monthly bars

# Monthly bars the signal needs: 12 back plus the signal month itself.
REQUIRED_MONTHS = MOM_LOOKBACK + 1


@dataclass
class Decision:
    """One rebalance decision. ``weights`` is what the broker should hold."""

    signal_month: str                       # last completed month, e.g. "2026-07"
    weights: dict = field(default_factory=dict)
    ranked: list = field(default_factory=list)      # top-N by momentum, best first
    skipped: list = field(default_factory=list)     # of ``ranked``, below own SMA
    momentum: dict = field(default_factory=dict)    # every sector, for the log
    trend_ok: dict = field(default_factory=dict)    # every sector, close > SMA
    reason: str = ""                                # set only when weights is empty

    @property
    def fully_defensive(self) -> bool:
        return len(self.skipped) == TOP_N

    def to_dict(self) -> dict:
        d = asdict(self)
        d["fully_defensive"] = self.fully_defensive
        return d


def completed_monthly_closes(
    daily: pd.DataFrame, asof: pd.Timestamp
) -> Optional[pd.DataFrame]:
    """Monthly closes strictly before ``asof``'s month, trimmed to what we need.

    The in-progress month is dropped: its "close" is one or two days old and
    would corrupt both the momentum ratio and the SMA. This is the step that
    makes the signal look-ahead free.

    Deviation from LEAN, deliberate: LEAN calls ``dropna(axis=1, how="any")``
    over its whole ~18-month history window, so one missing day in a partial
    edge month silently deletes that entire symbol from the ranking. Here the
    frame is trimmed to the 13 months actually used *before* dropping columns,
    so a gap outside the signal window cannot disqualify a sector. With complete
    data the two are identical -- proven over all 236 months of the tagged log.
    """
    if daily.empty:
        return None

    monthly = daily.groupby(daily.index.to_period("M")).last()
    monthly = monthly[monthly.index < pd.Period(asof, freq="M")]
    if len(monthly) < REQUIRED_MONTHS:
        return None

    monthly = monthly.iloc[-REQUIRED_MONTHS:]
    monthly = monthly.dropna(axis=1, how="any")
    return monthly


def decide(daily: pd.DataFrame, asof: pd.Timestamp) -> Decision:
    """Target weights as of ``asof``, from daily closes.

    ``asof`` is the rebalance date -- the first trading day of the month, which
    is when LEAN's ``date_rules.month_start`` fires. The signal itself only ever
    reads months that closed before it.
    """
    monthly = completed_monthly_closes(daily, asof)
    if monthly is None:
        return Decision(
            signal_month=str(pd.Period(asof, freq="M") - 1),
            reason=f"need {REQUIRED_MONTHS} completed monthly closes, have too few",
        )

    signal_month = str(monthly.index[-1])

    last = monthly.iloc[-1]
    momentum = last / monthly.iloc[-(MOM_LOOKBACK + 1)] - 1.0
    sma = monthly.iloc[-SMA_LENGTH:].mean()

    if DEFENSIVE not in monthly.columns:
        return Decision(
            signal_month=signal_month,
            reason=f"{DEFENSIVE} has no usable monthly history; cannot route skips",
        )

    # Stable sort over SECTORS order, matching both reference implementations:
    # equal momentum keeps the declared sector order rather than an arbitrary one.
    ranked_all = [s for s in SECTORS if s in momentum.index]
    if len(ranked_all) < TOP_N:
        return Decision(
            signal_month=signal_month,
            reason=f"only {len(ranked_all)} sectors have usable history, need {TOP_N}",
        )
    ranked_all.sort(key=lambda s: momentum[s], reverse=True)
    ranked = ranked_all[:TOP_N]

    slot_weight = 1.0 / TOP_N
    weights: dict = {}
    skipped: list = []

    for symbol in ranked:
        if last[symbol] > sma[symbol]:
            weights[symbol] = weights.get(symbol, 0.0) + slot_weight
        else:
            weights[DEFENSIVE] = weights.get(DEFENSIVE, 0.0) + slot_weight
            skipped.append(symbol)

    return Decision(
        signal_month=signal_month,
        weights=weights,
        ranked=ranked,
        skipped=skipped,
        momentum={s: round(float(momentum[s]), 6) for s in ranked_all},
        trend_ok={s: bool(last[s] > sma[s]) for s in ranked_all},
    )
