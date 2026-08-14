"""The synthetic instrument the hand calculation was done on.

FIXT is built here from the *sealed* spec rather than restated, so the bars the engine runs on and the
bars the arithmetic was done on cannot drift apart. If someone edited the sealed file, the seal check
in :mod:`stockedge100.backtest.config` fails before any of this loads.

FIXT is not a research instrument and carries no research meaning. It exists so that eight sessions
of engine output can be checked against arithmetic a person did on paper.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Any

from stockedge100.backtest.config import Stage2Config, load_stage2_config
from stockedge100.backtest.dataset import PriceSeries, series_from_rows
from stockedge100.backtest.probes import FixedScheduleProbe
from stockedge100.backtest.window import ResearchWindow, development_window

FIXT = "FIXT"
ENTRY_DECISION = dt.date(2015, 1, 6)
EXIT_DECISION = dt.date(2015, 1, 8)


def fixture_spec(config: Stage2Config | None = None) -> dict[str, Any]:
    cfg = config or load_stage2_config()
    return cfg.engine_spec["hand_calculated_fixtures"]


def fixt_series(config: Stage2Config | None = None) -> PriceSeries:
    """The eight sealed bars, as the engine will see them."""
    rows = fixture_spec(config)["instrument"]["sessions"]
    return series_from_rows(FIXT, rows)


def fixt_window() -> ResearchWindow:
    """FIXT's sessions sit inside the development window, so the ordinary guard applies unchanged."""
    return development_window()


def fixt_probe(budget: Decimal) -> FixedScheduleProbe:
    """The sealed schedule: enter on the close of 2015-01-06, exit on the close of 2015-01-08."""
    return FixedScheduleProbe(
        symbol=FIXT,
        entry_session=ENTRY_DECISION,
        exit_session=EXIT_DECISION,
        budget=budget,
    )


def expected(scenario: str, config: Stage2Config | None = None) -> dict[str, Any]:
    """The sealed hand-calculated expectations for one cost scenario."""
    return fixture_spec(config)[f"FIXT_{scenario}_COSTS"]


def fixt_sessions(config: Stage2Config | None = None) -> tuple[dt.date, ...]:
    rows = fixture_spec(config)["instrument"]["sessions"]
    return tuple(dt.date.fromisoformat(row["session"]) for row in rows)
