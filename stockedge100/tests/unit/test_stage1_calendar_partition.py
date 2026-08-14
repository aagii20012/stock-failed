"""Stage 1 — the trading calendar and the constitution section 6.1 partition arithmetic.

Pure functions only: no network, no provider data, nothing read from ``data/``. These are the two
pieces of Stage 1 whose correctness cannot be argued from the evidence files, because the evidence
files were produced *by* them. They have to be checked against independently known facts about the
US equity trading calendar and against section 6.1 read literally.

The partition is the single most consequential calculation in the stage: once it is locked the
holdout is sealed, and no later stage may move it.
"""

from __future__ import annotations

import datetime as dt

import pytest

from stockedge100.data.calendar import (
    CALENDAR_NAME,
    calendar_bounds,
    is_session,
    last_session_of_month,
    longest_missing_run,
    missing_sessions,
    sessions_between,
)
from stockedge100.data.partition import (
    HOLDOUT_MONTHS,
    MINIMUM_DEVELOPMENT_YEARS,
    VALIDATION_MONTHS,
    compute_partition,
)


def d(text: str) -> dt.date:
    return dt.date.fromisoformat(text)


# --------------------------------------------------------------------------------------------
# Calendar: checked against independently known facts, not against the price provider
# --------------------------------------------------------------------------------------------


def test_calendar_is_the_nyse_calendar_and_predates_the_oldest_candidate():
    """SPY listed 1993-01-29; a calendar starting later would leave those sessions unverifiable."""
    assert CALENDAR_NAME == "XNYS"
    first, last = calendar_bounds()
    assert first <= d("1993-01-29")
    assert last >= d("2026-07-31")


@pytest.mark.parametrize(
    "day",
    [
        "2020-12-25",  # Christmas
        "2021-01-01",  # New Year's Day
        "2015-07-03",  # Independence Day observed on the Friday
        "2012-10-29",  # Hurricane Sandy, an unscheduled closure
        "2015-01-03",  # a Saturday
    ],
)
def test_known_non_sessions_are_rejected(day: str):
    assert not is_session(d(day))


@pytest.mark.parametrize("day", ["1993-01-29", "2015-01-02", "2021-07-30", "2020-11-27"])
def test_known_sessions_are_accepted(day: str):
    assert is_session(d(day))


def test_last_session_of_month_is_the_last_trading_day_not_the_last_calendar_day():
    assert last_session_of_month(2021, 7) == d("2021-07-30")  # 31st was a Saturday
    assert last_session_of_month(2020, 5) == d("2020-05-29")  # 30th/31st weekend
    assert last_session_of_month(2026, 7) == d("2026-07-31")  # a Friday, so month-end coincides


def test_sessions_between_is_inclusive_and_ordered():
    window = sessions_between(d("2015-01-02"), d("2015-03-31"))
    assert window[0] == d("2015-01-02")
    assert window[-1] == d("2015-03-31")
    assert window == sorted(window)
    assert len(set(window)) == len(window)
    assert d("2015-01-19") not in window  # Martin Luther King Jr. Day


def test_sessions_between_refuses_ranges_outside_its_own_bounds():
    """Silently returning "no sessions" for an out-of-range request would fake completeness."""
    low, high = calendar_bounds()
    with pytest.raises(ValueError):
        sessions_between(low - dt.timedelta(days=365), high)
    with pytest.raises(ValueError):
        sessions_between(low, high + dt.timedelta(days=365))


def test_sessions_between_empty_for_a_reversed_range():
    assert sessions_between(d("2015-03-31"), d("2015-01-02")) == []


def test_missing_sessions_finds_the_gap_and_ignores_weekends():
    window = sessions_between(d("2015-01-02"), d("2015-01-30"))
    observed = [day for day in window if day not in {d("2015-01-13"), d("2015-01-14")}]
    assert missing_sessions(observed, d("2015-01-02"), d("2015-01-30")) == [
        d("2015-01-13"),
        d("2015-01-14"),
    ]
    assert missing_sessions(window, d("2015-01-02"), d("2015-01-30")) == []


def test_longest_missing_run_counts_calendar_adjacency_not_date_adjacency():
    """A Friday and the following Monday are consecutive *sessions*: that is a run of two."""
    friday, monday = d("2015-01-09"), d("2015-01-12")
    assert (friday.weekday(), monday.weekday()) == (4, 0)
    assert longest_missing_run([friday, monday], d("2015-01-02"), d("2015-01-30")) == 2
    # Two isolated gaps a week apart are two runs of one, not one run of two.
    assert longest_missing_run([friday, d("2015-01-20")], d("2015-01-02"), d("2015-01-30")) == 1
    assert longest_missing_run([], d("2015-01-02"), d("2015-01-30")) == 0


# --------------------------------------------------------------------------------------------
# Section 6.1: exclude the incomplete cutoff month, 24-month holdout, 36-month validation,
# everything earlier is development subject to a five-year floor.
# --------------------------------------------------------------------------------------------


def test_incomplete_cutoff_month_is_excluded():
    """2026-08-07 is mid-month, so August 2026 cannot contribute to any window."""
    partition = compute_partition(d("2026-08-07"), d("1993-01-29"))
    assert partition.cutoff_month == "2026-08"
    assert partition.cutoff_month_complete is False
    assert partition.last_complete_month == "2026-07"
    assert partition.holdout_end == "2026-07-31"


def test_complete_cutoff_month_is_kept():
    """A cutoff on the month's final *session* completes the month even if calendar days remain."""
    partition = compute_partition(d("2021-07-30"), d("2015-01-02"))
    assert partition.cutoff_month_complete is True
    assert partition.cutoff_month_last_session == "2021-07-30"
    assert partition.last_complete_month == "2021-07"
    assert partition.holdout_end == "2021-07-31"


def test_one_session_short_of_month_end_drops_the_month():
    partition = compute_partition(d("2021-07-29"), d("2015-01-02"))
    assert partition.cutoff_month_complete is False
    assert partition.last_complete_month == "2021-06"
    assert partition.holdout_end == "2021-06-30"


def test_holdout_is_exactly_twenty_four_months_and_validation_exactly_thirty_six():
    partition = compute_partition(d("2026-08-07"), d("1993-01-29"))
    assert (HOLDOUT_MONTHS, VALIDATION_MONTHS) == (24, 36)
    assert (partition.holdout_start, partition.holdout_end) == ("2024-08-01", "2026-07-31")
    assert (partition.validation_start, partition.validation_end) == ("2021-08-01", "2024-07-31")

    def months(start: str, end: str) -> int:
        a, b = d(start), d(end)
        return (b.year - a.year) * 12 + (b.month - a.month) + 1

    assert months(partition.holdout_start, partition.holdout_end) == HOLDOUT_MONTHS
    assert months(partition.validation_start, partition.validation_end) == VALIDATION_MONTHS


def test_windows_are_contiguous_and_non_overlapping():
    partition = compute_partition(d("2026-08-07"), d("1993-01-29"))
    assert d(partition.development_end) + dt.timedelta(days=1) == d(partition.validation_start)
    assert d(partition.validation_end) + dt.timedelta(days=1) == d(partition.holdout_start)
    assert d(partition.development_start) < d(partition.development_end)
    assert d(partition.holdout_end) <= d(partition.usable_cutoff_session)


def test_every_window_boundary_starts_and_ends_on_a_month_boundary():
    """A boundary mid-month would mean a partial month leaked across a window edge."""
    partition = compute_partition(d("2026-08-07"), d("1993-01-29"))
    for start in (partition.validation_start, partition.holdout_start):
        assert d(start).day == 1
    for end in (partition.development_end, partition.validation_end, partition.holdout_end):
        following = d(end) + dt.timedelta(days=1)
        assert following.day == 1


def test_development_start_is_the_earliest_session_in_the_dataset():
    partition = compute_partition(d("2026-08-07"), d("1993-01-29"))
    assert partition.development_start == "1993-01-29"


def test_minimum_development_length_is_reported_not_silently_satisfied():
    long_history = compute_partition(d("2026-08-07"), d("1993-01-29"))
    assert long_history.development_years > MINIMUM_DEVELOPMENT_YEARS
    assert long_history.meets_minimum_development is True

    short_history = compute_partition(d("2021-07-30"), d("2015-01-02"))
    assert short_history.development_years < MINIMUM_DEVELOPMENT_YEARS
    assert short_history.meets_minimum_development is False


@pytest.mark.parametrize(
    "session,expected",
    [
        ("1993-01-29", "development"),
        ("2021-07-30", "development"),
        ("2021-08-02", "validation"),
        ("2024-07-31", "validation"),
        ("2024-08-01", "holdout"),
        ("2026-07-31", "holdout"),
        ("2026-08-03", "excluded_after_cutoff"),
        ("1990-01-02", "excluded_before_start"),
    ],
)
def test_window_of_classifies_every_boundary_session(session: str, expected: str):
    partition = compute_partition(d("2026-08-07"), d("1993-01-29"))
    assert partition.window_of(session) == expected
    assert partition.window_of(d(session)) == expected


def test_partition_is_immutable_once_computed():
    """A partition that can be mutated in place is not a lock."""
    partition = compute_partition(d("2026-08-07"), d("1993-01-29"))
    with pytest.raises(Exception):
        partition.holdout_start = "2025-01-01"  # type: ignore[misc]


def test_partition_depends_only_on_the_two_declared_inputs():
    """Same cutoff and same earliest session must give the same boundaries, every time."""
    first = compute_partition(d("2026-08-07"), d("1993-01-29"))
    second = compute_partition(d("2026-08-07"), d("1993-01-29"))
    assert first == second
    assert first.to_json() == second.to_json()
