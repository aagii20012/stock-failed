"""Dry-run the Attempt 2 sealer without letting it write anything.

The sealer lives in src/, which is a repo_state_id pattern. A defect found after it has written its
record cannot be repaired without invalidating the digest that record carries, so every check it
performs is exercised here first, against the real artifacts, with the three write paths -- the JSON
record, the .sha256 record, and the runs/ record -- replaced by capturing stubs.

Two things this proves that reading the module cannot:
  - each check function returns an empty problem list against the artifacts as they actually are;
  - the record the sealer would write is assembled without raising, and its shape can be inspected
    before it is committed to disk.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1] / "stockedge100"
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.reporting import g2_rotation_ra1_preregistration as S  # noqa: E402

FAILED = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global FAILED
    if not ok:
        FAILED += 1
    print("  %-4s %s%s" % ("ok" if ok else "FAIL", label, ("  <- " + detail) if detail else ""))


def report(label: str, problems: list[str]) -> None:
    check("%s: no problems" % label, not problems, "%d problem(s)" % len(problems))
    for problem in problems:
        print("       - %s" % problem)


print("=== 0. the sealer does not name the candidate it seals ===")
source = (ROOT / "src/stockedge100/reporting/g2_rotation_ra1_preregistration.py").read_text(
    encoding="utf-8"
)
protocol = json.loads((ROOT / "config/generation_2/g2_rotation_ra1_protocol.json").read_text("utf-8"))
criteria = json.loads((ROOT / "config/generation_2/g2_gate_criteria_ra1.json").read_text("utf-8"))
strategy = protocol["strategy_id"]
check("strategy_id loads from config", S.candidate_id(protocol) == strategy, strategy)
check("sealer source does not contain the candidate id", strategy not in source)
check("sealer source does not contain the variant id template",
      protocol["grid"]["variant_id_format"] not in source)

print()
print("=== 1. seal-once, and the outputs are absent ===")
check("RECORD_JSON absent", not S.RECORD_JSON.exists(), str(S.RECORD_JSON))
check("RECORD_SHA absent", not S.RECORD_SHA.exists(), str(S.RECORD_SHA))
check("RECORD_MD present", S.RECORD_MD.exists())
for name in ("PROTOCOL_CONFIG", "CRITERIA_CONFIG", "COST_CONFIG", "ATTEMPT_1_SHA"):
    path = getattr(S, name)
    check("prerequisite present: %s" % path.name, path.exists())

print()
print("=== 2. frozen records this seal depends on ===")
ok, _ = S.verify_stage0_freeze()
check("Stage 0 freeze verifies", ok)
stage1 = S.verify_sha256_record(S.PROJECT_ROOT / "governance/STAGE_1_FREEZE.sha256",
                                root=S.PROJECT_ROOT / "governance")
check("STAGE_1_FREEZE verifies (%d entries)" % len(stage1),
      bool(stage1) and all(v == "OK" for v in stage1.values()))
lock = S.verify_sha256_record(S.PARTITION_LOCK_SHA, root=S.PROJECT_ROOT)
check("partition lock record verifies (%d entries)" % len(lock),
      bool(lock) and all(v == "OK" for v in lock.values()))
a1 = S.verify_sha256_record(S.ATTEMPT_1_SHA, root=S.PROJECT_ROOT)
check("Attempt 1 pre-registration record verifies (%d entries)" % len(a1),
      bool(a1) and all(v == "OK" for v in a1.values()))
for name, state in sorted(a1.items()):
    print("       %-72s %s" % (name, state))

print()
print("=== 3. contamination, content-based, plus Attempt 1 immutability ===")
contamination = S.measure_contamination(protocol)
report("contamination", S.contamination_problems(contamination))
check("the scan read a non-trivial number of .py files",
      contamination["python_files_scanned"] > 50, str(contamination["python_files_scanned"]))
check("zero src modules name the candidate",
      contamination["modules_naming_this_candidate_count"] == 0)
check("zero tests name the candidate",
      contamination["tests_naming_this_candidate_count"] == 0)
check("nine Attempt 1 modules re-hashed",
      len(contamination["attempt_1_module_digests"]) == 9,
      str(len(contamination["attempt_1_module_digests"])))
check("nine Attempt 1 artifacts re-hashed",
      len(contamination["attempt_1_artifact_digests"]) == 9,
      str(len(contamination["attempt_1_artifact_digests"])))
check("no Attempt 1 module moved", not contamination["attempt_1_modules_that_moved"])
check("no Attempt 1 artifact moved", not contamination["attempt_1_artifacts_that_moved"])
print("       immutability source: %s" % contamination["attempt_1_immutability_source"])

print()
print("=== 3b. the immutability check is not vacuous ===")
# A digest comparison that compares nothing passes. Perturb one module in memory and require the
# check to notice; the file on disk is never touched.
target = protocol["attempt_1_modules_immutable"]["modules"][0]
real_read = S.sha256_file


def poisoned(path):
    if path == S.PROJECT_ROOT / target:
        return "0" * 64
    return real_read(path)


S.sha256_file = poisoned
try:
    poisoned_measure = S.measure_contamination(protocol)
    problems = S.contamination_problems(poisoned_measure)
finally:
    S.sha256_file = real_read
check("a perturbed Attempt 1 module digest is detected",
      any(target in p for p in problems), "%d problem(s)" % len(problems))
check("the file on disk is untouched", real_read(S.PROJECT_ROOT / target) ==
      contamination["attempt_1_module_digests"][target])

print()
print("=== 4. measured span, and config agreement ===")
span = S.measure_span()
check("session lists agree", span["session_lists_agree"])
print("       run %s -> %s, %d sessions, binding %s @ %s"
      % (span["run_start"], span["run_end"], span["run_sessions"],
         span["binding_symbol"], span["binding_symbol_inception"]))
report("config agreement", S.check_config_agreement(protocol, span))
report("criteria agreement", S.check_criteria_agreement(criteria, protocol))

print()
print("=== 5. markdown agreement ===")
report("document agreement", S.check_document_agreement(
    S.RECORD_MD.read_text(encoding="utf-8"), protocol, span))

print()
print("=== 6. grid recomputed independently of the config ===")
grid = S.enumerate_grid(protocol)
check("eighteen variants", len(grid) == 18, str(len(grid)))
check("ids unique", len({r["variant_id"] for r in grid}) == 18)
declared = protocol["grid"]["variants"]
check("recomputed ids equal the sealed ids in order",
      [r["variant_id"] for r in grid] == [v["variant_id"] for v in declared])
ceiling = S.exposure_ceiling(protocol)
conc = S.concentration_ceiling(protocol)
for k in (1, 2, 3):
    w = S.target_weight(k, ceiling, conc)
    g = w * k
    check("k=%d aggregate target gross %.9f <= RA2-1 ceiling %s" % (k, g, ceiling), g <= ceiling)

print()
print("=== 7. build() end to end, with every write path stubbed ===")
written: dict[str, object] = {}


class StubPath:
    def __init__(self, real):
        self.real = real

    def write_text(self, text, encoding=None):
        written["json"] = text

    @property
    def parent(self):
        class P:
            def mkdir(self, **kw):
                written["mkdir"] = True
        return P()

    def exists(self):
        return False

    def relative_to(self, other):
        return self.real.relative_to(other)


class StubRun:
    def __init__(self, **kw):
        written["run"] = kw

    def write(self, directory):
        written["run_dir"] = str(directory)


S.RECORD_JSON = StubPath(S.RECORD_JSON.real if isinstance(S.RECORD_JSON, StubPath) else S.RECORD_JSON)
real_sha = S.sha256_file


def sha_or_stub(path):
    if isinstance(path, StubPath):
        return "f" * 64
    return real_sha(path)


S.sha256_file = sha_or_stub
S.write_sha256_record = lambda covered, target: (written.setdefault("covered", covered), "e" * 64)[1]
S.RunRecord = StubRun

code = S.build()
S.sha256_file = real_sha
print()
check("build() returned 0", code == 0, "exit %d" % code)
check("nothing was written to governance/", not S.RECORD_SHA.exists())
check("a JSON record was assembled", "json" in written)
check("a runs/ record was assembled", "run" in written)

if "json" in written:
    record = json.loads(written["json"])
    print()
    print("=== 8. the record the sealer would write ===")
    print("       %d top-level keys, %d bytes" % (len(record), len(written["json"])))
    check("artifact_id", record["artifact_id"] == "SE100-GOV-2005", record["artifact_id"])
    check("attempt is 2", record["attempt"] == 2)
    check("status SEALED", record["status"] == "SEALED")
    check("sealed_before_any_strategy_code true", record["sealed_before_any_strategy_code"] is True)
    check("sealed_before_any_result_was_seen FALSE and stated",
          record["sealed_before_any_result_was_seen"] is False)
    check("live_trading_authorized false", record["live_trading_authorized"] is False)
    check("stage_4_authorized false", record["stage_4_authorized"] is False)
    check("holdout_read_authorized false", record["holdout_read_authorized"] is False)
    check("adaptation disclosure carried verbatim",
          record["adaptation_disclosure"] == protocol["adaptation_disclosure_verbatim"])
    check("adaptation disclosure keeps its em dashes",
          record["adaptation_disclosure"].count("—") ==
          protocol["adaptation_disclosure_verbatim"].count("—"))
    check("eighteen variants in the record", len(record["grid"]["variants"]) == 18)
    check("total runs is 36", record["grid"]["total_runs"] == 36)
    check("nine module digests recorded",
          len(record["contamination_measurement"]["attempt_1_module_digests"]) == 9)
    check("no repo_state_id value in the record body",
          not __import__("re").search(r'"repo_state_id"\s*:\s*"[0-9a-f]{64}"', written["json"]))
    check("repo_state_id_location points at the runs/ record",
          "runs/" in record["repo_state_id_location"])
    check("both verdict tokens carried", record["gate"]["pass_token"] != record["gate"]["fail_token"])
    print("       pass %s" % record["gate"]["pass_token"])
    print("       fail %s" % record["gate"]["fail_token"])
    check("seventeen conflicts carried", len(record["conflicts_found"]) == 17,
          str(len(record["conflicts_found"])))
    check("nine binding rules", len(record["binding_rules"]) == 9, str(len(record["binding_rules"])))

if "covered" in written:
    print()
    print("=== 9. the .sha256 record's covered set ===")
    covered = written["covered"]
    check("five files covered", len(covered) == 5, str(len(covered)))
    for name in sorted(covered):
        print("       %s" % name)
    check("the record does not cover itself",
          not any(n.endswith("STAGE_3_G2_ROTATION_RA1_PROTOCOL.sha256") for n in covered))

if "run" in written:
    print()
    print("=== 10. the runs/ record ===")
    run = written["run"]
    check("holdout_state SEALED", run["holdout_state"] == "SEALED")
    check("random_seed None", run["random_seed"] is None)
    check("exit_status SEALED", run["exit_status"] == "SEALED")
    check("strategy_id is this candidate", run["strategy_id"] == strategy)
    check("date_range is the development window", run["date_range"] == ["1993-01-29", "2021-07-31"],
          str(run["date_range"]))
    check("34 dataset hashes", len(run["dataset_hashes"]) == 34, str(len(run["dataset_hashes"])))
    check("repo_state_id present", len(run["repo_state_id"]) == 64)
    check("notes mention Stage 4 is not authorized",
          any("Stage 4 validation is not authorized" in n for n in run["notes"]))
    check("notes disclose the post-hoc design",
          any("after Attempt 1's development results were known" in n for n in run["notes"]))

print()
print("=" * 96)
print("DRY RUN %s -- %d failed" % ("CLEAN" if FAILED == 0 else "HAS PROBLEMS", FAILED))
