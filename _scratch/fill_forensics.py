"""Attribute the LEAN-vs-harness gap to a specific, checkable mechanism.

Three questions, each answered from LEAN's own order events rather than by
argument:

1. WHICH BAR DOES LEAN FILL ON? Its log warns that market orders on daily
   data become MarketOnClose. If true, every fillPrice should equal close(D)
   of the order's own day -- not close(D-1) (the harness's convention) and
   not open(D). Match each fill against all three candidates and count.

2. DID THE MINIMUM-ORDER-SIZE FILTER CHANGE THE PORTFOLIO? LEAN warned once
   that a rebalance was "ignored as it resulted in a single share trade".
   That warning is a one-time flag, so the log cannot say how often it bit.
   Instead reconstruct LEAN's actual holdings from the fills and diff the
   realized weight vector against the harness's intended weights, month by
   month.

3. IS THE MONTHLY RETURN DIFFERENCE TIMING OR LOGIC? If it is timing, the
   difference for month M must be explained by the return of the assets
   traded across the one-day gap. Regress |monthly difference| on the
   first-trading-day move and see whether the worst months are the ones
   with the biggest first-day moves.
"""

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

SECTORS = lb.SECTORS
DEFENSIVE = lb.DEFENSIVE
RUN = sys.argv[1] if len(sys.argv) > 1 else None
SCALE = 10_000.0


def load_bars():
    """Every OHLC bar LEAN read, from its own zips."""
    o, h, l, c = {}, {}, {}, {}
    for t in SECTORS + [DEFENSIVE, "SPY"]:
        with zipfile.ZipFile(os.path.join(DAILY, t.lower() + ".zip")) as z:
            body = z.read(z.namelist()[0]).decode()
        df = pd.read_csv(io.StringIO(body), header=None,
                         names=["ts", "o", "h", "l", "c", "v"])
        idx = pd.to_datetime(df["ts"].str.slice(0, 8), format="%Y%m%d")
        o[t] = pd.Series((df["o"] / SCALE).values, index=idx)
        h[t] = pd.Series((df["h"] / SCALE).values, index=idx)
        l[t] = pd.Series((df["l"] / SCALE).values, index=idx)
        c[t] = pd.Series((df["c"] / SCALE).values, index=idx)
    return (pd.DataFrame(o), pd.DataFrame(h),
            pd.DataFrame(l), pd.DataFrame(c))


def load_fills():
    pattern = os.path.join(RUN, "*-order-events.json") if RUN else None
    if not pattern:
        sys.exit("pass the backtest run directory")
    import glob
    paths = glob.glob(pattern)
    if not paths:
        sys.exit("no order-events json in %s" % RUN)
    recs = json.load(open(paths[0], encoding="utf-8"))
    if isinstance(recs, dict):
        recs = recs.get("orderEvents", [])
    rows = []
    for r in recs:
        if str(r.get("status", "")).lower() != "filled":
            continue
        rows.append({
            "order_id": r["orderId"],
            "ticker": r.get("symbolValue") or r["symbol"].split()[0],
            "ts": pd.to_datetime(float(r["time"]), unit="s"),
            "price": float(r["fillPrice"]),
            "qty": float(r["fillQuantity"]),
        })
    df = pd.DataFrame(rows).sort_values(["ts", "order_id"])
    df["date"] = df["ts"].dt.normalize()
    return df


def q1_fill_convention(fills, opens, highs, lows, closes):
    print("\n" + "=" * 72)
    print("Q1: which bar does LEAN fill on?")
    print("=" * 72)
    trading = closes.index
    tally = {"close(D)": 0, "open(D)": 0, "close(D-1)": 0,
             "open(D+1)": 0, "none": 0}
    resid = {k: [] for k in tally}
    for r in fills.itertuples():
        t, d, p = r.ticker, r.date, r.price
        if t not in closes.columns:
            continue
        pos = trading.searchsorted(d)
        if pos >= len(trading) or trading[pos] != d:
            tally["none"] += 1
            continue
        cands = {"close(D)": closes.iloc[pos][t], "open(D)": opens.iloc[pos][t]}
        if pos > 0:
            cands["close(D-1)"] = closes.iloc[pos - 1][t]
        if pos + 1 < len(trading):
            cands["open(D+1)"] = opens.iloc[pos + 1][t]
        best, bestd = None, 1e18
        for k, v in cands.items():
            dd = abs(p - v) / max(v, 1e-9)
            resid[k].append(dd)
            if dd < bestd:
                best, bestd = k, dd
        tally[best] += 1

    n = sum(tally.values())
    print("  fills matched to nearest candidate bar (n=%d):" % n)
    for k, v in sorted(tally.items(), key=lambda kv: -kv[1]):
        if v:
            print("     %-12s %5d  (%5.1f%%)" % (k, v, 100.0 * v / max(n, 1)))
    print("\n  median |fillPrice/candidate - 1| across ALL fills:")
    for k in ["close(D)", "open(D)", "close(D-1)", "open(D+1)"]:
        if resid[k]:
            a = np.array(resid[k])
            print("     %-12s median=%9.3e  mean=%9.3e  p95=%9.3e"
                  % (k, np.median(a), a.mean(), np.quantile(a, 0.95)))
    print("\n  -> the candidate with a ~0 median is the convention LEAN used.")


def q2_realized_weights(fills, closes):
    print("\n" + "=" * 72)
    print("Q2: did LEAN's realized portfolio ever differ from the intent?")
    print("=" * 72)
    # Reconstruct share positions over time from the fills.
    shares = {}
    snapshots = {}          # date -> {ticker: shares} right after trading
    for d, grp in fills.groupby("date"):
        for r in grp.itertuples():
            shares[r.ticker] = shares.get(r.ticker, 0.0) + r.qty
            if abs(shares[r.ticker]) < 1e-9:
                del shares[r.ticker]
        snapshots[d] = dict(shares)

    # Harness intent, keyed by hold month.
    px = lb.load_prices()
    px = px[px.index >= pd.Timestamp(lb.WARMUP_START)]
    weights, diag, _ = lb.build_signals(px)

    rows = []
    for d in sorted(snapshots):
        pos = snapshots[d]
        if not pos:
            continue
        if d not in closes.index:
            continue
        mark = closes.loc[d]
        val = sum(q * mark[t] for t, q in pos.items() if t in mark.index)
        if val <= 0:
            continue
        realized = {t: q * mark[t] / val for t, q in pos.items()
                    if t in mark.index}
        month = pd.Period(d, freq="M")
        intent = weights.get(month)
        if intent is None:
            continue
        keys = set(realized) | set(intent)
        # cash sits outside the weight vector; compare on invested share
        l1 = sum(abs(realized.get(k, 0.0) - intent.get(k, 0.0)) for k in keys)
        rows.append({"date": d, "month": str(month), "l1": l1,
                     "held": tuple(sorted(realized)),
                     "intended": tuple(sorted(intent))})

    df = pd.DataFrame(rows)
    print("  rebalance dates reconstructed from fills : %d" % len(df))
    same_set = df[df["held"] == df["intended"]]
    print("  months where the HELD SET matches intent : %d / %d"
          % (len(same_set), len(df)))
    bad = df[df["held"] != df["intended"]]
    if len(bad):
        print("  months where the held set DIFFERS:")
        for r in bad.head(20).itertuples():
            print("     %s held=%s intended=%s" % (r.month, r.held, r.intended))
    else:
        print("  -> the minimum-order-size filter never changed WHICH assets"
              " were held.")
    print("\n  L1 weight error vs intent (sum |realized - intended|):")
    print("     median=%.5f  p95=%.5f  max=%.5f"
          % (df["l1"].median(), df["l1"].quantile(0.95), df["l1"].max()))
    print("     worst 5:")
    for r in df.nlargest(5, "l1").itertuples():
        print("       %s L1=%.5f held=%s" % (r.month, r.l1, r.held))
    print("\n  (a nonzero floor is expected: whole shares + 0.25% cash buffer)")

    # Order count sanity: 726 reported.
    print("\n  fills=%d  distinct order ids=%d  distinct trade dates=%d"
          % (len(fills), fills["order_id"].nunique(),
             fills["date"].nunique()))
    return df


def q3_timing_attribution(closes, opens):
    print("\n" + "=" * 72)
    print("Q3: is the monthly difference explained by the one-day gap?")
    print("=" * 72)
    import glob
    paths = [p for p in glob.glob(os.path.join(RUN, "*.json"))
             if "order-events" not in p and "summary" not in p]
    doc = json.load(open(max(paths, key=os.path.getsize), encoding="utf-8"))
    vals = doc["charts"]["Strategy Equity"]["series"]["Equity"]["values"]
    times, cl = [], []
    for v in vals:
        if isinstance(v, dict):
            times.append(pd.to_datetime(int(v.get("x")), unit="s"))
            cl.append(float(v.get("close", v.get("y"))))
        else:
            times.append(pd.to_datetime(int(v[0]), unit="s"))
            cl.append(float(v[-1]))
    lean = pd.Series(cl, index=pd.DatetimeIndex(times)).sort_index()
    lean.index = lean.index.normalize()
    lean = lean[~lean.index.duplicated(keep="last")]

    px = lb.load_prices()
    px = px[px.index >= pd.Timestamp(lb.WARMUP_START)]
    weights, diag, _ = lb.build_signals(px)
    h10 = lb.run(px, weights, 10.0)

    common = lean.index.intersection(h10.index)
    lm = lean.reindex(common).dropna()
    hm = h10.reindex(common).dropna()
    lmr = lm.groupby(lm.index.to_period("M")).last().pct_change()
    hmr = hm.groupby(hm.index.to_period("M")).last().pct_change()
    both = pd.concat([lmr.rename("lean"), hmr.rename("harness")],
                     axis=1).dropna()
    both["diff"] = both["lean"] - both["harness"]

    # For each hold month, the "gap return": what the NEWLY-BOUGHT basket did
    # on the first trading day, minus what the OLD basket did. That day is
    # earned by the harness's new book but by LEAN's old book.
    periods = closes.index.to_period("M")
    gap = {}
    months = sorted(weights)
    for i, m in enumerate(months):
        blk = closes.index[periods == m]
        if len(blk) == 0:
            continue
        pos = closes.index.get_loc(blk[0])
        if pos < 1:
            continue
        d0, dm1 = closes.index[pos], closes.index[pos - 1]
        new_w = weights[m]
        old_w = weights[months[i - 1]] if i > 0 else {}
        def basket(w):
            s = 0.0
            for t, wt in w.items():
                if t in closes.columns:
                    s += wt * (closes.loc[d0, t] / closes.loc[dm1, t] - 1.0)
            return s
        if not old_w:
            continue
        gap[str(m)] = basket(new_w) - basket(old_w)

    g = pd.Series(gap)
    g.index = pd.PeriodIndex(g.index, freq="M")
    j = pd.concat([both, g.rename("gap")], axis=1).dropna()
    print("  months with both a return diff and a computable gap: %d" % len(j))
    corr = j["diff"].corr(-j["gap"])
    print("  corr( lean-harness diff , -gap_return ) = %+.4f" % corr)
    print("  (positive and large => the difference IS the one-day handover)")
    # How much of the variance does the gap explain?
    ss_tot = float(((j["diff"] - j["diff"].mean()) ** 2).sum())
    resid = j["diff"] + j["gap"]
    ss_res = float(((resid - resid.mean()) ** 2).sum())
    print("  variance of monthly diff explained by the gap: %.1f%%"
          % (100.0 * (1 - ss_res / ss_tot)))
    print("  stdev of diff  = %.4f pp ; stdev after removing gap = %.4f pp"
          % (100 * j["diff"].std(), 100 * resid.std()))
    print("\n  worst 8 months by |diff|, with the gap that should explain them:")
    for m in j["diff"].abs().nlargest(8).index:
        print("    %s  diff %+6.2f pp   -gap %+6.2f pp   residual %+6.2f pp"
              % (m, 100 * j.loc[m, "diff"], -100 * j.loc[m, "gap"],
                 100 * (j.loc[m, "diff"] + j.loc[m, "gap"])))


def main():
    opens, highs, lows, closes = load_bars()
    fills = load_fills()
    print("fills loaded: %d  (%s -> %s)"
          % (len(fills), fills["date"].min().date(), fills["date"].max().date()))
    q1_fill_convention(fills, opens, highs, lows, closes)
    q2_realized_weights(fills, closes)
    q3_timing_attribution(closes, opens)


if __name__ == "__main__":
    main()
