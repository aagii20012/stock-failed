"""Replace section 18 of the Attempt 3 report template.

Two defects, both found by reading the template against the tree rather than against my memory of it:

* the numbering prose was wrong. It said "conflict ids below 26 that appear here are Attempt 2 ids",
  but 19, 21, 22 and 24 carry the ``G2A3`` prefix -- they are Attempt 3 ids that supersede the scope
  of the same-numbered ``G2A2`` entry. The sealed protocol config states the rule exactly; it is now
  quoted through a token instead of paraphrased.
* ``@@TABLE_CONFLICTS@@`` had no backing section in ``_ra3_tables.txt`` and could not have one: the
  builder assembles ``conflicts_found`` from f-strings inside ``build()``, so no emitter can extract
  them. The 22 rows are written here as summaries, with every number injected through a token so that
  none of them is typed.

Anchored replacement, not an exact-block match: the script refuses if either anchor is missing or if
the region does not still contain the placeholder it is meant to remove.
"""

from __future__ import annotations

from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent / "ra3_report_template.md"

START = "## 18. Conflicts"
END = "The full text of each, as written into the decision record, is in"

NEW = """## 18. Conflicts

The numbering is one space shared by `SE100-CFG-3105` and `SE100-CFG-3106`. `SE100-CFG-3105` states the
rule, and this is its text rather than a paraphrase of it:

> @@CONFLICT_NUMBERING@@

Read "this file" there as `SE100-CFG-3105`. Four ids below 26 therefore carry the `G2A3` prefix and are
Attempt 3 ids, not Attempt 2 ids: the prefix is what makes `G2A3-CONFLICT-19` and `G2A2-CONFLICT-19` two
distinct entries. Ids 34 to 38 were taken by the protocol config before the run. Ids 39, 40 and 41 were
taken during implementation, in `g2_rotation_ra3.py`, `g2_gate_ra3.py` and
`test_g2_sel2_selection_rule.py`. Id 42 is taken by this session's decision package, and 43 is free.

| Id | Conflict | Resolution |
|---|---|---|
| `G2A3-CONFLICT-19` | One of RA2's three ladder rungs is gone, so the engineered component of any MET verdict here is smaller than Attempt 2's by exactly that rung and no more. | Recorded in the sealed criteria before the run. Supersedes `G2A2-CONFLICT-18`'s scope. |
| `G2A3-CONFLICT-21` | The operating instruction names no verdict token at all, which is a change from both prior attempts. | The token was derived from `SE100-CFG-3106`'s `verdict_token_derivation`, which is the disk. The builder asserts the derived string against the evidence's own rather than restating a literal. |
| `G2A3-CONFLICT-22` | Across three attempts one hypothesis family has now been run under three ladder geometries — none at all, 5/8/10, and 8/10 — which is a search over risk architectures and not a robustness test of one. | Disclosed, not repaired. Carried forward as @@S:CUM_VARIANTS@@ cumulative variants and @@S:CUM_RUNS@@ cumulative runs on one family. |
| `G2A3-CONFLICT-24` | Candidate index 3 is the only live candidate, so the constitution's cross-candidate disjunction is taken over a one-member set. | The gate is decided by the `admissible_candidate_exists` row alone; the seven condition rows settle nothing on their own. |
| `G2A2-CONFLICT-25` | `SE100-CFG-3105` scopes the gate across both runs while `SE100-CFG-3106` lists the stress run as reported-but-not-gating for `S3-C1` and `S3-C4`, and neither outranks the other. | Inherited and resolved as Attempt 2 resolved it. The more restrictive reading governs and both readings are reported in full; here they agree — the permissive base-only reading gives `@@PERMISSIVE_READING@@`. |
| `G2A3-CONFLICT-26` | SEL-2 reads dispersion across a neighbourhood where Attempt 2's rule read a level, and the sealed protocol states plainly that Attempt 2's rule was the more conservative of the two. | This is the reason Attempt 3 required its own pre-registration rather than a re-run of Attempt 2's. |
| `G2A3-CONFLICT-27` | The operating instruction describes neighbourhoods of 2, 3 or 4 variants; the sealed geometry on this grid gives 3, 4 or 5, and the representative has @@S:REP_NEIGHBOURS@@. | The sealed geometry governs. The instruction's counts are not repeated as fact anywhere in this package. |
| `G2A3-CONFLICT-28` | `SE100-CFG-3103`'s closure sentence states that no Attempt 3 is authorized by that file. | Satisfied by the operating instruction, which authorizes one attempt and no more. |
| `G2A3-CONFLICT-29` | Removing a rung moves RA3 strictly toward Attempt 1 on the one axis that produced Attempt 1's failure mode, so a larger drawdown was the declared cost of the change. | No variant breached the research shutdown and the deepest maximum drawdown across all 36 runs was @@S:DEEPEST_DD_PCT@@ against a 15% limit. The declared risk did not materialise, which is a result and not a vindication of the reasoning. |
| `G2A3-CONFLICT-30` | `governance/*` is single-level and `config/**` is recursive, so this attempt's subtree splits down the middle of `repo_state_id`. | Both directions are asserted at build time and both hold. Widening the patterns is not available, because the patterns are themselves sealed by every earlier stage's digest. |
| `G2A3-CONFLICT-31` | `RotationEngineRA3` subclasses `RotationEngineRA1`, which belongs to a closed attempt. | It re-derives exactly the risk and sessions-in-band state it must after calling `super()`, which an AST test enforces. Subclassing reads the closed module without modifying it. |
| `G2A3-CONFLICT-32` | The dissimilarity denominator carries a floor of 1, so a pair that is zero on both sides scores 0 rather than dividing by zero. | Disclosed, not repaired. For the selected representative no pair was zero on both sides, so the floor did not decide this selection. |
| `G2A3-CONFLICT-33` | This is the third disclosed adaptation on one hypothesis family, and a PASS here would not on its own have distinguished which of the two changes produced it. | The attempt failed, so the question is moot for this result and remains live for the family. |
| `G2A3-CONFLICT-34` | @@S:MODULE_COUNT@@ prior-attempt modules are held immutable, not the nine the operating instruction implies. | The count is read from the seal rather than typed into the package, so a silently shortened list fails loudly instead of passing. |
| `G2A3-CONFLICT-35` | This pre-registration was written after two attempts' development results were known, and both of its changes were chosen in response to the second. | Pre-registration constrains what happens after the seal; it cannot undo what was known before. The adaptation is disclosed verbatim in five carriers, the multiplicity is quantified, and no threshold was adjusted in either direction to compensate. Supersedes `G2A2-CONFLICT-6`'s scope. |
| `G2A3-CONFLICT-36` | Both fail routes of this attempt emit the same verdict token. | The route is recorded separately: `@@FAIL_ROUTE@@`, which is the gate-reached-and-missed route and not Attempt 1's no-representative route. |
| `G2A3-CONFLICT-37` | Attempt 2's operating prompt named verdict tokens that existed in no artifact; Attempt 3's names none at all and directs that the sealed criteria file be grepped instead. | The failure mode is removed rather than resolved a second time. The tokens are minted once, in `SE100-CFG-3106`, and the four belonging to Attempts 1 and 2 are asserted absent from every Attempt 3 verdict field. Supersedes `G2A2-CONFLICT-8`'s scope. |
| `G2A3-CONFLICT-38` | Attempt 2's sealed pre-registration states that no Attempt 3 is authorized. | A stage artifact's self-imposed closure rule is not a constitutional provision and does not outrank the operator. What it does outrank is a silent reopening, which is not what happened: the adaptation is disclosed verbatim in five carriers and the decision package carries it in the sixth. |
| `G2A3-CONFLICT-39` | The sealed `mechanics_carried_unchanged.method` states that only the variant id format and the ids themselves differ from Attempt 2's. Compared pointer by pointer, four further pointers differ. | Three are additive provenance notes and the fourth is `gate_evaluation_scope.criteria_source`, which could not have been otherwise. None of the four is a mechanic. The seal is not edited; the checker implements the true predicate and reports the unused entries of both allow-lists, so a list that only ever widens shows up as evidence rather than passing quietly. |
| `G2A3-CONFLICT-40` | Two prose pointers were renamed between Attempt 2's criteria seal and Attempt 3's — `S3-C3`'s attempt note and `S3-C6`'s scope-interpretation significance note. | Both are evidence text read by no predicate. Attempt 2's evaluators are called unmodified against an adapted view binding the old names to the new values, and the adapter check proves the view differs from the seal in exactly those two pointers, that both aliases carry byte-identical values to their RA3 originals, and that the sealed object itself is unmutated. |
| `G2A3-CONFLICT-41` | Three lists of banned selection-input substrings exist and no two are equal. `ratio` and `factor` are named in the seal's AT-I prose and enforced by neither implementation, so a field named `information_ratio` would pass every substring check. | Widening an implemented list to match a prompt's prose is the one repair this project forbids, so the gap is asserted rather than closed. The frozen dataclass makes it moot on this attempt: the selection surface carries exactly six fields and no return field can reach it whatever the substring lists say. |
| `G2A3-CONFLICT-42` | The sealed adaptation disclosure reasons that the removed rung had suppressed ordinary-market returns as well as crisis losses. Half of that reasoning is confirmed by this attempt's own measurement and half is refuted. | The throttle did loosen — ladder descents fell from @@S:LAD_LADDER_DESCENTS_A2@@ to @@S:LAD_LADDER_DESCENTS_A3@@ across the same 36 runs. Grid returns did not improve: Attempt 2's grid was already positive on @@S:A2_POS_BASE@@ of 18 base runs and its best run, @@S:A2_RET_MAX_PCT@@, exceeded this attempt's @@S:A3_RET_MAX_PCT@@. The representative moved off the grid floor because SEL-2 replaced the lowest-turnover rule, not because a rung was removed. Section 12 carries the three-way measurement; the sealed text is not edited. |

"""

text = TEMPLATE.read_text(encoding="utf-8")
lines = text.splitlines(keepends=True)

start_idx = [i for i, ln in enumerate(lines) if ln.rstrip("\r\n") == START]
if len(start_idx) != 1:
    raise SystemExit("PATCH REFUSED: %d matches for the start anchor %r" % (len(start_idx), START))
end_idx = [i for i, ln in enumerate(lines) if ln.startswith(END)]
if len(end_idx) != 1:
    raise SystemExit("PATCH REFUSED: %d matches for the end anchor" % len(end_idx))
a, b = start_idx[0], end_idx[0]
if a >= b:
    raise SystemExit("PATCH REFUSED: anchors out of order (%d, %d)" % (a, b))

region = "".join(lines[a:b])
if "@@TABLE_CONFLICTS@@" not in region:
    raise SystemExit("PATCH REFUSED: the region does not contain @@TABLE_CONFLICTS@@; already patched?")
if "Conflict ids below 26" not in region:
    raise SystemExit("PATCH REFUSED: the region does not contain the wrong prose; already patched?")

patched = "".join(lines[:a]) + NEW + "".join(lines[b:])
if "@@TABLE_CONFLICTS@@" in patched:
    raise SystemExit("PATCH REFUSED: @@TABLE_CONFLICTS@@ survives elsewhere in the template")

TEMPLATE.write_bytes(patched.encode("utf-8"))

print("region replaced: lines %d..%d (%d lines out, %d lines in)"
      % (a + 1, b, b - a, len(NEW.splitlines())))
print("template now %d bytes, %d lines" % (len(patched.encode("utf-8")), len(patched.splitlines())))
crlf = patched.encode("utf-8").count(b"\r\n")
print("crlf %d (must be 0)" % crlf)
rows = [ln for ln in NEW.splitlines() if ln.startswith("| `") and "CONFLICT-" in ln]
print("conflict rows written: %d (must be 22)" % len(rows))
