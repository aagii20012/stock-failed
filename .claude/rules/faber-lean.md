---
paths: faber-lean/**
---

# faber-lean: ungoverned by design

This directory is an exploratory side project. SE100 governance does **not** apply here:
no pre-registration, no verdict tokens, no frozen artifacts, no decision packages, no
multiplicity accounting. The user's instruction was "fast and loose experimentation is
fine here" and "nothing production-grade, just something I can run and learn from."

The root `CLAUDE.md` describes the SE100 regime under `stockedge100/`. Do not import it
into this tree. Equally, do not let this tree's looseness leak the other way — anything
under `stockedge100/` stays frozen.

Only two hard constraints survive:

- **Never write into `stockedge100/`** from work started here. After any git operation,
  recompute `repo_state_id` and assert it is unchanged.
- **Never claim a backtest number you did not compute.** Loose about process, strict about
  evidence — the whole point of this project is learning what the data says.

## Conventions that earned their place

- Compute momentum and SMA signals on **completed monthly closes**, not 252/210-day daily
  approximations, and drop the in-progress month. `px.groupby(px.index.to_period("M")).last()`
  rather than `resample` — the `'M'` vs `'ME'` alias broke across pandas versions.
- Monthly rebalancing means **buy and hold within the month**. Applying fixed weights to
  each day's returns silently re-targets daily and harvests a rebalance premium the
  strategy never earns. Compound per-asset growth from the prior month's close instead.
- Report **Sharpe against the actual cash instrument** (SHY), not rf=0. A strategy that
  parks in T-bills is flattered by rf=0 — 0.700 vs 0.560 on the same equity curve.
- Report **max drawdown on daily marks**. Monthly marks understated it by 2.3pp here.
- **Do not charge 10 bps per unit of turnover.** That was a placeholder and it is
  ~6.7x too harsh for nine large SPDR ETFs traded monthly. LEAN's IB fee model charged
  $4,248 on $28,304,842 of traded notional over 19.6 years -- **1.50 bps of notional** --
  against $73,306 of terminal wealth removed by the 10 bps model. Quote ~2 bps as the
  realistic figure and say "conservative floor" out loud if quoting 10 bps. Note LEAN
  runs *no* slippage model, so it is the optimistic bound, not the truth.
- **Bracket a comparison instead of point-matching it.** Run the harness at 0 bps and at
  the cost assumption, and ask whether the other implementation's metric lands inside the
  interval. CAGR 9.32% between 9.64% and 8.91% is instantly interpretable where "off by
  0.37 pp" is not. The contrapositive is what earns its place: a metric landing *outside*
  the bracket cannot be a cost-model artifact, so it points at a different mechanism --
  that is how max drawdown was traced to fill timing rather than fees.
- **Never report a single-config backtest.** Sweep the free parameters first; a result that
  exists only at one setting is a fit to the window. See the top-N gradient test.
- Generated data (`data/`, `prices.csv`) is gitignored and reproducible from
  `fetch_reference_data.py` + `make_lean_data.py`. Do not commit vendor price data.

## Local LEAN gotchas

`lean init` refuses to run without QuantConnect credentials, so the workspace is
hand-built. `lean.json` needs an `organization-id` key or the CLI rejects the folder as
"an old Lean CLI root folder". The free sample data has no 2007-2026 history for these
ETFs. `quantconnect/lean:latest` is a multi-GB pull — run it as a background task, it
exceeds a 10-minute foreground timeout.

Two that cost real time:

- **A `docker pull` can report exit code 0 with no image on disk.** Verify with
  `docker image inspect quantconnect/lean:latest`, never the exit code.
- **On daily data LEAN fills market orders at that day's CLOSE**, not at the scheduled
  time. `time_rules.after_market_open` sets when the scheduled *method* runs; the order
  becomes MarketOnClose. Measured across 726 fills: 726/726 match close(D) exactly,
  while open(D) is off by 56 bps median. So a `month_start` schedule trades one trading
  day later than a harness that trades on the signal month's close, which makes LEAN
  late into every de-risking move and its drawdown the more honest number. Attribute
  such a gap from the order events, not by reading the schedule.
- **Never compare against LEAN's Strategy Equity chart directly.** At daily resolution it
  carries two stamps per day (midnight ET = the *previous* close, and 16:00 ET) and only
  ~2,899 of ~4,938 trading days have the 16:00 point. Reading it raw, then "fixing" it by
  shifting to maximise correlation, produced two wrong conclusions in one session. Instead
  reconstruct the curve from the fills plus the daily bars and prove it by matching
  reported final equity to the cent; only then compare with identical formulas over the
  common trading days.
