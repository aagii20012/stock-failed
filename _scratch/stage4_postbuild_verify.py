"""Post-build verification of the Stage 4 pre-registration decision package."""
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(r"D:\Product\stock-trade-alpaca\stockedge100")
sys.path.insert(0, str(ROOT / "src"))
from stockedge100.reporting.stage_package import repo_state, verify_sha256_record  # noqa: E402

fails = []
notes = []


def check(label, ok, detail=""):
    line = ("OK   " if ok else "FAIL ") + label + (" :: " + detail if detail else "")
    (notes if ok else fails).append(line)


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


DEC = ROOT / "reports/stage4/STAGE_4_VALIDATION_PREREGISTRATION.json"
MAN = ROOT / "reports/stage4/STAGE_4_VALIDATION_PREREGISTRATION_ARTIFACT_MANIFEST.json"
CHK = ROOT / "reports/stage4/STAGE_4_VALIDATION_PREREGISTRATION.sha256"
dec = json.loads(DEC.read_text(encoding="utf-8"))
man = json.loads(MAN.read_text(encoding="utf-8"))
run_id = dec["reproducibility"]["run_id"]
RUN = ROOT / "runs" / (run_id + ".json")
run = json.loads(RUN.read_text(encoding="utf-8"))

# 1. checksum records still verify, each from its own convention's directory
records = [
    ("STAGE_0_FREEZE.sha256", ROOT / "governance"),
    ("STAGE_1_FREEZE.sha256", ROOT / "governance"),
    ("governance/STAGE_4_PREREGISTRATION.sha256", ROOT),
    ("reports/stage4/STAGE_4_VALIDATION_PREREGISTRATION.sha256", ROOT),
    ("reports/stage3_attempt2/STAGE_3_ATTEMPT_2_DESIGN.sha256", ROOT),
    ("reports/stage3_attempt2/STAGE_3_ATTEMPT_2_STRATEGY_RESEARCH.sha256", ROOT),
]
for rel, cwd in records:
    results = verify_sha256_record(cwd / rel, cwd)
    bad = dict((k, v) for k, v in results.items() if v != "OK")
    check("sha256sum -c " + rel + " (from " + cwd.name + ") " + str(len(results)) + " entries",
          bad == {}, "not OK=" + str(bad))

# 2. repo_state_id recomputed from the patterns
code_hashes, rsid = repo_state()
recorded = dec["reproducibility"]["repo_state_id"]
check("repo_state_id recomputes", rsid == recorded, rsid[:16] + " vs " + recorded[:16])
check("run record repo_state_id agrees", run["repo_state_id"] == recorded)
check("manifest repo_state_id agrees", man["repo_state_id"] == recorded)
check("repo_state_files count", len(man["repo_state_files"]) == len(code_hashes),
      str(len(man["repo_state_files"])) + " vs " + str(len(code_hashes)))

# 3. no file covered by the digest carries the digest
carriers = [rel for rel in code_hashes
            if recorded in (ROOT / rel).read_text(encoding="utf-8", errors="ignore")]
check("no repo_state_id-covered file contains the tree digest", carriers == [], str(carriers))
for p in sorted((ROOT / "governance").glob("STAGE_4_*")):
    if p.suffix not in (".md", ".json", ".sha256"):
        continue
    hits = sorted(set(re.findall(r"\b[0-9a-f]{64}\b", p.read_text(encoding="utf-8"))))
    check(p.name + " carries no tree digest", recorded not in hits,
          str(len(hits)) + " hex64 present")

# 4. manifest integrity
manifest_rel = "reports/stage4/STAGE_4_VALIDATION_PREREGISTRATION_ARTIFACT_MANIFEST.json"
check("manifest excludes itself", manifest_rel not in man["produced_artifacts"])
flat = {}
for group in ("frozen_inputs", "produced_artifacts"):
    for k, v in man[group].items():
        flat[k] = v["sha256"]
for group in ("dataset_hashes", "repo_state_files"):
    for k, v in man[group].items():
        flat[k] = v
drift = [k for k, v in flat.items() if (ROOT / k).is_file() and sha(ROOT / k) != v]
absent = [k for k in flat if not (ROOT / k).is_file()]
check("every manifest digest matches disk", drift == [], str(drift[:4]))
check("every manifest path exists on disk", absent == [], str(absent[:4]))
check("frozen inputs all READ_ONLY_NOT_MODIFIED",
      set(e["disposition"] for e in man["frozen_inputs"].values()) == {"READ_ONLY_NOT_MODIFIED"})
check("manifest counts", (len(man["frozen_inputs"]), len(man["produced_artifacts"])) == (12, 13),
      str((len(man["frozen_inputs"]), len(man["produced_artifacts"]))))

# 5. checksum record coverage
covered = {}
for line in CHK.read_text(encoding="utf-8").splitlines():
    if line.strip():
        digest, path = line.split(None, 1)
        covered[path.strip().lstrip("*")] = digest
check("checksum record does not name itself",
      "reports/stage4/STAGE_4_VALIDATION_PREREGISTRATION.sha256" not in covered)
artifacts = [a["path"] if isinstance(a, dict) else a for a in dec["artifacts"]]
expect = set(dec["frozen_inputs_read_only"]) | set(artifacts)
expect = set(p for p in expect if (ROOT / p).is_file())
expect.discard("reports/stage4/STAGE_4_VALIDATION_PREREGISTRATION.sha256")
check("checksum record covers frozen inputs + produced artifacts", set(covered) == expect,
      "missing=" + str(sorted(expect - set(covered))) + " extra=" + str(sorted(set(covered) - expect)))
check("manifest is covered by the checksum record", manifest_rel in covered)
check("every artifact this package declares exists",
      all((ROOT / a).is_file() for a in artifacts),
      str([a for a in artifacts if not (ROOT / a).is_file()]))

# 6. required authorization fields (operating prompt section 10)
required = {
    "gate_3_passed": True,
    "gate_4_evaluated": False,
    "gate_4_passed": False,
    "validation_evaluation_authorized": True,
    "validation_access_authorized_in_this_session": False,
    "holdout_access_authorized": False,
    "stage_5_authorized": False,
    "paper_trading_authorized": False,
    "shadow_live_authorized": False,
    "live_trading_authorized": False,
    "capital_or_risk_expansion_authorized": False,
}
for k, v in required.items():
    check(k + " == " + str(v), dec.get(k, "<absent>") is v, repr(dec.get(k, "<absent>")))
check("next_authorized_stage names only the sealed Stage 4 evaluation",
      dec["next_authorized_stage"].startswith("STAGE_4_VALIDATION_EVALUATION"))
blob = json.dumps(dec)
tr = re.findall(r"[^.]{0,40}trade.ready[^.]{0,40}", blob, flags=re.I)
check("no trade-ready claim", all("not trade-ready" in s or "is not" in s or "no " in s for s in tr),
      str(tr))

# 7. gate row, tokens, verdict coherence
gc = dec["gate_conditions"]
check("gate_4_admissible_candidate_exists is NOT_RUN",
      gc["gate_4_admissible_candidate_exists"]["verdict"] == "NOT_RUN",
      gc["gate_4_admissible_candidate_exists"]["verdict"])
notmet = dict((k, v["verdict"]) for k, v in gc.items()
              if k.startswith("S4D-") and v["verdict"] != "MET")
check("all eleven S4D conditions MET", notmet == {} and len(gc) == 12, str(notmet))
crit = json.loads((ROOT / "config/stage4_gate_criteria.json").read_text(encoding="utf-8"))
der = crit["verdict_token_derivation"]
token = dec["verdict"].split(" ", 2)[-1]
check("verdict token is not a Gate 4 token", token not in (der["pass_token"], der["fail_token"]), token)
check("gate tokens come from the sealed derivation",
      (dec["gate"]["pass_token"], dec["gate"]["fail_token"]) == (der["pass_token"], der["fail_token"]))
check("gate_passed is False", dec["gate_passed"] is False)
check("representative is the sealed one",
      dec["representative"]["experiment_id"] == "SE100-S3A2-C2-MEANREV-RA1",
      dec["representative"]["experiment_id"])
check("survivor_count 1 and no human selection required",
      (dec["representative"]["survivor_count"], dec["representative"]["human_selection_required"]) == (1, False))

# 8. fields that live only in the runs/ record
check("run record holdout_state SEALED", run["holdout_state"] == "SEALED", str(run["holdout_state"]))
check("run record declares no dataset read", run["dataset_hashes"] == {}, str(run["dataset_hashes"])[:60])
check("run record universe_version present", bool(run["universe_version"]), str(run["universe_version"]))
check("run record exit_status GATE_NOT_PASSED", run["exit_status"] == "GATE_NOT_PASSED", run["exit_status"])
check("run record date_range", str(run["date_range"]), str(run["date_range"]))
oah = run["output_artifact_hashes"]
check("run record decision digest matches disk",
      oah["reports/stage4/STAGE_4_VALIDATION_PREREGISTRATION.json"] == sha(DEC))
check("run record manifest digest matches disk", oah[manifest_rel] == sha(MAN))
check("run record checksum digest matches disk",
      oah["reports/stage4/STAGE_4_VALIDATION_PREREGISTRATION.sha256"] == sha(CHK))
runs = sorted(p.name for p in (ROOT / "runs").glob("*.json"))
check("runs/ append-only 15 -> 16", len(runs) == 16, str(len(runs)) + " records")
check("the new run record is the only addition", (run_id + ".json") in runs)

# 9. tests, blockers, conflicts
check("tests block", dec["tests"] == {"passed": 263, "failed": 0, "skipped": 0, "collected": 708},
      str(dec["tests"]))
check("blockers empty", dec["blockers"] == [])
check("conflicts recorded", len(dec["conflicts_found"]) == 5, str(len(dec["conflicts_found"])))
check("evidence items", len(dec["evidence"]) == 11, str(len(dec["evidence"])))
check("limitations items", len(dec["limitations"]) == 12, str(len(dec["limitations"])))

print("\n".join(notes))
print("")
print("\n".join(fails) if fails else "ALL CHECKS PASS")
print("")
print(str(len(notes)) + " ok / " + str(len(fails)) + " failed")
print("repo_state_id " + recorded)
print("run_id        " + run_id)
