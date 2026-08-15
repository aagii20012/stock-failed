"""Measure the facts the Generation 2 Stage 3 pre-registration must state. ASCII output only.

Reads the *date* columns and (for coverage only) the presence of bars. It prints no price level and
computes no return: nothing here is a result, and nothing here may become one. Every session it
touches is on or before 2021-07-31.
"""

from __future__ import annotations

import calendar
import csv
import datetime as dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.data.calendar import sessions_between  # noqa: E402

DAILY = ROOT / "data" / "normalized" / "daily"
DEV_END = dt.date(2021, 7, 31)

UNIVERSE = tuple(
    __import__("json").loads(
        (ROOT / "governance" / "STAGE_1_UNIVERSE.json").read_text(encoding="utf-8")
    )["members"]
)


def month_offset(day: dt.date, months: int) -> dt.date:
    total = (day.year * 12 + day.month - 1) + months
    year, month = divmod(total, 12)
    month += 1
    last = calendar.monthrange(year, month)[1]
    return dt.date(year, month, min(day.day, last))


def sessions_of(symbol: str) -> list[dt.date]:
    path = DAILY / f"{symbol}.csv"
    out: list[dt.date] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            day = dt.date.fromisoformat(row["session"])
            if day <= DEV_END:
                out.append(day)
    return out


def main() -> int:
    first: dict[str, dt.date] = {}
    last: dict[str, dt.date] = {}
    counts: dict[str, int] = {}
    for symbol in UNIVERSE:
        days = sessions_of(symbol)
        first[symbol] = days[0]
        last[symbol] = days[-1]
        counts[symbol] = len(days)

    latest_first = max(first.values())
    latest_symbols = sorted(s for s in UNIVERSE if first[s] == latest_first)
    earliest_first = min(first.values())
    earliest_symbols = sorted(s for s in UNIVERSE if first[s] == earliest_first)
    print("universe members            :", len(UNIVERSE))
    print("earliest inception          :", earliest_first, earliest_symbols)
    print("latest inception            :", latest_first, latest_symbols)
    print("last dev session, min/max   :", min(last.values()), max(last.values()))
    ends_early = sorted(s for s in UNIVERSE if last[s] != max(last.values()))
    print("symbols ending early        :", ends_early)

    # Run start: the first exchange session S with month_offset(S, -12) >= latest inception, so a
    # twelve-month lookback has a reference bar for EVERY member. Common to all eighteen variants.
    all_sessions = sessions_between(dt.date(2007, 1, 1), DEV_END)
    run_start = None
    for day in all_sessions:
        if month_offset(day, -12) >= latest_first:
            run_start = day
            break
    print()
    print("run start (12m binding)     :", run_start, run_start.strftime("%A"))
    print("  month_offset(-12)         :", month_offset(run_start, -12))
    prior = [d for d in all_sessions if d < run_start][-1]
    print("  previous session          :", prior, "-> month_offset(-12) =", month_offset(prior, -12))

    run_end = max(last.values())
    run_sessions = [d for d in all_sessions if run_start <= d <= run_end]
    print("run end                     :", run_end)
    print("run sessions                :", len(run_sessions))

    # Every member must have a bar on the run start, else the first rebalance is degenerate.
    missing_at_start = []
    for symbol in UNIVERSE:
        days = set(sessions_of(symbol))
        if run_start not in days:
            missing_at_start.append(symbol)
    print("members with no bar at start:", missing_at_start)

    # Rebalance calendars, decided strictly backward: the first session whose calendar month (or
    # quarter) differs from the previous session's, plus the run's own first session.
    monthly = [run_sessions[0]]
    quarterly = [run_sessions[0]]
    for previous, day in zip(run_sessions, run_sessions[1:]):
        if day.month != previous.month:
            monthly.append(day)
            if day.month in (1, 4, 7, 10):
                quarterly.append(day)
    print()
    print("monthly rebalances          :", len(monthly), monthly[:3], "...", monthly[-2:])
    print("quarterly rebalances        :", len(quarterly), quarterly[:3], "...", quarterly[-2:])

    # Coverage of the union, for the report's descriptive table.
    union = sorted({d for s in UNIVERSE for d in sessions_of(s)})
    print()
    print("union sessions <= dev end   :", len(union), union[0], "->", union[-1])
    return 0


if __name__ == "__main__":
    sys.exit(main())
