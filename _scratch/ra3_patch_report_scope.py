"""Add the sealed resolved gating scope to the research report's section 14 Scope paragraph.

The report quoted the two halves of G2A2-CONFLICT-25 correctly but never stated its resolution, so the
`#STRESS` column of the `S3-C7` row read as gating when the decision record marks it
reported-not-gating. The strict dry-run surfaced the mismatch: the builder assembles
`gating_runs=['#BASE']` for `S3-C7` alone.

The resolution is quoted off disk from the sealed criteria, not restated.

Safe to run: `governance/generation_2/*.md` is outside the `repo_state_id` patterns
(`governance/*` is single-level), the report's digest is recorded nowhere yet, and the evidence
references the report only as a disclosure carrier. The one thing that must not move is the
1507-character disclosure on line 106, which the builder holds to byte-equality.
"""

import hashlib
import json
import sys
import textwrap
from pathlib import Path

ROOT = Path.cwd()
if not (ROOT / "governance").is_dir():
    sys.exit("wrong cwd: %s" % ROOT)

R = ROOT / "governance/generation_2/STAGE_3_G2_ROTATION_RA3_RESEARCH_REPORT.md"
data = R.read_bytes()
if b"\r\n" in data:
    sys.exit("report carries CRLF; refusing to touch it")
text = data.decode("utf-8")
L = text.split("\n")

# the disclosure line is held to byte-equality by the builder; assert it survives untouched
EV = json.loads((ROOT / "reports/stage3_g2_attempt3/"
                 "STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json").read_text(encoding="utf-8"))
DISCLOSURE = EV["adaptation_disclosure_verbatim"]
if text.count(DISCLOSURE) != 1:
    sys.exit("the disclosure appears %d times in the report, expected 1" % text.count(DISCLOSURE))

# quote the resolution from the sealed criteria rather than restating it
CRIT = json.loads((ROOT / "config/generation_2/g2_gate_criteria_ra3.json").read_text(encoding="utf-8"))
CONF = [c for c in CRIT["conflicts_found"] if c.get("id") == "G2A2-CONFLICT-25"]
if len(CONF) != 1:
    sys.exit("found %d sealed G2A2-CONFLICT-25 entries, expected 1" % len(CONF))
QUOTE = CONF[0]["resolution"].split(". ")[1].strip() + "."
if not QUOTE.startswith("Admission requires all seven conditions"):
    sys.exit("the sealed resolution's second sentence is %r" % QUOTE[:90])

OLD = [
    "reported-but-not-gating for `S3-C1` and `S3-C4`. Neither outranks the other, so the more restrictive",
    "reading governs and both readings are reported. Here they agree: the permissive base-only reading would",
]
hits = [j for j, ln in enumerate(L) if ln == OLD[0]]
if len(hits) != 1:
    sys.exit("the first anchor matched %d lines, expected 1" % len(hits))
i = hits[0]
if L[i + 1] != OLD[1]:
    sys.exit("L%d is %r, not the second anchor" % (i + 2, L[i + 1]))

# the sealed sentence is 103 characters on its own, so the replacement is written as one paragraph
# and rewrapped to the width the surrounding prose already uses. Markdown renders a single newline
# as a space, so wrapping changes nothing a reader sees and nothing the builder checks -- only
# line 106 is held to byte-equality.
LEAD = (
    "reported-but-not-gating for `S3-C1` and `S3-C4`. Neither outranks the other, so the more "
    "restrictive reading governs and both readings are reported. The resolved scope, quoted from "
    "`SE100-CFG-3106`'s own entry for this conflict, is:"
)
TAIL = (
    "The `#STRESS` column of the `S3-C7` row above is therefore reported, not gating; it is the only "
    "row of the seven where that is so, and the decision record carries the distinction per row as "
    "`gating_runs` and `reported_not_gating`. `S3-C7` is `MET` on both runs in any case, so nothing "
    "in the verdict turns on it. The two readings agree here as well: the permissive base-only "
    "reading would"
)
# the quotation occupies a line of its own so that it stays contiguous and greppable -- rewrapping it
# would break the one string a reader might want to match against the sealed file. It is 103
# characters, which fits the width the surrounding prose already uses.
if len(QUOTE) > 104:
    sys.exit("the sealed sentence is %d chars and no longer fits one line" % len(QUOTE))
W = dict(width=104, break_long_words=False, break_on_hyphens=False)
NEW = textwrap.wrap(LEAD, **W) + [QUOTE] + textwrap.wrap(TAIL, **W)
if " ".join(NEW) != LEAD + " " + QUOTE + " " + TAIL:
    sys.exit("rewrapping altered the paragraph")
L[i:i + 2] = NEW
patched = "\n".join(L)

if patched.count(DISCLOSURE) != 1:
    sys.exit("the patch disturbed the disclosure carrier")
if chr(13) in patched:
    sys.exit("carriage return in the patched text")
for must in (QUOTE, "`gating_runs`", "`reported_not_gating`",
             "give `STAGE_3_G2_ATTEMPT_3_NO_CANDIDATE`. `G2A2-CONFLICT-25`, inherited"):
    if must not in patched:
        sys.exit("missing after patch: %r" % must[:70])
if patched.count(QUOTE) != 1:
    sys.exit("the quoted resolution appears %d times" % patched.count(QUOTE))
over = [(j + 1, len(ln)) for j, ln in enumerate(L[i:i + len(NEW)], start=i) if len(ln) > 119]
if over:
    sys.exit("over-wide lines: %s" % over)

R.write_text(patched, encoding="utf-8", newline="\n")
out = R.read_bytes()
if b"\r\n" in out:
    sys.exit("the written report carries CRLF")
print("patched the section 14 Scope paragraph")
print("  bytes  %d -> %d" % (len(data), len(out)))
print("  lines  %d -> %d" % (len(L) - len(NEW) + 2, len(L)))
print("  sha256 %s..." % hashlib.sha256(data).hexdigest()[:16])
print("      -> %s" % hashlib.sha256(out).hexdigest())
print("  CRLF   %d" % out.count(b"\r\n"))
print("  quoted %d chars from the sealed resolution" % len(QUOTE))
