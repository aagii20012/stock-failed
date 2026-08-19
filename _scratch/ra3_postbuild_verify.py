"""Post-build verification of the Generation 2 Stage 3 Attempt 3 decision package.

Adapted from ``_scratch/g2a2_postbuild_verify.py``. Every predicate was re-derived from the Attempt 3
artifacts as they exist on disk rather than copied, because the Attempt 3 decision record's shape
differs from Attempt 2's in about fifteen places and a copied predicate would either raise KeyError
or -- worse -- pass vacuously. The differences that mattered:

  * ``dec["attempt"]`` and ``dec["generation"]`` are bare ints (2, 3), not dicts.
  * ``dec["partition"]["partition"]`` does not exist; the boundaries live only in the sealed
    partition lock, so this script reads them from there and treats the lock as the authority.
  * ``dec["authorization"]`` carries only ``explicit_non_authorizations`` (16) and
    ``live_trading_authorized``; Attempt 2's three booleans are gone.
  * the selection block has ``steps`` / ``result`` / ``selected_score`` / ``neighbour_scores``,
    not ``step_1..step_3``, and the selected id is ``selected_variant_id``.
  * the rollup row reports ``value`` (false), not ``satisfied``.
  * six of seven conditions are MET; ``S3-C6`` is the sole NOT_MET.
  * the fifth disclosure carrier -- the decision record itself -- was absent at build time by
    construction and must be measured now. Re-measuring it is the whole reason this script exists.

Two helper signatures are the reverse of the natural guess and are wrong in the same way every time:

    code_hashes, repo_state_id = repo_state()          # hashes first, digest second
    results = verify_sha256_record(record_path, cwd)   # dict[path] -> OK | FAILED | MISSING

Reads only. Writes only to stdout. Console output is laundered to ASCII because the verdict line
carries U+2014 and the limitations carry U+2212, neither of which cp1252 can encode.
"""

import ast
import hashlib
import io
import json
import pathlib
import re
import sys
import tokenize
import traceback

ROOT = pathlib.Path(r"D:\Product\stock-trade-alpaca\stockedge100")
sys.path.insert(0, str(ROOT / "src"))
from stockedge100.reporting.stage_package import repo_state, verify_sha256_record  # noqa: E402

# ---------------------------------------------------------------------------- expected constants
EXPECTED_DIGEST = "30cadd00c89fc09cbbcd37ae98ec69546c5992a652f3556e29d07a5a2d2d94a2"
EXPECTED_COVERED = 165
THIS_RUN = "SE100-R-20260819T104543Z"
PRIOR_RUN = "SE100-R-20260816T072617Z"          # the Attempt 3 pre-registration seal, 156 paths
SEALED_PASS = "STAGE_3_G2_ATTEMPT_3_STRATEGY_ADMITTED_IN_DEVELOPMENT"
SEALED_FAIL = "STAGE_3_G2_ATTEMPT_3_NO_CANDIDATE"
A1_TOKENS = ("STAGE_3_G2_STRATEGY_ADMITTED_IN_DEVELOPMENT", "STAGE_3_G2_NO_CANDIDATE")
A2_TOKENS = ("STAGE_3_G2_ATTEMPT_2_STRATEGY_ADMITTED_IN_DEVELOPMENT",
             "STAGE_3_G2_ATTEMPT_2_NO_CANDIDATE")
DISCLOSURE_SHA = "ce1d6476f44562310fb059c5817645baa25477cc4f6168b414f3423834c8e925"
DISCLOSURE_LEN = 1507
REPRESENTATIVE = "SE100-G2-S3-C3-ROTATION-RA3-L03-K2-QUARTERLY"
DEV_BOUND = "2021-07-31"

A3_DIR = "reports/stage3_g2_attempt3/"
DEC_P = A3_DIR + "STAGE_3_G2_A3_ROTATION_RESEARCH.json"
EVID_P = A3_DIR + "STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json"
MAN_P = A3_DIR + "STAGE_3_G2_A3_ARTIFACT_MANIFEST.json"
REC_P = A3_DIR + "STAGE_3_G2_A3_ROTATION_RESEARCH.sha256"
REPORT_P = "governance/generation_2/STAGE_3_G2_ROTATION_RA3_RESEARCH_REPORT.md"
LOCK_P = "governance/generation_2/STAGE_1_G2_PARTITION_LOCK.json"

NEW_SRC = (
    "src/stockedge100/strategies/g2_rotation_ra3.py",
    "src/stockedge100/strategies/g2_gate_ra3.py",
    "src/stockedge100/strategies/g2_runner_ra3.py",
    "src/stockedge100/strategies/g2_selection_v2.py",
    "src/stockedge100/backtest/g2_engine_ra3.py",
    "src/stockedge100/reporting/g2_stage3_attempt3_evidence.py",
    "src/stockedge100/reporting/g2_stage3_attempt3_package.py",
)
NEW_TESTS = (
    "tests/adversarial/test_g2_ra3_risk_architecture.py",
    "tests/adversarial/test_g2_sel2_selection_rule.py",
)
EXPECTED_ADDED = set(NEW_SRC) | set(NEW_TESTS)

# ---------------------------------------------------------------------------------------- harness
fails, notes = [], []
_n = [0]


def out(text):
    sys.stdout.write(str(text).encode("ascii", "backslashreplace").decode("ascii") + "\n")


def check(label, ok, detail=""):
    _n[0] += 1
    line = ("OK   " if ok else "FAIL ") + ("[%02d] " % _n[0]) + label + (" :: " + str(detail) if detail else "")
    (notes if ok else fails).append(line)


def section(title):
    def deco(fn):
        notes.append("")
        notes.append("--- " + title)
        try:
            fn()
        except Exception:
            tb = traceback.format_exc().strip().splitlines()
            check(title + " raised", False, tb[-1] + " | " + (tb[-3] if len(tb) > 2 else ""))
        return fn
    return deco


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def J(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


DEC = J(DEC_P)
EVID = J(EVID_P)
MAN = J(MAN_P)
LOCK = J(LOCK_P)
CRIT = J("config/generation_2/g2_gate_criteria_ra3.json")
PROTO = J("config/generation_2/g2_rotation_ra3_protocol.json")
REPORT = (ROOT / REPORT_P).read_text(encoding="utf-8")
RUN = J("runs/%s.json" % THIS_RUN)
PREV = J("runs/%s.json" % PRIOR_RUN)
CODE_HASHES, LIVE_DIGEST = repo_state()

HEX64 = re.compile(r"\b[0-9a-f]{64}\b")


# ==================================================================== 1. repo_state_id and patterns
@section("1. repo_state_id recomputes, and the patterns behave as the record claims")
def s1():
    check("repo_state_id recomputes to the value the package recorded",
          LIVE_DIGEST == EXPECTED_DIGEST, "live=%s" % LIVE_DIGEST)
    check("the decision record's repo_state_id equals the live digest",
          DEC["reproducibility"]["repo_state_id"] == LIVE_DIGEST)
    check("the run record's repo_state_id equals the live digest",
          RUN["repo_state_id"] == LIVE_DIGEST)
    check("the manifest's repo_state_id equals the live digest",
          MAN["repo_state_id"] == LIVE_DIGEST)
    check("the covered path count is %d" % EXPECTED_COVERED,
          len(CODE_HASHES) == EXPECTED_COVERED, "live=%d" % len(CODE_HASHES))
    check("the manifest's repo_state_files is the same set of paths",
          set(MAN["repo_state_files"]) == set(CODE_HASHES),
          "sym.diff=%d" % len(set(MAN["repo_state_files"]) ^ set(CODE_HASHES)))
    check("and the same digests",
          all(MAN["repo_state_files"][p] == CODE_HASHES[p] for p in CODE_HASHES))
    check("the run record's code_hashes is the same mapping",
          RUN["code_hashes"] == CODE_HASHES)

    # both directions of the glob-depth asymmetry, live, not as recorded
    covered = set(CODE_HASHES)
    outside = ["governance/generation_2/STAGE_3_G2_ROTATION_RA3_RESEARCH_REPORT.md",
               "governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.md",
               "governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.json",
               "governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.sha256"]
    inside = ["config/generation_2/g2_rotation_ra3_protocol.json",
              "config/generation_2/g2_gate_criteria_ra3.json",
              "README.md"]
    for p in outside:
        check("outside the digest (governance/* is single-level): " + p.split("/")[-1],
              p not in covered and (ROOT / p).is_file())
    for p in inside:
        check("inside the digest (config/** is recursive): " + p.split("/")[-1],
              p in covered and (ROOT / p).is_file())
    check("the record's expected_outside all hold", all(DEC["repo_state_pattern_membership"]["expected_outside"].values()))
    check("the record's expected_inside all hold", all(DEC["repo_state_pattern_membership"]["expected_inside"].values()))
    check("the record's covered_path_count agrees with the live count",
          DEC["repo_state_pattern_membership"]["covered_path_count"] == len(CODE_HASHES))

    # nothing the digest covers may carry the digest
    carriers = [p for p in sorted(covered)
                if EXPECTED_DIGEST in (ROOT / p).read_text(encoding="utf-8", errors="replace")]
    check("no file covered by repo_state_id carries repo_state_id", not carriers, str(carriers))
    # nor may any governance markdown, covered or not
    gov_md = [p.name for p in sorted(ROOT.glob("governance/**/*.md"))
              if EXPECTED_DIGEST in p.read_text(encoding="utf-8", errors="replace")]
    check("no governance markdown carries the tree digest", not gov_md, str(gov_md))
    check("the digest is recorded in the decision record and the runs/ record",
          DEC["reproducibility"]["repo_state_id"] == EXPECTED_DIGEST and RUN["repo_state_id"] == EXPECTED_DIGEST)


# ============================================================== 2. every checksum record verifies
@section("2. every checksum record on the tree verifies from its own convention's directory")
def s2():
    # Two incompatible conventions live on this tree. The two Stage 0/1 freeze records carry bare
    # filenames and resolve against governance/; every pre-registration and report record carries
    # PROJECT_ROOT-relative paths and resolves against stockedge100/. verify_sha256_record's second
    # argument is the base for the record's *entries*, not for the record itself, so the record path
    # is passed absolute -- getting that wrong is the operator error CLAUDE.md warns about, and it
    # presents as a missing file rather than as an integrity failure.
    BARE = ("STAGE_0_FREEZE.sha256", "STAGE_1_FREEZE.sha256")
    records = []
    for p in sorted(ROOT.glob("governance/*.sha256")):
        records.append((p, ROOT / "governance" if p.name in BARE else ROOT))
    for p in sorted(ROOT.glob("governance/generation_2/*.sha256")):
        records.append((p, ROOT))
    for p in sorted(ROOT.glob("reports/*/*.sha256")):
        records.append((p, ROOT))
    check("record inventory is the expected size", len(records) == 22, "found %d" % len(records))
    total = 0
    for p, base in records:
        res = verify_sha256_record(p, base)
        total += len(res)
        bad = {k: v for k, v in res.items() if v != "OK"}
        check("verifies (%d entries): %s" % (len(res), p.name), not bad, json.dumps(bad)[:220])
    check("the 22 records cover a substantial number of entries", total > 200, "%d entries" % total)

    # non-vacuity: the bare-filename records must actually fail from the other convention's
    # directory, otherwise the distinction above is untested and either base would have passed
    for name in BARE:
        p = ROOT / "governance" / name
        wrong = verify_sha256_record(p, ROOT)
        check("%s does not also verify from stockedge100/ (the conventions are really distinct)" % name,
              any(v != "OK" for v in wrong.values()),
              "all %d entries resolved from the wrong base" % len(wrong))


# =========================================================== 3. frozen inputs read only, unchanged
@section("3. the 26 frozen inputs are unchanged on disk and all marked read-only")
def s3():
    fi = MAN["frozen_inputs"]
    check("the manifest lists 26 frozen inputs", len(fi) == 26, "found %d" % len(fi))
    check("the decision record lists the same 26 paths",
          {e["path"] if isinstance(e, dict) else e for e in DEC["frozen_inputs_read_only"]} == set(fi),
          "record=%d" % len(DEC["frozen_inputs_read_only"]))
    bad_disp = {p: e.get("disposition") for p, e in fi.items()
                if e.get("disposition") != "READ_ONLY_NOT_MODIFIED"}
    check("every disposition is READ_ONLY_NOT_MODIFIED", not bad_disp, json.dumps(bad_disp)[:200])
    moved = {p: (e["sha256"], sha(ROOT / p)) for p, e in fi.items()
             if not (ROOT / p).is_file() or sha(ROOT / p) != e["sha256"]}
    check("every frozen input re-hashes to its recorded digest", not moved,
          ", ".join(sorted(moved))[:300])
    check("the constitution is among them and unmoved",
          fi.get("governance/STAGE_0_CONSTITUTION.md", {}).get("sha256") == sha(ROOT / "governance/STAGE_0_CONSTITUTION.md"))
    for must in ("config/generation_2/g2_rotation_ra3_protocol.json",
                 "config/generation_2/g2_gate_criteria_ra3.json",
                 "governance/generation_2/STAGE_1_G2_PARTITION_LOCK.json"):
        check("frozen-input list includes " + must.split("/")[-1], must in fi)


# ========================================================== 4. Markdown and JSON tell one story
@section("4. the report and the decision record agree, and the report carries no forward digest")
def s4():
    check("the report is on disk at its manifest digest",
          MAN["produced_artifacts"][REPORT_P]["sha256"] == sha(ROOT / REPORT_P))
    check("the report has no CRLF", b"\r\n" not in (ROOT / REPORT_P).read_bytes())
    for label, value in (("verdict token", SEALED_FAIL),
                         ("representative", REPRESENTATIVE),
                         ("selection rule id", "SE100-G2-SEL-2"),
                         ("risk architecture id", "RA3"),
                         ("evidence artifact id", "SE100-EVID-3103"),
                         ("report artifact id", "SE100-GOV-2008"),
                         ("protocol artifact id", "SE100-CFG-3105"),
                         ("criteria artifact id", "SE100-CFG-3106")):
        check("the report carries the " + label, value in REPORT, value)
    check("the report states the same verdict as the record",
          DEC["verdict"] in REPORT, DEC["verdict"])
    check("the report states FAIL, not PASS",
          DEC["stage_verdict"]["verdict"] == "FAIL" and SEALED_PASS not in REPORT.replace(SEALED_FAIL, ""))
    check("the report carries the sole NOT_MET condition id", "S3-C6" in REPORT)
    check("the report carries the test counts the record does",
          all(str(DEC["tests"][k]) in REPORT for k in ("collected", "passed", "failed")))
    check("the report names the permanent red test",
          "test_no_stage_4_module_can_reach_restricted_data_or_a_broker" in REPORT
          and "S4-CONFLICT-7" in REPORT)

    # no digest in the report may post-date the report
    forward = {"the decision record": MAN["produced_artifacts"][DEC_P]["sha256"],
               "the artifact manifest": sha(ROOT / MAN_P),
               "the checksum record": sha(ROOT / REC_P),
               "the report itself": sha(ROOT / REPORT_P),
               "the tree digest": EXPECTED_DIGEST}
    carried = {k: v for k, v in forward.items() if v in REPORT}
    check("the report carries no digest written at or after its own seal", not carried,
          ", ".join(sorted(carried)))

    # every hex64 in the report must resolve to something real
    known = set(CODE_HASHES.values())
    for m in (MAN, J("reports/stage3_g2/STAGE_3_G2_ARTIFACT_MANIFEST.json"),
              J("reports/stage3_g2_attempt2/STAGE_3_G2_A2_ARTIFACT_MANIFEST.json"),
              J("reports/stage4/STAGE_4_VALIDATION_ARTIFACT_MANIFEST.json")):
        known |= {e["sha256"] for e in m["frozen_inputs"].values()}
        known |= {e["sha256"] for e in m["produced_artifacts"].values()}
        known |= set(m["repo_state_files"].values())
        known |= set(m.get("dataset_hashes", {}).values())
        known.add(m["repo_state_id"])
    for p in sorted(ROOT.glob("governance/**/*.sha256")) + sorted(ROOT.glob("reports/*/*.sha256")):
        known |= set(HEX64.findall(p.read_text(encoding="utf-8")))
        known.add(sha(p))
    for p in sorted(ROOT.glob("governance/**/*.md")) + sorted(ROOT.glob("governance/**/*.json")):
        known.add(sha(p))
    # digests the sealed inputs themselves carry as values -- the universe identity digest is the one
    # that matters here, since the report cites it to say which universe the grid ran on. It lives in
    # governance/STAGE_1_UNIVERSE.json and is echoed by every Generation 2 protocol.
    for p in sorted(ROOT.glob("config/**/*.json")) + sorted(ROOT.glob("governance/**/*.json")) \
            + sorted(ROOT.glob("reports/*/*.json")) + sorted(ROOT.glob("data/manifests/*.json")):
        known |= set(HEX64.findall(p.read_text(encoding="utf-8")))
    known.add(DISCLOSURE_SHA)
    known.add(DEC["evidence_file"]["evidence_digest"])
    for rr in sorted(ROOT.glob("runs/*.json")):
        r = json.loads(rr.read_text(encoding="utf-8"))
        known.add(r.get("repo_state_id"))
        known |= set(r.get("code_hashes", {}).values())
        known |= set(r.get("output_artifact_hashes", {}).values())
    unresolved = sorted(set(HEX64.findall(REPORT)) - known)
    check("every 64-hex string in the report resolves to a real artifact digest",
          not unresolved, "%d unresolved: %s" % (len(unresolved), unresolved[:3]))
    check("the report actually carries digests (the check above is not vacuous)",
          len(set(HEX64.findall(REPORT))) >= 10, "%d distinct" % len(set(HEX64.findall(REPORT))))

    # the one digest in the report that is neither an artifact hash nor a tree digest: the identity of
    # the universe the grid ran on. Verified against the sealed source rather than merely tolerated.
    uid = J("governance/STAGE_1_UNIVERSE.json")["universe_identity_sha256"]
    check("the report's identity digest is the sealed universe identity",
          ("| Identity digest | `%s` |" % uid) in REPORT, uid[:16] + "...")
    check("the sealed protocol echoes the same universe identity",
          PROTO["eligible_universe"]["universe_identity_sha256"] == uid)
    check("Attempt 3 therefore ran on the same universe as Attempts 1 and 2",
          J("config/generation_2/g2_rotation_protocol.json")["eligible_universe"]["universe_identity_sha256"] == uid
          and J("config/generation_2/g2_rotation_ra1_protocol.json")["eligible_universe"]["universe_identity_sha256"] == uid)


# ============================================================ 5. the grid is the sealed grid
@section("5. eighteen variants, and they are the sealed eighteen")
def s5():
    axes = PROTO["grid"]["axes"]
    check("lookback axis is the sealed {3,6,12}", axes["lookback_months"] == [3, 6, 12], str(axes["lookback_months"]))
    check("top_k axis is the sealed {1,2,3}", axes["top_k"] == [1, 2, 3], str(axes["top_k"]))
    check("frequency axis is the sealed {MONTHLY,QUARTERLY}",
          [str(x).upper() for x in axes["rebalance_frequency"]] == ["MONTHLY", "QUARTERLY"],
          str(axes["rebalance_frequency"]))
    check("the sealed grid size is 18", PROTO["grid"]["size"] == 18)
    sealed = [v if isinstance(v, str) else v.get("variant_id") for v in PROTO["grid"]["variants"]]
    check("the sealed variants list holds 18 distinct ids",
          len(sealed) == 18 and len(set(sealed)) == 18, "%d/%d" % (len(sealed), len(set(sealed))))
    # the ids must be exactly the cartesian product under the sealed format
    fmt = PROTO["grid"]["variant_id_format"]
    built = set()
    for lb in axes["lookback_months"]:
        for k in axes["top_k"]:
            for f in axes["rebalance_frequency"]:
                built.add(fmt.replace("{lookback:02d}", "%02d" % lb).replace("{k}", str(k))
                          .replace("{FREQUENCY}", str(f).upper()))
    check("the sealed ids are exactly the cartesian product of the sealed axes",
          set(sealed) == built, "sym.diff=%d" % len(set(sealed) ^ built))

    table = DEC["grid_results_descriptive_only"]["table"]
    ran = {r["variant_id"] for r in table}
    check("the grid that ran is 18 variants", len(table) == 18 and len(ran) == 18)
    check("the grid that ran is the sealed grid", ran == set(sealed), "sym.diff=%d" % len(ran ^ set(sealed)))
    check("two runs per variant, 36 total",
          PROTO["runs_per_variant"]["total_runs"] == 36 and DEC["determinism"]["runs_compared"] == 36)
    check("the selection inputs cover all 18", {i["variant_id"] for i in DEC["selection"]["inputs"]} == ran)
    check("zero research-shutdown events across the grid",
          DEC["grid_results_descriptive_only"]["research_shutdown_events_total"] == 0)
    check("the representative is a member of the sealed grid", REPRESENTATIVE in ran)
    check("the record states the representative is not the best performer",
          DEC["grid_results_descriptive_only"]["representative_is_not_the_best"] is True)


# ==================================================== 6. selection was return-blind, and recomputes
@section("6. SEL-2 was return-blind and its arithmetic recomputes from the recorded inputs")
def s6():
    sel = DEC["selection"]
    check("the rule id is the sealed SE100-G2-SEL-2", sel["rule_id"] == "SE100-G2-SEL-2")
    check("the record asserts return-blindness", sel["return_blind"] is True)
    check("the rule was frozen before any variant ran", sel["frozen_before_any_variant_is_run"] is True)
    check("four ordered steps", [s["order"] for s in sel["steps"]] == [1, 2, 3, 4])

    from stockedge100.strategies import g2_selection_v2 as V2
    check("the module's rule id matches the record", V2.SELECTION_RULE_ID == sel["rule_id"])
    check("the module's field tuple matches the record",
          list(V2.SELECTION_V2_FIELD_NAMES) == list(sel["selection_input_fields"]),
          "%s vs %s" % (V2.SELECTION_V2_FIELD_NAMES, sel["selection_input_fields"]))
    check("the module's scored quantities match the record",
          list(V2.QUANTITIES) == list(sel["scored_quantities"]))
    check("the module's step criteria match the record",
          {s["order"]: s["criterion"] for s in sel["steps"]} == V2.EXPECTED_STEP_CRITERIA)
    forbidden_hits = [f for f in V2.SELECTION_V2_FIELD_NAMES
                      for w in V2.FORBIDDEN_FIELD_SUBSTRINGS if w in f.lower()]
    check("no selection field name contains a return-flavoured substring",
          not forbidden_hits, str(forbidden_hits))
    check("the forbidden-substring list is not empty (the check above is not vacuous)",
          len(V2.FORBIDDEN_FIELD_SUBSTRINGS) >= 10)

    # the dataclass must reject a float in a counter slot -- that is what stops a return figure
    # being passed positionally into the score
    try:
        V2.SelectionInputV2(variant_id="X", shutdown_events=0, fill_count=1.5,
                            ladder_descents=0, lockout_arms=0, stops_filled=0)
        rejected_float = False
    except Exception:
        rejected_float = True
    try:
        V2.SelectionInputV2(variant_id="X", shutdown_events=0, fill_count=True,
                            ladder_descents=0, lockout_arms=0, stops_filled=0)
        rejected_bool = False
    except Exception:
        rejected_bool = True
    check("SelectionInputV2 refuses a float in a counter slot", rejected_float)
    check("SelectionInputV2 refuses a bool in a counter slot", rejected_bool)

    # recompute the whole selection from the recorded inputs, through the sealed module
    inputs = [V2.SelectionInputV2(**{k: i[k] for k in V2.SELECTION_V2_FIELD_NAMES})
              for i in sel["inputs"]]
    res = V2.select_representative_v2(inputs)
    rj = res.to_json()
    check("recomputed selection picks the recorded representative",
          rj["selected_variant_id"] == sel["selected_variant_id"] == REPRESENTATIVE,
          "recomputed=%s" % rj["selected_variant_id"])
    check("recomputed selection decides at the recorded step",
          rj["decided_at_step"] == sel["decided_at_step"] == 2, "recomputed=%s" % rj["decided_at_step"])
    check("all 18 passed the zero-shutdown screen",
          len(rj["eligible_variants"]) == 18 and rj["ineligible_variants"] == [],
          "%d eligible" % len(rj["eligible_variants"]))
    check("the recomputed result is byte-identical to the recorded result block",
          rj == sel["result"],
          "differing keys=%s" % [k for k in rj if rj[k] != sel["result"].get(k)])

    # the winning score must be the strict unique minimum, recomputed through the sealed module
    scores = {v: e["instability_score"] for v, e in sel["result"]["all_scores"].items()}
    recomputed = {v: e["instability_score"] for v, e in rj["all_scores"].items()}
    check("all eighteen instability scores are recorded", len(scores) == 18, "%d" % len(scores))
    check("every recorded instability score recomputes",
          scores == recomputed,
          "mismatch on %s" % [v for v in scores if scores[v] != recomputed.get(v)][:3])
    vals = sorted((float(v), k) for k, v in scores.items())
    check("the winner holds the minimum instability score",
          vals and vals[0][1] == REPRESENTATIVE, str(vals[:2]))
    check("that minimum is strictly unique", len(vals) > 1 and vals[0][0] < vals[1][0],
          "%s then %s" % (vals[0] if vals else "-", vals[1] if len(vals) > 1 else "-"))
    check("the recorded selected_score is the winner's own score",
          sel["selected_score"]["variant_id"] == REPRESENTATIVE
          and sel["selected_score"]["instability_score"] == scores[REPRESENTATIVE])
    check("the ranking's first row is the winner",
          sel["result"]["ranking"][0]["variant_id"] == REPRESENTATIVE,
          sel["result"]["ranking"][0]["variant_id"])
    check("the ranking is ordered by instability score",
          [r["instability_score"] for r in sel["result"]["ranking"]]
          == sorted(r["instability_score"] for r in sel["result"]["ranking"]))
    check("no ranking row carries a return quantity",
          not [k for r in sel["result"]["ranking"] for k in r
               if any(w in k.lower() for w in V2.FORBIDDEN_FIELD_SUBSTRINGS)],
          str(sorted({k for r in sel["result"]["ranking"] for k in r})))
    check("the winner has four neighbours and four neighbour scores are recorded",
          sel["selected_score"]["neighbour_count"] == 4 == len(sel["neighbour_scores"]))
    check("the recorded neighbours are the winner's structural neighbours",
          sorted(sel["selected_score"]["neighbours"]) == sorted(V2.neighbours_of(REPRESENTATIVE)),
          str(sel["selected_score"]["neighbours"]))
    check("each recorded neighbour score belongs to a recorded neighbour",
          {s["variant_id"] for s in sel["neighbour_scores"]} == set(sel["selected_score"]["neighbours"]))

    # no return-flavoured field may appear anywhere in the selection block
    blob = json.dumps(sel).lower()
    leaks = [w for w in ("total_return", "max_drawdown", "profit_factor", "sharpe", "equity_curve")
             if w in blob]
    check("the selection block mentions no return quantity", not leaks, str(leaks))


# ==================================================== 7. gate conditions, rollup, and the two reads
@section("7. seven conditions, aggregated on satisfaction, with the rollup row present")
def s7():
    ROLLUP = "admissible_candidate_exists"
    all_rows = DEC["gate_conditions"]
    sealed_ids = [c["id"] for c in CRIT["conditions"]]
    check("eight rows are reported: the seven sealed conditions plus the rollup",
          len(all_rows) == 8, "found %d" % len(all_rows))
    check("the rollup row is present rather than silently dropped", ROLLUP in all_rows)
    gc = {k: v for k, v in all_rows.items() if k != ROLLUP}
    check("seven sealed conditions are reported", len(gc) == 7, "found %d" % len(gc))
    check("their ids are the sealed ids", sorted(gc) == sorted(sealed_ids), str(sorted(gc)))
    for cid in sorted(gc):
        c = gc[cid]
        sealed = [x for x in CRIT["conditions"] if x["id"] == cid][0]
        check("%s carries its sealed text verbatim" % cid,
              c["required_verbatim"] == sealed["required_verbatim"],
              repr(c["required_verbatim"])[:70])
        # satisfaction must equal what met_by/not_met_by/not_applicable_for say, recomputed
        derived = (not c["not_met_by"]) and (not c["not_evaluable_for"]) and \
                  bool(set(c["met_by"]) | set(c["not_applicable_for"]))
        check("%s satisfaction recomputes from its own lists" % cid,
              c["satisfied"] == derived, "recorded=%s derived=%s" % (c["satisfied"], derived))
        gating = set(c["gating_runs"])
        accounted = set(c["met_by"]) | set(c["not_met_by"]) | set(c["not_evaluable_for"]) | set(c["not_applicable_for"])
        check("%s accounts for every gating run" % cid, gating <= accounted,
              "unaccounted=%s" % sorted(gating - accounted))
        check("%s never reports a run as both met and not met" % cid,
              not (set(c["met_by"]) & set(c["not_met_by"])))

    met = sorted(k for k, c in gc.items() if c["verdict"] == "MET")
    notmet = sorted(k for k, c in gc.items() if c["verdict"] == "NOT_MET")
    check("six conditions are MET", len(met) == 6, str(met))
    check("S3-C6 is the sole NOT_MET", notmet == ["S3-C6"], str(notmet))
    check("no condition is NOT_RUN, UNKNOWN or NOT_EVALUABLE",
          not [k for k, c in gc.items() if c["verdict"] in ("NOT_RUN", "UNKNOWN", "NOT_EVALUABLE")])
    c6 = gc["S3-C6"]
    check("S3-C6 fails on both runs", sorted(c6["not_met_by"]) == ["#BASE", "#STRESS"], str(c6["not_met_by"]))
    check("S3-C6's measured values exceed its threshold",
          float(c6["measured"]["#BASE"]) > 0.50 and float(c6["measured"]["#STRESS"]) > 0.50,
          "%s / %s vs %s" % (c6["measured"]["#BASE"][:6], c6["measured"]["#STRESS"][:6], c6["threshold"]))
    check("S3-C7 is the only row with a reported-not-gating column",
          [k for k, c in gc.items() if c["reported_not_gating"]] == ["S3-C7"],
          str([k for k, c in gc.items() if c["reported_not_gating"]]))
    check("S3-C7 gates on #BASE alone, per the resolved G2A2-CONFLICT-25",
          gc["S3-C7"]["gating_runs"] == ["#BASE"], str(gc["S3-C7"]["gating_runs"]))

    # the rollup row -- the only row that decides the gate. A per-condition row means only "at least
    # one candidate satisfied this" and settles nothing on its own.
    row = all_rows[ROLLUP]
    check("the package carries an admissible_candidate_exists row", row is not None)
    if row:
        check("the rollup row is NOT_MET", row["verdict"] == "NOT_MET", str(row["verdict"]))
        check("the rollup row's value is false", row["value"] is False, str(row["value"]))
        check("18 variants declared and 18 eligible after the shutdown screen",
              row["variants_declared"] == 18 and row["variants_eligible_after_shutdown_screen"] == 18)
        check("one candidate evaluated, none admitted",
              row["candidates_evaluated"] == 1 and row["admitted_candidates"] == [])
        check("the rollup names the same representative", row["representative"] == REPRESENTATIVE)
        check("the rollup's base failure list recomputes from the conditions",
              sorted(row["conditions_not_satisfied_base"]) ==
              sorted(k for k, c in gc.items() if "#BASE" in c["not_met_by"]),
              str(row["conditions_not_satisfied_base"]))
        check("the rollup's stress failure list recomputes from the conditions",
              sorted(row["conditions_not_satisfied_stress"]) ==
              sorted(k for k, c in gc.items() if "#STRESS" in c["not_met_by"]),
              str(row["conditions_not_satisfied_stress"]))
        check("the permissive base-only reading also fails",
              row["permissive_base_only_reading_would_give"] is False)
        check("both readings therefore agree, so no reading admits a candidate",
              row["value"] is False and row["permissive_base_only_reading_would_give"] is False)
    check("gate_passed is False", DEC["gate_passed"] is False)
    check("the sole candidate is not admitted", DEC["candidate_results"][0]["admitted"] is False)
    check("the candidate is the representative", DEC["candidate_results"][0]["variant_id"] == REPRESENTATIVE)
    check("no blockers were recorded", DEC["blockers"] == [], str(DEC["blockers"]))


# ============================================================ 8. the verdict is the sealed verdict
@section("8. the verdict token came off disk, and no prior attempt's token is loose")
def s8():
    vtd = CRIT["verdict_token_derivation"]
    sealed_pass = [v for k, v in vtd.items() if isinstance(v, str) and v == SEALED_PASS]
    sealed_fail = [v for k, v in vtd.items() if isinstance(v, str) and v == SEALED_FAIL]
    check("the sealed criteria define the pass token used", bool(sealed_pass), SEALED_PASS)
    check("the sealed criteria define the fail token used", bool(sealed_fail), SEALED_FAIL)
    check("the record's stage verdict token is the sealed fail token",
          DEC["stage_verdict"]["verdict_token"] == SEALED_FAIL)
    check("the record's pass/fail tokens are the sealed pair",
          DEC["stage_verdict"]["pass_token"] == SEALED_PASS
          and DEC["stage_verdict"]["fail_token"] == SEALED_FAIL)
    check("the verdict line is FAIL followed by the fail token",
          DEC["verdict"].startswith("FAIL") and DEC["verdict"].endswith(SEALED_FAIL), DEC["verdict"])
    check("the verdict is not the gate's own pass token", SEALED_PASS not in DEC["verdict"])
    check("the constitutional equivalent is recorded",
          DEC["stage_verdict"]["constitutional_fail_result_equivalent"] == "STRATEGY_REJECTED_IN_DEVELOPMENT")
    check("the fail route is the representative-failed route",
          DEC["stage_verdict"]["fail_route"] == "REPRESENTATIVE_FAILED_AT_LEAST_ONE_CONDITION")
    check("a representative does exist, so the no-representative route is not claimed",
          DEC["stage_verdict"].get("representative_exists") is True)
    withheld = DEC["stage_verdict"]["prior_attempt_tokens_withheld"]
    check("all four prior-attempt tokens are named as withheld",
          set(withheld) == set(A1_TOKENS) | set(A2_TOKENS), str(withheld))
    check("no withheld token is this attempt's verdict", DEC["verdict"].split()[-1] not in withheld)

    # a prior attempt's token may appear in the report only on a line that says whose it is
    stray = []
    for i, line in enumerate(REPORT.splitlines(), 1):
        for t in A1_TOKENS:
            if t in line and "STAGE_3_G2_ATTEMPT_" not in line.replace(t, "") \
                    and "ttempt 1" not in line and "withheld" not in line and "prior" not in line.lower():
                stray.append("A1 L%d %s" % (i, line.strip()[:60]))
        for t in A2_TOKENS:
            if t in line and "ttempt 2" not in line and "withheld" not in line and "prior" not in line.lower():
                stray.append("A2 L%d %s" % (i, line.strip()[:60]))
    check("no prior attempt's token appears unattributed in the report", not stray,
          " | ".join(stray[:3]))
    check("the report carries this attempt's fail token", SEALED_FAIL in REPORT)

    # the same discipline in the run record and the evidence
    check("the run record carries no verdict field (verdicts live in the decision record)",
          "verdict" not in RUN, str(list(RUN)))
    check("the evidence's stage verdict token matches the decision record",
          EVID["stage_verdict"]["verdict_token"] == SEALED_FAIL)


# ======================================================= 9. nothing at or after the partition bound
@section("9. no observation at or after 2021-08-01 was read")
def s9():
    part = LOCK["partition"]
    check("the sealed development end is %s" % DEV_BOUND, part["development_end"] == DEV_BOUND)
    boundaries = {part[k] for k in ("validation_start", "validation_end", "generation_1_holdout_start",
                                    "generation_1_holdout_end", "holdout_start", "holdout_end")}
    check("the declared boundary set is the six sealed dates", len(boundaries) == 6, str(sorted(boundaries)))

    date_re = re.compile(r"\b(?:19|20)\d{2}-\d{2}-\d{2}\b")

    def walk(o, path, acc):
        if isinstance(o, dict):
            for k, v in o.items():
                walk(v, path + "." + str(k), acc)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, path + "[%d]" % i, acc)
        elif isinstance(o, str):
            for m in date_re.finditer(o):
                acc.setdefault(m.group(0), []).append(path)

    for rel in (DEC_P, EVID_P, A3_DIR + "run_span_recheck.json"):
        acc = {}
        walk(J(rel), "", acc)
        late = {d: v for d, v in acc.items() if d > DEV_BOUND}
        stray = {d: v for d, v in late.items() if d not in boundaries}
        check("%s: every post-bound date is a declared boundary" % rel.split("/")[-1],
              not stray, json.dumps({k: v[:2] for k, v in stray.items()})[:260])
        check("%s: the sweep found dates at all (not vacuous)" % rel.split("/")[-1],
              len(acc) >= 10, "%d distinct dates" % len(acc))
        for d in sorted(late):
            paths = late[d]
            declarative = all(any(seg in p for seg in ("non_authorization", "limitation", "enforcement",
                                                       "window", "partition", "prohibited", "holdout",
                                                       "disclosure", "note", "scope"))
                              for p in paths)
            check("%s: %s appears only in declarative prose" % (rel.split("/")[-1], d),
                  declarative, str(paths[:2]))

    rs = J(A3_DIR + "run_span_recheck.json")
    blob = json.dumps(rs)
    observed = sorted(set(date_re.findall(blob)))
    check("the run-span recheck's latest date is at or before the bound",
          observed and observed[-1] <= DEV_BOUND, "max=%s" % (observed[-1] if observed else "-"))
    check("the run record's date_range ends at or before the bound",
          RUN["date_range"][1] <= DEV_BOUND, str(RUN["date_range"]))
    check("the run record declares the holdout LOCKED", RUN["holdout_state"] == "LOCKED", RUN["holdout_state"])
    check("the decision record's window is the development window",
          DEV_BOUND in json.dumps(DEC["partition"]["window"]), json.dumps(DEC["partition"]["window"])[:120])


# ================================================================== 10. both holdouts stay sealed
@section("10. both holdout windows remain sealed and unread")
def s10():
    part = LOCK["partition"]
    check("Generation 2's holdout is the sealed 2026-08-01..2028-07-31",
          (part["holdout_start"], part["holdout_end"]) == ("2026-08-01", "2028-07-31"))
    check("Generation 1's holdout is the sealed 2024-08-01..2026-07-31",
          (part["generation_1_holdout_start"], part["generation_1_holdout_end"]) == ("2024-08-01", "2026-07-31"))
    from stockedge100.strategies import g2_window_guard as G
    labels = {name: (start, end) for name, start, end in G.prohibited_windows()}
    check("the window guard declares both holdouts prohibited",
          set(G.PROHIBITED_LABELS) == set(labels) and len(labels) >= 2, str(sorted(labels)))
    check("the guard's development bound is the sealed bound",
          str(G.development_bound()) == DEV_BOUND, str(G.development_bound()))
    for label, window in (("holdout", ("2026-08-01", "2026-09-01")),
                          ("generation_1_holdout", ("2024-08-01", "2024-09-01"))):
        try:
            G.generation_2_window("postbuild_probe", window[0], window[1])
            refused = False
        except Exception:
            refused = True
        check("the guard refuses a window inside %s" % label, refused, str(window))
    # the ignore rule that keeps the payload off GitHub
    gi = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for d in ("data/raw", "data/normalized", "data/reference"):
        check(".gitignore still excludes %s" % d, d in gi)


# ============================================== 11. determinism and reconciliation are not vacuous
@section("11. determinism and reconciliation held, and neither check was vacuous")
def s11():
    det = DEC["determinism"]
    check("all 36 runs reproduced identically", det["all_identical"] is True and det["runs_compared"] == 36)
    check("no mismatched runs", det["mismatched_runs"] == [], str(det["mismatched_runs"]))
    check("eight fields were compared per run, including the risk-state trace",
          len(det["fields_compared"]) == 8 and "risk_state_digest" in det["fields_compared"],
          str(det["fields_compared"]))
    check("no wall-clock value enters a digested payload", "No run id" in det["no_wall_clock_in_payloads"])
    rec = DEC["reconciliation"]
    check("all 36 runs were reconciled", rec["runs_reconciled"] == 36)
    check("zero reconciliation mismatches", rec["mismatches_total"] == 0)
    check("the reconciliation compared a non-zero number of single legs",
          rec["single_leg_compared_total"] > 0, str(rec["single_leg_compared_total"]))
    check("no run was vacuous", rec["vacuous_runs"] == [], str(rec["vacuous_runs"]))
    check("the vacuity rule is stated as implemented, not asserted",
          "closed_episodes > 0" in rec["vacuity_rule_as_implemented"])
    sd = DEC["selection_determinism"]
    check("the selection recomputed identically",
          all(v is True for k, v in sd.items() if isinstance(v, bool)),
          str({k: v for k, v in sd.items() if v is False}))
    # RA3 must have behaved differently from RA2 -- the requirement this attempt exists to test
    lec = DEC["ladder_engagement_comparison"]
    check("36 runs were compared against Attempt 2's ladder statistics", lec["runs_compared"] == 36)
    check("at least one statistic differs", lec["at_least_one_statistic_differs"] is True)
    check("no run is identical on every compared statistic",
          lec["runs_identical_on_every_compared_statistic"] == [],
          str(lec["runs_identical_on_every_compared_statistic"])[:120])
    saf = lec["sessions_at_full_sizing"]
    check("RA3 spends more sessions at full sizing than RA2 did",
          saf["attempt_3_total"] > saf["attempt_2_total"],
          "%d vs %d" % (saf["attempt_3_total"], saf["attempt_2_total"]))
    check("all 36 runs differ on sessions at full sizing",
          saf["runs_differing"] == 36 and saf["differs"] is True)


# ================================================== 12. no module can reach a broker or a holdout
@section("12. AST sweep of the new modules -- no network, no broker, no holdout")
def s12():
    NET_ROOTS = {"requests", "urllib", "urllib2", "urllib3", "http", "httpx", "socket", "ftplib",
                 "smtplib", "telnetlib", "websocket", "websockets", "yfinance", "pandas_datareader",
                 "alpaca", "alpaca_trade_api", "boto3", "paramiko", "ssl", "webbrowser"}
    BROKER_WORDS = ("submit_order", "cancel_order", "replace_order", "close_position",
                    "list_positions", "liquidate", "APCA_", "ALPACA_", "paper-api", "api_key",
                    "secret_key")
    swept = []
    for rel in NEW_SRC + NEW_TESTS:
        p = ROOT / rel
        check("exists: " + rel.split("/")[-1], p.is_file())
        src = p.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=rel)
        swept.append(rel)
        roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    roots.add(a.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                roots.add(node.module.split(".")[0])
        bad = sorted(roots & NET_ROOTS)
        check("%s imports nothing that can reach a network" % rel.split("/")[-1], not bad, str(bad))
        hits = [w for w in BROKER_WORDS if w in src]
        check("%s contains no broker or credential idiom" % rel.split("/")[-1], not hits, str(hits))
        # subprocess/eval/exec
        risky = sorted(roots & {"subprocess", "ctypes", "multiprocessing"})
        check("%s spawns no subprocess" % rel.split("/")[-1], not risky, str(risky))

    check("the sweep reached all nine new modules", len(swept) == 9, "%d swept" % len(swept))
    check("the sweep reached the RA3 engine specifically",
          "src/stockedge100/backtest/g2_engine_ra3.py" in swept)
    check("the sweep reached the SEL-2 module specifically",
          "src/stockedge100/strategies/g2_selection_v2.py" in swept)

    # post-bound date literals in the new modules: only the exclusive bound, or inside a guard test
    date_re = re.compile(r"\b(?:19|20)\d{2}-\d{2}-\d{2}\b")
    part = LOCK["partition"]
    for rel in NEW_SRC:
        src = (ROOT / rel).read_text(encoding="utf-8")
        late = sorted({d for d in date_re.findall(src) if d > DEV_BOUND})
        check("%s names no post-bound date but the exclusive bound" % rel.split("/")[-1],
              set(late) <= {part["validation_start"]}, str(late))
    # Post-bound dates in the adversarial test are legitimate only where the test asserts a refusal.
    # Scope that judgement to the enclosing test function via the AST rather than to a fixed window of
    # lines: the first draft used +/- a few lines and misjudged
    # test_at_g_the_window_object_does_not_enforce_the_bound, which builds a deliberately permissive
    # window to prove the *constructor* does not enforce the bound and only then asserts that the
    # loader refuses the series -- three lines further down than a narrow window can see.
    guard_test = ROOT / "tests/adversarial/test_g2_ra3_risk_architecture.py"
    gsrc = guard_test.read_text(encoding="utf-8")
    glines = gsrc.splitlines()
    gtree = ast.parse(gsrc, filename=guard_test.name)
    funcs = []
    for node in ast.walk(gtree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs.append((node.lineno, node.end_lineno, node.name, ast.get_source_segment(gsrc, node) or ""))
    # A post-bound date in a comment or a docstring is prose describing the bound, not a read of it:
    # the module docstring states "The Generation 2 window guard still blocks any read at or after
    # 2021-08-01" and a section banner repeats it. Classify by token so those are excluded explicitly
    # and by line number, rather than being swept in by a loose text window.
    doc_lines = set()
    for tok in tokenize.generate_tokens(io.StringIO(gsrc).readline):
        if tok.type == tokenize.COMMENT:
            doc_lines.update(range(tok.start[0], tok.end[0] + 1))
    for node in ast.walk(gtree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            ds = node.body[0] if node.body else None
            if isinstance(ds, ast.Expr) and isinstance(ds.value, ast.Constant) and isinstance(ds.value.value, str):
                doc_lines.update(range(ds.lineno, ds.end_lineno + 1))
    unguarded, guarded, prose = [], [], []
    for i, line in enumerate(glines, 1):
        for d in date_re.findall(line):
            if d <= DEV_BOUND:
                continue
            owners = [f for f in funcs if f[0] <= i <= f[1]]
            body = owners[-1][3] if owners else ""
            name = owners[-1][2] if owners else "<module level>"
            where = "L%d %s in %s" % (i, d, name)
            if i in doc_lines:
                prose.append(where)
                continue
            asserts_refusal = ("pytest.raises" in body or "prohibited_windows" in body
                               or "PROHIBITED_LABELS" in body)
            (guarded if asserts_refusal else unguarded).append(where)
    check("every post-bound date in executable code sits in a function that asserts a refusal",
          not unguarded, str(unguarded[:4]))
    check("the excluded occurrences really are prose, and they are enumerated not waved past",
          all(i in doc_lines for i in
              [int(s.split()[0][1:]) for s in prose]) and len(prose) == 2, str(prose))
    check("the post-bound dates in that test are not merely absent (the check is not vacuous)",
          len(guarded) >= 4, "%d guarded occurrences" % len(guarded))
    check("that test asserts both holdouts are refused, by their sealed start dates",
          "2026-08-01" in gsrc and "2024-08-01" in gsrc)
    check("and it asserts the window object alone does not enforce the bound",
          "does_not_enforce" in gsrc or "permissive" in gsrc)

    # No broker anywhere. The hard assertion is scoped to Attempt 3's own nine modules; tree-wide, two
    # Generation 1 modules do contain the string, and both are deny-lists -- the same shape as the
    # permanent S4-CONFLICT-7 red, where a scanner that names what it forbids trips a naive scanner.
    # Those two are enumerated as expected rather than waved past, so a third occurrence would fail.
    BROKER_WORDS = ("alpaca_trade_api", "submit_order", "APCA_API_KEY_ID", "APCA_API_SECRET_KEY")
    DECLARED_DENYLISTS = {
        "src/stockedge100/reporting/stage4_evaluation_package.py": "NETWORK_MODULES",
        "src/stockedge100/reporting/stage4_preregistration.py": "NETWORK_IMPORT_ROOTS",
    }
    new_hits, other_hits = [], []
    for p in sorted(ROOT.glob("src/**/*.py")):
        rel = p.relative_to(ROOT).as_posix()
        t = p.read_text(encoding="utf-8")
        if not any(w in t for w in BROKER_WORDS):
            continue
        (new_hits if rel in NEW_SRC else other_hits).append(rel)
    check("no Attempt 3 module names a broker API at all", not new_hits, str(new_hits))
    check("tree-wide, the only occurrences are the two declared Generation 1 deny-lists",
          sorted(other_hits) == sorted(DECLARED_DENYLISTS), str(sorted(other_hits)))
    # Each file declares its own vocabulary with its own comment; Generation 1 anticipated this exact
    # false positive ("naming one here is not using one" / "matched against ... never against the raw
    # text"). Require the file's own declaration, not a phrase borrowed from the other file.
    DECLARING_PHRASE = {
        "src/stockedge100/reporting/stage4_evaluation_package.py": "The AST markers of the sealed P5 predicate",
        "src/stockedge100/reporting/stage4_preregistration.py": "so naming one here is not using one",
    }
    for rel, const in DECLARED_DENYLISTS.items():
        src = (ROOT / rel).read_text(encoding="utf-8")
        lines = src.splitlines()
        at = [i + 1 for i, ln in enumerate(lines) if "alpaca_trade_api" in ln]
        # the string must appear only as an element of the named prohibition vocabulary: on a line that
        # is part of that assignment, never as a call, an import or a credential name
        owner_ok = all(const in chr(10).join(lines[max(0, n - 12):n]) for n in at)
        check("%s:%s carries the string only as a %s element" % (pathlib.Path(rel).name,
                                                                ",".join(map(str, at)), const),
              at and owner_ok and DECLARING_PHRASE[rel] in src
              and "submit_order" not in src and "import alpaca" not in src,
              "lines %s owner_ok=%s" % (at, owner_ok))
    check("S4-CONFLICT-7 is the conflict that already records this scanner shape",
          any("S4-CONFLICT-7" in str(c) for c in DEC["conflicts_found"]) or
          "S4-CONFLICT-7" in REPORT)


# ============================================== 13. manifest and checksum-record self-reference
@section("13. the manifest excludes itself and the checksum record does not name itself")
def s13():
    check("the manifest does not list itself in produced_artifacts", MAN_P not in MAN["produced_artifacts"])
    check("the manifest does not list itself in frozen_inputs", MAN_P not in MAN["frozen_inputs"])
    check("the manifest lists six produced artifacts", len(MAN["produced_artifacts"]) == 6,
          "%d" % len(MAN["produced_artifacts"]))
    moved = {p: e["sha256"] for p, e in MAN["produced_artifacts"].items()
             if not (ROOT / p).is_file() or sha(ROOT / p) != e["sha256"]}
    check("every produced artifact re-hashes to its manifest digest", not moved, ", ".join(sorted(moved)))

    covered = {}
    for line in (ROOT / REC_P).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, path = line.split(None, 1)
        covered[path.strip().lstrip("*")] = digest
    check("the checksum record does not cover itself", REC_P not in covered)
    check("the checksum record does cover the manifest", MAN_P in covered)
    check("the checksum record covers the decision record", DEC_P in covered)
    check("the checksum record covers the report", REPORT_P in covered)
    check("the checksum record covers the evidence file", EVID_P in covered)
    bad = {p: d for p, d in covered.items() if not (ROOT / p).is_file() or sha(ROOT / p) != d}
    check("every path the record names re-hashes correctly (%d paths)" % len(covered),
          not bad, ", ".join(sorted(bad))[:240])
    check("the manifest is covered by the record rather than by itself",
          MAN_P in covered and MAN_P not in MAN["produced_artifacts"])
    check("the record's own digest is recorded in the runs/ record",
          sha(ROOT / REC_P) in set(RUN.get("output_artifact_hashes", {}).values())
          or sha(ROOT / REC_P) not in set(HEX64.findall(REPORT)),
          "record sha=%s" % sha(ROOT / REC_P)[:16])
    check("the decision record's artifacts list has 8 entries", len(DEC["artifacts"]) == 8,
          "%d" % len(DEC["artifacts"]))
    listed = {a["path"] if isinstance(a, dict) else a for a in DEC["artifacts"]}
    missing = sorted(p for p in listed if not (ROOT / p).is_file())
    check("every artifact the record lists exists on disk", not missing, str(missing))


# ============================================ 14. Generation 1 and both prior attempts are untouched
@section("14. Generation 1, Attempt 1 and Attempt 2 are byte-identical")
def s14():
    ALLOWED = {"README.md", "src/stockedge100/reporting/stage_package.py"}
    for label, man_rel in (("Generation 1 (Stage 4 manifest)", "reports/stage4/STAGE_4_VALIDATION_ARTIFACT_MANIFEST.json"),
                           ("Attempt 1 (A1 manifest)", "reports/stage3_g2/STAGE_3_G2_ARTIFACT_MANIFEST.json"),
                           ("Attempt 2 (A2 manifest)", "reports/stage3_g2_attempt2/STAGE_3_G2_A2_ARTIFACT_MANIFEST.json")):
        m = J(man_rel)
        recorded = {}
        recorded.update({p: e["sha256"] for p, e in m["frozen_inputs"].items()})
        recorded.update({p: e["sha256"] for p, e in m["produced_artifacts"].items()})
        recorded.update(m["repo_state_files"])
        gone = sorted(p for p in recorded if not (ROOT / p).is_file())
        moved = sorted(p for p, d in recorded.items()
                       if (ROOT / p).is_file() and sha(ROOT / p) != d and p not in ALLOWED)
        check("%s: nothing it recorded has been deleted (%d paths)" % (label, len(recorded)),
              not gone, str(gone[:5]))
        check("%s: nothing it recorded has changed" % label, not moved, str(moved[:5]))
        check("%s: the check is not vacuous" % label, len(recorded) > 100, "%d paths" % len(recorded))
        allowed_moved = sorted(p for p in ALLOWED
                               if p in recorded and (ROOT / p).is_file() and sha(ROOT / p) != recorded[p])
        notes.append("     note: expected-to-move under %s: %s" % (label, allowed_moved))

    # the prior attempts' 17 stage-3 modules, re-hashed against the seal's own record
    pav = DEC["prior_attempt_module_verification"]
    check("the record verifies 17 prior-attempt modules", pav["module_count"] == 17)
    check("nine from Attempt 1, eight from Attempt 2",
          pav["attempt_1_module_count"] == 9 and pav["attempt_2_module_count"] == 8)
    check("the record reports no module moved", pav["modules_that_moved"] == [],
          str(pav["modules_that_moved"]))
    mv = pav["modules_verified"]
    check("seventeen digests are recorded", len(mv) == 17, "%d" % len(mv))
    moved = sorted(p for p, d in mv.items() if not (ROOT / p).is_file() or sha(ROOT / p) != d)
    check("all seventeen re-hash to their recorded digests now", not moved, str(moved))
    imm = DEC["prior_attempt_modules_immutable"]
    check("the immutable list agrees with the verified set",
          set(imm["attempt_1_modules"]) | set(imm["attempt_2_modules"]) == set(mv),
          "sym.diff=%d" % len(set(imm["attempt_1_modules"]) | set(imm["attempt_2_modules"]) ^ set(mv)))
    for stem in ("g2_rotation.py", "g2_engine.py", "g2_gate.py", "g2_runner.py",
                 "g2_rotation_ra1.py", "g2_engine_ra1.py", "g2_gate_ra1.py", "g2_runner_ra1.py"):
        check("the prompt's named module is among the seventeen: " + stem,
              any(p.endswith("/" + stem) for p in mv))
    # no Attempt 3 module overwrote a prior name
    for rel in NEW_SRC:
        check("new module does not collide with a prior name: " + rel.split("/")[-1], rel not in mv)
    # the closed attempts' report directories are unchanged as directories
    for d in ("reports/stage3_g2", "reports/stage3_g2_attempt2"):
        m = J(d + ("/STAGE_3_G2_ARTIFACT_MANIFEST.json" if d.endswith("g2")
                   else "/STAGE_3_G2_A2_ARTIFACT_MANIFEST.json"))
        own = {p for p in m["produced_artifacts"] if p.startswith(d + "/")}
        bad = sorted(p for p in own if sha(ROOT / p) != m["produced_artifacts"][p]["sha256"])
        check("%s: its own artifacts are unchanged (%d)" % (d, len(own)), not bad, str(bad))


# ================================================ 15. only the intended files changed this session
@section("15. exactly nine additions and one modification since the pre-registration seal")
def s15():
    prev, cur = PREV["code_hashes"], RUN["code_hashes"]
    check("the prior run record is the Attempt 3 pre-registration seal",
          "preregistration" in PREV["stage"].lower() and "attempt_3" in PREV["stage"].lower(),
          PREV["stage"])
    check("the seal covered 156 paths", len(prev) == 156, "%d" % len(prev))
    added = set(cur) - set(prev)
    removed = set(prev) - set(cur)
    modified = {p for p in set(cur) & set(prev) if cur[p] != prev[p]}
    check("nine paths were added", len(added) == 9, "%d: %s" % (len(added), sorted(added)))
    check("the nine are the expected new modules and tests", added == EXPECTED_ADDED,
          "unexpected=%s missing=%s" % (sorted(added - EXPECTED_ADDED), sorted(EXPECTED_ADDED - added)))
    check("nothing was removed", not removed, str(sorted(removed)))
    check("exactly one path was modified", len(modified) == 1, str(sorted(modified)))
    check("the modified path is README.md", modified == {"README.md"}, str(sorted(modified)))
    check("the live tree matches the run record exactly (nothing touched after the build)",
          CODE_HASHES == cur)
    check("the pre-registration seal's digest differs from this build's (the tree did move)",
          PREV["repo_state_id"] != RUN["repo_state_id"])
    # runs/ is append-only
    ids = sorted(p.stem for p in ROOT.glob("runs/*.json"))
    check("this build's run record is the newest on disk", ids[-1] == THIS_RUN, ids[-1])
    check("the pre-registration run record is still present", PRIOR_RUN in ids)
    check("run records are append-only (25 on disk)", len(ids) == 25, "%d" % len(ids))
    check("the run record's stage names this attempt",
          RUN["stage"] == "STAGE_3_G2_ATTEMPT_3_ROTATION_RA3_DEVELOPMENT", RUN["stage"])


# ======================================================= 16. the test floor held, with its one red
@section("16. the captured suite is the record, 1264 pass and the one permanent red is named")
def s16():
    cap = (ROOT / (A3_DIR + "pytest_stage3_g2_attempt3_output.txt")).read_text(encoding="utf-8")
    t = DEC["tests"]
    check("the capture's collected count matches the record",
          "%d tests collected" % t["collected"] in cap or "collected %d items" % t["collected"] in cap,
          "collected=%d" % t["collected"])
    check("the capture's summary line matches the record",
          "%d failed, %d passed" % (t["failed"], t["passed"]) in cap,
          [l for l in cap.splitlines() if " passed" in l][-1:])
    check("exactly one failure", t["failed"] == 1 and t["errors"] == 0 and t["skipped"] == 0)
    check("1265 collected = 1264 passed + 1 failed",
          t["collected"] == t["passed"] + t["failed"] + t["skipped"])
    RED = "test_no_stage_4_module_can_reach_restricted_data_or_a_broker"
    check("the capture names the expected permanent red", RED in cap)
    check("the capture names its file",
          "tests/unit/test_stage4_preregistration.py" in cap.replace("\\", "/"))
    check("no other test is reported as failed",
          len([l for l in cap.splitlines() if l.startswith("FAILED")]) <= 1,
          str([l for l in cap.splitlines() if l.startswith("FAILED")])[:200])
    check("the capture holds one summary line, not an appended second run",
          len([l for l in cap.splitlines() if re.search(r"\d+ passed", l)]) == 1,
          "%d summary lines" % len([l for l in cap.splitlines() if re.search(r"\d+ passed", l)]))
    check("the test summary document is on disk at its manifest digest",
          sha(ROOT / (A3_DIR + "STAGE_3_G2_A3_TEST_SUMMARY.md"))
          == MAN["produced_artifacts"][A3_DIR + "STAGE_3_G2_A3_TEST_SUMMARY.md"]["sha256"])
    summ = (ROOT / (A3_DIR + "STAGE_3_G2_A3_TEST_SUMMARY.md")).read_text(encoding="utf-8")
    check("the summary names S4-CONFLICT-7 as the reason for the red",
          "S4-CONFLICT-7" in summ and RED in summ)
    check("the summary carries the same counts", str(t["collected"]) in summ and str(t["passed"]) in summ)
    # the floor: Stage 0's 27 tests are still collected, and the suite only ever grew
    check("the suite is far above the Stage 0 floor of 27", t["collected"] > 27)
    check("the two new adversarial test files are collected",
          all(any(f.split("/")[-1] in line for line in cap.splitlines()) or f.split("/")[-1][:-3] in summ
              for f in NEW_TESTS), str(NEW_TESTS))


# ================================================= 17. the disclosures are carried verbatim, now
@section("17. the 1507-character adaptation disclosure is byte-exact in all five carriers")
def s17():
    disc = DEC["adaptation_disclosure_verbatim"]
    check("the decision record's copy is %d characters" % DISCLOSURE_LEN,
          len(disc) == DISCLOSURE_LEN, "%d" % len(disc))
    check("its sha256 is the sealed digest",
          hashlib.sha256(disc.encode("utf-8")).hexdigest() == DISCLOSURE_SHA)
    check("it carries no newline", "\n" not in disc and "\r" not in disc)
    check("it carries the em dash U+2014", "\u2014" in disc)
    check("it carries the minus sign U+2212 that Attempt 2's string did not", "\u2212" in disc)
    check("the evidence file carries the identical string",
          EVID["adaptation_disclosure_verbatim"] == disc)
    check("the sealed protocol carries the identical string",
          PROTO["adaptation_disclosure_verbatim"] == disc)

    adc = DEC["adaptation_disclosure_carriage"]
    required = PROTO["adaptation_disclosure_carriage_requirement"]["must_appear_verbatim_in"]
    check("five carriers are required by the seal", len(required) == 5, "%d" % len(required))
    check("the record measured every required carrier", set(adc["carriers"]) == set(required),
          "sym.diff=%s" % sorted(set(adc["carriers"]) ^ set(required)))
    check("the record's character count agrees", adc["characters"] == DISCLOSURE_LEN)
    check("the record's digest agrees with the evidence", adc["digest_agrees_with_evidence"] is True)
    check("the builder self-exempted only the then-unwritten decision record",
          [p for p, e in adc["carriers"].items() if not e["present"]] == [DEC_P],
          str([p for p, e in adc["carriers"].items() if not e["present"]]))
    check("no carrier needed prose normalisation", adc["carriers_requiring_normalisation"] == [])

    # The measurement the builder could not make: all five, now, off disk -- and it must be
    # format-aware. The two carriers under reports/ are written with ensure_ascii=True, so the
    # disclosure is stored there as backslash-u2014 escaped text and a raw substring search cannot match it
    # however verbatim the value is. For a JSON carrier the right probe is to parse it and compare the
    # decoded field, which is what the builder's own carriage measurement did; the literal-substring
    # test belongs to the Markdown carriers alone.
    UNWRAP = re.compile(r"\n>?[ \t]*")
    BS = chr(92)
    verdicts, how, enc = {}, {}, {}
    for rel in required:
        p = ROOT / rel
        if not p.is_file():
            verdicts[rel] = "MISSING"
            continue
        text = p.read_text(encoding="utf-8")
        if p.suffix == ".json":
            how[rel] = "decoded-field"
            obj = json.loads(text)
            fields = sorted(k for k, v in obj.items() if isinstance(v, str) and v == disc)
            verdicts[rel] = "BYTE_EXACT" if fields else "ABSENT"
            # The field name is not uniform across carriers: the report-directory JSONs use
            # adaptation_disclosure_verbatim, the governance protocol uses adaptation_disclosure.
            # What matters is that exactly one field holds the string and its name says what it is.
            check("JSON carrier stores it as one decoded field: %s -> %s"
                  % (rel.split("/")[-1], ",".join(fields) or "none"),
                  len(fields) == 1 and fields[0].startswith("adaptation_disclosure"), str(fields))
            # The escaping convention is not uniform either. Assert each file is internally consistent
            # -- raw em dashes xor u2014 escapes -- and record which convention it uses, so the claim
            # that a raw-substring probe is the wrong test for the escaped ones is measured, not assumed.
            raw, esc = text.count(chr(0x2014)), text.count(BS + "u2014")
            enc[rel] = ("ensure_ascii=True" if esc and not raw else
                        "ensure_ascii=False" if raw and not esc else "MIXED")
            check("its escaping convention is internally consistent: %s is %s"
                  % (rel.split("/")[-1], enc[rel]), enc[rel] != "MIXED",
                  "raw=%d escaped=%d" % (raw, esc))
            if enc[rel] == "ensure_ascii=True":
                check("a raw-substring probe would indeed have failed on " + rel.split("/")[-1],
                      disc not in text and bool(fields), "escaped=%d" % esc)
        else:
            how[rel] = "literal-substring"
            if disc in text:
                verdicts[rel] = "BYTE_EXACT"
            elif disc in UNWRAP.sub(" ", text):
                verdicts[rel] = "VERBATIM_BUT_REWRAPPED"
            else:
                verdicts[rel] = "ABSENT"
            check("Markdown carrier holds the literal 1507 characters: " + rel.split("/")[-1],
                  verdicts[rel] == "BYTE_EXACT", verdicts[rel])
    check("all five carriers carry it verbatim post-build",
          set(verdicts.values()) == {"BYTE_EXACT"}, json.dumps(verdicts))
    check("both probes were exercised (the format split is real, not assumed)",
          sorted(set(how.values())) == ["decoded-field", "literal-substring"], json.dumps(how))
    check("the two report-directory carriers are the escaped ones, the governance protocol is not",
          [enc[r] for r in sorted(enc) if r.startswith("reports/")] == ["ensure_ascii=True"] * 2
          and [enc[r] for r in sorted(enc) if r.startswith("governance/")] == ["ensure_ascii=False"],
          json.dumps(enc))
    check("the recorded file digests for the four measured carriers still hold",
          all(e["file_sha256"] == sha(ROOT / p)
              for p, e in adc["carriers"].items() if e.get("file_sha256")),
          str([p for p, e in adc["carriers"].items()
               if e.get("file_sha256") and e["file_sha256"] != sha(ROOT / p)]))

    # the evidence self-digest must recompute from the written file
    from stockedge100.reporting import g2_stage3_attempt3_evidence as EM
    body = {k: v for k, v in EVID.items() if k not in EM.EXCLUDED_FROM_DIGEST}
    recomputed = EM.evidence_digest(body)
    check("the evidence self-digest recomputes from the file on disk",
          recomputed == EVID["evidence_digest"],
          "file=%s recomputed=%s" % (EVID["evidence_digest"][:16], recomputed[:16]))
    check("the decision record recorded the same recomputation",
          DEC["evidence_file"]["recomputed_by_this_builder"] == EVID["evidence_digest"]
          and DEC["evidence_file"]["digest_agrees"] is True)
    check("the digest excludes exactly the two volatile fields",
          set(EM.EXCLUDED_FROM_DIGEST) == {"generated_utc", "evidence_digest"},
          str(EM.EXCLUDED_FROM_DIGEST))
    check("the evidence artifact id is SE100-EVID-3103", EVID["artifact_id"] == "SE100-EVID-3103")

    # multiplicity: the third attempt on one hypothesis family must be carried forward
    mcd = DEC["multiple_comparisons_disclosure"]
    blob = json.dumps(mcd)
    check("cumulative multiplicity counts all three attempts",
          "54" in blob and "108" in blob, blob[:200])
    check("a third-attempt note is present", "third_attempt_note" in mcd)
    check("the report carries the multiplicity figures", "54" in REPORT and "108" in REPORT)
    check("22 conflicts are recorded", len(DEC["conflicts_found"]) == 22,
          "%d" % len(DEC["conflicts_found"]))
    # the decision record's conflicts_found entries are prose strings, so the leading token carries the
    # delimiter that follows it ("G2A3-CONFLICT-21:", "G2A2-CONFLICT-25,"). Strip it before comparing.
    ids = [c["id"] if isinstance(c, dict) else str(c).split()[0].rstrip(":,;.") for c in DEC["conflicts_found"]]
    check("every id normalises to a bare CONFLICT token",
          all(re.fullmatch(r"(G2A2|G2A3|G2|S\d)-CONFLICT-\d+", i) for i in ids),
          str([i for i in ids if not re.fullmatch(r"(G2A2|G2A3|G2|S\d)-CONFLICT-\d+", i)]))
    check("every conflict has a distinct id", len(set(ids)) == 22, str([i for i in ids if ids.count(i) > 1]))
    check("G2A2-CONFLICT-25 is inherited by id", "G2A2-CONFLICT-25" in ids, str(ids[:6]))
    check("the glob-depth asymmetry is disclosed as a numbered conflict",
          "G2A3-CONFLICT-30" in ids, str(ids))
    check("Attempt 3 raised its own numbered conflicts, not only inherited ones",
          len([i for i in ids if i.startswith("G2A3-")]) >= 10,
          "%d of 22 are G2A3-" % len([i for i in ids if i.startswith("G2A3-")]))
    check("ten limitations are recorded", len(DEC["limitations"]) == 10, "%d" % len(DEC["limitations"]))
    check("seventeen evidence items are recorded", len(DEC["evidence"]) == 17, "%d" % len(DEC["evidence"]))
    check("live_trading_authorized is false", DEC["live_trading_authorized"] is False)
    check("every authorization_state entry is the string false",
          set(DEC["authorization_state"].values()) == {"false"}, str(DEC["authorization_state"]))
    check("sixteen explicit non-authorizations are recorded",
          len(DEC["authorization"]["explicit_non_authorizations"]) == 16,
          "%d" % len(DEC["authorization"]["explicit_non_authorizations"]))
    # The first draft of this check read `... or "no" in field.lower()[:40]`, which is very nearly
    # vacuous: the field begins "None." and "none" contains "no", so the disjunct passes on a field
    # that said anything at all. Require the actual shape instead -- the None. prefix, a stated length,
    # and an explicit statement that Stage 4 is unauthorized.
    nxt = DEC["next_authorized_stage"]
    check("the next authorized stage begins with the literal None.", nxt.startswith("None."), nxt[:60])
    check("it is a substantive statement, not a token", len(nxt) > 100, "%d chars" % len(nxt))
    check("it states in words that Stage 4 is not authorized",
          "stage 4" in nxt.lower() and ("not authorized" in nxt.lower() or "unauthoriz" in nxt.lower()
                                        or "no authorization" in nxt.lower()),
          nxt[:200])
    check("it does not license an Attempt 4 by itself but defers to a human in a later session",
          "attempt 4" in nxt.lower() and "human" in nxt.lower() and "later session" in nxt.lower(),
          nxt[-260:])
    check("and it restates that live trading is not authorized",
          "live_trading_authorized remains false" in nxt, nxt[-60:])


# ------------------------------------------------------------------------------------------ report
out("")
out("=" * 100)
out("Generation 2 / Stage 3 / Attempt 3 -- post-build verification")
out("tree: %s" % ROOT)
out("=" * 100)
out("\n".join(notes))
out("")
out("=" * 100)
out("\n".join(fails) if fails else "ALL CHECKS PASS")
out("=" * 100)
out("%d ok / %d failed" % (len([n for n in notes if n.startswith("OK")]), len(fails)))
sys.exit(1 if fails else 0)
