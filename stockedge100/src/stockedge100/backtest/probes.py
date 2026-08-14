"""Engine test instruments.

These are **not** strategies, and the distinction is not a formality. A strategy is governed by
constitution §8: it needs a hypothesis, a pre-registration, a validation gate, and a holdout. A probe
exists to make the engine execute a known sequence of orders so its arithmetic can be checked against
a hand calculation.

So each probe here is a fixed mechanical schedule: no signal, no indicator, no parameter fitted to an
outcome, and no comparison between probes used to prefer one rule to another. The sealed spec
prohibits all four at Stage 2. Nothing a probe returns is a research result, and nothing in the
Stage 2 report treats it as one.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from stockedge100.backtest.engine import DecisionContext, OrderRequest
from stockedge100.backtest.errors import ConfigViolation
from stockedge100.backtest.market import MarketView
from stockedge100.backtest.orders import BUY, SELL

PROBE_FIXED_SCHEDULE = "PROBE_FIXED_SCHEDULE"
PROBE_BUY_AND_HOLD = "PROBE_BUY_AND_HOLD"
PROBE_ALWAYS_CASH = "PROBE_ALWAYS_CASH"


class FixedScheduleProbe:
    """Enter on a named decision session, exit on a named decision session.

    The sessions are arguments, not discoveries: they are written into the fixture or the test that
    constructs the probe, and the probe never looks at a price to choose them.
    """

    name = PROBE_FIXED_SCHEDULE

    def __init__(
        self,
        symbol: str,
        entry_session: dt.date,
        exit_session: dt.date | None,
        budget: Decimal,
    ) -> None:
        if exit_session is not None and exit_session <= entry_session:
            raise ConfigViolation(
                f"exit decision {exit_session} must be after entry decision {entry_session}"
            )
        self.symbol = symbol
        self.entry_session = entry_session
        self.exit_session = exit_session
        self.budget = budget

    def decide(self, view: MarketView, context: DecisionContext) -> list[OrderRequest]:
        if context.session == self.entry_session:
            return [OrderRequest(symbol=self.symbol, side=BUY, budget=self.budget)]
        if self.exit_session is not None and context.session == self.exit_session:
            return [OrderRequest(symbol=self.symbol, side=SELL)]
        return []

    def to_json(self) -> dict[str, str | None]:
        return {
            "probe": self.name,
            "symbol": self.symbol,
            "entry_decision_session": self.entry_session.isoformat(),
            "exit_decision_session": None if self.exit_session is None else self.exit_session.isoformat(),
            "budget": f"{self.budget:f}",
        }


class BuyAndHoldProbe:
    """Enter on the first decision session that has a visible bar, and never exit.

    "First eligible" is a property of the calendar and the data, not of the price: the probe asks
    whether a bar exists, never what it says.
    """

    name = PROBE_BUY_AND_HOLD

    def __init__(self, symbol: str, budget: Decimal) -> None:
        self.symbol = symbol
        self.budget = budget
        self._entered = False

    def decide(self, view: MarketView, context: DecisionContext) -> list[OrderRequest]:
        if self._entered or context.open_symbols:
            return []
        if not view.has_data(self.symbol, context.session):
            return []
        self._entered = True
        return [OrderRequest(symbol=self.symbol, side=BUY, budget=self.budget)]

    def to_json(self) -> dict[str, str]:
        return {"probe": self.name, "symbol": self.symbol, "budget": f"{self.budget:f}"}


class AlwaysCashProbe:
    """Never submit an order. The control: its equity curve must be a flat line at starting cash."""

    name = PROBE_ALWAYS_CASH

    def decide(self, view: MarketView, context: DecisionContext) -> list[OrderRequest]:
        return []

    def to_json(self) -> dict[str, str]:
        return {"probe": self.name}


DECLARED_PROBES = (PROBE_FIXED_SCHEDULE, PROBE_BUY_AND_HOLD, PROBE_ALWAYS_CASH)
