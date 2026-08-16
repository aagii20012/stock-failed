"""Render the Attempt 2 research report from a template, substituting every sealed and derived value.

Nothing in the report is transcribed by hand. Four classes of value are substituted:

* the sealed disclosures, which must be carried byte-identically (the 842-character adaptation
  disclosure is one of five declared carriers and the package builder asserts byte-equality);
* the sealed identities and digests, re-read from the config, evidence and seal run record -- and
  each file digest is additionally *recomputed from the file on disk* and asserted equal to the
  sealed value, so a drifted artifact fails the render instead of reaching the report;
* the result tables, extracted from ``_scratch/_tables.txt`` which was itself generated from the
  evidence file, plus every figure the prose quotes, computed here from the same evidence;
* the authoring timestamp, read from the system clock at render time, and the test counts, parsed
  from the pytest capture rather than typed.

ASCII output only. The adaptation disclosure is never printed, only measured.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from pathlib import Path

SCRATCH = Path(__file__).resolve().parent
ROOT = SCRATCH.parent / "stockedge100"
TEMPLATE = SCRATCH / "g2a2_report_template.md"
TABLES = SCRATCH / "_tables.txt"
COUNTS = SCRATCH / "g2a2_test_counts.json"
PYTEST_CAPTURE = ROOT / "reports/stage3_g2_attempt2/pytest_stage3_g2_attempt2_output.txt"
EVIDENCE = ROOT / "reports/stage3_g2_attempt2/STAGE_3_G2_A2_DEVELOPMENT_ADMISSIBILITY.json"
OUT = ROOT / "governance" / "generation_2" / "STAGE_3_G2_ROTATION_RA1_RESEARCH_REPORT.md"

PREFIX_1 = "SE100-G2-S3-C1-ROTATION-"
PREFIX_2 = "SE100-G2-S3-C2-ROTATION-RA1-"


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def sha256_file(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


protocol = load("config/generation_2/g2_rotation_ra1_protocol.json")
lock = load("governance/generation_2/STAGE_1_G2_PARTITION_LOCK.json")
ev = load("reports/stage3_g2_attempt2/STAGE_3_G2_A2_DEVELOPMENT_ADMISSIBILITY.json")
a1 = load("reports/stage3_g2/STAGE_3_G2_DEVELOPMENT_ADMISSIBILITY.json")
counts_meta = json.loads(COUNTS.read_text(encoding="utf-8"))

sealed = ev["sealed_inputs"]
window = ev["window"]
span = window["run_span"]
universe = ev["universe"]
vt = ev["variant_table"]
cand = ev["candidate_results"][0]
base_conds = {c["id"]: c for c in cand["conditions"]}
stress_conds = {c["id"]: c for c in cand["stress_evaluation"]["conditions"]}


# --------------------------------------------------------------------------- structural assertions

def check(condition, message):
    if not condition:
        raise SystemExit("RENDER REFUSED: %s" % message)


check(len(vt) == 18, "variant_table is not 18 rows (%d)" % len(vt))
check(ev["grid"]["runs_executed"] == 36, "runs_executed is not 36")
check(sum(r["research_shutdown_events"] for r in vt) == 0,
      "some Attempt 2 run recorded a research shutdown; the report's headline claim is false")
a1_shutdown_runs = sum(
    1 for r in a1["variant_table"] for k in ("base_shutdown_session", "stress_shutdown_session")
    if r[k])
check(a1_shutdown_runs == 36, "Attempt 1 shutdown-run count is %d, not 36" % a1_shutdown_runs)
check(len(ev["candidate_results"]) == 1, "expected exactly one candidate")

# Every sealed digest must still describe the file on disk.
for name, rel in (("protocol", sealed["protocol"]), ("criteria", sealed["criteria"]),
                  ("governance_protocol_md", sealed["governance_protocol_md"]),
                  ("governance_protocol_json", sealed["governance_protocol_json"]),
                  ("cost_model", sealed["cost_model"]),
                  ("partition_lock", sealed["partition_lock"]),
                  ("charter", sealed["charter"])):
    recomputed = sha256_file(rel)
    check(recomputed == sealed[name + "_sha256"],
          "%s moved on disk: sealed %s, recomputed %s" % (rel, sealed[name + "_sha256"], recomputed))

# The seal run record, located by its stage rather than by a typed filename.
seal = None
for path in sorted((ROOT / "runs").glob("SE100-R-*.json")):
    record = json.loads(path.read_text(encoding="utf-8"))
    if "attempt_2_preregistration" in str(record.get("stage", "")):
        seal = record
check(seal is not None, "no seal run record found in runs/")

# The representative must be the unique minimum of the return-blind tiebreak.
rep_id = ev["selection"]["representative_variant_id"]
rep = next((r for r in vt if r["variant_id"] == rep_id), None)
check(rep is not None, "representative %s is not in the variant table" % rep_id)
lowest = min(r["fill_count_both_runs"] for r in vt)
tied = [r for r in vt if r["fill_count_both_runs"] == lowest]
check(len(tied) == 1 and tied[0]["variant_id"] == rep_id,
      "representative is not the unique lowest-turnover variant")


# --------------------------------------------------------------------------- formatting helpers

def pct(value):
    return "%+.2f%%" % (float(value) * 100.0)


def dec4(value):
    return "%.4f" % float(value)


def dec2(value):
    return "%.2f" % float(value)


def measured_min(condition_row):
    """S3-C5 reports ``min(a, b)``; return the smaller of the two removals as a percentage."""
    numbers = [float(n) for n in re.findall(r"-?\d+\.\d+", str(condition_row["measured"]))]
    check(len(numbers) == 2, "S3-C5 measured string did not yield two numbers")
    return pct(min(numbers))


# --------------------------------------------------------------------------- table extraction

def section(heading):
    """Return the block of ``_tables.txt`` under ``heading``, up to the next heading."""
    lines = TABLES.read_text(encoding="utf-8").splitlines()
    try:
        start = lines.index(heading)
    except ValueError:
        raise SystemExit("heading not found in _tables.txt: %r" % heading)
    out = []
    for line in lines[start + 1:]:
        if line.startswith("### ") or line.startswith("=== "):
            break
        out.append(line)
    return "\n".join(out).strip("\n")


def gate_table():
    """The gate table only, dropping the two provenance lines the emitter prints above it."""
    block = section("### Gate 3 conditions on the representative").splitlines()
    start = next(i for i, line in enumerate(block) if line.startswith("| Condition |"))
    return "\n".join(block[start:]).strip("\n")


def attempt_comparison():
    """Attempt 1's shutdown session and drawdown against Attempt 2's, variant by variant."""
    a1_rows = {r["variant_id"][len(PREFIX_1):]: r for r in a1["variant_table"]}
    rows = [
        "| # | Variant | A1 shutdown `#BASE` | A1 shutdown `#STRESS` | A1 max DD `#BASE` "
        "| A2 max DD `#BASE` | A2 shutdowns |",
        "| --- | --- | --- | --- | ---: | ---: | ---: |",
    ]
    for row in vt:
        short = row["variant_id"][len(PREFIX_2):]
        old = a1_rows[short]
        rows.append("| %d | `%s` | %s | %s | %.4f | %.4f | %d |" % (
            row["grid_index"], short, old["base_shutdown_session"],
            old["stress_shutdown_session"], float(old["base_max_drawdown"]),
            float(row["base_max_drawdown"]), row["research_shutdown_events"]))
    return "\n".join(rows)


def month_histogram():
    """Attempt 1's shutdown months, counted over runs, as the report's section 12 second table."""
    counts = {}
    for row in a1["variant_table"]:
        for key in ("base_shutdown_session", "stress_shutdown_session"):
            value = row[key]
            if value:
                counts[value[:7]] = counts.get(value[:7], 0) + 1
    rows = ["| Month | Attempt 1 runs shut down | Attempt 2 runs shut down |",
            "| --- | ---: | ---: |"]
    for month in sorted(counts):
        rows.append("| %s | %d | 0 |" % (month, counts[month]))
    rows.append("| **Total** | **%d** | **0** |" % sum(counts.values()))
    return "\n".join(rows)


def stop_outliers():
    """Runs whose stop triggers exceed their fills threefold, and the most extreme of them."""
    found = []
    for row in vt:
        for label in ("base", "stress"):
            triggered = row["%s_stops_triggered" % label]
            filled = row["%s_stops_filled" % label]
            if filled and triggered >= 3 * filled:
                found.append((triggered - filled, row["variant_id"][len(PREFIX_2):],
                              label.upper(), triggered, filled))
    check(bool(found), "no stop outliers found; the section 16 sentence would be false")
    worst = max(found)
    clause = "`%s#%s` at %d triggers against %d fills" % (worst[1], worst[2], worst[3], worst[4])
    return len(found), clause


# --------------------------------------------------------------------------- derived figures

base_dd = [float(r["base_max_drawdown"]) for r in vt]
stress_dd = [float(r["stress_max_drawdown"]) for r in vt]
a1_base_dd = [float(r["base_max_drawdown"]) for r in a1["variant_table"]]
gross_base = [float(r["base_max_gross_fraction_observed"]) for r in vt]
gross = gross_base + [float(r["stress_max_gross_fraction_observed"]) for r in vt]
# Section 16's range is grid-wide while the table above it is base-only; the sentence says the
# base-only minimum is higher, so require that rather than leaving it as an unchecked aside.
check(min(gross_base) > min(gross), "the base-only gross minimum is not above the grid-wide one")
check(min(gross) > 0.50, "gross exposure did not exceed the ceiling; conflict -27's premise is false")
scalar_sessions = [r["base_combined_scalar_sessions_below_one"] for r in vt]
scalar_means = [float(r["base_combined_scalar_mean"]) for r in vt]
blocked = [r["base_lockout_recoveries_blocked"] for r in vt]
best = max(vt, key=lambda r: float(r["base_total_return"]))
band3 = sum(1 for r in vt if int(float(r["base_ladder_deepest_band"])) == 3)
band2 = sum(1 for r in vt if int(float(r["base_ladder_deepest_band"])) == 2)
check(band3 + band2 == 18, "ladder deepest-band counts do not cover all 18 variants")
outlier_count, outlier_worst = stop_outliers()

# Every variant's drawdown must actually have improved -- section 12 says so in as many words.
a1_by_short = {r["variant_id"][len(PREFIX_1):]: r for r in a1["variant_table"]}
for row in vt:
    short = row["variant_id"][len(PREFIX_2):]
    check(float(row["base_max_drawdown"]) < float(a1_by_short[short]["base_max_drawdown"]),
          "variant %s did not improve its base drawdown; section 12's claim is false" % short)

# Test counts, parsed from the capture rather than typed.
capture = PYTEST_CAPTURE.read_text(encoding="utf-8", errors="replace")
summary = re.search(r"^(\d+) failed, (\d+) passed in ", capture, re.M)
check(summary is not None, "could not parse the pytest summary line from the capture")
tests_failed, tests_passed = int(summary.group(1)), int(summary.group(2))
tests_skipped = 0 if " skipped" not in summary.group(0) else -1
check(tests_skipped == 0, "the capture reports skipped tests; the report claims none")
tests_total = tests_failed + tests_passed
tests_new = counts_meta["new_tests_collected"]
tests_prior = tests_total - tests_new
check(tests_prior == counts_meta["attempt_1_floor_expected"],
      "derived prior floor %d does not equal Attempt 1's recorded floor %d"
      % (tests_prior, counts_meta["attempt_1_floor_expected"]))
check(tests_failed == 1, "expected exactly the one inherited S4-CONFLICT-7 failure")

# The sealed disclosure, verified against the evidence file's recorded digest before use.
disclosure = protocol["adaptation_disclosure_verbatim"]
digest = hashlib.sha256(disclosure.encode("utf-8")).hexdigest()
check(digest == ev["adaptation_disclosure_carriage"]["sha256_of_utf8"],
      "disclosure digest disagrees with the evidence file")

now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

substitutions = {
    # sealed prose, carried verbatim
    "@@ADAPTATION_DISCLOSURE@@": disclosure,
    "@@WHAT_THIS_ADDS@@": protocol["what_this_attempt_adds_over_attempt_1"],
    "@@DECL_PREDICATE@@": protocol["declared_before_any_strategy_code_measurement"]["predicate"],
    "@@VALIDATION_REUSE@@": lock["validation_reuse_disclosure"],
    "@@MC_NOCORR@@": protocol["multiple_comparisons_disclosure"]["no_correction_applied"],
    "@@MC_ADAPTIVE@@": protocol["multiple_comparisons_disclosure"]["adaptive_design_note"],
    # identity
    "@@GENERATION_ID@@": protocol["generation_id"],
    "@@STRATEGY_ID@@": protocol["strategy_id"],
    "@@REPRESENTATIVE@@": rep_id,
    "@@AUTHORED_UTC@@": now,
    # window
    "@@WINDOW_START@@": window["start"],
    "@@BOUND@@": window["development_bound"],
    "@@RUN_START@@": span["run_start"],
    "@@RUN_END@@": span["run_end"],
    "@@SESSIONS@@": str(span["sessions"]),
    "@@LATEST_LOADED@@": window["latest_session_loaded"],
    "@@BINDING@@": span["binding_symbol"],
    "@@BINDING_INCEPTION@@": span["binding_symbol_inception"],
    "@@A1_SPAN_SHA@@": span["carried_from_sha256"],
    # universe
    "@@UNIVERSE_VERSION@@": universe["universe_version"],
    "@@UNIVERSE_ID@@": universe["universe_identity_sha256"],
    "@@UNIV_DECLARED@@": str(universe["symbols_declared"]),
    "@@UNIV_LOADED@@": str(universe["symbols_loaded"]),
    # seal
    "@@SEAL_RUN_ID@@": seal["run_id"],
    "@@SEAL_UTC@@": seal["timestamp_utc"],
    "@@SEAL_REPO_STATE@@": seal["repo_state_id"],
    "@@PROTO_MD_SHA@@": sealed["governance_protocol_md_sha256"],
    "@@PROTO_JSON_SHA@@": sealed["governance_protocol_json_sha256"],
    "@@PROTOCOL_CFG_SHA@@": sealed["protocol_sha256"],
    "@@CRITERIA_CFG_SHA@@": sealed["criteria_sha256"],
    "@@COST_MODEL_SHA@@": sealed["cost_model_sha256"],
    "@@LOCK_SHA@@": sealed["partition_lock_sha256"],
    "@@CHARTER_SHA@@": sealed["charter_sha256"],
    # evidence provenance
    "@@EVIDENCE_BYTES@@": "{:,}".format(EVIDENCE.stat().st_size),
    "@@EVIDENCE_UTC@@": ev["generated_utc"],
    "@@EVIDENCE_SHA@@": hashlib.sha256(EVIDENCE.read_bytes()).hexdigest(),
    "@@EVIDENCE_SELF@@": ev["evidence_digest"],
    # representative figures
    "@@REP_FILLS@@": str(rep["fill_count_both_runs"]),
    "@@REP_TRADES@@": str(base_conds["S3-C4"]["measured"]),
    "@@REP_PF@@": dec4(base_conds["S3-C3"]["measured"]),
    "@@REP_PF_RECORDER@@": dec4(rep["base_profit_factor"]),
    "@@REP_BASE_RET@@": pct(base_conds["S3-C1"]["measured"]),
    "@@REP_STRESS_RET@@": pct(stress_conds["S3-C1"]["measured"]),
    "@@REP_BTR_BASE@@": measured_min(base_conds["S3-C5"]),
    "@@REP_BTR_STRESS@@": measured_min(stress_conds["S3-C5"]),
    "@@REP_CONC_BASE@@": dec2(base_conds["S3-C6"]["measured"]),
    "@@REP_CONC_STRESS@@": dec2(stress_conds["S3-C6"]["measured"]),
    # grid-wide figures
    "@@A1_DD_MAX@@": dec4(max(a1_base_dd)),
    "@@A1_DD_MIN@@": dec4(min(a1_base_dd)),
    "@@A2_DD_MIN@@": dec4(min(base_dd)),
    "@@A2_DD_MAX@@": dec4(max(base_dd)),
    "@@A2_DD_MAX_STRESS@@": dec4(max(stress_dd)),
    "@@GROSS_MIN@@": dec4(min(gross)),
    "@@GROSS_MIN_BASE@@": dec4(min(gross_base)),
    "@@GROSS_MAX@@": dec4(max(gross)),
    "@@GROSS_EXCESS_MIN@@": dec4(min(gross) - 0.50),
    "@@GROSS_EXCESS_MAX@@": dec4(max(gross) - 0.50),
    "@@SCALAR_SESS_MIN@@": str(min(scalar_sessions)),
    "@@SCALAR_SESS_MAX@@": str(max(scalar_sessions)),
    "@@SCALAR_MEAN_MIN@@": dec4(min(scalar_means)),
    "@@SCALAR_MEAN_MAX@@": dec4(max(scalar_means)),
    "@@LOCKOUT_MIN@@": str(min(blocked)),
    "@@LOCKOUT_MAX@@": str(max(blocked)),
    "@@BAND3_COUNT@@": str(band3),
    "@@BAND2_COUNT@@": str(band2),
    "@@STOP_OUTLIER_COUNT@@": str(outlier_count),
    "@@STOP_OUTLIER_MAX@@": outlier_worst,
    "@@BEST_VARIANT@@": best["variant_id"][len(PREFIX_2):],
    "@@BEST_RET@@": pct(best["base_total_return"]),
    "@@BEST_DD@@": dec4(best["base_max_drawdown"]),
    "@@BEST_PF@@": dec4(best["base_profit_factor"]),
    "@@BEST_TRADES@@": str(best["base_closed_trades"]),
    # tests
    "@@TESTS_PASSED@@": str(tests_passed),
    "@@TESTS_FAILED@@": str(tests_failed),
    "@@TESTS_SKIPPED@@": str(tests_skipped),
    "@@TESTS_TOTAL@@": str(tests_total),
    "@@TESTS_PRIOR@@": str(tests_prior),
    "@@TESTS_NEW@@": str(tests_new),
    # tables
    "@@TABLE_BASE@@": section("### `#BASE` runs"),
    "@@TABLE_STRESS@@": section("### `#STRESS` runs (2x frictions)"),
    "@@TABLE_RISK_BASE@@": section("### Risk-architecture activity, `#BASE` runs"),
    "@@TABLE_RISK_STRESS@@": section("### Risk-architecture activity, `#STRESS` runs"),
    "@@TABLE_THROTTLE@@": section("### Exposure throttle and combined scalar, `#BASE` runs"),
    "@@TABLE_TURNOVER@@": section("### Turnover (fills summed across both declared runs)"),
    "@@TABLE_GATE@@": gate_table(),
    "@@TABLE_A1_A2@@": attempt_comparison(),
    "@@TABLE_A1_MONTHS@@": month_histogram(),
}

text = TEMPLATE.read_text(encoding="utf-8")
for token, value in substitutions.items():
    if token not in text:
        raise SystemExit("template does not use %s" % token)
    text = text.replace(token, value)
leftover = [line for line in text.splitlines() if "@@" in line]
if leftover:
    raise SystemExit("unsubstituted placeholder: %r" % leftover[0])

OUT.write_text(text, encoding="utf-8", newline="\n")

written = OUT.read_text(encoding="utf-8")
print("wrote governance/generation_2/%s" % OUT.name)
print("  bytes            %d" % OUT.stat().st_size)
print("  lines            %d" % len(written.splitlines()))
print("  authored_utc     %s" % now)
print("  disclosure       %d chars  sha256 %s" % (len(disclosure), digest))
print("  disclosure carried verbatim in the written report: %s" % (disclosure in written))
print("  validation reuse carried verbatim:                 %s"
      % (lock["validation_reuse_disclosure"] in written))
print("  what-this-adds carried verbatim:                   %s"
      % (protocol["what_this_attempt_adds_over_attempt_1"] in written))
print("  file sha256      %s" % hashlib.sha256(OUT.read_bytes()).hexdigest())
print()
print("derived figures substituted (verify against _tables.txt):")
for key in sorted(substitutions):
    if key.startswith("@@TABLE") or key in ("@@ADAPTATION_DISCLOSURE@@", "@@WHAT_THIS_ADDS@@",
                                            "@@VALIDATION_REUSE@@", "@@MC_NOCORR@@",
                                            "@@MC_ADAPTIVE@@", "@@DECL_PREDICATE@@"):
        continue
    value = substitutions[key].encode("ascii", "backslashreplace").decode("ascii")
    print("  %-26s %s" % (key.strip("@"), value))
