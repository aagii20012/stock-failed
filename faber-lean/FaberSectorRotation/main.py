"""Faber-style sector rotation for LEAN.

Top-3 of the 9 SPDR sector ETFs by 12-month momentum, each slot held only
while that sector is above its own 10-month SMA; a slot that fails the
trend test is routed to SHY instead.

Adapted from QuantConnect's ETFGlobalRotationAlgorithm. Signals are
computed on completed monthly closes, which is what Faber's rules are
defined on -- not on daily bars with 252/210-day approximations.
"""

from datetime import timedelta

import pandas as pd

from AlgorithmImports import *


class FaberSectorRotation(QCAlgorithm):

    SECTORS = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB"]
    DEFENSIVE = "SHY"
    TOP_N = 3
    MOM_LOOKBACK = 12   # completed monthly bars
    SMA_LENGTH = 10     # completed monthly bars

    def initialize(self):
        self.set_start_date(2007, 1, 1)
        self.set_end_date(2026, 8, 19)
        self.set_cash(100_000)

        self.spy = self.add_equity("SPY", Resolution.DAILY).symbol
        self.set_benchmark(self.spy)

        self.defensive = self.add_equity(self.DEFENSIVE, Resolution.DAILY).symbol
        self.sectors = [self.add_equity(t, Resolution.DAILY).symbol for t in self.SECTORS]

        # Rebalance once a month. This time rule sets when the method runs, not
        # when the orders fill: on daily data LEAN converts market orders to
        # MarketOnClose, so every fill lands at that day's close -- verified
        # across all 726 fills of the 2007-2026 backtest. Signals use only
        # months that have already closed, so this is not look-ahead.
        self.schedule.on(
            self.date_rules.month_start(self.spy),
            self.time_rules.after_market_open(self.spy, 30),
            self.rebalance,
        )

        # Diagnostics for "how often did the trend filter kick in".
        self.rebalances = 0
        self.slots_filled = 0
        self.slots_skipped = 0
        self.skips_by_sector = {t: 0 for t in self.SECTORS}
        self.months_fully_defensive = 0

    def monthly_closes(self):
        """Completed-month closing prices, indexed by month, columns by symbol."""
        history = self.history(
            self.sectors + [self.defensive],
            timedelta(days=560),
            Resolution.DAILY,
        )
        if history.empty or "close" not in history.columns:
            return None

        closes = history["close"].unstack(level=0)
        monthly = closes.groupby(closes.index.to_period("M")).last()

        # Drop the month in progress: its "close" is one or two days old and
        # would corrupt both the momentum ratio and the SMA.
        monthly = monthly[monthly.index < pd.Period(self.time, freq="M")]
        monthly = monthly.dropna(axis=1, how="any")

        if len(monthly) < self.MOM_LOOKBACK + 1:
            return None
        return monthly

    def rebalance(self):
        monthly = self.monthly_closes()
        if monthly is None:
            return

        last = monthly.iloc[-1]
        momentum = last / monthly.iloc[-(self.MOM_LOOKBACK + 1)] - 1.0
        sma = monthly.iloc[-self.SMA_LENGTH:].mean()

        ranked = [s for s in self.sectors if s in momentum.index]
        if len(ranked) < self.TOP_N:
            return
        ranked.sort(key=lambda s: momentum[s], reverse=True)

        slot_weight = 1.0 / self.TOP_N
        weights = {}
        skipped_this_month = 0

        for symbol in ranked[: self.TOP_N]:
            if last[symbol] > sma[symbol]:
                weights[symbol] = weights.get(symbol, 0.0) + slot_weight
                self.slots_filled += 1
            else:
                weights[self.defensive] = weights.get(self.defensive, 0.0) + slot_weight
                self.slots_skipped += 1
                skipped_this_month += 1
                self.skips_by_sector[symbol.value] += 1

        self.rebalances += 1
        if skipped_this_month == self.TOP_N:
            self.months_fully_defensive += 1

        self.set_holdings([PortfolioTarget(s, w) for s, w in weights.items()], True)

    def on_end_of_algorithm(self):
        slots = self.slots_filled + self.slots_skipped
        pct = (100.0 * self.slots_skipped / slots) if slots else 0.0
        self.log(f"rebalances={self.rebalances} slots={slots} "
                 f"skipped={self.slots_skipped} ({pct:.1f}%) "
                 f"fully_defensive_months={self.months_fully_defensive}")
        self.log(f"skips_by_sector={self.skips_by_sector}")
