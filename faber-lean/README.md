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

Both implementations were run over 2007-2026 and reconciled down to the cent.

**Do not read LEAN's Strategy Equity chart directly.** At daily resolution it is not a
clean close series: it carries two stamps per day (midnight ET, which is the *previous*
close, and 16:00 ET) and only ~2,899 of ~4,938 trading days have the 16:00 point.
Everything below is instead computed on a curve reconstructed from LEAN's own 726 fills
plus the daily bars, which reproduces LEAN's reported final equity exactly --
$570,569.38 against $570,569.38, delta $0.00 -- so it *is* LEAN's curve.

Identical formulas, same 4,918 common trading days, same invested window:

| | LEAN actual | harness 0bps | harness 10bps |
|---|---|---|---|
| CAGR | **9.32%** | 9.64% | 8.91% |
| annualised vol | 14.86% | 14.80% | 14.80% |
| Sharpe (rf=0) | 0.675 | 0.697 | 0.652 |
| Sharpe (vs SHY) | 0.537 | 0.557 | 0.513 |
| max drawdown (daily) | **-24.75%** | -22.58% | -22.94% |
| total return | 470.78% | 503.95% | 430.65% |

Signal decisions are **identical**: 236 rebalances, 708 slots, 83 skips (11.7%), 11
fully-defensive months, and the same skip count in every one of the nine sectors.
Daily returns agree at corr 0.9919, mean |difference| 0.0154 pp, with only 31 of 4,917
days differing by more than 0.5 pp. Two independent implementations agreeing that
closely means the strategy logic is verified, not merely plausible.

What the cross-check actually established:

- **The 10 bps cost model is ~6.7x too harsh, so "8.95% net" was too pessimistic.**
  LEAN's real commissions over 19.6 years total $4,248 on $28.3M of traded notional --
  an effective **1.50 bps of notional**. The harness's 10 bps charge costs $73,306 of
  terminal wealth. Decomposed: harness 10bps 8.914% -> remove its cost model (+0.723 pp)
  -> 9.637% frictionless, against LEAN's actual 9.321%. Treat ~9.3% as the realistic
  figure and 8.9% as a deliberately conservative floor.
- **LEAN's drawdown is ~2.2 pp deeper, and that is real.** -24.75% against the harness's
  -22.58%. Cause, measured from the order events rather than inferred: all 726 fills land
  on the **close of their own trading day** (726/726 exact, median |fill/close(D)-1| =
  0.0e+00), because LEAN converts market orders to MarketOnClose on daily data. The
  schedule fires on the first trading day of the month, so LEAN trades one trading day
  after the harness's signal-month close and is late into every de-risking move. Note
  `time_rules.after_market_open` sets when the scheduled *method* runs, not when the
  order fills.

  Confirmed by a controlled rerun that changes **only** the fill bar and holds the
  whole-share quantization, 0.25% cash buffer and IB fee model fixed: filling at
  close(D-1) (harness timing) gives -22.63%, filling at close(D) (LEAN timing) gives
  -24.55%. Timing alone is worth -1.92 pp of drawdown and -0.158 pp of CAGR, which
  accounts for the observed -1.81 pp gap. It is the same episode in every variant
  (peak 2010-04-23 -> trough 2010-08-26), so the comparison is apples to apples.
- **LEAN sat out January 2007.** Its first fill is 2007-02-01 while the harness invests
  from 2007-01-03, worth a one-off +1.146% (+0.058 pp of CAGR). The table above already
  starts both on LEAN's invested window. The other 8 months with no LEAN fill are months
  where it already held the target, and there are zero months LEAN traded that the
  harness did not.
- **Whole-share rounding never changed which assets were held** -- realized holdings
  match intent in 227/227 rebalances, with L1 weight error median 0.45% and worst 2.53%
  (2020-03), the expected floor from whole shares plus the 0.25% cash buffer.
- **LEAN's own reported Sharpe of 0.497 is unusable.** It logged a failed request for
  `/alternative/interest-rate/usa/interest-rate.csv`, so it had no risk-free curve. The
  0.675 / 0.537 above are recomputed on the reconstructed curve and are comparable. The
  other failed request, `/equity/usa/hour/spy.zip`, is harmless -- only daily bars were
  generated and LEAN fell back cleanly.

### Retracted from the first pass

Three conclusions reached before the reconstruction are **withdrawn**, and none of their
numbers should be quoted anywhere. Two of them came from comparing against the raw
Strategy Equity stamps described above; the third came from reading the schedule instead
of the order events:

| retracted claim | why it was wrong | what stands instead |
|---|---|---|
| The volatility gap is a daily-vs-monthly annualisation convention. | An artifact of the ragged sampling, not a convention difference. | On identical formulas the two agree: 14.86% vs 14.80%. |
| The one-day handover explains **43.9%** of the month-to-month return difference. | Measured against mis-aligned stamps; re-aligning by one day collapses it to -2.4%. | No attribution figure is quoted for the *return* difference. The *drawdown* gap is attributed, from the order events, above. |
| LEAN fills at the **next month's open + 30 min**. | Inferred from reading `time_rules.after_market_open` instead of from the order events. | All 726 fills are at close(D) of their own trading day, because market orders become MarketOnClose on daily data. |

The 43.9% and the open+30min fill are the two most likely to resurface from an old note
or an earlier draft. Neither is a measurement of anything.

LEAN also recorded 726 orders and 1.84% portfolio turnover, consistent with 3 slots over
236 rebalances.

## Known caveats

See the flags list in the session notes. The short version:

1. Local data is yfinance `auto_adjust=True` back-adjusted closes fed through
   identity factor files. Not tradeable prices; LEAN emits no split/dividend
   events; the SMA is computed on adjusted rather than raw prices.
2. **Quote LEAN's -24.75% max drawdown, not the harness's -22.58%.** The harness
   trades at the signal month's close; LEAN trades one trading day later, at the
   close of the first trading day of the next month (market orders on daily data
   become MarketOnClose regardless of the scheduled time), so it is late into
   every de-risking move. A controlled rerun changing **only** the fill bar moves
   max drawdown by -1.92 pp (-22.63% -> -24.55%) and CAGR by -0.158 pp: that
   covers the -1.81 pp gap against the harness at 10 bps (-24.75% vs -22.94%) and
   most of the -2.17 pp gap against it at 0 bps (-24.75% vs -22.58%). The harness
   figure is optimistic by construction rather than more accurate, so LEAN is the
   honest side of this one and -24.75% is this strategy's max drawdown.
3. The 9-sector universe stopped spanning the S&P 500 when XLRE was carved out
   of XLF (2015) and XLC out of XLK/XLY (2018). Post-2018 there is no
   communication-services exposure at all.
4. Choosing these 9 tickers because they exist today is itself a look-ahead.
5. Sharpe with rf=0 flatters a strategy that parks in T-bills. The
   SHY-relative Sharpe is the honest one. SHY is also not risk-free -- it is a
   1-3yr Treasury fund with duration risk.
6. Max drawdown on monthly marks understates the daily figure.
7. 10 bps of turnover cost is worth ~72 bps/yr of CAGR here -- confirmed by the
   cross-check, which also shows LEAN's actual cost is only ~1.5 bps of notional.
