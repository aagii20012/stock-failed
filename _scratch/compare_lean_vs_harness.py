"""Compare the LEAN backtest against the standalone pandas harness.

Extracts LEAN's daily equity curve from the backtest result JSON and runs the
*harness's own* stats() formulas on it, so any difference is engine mechanics
(execution timing, fees, share quantization) rather than a different metric
definition. LEAN's own reported Sharpe uses a Fed-funds risk-free series and
its own annualization, which is not comparable to the harness's "vs SHY".

Usage: python compare_lean_vs_harness.py [path/to/backtests/<run>]
"""

import glob
import json
import os
import sys

import numpy as np
import pandas as pd

FABER = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "..", "faber-lean")
FABER = os.path.abspath(FABER)
sys.path.insert(0, FABER)

import local_backtest as lb  # noqa: E402


def find_result_json(run_dir=None):
    """Locate the LEAN backtest result JSON (the one with a statistics block)."""
    if run_dir:
        candidates = sorted(glob.glob(os.path.join(run_dir, "*.json")))
    else:
        pattern = os.path.join(FABER, "FaberSectorRotation", "backtests",
                               "*", "*.json")
        candidates = sorted(glob.glob(pattern))
    if not candidates:
        sys.exit("no backtest JSON found -- has `lean backtest` run?")

    best = None
    for path in candidates:
        base = os.path.basename(path)
        if base in ("config.json",) or "order-events" in base:
            continue
        try:
            with open(path, encoding="utf-8") as f:
                doc = json.load(f)
        except Exception:
            continue
        if not isinstance(doc, dict):
            continue
        if "statistics" in doc or "Statistics" in doc or "charts" in doc \
                or "Charts" in doc:
            # newest run wins
            if best is None or os.path.getmtime(path) > os.path.getmtime(best[0]):
                best = (path, doc)
    if best is None:
        sys.exit("found JSON files but none look like a LEAN result:\n  " +
                 "\n  ".join(candidates))
    return best


def key(doc, *names):
    for n in names:
        if n in doc:
            return doc[n]
    return None


def equity_curve(doc):
    """Pull the Strategy Equity series out of the result JSON as a Series."""
    charts = key(doc, "charts", "Charts") or {}
    chart = None
    for name in ("Strategy Equity", "StrategyEquity"):
        if name in charts:
            chart = charts[name]
            break
    if chart is None:
        sys.exit("no 'Strategy Equity' chart in result JSON; keys=%s"
                 % list(charts)[:20])

    series_map = key(chart, "series", "Series") or {}
    ser = None
    for name in ("Equity", "equity"):
        if name in series_map:
            ser = series_map[name]
            break
    if ser is None:
        sys.exit("no 'Equity' series; keys=%s" % list(series_map)[:20])

    values = key(ser, "values", "Values") or []
    times, closes = [], []
    for v in values:
        if isinstance(v, dict):
            t = v.get("x", v.get("X"))
            # candlestick points carry open/high/low/close
            c = v.get("close", v.get("Close", v.get("y", v.get("Y"))))
        elif isinstance(v, (list, tuple)) and v:
            t = v[0]
            c = v[-1]          # [time, o, h, l, c] -> close ; [time, y] -> y
        else:
            continue
        if t is None or c is None:
            continue
        times.append(pd.to_datetime(int(t), unit="s"))
        closes.append(float(c))

    curve = pd.Series(closes, index=pd.DatetimeIndex(times)).sort_index()
    # LEAN stamps daily equity points at midnight of the following day for
    # daily resolution; normalize to date so it aligns with the harness.
    curve.index = curve.index.normalize()
    curve = curve[~curve.index.duplicated(keep="last")]
    return curve


def main():
    run_dir = sys.argv[1] if len(sys.argv) > 1 else None
    path, doc = find_result_json(run_dir)
    print("result json : %s" % path)

    # ---- LEAN's own reported statistics -------------------------------
    stats_block = key(doc, "statistics", "Statistics") or {}
    runtime = key(doc, "runtimeStatistics", "RuntimeStatistics") or {}
    interesting = ["Compounding Annual Return", "Drawdown", "Sharpe Ratio",
                   "Probabilistic Sharpe Ratio", "Net Profit",
                   "Annual Standard Deviation", "Total Orders", "Total Trades",
                   "Total Fees", "Average Win", "Average Loss",
                   "Start Equity", "End Equity", "Capacity"]
    print("\n=== LEAN reported statistics ===")
    for k in interesting:
        if k in stats_block:
            print("  %-30s %s" % (k, stats_block[k]))
    for k, v in runtime.items():
        print("  [runtime] %-19s %s" % (k, v))

    # ---- LEAN equity curve, measured with the harness's formulas ------
    curve = equity_curve(doc)
    print("\n=== LEAN equity curve ===")
    print("  points      : %d" % len(curve))
    print("  window      : %s -> %s" % (curve.index[0].date(),
                                        curve.index[-1].date()))
    print("  start/end   : %.2f -> %.2f" % (curve.iloc[0], curve.iloc[-1]))

    # Harness prices, for the SHY risk-free leg and a like-for-like rerun.
    os.chdir(FABER)
    px = lb.load_prices()
    px = px[px.index >= pd.Timestamp(lb.WARMUP_START)]
    rf_daily = px[lb.DEFENSIVE].pct_change()

    weights, diag, _ = lb.build_signals(px)
    h0 = lb.run(px, weights, 0.0)
    h10 = lb.run(px, weights, 10.0)

    # Restrict every curve to the overlapping dates so the comparison is
    # not contaminated by a one-day difference in start or end.
    common = curve.index.intersection(h10.index)
    print("  overlap w/ harness: %d days (%s -> %s)"
          % (len(common), common.min().date(), common.max().date()))

    rows = []
    for label, c in [("LEAN (full)", curve),
                     ("LEAN (overlap)", curve.reindex(common).dropna()),
                     ("harness 10bps (overlap)", h10.reindex(common).dropna()),
                     ("harness 0bps (overlap)", h0.reindex(common).dropna()),
                     ("harness 10bps (full)", h10),
                     ("harness 0bps (full)", h0)]:
        if c.empty:
            continue
        rows.append(lb.stats(c, rf_daily, label))

    table = pd.DataFrame(rows).set_index("label")
    fmt = table.copy()
    for c in ["total_return", "cagr", "vol", "maxdd_daily", "maxdd_monthly"]:
        fmt[c] = (fmt[c] * 100).round(2).astype(str) + "%"
    for c in ["sharpe_rf0", "sharpe_rf_shy"]:
        fmt[c] = fmt[c].round(3)
    fmt["years"] = fmt["years"].round(2)
    pd.set_option("display.width", 220, "display.max_columns", 50)
    print("\n=== same formulas applied to both ===")
    print(fmt.to_string())

    # ---- headline deltas ---------------------------------------------
    L = table.loc["LEAN (overlap)"] if "LEAN (overlap)" in table.index else None
    H = table.loc["harness 10bps (overlap)"] \
        if "harness 10bps (overlap)" in table.index else None
    if L is not None and H is not None:
        print("\n=== deltas (LEAN - harness10bps, overlap window) ===")
        print("  CAGR         : %+.3f pp   (%.2f%% vs %.2f%%)"
              % (100 * (L.cagr - H.cagr), 100 * L.cagr, 100 * H.cagr))
        print("  Sharpe/SHY   : %+.4f      (%.3f vs %.3f)"
              % (L.sharpe_rf_shy - H.sharpe_rf_shy,
                 L.sharpe_rf_shy, H.sharpe_rf_shy))
        print("  MaxDD daily  : %+.3f pp   (%.2f%% vs %.2f%%)"
              % (100 * (L.maxdd_daily - H.maxdd_daily),
                 100 * L.maxdd_daily, 100 * H.maxdd_daily))
        print("  Vol          : %+.3f pp   (%.2f%% vs %.2f%%)"
              % (100 * (L.vol - H.vol), 100 * L.vol, 100 * H.vol))

    # ---- monthly return correlation: is it timing or is it logic? -----
    if L is not None:
        lc = curve.reindex(common).dropna()
        hc = h10.reindex(common).dropna()
        lm = lc.groupby(lc.index.to_period("M")).last().pct_change().dropna()
        hm = hc.groupby(hc.index.to_period("M")).last().pct_change().dropna()
        both = pd.concat([lm.rename("lean"), hm.rename("harness")],
                         axis=1).dropna()
        if len(both) > 2:
            corr = both["lean"].corr(both["harness"])
            print("\n=== monthly return agreement ===")
            print("  months compared      : %d" % len(both))
            print("  correlation          : %.4f" % corr)
            print("  mean abs difference  : %.4f pp"
                  % (100 * (both["lean"] - both["harness"]).abs().mean()))
            print("  worst 8 months by |difference|:")
            d = (both["lean"] - both["harness"]).abs().sort_values(
                ascending=False).head(8)
            for m in d.index:
                print("    %s  lean %+7.2f%%  harness %+7.2f%%  diff %+6.2f pp"
                      % (m, 100 * both.loc[m, "lean"],
                         100 * both.loc[m, "harness"],
                         100 * (both.loc[m, "lean"] - both.loc[m, "harness"])))

    # ---- harness diagnostics for the trend-filter comparison ---------
    slots = len(diag) * lb.TOP_N
    skipped = int(diag["n_skipped"].sum())
    print("\n=== harness trend filter (compare against LEAN log line) ===")
    print("  rebalances=%d slots=%d skipped=%d (%.1f%%) fully_defensive=%d"
          % (len(diag), slots, skipped, 100.0 * skipped / slots,
             int((diag["n_skipped"] == lb.TOP_N).sum())))
    counts = pd.Series([t for row in diag["skipped"] for t in row]).value_counts()
    print("  skips_by_sector=%s" % counts.to_dict())


if __name__ == "__main__":
    main()
