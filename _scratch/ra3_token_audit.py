"""Audit the Attempt 3 report template's tokens against the scalars the tables emitter produced.

Three questions, answered before a line of renderer is written:

* which ``@@S:NAME@@`` tokens have no backing ``NAME = value`` line in ``_ra3_tables.txt``;
* which scalars the emitter produced that the template never uses (dead weight, or a renamed token);
* which ``### heading`` sections exist, so the TABLES map can be written against measured names.
"""

from __future__ import annotations

import re
from pathlib import Path

SCRATCH = Path(__file__).resolve().parent
TEMPLATE = SCRATCH / "ra3_report_template.md"
TABLES = SCRATCH / "_ra3_tables.txt"

tables_text = TABLES.read_text(encoding="utf-8")
lines = tables_text.splitlines()

headings = [(i + 1, ln) for i, ln in enumerate(lines) if ln.startswith("### ")]

# The scalars section runs from its heading to the next heading or EOF.
start = next(i for i, ln in enumerate(lines) if ln == "### scalars")
end = len(lines)
for i in range(start + 1, len(lines)):
    if lines[i].startswith("### "):
        end = i
        break

scalars = {}
malformed = []
for ln in lines[start + 1 : end]:
    if not ln.strip():
        continue
    match = re.match(r"^([A-Z0-9_]+) = (.*)$", ln)
    if not match:
        malformed.append(ln)
        continue
    scalars[match.group(1)] = match.group(2)

template = TEMPLATE.read_text(encoding="utf-8")
used = sorted(set(re.findall(r"@@S:([A-Za-z0-9_]+)@@", template)))
tables_used = sorted(set(re.findall(r"@@TABLE_([A-Za-z0-9_]+)@@", template)))
bare = sorted(set(re.findall(r"@@([A-Z][A-Za-z0-9_]*)@@", template)))

print("=== tables file ===")
print("lines %d   sections %d   scalars parsed %d   malformed %d"
      % (len(lines), len(headings), len(scalars), len(malformed)))
for ln in malformed:
    print("  MALFORMED: %r" % ln)
print()
for num, ln in headings:
    print("  %4d  %s" % (num, ln))

print()
print("=== @@S:NAME@@ tokens: %d distinct ===" % len(used))
missing = [name for name in used if name not in scalars]
print("with no backing scalar (%d):" % len(missing))
for name in missing:
    print("  MISSING  %s" % name)

print()
unused = sorted(name for name in scalars if name not in used)
print("=== scalars emitted but unused by the template (%d) ===" % len(unused))
for name in unused:
    value = scalars[name].encode("ascii", "backslashreplace").decode("ascii")
    print("  %-34s %s" % (name, value[:70]))

print()
print("=== @@TABLE_X@@ tokens: %d ===" % len(tables_used))
print("  " + " ".join(tables_used))
print()
print("=== bare @@NAME@@ tokens: %d ===" % len(bare))
print("  " + " ".join(bare))
