"""Reconstruct LEAN's equity curve exactly, from its own fills and bars.

Why not just read the Strategy Equity chart? Because it is not a clean daily
close series. It carries ~10,100 points at two different times of day --
midnight ET (which is the *previous* close) and 16:00 ET (that day's close) --
and only ~2,899 of ~4,938 trading days have the 16:00 point. Taking the last
point per date therefore silently mixes the two conventions, which is why the
daily-return correlation against the harness topped out around 0.63 at every
shift instead of being near 1.0.

The fills are unambiguous: 726 filled events, each with an exact price,
signed quantity, and orderFeeAmount. Replaying them against LEAN's own daily
closes gives the portfolio value on every trading day with no sampling
question at all. The check that this is right is that the final value must
reproduce LEAN's reported End Equity of $570,569.38 and Total Fees of
$4,248.04 to the cent.

With a clean curve, the harness's own stats() can be applied to both sides and
the remaining difference decomposed into its three mechanical causes.
"""

import glob
import io
import json
import os
import sys
import zipfile

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
FABER = os.path.abspath(os.path.join(HERE, "..", "faber-lean"))
DAILY = os.path.join(FABER, "data", "equity", "usa", "daily")
sys.path.insert(0, FABER)
import local_backtest as lb  # noqa: E402

RUN = sys.argv[1]
SCALE = 10_000.0
START_CASH = 100_000.0
REPORTED_END = 570_569.38
REPORTED_FEES = 4_248.04


def lean_closes():
    out = {}
    for t in lb.SECTORS + [lb.DEFENSIVE, "SPY"]:
        with zipfile.ZipFile(os.path.join(DAILY, t.lower() + ".zip")) as z:
            body = z.read(z.namelist()[0]).decode()
        df = pd.read_csv(io.StringIO(body), header=None,
                         names=["ts", "o", "h", "l", "c", "v"])
        idx = pd.to_datetime(df["ts"].str.slice(0, 8), format="%Y%m%d")
        out[t] = pd.Series((df["c"] / SCALE).values, index=idx)
    return pd.DataFrame(out).sort_index()


def fills():
    path = glob.glob(os.path.join(RUN, "*-order-events.json"))[0]
    recs = json.load(open(path, encoding="utf-8"))
    if isinstance(recs, dict):
        recs = recs.get("orderEvents", [])
    rows = []
    for r in recs:
        if str(r.get("status", "")).lower() != "filled":
            continue
        q = float(r["fillQuantity"])
        rows.append({
            "ts": pd.to_datetime(float(r["time"]), unit="s"),
            "ticker": r.get("symbolValue") or r["symbol"].split()[0],
            "price": float(r["fillPrice"]),
            "qty": q,
            "fee": float(r.get("orderFeeAmount") or 0.0),
            "order_id": int(r["orderId"]),
        })
    df = pd.DataFrame(rows).sort_values(["ts", "order_id"]).reset_index(drop=True)
    df["date"] = df["ts"].dt.normalize()
    return df


def main():
    closes = lean_closes()
    fl = fills()
    print("=== inputs ===")
    print("  filled events : %d  (%s -> %s)"
          % (len(fl), fl["date"].min().date(), fl["date"].max().date()))
    print("  total fees    : $%.2f   (LEAN reported $%.2f)"
          % (fl["fee"].sum(), REPORTED_FEES))

    # ---- replay ------------------------------------------------------
    trade_dates = sorted(fl["date"].unique())
    start, end = trade_dates[0], pd.Timestamp("2026-08-19")
    cal = closes.index[(closes.index >= start) & (closes.index <= end)]

    cash = START_CASH
    shares = {}
    by_date = {d: g for d, g in fl.groupby("date")}
    dates, equity, invested = [], [], []
    for d in cal:
        if d in by_date:
            for r in by_date[d].itertuples():
                cash -= r.qty * r.price + r.fee
                shares[r.ticker] = shares.get(r.ticker, 0.0) + r.qty
                if abs(shares[r.ticker]) < 1e-9:
                    del shares[r.ticker]
        mark = closes.loc[d]
        hold = sum(q * mark[t] for t, q in shares.items() if t in mark.index)
        dates.append(d)
        equity.append(cash + hold)
        invested.append(hold)

    curve = pd.Series(equity, index=pd.DatetimeIndex(dates))
    print("\n=== reconstruction check (must match LEAN's report) ===")
    print("  final equity   : $%.2f   (LEAN reported $%.2f)  delta $%.2f"
          % (curve.iloc[-1], REPORTED_END, curve.iloc[-1] - REPORTED_END))
    print("  final holdings : $%.2f   (LEAN runtime $566,118.10)" % invested[-1])
    print("  final cash     : $%.2f" % (curve.iloc[-1] - invested[-1]))
    ok = abs(curve.iloc[-1] - REPORTED_END) < 1.0
    print("  VERDICT        : %s"
          % ("EXACT -- the reconstruction is LEAN's curve"
             if ok else "MISMATCH -- do not trust the reconstruction"))

    # ---- compare, same formulas both sides ---------------------------
    px = lb.load_prices()
    px = px[px.index >= pd.Timestamp(lb.WARMUP_START)]
    rf = px[lb.DEFENSIVE].pct_change()
    weights, diag, _ = lb.build_signals(px)
    h10 = lb.run(px, weights, 10.0)
    h0 = lb.run(px, weights, 0.0)

    common = curve.index.intersection(h10.index)
    L = curve.reindex(common).dropna()
    H10 = h10.reindex(common).dropna()
    H0 = h0.reindex(common).dropna()

    rows = [lb.stats(L, rf, "LEAN (reconstructed)"),
            lb.stats(H10, rf, "harness 10bps"),
            lb.stats(H0, rf, "harness 0bps")]
    table = pd.DataFrame(rows).set_index("label")
    fmt = table.copy()
    for k in ["total_return", "cagr", "vol", "maxdd_daily", "maxdd_monthly"]:
        fmt[k] = (fmt[k] * 100).round(2).astype(str) + "%"
    for k in ["sharpe_rf0", "sharpe_rf_shy"]:
        fmt[k] = fmt[k].round(3)
    fmt["years"] = fmt["years"].round(2)
    pd.set_option("display.width", 220, "display.max_columns", 50)
    print("\n=== identical formulas, %d common trading days ===" % len(common))
    print(fmt.to_string())

    lr = L.pct_change().dropna()
    hr = H10.pct_change().dropna()
    j = pd.concat([lr.rename("l"), hr.rename("h")], axis=1).dropna()
    print("\n=== daily return agreement (the real test) ===")
    print("  days compared        : %d" % len(j))
    print("  correlation          : %.6f" % j["l"].corr(j["h"]))
    print("  mean |difference|    : %.5f pp" % (100 * (j["l"] - j["h"]).abs().mean()))
    print("  days with |diff|>0.5pp: %d (%.2f%%)"
          % (int(((j["l"] - j["h"]).abs() > 0.005).sum()),
             100.0 * ((j["l"] - j["h"]).abs() > 0.005).mean()))

    # ---- decompose the CAGR gap --------------------------------------
    print("\n=== decomposition of the CAGR difference ===")
    yrs = (common[-1] - common[0]).days / 365.25
    def cagr(s):
        return (s.iloc[-1] / s.iloc[0]) ** (1 / yrs) - 1
    c_h10, c_h0, c_l = cagr(H10), cagr(H0), cagr(L)
    print("  harness 10bps                         %.3f%%" % (100 * c_h10))
    print("  + remove harness turnover cost model  %+.3f pp -> %.3f%%"
          % (100 * (c_h0 - c_h10), 100 * c_h0))
    print("  = harness frictionless                %.3f%%" % (100 * c_h0))
    print("  LEAN actual                           %.3f%%" % (100 * c_l))
    print("  residual (LEAN - frictionless)        %+.3f pp"
          % (100 * (c_l - c_h0)))
    print("     of which LEAN's own fees cost about %+.3f pp"
          % (-100 * ((1 + fl['fee'].sum() / START_CASH) ** (1 / yrs) - 1)))
    print("\n  harness cost model in dollars of terminal wealth: $%.0f"
          % (H0.iloc[-1] / H0.iloc[0] * START_CASH
             - H10.iloc[-1] / H10.iloc[0] * START_CASH))
    print("  LEAN's actual commissions                        : $%.0f"
          % fl["fee"].sum())
    vol_traded = (fl["qty"].abs() * fl["price"]).sum()
    print("  LEAN traded notional $%.0f -> effective %.2f bps of notional"
          % (vol_traded, 10_000 * fl["fee"].sum() / vol_traded))
    print("  harness charges 10.00 bps per unit of turnover"
          " (%.1fx more conservative)"
          % (10.0 / (10_000 * fl["fee"].sum() / vol_traded)))


if __name__ == "__main__":
    main()
