"""The constitution §6.1 prospective time partition.

Pure arithmetic on calendar months, deliberately kept free of any dependency on price data beyond
two dates. It is the single most consequential calculation in Stage 1: once it is locked, the
holdout is sealed and no later stage may move it.

§6.1, verbatim:

1. Exclude the incomplete cutoff month.
2. Lock the most recent 24 complete calendar months as the final holdout.
3. Lock the preceding 36 complete calendar months as validation/walk-forward assessment.
4. Use all earlier eligible history as development, subject to a minimum of five years.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, asdict
from typing import Any

from stockedge100.data.calendar import last_session_of_month

HOLDOUT_MONTHS = 24
VALIDATION_MONTHS = 36
MINIMUM_DEVELOPMENT_YEARS = 5


def _month_start(year: int, month: int) -> dt.date:
    return dt.date(year, month, 1)


def _shift_months(year: int, month: int, delta: int) -> tuple[int, int]:
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1


def _month_end(year: int, month: int) -> dt.date:
    nyear, nmonth = _shift_months(year, month, 1)
    return _month_start(nyear, nmonth) - dt.timedelta(days=1)


@dataclass(frozen=True)
class TimePartition:
    """A computed, lockable partition. Every boundary is an inclusive calendar date."""

    usable_cutoff_session: str
    cutoff_month: str
    cutoff_month_complete: bool
    cutoff_month_last_session: str
    last_complete_month: str

    development_start: str
    development_end: str
    validation_start: str
    validation_end: str
    holdout_start: str
    holdout_end: str

    development_years: float
    minimum_development_years: int
    meets_minimum_development: bool
    holdout_months: int
    validation_months: int

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    def window_of(self, session: dt.date | str) -> str:
        """Which partition a session belongs to: development, validation, holdout, or excluded."""
        day = dt.date.fromisoformat(session) if isinstance(session, str) else session
        if day > dt.date.fromisoformat(self.holdout_end):
            return "excluded_after_cutoff"
        if day >= dt.date.fromisoformat(self.holdout_start):
            return "holdout"
        if day >= dt.date.fromisoformat(self.validation_start):
            return "validation"
        if day >= dt.date.fromisoformat(self.development_start):
            return "development"
        return "excluded_before_start"


def compute_partition(usable_cutoff: dt.date, earliest_session: dt.date) -> TimePartition:
    """Apply §6.1 to a frozen usable-data cutoff and the earliest session in the dataset.

    ``usable_cutoff`` is the last session actually present in the acquired data, not today's date.
    The cutoff month counts as complete only if the cutoff is on or after that month's final
    trading session; otherwise it is the "incomplete cutoff month" §6.1 step 1 excludes.
    """
    month_last = last_session_of_month(usable_cutoff.year, usable_cutoff.month)
    complete = usable_cutoff >= month_last

    if complete:
        ly, lm = usable_cutoff.year, usable_cutoff.month
    else:
        ly, lm = _shift_months(usable_cutoff.year, usable_cutoff.month, -1)

    holdout_end = _month_end(ly, lm)
    hy, hm = _shift_months(ly, lm, -(HOLDOUT_MONTHS - 1))
    holdout_start = _month_start(hy, hm)

    validation_end = holdout_start - dt.timedelta(days=1)
    vy, vm = _shift_months(hy, hm, -VALIDATION_MONTHS)
    validation_start = _month_start(vy, vm)

    development_end = validation_start - dt.timedelta(days=1)
    development_start = earliest_session

    years = (development_end - development_start).days / 365.25

    return TimePartition(
        usable_cutoff_session=usable_cutoff.isoformat(),
        cutoff_month=f"{usable_cutoff.year:04d}-{usable_cutoff.month:02d}",
        cutoff_month_complete=complete,
        cutoff_month_last_session=month_last.isoformat(),
        last_complete_month=f"{ly:04d}-{lm:02d}",
        development_start=development_start.isoformat(),
        development_end=development_end.isoformat(),
        validation_start=validation_start.isoformat(),
        validation_end=validation_end.isoformat(),
        holdout_start=holdout_start.isoformat(),
        holdout_end=holdout_end.isoformat(),
        development_years=round(years, 4),
        minimum_development_years=MINIMUM_DEVELOPMENT_YEARS,
        meets_minimum_development=years >= MINIMUM_DEVELOPMENT_YEARS,
        holdout_months=HOLDOUT_MONTHS,
        validation_months=VALIDATION_MONTHS,
    )
