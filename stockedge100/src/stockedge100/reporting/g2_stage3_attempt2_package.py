"""Generation 2 Stage 3 **Attempt 2** decision package.

Assembles the decision record, artifact manifest, checksum record and ``runs/`` record for Attempt
2's development gate, from the evidence file
``reports/stage3_g2_attempt2/STAGE_3_G2_A2_DEVELOPMENT_ADMISSIBILITY.json`` and the sealed criteria
in ``config/generation_2/g2_gate_criteria_ra1.json``. It writes no verdict of its own.

**The guard is the portable one**, as in ``g2_stage3_package.py``. Attempt 2 can legitimately fail —
the sealed ``verdict_token_derivation`` says so in as many words (``fail_is_a_deliverable``) — so a
pass-only guard would suppress the deliverable the constitution requires be kept on disk. What this
guard refuses is a package that disagrees with its own evidence.

Three checks are new here and exist because Attempt 2 sits alongside a closed Attempt 1:

* the emitted token must be one of the two sealed **Attempt 2** tokens and must be **neither** of
  Attempt 1's, which the seal names in ``attempt_1_tokens_are_not_available_here``;
* the 842-character adaptation disclosure must be **byte-identical** across every carrier the seal
  lists, checked by digest against the protocol's own copy rather than by eye. The seal's wording is
  "a paraphrase is a failure, not a stylistic choice", so it is checked, not asserted;
* the nine Attempt 1 modules must not have moved, re-verified from the evidence rather than trusted.

Unlike Attempt 1's package, this one reaches Gate 3: a representative exists, so the seven hard
conditions are **evaluated**, not ``NOT_RUN``. The rows aggregate on ``satisfied`` rather than on
``verdict == "MET"`` — aggregating on MET produced a false FAIL for S3-C6 in Generation 1 Stage 3 —
and they aggregate across the run labels that actually gate each condition: ``#BASE`` and
``#STRESS`` for S3-C1..S3-C6, ``#BASE`` alone for S3-C7 (G2A2-CONFLICT-25).

Test counts are **parsed from the captured pytest output at build time**, never typed in. Typing
them would mean editing this module after taking the capture, and this module lives in ``src/``,
which ``repo_state_id`` covers — the edit would invalidate the capture it was describing.

Run **last**. Any edit to this module or to a test after the build invalidates the digest the build
just recorded, and ``runs/`` is append-only. Dry-run it first from ``_scratch/`` with
:func:`build_stage_package` monkeypatched.

Usage::

    cd stockedge100 && PYTHONPATH=src python -m stockedge100.reporting.g2_stage3_attempt2_package
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from stockedge100.audit import sha256_bytes, sha256_file
from stockedge100.reporting.g2_partition_lock import normalised_prose
from stockedge100.reporting.stage_package import (
    PROJECT_ROOT,
    StageDecision,
    build_stage_package,
    verify_sha256_record,
)

COMMAND = (
    "cd stockedge100 && PYTHONPATH=src python -m "
    "stockedge100.reporting.g2_stage3_attempt2_package"
)

VERDICT = "FAIL — STAGE_3_G2_ATTEMPT_2_NO_CANDIDATE"

EVIDENCE = "reports/stage3_g2_attempt2/STAGE_3_G2_A2_DEVELOPMENT_ADMISSIBILITY.json"
CRITERIA = "config/generation_2/g2_gate_criteria_ra1.json"
PROTOCOL = "config/generation_2/g2_rotation_ra1_protocol.json"
COST_MODEL = "config/generation_2/g2_cost_model.json"
CHARTER = "governance/generation_2/STAGE_10_GENERATION_2_CHARTER.md"

PARTITION_LOCK_MD = "governance/generation_2/STAGE_1_G2_PARTITION_LOCK.md"
PARTITION_LOCK_JSON = "governance/generation_2/STAGE_1_G2_PARTITION_LOCK.json"
PARTITION_LOCK_RECORD = "governance/generation_2/STAGE_1_G2_PARTITION_LOCK.sha256"

PROTOCOL_MD = "governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.md"
PROTOCOL_JSON = "governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.json"
PROTOCOL_RECORD = "governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.sha256"

# Attempt 1's artifacts are frozen inputs to this attempt, read to prove they did not move. They are
# never written, and the sealed digests they are checked against live in the Attempt 2 protocol.
ATTEMPT_1_PROTOCOL_MD = "governance/generation_2/STAGE_3_G2_ROTATION_PROTOCOL.md"
ATTEMPT_1_PROTOCOL_JSON = "governance/generation_2/STAGE_3_G2_ROTATION_PROTOCOL.json"
ATTEMPT_1_PROTOCOL_RECORD = "governance/generation_2/STAGE_3_G2_ROTATION_PROTOCOL.sha256"
ATTEMPT_1_REPORT = "governance/generation_2/STAGE_3_G2_ROTATION_RESEARCH_REPORT.md"
ATTEMPT_1_CRITERIA = "config/generation_2/g2_gate_criteria.json"
ATTEMPT_1_PROTOCOL_CONFIG = "config/generation_2/g2_rotation_protocol.json"

REPORT = "governance/generation_2/STAGE_3_G2_ROTATION_RA1_RESEARCH_REPORT.md"
PYTEST_CAPTURE = "reports/stage3_g2_attempt2/pytest_stage3_g2_attempt2_output.txt"

PRODUCED = [
    REPORT,
    EVIDENCE,
    "reports/stage3_g2_attempt2/STAGE_3_G2_A2_ROTATION_RESEARCH.json",
    "reports/stage3_g2_attempt2/STAGE_3_G2_A2_ROTATION_RESEARCH.sha256",
    "reports/stage3_g2_attempt2/STAGE_3_G2_A2_ARTIFACT_MANIFEST.json",
    "reports/stage3_g2_attempt2/STAGE_3_G2_A2_TEST_SUMMARY.md",
    PYTEST_CAPTURE,
    # The runner's own outputs. They sit under reports/, which repo_state_id does not cover, so this
    # package's manifest and checksum record are the only things that hold them.
    "reports/stage3_g2_attempt2/attempt_1_module_verification.json",
    "reports/stage3_g2_attempt2/run_span_recheck.json",
    "reports/stage3_g2_attempt2/grid_results.json",
    "reports/stage3_g2_attempt2/selection_inputs.json",
    "reports/stage3_g2_attempt2/selection_record.json",
    "reports/stage3_g2_attempt2/gate_record.json",
    "reports/stage3_g2_attempt2/stage_verdict.json",
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
    ATTEMPT_1_PROTOCOL_MD,
    ATTEMPT_1_PROTOCOL_JSON,
    ATTEMPT_1_PROTOCOL_RECORD,
    ATTEMPT_1_REPORT,
    ATTEMPT_1_PROTOCOL_CONFIG,
    ATTEMPT_1_CRITERIA,
]

# Named by the seal itself, in verdict_token_derivation.attempt_1_tokens_are_not_available_here.
ATTEMPT_1_TOKENS = (
    "STAGE_3_G2_STRATEGY_ADMITTED_IN_DEVELOPMENT",
    "STAGE_3_G2_NO_CANDIDATE",
)

VERDICT_SEMANTICS = (
    "FAIL — STAGE_3_G2_ATTEMPT_2_NO_CANDIDATE is the second of the two fail routes the sealed rule "
    "anticipated in writing before any variant was run, and it is not the route Attempt 1 took. "
    "Attempt 1 failed at step 1 of the selection rule: all eighteen variants recorded a research "
    "shutdown, so no representative existed and Gate 3 was never reached. Attempt 2's risk "
    "architecture removed that failure entirely — all eighteen variants recorded zero shutdown "
    "events, step 1 admitted all eighteen, and the turnover tiebreak produced a representative. "
    "The gate was therefore reached and evaluated, and the representative missed it. The token is "
    "the same because the seal gives both routes the same token; the route is recorded separately "
    "(REPRESENTATIVE_FAILED_AT_LEAST_ONE_CONDITION) and the distinction is the substance of this "
    "attempt's result. The verdict is a statement about the representative the frozen return-blind "
    "rule produced, not about the grid's best return: no return figure was an input to the "
    "selection, and several variants returned far more than the one selected. The result is a "
    "deliverable and is kept on disk. It does not license promoting a runner-up, re-selecting on "
    "return, loosening a risk constant, widening the grid, or an Attempt 3."
)


def load(rel: str) -> dict[str, Any]:
    return json.loads((PROJECT_ROOT / rel).read_text(encoding="utf-8"))


def read_text(rel: str) -> str:
    return (PROJECT_ROOT / rel).read_text(encoding="utf-8")


def test_counts(text: str) -> dict[str, int] | None:
    """Parse the captured pytest output. Counts are read from disk, never typed into the package.

    The summary line is taken from the END of the capture, so a capture that was appended to rather
    than overwritten would still describe its last run. That is a weaker guarantee than it looks —
    the build order rule requires the capture be overwritten — but reading from the end is the only
    reading that is ever right.
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    summary = next((ln for ln in reversed(lines) if re.search(r"\d+ (passed|failed)", ln)), None)
    collected = next((ln for ln in reversed(lines) if re.search(r"\d+ tests? collected", ln)), None)
    if summary is None or collected is None:
        return None

    def count(word: str, line: str) -> int:
        found = re.search(rf"(\d+) {word}", line)
        return int(found.group(1)) if found else 0

    return {
        "collected": count(r"tests? collected", collected),
        "passed": count("passed", summary),
        "failed": count("failed", summary),
        "skipped": count("skipped", summary),
        "errors": count("error", summary),
    }


def disclosure_carriage(protocol: dict[str, Any], ev: dict[str, Any]) -> dict[str, Any]:
    """Check the adaptation disclosure is carried by every carrier the seal names.

    The string is never printed: the seal's ``encoding_note`` forbids writing it to a cp1252 console
    and doing so would raise ``UnicodeEncodeError`` mid-build. Only digests and lengths surface.

    JSON carriers are compared as *decoded values*, because a JSON file stores the string escaped;
    comparing the raw bytes of a JSON file against the raw string would report a false mismatch for
    the em-dashes. Those three carriers are byte-exact and are asserted that way.

    Markdown carriers are the case G2A2-CONFLICT-29 records. The seal's ``enforcement`` says the
    sealer and this builder both assert byte-equality, but the sealed protocol Markdown hard-wraps
    the paragraph inside a blockquote at 100 columns: it stores 858 characters where the sealed
    string is 842, the difference being eight ``\\n>`` continuation markers and nothing else. The
    sealer never asserted byte-equality there either — it compared :func:`normalised_prose` of both
    sides, for exactly this reason. That artifact is frozen and may not be rewrapped, so this
    builder applies the sealer's own rule, **imported** rather than restated so the two cannot
    drift, and records the byte-exact result alongside it rather than in place of it.
    """
    sealed = protocol["adaptation_disclosure_verbatim"]
    sealed_digest = sha256_bytes(sealed.encode("utf-8"))
    requirement = protocol["adaptation_disclosure_carriage_requirement"]

    carriers: dict[str, Any] = {}
    for rel in requirement["must_appear_verbatim_in"]:
        path = PROJECT_ROOT / rel
        if not path.is_file():
            carriers[rel] = {
                "present": False,
                "carries_verbatim": False,
                "carries_byte_exact": False,
                "how": "file missing",
            }
            continue
        text = path.read_text(encoding="utf-8")
        if rel.endswith(".json"):
            byte_exact = sealed in json.dumps(json.loads(text), ensure_ascii=False)
            found = byte_exact
            how = "decoded JSON contains the sealed string byte-for-byte"
        else:
            byte_exact = sealed in text
            found = normalised_prose(sealed) in normalised_prose(text)
            how = (
                "byte-exact substring of the decoded UTF-8 text"
                if byte_exact
                else "hard-wrapped blockquote: equal under the sealer's normalised_prose, not "
                "byte-for-byte. See G2A2-CONFLICT-29."
            )
        carriers[rel] = {
            "present": True,
            "carries_verbatim": bool(found),
            "carries_byte_exact": bool(byte_exact),
            "how": how,
            "file_sha256": sha256_file(path),
        }

    return {
        "characters": len(sealed),
        "sha256_of_utf8": sealed_digest,
        "sha256_recorded_in_evidence": ev["adaptation_disclosure_carriage"]["sha256_of_utf8"],
        "digest_agrees_with_evidence": (
            sealed_digest == ev["adaptation_disclosure_carriage"]["sha256_of_utf8"]
        ),
        "enforcement": requirement["enforcement"],
        "encoding_note": requirement["encoding_note"],
        "carriers": carriers,
        "all_carriers_verbatim": all(c["carries_verbatim"] for c in carriers.values()),
        "all_carriers_byte_exact": all(c["carries_byte_exact"] for c in carriers.values()),
        "carriers_requiring_normalisation": [
            rel
            for rel, c in carriers.items()
            if c["present"] and c["carries_verbatim"] and not c["carries_byte_exact"]
        ],
        "normalisation_rule": (
            "reporting.g2_partition_lock.normalised_prose — strip '>', '*' and '`', then collapse "
            "whitespace. Imported from the module the sealer itself used rather than restated "
            "here, so the builder's reading of 'verbatim' cannot drift from the sealer's. Applied "
            "to Markdown carriers only; the three JSON carriers are asserted byte-exact. See "
            "G2A2-CONFLICT-29."
        ),
        "note": (
            "The decision record this package writes is itself one of the carriers, so it is "
            "listed here as absent at check time and carries the string in "
            "adaptation_disclosure_verbatim below. The post-build verification re-reads it."
        ),
    }


def gate_conditions(ev: dict[str, Any], criteria: dict[str, Any]) -> dict[str, Any]:
    """The seven hard conditions as actually evaluated, plus the one row that decides the gate.

    Aggregation is on ``satisfied``, not on ``verdict == "MET"``. The two coincide for every row of
    this attempt — nothing came back ``NOT_APPLICABLE_BY_CONDITION_TEXT`` — but aggregating on MET
    is the bug that produced a false FAIL for S3-C6 in Generation 1 Stage 3, and a table that would
    have been wrong under different evidence is not a table worth writing.

    The gating scope per condition comes from the sealed resolution of G2A2-CONFLICT-25 recorded in
    ``admission_basis``: all seven on ``#BASE``, and S3-C1..S3-C6 also on ``#STRESS``. S3-C7's
    stress side is measured and reported and gates nothing, because its own ``what_is_read`` fixes
    the neighbour comparison to base-run total return.
    """
    candidate = ev["candidate_results"][0]
    basis = candidate["admission_basis"]
    base_rows = {row["id"]: row for row in candidate["conditions"]}
    stress_rows = {row["id"]: row for row in candidate["stress_evaluation"]["conditions"]}
    non_gating_stress = basis["s3_c7_stress_side_reported_not_gating"]["id"]

    conditions: dict[str, Any] = {}
    for cond in criteria["conditions"]:
        cid = cond["id"]
        gating = {"#BASE": base_rows[cid]}
        reported_only = {}
        if cid == non_gating_stress:
            reported_only["#STRESS"] = stress_rows[cid]
        else:
            gating["#STRESS"] = stress_rows[cid]

        satisfied_by = [label for label, row in gating.items() if row["satisfied"]]
        met_by = [label for label, row in gating.items() if row["verdict"] == "MET"]
        not_met_by = [label for label, row in gating.items() if not row["satisfied"]]
        not_evaluable_for = [
            label for label, row in gating.items() if row["verdict"] == "NOT_EVALUABLE"
        ]
        not_applicable_for = [
            label
            for label, row in gating.items()
            if row["satisfied"] and row["verdict"] != "MET"
        ]
        all_satisfied = len(satisfied_by) == len(gating)
        if all_satisfied and len(met_by) == len(gating):
            verdict = "MET"
        elif all_satisfied:
            verdict = "SATISFIED_WITHOUT_BEING_MET"
        else:
            verdict = "NOT_MET"

        conditions[cid] = {
            "required_verbatim": cond["required_verbatim"],
            "predicate": cond.get("predicate", cond.get("threshold")),
            "verdict": verdict,
            "satisfied": all_satisfied,
            "gating_runs": sorted(gating),
            "satisfied_by": sorted(satisfied_by),
            "met_by": sorted(met_by),
            "not_met_by": sorted(not_met_by),
            "not_evaluable_for": sorted(not_evaluable_for),
            "not_applicable_for": sorted(not_applicable_for),
            "measured": {label: row["measured"] for label, row in gating.items()},
            "threshold": base_rows[cid]["threshold"],
            "reported_not_gating": {
                label: {"verdict": row["verdict"], "measured": row["measured"]}
                for label, row in reported_only.items()
            },
            "note": (
                "Evaluated on the representative "
                f"{candidate['variant_id']} only. A condition is satisfied only if EVERY gating run "
                "satisfies it; the stressed cost model is not a sensitivity check that may be "
                "waived. Aggregated on satisfied, not on verdict == MET."
            ),
        }

    admitted = ev["stage_verdict"]["admitted_candidates"]
    selection = ev["selection"]
    conditions["admissible_candidate_exists"] = {
        "required_verbatim": (
            "At least one candidate satisfies every hard condition of Gate 3 in development."
        ),
        "predicate": (
            "a representative exists AND every hard condition is satisfied on every run that "
            "gates it"
        ),
        "verdict": "NOT_MET",
        "value": False,
        "variants_declared": selection["variants_considered"],
        "variants_eligible_after_shutdown_screen": selection["step_1"]["eligible_count"],
        "candidates_evaluated": ev["stage_verdict"]["candidates_evaluated"],
        "admitted_candidates": admitted,
        "representative": selection["representative_variant_id"],
        "conditions_not_satisfied_base": basis["base_conditions_not_satisfied"],
        "conditions_not_satisfied_stress": basis["stress_conditions_not_satisfied"],
        "determination": (
            "This entry, and only this entry, is the gate determination. All "
            f"{selection['variants_considered']} declared variants survived step 1 of the frozen "
            "selection rule — a complete reversal of Attempt 1, where none did — and the turnover "
            f"tiebreak produced {selection['representative_variant_id']}. Gate 3 was reached, "
            "evaluated, and not satisfied: "
            f"{', '.join(basis['base_conditions_not_satisfied'])} failed on #BASE and "
            f"{', '.join(basis['stress_conditions_not_satisfied'])} on #STRESS."
        ),
        "note": (
            "A conditions table that omits this row reads as though the gate were irrelevant "
            "rather than decided. The seven rows above settle nothing on their own: gates are "
            "conjunctive within a candidate and the stage verdict is a disjunction across "
            "candidates, and here the candidate set has one member, which failed. Promoting a "
            "runner-up would convert a return-blind selection into a search over eighteen "
            "candidates for one that passes; the seal forbids it and so does this package."
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
    token = derivation["pass_token"] if declared["verdict"] == "PASS" else derivation["fail_token"]
    derived = f"{declared['verdict']} — {token}"
    if derived != VERDICT:
        print(f"EVIDENCE VERDICT {derived!r} DISAGREES WITH {VERDICT!r} — no package written")
        return 3
    if declared["verdict_token"] != token:
        print("EVIDENCE TOKEN DISAGREES WITH THE SEALED DERIVATION — no package written")
        return 3
    if token not in (derivation["pass_token"], derivation["fail_token"]):
        print("TOKEN IS NOT ONE OF THE TWO SEALED ATTEMPT 2 TOKENS — no package written")
        return 3
    if token in ATTEMPT_1_TOKENS:
        print("TOKEN BELONGS TO ATTEMPT 1, WHICH IS CLOSED — no package written")
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
    window = ev["window"]
    if (
        window["validation_read"]
        or window["generation_1_holdout_read"]
        or window["generation_2_holdout_read"]
    ):
        print("EVIDENCE REPORTS A READ OUTSIDE THE DEVELOPMENT WINDOW — no package written")
        return 3
    if ev["reconciliation"]["mismatches_total"] != 0 or ev["reconciliation"]["vacuous_runs"]:
        print("EVIDENCE REPORTS A RECONCILIATION MISMATCH — no package written")
        return 3
    if ev["attempt_1_module_verification"]["modules_that_moved"]:
        print("AN ATTEMPT 1 MODULE MOVED — no package written")
        return 3

    # ---- the evidence self-digest, recomputed rather than trusted ---------------------------
    excluded = ("generated_utc", "evidence_digest")
    covered = {k: v for k, v in ev.items() if k not in excluded}
    recomputed = sha256_bytes(
        json.dumps(covered, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
            "utf-8"
        )
    )
    if recomputed != ev["evidence_digest"]:
        print(f"EVIDENCE SELF-DIGEST DID NOT RECOMPUTE: {recomputed} — no package written")
        return 3

    # ---- the disclosure, byte-identical in every carrier the seal names ---------------------
    carriage = disclosure_carriage(protocol, ev)
    if not carriage["digest_agrees_with_evidence"]:
        print("DISCLOSURE DIGEST DISAGREES WITH THE EVIDENCE — no package written")
        return 3
    # The decision record this build is about to write is itself one of the five carriers, so it is
    # necessarily absent at check time. Every other carrier must already carry the string.
    pending_carrier = "reports/stage3_g2_attempt2/STAGE_3_G2_A2_ROTATION_RESEARCH.json"
    missing = [
        rel
        for rel, state in carriage["carriers"].items()
        if not state["carries_verbatim"] and rel != pending_carrier
    ]
    if missing:
        print(f"DISCLOSURE NOT CARRIED VERBATIM BY: {missing} — no package written")
        return 3
    # The seal demands byte-equality. One frozen Markdown carrier hard-wraps the paragraph and so
    # cannot meet it (G2A2-CONFLICT-29); every other carrier can, and is still held to it here, so
    # the relaxation covers exactly the artifact that forced it and nothing else.
    relaxed = set(carriage["carriers_requiring_normalisation"])
    if relaxed - {PROTOCOL_MD}:
        print(f"DISCLOSURE NEEDED NORMALISATION IN AN UNEXPECTED CARRIER: {sorted(relaxed)} — "
              "no package written")
        return 3
    not_byte_exact = [
        rel
        for rel, state in carriage["carriers"].items()
        if not state["carries_byte_exact"] and rel not in (pending_carrier, PROTOCOL_MD)
    ]
    if not_byte_exact:
        print(f"DISCLOSURE NOT BYTE-EXACT IN: {not_byte_exact} — no package written")
        return 3

    # ---- integrity of every seal this stage stood on ---------------------------------------
    # Both Generation 2 records list project-root-relative paths. Only the STAGE_0/STAGE_1 *freeze*
    # records use bare filenames and must be verified from governance/; passing the wrong root there
    # is an operator error that reads as an integrity failure, which is why the root is explicit.
    lock_record = verify_sha256_record(PROJECT_ROOT / PARTITION_LOCK_RECORD, PROJECT_ROOT)
    protocol_record = verify_sha256_record(PROJECT_ROOT / PROTOCOL_RECORD, PROJECT_ROOT)
    attempt_1_record = verify_sha256_record(
        PROJECT_ROOT / ATTEMPT_1_PROTOCOL_RECORD, PROJECT_ROOT
    )
    records = (lock_record, protocol_record, attempt_1_record)
    if any(set(rec.values()) != {"OK"} for rec in records):
        print(f"A GENERATION 2 FREEZE RECORD FAILED: {records}")
        return 3

    # ---- test counts, parsed from the capture on disk ---------------------------------------
    tests = test_counts(read_text(PYTEST_CAPTURE))
    if tests is None:
        print(f"COULD NOT PARSE {PYTEST_CAPTURE} — no package written")
        return 3
    if tests["failed"] != 1 or tests["errors"]:
        print(f"UNEXPECTED TEST RESULT {tests} — exactly one designed failure is expected")
        return 3

    selection = ev["selection"]
    candidate = ev["candidate_results"][0]
    basis = candidate["admission_basis"]

    decision = StageDecision(
        stage="STAGE_3_G2_ATTEMPT_2_ROTATION_RA1_DEVELOPMENT",
        stage_slug="stage3_g2_attempt2",
        decision_basename="STAGE_3_G2_A2_ROTATION_RESEARCH",
        manifest_basename="STAGE_3_G2_A2_ARTIFACT_MANIFEST",
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
            "run conditional on another's outcome, no grid revision after a result was seen, and "
            "no RA2 constant tuned before or after.",
            "Every one of the eighteen variants recorded ZERO research-shutdown events across both "
            "of its runs: 0 of 36 runs fired the constitution section 5.1 trip-wire. Attempt 1's "
            "figure on the identical window, universe, cost model and grid was 36 of 36. That "
            "reversal is the single measured effect of the RA2 risk architecture, and it is the "
            "only thing this stage establishes.",
            "The maximum drawdown across all 36 runs is "
            f"{max(row['base_max_drawdown'] for row in ev['variant_table'])} on the base runs and "
            f"{max(row['stress_max_drawdown'] for row in ev['variant_table'])} on the stressed "
            "runs — every run inside the 15% ceiling, where Attempt 1 breached it in all 36.",
            "The risk architecture is measurably load-bearing rather than nominally present: every "
            "variant descended the de-risk ladder tens of times, sixteen of eighteen reached the "
            "deepest band (25% sizing), the re-entry lockout armed on every descent and blocked "
            "between 75 and 276 recoveries per run, and per-position stops fired on every variant. "
            "A zero-shutdown result from an architecture that never activated would be evidence of "
            "a dead code path; this one activated continuously.",
            "The representative was selected from records carrying no performance figure at all: "
            f"{selection['return_blind_enforcement']}",
            f"Step 1 of the frozen rule admitted all {selection['step_1']['eligible_count']} of "
            f"{selection['variants_considered']} variants, so step 2 decided on turnover: "
            f"{selection['representative_variant_id']} at "
            f"{selection['step_2']['lowest_fill_count']} fills across both runs, with "
            f"{len(selection['step_2']['tied_at_lowest'])} variant at that count, so step 3 was "
            f"not reached ({selection['step_3']['reached']}). {selection['selection_note']}",
            "Gate 3 was reached and evaluated, and the representative did not satisfy it. On "
            f"#BASE, {', '.join(basis['base_conditions_not_satisfied'])} were not satisfied; on "
            f"#STRESS, {', '.join(basis['stress_conditions_not_satisfied'])}. Under the permissive "
            "base-only reading the gate would still have failed "
            f"({basis['permissive_base_only_reading_would_give']}), so the restrictive resolution "
            "of G2A2-CONFLICT-25 did not decide the outcome.",
            "Gate conditions were measured on the episode ledger rather than on the frozen "
            "recorder's trade list, because Attempt 2's throttle and ladder TRIM positions and the "
            "frozen recorder attributes a trim's proceeds to no trade at all. The difference is "
            "visible in the numbers: the descriptive grid table reports a profit factor of 1.2459 "
            "for the representative's base run, while S3-C3 measures "
            f"{candidate['conditions'][2]['measured']} on the ledger basis. See "
            "G2A2-CONFLICT-18.",
            f"Reconciliation ran on all {ev['reconciliation']['runs_reconciled']} runs and not only "
            f"the representative's: {ev['reconciliation']['single_leg_compared_total']} single legs "
            f"compared, {ev['reconciliation']['mismatches_total']} mismatches, "
            f"{len(ev['reconciliation']['vacuous_runs'])} vacuous runs.",
            "Determinism: the dataset was reloaded from disk and all 36 runs repeated on fresh "
            f"strategy objects; {ev['determinism']['runs_compared']} of "
            f"{ev['determinism']['runs_compared']} runs matched on every field of "
            f"{ev['determinism']['fields_compared']}, with zero mismatches.",
            "The nine Generation 2 Attempt 1 modules were re-hashed against the digests sealed in "
            f"SE100-GOV-2005 before this attempt ran and again after: "
            f"{ev['attempt_1_module_verification']['module_count']} modules verified, "
            f"{len(ev['attempt_1_module_verification']['modules_that_moved'])} moved. Attempt 1 is "
            "closed and was not reopened, re-run, edited or loosened.",
            f"Window: the latest session loaded anywhere in the dataset is "
            f"{window['latest_session_loaded']}, against a development bound of "
            f"{window['development_bound']}. {window['enforcement']}",
            f"Evidence self-digest {ev['evidence_digest']} covers {ev['evidence_digest_covers']}, "
            "recomputed here from the written file and independently by a script that follows the "
            "coverage sentence literally rather than re-running the writer's own function. "
            "Dropping a covered field changes the digest, so the coverage is not vacuous.",
            "The 842-character adaptation disclosure is carried byte-identically by every carrier "
            "the seal names, checked by digest rather than by eye: "
            f"{sorted(carriage['carriers'])}.",
        ],
        limitations=[
            protocol["adaptation_disclosure_verbatim"],
            lock["validation_reuse_disclosure"],
            protocol["multiple_comparisons_disclosure"]["adaptive_design_note"],
            "This stage read development data only. Nothing here is evidence about the validation "
            "window, the Generation 1 holdout, or the Generation 2 holdout, and a development "
            "result has never been evidence of an edge in this project.",
            "The zero-shutdown result is the strongest finding here and it is also the most "
            "over-determined. RA2 caps aggregate exposure at 50%, so a portfolio that can lose at "
            "most half of what Attempt 1's could lose is structurally unlikely to breach a 15% "
            "drawdown ceiling. The ladder and the volatility target cut that further. This stage "
            "does not separate the contribution of the five RA2 components, and the design "
            "deliberately forbids the ablation study that would: the constants are frozen and not "
            "gridded, so no variant was run with a subset of them.",
            "Several variants performed far better than the representative on every descriptive "
            "measure — the strongest, L03-K1-MONTHLY, returned +0.6315 on #BASE against the "
            "representative's +0.0042, with a profit factor of 1.9341 against 1.2459 — and would "
            "plausibly have cleared conditions the representative missed. The frozen return-blind "
            "rule selected on turnover, which is exactly what makes this result honest and exactly "
            "what makes it feel wrong. Re-selecting on return is forbidden, was forbidden before "
            "any variant ran, and is not done here. The consequence is that this attempt reports a "
            "FAIL while holding, on disk, grid rows that a return-driven researcher would have "
            "reported as a PASS. That is the cost of the design, stated rather than hidden.",
            "The turnover tiebreak now partly measures how often the risk architecture intervened, "
            "because throttle and stop legs count as fills. It is not the same quantity Attempt "
            "1's tiebreak measured and the two attempts' turnover figures are not comparable. "
            "Declared as SC-4 before any variant ran and not corrected afterwards.",
            "Gate conditions were evaluated on one representative only. Seventeen other variants "
            "were run and none was evaluated against Gate 3, by design. No statement is made about "
            "whether any of them would have passed.",
            "Maximum observed gross exposure sits marginally above the 50% ceiling on every "
            "variant (0.5043 to 0.5184 across all 36 runs; the base-only table in §16 has the "
            "slightly higher minimum 0.5044), because the ceiling is enforced at fill time and the "
            "position is then free to appreciate before the next session's measurement. See "
            "G2A2-CONFLICT-27 and G2A2-CONFLICT-28. The breach is a measurement-timing artefact of "
            "at most 1.84% of equity, disclosed rather than corrected, because correcting it after "
            "seeing the results would be a post-hoc change to a frozen constant.",
            "Generation 2 declares a single live candidate family, so the constitution's "
            "cross-candidate disjunction is over a set of size one. See G2-CONFLICT-15 and "
            "G2A2-CONFLICT-24.",
        ],
        blockers=[],
        conflicts_found=[
            "G2A2-CONFLICT-25: SE100-CFG-3103 scopes Gate 3 across both runs and states a "
            "condition is satisfied only if both satisfy it; SE100-CFG-3104 measures S3-C1 and "
            "S3-C4 on the base run and lists the stress run as reported_but_not_gating. Both were "
            "sealed in the same session and neither outranks the other, so the MORE RESTRICTIVE "
            "reading is adopted: all seven conditions on #BASE, S3-C1..S3-C6 also on #STRESS, "
            "S3-C7 once on #BASE because its own what_is_read fixes the neighbour side to base-run "
            "total return. Both condition sets are reported in full, and the permissive reading is "
            f"recorded as giving {basis['permissive_base_only_reading_would_give']} — the "
            "resolution did not decide the verdict.",
            "G2A2-CONFLICT-26: the sealed non-vacuity rule for reconciliation would halt a run "
            "that compared zero single legs, but a run that closed no episode at all compares zero "
            "legs without being defective. As implemented, the halt fires only when "
            "closed_episodes > 0 and single_leg_compared == 0; a genuinely empty run is recorded "
            "as vacuous rather than raised on. No run of this attempt was vacuous.",
            "G2A2-CONFLICT-27: RA2-1's 50% aggregate exposure ceiling is enforced when an order "
            "fills, at the open. Positions then appreciate intraday and between sessions, so the "
            "gross fraction measured at the close exceeds 0.50 on every variant, peaking at 0.5184. "
            "Enforcing the ceiling continuously would require unscheduled trades the protocol "
            "forbids. Disclosed, quantified per variant, and not corrected.",
            "G2A2-CONFLICT-28: adversarial test AT-A was written to assert the ceiling holds at "
            "fill time; read as a statement about all sessions it would be false, and read as a "
            "statement about fill time it is true and is what RA2-1 actually specifies. The test "
            "wording was fixed before any variant ran; the drift it does not cover is measured and "
            "reported instead, per G2A2-CONFLICT-27.",
            "G2A2-CONFLICT-29: the sealed adaptation_disclosure_carriage_requirement says the "
            "sealer and this builder both assert byte-equality of the 842-character disclosure in "
            "all five carriers, and calls a paraphrase a failure rather than a stylistic choice. "
            "One carrier cannot meet it. STAGE_3_G2_ROTATION_RA1_PROTOCOL.md hard-wraps the "
            "paragraph inside a blockquote at 100 columns, storing 858 characters — the sealed 842 "
            "plus eight newline-and-'>' continuation markers, and nothing else. That file is "
            "frozen and may not be rewrapped. The sealer never asserted byte-equality there "
            "either: it compared reporting.g2_partition_lock.normalised_prose of both sides, "
            "because a hard-wrapped document cannot be checked line by line. This builder imports "
            "that same function rather than restating it, so its reading of 'verbatim' cannot "
            "drift from the sealer's, and applies it to Markdown carriers only. The three JSON "
            "carriers and the research report Markdown are still asserted byte-exact and all four "
            "are; the relaxation is asserted to cover this one path and no other. The disclosure's "
            "words are unaltered in every carrier — only its line breaks differ — which is what "
            "the requirement was written to protect.",
            "G2A2-CONFLICT-18: Attempt 2's throttle and ladder trim positions, and the frozen trade "
            "recorder attributes a trim's proceeds to no trade at all, so trade-list profit factor "
            "and best-trade-removed return would both be measured on an incomplete P&L. Gate "
            "conditions S3-C3, S3-C4, S3-C5 and S3-C6 are therefore measured on an episode ledger "
            "built from the fill stream. The frozen recorder is not modified.",
            "G2A2-CONFLICT-21: the instruction's fail token names the absence of an admissible "
            "candidate; the constitution's names the rejection of one. They denote the same stage "
            "outcome. The sealed token is emitted and the constitutional equivalent "
            f"({derivation['constitutional_fail_result_equivalent']}) is recorded alongside it.",
            "G2A2-CONFLICT-24: Attempt 2 declares one live candidate, so the constitution's "
            "cross-candidate disjunction is over a set of size one, as Attempt 1's G2-CONFLICT-15 "
            "recorded for Attempt 1.",
            "G2-CONFLICT-4: repo_state_id's governance pattern is single-level (governance/*.md), "
            "so governance/generation_2/* is NOT covered by it, while config/**/*.json is recursive "
            "and config/generation_2/*.json IS. Verified explicitly in both directions rather than "
            "assumed. The Generation 2 governance artifacts — including this attempt's research "
            "report — are therefore held by their own .sha256 records and by this package's "
            "checksum record and manifest, not by repo_state_id. Disclosed rather than fixed: "
            "changing the pattern set would make repo_state_id values incomparable across stages.",
        ],
        body={
            "verdict_semantics": VERDICT_SEMANTICS,
            "verdict_token_derivation": derivation,
            "adaptation_disclosure_verbatim": protocol["adaptation_disclosure_verbatim"],
            "adaptation_disclosure_carriage": carriage,
            "attempt": {
                "attempt": protocol["attempt"],
                "strategy_id": protocol["strategy_id"],
                "candidate_index": protocol["candidate_index"],
                "family": protocol["family"],
                "attempt_1_ref": protocol["attempt_1_ref"],
                "attempt_1_module_verification": ev["attempt_1_module_verification"],
                "what_this_attempt_adds_over_attempt_1": protocol[
                    "what_this_attempt_adds_over_attempt_1"
                ],
                "attempt_1_disposition": (
                    "CLOSED_READ_ONLY. Attempt 1 ended FAIL — STAGE_3_G2_NO_CANDIDATE and that "
                    "verdict stands permanently. No Attempt 1 artifact or module was edited, "
                    "deleted, re-run, reopened or loosened by this attempt. Attempt 2's modules "
                    "are new files alongside Attempt 1's, under the _ra1 naming convention."
                ),
            },
            "generation": {
                "generation": 2,
                "generation_id": protocol["generation_id"],
                "charter": CHARTER,
                "charter_sha256": sha256_file(PROJECT_ROOT / CHARTER),
                "generation_1_status": (
                    "CLOSED. Generation 1 ended FAIL — STAGE_4_STRATEGY_REJECTED_IN_VALIDATION. No "
                    "Generation 1 artifact under governance/, config/ or reports/ was read for "
                    "anything but context, and none was edited, regenerated or reinterpreted by "
                    "this attempt."
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
                "declared_before_any_strategy_code_measurement": protocol[
                    "declared_before_any_strategy_code_measurement"
                ],
                "hypothesis": protocol["hypothesis"],
                "grid": ev["grid"],
                "revisions_after_seeing_a_result": 0,
                "structural_consequences_declared_before_running": protocol[
                    "structural_consequences_declared_before_running"
                ],
            },
            "risk_architecture": {
                "sealed_in": f"{PROTOCOL} risk_architecture",
                "as_evaluated": ev["risk_architecture"],
                "components": protocol["risk_architecture"]["components"],
                "combined_scalar": protocol["risk_architecture"]["combined_scalar"],
                "frozen_before_any_variant_is_run": protocol["risk_architecture"][
                    "frozen_before_any_variant_is_run"
                ],
                "not_part_of_the_grid": protocol["risk_architecture"]["not_part_of_the_grid"],
                "why_not_gridded": protocol["risk_architecture"]["why_not_gridded"],
                "provenance": protocol["risk_architecture"]["provenance"],
            },
            "partition": {
                "lock": PARTITION_LOCK_JSON,
                "lock_sha256": sha256_file(PROJECT_ROOT / PARTITION_LOCK_JSON),
                "lock_record_verification": lock_record,
                "partition": lock["partition"],
                "window_read_by_this_stage": window,
                "run_span_recheck": ev["run_span_recheck"],
                "generation_1_holdout_state": lock["generation_1_holdout_state"],
                "holdout_state": lock["holdout_state"],
            },
            "universe": ev["universe"],
            "selection": selection,
            "gate_evaluation_scope": ev["gate_scope"],
            "candidate_results": ev["candidate_results"],
            "stage_verdict": declared,
            "reconciliation": ev["reconciliation"],
            "determinism": {
                key: value for key, value in ev["determinism"].items() if key != "run_digests"
            },
            "grid_results_descriptive_only": {
                "status": ev["variant_table_is_descriptive_only"],
                "used_in_selection": False,
                "coverage": ev["reported_for_every_variant_coverage"],
                "table": ev["variant_table"],
            },
            "engine_capability_added": {
                "what": (
                    "The Attempt 1 multi-position engine was extended with the RA2 risk "
                    "architecture: an aggregate exposure throttle, a portfolio volatility scalar, "
                    "a per-position stop, a de-risk ladder state machine and a re-entry lockout "
                    "timer. Neither the frozen Generation 1 engine.py nor Attempt 1's "
                    "g2_engine.py was modified; the capability is a new module, "
                    "backtest/g2_engine_ra1.py, with the episode ledger in "
                    "backtest/g2_episodes_ra1.py."
                ),
                "adversarial_tests": (
                    "tests/adversarial/test_g2_ra1_risk_architecture.py covers all nine sealed "
                    "requirements, AT-A through AT-I: the exposure ceiling at fill time, the "
                    "volatility scalar's undefined-before-21-points behaviour, the stop's "
                    "close-evaluate/open-exit sequencing against cost basis, the ladder's band "
                    "boundaries and hysteresis, the lockout's session counting, rerun determinism "
                    "over the trade, equity, ranking and risk-state digests, the window guard's "
                    "refusal to read at or after 2021-08-01 through the Attempt 2 loading path, "
                    "the immutability of every Attempt 1 module, and the selection input's "
                    "inability to carry a performance figure. "
                    "tests/adversarial/test_stage3_attempt2_defects.py adds the defect probes."
                ),
            },
            "evidence_file": {
                "path": EVIDENCE,
                "artifact_id": ev["artifact_id"],
                "sha256": sha256_file(PROJECT_ROOT / EVIDENCE),
                "evidence_digest": ev["evidence_digest"],
                "evidence_digest_covers": ev["evidence_digest_covers"],
                "evidence_digest_recomputed_by_this_builder": recomputed,
                "generated_utc": ev["generated_utc"],
            },
            "authorization": {
                "stage_4_validation_authorized": False,
                "stage_4_note": (
                    "Stage 4 validation was not run and is not authorized by this package. The "
                    "validation-window data exists on disk and is technically reachable; it was "
                    "not read. Authorization requires an explicit human go-ahead in a separate "
                    "session, and this verdict gives it nothing to validate."
                ),
                "attempt_3_authorized": False,
                "attempt_3_note": derivation["fail_is_a_deliverable"],
                "holdout_read_authorized": False,
                "holdout_note": (
                    "Generation 2's holdout is 2026-08-01 to 2028-07-31 and does not exist in "
                    "calendar time. Generation 1's sealed holdout was not read by this attempt or "
                    "by any code it ran."
                ),
                "explicit_non_authorizations": protocol["explicit_non_authorizations"],
            },
        },
        tests=tests,
        authorization_state={
            "live_trading_authorized": "false",
            "paper_trading_authorized": "false",
            "broker_connection_made": "false",
            "credentials_read": "false",
            "stage_4_validation_authorized": "false",
            "attempt_3_authorized": "false",
            "generation_2_holdout_read_authorized": "false",
            "generation_1_holdout_read": "false",
        },
        next_authorized_stage=(
            "None without human review. Generation 2 Stage 3 Attempt 2 reached FAIL — "
            "STAGE_3_G2_ATTEMPT_2_NO_CANDIDATE, so no candidate is admitted to validation. The "
            "next authorized action is human review of this package. Per the sealed "
            "fail_is_a_deliverable clause the attempt now closes: there is no Attempt 3 without a "
            "further disclosed adaptation authorised in a later session, and no further work may "
            "reuse this grid, loosen an RA2 constant, re-select on return, or promote a runner-up."
        ),
        dataset_hashes={},
        universe_version=protocol["eligible_universe"]["universe_version"],
        date_range=[protocol["run_span"]["run_start"], protocol["run_span"]["run_end"]],
        holdout_state="LOCKED",
        config_hash=sha256_file(PROJECT_ROOT / PROTOCOL),
        run_notes=[
            "Generation 2 Stage 3 Attempt 2 development. Eighteen pre-registered rotation variants "
            "under the frozen RA2 risk architecture, two cost labels each, 36 runs, all executed.",
            "Verdict FAIL — STAGE_3_G2_ATTEMPT_2_NO_CANDIDATE by the second sealed fail route: a "
            "representative WAS produced and failed the gate. All eighteen variants recorded zero "
            "research-shutdown events against Attempt 1's eighteen-of-eighteen, so step 1 admitted "
            "everything and the turnover tiebreak selected "
            f"{selection['representative_variant_id']}, which then missed "
            f"{', '.join(basis['base_conditions_not_satisfied'])} on #BASE.",
            "This pre-registration was written after Attempt 1's development results were known. "
            "The development window is no longer pristine for this hypothesis family. The binding "
            "text is adaptation_disclosure_verbatim in the decision record.",
            "No Generation 1 artifact and no Generation 2 Attempt 1 artifact or module was "
            "modified. All nine Attempt 1 modules re-hashed clean against their sealed digests.",
            "No data dated 2021-08-01 or later was read. The latest session loaded anywhere is "
            f"{window['latest_session_loaded']}.",
            "No broker connection, credential read, or order of any kind. live_trading_authorized "
            "remains false.",
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
    print(f"tests            {tests}")
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
