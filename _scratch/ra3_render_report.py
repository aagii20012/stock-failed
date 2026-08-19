"""Render the Generation 2 Stage 3 Attempt 3 development research report.

Modelled on ``g2a2_render_report.py``, with the differences Attempt 3 forces:

* The builder holds Markdown carriers of the adaptation disclosure to **byte-equality**, permitting
  no ``normalised_prose`` relaxation. Attempt 2's protocol Markdown hard-wrapped its 842-character
  paragraph inside a blockquote and stored 858 characters, which is what ``G2A2-CONFLICT-29`` records
  and why that builder relaxed for one named artifact. Nothing here may wrap: the sealed string is
  written onto one unwrapped ``> `` line and this script refuses if it is not byte-present.
* Substitution runs in three passes, ``@@TABLE_X@@`` first, because the bare-token regex also matches
  a table token.
* Every value comes off disk. The digests in section 3 are recomputed from the named files and
  compared against the sealer's record; the verdict token is derived from the sealed
  ``verdict_token_derivation`` and asserted against both the evidence and the builder's constant; the
  test counts are parsed from the capture and the floor is subtracted rather than typed; the
  structural values hard-written into section 14 are checked against the evidence that produced them.

Output is LF-only UTF-8. The reporting tail is ASCII, because the console is cp1252 and the sealed
disclosure carries U+2212.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import sys
from decimal import Decimal
from pathlib import Path

SCRATCH = Path(__file__).resolve().parent
ROOT = SCRATCH.parent / "stockedge100"
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.audit import sha256_bytes, sha256_file  # noqa: E402
from stockedge100.reporting.g2_partition_lock import normalised_prose  # noqa: E402
from stockedge100.reporting.g2_stage3_attempt3_package import VERDICT as BUILDER_VERDICT  # noqa: E402

TEMPLATE = SCRATCH / "ra3_report_template.md"
TABLES = SCRATCH / "_ra3_tables.txt"
OUT = ROOT / "governance" / "generation_2" / "STAGE_3_G2_ROTATION_RA3_RESEARCH_REPORT.md"
BUILDER = ROOT / "src" / "stockedge100" / "reporting" / "g2_stage3_attempt3_package.py"
CAPTURE = ROOT / "reports" / "stage3_g2_attempt3" / "pytest_stage3_g2_attempt3_output.txt"
TEST_SUMMARY = ROOT / "reports" / "stage3_g2_attempt3" / "STAGE_3_G2_A3_TEST_SUMMARY.md"
SEAL_RECORD = ROOT / "governance" / "generation_2" / "STAGE_3_G2_ROTATION_RA3_PROTOCOL.sha256"

EXPECTED_SCALARS = 204
EXPECTED_CONFLICT_ROWS = 22
A2_FLOOR_EXPECTED = 1142
RED_TEST = "test_no_stage_4_module_can_reach_restricted_data_or_a_broker"


def check(condition, message):
    if not condition:
        raise SystemExit("RENDER REFUSED: %s" % message)


def ascii_(value):
    return str(value).encode("ascii", "backslashreplace").decode("ascii")


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


PROT = load("config/generation_2/g2_rotation_ra3_protocol.json")
CRIT = load("config/generation_2/g2_gate_criteria_ra3.json")
LOCK = load("governance/generation_2/STAGE_1_G2_PARTITION_LOCK.json")
SEAL = load("governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.json")
EV = load("reports/stage3_g2_attempt3/STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json")

SOURCES = {"PROT": PROT, "CRIT": CRIT, "LOCK": LOCK, "SEAL": SEAL, "EV": EV}


def deref(source, path):
    node = SOURCES[source]
    for part in path.split("."):
        if isinstance(node, dict):
            check(part in node, "%s has no key %r on path %s" % (source, part, path))
            node = node[part]
        elif isinstance(node, list) and part.isdigit():
            index = int(part)
            check(index < len(node), "%s index %d out of range on path %s" % (source, index, path))
            node = node[index]
        else:
            check(False, "%s is not a dict or list at %r on path %s" % (source, part, path))
    return node


# --------------------------------------------------------------------------------------------------
# 1. the sealed digests, recomputed from the named files before anything is substituted
# --------------------------------------------------------------------------------------------------

record_digests = {}
for line in SEAL_RECORD.read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    digest, rel = line.split(None, 1)
    rel = rel.strip()
    target = ROOT / rel
    check(target.is_file(), "the seal record names %s, which is not a file" % rel)
    actual = sha256_file(target)
    check(actual == digest, "%s: the seal record says %s, the file on disk is %s" % (rel, digest, actual))
    record_digests[rel] = digest
check(len(record_digests) == 5, "the seal record carries %d lines, expected 5" % len(record_digests))

sealed_inputs = SEAL["sealed_inputs"]
check(isinstance(sealed_inputs, dict), "sealed_inputs is not a path -> digest mapping")
for rel, digest in sealed_inputs.items():
    target = ROOT / rel
    check(target.is_file(), "sealed_inputs names %s, which is not a file" % rel)
    actual = sha256_file(target)
    check(actual == digest, "%s: the seal says %s, the file on disk is %s" % (rel, digest, actual))

# Nothing hashes itself: the protocol's own two artifacts are held by the surrounding record only.
for own in ("governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.md",
            "governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.json"):
    check(own not in sealed_inputs, "%s hashes itself inside sealed_inputs" % own)
    check(own in record_digests, "%s is not covered by the seal record" % own)

DIGESTS = {
    "SHA_PROTOCOL_MD": record_digests["governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.md"],
    "SHA_PROTOCOL_JSON": record_digests["governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.json"],
    "SHA_PROTOCOL_CFG": record_digests["config/generation_2/g2_rotation_ra3_protocol.json"],
    "SHA_CRITERIA": record_digests["config/generation_2/g2_gate_criteria_ra3.json"],
    "SHA_COST_MODEL": record_digests["config/generation_2/g2_cost_model.json"],
    "SHA_CHARTER": sealed_inputs["governance/generation_2/STAGE_10_GENERATION_2_CHARTER.md"],
    "SHA_LOCK_JSON": sealed_inputs["governance/generation_2/STAGE_1_G2_PARTITION_LOCK.json"],
}

# --------------------------------------------------------------------------------------------------
# 2. the seal run record, located by stage substring rather than by a typed filename
# --------------------------------------------------------------------------------------------------

seal_runs = []
for path in sorted((ROOT / "runs").glob("SE100-R-*.json")):
    record = json.loads(path.read_text(encoding="utf-8"))
    if "attempt_3_preregistration" in str(record.get("stage", "")):
        seal_runs.append((path, record))
check(len(seal_runs) == 1,
      "%d run records carry an attempt_3_preregistration stage, expected 1" % len(seal_runs))
seal_run_path, seal_run = seal_runs[0]
check(seal_run["run_id"] == SEAL["run_id"],
      "the seal names run %s, the run record is %s" % (SEAL["run_id"], seal_run["run_id"]))
check(seal_run["timestamp_utc"] == SEAL["sealed_utc"],
      "the seal and its run record disagree on the sealing time")
SEAL_REPO_STATE_ID = seal_run["repo_state_id"]
check(re.fullmatch(r"[0-9a-f]{64}", SEAL_REPO_STATE_ID),
      "the seal run record's repo_state_id is not a sha256")

# --------------------------------------------------------------------------------------------------
# 3. the verdict token, derived from the sealed derivation and asserted three ways
# --------------------------------------------------------------------------------------------------

vtd = CRIT["verdict_token_derivation"]
sv = EV["stage_verdict"]
admitted = sv["admitted_candidates"]
derived_token = vtd["pass_token"] if admitted else vtd["fail_token"]
check(derived_token == sv["verdict_token"],
      "derived %s, the evidence records %s" % (derived_token, sv["verdict_token"]))
check(sv["pass_token"] == vtd["pass_token"] and sv["fail_token"] == vtd["fail_token"],
      "the evidence's tokens are not the sealed criteria's tokens")
withheld = sv["prior_attempt_tokens_withheld"]
check(derived_token not in withheld, "the derived token belongs to a prior attempt")
verdict = "%s — %s" % (sv["verdict"], derived_token)
check(verdict == BUILDER_VERDICT,
      "the builder's VERDICT is %r, this render derived %r" % (ascii_(BUILDER_VERDICT), ascii_(verdict)))

permissive = EV["candidate_results"][0]["admission_basis"]["permissive_base_only_reading_would_give"]
check(isinstance(permissive, bool), "permissive_base_only_reading_would_give is not a boolean")
permissive_token = vtd["pass_token"] if permissive else vtd["fail_token"]

# --------------------------------------------------------------------------------------------------
# 4. the adaptation disclosure
# --------------------------------------------------------------------------------------------------

disclosure = PROT["adaptation_disclosure_verbatim"]
carriage = EV["adaptation_disclosure_carriage"]
check(disclosure == EV["adaptation_disclosure_verbatim"],
      "the protocol config and the evidence disagree on the disclosure text")
check("\n" not in disclosure and "\r" not in disclosure,
      "the sealed disclosure contains a newline and cannot be carried on one blockquote line")
check(len(disclosure) == carriage["characters"],
      "the disclosure is %d characters, the evidence records %d" % (len(disclosure), carriage["characters"]))
disclosure_sha = sha256_bytes(disclosure.encode("utf-8"))
check(disclosure_sha == carriage["sha256_of_utf8"],
      "the disclosure hashes to %s, the evidence records %s" % (disclosure_sha, carriage["sha256_of_utf8"]))
check(carriage["this_file_is_a_required_carrier"] is True, "the evidence is not a required carrier")
check(str(OUT.relative_to(ROOT)).replace("\\", "/") in carriage["must_appear_verbatim_in"],
      "this report is not on the disclosure's carrier list")

# --------------------------------------------------------------------------------------------------
# 5. the bare-token map, all of it dereferenced
# --------------------------------------------------------------------------------------------------

PROSE = {
    "ADAPTATION_DISCLOSURE": ("PROT", "adaptation_disclosure_verbatim"),
    "DISCLOSURE_ENFORCEMENT": ("PROT", "adaptation_disclosure_carriage_requirement.enforcement"),
    "DECL_PREDICATE": ("PROT", "declared_before_any_strategy_code_measurement.predicate"),
    "WHAT_THIS_CHANGES": ("PROT", "what_this_attempt_changes_from_attempt_2"),
    "WHAT_THIS_ADDS": ("PROT", "what_this_attempt_adds_over_attempt_1"),
    "CONFLICT_NUMBERING": ("PROT", "conflicts_declared_in_the_gate_criteria.note"),
    "SINGLE_DIFF": ("PROT", "risk_architecture.single_difference_from_ra2"),
    "WHY_NOT_GRIDDED": ("PROT", "risk_architecture.why_not_gridded"),
    "COMBINED_FORMULA": ("PROT", "risk_architecture.combined_scalar.formula"),
    "LADDER_PROVENANCE": ("PROT", "risk_architecture.components.RA3-4.provenance.statement"),
    "LADDER_ABS_CEILINGS": ("PROT", "risk_architecture.components.RA3-4.provenance.absolute_ceilings"),
    "DOF_REMOVED": ("PROT", "risk_architecture.components.RA3-4.provenance."
                            "degrees_of_freedom_removed_by_this_change"),
    "LADDER_FALSIFY": ("PROT", "risk_architecture.components.RA3-4.provenance."
                               "what_would_falsify_the_reasoning"),
    "SEL2_MECHANISM": ("PROT", "representative_selection_rule.structural_enforcement.mechanism"),
    "SEL2_IMPORT_ASSERTION": ("PROT", "representative_selection_rule.structural_enforcement."
                                      "import_time_assertion"),
    "SEL2_NEIGHBOURS_DEF": ("PROT", "representative_selection_rule.steps.1.neighbours"),
    "SEL2_NEIGHBOUR_COUNTS": ("PROT", "representative_selection_rule.steps.1.neighbour_counts"),
    "SEL2_WHY": ("PROT", "representative_selection_rule.why_it_changes"),
    "SEL2_RETRO": ("PROT", "representative_selection_rule.retrospective_check_disclosure.statement"),
    "SEL2_RETRO_NOT": ("PROT", "representative_selection_rule.retrospective_check_disclosure."
                               "what_the_check_did_not_do"),
    "SEL2_RETRO_WHY": ("PROT", "representative_selection_rule.retrospective_check_disclosure."
                               "why_disclosed"),
    "NO_RESELECTION": ("PROT", "representative_selection_rule.no_reselection"),
    "MC_NOCORR": ("PROT", "multiple_comparisons_disclosure.no_correction_applied"),
    "MC_ADAPTIVE": ("PROT", "multiple_comparisons_disclosure.adaptive_design_note"),
    "MC_THIRD": ("PROT", "multiple_comparisons_disclosure.third_attempt_note"),
    "SC7_CONSEQUENCE": ("PROT", "structural_consequences_declared_before_running.SC-7.consequence"),
    "GENERATION_ID": ("PROT", "generation_id"),
    "STRATEGY_ID": ("PROT", "strategy_id"),
    "UNIVERSE_VERSION": ("PROT", "eligible_universe.universe_version"),
    "UNIVERSE_IDENTITY": ("PROT", "eligible_universe.universe_identity_sha256"),
    "MEMBERS": ("PROT", "eligible_universe.member_count"),
    "MONTHLY_REB": ("PROT", "rebalance.measured_counts.monthly"),
    "QUARTERLY_REB": ("PROT", "rebalance.measured_counts.quarterly"),
    "WINDOW_START": ("PROT", "window.development.from"),
    "BOUND": ("PROT", "window.development.to"),
    "RUN_START": ("PROT", "run_span.run_start"),
    "RUN_END": ("PROT", "run_span.run_end"),
    "SESSIONS": ("PROT", "run_span.sessions"),
    "BINDING_SYMBOL": ("PROT", "run_span.binding_symbol"),
    "BINDING_INCEPTION": ("PROT", "run_span.binding_symbol_inception"),
    "UNION_SESSIONS": ("PROT", "run_span.development_union_sessions"),
    "VALIDATION_REUSE": ("LOCK", "validation_reuse_disclosure"),
    "LATEST_LOADED": ("EV", "window.latest_session_loaded"),
    "FAIL_ROUTE": ("EV", "stage_verdict.fail_route"),
    "SEAL_UTC": ("SEAL", "sealed_utc"),
    "SEAL_RUN_ID": ("SEAL", "run_id"),
}

resolved = {}
for token, (source, path) in PROSE.items():
    value = deref(source, path)
    if isinstance(value, str):
        check("\n" not in value and "\r" not in value,
              "sealed value %s (%s.%s) contains a newline; a wrapped carrier would not be byte-equal"
              % (token, source, path))
    resolved[token] = value if isinstance(value, str) else json.dumps(value)

# The two sealed carriers of the conflict-numbering note must agree, or the report would quote one
# and the decision record the other.
check(PROT["conflicts_declared_in_the_gate_criteria"]["note"]
      == EV["conflicts_declared_in_the_gate_criteria"]["note"],
      "the protocol config and the evidence disagree on the conflict-numbering note")

# --------------------------------------------------------------------------------------------------
# 6. the emitted tables and their scalars
# --------------------------------------------------------------------------------------------------

TABLES_TEXT = TABLES.read_text(encoding="utf-8")
TABLE_LINES = TABLES_TEXT.splitlines()


def section(heading):
    starts = [i for i, line in enumerate(TABLE_LINES) if line.strip() == "### " + heading]
    check(len(starts) == 1,
          "the tables file has %d sections named %r, expected 1" % (len(starts), heading))
    index = starts[0] + 1
    body = []
    while index < len(TABLE_LINES):
        line = TABLE_LINES[index]
        if line.startswith("### ") or line.startswith("=== "):
            break
        body.append(line)
        index += 1
    while body and not body[0].strip():
        body.pop(0)
    while body and not body[-1].strip():
        body.pop()
    check(body, "section %r is empty" % heading)
    return "\n".join(body)


TABLE_MAP = {
    "TABLE_THREEWAY_AGG": "three-way aggregate",
    "TABLE_A1_A2_A3": "three-way per variant",
    "TABLE_A1_MONTHS": "A1 shutdown months",
    "TABLE_LADDER_AB": "ladder engagement A3 vs A2",
    "TABLE_RANKING": "selection ranking",
    "TABLE_NEIGHBOURS": "neighbour scores",
    "TABLE_OWN": "own quantities",
    "TABLE_GATE": "gate conditions",
    "TABLE_BASE": "base runs",
    "TABLE_STRESS": "stress runs",
    "TABLE_RISK_BASE": "risk base",
    "TABLE_RISK_STRESS": "risk stress",
    "TABLE_THROTTLE": "throttle base",
    "TABLE_TURNOVER": "turnover",
    "TABLE_BAND_DEPTH": "band depth",
}

scalars = {}
for line in section("scalars").splitlines():
    if " = " not in line:
        continue
    name, value = line.split(" = ", 1)
    name = name.strip()
    check(name not in scalars, "the tables file defines scalar %s twice" % name)
    scalars[name] = value.strip()
check(len(scalars) == EXPECTED_SCALARS,
      "the tables file carries %d scalars, expected %d" % (len(scalars), EXPECTED_SCALARS))

deepest = max(Decimal(scalars["A3_DD_MAX"]), Decimal(scalars["A3_DD_MAX_STRESS"]))
EXTRA = {
    "MODULE_COUNT": str(deref("EV", "prior_attempt_module_verification.module_count")),
    "CUM_VARIANTS": str(deref("PROT", "multiple_comparisons_disclosure."
                                      "cumulative_variants_this_hypothesis_family")),
    "CUM_RUNS": str(deref("PROT", "multiple_comparisons_disclosure."
                                  "cumulative_runs_this_hypothesis_family")),
    "LADDERS_IDENTICAL": json.dumps(deref("EV", "risk_architecture.generation_1_provenance."
                                                "ladders_are_identical")),
    "DELETED_TIER": "(%s)" % ", ".join(deref("EV", "risk_architecture.single_difference_from_ra2."
                                                   "deleted_tier")),
    "DEEPEST_DD_PCT": "%.2f%%" % (deepest * 100),
}
check(EXTRA["LADDERS_IDENTICAL"] == "true",
      "the evidence does not record RA3's ladder as identical to Generation 1's RA1")
for name in EXTRA:
    check(name not in scalars, "%s is both an emitted scalar and a render-time extra" % name)
scalars.update(EXTRA)

# --------------------------------------------------------------------------------------------------
# 7. test counts, parsed rather than typed
# --------------------------------------------------------------------------------------------------

capture = CAPTURE.read_text(encoding="utf-8")
match = re.search(r"^(\d+) failed, (\d+) passed in ", capture, re.M)
check(match is not None, "the pytest capture carries no '<n> failed, <n> passed in' summary line")
tests_failed = int(match.group(1))
tests_passed = int(match.group(2))
tests_total = tests_failed + tests_passed
check(tests_failed == 1,
      "expected exactly the one inherited S4-CONFLICT-7 failure, the capture reports %d" % tests_failed)
check(RED_TEST in capture, "the capture does not name the S4-CONFLICT-7 test %s" % RED_TEST)

summary_text = TEST_SUMMARY.read_text(encoding="utf-8")
new_rows = re.findall(r"^(tests/\S+\.py)\s+(\d+)$", summary_text, re.M)
check(len(new_rows) == 2, "the test summary lists %d new test files, expected 2" % len(new_rows))
for rel, _ in new_rows:
    check((ROOT / rel).is_file(), "the test summary names %s, which is not a file" % rel)
tests_new = sum(int(count) for _, count in new_rows)
tests_floor = tests_total - tests_new
check(tests_floor == A2_FLOOR_EXPECTED,
      "derived floor %d does not match Attempt 2's recorded %d" % (tests_floor, A2_FLOOR_EXPECTED))
check("Attempt 2 left the floor at **%d** tests" % tests_floor in summary_text,
      "the test summary does not state the derived floor %d" % tests_floor)
check("| **Total** | **%d** |" % tests_total in summary_text,
      "the test summary's total is not the capture's %d" % tests_total)

# --------------------------------------------------------------------------------------------------
# 8. the structural values section 14 writes as literals
# --------------------------------------------------------------------------------------------------

cr = EV["candidate_results"][0]
check(len(cr["conditions"]) == 7,
      "the candidate carries %d conditions, section 14 says 7" % len(cr["conditions"]))
check(sv["candidates_evaluated"] == 1,
      "the evidence evaluated %d candidates, section 14 says 1" % sv["candidates_evaluated"])
check(len(admitted) == 0,
      "the evidence admitted %d candidates, section 14 says 0" % len(admitted))
check(cr["admitted"] is False, "the candidate is admitted but section 14 says admissible false")
check(cr["conditions_met"] == int(scalars["CONDITIONS_MET"]),
      "the evidence met %d conditions, the tables say %s"
      % (cr["conditions_met"], scalars["CONDITIONS_MET"]))
check(cr["conditions_not_met"] == ["S3-C6"],
      "the not-met list is %r, expected exactly S3-C6" % (cr["conditions_not_met"],))
check(EV["live_trading_authorized"] is False, "live_trading_authorized is not false")

# --------------------------------------------------------------------------------------------------
# 9. the conflict ids the builder will write must be the ids section 18 carries
# --------------------------------------------------------------------------------------------------

builder_lines = BUILDER.read_text(encoding="utf-8").splitlines()
opens = [i for i, line in enumerate(builder_lines) if line.strip() == "conflicts_found=["]
check(len(opens) == 1, "the builder has %d conflicts_found lists, expected 1" % len(opens))
start = opens[0]
indent = len(builder_lines[start]) - len(builder_lines[start].lstrip())
closes = [i for i in range(start + 1, len(builder_lines))
          if builder_lines[i].strip() in ("]", "],")
          and len(builder_lines[i]) - len(builder_lines[i].lstrip()) == indent]
check(closes, "the builder's conflicts_found list is not closed at its own indent")
region = "\n".join(builder_lines[start + 1:closes[0]])
builder_ids = re.findall(r'"([A-Z0-9]+-CONFLICT-\d+)', region)
check(len(builder_ids) == EXPECTED_CONFLICT_ROWS,
      "the builder writes %d conflicts, expected %d" % (len(builder_ids), EXPECTED_CONFLICT_ROWS))
check(len(set(builder_ids)) == len(builder_ids), "the builder writes a duplicate conflict id")

# --------------------------------------------------------------------------------------------------
# 10. substitute: tables, then @@S:...@@ scalars, then bare tokens
# --------------------------------------------------------------------------------------------------

text = TEMPLATE.read_text(encoding="utf-8")
check("\r" not in text, "the template carries CRLF")

for token, heading in TABLE_MAP.items():
    placeholder = "@@%s@@" % token
    check(text.count(placeholder) == 1,
          "the template uses %s %d times, expected once" % (placeholder, text.count(placeholder)))
    text = text.replace(placeholder, section(heading))
leftover_tables = sorted(set(re.findall(r"@@TABLE_[A-Z0-9_]+@@", text)))
check(not leftover_tables, "unsubstituted table token: %s" % (leftover_tables[:1],))

used_scalars = set()


def scalar_sub(match):
    name = match.group(1)
    check(name in scalars, "the template asks for scalar %s, which is not measured anywhere" % name)
    used_scalars.add(name)
    return scalars[name]


text = re.sub(r"@@S:([A-Z0-9_]+)@@", scalar_sub, text)
check("@@S:" not in text, "an @@S:...@@ token survived substitution")

authored_utc = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
substitutions = dict(resolved)
substitutions.update(DIGESTS)
substitutions.update({
    "SEAL_REPO_STATE_ID": SEAL_REPO_STATE_ID,
    "AUTHORED_UTC": authored_utc,
    "VERDICT": verdict,
    "PERMISSIVE_READING": permissive_token,
    "DISCLOSURE_LEN": str(len(disclosure)),
    "DISCLOSURE_SHA": disclosure_sha,
    "TESTS_TOTAL": str(tests_total),
    "TESTS_PASSED": str(tests_passed),
    "TESTS_FAILED": str(tests_failed),
    "TESTS_NEW": str(tests_new),
    "TESTS_FLOOR": str(tests_floor),
})

for token, value in sorted(substitutions.items()):
    placeholder = "@@%s@@" % token
    check(placeholder in text, "the template does not use %s" % placeholder)
    text = text.replace(placeholder, value)

leftover = [line for line in text.splitlines() if "@@" in line]
check(not leftover, "unsubstituted placeholder: %r" % (ascii_(leftover[0]) if leftover else "",))

unused = sorted(set(scalars) - used_scalars - set(EXTRA))
if unused:
    print("note: %d emitted scalars are not referenced by the template" % len(unused))

# --------------------------------------------------------------------------------------------------
# 11. post-substitution predicates on the rendered document
# --------------------------------------------------------------------------------------------------

check(text.count(disclosure) >= 1,
      "the rendered report does not carry the sealed disclosure byte-exact")
check(("> " + disclosure) in text,
      "the disclosure is present but not as an unwrapped blockquote line")
check(normalised_prose(disclosure) in normalised_prose(text),
      "the disclosure fails the normalised-prose check the builder also applies")
# The sealed prior_attempt_tokens_note forbids an Attempt 3 artifact emitting any of the four tokens
# belonging to the two closed attempts. Section 12's three-way comparison therefore identifies the
# prior verdicts by the directory that carries them, and the emitter asserts token identity, rather
# than reproducing the strings here. This gate's own pass token must likewise be absent: a FAIL report
# that carried it would read as a passed gate.
for token in withheld:
    check(token not in text, "the report emits a prior attempt's verdict token %s" % token)
check(vtd["pass_token"] not in text,
      "the report carries this gate's pass token, which a FAIL report must not")
check(derived_token in text, "the report does not carry its own verdict token")
check(chr(10).join(["```", verdict, "```"]) in text,
      "no fenced block carries exactly the derived verdict %s" % ascii_(verdict))

rendered_ids = re.findall(r"^\| `([A-Z0-9]+-CONFLICT-\d+)`", text, re.M)
check(len(rendered_ids) == EXPECTED_CONFLICT_ROWS,
      "section 18 carries %d conflict rows, expected %d" % (len(rendered_ids), EXPECTED_CONFLICT_ROWS))
check(sorted(rendered_ids) == sorted(builder_ids),
      "section 18 and the builder disagree: only in report %r, only in builder %r"
      % (sorted(set(rendered_ids) - set(builder_ids)), sorted(set(builder_ids) - set(rendered_ids))))
check("S4-CONFLICT-7" in text, "the report does not name the permanent red test's conflict id")
check(str(tests_total) in text and str(tests_floor) in text, "the test counts did not reach the report")

OUT.write_text(text, encoding="utf-8", newline="\n")
data = OUT.read_bytes()
check(b"\r\n" not in data, "the written report carries CRLF")
check(disclosure.encode("utf-8") in data, "the written bytes do not carry the disclosure")

# --------------------------------------------------------------------------------------------------
# 12. ASCII reporting tail
# --------------------------------------------------------------------------------------------------

print("wrote %s" % OUT.relative_to(ROOT.parent))
print("  bytes            %d" % len(data))
print("  lines            %d" % len(text.splitlines()))
print("  crlf             %d" % data.count(b"\r\n"))
print("  sha256           %s" % sha256_file(OUT))
print("  authored_utc     %s" % authored_utc)
print("  disclosure       %d chars, sha %s" % (len(disclosure), disclosure_sha))
print("  disclosure       byte-exact in report: %s" % (disclosure in text))
print("  verdict          %s" % ascii_(verdict))
print("  permissive       %s" % permissive_token)
print("  seal run         %s (%s)" % (seal_run["run_id"], seal_run_path.name))
print("  seal repo_state  %s" % SEAL_REPO_STATE_ID)
print("  tests            total %d passed %d failed %d floor %d new %d"
      % (tests_total, tests_passed, tests_failed, tests_floor, tests_new))
print("  conflict rows    %d (builder %d, sets equal)" % (len(rendered_ids), len(builder_ids)))
print("  tables pasted    %d" % len(TABLE_MAP))
print("  scalars used     %d of %d" % (len(used_scalars), len(scalars)))
print("  bare tokens      %d" % len(substitutions))
print("  digests verified %d from the record, %d from sealed_inputs"
      % (len(record_digests), len(sealed_inputs)))
print("  extras")
for name in sorted(EXTRA):
    print("    %-20s %s" % (name, ascii_(EXTRA[name])))
