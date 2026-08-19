"""Remove the sentence the exposure-ceiling edit duplicated.

The edit anchored on the last line of the bullet and re-emitted the wrapped line before it, so
"The related `SC-4` disclosure applies to the tiebreak itself - fill count includes stop and throttle
legs, so a variant whose risk architecture intervened less..." now appears twice. Drop the two added
lines and restore the single original tail line.
"""
import sys
from pathlib import Path

ROOT = Path.cwd()
if not (ROOT / "governance").is_dir():
    sys.exit("wrong cwd: %s" % ROOT)

EM = chr(0x2014)
README = ROOT / "README.md"
data = README.read_bytes()
if b"\r\n" in data:
    sys.exit("README.md carries CRLF; refusing to touch it")
LINES = data.decode("utf-8").split("\n")
BEFORE = len(LINES)

DUP = "  tiebreak itself " + EM + " fill count includes stop and throttle legs, so a variant whose risk"
TAIL = "  architecture intervened less has an advantage in step 2 that is not purely signal turnover."
ORIGINAL_TAIL = "  intervened less has an advantage in step 2 that is not purely signal turnover."

hits = [i for i, ln in enumerate(LINES) if ln == DUP]
if len(hits) != 1:
    sys.exit("the duplicated line matched %d times, expected 1" % len(hits))
i = hits[0]
if LINES[i + 1] != TAIL:
    sys.exit("L%d is %r, not the expected continuation" % (i + 2, LINES[i + 1]))
# the line before must be the original wrap, i.e. the sentence really is stated twice
if not LINES[i - 1].endswith("so a variant whose risk architecture"):
    sys.exit("L%d is %r, so the sentence is not duplicated after all" % (i, LINES[i - 1]))

LINES[i:i + 2] = [ORIGINAL_TAIL]

text = "\n".join(LINES)
sentence = "fill count includes stop and throttle legs"
if text.count(sentence) != 1:
    sys.exit("the sentence still occurs %d times" % text.count(sentence))
for must in ("Attempt 3 measures the same deviation under RA3",
             "The related `SC-4` disclosure applies to the",
             "could not have fixed it."):
    if must not in text:
        sys.exit("repair dropped: %r" % must)
if chr(13) in text:
    sys.exit("carriage return in the repaired text")

README.write_text(text, encoding="utf-8", newline="\n")
out = README.read_bytes()
if b"\r\n" in out:
    sys.exit("the written README carries CRLF")
print("repaired README.md")
print("  bytes %d -> %d" % (len(data), len(out)))
print("  lines %d -> %d" % (BEFORE, len(LINES)))
