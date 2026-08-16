"""Measure the protocol Markdown's stored copy of the adaptation disclosure exactly.

The sealed string is never printed. Only lengths, digests, marker shapes and booleans. ASCII only.

The dry-run harness took the LONGEST slice whose unwrapped-and-rstripped form equalled the sealed
string, which trails past the paragraph into the following blank line and inflates the count. The
honest measure is the SHORTEST slice that unwraps to the sealed string with no rstrip at all.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "stockedge100"

sealed = json.loads((ROOT / "config/generation_2/g2_rotation_ra1_protocol.json")
                    .read_text(encoding="utf-8"))["adaptation_disclosure_verbatim"]
md_rel = "governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.md"
md = (ROOT / md_rel).read_text(encoding="utf-8")

print("sealed length : %d" % len(sealed))
print("sealed sha256 : %s" % hashlib.sha256(sealed.encode("utf-8")).hexdigest())

start = md.index(sealed[:40])
UNWRAP = re.compile(r"\n>?[ \t]*")

exact = [n for n in range(len(sealed), len(sealed) + 128)
         if UNWRAP.sub(" ", md[start:start + n]) == sealed]
rstripped = [n for n in range(len(sealed), len(sealed) + 128)
             if UNWRAP.sub(" ", md[start:start + n]).rstrip() == sealed]

print()
print("slice lengths that unwrap EXACTLY to sealed     : %s" % exact)
print("slice lengths that unwrap to sealed after rstrip: %s" % rstripped)

n = exact[0] if exact else rstripped[0]
stored = md[start:start + n]
print()
print("stored length : %d  (sealed %d, +%d wrap characters)" % (n, len(sealed), n - len(sealed)))
print("stored sha256 : %s" % hashlib.sha256(stored.encode("utf-8")).hexdigest())

markers = re.findall(UNWRAP, stored)
print("inserted markers, by shape:")
for shape in sorted(set(markers)):
    print("    %-8r x %d" % (shape, markers.count(shape)))
print("total markers : %d   chars they occupy: %d   they replace %d spaces"
      % (len(markers), sum(len(m) for m in markers), len(markers)))
print("check: %d - %d + %d == %d -> %s"
      % (len(sealed), len(markers), sum(len(m) for m in markers), n,
         len(sealed) - len(markers) + sum(len(m) for m in markers) == n))

trail = md[start + n:start + n + 8]
print()
print("what follows the stored copy (escaped): %r" % trail)
print("first line of the stored copy is %d chars" % len(stored.split("\n", 1)[0]))
print("longest line in the stored copy is %d chars" % max(len(l) for l in stored.split("\n")))
