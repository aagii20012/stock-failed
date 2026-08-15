"""Post-build verification of the Generation 2 Stage 3 decision package.

Derived from _scratch/stage4_evaluation_postbuild_verify.py, which is why the two reversed signatures
are already right here:

    code_hashes, repo_state_id = repo_state()          # hashes FIRST, digest second
    results = verify_sha256_record(record_path, cwd)    # dict[path] -> "OK" | "FAILED" | "MISSING"

Nothing here trusts the package: every number is recomputed from disk or re-derived from the sealed
artifacts and then compared with what the package recorded. Every predicate is written against the
shape enumerated by g2_package_keys{,2,3}.py -- authorization_state holds the *strings* 'false', not
booleans, and `is False` on those would report a failure that is not there.

ASCII-only output: the console is cp1252.
"""
import ast
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


DEC = ROOT / "reports/stage3_g2/STAGE_3_G2_ROTATION_RESEARCH.json"
MAN = ROOT / "reports/stage3_g2/STAGE_3_G2_ARTIFACT_MANIFEST.json"
CHK = ROOT / "reports/stage3_g2/STAGE_3_G2_ROTATION_RESEARCH.sha256"
EVID = ROOT / "reports/stage3_g2/STAGE_3_G2_DEVELOPMENT_ADMISSIBILITY.json"
REPORT = ROOT / "governance/generation_2/STAGE_3_G2_ROTATION_RESEARCH_REPORT.md"
SUMMARY = ROOT / "reports/stage3_g2/STAGE_3_G2_TEST_SUMMARY.md"
PYTEST_TXT = ROOT / "reports/stage3_g2/pytest_stage3_g2_output.txt"

dec = json.loads(DEC.read_text(encoding="utf-8"))
man = json.loads(MAN.read_text(encoding="utf-8"))
evid = json.loads(EVID.read_text(encoding="utf-8"))
md = REPORT.read_text(encoding="utf-8")
crit = json.loads((ROOT / "config/generation_2/g2_gate_criteria.json").read_text(encoding="utf-8"))
proto = json.loads((ROOT / "config/generation_2/g2_rotation_protocol.json").read_text(encoding="utf-8"))
lock = json.loads((ROOT / "governance/generation_2/STAGE_1_G2_PARTITION_LOCK.json").read_text(encoding="utf-8"))
gproto = json.loads((ROOT / "governance/generation_2/STAGE_3_G2_ROTATION_PROTOCOL.json").read_text(encoding="utf-8"))
blob = json.dumps(dec, ensure_ascii=False)

run_id = dec["reproducibility"]["run_id"]
run = json.loads((ROOT / "runs" / (run_id + ".json")).read_text(encoding="utf-8"))

# ---------------------------------------------------------------- 1. repo_state_id recomputes
code_hashes, rsid = repo_state()
recorded = dec["reproducibility"]["repo_state_id"]
check(1, "repo_state_id recomputes from the patterns, unchanged since the build",
      rsid == recorded, rsid[:16] + " vs recorded " + recorded[:16])
check(1, "it is the digest this session set out to record",
      recorded == "1eeeb74ef15e38e097f276604cebfb16461b71bb2b77728b29bcdd5bd58f75a9", recorded[:24])
check(1, "run record and manifest carry the same repo_state_id",
      run["repo_state_id"] == recorded and man["repo_state_id"] == recorded)
check(1, "repo_state_files count matches the recomputation",
      len(man["repo_state_files"]) == len(code_hashes),
      str(len(man["repo_state_files"])) + " vs " + str(len(code_hashes)))
drift_rs = [k for k, v in man["repo_state_files"].items() if code_hashes.get(k) != v]
check(1, "every one of the %d recorded pattern digests still matches disk" % len(code_hashes),
      drift_rs == [], str(drift_rs[:4]))
carriers = [rel for rel in code_hashes
            if recorded in (ROOT / rel).read_text(encoding="utf-8", errors="ignore")]
check(1, "no file covered by the digest carries the digest", carriers == [], str(carriers))
# G2-CONFLICT-4: governance/*.md is single-level, so the Gen 2 report is NOT covered. It is still
# forbidden to carry the tree digest, and the conflict must be recorded rather than assumed.
check(1, "the Gen 2 report is outside the pattern set, as G2-CONFLICT-4 records",
      REPORT.relative_to(ROOT).as_posix() not in code_hashes
      and any("G2-CONFLICT-4" in c for c in dec["conflicts_found"]))
check(1, "config/generation_2/*.json IS covered, the recursive half of the same conflict",
      all("config/generation_2/" + n in code_hashes
          for n in ("g2_rotation_protocol.json", "g2_gate_criteria.json", "g2_cost_model.json")))

# ---------------------------------------------------------------- 2. every checksum record verifies
RECORDS = [("STAGE_0_FREEZE.sha256", ROOT / "governance"),
           ("STAGE_1_FREEZE.sha256", ROOT / "governance")]
for p in sorted(ROOT.glob("governance/*.sha256")):
    if p.name not in ("STAGE_0_FREEZE.sha256", "STAGE_1_FREEZE.sha256"):
        RECORDS.append(("governance/" + p.name, ROOT))
for p in sorted(ROOT.glob("governance/generation_2/*.sha256")):
    RECORDS.append((p.relative_to(ROOT).as_posix(), ROOT))
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
own = "reports/stage3_g2/STAGE_3_G2_ROTATION_RESEARCH.sha256"
check(2, "this package's own record is among them and verifies",
      any(r[0] == own for r in RECORDS) and not any(r[0] == own for r in bad_records))
g2_records = [r for r, _ in RECORDS if "generation_2" in r]
check(2, "both Generation 2 pre-registration records are covered and verify",
      sorted(g2_records) == ["governance/generation_2/STAGE_1_G2_PARTITION_LOCK.sha256",
                             "governance/generation_2/STAGE_3_G2_ROTATION_PROTOCOL.sha256"],
      str(sorted(g2_records)))
check(2, "the package re-verified those two records at build time and got OK on every path",
      set(dec["partition"]["lock_record_verification"].values()) == {"OK"}
      and set(dec["preregistration"]["protocol_record_verification"].values()) == {"OK"},
      str(sorted(set(dec["partition"]["lock_record_verification"].values())
                 | set(dec["preregistration"]["protocol_record_verification"].values()))))

# ---------------------------------------------------------------- 3. frozen inputs unchanged
frozen_drift = [k for k, v in man["frozen_inputs"].items()
                if not (ROOT / k).is_file() or sha(ROOT / k) != v["sha256"]]
check(3, "all %d frozen inputs match their recorded digests" % len(man["frozen_inputs"]),
      frozen_drift == [], str(frozen_drift[:4]))
check(3, "every frozen input is READ_ONLY_NOT_MODIFIED",
      set(e["disposition"] for e in man["frozen_inputs"].values()) == {"READ_ONLY_NOT_MODIFIED"},
      str(sorted(set(e.get("disposition") for e in man["frozen_inputs"].values()))))
check(3, "the decision record's frozen list and the manifest's agree exactly",
      sorted(dec["frozen_inputs_read_only"]) == sorted(man["frozen_inputs"]),
      str(sorted(set(dec["frozen_inputs_read_only"]) ^ set(man["frozen_inputs"]))[:4]))
sealed_now = {rel: sha(ROOT / rel) for rel in
              ("governance/generation_2/STAGE_1_G2_PARTITION_LOCK.json",
               "governance/generation_2/STAGE_3_G2_ROTATION_PROTOCOL.json",
               "config/generation_2/g2_rotation_protocol.json",
               "config/generation_2/g2_gate_criteria.json",
               "config/generation_2/g2_cost_model.json")}
check(3, "the five sealed Generation 2 inputs are byte-for-byte what the package recorded",
      all(sealed_now[k] == man["frozen_inputs"][k]["sha256"] for k in sealed_now),
      str([k for k in sealed_now if sealed_now[k] != man["frozen_inputs"][k]["sha256"]]))
check(3, "the package's own quoted digests resolve to those files",
      (dec["partition"]["lock_sha256"]
       == sealed_now["governance/generation_2/STAGE_1_G2_PARTITION_LOCK.json"]
       and dec["preregistration"]["protocol_sha256"]
       == sealed_now["governance/generation_2/STAGE_3_G2_ROTATION_PROTOCOL.json"]
       and dec["preregistration"]["criteria_sha256"]
       == sealed_now["config/generation_2/g2_gate_criteria.json"]))
check(3, "the charter digest quoted in the record resolves to the charter",
      dec["generation"]["charter_sha256"]
      == sha(ROOT / "governance/generation_2/STAGE_10_GENERATION_2_CHARTER.md"))
check(3, "the Stage 0 constitution freeze re-verified, recorded and computed equal",
      dec["constitution"]["freeze_verified"] is True
      and all(v["recorded"] == v["computed"] for v in dec["constitution"]["freeze_verification"].values())
      and dec["constitution"]["modified_by_this_stage"] is False)

# ---------------------------------------------------------------- 4. Markdown and JSON agree
token = dec["verdict"].split()[-1]
der = crit["verdict_token_derivation"]
agree = [
    ("fail token", der["fail_token"] in md),
    ("generation id", dec["generation"]["generation_id"] in md),
    ("strategy id", dec["preregistration"]["strategy_id"] in md),
    ("universe version", dec["universe"]["universe_version"] in md),
    ("evidence digest", dec["evidence_file"]["evidence_digest"] in md),
    ("run span start", dec["partition"]["window_read_by_this_stage"]["run_span"]["run_start"] in md),
    ("latest session loaded", dec["partition"]["window_read_by_this_stage"]["latest_session_loaded"] in md),
    ("development bound", dec["partition"]["partition"]["development_end"] in md),
    ("18 variants", "18" in md),
    ("36 runs", "36" in md),
    ("tests passed", str(dec["tests"]["passed"]) in md),
    ("decided_by no_candidate_path", dec["selection"]["decided_by"] in md),
    ("selection note verbatim", dec["selection"]["selection_note"] in md),
]
missing = [name for name, ok in agree if not ok]
check(4, "the Markdown report and the JSON decision agree on every headline value",
      missing == [], "absent from the report: " + str(missing))
check(4, "the report carries no tree digest", recorded not in md,
      str(len(set(re.findall(r"\b[0-9a-f]{64}\b", md)))) + " hex64 present, none of them the tree digest")
future = [d for d in (man["produced_artifacts"][REPORT.relative_to(ROOT).as_posix()]["sha256"],
                      sha(DEC), sha(MAN), sha(CHK)) if d in md]
check(4, "the report carries none of the digests that did not exist when it was written",
      future == [], str(future))
check(4, "the report does not emit the sealed PASS token", der["pass_token"] not in md)
check(4, "gate_passed is False and the rollup row says NOT_MET",
      dec["gate_passed"] is False
      and dec["gate_conditions"]["admissible_candidate_exists"]["verdict"] == "NOT_MET")

# ---------------------------------------------------------------- 5. the grid is the sealed grid
grid = dec["preregistration"]["grid"]
sealed_axes = None


def find_axes(node):
    """Locate the sealed axes by identity, not by a guess at where the protocol nests them."""
    if isinstance(node, dict):
        if {"lookback_months", "top_k", "rebalance_frequency"} <= set(node):
            return {k: node[k] for k in ("lookback_months", "top_k", "rebalance_frequency")}
        for v in node.values():
            hit = find_axes(v)
            if hit:
                return hit
    elif isinstance(node, list):
        for v in node:
            hit = find_axes(v)
            if hit:
                return hit
    return None


sealed_axes = find_axes(proto)
check(5, "the three axes in the package are the three axes in the sealed protocol",
      sealed_axes is not None and grid["axes"] == sealed_axes,
      str(grid["axes"]) + " vs sealed " + str(sealed_axes))
check(5, "3 x 3 x 2 = 18 declared, and 18 is what is recorded",
      len(grid["axes"]["lookback_months"]) * len(grid["axes"]["top_k"])
      * len(grid["axes"]["rebalance_frequency"]) == grid["variants_declared"] == 18)
check(5, "two runs per variant, 36 executed, all declared runs executed",
      (grid["runs_per_variant"]["count"], grid["runs_executed"],
       grid["all_declared_runs_executed"]) == (2, 36, True),
      str((grid["runs_per_variant"]["count"], grid["runs_executed"])))
check(5, "zero revisions after seeing a result, in both the package and the evidence",
      grid["revisions_after_seeing_a_result"] == 0
      and evid["grid"]["revisions_after_seeing_a_result"] == 0)
check(5, "the pre-registration was declared before any strategy code",
      dec["preregistration"]["declared_before_any_strategy_code"] is True)
table = dec["grid_results_descriptive_only"]["table"]
check(5, "the descriptive table carries exactly the 18 declared variants, once each",
      len(table) == 18 and len(set(r["variant_id"] for r in table)) == 18, str(len(table)))
expected_ids = set()
for lb in grid["axes"]["lookback_months"]:
    for k in grid["axes"]["top_k"]:
        for rb in grid["axes"]["rebalance_frequency"]:
            expected_ids.add("SE100-G2-S3-C1-ROTATION-L%02d-K%d-%s" % (lb, k, rb))
check(5, "every variant id is the cartesian product of the sealed axes, re-derived here",
      set(r["variant_id"] for r in table) == expected_ids,
      str(sorted(set(r["variant_id"] for r in table) ^ expected_ids)[:3]))
check(5, "the descriptive table is marked as not used in selection",
      dec["grid_results_descriptive_only"]["used_in_selection"] is False)

# ---------------------------------------------------------------- 6. selection was return-blind
sel = dec["selection"]
fields = sorted(set(k for row in sel["inputs"] for k in row))
check(6, "the selection inputs carry no performance field of any kind",
      fields == ["fill_count", "per_run", "research_shutdown_events", "variant_id"], str(fields))
per_run_fields = sorted(set(k for row in sel["inputs"] for pr in row["per_run"] for k in pr))
check(6, "nor does the per-run breakdown inside them",
      per_run_fields == ["fill_count", "label", "research_shutdown_events"], str(per_run_fields))
check(6, "18 inputs, 18 considered, and the ids match the declared grid",
      len(sel["inputs"]) == sel["variants_considered"] == 18
      and set(r["variant_id"] for r in sel["inputs"]) == expected_ids)
check(6, "the rule was frozen before any variant ran and is flagged return-blind",
      sel["frozen_before_any_variant_is_run"] is True and sel["return_blind"] is True)
check(6, "step 1 admitted nobody: eligible list empty, count 0, 18 ineligible",
      (sel["step_1"]["eligible"], sel["step_1"]["eligible_count"], len(sel["step_1"]["ineligible"]))
      == ([], 0, 18),
      str((sel["step_1"]["eligible_count"], len(sel["step_1"]["ineligible"]))))
check(6, "the shutdown counts in step 1 are recomputed here from the descriptive table and agree",
      {r["variant_id"]: r["research_shutdown_events"] for r in sel["step_1"]["ineligible"]}
      == {r["variant_id"]: r["research_shutdown_events"] for r in table})
check(6, "every one of the 18 recorded 2 shutdowns, so the screen could not admit anyone",
      sorted(set(r["research_shutdown_events"] for r in table)) == [2],
      str(sorted(set(r["research_shutdown_events"] for r in table))))
check(6, "steps 2 and 3 were never reached, so the turnover tiebreak never ran",
      sel["step_2"] is None and sel["step_3"] is None and sel["decided_at_step"] is None)
check(6, "no representative exists and the no_candidate_path decided it",
      (sel["representative_variant_id"], sel["representative_exists"], sel["decided_by"])
      == (None, False, "no_candidate_path"))
check(6, "the no_candidate_path forbids loosening the grid, the threshold, the screen and the rule",
      all(w in sel["no_candidate_path"]["prohibition"]
          for w in ("not loosened", "not raised", "not narrowed", "not revised")),
      sel["no_candidate_path"]["prohibition"][:70])
check(6, "the selection note in the decision record is the evidence file's, character for character",
      sel["selection_note"] == evid["selection"]["selection_note"])

# ---------------------------------------------------------------- 7. gate conditions and rollup
gc = dec["gate_conditions"]
hard = sorted(k for k in gc if re.fullmatch(r"S3-C\d", k))
check(7, "seven hard conditions, all present", hard == ["S3-C%d" % i for i in range(1, 8)], str(hard))
check(7, "all seven are NOT_RUN, because Gate 3 is evaluated on a representative and none exists",
      all(gc[k]["verdict"] == "NOT_RUN" for k in hard),
      str(sorted(set(gc[k]["verdict"] for k in hard))))
check(7, "no hard row claims a pass, and none carries a met_by entry",
      all(gc[k]["met_by"] == [] and gc[k]["satisfied_by"] == [] for k in hard))
check(7, "the seven required_verbatim strings are the constitution's, matched against the seal",
      all(gc[k]["required_verbatim"] in json.dumps(crit, ensure_ascii=False) for k in hard),
      str([k for k in hard if gc[k]["required_verbatim"] not in json.dumps(crit, ensure_ascii=False)]))
row = gc["admissible_candidate_exists"]
check(7, "the rollup row is present -- a table without it reads as though the gate were irrelevant",
      "admissible_candidate_exists" in gc)
check(7, "the rollup is NOT_MET, value False, 0 of 18 eligible, 0 evaluated, 0 admitted",
      (row["verdict"], row["value"], row["variants_declared"],
       row["variants_eligible_after_shutdown_screen"], row["candidates_evaluated"],
       row["admitted_candidates"]) == ("NOT_MET", False, 18, 0, 0, []),
      str((row["verdict"], row["value"], row["variants_eligible_after_shutdown_screen"])))
check(7, "the rollup agrees with gate_passed and with the selection block, recomputed here",
      (row["value"] is False) == (dec["gate_passed"] is False)
      == (sel["representative_exists"] is False) == (row["candidates_evaluated"] == 0))
check(7, "NOT_RUN is not a pass: nothing in the table is MET",
      not [k for k in gc if gc[k]["verdict"] == "MET"], str([k for k in gc if gc[k]["verdict"] == "MET"]))
check(7, "candidate_results is empty and stage_verdict counts 0 evaluated, 0 admitted",
      (len(dec["candidate_results"]), dec["stage_verdict"]["candidates_evaluated"],
       len(dec["stage_verdict"]["admitted_candidates"])) == (0, 0, 0))

# ---------------------------------------------------------------- 8. the verdict is the sealed one
check(8, "the emitted token is the sealed FAIL token, character for character",
      token == der["fail_token"], token + " vs " + der["fail_token"])
check(8, "it is not the sealed PASS token", token != der["pass_token"])
check(8, "the pass token appears nowhere except where the derivation names it",
      blob.count(der["pass_token"]) == sum(
          1 for v in (dec["verdict_token_derivation"]["pass_token"],
                      dec["stage_verdict"]["pass_token"]) if v == der["pass_token"])
      + sum(1 for s in (dec["verdict_token_derivation"]["pass_condition"],
                        dec["verdict_token_derivation"]["neither_token_is_a_stage_verdict_for_any_other_stage"],
                        dec["verdict_token_derivation"]["fail_is_a_deliverable"],
                        dec["stage_verdict"]["fail_is_a_deliverable"])
            if der["pass_token"] in s),
      "occurrences " + str(blob.count(der["pass_token"])))
check(8, "the package's own copy of the derivation matches the sealed criteria file",
      all(dec["verdict_token_derivation"][k] == der[k] for k in
          ("pass_token", "fail_token", "pass_condition", "fail_condition")),
      str([k for k in ("pass_token", "fail_token", "pass_condition", "fail_condition")
           if dec["verdict_token_derivation"][k] != der[k]]))
check(8, "the fail route is the no-representative branch the seal describes",
      (dec["stage_verdict"]["fail_route"], dec["stage_verdict"]["route"])
      == ("NO_REPRESENTATIVE_EXISTS", "NO_REPRESENTATIVE_EXISTS"))
check(8, "the verdict written is the verdict the evidence reached -- the portable guard, recomputed",
      dec["stage_verdict"]["verdict"] == "FAIL"
      and dec["stage_verdict"]["verdict_token"] == der["fail_token"]
      and dec["verdict"].endswith(der["fail_token"])
      and dec["gate_passed"] is False)
check(8, "no incoherent combination: a FAIL carries no admitted candidate",
      not (dec["gate_passed"] is False and dec["stage_verdict"]["admitted_candidates"]))
check(8, "the constitutional equivalent is recorded rather than substituted (G2-CONFLICT-12)",
      dec["verdict_token_derivation"]["constitutional_fail_result_equivalent"]
      == "STRATEGY_REJECTED_IN_DEVELOPMENT"
      and any("G2-CONFLICT-12" in c for c in dec["conflicts_found"]))
check(8, "FAIL is recorded as a deliverable, not as a suppressed result",
      der["fail_token"] in dec["verdict_token_derivation"]["fail_is_a_deliverable"]
      and dec["blockers"] == [])

# ---------------------------------------------------------------- 9. nothing after 2021-07-31 read
BOUND = "2021-07-31"
w = dec["partition"]["window_read_by_this_stage"]
check(9, "the latest session loaded anywhere is 2021-07-30, inside the development bound",
      w["latest_session_loaded"] == "2021-07-30" and w["latest_session_loaded"] < BOUND
      and w["development_bound"] == BOUND, w["latest_session_loaded"])
check(9, "validation, Generation 1 holdout and Generation 2 holdout all recorded unread",
      (w["validation_read"], w["generation_1_holdout_read"], w["generation_2_holdout_read"])
      == (False, False, False))
check(9, "the run record's date_range ends before the bound",
      run["date_range"][1] <= BOUND and run["date_range"] == ["2008-07-28", "2021-07-30"],
      str(run["date_range"]))
sessions = [r[k] for r in table for k in ("base_shutdown_session", "stress_shutdown_session")]
check(9, "every shutdown session in the descriptive table predates the bound",
      max(sessions) <= BOUND, "latest " + max(sessions))
# Enumerate every date-valued leaf in the evidence file rather than regex the blob: a bare regex
# reports the partition boundaries as violations, and a check that cannot distinguish a session from
# a declared boundary is not a check.
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
late = {}


def walk_dates(node, path):
    if isinstance(node, str):
        if DATE.match(node) and node > BOUND:
            late.setdefault(node, []).append(path)
    elif isinstance(node, dict):
        for k, v in node.items():
            walk_dates(v, path + "." + k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk_dates(v, path + "[%d]" % i)


walk_dates(evid, "evidence")
walk_dates(dec, "decision")
DECLARED_BOUNDARIES = {dec["partition"]["partition"][k] for k in
                       ("validation_start", "validation_end", "generation_1_holdout_start",
                        "generation_1_holdout_end", "holdout_start", "holdout_end")}
stray = {d: p[:2] for d, p in late.items() if d not in DECLARED_BOUNDARIES}
check(9, "every post-bound date in either artifact is a declared partition boundary, not a session",
      stray == {}, str(stray))
check(9, "the boundaries themselves are the sealed ones",
      DECLARED_BOUNDARIES == {"2021-08-01", "2024-07-31", "2024-08-01", "2026-07-31",
                              "2026-08-01", "2028-07-31"}, str(sorted(DECLARED_BOUNDARIES)))
check(9, "the partition in the package is the partition in the sealed lock",
      all(dec["partition"]["partition"][k] == lock["partition"][k]
          for k in ("development_end", "validation_start", "validation_end",
                    "holdout_start", "holdout_end")),
      str([k for k in ("development_end", "validation_start", "validation_end",
                       "holdout_start", "holdout_end")
           if dec["partition"]["partition"][k] != lock["partition"].get(k)]))

# ---------------------------------------------------------------- 10. holdouts sealed
check(10, "Generation 2's holdout is SEALED and its read is not authorized",
      dec["partition"]["holdout_state"] == "SEALED"
      and dec["authorization"]["holdout_read_authorized"] is False
      and dec["authorization_state"]["generation_2_holdout_read_authorized"] == "false")
check(10, "Generation 1's holdout is SPENT_AND_PROHIBITED and was not read",
      dec["partition"]["generation_1_holdout_state"] == "SPENT_AND_PROHIBITED"
      and dec["authorization_state"]["generation_1_holdout_read"] == "false")
check(10, "the run end precedes every holdout start, proved by comparison here",
      run["date_range"][1] < dec["partition"]["partition"]["generation_1_holdout_start"]
      < dec["partition"]["partition"]["holdout_start"])
check(10, "Stage 4 validation is not authorized by this package",
      dec["authorization"]["stage_4_validation_authorized"] is False
      and dec["authorization_state"]["stage_4_validation_authorized"] == "false")
check(10, "the next authorized action is human review, and it forbids reusing this grid",
      "human review" in dec["next_authorized_stage"]
      and "may not reuse this grid" in dec["next_authorized_stage"],
      dec["next_authorized_stage"][:60])
check(10, "ten explicit non-authorizations are recorded, covering data, broker and edits",
      len(dec["authorization"]["explicit_non_authorizations"]) == 10,
      str(len(dec["authorization"]["explicit_non_authorizations"])))

# ---------------------------------------------------------------- 11. determinism
det = dec["determinism"]
check(11, "36 runs recompared on a fresh load, all identical, none mismatched",
      (det["runs_compared"], det["all_identical"], det["mismatched_runs"]) == (36, True, []),
      str((det["runs_compared"], det["all_identical"])))
check(11, "the evidence file carries a digest for each of the 36 and they are all distinct enough "
          "to be per-run", len(evid["determinism"]["run_digests"]) == 36,
      str(len(evid["determinism"]["run_digests"])))
check(11, "the decision record's determinism block matches the evidence file's",
      (evid["determinism"]["runs_compared"], evid["determinism"]["all_identical"])
      == (det["runs_compared"], det["all_identical"]))

# ---------------------------------------------------------------- 12. no broker, no credential
FORBIDDEN_ROOTS = {"alpaca", "alpaca_trade_api", "alpaca_py", "requests", "httpx", "aiohttp",
                   "socket", "urllib", "urllib2", "urllib3", "http", "httplib", "websocket",
                   "websockets", "boto3", "paramiko", "ftplib", "smtplib", "telnetlib"}
FORBIDDEN_ATTRS = {"environ", "getenv", "urlopen", "urlretrieve", "connect", "Session"}
violations = []
scanned = 0
for path in sorted(ROOT.glob("src/**/*.py")):
    scanned += 1
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
check(12, "AST sweep of all %d modules under src/: no forbidden import, attribute or URL constant"
      % scanned, violations == [], str(sorted(set(violations))[:4]))
g2_modules = [p.relative_to(ROOT).as_posix() for p in sorted(ROOT.glob("src/**/g2_*.py"))]
check(12, "the sweep actually reached this generation's %d new modules -- a sweep that found "
          "nothing because it scanned nothing is not a check" % len(g2_modules),
      len(g2_modules) == 10 and all(m in code_hashes for m in g2_modules), str(g2_modules))
check(12, "every trading and credential flag is false in the authorization state",
      all(dec["authorization_state"][k] == "false" for k in dec["authorization_state"]),
      str(dec["authorization_state"]))
check(12, "live_trading_authorized is the boolean False at the top level",
      dec["live_trading_authorized"] is False)

# ---------------------------------------------------------------- 13. manifest and checksum policy
manifest_rel = "reports/stage3_g2/STAGE_3_G2_ARTIFACT_MANIFEST.json"
check(13, "the manifest excludes its own entry", manifest_rel not in man["produced_artifacts"])
flat = {}
for group in ("frozen_inputs", "produced_artifacts"):
    flat.update({k: v["sha256"] for k, v in man[group].items()})
for group in ("dataset_hashes", "repo_state_files"):
    flat.update(man[group])
drift = [k for k, v in flat.items() if (ROOT / k).is_file() and sha(ROOT / k) != v]
absent = [k for k in flat if not (ROOT / k).is_file()]
check(13, "every one of the %d manifest digests matches disk" % len(flat), drift == [], str(drift[:4]))
check(13, "every manifest path exists", absent == [], str(absent[:4]))
covered = {}
for line in CHK.read_text(encoding="utf-8").splitlines():
    if line.strip():
        digest, path = line.split(None, 1)
        covered[path.strip().lstrip("*")] = digest
check(13, "the checksum record does not name itself", own not in covered)
check(13, "the checksum record covers the manifest", manifest_rel in covered)
expect = set(dec["frozen_inputs_read_only"]) | set(dec["artifacts"])
expect = set(p for p in expect if (ROOT / p).is_file())
expect.discard(own)
check(13, "the record covers exactly the frozen inputs plus the produced artifacts",
      set(covered) == expect,
      "missing=" + str(sorted(expect - set(covered))[:3])
      + " extra=" + str(sorted(set(covered) - expect)[:3]))
chk_drift = [p for p, d in covered.items() if sha(ROOT / p) != d]
check(13, "every one of the %d digests in the record recomputes from disk" % len(covered),
      chk_drift == [], str(chk_drift[:4]))
check(13, "every declared artifact exists on disk",
      all((ROOT / a).is_file() for a in dec["artifacts"]),
      str([a for a in dec["artifacts"] if not (ROOT / a).is_file()]))
check(13, "the run record's output digests match disk",
      all(sha(ROOT / rel) == dig for rel, dig in run["output_artifact_hashes"].items()),
      str([rel for rel, dig in run["output_artifact_hashes"].items() if sha(ROOT / rel) != dig]))
check(13, "the evidence file's recorded sha256 resolves to the evidence file",
      dec["evidence_file"]["sha256"] == sha(EVID))

# ---------------------------------------------------------------- 14. Generation 1 untouched
S4MAN = ROOT / "reports/stage4/STAGE_4_VALIDATION_ARTIFACT_MANIFEST.json"
s4man = json.loads(S4MAN.read_text(encoding="utf-8"))
gen1 = {}
for group in ("frozen_inputs", "produced_artifacts"):
    gen1.update({k: v["sha256"] for k, v in s4man[group].items()})
gen1.update(s4man["repo_state_files"])
# Exactly two Generation 1 pattern files were rewritten by this stage. Neither is under governance/,
# config/ or reports/, so neither is a Generation 1 artifact in the sense section 0 protects:
#   README.md                              -- the stage-status page; the Stage 4 package that locked
#                                             it is sealed, and a new generation is what legitimately
#                                             rewrites it.
#   reporting/stage_package.py             -- the shared builder, which hardcoded "generation": 1 in
#                                             both the decision record and the manifest. A Generation 2
#                                             package would otherwise have claimed Generation 1's
#                                             lineage. Disclosed in the report, and asserted below to
#                                             be additive rather than a rewrite.
BUILDER = "src/stockedge100/reporting/stage_package.py"
ALLOWED_TO_CHANGE = {"README.md", BUILDER}
gen1_drift = [k for k, v in gen1.items()
              if k not in ALLOWED_TO_CHANGE and (not (ROOT / k).is_file() or sha(ROOT / k) != v)]
check(14, "all %d Generation 1 paths recorded by the Stage 4 package are byte-identical"
      % (len(gen1) - len(ALLOWED_TO_CHANGE)), gen1_drift == [], str(gen1_drift[:4]))
check(14, "the exceptions are exactly those two, and both really did change",
      sorted(k for k in ALLOWED_TO_CHANGE if sha(ROOT / k) != gen1[k]) == sorted(ALLOWED_TO_CHANGE),
      str(sorted(k for k in ALLOWED_TO_CHANGE if sha(ROOT / k) == gen1[k])) + " unchanged")
# An allow-list that only widens is not a check. The builder change has to be shown additive, and
# shown disclosed, or it is indistinguishable from an undisclosed rewrite of Generation 1 machinery.
from stockedge100.reporting.stage_package import StageDecision  # noqa: E402
check(14, "the builder's new field defaults to 1, so a Generation 1 rebuild is byte-identical",
      StageDecision.__dataclass_fields__["generation"].default == 1,
      str(StageDecision.__dataclass_fields__["generation"].default))
check(14, "Generation 1's own Stage 4 decision record still reads generation 1, unmodified on disk",
      json.loads((ROOT / "reports/stage4/STAGE_4_VALIDATION.json")
                 .read_text(encoding="utf-8"))["generation"] == 1
      and sha(ROOT / "reports/stage4/STAGE_4_VALIDATION.json")
      == gen1["reports/stage4/STAGE_4_VALIDATION.json"])
check(14, "this package reads generation 2 in both the decision record and the manifest",
      dec["generation"]["generation"] == 2 and man["generation"] == 2,
      str((dec["generation"]["generation"], man["generation"])))
check(14, "the builder change is disclosed by name in the report, not left to a diff to discover",
      BUILDER.split("/", 2)[-1] in md and "generation" in md and "shared builder" in md,
      "named in the report's scope-of-change section")
check(14, "the report does not overclaim: it says no *frozen* module was edited, then names this one",
      "no frozen module edited" in md and md.index("no frozen module edited") < md.index("shared builder"),
      "exception follows the claim it qualifies")
gen1_governed = sorted(k for k in gen1
                       if k.startswith(("governance/", "config/", "reports/"))
                       and "generation_2" not in k)
gov_drift = [k for k in gen1_governed if sha(ROOT / k) != gen1[k]]
check(14, "no file under governance/, config/ or reports/ from Generation 1 changed (%d checked)"
      % len(gen1_governed), gov_drift == [], str(gov_drift[:4]))
gen1_records = [k for k in gen1_governed if k.endswith(".sha256")]
check(14, "every pre-existing .sha256 record is unchanged (%d)" % len(gen1_records),
      not [k for k in gen1_records if sha(ROOT / k) != gen1[k]], str(gen1_records))
check(14, "the package states Generation 1 is closed and no Generation 1 artifact was modified",
      "CLOSED" in dec["generation"]["generation_1_status"]
      and "No Generation 1 arti" in dec["generation"]["generation_1_status"])
new_gov = sorted(p.relative_to(ROOT).as_posix() for p in ROOT.glob("governance/generation_2/*"))
check(14, "every artifact this stage wrote under governance/ lives in generation_2/",
      len(new_gov) == 8 and all(p.startswith("governance/generation_2/") for p in new_gov),
      str(len(new_gov)) + " files")

# ---------------------------------------------------------------- 15. only intended repo changes
prior = sorted(p for p in (ROOT / "runs").glob("SE100-R-*.json") if p.stem < run_id)
prev_run = json.loads(prior[-1].read_text(encoding="utf-8"))
prev = prev_run["code_hashes"]
added = sorted(set(code_hashes) - set(prev))
removed = sorted(set(prev) - set(code_hashes))
changed = sorted(k for k in set(code_hashes) & set(prev) if code_hashes[k] != prev[k])
ADDED_OK = re.compile(r"^(src/stockedge100/(backtest|reporting|strategies)/g2_[a-z0-9_]+\.py"
                      r"|tests/(unit|adversarial)/test_g2_[a-z0-9_]+\.py"
                      r"|config/generation_2/[a-z0-9_]+\.json)$")
unexpected_added = [a for a in added if not ADDED_OK.match(a)]
check(15, "everything added since run %s is a Generation 2 module, test or config (%d added)"
      % (prev_run["run_id"], len(added)), unexpected_added == [], str(unexpected_added))
check(15, "the only changes are README.md and the shared builder",
      changed == sorted(ALLOWED_TO_CHANGE), "changed " + str(changed))
check(15, "nothing was removed or renamed", removed == [], str(removed))
touched_gen1_code = [k for k in changed + added
                     if k.startswith(("src/", "tests/"))
                     and "g2_" not in k.rsplit("/", 1)[-1] and k != BUILDER]
check(15, "no Generation 1 source or test file was touched apart from the shared builder",
      touched_gen1_code == [], str(touched_gen1_code))
check(15, "the strategy, engine and gate modules Generation 1 validated are untouched",
      all(sha(ROOT / k) == gen1[k] for k in gen1
          if k.startswith(("src/stockedge100/strategies/", "src/stockedge100/backtest/"))
          and "g2_" not in k.rsplit("/", 1)[-1]),
      str([k for k in gen1
           if k.startswith(("src/stockedge100/strategies/", "src/stockedge100/backtest/"))
           and "g2_" not in k.rsplit("/", 1)[-1] and sha(ROOT / k) != gen1[k]]))
runs_on_disk = sorted(p.stem for p in (ROOT / "runs").glob("SE100-R-*.json"))
check(15, "runs/ is append-only and holds this package's record",
      run_id in runs_on_disk, str(len(runs_on_disk)) + " records, latest " + runs_on_disk[-1])
check(15, "this package's record is the newest, so nothing ran after the build",
      runs_on_disk[-1] == run_id, runs_on_disk[-1])

# ---------------------------------------------------------------- 16. tests and the regression floor
summary = SUMMARY.read_text(encoding="utf-8")
pytest_txt = PYTEST_TXT.read_text(encoding="utf-8", errors="replace")
tail = [ln for ln in pytest_txt.strip().splitlines() if "passed" in ln or "failed" in ln]
m = re.search(r"(\d+) failed, (\d+) passed", tail[-1]) if tail else None
check(16, "the captured pytest output's own summary line says 1 failed, 1090 passed",
      m is not None and (int(m.group(1)), int(m.group(2)))
      == (dec["tests"]["failed"], dec["tests"]["passed"]),
      tail[-1].strip()[:80] if tail else "no summary line")
check(16, "the decision record's counts are 1090 passed, 1 failed, 0 skipped",
      (dec["tests"]["passed"], dec["tests"]["failed"], dec["tests"]["skipped"]) == (1090, 1, 0),
      str(dec["tests"]))
check(16, "the test summary on disk carries the same three numbers",
      all(str(v) in summary for v in dec["tests"].values()), str(dec["tests"]))
check(16, "the single failure is Generation 1's permanent red marker, not a Generation 2 test",
      "test_no_stage_4_module_can_reach_restricted_data_or_a_broker" in pytest_txt
      and "S4-CONFLICT-7" in summary,
      "marker named in the capture and the summary")
check(16, "the count exceeds Generation 1's 837-test floor -- no test was weakened or removed",
      dec["tests"]["passed"] + dec["tests"]["failed"] > 837,
      str(dec["tests"]["passed"] + dec["tests"]["failed"]) + " collected")
g2_tests = sorted(p.relative_to(ROOT).as_posix() for p in ROOT.glob("tests/**/test_g2_*.py"))
check(16, "the four Generation 2 test modules exist and are inside the pattern set",
      len(g2_tests) == 4 and all(t in code_hashes for t in g2_tests), str(g2_tests))
check(16, "the adversarial multi-position suite is one of them, as section 5 requires",
      "tests/adversarial/test_g2_engine_multiposition.py" in g2_tests)

# ---------------------------------------------------------------- 17. disclosures carried verbatim
DISCLOSURE = lock["validation_reuse_disclosure"]
check(17, "the 820-character validation-reuse disclosure is sealed in the partition lock",
      len(DISCLOSURE) == 820, str(len(DISCLOSURE)))
check(17, "the rotation protocol carries it identically",
      gproto.get("validation_reuse_disclosure") == DISCLOSURE)
check(17, "it appears verbatim in the report", DISCLOSURE in md)
check(17, "it appears verbatim in the decision record's limitations",
      any(DISCLOSURE == lim or DISCLOSURE in lim for lim in dec["limitations"]),
      "limitations " + str(len(dec["limitations"])))
MULT = proto["multiple_comparisons_disclosure"]
check(17, "the multiplicity disclosure is carried verbatim in the report and the evidence file",
      MULT in md and evid["multiple_comparisons_disclosure"] == MULT, str(len(MULT)) + " chars")
check(17, "the evidence self-digest recomputes over its own declared coverage",
      dec["evidence_file"]["evidence_digest"] == evid["evidence_digest"]
      and dec["evidence_file"]["evidence_digest_covers"] == evid["evidence_digest_covers"])
check(17, "twelve conflicts and seven limitations are recorded, none of them empty",
      len(dec["conflicts_found"]) == 12 and len(dec["limitations"]) == 7
      and all(c.strip() for c in dec["conflicts_found"] + dec["limitations"]),
      "conflicts " + str(len(dec["conflicts_found"]))
      + " limitations " + str(len(dec["limitations"])))
check(17, "eleven evidence statements are recorded", len(dec["evidence"]) == 11,
      str(len(dec["evidence"])))

out("\n".join(notes))
out("")
out("\n".join(fails) if fails else "ALL CHECKS PASS")
out("")
out(str(len(notes)) + " ok / " + str(len(fails)) + " failed")
out("repo_state_id " + recorded)
out("package run   " + run_id)
out("verdict       " + dec["verdict"])
