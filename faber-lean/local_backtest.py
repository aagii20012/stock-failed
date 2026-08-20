"""Standalone re-implementation of faber_sector_rotation.py.

Same rules, same monthly-close signals, no LEAN and no QuantConnect account.
Exists so the strategy can be measured offline; it is a measuring stick for
the LEAN algorithm, not a replacement for it.
"""

import os
import sys

import numpy as np
import pandas as pd

SECTORS = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB"]
DEFENSIVE = "SHY"
BENCH = "SPY"
TOP_N = 3
MOM_LOOKBACK = 12
SMA_LENGTH = 10

START = "2007-01-01"
END = "2026-08-20"
WARMUP_START = "2005-06-01"   # 12 monthly bars of runway before START
HOLD_START = "2007-01"   # first month actually held
CACHE = "prices.csv"


def load_prices():
    if os.path.exists(CACHE):
        px = pd.read_csv(CACHE, index_col=0, parse_dates=True)
        print(f"prices: cached {CACHE}")
    else:
        import yfinance as yf
        raw = yf.download(SECTORS + [DEFENSIVE, BENCH], start=WARMUP_START, end=END,
                          auto_adjust=True, progress=False)
        px = raw["Close"].dropna(how="any")
        px.to_csv(CACHE)
        print(f"prices: downloaded -> {CACHE}")
    print(f"        {px.shape[0]} daily bars, {px.index.min().date()} -> {px.index.max().date()}")
    missing = [c for c in SECTORS + [DEFENSIVE, BENCH] if c not in px.columns]
    if missing:
        sys.exit(f"missing tickers: {missing}")
    return px


def build_signals(px):
    """Return (weights_by_month, diagnostics). Weights for month M are decided
    from closes through M-1, so they are applied to M's return."""
    monthly = px.groupby(px.index.to_period("M")).last()
    months = monthly.index

    weights = {}
    diag = []

    # i indexes the *signal* month; the trade is held the following month.
    for i in range(MOM_LOOKBACK, len(months) - 1):
        signal_month = months[i]
        hold_month = months[i + 1]

        last = monthly.iloc[i]
        momentum = last / monthly.iloc[i - MOM_LOOKBACK] - 1.0
        sma = monthly.iloc[i - SMA_LENGTH + 1: i + 1].mean()

        ranked = sorted(SECTORS, key=lambda t: momentum[t], reverse=True)[:TOP_N]

        w = {}
        skipped = []
        for t in ranked:
            if last[t] > sma[t]:
                w[t] = w.get(t, 0.0) + 1.0 / TOP_N
            else:
                w[DEFENSIVE] = w.get(DEFENSIVE, 0.0) + 1.0 / TOP_N
                skipped.append(t)

        if str(hold_month) >= HOLD_START:
            weights[hold_month] = w
        if str(hold_month) < HOLD_START:
            continue
        diag.append({"signal_month": str(signal_month), "hold_month": str(hold_month),
                     "ranked": ranked, "skipped": skipped,
                     "n_skipped": len(skipped)})

    return weights, pd.DataFrame(diag), monthly


def run(px, weights, cost_bps=0.0):
    """Daily-marked equity curve. Weights are set at the close of the signal
    month and then held -- assets drift with their own returns inside the
    month, which is what a monthly set_holdings actually does."""
    periods = px.index.to_period("M")

    levels, dates = [], []
    level = 1.0
    prev_w = {}

    for month in sorted(weights.keys()):
        w = weights[month]
        mask = periods == month
        if not mask.any():
            continue

        block = px.loc[mask]
        start_pos = px.index.get_loc(block.index[0]) - 1
        if start_pos < 0:
            continue

        turnover = sum(abs(w.get(t, 0.0) - prev_w.get(t, 0.0))
                       for t in set(w) | set(prev_w))
        level *= (1.0 - turnover * cost_bps / 10_000.0)
        prev_w = w

        growth = block.divide(px.iloc[start_pos], axis=1)
        port = sum(weight * growth[t] for t, weight in w.items())

        levels.extend((level * port).tolist())
        dates.extend(block.index.tolist())
        level *= port.iloc[-1]

    return pd.Series(levels, index=pd.DatetimeIndex(dates))


def stats(curve, rf_daily=None, label=""):
    if curve.empty:
        return {}
    years = (curve.index[-1] - curve.index[0]).days / 365.25
    total = curve.iloc[-1] / curve.iloc[0]
    cagr = total ** (1 / years) - 1

    daily = curve.pct_change().dropna()
    vol = daily.std() * np.sqrt(252)
    sharpe_0 = (daily.mean() * 252) / vol if vol > 0 else float("nan")

    sharpe_rf = float("nan")
    if rf_daily is not None:
        ex = (daily - rf_daily.reindex(daily.index).fillna(0.0))
        sharpe_rf = (ex.mean() * 252) / (ex.std() * np.sqrt(252))

    dd_daily = (curve / curve.cummax() - 1.0).min()
    monthly = curve.groupby(curve.index.to_period("M")).last()
    dd_monthly = (monthly / monthly.cummax() - 1.0).min()

    return {"label": label, "years": years, "total_return": total - 1, "cagr": cagr,
            "vol": vol, "sharpe_rf0": sharpe_0, "sharpe_rf_shy": sharpe_rf,
            "maxdd_daily": dd_daily, "maxdd_monthly": dd_monthly}


def main():
    px = load_prices()
    px = px[px.index >= pd.Timestamp(WARMUP_START)]

    weights, diag, monthly = build_signals(px)

    # Variant with the trend filter disabled: always hold the top 3.
    no_filter = {}
    for row in diag.itertuples():
        m = pd.Period(row.hold_month)
        no_filter[m] = {t: 1.0 / TOP_N for t in row.ranked}

    rf_daily = px[DEFENSIVE].pct_change()

    curves = {
        "faber (filter on, 0bps)": run(px, weights, 0.0),
        "faber (filter on, 10bps)": run(px, weights, 10.0),
        "no trend filter (0bps)": run(px, no_filter, 0.0),
    }

    first = curves["faber (filter on, 0bps)"].index[0]
    spy = px[BENCH].loc[px.index >= first]
    curves["SPY buy & hold"] = spy / spy.iloc[0]

    rows = [stats(c, rf_daily, name) for name, c in curves.items()]
    table = pd.DataFrame(rows).set_index("label")

    pd.set_option("display.width", 200, "display.max_columns", 50)
    print("\n=== performance ===")
    print(f"window: {first.date()} -> {px.index[-1].date()}\n")
    fmt = table.copy()
    for c in ["total_return", "cagr", "vol", "maxdd_daily", "maxdd_monthly"]:
        fmt[c] = (fmt[c] * 100).round(2).astype(str) + "%"
    for c in ["sharpe_rf0", "sharpe_rf_shy"]:
        fmt[c] = fmt[c].round(3)
    fmt["years"] = fmt["years"].round(1)
    print(fmt.to_string())

    slots = len(diag) * TOP_N
    skipped = int(diag["n_skipped"].sum())
    print("\n=== trend filter ===")
    print(f"rebalances                 : {len(diag)}")
    print(f"slots evaluated            : {slots}")
    print(f"slots sent to {DEFENSIVE}        : {skipped}  ({100*skipped/slots:.1f}%)")
    print(f"months fully in {DEFENSIVE}      : {int((diag['n_skipped'] == TOP_N).sum())}")
    print(f"months fully invested      : {int((diag['n_skipped'] == 0).sum())}")

    print("\nskips by sector (times a top-3 pick was below its 10m SMA):")
    counts = pd.Series([t for row in diag['skipped'] for t in row]).value_counts()
    print(counts.to_string() if not counts.empty else "  none")

    print("\nskipped slots by year:")
    by_year = diag.assign(year=diag["hold_month"].str[:4]).groupby("year")["n_skipped"].sum()
    print(by_year.to_string())

    diag.to_csv("rebalance_log.csv", index=False)
    print("\nper-month decisions -> rebalance_log.csv")


if __name__ == "__main__":
    main()
