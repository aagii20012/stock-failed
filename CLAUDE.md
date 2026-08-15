# StockEdge100 — project rules

Algorithmic trading research project under frozen governance. The working code lives in
[stockedge100/](stockedge100/). Read [stockedge100/README.md](stockedge100/README.md) first for the
current gate status.

## Precedence

1. `stockedge100/governance/STAGE_0_CONSTITUTION.md` (document id `SE100-GOV-0001`, FROZEN)
2. The operating prompt for the session
3. This file

The constitution outranks everything wherever it is **more restrictive**. A prompt may explain
implementation detail; it may never weaken a constitutional rule. Where the two differ, adopt the
constitution's value and record the divergence in the stage report.

## Hard rules

- **Never edit, regenerate, replace, or "improve" a frozen artifact.** Frozen artifacts are opened
  read-only. If one appears wrong, report it as a blocker; do not fix it.
- **One governance stage per session.** Finish the stage, issue exactly one verdict, stop — even if
  context remains.
- **No fabricated elapsed time.** Duration-based gates (paper, shadow, live evidence) require real
  wall-clock time. Simulated elapsed time can never satisfy them.
- **`live_trading_authorized` stays `false`** until explicit human authorization is recorded at the
  proper gate. No live order, cancel, replace, liquidation, or unattended scheduling without it.
- **Never weaken or delete a test to make a gate pass.** The Stage 0 suite (27 tests) is a permanent
  regression floor; later stages add to it and never subtract.
- **Credentials:** detect presence by variable name only. Never print, log, echo, or write a secret
  value; mask it if it surfaces in subprocess output. Never move secrets into the repository.

## Gate numbering

The operating prompt and the constitution number stages differently. The binding mapping is
[STAGE_0_VERIFICATION_REPORT.md](stockedge100/governance/STAGE_0_VERIFICATION_REPORT.md) §6.3.
The one that bites: **prompt Stage 4 must clear two constitutional gates — 4 (validation) and
5 (holdout)**. Prompt 5→6, 6→7, 7→8, 8 and 9→9.

## Authoring audit artifacts

- **Read the system clock before writing any timestamp.** Never hand-type a UTC time into a report.
  Let the generator emit it, or read it first and paste the real value.
- **Never write a prediction into an evidence field.** Stage 4's builder measures its contamination
  counts before the build writes anything — correct, and the note saying so is correct — but the note
  then predicted that "each of the three will rise by one artifact more once the build completes."
  Report artifacts rose by three (the decision record, manifest and checksum record), run records by
  one, and the module count not at all, because `reports/` is overwritten and `runs/` is appended.
  Nothing verifiable depended on the clause, so regenerating to reword it would have been worse than
  disclosing it — but an evidence field should state the *mechanism* (overwrite vs append, and which
  files) or say nothing, never a number no one has computed yet.
- **The same applies to every other value that already exists on disk.** Digests, counts, thresholds,
  dates, sealed wording: extract them and paste the extraction. A Stage 3 draft reproduced a
  determinism table from memory and every digest in it was invented; another draft asserted the
  sealed protocol carried hand-computed values it does not carry. Quote the file or drop the claim.
- **Never embed a tree digest inside a file that is part of that tree.** `repo_state_id` covers
  `governance/*.md`, so writing the digest into a governance report invalidates it on write. Put
  such values only in the JSON decision record and the `runs/` record, and have the prose point
  there.
- **Nothing may hash itself.** An artifact manifest excludes its own entry; the surrounding
  `.sha256` record covers it instead.
- Freeze records use bare filenames, so `sha256sum -c` must run **from the directory holding the
  record** (`stockedge100/governance/`). A failure from the wrong working directory is an operator
  error, not an integrity failure.

## Building a stage decision package

The shared builder exists as of Stage 1: `reporting/stage_package.py` provides `StageDecision` +
`build_stage_package()`, plus `verify_stage0_freeze()`, `repo_state()`, `verify_sha256_record()`,
and `new_run_id()`. A stage module supplies only its own evidence, limitations, and gate conditions
— `reporting/stage1_package.py` is the worked example to copy. `stage0_package.py` predates the
split and stays exactly as it is; its artifacts are already hashed.

Every stage produces: a Markdown report, a JSON decision record, a `.sha256` record, a test summary,
an artifact manifest, and an append-only `runs/` reproducibility record.

**Build the package last, and touch nothing tracked afterwards.** `repo_state_id` covers
`governance/*.{md,json,sha256}`, `src/**/*.py`, `tests/**/*.py`, `config/**/*.{json,yaml}`,
`pyproject.toml`, `README.md`, `.gitignore`. Editing any of those after the build invalidates the
digest the build just recorded, and `runs/` is append-only, so the only repair is to regenerate and
record the supersession in the new run record's notes.

**Read those glob depths literally — they are not uniform.** `governance/*` is single-level and
`config/**` is recursive, so a new generation's subtree splits down the middle: `config/generation_2/*.json`
**is** covered by `repo_state_id`, while `governance/generation_2/*.md|json|sha256` is **not**. That is
not a defect to fix by widening the pattern — the patterns are themselves sealed by every earlier stage's
digest — but it must be disclosed as a numbered conflict, as Generation 2 did in `G2-CONFLICT-4`. The
practical consequence is that a generation subtree's governance artifacts are held by their own `.sha256`
record and the artifact manifest alone, so those two must actually cover them; `repo_state_id` will not
notice if they drift. Verify both directions explicitly — assert the report is outside the patterns *and*
that the config JSON is inside — because a check that only confirms what you expect confirms nothing.

Four consequences worth internalizing:

- Finish the Markdown report, test summary, pytest output **and any `README.md` update** before
  running the builder. A stale README cost Stage 1 a full regeneration. The builder is itself in
  `src/`, so a late fix to it — even a prose-only fix to one evidence bullet — invalidates the captured
  pytest output too. Re-run the suite and **overwrite** the capture (never append: the parser reads the
  last summary lines, so an appended run silently becomes the record).
- **Recompute every evidence self-digest from its written file before running the builder**, not
  after. A digest that did not recompute cost Stage 2 a full regeneration — and the repair landed in
  `src/` and `tests/`, which are themselves patterns, so the invalidation was unavoidable once the
  package existed. Verifying evidence is cheap before the build and expensive after it.
- No test can cover the decision package, because `tests/**/*.py` is itself in the patterns — adding
  one would invalidate the `repo_state_id` that test would assert. Verify the package by rerunning
  the recomputation, not by writing a test.
- **The builder itself lives in `src/`, so dry-run it before it writes anything.** A defect found
  after the real build cannot be fixed without invalidating the digest that build just recorded.
  Import the module from an out-of-tree script with `build_stage_package` monkeypatched, print the
  assembled gate conditions, and diff them against the report's own gate table. Stage 3's rollup was
  wrong on the first dry-run and cost nothing to fix.

`reports/` and `runs/` are outside the patterns, so writing them never perturbs the digest.

**A builder's guard must fit the verdicts its stage can actually reach.** `stage2_package.py` refuses
to write when its evidence does not meet every condition, which is right for a stage whose package
could only ever be a pass. Copying that guard into a stage that can legitimately fail would suppress
the deliverable — the constitution keeps negative and rejected results on disk. The portable guard is
the other one, and `stage3_package.py` implements it: assert that the verdict written into the
package is the verdict the evidence reached, derive the token from the sealed
`verdict_token_derivation` rather than restating it as a literal, and refuse the incoherent
combinations (a `FAIL` with admitted candidates).

**A design or pre-registration session has no evidence file, so its artifacts *are* its evidence.**
`stage3_attempt2_package.py` is the pattern: its conditions are *seal* conditions recomputed from the
artifacts at build time — checksum records re-verified, digests recomputed from the written files,
agreement tokens found in both the Markdown and the JSON, contamination counts re-read — rather than
loaded from a results file. Two consequences. Its guard must still be the portable one, because a
design session can legitimately end `BLOCKED`; what it refuses is a package that disagrees with its own
conditions. And the gate row belongs in the table as `NOT_RUN`, not omitted: a package that silently
drops `admissible_candidate_exists` reads as though the gate were irrelevant rather than unevaluated.

Also assert that the verdict token is **not** either of the gate's own tokens, taken from the sealed
`verdict_token_derivation`. A design session that accidentally emitted the gate's `PASS` token would
otherwise look like a passed gate.

## Verdicts

End every stage with one token from constitution §10 plus its conditions table — never a vague
"looks good". Format: `PASS — <STAGE>_<CONDITION>`, `BLOCKED — <reason>`, etc.

**The token comes from disk, not from the prompt.** An operating prompt may name pass/fail tokens that
exist in no artifact: the Stage 3 Attempt 2 prompt specified
`STAGE_3_ATTEMPT_2_DEVELOPMENT_ADMISSIBILITY_MET` / `..._STRATEGIES_REJECTED_IN_DEVELOPMENT`, while the
sealed `verdict_token_derivation` in `config/stage3_gate_criteria.json` defines only
`STAGE_3_STRATEGY_ADMITTED_IN_DEVELOPMENT` / `STAGE_3_STRATEGY_REJECTED_IN_DEVELOPMENT`. Grep the tree
for the prompt's strings before using them; if they are absent, emit the sealed token, and record the
divergence as a numbered conflict in the package. Never edit a sealed derivation to match a prompt, and
never invent a token.

Gates are conjunctive **within a candidate**; the stage verdict is a **disjunction across candidates**
(§9). A per-condition rollup row therefore means only "at least one candidate satisfied this" and
settles nothing on its own — the gate is decided by the `admissible_candidate_exists` row alone, and
a conditions table that does not carry that row is misleading. Satisfied is also wider than met:
`NOT_APPLICABLE_BY_CONDITION_TEXT` is satisfied without being met, so aggregate on satisfaction and
report `met_by`, `not_met_by`, and `not_applicable_for` as separate lists. Aggregating on
`verdict == "MET"` produced a false `FAIL` for S3-C6 in Stage 3. `NOT_RUN`, `UNKNOWN`,
`NOT_EVALUABLE`, and missing evidence are never a pass.

## Environment

Windows 11, PowerShell + Git Bash. Python 3.10.6 global (no venv). `pyarrow` and `scipy` are **not**
installed. Tests: `cd stockedge100 && python -m pytest tests -q` (pytest reads `pythonpath = ["src"]`
from `pyproject.toml`).

Console stdout is cp1252: `print("→")` raises `UnicodeEncodeError` and kills a diagnostic script
mid-sweep. Keep throwaway output ASCII (`->`).

Diagnostic and dry-run scripts live in `_scratch/` at the workspace root — outside `stockedge100/`, so
they never perturb `repo_state_id`, and unlike `/tmp` they survive for the next stage to copy. Write
them with the Write tool rather than a heredoc: a long `<<'PY'` block failed with `unexpected EOF while
looking for matching` on a script containing nested quotes, and `python -c` with a PowerShell
here-string truncates.

That `pythonpath` setting applies to pytest only. Running a stage module directly needs an explicit
`PYTHONPATH=src`, and the Bash tool's working directory **persists** between calls — so always `cd` by
absolute path in the same command:

```bash
cd /d/Product/stock-trade-alpaca/stockedge100 && PYTHONPATH=src python -m stockedge100.reporting.stage1_package
```

Run from the parent directory instead and `PYTHONPATH=src` points at nothing; the resulting
`ModuleNotFoundError: No module named 'stockedge100.reporting'` looks like a packaging fault and is
not one.

Persistence bites in the other direction too, and this line used to claim the opposite. A later
`python _scratch/g2_stage3_postbuild_verify.py`, typed as though the shell were at the workspace root,
resolved against a previous call's `cd` into `stockedge100/` and failed with
`can't open file 'D:\Product\stock-trade-alpaca\stockedge100\_scratch\...'`. The path in the error is
the diagnostic: it names a directory you never asked for. Prefix every call with its own absolute `cd`.

## Git

The workspace **is** a git repository as of 2026-08-14, pushed to
`https://github.com/aagii20012/stock-failed.git`. The `.git` lives at the workspace root, not inside
`stockedge100/`, so the governed tree still carries no repository of its own.

Governance identity is still the content-derived `repo_state_id`, not a commit — and git can destroy
it. Two settings are load-bearing:

- **`core.autocrlf=false` and `* -text` in the root `.gitattributes`.** Git's Windows default rewrites
  LF to CRLF in the working tree on the *next checkout*, which changes the SHA-256 of every tracked
  file and silently invalidates every freeze record, manifest and `repo_state_id` from Stage 0 onward
  — with no file having been "edited". Never remove either.
- **The sealed `stockedge100/.gitignore` excludes `data/raw|normalized|reference`.** That is what
  keeps the final holdout observations off GitHub. Manifests and checksums are tracked, so the data
  stays reproducible without being published. Never `git add -f` a payload.

The root `.gitignore` and `.gitattributes` sit outside `stockedge100/`, so neither is a
`repo_state_id` pattern and creating them perturbed nothing. **Recompute `repo_state_id` after any git
operation and confirm it is unchanged** before reporting success.

Two statements on the record are now stale and **must not be corrected in place**: `README.md` and
`STAGE_0_VERIFICATION_REPORT.md` both say the tree is not a git repository. The Stage 0 report is
frozen; `README.md` is a pattern locked by the built Stage 4 package. Disclose the staleness in prose.
The README's correction belongs to whatever stage next legitimately rewrites it.

Commits are allowed when asked, but the post-package rule still binds: a commit must not **create,
move, rename or delete** anything under `governance|src|tests|config`, nor `README.md`,
`pyproject.toml` or `.gitignore`. A rename would break the manifest and the checksum records, which
pin exact paths.

**`git add` is not "adding a file" in that sense**, and reading it that way would make the rule
forbid ever committing a stage's own work. Staging a file that already exists on disk changes no
byte and creates no path, so `repo_state_id` cannot move. What the rule forbids is a *filesystem*
change after the package is built. Generation 2's commit staged 70 new paths under
`governance/generation_2`, `config/generation_2`, `src/` and `tests/` — all of them written before
the build and covered by it — and the digest was byte-identical afterwards.

The distinction is checkable rather than argued, so check it instead of reasoning about it. Stage,
then read the status codes back before committing:

```bash
git add -A && git status --porcelain | awk '{print $1}' | sort | uniq -c
```

`A` and `M` are safe. **Any `R` or `D` under a governed path is the violation** — that is the
signature of a move, rename or deletion, and it breaks the manifests whatever the intent was. Then
recompute `repo_state_id` and *assert* it, rather than eyeballing two hex strings:

```python
assert d == EXPECTED, 'DIGEST MOVED: %s' % d
```

One more thing a commit can quietly get wrong: `git ls-files 'stockedge100/data/*'` matches the
`.gitkeep` placeholders inside `data/raw|normalized|reference`, so a naive count reports payload that
is not there. Exclude them (`grep -v '\.gitkeep$'`) and require **zero**, then count what is on disk
and unpublished to prove the `.gitignore` is doing work — 0 tracked against 70 on disk is the
evidence; a bare "0 tracked" would also be produced by an empty data directory.
