"""Prove (or disprove) that LEAN and the harness are fed the same prices.

The harness reads faber-lean/prices.csv (yfinance Close, auto_adjust=True).
LEAN reads faber-lean/data/equity/usa/daily/<t>.zip, written by
make_lean_data.py from the same yfinance call, in deci-cents, with identity
factor files. If the two agree to rounding, then any backtest divergence is
engine mechanics and NOT a data/split/dividend adjustment difference.

Also checks the factor files really are identity (no split/div events) and
reports the deci-cent quantization error, which is the only data-level
difference that can exist by construction.
"""

import io
import os
import zipfile

import pandas as pd

FABER = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", "faber-lean"))
DAILY = os.path.join(FABER, "data", "equity", "usa", "daily")
FACTORS = os.path.join(FABER, "data", "equity", "usa", "factor_files")
MAPS = os.path.join(FABER, "data", "equity", "usa", "map_files")
SCALE = 10_000.0

TICKERS = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB",
           "SHY", "SPY"]


def read_zip(ticker):
    path = os.path.join(DAILY, ticker.lower() + ".zip")
    with zipfile.ZipFile(path) as z:
        name = z.namelist()[0]
        body = z.read(name).decode()
    df = pd.read_csv(io.StringIO(body), header=None,
                     names=["ts", "open", "high", "low", "close", "volume"])
    df["date"] = pd.to_datetime(df["ts"].str.slice(0, 8), format="%Y%m%d")
    for c in ("open", "high", "low", "close"):
        df[c] = df[c] / SCALE
    return df.set_index("date")


def main():
    px = pd.read_csv(os.path.join(FABER, "prices.csv"),
                     index_col=0, parse_dates=True)
    print("harness prices.csv : %d rows, %s -> %s, cols=%d"
          % (px.shape[0], px.index.min().date(), px.index.max().date(),
             px.shape[1]))

    print("\n=== factor files (must be identity: no split/dividend events) ===")
    non_identity = []
    for t in TICKERS:
        with open(os.path.join(FACTORS, t.lower() + ".csv")) as f:
            lines = [ln.strip() for ln in f if ln.strip()]
        bad = [ln for ln in lines if ln.split(",")[1:3] != ["1", "1"]]
        flag = "IDENTITY" if not bad else "NON-IDENTITY %s" % bad
        if bad:
            non_identity.append(t)
        print("  %-4s %d rows  %s" % (t, len(lines), flag))

    print("\n=== map files (delisting / ticker changes) ===")
    for t in TICKERS:
        with open(os.path.join(MAPS, t.lower() + ".csv")) as f:
            lines = [ln.strip() for ln in f if ln.strip()]
        print("  %-4s %s" % (t, " | ".join(lines)))

    print("\n=== zip close vs prices.csv close ===")
    print("  %-5s %7s %7s %9s %12s %12s %10s"
          % ("tick", "zipN", "csvN", "common", "max_abs_dif", "max_rel_bps",
             "verdict"))
    worst_rel = 0.0
    for t in TICKERS:
        z = read_zip(t)
        if t not in px.columns:
            print("  %-5s  MISSING from prices.csv" % t)
            continue
        common = z.index.intersection(px.index)
        a = z.loc[common, "close"]
        b = px.loc[common, t].astype(float)
        diff = (a - b).abs()
        rel_bps = (diff / b.abs()).max() * 10_000.0
        worst_rel = max(worst_rel, rel_bps)
        # deci-cent rounding can only move a price by <= 0.00005
        verdict = "ROUNDING" if diff.max() <= 5e-5 + 1e-12 else "MISMATCH"
        print("  %-5s %7d %7d %9d %12.3e %12.4f %10s"
              % (t, len(z), px[t].notna().sum(), len(common),
                 diff.max(), rel_bps, verdict))

    print("\n=== date-coverage differences ===")
    for t in TICKERS:
        if t not in px.columns:
            continue
        z = read_zip(t)
        csv_dates = set(px.index[px[t].notna()])
        zip_dates = set(z.index)
        only_csv = sorted(csv_dates - zip_dates)
        only_zip = sorted(zip_dates - csv_dates)
        if only_csv or only_zip:
            print("  %-4s only_in_csv=%d only_in_zip=%d  first_examples: %s / %s"
                  % (t, len(only_csv), len(only_zip),
                     [d.date() for d in only_csv[:3]],
                     [d.date() for d in only_zip[:3]]))
        else:
            print("  %-4s identical date coverage" % t)

    print("\nworst relative close difference across all tickers: %.4f bps"
          % worst_rel)
    print("non-identity factor files: %s" % (non_identity or "none"))

    # Monthly closes are what the signal actually uses -- verify those match,
    # since a single mismatched month-end would change a ranking.
    print("\n=== monthly signal closes: any month where a ranking could differ? ===")
    zip_monthly = {}
    for t in TICKERS:
        z = read_zip(t)["close"]
        zip_monthly[t] = z.groupby(z.index.to_period("M")).last()
    zm = pd.DataFrame(zip_monthly)
    csv_m = px.groupby(px.index.to_period("M")).last()
    cols = [c for c in zm.columns if c in csv_m.columns]
    common_m = zm.index.intersection(csv_m.index)
    d = (zm.loc[common_m, cols] - csv_m.loc[common_m, cols]).abs()
    print("  months compared      : %d" % len(common_m))
    print("  max abs monthly diff : %.3e" % d.max().max())
    print("  months with diff>1e-4: %d" % int((d > 1e-4).any(axis=1).sum()))


if __name__ == "__main__":
    main()
