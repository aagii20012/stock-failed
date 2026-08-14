"""Recompute the Attempt 2 evidence self-digest from the written file, following the file's own
coverage sentence literally, and re-read the sealed verdict-token derivation.

Nothing here is part of the repository state.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, r"d:\Product\stock-trade-alpaca\stockedge100\src")

from stockedge100.audit import sha256_text_canonical_json

ROOT = Path(r"d:\Product\stock-trade-alpaca\stockedge100")
EVIDENCE = ROOT / "reports/stage3_attempt2/STAGE_3_ATTEMPT_2_DEVELOPMENT_ADMISSIBILITY.json"

body = json.loads(EVIDENCE.read_text(encoding="utf-8"))

print("--- file ---")
print("  bytes:", EVIDENCE.stat().st_size)
print("  artifact_id:", body["artifact_id"])
print("  generated_utc:", body["generated_utc"])
print("  command:", body["command"])
print("  covers:", body["evidence_digest_covers"])

print("\n--- self-digest, per the coverage sentence, from the written file ---")
recomputed = sha256_text_canonical_json(
    {k: v for k, v in body.items() if k not in ("generated_utc", "evidence_digest")}
)
print("  recorded  :", body["evidence_digest"])
print("  recomputed:", recomputed)
print("  MATCH     :", recomputed == body["evidence_digest"])

print("\n--- top-level keys ---")
for key in body:
    print("  ", key)

print("\n--- iteration budget ---")
for k, v in body["iteration_budget"].items():
    if not isinstance(v, (dict, list)):
        print(f"   {k}: {v}")

print("\n--- determinism ---")
print("  all_identical:", body["determinism"]["all_identical"])
for entry in body["determinism"]["runs"]:
    print("  ", {k: v for k, v in entry.items() if k != "note"})

print("\n--- gate summary ---")
for entry in body["gate_summary"]:
    print("  ", json.dumps(entry))

print("\n--- decisive row ---")
print(json.dumps(body["per_condition_rollup"]["decisive_row"], indent=2))

print("\n--- rollup rows ---")
print(json.dumps(body["per_condition_rollup"]["rows"], indent=2)[:3000])

print("\n--- stage verdict ---")
print(json.dumps(body["stage_verdict"], indent=2))
