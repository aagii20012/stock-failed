"""Third-level enumeration: the nested blocks and the exact value TYPES the verifier compares.

ASCII only. authorization_state printed as lowercase 'false' at level 2, which str(False) never
produces -- so those are strings, not booleans, and a predicate written as `is False` would fail on a
package that is correct. Types are printed here so that never has to be guessed.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
DEC = ROOT / "reports/stage3_g2/STAGE_3_G2_ROTATION_RESEARCH.json"


def show(s) -> str:
    return str(s).encode("ascii", "backslashreplace").decode("ascii")


def dump(node, name: str, width: int = 130) -> None:
    print(f"----- {name} -----")
    if isinstance(node, dict):
        for k, v in node.items():
            print(f"   {k:44s} {type(v).__name__:5s} {show(v)[:width]}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            print(f"   [{i}] {type(v).__name__:5s} {show(v)[:width]}")
    else:
        print(f"   {type(node).__name__} {show(node)[:width]}")
    print()


def main() -> None:
    dec = json.loads(DEC.read_text(encoding="utf-8"))

    dump(dec["authorization_state"], "authorization_state (TYPES)")
    dump(dec["partition"]["partition"], "partition.partition")
    dump(dec["partition"]["window_read_by_this_stage"], "partition.window_read_by_this_stage")
    dump(dec["partition"]["lock_record_verification"], "partition.lock_record_verification")
    dump(dec["preregistration"]["protocol_record_verification"],
         "preregistration.protocol_record_verification")
    dump(dec["preregistration"]["grid"], "preregistration.grid")
    dump(dec["constitution"]["freeze_verification"], "constitution.freeze_verification")
    dump(dec["universe"]["re_check"], "universe.re_check")
    dump(dec["selection"]["step_1"], "selection.step_1")
    dump(dec["selection"]["no_candidate_path"], "selection.no_candidate_path")
    dump(dec["gate_conditions"]["admissible_candidate_exists"],
         "gate_conditions.admissible_candidate_exists")
    dump(dec["generation"]["what_changed_from_generation_1"],
         "generation.what_changed_from_generation_1")
    dump(dec["grid_results_descriptive_only"]["status"], "grid_results_descriptive_only.status")
    dump(dec["authorization"]["explicit_non_authorizations"],
         "authorization.explicit_non_authorizations")
    dump(dec["grid_results_descriptive_only"]["table"][0],
         "grid_results_descriptive_only.table[0]")
    dump(dec["selection"]["inputs"][0], "selection.inputs[0]")
    dump(dec["reproducibility"]["dependency_versions"], "reproducibility.dependency_versions")

    print("----- gate_conditions S3-C1..C7 required_verbatim -----")
    for k, v in dec["gate_conditions"].items():
        if k.startswith("S3-C"):
            print(f"   {k}  {show(v['required_verbatim'])[:110]}")


if __name__ == "__main__":
    main()
