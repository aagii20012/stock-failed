"""Why is LEAN's first fill 2007-02-01 when the harness invests from 2007-01-03?

LEAN logs rebalances=236, the same count as the harness, and its skip
breakdown matches sector for sector -- so the two are deciding the same 236
months. But LEAN's first *fill* is 2007-02-01 and its equity sits at exactly
100,000 through January. The likely cause: at daily resolution the scheduled
event fires at 10:00 on the first trading day, before that day's daily bar has
been emitted, so on the very first day of the algorithm no bar has ever
arrived and set_holdings has no price to size against. The January rebalance
increments the counter and buys nothing.

If so it is a real one-month difference in coverage, not a signal difference,
and it should be worth roughly one month of the strategy's return. Quantify
it, and confirm the 236 decided months line up on both sides.
"""

import glob
import io
import json
import os
import sys
import zipfile

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
FABER = os.path.abspath(os.path.join(HERE, "..", "faber-lean"))
DAILY = os.path.join(FABER, "data", "equity", "usa", "daily")
sys.path.insert(0, FABER)
import local_backtest as lb  # noqa: E402

RUN = sys.argv[1]


def main():
    # ---- LEAN's traded months ----------------------------------------
    path = glob.glob(os.path.join(RUN, "*-order-events.json"))[0]
    recs = json.load(open(path, encoding="utf-8"))
    fl = [r for r in recs if str(r.get("status", "")).lower() == "filled"]
    df = pd.DataFrame([{
        "date": pd.to_datetime(float(r["time"]), unit="s").normalize(),
        "ticker": r.get("symbolValue"),
        "qty": float(r["fillQuantity"]),
    } for r in fl])
    df["month"] = df["date"].dt.to_period("M")
    lean_months = sorted(df["month"].unique())

    # ---- harness's hold months ---------------------------------------
    px = lb.load_prices()
    px = px[px.index >= pd.Timestamp(lb.WARMUP_START)]
    weights, diag, monthly = lb.build_signals(px)
    h_months = sorted(weights)

    print("=== decided / traded months ===")
    print("  harness hold months : %d  (%s -> %s)"
          % (len(h_months), h_months[0], h_months[-1]))
    print("  LEAN months with a fill: %d  (%s -> %s)"
          % (len(lean_months), lean_months[0], lean_months[-1]))
    missing = [m for m in h_months if m not in set(lean_months)]
    extra = [m for m in lean_months if m not in set(h_months)]
    print("  harness months with NO LEAN fill : %d" % len(missing))
    print("     %s" % [str(m) for m in missing[:15]])
    print("  LEAN months not in harness       : %d  %s"
          % (len(extra), [str(m) for m in extra[:8]]))
    print("\n  (a month with no fill is usually 'already holding the target' --")
    print("   only the FIRST one can mean 'never got invested')")

    # ---- what did January 2007 cost? ---------------------------------
    h10 = lb.run(px, weights, 10.0)
    jan = h10[(h10.index >= pd.Timestamp("2007-01-01"))
              & (h10.index <= pd.Timestamp("2007-01-31"))]
    base_pos = px.index.get_loc(jan.index[0]) - 1
    print("\n=== the January 2007 month LEAN sat out ===")
    print("  harness weights for 2007-01 : %s"
          % {k: round(v, 4) for k, v in weights[pd.Period('2007-01')].items()})
    print("  harness level %.6f -> %.6f  = %+.3f%% over the month"
          % (h10.iloc[0], jan.iloc[-1],
             100 * (jan.iloc[-1] / h10.iloc[0] - 1)))
    m = px.groupby(px.index.to_period("M")).last()
    dec06, jan07 = m.loc[pd.Period("2006-12")], m.loc[pd.Period("2007-01")]
    port = sum(w * (jan07[t] / dec06[t] - 1.0)
               for t, w in weights[pd.Period("2007-01")].items())
    print("  month-on-month basket return: %+.3f%%" % (100 * port))
    yrs = 19.62
    print("  one-off %+.3f%% spread over %.2f years = %+.4f pp of CAGR"
          % (100 * port, yrs,
             100 * ((1 + port) ** (1 / yrs) - 1)))

    # ---- did LEAN really hold nothing in January? --------------------
    paths = [p for p in glob.glob(os.path.join(RUN, "*.json"))
             if "order-events" not in p and "summary" not in p]
    doc = json.load(open(max(paths, key=os.path.getsize), encoding="utf-8"))
    vals = doc["charts"]["Strategy Equity"]["series"]["Equity"]["values"]
    pts = []
    for v in vals:
        t = int(v["x"]) if isinstance(v, dict) else int(v[0])
        c = float(v.get("close", v.get("y"))) if isinstance(v, dict) else float(v[-1])
        pts.append((pd.to_datetime(t, unit="s"), c))
    ser = pd.Series([c for _, c in pts], index=[t for t, _ in pts]).sort_index()
    jan_l = ser[(ser.index >= pd.Timestamp("2007-01-01"))
                & (ser.index < pd.Timestamp("2007-02-03"))]
    print("\n=== LEAN equity through the first month (raw stamps) ===")
    print("  distinct values in Jan 2007: %s"
          % sorted(set(round(v, 2) for v in jan_l.values))[:6])
    print("  first change away from 100000 at: %s"
          % (jan_l[jan_l != 100000.0].index[:1].tolist()
             if (jan_l != 100000.0).any() else "never in window"))

    # ---- like-for-like: harness restricted to LEAN's invested window --
    print("\n=== apples-to-apples on LEAN's actual invested window ===")
    rf = px[lb.DEFENSIVE].pct_change()
    h0 = lb.run(px, weights, 0.0)
    start = pd.Timestamp("2007-02-01")
    for label, s in [("harness 10bps 2007-01-03 start", h10),
                     ("harness 10bps 2007-02-01 start", h10[h10.index >= start]),
                     ("harness 0bps  2007-02-01 start", h0[h0.index >= start])]:
        st = lb.stats(s, rf, label)
        print("  %-34s cagr=%.3f%%  sharpe_shy=%.3f  maxdd=%.2f%%"
              % (label, 100 * st["cagr"], st["sharpe_rf_shy"],
                 100 * st["maxdd_daily"]))


if __name__ == "__main__":
    main()
