"""Stage 3 Attempt 2 development-admissibility evidence — run the candidates, write what they did.

A writer, not a judge, exactly as :mod:`stockedge100.reporting.stage3_evidence` was for Attempt 1.
Every number comes from :func:`stockedge100.strategies.attempt2_harness.run_all`, and every
condition verdict from :mod:`stockedge100.strategies.gate`, which reads the engine's own outputs and
compares them against the criteria file the sealed Attempt 2 binding adopts unchanged. Nothing in
this module can change a verdict; it adds three fields the harness does not produce and seals the
result.

``generated_utc`` is read from the system clock at write time and never hand-typed.

``evidence_digest`` covers the harness body with ``generated_utc`` and ``evidence_digest`` themselves
removed. The order in :func:`finalize` is the whole point and is why it is a function: every field
the digest covers has to be in place *before* the digest is taken, **including
``evidence_digest_covers`` itself**. Stage 2 added that description afterwards, which left the file
asserting a coverage it did not have, and the repair cost a full package regeneration. Recomputing
the digest from the written file, following the file's own coverage sentence literally, is the only
thing that catches it; two-run stability does not, because a wrong-but-consistent coverage is stable.

This file may be written **exactly once**. The sealed protocol permits no rerun of a valid completed
evaluation, so :func:`build` refuses to overwrite an existing evidence file rather than quietly
producing a second set of numbers for the same declared runs. A crashed or invalid run is handled by
the sealed ``partial_or_failed_run_rule``, which is a governance decision and not something this
module may take on itself — hence a refusal with an explanation rather than a flag that clears it.

The evidence lands in ``reports/``, which is outside the ``repo_state_id`` patterns, so writing it
does not perturb the digest the decision package will later record.

Usage::

    cd stockedge100 && PYTHONPATH=src python -m stockedge100.reporting.attempt2_evidence
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from stockedge100.audit import sha256_text_canonical_json, utc_now_iso
from stockedge100.strategies.attempt2_harness import run_all

PROJECT_ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_REL = "reports/stage3_attempt2/STAGE_3_ATTEMPT_2_DEVELOPMENT_ADMISSIBILITY.json"

COMMAND = "cd stockedge100 && PYTHONPATH=src python -m stockedge100.reporting.attempt2_evidence"

EXCLUDED_FROM_DIGEST = ("generated_utc", "evidence_digest")
DIGEST_COVERS = (
    "every field of this file except generated_utc and evidence_digest, as canonical JSON"
)


def evidence_digest(body: dict[str, Any]) -> str:
    """The digest of the findings, with the two non-finding fields removed."""

    return sha256_text_canonical_json(
        {key: value for key, value in body.items() if key not in EXCLUDED_FROM_DIGEST}
    )


def finalize(body: dict[str, Any], generated_utc: str) -> dict[str, Any]:
    """Add the three fields the harness does not produce, then seal the body with its own digest."""

    body = dict(body)
    body["generated_utc"] = generated_utc
    body["command"] = COMMAND
    body["evidence_digest_covers"] = DIGEST_COVERS
    body["evidence_digest"] = evidence_digest(body)
    return body


def build() -> int:
    path = PROJECT_ROOT / EVIDENCE_REL
    if path.exists():
        print(f"refusing to overwrite {EVIDENCE_REL}")
        print(
            "The declared Attempt 2 evaluations run exactly once. A second write would either "
            "repeat a valid completed evaluation or replace its numbers with a later set; both are "
            "prohibited. If the existing file records a partial or invalid run, that is resolved "
            "under the sealed partial_or_failed_run_rule, not by rerunning this module."
        )
        return 4

    body = finalize(run_all(), utc_now_iso())

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    print(f"generated_utc     {body['generated_utc']}")
    print(f"evidence_digest   {body['evidence_digest']}")
    print(f"runs_executed     {body['iteration_budget']['runs_executed']}")
    print(f"determinism       {body['determinism']['all_identical']}")
    for entry in body["gate_summary"]:
        flags = ",".join(entry["conditions_not_met"] + entry["conditions_not_evaluable"]) or "-"
        print(f"  {entry['experiment_id']:<32} admitted={str(entry['admitted']):<5} failed={flags}")
    decisive = body["per_condition_rollup"]["decisive_row"]
    print(f"admissible_exists {decisive['value']}")
    print(
        f"stage_verdict     {body['stage_verdict']['verdict']} "
        f"{decisive['gate_verdict_token']}"
    )
    print(f"wrote             {EVIDENCE_REL}")

    # The stage verdict is a finding, not an error: the seal states that FAIL is a legitimate and
    # fully anticipated outcome for Attempt 2. What must never exit clean is a run that did not do
    # what it said — a non-deterministic primary invalidates the evidence itself.
    if not body["determinism"]["all_identical"]:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
