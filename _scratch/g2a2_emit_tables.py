"""Emit the measured Markdown table rows for the Attempt 2 pre-registration.

Nothing here is typed by hand. Every row is built by the same functions Attempt 1's sealer uses to
CHECK the Markdown, so a row pasted from this output cannot disagree with the checker. Reading
Attempt 1's module is a read; no Attempt 1 file is written.

ASCII output only (cp1252 console).
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1] / "stockedge100"
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.reporting.g2_rotation_preregistration import (  # noqa: E402
    POSITION_COUNTS,
    WEIGHT_QUANTUM,
    enumerate_grid,
    measure_span,
    target_weight,
)
from stockedge100.reporting.g2_partition_lock import (  # noqa: E402
    DEVELOPMENT_END,
    DEVELOPMENT_START,
    GENERATION_1_HOLDOUT_END,
    GENERATION_1_HOLDOUT_START,
    HOLDOUT_END,
    HOLDOUT_START,
    UNIVERSE,
    UNIVERSE_VERSION,
    VALIDATION_END,
    VALIDATION_START,
    generation_identity,
)

span = measure_span()

print("=== span (measured from disk, session dates only) ===")
for k in sorted(span):
    v = span[k]
    s = json.dumps(v)
    print("  %-34s %s" % (k, s if len(s) < 140 else s[:140] + " ...(%d)" % len(s)))

print()
print("=== identity / windows ===")
print("  generation_id            %s" % generation_identity()["generation_id"])
print("  universe_version         %s  (%d members)" % (UNIVERSE_VERSION, len(UNIVERSE)))
print("  development              %s -> %s" % (DEVELOPMENT_START, DEVELOPMENT_END))
print("  validation               %s -> %s" % (VALIDATION_START, VALIDATION_END))
print("  generation_1_holdout     %s -> %s" % (GENERATION_1_HOLDOUT_START, GENERATION_1_HOLDOUT_END))
print("  generation_2_holdout     %s -> %s" % (HOLDOUT_START, HOLDOUT_END))

print()
print("=== GRID TABLE ROWS (paste verbatim) ===")
counts = {
    "MONTHLY": span["monthly_rebalance_sessions"],
    "QUARTERLY": span["quarterly_rebalance_sessions"],
}
print("| # | Variant id | Lookback | k | Rebalance | Weight/position | Gross | Rebalance sessions |")
print("|---|---|---|---|---|---|---|---|")
for row in enumerate_grid():
    print(
        "| %s | %s | %s | %s | %s | %s | %s | %s |"
        % (
            row["index"],
            row["variant_id"],
            row["lookback_months"],
            row["top_k"],
            row["rebalance_frequency"],
            row["target_weight_per_position"],
            row["target_gross_exposure"],
            counts[row["rebalance_frequency"]],
        )
    )

print()
print("=== WEIGHT TABLE ROWS (paste verbatim) ===")
print("| k | Weight per position | Target gross |")
print("|---|---|---|")
for k in POSITION_COUNTS:
    w = target_weight(k)
    g = (w * k).quantize(WEIGHT_QUANTUM)
    print("| %d | %.9f | %.9f |" % (k, w, g))

print()
print("=== REBALANCE CALENDAR ROWS (paste verbatim) ===")
print("| Frequency | Sessions | First three | Last two |")
print("|---|---|---|---|")
for freq, cnt, first3, last2 in (
    ("MONTHLY", span["monthly_rebalance_sessions"], span["monthly_first_three"], span["monthly_last_two"]),
    ("QUARTERLY", span["quarterly_rebalance_sessions"], span["quarterly_first_three"], span["quarterly_last_two"]),
):
    print("| %s | %s | %s | %s |" % (freq, cnt, ", ".join(first3), ", ".join(last2)))

print()
print("=== ATTEMPT 2 CONTAMINATION INVENTORY (g2_ or ra1 in basename) ===")
src = ROOT / "src" / "stockedge100"
tests = ROOT / "tests"


def matches(root: pathlib.Path) -> list[str]:
    if not root.exists():
        return []
    return sorted(
        p.relative_to(ROOT).as_posix()
        for p in root.rglob("*.py")
        if "g2_" in p.name or "ra1" in p.name
    )


for label, root in (
    ("strategies", src / "strategies"),
    ("backtest", src / "backtest"),
    ("reporting", src / "reporting"),
    ("tests", tests),
):
    found = matches(root)
    print("  %-11s %d" % (label, len(found)))
    for f in found:
        print("      %s" % f)

ra1 = sorted(set(matches(src)) | set(matches(tests)))
ra1 = [f for f in ra1 if "ra1" in pathlib.Path(f).name]
print("  ra1-named modules anywhere: %d %s" % (len(ra1), ra1))
print("  reports/stage3_g2_attempt2 exists: %s" % (ROOT / "reports" / "stage3_g2_attempt2").exists())
