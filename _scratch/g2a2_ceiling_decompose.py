"""Decompose the RA2-1 part_c excess into its two structural terms, by measurement not by argument.

The claim to be checked: the observed close-time excess over 0.50 is bounded by
(one minimum lot, left behind by a skipped sub-minimum trim) + (one session's appreciation between
the open at which the ceiling was last enforced and the close at which it is measured).

Nothing here modifies the engine. ``_record_gross_fraction`` is wrapped from the outside so the run
is byte-identical to the real one; the wrapper only observes.

ASCII output only.
"""

from __future__ import annotations

import datetime as dt
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.backtest.g2_engine_ra1 import RotationEngineRA1  # noqa: E402
from stockedge100.strategies import g2_runner_ra1 as R  # noqa: E402
from stockedge100.strategies.g2_rotation_ra1 import rotation_variants  # noqa: E402

TRACE: list[tuple[dt.date, Decimal, Decimal, Decimal]] = []
_original = RotationEngineRA1._record_gross_fraction


def _wrapped(self, session, equity):
    gross = sum(self._close_marked_values(session).values(), Decimal("0"))
    if equity > 0:
        TRACE.append((session, gross, equity, gross / equity))
    return _original(self, session, equity)


RotationEngineRA1._record_gross_fraction = _wrapped

variant = rotation_variants()[0]
series = R.load_grid_dataset()
run = R.run_grid(series, variants=(variant,), labels=("#BASE",), verify=False)[0]

RotationEngineRA1._record_gross_fraction = _original

risk = run.risk
peak_session = dt.date.fromisoformat(risk["max_gross_fraction_session"])
by_session = {s: (g, e, f) for s, g, e, f in TRACE}
order = [s for s, _, _, _ in TRACE]
index = order.index(peak_session)

print("peak session %s, fraction %s" % (peak_session, by_session[peak_session][2]))
print()
print("%-12s %14s %14s %22s %14s" % ("session", "gross", "equity", "gross/equity", "excess_usd"))
for session in order[max(0, index - 6): index + 4]:
    gross, equity, fraction = by_session[session]
    excess = gross - Decimal("0.50") * equity
    marker = "  <== peak" if session == peak_session else ""
    print("%-12s %14.6f %14.6f %22s %14.6f%s" % (
        session, gross, equity, fraction, excess, marker))

print()
print("The excess is the amount a trim would have had to sell to restore 0.50 at that close.")
print("min_order_notional is 1.00, so an excess below 1.00 is skipped as MIN_NOTIONAL and carried.")

# How much of the peak excess is the carried sub-minimum residual, and how much is that session's
# appreciation? The prior close's excess is the carry; the difference is the move.
prior = order[index - 1]
peak_excess = by_session[peak_session][0] - Decimal("0.50") * by_session[peak_session][1]
prior_excess = by_session[prior][0] - Decimal("0.50") * by_session[prior][1]
print()
print("carried into the peak session (prior close excess) %s" % prior_excess)
print("added by the peak session itself                   %s" % (peak_excess - prior_excess))
print("peak excess                                        %s" % peak_excess)
print("in minimum lots                                    %s" % peak_excess)

# The distribution of the excess across every breaching close, which is what tells us whether the
# peak is an outlier or the tail of a systematic effect.
excesses = sorted(
    (g - Decimal("0.50") * e for _, g, e, f in TRACE if f > Decimal("0.50")), reverse=True
)
print()
print("closes breaching 0.50: %d of %d" % (len(excesses), len(TRACE)))
if excesses:
    print("largest ten excesses (in units of min_order_notional = 1.00):")
    for value in excesses[:10]:
        print("   %s" % value)
    above_one_lot = [v for v in excesses if v > Decimal("1.00")]
    print("closes whose excess exceeded one minimum lot: %d" % len(above_one_lot))
    print("closes whose excess exceeded two minimum lots: %d" % len([v for v in excesses if v > 2]))
