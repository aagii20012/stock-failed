"""Bring CLAUDE.local.md in line with the reconciled cross-check."""
import pathlib

p = pathlib.Path("CLAUDE.local.md")
txt = p.read_text(encoding="utf-8")

OLD = """- **LEAN cross-check: DONE 2026-08-20.** `lean backtest FaberSectorRotation` ran to
  completion. Every signal decision matches the harness exactly (236 rebalances, 708
  slots, 83 skips, 11 fully-defensive months, identical per-sector breakdown). CAGR
  9.27% vs 9.67% gross, explained by $4,248 of real fees. See the README table.

  Two live issues it left behind:
  - LEAN reports max drawdown **-24.70%** vs the harness's -22.58%. The harness trades
    at the signal month's close, LEAN at next-month open+30min, so LEAN is late into
    every de-risk. Treat -24.70% as the honest number and stop quoting -22.58%.
  - LEAN could not load `/alternative/interest-rate/usa/interest-rate.csv`, so its
    Sharpe of 0.497 has no risk-free curve behind it. Do not compare it to the
    harness's SHY-relative figures. Fixing it means sourcing that file into the data
    root; not done.
"""

NEW = """- **LEAN cross-check: DONE and fully reconciled 2026-08-20.** Every signal decision
  matches the harness exactly (236 rebalances, 708 slots, 83 skips, 11 fully-defensive
  months, identical per-sector breakdown), and daily returns agree at corr 0.9919.
  Comparisons are computed on a curve reconstructed from LEAN's 726 fills, which hits
  its reported final equity to the cent ($570,569.38, delta $0.00). Numbers on identical
  formulas: LEAN 9.32% CAGR / -24.75% maxdd vs harness 9.64% / -22.58% gross. See the
  README section, which is now the authoritative write-up.

  What changed from the first pass -- I had built the comparison on LEAN's raw Strategy
  Equity stamps, which are ragged (two points per day, only ~2,899 of ~4,938 days carry
  the 16:00 ET one). Three claims from that pass were wrong: the vol difference was not
  an annualisation convention (they agree at 14.8%), the one-day handover does not
  explain 43.9% of the month-to-month return difference (-2.4% once re-aligned), and
  LEAN does not fill at "next-month open+30min" -- all 726 fills are at close(D) of
  their own trading day, because market orders become MarketOnClose on daily data.

  Still open / worth knowing:
  - The drawdown gap is real and attributed: a controlled rerun changing only the fill
    bar moves maxdd -1.92pp, covering the observed -1.81pp. Quote -24.75%, not -22.58%.
  - **The 10bps cost model is ~6.7x too harsh.** LEAN's real commissions are $4,248 on
    $28.3M notional (1.50bps) against $73,306 charged by the harness. So ~9.3% CAGR is
    realistic; 8.9% is a deliberately conservative floor. Consider dropping the harness
    default to ~2bps.
  - LEAN could not load `/alternative/interest-rate/usa/interest-rate.csv`, so its own
    reported Sharpe of 0.497 has no risk-free curve. Recomputing on the reconstructed
    curve gives 0.675 rf=0 / 0.537 vs SHY, which are comparable. Sourcing that file into
    the data root is still not done.
  - LEAN sat out January 2007 (first fill 2007-02-01 vs the harness's 2007-01-03), worth
    +0.058pp of CAGR. Comparisons above already start on LEAN's invested window.
"""

if OLD not in txt:
    raise SystemExit("anchor not found")

txt = txt.replace(OLD, NEW, 1)

ADD_NOTE = """
- **Something other than my own edits wrote into `_scratch/` during the 2026-08-20
  session.** Diagnostics appeared between consecutive `git status` calls, each one
  continuing the analysis thread (fill convention -> equity-stamp lag -> reconstruct the
  curve -> Jan 2007 gap -> drawdown attribution). No hooks are configured and no python
  processes were running. They were correct and I verified each by running it, but the
  provenance is unexplained -- possibly a concurrent session in this workspace. Practical
  consequence: **never `git add -A` here.** A blind stage pushed ten unreviewed files in
  commit 0027d94. Stage explicit paths.
"""

MARKER = "- **`gen2-attempt4-concentration`** is a local-only branch"
if MARKER not in txt:
    raise SystemExit("branch marker not found")
txt = txt.replace(MARKER, ADD_NOTE.lstrip("\n") + "\n" + MARKER, 1)

body = txt.encode("utf-8")
body.decode("utf-8")
p.write_bytes(body)
print("patched OK, %d bytes" % len(body))
