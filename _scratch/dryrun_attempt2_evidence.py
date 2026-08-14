"""Dry-run the Attempt 2 evidence writer's non-evaluation parts.

``run_all`` is monkeypatched to a stub, so this exercises finalize(), the digest coverage, the
overwrite refusal and every print statement without executing a single declared run. The real
execution happens exactly once, from the module itself.

Nothing here is part of the repository state.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, r"d:\Product\stock-trade-alpaca\stockedge100\src")

from stockedge100.audit import sha256_text_canonical_json
from stockedge100.reporting import attempt2_evidence as mod

STUB = {
    "artifact_id": "SE100-EVID-3002",
    "iteration_budget": {"runs_executed": 18},
    "determinism": {"all_identical": True},
    "gate_summary": [
        {
            "experiment_id": "SE100-S3A2-C1-PULLBACK-RA1",
            "admitted": False,
            "conditions_not_met": ["S3-C2"],
            "conditions_not_evaluable": [],
        },
        {
            "experiment_id": "SE100-S3A2-C2-MEANREV-RA1",
            "admitted": True,
            "conditions_not_met": [],
            "conditions_not_evaluable": [],
        },
    ],
    "per_condition_rollup": {
        "decisive_row": {"value": True, "gate_verdict_token": "TOKEN-PASS"},
    },
    "stage_verdict": {"verdict": "PASS"},
}

print("--- target path ---")
print(" ", mod.EVIDENCE_REL)
print("  exists:", (mod.PROJECT_ROOT / mod.EVIDENCE_REL).exists())
print("  parent exists:", (mod.PROJECT_ROOT / mod.EVIDENCE_REL).parent.exists())
print("  PROJECT_ROOT:", mod.PROJECT_ROOT)

print("\n--- finalize field order ---")
body = mod.finalize(dict(STUB), "2026-08-12T00:00:00Z")
print("  keys:", list(body)[-4:])

print("\n--- coverage sentence followed literally, from the serialized form ---")
text = json.dumps(body, indent=2, sort_keys=False) + "\n"
reloaded = json.loads(text)
recomputed = sha256_text_canonical_json(
    {k: v for k, v in reloaded.items() if k not in ("generated_utc", "evidence_digest")}
)
print("  written  :", body["evidence_digest"])
print("  recomputed:", recomputed)
print("  match    :", recomputed == body["evidence_digest"])
print("  covers   :", body["evidence_digest_covers"])
print("  command  :", body["command"])

print("\n--- prints and exit status, with run_all stubbed ---")
tmp = Path(r"d:\Product\stock-trade-alpaca\_scratch\dryrun_out")
tmp.mkdir(exist_ok=True)
mod.PROJECT_ROOT = tmp
mod.run_all = lambda: dict(STUB)
print("  exit:", mod.build())
print("  written file exists:", (tmp / mod.EVIDENCE_REL).exists())

print("\n--- second call refuses ---")
print("  exit:", mod.build())

print("\n--- non-deterministic body exits 3 ---")
(tmp / mod.EVIDENCE_REL).unlink()
bad = dict(STUB)
bad["determinism"] = {"all_identical": False}
mod.run_all = lambda: dict(bad)
print("  exit:", mod.build())
