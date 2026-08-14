"""The six strategy families, one class each, tested independently.

Constitution §8: "Strategy families must first be tested independently. Combining strategies is
prohibited until each component has an independent verdict." Nothing here reads another family's
state, and the Stage 3 harness never forms a portfolio of candidates. §8 also forbids machine
learning for Generation 1: every number a class below uses arrives from the sealed
``primary_parameters`` or a sealed ``robustness_neighbours`` entry, and nothing is estimated from
the data.

Each ``target_rule`` docstring is the sealed rule quoted verbatim. Read the docstring, then the
code; if the two ever disagree, the seal is the specification and the code is the defect.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Any, Sequence

from stockedge100.backtest.costs import CostModel, ZERO
from stockedge100.backtest.engine import DecisionContext, OrderRequest
from stockedge100.backtest.errors import ConfigViolation
from stockedge100.backtest.market import MarketView
from stockedge100.data.calendar import last_session_of_month
from stockedge100.strategies.base import Candidate
from stockedge100.strategies.indicators import (
    momentum,
    rolling_max_close,
    rolling_min_close,
    sma,
    wilder_rsi,
)

MONTHLY_REBALANCE = "last XNYS session of each calendar month"


class TrendSma(Candidate):
    """F1 — "target = SPY if close(t) > SMA(200)(t), else cash." """

    family = "trend/momentum"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.symbol = self.universe[0]
        self.sma_long = int(self.parameters["sma_long"])

    def target(self, view: MarketView, context: DecisionContext) -> str | None:
        bars = self.bars_at(view, self.symbol, context.session, self.sma_long)
        average = sma(bars, self.sma_long)
        if average is None:
            return None
        return self.symbol if bars[-1].close > average else None


class PullbackSma(Candidate):
    """F2 — "target = SPY if close(t) > SMA(200)(t) AND close(t) < SMA(10)(t), else cash." """

    family = "pullback"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.symbol = self.universe[0]
        self.sma_long = int(self.parameters["sma_long"])
        self.sma_short = int(self.parameters["sma_short"])

    def target(self, view: MarketView, context: DecisionContext) -> str | None:
        need = max(self.sma_long, self.sma_short)
        bars = self.bars_at(view, self.symbol, context.session, need)
        long_average = sma(bars, self.sma_long)
        short_average = sma(bars, self.sma_short)
        if long_average is None or short_average is None:
            return None
        close = bars[-1].close
        return self.symbol if close > long_average and close < short_average else None


class MeanReversionRsi(Candidate):
    """F3 — "If flat: target = SPY if RSI(rsi_period)(t) < rsi_entry_below, else cash. If holding
    SPY: target = cash if close(t) > SMA(exit_sma)(t), else SPY."

    The branch is selected by the account's own position, supplied by the engine's
    ``DecisionContext``. That is present information, not future information.
    """

    family = "mean reversion"

    def __init__(self, *, warmup_changes: int, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.symbol = self.universe[0]
        self.rsi_period = int(self.parameters["rsi_period"])
        self.rsi_entry_below = Decimal(str(self.parameters["rsi_entry_below"]))
        self.exit_sma = int(self.parameters["exit_sma"])
        self.warmup_changes = warmup_changes

    def target(self, view: MarketView, context: DecisionContext) -> str | None:
        need = max(self.warmup_changes + 1, self.exit_sma)
        bars = self.bars_at(view, self.symbol, context.session, need)
        if not bars:
            return None
        if context.open_symbols:
            average = sma(bars, self.exit_sma)
            if average is None:
                return None
            return None if bars[-1].close > average else self.symbol
        strength = wilder_rsi(bars, self.rsi_period, self.warmup_changes)
        if strength is None:
            return None
        return self.symbol if strength < self.rsi_entry_below else None


class DonchianBreakout(Candidate):
    """F4 — "If flat: target = SPY if close(t) >= MAXCLOSE(entry_lookback)(t), else cash. If holding
    SPY: target = cash if close(t) <= MINCLOSE(exit_lookback)(t), else SPY."

    Both comparisons are inclusive, because the close at *t* is inside both windows by definition and
    a strict inequality could never fire.
    """

    family = "breakout"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.symbol = self.universe[0]
        self.entry_lookback = int(self.parameters["entry_lookback"])
        self.exit_lookback = int(self.parameters["exit_lookback"])

    def target(self, view: MarketView, context: DecisionContext) -> str | None:
        need = max(self.entry_lookback, self.exit_lookback)
        bars = self.bars_at(view, self.symbol, context.session, need)
        if not bars:
            return None
        close = bars[-1].close
        if context.open_symbols:
            floor = rolling_min_close(bars, self.exit_lookback)
            if floor is None:
                return None
            return None if close <= floor else self.symbol
        ceiling = rolling_max_close(bars, self.entry_lookback)
        if ceiling is None:
            return None
        return self.symbol if close >= ceiling else None


class DualMomentumRotation(Candidate):
    """F5 — ranked monthly, held between rebalances.

    This is the one family that overrides :meth:`decide` rather than supplying a :meth:`target`, and
    the reason is in the sealed exit rule: "On a rebalance session, if the held symbol is not the
    target, sell the whole position." A position is therefore *never* exited on a non-rebalance
    session, so the shared base implementation — which recomputes a target every session — would
    exit on any session whose target happened to differ. Overriding ``decide`` keeps the rebalance
    calendar as the only thing that can move the position.

    ``pending_target`` implements the sealed deferral: "the candidate records the target as
    pending_target, emits only the exit, and issues the buy on the next session on which the account
    is flat. pending_target holds no future information — it is the decision already taken at the
    rebalance close — and it is cleared at the next rebalance session whether or not it was ever
    issued."

    Because that is per-run mutable state, the harness constructs a fresh instance for every run,
    including determinism re-runs. Reusing one instance across two runs would carry a pending target
    across a boundary the seal does not permit.
    """

    family = "ETF rotation"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.momentum_lookback = int(self.parameters["momentum_lookback"])
        self.top_n = int(self.parameters["top_n"])
        rebalance = str(self.parameters["rebalance"])
        if rebalance != MONTHLY_REBALANCE:
            raise ConfigViolation(f"unsupported sealed rebalance rule {rebalance!r}")
        if self.top_n != 1:
            raise ConfigViolation(
                f"top_n={self.top_n} exceeds the sealed cost model's one open risky position"
            )
        self.pending_target: str | None = None

    def is_rebalance(self, session: dt.date) -> bool:
        """The sealed rebalance date is calendar-derived, not data-derived.

        The XNYS calendar is published in advance, so knowing that a given session is the month's
        last one uses no information a decision-maker at that close would lack. Deriving it from the
        price file instead — "no later bar exists this month" — would be look-ahead.
        """

        return session == last_session_of_month(session.year, session.month)

    def rank_target(self, view: MarketView, context: DecisionContext) -> str | None:
        """"Rank eligible members by MOM(momentum_lookback) descending, ties broken by ascending
        symbol. target = the top-ranked member if its momentum is strictly greater than 0, else cash."
        """

        need = self.momentum_lookback + 1
        ranked: list[tuple[str, Decimal]] = []
        for symbol in sorted(self.universe):
            bars = self.bars_at(view, symbol, context.session, need)
            if len(bars) < need:
                continue
            value = momentum(bars, self.momentum_lookback)
            if value is None:
                continue
            ranked.append((symbol, value))
        if not ranked:
            return None
        ranked.sort(key=lambda item: (-item[1], item[0]))
        best_symbol, best_momentum = ranked[0]
        return best_symbol if best_momentum > ZERO else None

    def target(self, view: MarketView, context: DecisionContext) -> str | None:
        """Only meaningful on a rebalance session; "On a non-rebalance session no ranking is performed." """

        if not self.is_rebalance(context.session):
            return context.open_symbols[0] if context.open_symbols else None
        return self.rank_target(view, context)

    def decide(self, view: MarketView, context: DecisionContext) -> list[OrderRequest]:
        held = context.open_symbols
        if self.is_rebalance(context.session):
            self.pending_target = self.rank_target(view, context)
            if held:
                if held[0] == self.pending_target:
                    return []
                return [self.exit_order(held[0])]
            if self.pending_target is None:
                return []
            return [self.entry_order(self.pending_target, context)]
        if held or self.pending_target is None:
            return []
        return [self.entry_order(self.pending_target, context)]


class DefensiveRegime(Candidate):
    """F6 — "target = SPY if close(SPY, t) > SMA(sma_long)(SPY, t); else the defensive symbol if it
    has a visible bar at t; else cash."

    "The regime is read from SPY only: the defensive leg is a destination, never a signal."
    """

    family = "defensive regime logic"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.sma_long = int(self.parameters["sma_long"])
        self.risk_symbol = str(self.parameters["risk_symbol"])
        defensive = self.parameters.get("defensive_symbol")
        self.defensive_symbol = None if defensive is None else str(defensive)

    def target(self, view: MarketView, context: DecisionContext) -> str | None:
        bars = self.bars_at(view, self.risk_symbol, context.session, self.sma_long)
        average = sma(bars, self.sma_long)
        if average is None:
            return None
        if bars[-1].close > average:
            return self.risk_symbol
        if self.defensive_symbol is None:
            return None
        if not view.has_data(self.defensive_symbol, context.session):
            return None
        return self.defensive_symbol


FAMILY_CLASSES: dict[str, type[Candidate]] = {
    "SE100-S3-F1-TREND-SMA200": TrendSma,
    "SE100-S3-F2-PULLBACK-SMA200-SMA10": PullbackSma,
    "SE100-S3-F3-MEANREV-RSI2": MeanReversionRsi,
    "SE100-S3-F4-BREAKOUT-DONCHIAN-50-25": DonchianBreakout,
    "SE100-S3-F5-ROTATION-DUALMOM": DualMomentumRotation,
    "SE100-S3-F6-DEFENSIVE-SMA200-SHY": DefensiveRegime,
}


def traded_symbols(experiment_id: str, universe: Sequence[str], parameters: dict[str, Any]) -> tuple[str, ...]:
    """Every symbol this variant may name in an order.

    The engine raises ``InvariantViolation`` for an order in a symbol it was not given, so this is
    the exact set the run must load — no wider, because every extra series is also checked for
    staleness on every session and would let an unrelated instrument halt the run.
    """

    symbols = set(universe)
    if experiment_id == "SE100-S3-F6-DEFENSIVE-SMA200-SHY":
        symbols = {str(parameters["risk_symbol"])}
        defensive = parameters.get("defensive_symbol")
        if defensive is not None:
            symbols.add(str(defensive))
    return tuple(sorted(symbols))


def build_candidate(
    *,
    experiment_id: str,
    variant_id: str,
    universe: Sequence[str],
    parameters: dict[str, Any],
    costs: CostModel,
    indicator_definitions: dict[str, Any],
) -> Candidate:
    """Construct one variant. A fresh object per run; never reused across runs."""

    cls = FAMILY_CLASSES.get(experiment_id)
    if cls is None:
        raise ConfigViolation(f"no implementation registered for sealed experiment {experiment_id!r}")
    kwargs: dict[str, Any] = {
        "experiment_id": experiment_id,
        "variant_id": variant_id,
        "universe": tuple(universe),
        "parameters": dict(parameters),
        "costs": costs,
    }
    if cls is MeanReversionRsi:
        kwargs["warmup_changes"] = int(indicator_definitions["RSI"]["warmup_changes"])
    return cls(**kwargs)
