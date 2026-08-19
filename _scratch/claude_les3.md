- **CRLF in a hashed file is not automatically a finding.** 85 files in the tree carry CRLF and 7 of them
  are `repo_state_id`-covered paths (`STAGE_1_HOLDOUT_LOCK.json`, `STAGE_1_PREREGISTRATION.json`,
  `STAGE_1_UNIVERSE.json`, `STAGE_2_PREREGISTRATION.json`, `STAGE_3_PREREGISTRATION.json`,
  `STAGE_3_ATTEMPT_2_PREREGISTRATION.json`, `STAGE_4_PREREGISTRATION.json`). Their sealed digests match,
  so CRLF *is* their sealed state and normalizing them would be the corruption. What matters is that the
  `* -text` guard stops a checkout from *changing* line endings — so verify the digests, not the bytes'
  flavour, and never "fix" a CRLF file that verifies.
