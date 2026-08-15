"""Recompute the Generation 2 Stage 3 evidence self-digest from the written file. ASCII only.

Deliberately does NOT import the writer's own ``evidence_digest``. The point is to follow the
coverage sentence the file itself carries -- ``evidence_digest_covers`` -- rather than to re-run the
code that produced the value, because the failure this guards against is exactly a file whose
coverage sentence and actual coverage disagree. Re-running the writer's own function would agree
with itself no matter what the sentence said.

Stage 2 of Generation 1 shipped that defect: the coverage field was added after digesting, so a
reader who recomputed the digest exactly as documented got a different value. It cost a full package
regeneration, and two-run stability had not caught it -- a wrong-but-consistent coverage is stable.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
EVIDENCE = ROOT / "reports/stage3_g2/STAGE_3_G2_DEVELOPMENT_ADMISSIBILITY.json"

# Parsed out of the coverage sentence by hand, as a reader would.
EXCLUDED = ("generated_utc", "evidence_digest")


def canonical(payload) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def main() -> int:
    body = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    print(f"file          {EVIDENCE.relative_to(ROOT)}")
    print(f"bytes         {EVIDENCE.stat().st_size}")
    print(f"top-level     {len(body)} fields")
    print(f"covers        {body['evidence_digest_covers']}")

    covered = {k: v for k, v in body.items() if k not in EXCLUDED}
    recomputed = hashlib.sha256(canonical(covered).encode("utf-8")).hexdigest()
    recorded = body["evidence_digest"]

    print()
    print(f"recorded      {recorded}")
    print(f"recomputed    {recomputed}")
    print(f"match         {recomputed == recorded}")

    # The coverage sentence must be inside the coverage. If it were excluded, the file could assert
    # any coverage at all without changing its own digest.
    print()
    print(f"covers_field_is_itself_covered  {'evidence_digest_covers' in covered}")
    print(f"command_is_covered              {'command' in covered}")
    print(f"excluded_fields_present         {[k for k in EXCLUDED if k in body]}")

    # And a covered field must actually move the digest.
    probe = dict(covered)
    probe["evidence_digest_covers"] = probe["evidence_digest_covers"] + " "
    moved = hashlib.sha256(canonical(probe).encode("utf-8")).hexdigest() != recorded
    print(f"one-space perturbation moves it {moved}")

    ok = recomputed == recorded and "evidence_digest_covers" in covered and moved
    print()
    print("RESULT " + ("OK" if ok else "MISMATCH"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
