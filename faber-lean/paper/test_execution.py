"""Tests for the execution shell that need no keys, no network, no price cache.

This is the suite CI runs. The signal itself is covered by
``test_signal_parity.py``, which needs the gitignored price cache and so only
runs locally.
"""

from __future__ import annotations

import os
import sys
from datetime import date

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from faber_signal import DEFENSIVE, SECTORS, TOP_N, UNIVERSE  # noqa: E402
from paper_trade import (  # noqa: E402
    CASH_BUFFER,
    CLS_CUTOFF_ET,
    LOG_FIELDS,
    RunResult,
    plan_orders,
    rebalance_trigger,
    render_summary,
    webhook_body,
    whole_share_targets,
)

FIRST_TD = date(2026, 9, 1)     # first NYSE trading day of September 2026
MID_MONTH = date(2026, 9, 10)
TRADED_AUG = {"last_rebalance_signal_month": "2026-08",
              "last_rebalance_date": "2026-09-01"}
TRADED_JUL = {"last_rebalance_signal_month": "2026-07",
              "last_rebalance_date": "2026-08-03"}


def test_universe_is_the_verified_one():
    assert SECTORS == ["XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB"]
    assert DEFENSIVE == "SHY"
    assert UNIVERSE == SECTORS + [DEFENSIVE]
    assert TOP_N == 3


def test_cls_cutoff_is_inside_alpacas_window():
    """Alpaca rejects CLS submitted after 15:50 ET, so ours must be earlier."""
    assert CLS_CUTOFF_ET < (15, 50)


def test_whole_share_targets_floor_and_respect_the_buffer():
    weights = {"XLK": 1 / 3, "XLE": 1 / 3, "SHY": 1 / 3}
    prices = {"XLK": 250.0, "XLE": 90.0, "SHY": 82.5}
    targets = whole_share_targets(weights, 100_000.0, prices, CASH_BUFFER)

    investable = 100_000.0 * (1 - CASH_BUFFER)
    assert targets == {
        "XLK": int(investable / 3 // 250.0),
        "XLE": int(investable / 3 // 90.0),
        "SHY": int(investable / 3 // 82.5),
    }
    # Flooring plus the buffer must never over-commit the account.
    notional = sum(targets[s] * prices[s] for s in targets)
    assert notional <= investable


def test_missing_price_refuses_to_size():
    with pytest.raises(RuntimeError, match="no usable price"):
        whole_share_targets({"XLK": 1.0}, 100_000.0, {"XLE": 90.0}, CASH_BUFFER)


def test_plan_orders_liquidates_what_is_no_longer_a_target():
    orders = plan_orders({"XLK": 100, "SHY": 400}, {"XLF": 250, "XLK": 40})
    by_symbol = {o["symbol"]: o for o in orders}
    assert by_symbol["XLF"] == {"symbol": "XLF", "side": "sell", "qty": 250,
                                "have": 250, "want": 0}
    assert by_symbol["XLK"]["side"] == "buy" and by_symbol["XLK"]["qty"] == 60
    assert by_symbol["SHY"]["side"] == "buy" and by_symbol["SHY"]["qty"] == 400


def test_plan_orders_puts_sells_first():
    """Sells fund the buys, so they must be submitted ahead of them."""
    orders = plan_orders({"XLK": 500, "XLE": 500}, {"XLP": 300, "XLU": 300})
    sides = [o["side"] for o in orders]
    assert sides == sorted(sides, key=lambda s: s != "sell")
    assert sides[:2] == ["sell", "sell"]


def test_plan_orders_is_empty_when_already_on_target():
    assert plan_orders({"XLK": 10, "SHY": 20}, {"XLK": 10, "SHY": 20}) == []


def test_log_fields_cover_every_written_key():
    """append_log uses a strict DictWriter; a missing field raises at runtime."""
    assert len(LOG_FIELDS) == len(set(LOG_FIELDS))
    for required in ("ts_utc", "action", "signal_month", "orders", "equity"):
        assert required in LOG_FIELDS


def test_summary_renders_for_every_action():
    from datetime import datetime, timezone

    now = datetime(2026, 9, 1, 14, 5, tzinfo=timezone.utc)
    for action in ("REBALANCED", "HELD", "SKIPPED", "DEFERRED", "ERROR"):
        r = RunResult(action=action, detail="d", signal_month="2026-08",
                      ranked=["XLK", "XLE", "XLV"], skipped=["XLV"],
                      target_weights={"XLK": 1 / 3, "XLE": 1 / 3, "SHY": 1 / 3},
                      orders=[{"symbol": "XLK", "side": "buy", "qty": 10,
                               "have": 0, "want": 10, "status": "accepted"}],
                      equity=100_000.0, cash=250.0, data_feed="sip")
        out = render_summary(r, now)
        assert action in out and "XLK" in out and "2026-08" in out
        assert webhook_body(r)


# --------------------------------------------------------------------------- #
# the rebalance trigger
# --------------------------------------------------------------------------- #

def test_trigger_fires_on_the_first_trading_day():
    t = rebalance_trigger(TRADED_JUL, FIRST_TD, True, FIRST_TD, False)
    assert t.due and not t.catch_up
    assert "first trading day" in t.reason


def test_trigger_will_not_trade_the_same_signal_twice():
    """The whole point of keying on the signal month, not the date."""
    for day in (FIRST_TD, MID_MONTH):
        # is_month_start is True on the first pass, so this also proves the
        # already-traded check runs ahead of the month-start check.
        t = rebalance_trigger(TRADED_AUG, day, day == FIRST_TD, FIRST_TD, False)
        assert not t.due and t.action == "HELD"
        assert "2026-08" in t.reason


def test_trigger_catches_up_a_dropped_scheduled_run():
    """GitHub can drop a scheduled run; a month must not be silently skipped."""
    t = rebalance_trigger(TRADED_JUL, MID_MONTH, False, FIRST_TD, False)
    assert t.due and t.catch_up
    assert "catch-up" in t.reason and "2026-08" in t.reason


def test_trigger_resumes_a_deferred_rebalance():
    state = dict(TRADED_JUL, pending_rebalance={"date": "2026-09-01",
                                                "reason": "past the MOC window"})
    t = rebalance_trigger(state, date(2026, 9, 2), False, FIRST_TD, False)
    assert t.due and t.catch_up
    assert "deferred from 2026-09-01" in t.reason


def test_trigger_does_not_enter_mid_month_on_a_cold_start():
    t = rebalance_trigger({}, MID_MONTH, False, FIRST_TD, False)
    assert not t.due and t.action == "SKIPPED"
    assert "force_rebalance" in t.reason


def test_trigger_cold_start_enters_on_the_first_trading_day():
    t = rebalance_trigger({}, FIRST_TD, True, FIRST_TD, False)
    assert t.due and not t.catch_up


def test_force_overrides_every_refusal():
    for state in ({}, TRADED_AUG, TRADED_JUL):
        t = rebalance_trigger(state, MID_MONTH, False, FIRST_TD, True)
        assert t.due and t.reason == "forced by workflow input"


def test_summary_survives_an_empty_result():
    from datetime import datetime, timezone

    out = render_summary(RunResult(action="SKIPPED", detail="holiday"),
                         datetime(2026, 7, 3, 14, 0, tzinfo=timezone.utc))
    assert "SKIPPED" in out
