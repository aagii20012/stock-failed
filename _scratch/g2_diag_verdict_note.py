"""Diagnose three checker failures: stage_verdict field shapes, the selection note, return types.

ASCII only -- the sealed strings contain an em dash, so print with a replacement codec rather than
letting cp1252 kill the sweep mid-run.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
EVIDENCE = ROOT / "reports/stage3_g2/STAGE_3_G2_DEVELOPMENT_ADMISSIBILITY.json"
REPORT = ROOT / "governance/generation_2/STAGE_3_G2_ROTATION_RESEARCH_REPORT.md"


def show(s: str) -> str:
    return s.encode("ascii", "backslashreplace").decode("ascii")


def main() -> None:
    ev = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    report = REPORT.read_text(encoding="utf-8")

    print("== stage_verdict fields ==")
    for k, v in ev["stage_verdict"].items():
        if isinstance(v, str):
            print(f"   {k:38s} = {show(v)!r}")
        else:
            print(f"   {k:38s} = {v!r}")

    print()
    print("== selection.selection_note (sealed) ==")
    note = ev["selection"]["selection_note"]
    print(f"   len {len(note)}")
    print(f"   {show(note)}")

    print()
    print("== does the report contain it? ==")
    norm = lambda s: re.sub(r"[\s>]+", " ", s).strip()
    n_note, n_report = norm(note), norm(report)
    print(f"   exact substring      : {note in report}")
    print(f"   normalised substring : {n_note in n_report}")
    lo, hi = 0, len(n_note)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if n_note[:mid] in n_report:
            lo = mid
        else:
            hi = mid - 1
    print(f"   longest matching prefix: {lo}/{len(n_note)} chars")
    if lo < len(n_note):
        print(f"   matched : ...{show(n_note[max(0, lo - 60):lo])}")
        print(f"   diverges: {show(n_note[lo:lo + 90])}...")

    print()
    print("== stage_verdict.selection_note (separate copy?) ==")
    sv_note = ev["stage_verdict"].get("selection_note")
    if isinstance(sv_note, str):
        print(f"   len {len(sv_note)}, identical to selection.selection_note: {sv_note == note}")
        print(f"   in report exactly: {sv_note in report}")
        print(f"   in report normalised: {norm(sv_note) in n_report}")

    print()
    print("== variant_table numeric field types ==")
    row = ev["variant_table"][0]
    for k, v in row.items():
        print(f"   {k:34s} {type(v).__name__:5s} = {v!r}")


if __name__ == "__main__":
    main()
