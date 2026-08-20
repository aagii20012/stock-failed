"""Inspect the one slot-decision that sits inside the data-noise band.

decision_equivalence.py found 2022-06 XLV gated at +0.12 bps above its 10-month
SMA -- the same order of magnitude as the difference between prices.csv and the
LEAN zips. It did not flip, but it is the one decision in 708 that is not
robust to the data source. Quantify it on both sources and price the impact.
"""

import io
import os
import zipfile

import pandas as pd

FABER = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", "faber-lean"))
DAILY = os.path.join(FABER, "data", "equity", "usa", "daily")
SECTORS = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB"]
SMA_LENGTH, MOM_LOOKBACK, TOP_N = 10, 12, 3
SIGNAL_MONTH = "2022-05"
HOLD_MONTH = "2022-06"


def zip_closes():
    out = {}
    for t in SECTORS + ["SHY", "SPY"]:
        with zipfile.ZipFile(os.path.join(DAILY, t.lower() + ".zip")) as z:
            body = z.read(z.namelist()[0]).decode()
        df = pd.read_csv(io.StringIO(body), header=None,
                         names=["ts", "o", "h", "l", "c", "v"])
        idx = pd.to_datetime(df["ts"].str.slice(0, 8), format="%Y%m%d")
        out[t] = pd.Series((df["c"] / 10_000.0).values, index=idx)
    return pd.DataFrame(out).dropna(how="any")


def report(name, px):
    monthly = px.groupby(px.index.to_period("M")).last()
    i = list(monthly.index).index(pd.Period(SIGNAL_MONTH))
    last = monthly.iloc[i]
    mom = (last / monthly.iloc[i - MOM_LOOKBACK] - 1.0)[SECTORS]
    sma = monthly.iloc[i - SMA_LENGTH + 1: i + 1].mean()
    ranked = mom.sort_values(ascending=False).index[:TOP_N]

    print("\n--- %s ---" % name)
    print("  top-3 by 12m momentum: %s" % list(ranked))
    for t in ranked:
        margin = last[t] / sma[t] - 1.0
        print("    %-4s close=%.6f  sma10=%.6f  close/sma-1=%+.8f (%+.3f bps)"
              " -> %s"
              % (t, last[t], sma[t], margin, 10_000 * margin,
                 "HOLD SECTOR" if margin > 0 else "route to SHY"))
    return {t: float(last[t] / sma[t] - 1.0) for t in ranked}


def main():
    csv_px = pd.read_csv(os.path.join(FABER, "prices.csv"),
                         index_col=0, parse_dates=True)
    zp = zip_closes()

    a = report("harness prices.csv", csv_px)
    b = report("LEAN daily zips", zp)

    print("\n=== margin difference between the two sources ===")
    for t in a:
        if t in b:
            print("  %-4s csv=%+.8f  zip=%+.8f  delta=%+.2e  same_side=%s"
                  % (t, a[t], b[t], b[t] - a[t],
                     (a[t] > 0) == (b[t] > 0)))

    # What would flipping XLV for this one month have cost or saved?
    m = csv_px.groupby(csv_px.index.to_period("M")).last()
    hold = pd.Period(HOLD_MONTH)
    j = list(m.index).index(hold)
    prev, cur = m.iloc[j - 1], m.iloc[j]
    xlv_ret = cur["XLV"] / prev["XLV"] - 1.0
    shy_ret = cur["SHY"] / prev["SHY"] - 1.0
    print("\n=== economic size of the knife edge (%s) ===" % HOLD_MONTH)
    print("  XLV return that month : %+.4f%%" % (100 * xlv_ret))
    print("  SHY return that month : %+.4f%%" % (100 * shy_ret))
    print("  one slot = 1/3 of book -> portfolio impact if it flipped: %+.4f%%"
          % (100 * (shy_ret - xlv_ret) / 3.0))
    print("  as a share of 19.6y CAGR: about %.4f pp"
          % (abs((shy_ret - xlv_ret) / 3.0) / 19.6 * 100))


if __name__ == "__main__":
    main()
