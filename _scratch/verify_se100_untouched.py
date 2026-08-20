"""Prove the paper-trading work left stockedge100/ byte-identical.

Two independent checks:
  1. Recompute repo_state_id from the sealed patterns and assert it equals the
     value on record in CLAUDE.local.md.
  2. Assert git sees no modification of any kind under stockedge100/.

Run from the workspace root:
    python _scratch/verify_se100_untouched.py
"""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
GOVERNED = os.path.join(ROOT, "stockedge100")
EXPECTED = "30cadd00c89fc09cbbcd37ae98ec69546c5992a652f3556e29d07a5a2d2d94a2"

sys.path.insert(0, os.path.join(GOVERNED, "src"))
os.chdir(GOVERNED)

from stockedge100.reporting.stage_package import repo_state  # noqa: E402

files, digest = repo_state()
print("repo_state_id : %s" % digest)
print("files covered : %d" % len(files))
print("expected      : %s" % EXPECTED)
assert digest == EXPECTED, "DIGEST MOVED: %s" % digest
print("MATCH -> stockedge100/ is byte-identical to the parked state")

os.chdir(ROOT)
porcelain = subprocess.run(
    ["git", "status", "--porcelain", "--", "stockedge100"],
    capture_output=True, text=True, check=True,
).stdout.strip()
print("\ngit status -- stockedge100 : %s" % (porcelain or "(empty)"))
assert porcelain == "", "git reports changes under stockedge100/"
print("CLEAN -> no tracked or untracked change under stockedge100/")

# What this session did touch, for the record.
changed = subprocess.run(
    ["git", "status", "--porcelain"], capture_output=True, text=True, check=True,
).stdout.strip().splitlines()
print("\nchanged paths in the workspace (%d):" % len(changed))
for line in sorted(changed):
    print("  " + line)
