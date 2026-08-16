"""Post-build verification of the Generation 2 Stage 3 ATTEMPT 2 decision package.

Adapted from _scratch/g2_stage3_postbuild_verify.py (the Attempt 1 sweep), which is why the two
reversed helper signatures are already right here:

    code_hashes, repo_state_id = repo_state()          # hashes FIRST, digest second
    results = verify_sha256_record(record_path, cwd)    # dict[path] -> "OK" | "FAILED" | "MISSING"

Nothing here trusts the package: every number is recomputed from disk or re-derived from the sealed
artifacts and then compared with what the package recorded.

Where Attempt 2 differs from Attempt 1, and where a copied predicate would have produced a false
FAIL:

  * a representative EXISTS. Selection reached step 2 (lowest turnover) and decided there, so the
    Attempt 1 predicates (step_2 is None, decided_by == "no_candidate_path") are all inverted.
  * all seven hard conditions were actually RUN. Attempt 1's "all seven are NOT_RUN" is wrong here;
    three are MET and four NOT_MET.
  * zero research shutdowns, so every *_shutdown_session is None. `max(sessions)` would raise.
  * both Attempt 1 verdict tokens appear in the report ON PURPOSE, in prose about Attempt 1. The
    honest predicate is that this package's own emitted token is neither of them, and that every
    mention of them sits on a line that names Attempt 1.
  * the fifth disclosure carrier -- this package's own decision record -- did not exist at build
    time and is recorded "present": false. It exists now, so it is re-measured here.

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


A2 = "reports/stage3_g2_attempt2/"
DEC = ROOT / (A2 + "STAGE_3_G2_A2_ROTATION_RESEARCH.json")
MAN = ROOT / (A2 + "STAGE_3_G2_A2_ARTIFACT_MANIFEST.json")
CHK = ROOT / (A2 + "STAGE_3_G2_A2_ROTATION_RESEARCH.sha256")
EVID = ROOT / (A2 + "STAGE_3_G2_A2_DEVELOPMENT_ADMISSIBILITY.json")
REPORT = ROOT / "governance/generation_2/STAGE_3_G2_ROTATION_RA1_RESEARCH_REPORT.md"
SUMMARY = ROOT / (A2 + "STAGE_3_G2_A2_TEST_SUMMARY.md")
PYTEST_TXT = ROOT / (A2 + "pytest_stage3_g2_attempt2_output.txt")

dec = json.loads(DEC.read_text(encoding="utf-8"))
man = json.loads(MAN.read_text(encoding="utf-8"))
evid = json.loads(EVID.read_text(encoding="utf-8"))
md = REPORT.read_text(encoding="utf-8")
crit = json.loads((ROOT / "config/generation_2/g2_gate_criteria_ra1.json").read_text(encoding="utf-8"))
proto = json.loads((ROOT / "config/generation_2/g2_rotation_ra1_protocol.json").read_text(encoding="utf-8"))
lock = json.loads((ROOT / "governance/generation_2/STAGE_1_G2_PARTITION_LOCK.json").read_text(encoding="utf-8"))
gproto = json.loads((ROOT / "governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.json").read_text(encoding="utf-8"))
blob = json.dumps(dec, ensure_ascii=False)

run_id = dec["reproducibility"]["run_id"]
run = json.loads((ROOT / "runs" / (run_id + ".json")).read_text(encoding="utf-8"))
# the run record immediately before this one is Attempt 2's own pre-registration seal; section 4
# resolves the seal-time digest against it and section 15 diffs the tree against it
prior = sorted(p for p in (ROOT / "runs").glob("SE100-R-*.json") if p.stem < run_id)
prev_run = json.loads(prior[-1].read_text(encoding="utf-8"))

# ---------------------------------------------------------------- 1. repo_state_id recomputes
code_hashes, rsid = repo_state()
recorded = dec["reproducibility"]["repo_state_id"]
check(1, "repo_state_id recomputes from the patterns, unchanged since the build",
      rsid == recorded, rsid[:16] + " vs recorded " + recorded[:16])
check(1, "it is the digest this session's build recorded",
      recorded == "40c0c8b1a6043ed13f467674b287ba8c64c78a18fa13858f911ad44b2945f83d", recorded[:24])
check(1, "run record and manifest carry the same repo_state_id",
      run["repo_state_id"] == recorded and man["repo_state_id"] == recorded)
check(1, "repo_state_files count matches the recomputation",
      len(man["repo_state_files"]) == len(code_hashes) == 153,
      str(len(man["repo_state_files"])) + " vs " + str(len(code_hashes)))
drift_rs = [k for k, v in man["repo_state_files"].items() if code_hashes.get(k) != v]
check(1, "every one of the %d recorded pattern digests still matches disk" % len(code_hashes),
      drift_rs == [], str(drift_rs[:4]))
carriers = [rel for rel in code_hashes
            if recorded in (ROOT / rel).read_text(encoding="utf-8", errors="ignore")]
check(1, "no file covered by the digest carries the digest", carriers == [], str(carriers))
# G2-CONFLICT-4: governance/*.md is single-level, so the Gen 2 report is NOT covered, while
# config/generation_2/*.json IS. Both directions are asserted -- a check that only confirms what it
# expects confirms nothing.
check(1, "the Attempt 2 report is outside the pattern set, as G2-CONFLICT-4 records",
      REPORT.relative_to(ROOT).as_posix() not in code_hashes
      and any("G2-CONFLICT-4" in c for c in dec["conflicts_found"]))
check(1, "config/generation_2/*.json IS covered, the recursive half of the same conflict",
      all("config/generation_2/" + n in code_hashes
          for n in ("g2_rotation_ra1_protocol.json", "g2_gate_criteria_ra1.json",
                    "g2_cost_model.json")))
gov_g2 = [k for k in code_hashes if k.startswith("governance/generation_2/")]
check(1, "no governance/generation_2 file at all is inside the patterns", gov_g2 == [], str(gov_g2[:3]))

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
own = A2 + "STAGE_3_G2_A2_ROTATION_RESEARCH.sha256"
check(2, "this package's own record is among them and verifies",
      any(r[0] == own for r in RECORDS) and not any(r[0] == own for r in bad_records))
g2_records = sorted(r for r, _ in RECORDS if "generation_2" in r)
check(2, "all three Generation 2 pre-registration records are covered and verify",
      g2_records == ["governance/generation_2/STAGE_1_G2_PARTITION_LOCK.sha256",
                     "governance/generation_2/STAGE_3_G2_ROTATION_PROTOCOL.sha256",
                     "governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.sha256"],
      str(g2_records))
check(2, "Attempt 1's record is one of them and still verifies -- it was not reopened",
      "governance/generation_2/STAGE_3_G2_ROTATION_PROTOCOL.sha256" in g2_records
      and not any("STAGE_3_G2_ROTATION_PROTOCOL.sha256" in r[0] for r in bad_records))
check(2, "the package re-verified the lock and the RA1 protocol at build time, OK on every path",
      set(dec["partition"]["lock_record_verification"].values()) == {"OK"}
      and set(dec["preregistration"]["protocol_record_verification"].values()) == {"OK"},
      str(sorted(set(dec["partition"]["lock_record_verification"].values())
                 | set(dec["preregistration"]["protocol_record_verification"].values()))))

# ---------------------------------------------------------------- 3. frozen inputs unchanged
frozen_drift = [k for k, v in man["frozen_inputs"].items()
                if not (ROOT / k).is_file() or sha(ROOT / k) != v["sha256"]]
check(3, "all %d frozen inputs match their recorded digests" % len(man["frozen_inputs"]),
      frozen_drift == [] and len(man["frozen_inputs"]) == 19, str(frozen_drift[:4]))
check(3, "every frozen input is READ_ONLY_NOT_MODIFIED",
      set(e["disposition"] for e in man["frozen_inputs"].values()) == {"READ_ONLY_NOT_MODIFIED"},
      str(sorted(set(e.get("disposition") for e in man["frozen_inputs"].values()))))
check(3, "the decision record's frozen list and the manifest's agree exactly",
      sorted(dec["frozen_inputs_read_only"]) == sorted(man["frozen_inputs"]),
      str(sorted(set(dec["frozen_inputs_read_only"]) ^ set(man["frozen_inputs"]))[:4]))
SEALED = ("governance/generation_2/STAGE_1_G2_PARTITION_LOCK.json",
          "governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.json",
          "governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.md",
          "config/generation_2/g2_rotation_ra1_protocol.json",
          "config/generation_2/g2_gate_criteria_ra1.json",
          "config/generation_2/g2_cost_model.json")
sealed_now = {rel: sha(ROOT / rel) for rel in SEALED}
check(3, "the six sealed Attempt 2 inputs are byte-for-byte what the package recorded",
      all(sealed_now[k] == man["frozen_inputs"][k]["sha256"] for k in sealed_now),
      str([k for k in sealed_now if sealed_now[k] != man["frozen_inputs"][k]["sha256"]]))
check(3, "the package's own quoted digests resolve to those files",
      (dec["partition"]["lock_sha256"]
       == sealed_now["governance/generation_2/STAGE_1_G2_PARTITION_LOCK.json"]
       and dec["preregistration"]["protocol_sha256"]
       == sealed_now["governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.json"]
       and dec["preregistration"]["criteria_sha256"]
       == sealed_now["config/generation_2/g2_gate_criteria_ra1.json"]))
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
    ("verdict line", dec["verdict"] in md),
    ("fail token", der["fail_token"] in md),
    ("generation id", dec["generation"]["generation_id"] in md),
    ("strategy id", dec["attempt"]["strategy_id"] in md),
    ("representative", dec["selection"]["representative_variant_id"] in md),
    ("universe version", dec["universe"]["universe_version"] in md),
    ("evidence digest", dec["evidence_file"]["evidence_digest"] in md),
    ("run span start", dec["partition"]["window_read_by_this_stage"]["run_span"]["run_start"] in md),
    ("latest session loaded", dec["partition"]["window_read_by_this_stage"]["latest_session_loaded"] in md),
    ("development bound", dec["partition"]["partition"]["development_end"] in md),
    ("18 variants", "18" in md),
    ("36 runs", "36" in md),
    ("tests passed", str(dec["tests"]["passed"]) in md),
    ("selection step", "step 2" in md),
    ("selection criterion", "lowest turnover" in md),
    ("winning fill count", str(dec["selection"]["step_2"]["fill_counts"]
                               [dec["selection"]["representative_variant_id"]]) in md),
]
missing = [name for name, ok in agree if not ok]
check(4, "the Markdown report and the JSON decision agree on every headline value",
      missing == [], "absent from the report: " + str(missing))
check(4, "the report carries no tree digest", recorded not in md,
      str(len(set(re.findall(r"\b[0-9a-f]{64}\b", md)))) + " hex64 present, none of them the tree digest")
hex64 = set(re.findall(r"\b[0-9a-f]{64}\b", md))
on_disk = {}
for rel, d in list(man["frozen_inputs"].items()):
    on_disk[d["sha256"]] = rel
for rel, d in list(man["produced_artifacts"].items()):
    on_disk.setdefault(d["sha256"], rel)
on_disk[dec["evidence_file"]["evidence_digest"]] = "evidence self-digest"
on_disk[dec["adaptation_disclosure_carriage"]["sha256_of_utf8"]] = "adaptation disclosure"
on_disk[dec["universe"]["universe_identity_sha256"]] = "universe identity"
on_disk[prev_run["repo_state_id"]] = "repo_state_id at the pre-registration seal"
unresolved = sorted(h for h in hex64 if h not in on_disk)
check(4, "every one of the %d digests quoted in the report resolves to a real artifact" % len(hex64),
      unresolved == [], str(unresolved[:3]))
# Two of those are not file digests, so each gets its own resolution rather than a map entry alone.
check(4, "the universe digest quoted in the report is the one the universe_version abbreviates",
      dec["universe"]["universe_version"].endswith(dec["universe"]["universe_identity_sha256"][:16])
      and dec["universe"]["universe_identity_sha256"] in md,
      dec["universe"]["universe_version"])
check(4, "the 'repo_state_id at seal' the report quotes is the seal run record's, not this build's",
      prev_run["repo_state_id"] in md and prev_run["repo_state_id"] != recorded
      and prev_run["run_id"] in md,
      "seal " + prev_run["repo_state_id"][:16] + " vs build " + recorded[:16])
own_digest = man["produced_artifacts"][REPORT.relative_to(ROOT).as_posix()]["sha256"]
future = [d for d in (own_digest, sha(DEC), sha(MAN), sha(CHK)) if d in md]
check(4, "the report carries neither its own digest nor any digest that post-dates it",
      future == [], str(future))
check(4, "the report does not emit the sealed Attempt 2 PASS token", der["pass_token"] not in md)
check(4, "gate_passed is False and the rollup row says NOT_MET",
      dec["gate_passed"] is False
      and dec["gate_conditions"]["admissible_candidate_exists"]["verdict"] == "NOT_MET")

# ---------------------------------------------------------------- 5. the grid is the sealed grid
grid = dec["preregistration"]["grid"]


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
check(5, "the axes are unchanged from Attempt 1, as section 2 of the instruction requires",
      sealed_axes == find_axes(json.loads(
          (ROOT / "config/generation_2/g2_rotation_protocol.json").read_text(encoding="utf-8"))),
      str(sealed_axes))
check(5, "3 x 3 x 2 = 18 declared, and 18 is what is recorded",
      len(grid["axes"]["lookback_months"]) * len(grid["axes"]["top_k"])
      * len(grid["axes"]["rebalance_frequency"]) == grid["variants_declared"] == 18)
check(5, "two runs per variant, 36 executed, all declared runs executed",
      (grid["runs_per_variant"]["count"], grid["runs_executed"],
       grid["all_declared_runs_executed"]) == (2, 36, True),
      str((grid["runs_per_variant"]["count"], grid["runs_executed"])))
check(5, "the grid was not widened from Attempt 1",
      evid["grid"]["grid_widened_from_attempt_1"] is False,
      str(evid["grid"]["grid_widened_from_attempt_1"]))
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
            expected_ids.add("SE100-G2-S3-C2-ROTATION-RA1-L%02d-K%d-%s" % (lb, k, str(rb).upper()))
check(5, "every variant id is the cartesian product of the sealed axes, re-derived here",
      set(r["variant_id"] for r in table) == expected_ids,
      str(sorted(set(r["variant_id"] for r in table) ^ expected_ids)[:3]))
check(5, "every variant id is an Attempt 2 id -- none reuses Attempt 1's C1 namespace",
      all(r["variant_id"].startswith("SE100-G2-S3-C2-ROTATION-RA1-") for r in table)
      and not any("S3-C1-ROTATION" in r["variant_id"] for r in table))
check(5, "the descriptive table is marked as not used in selection",
      dec["grid_results_descriptive_only"]["used_in_selection"] is False)
cov = dec["grid_results_descriptive_only"]["coverage"]
check(5, "all 16 sealed reported-but-not-gating quantities are covered, none dropped",
      cov["quantities"] == cov["quantities_sealed"] == 16 == len(cov["map"]),
      str((cov["quantities"], cov["quantities_sealed"], len(cov["map"]))))
for col in ("ladder_descents", "lockout_arms", "stops_filled", "throttle_legs_scheduled"):
    present = all(("base_" + col) in r and ("stress_" + col) in r for r in table)
    check(5, "the risk-architecture column %s is present for both runs of every variant" % col,
          present)

# ---------------------------------------------------------------- 6. selection was return-blind
sel = dec["selection"]
fields = sorted(set(k for row in sel["inputs"] for k in row))
check(6, "the selection inputs carry no performance field of any kind",
      fields == ["fill_count", "per_run", "research_shutdown_events", "variant_id"], str(fields))
per_run_fields = sorted(set(k for row in sel["inputs"] for pr in row["per_run"] for k in pr))
check(6, "nor does the per-run breakdown inside them",
      per_run_fields == ["fills", "label", "research_shutdown_events"], str(per_run_fields))
check(6, "18 inputs, 18 considered, and the ids match the declared grid",
      len(sel["inputs"]) == sel["variants_considered"] == 18
      and set(r["variant_id"] for r in sel["inputs"]) == expected_ids)
check(6, "the rule was frozen before any variant ran and is flagged return-blind",
      sel["frozen_before_any_variant_is_run"] is True and sel["return_blind"] is True
      and sel["unchanged_from_attempt_1"] is True)
check(6, "step 1 admitted all 18: zero shutdowns everywhere, nobody eliminated",
      (len(sel["step_1"]["eligible"]), sel["step_1"]["eligible_count"],
       len(sel["step_1"]["ineligible"])) == (18, 18, 0),
      str((sel["step_1"]["eligible_count"], len(sel["step_1"]["ineligible"]))))
check(6, "the shutdown counts behind step 1 are recomputed here from the descriptive table and agree",
      all(r["research_shutdown_events"] == 0 for r in table)
      and all(r["research_shutdown_events"] == 0 for r in sel["inputs"]),
      "shutdown counts seen: " + str(sorted(set(r["research_shutdown_events"] for r in table))))
# Step 2 is the tiebreak that actually decided it. Recompute the minimum from the inputs rather than
# trust the recorded winner, and require the minimum to be UNIQUE -- a tie would have to reach step 3.
fill_counts = {r["variant_id"]: r["fill_count"] for r in sel["inputs"]}
lowest = min(fill_counts.values())
winners = sorted(v for v, f in fill_counts.items() if f == lowest)
check(6, "the lowest fill count across the 18 is unique, so step 2 could decide alone",
      len(winners) == 1, "minimum %d attained by %d variant(s)" % (lowest, len(winners)))
check(6, "the representative is that unique minimum, recomputed here from the selection inputs",
      winners == [sel["representative_variant_id"]] and lowest == 189,
      winners[0] + " at " + str(lowest) + " fills")
check(6, "the recorded step_2 fill counts equal the table's fill_count_both_runs, all 18",
      sel["step_2"]["fill_counts"] == {r["variant_id"]: r["fill_count_both_runs"] for r in table},
      str(len(sel["step_2"]["fill_counts"])) + " entries")
check(6, "the tiebreak is fill count, not gross notional -- a partial return proxy is excluded",
      sel["step_2"]["criterion"] == "lowest_turnover"
      and "fill count" in sel["step_2"]["definition"]
      and "return proxy" in sel["step_2"]["why_not_gross_notional"])
check(6, "step 3 was never reached, so the lexicographic tiebreak never ran",
      sel["step_3"]["reached"] is False)
check(6, "a representative exists and step 2 decided it -- not step 1, and not any return figure",
      (sel["representative_exists"], sel["decided_at_step"], sel["decided_by"])
      == (True, 2, "lowest_turnover"))
check(6, "the representative is L12-K1-QUARTERLY, and it is one of the 18 declared ids",
      sel["representative_variant_id"] == "SE100-G2-S3-C2-ROTATION-RA1-L12-K1-QUARTERLY"
      and sel["representative_variant_id"] in expected_ids)
# The structural guarantee, not just the claim: the dataclass has no field that could carry a return.
from stockedge100.strategies.g2_runner_ra1 import (  # noqa: E402
    SelectionInputRA1, SELECTION_FIELD_NAMES)
check(6, "the selection dataclass's real field tuple is the declared return-blind one",
      tuple(SelectionInputRA1.__dataclass_fields__) == tuple(SELECTION_FIELD_NAMES)
      == ("variant_id", "shutdown_events", "fill_count", "per_run"),
      str(tuple(SelectionInputRA1.__dataclass_fields__)))
RETURNISH = ("return", "pnl", "profit", "drawdown", "sharpe", "cagr", "win", "equity")
check(6, "no field name in it is return-shaped, checked against an allow-list of forbidden stems",
      not [f for f in SelectionInputRA1.__dataclass_fields__ if any(s in f.lower() for s in RETURNISH)],
      str([f for f in SelectionInputRA1.__dataclass_fields__
           if any(s in f.lower() for s in RETURNISH)]))
check(6, "the second fail path forbids promoting a runner-up",
      "no runner-up is promoted" in sel["second_fail_path"]["runner_up_not_promoted"]
      or "not promoted" in sel["second_fail_path"]["runner_up_not_promoted"],
      sel["second_fail_path"]["runner_up_not_promoted"][:60])
check(6, "the selection note in the decision record is the evidence file's, character for character",
      sel["selection_note"] == evid["selection"]["selection_note"])

# ---------------------------------------------------------------- 7. gate conditions and rollup
gc = dec["gate_conditions"]
hard = sorted(k for k in gc if re.fullmatch(r"S3-C\d", k))
check(7, "seven hard conditions, all present", hard == ["S3-C%d" % i for i in range(1, 8)], str(hard))
check(7, "none is NOT_RUN -- Gate 3 was actually reached and evaluated this time",
      not [k for k in hard if gc[k]["verdict"] in ("NOT_RUN", "UNKNOWN", "NOT_EVALUABLE")],
      str(sorted(set(gc[k]["verdict"] for k in hard))))
met = sorted(k for k in hard if gc[k]["satisfied"] is True)
not_met = sorted(k for k in hard if gc[k]["satisfied"] is False)
check(7, "three satisfied (S3-C2, S3-C4, S3-C7) and four not (S3-C1, S3-C3, S3-C5, S3-C6)",
      met == ["S3-C2", "S3-C4", "S3-C7"] and not_met == ["S3-C1", "S3-C3", "S3-C5", "S3-C6"],
      "met " + str(met) + " not_met " + str(not_met))
check(7, "verdict and satisfied agree on every row -- aggregation is on satisfaction, not on MET",
      all((gc[k]["verdict"] == "MET") == (gc[k]["satisfied"] is True) for k in hard
          if not gc[k]["not_applicable_for"]),
      str([k for k in hard if (gc[k]["verdict"] == "MET") != (gc[k]["satisfied"] is True)]))
check(7, "S3-C1..S3-C6 gate on both runs; S3-C7 gates on #BASE alone, per G2A2-CONFLICT-25",
      all(gc["S3-C%d" % i]["gating_runs"] == ["#BASE", "#STRESS"] for i in range(1, 7))
      and gc["S3-C7"]["gating_runs"] == ["#BASE"],
      str({k: gc[k]["gating_runs"] for k in hard}))
check(7, "no row claims satisfaction on a run that is not in its own gating scope",
      not [k for k in hard if set(gc[k]["met_by"]) - set(gc[k]["gating_runs"])],
      str([k for k in hard if set(gc[k]["met_by"]) - set(gc[k]["gating_runs"])]))
check(7, "every not-satisfied row names the run(s) that failed it -- no bare NOT_MET",
      all(gc[k]["not_met_by"] for k in not_met),
      str({k: gc[k]["not_met_by"] for k in not_met}))
check(7, "the seven required_verbatim strings are the sealed criteria's, matched against the seal",
      all(gc[k]["required_verbatim"] in json.dumps(crit, ensure_ascii=False) for k in hard),
      str([k for k in hard if gc[k]["required_verbatim"] not in json.dumps(crit, ensure_ascii=False)]))
row = gc["admissible_candidate_exists"]
check(7, "the rollup row is present -- a table without it reads as though the gate were irrelevant",
      "admissible_candidate_exists" in gc)
check(7, "the rollup is NOT_MET, value False, 18 declared, 18 eligible, 1 evaluated, 0 admitted",
      (row["verdict"], row["value"], row["variants_declared"],
       row["variants_eligible_after_shutdown_screen"], row["candidates_evaluated"],
       row["admitted_candidates"]) == ("NOT_MET", False, 18, 18, 1, []),
      str((row["verdict"], row["value"], row["variants_eligible_after_shutdown_screen"],
           row["candidates_evaluated"])))
check(7, "the rollup names the representative that was evaluated",
      row["representative"] == sel["representative_variant_id"])
# The rollup's two per-run failure lists must be exactly what the per-condition rows say. Attempt 1's
# copy of this check aggregated the wrong way and produced a false FAIL for S3-C6; here the base and
# stress lists are recomputed independently from met_by / not_met_by.
base_fail = sorted(k for k in hard if "#BASE" in gc[k]["not_met_by"])
stress_fail = sorted(k for k in hard if "#STRESS" in gc[k]["not_met_by"])
check(7, "the rollup's base failure list is recomputed from the rows and agrees",
      row["conditions_not_satisfied_base"] == base_fail == ["S3-C3", "S3-C5", "S3-C6"],
      str(row["conditions_not_satisfied_base"]) + " vs recomputed " + str(base_fail))
check(7, "the rollup's stress failure list is recomputed from the rows and agrees",
      row["conditions_not_satisfied_stress"] == stress_fail
      == ["S3-C1", "S3-C3", "S3-C5", "S3-C6"],
      str(row["conditions_not_satisfied_stress"]) + " vs recomputed " + str(stress_fail))
check(7, "the union of the two lists is exactly the set of unsatisfied rows -- conjunctive, both-gate",
      sorted(set(base_fail) | set(stress_fail)) == not_met)
check(7, "the rollup agrees with gate_passed and with the candidate count, recomputed here",
      (row["value"] is False) == (dec["gate_passed"] is False)
      == (len(dec["candidate_results"]) == 1) == (row["candidates_evaluated"] == 1))
check(7, "one candidate evaluated, not admitted, and stage_verdict agrees",
      (len(dec["candidate_results"]), dec["candidate_results"][0]["admitted"],
       dec["stage_verdict"]["candidates_evaluated"],
       len(dec["stage_verdict"]["admitted_candidates"])) == (1, False, 1, 0),
      str((len(dec["candidate_results"]), dec["candidate_results"][0]["admitted"])))
basis = dec["candidate_results"][0]["admission_basis"]
check(7, "the candidate's own basis lists the same failures, per run, as the rollup",
      sorted(basis["base_conditions_not_satisfied"]) == base_fail
      and sorted(basis["stress_conditions_not_satisfied"]) == stress_fail,
      str(sorted(basis["base_conditions_not_satisfied"])))
check(7, "the restrictive both-gate reading was adopted, not the permissive base-only one",
      basis.get("permissive_base_only_reading_would_give") is False
      and basis["conflict_ref"] == "G2A2-CONFLICT-25",
      str(basis.get("permissive_base_only_reading_would_give")))
check(7, "the candidate is the representative, and the only candidate",
      dec["candidate_results"][0]["variant_id"] == sel["representative_variant_id"])

# ---------------------------------------------------------------- 8. the verdict is the sealed one
A1_TOKENS = ("STAGE_3_G2_STRATEGY_ADMITTED_IN_DEVELOPMENT", "STAGE_3_G2_NO_CANDIDATE")
check(8, "the emitted token is the sealed Attempt 2 FAIL token, character for character",
      token == der["fail_token"] == "STAGE_3_G2_ATTEMPT_2_NO_CANDIDATE",
      token + " vs " + der["fail_token"])
check(8, "it is not the sealed Attempt 2 PASS token", token != der["pass_token"])
check(8, "it is neither of Attempt 1's tokens -- Attempt 1's verdict is not restated as this one's",
      token not in A1_TOKENS, token)
check(8, "the package says so itself, withholding both Attempt 1 tokens by name",
      sorted(dec["stage_verdict"]["attempt_1_tokens_withheld"]) == sorted(A1_TOKENS),
      str(dec["stage_verdict"]["attempt_1_tokens_withheld"]))
# Both Attempt 1 tokens DO appear in the report, in prose about Attempt 1. That is correct, so the
# predicate is about placement, not absence: every mention must sit on a line naming Attempt 1.
stray_a1 = []
for i, line in enumerate(md.splitlines(), 1):
    for t in A1_TOKENS:
        if t in line and "ttempt 1" not in line:
            stray_a1.append("L%d %s" % (i, line.strip()[:70]))
check(8, "every mention of an Attempt 1 token in the report sits on a line naming Attempt 1",
      stray_a1 == [], str(stray_a1[:2]))
check(8, "the package's own copy of the derivation matches the sealed criteria file",
      all(dec["verdict_token_derivation"][k] == der[k] for k in
          ("pass_token", "fail_token", "pass_condition", "fail_condition")),
      str([k for k in ("pass_token", "fail_token", "pass_condition", "fail_condition")
           if dec["verdict_token_derivation"][k] != der[k]]))
check(8, "the fail route is the representative-failed branch, not the no-representative branch",
      (dec["stage_verdict"]["fail_route"], dec["stage_verdict"]["route"])
      == ("REPRESENTATIVE_FAILED_AT_LEAST_ONE_CONDITION",
          "REPRESENTATIVE_FAILED_AT_LEAST_ONE_CONDITION"),
      str(dec["stage_verdict"]["fail_route"]))
check(8, "and the route agrees with the selection: a representative really does exist",
      dec["stage_verdict"]["representative_exists"] is True and sel["representative_exists"] is True)
check(8, "the verdict written is the verdict the evidence reached -- the portable guard, recomputed",
      dec["stage_verdict"]["verdict"] == "FAIL"
      and dec["stage_verdict"]["verdict_token"] == der["fail_token"]
      and dec["verdict"].endswith(der["fail_token"])
      and dec["gate_passed"] is False)
check(8, "no incoherent combination: a FAIL carries no admitted candidate",
      not (dec["gate_passed"] is False and dec["stage_verdict"]["admitted_candidates"]))
check(8, "the evidence file's stage_verdict says the same thing",
      evid["stage_verdict"]["verdict_token"] == der["fail_token"],
      str(evid["stage_verdict"]["verdict_token"]))
check(8, "the constitutional equivalent is recorded rather than substituted (G2A2-CONFLICT-21)",
      dec["verdict_token_derivation"]["constitutional_fail_result_equivalent"]
      == "STRATEGY_REJECTED_IN_DEVELOPMENT"
      and any("G2A2-CONFLICT-21" in c for c in dec["conflicts_found"]))
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
check(9, "the run record's date_range ends before the bound and matches Attempt 1's span",
      run["date_range"][1] <= BOUND and run["date_range"] == ["2008-07-28", "2021-07-30"],
      str(run["date_range"]))
check(9, "the run span was recomputed from the loaded series, not carried on trust",
      "recomputes every value" in dec["partition"]["run_span_recheck"]["requirement"])
sessions = [r[k] for r in table for k in ("base_shutdown_session", "stress_shutdown_session")]
check(9, "no shutdown session exists to compare, because no run shut down (36 of 36 clean)",
      all(s is None for s in sessions) and len(sessions) == 36,
      str(len(sessions)) + " session slots, all None")
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
check(10, "the run record carries the holdout as LOCKED", run["holdout_state"] == "LOCKED",
      str(run["holdout_state"]))
check(10, "the run end precedes every holdout start, proved by comparison here",
      run["date_range"][1] < dec["partition"]["partition"]["generation_1_holdout_start"]
      < dec["partition"]["partition"]["holdout_start"])
check(10, "Stage 4 validation is not authorized by this package",
      dec["authorization"]["stage_4_validation_authorized"] is False
      and dec["authorization_state"]["stage_4_validation_authorized"] == "false")
check(10, "no Attempt 3 is authorized either",
      dec["authorization"]["attempt_3_authorized"] is False
      and dec["authorization_state"]["attempt_3_authorized"] == "false")
check(10, "the next authorized action is human review",
      "human review" in dec["next_authorized_stage"], dec["next_authorized_stage"][:70])
check(10, "thirteen explicit non-authorizations are recorded, covering data, broker and edits",
      len(dec["authorization"]["explicit_non_authorizations"]) == 13
      and all(s.strip() for s in dec["authorization"]["explicit_non_authorizations"]),
      str(len(dec["authorization"]["explicit_non_authorizations"])))

# ---------------------------------------------------------------- 11. determinism and reconciliation
det = dec["determinism"]
check(11, "36 runs recompared on a fresh load, all identical, none mismatched",
      (det["runs_compared"], det["all_identical"], det["mismatched_runs"]) == (36, True, []),
      str((det["runs_compared"], det["all_identical"])))
check(11, "the evidence file carries a digest for each of the 36",
      len(evid["determinism"]["run_digests"]) == 36, str(len(evid["determinism"]["run_digests"])))
check(11, "the decision record's determinism block matches the evidence file's",
      (evid["determinism"]["runs_compared"], evid["determinism"]["all_identical"])
      == (det["runs_compared"], det["all_identical"]))
rec = dec["reconciliation"]
check(11, "reconciliation ran on all 36 runs with zero mismatches",
      (rec["runs_reconciled"], rec["mismatches_total"], rec["vacuous_runs"]) == (36, 0, []),
      str((rec["runs_reconciled"], rec["mismatches_total"])))
check(11, "and it is not vacuous: 2760 single legs were actually compared",
      rec["single_leg_compared_total"] == 2760 and rec["single_leg_compared_total"] > 0,
      str(rec["single_leg_compared_total"]) + " legs compared")

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
NEW_A2 = ["src/stockedge100/strategies/g2_rotation_ra1.py",
          "src/stockedge100/strategies/g2_gate_ra1.py",
          "src/stockedge100/strategies/g2_runner_ra1.py",
          "src/stockedge100/backtest/g2_engine_ra1.py",
          "src/stockedge100/backtest/g2_episodes_ra1.py",
          "src/stockedge100/reporting/g2_stage3_attempt2_evidence.py",
          "src/stockedge100/reporting/g2_stage3_attempt2_package.py"]
scanned_rel = set(p.relative_to(ROOT).as_posix() for p in ROOT.glob("src/**/*.py"))
check(12, "the sweep actually reached all seven new Attempt 2 modules -- a sweep that found nothing "
          "because it scanned nothing is not a check",
      all(m in scanned_rel and m in code_hashes for m in NEW_A2),
      str([m for m in NEW_A2 if m not in scanned_rel]))
check(12, "it also reached the adversarial risk-architecture test module",
      not [v for v in violations if "test_g2_ra1" in v]
      and (ROOT / "tests/adversarial/test_g2_ra1_risk_architecture.py").is_file())
check(12, "every trading and credential flag is false in the authorization state",
      all(dec["authorization_state"][k] == "false" for k in dec["authorization_state"]),
      str(dec["authorization_state"]))
check(12, "live_trading_authorized is the boolean False at the top level",
      dec["live_trading_authorized"] is False)

# ---------------------------------------------------------------- 13. manifest and checksum policy
manifest_rel = A2 + "STAGE_3_G2_A2_ARTIFACT_MANIFEST.json"
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
check(13, "the record covers the report, which repo_state_id does NOT -- G2-CONFLICT-4's mitigation",
      REPORT.relative_to(ROOT).as_posix() in covered
      and REPORT.relative_to(ROOT).as_posix() in man["produced_artifacts"]
      and REPORT.relative_to(ROOT).as_posix() not in code_hashes)
check(13, "all 14 declared artifacts exist on disk",
      len(dec["artifacts"]) == 14 and all((ROOT / a).is_file() for a in dec["artifacts"]),
      str([a for a in dec["artifacts"] if not (ROOT / a).is_file()]))
check(13, "the run record's output digests match disk",
      all(sha(ROOT / rel) == dig for rel, dig in run["output_artifact_hashes"].items()),
      str([rel for rel, dig in run["output_artifact_hashes"].items() if sha(ROOT / rel) != dig]))
check(13, "the evidence file's recorded sha256 resolves to the evidence file",
      dec["evidence_file"]["sha256"] == sha(EVID))
check(13, "no produced artifact was written into Attempt 1's reports/stage3_g2/ directory",
      not [a for a in dec["artifacts"] if a.startswith("reports/stage3_g2/")],
      str([a for a in dec["artifacts"] if a.startswith("reports/stage3_g2/")]))

# ---------------------------------------------------------------- 14. Gen 1 and Attempt 1 untouched
S4MAN = ROOT / "reports/stage4/STAGE_4_VALIDATION_ARTIFACT_MANIFEST.json"
s4man = json.loads(S4MAN.read_text(encoding="utf-8"))
gen1 = {}
for group in ("frozen_inputs", "produced_artifacts"):
    gen1.update({k: v["sha256"] for k, v in s4man[group].items()})
gen1.update(s4man["repo_state_files"])
BUILDER = "src/stockedge100/reporting/stage_package.py"
ALLOWED_TO_CHANGE = {"README.md", BUILDER}
gen1_drift = [k for k, v in gen1.items()
              if k not in ALLOWED_TO_CHANGE and (not (ROOT / k).is_file() or sha(ROOT / k) != v)]
check(14, "all %d Generation 1 paths recorded by the Stage 4 package are byte-identical"
      % (len(gen1) - len(ALLOWED_TO_CHANGE)), gen1_drift == [], str(gen1_drift[:4]))
check(14, "the exceptions are exactly those two, and both really did change",
      sorted(k for k in ALLOWED_TO_CHANGE if sha(ROOT / k) != gen1[k]) == sorted(ALLOWED_TO_CHANGE),
      str(sorted(k for k in ALLOWED_TO_CHANGE if sha(ROOT / k) == gen1[k])) + " unchanged")
from stockedge100.reporting.stage_package import StageDecision  # noqa: E402
check(14, "the builder's generation field still defaults to 1, so a Gen 1 rebuild is byte-identical",
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
gen1_governed = sorted(k for k in gen1
                       if k.startswith(("governance/", "config/", "reports/"))
                       and "generation_2" not in k)
gov_drift = [k for k in gen1_governed if sha(ROOT / k) != gen1[k]]
check(14, "no file under governance/, config/ or reports/ from Generation 1 changed (%d checked)"
      % len(gen1_governed), gov_drift == [], str(gov_drift[:4]))
gen1_records = [k for k in gen1_governed if k.endswith(".sha256")]
check(14, "every pre-existing Generation 1 .sha256 record is unchanged (%d)" % len(gen1_records),
      not [k for k in gen1_records if sha(ROOT / k) != gen1[k]], str(gen1_records))
check(14, "the package states Generation 1 is closed and no Generation 1 artifact was modified",
      "CLOSED" in dec["generation"]["generation_1_status"]
      and "No Generation 1 arti" in dec["generation"]["generation_1_status"])
# --- Attempt 1, separately: re-hashed, not asserted.
A1MAN = ROOT / "reports/stage3_g2/STAGE_3_G2_ARTIFACT_MANIFEST.json"
a1man = json.loads(A1MAN.read_text(encoding="utf-8"))
a1 = {}
for group in ("frozen_inputs", "produced_artifacts"):
    a1.update({k: v["sha256"] for k, v in a1man[group].items()})
a1_drift = [k for k, v in a1.items() if not (ROOT / k).is_file() or sha(ROOT / k) != v]
check(14, "all %d artifacts and inputs Attempt 1 recorded are byte-identical -- re-hashed, not "
          "asserted" % len(a1), a1_drift == [], str(a1_drift[:4]))
a1_code = a1man["repo_state_files"]
a1_code_drift = [k for k in a1_code if k not in ALLOWED_TO_CHANGE and sha(ROOT / k) != a1_code[k]]
check(14, "every pattern file Attempt 1 hashed is unchanged apart from README.md (%d checked)"
      % len(a1_code), a1_code_drift == [], str(a1_code_drift[:4]))
AT_H = dec["attempt"]["attempt_1_module_verification"]
mod_drift = [k for k, v in AT_H["modules_verified"].items() if sha(ROOT / k) != v]
check(14, "AT-H: all %d Attempt 1 modules re-hash to their sealed digests" % AT_H["module_count"],
      AT_H["module_count"] == 9 and len(AT_H["modules_verified"]) == 9
      and mod_drift == [] and AT_H["modules_that_moved"] == [], str(mod_drift))
check(14, "the six modules section 0 names by name are among them",
      all(any(n in k for k in AT_H["modules_verified"]) for n in
          ("g2_rotation.py", "g2_engine.py", "g2_gate.py", "g2_runner.py", "g2_costs.py",
           "g2_window_guard.py")),
      str(sorted(k.rsplit("/", 1)[-1] for k in AT_H["modules_verified"])))
check(14, "those digests are the sealer's, taken from the protocol, not recomputed to match",
      all(gproto["contamination_measurement"]["attempt_1_module_digests"][k] == v
          for k, v in AT_H["modules_verified"].items()),
      AT_H["digest_source"])
check(14, "Attempt 1's protocol, report and configs are frozen inputs of this package, not outputs",
      all(p in man["frozen_inputs"] and p not in man["produced_artifacts"] for p in
          ("governance/generation_2/STAGE_3_G2_ROTATION_PROTOCOL.md",
           "governance/generation_2/STAGE_3_G2_ROTATION_PROTOCOL.json",
           "governance/generation_2/STAGE_3_G2_ROTATION_RESEARCH_REPORT.md",
           "config/generation_2/g2_rotation_protocol.json",
           "config/generation_2/g2_gate_criteria.json")))
check(14, "Attempt 1's verdict is recorded as standing permanently",
      "CLOSED_READ_ONLY" in dec["attempt"]["attempt_1_disposition"]
      and "stands p" in dec["attempt"]["attempt_1_disposition"],
      dec["attempt"]["attempt_1_disposition"][:60])
new_gov = sorted(p.relative_to(ROOT).as_posix() for p in ROOT.glob("governance/generation_2/*"))
check(14, "every artifact this generation wrote under governance/ lives in generation_2/",
      all(p.startswith("governance/generation_2/") for p in new_gov),
      str(len(new_gov)) + " files")

# ---------------------------------------------------------------- 15. only intended repo changes
prev = prev_run["code_hashes"]
added = sorted(set(code_hashes) - set(prev))
removed = sorted(set(prev) - set(code_hashes))
changed = sorted(k for k in set(code_hashes) & set(prev) if code_hashes[k] != prev[k])
ADDED_OK = re.compile(r"^(src/stockedge100/(backtest|reporting|strategies)/g2_[a-z0-9_]*"
                      r"(ra1|attempt2)[a-z0-9_]*\.py"
                      r"|tests/(unit|adversarial)/test_g2_[a-z0-9_]*ra1[a-z0-9_]*\.py)$")
unexpected_added = [a for a in added if not ADDED_OK.match(a)]
check(15, "everything added since run %s is an Attempt 2 module or test (%d added)"
      % (prev_run["run_id"], len(added)), unexpected_added == [] and len(added) == 8,
      str(unexpected_added) if unexpected_added else str(len(added)) + " added")
check(15, "the previous run record is Attempt 2's own pre-registration, so the diff is this session's",
      "attempt_2_preregistration" in prev_run["stage"], prev_run["stage"])
check(15, "the only changed pattern file is README.md",
      changed == ["README.md"], "changed " + str(changed))
check(15, "nothing was removed or renamed -- an R or D under a governed path breaks every manifest",
      removed == [], str(removed))
touched_other = [k for k in changed + added
                 if k.startswith(("src/", "tests/")) and "g2_" not in k.rsplit("/", 1)[-1]]
check(15, "no Generation 1 or Attempt 1 source or test file was touched at all",
      touched_other == [], str(touched_other))
a1_modules = list(AT_H["modules_verified"])
check(15, "none of Attempt 1's nine modules is in the changed set",
      not [m for m in a1_modules if m in changed], str([m for m in a1_modules if m in changed]))
runs_on_disk = sorted(p.stem for p in (ROOT / "runs").glob("SE100-R-*.json"))
check(15, "runs/ is append-only and holds this package's record",
      run_id in runs_on_disk, str(len(runs_on_disk)) + " records, latest " + runs_on_disk[-1])
check(15, "this package's record is the newest, so nothing ran after the build",
      runs_on_disk[-1] == run_id, runs_on_disk[-1])
newer = [p.relative_to(ROOT).as_posix() for p in
         [ROOT / k for k in code_hashes]
         if p.stat().st_mtime > (ROOT / "runs" / (run_id + ".json")).stat().st_mtime]
check(15, "no pattern file has been modified since the run record was written",
      newer == [], str(newer[:4]))

# ---------------------------------------------------------------- 16. tests and the regression floor
summary = SUMMARY.read_text(encoding="utf-8")
pytest_txt = PYTEST_TXT.read_text(encoding="utf-8", errors="replace")
tail = [ln for ln in pytest_txt.strip().splitlines() if "passed" in ln or "failed" in ln]
m = re.search(r"(\d+) failed, (\d+) passed", tail[-1]) if tail else None
check(16, "the captured pytest output's own summary line says 1 failed, 1141 passed",
      m is not None and (int(m.group(1)), int(m.group(2)))
      == (dec["tests"]["failed"], dec["tests"]["passed"]),
      tail[-1].strip()[:80] if tail else "no summary line")
check(16, "the decision record's counts are 1141 passed, 1 failed, 0 skipped",
      (dec["tests"]["collected"], dec["tests"]["passed"], dec["tests"]["failed"],
       dec["tests"]["skipped"]) == (1142, 1141, 1, 0), str(dec["tests"]))
check(16, "the test summary on disk carries the same numbers",
      all(str(v) in summary for v in dec["tests"].values()), str(dec["tests"]))
check(16, "the single failure is Generation 1's permanent red marker, not an Attempt 2 test",
      "test_no_stage_4_module_can_reach_restricted_data_or_a_broker" in pytest_txt
      and "S4-CONFLICT-7" in summary,
      "marker named in the capture and the summary")
check(16, "the count exceeds Attempt 1's 1091-test floor -- no test was weakened or removed",
      dec["tests"]["collected"] > 1091,
      str(dec["tests"]["collected"]) + " collected vs 1091 at Attempt 1")
g2_tests = sorted(p.relative_to(ROOT).as_posix() for p in ROOT.glob("tests/**/test_g2_*.py"))
check(16, "the five Generation 2 test modules exist and are inside the pattern set",
      len(g2_tests) == 5 and all(t in code_hashes for t in g2_tests), str(g2_tests))
check(16, "the adversarial risk-architecture suite is one of them, as section 4 requires",
      "tests/adversarial/test_g2_ra1_risk_architecture.py" in g2_tests)
AT_IDS = ["AT-A", "AT-B", "AT-C", "AT-D", "AT-E", "AT-F", "AT-G", "AT-H", "AT-I"]
check(16, "all nine sealed adversarial-test ids are named in the test summary",
      all(a in summary for a in AT_IDS), str([a for a in AT_IDS if a not in summary]))

# ---------------------------------------------------------------- 17. disclosures carried verbatim
DISCLOSURE = lock["validation_reuse_disclosure"]
check(17, "the 820-character validation-reuse disclosure is sealed in the partition lock",
      len(DISCLOSURE) == 820, str(len(DISCLOSURE)))
check(17, "it appears verbatim in the report", DISCLOSURE in md)
check(17, "it appears verbatim in the decision record's limitations",
      any(DISCLOSURE == lim or DISCLOSURE in lim for lim in dec["limitations"]),
      "limitations " + str(len(dec["limitations"])))
MULT = proto["multiple_comparisons_disclosure"]
check(17, "the evidence file carries the sealed multiplicity disclosure field for field",
      evid["multiple_comparisons_disclosure"] == MULT,
      str(sorted(set(MULT) ^ set(evid["multiple_comparisons_disclosure"]))))
mult_prose = [k for k, v in MULT.items() if isinstance(v, str)]
check(17, "its two substantive prose statements appear verbatim in the report",
      sorted(mult_prose) == ["adaptive_design_note", "no_correction_applied", "statement"]
      and MULT["no_correction_applied"] in md and MULT["adaptive_design_note"] in md,
      str([k for k in ("no_correction_applied", "adaptive_design_note") if MULT[k] not in md]))
# The third, "statement", is a pointer rather than prose: it says the binding text is
# adaptation_disclosure_verbatim. So what the report must carry is the referent, not the pointer.
check(17, "the third is a pointer to adaptation_disclosure_verbatim, and the report carries that "
          "referent rather than the pointer",
      "adaptation_disclosure_verbatim" in MULT["statement"]
      and proto["adaptation_disclosure_verbatim"] in md,
      "referent is %d characters, present verbatim" % len(proto["adaptation_disclosure_verbatim"]))
check(17, "its cumulative counts are the two attempts summed -- recomputed here, not restated",
      (MULT["variants_this_attempt"] + MULT["variants_attempt_1"]
       == MULT["cumulative_variants_this_hypothesis_family"] == 36)
      and (MULT["runs_this_attempt"] + MULT["runs_attempt_1"]
           == MULT["cumulative_runs_this_hypothesis_family"] == 72),
      "36 variants / 72 runs across the family")
# The adaptation disclosure -- the one section 1 requires verbatim everywhere Attempt 2's result is
# referenced. Five carriers. Four byte-exact; the protocol Markdown hard-wraps it (G2A2-CONFLICT-29).
ADAPT = proto["adaptation_disclosure_verbatim"]
carriage = dec["adaptation_disclosure_carriage"]
check(17, "the sealed adaptation disclosure is 842 characters, as the package records",
      len(ADAPT) == 842 == carriage["characters"], str(len(ADAPT)))
check(17, "its digest recomputes and agrees with the evidence file's copy",
      hashlib.sha256(ADAPT.encode("utf-8")).hexdigest() == carriage["sha256_of_utf8"]
      == carriage["sha256_recorded_in_evidence"], carriage["sha256_of_utf8"][:16])
req_carriers = json.loads(
    (ROOT / "config/generation_2/g2_rotation_ra1_protocol.json").read_text(encoding="utf-8")
)["adaptation_disclosure_carriage_requirement"]["must_appear_verbatim_in"]
check(17, "the package measured every carrier the seal requires, and no fewer",
      sorted(carriage["carriers"]) == sorted(req_carriers),
      str(sorted(set(carriage["carriers"]) ^ set(req_carriers))))
PROTOCOL_MD = "governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.md"
byte_exact_now = {}
for rel in req_carriers:
    raw = (ROOT / rel).read_text(encoding="utf-8")
    hay = json.dumps(json.loads(raw), ensure_ascii=False) if rel.endswith(".json") else raw
    byte_exact_now[rel] = ADAPT in hay
should_be_exact = [r for r in req_carriers if r != PROTOCOL_MD]
check(17, "all four non-wrapping carriers hold the 842 characters byte-exactly, re-measured now",
      all(byte_exact_now[r] for r in should_be_exact),
      str([r for r in should_be_exact if not byte_exact_now[r]]))
check(17, "including this package's own decision record, which did not exist at build time and is "
          "recorded 'present': false",
      byte_exact_now[A2 + "STAGE_3_G2_A2_ROTATION_RESEARCH.json"]
      and carriage["carriers"][A2 + "STAGE_3_G2_A2_ROTATION_RESEARCH.json"]["present"] is False)
check(17, "the one carrier needing normalisation is the hard-wrapped protocol Markdown, and only it",
      carriage["carriers_requiring_normalisation"] == [PROTOCOL_MD]
      and byte_exact_now[PROTOCOL_MD] is False, str(carriage["carriers_requiring_normalisation"]))
from stockedge100.reporting.g2_partition_lock import normalised_prose  # noqa: E402
check(17, "and under the sealer's own normalised_prose it is equal -- the frozen file was not rewrapped",
      normalised_prose(ADAPT) in normalised_prose((ROOT / PROTOCOL_MD).read_text(encoding="utf-8")))
UNWRAP = re.compile(r"\n>?[ \t]*")
pmd = (ROOT / PROTOCOL_MD).read_text(encoding="utf-8")
start = pmd.index(ADAPT[:40])
exact = [n for n in range(len(ADAPT), len(ADAPT) + 128)
         if UNWRAP.sub(" ", pmd[start:start + n]) == ADAPT]
markers = re.findall(UNWRAP, pmd[start:start + exact[0]]) if exact else []
check(17, "the stored copy is 858 characters: the sealed 842 with eight spaces replaced by '\\n> '",
      exact and exact[0] == 858 and markers == ["\n> "] * 8
      and len(ADAPT) - 8 + 8 * 3 == 858,
      str(exact[:1]) + " markers " + str(len(markers)))
check(17, "G2A2-CONFLICT-29 states both numbers rather than describing the gap in words",
      any("G2A2-CONFLICT-29" in c and "858" in c and "842" in c for c in dec["conflicts_found"]))
check(17, "the same conflict is disclosed in the report, not only in the decision record",
      "G2A2-CONFLICT-29" in md)
# the evidence self-digest, recomputed over its own declared coverage
from stockedge100.reporting.g2_stage3_attempt2_evidence import (  # noqa: E402
    EXCLUDED_FROM_DIGEST, evidence_digest)
recomputed = evidence_digest({k: v for k, v in evid.items() if k not in EXCLUDED_FROM_DIGEST})
check(17, "the evidence self-digest recomputes from the written file over its declared coverage",
      recomputed == evid["evidence_digest"] == dec["evidence_file"]["evidence_digest"],
      recomputed[:16] + " vs recorded " + evid["evidence_digest"][:16])
check(17, "the decision record and the evidence file agree on what that digest covers",
      dec["evidence_file"]["evidence_digest_covers"] == evid["evidence_digest_covers"])
check(17, "nine conflicts, ten limitations, fourteen evidence statements, none of them empty",
      (len(dec["conflicts_found"]), len(dec["limitations"]), len(dec["evidence"])) == (9, 10, 14)
      and all(s.strip() for s in dec["conflicts_found"] + dec["limitations"] + dec["evidence"]),
      "conflicts %d limitations %d evidence %d" % (len(dec["conflicts_found"]),
                                                   len(dec["limitations"]), len(dec["evidence"])))
conflict_ids = sorted(set(re.findall(r"G2A?2?A?2?-CONFLICT-\d+", " ".join(dec["conflicts_found"]))))
check(17, "the five conflicts found after the seal (-25..-29) are all disclosed",
      all(("G2A2-CONFLICT-%d" % i) in " ".join(dec["conflicts_found"]) for i in range(25, 30))
      and all(("G2A2-CONFLICT-%d" % i) in md for i in range(25, 30)),
      str(conflict_ids))

out("\n".join(notes))
out("")
out("\n".join(fails) if fails else "ALL CHECKS PASS")
out("")
out(str(len(notes)) + " ok / " + str(len(fails)) + " failed")
out("repo_state_id " + recorded)
out("package run   " + run_id)
out("verdict       " + dec["verdict"])
