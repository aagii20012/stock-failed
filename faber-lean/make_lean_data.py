"""Write yfinance daily bars into LEAN's local data format.

LEAN's free sample bundle has no history for these ETFs, and `lean init`
refuses to provision anything without QuantConnect credentials, so the
local data folder is built here instead.

Layout produced (relative to ./data):
    equity/usa/daily/<ticker>.zip      -> <ticker>.csv, prices in deci-cents
    equity/usa/map_files/<ticker>.csv
    equity/usa/factor_files/<ticker>.csv

Prices are already total-return adjusted (auto_adjust=True), so the factor
files are identity. LEAN will therefore emit no split or dividend events --
the total return is baked into the price series instead.
"""

import os
import zipfile

import pandas as pd
import yfinance as yf

TICKERS = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB", "SHY", "SPY"]
START = "2005-06-01"
END = "2026-08-20"
EXCHANGE = "P"          # NYSE Arca, where the sector SPDRs and SHY trade
ROOT = os.path.join("data", "equity", "usa")
SCALE = 10_000          # LEAN stores equity prices in deci-cents


def main():
    for sub in ("daily", "map_files", "factor_files"):
        os.makedirs(os.path.join(ROOT, sub), exist_ok=True)

    raw = yf.download(TICKERS, start=START, end=END, auto_adjust=True,
                      progress=False, group_by="ticker")

    for ticker in TICKERS:
        df = raw[ticker].dropna(how="any")
        low = ticker.lower()

        lines = []
        for ts, row in df.iterrows():
            lines.append("{},{},{},{},{},{}".format(
                ts.strftime("%Y%m%d 00:00"),
                int(round(row["Open"] * SCALE)),
                int(round(row["High"] * SCALE)),
                int(round(row["Low"] * SCALE)),
                int(round(row["Close"] * SCALE)),
                int(row["Volume"]),
            ))

        zip_path = os.path.join(ROOT, "daily", f"{low}.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(f"{low}.csv", "\n".join(lines) + "\n")

        first = df.index[0].strftime("%Y%m%d")
        with open(os.path.join(ROOT, "map_files", f"{low}.csv"), "w") as f:
            f.write(f"{first},{low},{EXCHANGE}\n20501231,{low},{EXCHANGE}\n")

        with open(os.path.join(ROOT, "factor_files", f"{low}.csv"), "w") as f:
            f.write(f"{first},1,1,0\n20501231,1,1,0\n")

        print(f"{ticker:4s} {len(lines):5d} bars  "
              f"{df.index[0].date()} -> {df.index[-1].date()}")


if __name__ == "__main__":
    main()
