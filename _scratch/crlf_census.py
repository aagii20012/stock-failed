"""Byte-level CR/LF census of every sealed Generation 2 governance artifact.

A shell `grep -c $'\r'` reported a CR count exactly equal to each file's line
count, which is the signature of an empty pattern matching every line, not of a
genuine CRLF finding.  Count the bytes instead: b"\r\n" and bare b"\n" cannot be
confused with each other and cannot be faked by a quoting accident.

This matters because the Attempt 2 sealer writes its JSON with Path.write_text()
and no newline= argument, which on Windows translates every \n to \r\n.  If the
sealed artifacts are CRLF then that is the established on-disk convention and
Attempt 3 must match it deliberately; if they are LF then write_text() is not
doing what its default implies and the reason needs finding.  Either way the
answer has to be read off the bytes.
"""

import pathlib

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")

TARGETS = sorted(
    list((ROOT / "governance/generation_2").glob("*"))
    + list((ROOT / "config/generation_2").glob("*.json"))
    + [ROOT / "governance/STAGE_1_FREEZE.sha256"]
)

print("%-58s %9s %7s %7s %5s" % ("file", "bytes", "CRLF", "LF", "bareCR"))
print("-" * 92)
for p in TARGETS:
    if not p.is_file():
        continue
    b = p.read_bytes()
    crlf = b.count(b"\r\n")
    lf = b.count(b"\n")
    cr = b.count(b"\r")
    print("%-58s %9d %7d %7d %5d"
          % (p.relative_to(ROOT).as_posix(), len(b), crlf, lf, cr - crlf))

print()
print("A file is pure-LF when CRLF == 0 and bareCR == 0.")
print("A file is pure-CRLF when CRLF == LF and bareCR == 0.")
