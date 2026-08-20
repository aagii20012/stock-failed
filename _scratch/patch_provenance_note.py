"""Retract the "something else wrote into _scratch/" note.

I wrote that bullet mid-session after a context compaction, having lost track of
scripts I had authored myself. The file timestamps are a continuous chain of my own
analysis, in the exact order I ran it:

  20:43 compare_lean_vs_harness   20:44 verify_data_identity
  20:45 decision_equivalence      20:45 knife_edge_2022_06
  20:52 timing_bracket            20:59 fill_forensics
  21:01 lag_check                 21:02 reconstruct_lean
  21:03 jan2007_gap               21:04 dd_attribution
  ... plus the patch_*/rewrite_* scripts that edited the writeups

There was no concurrent writer. Leaving the claim in would send a real person
hunting a phantom. The one durable lesson in the bullet -- that `git add -A` in this
workspace swept ten unreviewed files into 0027d94 -- is true and is kept.
"""

import io
import os

NOTES = os.path.abspath(os.path.join(os.path.dirname(__file__), "..",
                                     "CLAUDE.local.md"))

OLD_START = "- **Something other than my own edits wrote into `_scratch/`"
OLD_END = "- **`gen2-attempt4-concentration`**"

NEW = """- **`_scratch/` is committed to this repo (357 files) and `git add -A` sweeps it.**
  Commit 0027d94 pushed ten unreviewed diagnostics that way. Stage explicit paths here.

  Retracting an earlier note in this file which claimed something other than my own
  edits was writing into `_scratch/` during the 2026-08-20 session: not true. The file
  mtimes are one continuous chain of my own analysis (20:43 compare_lean_vs_harness ->
  20:52 timing_bracket -> 20:59 fill_forensics -> 21:01 lag_check -> 21:02
  reconstruct_lean -> 21:03 jan2007_gap -> 21:04 dd_attribution). I lost track of
  authoring them across a context compaction and read my own output as a third party's.
  Relatedly, git reported `.gitignore` and `.claude/rules/faber-lean.md` as modified
  when their content matched HEAD -- a stale stat cache after a script rewrote them
  with identical bytes, which is the same kind of false signal.

"""


def main():
    with io.open(NOTES, encoding="utf-8") as fh:
        body = fh.read()
    if OLD_START not in body:
        print("  already retracted")
        return
    i = body.index(OLD_START)
    j = body.index(OLD_END)
    with io.open(NOTES, "w", encoding="utf-8", newline="") as fh:
        fh.write(body[:i] + NEW + body[j:])
    print("  retracted (%d -> %d chars)" % (len(body), len(body) - (j - i) + len(NEW)))


if __name__ == "__main__":
    print("=== retracting the phantom-writer note ===")
    main()
