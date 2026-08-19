"""Dry-run the Attempt 3 sealer with all three of its outputs redirected out of the governed tree.

The sealer is in src/, and it seals once: a defect found after the real run cannot be repaired,
because the seal-once guard refuses to regenerate and the constitution refuses to edit a sealed
artifact in place.  So every code path -- including the record dict, where a bad key lands *after*
the JSON is on disk -- is exercised here first, against _scratch paths that no digest covers.

Redirecting the module globals rather than the filesystem is deliberate: build() reads RECORD_JSON,
RECORD_SHA and RUNS_DIR out of its own module namespace, so rebinding those three names moves every
write and leaves every read pointing at the real, frozen inputs.
"""

import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
OUT = pathlib.Path("d:/Product/stock-trade-alpaca/_scratch/dryrun")
sys.path.insert(0, str(ROOT / "src"))

if OUT.exists():
    shutil.rmtree(OUT)
(OUT / "runs").mkdir(parents=True)

from stockedge100.reporting import g2_rotation_ra3_preregistration as sealer  # noqa: E402

# The predicate this attempt's own sealer must satisfy, checked against the real file on disk before
# anything else: a sealer that names the candidate falsifies the precondition it is about to record.
own = (ROOT / "src/stockedge100/reporting/g2_rotation_ra3_preregistration.py").read_text("utf-8")
protocol = json.loads((ROOT / "config/generation_2/g2_rotation_ra3_protocol.json").read_text("utf-8"))
strategy = protocol["strategy_id"]
print("sealer names the candidate id:  %s" % (strategy in own))
assert strategy not in own, "the sealer contains the literal candidate id"

print("real .json exists: %s   real .sha256 exists: %s"
      % (sealer.RECORD_JSON.exists(), sealer.RECORD_SHA.exists()))
print("real .md   exists: %s" % sealer.RECORD_MD.exists())

sealer.RECORD_JSON = OUT / "STAGE_3_G2_ROTATION_RA3_PROTOCOL.json"
sealer.RECORD_SHA = OUT / "STAGE_3_G2_ROTATION_RA3_PROTOCOL.sha256"

# RUNS_DIR is *read* three times before it is written once -- both prior development records are
# located there, and it is swept for any record already naming this candidate -- so rebinding it
# starves the immutability check instead of redirecting the write.  The first attempt at this
# harness did exactly that and refused with "found []".  Redirect the write alone.
_RealRunRecord = sealer.RunRecord


class _DryRunRecord(_RealRunRecord):
    def write(self, runs_dir):
        return _RealRunRecord.write(self, OUT / "runs")


sealer.RunRecord = _DryRunRecord

print("=" * 92)
code = sealer.build()
print("=" * 92)
print("exit code: %s" % code)

if code != 0:
    sys.exit(code)

payload = sealer.RECORD_JSON.read_bytes()
print()
print("-- written JSON " + "-" * 76)
print("  bytes           %d" % len(payload))
print("  LF              %d" % payload.count(b"\n"))
print("  CRLF            %d" % payload.count(b"\r\n"))
print("  bare LF         %d" % (payload.count(b"\n") - payload.count(b"\r\n")))
record = json.loads(payload.decode("utf-8"))
print("  top-level keys  %d" % len(record))
print("  keys            %s" % list(record))

print()
print("-- values that must be exactly right " + "-" * 55)
print("  artifact_id                  %s" % record["artifact_id"])
print("  attempt                      %s" % record["attempt"])
print("  strategy_id                  %s" % record["strategy"]["strategy_id"])
print("  sealed_before_any_result     %s" % record["sealed_before_any_result_was_seen"])
print("  live_trading_authorized      %s" % record["live_trading_authorized"])
print("  stage_4_authorized           %s" % record["stage_4_authorized"])
print("  holdout_read_authorized      %s" % record["holdout_read_authorized"])
print("  grid size / runs             %s / %s" % (record["grid"]["size"], record["grid"]["total_runs"]))
print("  ladder bands                 %d" % len(record["risk_architecture"]["ladder_bands"]))
print("  pass / fail token            %s / %s" % (record["gate"]["pass_token"], record["gate"]["fail_token"]))
print("  excluded tokens              %s" % record["gate"]["prior_attempt_tokens_extracted_and_excluded"])
print("  sealed_inputs                %d" % len(record["sealed_inputs"]))
print("  binding_rules                %d" % len(record["binding_rules"]))
print("  conflicts_found              %d" % len(record["conflicts_found"]))

prov = record["risk_architecture"]["provenance_recomputed_here"]
print()
print("-- ladder provenance, as recorded " + "-" * 58)
for key in sorted(prov):
    print("  %-46s %s" % (key, json.dumps(prov[key], ensure_ascii=False)[:120]))

cont = record["contamination_measurement"]
print()
print("-- contamination, as recorded " + "-" * 62)
for key in ("python_files_scanned", "modules_naming_this_candidate_count",
            "tests_naming_this_candidate_count", "prior_attempt_module_count",
            "prior_attempt_module_duplicates", "prior_attempt_modules_that_moved",
            "prior_attempt_modules_that_disagree_between_records",
            "prior_attempt_modules_not_in_any_run_record",
            "prior_attempt_artifacts_that_moved", "prior_attempt_pinned_artifact_counts",
            "prior_attempt_path_shaped_values_without_a_pin",
            "attempt_2_run_record_routes_agree", "attempt_3_report_artifacts",
            "run_records_naming_this_candidate"):
    print("  %-52s %s" % (key, json.dumps(cont[key], ensure_ascii=False)[:110]))
doubly = sum(1 for v in cont["prior_attempt_module_record_coverage"].values() if v > 1)
print("  %-52s %d" % ("modules named by more than one run record", doubly))

# The mandated disclosure must survive serialisation byte for byte.  Never printed: the console is
# cp1252 and the string carries U+2014 and U+2212.
import hashlib  # noqa: E402
disc = record["adaptation_disclosure"]
print()
print("-- mandated disclosure " + "-" * 69)
print("  length          %d" % len(disc))
print("  sha256 prefix   %s" % hashlib.sha256(disc.encode("utf-8")).hexdigest()[:16])
print("  em dash U+2014  %d" % disc.count("\u2014"))
print("  minus  U+2212   %d" % disc.count("\u2212"))
print("  matches config  %s" % (disc == protocol["adaptation_disclosure_verbatim"]))

print()
print("-- .sha256 record " + "-" * 74)
print(sealer.RECORD_SHA.read_text("utf-8"))
runs = sorted((OUT / "runs").glob("*.json"))
print("-- runs/ record: %d written -> %s" % (len(runs), [p.name for p in runs]))
if runs:
    body = json.loads(runs[0].read_text("utf-8"))
    print("  stage             %s" % body["stage"])
    print("  holdout_state     %s" % body["holdout_state"])
    print("  strategy_id       %s" % body["strategy_id"])
    print("  date_range        %s" % body["date_range"])
    print("  exit_status       %s" % body["exit_status"])
    print("  repo_state_id     %s" % body["repo_state_id"])
    print("  code_hashes       %d" % len(body["code_hashes"]))
    print("  dataset_hashes    %d" % len(body["dataset_hashes"]))
    print("  notes             %d" % len(body["notes"]))

print()
print("=" * 92)
print("DRY RUN COMPLETE - nothing was written inside stockedge100/")
