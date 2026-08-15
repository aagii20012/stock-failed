"""Generation 2's window guard.

Generation 1 already enforces its partition structurally: :class:`ResearchWindow` raises
:class:`WindowViolation` for a session outside its bounds, and ``MarketView`` raises
``LookAheadError`` for a session after the decision date. Both still bind here. This module adds the
three checks sealed in ``governance/generation_2/STAGE_1_G2_PARTITION_LOCK.md`` §4, and nothing
else:

1. the window handed to a Generation 2 Stage 3 run ends on or before the development bound;
2. no ``PriceSeries`` loaded for such a run contains a session after that bound — established by
   inspecting the loaded bars, not by trusting the loader;
3. constructing a Generation 2 research window that intersects either prohibited period raises.

The third check is deliberately broader than Stage 3 needs. Stage 3 never approaches either holdout,
so the check can only fire in a later stage — which is the point of writing it now, while no result
is visible and nobody wants it to be weaker.

Every bound is read from ``STAGE_1_G2_PARTITION_LOCK.json``. Restating the dates here would create a
second copy of the partition, and the second copy is the one that eventually disagrees.

The loader in this module truncates at the development bound *while parsing*, so a bar dated after
the bound is never materialized at all. Check 2 then runs against the result independently: the
truncation is the mechanism, the assertion is the evidence, and the assertion does not assume the
mechanism worked.
"""

from __future__ import annotations

import csv
import datetime as dt
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Mapping

import json

from stockedge100.backtest.config import PROJECT_ROOT
from stockedge100.backtest.dataset import COLUMNS, NORMALIZED_DIR, Bar, PriceSeries
from stockedge100.backtest.errors import BacktestError, ConfigViolation, WindowViolation
from stockedge100.backtest.window import DEVELOPMENT, ResearchWindow, development_window

__all__ = [
    "PARTITION_LOCK_PATH",
    "PARTITION_LOCK_ID",
    "development_bound",
    "prohibited_windows",
    "assert_not_prohibited",
    "generation_2_window",
    "assert_run_window",
    "stage_3_window",
    "assert_series_within_bound",
    "load_stage_3_series",
    "load_stage_3_dataset",
    "guard_state",
]

PARTITION_LOCK_PATH = PROJECT_ROOT / "governance" / "generation_2" / "STAGE_1_G2_PARTITION_LOCK.json"
PARTITION_LOCK_ID = "SE100-GOV-2002"

#: The two prohibited periods, in the order the lock records them, with the label each carries in
#: the lock's own ``partition`` block. The dates come from the lock; only the labels live here.
PROHIBITED_LABELS = ("generation_1_holdout", "holdout")


def _as_date(value: dt.date | str) -> dt.date:
    return dt.date.fromisoformat(value) if isinstance(value, str) else value


@lru_cache(maxsize=1)
def _lock() -> dict:
    """The Generation 2 partition lock, checked for identity and internal agreement."""
    if not PARTITION_LOCK_PATH.is_file():
        raise ConfigViolation(
            f"the Generation 2 partition lock is missing at {PARTITION_LOCK_PATH}; no Generation 2 "
            "run may proceed without the artifact that fixes its bounds"
        )
    lock = json.loads(PARTITION_LOCK_PATH.read_text(encoding="utf-8"))
    if lock.get("artifact_id") != PARTITION_LOCK_ID:
        raise ConfigViolation(
            f"{PARTITION_LOCK_PATH.name} declares artifact_id {lock.get('artifact_id')!r}; "
            f"expected {PARTITION_LOCK_ID!r}"
        )
    if lock.get("generation") != 2:
        raise ConfigViolation(f"{PARTITION_LOCK_PATH.name} is not a Generation 2 artifact")

    partition = lock["partition"]
    enforcement = lock["enforcement"]

    # The lock states the development bound twice — once as a partition boundary and once as the
    # value this guard is told to enforce. If they ever disagree, refuse rather than pick one.
    if enforcement["development_bound"] != partition["development_end"]:
        raise ConfigViolation(
            "the partition lock disagrees with itself: enforcement.development_bound is "
            f"{enforcement['development_bound']!r} but partition.development_end is "
            f"{partition['development_end']!r}"
        )

    declared = [[_as_date(a), _as_date(b)] for a, b in enforcement["prohibited_windows"]]
    expected = [
        [_as_date(partition[f"{label}_start"]), _as_date(partition[f"{label}_end"])]
        for label in PROHIBITED_LABELS
    ]
    if declared != expected:
        raise ConfigViolation(
            "enforcement.prohibited_windows does not match the partition's holdout ranges: "
            f"{declared} vs {expected}"
        )
    if not partition.get("boundaries_inclusive"):
        raise ConfigViolation("this guard assumes inclusive partition boundaries; the lock does not")
    if lock.get("holdout_read_authorized") is not False:
        raise ConfigViolation(
            "the partition lock no longer records holdout_read_authorized as false; this guard "
            "refuses to run against a lock that authorizes a holdout read"
        )
    return lock


def development_bound() -> dt.date:
    """The last session any Generation 2 Stage 3 run may see, read from the lock."""
    return _as_date(_lock()["enforcement"]["development_bound"])


def prohibited_windows() -> tuple[tuple[str, dt.date, dt.date], ...]:
    """``(label, start, end)`` for each period no Generation 2 window may intersect."""
    partition = _lock()["partition"]
    return tuple(
        (label, _as_date(partition[f"{label}_start"]), _as_date(partition[f"{label}_end"]))
        for label in PROHIBITED_LABELS
    )


def assert_not_prohibited(
    start: dt.date | str, end: dt.date | str, *, what: str = "window"
) -> None:
    """Sealed check 3. Raise if ``[start, end]`` intersects either prohibited period."""
    first, last = _as_date(start), _as_date(end)
    if first > last:
        raise WindowViolation(
            f"{what} {first.isoformat()}..{last.isoformat()} runs backwards; a Generation 2 window "
            "must start on or before it ends"
        )
    for label, lo, hi in prohibited_windows():
        if first <= hi and lo <= last:
            raise WindowViolation(
                f"{what} {first.isoformat()}..{last.isoformat()} intersects the prohibited "
                f"{label} period {lo.isoformat()}..{hi.isoformat()}. Generation 1's final holdout "
                "is spent and may never be read again in any generation; Generation 2's holdout is "
                "sealed until that period has elapsed in real calendar time. No result, and no "
                "argument about what a result would show, reopens either."
            )


def generation_2_window(name: str, start: dt.date | str, end: dt.date | str) -> ResearchWindow:
    """Construct a Generation 2 research window, or raise if it touches a prohibited period."""
    first, last = _as_date(start), _as_date(end)
    assert_not_prohibited(first, last, what=f"{name} window")
    return ResearchWindow(name=name, start=first, end=last)


def assert_run_window(window: ResearchWindow) -> ResearchWindow:
    """Sealed check 1 (plus check 3). Raise unless ``window`` is legal for a Stage 3 run."""
    bound = development_bound()
    assert_not_prohibited(window.start, window.end, what=f"{window.name} window")
    if window.end > bound:
        raise WindowViolation(
            f"the {window.name} window ends {window.end.isoformat()}, after the Generation 2 "
            f"development bound {bound.isoformat()}. Stage 3 is authorized to read development data "
            "only; the validation window is LOCKED and both holdouts are prohibited."
        )
    if window.start > window.end:
        raise WindowViolation(
            f"the {window.name} window runs backwards: "
            f"{window.start.isoformat()}..{window.end.isoformat()}"
        )
    return window


def stage_3_window() -> ResearchWindow:
    """The one window Generation 2 Stage 3 may read, taken from the lock and then guarded."""
    window = development_window()
    lock = _lock()
    partition = lock["partition"]
    if (window.start, window.end) != (
        _as_date(partition["development_start"]),
        _as_date(partition["development_end"]),
    ):
        raise ConfigViolation(
            "the Generation 1 partition bounds and the Generation 2 partition lock disagree on the "
            f"development window: {window.start}..{window.end} vs "
            f"{partition['development_start']}..{partition['development_end']}"
        )
    if lock["authorized_windows"] != [DEVELOPMENT]:
        raise ConfigViolation(
            f"the partition lock authorizes {lock['authorized_windows']!r}, not development alone"
        )
    return assert_run_window(window)


def assert_series_within_bound(series: Mapping[str, PriceSeries]) -> dict[str, str]:
    """Sealed check 2. Inspect the loaded bars of every series; raise on any past the bound.

    Returns each symbol's last loaded session, so a caller can record what was actually in memory
    rather than what it believes was in memory.
    """
    bound = development_bound()
    last_seen: dict[str, str] = {}
    for symbol in sorted(series):
        one = series[symbol]
        # Read the bar map itself. A loader that truncated ``sessions`` while leaving the bars in
        # place would pass an inspection of ``sessions`` alone, so check both and require agreement.
        bar_sessions = tuple(sorted(one.bars))
        if bar_sessions != tuple(one.sessions):
            raise WindowViolation(
                f"{symbol}: the loaded bar map and the session index disagree "
                f"({len(bar_sessions)} bars, {len(one.sessions)} sessions); a series whose index "
                "hides part of its own contents cannot be checked against the partition"
            )
        if not bar_sessions:
            raise WindowViolation(f"{symbol}: no bars were loaded inside the development window")
        past = [day for day in bar_sessions if day > bound]
        if past:
            raise WindowViolation(
                f"{symbol}: {len(past)} loaded bar(s) fall after the Generation 2 development bound "
                f"{bound.isoformat()}, the first at {past[0].isoformat()}. Stage 3 may not hold "
                "post-bound data in memory, whatever it intends to do with it."
            )
        last_seen[symbol] = bar_sessions[-1].isoformat()
    return last_seen


def _decimal(text: str, field: str, symbol: str, session: str) -> Decimal:
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise BacktestError(f"{symbol} {session}: could not parse {field}={text!r}") from exc


def load_stage_3_series(symbol: str, *, directory: Path | None = None) -> PriceSeries:
    """Load one symbol, stopping at the development bound instead of loading and discarding.

    ``dataset.load_series`` reads a whole file. That is correct for Generation 1, whose windows were
    applied downstream, but it would leave post-bound bars in memory for the duration of a
    Generation 2 run. Here the read stops at the first session past the bound, so the assertion in
    :func:`assert_series_within_bound` is checking a fact rather than restating an intention.
    """
    bound = development_bound()
    path = (directory or NORMALIZED_DIR) / f"{symbol}.csv"
    if not path.is_file():
        raise BacktestError(f"no normalized series for {symbol!r} at {path}")

    bars: dict[dt.date, Bar] = {}
    sessions: list[dt.date] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != COLUMNS:
            raise BacktestError(
                f"{symbol}: unexpected normalized schema {reader.fieldnames!r}; expected {list(COLUMNS)}"
            )
        for row in reader:
            session = dt.date.fromisoformat(row["session"])
            if session > bound:
                break
            if session in bars:
                raise BacktestError(f"{symbol}: duplicate session {session}")
            if sessions and session <= sessions[-1]:
                raise BacktestError(f"{symbol}: sessions are not strictly increasing at {session}")
            bars[session] = Bar(
                session=session,
                open=_decimal(row["open"], "open", symbol, row["session"]),
                high=_decimal(row["high"], "high", symbol, row["session"]),
                low=_decimal(row["low"], "low", symbol, row["session"]),
                close=_decimal(row["close"], "close", symbol, row["session"]),
                adj_close=_decimal(row["adj_close"], "adj_close", symbol, row["session"]),
                volume=int(row["volume"]),
                dividend=_decimal(row["dividend"], "dividend", symbol, row["session"]),
                split_ratio=_decimal(row["split_ratio"], "split_ratio", symbol, row["session"]),
            )
            sessions.append(session)

    if not sessions:
        raise BacktestError(
            f"{symbol}: no sessions on or before the development bound {bound.isoformat()}"
        )
    return PriceSeries(symbol=symbol, bars=bars, sessions=tuple(sessions))


def load_stage_3_dataset(
    symbols: Iterable[str], *, directory: Path | None = None
) -> dict[str, PriceSeries]:
    """Load several symbols under the bound, in sorted order, and then verify the result."""
    series = {
        symbol: load_stage_3_series(symbol, directory=directory) for symbol in sorted(set(symbols))
    }
    assert_series_within_bound(series)
    return series


def guard_state() -> dict[str, object]:
    """What the guard is enforcing, for a report that must show its bounds rather than claim them."""
    lock = _lock()
    return {
        "guard": "stockedge100.strategies.g2_window_guard",
        "bounds_source": PARTITION_LOCK_PATH.name,
        "bounds_source_artifact_id": lock["artifact_id"],
        "development_bound": development_bound().isoformat(),
        "prohibited_windows": [
            {"label": label, "start": lo.isoformat(), "end": hi.isoformat()}
            for label, lo, hi in prohibited_windows()
        ],
        "validation_window_state": lock["validation_window_state"],
        "generation_1_holdout_state": lock["generation_1_holdout_state"],
        "holdout_state": lock["holdout_state"],
        "stage_3_authorized": lock["stage_3_authorized"],
        "stage_4_authorized": lock["stage_4_authorized"],
        "holdout_read_authorized": lock["holdout_read_authorized"],
        "live_trading_authorized": lock["live_trading_authorized"],
    }
