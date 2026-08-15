"""Generation 2 eligibility re-check probe -- development window only, ASCII output only.

Reads normalized daily CSVs and reports, per Stage 1 universe candidate, the four
``measured_on_development_window_only`` eligibility figures plus the first session.
Hard stop at 2021-07-31: no row later than that is even parsed into the statistics.

This is a diagnostic. It measures eligibility (inception, session count, dollar volume,
minimum close). It measures no return, no drawdown and no performance figure of any kind.
"""

from __future__ import annotations

import csv
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
DEV_END = "2021-07-31"
DEV_START = "1993-01-29"

SYMBOLS = [
    "SPY", "IVV", "VTI", "QQQ", "IWM", "DIA", "MDY", "XLB", "XLE", "XLF", "XLI",
    "XLK", "XLP", "XLU", "XLV", "XLY", "SHY", "IEF", "TLT", "LQD", "HYG", "AGG",
    "BND", "TIP", "EFA", "VEA", "VGK", "EEM", "VWO", "IYR", "VNQ", "DVY", "VIG", "VYM",
]


def main() -> None:
    rows = []
    for symbol in SYMBOLS:
        path = ROOT / "data" / "normalized" / "daily" / f"{symbol}.csv"
        sessions: list[str] = []
        dollar_volume: list[float] = []
        closes: list[float] = []
        with path.open(newline="", encoding="utf-8") as handle:
            for record in csv.DictReader(handle):
                session = record["session"]
                if session < DEV_START or session > DEV_END:
                    continue
                sessions.append(session)
                close = float(record["close"])
                closes.append(close)
                dollar_volume.append(close * float(record["volume"]))
        rows.append(
            {
                "symbol": symbol,
                "first": sessions[0],
                "last": sessions[-1],
                "n": len(sessions),
                "median_dv": statistics.median(dollar_volume),
                "min_close": min(closes),
            }
        )

    rows.sort(key=lambda r: r["first"])
    print(f"{'SYM':<6}{'FIRST':<12}{'LAST':<12}{'SESSIONS':>9}{'MED_DOLLAR_VOL':>18}{'MIN_CLOSE':>11}  ELIG")
    latest = rows[-1]
    for r in rows:
        ok = r["n"] >= 1260 and r["median_dv"] >= 5_000_000 and r["min_close"] >= 5.00
        print(
            f"{r['symbol']:<6}{r['first']:<12}{r['last']:<12}{r['n']:>9}"
            f"{r['median_dv']:>18,.0f}{r['min_close']:>11.2f}  {'PASS' if ok else 'FAIL'}"
        )
    print()
    print(f"latest inception among the 34: {latest['symbol']} at {latest['first']}")
    fails = [r["symbol"] for r in rows if not (r["n"] >= 1260 and r["median_dv"] >= 5_000_000 and r["min_close"] >= 5.00)]
    print(f"symbols failing the Stage 1 development-measured rules: {fails or 'none'}")


if __name__ == "__main__":
    main()
