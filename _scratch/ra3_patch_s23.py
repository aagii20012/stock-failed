"""Repair section 23 of the Attempt 3 report template.

The template told the reader to verify this attempt's checksum record from ``stockedge100/governance``
and justified it with the freeze-record rule about bare filenames. Measured, in both directions:

    from governance/generation_2 : all five lines FAILED open or read
    from stockedge100/           : all five lines OK
    governance/STAGE_0_FREEZE.sha256          OK from governance/   (bare filenames)
    governance/STAGE_3_PREREGISTRATION.sha256 OK from stockedge100/ (root-relative), FAILS from governance/

The freeze records carry bare filenames; every pre-registration record, including this attempt's,
carries project-root-relative paths. Publishing the old command would have handed a reader a
reproduction step that fails on a clean tree.

Anchored replacement with refusal guards, same shape as ra3_patch_s18.py.
"""

from __future__ import annotations

from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent / "ra3_report_template.md"

OLD = """```bash
cd stockedge100/governance
sha256sum -c generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.sha256
```

Every path in this report is relative to the project root, `stockedge100/`. The freeze records use bare
filenames, so `sha256sum -c` must run from the directory holding the record; a failure from any other
working directory is an operator error and not an integrity failure.
"""

NEW = """```bash
cd stockedge100
sha256sum -c governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.sha256
```

Every path in this report is relative to the project root, `stockedge100/`, and so is every path inside
this attempt's checksum record — which is why that verification runs from `stockedge100/` and not from
the directory holding the record. The two conventions in this tree are not interchangeable, and both
were run in both directions before this sentence was written. `governance/STAGE_0_FREEZE.sha256` and
`governance/STAGE_1_FREEZE.sha256` carry bare filenames and verify only from `governance/`. Every
pre-registration record, this one included, carries project-root-relative paths and verifies only from
`stockedge100/`. Either one run from the wrong directory reports `FAILED open or read` on every line,
which is an operator error and not an integrity failure; the two are distinguishable in the output,
because a real integrity failure names the file and says `FAILED` without saying
`No such file or directory` first.
"""

text = TEMPLATE.read_text(encoding="utf-8")
if text.count(OLD) != 1:
    raise SystemExit("PATCH REFUSED: %d matches for the old block" % text.count(OLD))
if ("use bare" + chr(10) + "filenames, so") not in text:
    raise SystemExit("PATCH REFUSED: the template does not carry the wrong justification; already patched?")

patched = text.replace(OLD, NEW)
if "cd stockedge100/governance" in patched:
    raise SystemExit("PATCH REFUSED: the wrong working directory survives elsewhere")

TEMPLATE.write_bytes(patched.encode("utf-8"))
raw = patched.encode("utf-8")
print("template now %d bytes, %d lines, crlf %d (must be 0)"
      % (len(raw), len(patched.splitlines()), raw.count(b"\r\n")))
print("sha256sum lines now:")
for i, ln in enumerate(patched.splitlines(), 1):
    if "sha256sum" in ln or "cd stockedge100" in ln:
        print("  %4d  %s" % (i, ln))
