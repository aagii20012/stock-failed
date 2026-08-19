"""Render the Attempt 3 test summary, measuring every count rather than transcribing it.

Copied from ``_scratch/g2a2_render_test_summary.py`` and adapted in four places: two new test files
instead of one, thirteen sealed adversarial requirements instead of nine, the prior floor is Attempt
2's rather than Attempt 1's, and the control/non-vacuity tests are enumerated from the collected ids
instead of being summarised in a sentence.

Every figure below is measured. The renderer refuses rather than substituting a number it cannot
confirm, so a stale template placeholder or a drifted count fails here instead of reaching the
summary.

ASCII output only.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

SCRATCH = Path(__file__).resolve().parent
ROOT = SCRATCH.parent / "stockedge100"
TEMPLATE = SCRATCH / "ra3_test_summary_template.md"
CAPTURE = ROOT / "reports/stage3_g2_attempt3/pytest_stage3_g2_attempt3_output.txt"
A2_SUMMARY = ROOT / "reports/stage3_g2_attempt2/STAGE_3_G2_A2_TEST_SUMMARY.md"
A2_MANIFEST = ROOT / "reports/stage3_g2_attempt2/STAGE_3_G2_A2_ARTIFACT_MANIFEST.json"
PROTOCOL = json.loads(
    (ROOT / "config/generation_2/g2_rotation_ra3_protocol.json").read_text(encoding="utf-8"))
OUT = ROOT / "reports/stage3_g2_attempt3/STAGE_3_G2_A3_TEST_SUMMARY.md"

NEW_FILES = [
    "tests/adversarial/test_g2_ra3_risk_architecture.py",
    "tests/adversarial/test_g2_sel2_selection_rule.py",
]
A2_FLOOR_EXPECTED = 1142
WORDS = {9: "nine", 10: "ten", 11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen"}


def check(condition, message):
    if not condition:
        raise SystemExit("RENDER REFUSED: %s" % message)


# --- collect, grouped by file -------------------------------------------------------------------
proc = subprocess.run([sys.executable, "-m", "pytest", "tests", "--collect-only", "-q"],
                      cwd=str(ROOT), capture_output=True, text=True)
per_file = {}
ids_by_file = {}
order = []
for line in proc.stdout.splitlines():
    line = line.strip()
    if "::" not in line or not line.startswith("tests/"):
        continue
    path, test_id = line.split("::", 1)
    if path not in per_file:
        per_file[path] = 0
        ids_by_file[path] = []
        order.append(path)
    per_file[path] += 1
    ids_by_file[path].append(test_id)
check(bool(per_file), "collection produced no test ids")

collected = re.search(r"^(\d+) tests collected", proc.stdout.strip().splitlines()[-1])
check(collected is not None, "could not parse the collection total")
total = int(collected.group(1))
check(sum(per_file.values()) == total,
      "per-file counts sum to %d but collection reports %d" % (sum(per_file.values()), total))

for rel in NEW_FILES:
    check(rel in per_file, "the new Attempt 3 test file %s is not in the collection" % rel)
new_tests = sum(per_file[rel] for rel in NEW_FILES)
prior = total - new_tests
check(prior == A2_FLOOR_EXPECTED,
      "derived prior floor %d does not match Attempt 2's recorded %d" % (prior, A2_FLOOR_EXPECTED))

# Attempt 2's own summary must still say what we are crediting it with -- read it, do not assume.
a2_text = A2_SUMMARY.read_text(encoding="utf-8")
check("| **Total** | **%d** |" % prior in a2_text,
      "Attempt 2's summary does not record a total of %d" % prior)

# --- the captured run ---------------------------------------------------------------------------
capture = CAPTURE.read_text(encoding="utf-8")
summary = re.search(r"^(\d+) failed, (\d+) passed in ([0-9.]+)s", capture, re.M)
check(summary is not None, "could not parse the pytest summary line")
failed, passed = int(summary.group(1)), int(summary.group(2))
check(failed + passed == total,
      "the capture totals %d, collection totals %d" % (failed + passed, total))
check(failed == 1, "expected exactly one failure, the inherited red marker")

failing = [l.strip() for l in capture.splitlines() if l.startswith("FAILED ")]
check(len(failing) == 1, "expected exactly one FAILED line, found %d" % len(failing))
check("test_stage4_preregistration.py" in failing[0],
      "the failing test is not the inherited Stage 4 marker: %s" % failing[0])

# --- the composition table ----------------------------------------------------------------------
NEW_NOTE = {
    NEW_FILES[0]: ("**New.** RA3's five risk components and the sealed requirements `AT-A` ... `AT-H`, "
                   "`AT-L` and `AT-M`, each section opening with a control and closing with an "
                   "injected defect that must be caught."),
    NEW_FILES[1]: ("**New.** `SE100-G2-SEL-2`'s return-blindness, edge-correct neighbour "
                   "identification and determinism — the sealed requirements `AT-I`, `AT-J` and "
                   "`AT-K`."),
}
rows = ["| File | Tests | What it establishes |", "| --- | ---: | --- |"]
for path in order:
    if path in NEW_NOTE:
        note = NEW_NOTE[path]
    elif "test_g2_ra1_risk_architecture" in path:
        note = "Generation 2 Attempt 2 floor. **Unmodified.**"
    elif "test_g2_" in path:
        note = "Generation 2 Attempt 1 floor. **Unmodified.**"
    elif "test_stage4_preregistration" in path:
        note = "Generation 1 floor. **Unmodified**, including the one red marker."
    else:
        note = "Generation 1 floor. **Unmodified.**"
    rows.append("| `%s` | %d | %s |" % (path, per_file[path], note))
rows.append("| **Total** | **%d** | %d passed, %d failed by design |" % (total, passed, failed))
table = "\n".join(rows)

# --- the thirteen declared adversarial tests ------------------------------------------------------
# The wording is the protocol's, pasted from disk; the count and the file beside it are measured from
# the ids the collector actually produced. Neither is typed here.
requirements = PROTOCOL["adversarial_test_requirements"]
keys = sorted(k for k in requirements if re.fullmatch(r"AT-[A-Z]", k))
check(len(keys) == 13, "expected thirteen declared adversarial tests, found %d" % len(keys))
check("regression_floor" in requirements, "the sealed regression_floor item is missing")

bullets = []
attributed = 0
at_ids = {rel: set() for rel in NEW_FILES}
for key in keys:
    prefix = "test_at_%s_" % key[-1].lower()
    homes = {rel: [i for i in ids_by_file[rel] if i.startswith(prefix)] for rel in NEW_FILES}
    hits = {rel: ids for rel, ids in homes.items() if ids}
    check(hits, "no test in either new file implements %s" % key)
    check(len(hits) == 1,
          "%s is split across %s; the bullet cannot name one file" % (key, sorted(hits)))
    rel, ids = next(iter(hits.items()))
    at_ids[rel].update(ids)
    attributed += len(ids)
    wording = " ".join(str(requirements[key]).split())
    bullets.append("- **`%s`** — %d tests in `%s`. Sealed requirement: %s"
                   % (key, len(ids), Path(rel).name, wording))
at_list = "\n".join(bullets)

# --- the controls and non-vacuity gates, enumerated -----------------------------------------------
control_lines = []
harness = 0
for rel in NEW_FILES:
    leftover_ids = [i for i in ids_by_file[rel] if i not in at_ids[rel]]
    check(leftover_ids, "%s attributes every test to an AT group, so it has no control" % rel)
    check(all(i.startswith("test_control_") or i.startswith("test_gate_") for i in leftover_ids),
          "unclassified tests in %s: %s" % (rel, [i for i in leftover_ids
                                                 if not i.startswith(("test_control_", "test_gate_"))]))
    harness += len(leftover_ids)
    control_lines.append("`%s`:" % Path(rel).name)
    control_lines.append("")
    for i in sorted(leftover_ids):
        control_lines.append("- `%s`" % i)
    control_lines.append("")
controls = "\n".join(control_lines).rstrip()
check(attributed + harness == new_tests,
      "attributed %d + controls %d != new tests %d" % (attributed, harness, new_tests))

# --- "unmodified" is re-hashed, not asserted -----------------------------------------------------
# Attempt 2's artifact manifest recorded a digest for every path under tests/ that existed when its
# package was built. Re-hash each one now; the claim in the prose is exactly this loop's result.
recorded = json.loads(A2_MANIFEST.read_text(encoding="utf-8"))["repo_state_files"]
prior_files = sorted(k for k in recorded if k.startswith("tests/"))
check(len(prior_files) > 1, "Attempt 2's manifest recorded no test files to re-hash")
check("tests/conftest.py" in prior_files,
      "conftest.py is not in the re-hashed set, so the summary must not claim it is verified")
moved = []
for rel in prior_files:
    entry = recorded[rel]
    digest = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
    if digest != (entry if isinstance(entry, str) else entry["sha256"]):
        moved.append(rel)
check(not moved, "these files Attempt 2 recorded have changed: %s" % ", ".join(moved))
for rel in NEW_FILES:
    check(rel not in recorded,
          "the 'new' file %s was already in Attempt 2's manifest; it is not new" % rel)

new_block = "\n".join("%-52s %3d" % (rel, per_file[rel]) for rel in NEW_FILES)

substitutions = {
    "@@TABLE_COMPOSITION@@": table,
    "@@LIST_AT@@": at_list,
    "@@LIST_CONTROLS@@": controls,
    "@@AT_COUNT_WORD@@": WORDS[len(keys)],
    "@@AT_ATTRIBUTED@@": str(attributed),
    "@@HARNESS@@": str(harness),
    "@@PRIOR_FILES_VERIFIED@@": str(len(prior_files)),
    "@@PASSED@@": str(passed),
    "@@FAILED@@": str(failed),
    "@@TOTAL@@": str(total),
    "@@PRIOR@@": str(prior),
    "@@NEW@@": str(new_tests),
    "@@NEW_FILE_COUNT@@": WORDS.get(len(NEW_FILES), str(len(NEW_FILES))) if len(NEW_FILES) > 8 else "two",
    "@@NEW_FILES_BLOCK@@": new_block,
    "@@FAILING@@": failing[0][len("FAILED "):].split(" ")[0],
}

text = TEMPLATE.read_text(encoding="utf-8")
for token, value in substitutions.items():
    check(token in text, "template does not use %s" % token)
    text = text.replace(token, value)
leftover = [l for l in text.splitlines() if "@@" in l]
check(not leftover, "unsubstituted placeholder: %r" % (leftover[0] if leftover else ""))

# No tree digest and no self digest may appear in a governance-adjacent artifact; this one needs no
# digest at all, so the honest predicate is that it carries none.
hexes = re.findall(r"\b[0-9a-f]{64}\b", text)
check(not hexes, "the test summary carries a 64-hex digest: %s" % hexes[:2])

OUT.write_text(text, encoding="utf-8", newline="\n")
raw = OUT.read_bytes()
print("wrote reports/stage3_g2_attempt3/%s" % OUT.name)
print("  collected %d across %d files" % (total, len(per_file)))
print("  %d passed, %d failed" % (passed, failed))
print("  prior floor %d + new %d = %d" % (prior, new_tests, total))
print("  AT-attributed %d + controls %d = %d" % (attributed, harness, new_tests))
print("  re-hashed %d tests/ paths from Attempt 2's manifest, 0 moved" % len(prior_files))
print("  failing: %s" % substitutions["@@FAILING@@"])
print("  bytes %d, lines %d, crlf %d, lf %d"
      % (len(raw), text.count("\n"), raw.count(b"\r\n"), raw.count(b"\n")))
