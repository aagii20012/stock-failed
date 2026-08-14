"""The only way a strategy is allowed to see a price.

Look-ahead bias is not usually introduced by someone deciding to cheat. It arrives when a convenient
data structure holds the whole series and a loop indexes one element too far. The defence has to be
structural: the object handed to a decision *cannot* return tomorrow's bar, because it does not
accept the request.

:class:`MarketView` carries a hard visibility bound set at construction. It has no method that
widens it. The engine builds a fresh view for each decision session; a strategy holding a stale view
sees a smaller world, never a larger one, so even a retained reference cannot leak the future.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Iterable

from stockedge100.backtest.dataset import Bar, PriceSeries
from stockedge100.backtest.errors import LookAheadError
from stockedge100.backtest.window import ResearchWindow


class MarketView:
    """A read-only view of the dataset, visible only through ``as_of``."""

    __slots__ = ("_series", "_as_of", "_window")

    def __init__(
        self,
        series: dict[str, PriceSeries],
        as_of: dt.date,
        window: ResearchWindow,
    ) -> None:
        window.check(as_of, what="visibility bound")
        object.__setattr__(self, "_series", series)
        object.__setattr__(self, "_as_of", as_of)
        object.__setattr__(self, "_window", window)

    def __setattr__(self, name: str, value: object) -> None:
        """Refuse every rebinding, including the visibility bound.

        A widenable bound is not a bound. Moving it has to be impossible rather than merely
        discouraged, because the mistake this guards against is an ordinary one.
        """
        raise LookAheadError(
            f"MarketView is immutable; refusing to rebind {name!r}. To see a later session, ask the "
            "engine for the view belonging to that session."
        )

    @property
    def as_of(self) -> dt.date:
        """The last session whose data this view may reveal."""
        return self._as_of

    @property
    def symbols(self) -> tuple[str, ...]:
        return tuple(sorted(self._series))

    def _check(self, symbol: str, session: dt.date) -> dt.date:
        if session > self._as_of:
            raise LookAheadError(
                f"{symbol}: session {session.isoformat()} was requested from a view bounded at "
                f"{self._as_of.isoformat()}. Nothing after the decision session exists yet."
            )
        self._window.check(session, what=f"{symbol} session")
        return session

    def bar(self, symbol: str, session: dt.date) -> Bar | None:
        """One bar, or ``None`` if the symbol has no data for that session."""
        self._check(symbol, session)
        series = self._series.get(symbol)
        return None if series is None else series.get(session)

    def latest_bar(self, symbol: str) -> Bar | None:
        """The most recent visible bar for a symbol, which may be older than ``as_of``."""
        series = self._series.get(symbol)
        if series is None:
            return None
        for session in reversed(series.sessions):
            if session <= self._as_of and self._window.contains(session):
                return series.bars[session]
        return None

    def close(self, symbol: str, session: dt.date) -> Decimal | None:
        bar = self.bar(symbol, session)
        return None if bar is None else bar.close

    def history(self, symbol: str, count: int) -> list[Bar]:
        """The last ``count`` visible bars, oldest first. Never includes anything after ``as_of``."""
        series = self._series.get(symbol)
        if series is None or count <= 0:
            return []
        visible = [
            series.bars[day]
            for day in series.sessions
            if day <= self._as_of and self._window.contains(day)
        ]
        return visible[-count:]

    def has_data(self, symbol: str, session: dt.date) -> bool:
        return self.bar(symbol, session) is not None

    def last_session_of(self, symbol: str) -> dt.date | None:
        """The final session of a symbol's series.

        This is series metadata rather than a price, and the engine needs it to detect a delisting
        before it silently carries a position past the end of the data. It reveals no future value:
        it is a date, not a bar, and any attempt to read the bar at that date still goes through
        :meth:`bar` and is still bounded.
        """
        series = self._series.get(symbol)
        return None if series is None else series.last_session


def visible_symbols(series: dict[str, PriceSeries], symbols: Iterable[str] | None = None) -> tuple[str, ...]:
    """Sorted symbol tuple. Sorted at every boundary so no result depends on dict ordering."""
    return tuple(sorted(series if symbols is None else set(symbols) & set(series)))
