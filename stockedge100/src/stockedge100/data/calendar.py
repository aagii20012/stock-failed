"""Independent XNYS session calendar.

The point of this module is that it is *independent of the price provider*. Asking the provider
which days were trading days and then checking the provider's data against that answer would prove
nothing. ``exchange_calendars`` is maintained separately from Yahoo Finance, so a missing session,
a phantom session, or a timezone error shows up as a disagreement between two unrelated sources.

The calendar is pinned to start at 1990-01-01 because the oldest candidate ETF predates the
library's default 20-year window, and a session that falls outside the calendar's own bounds would
otherwise be silently unverifiable.
"""

from __future__ import annotations

import datetime as dt
import functools
from typing import Iterable

import exchange_calendars as xcals

CALENDAR_NAME = "XNYS"
CALENDAR_START = "1990-01-01"


@functools.lru_cache(maxsize=1)
def xnys():
    """The XNYS calendar, built once per process."""
    return xcals.get_calendar(CALENDAR_NAME, start=CALENDAR_START)


@functools.lru_cache(maxsize=1)
def _session_set() -> frozenset[dt.date]:
    cal = xnys()
    return frozenset(ts.date() for ts in cal.sessions)


def calendar_bounds() -> tuple[dt.date, dt.date]:
    cal = xnys()
    return cal.first_session.date(), cal.last_session.date()


def is_session(day: dt.date) -> bool:
    return day in _session_set()


def sessions_between(start: dt.date, end: dt.date) -> list[dt.date]:
    """Every XNYS trading session in ``[start, end]`` inclusive."""
    if start > end:
        return []
    lo, hi = calendar_bounds()
    if start < lo or end > hi:
        raise ValueError(
            f"requested range {start}..{end} falls outside the calendar bounds {lo}..{hi}; "
            "widen CALENDAR_START rather than assuming the sessions are absent"
        )
    index = xnys().sessions_in_range(start.isoformat(), end.isoformat())
    return [ts.date() for ts in index]


def last_session_of_month(year: int, month: int) -> dt.date:
    """Last XNYS session in the given calendar month.

    Used to decide whether the cutoff month is complete. Note this is the last *trading* session,
    not the last calendar day: a month whose final calendar days are a weekend is complete once its
    final Friday session has traded.
    """
    first = dt.date(year, month, 1)
    last = dt.date(year + (month == 12), month % 12 + 1, 1) - dt.timedelta(days=1)
    sessions = sessions_between(first, last)
    if not sessions:
        raise ValueError(f"no XNYS sessions in {year}-{month:02d}")
    return sessions[-1]


def missing_sessions(observed: Iterable[dt.date], start: dt.date, end: dt.date) -> list[dt.date]:
    """XNYS sessions in ``[start, end]`` that are absent from ``observed``."""
    have = set(observed)
    return [day for day in sessions_between(start, end) if day not in have]


def longest_missing_run(missing: list[dt.date], start: dt.date, end: dt.date) -> int:
    """Longest run of *consecutive* missing trading sessions.

    Consecutive means adjacent in the trading calendar, not adjacent by calendar date; a weekend or
    a market holiday does not break a run.
    """
    if not missing:
        return 0
    ordinal = {day: i for i, day in enumerate(sessions_between(start, end))}
    positions = sorted(ordinal[day] for day in missing if day in ordinal)
    best = run = 1
    for prev, current in zip(positions, positions[1:]):
        run = run + 1 if current == prev + 1 else 1
        best = max(best, run)
    return best
