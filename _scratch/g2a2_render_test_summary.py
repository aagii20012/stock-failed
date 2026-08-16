"""Render the Attempt 2 test summary, measuring every count rather than transcribing it.

The composition table is built from a real ``pytest --collect-only`` run, grouped by file, so a row
cannot drift from the suite. The pass/fail line is parsed from the captured run. Attempt 1's floor is
derived as (total - new) and cross-checked against the figure Attempt 1 recorded, so a disagreement
fails the render instead of reaching the summary.

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
TEMPLATE = SCRATCH / "g2a2_test_summary_template.md"
COUNTS = json.loads((SCRATCH / "g2a2_test_counts.json").read_text(encoding="utf-8"))
CAPTURE = ROOT / "reports/stage3_g2_attempt2/pytest_stage3_g2_attempt2_output.txt"
A1_SUMMARY = ROOT / "reports/stage3_g2/STAGE_3_G2_TEST_SUMMARY.md"
PROTOCOL = json.loads(
    (ROOT / "config/generation_2/g2_rotation_ra1_protocol.json").read_text(encoding="utf-8"))
OUT = ROOT / "reports/stage3_g2_attempt2/STAGE_3_G2_A2_TEST_SUMMARY.md"

NEW_FILE = COUNTS["new_test_file"]


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

check(NEW_FILE in per_file, "the new Attempt 2 test file is not in the collection")
check(per_file[NEW_FILE] == COUNTS["new_tests_collected"],
      "the new file now collects %d tests, not the recorded %d"
      % (per_file[NEW_FILE], COUNTS["new_tests_collected"]))
new_tests = per_file[NEW_FILE]
prior = total - new_tests
check(prior == COUNTS["attempt_1_floor_expected"],
      "derived prior floor %d does not match Attempt 1's recorded %d"
      % (prior, COUNTS["attempt_1_floor_expected"]))

# Attempt 1's own summary must still say what we are crediting it with -- read it, do not assume.
a1_text = A1_SUMMARY.read_text(encoding="utf-8")
check("| **Total** | **%d** |" % prior in a1_text,
      "Attempt 1's summary does not record a total of %d" % prior)

# --- the captured run ---------------------------------------------------------------------------
capture = CAPTURE.read_text(encoding="utf-8", errors="replace")
summary = re.search(r"^(\d+) failed, (\d+) passed in ([0-9.]+)s", capture, re.M)
check(summary is not None, "could not parse the pytest summary line")
failed, passed = int(summary.group(1)), int(summary.group(2))
check(failed + passed == total, "the capture totals %d, collection totals %d" % (failed + passed, total))
check(failed == 1, "expected exactly one failure, the inherited red marker")

failing = [l.strip() for l in capture.splitlines() if l.startswith("FAILED ")]
check(len(failing) == 1, "expected exactly one FAILED line, found %d" % len(failing))
check("test_stage4_preregistration.py" in failing[0],
      "the failing test is not the inherited Stage 4 marker: %s" % failing[0])

# --- the composition table ----------------------------------------------------------------------
rows = ["| File | Tests | What it establishes |", "| --- | ---: | --- |"]
for path in order:
    if path == NEW_FILE:
        note = ("**New.** The five risk-architecture mechanisms and the nine required adversarial "
                "tests `AT-A` ... `AT-I`, each section opening with a control and closing with an "
                "injected defect that must be caught.")
    elif "test_g2_" in path:
        note = "Generation 2 Attempt 1 floor. **Unmodified.**"
    elif "test_stage4_preregistration" in path:
        note = "Generation 1 floor. **Unmodified**, including the one red marker."
    else:
        note = "Generation 1 floor. **Unmodified.**"
    rows.append("| `%s` | %d | %s |" % (path, per_file[path], note))
rows.append("| **Total** | **%d** | %d passed, %d failed by design |" % (total, passed, failed))
table = "\n".join(rows)

# --- the nine declared adversarial tests ---------------------------------------------------------
# The wording is the protocol's, pasted from disk; the count beside it is measured from the ids the
# collector actually produced. Neither is typed here.
requirements = PROTOCOL["adversarial_test_requirements"]
keys = [k for k in requirements if re.fullmatch(r"AT-[A-I]", k)]
check(len(keys) == 9, "expected nine declared adversarial tests, found %d" % len(keys))

new_ids = ids_by_file[NEW_FILE]
bullets = []
attributed = 0
for key in keys:
    letter = key[-1].lower()
    n = sum(1 for i in new_ids if i.startswith("test_at_%s_" % letter))
    check(n > 0, "no test in the new file implements %s" % key)
    attributed += n
    wording = " ".join(str(requirements[key]).split())
    bullets.append("- **`%s`** — %d tests. Sealed requirement: %s" % (key, n, wording))
at_list = "\n".join(bullets)

# --- "unmodified" is re-hashed, not asserted -----------------------------------------------------
# Attempt 1's artifact manifest recorded a digest for every tests/**/*.py file that existed when its
# package was built. Re-hash each one now; the claim in the prose is exactly this loop's result.
a1_manifest = json.loads(
    (ROOT / "reports/stage3_g2/STAGE_3_G2_ARTIFACT_MANIFEST.json").read_text(encoding="utf-8"))
recorded = a1_manifest["repo_state_files"]
prior_files = sorted(k for k in recorded if k.startswith("tests/"))
check(len(prior_files) > 1, "Attempt 1's manifest recorded no test files to re-hash")
moved = []
for rel in prior_files:
    entry = recorded[rel]
    digest = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
    if digest != (entry if isinstance(entry, str) else entry["sha256"]):
        moved.append(rel)
check(not moved, "these files Attempt 1 recorded have changed: %s" % ", ".join(moved))
check(NEW_FILE not in recorded,
      "the 'new' Attempt 2 test file was already in Attempt 1's manifest; it is not new")

harness = new_tests - attributed
check(harness > 0,
      "every test in the new file is attributed to an AT group; the shared fixtures and the "
      "independent replay are then untested, which contradicts the summary's own description")
harness_clause = ("The remaining one covers" if harness == 1
                  else "The remaining %d cover" % harness)

substitutions = {
    "@@TABLE_COMPOSITION@@": table,
    "@@LIST_AT@@": at_list,
    "@@AT_ATTRIBUTED@@": str(attributed),
    "@@HARNESS_CLAUSE@@": harness_clause,
    "@@PRIOR_FILES_VERIFIED@@": str(len(prior_files)),
    "@@PASSED@@": str(passed),
    "@@FAILED@@": str(failed),
    "@@TOTAL@@": str(total),
    "@@PRIOR@@": str(prior),
    "@@NEW@@": str(new_tests),
    "@@NEW_FILE@@": NEW_FILE,
    "@@FAILING@@": failing[0][len("FAILED "):].split(" ")[0],
}

text = TEMPLATE.read_text(encoding="utf-8")
for token, value in substitutions.items():
    check(token in text, "template does not use %s" % token)
    text = text.replace(token, value)
leftover = [l for l in text.splitlines() if "@@" in l]
check(not leftover, "unsubstituted placeholder: %r" % (leftover[0] if leftover else ""))

OUT.write_text(text, encoding="utf-8", newline="\n")
print("wrote reports/stage3_g2_attempt2/%s" % OUT.name)
print("  collected %d across %d files" % (total, len(per_file)))
print("  %d passed, %d failed" % (passed, failed))
print("  prior floor %d + new %d = %d" % (prior, new_tests, total))
print("  AT-attributed %d + harness %d = %d" % (attributed, harness, new_tests))
print("  failing: %s" % substitutions["@@FAILING@@"])
print("  bytes %d, lines %d" % (len(text.encode("utf-8")), text.count("\n")))
