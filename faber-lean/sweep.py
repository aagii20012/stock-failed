"""Parameter sensitivity for the Faber rotation.

One backtest is one draw. If the result only exists at (12, 10, 3) it is a
fit to this window, not a property of the strategy. This sweeps the three
free parameters and reports CAGR / Sharpe / max drawdown for each.
"""

import itertools

import pandas as pd

import local_backtest as lb

ROWS = []

px = lb.load_prices()
px = px[px.index >= pd.Timestamp(lb.WARMUP_START)]
rf = px[lb.DEFENSIVE].pct_change()

for mom, sma, top_n in itertools.product([3, 6, 9, 12], [6, 10, 12], [1, 2, 3, 4]):
    lb.MOM_LOOKBACK, lb.SMA_LENGTH, lb.TOP_N = mom, sma, top_n
    weights, diag, _ = lb.build_signals(px)
    if diag.empty:
        continue
    curve = lb.run(px, weights, cost_bps=10.0)
    s = lb.stats(curve, rf, f"m{mom}/s{sma}/k{top_n}")
    slots = len(diag) * top_n
    s["skip_pct"] = 100.0 * diag["n_skipped"].sum() / slots
    ROWS.append(s)

t = pd.DataFrame(ROWS).set_index("label")
t = t[["cagr", "sharpe_rf_shy", "maxdd_daily", "skip_pct"]]
t.columns = ["CAGR", "Sharpe(SHY)", "MaxDD", "skip%"]
t["CAGR"] = (t["CAGR"] * 100).round(2)
t["MaxDD"] = (t["MaxDD"] * 100).round(1)
t["Sharpe(SHY)"] = t["Sharpe(SHY)"].round(3)
t["skip%"] = t["skip%"].round(1)

pd.set_option("display.max_rows", 100)
print("\n=== all 48 configs, net of 10bps turnover cost ===")
print(t.to_string())
print("\n=== distribution of CAGR across configs ===")
print(t["CAGR"].describe().round(2).to_string())
print("\n=== best / worst 5 by Sharpe ===")
srt = t.sort_values("Sharpe(SHY)", ascending=False)
print(srt.head(5).to_string())
print("...")
print(srt.tail(5).to_string())
