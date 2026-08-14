"""Dry-run the Stage 3 Attempt 2 evaluation package builder without letting it write anything.

build_stage_package is replaced with a stub that captures the StageDecision, so every guard, every
recomputation and the whole assembled gate-conditions block can be inspected before the real build
records a repo_state_id that a later fix would invalidate.

PYTEST_OUTPUT is pointed at an out-of-tree stand-in with reconciling counts, because the real capture
does not exist yet. Nothing here is part of the repository state.
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path

SCRATCH = Path(r"d:\Product\stock-trade-alpaca\_scratch")
sys.path.insert(0, r"d:\Product\stock-trade-alpaca\stockedge100\src")

from stockedge100.reporting import stage3_attempt2_evaluation_package as mod  # noqa: E402

CAPTURED = {}


@dataclass
class FakeResult:
    run_id: str = "SE100-R-DRYRUN"
    repo_state_id: str = "<not computed in a dry run>"
    timestamp_utc: str = "<not read in a dry run>"
    freeze_ok: bool = True
    decision_path: Path = mod.PROJECT_ROOT / "reports/stage3_attempt2/DRYRUN.json"
    manifest_path: Path = mod.PROJECT_ROOT / "reports/stage3_attempt2/DRYRUN_MANIFEST.json"
    checksum_path: Path = mod.PROJECT_ROOT / "reports/stage3_attempt2/DRYRUN.sha256"
    run_record_path: Path = mod.PROJECT_ROOT / "runs/DRYRUN.json"


def stub(decision):
    CAPTURED["decision"] = decision
    return FakeResult()


mod.build_stage_package = stub
if "--real-capture" not in sys.argv:
    mod.PYTEST_OUTPUT = "../_scratch/fake_pytest_capture.txt"

print("=== source safety scan ===")
source = (
    Path(r"d:\Product\stock-trade-alpaca\stockedge100\src\stockedge100\reporting")
    / "stage3_attempt2_evaluation_package.py"
).read_text(encoding="utf-8")
for needle in ("0.15", "require_seal", "ALPACA", "API_KEY", "SECRET", "0.14"):
    print(f"  {needle!r:16} occurrences: {source.count(needle)}")
print(f"  lines: {len(source.splitlines())}")

print("\n=== build() ===")
rc = mod.build()
print(f"  return code: {rc}")

if "decision" not in CAPTURED:
    print("  NO DECISION CAPTURED — a guard refused before assembly")
    raise SystemExit(rc)

d = CAPTURED["decision"]

print("\n=== identity ===")
for name in (
    "stage",
    "stage_slug",
    "decision_basename",
    "manifest_basename",
    "gate_id",
    "gate_name",
    "verdict",
    "gate_passed",
    "next_authorized_stage",
    "universe_version",
    "holdout_state",
    "config_hash",
    "random_seed",
):
    print(f"  {name:22} {getattr(d, name)}")
print(f"  date_range             {d.date_range}")
print(f"  tests                  {d.tests}")
print(f"  command                {d.command}")

print("\n=== assembled gate conditions (diff this against the report's gate table) ===")
for cid, entry in d.gate_conditions.items():
    print(f"\n  {cid}: {entry['verdict']}")
    print(f"    required: {entry['required'][:150]}")
    if cid == "admissible_candidate_exists":
        print(f"    value:               {entry['value']}")
        print(f"    within_candidate:    {entry['within_candidate']}")
        print(f"    across_candidates:   {entry['across_candidates']}")
        print(f"    admitted:            {entry['evidence']['admitted_candidates']}")
        print(f"    gate_verdict_token:  {entry['evidence']['gate_verdict_token']}")
        print(f"    candidates_evaluated {entry['evidence']['candidates_evaluated']}")
        continue
    print(f"    satisfied_by:        {entry['satisfied_by']}")
    print(f"    met_by:              {entry['met_by']}")
    print(f"    not_met_by:          {entry['not_met_by']}")
    print(f"    not_evaluable_for:   {entry['not_evaluable_for']}")
    print(f"    not_applicable_for:  {entry['not_applicable_for']}")
    print(f"    candidates_evaluated {entry['candidates_evaluated']}")
    print(f"    aggregated_on:       {entry['aggregated_on'][:110]}")
    for eid, per in entry["evidence"]["per_candidate"].items():
        print(
            f"      {eid:34} {per['verdict']:32} satisfied={per['satisfied']!s:5} "
            f"measured={str(per['measured'])[:26]:28} threshold={str(per['threshold'])[:22]}"
        )
    print(f"    sealed spec keys: {list(entry['evidence']['sealed_measurement_specification'])}")

print("\n=== body top-level keys ===")
for key, value in d.body.items():
    kind = type(value).__name__
    size = len(value) if isinstance(value, (dict, list, str)) else ""
    print(f"  {key:34} {kind}[{size}]")

print("\n=== body.verdict_token_derivation ===")
print(json.dumps(d.body["verdict_token_derivation"], indent=2))

print("\n=== body.repository_state ===")
print(json.dumps(d.body["repository_state"], indent=2))

print("\n=== body.independent_recomputation ===")
print(json.dumps(d.body["independent_recomputation"], indent=2))

print("\n=== body.results.per_candidate_primary ===")
for eid, block in d.body["results"]["per_candidate_primary"].items():
    print(f"  {eid}")
    for key in (
        "family",
        "declared_universe",
        "run_start",
        "run_end",
        "total_return",
        "deepest_drawdown_4dp",
        "profit_factor",
        "closed_trades",
        "shutdown_session",
        "open_positions_at_end",
        "admitted",
        "conditions_met",
        "conditions_not_met",
        "conditions_not_applicable",
    ):
        print(f"    {key:26} {block[key]}")

print("\n=== body.results.all_registered_variants ===")
for vid, row in d.body["results"]["all_registered_variants"].items():
    print(
        f"  {vid:44} {row['role']:9} gating={row['gating']!s:5} "
        f"ret={str(row['total_return']):<24} dd={row['deepest_drawdown_4dp']:<8} "
        f"pf={str(row['profit_factor'])[:7]:<8} trades={row['closed_trades']:<5} "
        f"shutdown={row['shutdown_session']}"
    )
print(f"  rows: {len(d.body['results']['all_registered_variants'])}")

print("\n=== body.test_execution ===")
print(json.dumps(d.body["test_execution"], indent=2))

print("\n=== body.integrity.checksum_records_verified ===")
for rel, block in d.body["integrity"]["checksum_records_verified"].items():
    states = sorted(set(block["entries"].values()))
    print(f"  {rel:58} from {block['working_directory']:26} {len(block['entries'])} entries {states}")

print("\n=== evidence ===")
for i, line in enumerate(d.evidence, 1):
    print(f"  [{i}] {line}")

print("\n=== limitations ===")
for i, line in enumerate(d.limitations, 1):
    print(f"  [{i}] {line}")

print("\n=== conflicts_found ===")
for i, line in enumerate(d.conflicts_found, 1):
    print(f"  [{i}] {line}")

print(f"\n=== blockers === {d.blockers}")

print("\n=== authorization_state ===")
for key, value in d.authorization_state.items():
    print(f"  {key:44} {value}")

print("\n=== produced ===")
for name in d.produced:
    exists = (mod.PROJECT_ROOT / name).is_file()
    print(f"  {'EXISTS ' if exists else 'MISSING'} {name}")

print("\n=== frozen_inputs ===")
missing = [n for n in d.frozen_inputs if not (mod.PROJECT_ROOT / n).is_file()]
print(f"  {len(d.frozen_inputs)} declared, {len(missing)} missing")
for name in missing:
    print(f"  MISSING {name}")

print("\n=== dataset_hashes ===")
for key, value in d.dataset_hashes.items():
    print(f"  {key:46} {value}")

print("\n=== run_notes ===")
for i, line in enumerate(d.run_notes, 1):
    print(f"  [{i}] {line}")

print("\n=== serialisation check ===")
blob = json.dumps({**d.body, "gate_conditions": d.gate_conditions}, indent=2, sort_keys=False)
print(f"  body + gate_conditions serialise to {len(blob)} bytes")
print(f"  non-ascii characters: {sum(1 for ch in blob if ord(ch) > 127)}")

print("\n=== nothing was written ===")
for name in ("DRYRUN.json", "DRYRUN_MANIFEST.json", "DRYRUN.sha256"):
    print(f"  {name}: exists={(mod.PROJECT_ROOT / 'reports/stage3_attempt2' / name).exists()}")
print(f"  runs/DRYRUN.json: exists={(mod.PROJECT_ROOT / 'runs/DRYRUN.json').exists()}")
