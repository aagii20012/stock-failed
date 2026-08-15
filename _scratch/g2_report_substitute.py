"""Substitute the sealed verbatim disclosures and the real UTC clock into the Stage 3 G2 report.

ASCII output only. The two disclosures must appear *verbatim*; retyping them by hand is exactly the
failure mode the operating instruction warns about ("do not soften, shorten, or omit this text"), so
they are read from the sealed JSON and pasted mechanically. Each is substituted as a single line so
the string stays contiguous -- re-wrapping it across ``> `` prefixes would break the verbatim match.

The timestamp is read from the system clock at substitution time, never hand-typed.

Idempotent-safe: refuses to run if a placeholder is already gone, so a second run cannot double-write
or silently do nothing while reporting success.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
REPORT = ROOT / "governance/generation_2/STAGE_3_G2_ROTATION_RESEARCH_REPORT.md"
LOCK = ROOT / "governance/generation_2/STAGE_1_G2_PARTITION_LOCK.json"
# The multiplicity disclosure is sealed in the *config* protocol (SE100-CFG-3101), not the
# governance counterpart -- checked, not assumed: it is absent from
# governance/generation_2/STAGE_3_G2_ROTATION_PROTOCOL.{md,json} even after whitespace normalisation.
PROTOCOL = ROOT / "config/generation_2/g2_rotation_protocol.json"


def main() -> int:
    text = REPORT.read_text(encoding="utf-8")
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))

    validation = lock["validation_reuse_disclosure"]
    multiplicity = protocol["multiple_comparisons_disclosure"]
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    subs = [
        ("@@AUTHORED_UTC@@", stamp),
        ("@@VALIDATION_REUSE_DISCLOSURE@@", validation),
        ("@@MULTIPLE_COMPARISONS_DISCLOSURE@@", multiplicity),
    ]

    for token, _ in subs:
        count = text.count(token)
        print(f"placeholder {token:38s} occurrences={count}")
        if count != 1:
            print(f"*** expected exactly 1 occurrence of {token}, found {count} -- refusing")
            return 1

    for token, value in subs:
        text = text.replace(token, value)

    REPORT.write_text(text, encoding="utf-8", newline="\n")

    written = REPORT.read_text(encoding="utf-8")
    print()
    print(f"authored_utc stamped            {stamp}")
    print(f"validation disclosure chars     {len(validation)}")
    print(f"multiplicity disclosure chars   {len(multiplicity)}")
    print()
    print(f"validation verbatim in report   {validation in written}")
    print(f"multiplicity verbatim in report {multiplicity in written}")
    print(f"stamp in report                 {stamp in written}")
    print(f"no placeholder left             {'@@' not in written}")
    print(f"report bytes                    {REPORT.stat().st_size}")

    ok = (
        validation in written
        and multiplicity in written
        and stamp in written
        and "@@" not in written
    )
    print()
    print("RESULT " + ("OK" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
