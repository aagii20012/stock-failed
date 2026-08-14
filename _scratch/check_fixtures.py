"""Out-of-tree: verify by computation every synthetic number the adversarial tests assert.

Nothing here reads a market observation. Every series is built in memory from literals.
"""

import datetime as dt
import sys
from decimal import Decimal

sys.path.insert(0, r"d:\Product\stock-trade-alpaca\stockedge100\src")

from stockedge100.backtest.config import load_stage2_config
from stockedge100.backtest.costs import BASE, CostModel
from stockedge100.backtest.dataset import series_from_rows
from stockedge100.strategies import attempt2_risk
from stockedge100.strategies.attempt2_config import load_attempt2_config
from stockedge100.strategies.attempt2_indicators import vol20

CONFIG = load_attempt2_config()
COSTS = CostModel(load_stage2_config().cost_model, BASE)
sealed = next(
    e["primary_parameters"]
    for e in CONFIG.experiments
    if e["experiment_id"].startswith("SE100-S3A2-C1")
)
RA1 = attempt2_risk.Ra1Parameters.from_parameters(sealed)

DAY_ZERO = dt.date(2000, 1, 3)


def prices(symbol, closes, adj=None):
    rows = []
    for offset, close in enumerate(closes):
        value = adj[offset] if adj is not None else close
        rows.append(
            {
                "session": (DAY_ZERO + dt.timedelta(days=offset)).isoformat(),
                "open": str(close),
                "high": str(close),
                "low": str(close),
                "close": str(close),
                "adj_close": str(value),
                "split_ratio": "1",
            }
        )
    return series_from_rows(symbol, rows)


def alternating(count, low="100", high="101"):
    return [low if index % 2 == 0 else high for index in range(count)]


def ramp(count, first=80):
    return [str(first + index) for index in range(count)]


def report(label, adj, equity="100"):
    series = prices("SPY", ramp(len(adj)), adj)
    bars = [series.bars[session] for session in series.sessions]
    sigma = vol20(bars)
    print(f"-- {label}")
    print(f"   sigma_annual = {sigma}")
    if sigma is None or sigma == 0:
        print("   (no division performed)")
        return
    f_vol = RA1.vol_target / sigma
    f_cap = RA1.f_cap(Decimal(0))
    fraction = min(f_cap, f_vol)
    print(f"   f_vol = {f_vol}")
    print(f"   f     = {fraction}  (f_base={RA1.f_base}, floor={RA1.vol_floor_fraction})")
    print(f"   below floor? {fraction < RA1.vol_floor_fraction}")
    print(f"   budget at equity {equity} = {fraction * Decimal(equity)}")
    print(f"   below min_order_notional {COSTS.min_order_notional}? "
          f"{fraction * Decimal(equity) < COSTS.min_order_notional}")


print(f"sealed RA1 = {RA1}")
print(f"ladder_bands = {RA1.ladder_bands}")
print(f"min_order_notional = {COSTS.min_order_notional}")
print(f"max_open_risky_positions = {COSTS.max_open_risky_positions}")
print(f"vol_target / vol_floor_fraction = {RA1.vol_target / RA1.vol_floor_fraction}")
print()

report("alternating 100/101 (clean)", alternating(21))
report("alternating 100/101, equity 1", alternating(21), equity="1")
report("alternating 100/101, equity 2", alternating(21), equity="2")
report("alternating 100/200 (volatility floor)", alternating(21, "100", "200"))
report("constant adj (zero volatility)", ["100"] * 21)
report("20 bars only", alternating(20))
print()

# parity invariance of the 21-bar window across successive decision sessions
for total in (21, 22, 23, 24, 28):
    series = prices("SPY", ramp(total), alternating(total))
    bars = [series.bars[session] for session in series.sessions]
    print(f"   {total} bars: last-21 sigma = {vol20(bars[-21:])}")
print()

# ladder budgets
for equity in ("100", "91", "89"):
    hwm = Decimal(100)
    dd = (hwm - Decimal(equity)) / hwm
    cap = RA1.f_cap(dd)
    print(f"   equity {equity}: dd={dd} band={RA1.band_of(dd)} f_cap={cap} "
          f"budget={cap * Decimal(equity)}")
print()

# hwm scenarios
for label, series_equity in (
    ("flat 100/120/90", ["100", "120", "90"]),
    ("held 100/130/110", ["100", "130", "110"]),
):
    hwm = None
    bands = {}
    for value in series_equity:
        equity = Decimal(value)
        if hwm is None or equity > hwm:
            hwm = equity
        dd = (hwm - equity) / hwm
        band = RA1.band_of(dd)
        bands[band] = bands.get(band, 0) + 1
        print(f"   {label}: equity={value} hwm={hwm} dd={dd} band={band}")
    print(f"   {label}: tally={bands}")
print()

# RA1-3 boundary
p_ref = Decimal(100)
trigger = p_ref * (Decimal(1) - RA1.loss_control)
print(f"   P_ref=100 -> trigger at close <= {trigger}")
print(f"   close 92    triggers? {Decimal('92') <= trigger}")
print(f"   close 92.01 triggers? {Decimal('92.01') <= trigger}")
print(f"   fill-price reading (open 50): {Decimal('92') <= Decimal('50') * (1 - RA1.loss_control)}")
print(f"   P_ref=120 -> trigger at close <= {Decimal(120) * (1 - RA1.loss_control)}")
print(f"   close 100 under P_ref=120 triggers? "
      f"{Decimal('100') <= Decimal(120) * (1 - RA1.loss_control)}")
print(f"   close 100 under P_ref=100 triggers? "
      f"{Decimal('100') <= Decimal(100) * (1 - RA1.loss_control)}")
print()

# C3 signal: sma_long=3 over a ramp and over a descending ramp
def sma3(values, index):
    window = [Decimal(v) for v in values[index - 2: index + 1]]
    return sum(window) / Decimal(3)


up = ramp(23, 80)
print(f"   ramp: close[20]={up[20]} sma3={sma3(up, 20)} fires={Decimal(up[20]) > sma3(up, 20)}")
down = [str(100 - index) for index in range(23)]
print(f"   descending: close[20]={down[20]} sma3={sma3(down, 20)} "
      f"fires={Decimal(down[20]) > sma3(down, 20)}")

# unfilled-entry path: ramp(21,80) + [120, 100]
mixed = ramp(21, 80) + ["120", "100"]
for index in (20, 21, 22):
    print(f"   mixed[{index}]={mixed[index]} sma3={sma3(mixed, index)} "
          f"fires={Decimal(mixed[index]) > sma3(mixed, index)}")

# signal-exit path: ramp(21,80) + [95, 105]
sig = ramp(21, 80) + ["95", "105"]
for index in (20, 21, 22):
    print(f"   sig[{index}]={sig[index]} sma3={sma3(sig, index)} "
          f"fires={Decimal(sig[index]) > sma3(sig, index)}")

# flat-first path: descending 100..80 then a jump to 200
flat = [str(100 - index) for index in range(21)] + ["200"]
for index in (20, 21):
    print(f"   flat[{index}]={flat[index]} sma3={sma3(flat, index)} "
          f"fires={Decimal(flat[index]) > sma3(flat, index)}")
