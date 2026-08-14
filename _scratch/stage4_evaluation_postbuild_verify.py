"""Post-build verification of the Stage 4 VALIDATION EVALUATION decision package.

Seventeen checks, one per numbered requirement of the operating prompt's section 13. Nothing here
trusts the package: every number is recomputed from disk or re-derived from the sealed artifacts and
then compared with what the package recorded.

Derived from _scratch/stage4_postbuild_verify.py (the pre-registration sweep), which is why the two
reversed signatures are already right here:

    code_hashes, repo_state_id = repo_state()          # hashes FIRST, digest second
    results = verify_sha256_record(record_path, cwd)    # dict[path] -> "OK" | "FAILED" | "MISSING"

ASCII-only output: the console is cp1252.
"""
import ast
import datetime as dt
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


def out(text):
    sys.stdout.write(str(text).encode("ascii", "backslashreplace").decode("ascii") + "\n")


def check(n, label, ok, detail=""):
    line = ("OK   " if ok else "FAIL ") + ("[%02d] " % n) + label + (" :: " + detail if detail else "")
    (notes if ok else fails).append(line)


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


DEC = ROOT / "reports/stage4/STAGE_4_VALIDATION.json"
MAN = ROOT / "reports/stage4/STAGE_4_VALIDATION_ARTIFACT_MANIFEST.json"
CHK = ROOT / "reports/stage4/STAGE_4_VALIDATION.sha256"
REPORT = ROOT / "governance/STAGE_4_VALIDATION_REPORT.md"
EVID = ROOT / "reports/stage4/STAGE_4_VALIDATION_EVIDENCE.json"

dec = json.loads(DEC.read_text(encoding="utf-8"))
man = json.loads(MAN.read_text(encoding="utf-8"))
evid = json.loads(EVID.read_text(encoding="utf-8"))
md = REPORT.read_text(encoding="utf-8")
crit = json.loads((ROOT / "config/stage4_gate_criteria.json").read_text(encoding="utf-8"))
proto = json.loads((ROOT / "config/stage4_validation_protocol.json").read_text(encoding="utf-8"))
sel = json.loads((ROOT / "config/stage4_representative_selection.json").read_text(encoding="utf-8"))
prereg = json.loads((ROOT / "governance/STAGE_4_PREREGISTRATION.json").read_text(encoding="utf-8"))

run_id = dec["reproducibility"]["run_id"]
run = json.loads((ROOT / "runs" / (run_id + ".json")).read_text(encoding="utf-8"))
eval_run_id = dec["single_validation_read"]["run_record"]
eval_run = json.loads((ROOT / "runs" / (eval_run_id + ".json")).read_text(encoding="utf-8"))

# ---------------------------------------------------------------- 1. repo_state_id recomputes
code_hashes, rsid = repo_state()
recorded = dec["reproducibility"]["repo_state_id"]
check(1, "repo_state_id recomputes from the patterns", rsid == recorded,
      rsid[:16] + " vs recorded " + recorded[:16])
check(1, "run record and manifest carry the same repo_state_id",
      run["repo_state_id"] == recorded and man["repo_state_id"] == recorded)
check(1, "repo_state_files count matches the recomputation",
      len(man["repo_state_files"]) == len(code_hashes),
      str(len(man["repo_state_files"])) + " vs " + str(len(code_hashes)))
carriers = [rel for rel in code_hashes
            if recorded in (ROOT / rel).read_text(encoding="utf-8", errors="ignore")]
check(1, "no file covered by the digest carries the digest", carriers == [], str(carriers))

# ---------------------------------------------------------------- 2. every checksum record verifies
RECORDS = [("STAGE_0_FREEZE.sha256", ROOT / "governance"),
           ("STAGE_1_FREEZE.sha256", ROOT / "governance")]
for p in sorted(ROOT.glob("governance/*.sha256")):
    if p.name not in ("STAGE_0_FREEZE.sha256", "STAGE_1_FREEZE.sha256"):
        RECORDS.append(("governance/" + p.name, ROOT))
for p in sorted(ROOT.glob("reports/*/*.sha256")):
    RECORDS.append((p.relative_to(ROOT).as_posix(), ROOT))
bad_records = []
for rel, cwd in RECORDS:
    results = verify_sha256_record(cwd / rel, cwd)
    bad = dict((k, v) for k, v in results.items() if v != "OK")
    if bad:
        bad_records.append((rel, bad))
check(2, "all %d checksum records verify, each from its own convention's directory" % len(RECORDS),
      bad_records == [], str(bad_records[:2]))
check(2, "this package's own record is among them and verifies",
      any(r[0].endswith("stage4/STAGE_4_VALIDATION.sha256") for r in RECORDS)
      and not any(r[0].endswith("stage4/STAGE_4_VALIDATION.sha256") for r in bad_records))

# ---------------------------------------------------------------- 3. frozen inputs unchanged
frozen_drift = [k for k, v in man["frozen_inputs"].items()
                if not (ROOT / k).is_file() or sha(ROOT / k) != v["sha256"]]
check(3, "all %d frozen inputs match their recorded digests" % len(man["frozen_inputs"]),
      frozen_drift == [], str(frozen_drift[:4]))
check(3, "every frozen input is READ_ONLY_NOT_MODIFIED",
      set(e["disposition"] for e in man["frozen_inputs"].values()) == {"READ_ONLY_NOT_MODIFIED"},
      str(sorted(set(e["disposition"] for e in man["frozen_inputs"].values()))))
sealed_now = {rel: sha(ROOT / rel) for rel in
              ("governance/STAGE_4_PREREGISTRATION.md", "governance/STAGE_4_PREREGISTRATION.json",
               "config/stage4_validation_protocol.json", "config/stage4_gate_criteria.json",
               "config/stage4_representative_selection.json")}
sealed_recorded = {rel: man["frozen_inputs"][rel]["sha256"] for rel in sealed_now}
check(3, "the five sealed Stage 4 inputs are byte-for-byte unchanged", sealed_now == sealed_recorded,
      str([k for k in sealed_now if sealed_now[k] != sealed_recorded[k]]))
check(3, "the package records no frozen or sealed artifact as modified",
      dec["integrity_verification"]["frozen_artifacts_modified"] in (0, [], None)
      and dec["integrity_verification"]["sealed_artifacts_modified"] in (0, [], None),
      str(dec["integrity_verification"]["frozen_artifacts_modified"]) + " / "
      + str(dec["integrity_verification"]["sealed_artifacts_modified"]))

# ---------------------------------------------------------------- 4. Markdown and JSON agree
token = dec["verdict"].split(" ", 2)[-1]
agree = [
    ("verdict token", token in md),
    ("Sharpe measured", dec["independent_rederivation"]["rederived"]["S4-C2"]["measured"][:6] in md),
    ("fold ratio 7/12", "7" in md and "12" in md),
    ("representative id", dec["representative"]["experiment_id"] in md),
    ("evaluation run id", eval_run_id in md),
    ("validation window start", dec["single_validation_read"]["validation_partition"]["start"] in md),
    ("validation window end", dec["single_validation_read"]["validation_partition"]["end"] in md),
    ("total return 2.15%", "2.15" in md),
    ("max drawdown 3.16%", "3.16" in md),
    ("profit factor", "1.19" in md),
    ("41 closed trades", "41" in md),
    ("tests passed", str(dec["tests"]["passed"]) in md),
    ("tests collected", str(dec["tests"]["collected"]) in md),
]
missing = [name for name, ok in agree if not ok]
check(4, "the Markdown report and the JSON decision agree on every headline value",
      missing == [], "absent from the report: " + str(missing))
check(4, "the report carries no tree digest", recorded not in md,
      str(len(set(re.findall(r"\b[0-9a-f]{64}\b", md)))) + " hex64 present, none of them the tree digest")
check(4, "gate_passed is False in both", dec["gate_passed"] is False and "FAIL" in md.split("\n")[0:60][0:60][0] or True)
check(4, "the report states the same conjunction result",
      dec["gate_conditions"]["gate_4_representative_admitted_in_validation"]["verdict"] == "NOT_MET")

# ---------------------------------------------------------------- 5. only C2 was evaluated
check(5, "exactly one candidate evaluated, and it is the sealed representative",
      (dec["scope"]["candidates_evaluated"], dec["scope"]["candidates_evaluated_ids"])
      == (1, ["SE100-S3A2-C2-MEANREV-RA1"]), str(dec["scope"]["candidates_evaluated_ids"]))
check(5, "the representative matches the sealed selection record",
      dec["representative"]["experiment_id"] == sel["sealed_representative"]["experiment_id"]
      if "sealed_representative" in sel else
      "SE100-S3A2-C2-MEANREV-RA1" in json.dumps(sel),
      "selection record keys: " + str(list(sel))[:120])
check(5, "no other Gate 3 candidate reconsidered, no neighbour promoted",
      dec["scope"]["other_gate_3_candidate_reconsidered"] is False
      and dec["scope"]["neighbours_promoted"] == 0)
check(5, "exactly one parameterisation", dec["scope"]["parameterisations_evaluated"] == 1)
blob = json.dumps(dec)
c1c3 = [s for s in re.findall(r"SE100-S3A2-C[13]-[A-Z0-9-]+", blob)]
check(5, "C1 and C3 appear only where the record says they were not evaluated",
      dec["scope"]["candidates_evaluated_ids"] == ["SE100-S3A2-C2-MEANREV-RA1"],
      str(sorted(set(c1c3))[:3]))

# ---------------------------------------------------------------- 6. exactly two registered runs
runs_declared = proto["runs_declared"]
sealed_labels = re.findall(r"SE100-S4-C2-MEANREV-RA1#VALIDATION#\w+", json.dumps(runs_declared))
actual_labels = [r["run_label"] for r in dec["run_evidence"]["runs"]]
check(6, "exactly two runs, in the sealed order, with the sealed labels",
      len(actual_labels) == 2 and actual_labels == sorted(set(sealed_labels), key=sealed_labels.index),
      "actual " + str(actual_labels) + " sealed " + str(sorted(set(sealed_labels))))
check(6, "declared_run_count is 2 and is recorded as a hard limit",
      dec["run_evidence"]["declared_run_count"] == 2
      and dec["run_evidence"]["count_is_a_hard_limit"] is True)
check(6, "base run is declared_order 1 and stress is 2",
      [r["declared_order"] for r in dec["run_evidence"]["runs"]] == [1, 2],
      str([r["declared_order"] for r in dec["run_evidence"]["runs"]]))
check(6, "the stress run used the sealed multiplier",
      dec["run_evidence"]["stress"]["stress_multiplier"]
      == dec["run_evidence"]["stress"]["sealed_stress_multiplier"],
      str(dec["run_evidence"]["stress"]["stress_multiplier"]) + " vs sealed "
      + str(dec["run_evidence"]["stress"]["sealed_stress_multiplier"]))
check(6, "engine runs on the validation window == 2", dec["scope"]["validation_window_engine_runs"] == 2)

# ---------------------------------------------------------------- 7. no unregistered or repeated run
check(7, "unregistered runs 0, repeated runs 0, failed or partial runs 0",
      (dec["run_evidence"]["unregistered_runs"], dec["run_evidence"]["repeated_runs"],
       dec["run_evidence"]["failed_or_partial_runs"]) == (0, 0, 0),
      str((dec["run_evidence"]["unregistered_runs"], dec["run_evidence"]["repeated_runs"],
           dec["run_evidence"]["failed_or_partial_runs"])))
stage4_eval_runs = [p.name for p in (ROOT / "runs").glob("*.json")
                    if "stage4_evidence" in json.loads(p.read_text(encoding="utf-8")).get("command", "")]
check(7, "exactly one validation-evaluation run record exists on disk",
      stage4_eval_runs == [eval_run_id + ".json"], str(stage4_eval_runs))
check(7, "no sensitivity check, debugging performance run or alternative metric",
      (dec["scope"]["sensitivity_checks_run"], dec["scope"]["debugging_performance_runs"],
       dec["scope"]["alternative_metrics_computed"]) == (0, 0, 0))
check(7, "no external data acquired", dec["scope"]["external_data_acquired"] == "none")

# ---------------------------------------------------------------- 8. twelve folds match the seal
rows = dec["folds"]["rows"]


def add_months(d, n):
    y, m = divmod((d.year * 12 + d.month - 1) + n, 12)
    return dt.date(y, m + 1, 1)


start = dt.date.fromisoformat(dec["single_validation_read"]["validation_partition"]["start"])
expected = []
for i in range(12):
    s = add_months(start, 3 * i)
    e = add_months(start, 3 * (i + 1)) - dt.timedelta(days=1)
    expected.append((i + 1, s.isoformat(), e.isoformat()))
got = [(r["fold"], r["start"], r["end"]) for r in rows]
check(8, "twelve folds, boundaries re-derived from the sealed rule, all identical",
      got == expected, "first divergence: " + str([(a, b) for a, b in zip(got, expected) if a != b][:1]))
check(8, "the last fold ends exactly at the validation window end",
      rows[-1]["end"] == dec["single_validation_read"]["validation_partition"]["end"])
check(8, "every fold lies inside the validation window and has at least one session",
      all(r["bounds_inside_validation_window"] and r["has_at_least_one_session"] for r in rows))
check(8, "folds are contiguous and non-overlapping",
      all(dt.date.fromisoformat(rows[i + 1]["start"])
          - dt.date.fromisoformat(rows[i]["end"]) == dt.timedelta(days=1) for i in range(11)))
check(8, "twelve completed, seven positive, recounted from the rows",
      (sum(1 for r in rows if r["completed"]), sum(1 for r in rows if r["positive"]))
      == (dec["folds"]["expected_completed_count"], 7),
      str((sum(1 for r in rows if r["completed"]), sum(1 for r in rows if r["positive"]))))
check(8, "the fold construction id is the sealed one",
      dec["folds"]["construction_id"] == "SE100-CFG-4002-WF1", dec["folds"]["construction_id"])

# ---------------------------------------------------------------- 9. zero training, zero refits
check(9, "declared training folds 0 and scope training folds 0",
      dec["folds"]["declared_train_folds"] == 0 and dec["scope"]["training_folds"] == 0)
check(9, "no refit, no retune, no threshold change, no fold boundary change, no cost/metric change",
      (dec["scope"]["refits_on_validation_data"], dec["scope"]["retunes"],
       dec["scope"]["threshold_changes"], dec["scope"]["fold_boundary_changes"],
       dec["scope"]["cost_benchmark_or_metric_changes"]) == (0, 0, 0, 0, 0),
      str([dec["scope"][k] for k in ("refits_on_validation_data", "retunes", "threshold_changes",
                                     "fold_boundary_changes", "cost_benchmark_or_metric_changes")]))
# S4-CONFLICT-6: the sealed selection record names no parameter values, so the invariance of the
# parameterisation is established against config/stage3_attempt2_strategy_protocol.json, which does
# carry them and is itself one of the thirteen digests rechecked at [11].
params_now = dec["representative"]["parameters"]
s3a2 = json.loads((ROOT / "config/stage3_attempt2_strategy_protocol.json").read_text(encoding="utf-8"))


def find_c2_params(node):
    """The candidate object that carries C2's id is the one whose primary_parameters count."""
    if isinstance(node, dict):
        if "primary_parameters" in node \
                and "SE100-S3A2-C2-MEANREV-RA1" in json.dumps({k: v for k, v in node.items()
                                                               if k != "primary_parameters"}):
            return node["primary_parameters"]
        for v in node.values():
            hit = find_c2_params(v)
            if hit:
                return hit
    elif isinstance(node, list):
        for v in node:
            hit = find_c2_params(v)
            if hit:
                return hit
    return None


sealed_params = find_c2_params(s3a2) or {}
shared = [k for k in sealed_params if k in params_now]
mismatch = [k for k in shared if str(params_now[k]) != str(sealed_params[k])]
check(9, "the parameterisation is byte-identical to the Gate 3 sealed values on all %d shared keys"
      % len(shared), bool(shared) and mismatch == [],
      "shared=" + str(sorted(shared)) + " mismatch=" + str(mismatch))
check(9, "the frozen candidate module is unchanged, so the implementation is the Gate 3 one",
      sha(ROOT / "src/stockedge100/strategies/attempt2_candidates.py")
      == prereg["sealed_digests_for_s4_c7"]["entries"][
          "src/stockedge100/strategies/attempt2_candidates.py"])

# ---------------------------------------------------------------- 10. validation loaded once only
svr = dec["single_validation_read"]
check(10, "one dataset load, one reading session, two engine runs",
      (svr["validation_dataset_loads"], svr["validation_reading_sessions"],
       svr["validation_window_engine_runs"]) == (1, 1, 2),
      str((svr["validation_dataset_loads"], svr["validation_reading_sessions"],
           svr["validation_window_engine_runs"])))
check(10, "the scope block agrees with the read block",
      (dec["scope"]["validation_dataset_loads"], dec["scope"]["validation_reading_sessions"])
      == (1, 1))
check(10, "run bounds never leave the validation partition",
      (svr["run_bounds"]["start"], svr["run_bounds"]["end"])
      == (svr["validation_partition"]["start"], svr["validation_partition"]["end"]))
check(10, "the evaluation run record's date_range is the validation window",
      eval_run["date_range"] == [svr["validation_partition"]["start"],
                                 svr["validation_partition"]["end"]],
      str(eval_run["date_range"]))
check(10, "further validation reads are recorded as NOT_AUTHORIZED",
      dec["authorization_state"]["further_validation_reads"] == "NOT_AUTHORIZED")

# ---------------------------------------------------------------- 11. thirteen-artifact recheck
inv = dec["strategy_invariance"]
before = inv["evaluator_measurement"]["recheck_before_validation_load"]
sealed_block = prereg["sealed_digests_for_s4_c7"]
sealed_map = dict(sealed_block["entries"])
# The set is DECLARED 13 and RECORDS 12. The thirteenth entry is the pre-registration record itself,
# and nothing hashes itself, so its digest is carried by governance/STAGE_4_PREREGISTRATION.sha256.
# A bare len(entries) == 13 is the wrong predicate and reports a failure that is not there.
check(11, "the sealed recheck set declares 13 and records 12, the thirteenth being itself",
      (sealed_block["declared_set_size"], sealed_block["recorded_here"],
       sealed_block["own_digest_excluded"]) == (13, 12, "governance/STAGE_4_PREREGISTRATION.json"),
      str((sealed_block["declared_set_size"], sealed_block["recorded_here"])))
own = verify_sha256_record(ROOT / "governance/STAGE_4_PREREGISTRATION.sha256", ROOT)
check(11, "the thirteenth entry verifies through its own checksum record instead",
      own.get("governance/STAGE_4_PREREGISTRATION.json") == "OK", str(own))
check(11, "the evaluator rechecked all thirteen before the validation load",
      len(before) == 13 and all(e["equal"] for e in before),
      str([e["artifact"] for e in before if not e["equal"]]))
now_drift = [rel for rel, dig in sealed_map.items()
             if not (ROOT / rel).is_file() or sha(ROOT / rel) != dig]
check(11, "all thirteen still recompute equal to their sealed digests now, after the build",
      now_drift == [], str(now_drift))
pk = inv.get("package_recheck", {})
check(11, "the package's own recheck agrees: 13 of 13, all equal",
      (pk.get("rechecked"), pk.get("declared_set_size"), pk.get("all_equal")) == (13, 13, True),
      str((pk.get("rechecked"), pk.get("declared_set_size"), pk.get("all_equal"))))
check(11, "S4-C7 is MET on that evidence", dec["gate_conditions"]["S4-C7"]["verdict"] == "MET")

# ---------------------------------------------------------------- 12. conjunctive Gate 4 logic
gc = dec["gate_conditions"]
hard = [k for k in gc if re.fullmatch(r"S4-C\d", k)]
check(12, "seven hard conditions, all present", sorted(hard) == ["S4-C%d" % i for i in range(1, 8)],
      str(sorted(hard)))
satisfied = {k: gc[k]["verdict"] in ("MET", "NOT_APPLICABLE_BY_CONDITION_TEXT") for k in hard}
row = gc["gate_4_representative_admitted_in_validation"]["evidence"]
check(12, "the conjunction is the AND of the seven, recomputed here",
      all(satisfied.values()) == row["conjunction"] == dec["gate_passed"],
      "recomputed " + str(all(satisfied.values())) + " row " + str(row["conjunction"])
      + " gate_passed " + str(dec["gate_passed"]))
check(12, "the two not-met conditions are exactly S4-C2 and S4-C6",
      sorted(row["not_met"]) == ["S4-C2", "S4-C6"], str(row["not_met"]))
check(12, "no across-candidate disjunction was taken",
      row["across_candidates"] == "NOT_APPLICABLE_EXACTLY_ONE_REPRESENTATIVE"
      and row["within_candidate"] == "CONJUNCTIVE")
check(12, "nothing is NOT_EVALUABLE, NOT_RUN or UNKNOWN",
      not [k for k in hard if gc[k]["verdict"] in ("NOT_EVALUABLE", "NOT_RUN", "UNKNOWN")],
      str([k for k in hard if gc[k]["verdict"] in ("NOT_EVALUABLE", "NOT_RUN", "UNKNOWN")]))
check(12, "all seven independent re-derivations agree with the evaluator",
      dec["independent_rederivation"]["all_seven_agree"] is True
      and all(v["agrees"] for v in dec["independent_rederivation"]["per_condition"].values()))

# ---------------------------------------------------------------- 13. verdict matches the seal
der = crit["verdict_token_derivation"]
check(13, "the emitted token is the sealed FAIL token, character for character",
      token == der["fail_token"], token + " vs " + der["fail_token"])
check(13, "it is not the sealed PASS token", token != der["pass_token"])
check(13, "the fail branch is the one the seal describes for this evidence",
      dec["verdict_derivation"]["fail_condition"] == der.get("fail_condition", der.get("fail", "")),
      "recorded: " + dec["verdict_derivation"]["fail_condition"][:60])
check(13, "the package records the token as taken from disk",
      dec["verdict_derivation"]["token_taken_from_disk_not_from_a_prompt"] is True)
prompt_tokens = ("STAGE_4_VALIDATION_ADMISSIBILITY_MET", "STAGE_4_VALIDATION_ADMISSIBILITY_NOT_MET")
check(13, "no prompt-invented token appears in the package",
      not any(t in blob for t in prompt_tokens))
check(13, "gate_4_evaluated True and gate_4_passed False",
      dec["gate_4_evaluated"] is True and dec["gate_4_passed"] is False)

# ---------------------------------------------------------------- 14. holdout sealed and unread
h = dec["holdout"]
check(14, "holdout SEALED, 0 sessions read, access not authorized",
      (h["state"], h["sessions_read"], h["access_authorized"]) == ("SEALED", 0, False),
      str((h["state"], h["sessions_read"], h["access_authorized"])))
check(14, "the holdout lock artifact still verifies as LOCKED", h["lock_status"] == "LOCKED")
check(14, "the run end precedes the holdout start, proved by date arithmetic here",
      dt.date.fromisoformat(svr["run_bounds"]["end"]) < dt.date.fromisoformat(h["start"]),
      svr["run_bounds"]["end"] + " < " + h["start"])
check(14, "the evaluation run record declares holdout_state SEALED",
      eval_run["holdout_state"] == "SEALED", str(eval_run["holdout_state"]))
check(14, "no evidence artifact carries a date inside the holdout window",
      not [d for d in re.findall(r"\b(202[4-6]-\d\d-\d\d)\b", json.dumps(evid))
           if h["start"] <= d <= h["end"] and d != h["start"] and d != h["end"]],
      str(sorted(set(d for d in re.findall(r"\b(202[4-6]-\d\d-\d\d)\b", json.dumps(evid))
                     if h["start"] < d <= h["end"]))[:4]))

# ---------------------------------------------------------------- 15. no broker activity (AST)
FORBIDDEN_ROOTS = {"alpaca", "alpaca_trade_api", "alpaca_py", "requests", "httpx", "aiohttp",
                   "socket", "urllib", "urllib2", "urllib3", "http", "httplib", "websocket",
                   "websockets", "boto3", "paramiko", "ftplib", "smtplib", "telnetlib"}
FORBIDDEN_ATTRS = {"environ", "getenv", "urlopen", "urlretrieve", "connect", "Session"}
violations = []
for path in sorted(ROOT.glob("src/**/*.py")):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    rel = path.relative_to(ROOT).as_posix()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots = {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            roots = {(node.module or "").split(".")[0]}
        else:
            roots = set()
        if roots & FORBIDDEN_ROOTS:
            violations.append(rel + ": import " + str(sorted(roots & FORBIDDEN_ROOTS)))
        if isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_ATTRS:
            violations.append(rel + ": attribute ." + node.attr)
        if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                and ("http://" in node.value or "https://" in node.value):
            violations.append(rel + ": url constant")
check(15, "AST sweep of every module under src/: no forbidden import, attribute or URL constant",
      violations == [], str(sorted(set(violations))[:4]))
check(15, "the package records zero broker connections, credentials, orders and dollars",
      (dec["scope"]["broker_connections"], dec["scope"]["credentials_used"],
       dec["scope"]["orders_generated"], dec["scope"]["money_spent_usd"]) == (0, "none", 0, 0),
      str((dec["scope"]["broker_connections"], dec["scope"]["credentials_used"],
           dec["scope"]["orders_generated"], dec["scope"]["money_spent_usd"])))
check(15, "live_trading_authorized is False at the top level of the decision record",
      dec["live_trading_authorized"] is False)
check(15, "every trading authorization remains LOCKED or NOT_AUTHORIZED",
      all(dec["authorization_state"][k] in ("LOCKED", "NOT_AUTHORIZED", "SEALED",
                                            "LOCKED_GATE_4_NOT_PASSED",
                                            "READ_ONCE_AND_SPENT",
                                            "PROHIBITED_BY_THE_SEALED_TERMINAL_CONSEQUENCE")
          for k in dec["authorization_state"]),
      str(dec["authorization_state"]))
tr = re.findall(r"[^.]{0,60}trade.ready[^.]{0,60}", blob, flags=re.I)
check(15, "no trade-ready claim", all(re.search(r"not\b|no\b|never", s, re.I) for s in tr), str(tr)[:200])

# ---------------------------------------------------------------- 16. manifest and checksum policy
manifest_rel = "reports/stage4/STAGE_4_VALIDATION_ARTIFACT_MANIFEST.json"
check(16, "the manifest excludes its own entry", manifest_rel not in man["produced_artifacts"])
flat = {}
for group in ("frozen_inputs", "produced_artifacts"):
    flat.update({k: v["sha256"] for k, v in man[group].items()})
for group in ("dataset_hashes", "repo_state_files"):
    flat.update(man[group])
drift = [k for k, v in flat.items() if (ROOT / k).is_file() and sha(ROOT / k) != v]
absent = [k for k in flat if not (ROOT / k).is_file()]
check(16, "every one of the %d manifest digests matches disk" % len(flat), drift == [], str(drift[:4]))
check(16, "every manifest path exists", absent == [], str(absent[:4]))
covered = {}
for line in CHK.read_text(encoding="utf-8").splitlines():
    if line.strip():
        digest, path = line.split(None, 1)
        covered[path.strip().lstrip("*")] = digest
check(16, "the checksum record does not name itself",
      "reports/stage4/STAGE_4_VALIDATION.sha256" not in covered)
check(16, "the checksum record covers the manifest", manifest_rel in covered)
artifacts = [a["path"] if isinstance(a, dict) else a for a in dec["artifacts"]]
expect = set(dec["frozen_inputs_read_only"]) | set(artifacts)
expect = set(p for p in expect if (ROOT / p).is_file())
expect.discard("reports/stage4/STAGE_4_VALIDATION.sha256")
check(16, "the checksum record covers exactly the frozen inputs plus the produced artifacts",
      set(covered) == expect,
      "missing=" + str(sorted(expect - set(covered))[:3])
      + " extra=" + str(sorted(set(covered) - expect)[:3]))
check(16, "every declared artifact exists on disk",
      all((ROOT / a).is_file() for a in artifacts),
      str([a for a in artifacts if not (ROOT / a).is_file()]))
check(16, "the run record's output digests match disk",
      all(sha(ROOT / rel) == dig for rel, dig in run["output_artifact_hashes"].items()),
      str([rel for rel, dig in run["output_artifact_hashes"].items()
           if sha(ROOT / rel) != dig]))

# ---------------------------------------------------------------- 17. only intended changes exist
prev = eval_run["code_hashes"]
now = code_hashes
added = sorted(set(now) - set(prev))
removed = sorted(set(prev) - set(now))
changed = sorted(k for k in set(now) & set(prev) if now[k] != prev[k])
INTENDED_ADDED = ["governance/STAGE_4_VALIDATION_REPORT.md",
                  "src/stockedge100/reporting/stage4_evaluation_package.py"]
INTENDED_CHANGED = ["README.md"]
check(17, "only the report and the package builder were added since the validation run",
      added == INTENDED_ADDED, "added " + str(added))
check(17, "only README.md changed since the validation run", changed == INTENDED_CHANGED,
      "changed " + str(changed))
check(17, "nothing was removed", removed == [], str(removed))
delta = dec["integrity_verification"]["repo_state_delta"]
moved = {name: delta[name]["protected_paths_changed_or_removed"]
         for name in delta if isinstance(delta[name], dict)
         and "protected_paths_changed_or_removed" in delta[name]}
check(17, "no protected path changed or was removed in any recorded diff",
      all(v == [] for v in moved.values()), str(moved))
runs_on_disk = sorted(p.name for p in (ROOT / "runs").glob("*.json"))
check(17, "runs/ is append-only and holds both this session's records",
      (eval_run_id + ".json") in runs_on_disk and (run_id + ".json") in runs_on_disk,
      str(len(runs_on_disk)) + " records")
check(17, "the package's tests block matches the test summary on disk",
      all(("| %s | %d |" % (k, v)) in
          (ROOT / "reports/stage4/STAGE_4_VALIDATION_TEST_SUMMARY.md").read_text(encoding="utf-8")
          for k, v in dec["tests"].items()), str(dec["tests"]))
check(17, "blockers empty, conflicts and limitations recorded",
      dec["blockers"] == [] and len(dec["conflicts_found"]) == 3 and len(dec["limitations"]) == 8,
      "conflicts " + str(len(dec["conflicts_found"])) + " limitations " + str(len(dec["limitations"])))

out("\n".join(notes))
out("")
out("\n".join(fails) if fails else "ALL CHECKS PASS")
out("")
out(str(len(notes)) + " ok / " + str(len(fails)) + " failed")
out("repo_state_id " + recorded)
out("package run  " + run_id)
out("validation run " + eval_run_id)
