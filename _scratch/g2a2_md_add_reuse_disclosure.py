"""Insert the mandated validation-reuse disclosure into the Attempt 2 protocol Markdown.

Partition lock binding rule 7: "The section 2 disclosure text is reproduced verbatim wherever the
validation window is referenced." Section 14's window table references it, and the document carried
only the *adaptation* disclosure. The sealer's document check caught the omission before the seal;
this repairs it.

The text is built from the sealed constant and wrapped, never hand-typed. An earlier draft of the
adaptation disclosure lost an em dash to an ASCII hyphen that way, and "verbatim" survives exactly
one such substitution before it means nothing. Bytes are written directly so that Windows text-mode
newline translation cannot turn 978 LF endings into CRLF and silently move every future digest.
"""
from __future__ import annotations

import pathlib
import sys
import textwrap

ROOT = pathlib.Path(__file__).resolve().parents[1] / "stockedge100"
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.reporting.g2_partition_lock import (  # noqa: E402
    VALIDATION_REUSE_DISCLOSURE,
    normalised_prose,
)

MD = ROOT / "governance" / "generation_2" / "STAGE_3_G2_ROTATION_RA1_PROTOCOL.md"

ANCHOR = "(`G2A2-CONFLICT-6`.)\n"
OLD_HEADING = "## 14. Windows referenced, and the mandated adaptation disclosure\n"
NEW_HEADING = "## 14. Windows referenced, and the two mandated disclosures\n"

PREAMBLE = """
### 14.2 The validation-reuse disclosure

The window table above references Generation 2's validation window. Binding rule 7 of
[STAGE_1_G2_PARTITION_LOCK.md](STAGE_1_G2_PARTITION_LOCK.md) requires that the disclosure sealed in
its §2 be reproduced verbatim wherever that window is referenced, so it is reproduced here. It is a
disclosure about a window this attempt does not read; carrying it is not an authorization to read it.

"""

text = MD.read_text(encoding="utf-8")

if normalised_prose(VALIDATION_REUSE_DISCLOSURE) in normalised_prose(text):
    print("REFUSED: the disclosure is already present. Nothing changed.")
    raise SystemExit(2)
if text.count(ANCHOR) != 1:
    print("REFUSED: expected exactly one %r anchor, found %d" % (ANCHOR, text.count(ANCHOR)))
    raise SystemExit(3)
if text.count(OLD_HEADING) != 1:
    print("REFUSED: section 14's heading is not what this script expects.")
    raise SystemExit(3)

quote = "\n".join(
    "> " + line for line in textwrap.wrap(VALIDATION_REUSE_DISCLOSURE, width=98)
)
block = PREAMBLE + quote + "\n\n(Carried under partition lock binding rule 7.)\n"

updated = text.replace(OLD_HEADING, NEW_HEADING).replace(ANCHOR, ANCHOR + block, 1)

# The whole point of the edit is byte-fidelity of the quoted text; verify it before writing, not
# after, and verify the two things that a wrap could plausibly break.
flat_new = normalised_prose(updated)
assert normalised_prose(VALIDATION_REUSE_DISCLOSURE) in flat_new, "the wrap broke the disclosure"
assert updated.count("—") == text.count("—") + VALIDATION_REUSE_DISCLOSURE.count("—"), "em dash lost"
assert updated.count("≈") == text.count("≈") + VALIDATION_REUSE_DISCLOSURE.count("≈"), "approx lost"
assert normalised_prose(
    [ln for ln in text.splitlines() if "designed after Attempt 1" in ln][0]
) in flat_new, "the adaptation disclosure was disturbed"
assert "\r" not in updated, "a CR entered the document"
assert len(updated) > len(text), "nothing was inserted"

MD.write_bytes(updated.encode("utf-8"))

longest = max((len(ln) for ln in block.splitlines()), default=0)
print("Inserted section 14.2 into %s" % MD.name)
print("  lines %d -> %d" % (len(text.splitlines()), len(updated.splitlines())))
print("  longest inserted line: %d columns" % longest)
print("  section 14 retitled to: %s" % NEW_HEADING.strip())
print("  disclosure present verbatim: True")
