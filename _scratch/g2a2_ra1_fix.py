"""Two corrections: floor the Attempt 2 weights, and name the one short monthly rebalance gap."""
from __future__ import annotations

import datetime as dt
import pathlib
import sys
from decimal import ROUND_FLOOR, Decimal, localcontext

ROOT = pathlib.Path(__file__).resolve().parents[1] / "stockedge100"
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.backtest.costs import ENGINE_CONTEXT  # noqa: E402
from stockedge100.data.calendar import sessions_between  # noqa: E402
from stockedge100.reporting.g2_rotation_preregistration import (  # noqa: E402
    CONCENTRATION_CEILING,
    MAX_GROSS,
    POSITION_COUNTS,
    WEIGHT_QUANTUM,
    measure_span,
    target_weight,
)

D = Decimal
F_BASE = D("0.50")


def weight_ra1(k: int) -> Decimal:
    """Attempt 2's per-position target weight: Attempt 1's own formula with MAX_GROSS -> F_BASE."""
    return min(F_BASE / k, CONCENTRATION_CEILING).quantize(WEIGHT_QUANTUM, rounding=ROUND_FLOOR)


with localcontext(ENGINE_CONTEXT):
    print("=== Attempt 1's formula, reproduced, to prove the Attempt 2 form is the same shape ===")
    print("Attempt 1: floor_9(min(MAX_GROSS/k, CONCENTRATION_CEILING)), MAX_GROSS=%s ceiling=%s"
          % (MAX_GROSS, CONCENTRATION_CEILING))
    ok = True
    for k in POSITION_COUNTS:
        mine = min(MAX_GROSS / k, CONCENTRATION_CEILING).quantize(WEIGHT_QUANTUM, rounding=ROUND_FLOOR)
        theirs = target_weight(k)
        same = mine == theirs
        ok &= same
        print("  k=%d  reproduced %s  sealed %s  %s" % (k, mine, theirs, "MATCH" if same else "DIFFER"))
    print("  formula reproduces Attempt 1 exactly: %s" % ok)
    assert ok, "the Attempt 2 weight formula is not Attempt 1's formula with one constant swapped"

    print()
    print("=== B (corrected). Attempt 2 weights: same formula, MAX_GROSS replaced by f_base=0.50 ===")
    print("| k | Attempt 1 weight | Attempt 1 gross | Attempt 2 weight | Attempt 2 gross | Under ceiling? |")
    print("|---|---|---|---|---|---|")
    for k in POSITION_COUNTS:
        w1 = target_weight(k)
        g1 = (w1 * k).quantize(WEIGHT_QUANTUM)
        w2 = weight_ra1(k)
        g2 = (w2 * k).quantize(WEIGHT_QUANTUM)
        assert g2 <= F_BASE, "k=%d gross %s exceeds the ceiling" % (k, g2)
        print("| %d | %.9f | %.9f | %.9f | %.9f | %s |"
              % (k, w1, g1, w2, g2, "yes" if g2 <= F_BASE else "NO"))
    print("  every k: aggregate target gross <= f_base = 0.50 ..... ASSERTED")

print()
print("=== D (corrected). The one monthly rebalance gap shorter than the 10-session lockout ===")
span = measure_span()
all_sessions = sessions_between(dt.date.fromisoformat(span["run_start"]),
                                dt.date.fromisoformat(span["run_end"]))
index = {s: i for i, s in enumerate(all_sessions)}
cal, seen = [], set()
for s in all_sessions:
    key = (s.year, s.month)
    if key not in seen:
        seen.add(key)
        cal.append(s)
short = [(a, b, index[b] - index[a]) for a, b in zip(cal, cal[1:]) if index[b] - index[a] < 10]
for a, b, g in short:
    print("  %s -> %s : %d sessions" % (a.isoformat(), b.isoformat(), g))
print("  count of monthly gaps < 10 sessions: %d of %d" % (len(short), len(cal) - 1))
print("  count of monthly gaps <  5 sessions: %d of %d"
      % (sum(1 for a, b in zip(cal, cal[1:]) if index[b] - index[a] < 5), len(cal) - 1))
