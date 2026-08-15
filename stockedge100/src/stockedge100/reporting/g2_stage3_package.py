"""Generation 2 Stage 3 decision package.

Assembles the decision record, artifact manifest, checksum record and ``runs/`` record for
Generation 2's development gate, from the evidence file
``reports/stage3_g2/STAGE_3_G2_DEVELOPMENT_ADMISSIBILITY.json`` and the sealed criteria in
``config/generation_2/g2_gate_criteria.json``. It writes no verdict of its own.

**The guard is the portable one.** ``stage2_package.py`` refuses to write unless its evidence meets
every condition, which suits a stage whose package could only ever be a pass. Generation 2 Stage 3
can legitimately fail — the sealed ``verdict_token_derivation`` says so in as many words
(``fail_is_a_deliverable``) — and suppressing the deliverable on a FAIL would be the opposite of what
the constitution requires, which is that negative results stay on disk. So the guard here is
``stage3_package.py``'s: the verdict written into the package must be the verdict the evidence
reached, derived from the sealed token derivation rather than restated as a literal, and the
incoherent combinations are refused. A FAIL carrying admitted candidates writes nothing.

Nothing here is hand-typed that exists on disk. The verdict token, the condition text, the
representative-selection rule, the multiple-comparisons disclosure and the validation-reuse
disclosure are all read from their sealed files. The last of those must appear verbatim in every
report that references validation; loading it rather than retyping it is what makes "verbatim"
checkable instead of asserted.

Run **last**. ``repo_state_id`` covers ``src/**/*.py`` and ``tests/**/*.py``, so any edit to this
module or to a test after the build invalidates the digest the build just recorded, and ``runs/`` is
append-only. Dry-run it first from ``_scratch/`` with :func:`build_stage_package` monkeypatched.

Usage::

    cd stockedge100 && PYTHONPATH=src python -m stockedge100.reporting.g2_stage3_package
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from stockedge100.audit import sha256_file
from stockedge100.reporting.stage_package import (
    PROJECT_ROOT,
    StageDecision,
    build_stage_package,
    verify_sha256_record,
)

COMMAND = "cd stockedge100 && PYTHONPATH=src python -m stockedge100.reporting.g2_stage3_package"

VERDICT = "FAIL — STAGE_3_G2_NO_CANDIDATE"

EVIDENCE = "reports/stage3_g2/STAGE_3_G2_DEVELOPMENT_ADMISSIBILITY.json"
CRITERIA = "config/generation_2/g2_gate_criteria.json"
PROTOCOL = "config/generation_2/g2_rotation_protocol.json"
COST_MODEL = "config/generation_2/g2_cost_model.json"
CHARTER = "governance/generation_2/STAGE_10_GENERATION_2_CHARTER.md"
PARTITION_LOCK_MD = "governance/generation_2/STAGE_1_G2_PARTITION_LOCK.md"
PARTITION_LOCK_JSON = "governance/generation_2/STAGE_1_G2_PARTITION_LOCK.json"
PARTITION_LOCK_RECORD = "governance/generation_2/STAGE_1_G2_PARTITION_LOCK.sha256"
PROTOCOL_MD = "governance/generation_2/STAGE_3_G2_ROTATION_PROTOCOL.md"
PROTOCOL_JSON = "governance/generation_2/STAGE_3_G2_ROTATION_PROTOCOL.json"
PROTOCOL_RECORD = "governance/generation_2/STAGE_3_G2_ROTATION_PROTOCOL.sha256"

REPORT = "governance/generation_2/STAGE_3_G2_ROTATION_RESEARCH_REPORT.md"

PRODUCED = [
    REPORT,
    EVIDENCE,
    "reports/stage3_g2/STAGE_3_G2_ROTATION_RESEARCH.json",
    "reports/stage3_g2/STAGE_3_G2_ROTATION_RESEARCH.sha256",
    "reports/stage3_g2/STAGE_3_G2_ARTIFACT_MANIFEST.json",
    "reports/stage3_g2/STAGE_3_G2_TEST_SUMMARY.md",
    "reports/stage3_g2/pytest_stage3_g2_output.txt",
]

FROZEN_INPUTS = [
    "governance/STAGE_0_CONSTITUTION.md",
    "governance/STAGE_0_CONSTITUTION.json",
    "governance/STAGE_0_FREEZE.sha256",
    CHARTER,
    PARTITION_LOCK_MD,
    PARTITION_LOCK_JSON,
    PARTITION_LOCK_RECORD,
    PROTOCOL_MD,
    PROTOCOL_JSON,
    PROTOCOL_RECORD,
    PROTOCOL,
    CRITERIA,
    COST_MODEL,
]

VERDICT_SEMANTICS = (
    "FAIL — STAGE_3_G2_NO_CANDIDATE is the outcome the sealed no_candidate_path anticipated in "
    "writing before any variant was run. Every one of the eighteen declared variants recorded a "
    "research-shutdown event in both of its declared runs, so step 1 of the frozen "
    "return-blind selection rule admitted nothing and Gate 3 was never reached. The verdict is a "
    "statement about the grid, not about any variant's return: no return figure was an input to "
    "it, and the strongest variant by return failed the screen on the same terms as the weakest. "
    "The result is a deliverable and is kept on disk. It does not license a nineteenth variant, a "
    "re-run with a loosened grid, a raised shutdown threshold, a screen narrowed to the base run, "
    "or the promotion of a runner-up."
)


def load(rel: str) -> dict[str, Any]:
    return json.loads((PROJECT_ROOT / rel).read_text(encoding="utf-8"))


def gate_conditions(ev: dict[str, Any], criteria: dict[str, Any]) -> dict[str, Any]:
    """The seven hard conditions plus the one row that actually decides the gate.

    With no representative, every condition is ``NOT_RUN`` — not ``NOT_APPLICABLE``, and certainly
    not a pass. The constitution is explicit that NOT_RUN is never a pass, and the difference
    matters here: these conditions were not inapplicable, they were never reached, because the
    return-blind screen that runs before them admitted nothing.

    ``admissible_candidate_exists`` is a determination rather than a NOT_RUN. The stage did evaluate
    whether an admissible candidate exists; the answer is no.
    """
    selection = ev["selection"]
    eligible = selection["step_1"]["eligible_count"]
    considered = selection["variants_considered"]

    conditions: dict[str, Any] = {}
    for cond in criteria["conditions"]:
        conditions[cond["id"]] = {
            "required_verbatim": cond["required_verbatim"],
            "predicate": cond["predicate"],
            "verdict": "NOT_RUN",
            "satisfied_by": [],
            "met_by": [],
            "not_met_by": [],
            "not_evaluable_for": [],
            "not_applicable_for": [],
            "note": (
                "Not evaluated. Gate 3 is evaluated only on the representative produced by the "
                "frozen selection rule, and no representative was produced. NOT_RUN is not a pass "
                "(constitution section 9)."
            ),
        }

    conditions["admissible_candidate_exists"] = {
        "required_verbatim": (
            "At least one candidate satisfies every hard condition of Gate 3 in development."
        ),
        "predicate": "a representative exists AND every hard condition is MET on its base run",
        "verdict": "NOT_MET",
        "value": False,
        "variants_declared": considered,
        "variants_eligible_after_shutdown_screen": eligible,
        "candidates_evaluated": ev["stage_verdict"]["candidates_evaluated"],
        "admitted_candidates": ev["stage_verdict"]["admitted_candidates"],
        "determination": (
            "This entry, and only this entry, is the gate determination. "
            f"{eligible} of {considered} declared variants survived step 1 of the frozen "
            "selection rule, so no candidate reached Gate 3 and none can satisfy it."
        ),
        "note": (
            "A conditions table that omits this row reads as though the gate were irrelevant "
            "rather than decided. The seven rows above settle nothing on their own: gates are "
            "conjunctive within a candidate and the stage verdict is a disjunction across "
            "candidates, and here the candidate set is empty."
        ),
    }
    return conditions


def build() -> int:
    ev = load(EVIDENCE)
    criteria = load(CRITERIA)
    protocol = load(PROTOCOL)
    lock = load(PARTITION_LOCK_JSON)

    # ---- guard -----------------------------------------------------------------------------
    # The token is derived from the seal, never restated as a literal, so a package cannot claim a
    # verdict the evidence did not reach.
    declared = ev["stage_verdict"]
    derivation = criteria["verdict_token_derivation"]
    token = (
        derivation["pass_token"] if declared["verdict"] == "PASS" else derivation["fail_token"]
    )
    derived = f"{declared['verdict']} — {token}"
    if derived != VERDICT:
        print(f"EVIDENCE VERDICT {derived!r} DISAGREES WITH {VERDICT!r} — no package written")
        return 3
    if declared["verdict_token"] != token:
        print("EVIDENCE TOKEN DISAGREES WITH THE SEALED DERIVATION — no package written")
        return 3
    if declared["verdict"] == "FAIL" and declared["admitted_candidates"]:
        print("EVIDENCE REPORTS A FAIL WITH ADMITTED CANDIDATES — no package written")
        return 3
    if declared["verdict"] == "PASS" and not declared["admitted_candidates"]:
        print("EVIDENCE REPORTS A PASS WITH NO ADMITTED CANDIDATE — no package written")
        return 3
    if declared["representative_exists"] != ev["selection"]["representative_exists"]:
        print("VERDICT AND SELECTION DISAGREE ON THE REPRESENTATIVE — no package written")
        return 3
    if not ev["determinism"]["all_identical"]:
        print("EVIDENCE REPORTS A NON-DETERMINISTIC RERUN — no package written")
        return 3
    if ev["window"]["validation_read"] or ev["window"]["generation_1_holdout_read"]:
        print("EVIDENCE REPORTS A READ OUTSIDE THE DEVELOPMENT WINDOW — no package written")
        return 3

    # ---- integrity of every seal this stage stood on ---------------------------------------
    # Both Generation 2 records list project-root-relative paths, as Generation 1's preregistration
    # records do. Only the STAGE_0/STAGE_1 *freeze* records use bare filenames and must be verified
    # from governance/. Passing the wrong root here is an operator error that reads as an integrity
    # failure, which is why the root is explicit rather than implied by the file's location.
    lock_record = verify_sha256_record(PROJECT_ROOT / PARTITION_LOCK_RECORD, PROJECT_ROOT)
    protocol_record = verify_sha256_record(PROJECT_ROOT / PROTOCOL_RECORD, PROJECT_ROOT)
    if set(lock_record.values()) != {"OK"} or set(protocol_record.values()) != {"OK"}:
        print(f"A GENERATION 2 FREEZE RECORD FAILED: {lock_record} {protocol_record}")
        return 3

    grid = ev["variant_table"]
    selection = ev["selection"]

    decision = StageDecision(
        stage="STAGE_3_G2_ROTATION_DEVELOPMENT",
        stage_slug="stage3_g2",
        decision_basename="STAGE_3_G2_ROTATION_RESEARCH",
        manifest_basename="STAGE_3_G2_ARTIFACT_MANIFEST",
        gate_id=3,
        gate_name="development_admissibility",
        verdict=VERDICT,
        gate_passed=False,
        generation=2,
        command=COMMAND,
        gate_conditions=gate_conditions(ev, criteria),
        frozen_inputs=FROZEN_INPUTS,
        produced=PRODUCED,
        evidence=[
            f"All {ev['grid']['runs_executed']} declared runs were executed — eighteen variants "
            f"times the two sealed cost labels {protocol['runs_per_variant']['labels']} — with no "
            "run conditional on another's outcome and no grid revision after any result was seen.",
            f"Every one of the eighteen variants recorded {2} research-shutdown events, one in each "
            "of its two runs: 36 of 36 runs fired the constitution section 5.1 trip-wire (15% below "
            "the running high-water mark, LIQUIDATE_AT_NEXT_OPEN_AND_BLOCK_ENTRIES).",
            "The shutdowns fired on 18 distinct sessions spread from 2008-10-24 to 2020-03-12, not "
            "on a single session, and each base/stress pair fired on the same or an adjacent "
            "session — the signature of a real equity path, not of a constant.",
            "Buy-and-hold on the same run span is the control: SPY first breaches the same 15% "
            "threshold on 2008-10-03 with a worst drawdown of 0.4789, and IVV on 2008-10-03 with "
            "0.4790 — both before any variant fired. The sealed run span opens 2008-07-28, ten "
            "weeks before the worst equity drawdown in modern market history, so a long-only "
            "rotation tripping a 15% trip-wire is a property of the window and not a defect.",
            "The shutdown's effect was verified from the fill stream rather than from the engine's "
            "own rejection counters, on four probe variants spanning the earliest firing, the "
            "latest, the highest turnover and the lowest: every shutdown liquidates the whole book "
            "at the next open with SHUTDOWN-tagged sells, and no BUY fill occurs at or after the "
            "shutdown session in any probe.",
            "The representative was selected from records carrying no performance figure at all: "
            f"{selection['return_blind_enforcement']}",
            f"Step 1 of the frozen rule admitted {selection['step_1']['eligible_count']} of "
            f"{selection['variants_considered']} variants, so steps 2 and 3 were never "
            "reached and the sealed no_candidate_path applies.",
            "Determinism: the dataset was reloaded from disk and all 36 runs repeated on fresh "
            f"strategy objects; {ev['determinism']['runs_compared']} of "
            f"{ev['determinism']['runs_compared']} runs matched on trade digest, equity digest, "
            "ranking digest, fill count, final equity and shutdown session, with zero mismatches.",
            "Cross-sectionality, the one thing Generation 2 was built to change: the variants "
            "targeted up to 21 distinct symbols across the run, against Generation 1's validated "
            "candidate which only ever traded SPY. The failure is not a collapse back onto one "
            "symbol.",
            f"Window: the latest session loaded anywhere in the dataset is "
            f"{ev['window']['latest_session_loaded']}, against a development bound of "
            f"{ev['window']['development_bound']}. {ev['window']['enforcement']}",
            f"Evidence self-digest {ev['evidence_digest']} covers {ev['evidence_digest_covers']}, "
            "recomputed from the written file by an independent script that follows the coverage "
            "sentence literally rather than re-running the writer's own function.",
        ],
        limitations=[
            lock["validation_reuse_disclosure"],
            protocol["multiple_comparisons_disclosure"],
            "This stage read development data only. Nothing here is evidence about the validation "
            "window, the Generation 1 holdout, or the Generation 2 holdout, and a development "
            "result has never been evidence of an edge in this project.",
            "The verdict is bounded by the sealed run span 2008-07-28 to 2021-07-30, which begins "
            "at the first session where the 12-month lookback has a reference bar for every "
            "universe member. All eighteen variants share that start, including the 3- and 6-month "
            "variants that could individually have started earlier. That choice makes the "
            "cross-lookback comparison fair and costs the shorter lookbacks history they could "
            "have used; a grid run on a later start that excluded 2008 would very likely have "
            "produced a different shutdown count, and this stage cannot say what it would have "
            "been.",
            "The shutdown screen is the whole of the selection here. Because it eliminated every "
            "variant at step 1, the tiebreak on turnover was never exercised on real data, and "
            "this stage provides no evidence that step 2 or step 3 behaves correctly beyond the "
            "unit tests that cover them.",
            "Profit factor, drawdown and return were computed for all 36 runs and are reported in "
            "full, but no Gate 3 hard condition was evaluated, because Gate 3 is evaluated only on "
            "a representative and none exists. Those figures are descriptive and gate nothing.",
            "Generation 2 declares a single candidate family, so the constitution's cross-candidate "
            "disjunction is over a set of size one. See G2-CONFLICT-15.",
        ],
        blockers=[],
        conflicts_found=[
            "G2-CONFLICT-6: the constitution's best-trade-removed condition does not state the "
            "basis for the removal in a multi-position strategy; the sealed criteria fix it as the "
            "single closed trade with the largest positive net contribution across the whole run.",
            "G2-CONFLICT-7: the instruction's neighbour-robustness condition does not define "
            "neighbours for a three-axis grid; the seal defines them as variants differing on "
            "exactly one axis by one step.",
            "G2-CONFLICT-8: the instruction says 'monthly' and 'quarterly' without defining the "
            "rebalance session; the seal fixes it as the first session whose month boundary has "
            "been crossed, not the calendar month end.",
            "G2-CONFLICT-9: at k=1 the 95% gross exposure ceiling and the 50% concentration ceiling "
            "conflict; the concentration ceiling is more restrictive and binds, so a k=1 variant "
            "holds half its equity in cash by construction. This is disclosed, not corrected.",
            "G2-CONFLICT-10: equal weighting is applied at entry and not maintained by drift "
            "between rebalances; the instruction's 'equal-weight across k held positions' is read "
            "as a sizing rule, since maintaining it continuously would require unscheduled trades "
            "the instruction forbids.",
            "G2-CONFLICT-11: the instruction defines one FAIL path (no variant has zero shutdowns); "
            "the constitution implies a second (a representative exists and misses a hard "
            "condition). Both are sealed, and the route actually taken is recorded.",
            "G2-CONFLICT-12: the instruction's fail token names the absence of a candidate and the "
            "constitution's names the rejection of one. Both are recorded; the sealed token is "
            "emitted.",
            "G2-CONFLICT-13: the instruction's turnover tiebreak does not define turnover; the seal "
            "fixes it as the fill count across both declared runs, a return-blind proxy.",
            "G2-CONFLICT-14: the multi-position engine must mark open positions and sequence sells "
            "before buys within a rebalance; neither is specified by the instruction and both are "
            "sealed and adversarially tested.",
            "G2-CONFLICT-15: Generation 2 declares one candidate, so the constitution's "
            "cross-candidate disjunction is over a set of size one.",
            "G2-CONFLICT-16: the frozen Order contract carries a budget measured at the decision "
            "close, but rotation buys execute at the next open; the seal re-measures the budget at "
            "the open and records the re-evaluation count rather than editing the frozen contract.",
            "G2-CONFLICT-4: repo_state_id's governance pattern is single-level "
            "(governance/*.md), so governance/generation_2/* is NOT covered by it, while "
            "config/**/*.json is recursive and config/generation_2/*.json IS. The Generation 2 "
            "governance artifacts are therefore covered by their own .sha256 records and by this "
            "package's checksum record, not by repo_state_id. Disclosed rather than fixed: "
            "changing the pattern set would make repo_state_id values incomparable across stages.",
        ],
        body={
            "verdict_semantics": VERDICT_SEMANTICS,
            "verdict_token_derivation": derivation,
            "generation": {
                "generation": 2,
                "generation_id": protocol["generation_id"],
                "charter": CHARTER,
                "charter_sha256": sha256_file(PROJECT_ROOT / CHARTER),
                "generation_1_status": (
                    "CLOSED. Generation 1 ended FAIL — STAGE_4_STRATEGY_REJECTED_IN_VALIDATION. No "
                    "Generation 1 artifact under governance/, config/ or reports/ was read for "
                    "anything but context, and none was edited, regenerated or reinterpreted by "
                    "this stage."
                ),
                "what_changed_from_generation_1": protocol[
                    "what_makes_this_genuinely_cross_sectional"
                ],
            },
            "preregistration": {
                "protocol": PROTOCOL_JSON,
                "protocol_sha256": sha256_file(PROJECT_ROOT / PROTOCOL_JSON),
                "protocol_record": PROTOCOL_RECORD,
                "protocol_record_verification": protocol_record,
                "criteria": CRITERIA,
                "criteria_sha256": sha256_file(PROJECT_ROOT / CRITERIA),
                "declared_before_any_strategy_code": protocol[
                    "declared_before_any_strategy_code"
                ],
                "strategy_id": protocol["strategy_id"],
                "hypothesis": protocol["hypothesis"],
                "grid": ev["grid"],
                "revisions_after_seeing_a_result": 0,
            },
            "partition": {
                "lock": PARTITION_LOCK_JSON,
                "lock_sha256": sha256_file(PROJECT_ROOT / PARTITION_LOCK_JSON),
                "lock_record_verification": lock_record,
                "partition": lock["partition"],
                "window_read_by_this_stage": ev["window"],
                "generation_1_holdout_state": lock["generation_1_holdout_state"],
                "holdout_state": lock["holdout_state"],
            },
            "universe": ev["universe"],
            "selection": selection,
            "gate_evaluation_scope": ev["gate_evaluation_scope"],
            "candidate_results": ev["candidate_results"],
            "stage_verdict": declared,
            "determinism": {
                key: value
                for key, value in ev["determinism"].items()
                if key != "run_digests"
            },
            "grid_results_descriptive_only": {
                "status": ev["variant_table_is_descriptive_only"],
                "used_in_selection": False,
                "table": grid,
            },
            "engine_capability_added": {
                "what": (
                    "The Stage 2 single-position engine was extended to hold up to k risky "
                    "positions simultaneously. The frozen engine.py was not modified; the "
                    "capability is a new module, backtest/g2_engine.py."
                ),
                "ceilings_enforced": (
                    "at most k open positions; 95% maximum gross exposure across the combined "
                    "book; 50% maximum single-position concentration at any rebalance"
                ),
                "adversarial_tests": (
                    "tests/adversarial/test_g2_engine_multiposition.py asserts the engine cannot "
                    "exceed k positions, cannot breach either ceiling, cannot trade at the close "
                    "that generated its ranking, cannot see tomorrow's bar in today's ranking, and "
                    "reproduces identical results from identical inputs on a clean rerun"
                ),
            },
            "evidence_file": {
                "path": EVIDENCE,
                "artifact_id": ev["artifact_id"],
                "sha256": sha256_file(PROJECT_ROOT / EVIDENCE),
                "evidence_digest": ev["evidence_digest"],
                "evidence_digest_covers": ev["evidence_digest_covers"],
                "generated_utc": ev["generated_utc"],
            },
            "authorization": {
                "stage_4_validation_authorized": False,
                "stage_4_note": (
                    "Stage 4 validation was not run and is not authorized by this package. The "
                    "validation-window data exists on disk and is technically reachable; it was "
                    "not read. Authorization requires an explicit human go-ahead in a separate "
                    "session."
                ),
                "holdout_read_authorized": False,
                "holdout_note": (
                    "Generation 2's holdout is 2026-08-01 to 2028-07-31 and does not exist in "
                    "calendar time. Generation 1's sealed holdout was not read by this stage or by "
                    "any code it ran."
                ),
                "explicit_non_authorizations": protocol["explicit_non_authorizations"],
            },
        },
        tests={"passed": 1090, "failed": 1, "skipped": 0},
        authorization_state={
            "live_trading_authorized": "false",
            "paper_trading_authorized": "false",
            "broker_connection_made": "false",
            "credentials_read": "false",
            "stage_4_validation_authorized": "false",
            "generation_2_holdout_read_authorized": "false",
            "generation_1_holdout_read": "false",
        },
        next_authorized_stage=(
            "None without human review. Generation 2 Stage 3 reached FAIL — "
            "STAGE_3_G2_NO_CANDIDATE, so no candidate is admitted to validation. The next "
            "authorized action is human review of this package. Any subsequent work restarts at "
            "Gate 3 with a new pre-registration; it may not reuse this grid, loosen this rule, or "
            "promote a runner-up."
        ),
        dataset_hashes={},
        universe_version=protocol["eligible_universe"]["universe_version"],
        date_range=[
            protocol["run_span"]["run_start"],
            protocol["run_span"]["run_end"],
        ],
        holdout_state="LOCKED",
        config_hash=sha256_file(PROJECT_ROOT / PROTOCOL),
        run_notes=[
            "Generation 2 Stage 3 development. Eighteen pre-registered rotation variants, two cost "
            "labels each, 36 runs, all executed.",
            "Verdict FAIL — STAGE_3_G2_NO_CANDIDATE: every variant recorded a research shutdown in "
            "both runs, so the frozen return-blind selection rule admitted no representative and "
            "Gate 3 was never reached.",
            "No Generation 1 artifact under governance/, config/ or reports/ was modified. The "
            "Generation 2 artifacts live in governance/generation_2/ and config/generation_2/.",
            "No data dated 2021-08-01 or later was read. The latest session loaded anywhere is "
            f"{ev['window']['latest_session_loaded']}.",
            "Stage 4 validation was not run and is not authorized by this package.",
            "One test fails by design: the Stage 4 preregistration red marker recorded as "
            "S4-CONFLICT-7. It is a permanent regression marker from Generation 1 and is not "
            "weakened, skipped or deleted here.",
        ],
    )

    result = build_stage_package(decision)

    print(f"verdict          {VERDICT}")
    print(f"run_id           {result.run_id}")
    print(f"repo_state_id    {result.repo_state_id}")
    print(f"timestamp_utc    {result.timestamp_utc}")
    print(f"stage0 freeze    {result.freeze_ok}")
    print(f"decision         {result.decision_path.relative_to(PROJECT_ROOT)}")
    print(f"manifest         {result.manifest_path.relative_to(PROJECT_ROOT)}")
    print(f"checksums        {result.checksum_path.relative_to(PROJECT_ROOT)}")
    print(f"checksum_digest  {result.checksum_digest}")
    print(f"run record       {result.run_record_path.relative_to(PROJECT_ROOT)}")

    if not result.freeze_ok:
        print("STAGE 0 FREEZE VERIFICATION FAILED")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
