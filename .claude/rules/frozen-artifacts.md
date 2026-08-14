---
paths:
  - stockedge100/governance/**
  - stockedge100/reports/**
  - stockedge100/runs/**
description: Handling rules for frozen and hashed governance artifacts
---

# Frozen and hashed artifacts

Files under these paths are evidence. Once a stage has issued its verdict, its artifacts are
**append-only history**, not working files.

## Never modify

- `governance/STAGE_0_CONSTITUTION.md`, `.json`, and `STAGE_0_FREEZE.sha256` are FROZEN
  (`SE100-GOV-0001` v1.0.0). Open them read-only. Not a typo fix, not a reformat, not a "clarify the
  wording" edit. If one is wrong, that is a blocker to report, not a defect to repair.
- Any `STAGE_N_*` artifact after Gate N has been issued. Correcting a shipped stage means a new
  document with a new id that supersedes it, never an in-place edit.
- `runs/*.json` — append only, one file per run, never rewritten.

## Verifying

Freeze records list **bare filenames**, so run the check from the directory that holds the record:

```bash
cd stockedge100/governance && sha256sum -c STAGE_0_FREEZE.sha256
```

A mismatch reported from any other working directory is an operator error. Re-run from the right
directory before concluding anything about integrity.

`reports/stageN/STAGE_N_VERIFICATION.sha256` uses project-root-relative paths, so it verifies from
`stockedge100/`.

## Writing a new artifact

- No timestamp is hand-typed. Read the clock or let the generator emit it.
- No file contains a digest of a tree that includes that file (`repo_state_id` covers
  `governance/*.md` and `src/**/*.py`). Digests belong in the JSON decision record and the `runs/`
  record; prose points at them.
- No manifest hashes itself; the enclosing `.sha256` record covers it.
- Digests recorded in tests are pinned **independently** of the freeze file, so that rewriting an
  artifact and its freeze record together still fails the suite.

## A self-digest must seal its own description first

If an artifact records what its digest covers — an `evidence_digest_covers` field, a coverage note —
that field **is covered by the digest**. Assemble every covered field before hashing, in one function
whose whole job is the ordering; do not append anything to the body afterwards.

Stage 2 got this wrong. The writer set the coverage description after taking the digest, so the
recorded digest excluded three fields while the description named two. Nothing in the findings was
affected, and 270 passing tests said nothing, because the only thing that detects it is performing
the recomputation:

```python
recomputed = sha256_text_canonical_json(
    {k: v for k, v in body.items() if k not in ("generated_utc", "evidence_digest")}
)
assert recomputed == body["evidence_digest"]
```

So: **recompute a self-digest from the written file, following the file's own coverage description
literally, before anything is built on top of that file.** An artifact that asserts a coverage it
does not have is the exact discrepancy the digest exists to expose, occurring in the digest itself —
and it stays invisible until someone does the arithmetic.

Two-run stability is a separate, weaker claim: rerun the writer and require the digest to be
identical across different timestamps. That proves the findings depend on code and data only. It does
**not** prove the digest covers what it says. Check both.

## Checking "this file contains no digest"

Test for the **value**, not the field name. A report is expected to name `repo_state_id` in the
prose that explains where the value actually lives, so `"repo_state_id" not in text` reports a
violation that is not there. The honest predicate is a search for a 64-hex string — either any of
them, or the specific digest just computed:

```python
re.search(r"\b[0-9a-f]{64}\b", text)   # or: repo_state_id not in text
```

Stage 1's first sweep printed a scary `False` on the field-name form. Nothing was wrong with the
report; the predicate was wrong. Say so plainly rather than leaving a misleading line in the record.

The broad `[0-9a-f]{64}` form has the opposite failure once a report legitimately **pins its inputs**.
What is forbidden is a *tree* digest or a *self* digest, not any digest: the Stage 3 Attempt 2 design
report carries eight, and all eight are of individual frozen or sealed files it is quoting on purpose
(both Stage 0 artifacts, the Stage 3 protocol and criteria, the two Attempt 2 config artifacts, the
holdout lock, the pre-registration Markdown). If you do sweep broadly, resolve every hit back to a file
on disk and confirm none is the tree digest and none is the file's own — a bare count proves nothing.

## Verifying a package after the build

**Start from the previous stage's verifier, not from a blank file.** `_scratch/postbuild_verify.py` is
the Stage 3 Attempt 2 sweep, `_scratch/stage4_postbuild_verify.py` the Stage 4 pre-registration one,
and `_scratch/stage4_evaluation_postbuild_verify.py` the Stage 4 evaluation one — 86 checks across the
seventeen post-build requirements, and the richest of the three. Copy that one. All three already call
the helpers correctly. Two signatures are the reverse of the natural guess and cost two failed
runs when re-derived from scratch:

```python
code_hashes, repo_state_id = repo_state()          # hashes FIRST, digest second
results = verify_sha256_record(record_path, cwd)    # dict[path] -> "OK" | "FAILED" | "MISSING"
```

Nor is a decision basename guessable: the Gate 3 Attempt 2 records are
`STAGE_3_ATTEMPT_2_DESIGN.sha256` and `STAGE_3_ATTEMPT_2_STRATEGY_RESEARCH.sha256`, not the
`..._DEVELOPMENT_EVALUATION.sha256` the report's prose suggests. List the directory.

Write the post-build verifier against where the shared builder actually puts each field, not where the
report's prose mentions it. In the decision record, `repo_state_id`, `config_hash` and `random_seed` are
nested under `reproducibility`; `holdout_state`, `dataset_hashes`, `date_range` and `universe_version`
are **not in the decision record at all** — they live in the `runs/` record, and the decision record
carries the window posture in `body.windows` instead. Reading them at top level produces confident
`FAIL` lines about a package that is fine. Three of five failures in one post-seal sweep were this.

Two more predicates that go wrong the same way, both because a directory that was empty for one stage is
legitimately populated by the next:

- **"No strategy code for this attempt exists"** cannot be a path test over `strategies/` once an
  earlier attempt's modules live there. Make it content-based — no module names a candidate of this
  attempt — and pair it with an immutability check that every module there still matches the earlier
  run record's digest.
- **"Nothing the previous run record hashed has moved"** will flag `README.md`, which is in
  `code_hashes` and is *supposed* to change each stage. Allow it explicitly and name it, rather than
  reporting a bare list and leaving the reader to guess whether evidence moved.

When a sweep and a checksum record disagree, the record is right and the predicate is wrong — a
`sha256sum -c` that reports OK while your probe reports a mismatch means the probe misread the file
shape. Fix the probe before doubting the disk.

**"Nothing hashes itself" applies to sealed digest sets too, not just manifests.** Stage 4's S4-C7
recheck set carries `declared_set_size: 13` and `recorded_here: 12`, because the thirteenth entry is
`governance/STAGE_4_PREREGISTRATION.json` — the file doing the declaring. Its digest is carried by
`governance/STAGE_4_PREREGISTRATION.sha256` instead. A bare `len(entries) == 13` reports a scary
`FAIL` on a package that is fine. Assert the triple and then verify the excluded member through its
own record:

```python
(block["declared_set_size"], block["recorded_here"], block["own_digest_excluded"]) == (13, 12, "...")
verify_sha256_record(ROOT / "governance/STAGE_4_PREREGISTRATION.sha256", ROOT)[excluded] == "OK"
```

**A predicate that compares against an empty collection passes vacuously.** The Stage 4 parameterisation
check printed `rsi_period now 2, sealed []` and reported OK — it had found nothing to disagree with,
because the sealed selection record names no parameter values at all (`S4-CONFLICT-6`; they live in
`config/stage3_attempt2_strategy_protocol.json` → the candidate's `primary_parameters`). `all()` over an
empty sequence is `True`, and so is a zero-length mismatch list. **Assert the source is non-empty and
assert the overlap count before asserting agreement** — report `shared=10 mismatch=0`, never a bare
"matches". Any check whose output could be produced by finding nothing is not a check.

Locating that block by *shape* failed too: `all(not isinstance(v, list) for v in node.values())`
excluded the real candidate object because one parameter, `ladder_rungs`, is a list of pairs. Locate
evidence structures by **identity** — the object carrying the candidate's id — not by a guess at their
shape.

**"No broker or credential access" is an AST question, not a `grep` question.** A textual sweep of
`src/` for `alpaca` or `requests` returns a wall of false violations: prose recording Alpaca as
`LOCKED`, the `alpaca_*` keys in `authorization_state`, the `TRACKED_DEPENDENCIES` name list, and a
local variable `requests: list[OrderRequest]` in `backtest/engine.py`. Walk the tree instead and assert
three zeros — no forbidden import root (`alpaca*`, `requests`, `httpx`, `aiohttp`, `socket`, `urllib`,
`http*`, `websocket*`, `boto3`, …), no forbidden attribute (`environ`, `getenv`, `urlopen`, `connect`,
`urlretrieve`), and no string constant containing `http://` or `https://`:

```python
for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
    if isinstance(node, ast.Import):      roots = {a.name.split(".")[0] for a in node.names}
    elif isinstance(node, ast.ImportFrom): roots = {(node.module or "").split(".")[0]}
```

Two more predicates that cost a false `FAIL` on a package that was fine: the declared-variant set must
include the **non-gating** run labels (the three `#PRIMARY#STRESS` runs are declared, just not gating),
and a manifest's group values are `{"sha256": …}` dicts in `frozen_inputs`/`produced_artifacts` but bare
strings in `dataset_hashes`/`repo_state_files` — flatten before comparing, or `in` raises `TypeError`.
Enumerate the actual keys of any evidence structure before writing a predicate against it.

## Secrets

Nothing under these paths may contain a credential value. `tests/unit/test_stage0_governance.py`
scans governance and source for key-shaped strings; keep that test passing rather than adding
exclusions to it.
