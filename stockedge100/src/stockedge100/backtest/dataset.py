"""Normalized daily bars, read into exact decimal values.

The Stage 1 normalizer writes ``%.10f`` decimal text. Parsing it with ``float`` would discard the
exactness the format was chosen to preserve, so every price crosses into the engine as a
:class:`~decimal.Decimal` built from the original characters. ``volume`` stays an integer because it
is a count, not money.
"""

from __future__ import annotations

import csv
import datetime as dt
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Iterable, Iterator

from stockedge100.backtest.errors import BacktestError

PROJECT_ROOT = Path(__file__).resolve().parents[3]
NORMALIZED_DIR = PROJECT_ROOT / "data" / "normalized" / "daily"

COLUMNS = ("session", "open", "high", "low", "close", "adj_close", "volume", "dividend", "split_ratio")


@dataclass(frozen=True)
class Bar:
    session: dt.date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    adj_close: Decimal
    volume: int
    dividend: Decimal
    split_ratio: Decimal

    @property
    def has_dividend(self) -> bool:
        return self.dividend > 0

    @property
    def has_split(self) -> bool:
        return self.split_ratio > 0 and self.split_ratio != 1


@dataclass(frozen=True)
class PriceSeries:
    """One symbol's bars, indexed by session and ordered.

    ``sessions`` is the *observed* session list. It is deliberately not reconciled against the
    exchange calendar here: a gap between the two is a stale-data condition the engine must notice
    at the moment it matters, not something to paper over at load time.
    """

    symbol: str
    bars: dict[dt.date, Bar]
    sessions: tuple[dt.date, ...]

    @property
    def first_session(self) -> dt.date:
        return self.sessions[0]

    @property
    def last_session(self) -> dt.date:
        return self.sessions[-1]

    def get(self, session: dt.date) -> Bar | None:
        return self.bars.get(session)

    def prior_session(self, session: dt.date) -> dt.date | None:
        """The observed session immediately before ``session``, or ``None`` at the start."""
        index = self._index.get(session)
        if index is None or index == 0:
            return None
        return self.sessions[index - 1]

    def __post_init__(self) -> None:
        object.__setattr__(self, "_index", {day: i for i, day in enumerate(self.sessions)})

    def __len__(self) -> int:
        return len(self.sessions)


def _decimal(text: str, field: str, symbol: str, session: str) -> Decimal:
    try:
        return Decimal(text)
    except Exception as exc:  # pragma: no cover - malformed input path
        raise BacktestError(f"{symbol} {session}: could not parse {field}={text!r}") from exc


def load_series(symbol: str, *, directory: Path | None = None) -> PriceSeries:
    """Load one normalized symbol file into exact decimal bars."""
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
        raise BacktestError(f"{symbol}: normalized series is empty")
    return PriceSeries(symbol=symbol, bars=bars, sessions=tuple(sessions))


def load_dataset(symbols: Iterable[str], *, directory: Path | None = None) -> dict[str, PriceSeries]:
    """Load several symbols, in sorted order so the result never depends on caller iteration order."""
    return {symbol: load_series(symbol, directory=directory) for symbol in sorted(set(symbols))}


def series_from_rows(symbol: str, rows: Iterable[dict[str, str]]) -> PriceSeries:
    """Build a series from in-memory rows, for fixtures that must not touch the acquired data."""
    bars: dict[dt.date, Bar] = {}
    sessions: list[dt.date] = []
    for row in rows:
        session = dt.date.fromisoformat(row["session"])
        bars[session] = Bar(
            session=session,
            open=Decimal(row["open"]),
            high=Decimal(row.get("high", row["close"])),
            low=Decimal(row.get("low", row["close"])),
            close=Decimal(row["close"]),
            adj_close=Decimal(row.get("adj_close", row["close"])),
            volume=int(row.get("volume", 0)),
            dividend=Decimal(row.get("dividend", "0")),
            split_ratio=Decimal(row.get("split_ratio", "0")),
        )
        sessions.append(session)
    return PriceSeries(symbol=symbol, bars=bars, sessions=tuple(sorted(sessions)))


def iter_sessions(series: PriceSeries) -> Iterator[Bar]:
    for session in series.sessions:
        yield series.bars[session]
