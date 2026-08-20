"""Two stale statements left over from the first-pass cross-check writeup.

Both say LEAN trades "~30 min after the open" / "next-month open+30min". That was
inferred from reading `time_rules.after_market_open` in the algorithm. It is wrong:
on daily data LEAN converts market orders to MarketOnClose, and all 726 fills match
close(D) exactly. The README's own cross-check section was already corrected; caveat
#2 and the CLAUDE.local.md summary were not.

The CLAUDE.local.md entry also attributes the whole CAGR gap to "$4,248 of real fees",
which the decomposition contradicts -- fees are worth about -0.21 pp, the harness's
10 bps turnover charge about -0.72 pp.
"""

import io
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

README_OLD = """2. The harness trades at the signal month's close; the LEAN algorithm trades
   ~30 min after the open on the first trading day of the next month. The two
   will not agree to the basis point.
"""

README_NEW = """2. The harness trades at the signal month's close; LEAN trades one trading day
   later, at the close of the first trading day of the next month (market orders
   on daily data become MarketOnClose regardless of the scheduled time). Measured
   at -1.92 pp of max drawdown and -0.158 pp of CAGR, so LEAN is the more honest
   side of this one.
"""

NOTES_OLD_START = "- **LEAN cross-check: DONE 2026-08-20.**"
NOTES_OLD_END = "- **`gen2-attempt4-concentration`**"

NOTES_NEW = """- **LEAN cross-check: DONE 2026-08-20, no bug found.** The two implementations agree
  closely enough to keep iterating on the harness. Signal decisions are bit-identical
  (236 rebalances, 708 slots, 83 skips, 11 fully-defensive months, same count in every
  one of the nine sectors), and daily returns correlate 0.9919 with mean |difference|
  0.0154 pp. Full table in `faber-lean/README.md`.

  On the identical window and with the harness's own formulas: LEAN CAGR **9.32%**,
  Sharpe-vs-SHY **0.537**, max drawdown **-24.75%**; harness 9.64% / 0.557 / -22.58%
  at 0bps and 8.91% / 0.513 / -22.94% at 10bps. LEAN's return metrics sit *inside* the
  harness's own 0-to-10bps cost bracket, which is where they belong.

  Do not read LEAN's numbers off the `Strategy Equity` chart -- it carries two stamps
  per day and mixing them produced two wrong conclusions before the curve was rebuilt
  from the 726 order events (which reproduces LEAN's End Equity to the cent).

  Three things it settled, each measured rather than inferred:
  - **The 10 bps cost model is ~6.7x too harsh.** LEAN's actual commissions are $4,248
    on $28.3M of traded notional = 1.50 bps; the harness's charge costs $73,306 of
    terminal wealth. Fees explain only ~0.21 pp of the CAGR gap, the cost model ~0.72 pp.
    Quote ~9.3% as realistic and 8.9% as a deliberately conservative floor. (LEAN runs no
    slippage model, so it is the optimistic bound, not the truth.)
  - **-24.75% is the honest drawdown.** On daily data LEAN fills market orders at
    close(D), not at the scheduled `after_market_open` time -- 726/726 fills match
    close(D) exactly. So the harness is one trading day *early* into every de-risk.
    A controlled rerun changing only the fill bar moves drawdown -1.92 pp and CAGR
    -0.158 pp, which covers the observed -1.81 pp gap, same trough episode
    (2010-04-23 -> 2010-08-26). Stop quoting -22.58%.
  - **LEAN sits out January 2007** (~0.058 pp of CAGR): at 10:00 on the algorithm's
    first day no daily bar has arrived, so `set_holdings` cannot size. Add explicit
    warmup if that month matters.

  Still open: LEAN could not load `/alternative/interest-rate/usa/interest-rate.csv`,
  so its own reported Sharpe of 0.497 has no risk-free curve behind it and must not be
  compared to the harness's SHY-relative figures. Sourcing that file into the data root
  is not done.

  Note the pull that "finished" first time reported exit 0 with no image on disk. Verify
  `docker image inspect quantconnect/lean:latest`, never the exit code. Real image is
  14GB compressed / 42.5GB on disk.

"""


def patch(path, old, new, label):
    with io.open(path, encoding="utf-8") as fh:
        body = fh.read()
    if new.strip()[:60] in body:
        print("  %-22s already patched" % label)
        return
    n = body.count(old)
    if n != 1:
        raise SystemExit("%s: expected 1 match, found %d" % (label, n))
    with io.open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(body.replace(old, new))
    print("  %-22s patched (%d -> %d chars)" % (label, len(body), len(body) - len(old) + len(new)))


def main():
    readme = os.path.join(ROOT, "faber-lean", "README.md")
    patch(readme, README_OLD, README_NEW, "README caveat 2")

    notes = os.path.join(ROOT, "CLAUDE.local.md")
    with io.open(notes, encoding="utf-8") as fh:
        body = fh.read()
    if "no bug found" in body:
        print("  %-22s already patched" % "CLAUDE.local.md")
        return
    i = body.index(NOTES_OLD_START)
    j = body.index(NOTES_OLD_END)
    with io.open(notes, "w", encoding="utf-8", newline="") as fh:
        fh.write(body[:i] + NOTES_NEW + body[j:])
    print("  %-22s patched" % "CLAUDE.local.md")


if __name__ == "__main__":
    print("=== patching stale fill-timing claims ===")
    main()
