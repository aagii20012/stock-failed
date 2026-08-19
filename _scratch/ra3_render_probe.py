"""Resolve every bare ``@@NAME@@`` token of the Attempt 3 report template against the tree.

The renderer is long and the map is the part that can silently be wrong, so the map is exercised
here first: each entry names a source file and a dotted path, this script dereferences all of them,
and anything that does not resolve is printed as ``MISSING`` rather than discovered later inside a
300-line render.

Six ``@@S:NAME@@`` scalars have no backing line in ``_ra3_tables.txt`` and are resolved here too,
because they are the renderer's ``EXTRA`` dict and each one is a measurement rather than a literal.

ASCII output only: values are backslash-escaped, because the console is cp1252 and the sealed
disclosure contains U+2212.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

SCRATCH = Path(__file__).resolve().parent
ROOT = SCRATCH.parent / "stockedge100"
TEMPLATE = SCRATCH / "ra3_report_template.md"


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


PROT = load("config/generation_2/g2_rotation_ra3_protocol.json")
CRIT = load("config/generation_2/g2_gate_criteria_ra3.json")
LOCK = load("governance/generation_2/STAGE_1_G2_PARTITION_LOCK.json")
SEAL_JSON = load("governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.json")
EV = load("reports/stage3_g2_attempt3/STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json")

SOURCES = {"PROT": PROT, "CRIT": CRIT, "LOCK": LOCK, "SEAL": SEAL_JSON, "EV": EV}

# token -> (source, dotted path)   |   token -> ("COMPUTED", explanation)
MAP = {
    # --- sealed prose from the protocol config ---------------------------------------------------
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
    "DOF_REMOVED": ("PROT",
                    "risk_architecture.components.RA3-4.provenance."
                    "degrees_of_freedom_removed_by_this_change"),
    "LADDER_FALSIFY": ("PROT",
                       "risk_architecture.components.RA3-4.provenance."
                       "what_would_falsify_the_reasoning"),
    "SEL2_MECHANISM": ("PROT", "representative_selection_rule.structural_enforcement.mechanism"),
    "SEL2_WHY": ("PROT", "representative_selection_rule.why_it_changes"),
    "SEL2_NEIGHBOURS_DEF": ("PROT", "representative_selection_rule.steps.1.neighbours"),
    "SEL2_NEIGHBOUR_COUNTS": ("PROT", "representative_selection_rule.steps.1.neighbour_counts"),
    "SEL2_IMPORT_ASSERTION": ("PROT",
                              "representative_selection_rule.structural_enforcement."
                              "import_time_assertion"),
    "SEL2_RETRO": ("PROT",
                   "representative_selection_rule.retrospective_check_disclosure.statement"),
    "SEL2_RETRO_NOT": ("PROT",
                       "representative_selection_rule.retrospective_check_disclosure."
                       "what_the_check_did_not_do"),
    "SEL2_RETRO_WHY": ("PROT",
                       "representative_selection_rule.retrospective_check_disclosure.why_disclosed"),
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
    # --- partition lock --------------------------------------------------------------------------
    "VALIDATION_REUSE": ("LOCK", "validation_reuse_disclosure"),
    # --- evidence --------------------------------------------------------------------------------
    "LATEST_LOADED": ("EV", "window.latest_session_loaded"),
    "FAIL_ROUTE": ("EV", "stage_verdict.fail_route"),
    # --- seal ------------------------------------------------------------------------------------
    "SEAL_UTC": ("SEAL", "sealed_utc"),
    "SEAL_RUN_ID": ("SEAL", "run_id"),
    # --- computed at render time -----------------------------------------------------------------
    "AUTHORED_UTC": ("COMPUTED", "system clock at render time"),
    "VERDICT": ("COMPUTED", "derived from CRIT verdict_token_derivation, asserted against builder"),
    "PERMISSIVE_READING": ("COMPUTED",
                           "EV candidate_results[0].admission_basis."
                           "permissive_base_only_reading_would_give -> token"),
    "DISCLOSURE_LEN": ("COMPUTED", "len of the sealed disclosure"),
    "DISCLOSURE_SHA": ("COMPUTED", "sha256 of the sealed disclosure, checked against evidence"),
    "SHA_PROTOCOL_MD": ("COMPUTED", "from the .sha256 record, recomputed from disk"),
    "SHA_PROTOCOL_JSON": ("COMPUTED", "from the .sha256 record, recomputed from disk"),
    "SHA_PROTOCOL_CFG": ("COMPUTED", "from the .sha256 record, recomputed from disk"),
    "SHA_CRITERIA": ("COMPUTED", "from the .sha256 record, recomputed from disk"),
    "SHA_COST_MODEL": ("COMPUTED", "from the .sha256 record, recomputed from disk"),
    "SHA_CHARTER": ("COMPUTED", "from SEAL sealed_inputs, recomputed from disk"),
    "SHA_LOCK_JSON": ("COMPUTED", "from SEAL sealed_inputs, recomputed from disk"),
    "SEAL_REPO_STATE_ID": ("COMPUTED", "from the seal run record, located by stage substring"),
    "TESTS_TOTAL": ("COMPUTED", "parsed from the pytest capture"),
    "TESTS_PASSED": ("COMPUTED", "parsed from the pytest capture"),
    "TESTS_FAILED": ("COMPUTED", "parsed from the pytest capture"),
    "TESTS_NEW": ("COMPUTED", "collected from the two new test files"),
    "TESTS_FLOOR": ("COMPUTED", "TESTS_TOTAL - TESTS_NEW, asserted == 1142"),
}

EXTRA = {
    "MODULE_COUNT": ("EV", "prior_attempt_module_verification.module_count"),
    "CUM_VARIANTS": ("PROT",
                     "multiple_comparisons_disclosure.cumulative_variants_this_hypothesis_family"),
    "CUM_RUNS": ("PROT", "multiple_comparisons_disclosure.cumulative_runs_this_hypothesis_family"),
    "LADDERS_IDENTICAL": ("EV",
                          "risk_architecture.generation_1_provenance.ladders_are_identical"),
    "DELETED_TIER": ("EV", "risk_architecture.single_difference_from_ra2.deleted_tier"),
    "DEEPEST_DD_PCT": ("COMPUTED", "max of A3_DD_MAX and A3_DD_MAX_STRESS, as a percentage"),
}


def deref(source, path):
    node = SOURCES[source]
    for part in path.split("."):
        if isinstance(node, dict):
            if part not in node:
                return ("MISSING", "no key %r" % part)
            node = node[part]
        elif isinstance(node, list) and part.isdigit():
            index = int(part)
            if index >= len(node):
                return ("MISSING", "index %d out of range" % index)
            node = node[index]
        else:
            return ("MISSING", "not a dict or list at %r" % part)
    return ("OK", node)


def ascii_(value):
    return str(value).encode("ascii", "backslashreplace").decode("ascii")


template = TEMPLATE.read_text(encoding="utf-8")
bare = sorted(set(re.findall(r"@@([A-Z][A-Za-z0-9_]*)@@", template)))
bare = [name for name in bare if not name.startswith("TABLE_")]

print("=== bare tokens in template: %d ; mapped: %d ===" % (len(bare), len(MAP)))
unmapped = [name for name in bare if name not in MAP]
extra_mapped = [name for name in MAP if name not in bare]
for name in unmapped:
    print("  UNMAPPED   %s" % name)
for name in extra_mapped:
    print("  NOT IN TEMPLATE  %s" % name)
print()

failures = 0
for name in sorted(MAP):
    source, path = MAP[name]
    if source == "COMPUTED":
        print("  %-24s COMPUTED   %s" % (name, path))
        continue
    status, value = deref(source, path)
    if status == "MISSING":
        failures += 1
        print("  %-24s MISSING    %s.%s  (%s)" % (name, source, path, value))
        continue
    kind = type(value).__name__
    if isinstance(value, str):
        shown = "%s len=%d  %s" % (kind, len(value), ascii_(value)[:70])
    else:
        shown = "%s  %s" % (kind, ascii_(value)[:70])
        if isinstance(value, str) is False and "\n" in str(value):
            shown += "  <NEWLINE>"
    print("  %-24s %-6s %s" % (name, source, shown))
    if isinstance(value, str) and "\n" in value:
        failures += 1
        print("        NEWLINE INSIDE A SEALED PROSE VALUE -- the renderer refuses these")

print()
print("=== EXTRA scalars: %d ===" % len(EXTRA))
for name in sorted(EXTRA):
    source, path = EXTRA[name]
    if source == "COMPUTED":
        print("  %-24s COMPUTED   %s" % (name, path))
        continue
    status, value = deref(source, path)
    if status == "MISSING":
        failures += 1
        print("  %-24s MISSING    %s.%s  (%s)" % (name, source, path, value))
    else:
        print("  %-24s %-6s %s  %s" % (name, source, type(value).__name__, ascii_(value)[:60]))

print()
print("=== verdict token derivation ===")
vtd = CRIT["verdict_token_derivation"]
for key in sorted(vtd):
    print("  %-44s %s" % (key, ascii_(vtd[key])[:80]))
print("  evidence verdict_token: %s" % EV["stage_verdict"]["verdict_token"])

print()
print("=== disclosure ===")
disclosure = PROT["adaptation_disclosure_verbatim"]
print("  chars %d  sha256 %s" % (len(disclosure), hashlib.sha256(
    disclosure.encode("utf-8")).hexdigest()))
print("  evidence records %s" % EV["adaptation_disclosure_carriage"]["sha256_of_utf8"])
print("  newlines in it: %d (must be 0 for the one-line blockquote)" % disclosure.count("\n"))

print()
print("failures: %d" % failures)
