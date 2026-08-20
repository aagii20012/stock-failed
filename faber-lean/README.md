# Faber-style ETF Sector Rotation (LEAN)

Exploratory side project. Not part of StockEdge100/SE100 and not governed by its rules.

## Strategy

- Universe: XLK XLF XLE XLV XLI XLY XLP XLU XLB (9 SPDR sectors)
- Monthly rebalance
- Rank by 12-month momentum
- Hold top 3 equal-weight, but only if the sector's last monthly close is above
  its own 10-month SMA
- Any top-3 slot failing the trend gate is filled with SHY instead

Both implementations compute signals on **completed monthly closes** (not
252/210-day daily proxies) and drop the in-progress month, so there is no
look-ahead in the signal.

## Three ways to run it

### 1. Standalone pandas harness (fastest, no Docker, no account)

    pip install yfinance pandas numpy
    python local_backtest.py     # prints stats, writes rebalance_log.csv
    python sweep.py              # 48-config parameter sensitivity

Prices are cached in `prices.csv`; delete it to re-download.
This is what produced the numbers reported to date.

### 2. Local LEAN (Docker)

    pip install lean
    python fetch_reference_data.py   # LEAN reference DBs (once)
    python make_lean_data.py         # price data in LEAN's format
    lean backtest FaberSectorRotation

Notes on why this folder looks hand-built:

- `lean init` refuses to provision a workspace without QuantConnect
  credentials, so `lean.json` and `FaberSectorRotation/config.json` were
  written by hand and the reference databases under `data/market-hours` +
  `data/symbol-properties` are fetched by `fetch_reference_data.py`.
- `lean.json` needs `"organization-id"` or the CLI rejects the folder as
  "an old Lean CLI root folder".
- The free LEAN sample data has no 2007-2026 history for these ETFs, so
  `make_lean_data.py` writes yfinance OHLCV into LEAN's local format
  (`data/equity/usa/daily/<ticker>.zip`, prices in deci-cents, plus map and
  identity factor files). Re-run it to refresh. `data/` and `prices.csv` are
  gitignored -- they are derived, and redistributing vendor price data in a
  repo is a licensing question nobody needs.
- First `lean backtest` pulls the multi-GB `quantconnect/lean` image.

### 3. QuantConnect cloud

Paste `faber_sector_rotation.py` into a new Python algorithm. Cloud data is
survivorship- and corporate-action-correct, unlike the local shim above.

## Files

| file | what it is |
|---|---|
| `faber_sector_rotation.py` | the algorithm (readable copy) |
| `FaberSectorRotation/main.py` | same file, LEAN project entry point |
| `local_backtest.py` | standalone harness; mirrors the LEAN logic |
| `sweep.py` | parameter sensitivity over lookback x SMA x top-N |
| `make_lean_data.py` | yfinance -> LEAN local data format |
| `fetch_reference_data.py` | downloads LEAN's market-hours + symbol-properties DBs |
| `rebalance_log.csv` | generated: per-month picks, weights, skips |

## LEAN vs harness cross-check (2026-08-20)

Both implementations were run over 2007-01-03..2026-08-19 and reconciled.

| | harness | LEAN | |
|---|---|---|---|
| rebalances / slots / skips / full-SHY months | 236 / 708 / 83 / 11 | 236 / 708 / 83 / 11 | identical |
| skips by sector | XLP 21, XLV 15, XLU 12, XLY 10, XLE 6, XLK 6, XLI 6, XLB 5, XLF 2 | same | identical |
| net profit | 512.23% gross, 437.92% at 10bps | 470.57% (real fees $4,248.04) | reconciles |
| CAGR | 9.67% gross, 8.95% at 10bps | 9.27% | reconciles |
| annualised vol | 14.78% daily-ann, 12.13% monthly-ann | 12.30% | convention, not a gap |
| max drawdown | -22.58% | **-24.70%** | LEAN 2.1pp deeper |

Every signal decision matches exactly across two independent implementations, which is
the useful result -- the strategy logic is verified, not just plausible.

Two things the cross-check surfaced:

- **The harness understates drawdown by 2.1pp.** LEAN trades ~30 min after the next
  month's open; the harness trades at the signal month's close. LEAN is therefore late
  into every de-risking move, and -24.70% is the more honest figure. Execution lag is a
  real cost, not a rounding difference.
- **LEAN's Sharpe of 0.497 is not comparable to the harness numbers.** LEAN logged a
  failed data request for `/alternative/interest-rate/usa/interest-rate.csv`, so it had
  no risk-free curve to work with. Use the harness's SHY-relative Sharpe instead.
  The other failed request, `/equity/usa/hour/spy.zip`, is harmless -- only daily bars
  were generated and LEAN fell back cleanly.

LEAN also recorded 726 orders and 1.84% portfolio turnover, consistent with 3 slots
over 236 rebalances.

## Known caveats

See the flags list in the session notes. The short version:

1. Local data is yfinance `auto_adjust=True` back-adjusted closes fed through
   identity factor files. Not tradeable prices; LEAN emits no split/dividend
   events; the SMA is computed on adjusted rather than raw prices.
2. The harness trades at the signal month's close; the LEAN algorithm trades
   ~30 min after the open on the first trading day of the next month. The two
   will not agree to the basis point.
3. The 9-sector universe stopped spanning the S&P 500 when XLRE was carved out
   of XLF (2015) and XLC out of XLK/XLY (2018). Post-2018 there is no
   communication-services exposure at all.
4. Choosing these 9 tickers because they exist today is itself a look-ahead.
5. Sharpe with rf=0 flatters a strategy that parks in T-bills. The
   SHY-relative Sharpe is the honest one. SHY is also not risk-free -- it is a
   1-3yr Treasury fund with duration risk.
6. Max drawdown on monthly marks understates the daily figure.
7. 10 bps of turnover cost is worth ~72 bps/yr of CAGR here.
