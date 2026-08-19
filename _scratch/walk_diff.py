"""Show the generated walk rows against the sealed Attempt 2 rows, side by side.

The generator asserts they are equal and the assertion failed on all nine rows,
which usually means a formatting convention differs rather than the arithmetic.
Print both so the difference is read off the page, not guessed at.
"""

import json
import pathlib
import re
from decimal import Decimal, ROUND_HALF_EVEN

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
EM = "\u2014"

P = json.loads((ROOT / "config/generation_2/g2_rotation_ra3_protocol.json")
               .read_text(encoding="utf-8"))
SEALED = (ROOT / "governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.md"
          ).read_text(encoding="utf-8")

COMP = P["risk_architecture"]["components"]
F_BASE = Decimal(str(COMP["RA3-1"]["value"]))
STOP = Decimal(str(COMP["RA3-3"]["value"]))
BREACH = Decimal("0.15")

A2 = json.loads((ROOT / "config/generation_2/g2_rotation_ra1_protocol.json")
                .read_text(encoding="utf-8"))
ra2_bands = A2["risk_architecture"]["components"]["RA2-4"]["bands"]
print("f_base=%s  stop=%s" % (F_BASE, STOP))
print("RA2 bands from CFG-3103:")
for b in ra2_bands:
    print("   %s" % json.dumps(b, ensure_ascii=False))

WALK = [(Decimal(str(b["dd_from"])),
         None if b["dd_to_exclusive"] is None else Decimal(str(b["dd_to_exclusive"])),
         (F_BASE * Decimal(str(b["scalar"]))).quantize(Decimal("0.000000001"),
                                                       rounding=ROUND_HALF_EVEN),
         str(b["band"])) for b in ra2_bands]


def pct(x, places="0.0001"):
    return (x * 100).quantize(Decimal(places), rounding=ROUND_HALF_EVEN)


equity, rows = Decimal(1), []
for trip in range(1, 41):
    dd_before = Decimal(1) - equity
    scalar, lab = next((s, l) for lo, hi, s, l in WALK
                       if dd_before >= lo and (hi is None or dd_before < hi))
    loss = scalar * STOP
    equity *= (Decimal(1) - loss)
    dd_after = Decimal(1) - equity
    rows.append((trip, dd_before, lab, scalar, loss, dd_after, dd_after >= BREACH))
    if dd_after >= BREACH:
        break

gen = []
for trip, dd_before, lab, scalar, loss, dd_after, breached in rows:
    after = ("**%s%% - breach**" % pct(dd_after)) if breached else "%s%%" % pct(dd_after)
    gen.append("| %d | %s%% | %s | %s | %s%% | %s |"
               % (trip, pct(dd_before), lab, scalar, pct(loss, "0.000"), after))

block = re.search(r"\| Trip \| `dd` before \|.*?\n\n", SEALED, re.S).group(0)
sealed = [ln.replace(EM, "-") for ln in block.splitlines()
          if ln.startswith("| ") and not ln.startswith("| Trip")]

print("\nsealed block header lines:")
for ln in block.splitlines()[:3]:
    print("   %r" % ln)

print("\n%-4s %s" % ("", "GEN  vs  SEALED"))
for i in range(max(len(gen), len(sealed))):
    g = gen[i] if i < len(gen) else "<none>"
    s = sealed[i] if i < len(sealed) else "<none>"
    print("%-4s %s\n     %s   %s" % (i + 1, g, s, "OK" if g == s else "<<< DIFFERS"))
