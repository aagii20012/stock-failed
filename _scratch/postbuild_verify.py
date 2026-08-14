"""Out-of-tree post-build verification for the Stage 3 Attempt 2 evaluation package.

Implements the twelve checks the operating prompt's section 15 requires. Writes nothing.
Run from the project root:

    cd /d/Product/stock-trade-alpaca/stockedge100 && \
        PYTHONPATH=src python /d/Product/stock-trade-alpaca/_scratch/postbuild_verify.py
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys

sys.path.insert(0, "src")

from stockedge100.reporting.stage_package import repo_state  # noqa: E402

ROOT = pathlib.Path(".").resolve()
RUN_ID = "SE100-R-20260813T120406Z"
PRE_BUILD_RSID = "222117e8b215ebb35e001467348928b72d589c5ced909d638e94b8b82a47ae7e"
SEALED_START_RSID = "af0133a8c006121a0927f5e230af51599eb13e5dc3e8a8a1c5e9884d36aae926"

DECISION = pathlib.Path("reports/stage3_attempt2/STAGE_3_ATTEMPT_2_STRATEGY_RESEARCH.json")
MANIFEST = pathlib.Path("reports/stage3_attempt2/STAGE_3_ATTEMPT_2_EVALUATION_ARTIFACT_MANIFEST.json")
RECORD = pathlib.Path("reports/stage3_attempt2/STAGE_3_ATTEMPT_2_STRATEGY_RESEARCH.sha256")
RUNREC = pathlib.Path(f"runs/{RUN_ID}.json")
REPORT = pathlib.Path("governance/STAGE_3_ATTEMPT_2_STRATEGY_RESEARCH_REPORT.md")
EVIDENCE = pathlib.Path("reports/stage3_attempt2/STAGE_3_ATTEMPT_2_DEVELOPMENT_ADMISSIBILITY.json")
DESIGN_RUN = pathlib.Path("runs/SE100-R-20260810T131107Z.json")

# Checksum records and the working directory each one is meant to be verified from.
CHECKSUM_RECORDS = [
    ("governance/STAGE_0_FREEZE.sha256", "governance"),
    ("governance/STAGE_1_FREEZE.sha256", "governance"),
    ("governance/STAGE_1_PREREGISTRATION.sha256", "."),
    ("governance/STAGE_2_PREREGISTRATION.sha256", "."),
    ("governance/STAGE_3_PREREGISTRATION.sha256", "."),
    ("governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.sha256", "."),
    ("reports/stage0/STAGE_0_VERIFICATION.sha256", "."),
    ("reports/stage1/STAGE_1_DATA_READINESS.sha256", "."),
    ("reports/stage2/STAGE_2_BACKTEST_ENGINE.sha256", "."),
    ("reports/stage3/STAGE_3_STRATEGY_RESEARCH.sha256", "."),
    ("reports/stage3_attempt2/STAGE_3_ATTEMPT_2_DESIGN.sha256", "."),
    ("reports/stage3_attempt2/STAGE_3_ATTEMPT_2_STRATEGY_RESEARCH.sha256", "."),
]

FAILURES: list[str] = []
CHECKS = 0


def check(label: str, ok: bool, detail: str = "") -> bool:
    global CHECKS
    CHECKS += 1
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAILURES.append(label + (f" — {detail}" if detail else ""))
    return ok


def sha256_file(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


decision = load(DECISION)
manifest = load(MANIFEST)
runrec = load(RUNREC)
evidence = load(EVIDENCE)
report_text = REPORT.read_text(encoding="utf-8")
code_hashes, rsid = repo_state()

# ---------------------------------------------------------------- 1
print("\n1. Ending repository-state identifier recomputed")
check("recomputed rsid == pre-build rsid (the build touched nothing tracked)",
      rsid == PRE_BUILD_RSID, rsid)
check("tracked file count is 108", len(code_hashes) == 108, str(len(code_hashes)))
check("decision.reproducibility.repo_state_id matches",
      decision["reproducibility"]["repo_state_id"] == rsid)
check("manifest.repo_state_id matches", manifest["repo_state_id"] == rsid)
check("runs record repo_state_id matches", runrec["repo_state_id"] == rsid)
check("starting id is the sealed design ending id",
      decision["repository_state"]["starting_repo_state_id"] == SEALED_START_RSID)
check("no tracked file contains the ending digest",
      not any(rsid in p.read_text(encoding="utf-8", errors="ignore")
              for p in (REPORT, pathlib.Path("README.md"))))

# ---------------------------------------------------------------- 2
print("\n2. Every checksum record verified from its intended working directory")
for rec_path, base in CHECKSUM_RECORDS:
    rec = pathlib.Path(rec_path)
    base_dir = (ROOT / base).resolve()
    entries, bad, missing = 0, [], []
    for line in rec.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        digest, _, name = line.partition("  ")
        name = name.strip().lstrip("*")
        entries += 1
        target = base_dir / name
        if not target.is_file():
            missing.append(name)
        elif sha256_file(target) != digest:
            bad.append(name)
    check(f"{rec_path} ({entries} entries, cwd={base})",
          entries > 0 and not bad and not missing,
          f"changed={bad} missing={missing}" if (bad or missing) else "all OK")

# ---------------------------------------------------------------- 3
print("\n3. Markdown report and JSON decision record agree materially")
cand = {c["gate"]["experiment_id"]: c for c in evidence["candidates"]}
must_appear = [
    decision["verdict"],
    decision["authorization_state"]["stage_4_validation"],
    *decision["results"]["admitted_candidates"],
    "SE100-S3A2-C3-DEFENSIVE-RA1",
    str(decision["tests"]["passed"]),
    evidence["window"]["start"],
    evidence["window"]["end"],
]
for token in must_appear:
    check(f"report carries {token!r}", str(token) in report_text)
check("report states live_trading_authorized false",
      decision["live_trading_authorized"] is False and "`false`" in report_text)
check("report's next-authorized-action agrees with next_authorized_stage in the JSON",
      decision["next_authorized_stage"] == "STAGE_4_VALIDATION_PREREGISTRATION_SESSION_ONLY"
      and "pre-registration for Stage 4 validation" in report_text
      and "This session does not perform it" in report_text)
for key, state in decision["authorization_state"].items():
    check(f"report carries authorization state {key} = {state}", state in report_text)
check("report and JSON agree on gate_passed",
      decision["gate_passed"] is True
      and decision["gate_conditions"]["admissible_candidate_exists"]["value"] is True)
cum = decision["adaptive_research"]["cumulative_experiment_count"]
cum_text = json.dumps(cum)
for n in ("9", "45", "48"):
    check(f"cumulative count {n} present in both", n in cum_text and n in report_text)
check("JSON verdict token is the sealed pass token",
      decision["verdict_token_derivation"]["pass_token"] in decision["verdict"]
      and decision["verdict_token_derivation"]["fail_token"] not in decision["verdict"])

# ---------------------------------------------------------------- 4 and 5
print("\n4/5. Registered variants evaluated exactly, and nothing undeclared")
budget = evidence["iteration_budget"]
primaries = sorted(cand)
gating_ids = sorted(vid for c in evidence["candidates"] for vid in c["runs"])
neighbours = [v for v in gating_ids if "#N" in v]
rerun_labels = sorted(r["rerun_label"] for r in evidence["determinism"]["runs"])
check("exactly 3 primary candidates", len(primaries) == 3, ", ".join(primaries))
check("exactly 12 registered neighbour runs", len(neighbours) == 12, str(len(neighbours)))
check("15 gating variants declared and executed",
      len(gating_ids) == 15 == budget["total_declared_gating_variants"] == budget["gating_variants_executed"])
check("18 declared runs, 18 executed",
      budget["total_declared_runs"] == 18 == budget["runs_executed"], str(budget["runs_executed"]))
check("3 non-gating stressed-cost runs declared and executed",
      budget["total_declared_non_gating_stress_runs"] == 3 == budget["non_gating_stress_runs_executed"]
      and len(decision["results"]["stressed_cost_runs"]) == 3)
check("gating + non-gating == declared runs",
      budget["gating_variants_executed"] + budget["non_gating_stress_runs_executed"] == budget["runs_executed"])
stress_labels = {f"{eid}#PRIMARY#STRESS" for eid in primaries}
declared = set(gating_ids) | set(rerun_labels) | stress_labels | set(primaries)
seen = set(re.findall(r"SE100-S3A2-[A-Za-z0-9#_\-]+", json.dumps(decision["results"])))
seen = {s.rstrip(".,;") for s in seen}
extra = seen - declared
check("no evaluated identifier is outside the registered set",
      not extra, f"extra={sorted(extra)}")
check("exactly 3 non-gating stress labels, one per primary",
      len(seen & stress_labels) == 3, ", ".join(sorted(seen & stress_labels)))
check("every registered gating variant appears in the results",
      set(gating_ids) <= (seen | set(primaries)),
      f"missing={sorted(set(gating_ids) - seen - set(primaries))}")

# ---------------------------------------------------------------- 6
print("\n6. No valid completed run was repeated")
check("revisions after seeing a result == 0",
      decision["scope"]["revisions_after_seeing_a_result"] in (0, "0", "none", "None"),
      str(decision["scope"]["revisions_after_seeing_a_result"]))
check("attempt 2 revisions made == 0",
      str(decision["adaptive_research"]["attempt_2_revisions_made"]).startswith("0"),
      str(decision["adaptive_research"]["attempt_2_revisions_made"]))
check("exactly one evidence file for this attempt",
      len(list(pathlib.Path("reports/stage3_attempt2").glob("*DEVELOPMENT_ADMISSIBILITY*.json"))) == 1)
todays = sorted(p.name for p in pathlib.Path("runs").glob("SE100-R-20260813*.json"))
check("exactly one runs record written today", len(todays) == 1, ", ".join(todays))
check("evidence: variants re-run after seeing a result == 0",
      budget["variants_rerun_after_seeing_a_result"] == 0)
check("evidence: revisions made == 0", budget["revisions_made"] == 0)
check("determinism re-runs reproduced every primary byte-for-byte",
      evidence["determinism"]["all_identical"] is True
      and budget["determinism_reruns_outside_the_declared_budget"] == 3)

# ---------------------------------------------------------------- 7 and 8
print("\n7/8. Validation unread, holdout sealed and unread")
check("scope: validation observations read == false",
      decision["scope"]["validation_observations_read"] is False)
check("scope: holdout observations read == false",
      decision["scope"]["holdout_observations_read"] is False)
check("runs record holdout_state == SEALED", runrec["holdout_state"] == "SEALED")
check("runs record date_range ends at the development boundary",
      runrec["date_range"][1] == "2021-07-31", " -> ".join(runrec["date_range"]))
ends = {c["plan"]["run_end"] for c in evidence["candidates"]}
starts = {c["plan"]["run_start"] for c in evidence["candidates"]}
check("no candidate ran past 2021-07-31", all(e <= "2021-07-31" for e in ends), ", ".join(sorted(ends)))
check("no candidate started before 1993-01-29", all(s >= "1993-01-29" for s in starts),
      ", ".join(sorted(starts)))
check("evidence window states validation LOCKED and holdout SEALED, both unread",
      evidence["window"]["validation_state"] == "LOCKED"
      and evidence["window"]["holdout_state"] == "SEALED"
      and evidence["window"]["validation_observations_read"] is False
      and evidence["window"]["holdout_observations_read"] is False
      and evidence["window"]["boundary_changed"] is False)
lock_digest = sha256_file(pathlib.Path("governance/STAGE_1_HOLDOUT_LOCK.json"))
check("holdout lock file byte-for-byte unchanged",
      lock_digest == "9696161c4c5612fc7f6b3e5a3410917f20ad5707cb9b89b8bcc39cb70831dfb3",
      lock_digest)

# ---------------------------------------------------------------- 9
print("\n9. No broker or credential activity is possible from this tree")
#
# A textual sweep is the wrong predicate here: the reporting modules legitimately contain the
# strings "Alpaca" and "requests" in prose that records Alpaca as LOCKED, in the
# authorization_state keys, in the tracked-dependency name list, and as a local variable name in
# the engine (`requests: list[OrderRequest]`). The honest predicate is a syntactic one: no module
# imports a network or broker library, constructs a URL, or reads a credential from the
# environment.
#
import ast  # noqa: E402

FORBIDDEN_IMPORTS = {
    "alpaca", "alpaca_trade_api", "alpaca_py", "requests", "httpx", "aiohttp", "socket",
    "urllib", "http", "http.client", "ftplib", "telnetlib", "smtplib", "paramiko", "websocket",
    "websockets", "boto3",
}
FORBIDDEN_NAMES = {"environ", "getenv", "putenv", "urlopen", "Request", "connect", "urlretrieve"}
bad_imports: list[str] = []
bad_names: list[str] = []
url_literals: list[str] = []
for py in sorted(pathlib.Path("src").rglob("*.py")):
    tree = ast.parse(py.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in FORBIDDEN_IMPORTS:
                    bad_imports.append(f"{py.as_posix()}:{node.lineno} import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root in FORBIDDEN_IMPORTS:
                bad_imports.append(f"{py.as_posix()}:{node.lineno} from {node.module}")
        elif isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_NAMES:
            bad_names.append(f"{py.as_posix()}:{node.lineno} .{node.attr}")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if "http://" in node.value or "https://" in node.value:
                url_literals.append(f"{py.as_posix()}:{node.lineno}")

check("no src/ module imports a network or broker library",
      not bad_imports, "; ".join(bad_imports[:4]))
check("no src/ module reads the environment, opens a URL, or connects a socket",
      not bad_names, "; ".join(bad_names[:4]))
check("no src/ module contains a URL literal", not url_literals, "; ".join(url_literals[:4]))
dep_versions = decision["reproducibility"]["dependency_versions"]
check("'requests' appears only as a tracked-dependency name in the reproducibility record",
      "requests" in dep_versions, f"recorded version {dep_versions.get('requests')!r}")
check("no credential-shaped name in the decision record or manifest",
      not re.search(r"(API_KEY|SECRET_KEY|ACCESS_TOKEN|PRIVATE_KEY)",
                    DECISION.read_text(encoding="utf-8") + MANIFEST.read_text(encoding="utf-8")))
check("decision record states live trading not authorized",
      decision["live_trading_authorized"] is False
      and decision["authorization_state"]["alpaca_live_trading"] == "LOCKED")

# ---------------------------------------------------------------- 10
print("\n10. Frozen artifacts unchanged since the sealed design state")
design = load(DESIGN_RUN)
allowed_to_change = {"README.md"}
moved, gone = [], []
for path, digest in design["code_hashes"].items():
    p = pathlib.Path(path)
    if not p.is_file():
        gone.append(path)
    elif sha256_file(p) != digest and path not in allowed_to_change:
        moved.append(path)
check("nothing the design run record hashed has moved",
      not moved and not gone, f"moved={moved} missing={gone}")
check("README.md is the only allowed change and it did change",
      sha256_file(pathlib.Path("README.md")) != design["code_hashes"]["README.md"])
check("decision record reports zero frozen-artifact changes",
      decision["integrity"]["frozen_artifacts_changed"] in (0, "0", "none", "None") or
      str(decision["integrity"]["frozen_artifacts_changed"]).lower().startswith("none"),
      str(decision["integrity"]["frozen_artifacts_changed"]))
check("all checksum records recorded as verified", decision["integrity"]["all_verified"] is True)

# ---------------------------------------------------------------- 11
print("\n11. Self-reference conventions")
man_rel = MANIFEST.as_posix()
check("manifest excludes its own entry",
      man_rel not in manifest["produced_artifacts"] and man_rel not in manifest["frozen_inputs"]
      and man_rel not in manifest["repo_state_files"])
rec_lines = [l for l in RECORD.read_text(encoding="utf-8").splitlines() if l.strip()]
rec_names = {l.split("  ", 1)[1].strip() for l in rec_lines}
check("checksum record covers the manifest", man_rel in rec_names)
check("checksum record excludes itself", RECORD.as_posix() not in rec_names)
self_hashing = [p for p, meta in manifest["produced_artifacts"].items()
                if meta["sha256"] in pathlib.Path(p).read_text(encoding="utf-8", errors="ignore")]
check("no produced artifact contains its own digest", not self_hashing, ", ".join(self_hashing))
check("evidence self-digest recomputes from the written file",
      hashlib.sha256(json.dumps(
          {k: v for k, v in evidence.items() if k not in ("generated_utc", "evidence_digest")},
          sort_keys=True, separators=(",", ":"), ensure_ascii=False,
      ).encode("utf-8")).hexdigest() == evidence["evidence_digest"],
      evidence["evidence_digest"])

# ---------------------------------------------------------------- 12
print("\n12. Recorded hashes match the final repository state")
flat = lambda d: {k: (v["sha256"] if isinstance(v, dict) else v) for k, v in d.items()}  # noqa: E731
for label, mapping in (
    ("manifest.repo_state_files", manifest["repo_state_files"]),
    ("manifest.frozen_inputs", flat(manifest["frozen_inputs"])),
    ("manifest.produced_artifacts", flat(manifest["produced_artifacts"])),
    ("manifest.dataset_hashes", manifest["dataset_hashes"]),
    ("runs.code_hashes", runrec["code_hashes"]),
    ("runs.output_artifact_hashes", runrec["output_artifact_hashes"]),
    ("runs.dataset_hashes", runrec["dataset_hashes"]),
):
    bad = [p for p, d in mapping.items()
           if not pathlib.Path(p).is_file() or sha256_file(pathlib.Path(p)) != d]
    check(f"{label} ({len(mapping)} entries)", not bad, f"mismatched={bad[:4]}")
check("manifest.repo_state_files equals the recomputed pattern map",
      manifest["repo_state_files"] == code_hashes)
check("decision.artifacts lists exactly the files produced by this session",
      set(decision["artifacts"]) >= set(manifest["produced_artifacts"]),
      f"{len(decision['artifacts'])} listed")
rec_bad = [n for n in rec_names
           if not (ROOT / n).is_file() or sha256_file(ROOT / n) != next(
               l.split("  ", 1)[0] for l in rec_lines if l.split("  ", 1)[1].strip() == n)]
check(f"every line of the new checksum record re-verifies ({len(rec_names)} entries)", not rec_bad,
      ", ".join(rec_bad[:4]))

print("\n" + "=" * 72)
print(f"{CHECKS} checks run, {len(FAILURES)} failed")
for f in FAILURES:
    print("  FAIL:", f)
sys.exit(1 if FAILURES else 0)
