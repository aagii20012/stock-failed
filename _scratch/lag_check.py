"""Is LEAN's equity series aligned to the harness, or off by a day?

LEAN samples the Strategy Equity chart for a daily-resolution algorithm at
midnight *following* the bar it summarizes, so a point stamped 2014-08-01T00:00
can be the value at the close of 2014-07-31. Normalizing the timestamp to a
date (what compare_lean_vs_harness.py does) does not undo that -- it would
leave the whole series shifted one day late, which would mis-attribute each
month's last day to the next month and show up as offsetting adjacent-month
residuals. That is exactly the pattern fill_forensics Q3 found.

Test it the cheap way: correlate LEAN daily returns against harness daily
returns at several lags. The lag with the highest correlation is the true
alignment. Then re-run the month-boundary attribution on the corrected series.
"""

import glob
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
FABER = os.path.abspath(os.path.join(HERE, "..", "faber-lean"))
sys.path.insert(0, FABER)
import local_backtest as lb  # noqa: E402

RUN = sys.argv[1]


def lean_curve():
    paths = [p for p in glob.glob(os.path.join(RUN, "*.json"))
             if "order-events" not in p and "summary" not in p]
    doc = json.load(open(max(paths, key=os.path.getsize), encoding="utf-8"))
    vals = doc["charts"]["Strategy Equity"]["series"]["Equity"]["values"]
    times, cl = [], []
    for v in vals:
        if isinstance(v, dict):
            times.append(int(v.get("x")))
            cl.append(float(v.get("close", v.get("y"))))
        else:
            times.append(int(v[0]))
            cl.append(float(v[-1]))
    raw = pd.Series(cl, index=pd.to_datetime(times, unit="s")).sort_index()
    return raw


def main():
    raw = lean_curve()
    print("=== raw LEAN equity timestamps ===")
    print("  points: %d" % len(raw))
    print("  first 5:")
    for t, v in raw.head(5).items():
        print("     %s  %.2f" % (t, v))
    print("  last 5:")
    for t, v in raw.tail(5).items():
        print("     %s  %.2f" % (t, v))
    tod = pd.Series(raw.index.time).value_counts()
    print("  distinct times-of-day: %s" % dict(list(tod.items())[:6]))

    px = lb.load_prices()
    px = px[px.index >= pd.Timestamp(lb.WARMUP_START)]
    weights, diag, _ = lb.build_signals(px)
    h10 = lb.run(px, weights, 10.0)
    hr = h10.pct_change().dropna()

    print("\n=== daily-return correlation vs harness, by shift ===")
    print("  (shift = days SUBTRACTED from LEAN's stamp before aligning)")
    best = None
    for shift in (-2, -1, 0, 1, 2):
        c = raw.copy()
        c.index = (c.index.normalize() - pd.Timedelta(days=shift))
        c = c[~c.index.duplicated(keep="last")]
        common = c.index.intersection(h10.index)
        if len(common) < 100:
            print("  shift %+d : too few common days (%d)" % (shift, len(common)))
            continue
        lr = c.reindex(common).dropna().pct_change().dropna()
        j = pd.concat([lr.rename("l"), hr.rename("h")], axis=1).dropna()
        corr = j["l"].corr(j["h"])
        mad = (j["l"] - j["h"]).abs().mean()
        print("  shift %+d : n=%4d  corr=%+.5f  mean|diff|=%.5f pp"
              % (shift, len(j), corr, 100 * mad))
        if best is None or corr > best[1]:
            best = (shift, corr)
    print("\n  -> best alignment: shift %+d (corr %+.5f)" % best)

    # Rebuild on the best alignment and recompute the headline stats.
    shift = best[0]
    c = raw.copy()
    c.index = (c.index.normalize() - pd.Timedelta(days=shift))
    c = c[~c.index.duplicated(keep="last")]
    common = c.index.intersection(h10.index)
    lean = c.reindex(common).dropna()
    rf = px[lb.DEFENSIVE].pct_change()
    h0 = lb.run(px, weights, 0.0)

    rows = [lb.stats(lean, rf, "LEAN (aligned shift %+d)" % shift),
            lb.stats(h10.reindex(common).dropna(), rf, "harness 10bps"),
            lb.stats(h0.reindex(common).dropna(), rf, "harness 0bps")]
    table = pd.DataFrame(rows).set_index("label")
    fmt = table.copy()
    for k in ["total_return", "cagr", "vol", "maxdd_daily", "maxdd_monthly"]:
        fmt[k] = (fmt[k] * 100).round(2).astype(str) + "%"
    for k in ["sharpe_rf0", "sharpe_rf_shy"]:
        fmt[k] = fmt[k].round(3)
    fmt["years"] = fmt["years"].round(2)
    pd.set_option("display.width", 220, "display.max_columns", 50)
    print("\n=== stats on the ALIGNED LEAN curve ===")
    print(fmt.to_string())

    # Month-boundary attribution on the aligned series.
    lm = lean.groupby(lean.index.to_period("M")).last().pct_change()
    hc = h10.reindex(common).dropna()
    hm = hc.groupby(hc.index.to_period("M")).last().pct_change()
    both = pd.concat([lm.rename("lean"), hm.rename("harness")],
                     axis=1).dropna()
    both["diff"] = both["lean"] - both["harness"]

    periods = px.index.to_period("M")
    months = sorted(weights)
    gap = {}
    for i, m in enumerate(months):
        if i == 0:
            continue
        blk = px.index[periods == m]
        if len(blk) == 0:
            continue
        pos = px.index.get_loc(blk[0])
        if pos < 1:
            continue
        d0, dm1 = px.index[pos], px.index[pos - 1]
        def basket(w):
            return sum(wt * (px.loc[d0, t] / px.loc[dm1, t] - 1.0)
                       for t, wt in w.items() if t in px.columns)
        gap[m] = basket(weights[m]) - basket(weights[months[i - 1]])
    g = pd.Series(gap)
    j = pd.concat([both, g.rename("gap")], axis=1).dropna()
    corr = j["diff"].corr(-j["gap"])
    resid = j["diff"] + j["gap"]
    ss_tot = float(((j["diff"] - j["diff"].mean()) ** 2).sum())
    ss_res = float(((resid - resid.mean()) ** 2).sum())
    print("\n=== month-boundary attribution on the aligned series ===")
    print("  months            : %d" % len(j))
    print("  corr(diff, -gap)  : %+.4f" % corr)
    print("  variance explained: %.1f%%" % (100 * (1 - ss_res / ss_tot)))
    print("  stdev diff        : %.4f pp -> after removing gap %.4f pp"
          % (100 * j["diff"].std(), 100 * resid.std()))
    print("  worst 8 by |diff|:")
    for m in j["diff"].abs().nlargest(8).index:
        print("    %s  diff %+6.2f pp   -gap %+6.2f pp   residual %+6.2f pp"
              % (m, 100 * j.loc[m, "diff"], -100 * j.loc[m, "gap"],
                 100 * resid.loc[m]))


if __name__ == "__main__":
    main()
