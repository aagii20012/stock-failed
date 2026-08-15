"""Dry-run the Generation 2 Stage 3 package builder. Writes nothing. ASCII output only.

The builder lives in ``src/``, which is a ``repo_state_id`` pattern, so a defect found after the
real build cannot be fixed without invalidating the digest that build just recorded. Stage 3 of
Generation 1 found its rollup wrong on the first dry-run and the fix cost nothing.

``build_stage_package`` is monkeypatched to a recorder, so the assembled ``StageDecision`` is printed
and no file is written, no run record appended.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.reporting import g2_stage3_package as pkg  # noqa: E402

CAPTURED = {}


class FakeResult:
    run_id = "SE100-R-DRYRUN"
    repo_state_id = "DRYRUN-NOT-COMPUTED"
    timestamp_utc = "DRYRUN"
    freeze_ok = True
    checksum_digest = "DRYRUN"
    decision_path = ROOT / "reports/stage3_g2/DRYRUN.json"
    manifest_path = ROOT / "reports/stage3_g2/DRYRUN.json"
    checksum_path = ROOT / "reports/stage3_g2/DRYRUN.sha256"
    run_record_path = ROOT / "runs/DRYRUN.json"


def recorder(decision):
    CAPTURED["decision"] = decision
    return FakeResult()


def main() -> int:
    pkg.build_stage_package = recorder
    rc = pkg.build()
    print()
    print(f"builder returned {rc}")
    if "decision" not in CAPTURED:
        print("*** the guard refused to write -- nothing to inspect")
        return 1

    d = CAPTURED["decision"]
    print()
    print("== identity ==")
    for field in ("stage", "stage_slug", "decision_basename", "manifest_basename", "gate_id",
                  "gate_name", "verdict", "gate_passed", "generation", "holdout_state",
                  "universe_version", "date_range", "next_authorized_stage"):
        value = getattr(d, field)
        text = str(value)
        print(f"   {field:22s} {text[:150]}")

    print()
    print("== gate conditions ==")
    for cid, row in d.gate_conditions.items():
        print(f"   {cid:32s} {row['verdict']}")
        print(f"      required: {row['required_verbatim'][:110]}")
    print(f"   rows={len(d.gate_conditions)}")
    print(f"   admissible_candidate_exists present: "
          f"{'admissible_candidate_exists' in d.gate_conditions}")
    print(f"   any row claiming a pass: "
          f"{[c for c, r in d.gate_conditions.items() if r['verdict'] in ('MET', 'PASS')]}")

    print()
    print("== verdict token hygiene ==")
    criteria = pkg.load(pkg.CRITERIA)
    der = criteria["verdict_token_derivation"]
    print(f"   sealed pass_token   {der['pass_token']}")
    print(f"   sealed fail_token   {der['fail_token']}")
    print(f"   emitted             {d.verdict}")
    print(f"   emits the pass token: {der['pass_token'] in d.verdict}")
    print(f"   gate_passed is False: {d.gate_passed is False}")

    print()
    print("== counts ==")
    print(f"   evidence     {len(d.evidence)}")
    print(f"   limitations  {len(d.limitations)}")
    print(f"   blockers     {len(d.blockers)}")
    print(f"   conflicts    {len(d.conflicts_found)}")
    print(f"   produced     {len(d.produced)}")
    print(f"   frozen       {len(d.frozen_inputs)}")
    print(f"   tests        {d.tests}")

    print()
    print("== produced artifacts: do they exist yet? ==")
    for name in d.produced:
        target = ROOT / name
        print(f"   {'OK  ' if target.is_file() else 'MISS'} {name}")

    print()
    print("== frozen inputs: do they exist? ==")
    missing = [n for n in d.frozen_inputs if not (ROOT / n).is_file()]
    print(f"   {len(d.frozen_inputs)} listed, missing={missing}")

    print()
    print("== verbatim validation-overlap disclosure ==")
    lock = pkg.load(pkg.PARTITION_LOCK_JSON)
    sealed = lock["validation_reuse_disclosure"]
    print(f"   sealed length {len(sealed)}")
    print(f"   present verbatim in limitations: {sealed in d.limitations}")

    print()
    print("== body is JSON-serialisable ==")
    try:
        blob = json.dumps(d.body, indent=2, sort_keys=False)
        print(f"   OK, {len(blob)} chars, top-level keys={list(d.body.keys())}")
    except TypeError as exc:
        print(f"   *** NOT SERIALISABLE: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
