"""Rewrite the cross-check section from the exact reconstruction.

Supersedes two rounds of patching. The basis is now reconstruct_lean.py, which
rebuilds LEAN's equity from its own 726 fills and the daily bars and lands on
LEAN's reported final equity to the cent ($570,569.38, delta $0.00). Every
figure below is computed on that curve with the harness's own formulas over the
same 4,918 common trading days, which is the only way the two are comparable.
"""
import pathlib

p = pathlib.Path("faber-lean/README.md")
txt = p.read_text(encoding="utf-8")

start = txt.index("## LEAN vs harness cross-check")
end = txt.index("## Known caveats")

NEW = """## LEAN vs harness cross-check (2026-08-20)

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

Two earlier claims in this section were wrong and are corrected above, both because they
were computed on the ragged raw equity stamps rather than the reconstruction: that the
volatility difference was a daily-vs-monthly annualisation convention (it is not -- on
identical formulas the two agree at 14.8%), and that the one-day handover explained 43.9%
of the month-to-month return difference (that figure fell to -2.4% under a one-day
re-alignment, so no attribution figure is quoted).

LEAN also recorded 726 orders and 1.84% portfolio turnover, consistent with 3 slots over
236 rebalances.

"""

txt = txt[:start] + NEW + txt[end:]

OLD_C7 = "7. 10 bps of turnover cost is worth ~72 bps/yr of CAGR here."
NEW_C7 = ("7. 10 bps of turnover cost is worth ~72 bps/yr of CAGR here -- confirmed by the\n"
          "   cross-check, which also shows LEAN's actual cost is only ~1.5 bps of notional.")
if OLD_C7 in txt:
    txt = txt.replace(OLD_C7, NEW_C7, 1)
else:
    raise SystemExit("caveat 7 anchor not found")

body = txt.encode("utf-8")
body.decode("utf-8")
p.write_bytes(body)
print("rewritten OK, %d bytes, non-ascii=%d" % (len(body), sum(1 for b in body if b > 127)))
