"""Turn the sealed protocol into the thirty declared runs, and measure each one.

The iteration budget is fixed by the seal: "6 candidates, 1 primary + 4 neighbours each,
total_declared_runs: 30, revisions_permitted: 0". :func:`variant_specs` enumerates exactly those
thirty and nothing else, from the sealed file, so the count is a property of the protocol rather
than of anything typed here.

Three details govern how a run is set up, and each of them is a place a plausible shortcut would
have produced a wrong number:

**The engine is always given the whole development window, never a narrowed one.**
``MarketView.history`` filters visible bars with ``self._window.contains(day)``. Passing a window
that began at the candidate's run start would therefore delete the warm-up history the run start
exists to guarantee — a 200-session average would be computed from one bar on the first session. The
run start is passed as the engine's ``start`` argument instead, which moves the first *decision*
without moving the visibility bound.

**Warm-up is the largest lookback across the primary and every neighbour**, per the sealed
``warmup_rule``, and the run start is computed once per candidate from its *declared* universe. All
five runs of a candidate therefore share one window, which is what makes the sign-stability
condition a comparison of rules rather than a comparison of periods. It also means F5 and F6 run a
shorter history than F1–F4; the seal discloses this, and no condition compares one candidate to
another.

**Each run loads exactly the symbols its own variant may trade.** The engine raises
``InvariantViolation`` for an order in a symbol it was not given, and it runs a staleness check over
every series it *was* given — so a wider load is both unnecessary and a way for an untraded
instrument to halt a run.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Iterable, Sequence

from stockedge100.backtest.costs import CostModel, ZERO, exact
from stockedge100.backtest.dataset import PriceSeries, load_dataset
from stockedge100.backtest.engine import BacktestEngine, BacktestResult
from stockedge100.backtest.errors import ConfigViolation
from stockedge100.backtest.metrics import max_drawdown, summarize
from stockedge100.backtest.window import ResearchWindow, development_window
from stockedge100.strategies.config import Stage3Config
from stockedge100.strategies.families import build_candidate, traded_symbols

PRIMARY = "primary"
NEIGHBOUR = "neighbour"


@dataclass(frozen=True)
class VariantSpec:
    """One of the thirty declared runs."""

    experiment_id: str
    variant_id: str
    role: str
    index: int
    universe: tuple[str, ...]
    parameters: dict[str, Any]
    symbols: tuple[str, ...]

    def to_json(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "variant_id": self.variant_id,
            "role": self.role,
            "universe": list(self.universe),
            "parameters": _jsonable(self.parameters),
            "symbols_loaded": list(self.symbols),
        }


@dataclass(frozen=True)
class CandidatePlan:
    """A candidate's five runs and the single window they all share."""

    experiment_id: str
    family: str
    declared_universe: tuple[str, ...]
    warmup_sessions: int
    effective_warmup: int
    run_start: dt.date
    run_end: dt.date
    binding_symbol: str
    variants: tuple[VariantSpec, ...]
    all_symbols: tuple[str, ...]

    def to_json(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "family": self.family,
            "declared_universe": list(self.declared_universe),
            "declared_warmup_sessions": self.warmup_sessions,
            "largest_lookback_across_primary_and_neighbours": self.effective_warmup,
            "run_start": self.run_start.isoformat(),
            "run_end": self.run_end.isoformat(),
            "run_start_binding_symbol": self.binding_symbol,
            "symbols_loaded": list(self.all_symbols),
            "variants": [variant.to_json() for variant in self.variants],
        }


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return f"{value:f}"
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


# -- planning ------------------------------------------------------------------------------------


def variant_specs(experiment: dict[str, Any]) -> tuple[VariantSpec, ...]:
    """The primary plus every sealed robustness neighbour, in sealed order."""

    experiment_id = experiment["experiment_id"]
    declared_universe = tuple(experiment["universe"])
    primary = dict(experiment["primary_parameters"])
    specs = [
        VariantSpec(
            experiment_id=experiment_id,
            variant_id=f"{experiment_id}#PRIMARY",
            role=PRIMARY,
            index=0,
            universe=declared_universe,
            parameters=primary,
            symbols=traded_symbols(experiment_id, declared_universe, primary),
        )
    ]
    for position, neighbour in enumerate(experiment["robustness_neighbours"], start=1):
        overrides = dict(neighbour)
        universe = tuple(overrides.pop("universe", declared_universe))
        parameters = {**primary, **overrides}
        specs.append(
            VariantSpec(
                experiment_id=experiment_id,
                variant_id=f"{experiment_id}#N{position}",
                role=NEIGHBOUR,
                index=position,
                universe=universe,
                parameters=parameters,
                symbols=traded_symbols(experiment_id, universe, parameters),
            )
        )
    return tuple(specs)


LOOKBACK_KEYS = ("sma_long", "sma_short", "exit_sma", "entry_lookback", "exit_lookback")


def largest_lookback(specs: Sequence[VariantSpec], indicator_definitions: dict[str, Any]) -> int:
    """Sealed ``warmup_rule``: the largest lookback used by the primary *or by any neighbour*,
    expressed as the number of visible bars the indicator consumes.

    Two conversions are not cosmetic. ``MOM(n)`` reads the bar *n* sessions back as well as today's,
    so it consumes ``n + 1`` bars — which is why F5's sealed warm-up is 316 for a largest lookback
    of 315. And the RSI family's binding lookback is its sealed ``warmup_changes``, not
    ``rsi_period``: Wilder's average is an infinite-memory recursion, so the seeding distance is the
    history the value actually depends on, and ``warmup_changes`` changes need ``warmup_changes + 1``
    closes — which is why F3's sealed warm-up is 101.

    Recomputing this is a check on the seal, not a substitute for it: :func:`plan_candidate` runs
    the declared ``warmup_sessions`` and this number against each other and refuses to plan a
    candidate where they disagree.
    """

    largest = 0
    for spec in specs:
        for key in LOOKBACK_KEYS:
            value = spec.parameters.get(key)
            if isinstance(value, int):
                largest = max(largest, value)
        if "momentum_lookback" in spec.parameters:
            largest = max(largest, int(spec.parameters["momentum_lookback"]) + 1)
        if "rsi_period" in spec.parameters:
            largest = max(largest, int(indicator_definitions["RSI"]["warmup_changes"]) + 1)
    return largest


def run_start_for(
    universe: Sequence[str],
    warmup_sessions: int,
    window: ResearchWindow,
    series: dict[str, PriceSeries],
) -> tuple[dt.date, str]:
    """Sealed ``run_start_rule``: "the first development-window session on which EVERY symbol in its
    universe has at least warmup_sessions visible bars inside the development window".

    A symbol's visible-bar count is non-decreasing in session, so the first session at which *all*
    symbols qualify is the latest of the per-symbol qualifying sessions — and each of those is
    itself an exchange session, because it is the date of a bar. The binding symbol is returned
    alongside, because "which instrument's history set the start date" is the fact a reader needs to
    check the number rather than take it.

    Sealed ``warmup_data_source``: "Warm-up history is drawn only from sessions inside the
    development window", which is why the count filters on ``window.contains`` rather than counting
    from the start of the file.
    """

    binding_session: dt.date | None = None
    binding_symbol = ""
    for symbol in sorted(set(universe)):
        history = series.get(symbol)
        if history is None:
            raise ConfigViolation(f"run start needs {symbol} but its series was not loaded")
        inside = [day for day in history.sessions if window.contains(day)]
        if len(inside) < warmup_sessions:
            raise ConfigViolation(
                f"{symbol} has only {len(inside)} sessions inside {window.name}; "
                f"{warmup_sessions} are required by the sealed warm-up rule"
            )
        qualifies = inside[warmup_sessions - 1]
        if binding_session is None or qualifies > binding_session:
            binding_session, binding_symbol = qualifies, symbol
    if binding_session is None:
        raise ConfigViolation("run start requested for an empty universe")
    return binding_session, binding_symbol


def plan_candidate(
    experiment: dict[str, Any],
    window: ResearchWindow,
    series: dict[str, PriceSeries],
    indicator_definitions: dict[str, Any],
) -> CandidatePlan:
    specs = variant_specs(experiment)
    declared_universe = tuple(experiment["universe"])
    warmup = int(experiment["warmup_sessions"])
    effective = largest_lookback(specs, indicator_definitions)
    if effective != warmup:
        raise ConfigViolation(
            f"{experiment['experiment_id']}: sealed warmup_sessions={warmup} but the largest "
            f"lookback across the primary and its neighbours consumes {effective} visible bars. "
            "The seal is the specification; report the discrepancy rather than adjusting either."
        )
    run_start, binding = run_start_for(declared_universe, warmup, window, series)
    all_symbols = sorted({symbol for spec in specs for symbol in spec.symbols})
    return CandidatePlan(
        experiment_id=experiment["experiment_id"],
        family=experiment["family"],
        declared_universe=declared_universe,
        warmup_sessions=warmup,
        effective_warmup=effective,
        run_start=run_start,
        run_end=window.end,
        binding_symbol=binding,
        variants=specs,
        all_symbols=tuple(all_symbols),
    )


def required_symbols(config: Stage3Config) -> tuple[str, ...]:
    symbols: set[str] = set()
    for experiment in config.experiments:
        for spec in variant_specs(experiment):
            symbols.update(spec.symbols)
        symbols.update(experiment["universe"])
    return tuple(sorted(symbols))


def load_required_dataset(config: Stage3Config) -> dict[str, PriceSeries]:
    """Load only what the sealed protocol names.

    ``excluded_symbols`` in the seal calls out AAPL by name: a price file for it exists because
    Stage 1 measured the split convention against two AAPL split events, and it is not a member of
    the frozen research universe. Nothing here can reach it, because nothing here names it.
    """

    excluded = set(config.protocol.get("excluded_symbols", {}))
    wanted = [symbol for symbol in required_symbols(config)]
    overlap = sorted(set(wanted) & excluded)
    if overlap:
        raise ConfigViolation(f"sealed protocol both requires and excludes {overlap}")
    return load_dataset(wanted)


# -- running -------------------------------------------------------------------------------------


def run_variant(
    spec: VariantSpec,
    plan: CandidatePlan,
    series: dict[str, PriceSeries],
    costs: CostModel,
    window: ResearchWindow,
    indicator_definitions: dict[str, Any],
    *,
    label_suffix: str = "",
) -> BacktestResult:
    """One declared run. A fresh candidate object every time — see :class:`DualMomentumRotation`."""

    candidate = build_candidate(
        experiment_id=spec.experiment_id,
        variant_id=spec.variant_id,
        universe=spec.universe,
        parameters=spec.parameters,
        costs=costs,
        indicator_definitions=indicator_definitions,
    )
    subset = {symbol: series[symbol] for symbol in spec.symbols}
    engine = BacktestEngine(
        subset,
        costs,
        window,
        candidate,
        start=plan.run_start,
        end=plan.run_end,
        label=spec.variant_id + label_suffix,
        enforce_research_shutdown=True,
    )
    return engine.run()


# -- measurement ---------------------------------------------------------------------------------


@exact
def trade_pnls(result: BacktestResult) -> list[Decimal]:
    """Closed-trade P&L in exit order. One position at a time, so exit order is append order."""

    return [trade.pnl for trade in result.trades]


@exact
def contribution_by_symbol(result: BacktestResult) -> dict[str, Decimal]:
    totals: dict[str, Decimal] = {}
    for trade in result.trades:
        totals[trade.symbol] = totals.get(trade.symbol, ZERO) + trade.pnl
    return totals


@exact
def _mean(values: Sequence[Decimal]) -> Decimal | None:
    if not values:
        return None
    total = ZERO
    for value in values:
        total += value
    return total / Decimal(len(values))


def longest_flat_streak(result: BacktestResult) -> int:
    longest = 0
    current = 0
    for point in result.equity_curve:
        if point.position_count == 0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def measure(result: BacktestResult, costs: CostModel, cost_model_raw: dict[str, Any]) -> dict[str, Any]:
    """Everything the gate reads, plus everything the seal lists as reported-but-not-gating."""

    metrics_cfg = cost_model_raw.get("metrics", {})
    trading_days = int(metrics_cfg.get("trading_days_per_year", 252))
    risk_free = Decimal(str(metrics_cfg.get("sharpe_risk_free_annual_rate", "0")))

    equity = [point.equity for point in result.equity_curve]
    sessions = [point.session for point in result.equity_curve]
    positions = [point.position_count for point in result.equity_curve]
    pnls = trade_pnls(result)

    summary = summarize(
        sessions=sessions,
        equity=equity,
        position_counts=positions,
        trade_pnls=pnls,
        trading_days=trading_days,
        risk_free_annual=risk_free,
    )

    wins = [value for value in pnls if value > ZERO]
    losses = [value for value in pnls if value < ZERO]
    average_win = _mean(wins)
    average_loss = _mean(losses)
    rejection_counts: dict[str, int] = {}
    for rejection in result.rejections:
        rejection_counts[rejection.reason] = rejection_counts.get(rejection.reason, 0) + 1

    return {
        "label": result.label,
        "start": result.start.isoformat(),
        "end": result.end.isoformat(),
        "sessions": summary["sessions"],
        "starting_equity": f"{result.starting_equity:f}",
        "final_equity": f"{result.final_equity:f}",
        "final_cash": f"{result.final_cash:f}",
        "total_return": summary["total_return"],
        "cagr": summary["cagr"],
        "max_drawdown": summary["max_drawdown"],
        "daily_return_stdev": summary["daily_return_stdev"],
        "sharpe": summary["sharpe"],
        "sharpe_risk_free_annual": summary["sharpe_risk_free_annual"],
        "profit_factor": summary["profit_factor"],
        "profit_factor_note": summary["profit_factor_note"],
        "closed_trades": summary["closed_trades"],
        "exposure_fraction": summary["exposure_fraction"],
        "win_rate": _ratio(len(wins), summary["closed_trades"]),
        "wins": len(wins),
        "losses": len(losses),
        "scratches": len(pnls) - len(wins) - len(losses),
        "average_win": None if average_win is None else f"{average_win:f}",
        "average_loss": None if average_loss is None else f"{average_loss:f}",
        "longest_flat_streak_sessions": longest_flat_streak(result),
        "fills": len(result.fills),
        "rejections": len(result.rejections),
        "rejection_reasons": dict(sorted(rejection_counts.items())),
        "dividend_events": len(result.dividend_events),
        "stale_marks": result.stale_marks,
        "shutdown_session": None if result.shutdown_session is None else result.shutdown_session.isoformat(),
        "open_positions_at_end": len(result.open_positions),
        "contribution_by_symbol": {
            symbol: f"{value:f}" for symbol, value in sorted(contribution_by_symbol(result).items())
        },
        "trades_digest": result.trades_digest(),
        "equity_digest": result.equity_digest(),
    }


@exact
def _ratio(numerator: int, denominator: int) -> str | None:
    if denominator == 0:
        return None
    return f"{Decimal(numerator) / Decimal(denominator):f}"


def trade_ledger(result: BacktestResult) -> list[dict[str, Any]]:
    """The closed-trade list, so a reader can recompute C3, C5, and C6 without rerunning anything."""

    return [
        {
            "symbol": trade.symbol,
            "entry_session": trade.entry_session.isoformat(),
            "exit_session": trade.exit_session.isoformat(),
            "quantity": f"{trade.quantity:f}",
            "pnl": f"{trade.pnl:f}",
        }
        for trade in result.trades
    ]
