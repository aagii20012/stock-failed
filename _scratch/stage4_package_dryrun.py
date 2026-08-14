"""Dry-run stage4_evaluation_package.build() with build_stage_package monkeypatched.

CLAUDE.md: "The builder itself lives in src/, so dry-run it before it writes anything. A defect found
after the real build cannot be fixed without invalidating the digest that build just recorded."

Everything real runs -- the checksum sweep, the thirteen-artifact recheck, repo_state(), the
contamination predicates, the independent re-derivation of all seven conditions, the whole guard --
and only the final write is intercepted. The intercepted call prints the assembled StageDecision so
its gate table can be diffed against section 8 of governance/STAGE_4_VALIDATION_REPORT.md.

The test summary does not exist yet, so a stand-in is supplied in memory for the parse. The real
build reads the real file.

ASCII-only output: the console is cp1252.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(r"D:\Product\stock-trade-alpaca\stockedge100")
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.reporting import stage4_evaluation_package as pkg  # noqa: E402


def out(text):
    sys.stdout.write(str(text).encode("ascii", "backslashreplace").decode("ascii") + "\n")


CAPTURED = {}


class FakeResult:
    freeze_ok = True
    run_id = "SE100-R-DRYRUN"
    timestamp_utc = "DRYRUN"
    decision_path = ROOT / "reports/stage4/STAGE_4_VALIDATION.json"
    manifest_path = ROOT / "reports/stage4/STAGE_4_VALIDATION_ARTIFACT_MANIFEST.json"
    checksum_path = ROOT / "reports/stage4/STAGE_4_VALIDATION.sha256"
    run_record_path = ROOT / "runs/SE100-R-DRYRUN.json"

    def __init__(self, repo_state_id):
        self.repo_state_id = repo_state_id


def fake_build(decision):
    CAPTURED["decision"] = decision
    _, repo_state_id = pkg.repo_state()
    return FakeResult(repo_state_id)


# The test summary now exists on disk, so nothing is stood in any more: read_text is left alone and
# the parse below is the same parse the real build will perform, against the same bytes.
pkg.build_stage_package = fake_build

out("== running build() with the writer intercepted ==")
code = pkg.build()
out("  build() -> %s" % code)
out("")

if "decision" not in CAPTURED:
    out("THE GUARD REFUSED -- nothing was assembled. Read the message above.")
    raise SystemExit(1)

d = CAPTURED["decision"]

out("=" * 96)
out("== scalar fields ==")
for name in ("stage", "stage_slug", "decision_basename", "manifest_basename", "gate_id",
             "gate_name", "verdict", "gate_passed", "universe_version", "date_range",
             "holdout_state", "config_hash", "random_seed", "command"):
    out("  %-22s %s" % (name, json.dumps(getattr(d, name), default=str)[:110]))
out("  %-22s %s" % ("tests", json.dumps(d.tests)))
out("  %-22s %s" % ("dataset_hashes", json.dumps(d.dataset_hashes)[:110]))
out("  %-22s %d entries" % ("frozen_inputs", len(d.frozen_inputs)))
out("  %-22s %d entries" % ("produced", len(d.produced)))
out("")

out("== gate conditions (diff these against report section 8) ==")
for cid, cond in d.gate_conditions.items():
    out("  %-46s %-8s satisfied=%s" % (cid, cond["verdict"], cond["satisfied"]))
    out("      required: %s" % cond["required"][:150])
    ev = cond["evidence"]
    if "independent_rederivation" in ev:
        r = ev["independent_rederivation"]
        out("      measured=%s threshold=%s cmp=%s rederived_met=%s agrees=%s"
            % (str(r["measured"])[:34], r["threshold"], r["comparison"], r["met"],
               ev["agrees_with_the_evaluator"]))
out("")

out("== decisive row detail ==")
out(json.dumps(d.gate_conditions["gate_4_representative_admitted_in_validation"]["evidence"],
               indent=2, default=str))
out("")

out("== evidence bullets ==")
for line in d.evidence:
    out("  - %s" % line)
out("")

out("== conflicts ==")
for line in d.conflicts_found:
    out("  - %s" % line[:200])
out("")

out("== body key tree ==")


def walk(node, prefix="  "):
    if isinstance(node, dict):
        for key, value in node.items():
            kind = type(value).__name__
            size = len(value) if isinstance(value, (dict, list, str)) else ""
            out("%s%-46s %s %s" % (prefix, key, kind, size))
            if isinstance(value, dict) and len(prefix) < 8:
                walk(value, prefix + "  ")


walk(d.body)
out("")

out("== integrity summary ==")
integ = d.body["integrity_verification"]
out("  checksum records all_ok        %s" % integ["checksum_records"]["all_ok"])
out("  stage 0 freeze verified        %s" % integ["checksum_records"]["stage_0_freeze_verified"])
out("  records verified               %s" % integ["checksum_records"]["records_verified"])
for rel, row in integ["checksum_records"]["records"].items():
    if not row["all_ok"]:
        out("    NOT OK  %s  %s entries (expected %s) %s"
            % (rel, row["entries"], row["entries_expected"], row["statuses"]))
out("  evidence digest equal          %s" % integ["evidence_digest"]["equal"])
inv = d.body["strategy_invariance"]["package_recheck"]
out("  sealed digests rechecked       %s of %s, all_equal=%s"
    % (inv["rechecked"], inv["declared_set_size"], inv["all_equal"]))
for rel, row in inv["entries"].items():
    if not row["equal"]:
        out("    NOT EQUAL  %s" % rel)
out("")

out("== repo state delta ==")
out("  baselines: %s" % json.dumps(integ["repo_state_delta"]["baselines"], indent=2))
for name in ("seal_to_preregistration_package", "preregistration_package_to_evaluation",
             "evaluation_to_package_build", "seal_to_package_build"):
    diff = integ["repo_state_delta"][name]
    out("  %s: %s -> %s entries, +%s ~%s -%s protected_moved=%s"
        % (name, diff["entries_before"], diff["entries_after"], diff["added_count"],
           diff["changed_count"], diff["removed_count"],
           diff["protected_paths_changed_or_removed"]))
    for path in diff["added"]:
        out("      + %s" % path)
    for path in diff["changed"]:
        out("      ~ %s" % path)
    for path in diff["removed"]:
        out("      - %s" % path)
out("")

out("== contamination predicates ==")
con = d.body["contamination_predicates"]
out("  sealed at sealing: %s" % json.dumps(con["sealed_values_at_sealing"]))
out("  P1 evaluator/result modules    %s %s"
    % (con["stage_4_evaluator_or_result_modules"]["count"],
       con["stage_4_evaluator_or_result_modules"]["files"]))
out("  P2 modules naming a run label  %s %s"
    % (con["modules_naming_a_stage_4_run_label"]["count"],
       con["modules_naming_a_stage_4_run_label"]["files"]))
out("  P3 report artifacts            %s" % con["stage_4_report_artifacts"]["count"])
for path in con["stage_4_report_artifacts"]["files"]:
    out("      %s" % path)
out("  P4 run records                 %s %s"
    % (con["stage_4_run_records"]["count"], con["stage_4_run_records"]["files"]))
p5 = con["stage_4_modules_touching_restricted_data_or_a_broker"]
out("  P5 REFERENCE (frozen sealer)   %s %s"
    % (p5["reference_implementation"]["count"],
       json.dumps(p5["reference_implementation"]["files"])))
dis = p5["two_implementations_disagree"]
out("  P5 divergence                  reference=%s this_package=%s"
    % (dis["reference_count"], dis["this_package_count"]))
out("      only this package sees: %s" % json.dumps(dis["seen_only_by_this_package"]))
out("      only the reference sees: %s" % json.dumps(dis["seen_only_by_the_reference"]))
out("  P5 data-access half            %s %s"
    % (p5["data_access_half"]["count"], json.dumps(p5["data_access_half"]["files"])))
out("  P5 broker/net/env/url half     %s %s"
    % (p5["broker_network_env_url_half"]["count"],
       json.dumps(p5["broker_network_env_url_half"]["files"])))
out("  P5 no network/broker marker    %s" % p5["no_network_or_broker_import_anywhere"])
out("  P5 unresolved                  %s" % json.dumps(p5["unresolved"]))
for rel, why in p5["resolution"].items():
    out("      %s\n         -> %s" % (rel, why[:170]))
out("  P6 gate 3 records verify       %s %s"
    % (con["gate_3_attempt_2_records_verify"]["value"],
       json.dumps(con["gate_3_attempt_2_records_verify"]["records"])))
out("")

out("== serialisation ==")
try:
    blob = json.dumps({
        "gate_conditions": d.gate_conditions, "body": d.body, "evidence": d.evidence,
        "limitations": d.limitations, "conflicts_found": d.conflicts_found,
        "authorization_state": d.authorization_state, "run_notes": d.run_notes,
        "dataset_hashes": d.dataset_hashes, "tests": d.tests,
    }, indent=2)
except TypeError as exc:
    out("  NOT SERIALISABLE: %s" % exc)
    raise SystemExit(1)
out("  ok, %d bytes" % len(blob))
out("")
out("DRY RUN COMPLETE -- nothing was written into the tree")
