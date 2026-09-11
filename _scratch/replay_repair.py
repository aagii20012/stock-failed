"""Replay the real 2026-09 account state through live_run with a fake broker.

The unit tests cover the new pure functions. This exercises the wiring: does
the repair trigger actually fire on the state committed on 2026-09-04, does it
produce sane residual orders, does the cash fit bind, and does the state it
writes let the next run stop?

No keys, no network. Run from the workspace root:

    python _scratch/replay_repair.py
"""

import json
import os
import sys
from datetime import date, datetime, timezone

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAPER = os.path.join(ROOT, "faber-lean", "paper")
sys.path.insert(0, PAPER)

os.environ.setdefault("ALPACA_API_KEY_ID", "PKFAKEFAKEFAKEFAKEFAKE")
os.environ.setdefault("ALPACA_API_SECRET_KEY", "x" * 40)

import paper_trade as pt  # noqa: E402

NOW = datetime(2026, 9, 8, 18, 14, 0, tzinfo=timezone.utc)   # 14:14 ET, Tue
TODAY = date(2026, 9, 8)

# The account as of the 2026-09-04 run.
EQUITY, CASH = 99522.21, 34759.88
POSITIONS = {"XLE": 485, "XLK": 49, "XLV": 143}


# --------------------------------------------------------------------------- #
# fakes
# --------------------------------------------------------------------------- #

class Obj:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class FakeAccount(Obj):
    pass


class FakeTrading:
    def __init__(self, fills):
        self._base_url = "https://paper-api.alpaca.markets"
        self.submitted = []
        self._fills = fills

    def get_account(self):
        return FakeAccount(equity=str(EQUITY), cash=str(CASH),
                           buying_power=str(CASH), status="ACTIVE",
                           account_number="123456789")

    def get_all_positions(self):
        return [Obj(symbol=s, qty=str(q)) for s, q in POSITIONS.items()]

    def get_order_by_id(self, oid):
        f = self._fills[oid]
        return Obj(status=Obj(value=f["status"]), filled_qty=f["filled_qty"],
                   filled_avg_price=f.get("px"), filled_at=None)

    def get_calendar(self, req):
        # September 2026 trading days up to the 8th (7th is Labor Day).
        days = [date(2026, 9, d) for d in (1, 2, 3, 4, 8)]
        return [Obj(date=d) for d in days if d <= TODAY]

    def get_clock(self):
        return Obj(is_open=True)

    def submit_order(self, req):
        self.submitted.append(req)
        return Obj(status=Obj(value="pending_new"), id="new-%s" % req.symbol)


class FakeData:
    def __init__(self, closes):
        self._closes = closes

    def get_stock_latest_trade(self, req):
        last = self._closes.iloc[-1]
        return {s: Obj(price=float(last[s])) for s in req.symbol_or_symbols
                if s in self._closes.columns}


def load_closes():
    df = pd.read_csv(os.path.join(ROOT, "faber-lean", "prices.csv"),
                     index_col=0, parse_dates=True)
    # The cache stops 2026-08-19, so August never completes and the signal
    # month would come out 2026-07. Pad the last row forward to month end so
    # the replay computes the 2026-08 signal the live run computed.
    tail = pd.date_range("2026-08-20", "2026-08-31", freq="B")
    pad = pd.DataFrame([df.iloc[-1].values] * len(tail), index=tail,
                       columns=df.columns)
    return pd.concat([df, pad])


# --------------------------------------------------------------------------- #

def run(state, label, fills):
    print("=" * 72)
    print(label)
    print("=" * 72)

    closes = load_closes()
    trading = FakeTrading(fills)
    data = FakeData(closes)

    pt.fetch_daily_closes = lambda *a, **k: closes

    import alpaca.trading.client as tc
    import alpaca.data.historical as dh
    tc.TradingClient = lambda **kw: trading
    dh.StockHistoricalDataClient = lambda **kw: data

    args = Obj(force_rebalance=False, dry_run=False, cash_buffer=pt.CASH_BUFFER,
               submit_cash_margin=pt.SUBMIT_CASH_MARGIN)
    result = pt.RunResult()
    out = pt.live_run(args, result, NOW, state)

    print("\naction   :", out.action)
    print("detail   :", out.detail)
    print("orders   :", json.dumps(
        [{k: o[k] for k in ("symbol", "side", "qty", "have", "want")}
         for o in out.orders]))
    print("notes    :")
    for n in out.notes:
        print("   -", n)
    print("state    :", json.dumps(
        {k: state[k] for k in sorted(state) if k != "last_fills"},
        indent=2, sort_keys=True))
    return out


PRIOR_FILLS = {
    "f6e9cfb2-d044-4133-8075-4a43444a44a9":
        {"status": "expired", "filled_qty": "485", "px": "64.79"},
    "41be23b3-3636-4289-ab44-8e0a32e20164":
        {"status": "expired", "filled_qty": "49", "px": "184.66"},
    "dc33dcaf-2ade-4b9c-afc1-f9bbdaef3713":
        {"status": "expired", "filled_qty": "0", "px": None},
}

with open(os.path.join(PAPER, "state.json"), encoding="utf-8") as fh:
    live_state = json.load(fh)

assert "last_share_targets" not in live_state, "state already migrated; edit me"
out1 = run(live_state, "RUN 1 -- the committed 2026-09-04 state, one run later",
           PRIOR_FILLS)

# Second run: pretend the repair filled completely, and check it stops.
print()
filled = dict(out1.orders and
              {o["order_id"]: {"status": "filled", "filled_qty": str(o["qty"]),
                               "px": "1.0"} for o in out1.orders})
POSITIONS.clear()
POSITIONS.update(live_state["last_share_targets"])
out2 = run(live_state, "RUN 2 -- residual filled; must go quiet", filled)

print()
print("=" * 72)
print("RUN 1 repaired:", out1.action == "REBALANCED")
print("RUN 2 held    :", out2.action == "HELD",
      "| detail:", out2.detail[:60])
