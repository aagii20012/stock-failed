"""Derive SE100-CFG-3105 (Attempt 3 protocol) from SE100-CFG-3103 (Attempt 2 protocol).

Run from stockedge100/.  Every block that Attempt 3 inherits unchanged is COPIED from the
sealed Attempt 2 file rather than retyped, so the two cannot silently diverge.  Every block
that changes is written here explicitly and is listed in CHANGED_KEYS below.

This script lives outside stockedge100/ so it perturbs no repo_state_id pattern, and it is the
only place the Attempt 3 strategy id appears outside config/ and governance/ before the seal.
"""

import copy
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path.cwd()
SRC = ROOT / "config/generation_2/g2_rotation_ra1_protocol.json"
OUT = ROOT / "config/generation_2/g2_rotation_ra3_protocol.json"

STRATEGY_ID = "SE100-G2-S3-C3-ROTATION-RA3"
EM = "—"
MINUS = "−"


def sha256(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def pin(rel, expect=None):
    got = sha256(rel)
    if expect is not None and got != expect:
        sys.exit("PIN MISMATCH %s: %s != %s" % (rel, got, expect))
    return got


d = json.loads(SRC.read_text(encoding="utf-8"))
out = {}

# ---------------------------------------------------------------- identity
out["artifact_id"] = "SE100-CFG-3105"
out["title"] = (
    "Generation 2 Stage 3 Attempt 3 strategy protocol - cross-sectional rotation under "
    "risk architecture RA3 and representative-selection rule SE100-G2-SEL-2"
)
out["version"] = "1.0.0"
out["project"] = d["project"]
out["generation"] = d["generation"]
out["generation_id"] = d["generation_id"]
out["stage"] = d["stage"]
out["gate_id"] = d["gate_id"]
out["attempt"] = 3

# ---------------------------------------------------------------- prior attempts
out["attempt_1_ref"] = copy.deepcopy(d["attempt_1_ref"])
out["attempt_1_ref"]["carried_from"] = (
    "SE100-CFG-3103.attempt_1_ref, copied field for field. Every digest in it was recomputed "
    "from the file it names before this file was written and all nine matched."
)

out["attempt_2_ref"] = {
    "strategy_id": d["strategy_id"],
    "protocol_config": "config/generation_2/g2_rotation_ra1_protocol.json",
    "protocol_config_sha256": pin("config/generation_2/g2_rotation_ra1_protocol.json"),
    "gate_criteria_config": "config/generation_2/g2_gate_criteria_ra1.json",
    "gate_criteria_config_sha256": pin(
        "config/generation_2/g2_gate_criteria_ra1.json",
        "3b9626214db6a6f6183384456489338ea19a277866e35a1aa6c09b0bacb3e625",
    ),
    "protocol_md": "governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.md",
    "protocol_md_sha256": pin("governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.md"),
    "protocol_json": "governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.json",
    "protocol_json_sha256": pin("governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.json"),
    "protocol_sha256_record": "governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.sha256",
    "protocol_sha256_record_sha256": pin(
        "governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.sha256"
    ),
    "research_report_md": "governance/generation_2/STAGE_3_G2_ROTATION_RA1_RESEARCH_REPORT.md",
    "research_report_md_sha256": pin(
        "governance/generation_2/STAGE_3_G2_ROTATION_RA1_RESEARCH_REPORT.md"
    ),
    "research_json": "reports/stage3_g2_attempt2/STAGE_3_G2_A2_ROTATION_RESEARCH.json",
    "research_json_sha256": pin(
        "reports/stage3_g2_attempt2/STAGE_3_G2_A2_ROTATION_RESEARCH.json"
    ),
    "decision_json": "reports/stage3_g2_attempt2/STAGE_3_G2_A2_DEVELOPMENT_ADMISSIBILITY.json",
    "decision_json_sha256": pin(
        "reports/stage3_g2_attempt2/STAGE_3_G2_A2_DEVELOPMENT_ADMISSIBILITY.json"
    ),
    "manifest_json": "reports/stage3_g2_attempt2/STAGE_3_G2_A2_ARTIFACT_MANIFEST.json",
    "manifest_json_sha256": pin(
        "reports/stage3_g2_attempt2/STAGE_3_G2_A2_ARTIFACT_MANIFEST.json"
    ),
    "run_record": "runs/SE100-R-20260816T030122Z.json",
    "run_record_stage": "STAGE_3_G2_ATTEMPT_2_ROTATION_RA1_DEVELOPMENT",
    "verdict": "FAIL - STAGE_3_G2_ATTEMPT_2_NO_CANDIDATE",
    "verdict_source": (
        "reports/stage3_g2_attempt2/stage_verdict.json, field verdict_token, read at the time "
        "this file was written rather than transcribed from the operating instruction."
    ),
    "fail_route": "REPRESENTATIVE_FAILED_AT_LEAST_ONE_CONDITION",
    "disposition": "CLOSED_READ_ONLY",
    "disposition_note": (
        "Attempt 2 is closed permanently. Its verdict stands. Nothing in this attempt edits, "
        "deletes, reopens, re-runs, loosens or supersedes any Attempt 2 artifact or module. "
        "Every file listed above is pinned here so that a change to any of them is detectable, "
        "not so that any of them may be changed. Attempt 3 disagrees with two of Attempt 2's "
        "stated positions " + EM + " its exclusion of the risk counters from selection, and its "
        "statement that no Attempt 3 is authorized " + EM + " and records both disagreements as "
        "numbered conflicts (G2A3-CONFLICT-26 and G2A3-CONFLICT-28 in SE100-CFG-3106) instead of "
        "editing the sentences it disagrees with."
    ),
    "run_record_is_not_pinned_by_digest": (
        "runs/ is append-only and outside every repo_state_id pattern, and a later stage appends "
        "to the directory rather than to the file. The record is pinned by id and stage string, "
        "which is what the Attempt 3 sealer looks it up by, and its module digests are re-read "
        "from it at seal time."
    ),
}

# ---------------------------------------------------------------- refs
for k in [
    "constitution_ref", "constitution_md_sha256", "constitution_json_sha256",
    "charter_ref", "partition_lock_ref", "partition_lock_md_sha256",
    "partition_lock_json_sha256", "charter_md_sha256",
    "cost_model_derivation_ref", "cost_model_derivation_sha256",
]:
    out[k] = d[k]

pin("governance/STAGE_0_CONSTITUTION.md", d["constitution_md_sha256"])
pin("governance/STAGE_0_CONSTITUTION.json", d["constitution_json_sha256"])
pin("governance/generation_2/STAGE_1_G2_PARTITION_LOCK.md", d["partition_lock_md_sha256"])
pin("governance/generation_2/STAGE_1_G2_PARTITION_LOCK.json", d["partition_lock_json_sha256"])
pin("governance/generation_2/STAGE_10_GENERATION_2_CHARTER.md", d["charter_md_sha256"])
pin(d["cost_model_derivation_ref"], d["cost_model_derivation_sha256"])

out["refs_reverified"] = (
    "Every digest in this block, in attempt_1_ref and in attempt_2_ref was recomputed from the "
    "file it names at the moment this file was generated. None was transcribed from SE100-CFG-3103 "
    "without being checked against the file itself."
)

out["gate_criteria_ref"] = "config/generation_2/g2_gate_criteria_ra3.json"
out["gate_criteria_sha256_not_recorded_here"] = (
    "SE100-CFG-3106 is sealed alongside this file and the two are mutually referential: it names "
    "this file as protocol_ref and this file names it as gate_criteria_ref. Recording either "
    "digest inside the other would make the pair unwritable. Both are covered by repo_state_id "
    "(config/**/*.json is recursive) and both are listed in the Attempt 3 artifact manifest."
)

# ---------------------------------------------------------------- declaration
out["declared_before_any_strategy_code"] = True
out["declaration_note"] = (
    "This file and its Markdown counterpart "
    "governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.md were written and sealed before "
    "any Attempt 3 strategy, engine, selection, gate or runner module existed, and before any "
    "Attempt 3 variant was run. That claim is machine-checked by the sealer, which measures "
    "contamination before it writes: no module under src/stockedge100 or tests may name this "
    "attempt's strategy_id, and every one of the seventeen Attempt 1 and Attempt 2 modules must "
    "still match the digest its own run record recorded. See "
    "declared_before_any_strategy_code_measurement. What this file cannot claim, and does not "
    "claim, is that the *development window* is pristine for this hypothesis family. It is not, "
    "and it is now less pristine than it was when SE100-CFG-3103 said the same thing: two full "
    "eighteen-variant grids have been run on this window and both results are known. See "
    "adaptation_disclosure_verbatim."
)
out["declared_before_any_strategy_code_measurement"] = {
    "contamination_predicate": "CONTENT_BASED",
    "predicate": (
        "No .py file under src/stockedge100 or tests contains the string %s at seal time."
        % STRATEGY_ID
    ),
    "why_not_path_based": d["declared_before_any_strategy_code_measurement"]["why_not_path_based"],
    "paired_immutability_check": (
        "Every module listed in prior_attempt_modules_immutable is re-hashed at seal time and "
        "must equal the digest recorded for it. The list is now seventeen modules, not Attempt "
        "2's nine: Attempt 1's nine plus Attempt 2's own eight, which became immutable the "
        "moment Attempt 2 closed. A content-based predicate alone would pass while a prior "
        "attempt's module was being quietly rewritten; the pair does not."
    ),
    "sealer_indirection_note": d["declared_before_any_strategy_code_measurement"][
        "sealer_indirection_note"
    ],
    "conflict_ref": "G2A3-CONFLICT-34",
    "supersedes_in_scope": (
        "G2A2-CONFLICT-3, which declared the same predicate over nine modules and is not edited."
    ),
}

out["prior_attempt_modules_immutable"] = {
    "count": 17,
    "attempt_1_modules": [
        "src/stockedge100/strategies/g2_rotation.py",
        "src/stockedge100/strategies/g2_gate.py",
        "src/stockedge100/strategies/g2_runner.py",
        "src/stockedge100/strategies/g2_window_guard.py",
        "src/stockedge100/backtest/g2_engine.py",
        "src/stockedge100/backtest/g2_costs.py",
        "src/stockedge100/reporting/g2_rotation_preregistration.py",
        "src/stockedge100/reporting/g2_stage3_evidence.py",
        "src/stockedge100/reporting/g2_stage3_package.py",
    ],
    "attempt_2_modules": [
        "src/stockedge100/strategies/g2_rotation_ra1.py",
        "src/stockedge100/strategies/g2_gate_ra1.py",
        "src/stockedge100/strategies/g2_runner_ra1.py",
        "src/stockedge100/backtest/g2_engine_ra1.py",
        "src/stockedge100/backtest/g2_episodes_ra1.py",
        "src/stockedge100/reporting/g2_rotation_ra1_preregistration.py",
        "src/stockedge100/reporting/g2_stage3_attempt2_evidence.py",
        "src/stockedge100/reporting/g2_stage3_attempt2_package.py",
    ],
    "attempt_1_list_source": (
        "SE100-CFG-3103.attempt_1_modules_immutable.modules, copied unchanged."
    ),
    "attempt_2_list_source": (
        "The eight Generation 2 modules created by Attempt 2, enumerated by listing "
        "src/stockedge100/{strategies,backtest,reporting} and subtracting Attempt 1's nine and "
        "the Stage 1 module g2_partition_lock.py, which belongs to neither attempt."
    ),
    "g2_partition_lock_excluded": (
        "src/stockedge100/backtest/g2_partition_lock.py is a Generation 2 STAGE 1 module. It is "
        "immutable for the ordinary reason that every sealed module is, and it is covered by "
        "repo_state_id, but it is not a Stage 3 attempt module and is not listed here."
    ),
    "digests_recorded_by": (
        "governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.json at seal time"
    ),
    "digests_not_recorded_here": d["attempt_1_modules_immutable"]["digests_not_recorded_here"],
}

out["serialisation"] = copy.deepcopy(d["serialisation"])
out["currency"] = d["currency"]

# ---------------------------------------------------------------- candidate
out["strategy_id"] = STRATEGY_ID
out["candidate_index"] = 3
out["candidate_index_note"] = (
    "C3, not C2 and not C1. Attempt 3 is a distinct candidate specification, not a re-run of "
    "Attempt 2's: it holds full sizing through a band in which Attempt 2's candidate was "
    "throttled to 75 percent, and it is selected by a different frozen rule. Constitution "
    "section 9 makes a gate conjunctive *within a candidate*, so reusing C2 would attach "
    "Attempt 2's already-recorded FAIL to the same candidate id and make two results look like "
    "one candidate evaluated twice. They are three candidates, evaluated once each, in a family "
    "whose development window is no longer pristine and has now been read twice. See "
    "G2A3-CONFLICT-24 in SE100-CFG-3106."
)
out["family"] = d["family"]
out["hypothesis"] = (
    "Cross-sectional relative strength over a fixed 34-member ETF universe, held in an equally "
    "weighted top-k basket and refreshed on a fixed calendar, produces a positive net return "
    "over the Generation 2 development window while remaining inside the constitutional "
    "research-shutdown ceiling, WHEN exposure is capped at half of equity, scaled down by "
    "realized portfolio volatility, staged down further once the equity drawdown reaches 8 "
    "percent, and cut at the position level by a fixed stop."
)
out["what_this_attempt_changes_from_attempt_2"] = (
    "Exactly two things, and nothing else. (1) The de-risk ladder loses its 5-to-8 percent rung, "
    "reverting to the three-band spacing Generation 1's RA1-5 sealed before Attempt 1 was ever "
    "run. (2) The representative-selection rule changes from lowest turnover to SE100-G2-SEL-2, "
    "a neighbourhood-stability score over four risk-behaviour counters. The signal, the "
    "universe, the calendar, the grid, the cost model, the gate thresholds, the aggregate "
    "ceiling, the volatility target, the stop, the lockout, the throttle and the episode ledger "
    "are all held fixed. Because two things change rather than one, this attempt cannot by "
    "itself attribute an outcome to either. That is stated here, before the run, rather than "
    "discovered afterwards."
)
out["what_this_attempt_adds_over_attempt_1"] = d["what_this_attempt_adds_over_attempt_1"]
out["what_this_attempt_adds_over_attempt_1_carriage"] = (
    "Copied verbatim from SE100-CFG-3103. It describes the risk architecture Attempt 3 still "
    "carries, minus one rung, and is retained so the lineage statement is not silently reworded."
)

out["adaptation_disclosure_verbatim"] = (
    "This pre-registration was designed after both Attempt 1 and Attempt 2's development results "
    "were known. Attempt 1 (no risk architecture) failed via research-shutdown on all 18 "
    "variants, clustered around the 2008 financial crisis. Attempt 2 (RA2 risk architecture) "
    "survived every variant without a shutdown, but its representative " + EM + " selected by a "
    "rule blind to return " + EM + " earned approximately 0.4% over thirteen years, indicating "
    "the risk architecture suppressed ordinary-market returns as well as crisis losses. Attempt "
    "3 makes two disclosed, evidence-informed changes: (1) a new representative-selection rule "
    "(SE100-G2-SEL-2) that screens for neighborhood stability across non-return risk-behavior "
    "statistics rather than raw turnover, and (2) a revised risk architecture (RA3) that removes "
    "a " + MINUS + "5%-drawdown de-risk tier RA2 had added beyond Generation 1's own original "
    "architecture, on the reasoning that a 5%-from-peak dip is common in ordinary markets and is "
    "a plausible cause of RA2's near-constant throttling. Both changes were selected using only "
    "non-return diagnostics already on record " + EM + " RA2's ladder-activation and "
    "combined-scalar statistics, and a retrospective (but not selection-informing) check of "
    "SEL-2 against Attempt 2's frozen data. No return figure from any prior attempt informed "
    "either change. This is nonetheless a third disclosed adaptation on the same hypothesis "
    "family, and cumulative multiplicity across all three attempts must be carried forward in "
    "any final assessment of this family."
)
out["adaptation_disclosure_carriage_requirement"] = {
    "must_appear_verbatim_in": [
        "governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.md",
        "governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.json",
        "governance/generation_2/STAGE_3_G2_ROTATION_RA3_RESEARCH_REPORT.md",
        "reports/stage3_g2_attempt3/STAGE_3_G2_A3_ROTATION_RESEARCH.json",
        "reports/stage3_g2_attempt3/STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json",
    ],
    "enforcement": d["adaptation_disclosure_carriage_requirement"]["enforcement"],
    "encoding_note": d["adaptation_disclosure_carriage_requirement"]["encoding_note"],
    "attempt_3_encoding_addendum": (
        "This attempt's string carries one character the Attempt 2 string did not: U+2212 MINUS "
        "SIGN, in the phrase naming the removed drawdown tier. It is stored as it appears in the "
        "source prose, for the same reason the em dashes are. A reader diffing the two strings "
        "for a hyphen will not find one and should not add one."
    ),
    "source": (
        "The Attempt 3 operating instruction, section 1, which requires this paragraph to be "
        "carried verbatim in the decision report and everywhere the development result is "
        "referenced."
    ),
}
out["what_makes_this_genuinely_cross_sectional"] = d["what_makes_this_genuinely_cross_sectional"]

# ------------------------------------------------- mechanics carried unchanged
for k in [
    "eligible_universe", "ranking_signal", "ranking_rule", "position_count",
    "rebalance", "execution", "position_sizing", "concentration_ceiling",
]:
    out[k] = copy.deepcopy(d[k])

out["mechanics_carried_unchanged"] = {
    "blocks": [
        "eligible_universe", "ranking_signal", "ranking_rule", "position_count", "rebalance",
        "execution", "position_sizing", "concentration_ceiling", "window", "run_span", "grid",
        "runs_per_variant", "gate_evaluation_scope",
    ],
    "method": (
        "Each block was copied from SE100-CFG-3103 programmatically, not retyped, so a "
        "transcription difference between the two attempts is impossible by construction. Only "
        "grid.variant_id_format and grid.variants[].variant_id differ, because a variant id "
        "encodes the candidate index and the architecture name."
    ),
    "why_this_matters": (
        "Attempt 3 changes two things. Any third difference, including an accidental one in a "
        "constant nobody re-read, would make the result uninterpretable."
    ),
}

# ---------------------------------------------------------------- RA3
ra2 = d["risk_architecture"]
ra2c = ra2["components"]

comp = {}
for old, new in [("RA2-1", "RA3-1"), ("RA2-2", "RA3-2"), ("RA2-3", "RA3-3"), ("RA2-5", "RA3-5")]:
    block = copy.deepcopy(ra2c[old])
    block["carriage"] = (
        "Copied verbatim from SE100-CFG-3103's %s. Prose inside it that says 'Attempt 2' or "
        "'%s' refers to the attempt and component the text was written for; the mechanism, its "
        "constants and its code path are inherited by %s unchanged and are not reimplemented. "
        "Runtime identifiers keep their original names for the same reason " % (old, old, new)
        + EM
        + " the clamp is still called AGGREGATE_RA2 in the engine because it is literally the "
        "same code, and renaming it would suggest a change that did not happen."
    )
    block["inherited_unchanged_from"] = old
    comp[new] = block

ladder = copy.deepcopy(ra2c["RA2-4"])
ladder["inherited_unchanged_from"] = None
ladder["derived_from"] = "RA2-4, with band 1 deleted and the remaining bands renumbered."
ladder["purpose"] = (
    "Staged exposure reduction as the drawdown from the equity high-water mark deepens, "
    "re-normalizing as the drawdown recovers. The one changed component of this attempt."
)
ladder["bands"] = [
    {"band": 0, "dd_from": "0.00", "dd_to_exclusive": "0.08", "scalar": "1.00"},
    {"band": 1, "dd_from": "0.08", "dd_to_exclusive": "0.10", "scalar": "0.50"},
    {"band": 2, "dd_from": "0.10", "dd_to_exclusive": None, "scalar": "0.25"},
]
ladder["boundary_convention"] = (
    "Each band is closed at its lower bound and open at its upper bound, so dd exactly equal to "
    "0.08 is band 1, not band 0. Stated because a threshold is a decision and an inequality "
    "direction chosen at implementation time is a free parameter. The convention is RA2-4's and "
    "is not re-chosen; only the threshold it applies to has moved."
)
ladder["recovery"] = (
    "At most one band per session, and only when the computed band is strictly below the "
    "current band AND the re-entry lockout of RA3-5 has elapsed. Recovery from band 2 to band 0 "
    "therefore requires at least two sessions after the lockout expires. RA2-4's ladder was one "
    "rung deeper and required at least three."
)
ladder["provenance"] = {
    "statement": (
        "RA3-4 is not a new ladder. It is Generation 1's sealed RA1-5 ladder, restored. "
        "SE100-CFG-3103's own provenance field records that three of RA2-4's four bands "
        "reproduce the RA1-5 f_cap values exactly and that 'only band 1 is new'. Deleting band 1 "
        "therefore leaves an architecture with no post-Attempt-1 degree of freedom in it at all."
    ),
    "quoted_from_attempt_2": ra2["provenance"],
    "absolute_ceilings": (
        "Expressed as absolute aggregate ceilings (f_base * ladder scalar), RA3-4's three bands "
        "give 0.500000000 for dd < 0.08, 0.250000000 for 0.08 <= dd < 0.10 and 0.125000000 for "
        "dd >= 0.10. Those are the three RA1-5 f_cap values SE100-CFG-3103 names, in the same "
        "order, at the same thresholds."
    ),
    "degrees_of_freedom_added_by_this_change": 0,
    "degrees_of_freedom_removed_by_this_change": (
        "One threshold (0.05) and one scalar (0.75) " + EM + " precisely the pair SE100-CFG-3103 "
        "identified as 'the single degree of freedom it adds'."
    ),
    "why_this_direction": (
        "The adaptation disclosure states the reasoning: a 5-percent-from-peak dip is common in "
        "ordinary markets, so a rung at 5 percent throttles ordinary conditions rather than "
        "crises. Attempt 2's own non-return evidence is consistent with that " + EM + " the "
        "combined scalar ran as low as 0.19 and the ladder descended over a thousand times "
        "across 36 runs " + EM + " but consistency is not proof, and no return figure was "
        "consulted in making the change."
    ),
    "what_would_falsify_the_reasoning": (
        "If RA3's ladder-descent counts are close to RA2's, the 5-percent rung was not the cause "
        "of the near-constant throttling and the change was aimed at the wrong mechanism. The "
        "descent counts are therefore reported per variant against Attempt 2's, and the "
        "comparison is required by the operating instruction rather than optional."
    ),
}
ladder["relationship_to_the_shutdown_threshold"] = {
    "statement": (
        "The deepest rung still fires at a 10 percent drawdown. The constitutional research "
        "shutdown fires at 15 percent, and Gate 3's max-drawdown condition S3-C2 is also 15 "
        "percent. The ladder remains entirely inside the threshold it is trying to keep the "
        "strategy away from, by construction. What has changed is the shallow end: RA3 holds "
        "full sizing across the whole of [0, 0.08), where RA2 throttled to 75 percent from 0.05."
    ),
    "consequence_for_the_gate": ra2c["RA2-4"]["relationship_to_the_shutdown_threshold"][
        "consequence_for_the_gate"
    ],
    "consequence_for_the_shutdown": (
        "Less exposure reduction on the way down means a shutdown breach is easier to reach than "
        "it was in Attempt 2. Attempt 1, with no ladder at all, tripped 36 of 36. Attempt 2, "
        "with four rungs, tripped 0 of 36. RA3 sits between them and the outcome is not "
        "predictable from either. See G2A3-CONFLICT-29."
    ),
    "conflict_refs": ["G2A2-CONFLICT-15", "G2A3-CONFLICT-22", "G2A3-CONFLICT-29"],
}
ladder["measurement"] = (
    "Per variant: the number of downward transitions (ladder descents), the number of upward "
    "transitions, the deepest band reached, the number of sessions spent in each band, and the "
    "number of sessions on which a recovery was computed but blocked by the lockout. All five "
    "are reported alongside Attempt 2's corresponding figures, and the descent count is one of "
    "SE100-G2-SEL-2's four inputs."
)
comp["RA3-4"] = ladder

out["risk_architecture"] = {
    "id": "RA3",
    "name": "Generation 2 Attempt 3 risk architecture",
    "frozen_before_any_variant_is_run": True,
    "not_part_of_the_grid": True,
    "derived_from": "RA2, by deleting one ladder band. Four of the five components are identical.",
    "why_not_gridded": ra2["why_not_gridded"],
    "single_difference_from_ra2": (
        "RA2-4's band 1 (0.05 <= dd < 0.08, scalar 0.75) is deleted and band 0 is extended to "
        "0.08. No other threshold, scalar, formula, order of operations or code path differs. "
        "The engine subclasses Attempt 2's and overrides the band table and the state derived "
        "from it; see G2A3-CONFLICT-31."
    ),
    "provenance": (
        "RA3-1, RA3-2, RA3-3 and RA3-5 are RA2-1, RA2-2, RA2-3 and RA2-5 unchanged, which are in "
        "turn the values of the Attempt 2 operating prompt and, for RA2-2 and RA2-3, of "
        "Generation 1's RA1. RA3-4 is Generation 1's RA1-5 ladder restored: see "
        "components.RA3-4.provenance, which quotes SE100-CFG-3103's own statement that only "
        "RA2-4's band 1 was new. Every constant in RA3 was therefore sealed before Attempt 1 ran."
    ),
    "components": comp,
    "combined_scalar": copy.deepcopy(ra2["combined_scalar"]),
    "state_ownership": copy.deepcopy(ra2["state_ownership"]),
}
out["risk_architecture"]["combined_scalar"]["range"] = (
    "(0, 1]. f(t) = 1 exactly when volatility is at or below target and the drawdown is below 8 "
    "percent. Under RA2 the second clause read 5 percent; the widening of that clause is the "
    "whole of this attempt's architectural change."
)
out["risk_architecture"]["state_ownership"]["owner"] = "The Attempt 3 engine subclass."
out["risk_architecture"]["state_ownership"][
    "no_generation_1_or_prior_attempt_file_is_edited"
] = (
    "The Attempt 3 engine subclasses the Attempt 2 RotationEngineRA1, which subclasses the "
    "Attempt 1 RotationEngine, which subclasses the frozen Generation 1 engine. Each layer "
    "overrides only its own methods. Nothing below Attempt 3 is modified, and all seventeen "
    "prior-attempt modules are re-hashed at seal time and again at package time."
)
out["risk_architecture"]["state_ownership"].pop(
    "no_generation_1_or_attempt_1_file_is_edited", None
)

# ---------------------------------------------------------------- window / span / grid
out["window"] = copy.deepcopy(d["window"])
out["run_span"] = copy.deepcopy(d["run_span"])
out["run_span"]["reverification_required"] = (
    "The span above is carried from Attempt 2 and must not be assumed. The Attempt 3 runner "
    "recomputes it from the loaded data before the first variant runs, asserts equality with "
    "every field recorded here, and writes the recomputation to "
    "reports/stage3_g2_attempt3/run_span_recheck.json. A mismatch is a blocker, not a value to "
    "adopt."
)

grid = copy.deepcopy(d["grid"])
fmt = "SE100-G2-S3-C3-ROTATION-RA3-L{lookback:02d}-K{k}-{FREQUENCY}"
grid["variant_id_format"] = fmt
grid["unchanged_from_attempt_1"] = True
grid["unchanged_from_attempt_2"] = True
for v in grid["variants"]:
    v["variant_id"] = fmt.format(
        lookback=v["lookback_months"], k=v["top_k"], FREQUENCY=v["rebalance_frequency"]
    )
grid["variant_id_change_note"] = (
    "Only the candidate index and architecture segment differ from Attempt 2's ids: "
    "C2-ROTATION-RA1 becomes C3-ROTATION-RA3. The axes, their orderings, the enumeration order, "
    "the zero padding, the target weights and the scheduled-rebalance counts are copied and "
    "unchanged, so variant n of Attempt 3 is the same parameterisation as variant n of Attempts "
    "1 and 2 and the three grids are directly comparable row by row."
)
out["grid"] = grid

out["runs_per_variant"] = copy.deepcopy(d["runs_per_variant"])

# ---------------------------------------------------------------- multiplicity
out["multiple_comparisons_disclosure"] = {
    "variants_this_attempt": 18,
    "runs_this_attempt": 36,
    "variants_attempt_1": 18,
    "runs_attempt_1": 36,
    "variants_attempt_2": 18,
    "runs_attempt_2": 36,
    "cumulative_variants_this_hypothesis_family": 54,
    "cumulative_runs_this_hypothesis_family": 108,
    "no_correction_applied": d["multiple_comparisons_disclosure"]["no_correction_applied"],
    "adaptive_design_note": (
        "The 54 cumulative variants are not 54 independent tests. Attempt 2's risk architecture "
        "was chosen after seeing where Attempt 1 broke; Attempt 3's ladder change and selection "
        "rule were chosen after seeing how Attempt 2 behaved. The effective number of researcher "
        "degrees of freedom is larger than 54 and grows faster than the variant count, because "
        "each attempt conditions on all preceding results. It is not quantified here because any "
        "quantification would itself be a choice made after the fact."
    ),
    "third_attempt_note": (
        "A third adaptation on one hypothesis family is the point at which a development PASS "
        "carries very little evidential weight on its own. This is stated before the run. See "
        "G2A3-CONFLICT-33."
    ),
    "statement": d["multiple_comparisons_disclosure"]["statement"],
}

# ---------------------------------------------------------------- SEL-2
out["representative_selection_rule"] = {
    "id": "SE100-G2-SEL-2",
    "frozen_before_any_variant_is_run": True,
    "return_blind": True,
    "unchanged_from_attempt_1": False,
    "unchanged_from_attempt_2": False,
    "replaces": (
        "The unnamed lowest-turnover rule of SE100-CFG-3103, which selected "
        "SE100-G2-S3-C2-ROTATION-RA1-L12-K1-QUARTERLY."
    ),
    "why_it_changes": (
        "Attempt 2's rule preferred the variant that traded least. On a grid where every variant "
        "survived the eligibility screen, 'traded least' selected the quarterly k=1 corner "
        + EM + " the parameterisation that by construction takes the fewest decisions and holds "
        "the fewest positions. Lowest turnover is a defensible tiebreak among near-equals and a "
        "poor primary criterion on a grid with no ties, because it is monotone in a structural "
        "property of the axes rather than in anything about the strategy's behaviour. SEL-2 "
        "prefers a variant whose immediate neighbours behave like it does, which is a stability "
        "criterion rather than a corner-seeking one. Turnover is retained as the tiebreak."
    ),
    "structural_enforcement": {
        "mechanism": (
            "The scoring function accepts a frozen SelectionInputV2 dataclass whose fields are "
            "exactly (variant_id, shutdown_events, fill_count, ladder_descents, lockout_arms, "
            "stops_filled). No return, drawdown, profit factor, Sharpe, trade-count or equity "
            "figure can reach it, because there is no field to carry one."
        ),
        "field_names": [
            "variant_id", "shutdown_events", "fill_count", "ladder_descents", "lockout_arms",
            "stops_filled",
        ],
        "import_time_assertion": (
            "The module asserts at import that the dataclass's actual field tuple equals the "
            "declared SELECTION_V2_FIELD_NAMES, in order. A field added later fails the import "
            "rather than silently widening what the selector can see. This is the same mechanism "
            "SE100-CFG-3103 required of Attempt 2's SelectionInput, extended to six fields."
        ),
        "frozen_dataclass": (
            "frozen=True, so a field cannot be reassigned between scoring and selection either."
        ),
        "what_is_still_excluded": (
            "Every performance quantity, without exception. What is newly admitted relative to "
            "Attempt 2 is three risk-behaviour counters, and they are admitted as dispersions "
            "across neighbours rather than as levels. See G2A3-CONFLICT-26, which records that "
            "Attempt 2 explicitly excluded two of them and does not pretend the change is "
            "continuity."
        ),
    },
    "steps": [
        {
            "order": 1,
            "criterion": "zero_research_shutdown_events",
            "scope": "across BOTH runs of the variant",
            "eliminates": "any variant with one or more shutdown events in either run",
            "unchanged_from_attempt_2": True,
        },
        {
            "order": 2,
            "criterion": "lowest_neighbourhood_instability_score",
            "neighbours": (
                "The immediate grid neighbours of a variant are the variants reachable by "
                "exactly one single-axis step: lookback one position up or down the ordered list "
                "[3, 6, 12], k one position up or down the ordered list [1, 2, 3], and the "
                "rebalance frequency flipped. Every other axis value is held equal."
            ),
            "neighbour_counts": (
                "3, 4 or 5. The frequency axis has two values, so it contributes exactly one "
                "neighbour to every variant with no edge case. The lookback and k axes have "
                "three ordered values each and contribute one neighbour at an end and two in the "
                "middle. A variant at an end of both ordered axes has 1+1+1 = 3; at an end of one "
                "of them, 1+2+1 = 4; at the middle of both, 2+2+1 = 5. Over the eighteen "
                "variants the partition is 8 with three neighbours, 8 with four, and 2 with five."
            ),
            "neighbour_counts_provenance": (
                "The 8/8/2 partition was computed by enumerating the sealed grid, not counted by "
                "hand: 2 end values on the lookback axis times 2 end values on the k axis times "
                "2 frequencies is 8 variants at an end of both ordered axes, 1 middle lookback "
                "times 1 middle k times 2 frequencies is 2 at the middle of both, and the "
                "remaining 8 are at an end of exactly one. A hand count of this partition was "
                "wrong on the first pass, which is why the build asserts it."
            ),
            "symmetry": (
                "The neighbour relation is symmetric: b is a neighbour of a if and only if a is "
                "a neighbour of b. Asserted over all eighteen variants at build time and again "
                "in AT-J."
            ),
            "neighbour_count_conflict": (
                "The operating instruction describes this as 'up to 4 neighbours' with corner=2, "
                "edge=3, interior=4. That is the count for a two-axis grid and omits the "
                "frequency axis, which the same instruction lists as a one-step change. Adding "
                "the frequency neighbour to each of the instruction's figures gives exactly 3, 4 "
                "and 5. The sealed counts are 3/4/5. See G2A3-CONFLICT-27 in SE100-CFG-3106."
            ),
            "quantities": ["fill_count", "ladder_descents", "lockout_arms", "stops_filled"],
            "quantity_basis": (
                "Each quantity is summed across the variant's two runs (#BASE and #STRESS) "
                "before any comparison, so a variant contributes one integer per quantity."
            ),
            "per_pair_dissimilarity": "abs(a - b) / max(abs(a), abs(b), 1)",
            "score": (
                "The arithmetic mean of the per-pair dissimilarity over all (neighbour, "
                "quantity) pairs: sum over neighbours, sum over the four quantities, divided by "
                "4 * len(neighbours). Lower is preferred."
            ),
            "arithmetic": (
                "Computed in Decimal under the sealed ENGINE_CONTEXT and quantized to nine "
                "decimal places, ROUND_HALF_EVEN, so the score is reproducible and comparable "
                "without float drift. The inputs are integers, so the only inexactness is the "
                "division."
            ),
            "denominator_floor_note": (
                "The max(..., 1) term means a quantity that is zero for both a variant and its "
                "neighbour contributes 0, reading as perfect stability where in fact nothing "
                "fired. The formula is sealed as the instruction specifies it and is not "
                "repaired; the per-quantity contributions are reported per variant so a reader "
                "can see how much of a low score is agreement and how much is absence. See "
                "G2A3-CONFLICT-32 in SE100-CFG-3106."
            ),
            "eligibility_of_neighbours": (
                "Neighbours are structural, not filtered by eligibility. A variant's score uses "
                "all of its grid neighbours whether or not those neighbours passed the "
                "shutdown screen, because the score measures the smoothness of the parameter "
                "region and an ineligible neighbour is part of that region. Only the variant "
                "being scored must itself be eligible to be selectable."
            ),
        },
        {
            "order": 3,
            "criterion": "lowest_turnover",
            "definition": "total fill count across both runs",
            "role_change": (
                "Attempt 2's primary criterion becomes Attempt 3's tiebreak. Its rationale is "
                "unchanged and is carried from SE100-CFG-3103: gross notional traded is a "
                "partial return proxy and fill count is not."
            ),
        },
        {
            "order": 4,
            "criterion": "lexicographic_variant_id",
            "purpose": "A total order. Reached only if two variants tie on all criteria above.",
        },
    ],
    "retrospective_check_disclosure": {
        "statement": (
            "SEL-2 was checked against Attempt 2's frozen recorded statistics before being "
            "sealed, to confirm it computes and produces a total order on real data rather than "
            "only on fixtures."
        ),
        "what_the_check_did_not_do": (
            "It did not compare the variant SEL-2 would have chosen in Attempt 2 against that "
            "variant's return, drawdown or profit factor, and no such comparison informed the "
            "rule. The adaptation disclosure states this as 'a retrospective (but not "
            "selection-informing) check'."
        ),
        "why_disclosed": (
            "A rule tested on the data of a prior attempt is not fully independent of it, "
            "however narrow the test. Saying so is cheaper than defending it later."
        ),
    },
    "no_candidate_path": {
        "condition": (
            "If all eighteen variants record at least one research-shutdown event, no variant is "
            "eligible and no representative exists."
        ),
        "verdict": "FAIL - STAGE_3_G2_ATTEMPT_3_NO_CANDIDATE",
        "attempt_closes": (
            "The attempt closes. No Attempt 4 is authorized by this file, and no Attempt 4 may "
            "be opened without a further disclosed adaptation and a separate authorization."
        ),
        "live_possibility_note": (
            "This route is materially more likely under RA3 than under RA2, because RA3 removes "
            "a rung. See G2A3-CONFLICT-29."
        ),
    },
    "second_fail_path": {
        "condition": (
            "If a representative is selected and then fails one or more Gate 3 conditions."
        ),
        "verdict": "FAIL - STAGE_3_G2_ATTEMPT_3_NO_CANDIDATE",
        "same_token_note": (
            "The same FAIL token is emitted on both fail routes. The routes are distinguished in "
            "the decision record's gate conditions and in the report prose, not in the token. "
            "Carried from Attempt 1's G2-CONFLICT-11 through Attempt 2's G2A2-CONFLICT-9. See "
            "G2A3-CONFLICT-36."
        ),
        "runner_up_not_promoted": d["representative_selection_rule"]["second_fail_path"][
            "runner_up_not_promoted"
        ],
        "conflict_ref": "G2A3-CONFLICT-36",
    },
    "no_reselection": d["representative_selection_rule"]["no_reselection"],
}

out["gate_evaluation_scope"] = copy.deepcopy(d["gate_evaluation_scope"])
out["gate_evaluation_scope"]["criteria_source"] = "config/generation_2/g2_gate_criteria_ra3.json"
out["gate_evaluation_scope"]["thresholds_changed_from_attempt_2"] = "none"

# ---------------------------------------------------------------- reporting
out["reported_for_every_variant_but_not_gating"] = list(
    d["reported_for_every_variant_but_not_gating"]
) + [
    "The SE100-G2-SEL-2 stability score, its four per-quantity components, and the identity and "
    "score of every neighbour used to compute it.",
    "The Attempt 2 counterpart of each ladder, lockout and stop statistic, so the required "
    "comparison is on the same page as the figure it compares.",
]

# ---------------------------------------------------------------- SC
sc = copy.deepcopy(d["structural_consequences_declared_before_running"])
sc["SC-1"]["attempt_3_amendment"] = (
    "Unchanged in kind from Attempt 2. The stop and the throttle still close positions, so the "
    "closed-trade count is still not bounded by the rebalance count. RA3 throttles less, so "
    "fewer of the additional trades come from the ladder and more of the exposure is left in "
    "place; the direction of the effect on trade count is not predictable and is measured."
)
sc["SC-2"]["attempt_3_amendment"] = (
    "The margin is wider than Attempt 2's at shallow drawdowns, because the combined scalar is "
    "1 rather than 0.75 across [0.05, 0.08), and identical to Attempt 2's at 0.08 and beyond. "
    "MIN_NOTIONAL and ZERO_QUANTITY rejections are still counted and reported."
)
sc["SC-4"]["attempt_3_amendment"] = (
    "Turnover is no longer the primary selection criterion, so the objection SC-4 raised against "
    "it " + EM + " that it partly measures how often the risk architecture intervened " + EM + " "
    "now bites only on the tiebreak. It is not thereby resolved: fill_count is also one of "
    "SEL-2's four stability quantities, where the same objection applies to its dispersion "
    "rather than its level. See G2A3-CONFLICT-26."
)
sc["SC-6"]["statement"] = (
    "The risk architecture reduces exposure and can only reduce it. Every one of RA3-1, RA3-2, "
    "RA3-4 and RA3-5 scales sizing down or holds it, and RA3-3 exits."
)
sc["SC-6"]["attempt_3_amendment"] = (
    "RA3 reduces exposure strictly less than RA2 did, and never more. At every session the "
    "RA3 combined scalar is greater than or equal to the RA2 scalar for the same drawdown, with "
    "equality outside [0.05, 0.08). Mechanically this raises both the expected return and the "
    "expected drawdown relative to Attempt 2. A FAIL on net return remains a predictable "
    "consequence of an architecture that halves exposure, and a PASS on net return that arrives "
    "together with a materially larger drawdown is the architecture being paid for, not the "
    "signal being better."
)
sc["SC-7"] = {
    "statement": (
        "SE100-G2-SEL-2 scores a variant using four quantities the risk architecture produces: "
        "ladder descents, lockout arms, stop fills and total fills. On a grid where the "
        "architecture rarely engages, three of the four are small integers and the score is "
        "dominated by fill_count."
    ),
    "consequence": (
        "If RA3 turns out to engage rarely, SEL-2 degenerates toward a fill-count dispersion "
        "rule and is closer to Attempt 2's turnover rule than its description suggests. The "
        "per-quantity components are reported so this is visible in the evidence rather than "
        "inferred."
    ),
    "not_corrected": (
        "The rule is not reweighted to compensate. It is sealed before the run and the "
        "degenerate case is declared before the run."
    ),
}
sc["SC-8"] = {
    "statement": (
        "RA3 holds full sizing across the whole of [0, 0.08) drawdown, where RA2 throttled to 75 "
        "percent from 0.05."
    ),
    "consequence": (
        "Every drawdown episode that reached 5 percent but not 8 percent " + EM + " which on "
        "thirteen years of equity-index history is the common case " + EM + " is now traversed "
        "at full sizing. This is the intended effect. It also means the maximum drawdown "
        "condition S3-C2 is under more pressure than in Attempt 2, and the research shutdown is "
        "closer than it was."
    ),
    "why_declared_now": (
        "So that a larger drawdown under RA3 is read as the declared cost of the change and not "
        "as a defect, and so that a S3-C2 failure cannot be presented afterwards as unforeseen."
    ),
}
out["structural_consequences_declared_before_running"] = sc

# ---------------------------------------------------------------- reproducibility
rep = copy.deepcopy(d["reproducibility_requirements"])
rep["risk_state_trace_digest"] = (
    "As Attempt 2: a SHA-256 over the per-session risk state (band, lockout counter, volatility "
    "scalar, combined scalar) in session order, recorded in addition to the ranking digest. "
    "Under RA3 the band alphabet is {0, 1, 2} rather than {0, 1, 2, 3}, so an Attempt 3 trace "
    "digest is not comparable with an Attempt 2 trace digest and neither is expected to equal "
    "the other."
)
rep["selection_determinism"] = (
    "SE100-G2-SEL-2 must produce identical scores, identical per-quantity components, identical "
    "neighbour sets and an identical selected variant on a clean rerun from the same recorded "
    "statistics. This is tested directly against the recorded selection inputs, not only "
    "end-to-end, so a determinism failure in the selector cannot hide behind a determinism pass "
    "in the engine."
)
out["reproducibility_requirements"] = rep

# ---------------------------------------------------------------- tests
at = copy.deepcopy(d["adversarial_test_requirements"])
at["AT-D"] = (
    "The de-risk ladder steps down at the declared RA3 thresholds and back up only after the "
    "declared recovery condition, verified against a hand-constructed drawdown-and-recovery "
    "fixture that visits every band in both directions. The fixture must include a drawdown that "
    "reaches 6 percent and assert that the combined ladder scalar is exactly 1 there, which is "
    "the single behavioural difference from RA2 and would otherwise be tested only by absence."
)
at["AT-G"] = (
    "The Generation 2 window guard still blocks any read at or after 2021-08-01, exercised "
    "through the Attempt 3 loading path. The guard is reused, not reimplemented, and the test "
    "asserts that the module under test is the existing g2_window_guard."
)
at["AT-H"] = (
    "No Generation 1, Attempt 1 or Attempt 2 module is modified: every one of the seventeen "
    "modules listed in prior_attempt_modules_immutable re-hashes to its recorded digest."
)
at["AT-I"] = (
    "The selection input cannot carry a performance figure: the SelectionInputV2 field tuple "
    "equals SELECTION_V2_FIELD_NAMES and the import-time assertion fires when it does not. The "
    "test also asserts that no field name matches a performance vocabulary "
    "(return, pnl, profit, drawdown, sharpe, equity, ratio, factor), so a future field named "
    "plausibly rather than obviously is also caught."
)
at["AT-J"] = (
    "Neighbour identification is correct at the grid edges: the neighbour counts are 3, 4 and 5, "
    "the partition over the eighteen variants is 8 / 8 / 2, and at least one variant of each "
    "class has its full neighbour set written out as a literal in the test and compared element "
    "by element against the computed set. The relation is also asserted symmetric, and asserted "
    "to contain no variant outside the grid and never the variant itself."
)
at["AT-K"] = (
    "SE100-G2-SEL-2 is deterministic: identical recorded statistics produce identical scores, "
    "identical component breakdowns and an identical selected variant across two independent "
    "computations in the same process and one from a round-trip through the serialised "
    "selection inputs."
)
at["AT-L"] = (
    "The RA3 band table is the sealed one and contains no band boundary below 0.08: the loaded "
    "architecture has exactly three bands, its scalars are strictly decreasing in (0, 1], its "
    "first band starts at 0.00 with scalar 1.00, its last band is open-ended, and the absolute "
    "aggregate ceilings it induces equal 0.500000000 / 0.250000000 / 0.125000000."
)
at["AT-M"] = (
    "The RA3 engine re-derives exactly the risk-dependent attributes it must after calling "
    "super().__init__, verified by parsing the Attempt 2 engine's __init__ for the attributes "
    "assigned from self.risk and asserting the RA3 subclass reassigns precisely that set. This "
    "is the same AST mechanism Attempt 2 used against Attempt 1's __init__."
)
out["adversarial_test_requirements"] = at

# ---------------------------------------------------------------- conflicts
INHERIT = ["G2A2-CONFLICT-%d" % n for n in (1, 2, 4, 5, 7, 11, 12, 13, 14, 16, 17)]
by_id = {c["id"]: c for c in d["conflicts_found"]}
conflicts = []
for cid in INHERIT:
    c = copy.deepcopy(by_id[cid])
    c["carried_from"] = (
        "SE100-CFG-3103, copied verbatim. The mechanism it describes is inherited by Attempt 3 "
        "unchanged, so the conflict is inherited unchanged and keeps its original id."
    )
    conflicts.append(c)

conflicts.append({
    "id": "G2A3-CONFLICT-34",
    "supersedes_in_scope": (
        "G2A2-CONFLICT-3, which declared a content-based contamination predicate over Attempt "
        "1's nine modules and is not edited."
    ),
    "summary": (
        "The paired immutability check must now cover seventeen modules, not nine: Attempt 2's "
        "eight became immutable when Attempt 2 closed, and a check that still counted nine would "
        "pass while an Attempt 2 module was being rewritten."
    ),
    "resolution": (
        "prior_attempt_modules_immutable enumerates both lists separately and declares the total. "
        "The Attempt 3 sealer refuses to seal unless it measures seventeen, and the count is a "
        "literal in the sealer so a silently shortened list fails loudly rather than quietly."
    ),
    "see": "prior_attempt_modules_immutable, declared_before_any_strategy_code_measurement",
})
conflicts.append({
    "id": "G2A3-CONFLICT-35",
    "supersedes_in_scope": (
        "G2A2-CONFLICT-6, which disclosed that Attempt 2's pre-registration was written after "
        "Attempt 1's results were known, and is not edited."
    ),
    "summary": (
        "This pre-registration was written after TWO attempts' development results were known, "
        "and both of its changes were chosen in response to the second. Pre-registration "
        "constrains what happens after this file is sealed; it cannot undo what was known before."
    ),
    "resolution": (
        "The adaptation is disclosed in adaptation_disclosure_verbatim, which is carried byte "
        "for byte into five artifacts and enforced by both the sealer and the package builder. "
        "The multiplicity is disclosed as 54 variants and 108 runs with an explicit statement "
        "that the effective degrees of freedom exceed the count. No threshold is adjusted in "
        "either direction to compensate."
    ),
    "see": "adaptation_disclosure_verbatim, multiple_comparisons_disclosure, G2A3-CONFLICT-33",
})
conflicts.append({
    "id": "G2A3-CONFLICT-36",
    "supersedes_in_scope": (
        "G2A2-CONFLICT-9, which recorded the same collision for Attempt 2's token and is not "
        "edited."
    ),
    "summary": (
        "Both fail routes " + EM + " no eligible representative, and a representative that fails "
        "the gate " + EM + " emit the same token, STAGE_3_G2_ATTEMPT_3_NO_CANDIDATE, although "
        "they are different findings. Under RA3 the two routes are also more nearly equally "
        "likely than they were in Attempt 2, where the first was effectively closed."
    ),
    "resolution": (
        "The route is recorded as an explicit fail_route field in the verdict record, in the "
        "gate conditions and in the report prose. The token is not split, because the token "
        "vocabulary is sealed in SE100-CFG-3106 and minting a third would be a stage inventing "
        "its own verdict space."
    ),
    "see": "representative_selection_rule.no_candidate_path, .second_fail_path",
})
conflicts.append({
    "id": "G2A3-CONFLICT-37",
    "supersedes_in_scope": (
        "G2A2-CONFLICT-8, which recorded that the Attempt 2 operating prompt named verdict "
        "tokens existing in no artifact, and is not edited."
    ),
    "summary": (
        "The Attempt 3 operating instruction names no verdict token at all. It requires a token "
        "'of your own derivation' and directs that the sealed criteria file be grepped for the "
        "actual strings rather than inventing one from the prompt."
    ),
    "resolution": (
        "There is no prompt string to conflict with, so the tokens are minted once, in "
        "SE100-CFG-3106's verdict_token_derivation, and every other artifact reads them from "
        "there. This is the first attempt in which the prompt and the sealed derivation cannot "
        "disagree, which removes the failure mode G2A2-CONFLICT-8 described rather than "
        "resolving it a second time. The four tokens belonging to Attempts 1 and 2 are read from "
        "those attempts' own files and asserted absent from every Attempt 3 verdict field."
    ),
    "see": "SE100-CFG-3106 verdict_token_derivation, G2A3-CONFLICT-21",
})

out["conflicts_found"] = conflicts
out["conflicts_declared_in_the_gate_criteria"] = {
    "note": (
        "The Attempt 3 conflict numbering is one space shared by this file and "
        "SE100-CFG-3106, exactly as Attempt 2's was shared by SE100-CFG-3103 and "
        "SE100-CFG-3104. Ids 18 to 25 were taken by Attempt 2's criteria file; ids 26 to 33 are "
        "taken by Attempt 3's criteria file; this file takes 34 onward. Nothing is duplicated "
        "across the two files, so the two cannot drift into disagreeing versions of one conflict."
    ),
    "declared_in_g2_gate_criteria_ra3": [
        "G2A3-CONFLICT-19", "G2A3-CONFLICT-21", "G2A3-CONFLICT-22", "G2A3-CONFLICT-24",
        "G2A3-CONFLICT-26", "G2A3-CONFLICT-27", "G2A3-CONFLICT-28", "G2A3-CONFLICT-29",
        "G2A3-CONFLICT-30", "G2A3-CONFLICT-31", "G2A3-CONFLICT-32", "G2A3-CONFLICT-33",
    ],
    "inherited_and_restated_in_g2_gate_criteria_ra3": [
        "S3-CONFLICT-1", "S3-CONFLICT-3", "G2-CONFLICT-6", "G2-CONFLICT-7", "G2-CONFLICT-15",
        "G2A2-CONFLICT-18", "G2A2-CONFLICT-20", "G2A2-CONFLICT-23", "G2A2-CONFLICT-25",
    ],
}

out["post_seal_defect_rule"] = {
    "rule": d["post_seal_defect_rule"]["rule"],
    "applies_equally_to": (
        "Every Generation 1 artifact, every Generation 2 Attempt 1 artifact, every Generation 2 "
        "Attempt 2 artifact, and this one."
    ),
}

nona = list(d["explicit_non_authorizations"])
nona = [
    s.replace(
        "This file does not authorize an Attempt 3. If Attempt 2 fails, the attempt closes and "
        "any further work requires a further disclosed adaptation and a separate authorization.",
        "This file does not authorize an Attempt 4. If Attempt 3 fails, the attempt closes and "
        "any further work requires a further disclosed adaptation and a separate authorization. "
        "SE100-CFG-3103 said the same of Attempt 3; see G2A3-CONFLICT-28, which records that "
        "this attempt exists on a separate authorization and not on SE100-CFG-3103's.",
    ).replace(
        "This file does not authorize grid-searching, tuning or adjusting any RA2 constant, "
        "before or after seeing a result.",
        "This file does not authorize grid-searching, tuning or adjusting any RA3 constant, or "
        "any SE100-G2-SEL-2 quantity, weight or threshold, before or after seeing a result.",
    )
    for s in nona
]
nona.insert(
    8,
    "This file does not authorize editing, deleting, re-running, reopening or loosening any "
    "Generation 2 Attempt 2 artifact or module. Attempt 2's verdict stands permanently.",
)
nona.append(
    "This file does not authorize a fourth selection rule, a reweighting of SE100-G2-SEL-2's "
    "four quantities, or the addition of a fifth, at any point after this file is sealed."
)
nona.append(
    "This file does not authorize isolating the two changes by re-running either of them alone. "
    "An isolation attempt is a further attempt and requires its own authorization and its own "
    "disclosure of the multiplicity it adds."
)
out["explicit_non_authorizations"] = nona
out["live_trading_authorized"] = False

# The two .replace() calls above are silent no-ops if the sealed wording differs by one
# character. Assert they fired, and that no Attempt-2-era phrasing survived.
_blob = "\n".join(nona)
assert "does not authorize an Attempt 4" in _blob, "bullet 12 replacement did not fire"
assert "does not authorize an Attempt 3" not in _blob, "Attempt 2 wording survived"
assert "adjusting any RA3 constant" in _blob, "RA2-constant replacement did not fire"
assert "any RA2 constant" not in _blob, "RA2-constant wording survived"
assert "Attempt 2 artifact or module" in _blob
assert len(nona) == len(d["explicit_non_authorizations"]) + 3, len(nona)

# ---------------------------------------------------------------- checks
assert out["live_trading_authorized"] is False
bands = out["risk_architecture"]["components"]["RA3-4"]["bands"]
assert len(bands) == 3, bands
assert bands[0]["dd_from"] == "0.00" and bands[0]["scalar"] == "1.00"
assert bands[0]["dd_to_exclusive"] == "0.08"
assert bands[-1]["dd_to_exclusive"] is None
from decimal import Decimal
for a, b in zip(bands, bands[1:]):
    assert a["dd_to_exclusive"] == b["dd_from"], (a, b)
    assert Decimal(a["scalar"]) > Decimal(b["scalar"])
assert not any(Decimal(b["dd_from"]) < Decimal("0.08") and b["band"] > 0 for b in bands)
assert Decimal(bands[-1]["dd_from"]) < Decimal("0.15")
ids = [v["variant_id"] for v in out["grid"]["variants"]]
assert len(ids) == 18 and len(set(ids)) == 18
assert all(i.startswith("SE100-G2-S3-C3-ROTATION-RA3-L") for i in ids)

# The neighbour partition claimed in representative_selection_rule is computed here from the
# sealed axes, not trusted from the prose. A hand count of it was wrong once.
import collections
_ax = out["grid"]["axes"]
_LB, _K, _F = _ax["lookback_months"], _ax["top_k"], _ax["rebalance_frequency"]
assert (_LB, _K, _F) == ([3, 6, 12], [1, 2, 3], ["MONTHLY", "QUARTERLY"]), _ax
_key = lambda v: (v["lookback_months"], v["top_k"], v["rebalance_frequency"])
_idx = {_key(v): v for v in out["grid"]["variants"]}
assert len(_idx) == 18


def _nb(t):
    lb, k, f = t
    r = []
    for axis, vals, pos in ((0, _LB, lb), (1, _K, k)):
        i = vals.index(pos)
        for j in (i - 1, i + 1):
            if 0 <= j < len(vals):
                r.append((vals[j], k, f) if axis == 0 else (lb, vals[j], f))
    r.append((lb, k, _F[1 - _F.index(f)]))
    return r


_counts = collections.Counter()
_nbs = {}
for _t in _idx:
    _n = _nb(_t)
    assert len(set(_n)) == len(_n) and _t not in _n
    assert all(x in _idx for x in _n)
    _nbs[_t] = set(_n)
    _counts[len(_n)] += 1
for _a, _ns in _nbs.items():
    for _b in _ns:
        assert _a in _nbs[_b], (_a, _b)
assert dict(_counts) == {3: 8, 4: 8, 5: 2}, dict(_counts)
_step = out["representative_selection_rule"]["steps"][1]
assert "8 with three neighbours, 8 with four, and 2 with five" in _step["neighbour_counts"]
assert "8/8/2" in _step["neighbour_counts_provenance"]
assert "8 / 8 / 2" in out["adversarial_test_requirements"]["AT-J"]
assert len(out["prior_attempt_modules_immutable"]["attempt_1_modules"]) == 9
assert len(out["prior_attempt_modules_immutable"]["attempt_2_modules"]) == 8
sel = out["representative_selection_rule"]["structural_enforcement"]["field_names"]
assert sel == ["variant_id", "shutdown_events", "fill_count", "ladder_descents",
               "lockout_arms", "stops_filled"], sel
BANNED = ("return", "pnl", "profit", "drawdown", "sharpe", "equity", "ratio", "factor")
assert not any(any(w in f for w in BANNED) for f in sel)
disc = out["adaptation_disclosure_verbatim"]
assert disc.count(EM) == 3 and disc.count(MINUS) == 1
DISC_SHA = hashlib.sha256(disc.encode("utf-8")).hexdigest()
assert "-5%" not in disc and disc.startswith("This pre-registration was designed after both")
assert disc.rstrip().endswith("in any final assessment of this family.")
assert STRATEGY_ID not in json.dumps(out["attempt_1_ref"])
assert out["multiple_comparisons_disclosure"]["cumulative_variants_this_hypothesis_family"] == 54
assert out["multiple_comparisons_disclosure"]["cumulative_runs_this_hypothesis_family"] == 108
seen = set()
for c in out["conflicts_found"]:
    assert c["id"] not in seen, c["id"]
    seen.add(c["id"])
cross = set(out["conflicts_declared_in_the_gate_criteria"]["declared_in_g2_gate_criteria_ra3"])
assert not (seen & cross), seen & cross

if "--write" in sys.argv:
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
                   newline="\n")
    print("WROTE", OUT, sha256(OUT.relative_to(ROOT).as_posix()))
else:
    print("DRY RUN ok. top-level keys:", len(out))
    print("bands:", json.dumps(bands))
    print("variant[0]:", ids[0], "| variant[17]:", ids[17])
    print("conflicts:", [c["id"] for c in out["conflicts_found"]])
    print("non_authorizations:", len(nona))
    print("disclosure len:", len(disc), "| em:", disc.count(EM), "| minus:", disc.count(MINUS))
    print("disclosure sha256:", DISC_SHA)
    print("disclosure words:", len(disc.split()))
    print("bytes if written:", len(json.dumps(out, indent=2, ensure_ascii=False)) + 1)
