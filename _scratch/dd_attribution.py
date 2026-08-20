"""Is the 1.8pp worse max drawdown in LEAN timing, or something else?

Return metrics already reconcile: on the identical window LEAN's 9.32% CAGR
sits between the harness's 0bps (9.64%) and 10bps (8.91%) variants, which is
where 1.5bps of real commission belongs. Max drawdown is the one metric that
falls OUTSIDE that bracket -- LEAN -24.75% against the harness's -22.58% to
-22.94%. So it cannot be the cost model.

The remaining candidate is execution timing: LEAN fills at the close of the
first trading day of the hold month (all 726 fills confirmed), the harness at
the close of the last day of the prior month. Hold frictions fixed and vary
only the fill convention -- if timing is the cause, the drawdown should move
by about the observed gap and the trough should sit in the same episode.
"""

import io
import os
import sys
import zipfile

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
FABER = os.path.abspath(os.path.join(HERE, "..", "faber-lean"))
sys.path.insert(0, FABER)
import local_backtest as lb  # noqa: E402
sys.path.insert(0, HERE)
import timing_bracket as tb  # noqa: E402


def dd_window(curve):
    peak = curve.cummax()
    dd = curve / peak - 1.0
    trough = dd.idxmin()
    peak_date = curve[:trough].idxmax()
    rec = curve[trough:][curve[trough:] >= curve[peak_date]]
    return {
        "maxdd": float(dd.min()),
        "peak": peak_date.date(),
        "trough": trough.date(),
        "recovered": rec.index[0].date() if len(rec) else None,
    }


def main():
    opens, closes = tb.load_ohlc()
    opens = opens[opens.index >= pd.Timestamp("2005-06-01")]
    closes = closes[closes.index >= pd.Timestamp("2005-06-01")]
    w = tb.signals(closes)

    px = lb.load_prices()
    px = px[px.index >= pd.Timestamp(lb.WARMUP_START)]
    rf = px[lb.DEFENSIVE].pct_change()
    weights, _, _ = lb.build_signals(px)

    print("=== drawdown episode, harness vs LEAN-reconstructed ===")
    h10 = lb.run(px, weights, 10.0)
    h0 = lb.run(px, weights, 0.0)
    for label, c in [("harness 10bps", h10), ("harness 0bps", h0)]:
        d = dd_window(c)
        print("  %-32s %7.2f%%  peak %s -> trough %s (recovered %s)"
              % (label, 100 * d["maxdd"], d["peak"], d["trough"],
                 d["recovered"]))

    print("\n=== fill convention held everything-else-equal ===")
    print("  (same whole-share quantization, 0.25%% cash buffer, IB fees;")
    print("   ONLY the fill bar changes)")
    rows = []
    for label, when in [("B fill at close(D-1)  [harness timing]", "prev_close"),
                        ("D fill at close(D)    [LEAN timing]", "close")]:
        curve, meta = tb.simulate(opens, closes, w, when=when,
                                  whole_shares=True, buffer_pct=0.0025,
                                  fees=True)
        d = dd_window(curve)
        st = lb.stats(curve, rf, label)
        rows.append((label, st, d, meta))
        print("  %-40s cagr=%.3f%%  maxdd=%7.2f%%  peak %s -> trough %s"
              % (label, 100 * st["cagr"], 100 * d["maxdd"],
                 d["peak"], d["trough"]))

    b, dd_b = rows[0][1], rows[0][2]
    d_, dd_d = rows[1][1], rows[1][2]
    print("\n  timing alone moves max drawdown by %+.2f pp (%.2f%% -> %.2f%%)"
          % (100 * (dd_d["maxdd"] - dd_b["maxdd"]),
             100 * dd_b["maxdd"], 100 * dd_d["maxdd"]))
    print("  timing alone moves CAGR by          %+.3f pp"
          % (100 * (d_["cagr"] - b["cagr"])))
    print("\n  observed LEAN - harness10bps max drawdown gap: %+.2f pp"
          % (100 * (-0.2475 - -0.2294)))
    print("  explained by the timing shift above          : %+.2f pp"
          % (100 * (dd_d["maxdd"] - dd_b["maxdd"])))

    print("\n=== why one day matters so much here ===")
    # The drawdown trough sits in an episode where the rebalance day itself
    # moved a lot. Show the first-trading-day moves in the worst episode.
    ep = closes.loc["2020-02-01":"2020-04-30"]
    per = ep.index.to_period("M")
    print("  first-trading-day move of each sector, Feb-Apr 2020:")
    for m in sorted(set(per)):
        blk = ep.index[per == m]
        pos = closes.index.get_loc(blk[0])
        d0, dm1 = closes.index[pos], closes.index[pos - 1]
        mv = (closes.loc[d0] / closes.loc[dm1] - 1.0)
        held = weights.get(pd.Period(m), {})
        basket = sum(wt * mv[t] for t, wt in held.items() if t in mv.index)
        print("     %s  day1=%s  new-basket day1 move %+6.2f%%  held=%s"
              % (m, d0.date(), 100 * basket,
                 {k: round(v, 2) for k, v in held.items()}))


if __name__ == "__main__":
    main()
