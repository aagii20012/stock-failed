"""How does each required carrier actually hold the adaptation disclosure? ASCII output only.

The sealed string is never printed -- only digests, lengths and the shape of the difference.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "stockedge100"

protocol = json.loads((ROOT / "config/generation_2/g2_rotation_ra1_protocol.json")
                      .read_text(encoding="utf-8"))
sealed = protocol["adaptation_disclosure_verbatim"]
req = protocol["adaptation_disclosure_carriage_requirement"]

print("=== the sealed carriage requirement, in full ===")
for k, v in req.items():
    if isinstance(v, list):
        print("  %s:" % k)
        for item in v:
            print("      %s" % item)
    else:
        print("  %s: %s" % (k, v))

print()
print("=== how each carrier holds it ===")


def unwrap(text: str) -> str:
    """Undo Markdown blockquote hard-wrapping: a newline plus optional '>' plus indent -> one space."""
    return re.sub(r"\n>?[ \t]*", " ", text)


for rel in req["must_appear_verbatim_in"]:
    path = ROOT / rel
    print()
    print("  %s" % rel)
    if not path.is_file():
        print("      NOT ON DISK (written by the build itself)")
        continue
    raw = path.read_text(encoding="utf-8")
    if rel.endswith(".json"):
        decoded = json.dumps(json.loads(raw), ensure_ascii=False)
        print("      verbatim in decoded JSON        : %s" % (sealed in decoded))
        continue
    print("      verbatim as a raw substring     : %s" % (sealed in raw))
    head = sealed[:40]
    if head not in raw:
        print("      opening fragment not found either -- carrier may hard-wrap from the start")
        flat = re.sub(r"\s+", " ", raw)
        print("      present after flattening ALL ws : %s" % (re.sub(r"\s+", " ", sealed) in flat))
        continue
    start = raw.index(head)
    # Take a generous window and unwrap it, then look for the sealed string inside.
    window = raw[start:start + len(sealed) + 200]
    print("      present after blockquote unwrap : %s" % (sealed in unwrap(window)))
    tail = sealed[-40:]
    if tail in unwrap(window):
        stored = window[:len(window)]
        # Measure the true stored length by walking forward until the unwrap matches.
        for n in range(len(sealed), len(sealed) + 200):
            if unwrap(raw[start:start + n]).rstrip() == sealed:
                print("      stored length                   : %d (sealed %d, +%d wrap chars)"
                      % (n, len(sealed), n - len(sealed)))
                print("      stored sha256                   : %s"
                      % hashlib.sha256(raw[start:start + n].encode("utf-8")).hexdigest())
                break
        else:
            print("      could not align the stored copy to the sealed string")
    print("      newlines in the stored copy     : %d" % window[:len(sealed) + 40].count("\n"))
    line = raw[:start].count("\n") + 1
    print("      starts at line                  : %d" % line)
    ctx = raw[max(0, start - 200):start].splitlines()[-3:]
    print("      preceding lines                 :")
    for c in ctx:
        print("          %s" % c.encode("ascii", "replace").decode()[:100])
