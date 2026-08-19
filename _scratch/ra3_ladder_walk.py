"""Recompute the maximum-loss round-trip walk for RA2 and RA3.

The model is reverse-engineered from Attempt 2's sealed table and then VALIDATED
against it row by row.  Only if every RA2 row reproduces byte-identically is the
RA3 walk trusted.

Model: consecutive round trips each losing exactly the 8% per-position stop on the
full permitted aggregate exposure f_cap.  Portfolio loss per trip = f_cap * 0.08.
Equity compounds; dd is measured from the high-water mark (equity starts at 1 and
never rises in this walk, so high_water == 1 throughout).
"""

import pathlib
import re
from decimal import Decimal, ROUND_HALF_EVEN

STOP = Decimal("0.08")

RA2_BANDS = [  # (lower, upper_or_None, scalar, band_label_used_in_the_sealed_table)
    (Decimal("0.00"), Decimal("0.05"), Decimal("0.500"), "0"),
    (Decimal("0.05"), Decimal("0.08"), Decimal("0.375"), "1"),
    (Decimal("0.08"), Decimal("0.10"), Decimal("0.250"), "2"),
    (Decimal("0.10"), None, Decimal("0.125"), "3"),
]

RA3_BANDS = [
    (Decimal("0.00"), Decimal("0.08"), Decimal("0.500"), "0"),
    (Decimal("0.08"), Decimal("0.10"), Decimal("0.250"), "1"),
    (Decimal("0.10"), None, Decimal("0.125"), "2"),
]


def band_for(dd, bands):
    for lower, upper, scalar, label in bands:
        if dd >= lower and (upper is None or dd < upper):
            return scalar, label
    raise AssertionError("no band for %s" % dd)


def pct(x, places="0.0001"):
    return (x * 100).quantize(Decimal(places), rounding=ROUND_HALF_EVEN)


def walk(bands, breach=Decimal("0.15"), limit=40):
    equity = Decimal(1)
    rows = []
    for trip in range(1, limit + 1):
        dd_before = Decimal(1) - equity
        scalar, label = band_for(dd_before, bands)
        loss = scalar * STOP
        equity = equity * (Decimal(1) - loss)
        dd_after = Decimal(1) - equity
        rows.append((trip, dd_before, label, scalar, loss, dd_after,
                     dd_after >= breach))
        if dd_after >= breach:
            break
    return rows


def render(rows):
    out = []
    for trip, dd_before, label, scalar, loss, dd_after, breached in rows:
        after = "%s%%" % pct(dd_after)
        if breached:
            after = "**%s%% - breach**" % pct(dd_after)
        out.append("| %d | %s%% | %s | %s | %s%% | %s |" % (
            trip, pct(dd_before), label, scalar, pct(loss, "0.000"), after))
    return out


# ---- validate against the sealed Attempt 2 table -----------------------------
sealed = pathlib.Path(
    "stockedge100/governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.md"
).read_text(encoding="utf-8")
block = re.search(r"\| Trip \| `dd` before \|.*?\n\n", sealed, re.S).group(0)
sealed_rows = [ln for ln in block.splitlines()
               if ln.startswith("| ") and not ln.startswith("| Trip")]
sealed_rows = [ln.replace("—", "-") for ln in sealed_rows]

ra2 = render(walk(RA2_BANDS))
print("RA2 sealed rows : %d" % len(sealed_rows))
print("RA2 recomputed  : %d" % len(ra2))
mismatch = 0
for i, (got, want) in enumerate(zip(ra2, sealed_rows), 1):
    if got != want:
        mismatch += 1
        print("  ROW %d MISMATCH" % i)
        print("    sealed: %s" % want)
        print("    ours  : %s" % got)
assert len(ra2) == len(sealed_rows), "row count differs"
assert mismatch == 0, "%d rows differ" % mismatch
print("MODEL VALIDATED: all %d RA2 rows reproduce the sealed table exactly." % len(ra2))

# ---- emit the RA3 walk -------------------------------------------------------
ra3rows = walk(RA3_BANDS)
print("\nRA3 walk (%d trips to breach):" % len(ra3rows))
print("| Trip | `dd` before | Band | `f_cap` | Loss this trip | `dd` after |")
print("|---|---|---|---|---|---|")
for line in render(ra3rows):
    print(line)

pen = ra3rows[-2]
print("\nRA3 trips to breach : %d" % len(ra3rows))
print("RA2 trips to breach : %d" % len(ra2))
print("RA3 dd after trip %d : %s%%" % (len(ra3rows) - 1, pct(pen[5])))
bands_touched = sorted({r[2] for r in ra3rows})
print("RA3 bands touched in the walk: %s" % bands_touched)
print("RA3 band skipped             : %s" % (
    sorted({"0", "1", "2"} - set(bands_touched)) or "none"))
