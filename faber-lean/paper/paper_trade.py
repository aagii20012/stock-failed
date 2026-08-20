"""Faber sector rotation, paper-traded through Alpaca.

Execution shell around ``faber_signal.decide()``. It changes *where* the
strategy runs, not what it decides -- the signal module is replayed against the
tagged decision log by ``test_signal_parity.py`` and must stay bit-identical.

What one run does:

1. Ask Alpaca's calendar whether today is a trading day, and whether it is the
   first trading day of the month (LEAN's ``date_rules.month_start(SPY)``).
2. Report the status of orders the previous run submitted, so fills get
   confirmed somewhere.
3. On a rebalance day: pull ~2 years of split/dividend-adjusted daily closes,
   reduce to completed monthly closes, compute target weights, diff against
   current positions, and submit whole-share **market-on-close** orders.

Market-on-close is the deliberate choice. On daily data LEAN converts market
orders to MarketOnClose, so all 726 fills of the verified backtest landed on the
close of the first trading day of the month. Submitting ``TimeInForce.CLS``
here reproduces that exact fill bar. Alpaca accepts CLS any time before
15:50 ET, so a scheduled run in the morning has hours of slack.

Paper only. The trading client is constructed with ``paper=True`` and the base
URL is asserted before anything is sent; live keys do not authenticate against
the paper endpoint, so there is no key that makes this script trade real money.

    python paper_trade.py --dry-run              # needs keys, sends nothing
    python paper_trade.py --offline ../prices.csv --dry-run   # no keys at all
    python paper_trade.py                        # the real (paper) run
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import traceback
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from faber_signal import DEFENSIVE, TOP_N, UNIVERSE, Decision, decide

ET = ZoneInfo("America/New_York")
HERE = os.path.dirname(os.path.abspath(__file__))

# Calendar days of daily bars to pull. The signal needs 13 completed months;
# 760 days leaves ~24 months of runway so a long holiday stretch or a late
# vendor bar can never starve it.
LOOKBACK_DAYS = 760

# The Basic (free) data plan serves SIP history only for data older than 15
# minutes. Ask for slightly less than now so the request is always allowed.
END_LAG_MINUTES = 25

# Alpaca rejects CLS submitted after 15:50 ET. Stop a few minutes early rather
# than race the cutoff with a scheduled job that can start late.
CLS_CUTOFF_ET = (15, 45)

# LEAN's Settings.FreePortfolioValuePercentage default, kept for parity.
CASH_BUFFER = 0.0025

LOG_FIELDS = [
    "ts_utc", "ts_et", "action", "detail", "trading_day", "rebalance_day",
    "signal_month", "ranked", "skipped", "target_weights", "equity", "cash",
    "positions_before", "orders", "data_feed", "notes",
]


@dataclass
class RunResult:
    action: str = "ERROR"
    detail: str = ""
    headline: str = ""
    notify: bool = False
    signal_month: str = ""
    ranked: list = field(default_factory=list)
    skipped: list = field(default_factory=list)
    target_weights: dict = field(default_factory=dict)
    orders: list = field(default_factory=list)
    fills: list = field(default_factory=list)
    equity: float = 0.0
    cash: float = 0.0
    positions_before: dict = field(default_factory=dict)
    trading_day: bool = False
    rebalance_day: bool = False
    data_feed: str = ""
    notes: list = field(default_factory=list)
    error: str = ""

    def note(self, msg: str) -> None:
        self.notes.append(msg)
        print("note: " + msg)


# --------------------------------------------------------------------------- #
# state + logs
# --------------------------------------------------------------------------- #

def load_state(path: str) -> dict:
    if not os.path.exists(path):
        return {"version": 1}
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_state(path: str, state: dict) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2, sort_keys=True)
        fh.write("\n")


def append_log(path: str, result: RunResult, now_utc: datetime) -> None:
    """Append one row per run. Header is written only when the file is new."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    new = not os.path.exists(path) or os.path.getsize(path) == 0
    row = {
        "ts_utc": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ts_et": now_utc.astimezone(ET).strftime("%Y-%m-%d %H:%M:%S %Z"),
        "action": result.action,
        "detail": result.detail,
        "trading_day": result.trading_day,
        "rebalance_day": result.rebalance_day,
        "signal_month": result.signal_month,
        "ranked": " ".join(result.ranked),
        "skipped": " ".join(result.skipped),
        "target_weights": json.dumps(
            {k: round(v, 6) for k, v in sorted(result.target_weights.items())}
        ),
        "equity": f"{result.equity:.2f}",
        "cash": f"{result.cash:.2f}",
        "positions_before": json.dumps(dict(sorted(result.positions_before.items()))),
        "orders": json.dumps(result.orders),
        "data_feed": result.data_feed,
        "notes": " | ".join(result.notes),
    }
    with open(path, "a", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=LOG_FIELDS)
        if new:
            w.writeheader()
        w.writerow(row)


# --------------------------------------------------------------------------- #
# market data
# --------------------------------------------------------------------------- #

def fetch_daily_closes(data_client, now_utc: datetime, result: RunResult):
    """Split/dividend-adjusted daily closes for the universe, columns=symbol.

    Tries the consolidated tape first and degrades explicitly rather than
    silently: SIP (all US exchanges, free for data older than 15 minutes) ->
    delayed SIP -> IEX. IEX alone is one venue at a few percent of volume, so if
    the run lands there the fallback is recorded in the log and the notification.
    """
    from alpaca.common.exceptions import APIError
    from alpaca.data.enums import Adjustment, DataFeed
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame

    start = now_utc - timedelta(days=LOOKBACK_DAYS)
    end = now_utc - timedelta(minutes=END_LAG_MINUTES)

    last_error = None
    for feed in (DataFeed.SIP, DataFeed.DELAYED_SIP, DataFeed.IEX):
        try:
            bars = data_client.get_stock_bars(
                StockBarsRequest(
                    symbol_or_symbols=list(UNIVERSE),
                    timeframe=TimeFrame.Day,
                    start=start,
                    end=end,
                    adjustment=Adjustment.ALL,
                    feed=feed,
                )
            )
        except APIError as exc:
            last_error = exc
            result.note(f"feed {feed.value} rejected ({exc}); trying the next one")
            continue

        frame = bars.df
        if frame is None or frame.empty:
            last_error = RuntimeError("empty frame")
            result.note(f"feed {feed.value} returned no bars; trying the next one")
            continue

        result.data_feed = feed.value
        if feed is not DataFeed.SIP:
            result.note(
                f"DATA DEGRADED: using {feed.value} instead of the consolidated "
                "SIP tape; monthly closes may differ slightly from the backtest"
            )

        closes = frame["close"].unstack(level=0)
        # Daily bars are stamped at 00:00 ET (05:00/04:00 UTC). Dropping the tz
        # and normalising in UTC yields the trading date under that convention
        # and under a 00:00-UTC or 16:00-ET stamp alike; converting to ET first
        # would shift a 00:00-UTC stamp back a day and corrupt month boundaries.
        closes.index = closes.index.tz_localize(None).normalize()
        closes = closes.sort_index()
        return closes

    raise RuntimeError(f"no usable data feed for {UNIVERSE}: {last_error}")


def sizing_prices(data_client, symbols, closes, result: RunResult) -> dict:
    """Best available price per symbol for turning weights into share counts.

    A market-on-close order fills at a price nobody knows yet, so this only has
    to be close. The latest IEX trade (free, real time) beats yesterday's close;
    the close is the fallback when a symbol has not printed on IEX today.
    """
    prices = {s: float(closes[s].dropna().iloc[-1]) for s in symbols if s in closes}

    from alpaca.common.exceptions import APIError
    from alpaca.data.enums import DataFeed
    from alpaca.data.requests import StockLatestTradeRequest

    try:
        latest = data_client.get_stock_latest_trade(
            StockLatestTradeRequest(symbol_or_symbols=list(symbols), feed=DataFeed.IEX)
        )
    except APIError as exc:
        result.note(f"no live IEX prices ({exc}); sizing off the last daily close")
        return prices

    stale = []
    for s in symbols:
        trade = latest.get(s)
        if trade is not None and trade.price and trade.price > 0:
            prices[s] = float(trade.price)
        else:
            stale.append(s)
    if stale:
        result.note(f"sized {','.join(stale)} off the last daily close (no IEX print)")
    return prices


# --------------------------------------------------------------------------- #
# calendar
# --------------------------------------------------------------------------- #

def calendar_facts(trading_client, today_et: date):
    """(is_trading_day, is_first_trading_day_of_month, first_trading_day)."""
    from alpaca.trading.requests import GetCalendarRequest

    month_start = today_et.replace(day=1)
    days = trading_client.get_calendar(
        GetCalendarRequest(start=month_start, end=today_et)
    )
    dates = sorted(d.date if isinstance(d.date, date) else d.date.date() for d in days)
    if not dates:
        return False, False, None
    return today_et in dates, dates[0] == today_et, dates[0]


@dataclass
class Trigger:
    """Whether today's run should rebalance, and why (or why not)."""

    due: bool
    reason: str = ""        # why we are trading, or why we are not
    action: str = ""        # set only when not due: HELD or SKIPPED
    headline: str = ""      # set only when not due
    catch_up: bool = False  # due, but later than the backtest's rebalance day


def rebalance_trigger(state: dict, today_et: date, is_month_start: bool,
                      first_td, force: bool) -> Trigger:
    """Pure trigger decision -- no broker, no clock, no network.

    Keyed on the *signal month* (the last completed month) rather than on the
    calendar date. Two properties fall out of that. It is idempotent: a second
    run on the same day, or a re-dispatch, cannot trade the same signal twice.
    And it is self-healing: GitHub Actions can delay a scheduled run or drop it
    outright, and a date-keyed trigger would then skip that month's rebalance
    in silence -- something the backtest never does. Here the next weekday's
    run sees the month's signal is still untraded and catches up.
    """
    signal_month_due = str(pd.Period(today_et, freq="M") - 1)
    last_traded = state.get("last_rebalance_signal_month")
    pending = state.get("pending_rebalance")

    if force:
        return Trigger(True, "forced by workflow input")

    if last_traded == signal_month_due:
        return Trigger(
            False,
            f"the {signal_month_due} signal was already traded on "
            f"{state.get('last_rebalance_date')}",
            action="HELD",
            headline=f"Faber: holding, {signal_month_due} signal already traded",
        )

    if is_month_start:
        return Trigger(True, f"first trading day of {today_et:%B %Y}")

    if pending:
        return Trigger(
            True,
            f"deferred from {pending.get('date')}: {pending.get('reason')}",
            catch_up=True,
        )

    if last_traded:
        return Trigger(
            True,
            f"catch-up: the {signal_month_due} rebalance never ran (first "
            f"trading day of the month was {first_td}, last traded signal was "
            f"{last_traded})",
            catch_up=True,
        )

    # Cold start. Entering mid-month is an arbitrary entry date the backtest
    # never takes, so it is opt-in rather than automatic.
    return Trigger(
        False,
        "cold start: no rebalance on record and today is not the first trading "
        f"day of the month (that was {first_td}); dispatch the workflow with "
        "force_rebalance to enter now, or wait for next month's first trading day",
        action="SKIPPED",
        headline="Faber: idle, waiting for the 1st trading day to enter",
    )


# --------------------------------------------------------------------------- #
# order construction
# --------------------------------------------------------------------------- #

def whole_share_targets(weights: dict, equity: float, prices: dict,
                        cash_buffer: float) -> dict:
    """Weights -> integer share counts, floored, against a cash-buffered equity."""
    investable = equity * (1.0 - cash_buffer)
    targets = {}
    for symbol, weight in weights.items():
        price = prices.get(symbol)
        if not price or price <= 0:
            raise RuntimeError(f"no usable price for {symbol}; refusing to size it")
        targets[symbol] = int(math.floor(weight * investable / price))
    return targets


def plan_orders(targets: dict, current: dict) -> list:
    """Share deltas needed to move from ``current`` to ``targets``.

    Everything held that is not a target is liquidated, mirroring LEAN's
    ``set_holdings(..., liquidate_existing=True)``. Sells are ordered first so
    the buys they fund are submitted behind them.
    """
    orders = []
    for symbol in sorted(set(targets) | set(current)):
        have = current.get(symbol, 0)
        want = targets.get(symbol, 0)
        delta = want - have
        if delta == 0:
            continue
        orders.append({
            "symbol": symbol,
            "side": "buy" if delta > 0 else "sell",
            "qty": abs(delta),
            "have": have,
            "want": want,
        })
    orders.sort(key=lambda o: (o["side"] != "sell", o["symbol"]))
    return orders


def submit_orders(trading_client, orders: list, today_et: date, tif_name: str,
                  result: RunResult) -> list:
    """Submit each delta, recording what happened to it either way."""
    from alpaca.common.exceptions import APIError
    from alpaca.trading.enums import OrderSide, TimeInForce
    from alpaca.trading.requests import MarketOrderRequest

    tif = TimeInForce.CLS if tif_name == "cls" else TimeInForce.DAY
    submitted = []

    for order in orders:
        # Deterministic id: a second run on the same day is rejected by the
        # broker rather than doubling the position.
        client_order_id = f"faber-{today_et.isoformat()}-{order['symbol']}-{order['side']}"
        try:
            placed = trading_client.submit_order(
                MarketOrderRequest(
                    symbol=order["symbol"],
                    qty=order["qty"],
                    side=OrderSide.BUY if order["side"] == "buy" else OrderSide.SELL,
                    time_in_force=tif,
                    client_order_id=client_order_id,
                )
            )
        except APIError as exc:
            order = dict(order, status="REJECTED", error=str(exc)[:300],
                         tif=tif_name, client_order_id=client_order_id)
            result.note(f"order rejected: {order['side']} {order['qty']} "
                        f"{order['symbol']} -- {exc}")
            submitted.append(order)
            continue

        submitted.append(dict(
            order,
            status=str(getattr(placed.status, "value", placed.status)),
            tif=tif_name,
            client_order_id=client_order_id,
            order_id=str(placed.id),
        ))
        print(f"submitted {order['side']} {order['qty']} {order['symbol']} "
              f"tif={tif_name} ({order['have']} -> {order['want']})")

    return submitted


def check_previous_orders(trading_client, state: dict, result: RunResult) -> list:
    """Look up what the last run's orders actually did.

    Market-on-close fills hours after submission, so the submitting run can only
    ever report "sent". This is where a fill gets confirmed.
    """
    from alpaca.common.exceptions import APIError

    pending = state.get("submitted_orders") or []
    if not pending:
        return []

    fills = []
    for order in pending:
        oid = order.get("order_id")
        if not oid:
            continue
        try:
            live = trading_client.get_order_by_id(oid)
        except APIError as exc:
            fills.append({**{k: order[k] for k in ("symbol", "side", "qty")},
                          "status": "LOOKUP_FAILED", "error": str(exc)[:200]})
            continue
        status = str(getattr(live.status, "value", live.status))
        fills.append({
            "symbol": order["symbol"],
            "side": order["side"],
            "qty": order["qty"],
            "status": status,
            "filled_qty": str(live.filled_qty or "0"),
            "filled_avg_price": str(live.filled_avg_price or ""),
            "filled_at": live.filled_at.isoformat() if live.filled_at else "",
        })

    unfilled = [f for f in fills if f["status"] not in ("filled",)]
    if unfilled:
        result.note(
            f"{len(unfilled)}/{len(fills)} order(s) from "
            f"{state.get('last_rebalance_date')} are not filled: "
            + ", ".join(f"{f['symbol']} {f['status']}" for f in unfilled)
        )
    else:
        result.note(f"all {len(fills)} order(s) from "
                    f"{state.get('last_rebalance_date')} filled")
    return fills


# --------------------------------------------------------------------------- #
# reporting
# --------------------------------------------------------------------------- #

def render_summary(result: RunResult, now_utc: datetime) -> str:
    icon = {"REBALANCED": "🔁", "HELD": "✅", "SKIPPED": "💤",
            "DEFERRED": "⏳", "ERROR": "❌"}.get(result.action, "•")
    et = now_utc.astimezone(ET).strftime("%Y-%m-%d %H:%M %Z")

    lines = [
        f"## {icon} {result.action} — {result.detail}",
        "",
        f"`{et}` · trading day: **{result.trading_day}** · "
        f"rebalance day: **{result.rebalance_day}**",
        "",
    ]

    if result.equity:
        lines += [f"**Equity** ${result.equity:,.2f} · **Cash** ${result.cash:,.2f}", ""]

    if result.target_weights:
        lines += ["### Target (signal month " + result.signal_month + ")", "",
                  "| symbol | weight | note |", "|---|---|---|"]
        for sym, w in sorted(result.target_weights.items(),
                             key=lambda kv: -kv[1]):
            note = "defensive (trend filter)" if sym == DEFENSIVE else ""
            lines.append(f"| {sym} | {w:.1%} | {note} |")
        lines += ["", f"Momentum top-{TOP_N}: `{' '.join(result.ranked)}`"]
        if result.skipped:
            lines.append(f"Below 10-month SMA → {DEFENSIVE}: "
                         f"`{' '.join(result.skipped)}`")
        lines.append("")

    if result.orders:
        lines += ["### Orders", "", "| symbol | side | qty | held → target | status |",
                  "|---|---|---|---|---|"]
        for o in result.orders:
            lines.append(f"| {o['symbol']} | {o['side']} | {o['qty']} | "
                         f"{o.get('have')} → {o.get('want')} | "
                         f"{o.get('status', '?')} |")
        lines += ["", "_Market-on-close: these fill at today's 16:00 ET close, "
                      "matching the backtest's fill bar. The next run confirms them._",
                  ""]

    if result.fills:
        lines += ["### Previous orders", "",
                  "| symbol | side | qty | status | filled @ |", "|---|---|---|---|---|"]
        for f in result.fills:
            lines.append(f"| {f['symbol']} | {f['side']} | {f['qty']} | "
                         f"{f['status']} | {f.get('filled_avg_price', '')} |")
        lines.append("")

    if result.positions_before:
        held = ", ".join(f"{k} {v}" for k, v in sorted(result.positions_before.items()))
        lines += [f"**Positions at run start:** {held or 'none'}", ""]

    if result.notes:
        lines += ["<details><summary>Notes</summary>", ""]
        lines += [f"- {n}" for n in result.notes]
        lines += ["", "</details>", ""]

    if result.error:
        lines += ["```", result.error, "```"]

    if result.data_feed:
        lines.append(f"<sub>data feed: {result.data_feed}</sub>")

    return "\n".join(lines)


def send_webhook(url: str, headline: str, body: str) -> None:
    """Post to a Discord or Slack incoming webhook. Never fatal."""
    import requests

    text = f"**{headline}**\n{body}" if "discord" in url else f"*{headline}*\n{body}"
    payload = {"content": text} if "discord" in url else {"text": text}
    try:
        resp = requests.post(url, json=payload, timeout=15)
        if resp.status_code >= 300:
            print(f"note: webhook returned {resp.status_code}")
    except Exception as exc:  # noqa: BLE001 - a failed ping must not fail the run
        print(f"note: webhook failed ({exc})")


def webhook_body(result: RunResult) -> str:
    parts = []
    if result.target_weights:
        parts.append(" ".join(
            f"{s} {w:.0%}" for s, w in
            sorted(result.target_weights.items(), key=lambda kv: -kv[1])
        ))
    if result.skipped:
        parts.append(f"trend filter -> {DEFENSIVE}: {' '.join(result.skipped)}")
    if result.orders:
        parts.append(" | ".join(
            f"{o['side']} {o['qty']} {o['symbol']} [{o.get('status', '?')}]"
            for o in result.orders
        ))
    if result.equity:
        parts.append(f"equity ${result.equity:,.0f}")
    if result.error:
        parts.append(result.error.splitlines()[-1][:300])
    return "\n".join(parts) or result.detail


# --------------------------------------------------------------------------- #
# the run
# --------------------------------------------------------------------------- #

def offline_run(args, result: RunResult, now_utc: datetime) -> RunResult:
    """Signal only, from a cached price CSV. No keys, no broker, no orders."""
    closes = pd.read_csv(args.offline, index_col=0, parse_dates=True)
    asof = pd.Timestamp(args.asof) if args.asof else closes.index[-1]
    d = decide(closes.loc[closes.index <= asof], asof)

    result.action = "HELD" if d.weights else "SKIPPED"
    result.detail = (f"offline signal from {os.path.basename(args.offline)} "
                     f"as of {asof.date()}")
    result.signal_month, result.ranked, result.skipped = (
        d.signal_month, d.ranked, d.skipped)
    result.target_weights = d.weights
    result.data_feed = f"offline:{os.path.basename(args.offline)}"
    if d.reason:
        result.note(d.reason)
    result.headline = f"Faber offline signal {d.signal_month}: " + " ".join(
        f"{s} {w:.0%}" for s, w in sorted(d.weights.items(), key=lambda kv: -kv[1]))
    return result


def live_run(args, result: RunResult, now_utc: datetime, state: dict) -> RunResult:
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.trading.client import TradingClient

    key = os.environ.get("ALPACA_API_KEY_ID", "")
    secret = os.environ.get("ALPACA_API_SECRET_KEY", "")
    if not key or not secret:
        raise RuntimeError(
            "ALPACA_API_KEY_ID and/or ALPACA_API_SECRET_KEY are not set. "
            "Presence is checked by name only; values are never printed."
        )

    # A trailing newline or space pasted into a GitHub Secret is stored verbatim
    # and goes straight into the auth header, where Alpaca answers a bare
    # "unauthorized." with no hint that the value is merely dirty. Strip it, then
    # report the *shape* of what arrived -- lengths only, never the values -- so
    # the next rejection can be diagnosed from the log instead of by pasting a
    # key somewhere it should not go.
    raw_lengths = (len(key), len(secret))
    key, secret = key.strip(), secret.strip()
    shape = (f"key id {len(key)} chars, PK-prefixed: {key.startswith('PK')}; "
             f"secret {len(secret)} chars")
    if raw_lengths != (len(key), len(secret)):
        shape += "; stripped surrounding whitespace"
    if secret.startswith("PK") and not key.startswith("PK"):
        shape += "; SWAPPED -- the secret holds the key id"
    print("[auth] " + shape)
    # Also record it on the result, so it reaches the committed log and the run
    # artifact. stdout only survives in the job log, which needs a GitHub token
    # to download -- three rejections in a row went undiagnosed for exactly that
    # reason. Lengths and a prefix boolean carry no key material: every Alpaca
    # paper key id starts "PK", so that bit is a constant, not a secret.
    result.note("auth shape: " + shape)

    # Paper is not a flag. It is hardcoded, and asserted before any request.
    trading = TradingClient(api_key=key, secret_key=secret, paper=True)
    base = str(getattr(trading._base_url, "value", trading._base_url))
    if "paper-api.alpaca.markets" not in base:
        raise RuntimeError(f"refusing to trade: endpoint is not paper ({base})")
    data = StockHistoricalDataClient(api_key=key, secret_key=secret)

    account = trading.get_account()
    result.equity = float(account.equity)
    result.cash = float(account.cash)
    print(f"account {account.account_number[-4:].rjust(8, '*')} "
          f"status={account.status} equity=${result.equity:,.2f}")

    positions = trading.get_all_positions()
    current = {}
    for p in positions:
        qty = float(p.qty)
        if qty != int(qty):
            result.note(f"{p.symbol} holds a fractional {qty} shares; "
                        "market-on-close is whole-share only, so the fraction "
                        "will be left untouched")
        current[p.symbol] = int(qty)
    result.positions_before = dict(current)

    # Confirm what last run's orders did before deciding anything new.
    result.fills = check_previous_orders(trading, state, result)

    today_et = now_utc.astimezone(ET).date()
    is_trading_day, is_month_start, first_td = calendar_facts(trading, today_et)
    result.trading_day = is_trading_day

    if not is_trading_day:
        result.action = "SKIPPED"
        result.detail = f"{today_et} is not a NYSE trading day"
        result.headline = f"Faber: no action, {today_et} is a market holiday"
        return result

    trigger = rebalance_trigger(state, today_et, is_month_start, first_td,
                                args.force_rebalance)
    if not trigger.due:
        result.action = trigger.action
        result.detail = f"{trigger.reason}; holding {len(current)} position(s)"
        result.headline = trigger.headline
        return result

    result.rebalance_day = True
    result.note(f"rebalance due: {trigger.reason}")
    if trigger.catch_up:
        result.note("this is later than the backtest's rebalance day (the first "
                    "trading day of the month), so the fill bar differs from the "
                    "verified one")
        result.notify = True

    closes = fetch_daily_closes(data, now_utc, result)
    missing = [s for s in UNIVERSE if s not in closes.columns]
    if missing:
        result.note(f"no bars returned for {','.join(missing)}")
    print(f"bars: {closes.shape[0]} days, {closes.index.min().date()} -> "
          f"{closes.index.max().date()}, {closes.shape[1]} symbols")

    d: Decision = decide(closes, pd.Timestamp(today_et))
    result.signal_month, result.ranked, result.skipped = (
        d.signal_month, d.ranked, d.skipped)
    result.target_weights = d.weights

    if not d.weights:
        result.action = "SKIPPED"
        result.detail = f"no tradeable signal: {d.reason}"
        result.headline = "Faber: rebalance day but no signal"
        result.notify = True
        result.note(d.reason)
        return result

    print(f"signal month {d.signal_month}: ranked={d.ranked} skipped={d.skipped}")

    prices = sizing_prices(data, sorted(d.weights), closes, result)
    targets = whole_share_targets(d.weights, result.equity, prices, args.cash_buffer)
    orders = plan_orders(targets, current)

    if not orders:
        result.action = "HELD"
        result.detail = (f"signal unchanged for {d.signal_month}; already holding "
                         f"the target, no orders needed")
        result.headline = ("Faber rebalance day: target already held, no trades "
                           f"({' '.join(d.ranked)})")
        result.notify = True
        state["last_rebalance_date"] = today_et.isoformat()
        state["last_rebalance_signal_month"] = d.signal_month
        state["last_target_weights"] = d.weights
        state["submitted_orders"] = []
        state.pop("pending_rebalance", None)
        return result

    now_et = now_utc.astimezone(ET)
    cutoff = now_et.replace(hour=CLS_CUTOFF_ET[0], minute=CLS_CUTOFF_ET[1],
                            second=0, microsecond=0)
    clock = trading.get_clock()

    if now_et < cutoff:
        tif = "cls"
    elif clock.is_open:
        tif = "day"
        result.note(f"past the {CLS_CUTOFF_ET[0]}:{CLS_CUTOFF_ET[1]:02d} ET "
                    "market-on-close cutoff, falling back to a plain market "
                    "order; it fills near but not at the close, which is a "
                    "small deviation from the backtest's fill bar")
    else:
        result.action = "DEFERRED"
        result.detail = (f"rebalance due but it is {now_et:%H:%M} ET with the market "
                         "closed and the market-on-close window gone; deferring "
                         "to the next trading day")
        result.headline = "Faber: rebalance DEFERRED to the next trading day"
        result.notify = True
        state["pending_rebalance"] = {
            "date": today_et.isoformat(),
            "reason": "run fired outside the market-on-close window",
        }
        return result

    if args.dry_run:
        result.action = "REBALANCED"
        result.detail = f"DRY RUN — {len(orders)} order(s) computed, none sent"
        result.orders = [dict(o, status="DRY_RUN", tif=tif) for o in orders]
        result.headline = f"Faber DRY RUN: would place {len(orders)} order(s)"
        for o in orders:
            print(f"[dry-run] {o['side']} {o['qty']} {o['symbol']} tif={tif} "
                  f"({o['have']} -> {o['want']})")
        return result

    result.orders = submit_orders(trading, orders, today_et, tif, result)
    accepted = [o for o in result.orders if o.get("status") != "REJECTED"]
    rejected = [o for o in result.orders if o.get("status") == "REJECTED"]

    result.action = "REBALANCED"
    result.detail = (f"{len(accepted)} order(s) submitted as {tif.upper()}"
                     + (f", {len(rejected)} rejected" if rejected else ""))
    result.headline = (f"Faber REBALANCED {d.signal_month} -> "
                       + " ".join(f"{s} {w:.0%}" for s, w in
                                  sorted(d.weights.items(), key=lambda kv: -kv[1])))
    result.notify = True

    state["last_rebalance_date"] = today_et.isoformat()
    state["last_rebalance_signal_month"] = d.signal_month
    state["last_target_weights"] = d.weights
    state["submitted_orders"] = accepted
    state.pop("pending_rebalance", None)
    if rejected:
        result.note(f"{len(rejected)} order(s) were rejected and are NOT part of "
                    "the position; the next rebalance will re-diff toward target")
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true",
                    help="compute everything, submit nothing")
    ap.add_argument("--force-rebalance", action="store_true",
                    help="rebalance even if today is not the first trading day")
    ap.add_argument("--offline", metavar="CSV",
                    help="signal only, from a cached daily-close CSV; no keys needed")
    ap.add_argument("--asof", metavar="YYYY-MM-DD",
                    help="pretend this is the rebalance date (offline mode only)")
    ap.add_argument("--cash-buffer", type=float, default=CASH_BUFFER,
                    help=f"fraction of equity left uninvested (default {CASH_BUFFER})")
    ap.add_argument("--log", default=os.path.join(HERE, "paper_log.csv"))
    ap.add_argument("--state", default=os.path.join(HERE, "state.json"))
    ap.add_argument("--result", default=os.path.join(HERE, "run_result.json"))
    args = ap.parse_args()

    # The summary is Markdown for GitHub, so it carries non-ASCII. A Windows
    # console is cp1252 and would raise UnicodeEncodeError on it mid-run;
    # escaping beats crashing, and on a UTF-8 runner this changes nothing.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="backslashreplace")
        except (AttributeError, OSError):
            pass

    now_utc = datetime.now(timezone.utc)
    result = RunResult()
    state = load_state(args.state)

    try:
        if args.offline:
            result = offline_run(args, result, now_utc)
        else:
            result = live_run(args, result, now_utc, state)
    except Exception as exc:  # noqa: BLE001 - the run must still report itself
        result.action = "ERROR"
        result.detail = f"{type(exc).__name__}: {exc}"
        result.headline = f"Faber paper run FAILED: {type(exc).__name__}"
        result.error = traceback.format_exc()
        result.notify = True
        print(result.error, file=sys.stderr)

    summary = render_summary(result, now_utc)
    print("\n" + summary)

    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a", encoding="utf-8") as fh:
            fh.write(summary + "\n")

    if not args.offline:
        append_log(args.log, result, now_utc)
        state["last_run_utc"] = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        state["last_action"] = result.action
        if not args.dry_run:
            save_state(args.state, state)

    with open(args.result, "w", encoding="utf-8") as fh:
        json.dump({
            "action": result.action,
            "detail": result.detail,
            "headline": result.headline,
            "notify": result.notify,
            "error": bool(result.error),
            "summary_markdown": summary,
            "webhook_body": webhook_body(result),
        }, fh, indent=2)
        fh.write("\n")

    hook = os.environ.get("WEBHOOK_URL", "").strip()
    if hook and result.notify:
        send_webhook(hook, result.headline, webhook_body(result))

    # A failed run should turn the workflow red; a quiet day should not.
    return 1 if result.action == "ERROR" else 0


if __name__ == "__main__":
    sys.exit(main())
