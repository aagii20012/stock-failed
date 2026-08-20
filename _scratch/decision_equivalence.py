"""Do the two price sources ever produce a different trading decision?

verify_data_identity.py showed the LEAN zips and prices.csv differ by at most
~0.12 bps (two separate yfinance pulls + deci-cent quantization). That is
economically nil, but a ranking is a discrete function of prices, so noise CAN
in principle flip a top-3 pick or an SMA gate. This runs the exact signal
logic on both sources and diffs the decisions month by month.

If every month agrees, the data difference is provably irrelevant and any
LEAN-vs-harness divergence must be execution mechanics.
"""

import io
import os
import zipfile

import pandas as pd

FABER = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", "faber-lean"))
DAILY = os.path.join(FABER, "data", "equity", "usa", "daily")
SCALE = 10_000.0

SECTORS = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB"]
DEFENSIVE = "SHY"
TOP_N, MOM_LOOKBACK, SMA_LENGTH = 3, 12, 10
HOLD_START = "2007-01"


def zip_closes():
    out = {}
    for t in SECTORS + [DEFENSIVE, "SPY"]:
        with zipfile.ZipFile(os.path.join(DAILY, t.lower() + ".zip")) as z:
            body = z.read(z.namelist()[0]).decode()
        df = pd.read_csv(io.StringIO(body), header=None,
                         names=["ts", "o", "h", "l", "c", "v"])
        idx = pd.to_datetime(df["ts"].str.slice(0, 8), format="%Y%m%d")
        out[t] = pd.Series((df["c"] / SCALE).values, index=idx)
    return pd.DataFrame(out).dropna(how="any")


def decisions(px):
    """Replicate build_signals: returns {hold_month: (ranked, skipped)}."""
    monthly = px.groupby(px.index.to_period("M")).last()
    months = monthly.index
    out = {}
    for i in range(MOM_LOOKBACK, len(months) - 1):
        hold = months[i + 1]
        if str(hold) < HOLD_START:
            continue
        last = monthly.iloc[i]
        momentum = last / monthly.iloc[i - MOM_LOOKBACK] - 1.0
        sma = monthly.iloc[i - SMA_LENGTH + 1: i + 1].mean()
        ranked = sorted(SECTORS, key=lambda t: momentum[t], reverse=True)[:TOP_N]
        skipped = [t for t in ranked if not last[t] > sma[t]]
        out[str(hold)] = (tuple(ranked), tuple(sorted(skipped)))
    return out, monthly


def main():
    csv_px = pd.read_csv(os.path.join(FABER, "prices.csv"),
                         index_col=0, parse_dates=True)
    csv_px = csv_px[csv_px.index >= pd.Timestamp("2005-06-01")]
    zp = zip_closes()
    zp = zp[zp.index >= pd.Timestamp("2005-06-01")]

    d_csv, m_csv = decisions(csv_px)
    d_zip, m_zip = decisions(zp)

    print("months decided: csv=%d zip=%d" % (len(d_csv), len(d_zip)))
    keys = sorted(set(d_csv) & set(d_zip))
    only_csv = sorted(set(d_csv) - set(d_zip))
    only_zip = sorted(set(d_zip) - set(d_csv))
    print("common=%d only_csv=%s only_zip=%s" % (len(keys), only_csv, only_zip))

    diff_rank = [k for k in keys if d_csv[k][0] != d_zip[k][0]]
    diff_skip = [k for k in keys if d_csv[k][1] != d_zip[k][1]]

    print("\n=== decision differences ===")
    print("  months where top-3 set/order differs : %d" % len(diff_rank))
    for k in diff_rank[:15]:
        print("     %s  csv=%s  zip=%s" % (k, d_csv[k][0], d_zip[k][0]))
    print("  months where SMA gate differs        : %d" % len(diff_skip))
    for k in diff_skip[:15]:
        print("     %s  csv_skipped=%s  zip_skipped=%s"
              % (k, d_csv[k][1], d_zip[k][1]))

    # Same held-weight vector? (order within top-3 does not affect weights)
    def wvec(v):
        ranked, skipped = v
        w = {}
        for t in ranked:
            k = DEFENSIVE if t in skipped else t
            w[k] = round(w.get(k, 0.0) + 1.0 / TOP_N, 10)
        return tuple(sorted(w.items()))

    diff_w = [k for k in keys if wvec(d_csv[k]) != wvec(d_zip[k])]
    print("  months where the HELD PORTFOLIO differs: %d" % len(diff_w))
    for k in diff_w[:15]:
        print("     %s  csv=%s  zip=%s" % (k, wvec(d_csv[k]), wvec(d_zip[k])))

    # How close are the decisions to flipping? Margin analysis tells us whether
    # a 0.12 bps data difference is comfortably inside tolerance or borderline.
    print("\n=== decision margins on the LEAN (zip) data ===")
    months = m_zip.index
    rank_margins, gate_margins = [], []
    for i in range(MOM_LOOKBACK, len(months) - 1):
        hold = months[i + 1]
        if str(hold) < HOLD_START:
            continue
        last = m_zip.iloc[i]
        mom = (last / m_zip.iloc[i - MOM_LOOKBACK] - 1.0)[SECTORS].sort_values(
            ascending=False)
        # gap between the 3rd and 4th ranked momentum, in bps of momentum
        rank_margins.append((str(hold), float(mom.iloc[2] - mom.iloc[3])))
        sma = m_zip.iloc[i - SMA_LENGTH + 1: i + 1].mean()
        for t in mom.index[:TOP_N]:
            gate_margins.append((str(hold), t,
                                 float(last[t] / sma[t] - 1.0)))

    rm = pd.Series(dict((k, v) for k, v in rank_margins))
    print("  rank margin (3rd vs 4th momentum), %d months:" % len(rm))
    print("     min=%.6f  p1=%.6f  median=%.6f" %
          (rm.min(), rm.quantile(0.01), rm.median()))
    print("     tightest 5: %s" % [(k, round(v, 6))
                                   for k, v in rm.nsmallest(5).items()])
    gm = pd.DataFrame(gate_margins, columns=["month", "ticker", "margin"])
    gm["abs"] = gm["margin"].abs()
    print("  SMA gate margin |close/sma - 1|, %d slot-decisions:" % len(gm))
    print("     min=%.6f  p1=%.6f  median=%.6f" %
          (gm["abs"].min(), gm["abs"].quantile(0.01), gm["abs"].median()))
    print("     tightest 5:")
    for r in gm.nsmallest(5, "abs").itertuples():
        print("       %s %-4s margin=%+.6f (%.2f bps)"
              % (r.month, r.ticker, r.margin, 10_000 * r.margin))
    print("\n  data noise to beat: 0.12 bps = 0.000012 relative")


if __name__ == "__main__":
    main()
