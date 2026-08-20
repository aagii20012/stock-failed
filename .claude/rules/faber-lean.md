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
