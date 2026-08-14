"""Stage 2 engine validation evidence — run the harness, write what it found.

This module is a writer, not a judge. Every number in the output comes from
:func:`stockedge100.backtest.harness.run_all`, which runs the engine over the development window and
compares it against ``config/stage2_engine_spec.json``. Nothing here decides whether Gate 2 passes;
that is :mod:`stockedge100.reporting.stage2_package`, which reads this file back.

Two fields are added on top of the harness output.

``generated_utc`` is read from the system clock at write time and never hand-typed.

``evidence_digest`` covers the harness body with ``generated_utc`` and ``evidence_digest`` themselves
removed, so it is a digest of the *findings* and not of when they were written down. Rerunning the
harness on unchanged code and unchanged data must reproduce it exactly; if it does not, the engine is
not deterministic and the digest says so before anyone has to read the file. It excludes its own
entry for the ordinary reason that nothing may hash itself.

The evidence lands in ``reports/``, which is outside the ``repo_state_id`` patterns, so writing it
does not perturb the digest the decision package will later record.

Usage::

    cd stockedge100 && PYTHONPATH=src python -m stockedge100.reporting.stage2_evidence
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from stockedge100.audit import sha256_text_canonical_json, utc_now_iso
from stockedge100.backtest.harness import run_all

PROJECT_ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_REL = "reports/stage2/STAGE_2_ENGINE_VALIDATION.json"

COMMAND = "cd stockedge100 && PYTHONPATH=src python -m stockedge100.reporting.stage2_evidence"


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
    """Add the three fields the harness does not produce, then seal the body with its own digest.

    Order is the whole point, and is why this is a function rather than four lines inside
    :func:`build`. Every field the digest covers has to be in place *before* the digest is taken —
    including :data:`DIGEST_COVERS`, the field that describes the coverage. Adding that description
    afterwards left the file asserting a coverage it did not have, so a reader who recomputed the
    digest from the file exactly as documented got a different value. That is the precise failure
    mode the digest exists to expose, occurring in the digest itself, and it is invisible unless the
    recomputation is actually performed.
    """
    body = dict(body)
    body["generated_utc"] = generated_utc
    body["command"] = COMMAND
    body["evidence_digest_covers"] = DIGEST_COVERS
    body["evidence_digest"] = evidence_digest(body)
    return body


def build() -> int:
    body = finalize(run_all(), utc_now_iso())

    path = PROJECT_ROOT / EVIDENCE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    print(f"generated_utc     {body['generated_utc']}")
    print(f"evidence_digest   {body['evidence_digest']}")
    print(f"determinism       {body['determinism']['all_identical']}")
    print(f"look_ahead        {body['look_ahead_truncation']['identical']}")
    print(f"fixtures          {body['hand_calculated_fixtures']['all_match']}")
    print(f"benchmarks        {body['benchmarks']['reconciles']}")
    print(f"defect_classes    {body['defect_classes']['declared_class_count']} declared, all with tests")
    print(f"all_conditions    {body['all_conditions_met']}")
    print(f"wrote             {EVIDENCE_REL}")

    # A harness that found a failure must not exit clean. The decision package reads this file, and a
    # silent zero here would be the one place a false pass could enter the record unexamined.
    return 0 if body["all_conditions_met"] else 3


if __name__ == "__main__":
    raise SystemExit(build())
