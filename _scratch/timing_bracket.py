"""Bracket what LEAN *should* report, so a divergence is attributable.

The harness sets weights at the close of the signal month and holds through
the hold month. The LEAN algorithm schedules month_start + 30min, so its
order is submitted on the first trading day D of the hold month. At daily
resolution the last bar LEAN has received at 10:00 on D is D-1's bar, so
set_holdings sizes the order off close(D-1) -- which IS the harness's signal
close -- but the *fill* lands on D's bar. Whether that fill uses D's open or
D's close is a LEAN fill-model detail, so both are simulated here.

Also modelled, because each is a real LEAN behaviour the harness omits:
  * whole-share quantization (harness holds fractional weights)
  * a cash buffer (Settings.FreePortfolioValuePercentage, default 0.25%)
  * InteractiveBrokersFeeModel: $0.005/share, min $1, cap 0.5% of trade value
  * idle cash earns nothing

Output is a bracket. If LEAN's reported CAGR lands inside it, the two
implementations agree and the harness is trustworthy for iteration. If LEAN
lands outside it, something is wrong that timing does not explain.
"""

import io
import os
import sys
import zipfile

import numpy as np
import pandas as pd

FABER = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", "faber-lean"))
DAILY = os.path.join(FABER, "data", "equity", "usa", "daily")
sys.path.insert(0, FABER)
import local_backtest as lb  # noqa: E402

SECTORS = lb.SECTORS
DEFENSIVE = lb.DEFENSIVE
TOP_N, MOM_LOOKBACK, SMA_LENGTH = lb.TOP_N, lb.MOM_LOOKBACK, lb.SMA_LENGTH
START_CASH = 100_000.0
HOLD_START = "2007-01"
END = pd.Timestamp("2026-08-19")


def load_ohlc():
    """The exact bars LEAN reads, from its own daily zips."""
    frames = {}
    for t in SECTORS + [DEFENSIVE, "SPY"]:
        with zipfile.ZipFile(os.path.join(DAILY, t.lower() + ".zip")) as z:
            body = z.read(z.namelist()[0]).decode()
        df = pd.read_csv(io.StringIO(body), header=None,
                         names=["ts", "open", "high", "low", "close", "volume"])
        df.index = pd.to_datetime(df["ts"].str.slice(0, 8), format="%Y%m%d")
        for c in ("open", "high", "low", "close"):
            df[c] = df[c] / 10_000.0
        frames[t] = df[["open", "close"]]
    opens = pd.DataFrame({t: f["open"] for t, f in frames.items()}).dropna(how="any")
    closes = pd.DataFrame({t: f["close"] for t, f in frames.items()}).dropna(how="any")
    idx = opens.index.intersection(closes.index)
    return opens.loc[idx], closes.loc[idx]


def signals(closes):
    """{hold_month: {ticker: weight}} -- identical logic to the harness."""
    monthly = closes.groupby(closes.index.to_period("M")).last()
    months = monthly.index
    out = {}
    for i in range(MOM_LOOKBACK, len(months) - 1):
        hold = months[i + 1]
        if str(hold) < HOLD_START:
            continue
        last = monthly.iloc[i]
        mom = last / monthly.iloc[i - MOM_LOOKBACK] - 1.0
        sma = monthly.iloc[i - SMA_LENGTH + 1: i + 1].mean()
        ranked = sorted(SECTORS, key=lambda t: mom[t], reverse=True)[:TOP_N]
        w = {}
        for t in ranked:
            k = DEFENSIVE if not last[t] > sma[t] else t
            w[k] = w.get(k, 0.0) + 1.0 / TOP_N
        out[hold] = w
    return out


def ib_fee(shares):
    """InteractiveBrokersFeeModel, equities: $0.005/share, $1 minimum."""
    if shares <= 0:
        return 0.0
    return max(1.0, 0.005 * shares)


def simulate(opens, closes, weights, when="prev_close", whole_shares=True,
             buffer_pct=0.0025, fees=True, fee_cap=True):
    """Portfolio sim with explicit execution timing.

    when:
      'prev_close'  -- fill at close of the last day of the signal month
                       (this is the harness's convention)
      'open'        -- fill at the open of the first trading day of the month
      'close'       -- fill at the close of the first trading day of the month
    """
    periods = closes.index.to_period("M")
    cash = START_CASH
    shares = {}
    curve_dates, curve_vals = [], []
    total_fees = 0.0
    n_orders = 0

    for month in sorted(weights):
        w = weights[month]
        mask = periods == month
        if not mask.any():
            continue
        block_idx = closes.index[mask]
        d_pos = closes.index.get_loc(block_idx[0])
        if d_pos < 1:
            continue

        # Sizing price: what LEAN's Securities[..].Price is when the scheduled
        # event fires -- the previous daily bar's close.
        size_px = closes.iloc[d_pos - 1]

        if when == "prev_close":
            fill_px = closes.iloc[d_pos - 1]
            fill_pos = d_pos - 1
        elif when == "open":
            fill_px = opens.iloc[d_pos]
            fill_pos = d_pos
        elif when == "close":
            fill_px = closes.iloc[d_pos]
            fill_pos = d_pos
        else:
            raise ValueError(when)

        # Mark the days between the previous rebalance and this fill at the
        # OLD holdings, so no return is double counted or skipped.
        while curve_dates and curve_dates[-1] < closes.index[fill_pos]:
            nxt = closes.index[closes.index.get_loc(curve_dates[-1]) + 1]
            if nxt > closes.index[fill_pos]:
                break
            val = cash + sum(q * closes.loc[nxt, t] for t, q in shares.items())
            curve_dates.append(nxt)
            curve_vals.append(val)
        if not curve_dates:
            curve_dates.append(closes.index[fill_pos])
            curve_vals.append(START_CASH)

        # Portfolio value at the fill, then rebalance to targets.
        equity = cash + sum(q * fill_px[t] for t, q in shares.items())
        investable = equity * (1.0 - buffer_pct)

        target_shares = {}
        for t, weight in w.items():
            notional = investable * weight
            q = notional / fill_px[t]
            target_shares[t] = float(int(q)) if whole_shares else q

        # Sells first (frees cash), then buys -- LEAN orders targets this way.
        deltas = {}
        for t in set(list(shares) + list(target_shares)):
            deltas[t] = target_shares.get(t, 0.0) - shares.get(t, 0.0)
        for t in sorted(deltas, key=lambda k: deltas[k]):
            dq = deltas[t]
            if abs(dq) < 1e-9:
                continue
            px = fill_px[t]
            cash -= dq * px
            if fees:
                f = ib_fee(abs(dq))
                if fee_cap:
                    # IB caps equity commission at 0.5% of trade value.
                    f = min(f, 0.005 * abs(dq) * px)
                cash -= f
                total_fees += f
            n_orders += 1
            shares[t] = shares.get(t, 0.0) + dq
            if abs(shares[t]) < 1e-9:
                del shares[t]

        # Mark the fill day and the rest of the month at the new holdings.
        start_mark = fill_pos if when != "prev_close" else d_pos
        for pos in range(start_mark, closes.index.get_loc(block_idx[-1]) + 1):
            day = closes.index[pos]
            if curve_dates and day <= curve_dates[-1]:
                continue
            val = cash + sum(q * closes.loc[day, t] for t, q in shares.items())
            curve_dates.append(day)
            curve_vals.append(val)

    curve = pd.Series(curve_vals, index=pd.DatetimeIndex(curve_dates))
    curve = curve[~curve.index.duplicated(keep="last")].sort_index()
    curve = curve[curve.index <= END]
    return curve, {"fees": total_fees, "orders": n_orders}


def main():
    opens, closes = load_ohlc()
    opens = opens[opens.index >= pd.Timestamp("2005-06-01")]
    closes = closes[closes.index >= pd.Timestamp("2005-06-01")]
    w = signals(closes)
    print("hold months: %d  (%s -> %s)"
          % (len(w), min(w), max(w)))

    # Harness reference, on the harness's own prices, for the published numbers.
    px = pd.read_csv(os.path.join(FABER, "prices.csv"), index_col=0,
                     parse_dates=True)
    px = px[px.index >= pd.Timestamp(lb.WARMUP_START)]
    rf = px[DEFENSIVE].pct_change()
    hw, _, _ = lb.build_signals(px)
    h10 = lb.run(px, hw, 10.0)
    h0 = lb.run(px, hw, 0.0)

    rows = [lb.stats(h0, rf, "harness 0bps (published)"),
            lb.stats(h10, rf, "harness 10bps (published)")]

    variants = [
        ("A prev_close, fractional, no fee, no buffer", dict(
            when="prev_close", whole_shares=False, buffer_pct=0.0, fees=False)),
        ("B prev_close, whole+fee+buffer", dict(
            when="prev_close", whole_shares=True, buffer_pct=0.0025, fees=True)),
        ("C next-day OPEN, whole+fee+buffer  <- LEAN candidate", dict(
            when="open", whole_shares=True, buffer_pct=0.0025, fees=True)),
        ("D next-day CLOSE, whole+fee+buffer <- LEAN candidate", dict(
            when="close", whole_shares=True, buffer_pct=0.0025, fees=True)),
    ]
    meta = {}
    curves = {}
    for label, kw in variants:
        c, m = simulate(opens, closes, w, **kw)
        curves[label] = c
        meta[label] = m
        rows.append(lb.stats(c, rf, label))

    table = pd.DataFrame(rows).set_index("label")
    fmt = table.copy()
    for c in ["total_return", "cagr", "vol", "maxdd_daily", "maxdd_monthly"]:
        fmt[c] = (fmt[c] * 100).round(2).astype(str) + "%"
    for c in ["sharpe_rf0", "sharpe_rf_shy"]:
        fmt[c] = fmt[c].round(3)
    fmt["years"] = fmt["years"].round(2)
    pd.set_option("display.width", 240, "display.max_columns", 50)
    print("\n=== execution-timing bracket (all measured with harness stats()) ===")
    print(fmt.to_string())

    print("\n=== simulated frictions ===")
    for label, m in meta.items():
        print("  %-52s orders=%4d  fees=$%.0f"
              % (label, m["orders"], m["fees"]))

    lo = min(table.loc[l, "cagr"] for l, _ in variants[2:])
    hi = max(table.loc[l, "cagr"] for l, _ in variants[2:])
    print("\n=== prediction for LEAN ===")
    print("  timing variants C/D span CAGR %.2f%% .. %.2f%%" % (100 * lo, 100 * hi))
    print("  harness published (10bps)   %.2f%%" % (100 * table.loc[
        "harness 10bps (published)", "cagr"]))
    print("  => a LEAN CAGR inside roughly %.2f%%..%.2f%% is AGREEMENT;"
          % (100 * min(lo, hi) - 0.35, 100 * max(lo, hi) + 0.35))
    print("     outside that band is a real discrepancy to explain.")

    for label in list(curves)[2:]:
        c = curves[label]
        print("\n  %s" % label)
        print("    final equity  $%.0f  (start $%.0f)" % (c.iloc[-1], START_CASH))
        print("    window        %s -> %s (%d days)"
              % (c.index[0].date(), c.index[-1].date(), len(c)))


if __name__ == "__main__":
    main()
