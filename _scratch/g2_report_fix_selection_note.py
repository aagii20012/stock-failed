"""Replace the report's hand-wrapped selection-note blockquote with the sealed string itself.

ASCII output only.

The report introduces the quotation as "verbatim from the evidence file" and then carried
``` `no_candidate_path` ``` -- markdown backticks I added inside a quotation. That is a modification,
however cosmetic, and it made the verbatim claim false. The two big sealed disclosures are already
substituted from disk as single unbroken lines so that byte-identity is checkable by plain string
comparison; this note is now handled the same way, for the same reason.

Refuses unless it finds exactly one anchor and the sealed text is present verbatim afterwards.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
REPORT = ROOT / "governance/generation_2/STAGE_3_G2_ROTATION_RESEARCH_REPORT.md"
EVIDENCE = ROOT / "reports/stage3_g2/STAGE_3_G2_DEVELOPMENT_ADMISSIBILITY.json"

ANCHOR = "The sealed selection note, verbatim from the evidence file:\n\n"


def main() -> int:
    text = REPORT.read_text(encoding="utf-8")
    note = json.loads(EVIDENCE.read_text(encoding="utf-8"))["selection"]["selection_note"]

    count = text.count(ANCHOR)
    print(f"anchor occurrences        {count}")
    if count != 1:
        print("*** expected exactly 1 anchor -- refusing")
        return 1

    if note in text:
        print("sealed note already present verbatim -- nothing to do")
        return 0

    start = text.index(ANCHOR) + len(ANCHOR)
    match = re.compile(r"(?:^> .*\n)+", re.MULTILINE).match(text, start)
    if match is None:
        print("*** no blockquote block follows the anchor -- refusing")
        return 1

    old = match.group(0)
    print(f"old blockquote lines      {old.count(chr(10))}")
    print(f"old blockquote chars      {len(old)}")
    print(f"sealed note chars         {len(note)}")

    text = text[:match.start()] + "> " + note + "\n" + text[match.end():]
    REPORT.write_text(text, encoding="utf-8", newline="\n")

    written = REPORT.read_text(encoding="utf-8")
    verbatim = note in written
    backtick_free = "`no_candidate_path` applies" not in written
    print()
    print(f"sealed note verbatim      {verbatim}")
    print(f"altered quotation gone    {backtick_free}")
    print(f"report bytes              {REPORT.stat().st_size}")
    print()
    print("RESULT " + ("OK" if verbatim and backtick_free else "FAILED"))
    return 0 if (verbatim and backtick_free) else 1


if __name__ == "__main__":
    sys.exit(main())
