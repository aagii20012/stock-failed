"""Compute every derived RA1 table the Attempt 2 pre-registration will carry.

Nothing below is a prediction. Every figure is an arithmetic property of the five frozen constants,
computed before any Attempt 2 strategy module exists, in the same Decimal context the engine uses.

ASCII output only.
"""
from __future__ import annotations

import pathlib
import sys
from decimal import Decimal, localcontext

ROOT = pathlib.Path(__file__).resolve().parents[1] / "stockedge100"
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.backtest.costs import ENGINE_CONTEXT  # noqa: E402
from stockedge100.reporting.g2_rotation_preregistration import (  # noqa: E402
    POSITION_COUNTS,
    WEIGHT_QUANTUM,
    measure_span,
    target_weight,
)

D = Decimal
Q9 = D("1E-9")

F_BASE = D("0.50")       # RA1-1, sealed
L = D("0.08")            # RA1-3, sealed
SIGMA_TARGET = D("0.10")  # RA1-2, sealed
F_FLOOR = D("0.05")      # RA1-2, sealed
LOCKOUT = 10             # new, account-level

# rung threshold (dd >=) -> multiplier of normal sizing
LADDER = ((D("0.10"), D("0.25")), (D("0.08"), D("0.50")), (D("0.05"), D("0.75")), (D("0"), D("1.00")))


def ladder_multiplier(dd: Decimal) -> Decimal:
    for threshold, mult in LADDER:
        if dd >= threshold:
            return mult
    raise AssertionError("unreachable: ladder is total over dd >= 0")


with localcontext(ENGINE_CONTEXT):
    print("=== A. Ladder rungs, absolute and as fractions of f_base ===")
    print("| Rung | Drawdown from HWM | Multiplier of normal sizing | Aggregate ceiling f_cap | Gen 1 RA1-5 f_cap | Same? |")
    print("|---|---|---|---|---|---|")
    g1 = {D("0.08"): D("0.25"), D("0.10"): D("0.125")}
    names = {D("0"): "R0", D("0.05"): "R1", D("0.08"): "R2", D("0.10"): "R3"}
    for threshold, mult in reversed(LADDER):
        f_cap = (F_BASE * mult).quantize(Q9)
        if threshold == 0:
            g1v, same = F_BASE.quantize(Q9), "yes"
        elif threshold in g1:
            g1v = g1[threshold].quantize(Q9)
            same = "yes" if g1v == f_cap else "NO"
        else:
            g1v, same = None, "new rung"
        lo = "dd < 0.05" if threshold == 0 else (
            "0.05 <= dd < 0.08" if threshold == D("0.05") else
            "0.08 <= dd < 0.10" if threshold == D("0.08") else "dd >= 0.10")
        print("| %s | %s | %s | %s | %s | %s |"
              % (names[threshold], lo, mult, f_cap, g1v if g1v is not None else "-- (absent)", same))

    print()
    print("=== B. Effective per-position target weight under the RA1-1 ceiling, by k ===")
    print("(base weights are Attempt 1's, unchanged; the ceiling rescales the vector proportionally)")
    print("| k | Attempt 1 weight/position | Attempt 1 gross | Ceiling scale | Attempt 2 weight/position | Attempt 2 gross |")
    print("|---|---|---|---|---|---|")
    for k in POSITION_COUNTS:
        w = target_weight(k)
        gross = (w * k).quantize(WEIGHT_QUANTUM)
        scale = min(D(1), F_BASE / gross)
        w2 = (w * scale).quantize(WEIGHT_QUANTUM)
        g2 = (w2 * k).quantize(WEIGHT_QUANTUM)
        print("| %d | %.9f | %.9f | %.9f | %.9f | %.9f |" % (k, w, gross, scale, w2, g2))

    print()
    print("=== C. Worst-case drawdown walk under the frozen constants ===")
    print("Consecutive round trips each losing exactly L on the full permitted aggregate exposure.")
    print("Loss per round trip = f_cap(dd) * L. Ladder read at each decision close.")
    print()
    equity, hwm, step = D(1), D(1), 0
    rows = []
    while True:
        step += 1
        dd = ((hwm - equity) / hwm)
        f_cap = (F_BASE * ladder_multiplier(dd)).quantize(Q9)
        loss = (f_cap * L)
        equity = equity * (D(1) - loss)
        dd_after = ((hwm - equity) / hwm)
        rows.append((step, dd, f_cap, loss, equity, dd_after))
        if dd_after >= D("0.15") or step > 40:
            break
    print("| Trip | dd before | f_cap | Loss this trip | Equity after | dd after |")
    print("|---|---|---|---|---|---|")
    for s, dd, f, ls, eq, dda in rows:
        flag = " **BREACH**" if dda >= D("0.15") else ""
        print("| %d | %.4f%% | %.3f | %.3f%% | %.6f | %.4f%%%s |"
              % (s, dd * 100, f, ls * 100, eq, dda * 100, flag))
    print()
    print("RESULT: %d consecutive maximum-loss round trips are required to breach 15%%." % len(rows))
    print("        %d leave drawdown at %.4f%%." % (len(rows) - 1, rows[-2][5] * 100))

    # The Generation 1 comparison, recomputed here rather than quoted from its report.
    equity, hwm, step = D(1), D(1), 0
    while True:
        step += 1
        dd = (hwm - equity) / hwm
        f_cap = D("0.125") if dd >= D("0.10") else (D("0.25") if dd >= D("0.08") else D("0.50"))
        equity = equity * (D(1) - f_cap * L)
        if (hwm - equity) / hwm >= D("0.15") or step > 40:
            break
    print("        Under Generation 1's sealed RA1-5 rungs the same walk breaches in %d trips." % step)
    print("        The -5%% rung therefore buys %d additional maximum-loss round trips." % (len(rows) - step))

print()
print("=== D. Rebalance spacing, against the 10-session ladder lockout ===")
span = measure_span()
sessions = None
try:
    from stockedge100.reporting.g2_rotation_preregistration import sessions_only  # noqa: E402
except ImportError:
    sessions_only = None

import datetime as dt  # noqa: E402
from stockedge100.data.calendar import sessions_between  # noqa: E402

all_sessions = sessions_between(dt.date.fromisoformat(span["run_start"]),
                                dt.date.fromisoformat(span["run_end"]))
index = {s: i for i, s in enumerate(all_sessions)}
print("| Frequency | Rebalances | Min gap (sessions) | Median gap | Max gap | Gaps < 5 | Gaps < 10 |")
print("|---|---|---|---|---|---|---|")
for freq in ("MONTHLY", "QUARTERLY"):
    # Rebuild the calendar the same way the sealer measures it: first session of each period.
    months = (1, 4, 7, 10) if freq == "QUARTERLY" else tuple(range(1, 13))
    cal, seen = [], set()
    for s in all_sessions:
        key = (s.year, s.month)
        if s.month in months and key not in seen:
            seen.add(key)
            cal.append(s)
    cal = [s for s in cal if s >= all_sessions[0]]
    gaps = [index[b] - index[a] for a, b in zip(cal, cal[1:])]
    gaps_sorted = sorted(gaps)
    median = gaps_sorted[len(gaps_sorted) // 2]
    print("| %s | %d | %d | %d | %d | %d | %d |"
          % (freq, len(cal), min(gaps), median, max(gaps),
             sum(1 for g in gaps if g < 5), sum(1 for g in gaps if g < LOCKOUT)))
print()
print("(cross-check against the sealer's own counts: monthly %d, quarterly %d)"
      % (span["monthly_rebalance_sessions"], span["quarterly_rebalance_sessions"]))
