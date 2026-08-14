"""The shape every Stage 3 candidate has, and the shared rules it cannot opt out of.

Six families differ only in what they want to hold. Everything else — how large a position is, what
happens when the target changes, what happens when an indicator is unavailable — is sealed once in
``shared_rules`` and implemented once here, so that a family cannot accidentally acquire a private
sizing rule or a private exit path.

The important one is ``flat_first_rule``, quoted from the seal:

    "A candidate holds at most one position. If it holds H and its target is T with T not equal to
    H, it emits only SELL H. It emits BUY T only on a session on which the account is already flat.
    A candidate never emits a sell and a buy on the same session, because the engine executes orders
    sorted by (symbol, side, order_id), so an entry whose symbol sorts before the exit's symbol
    would execute first and be rejected MAX_POSITIONS."

That last clause is why the rule is structural and not stylistic. Emitting both legs at once would
make a rotation's behaviour depend on the alphabetical order of the two tickers involved — SPY→IEF
would round-trip through cash while SPY→XLF would silently fail its entry. The single-leg rule
removes the alphabet from the result.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Any, Sequence

from stockedge100.backtest.costs import CostModel, round_down_cent
from stockedge100.backtest.dataset import Bar
from stockedge100.backtest.engine import DecisionContext, OrderRequest
from stockedge100.backtest.market import MarketView
from stockedge100.backtest.orders import BUY, SELL


class Candidate:
    """One parameterisation of one strategy family, run on one window.

    Subclasses implement :meth:`target` — "the symbol this candidate wants to be holding at the
    close of session t, or ``None`` for cash". The order plumbing below is identical for all of
    them and is never overridden, with the single documented exception of the rotation family, which
    overrides :meth:`decide` because its sealed exit rule fires only on rebalance sessions.
    """

    family: str = ""

    def __init__(
        self,
        *,
        experiment_id: str,
        variant_id: str,
        universe: Sequence[str],
        parameters: dict[str, Any],
        costs: CostModel,
    ) -> None:
        self.experiment_id = experiment_id
        self.variant_id = variant_id
        self.universe = tuple(universe)
        self.parameters = dict(parameters)
        self.costs = costs
        self.name = variant_id

    # -- the shared rules ------------------------------------------------------------------

    def target(self, view: MarketView, context: DecisionContext) -> str | None:
        raise NotImplementedError

    def decide(self, view: MarketView, context: DecisionContext) -> list[OrderRequest]:
        held = context.open_symbols
        target = self.target(view, context)
        if held:
            current = held[0]
            if target == current:
                return []
            return [self.exit_order(current)]
        if target is None:
            return []
        return [self.entry_order(target, context)]

    def entry_order(self, symbol: str, context: DecisionContext) -> OrderRequest:
        """Sealed ``sizing_rule``: "A buy requests a budget of 95% of account equity measured at the
        decision close."

        The 95% is read from the sealed cost model's ``max_gross_exposure_fraction`` rather than
        written here, so the request and the cap the engine applies to it are the same number by
        construction and cannot drift apart.
        """

        budget = round_down_cent(self.costs.max_gross_exposure_fraction * context.equity)
        return OrderRequest(symbol=symbol, side=BUY, budget=budget, tag=self.experiment_id)

    def exit_order(self, symbol: str) -> OrderRequest:
        """Sealed exit: sell the whole position. Quantity ``None`` means the engine sells all of it."""

        return OrderRequest(symbol=symbol, side=SELL, tag=self.experiment_id)

    # -- history access --------------------------------------------------------------------

    def bars_at(self, view: MarketView, symbol: str, session: dt.date, count: int) -> list[Bar]:
        """The last ``count`` visible bars, but only if the newest of them *is* the bar at ``t``.

        The sealed indicator definitions all say "including the close at t". A symbol with no bar at
        the decision session has no ``close(t)``, so no rule that references ``close(t)`` can be
        evaluated, and ``insufficient_history_rule`` sends the session to cash. Returning the stale
        tail instead would evaluate today's rule against an older price and call the result today's
        signal.
        """

        bars = view.history(symbol, count)
        if not bars or bars[-1].session != session:
            return []
        return bars

    def to_json(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "variant_id": self.variant_id,
            "family": self.family,
            "universe": list(self.universe),
            "parameters": _jsonable(self.parameters),
        }


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return f"{value:f}"
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value
