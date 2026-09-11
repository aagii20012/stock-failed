"""Tests for the execution shell that need no keys, no network, no price cache.

This is the suite CI runs. The signal itself is covered by
``test_signal_parity.py``, which needs the gitignored price cache and so only
runs locally.
"""

from __future__ import annotations

import csv
import io
import json
import os
import sys
from datetime import date, datetime, timezone

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from faber_signal import DEFENSIVE, SECTORS, TOP_N, UNIVERSE  # noqa: E402
from paper_trade import (  # noqa: E402
    CASH_BUFFER,
    CLS_CUTOFF_ET,
    LOG_FIELDS,
    MAX_REPAIR_ATTEMPTS,
    SUBMIT_CASH_MARGIN,
    RunResult,
    append_log,
    fit_orders_to_cash,
    plan_orders,
    rebalance_trigger,
    render_summary,
    unfinished_rebalance,
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


def test_log_carries_the_signal_not_just_the_outcome():
    """The daily row has to be readable as a signal series on its own.

    Before the observation change the log recorded only what the account did,
    which on a non-rebalance day is nothing. These two columns are what make a
    month of idle rows worth keeping.
    """
    for required in ("momentum", "trend_ok"):
        assert required in LOG_FIELDS


def _write_row(path, **overrides):
    result = RunResult()
    for k, v in overrides.items():
        setattr(result, k, v)
    append_log(path, result, datetime(2026, 8, 25, 15, 0, tzinfo=timezone.utc))


def _read(path):
    with io.open(path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        return reader.fieldnames, list(reader)


def test_append_log_writes_a_header_once(tmp_path):
    log = str(tmp_path / "paper_log.csv")
    _write_row(log, action="SKIPPED")
    _write_row(log, action="HELD")
    header, rows = _read(log)
    assert header == LOG_FIELDS
    assert [r["action"] for r in rows] == ["SKIPPED", "HELD"]


def test_append_log_migrates_a_log_written_under_an_older_header(tmp_path):
    """A widened LOG_FIELDS must rewrite the file, not append ragged rows.

    Appending an 18-column row under a 16-column header still *parses* -- the
    extra values land in DictReader's restkey -- so nothing would fail until
    someone read the series back months later and found the columns misaligned.
    """
    log = str(tmp_path / "paper_log.csv")
    old_fields = [f for f in LOG_FIELDS if f not in ("momentum", "trend_ok")]
    with io.open(log, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=old_fields)
        w.writeheader()
        w.writerow({f: "" for f in old_fields}
                   | {"ts_utc": "2026-08-24T15:41:43Z", "action": "SKIPPED",
                      "detail": "cold start, comma, and \"quotes\" preserved"})

    _write_row(log, action="HELD", momentum={"XLK": 0.34}, trend_ok={"XLK": True})

    header, rows = _read(log)
    assert header == LOG_FIELDS
    assert len(rows) == 2
    # the earlier row survives verbatim and is padded, not dropped
    assert rows[0]["ts_utc"] == "2026-08-24T15:41:43Z"
    assert rows[0]["detail"] == 'cold start, comma, and "quotes" preserved'
    assert rows[0]["momentum"] == "" and rows[0]["trend_ok"] == ""
    # and the new row actually carries the new columns
    assert json.loads(rows[1]["momentum"]) == {"XLK": 0.34}
    assert json.loads(rows[1]["trend_ok"]) == {"XLK": True}

    # a subsequent append is a plain append, not a second rewrite
    _write_row(log, action="REBALANCED")
    header, rows = _read(log)
    assert header == LOG_FIELDS
    assert [r["action"] for r in rows] == ["SKIPPED", "HELD", "REBALANCED"]


def test_summary_does_not_read_as_a_trade_on_an_observation_day():
    """The same target table appears whether or not we traded; say which."""
    now = datetime(2026, 8, 25, 15, 0, tzinfo=timezone.utc)
    weights = {"XLE": 1 / 3, "XLK": 1 / 3, "XLV": 1 / 3}

    observed = render_summary(
        RunResult(action="SKIPPED", rebalance_day=False, signal_month="2026-07",
                  ranked=["XLE", "XLK", "XLV"], target_weights=weights), now)
    traded = render_summary(
        RunResult(action="REBALANCED", rebalance_day=True, signal_month="2026-08",
                  ranked=["XLE", "XLK", "XLV"], target_weights=weights), now)

    assert "nothing traded" in observed
    assert "nothing traded" not in traded
    assert "### Target (signal month 2026-08)" in traded


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


# --------------------------------------------------------------------------- #
# fitting the basket to the money behind it
#
# Sizing is done against equity and the orders are paid for out of cash, and
# for the first two rebalances nothing reconciled the two. On 2026-09-01 the
# run sent $75,087 of buys against $75,180.91 of cash and all three orders
# expired part-filled.
# --------------------------------------------------------------------------- #

PRICES = {"XLE": 64.79, "XLK": 184.66, "XLV": 172.22, "XLB": 100.0}


def _notional(orders, side):
    return sum(o["qty"] * PRICES[o["symbol"]] for o in orders if o["side"] == side)


def test_fit_leaves_an_affordable_basket_alone():
    orders = [{"symbol": "XLE", "side": "buy", "qty": 100, "have": 0, "want": 100}]
    assert fit_orders_to_cash(orders, PRICES, 100_000.0, SUBMIT_CASH_MARGIN) is orders


def test_fit_trims_the_basket_that_actually_expired():
    """The 2026-09-01 submission, to the share and to the cent."""
    orders = [
        {"symbol": "XLE", "side": "buy", "qty": 513, "have": 0, "want": 513},
        {"symbol": "XLK", "side": "buy", "qty": 180, "have": 0, "want": 180},
        {"symbol": "XLV", "side": "buy", "qty": 50, "have": 143, "want": 193},
    ]
    cash = 75_180.91
    assert _notional(orders, "buy") > cash * (1 - SUBMIT_CASH_MARGIN)

    fitted = fit_orders_to_cash(orders, PRICES, cash, SUBMIT_CASH_MARGIN)

    assert _notional(fitted, "buy") <= cash * (1 - SUBMIT_CASH_MARGIN)
    # Trimmed proportionally: an equal-weight basket stays equal-weight rather
    # than filling XLE and starving XLV.
    assert [o["qty"] for o in fitted] == [503, 176, 49]


def test_fit_rewrites_want_so_the_repair_check_can_ever_be_satisfied():
    """A trimmed order's target is the trimmed one, or the repair loops.

    ``unfinished_rebalance`` measures holdings against the recorded target. If
    that stayed at the pre-trim number the account could never reach it, and
    every run for the rest of the month would file another repair.
    """
    orders = [{"symbol": "XLE", "side": "buy", "qty": 513, "have": 40, "want": 553}]
    fitted = fit_orders_to_cash(orders, PRICES, 10_000.0, SUBMIT_CASH_MARGIN)
    assert fitted[0]["want"] == fitted[0]["have"] + fitted[0]["qty"]
    assert fitted[0]["want"] < 553


def test_fit_counts_sell_proceeds_so_a_rotation_still_trades():
    """The failure mode of a naive cash check: no month ever rotates again.

    Fully invested, cash is ~0 and every buy is funded by that day's sells. A
    guard that looked at cash alone would trim every rotation to nothing.
    """
    orders = [
        {"symbol": "XLE", "side": "sell", "qty": 500, "have": 500, "want": 0},
        {"symbol": "XLB", "side": "buy", "qty": 300, "have": 0, "want": 300},
    ]
    fitted = fit_orders_to_cash(orders, PRICES, 100.0, SUBMIT_CASH_MARGIN)
    assert [o["qty"] for o in fitted] == [500, 300]


def test_fit_drops_a_buy_trimmed_out_of_existence():
    orders = [{"symbol": "XLK", "side": "buy", "qty": 2, "have": 0, "want": 2}]
    assert fit_orders_to_cash(orders, PRICES, 10.0, SUBMIT_CASH_MARGIN) == []


# --------------------------------------------------------------------------- #
# noticing that a rebalance did not finish
# --------------------------------------------------------------------------- #

SIZED = {"XLE": 513, "XLK": 180, "XLV": 193}          # 2026-09-01 targets
HELD_SHORT = {"XLE": 485, "XLK": 49, "XLV": 143}      # what actually filled
TRADED_AUG_SIZED = dict(TRADED_AUG, last_share_targets=SIZED)


def test_unfinished_rebalance_sees_the_2026_09_01_shortfall():
    missed = unfinished_rebalance(TRADED_AUG_SIZED, HELD_SHORT)
    assert set(missed) == {"XLE", "XLK", "XLV"}
    assert missed["XLK"] == {"have": 49, "want": 180}


def test_unfinished_rebalance_ignores_a_whole_share_rounding_miss():
    missed = unfinished_rebalance(TRADED_AUG_SIZED, {"XLE": 512, "XLK": 180, "XLV": 193})
    assert missed == {}


def test_unfinished_rebalance_counts_a_position_the_target_does_not_name():
    """The target is the whole portfolio, so a leftover is a miss of its size."""
    missed = unfinished_rebalance(TRADED_AUG_SIZED, dict(SIZED, XLU=200))
    assert missed == {"XLU": {"have": 200, "want": 0}}


def test_unfinished_rebalance_is_quiet_with_nothing_to_measure_against():
    assert unfinished_rebalance(TRADED_AUG, HELD_SHORT) == {}
    assert unfinished_rebalance(TRADED_AUG_SIZED, None) == {}


# state.json as committed on 2026-09-04, before last_share_targets existed.
# Copied rather than read from disk on purpose: once this change ships the real
# file grows the field, and a test that read it would quietly stop covering the
# fallback on the very next run.
STATE_BEFORE_SHARE_TARGETS = {
    "last_action": "HELD",
    "last_rebalance_date": "2026-09-01",
    "last_rebalance_signal_month": "2026-08",
    "submitted_orders": [
        {"symbol": "XLE", "side": "buy", "qty": 513, "have": 0, "want": 513},
        {"symbol": "XLK", "side": "buy", "qty": 180, "have": 0, "want": 180},
        {"symbol": "XLV", "side": "buy", "qty": 50, "have": 143, "want": 193},
    ],
}


def test_unfinished_rebalance_falls_back_to_the_submitted_orders():
    """The live state.json predates last_share_targets and is the broken one.

    Without this the first run after the change finds nothing to measure,
    reports HELD exactly as it has every day since 2026-09-02, and leaves the
    account a third in cash until October.
    """
    missed = unfinished_rebalance(STATE_BEFORE_SHARE_TARGETS, HELD_SHORT)
    assert missed["XLK"] == {"have": 49, "want": 180}
    assert set(missed) == {"XLE", "XLK", "XLV"}


def test_trigger_repairs_the_position_the_account_is_actually_in():
    """End to end on the real 2026-09 state: the run after this ships trades."""
    t = rebalance_trigger(STATE_BEFORE_SHARE_TARGETS, date(2026, 9, 8), False,
                          FIRST_TD, False, HELD_SHORT)
    assert t.due and t.repair


def test_the_submitted_orders_fallback_cannot_invent_a_leftover():
    """It only knows the symbols that needed an order, so it judges only those.

    A symbol already at target gets no order and so is absent from
    ``submitted_orders``; reading that absence as "want 0" would liquidate a
    correct position.
    """
    state = {"submitted_orders": [{"symbol": "XLE", "want": 513}]}
    assert unfinished_rebalance(state, {"XLE": 513, "XLV": 143}) == {}


def test_trigger_repairs_a_rebalance_that_did_not_reach_its_target():
    """Traded is not filled -- the distinction this whole branch exists for."""
    t = rebalance_trigger(TRADED_AUG_SIZED, MID_MONTH, False, FIRST_TD, False,
                          HELD_SHORT)
    assert t.due and t.repair and t.catch_up
    assert "XLK 49/180" in t.reason and "attempt 1 of" in t.reason


def test_trigger_holds_when_the_target_is_genuinely_held():
    t = rebalance_trigger(TRADED_AUG_SIZED, MID_MONTH, False, FIRST_TD, False, SIZED)
    assert not t.due and t.action == "HELD" and not t.exhausted
    assert "already traded" in t.reason


def test_trigger_gives_up_after_the_attempt_cap():
    """A residual that will not fill must not be resubmitted every day."""
    state = dict(TRADED_AUG_SIZED,
                 repair_attempts={"2026-08": MAX_REPAIR_ATTEMPTS})
    t = rebalance_trigger(state, MID_MONTH, False, FIRST_TD, False, HELD_SHORT)
    assert not t.due and t.action == "HELD" and t.exhausted
    assert "STALLED" in t.headline


def test_trigger_repair_does_not_pre_empt_a_real_rebalance_day():
    """A new month's signal outranks last month's unfinished business."""
    state = dict(TRADED_JUL, last_share_targets=SIZED)
    t = rebalance_trigger(state, FIRST_TD, True, FIRST_TD, False, HELD_SHORT)
    assert t.due and not t.repair
    assert "first trading day" in t.reason


def test_log_records_what_the_orders_actually_did():
    """The fill detail was fetched on every run and persisted on none of them.

    A HELD day posts no issue, so the 2026-09-01 fills -- resolved by the
    2026-09-02 run -- existed only in that run's stdout.
    """
    for required in ("fills", "buying_power"):
        assert required in LOG_FIELDS


def test_log_row_carries_the_fill_quantities(tmp_path):
    log = str(tmp_path / "paper_log.csv")
    _write_row(log, action="HELD", buying_power=34_759.88, fills=[
        {"symbol": "XLK", "side": "buy", "qty": 180, "status": "expired",
         "filled_qty": "49", "filled_avg_price": "184.66"},
    ])
    _, rows = _read(log)
    assert json.loads(rows[0]["fills"])[0]["filled_qty"] == "49"
    assert rows[0]["buying_power"] == "34759.88"
