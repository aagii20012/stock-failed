"""Locate exactly how the protocol Markdown's copy of the adaptation disclosure differs.

The sealed string is never printed. Only lengths, digests and character-class positions surface --
the seal's encoding_note forbids writing it to a cp1252 console. ASCII output only.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "stockedge100"

protocol = json.loads((ROOT / "config/generation_2/g2_rotation_ra1_protocol.json")
                      .read_text(encoding="utf-8"))
sealed = protocol["adaptation_disclosure_verbatim"]
req = protocol["adaptation_disclosure_carriage_requirement"]

print("sealed length      : %d" % len(sealed))
print("sealed sha256      : %s" % hashlib.sha256(sealed.encode("utf-8")).hexdigest())
print("carriers required  :")
for rel in req["must_appear_verbatim_in"]:
    print("    %s" % rel)

md_rel = "governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.md"
md = (ROOT / md_rel).read_text(encoding="utf-8")
print()
print("%s: %d characters" % (md_rel, len(md)))
print("contains sealed verbatim: %s" % (sealed in md))

# Find the region that was meant to be the carrier, using a distinctive opening fragment.
head = sealed[:40]
print("opening fragment present: %s" % (head in md))
if head not in md:
    # Fall back to a whitespace-insensitive search so the region can still be located.
    flat_md = re.sub(r"\s+", " ", md)
    flat_sealed = re.sub(r"\s+", " ", sealed)
    print("whitespace-flattened match: %s" % (flat_sealed in flat_md))
    idx = flat_md.find(flat_sealed[:40])
    print("flattened opening at index: %s" % idx)
    if idx >= 0:
        print("  -> the text IS present but its whitespace differs (line wrapping)")
    raise SystemExit(0)

start = md.index(head)
region = md[start:start + len(sealed)]
print("region length      : %d" % len(region))
print("region sha256      : %s" % hashlib.sha256(region.encode("utf-8")).hexdigest())

flat_region = re.sub(r"\s+", " ", region)
flat_sealed = re.sub(r"\s+", " ", sealed)
print()
print("whitespace-insensitive equal: %s" % (flat_region == flat_sealed))
if flat_region == flat_sealed:
    print("  -> the ONLY difference is whitespace: the Markdown hard-wraps the paragraph.")

print()
print("character-level differences (positions and unicode names, never the text):")
sm = difflib.SequenceMatcher(None, sealed, region, autojunk=False)
shown = 0
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == "equal":
        continue
    shown += 1
    if shown > 12:
        print("    ... more")
        break

    def describe(seg: str) -> str:
        out = []
        for ch in seg[:6]:
            try:
                name = unicodedata.name(ch)
            except ValueError:
                name = "U+%04X" % ord(ch)
            out.append(name)
        return "[%s]%s" % ("; ".join(out), " ..." if len(seg) > 6 else "")

    print("    %-8s sealed[%d:%d] %s" % (tag, i1, i2, describe(sealed[i1:i2])))
    print("             file  [%d:%d] %s" % (j1, j2, describe(region[j1:j2])))

print()
print("newline count in region : %d" % region.count("\n"))
print("newline count in sealed : %d" % sealed.count("\n"))
