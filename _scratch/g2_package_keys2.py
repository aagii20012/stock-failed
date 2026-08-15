"""Second-level enumeration of the built Stage 3 G2 package: the blocks the verifier predicates on.

ASCII only. Level-1 shape came from g2_package_keys.py; this dumps the leaf values of the blocks the
post-build verifier will assert against, so no predicate is written against a guessed field name.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
DEC = ROOT / "reports/stage3_g2/STAGE_3_G2_ROTATION_RESEARCH.json"
MAN = ROOT / "reports/stage3_g2/STAGE_3_G2_ARTIFACT_MANIFEST.json"


def show(s) -> str:
    return str(s).encode("ascii", "backslashreplace").decode("ascii")


def dump(node, name: str, width: int = 100) -> None:
    print(f"----- {name} -----")
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, (dict, list)):
                print(f"   {k:40s} {type(v).__name__}({len(v)}) {show(v)[:width]}")
            else:
                print(f"   {k:40s} {show(v)[:width]}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            print(f"   [{i}] {show(v)[:width + 20]}")
    else:
        print(f"   {show(node)[:width]}")
    print()


def main() -> None:
    dec = json.loads(DEC.read_text(encoding="utf-8"))
    man = json.loads(MAN.read_text(encoding="utf-8"))

    print(f"top-level verdict   {show(dec['verdict'])!r}")
    print(f"top-level gate      {show(dec['gate'])}")
    print(f"gate_passed         {dec['gate_passed']!r}")
    print(f"stage               {show(dec['stage'])!r}")
    print(f"project             {show(dec['project'])!r}")
    print(f"timestamp_utc       {show(dec['timestamp_utc'])!r}")
    print()

    for key in ("generation", "constitution", "verdict_semantics", "verdict_token_derivation",
                "preregistration", "partition", "universe", "gate_evaluation_scope",
                "determinism", "engine_capability_added", "evidence_file", "authorization",
                "authorization_state", "tests", "grid_results_descriptive_only"):
        dump(dec[key], f"decision.{key}")

    dump(dec["selection"], "decision.selection")
    dump(dec["stage_verdict"], "decision.stage_verdict")

    print("----- decision.gate_conditions (element shape) -----")
    first = next(iter(dec["gate_conditions"]))
    print(f"   first key {first}")
    dump(dec["gate_conditions"][first], f"gate_conditions[{first}]")
    print("   all rows:")
    for k, v in dec["gate_conditions"].items():
        print(f"      {k:32s} verdict={show(v.get('verdict'))}  keys={show(list(v))}")
    print()

    dump(dec["artifacts"], "decision.artifacts")
    dump(dec["frozen_inputs_read_only"], "decision.frozen_inputs_read_only")
    dump(dec["conflicts_found"], "decision.conflicts_found", width=150)
    dump(dec["limitations"], "decision.limitations", width=150)
    dump(dec["evidence"], "decision.evidence", width=150)
    dump(dec["blockers"], "decision.blockers")
    print(f"next_authorized_stage  {show(dec['next_authorized_stage'])[:300]}")
    print(f"live_trading_authorized {dec['live_trading_authorized']!r}")
    print()

    print("----- manifest.frozen_inputs element shape -----")
    fk = next(iter(man["frozen_inputs"]))
    print(f"   {fk} -> {show(man['frozen_inputs'][fk])}")
    pk = next(iter(man["produced_artifacts"]))
    print(f"   {pk} -> {show(man['produced_artifacts'][pk])}")
    print()

    run_id = dec["reproducibility"]["run_id"]
    run = json.loads((ROOT / "runs" / f"{run_id}.json").read_text(encoding="utf-8"))
    for key in ("date_range", "holdout_state", "notes", "output_artifact_hashes",
                "exit_status", "strategy_id", "universe_version", "stage", "command"):
        dump(run[key], f"run.{key}", width=150)

    print("----- checksum record -----")
    chk = ROOT / "reports/stage3_g2/STAGE_3_G2_ROTATION_RESEARCH.sha256"
    lines = chk.read_text(encoding="utf-8").splitlines()
    print(f"   {len(lines)} lines")
    for line in lines[:3]:
        print(f"   {show(line)}")
    print("   ...")
    for line in lines[-3:]:
        print(f"   {show(line)}")


if __name__ == "__main__":
    main()
