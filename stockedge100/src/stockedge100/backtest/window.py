"""The research-window guard.

Stage 2 validates an engine. It has no need to read validation or holdout data and no authorization
to do so, and "we were careful not to" is not evidence. So the restriction is a piece of code that
raises, wrapped around every price the engine can see, with its boundaries read from
``governance/STAGE_1_HOLDOUT_LOCK.json`` rather than restated here — a second copy of the boundaries
would eventually be the copy that was wrong.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from stockedge100.backtest.config import load_partition_bounds
from stockedge100.backtest.errors import WindowViolation

DEVELOPMENT = "development"
VALIDATION = "validation"
HOLDOUT = "holdout"


def _as_date(value: dt.date | str) -> dt.date:
    return dt.date.fromisoformat(value) if isinstance(value, str) else value


@dataclass(frozen=True)
class ResearchWindow:
    """An inclusive session range, and the authority that permits reading it."""

    name: str
    start: dt.date
    end: dt.date

    def contains(self, session: dt.date | str) -> bool:
        day = _as_date(session)
        return self.start <= day <= self.end

    def check(self, session: dt.date | str, *, what: str = "session") -> dt.date:
        """Return the session, or raise if it falls outside the authorized window."""
        day = _as_date(session)
        if not self.contains(day):
            raise WindowViolation(
                f"{what} {day.isoformat()} lies outside the authorized {self.name} window "
                f"{self.start.isoformat()}..{self.end.isoformat()}. Stage 2 is authorized to read "
                "development data only; the validation window is LOCKED and the holdout is SEALED."
            )
        return day

    def clip(self, sessions: list[dt.date]) -> list[dt.date]:
        return [day for day in sessions if self.contains(day)]

    def to_json(self) -> dict[str, str]:
        return {"window": self.name, "start": self.start.isoformat(), "end": self.end.isoformat()}


def development_window() -> ResearchWindow:
    """The only window Stage 2 may read, taken from the Stage 1 lock."""
    bounds = load_partition_bounds()
    return ResearchWindow(
        name=DEVELOPMENT,
        start=_as_date(bounds["development_start"]),
        end=_as_date(bounds["development_end"]),
    )


def window_named(name: str) -> ResearchWindow:
    """Any locked window by name. Used by tests to prove the guard refuses the forbidden ones."""
    if name not in (DEVELOPMENT, VALIDATION, HOLDOUT):
        raise WindowViolation(f"unknown research window {name!r}")
    bounds = load_partition_bounds()
    return ResearchWindow(
        name=name,
        start=_as_date(bounds[f"{name}_start"]),
        end=_as_date(bounds[f"{name}_end"]),
    )
