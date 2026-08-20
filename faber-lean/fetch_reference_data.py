"""Fetch the two LEAN reference databases a local backtest needs.

`lean init` would normally provision these, but it refuses to run without
QuantConnect credentials, so grab them straight from the Lean repo.
Run once after cloning, then run make_lean_data.py for the price data.
"""

import pathlib
import urllib.request

BASE = "https://raw.githubusercontent.com/QuantConnect/Lean/master/Data"
FILES = [
    "market-hours/market-hours-database.json",
    "symbol-properties/symbol-properties-database.csv",
]

for rel in FILES:
    dest = pathlib.Path("data") / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(f"{BASE}/{rel}") as r:
        body = r.read()
    dest.write_bytes(body)
    print(f"{dest}  {len(body):,} bytes")
