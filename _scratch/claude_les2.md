Two API shapes that are easy to guess wrong when writing an out-of-tree immutability check, both learned
by traceback: **`repo_state()` takes no arguments and returns a 2-tuple `(files_dict, digest_str)`** —
unpack it as `files, d = repo_state()`; reversing it produces an `AssertionError` that dumps all 165
paths. And a prior stage's **artifact manifest stores its groups as `path -> digest` dicts**, not lists
of `{path, sha256}` records, under the four keys `frozen_inputs`, `produced_artifacts`, `dataset_hashes`
and `repo_state_files`. Handle both a bare digest string and a `{"sha256": …}` value. Manifests are also
not all in one place: Generation 1's Stage 4 manifest is
`reports/stage4/STAGE_4_VALIDATION_ARTIFACT_MANIFEST.json`, **not** under `governance/` — `find . -name
'*ARTIFACT_MANIFEST*.json'` before assuming a path, or a missing file surfaces later as
`TypeError: 'NoneType' object is not iterable`.
