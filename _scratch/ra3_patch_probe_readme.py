"""Locate every README anchor line by a short unique substring and print it as ASCII repr."""
import sys
from pathlib import Path

ROOT = Path.cwd()
if not (ROOT / "governance").is_dir():
    sys.exit("wrong cwd: %s" % ROOT)

LINES = (ROOT / "README.md").read_text(encoding="utf-8").split("\n")

PROBES = [
    ("heading", "open, and failing at Gate 3"),
    ("a2 gate row", "STAGE_3_G2_ATTEMPT_2_NO_CANDIDATE`)"),
    ("next stage row", "| Next authorized stage |"),
    ("link tail", "STAGE_3_G2_ROTATION_RA1_RESEARCH_REPORT.md)."),
    ("no expected income", "**No expected income, profit, or return is claimed"),
    ("preregistrations", "seals its partition and each of its"),
    ("scanned files", "scanned files"),
    ("nine modules", "attempt 1 modules"),
    ("verify block last line", "STAGE_3_G2_A2_ROTATION_RESEARCH.sha256"),
    ("five records", "records"),
    ("limitation count", "sets now, and all of them travel"),
    ("limitation pointer", "An engine cannot be more trustworthy than its inputs"),
    ("half tested", "unique minimum of 189 fills"),
    ("exposure ceiling", "not purely signal turnover"),
]

for label, needle in PROBES:
    hits = [i for i, ln in enumerate(LINES) if needle in ln]
    print("### %s  -- %d hit(s)" % (label, len(hits)))
    for i in hits:
        print("  L%d: %s" % (i + 1, repr(LINES[i]).encode("ascii", "backslashreplace").decode("ascii")))

print("### context: the verification fence and what follows")
i = [i for i, ln in enumerate(LINES) if "STAGE_3_G2_A2_ROTATION_RESEARCH.sha256" in ln][0]
for j in range(i - 8, i + 10):
    if 0 <= j < len(LINES):
        print("  L%d: %s" % (j + 1, repr(LINES[j]).encode("ascii", "backslashreplace").decode("ascii")))

print("### context: the half-tested bullet")
i = [i for i, ln in enumerate(LINES) if "unique minimum of 189 fills" in ln][0]
for j in range(i - 4, i + 4):
    if 0 <= j < len(LINES):
        print("  L%d: %s" % (j + 1, repr(LINES[j]).encode("ascii", "backslashreplace").decode("ascii")))

print("### context: the exposure-ceiling bullet and end of file")
i = [i for i, ln in enumerate(LINES) if "not purely signal turnover" in ln][0]
for j in range(i - 6, len(LINES)):
    print("  L%d: %s" % (j + 1, repr(LINES[j]).encode("ascii", "backslashreplace").decode("ascii")))
