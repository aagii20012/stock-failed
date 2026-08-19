"""Generation 2 Stage 3 Attempt 3 decision package — the rotation grid under risk architecture RA3.

Copied in structure from :mod:`g2_stage3_attempt2_package`, which is itself the worked example of the
*portable* guard from :mod:`g2_stage3_package`: it asserts that the verdict written into the package
is the verdict the evidence reached and refuses the incoherent combinations, rather than refusing to
write anything that is not a pass. That distinction matters here for the same reason it mattered
twice before — ``verdict_token_derivation.fail_is_a_deliverable`` in SE100-CFG-3106 says in terms
that a FAIL is a legitimate and fully anticipated outcome that is recorded and kept on disk, so a
pass-only guard would suppress the deliverable the constitution requires.

Attempt 3 sits alongside *two* closed attempts rather than one, and four of this module's checks
follow from that:

* The verdict token is derived from the sealed ``verdict_token_derivation`` and asserted to be one of
  the two Attempt 3 tokens and **none of the four** that belong to Attempts 1 and 2. The four-tuple
  is additionally cross-checked against the seal's own prose and against the evidence's
  ``prior_attempt_tokens_withheld`` list, so a silently shortened constant fails loudly rather than
  quietly permitting a prior attempt's token.
* The 1507-character adaptation disclosure must be carried **byte-exact** by every carrier the seal
  names. Attempt 2 needed a normalisation allowance because its own protocol Markdown hard-wrapped
  the paragraph inside a blockquote (G2A2-CONFLICT-29); Attempt 3's protocol Markdown does not, so
  the allowance here is empty. A paraphrase, and now also a rewrap, is a failure and not a
  stylistic choice.
* The seventeen prior-attempt modules — nine from Attempt 1, eight from Attempt 2 — must not have
  moved. The count is read from the seal, not from a literal here (G2A3-CONFLICT-34).
* The ``repo_state_id`` glob asymmetry that G2A3-CONFLICT-30 records is asserted in **both**
  directions: that this attempt's governance artifacts fall *outside* the patterns and that its
  config artifacts fall *inside* them. A check that only confirms what is expected confirms nothing.

Two further checks have no Attempt 2 counterpart because the things they check are new: the
selection rule is replayed from its recorded six-field inputs (``selection_determinism``), and the
RA3 ladder statistics are compared against Attempt 2's on all thirty-six runs
(``ladder_engagement_comparison``) — a ladder change that changed no ladder statistic would mean the
engine had not actually been modified.

Test counts are parsed from the captured pytest output at build time and never typed in. Decimal
strings are compared as :class:`~decimal.Decimal`, never lexicographically.

Run **last**: this module lives in ``src/``, which ``repo_state_id`` covers, so any later edit to it
invalidates the digest the build recorded and the pytest capture the build parsed.
"""

from __future__ import annotations

import json
import re
from decimal import Decimal
from pathlib import Path
from typing import Any

from stockedge100.audit import sha256_bytes, sha256_file
from stockedge100.reporting.g2_partition_lock import normalised_prose
from stockedge100.reporting.stage_package import (
    PROJECT_ROOT,
    StageDecision,
    build_stage_package,
    repo_state,
    verify_sha256_record,
)

COMMAND = (
    "cd stockedge100 && PYTHONPATH=src python -m "
    "stockedge100.reporting.g2_stage3_attempt3_package"
)

VERDICT = "FAIL — STAGE_3_G2_ATTEMPT_3_NO_CANDIDATE"

EVIDENCE = "reports/stage3_g2_attempt3/STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json"
CRITERIA = "config/generation_2/g2_gate_criteria_ra3.json"
PROTOCOL = "config/generation_2/g2_rotation_ra3_protocol.json"
COST_MODEL = "config/generation_2/g2_cost_model.json"
CHARTER = "governance/generation_2/STAGE_10_GENERATION_2_CHARTER.md"

PARTITION_LOCK_MD = "governance/generation_2/STAGE_1_G2_PARTITION_LOCK.md"
PARTITION_LOCK_JSON = "governance/generation_2/STAGE_1_G2_PARTITION_LOCK.json"
PARTITION_LOCK_RECORD = "governance/generation_2/STAGE_1_G2_PARTITION_LOCK.sha256"

PROTOCOL_MD = "governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.md"
PROTOCOL_JSON = "governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.json"
PROTOCOL_RECORD = "governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.sha256"

# Attempt 1's and Attempt 2's artifacts are frozen inputs to this attempt, read only to prove they
# did not move. They are never written. The sealed digests they are checked against live in the
# Attempt 3 protocol's attempt_1_ref and attempt_2_ref blocks.
ATTEMPT_1_PROTOCOL_MD = "governance/generation_2/STAGE_3_G2_ROTATION_PROTOCOL.md"
ATTEMPT_1_PROTOCOL_JSON = "governance/generation_2/STAGE_3_G2_ROTATION_PROTOCOL.json"
ATTEMPT_1_PROTOCOL_RECORD = "governance/generation_2/STAGE_3_G2_ROTATION_PROTOCOL.sha256"
ATTEMPT_1_REPORT = "governance/generation_2/STAGE_3_G2_ROTATION_RESEARCH_REPORT.md"
ATTEMPT_1_CRITERIA = "config/generation_2/g2_gate_criteria.json"
ATTEMPT_1_PROTOCOL_CONFIG = "config/generation_2/g2_rotation_protocol.json"

ATTEMPT_2_PROTOCOL_MD = "governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.md"
ATTEMPT_2_PROTOCOL_JSON = "governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.json"
ATTEMPT_2_PROTOCOL_RECORD = "governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.sha256"
ATTEMPT_2_REPORT = "governance/generation_2/STAGE_3_G2_ROTATION_RA1_RESEARCH_REPORT.md"
ATTEMPT_2_CRITERIA = "config/generation_2/g2_gate_criteria_ra1.json"
ATTEMPT_2_PROTOCOL_CONFIG = "config/generation_2/g2_rotation_ra1_protocol.json"

# Generation 1's own strategy protocol. RA3's ladder is not a new geometry: it is Generation 1's
# RA1-5 spacing, and this is the file the reversion was read out of. Read-only, and Generation 1 is
# closed.
GENERATION_1_STRATEGY_PROTOCOL = "config/stage3_attempt2_strategy_protocol.json"

REPORT = "governance/generation_2/STAGE_3_G2_ROTATION_RA3_RESEARCH_REPORT.md"
PYTEST_CAPTURE = "reports/stage3_g2_attempt3/pytest_stage3_g2_attempt3_output.txt"

# Eight entries, where Attempt 2 had fifteen. This is a deliberate structural difference and not a
# shortfall: Attempt 3's evidence writer inlines the grid table, the selection inputs, the selection
# record, the gate record, the stage verdict and the prior-attempt module verification into the
# single evidence document rather than emitting them as six separate side files. Recorded in the run
# notes so a reader comparing the two manifests does not read the shorter list as missing work.
PRODUCED = [
    REPORT,
    EVIDENCE,
    "reports/stage3_g2_attempt3/STAGE_3_G2_A3_ROTATION_RESEARCH.json",
    "reports/stage3_g2_attempt3/STAGE_3_G2_A3_ROTATION_RESEARCH.sha256",
    "reports/stage3_g2_attempt3/STAGE_3_G2_A3_ARTIFACT_MANIFEST.json",
    "reports/stage3_g2_attempt3/STAGE_3_G2_A3_TEST_SUMMARY.md",
    PYTEST_CAPTURE,
    # The runner's own output. It sits under reports/, which repo_state_id does not cover, so this
    # package's manifest and checksum record are the only things that hold it.
    "reports/stage3_g2_attempt3/run_span_recheck.json",
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
    ATTEMPT_2_PROTOCOL_MD,
    ATTEMPT_2_PROTOCOL_JSON,
    ATTEMPT_2_PROTOCOL_RECORD,
    ATTEMPT_2_REPORT,
    ATTEMPT_2_PROTOCOL_CONFIG,
    ATTEMPT_2_CRITERIA,
    GENERATION_1_STRATEGY_PROTOCOL,
]

# Named by the seal itself, in verdict_token_derivation.prior_attempt_tokens_are_not_available_here,
# and independently by the evidence in stage_verdict.prior_attempt_tokens_withheld. Both are checked
# against this tuple at build time, so a shortened constant fails rather than silently admitting a
# closed attempt's token.
PRIOR_ATTEMPT_TOKENS = (
    "STAGE_3_G2_STRATEGY_ADMITTED_IN_DEVELOPMENT",
    "STAGE_3_G2_NO_CANDIDATE",
    "STAGE_3_G2_ATTEMPT_2_STRATEGY_ADMITTED_IN_DEVELOPMENT",
    "STAGE_3_G2_ATTEMPT_2_NO_CANDIDATE",
)

# G2A3-CONFLICT-30, asserted in both directions. governance/* is single-level and config/** is
# recursive, so this attempt's subtree splits: the governance artifacts are held by their own
# .sha256 record and this package's manifest alone, while the config artifacts are additionally
# sealed by repo_state_id.
EXPECTED_OUTSIDE_PATTERNS = (REPORT, PROTOCOL_MD, PROTOCOL_JSON, PROTOCOL_RECORD, CHARTER)
EXPECTED_INSIDE_PATTERNS = (PROTOCOL, CRITERIA, COST_MODEL, "README.md")

VERDICT_SEMANTICS = (
    "FAIL — STAGE_3_G2_ATTEMPT_3_NO_CANDIDATE is the second of the two fail routes the sealed rule "
    "anticipated in writing before any variant was run. It is the same route Attempt 2 took and not "
    "the route Attempt 1 took, and the three attempts fail in three different places. Attempt 1 "
    "failed at step 1 of its selection rule: all eighteen variants recorded a research shutdown, no "
    "representative existed, and Gate 3 was never reached. Attempt 2 reached the gate and its "
    "representative missed four conditions — net return, profit factor, best-trade-removed return "
    "and single-instrument concentration — having earned about 0.4% over thirteen years, which is "
    "the signature of an architecture that suppressed ordinary-market return along with crisis "
    "loss. Attempt 3 reached the gate with the throttling demonstrably loosened: zero shutdowns "
    "again, but eighteen of eighteen variants positive on the base run, the representative at "
    "+10.34% base and +8.11% stressed, profit factor above 1.10 on both runs, sixty-two closed "
    "trades, and the best-trade-removed return positive on both. Six of the seven hard conditions "
    "are satisfied on both runs. The single miss is S3-C6, single-instrument concentration, at "
    "0.7505 of total profit on the base run and 0.9772 on the stressed run against a ceiling of "
    "0.50 — a condition whose failure is not reducible to either prior attempt's failure mode. The "
    "token is the same as Attempt 2's route because the seal gives both routes of this attempt the "
    "same token; the route is recorded separately in fail_route and the distinction is the substance "
    "of the result. The verdict is a statement about the representative the frozen return-blind rule "
    "produced, not about the grid's best return: no return figure was an input to the selection, and "
    "the best variant returned +53.41% while the selected one returned +10.34%. The result is a "
    "deliverable and is kept on disk. It does not license promoting a runner-up, re-selecting on "
    "return, loosening a risk constant, widening the grid, a third selection rule, or an Attempt 4."
)


def load(rel: str) -> dict[str, Any]:
    return json.loads((PROJECT_ROOT / rel).read_text(encoding="utf-8"))


def read_text(rel: str) -> str:
    return (PROJECT_ROOT / rel).read_text(encoding="utf-8")


def test_counts(text: str) -> dict[str, int] | None:
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


def pct(value: str | Decimal) -> str:
    """Format a decimal-string fraction as a signed percentage, two places, ASCII sign."""
    quantised = (Decimal(str(value)) * 100).quantize(Decimal("0.01"))
    return f"{quantised:+.2f}%"


def dd_pct(value: str | Decimal) -> str:
    """Format a drawdown as an unsigned magnitude.

    The engine records drawdowns as positive fractions of peak equity, so passing one through
    :func:`pct` yields ``+9.94%`` — which reads as a gain. Drawdowns are magnitudes measured
    against a ``<= 0.15`` ceiling and are printed without a sign.
    """
    return f"{(Decimal(str(value)) * 100).quantize(Decimal('0.01')):.2f}%"


def disclosure_carriage(protocol: dict[str, Any], ev: dict[str, Any]) -> dict[str, Any]:
    """Check the adaptation disclosure is carried by every carrier the seal names.

    The string is never printed: the seal's ``encoding_note`` forbids writing it to a cp1252 console
    and doing so would raise ``UnicodeEncodeError`` mid-build. Only digests and lengths surface.

    JSON carriers are compared as *decoded values*, because a JSON file stores the string escaped;
    comparing the raw bytes of a JSON file against the raw string would report a false mismatch for
    the em-dashes and the minus sign.

    Markdown carriers are held to byte-equality outright. Attempt 2 could not do that: its own
    protocol Markdown hard-wrapped the paragraph inside a blockquote and stored 858 characters where
    the sealed string was 842, which is what G2A2-CONFLICT-29 records and why that builder relaxed
    to the sealer's own :func:`normalised_prose` for one named artifact. Attempt 3's protocol
    Markdown stores the paragraph unwrapped, so no relaxation is warranted and the guard below
    permits none. ``normalised_prose`` is still imported and still evaluated, so a carrier that
    needs it is *detected* rather than silently accepted — the difference from Attempt 2 is that
    detection is a failure here, not an allowance.
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
                else "NOT byte-exact: equal only under the sealer's normalised_prose, which for "
                "Attempt 3 is a guard failure. G2A2-CONFLICT-29's allowance was scoped to "
                "Attempt 2's own protocol Markdown and does not extend here."
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
        "normalisation_allowance": (
            "empty. Every Markdown carrier of this attempt stores the paragraph unwrapped, so the "
            "builder requires byte-equality from all of them. reporting.g2_partition_lock."
            "normalised_prose is imported from the module the sealer itself used and is still "
            "evaluated, so a rewrapped carrier is reported as carrying the disclosure in substance "
            "while failing the byte check — and the guard refuses that combination rather than "
            "accepting it."
        ),
        "note": (
            "The decision record this package writes is itself one of the carriers, so it is "
            "listed here as absent at check time and carries the string in "
            "adaptation_disclosure_verbatim below. The post-build verification re-reads it."
        ),
    }


def pattern_membership() -> dict[str, Any]:
    """G2A3-CONFLICT-30, checked in both directions rather than asserted in prose.

    ``repo_state()`` returns the exact set of paths ``repo_state_id`` is computed over. The claim
    being checked is that this attempt's *governance* artifacts are not in it — so the only things
    holding them are their own ``.sha256`` record and this package's manifest — while its *config*
    artifacts are. Confirming only the first half would confirm nothing: a bug that returned an
    empty set would pass it.

    The digest itself is deliberately not recorded here. It would be a tree digest computed before
    the build, embedded in a document the build then writes, and the authoritative value is the
    ``repo_state_id`` the builder records in the decision record and the ``runs/`` record.
    """
    covered, _digest = repo_state()
    keys = set(covered)
    outside = {rel: rel not in keys for rel in EXPECTED_OUTSIDE_PATTERNS}
    inside = {rel: rel in keys for rel in EXPECTED_INSIDE_PATTERNS}
    return {
        "conflict_ref": "G2A3-CONFLICT-30",
        "covered_path_count": len(keys),
        "patterns": (
            "governance/*.{md,json,sha256} (single-level), src/**/*.py, tests/**/*.py, "
            "config/**/*.{json,yaml} (recursive), pyproject.toml, README.md, .gitignore"
        ),
        "expected_outside": outside,
        "expected_inside": inside,
        "all_outside_as_expected": all(outside.values()),
        "all_inside_as_expected": all(inside.values()),
        "consequence": (
            "This attempt's governance subtree is held by "
            f"{PROTOCOL_RECORD} and this package's artifact manifest alone; repo_state_id will not "
            "notice if it drifts. Its config subtree is additionally sealed by repo_state_id and by "
            "every earlier stage's digest. The asymmetry is a property of sealed patterns and is "
            "reported, not repaired: widening the globs would invalidate every digest that already "
            "covers them."
        ),
        "digest_recorded_where": (
            "the decision record's repo_state_id field and the appended runs/ record, never in a "
            "governance document that would then be part of the tree it digests"
        ),
    }


def gate_conditions(ev: dict[str, Any], criteria: dict[str, Any]) -> dict[str, Any]:
    """The seven hard conditions as actually evaluated, plus the one row that decides the gate.

    Aggregation is on ``satisfied``, not on ``verdict == "MET"``. The two coincide for every row of
    this attempt — nothing came back ``NOT_APPLICABLE_BY_CONDITION_TEXT`` — but aggregating on MET
    is the bug that produced a false FAIL for S3-C6 in Generation 1 Stage 3, and a table that would
    have been wrong under different evidence is not a table worth writing.

    The gating scope per condition comes from the sealed resolution of G2A2-CONFLICT-25 recorded in
    ``admission_basis`` and inherited here unchanged: all seven on ``#BASE``, and S3-C1..S3-C6 also
    on ``#STRESS``. S3-C7's stress side is measured and reported and gates nothing, because its own
    ``what_is_read`` fixes the neighbour comparison to base-run total return.
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
    result = selection["result"]
    score = selection["selected_score"]
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
        "variants_declared": ev["grid"]["variants_declared"],
        "variants_eligible_after_shutdown_screen": result["eligible_count"],
        "candidates_evaluated": ev["stage_verdict"]["candidates_evaluated"],
        "admitted_candidates": admitted,
        "representative": result["selected_variant_id"],
        "selection_rule": selection["rule_id"],
        "selection_decided_at_step": selection["decided_at_step"],
        "conditions_not_satisfied_base": basis["base_conditions_not_satisfied"],
        "conditions_not_satisfied_stress": basis["stress_conditions_not_satisfied"],
        "permissive_base_only_reading_would_give": basis[
            "permissive_base_only_reading_would_give"
        ],
        "determination": (
            "This entry, and only this entry, is the gate determination. All "
            f"{ev['grid']['variants_declared']} declared variants survived step 1 of the frozen "
            "selection rule, as in Attempt 2 and unlike Attempt 1 where none did, and SE100-G2-SEL-2 "
            f"decided at step {selection['decided_at_step']} — the neighbourhood-instability score, "
            f"not the turnover tiebreak — producing {result['selected_variant_id']} with an "
            f"instability score of {score['instability_score']} over {score['neighbour_count']} "
            "neighbours. Gate 3 was reached, evaluated, and not satisfied: "
            f"{', '.join(basis['base_conditions_not_satisfied'])} failed on #BASE and "
            f"{', '.join(basis['stress_conditions_not_satisfied'])} on #STRESS. The restrictive "
            "reading of G2A2-CONFLICT-25 did not decide this outcome — the permissive base-only "
            "reading would have given "
            f"{basis['permissive_base_only_reading_would_give']}."
        ),
        "note": (
            "A conditions table that omits this row reads as though the gate were irrelevant "
            "rather than decided. The seven rows above settle nothing on their own: gates are "
            "conjunctive within a candidate and the stage verdict is a disjunction across "
            "candidates, and here the candidate set has one member, which failed — see "
            "G2A3-CONFLICT-24. Promoting a runner-up would convert a return-blind selection into a "
            "search over eighteen candidates for one that passes; the seal forbids it and so does "
            "this package. The runner-up's instability score was within 0.000048608 of the "
            "selected variant's, which makes the prohibition matter more here than in Attempt 2, "
            "not less."
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
        print("TOKEN IS NOT ONE OF THE TWO SEALED ATTEMPT 3 TOKENS — no package written")
        return 3
    if token in PRIOR_ATTEMPT_TOKENS:
        print("TOKEN BELONGS TO A CLOSED PRIOR ATTEMPT — no package written")
        return 3
    # The four-tuple is checked against the seal's prose and against the evidence's own withheld
    # list, so a silently shortened constant fails here instead of quietly permitting a token.
    prose = derivation["prior_attempt_tokens_are_not_available_here"]
    unnamed = [name for name in PRIOR_ATTEMPT_TOKENS if name not in prose]
    if unnamed:
        print(f"SEAL DOES NOT NAME PROHIBITED TOKENS {unnamed} — no package written")
        return 3
    if set(declared["prior_attempt_tokens_withheld"]) != set(PRIOR_ATTEMPT_TOKENS):
        print(
            "EVIDENCE WITHHELD-TOKEN LIST DISAGREES WITH THE BUILDER'S — "
            f"{sorted(declared['prior_attempt_tokens_withheld'])} — no package written"
        )
        return 3
    if declared["verdict"] == "FAIL" and declared["admitted_candidates"]:
        print("EVIDENCE REPORTS A FAIL WITH ADMITTED CANDIDATES — no package written")
        return 3
    if declared["verdict"] == "PASS" and not declared["admitted_candidates"]:
        print("EVIDENCE REPORTS A PASS WITH NO ADMITTED CANDIDATE — no package written")
        return 3
    selection = ev["selection"]
    if declared["representative_exists"] != (selection["outcome"] == "representative_selected"):
        print("VERDICT AND SELECTION DISAGREE ON THE REPRESENTATIVE — no package written")
        return 3
    if not selection["return_blind"]:
        print("SELECTION DOES NOT DECLARE ITSELF RETURN-BLIND — no package written")
        return 3
    if not ev["determinism"]["all_identical"]:
        print("EVIDENCE REPORTS A NON-DETERMINISTIC RERUN — no package written")
        return 3
    # New in Attempt 3: the selection rule itself is replayed from its recorded six-field inputs.
    if not ev["selection_determinism"]["all_identical"]:
        print("SELECTION RULE DID NOT REPRODUCE ON REPLAY — no package written")
        return 3
    # Also new: a ladder change that changed no ladder statistic would mean the engine was not
    # actually modified, and the whole attempt would be a re-run of Attempt 2 under a new name.
    if not ev["ladder_engagement_comparison"]["at_least_one_statistic_differs"]:
        print("RA3 LADDER STATISTICS ARE IDENTICAL TO ATTEMPT 2'S — no package written")
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
    if ev["prior_attempt_module_verification"]["modules_that_moved"]:
        print("A CLOSED ATTEMPT'S MODULE MOVED — no package written")
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
    pending_carrier = "reports/stage3_g2_attempt3/STAGE_3_G2_A3_ROTATION_RESEARCH.json"
    missing = [
        rel
        for rel, state in carriage["carriers"].items()
        if not state["carries_verbatim"] and rel != pending_carrier
    ]
    if missing:
        print(f"DISCLOSURE NOT CARRIED VERBATIM BY: {missing} — no package written")
        return 3
    # Attempt 2 allowed exactly one hard-wrapped Markdown carrier (G2A2-CONFLICT-29). Attempt 3
    # allows none: every carrier of this attempt stores the paragraph unwrapped, so any carrier that
    # needs normalisation is a rewrap that has to be fixed before the package is written.
    relaxed = set(carriage["carriers_requiring_normalisation"])
    if relaxed:
        print(f"DISCLOSURE NEEDED PROSE NORMALISATION IN: {sorted(relaxed)} — no package written")
        return 3
    not_byte_exact = [
        rel
        for rel, state in carriage["carriers"].items()
        if not state["carries_byte_exact"] and rel != pending_carrier
    ]
    if not_byte_exact:
        print(f"DISCLOSURE NOT BYTE-EXACT IN: {not_byte_exact} — no package written")
        return 3

    # ---- integrity of every seal this stage stood on ---------------------------------------
    # All four Generation 2 records list project-root-relative paths. Only the STAGE_0/STAGE_1
    # *freeze* records use bare filenames and must be verified from governance/; passing the wrong
    # root there is an operator error that reads as an integrity failure, which is why the root is
    # explicit.
    lock_record = verify_sha256_record(PROJECT_ROOT / PARTITION_LOCK_RECORD, PROJECT_ROOT)
    protocol_record = verify_sha256_record(PROJECT_ROOT / PROTOCOL_RECORD, PROJECT_ROOT)
    attempt_1_record = verify_sha256_record(
        PROJECT_ROOT / ATTEMPT_1_PROTOCOL_RECORD, PROJECT_ROOT
    )
    attempt_2_record = verify_sha256_record(
        PROJECT_ROOT / ATTEMPT_2_PROTOCOL_RECORD, PROJECT_ROOT
    )
    records = {
        PARTITION_LOCK_RECORD: lock_record,
        PROTOCOL_RECORD: protocol_record,
        ATTEMPT_1_PROTOCOL_RECORD: attempt_1_record,
        ATTEMPT_2_PROTOCOL_RECORD: attempt_2_record,
    }
    failed_records = {
        rel: rec for rel, rec in records.items() if set(rec.values()) != {"OK"}
    }
    if failed_records:
        print(f"A GENERATION 2 FREEZE RECORD FAILED: {failed_records}")
        return 3

    # ---- G2A3-CONFLICT-30, both directions --------------------------------------------------
    membership = pattern_membership()
    if not membership["all_outside_as_expected"]:
        print(
            "A GOVERNANCE ARTIFACT IS INSIDE THE repo_state_id PATTERNS: "
            f"{membership['expected_outside']} — no package written"
        )
        return 3
    if not membership["all_inside_as_expected"]:
        print(
            "A CONFIG ARTIFACT IS OUTSIDE THE repo_state_id PATTERNS: "
            f"{membership['expected_inside']} — no package written"
        )
        return 3

    # ---- test counts, parsed from the capture on disk ---------------------------------------
    tests = test_counts(read_text(PYTEST_CAPTURE))
    if tests is None:
        print(f"COULD NOT PARSE {PYTEST_CAPTURE} — no package written")
        return 3
    if tests["failed"] != 1 or tests["errors"]:
        print(f"UNEXPECTED TEST RESULT {tests} — exactly one designed failure is expected")
        return 3

    candidate = ev["candidate_results"][0]
    basis = candidate["admission_basis"]
    result = selection["result"]
    score = selection["selected_score"]
    ladder = ev["ladder_engagement_comparison"]
    table = ev["variant_table"]
    modules = ev["prior_attempt_module_verification"]
    mcd = ev["multiple_comparisons_disclosure"]

    # Decimal, not lexicographic: these are 20-to-34 digit decimal strings and string comparison
    # would order 0.09 above 0.14.
    base_returns = [Decimal(row["base_total_return"]) for row in table]
    stress_returns = [Decimal(row["stress_total_return"]) for row in table]
    base_dd = [Decimal(row["base_max_drawdown"]) for row in table]
    stress_dd = [Decimal(row["stress_max_drawdown"]) for row in table]
    base_positive = sum(1 for value in base_returns if value > 0)
    stress_positive = sum(1 for value in stress_returns if value > 0)
    best_base = max(table, key=lambda row: Decimal(row["base_total_return"]))
    shutdowns = sum(int(row["research_shutdown_events"]) for row in table)

    # The runner-up comes from the ranking, which is ordered, and not from ``neighbour_scores`` —
    # that list holds the representative's *neighbours*, and it only coincidentally begins with the
    # second-ranked variant. Reading the margin off a neighbour list would be right by accident here
    # and wrong the moment the geometry changed.
    ranking = result["ranking"]
    if ranking[0]["variant_id"] != result["selected_variant_id"]:
        print("RANKING HEAD IS NOT THE SELECTED VARIANT — selection record is incoherent")
        return 3
    runner_up = ranking[1]
    selection_margin = Decimal(runner_up["instability_score"]) - Decimal(
        score["instability_score"]
    )

    decision = StageDecision(
        stage="STAGE_3_G2_ATTEMPT_3_ROTATION_RA3_DEVELOPMENT",
        stage_slug="stage3_g2_attempt3",
        decision_basename="STAGE_3_G2_A3_ROTATION_RESEARCH",
        manifest_basename="STAGE_3_G2_A3_ARTIFACT_MANIFEST",
        gate_id=ev["gate"]["constitution_gate_id"],
        gate_name=ev["gate"]["name"],
        verdict=VERDICT,
        gate_passed=False,
        command=COMMAND,
        generation=2,
        gate_conditions=gate_conditions(ev, criteria),
        evidence=[
            "Grid, run in full and unrevised: "
            f"{ev['grid']['variants_declared']} declared variants x "
            f"{ev['grid']['runs_per_variant']['count']} cost scenarios "
            f"({', '.join(ev['grid']['runs_per_variant']['labels'])}) = "
            f"{ev['grid']['runs_executed']} runs executed, "
            f"all_declared_runs_executed={ev['grid']['all_declared_runs_executed']}, "
            f"grid_widened_from_attempt_1={ev['grid']['grid_widened_from_attempt_1']}, "
            f"grid_widened_from_attempt_2={ev['grid']['grid_widened_from_attempt_2']}, "
            f"revisions_after_seeing_a_result={ev['grid']['revisions_after_seeing_a_result']}. "
            "The axes are Attempt 2's unchanged: lookback in {3, 6, 12} months, k in {1, 2, 3}, "
            "rebalance in {monthly, quarterly}.",

            "Risk architecture RA3, loaded from SE100-CFG-3105 and frozen before the first variant "
            f"ran: exposure ceiling {ev['risk_architecture']['as_loaded']['exposure_ceiling']} of "
            "equity, volatility target "
            f"{ev['risk_architecture']['as_loaded']['volatility_target']} annualised over "
            f"{ev['risk_architecture']['as_loaded']['volatility_window_bars']} bars, per-position "
            f"stop {ev['risk_architecture']['as_loaded']['stop_fraction']}, re-entry lockout "
            f"{ev['risk_architecture']['as_loaded']['lockout_sessions']} sessions, de-risk ladder "
            "with bands "
            + "; ".join(
                f"[{band['dd_from']}, "
                f"{'inf' if band['dd_to_exclusive'] is None else band['dd_to_exclusive']}) -> "
                f"scalar {band['scalar']}"
                for band in ev["risk_architecture"]["as_loaded"]["bands"]
            )
            + ". The single difference from RA2 is the removal of one ladder rung: "
            f"bands_removed_from_ra2={ev['risk_architecture']['single_difference_from_ra2']['bands_removed_from_ra2']}, "
            f"bands_added_by_ra3={ev['risk_architecture']['single_difference_from_ra2']['bands_added_by_ra3']}. "
            "The four other mechanisms are byte-identical constants.",

            "RA3's ladder is Generation 1's own RA1-5 spacing, not a third invented geometry. The "
            "evidence records the reversion as read out of "
            f"{ev['risk_architecture']['generation_1_provenance']['generation_1_protocol']}, with "
            "generation_1_states_it_twice_and_they_agree="
            f"{ev['risk_architecture']['generation_1_provenance']['generation_1_states_it_twice_and_they_agree']} "
            "and ladders_are_identical="
            f"{ev['risk_architecture']['generation_1_provenance']['ladders_are_identical']} after "
            "converting Generation 1's absolute caps by the "
            f"{ev['risk_architecture']['generation_1_provenance']['exposure_ceiling_used_to_convert']} "
            "exposure ceiling.",

            "The ladder change is measurable, not nominal. Across all "
            f"{ladder['runs_compared']} runs, compared against "
            f"{ladder['attempt_2_source']}: "
            + "; ".join(
                f"{name} {stat['attempt_3_total']} vs {stat['attempt_2_total']} "
                f"({stat['runs_differing']} runs differ)"
                for name, stat in ladder["per_statistic"].items()
            )
            + f". runs_identical_on_every_compared_statistic="
            f"{ladder['runs_identical_on_every_compared_statistic']}. Sessions at full sizing rose "
            "and every throttling statistic fell, which is the declared direction of the change.",

            f"Selection: {selection['rule_id']}, sourced from {selection['rule_source']}, "
            f"return_blind={selection['return_blind']}. Its inputs are exactly the six fields "
            f"{selection['selection_input_fields']}, structurally enforced by a frozen dataclass "
            "asserted at import time; no return, drawdown, profit factor or Sharpe figure is "
            "reachable from the scorer. Step 1 (zero research-shutdown events across both runs) "
            f"admitted {result['eligible_count']} of {ev['grid']['variants_declared']} variants, "
            f"with ineligible_variants={result['ineligible_variants']}. The decision was made at "
            f"step {selection['decided_at_step']} "
            f"({selection['steps'][selection['decided_at_step'] - 1]['criterion']}), so the "
            "turnover tiebreak that decided Attempt 2 was never reached.",

            f"Representative: {result['selected_variant_id']}, instability score "
            f"{score['instability_score']} over {score['neighbour_count']} neighbours, from own "
            f"quantities {score['own_quantities']} and per-quantity mean dissimilarities "
            f"{score['per_quantity_mean_dissimilarity']}. The runner-up, taken from position 2 of "
            f"the ranking rather than from the neighbour list, is {runner_up['variant_id']} at "
            f"{runner_up['instability_score']} — a margin of {selection_margin}, which is disclosed "
            "rather than smoothed over. "
            f"per_quantity_pairs_zero_on_both_sides={score['per_quantity_pairs_zero_on_both_sides']} "
            "for the representative, so the G2A3-CONFLICT-32 denominator-floor degeneracy did not "
            "bear on this selection.",

            "Selection determinism, new in this attempt: "
            f"{ev['selection_determinism']['inputs_replayed']} recorded six-field inputs were "
            "rebuilt from JSON and rescored on a fresh call with the run objects withheld — "
            f"selected_variant_identical={ev['selection_determinism']['selected_variant_identical']}, "
            f"decided_at_step_identical={ev['selection_determinism']['decided_at_step_identical']}, "
            f"eligible_set_identical={ev['selection_determinism']['eligible_set_identical']}, "
            f"ranking_identical={ev['selection_determinism']['ranking_identical']}, "
            f"scores_identical={ev['selection_determinism']['scores_identical']}, "
            f"variants_whose_scores_differ="
            f"{ev['selection_determinism']['variants_whose_scores_differ']}.",

            "Gate 3 on the representative, both runs, restrictive reading of G2A2-CONFLICT-25: "
            f"base_all_seven_satisfied={basis['base_all_seven_satisfied']}, "
            f"stress_first_six_satisfied={basis['stress_first_six_satisfied']}, "
            f"base_conditions_not_satisfied={basis['base_conditions_not_satisfied']}, "
            f"stress_conditions_not_satisfied={basis['stress_conditions_not_satisfied']}, "
            f"aggregated_on={basis['aggregated_on']}. The sole miss on both runs is S3-C6, "
            "single-instrument concentration: "
            f"{candidate['conditions'][5]['measured']} on #BASE and "
            f"{candidate['stress_evaluation']['conditions'][5]['measured']} on #STRESS against a "
            f"ceiling of {candidate['conditions'][5]['threshold']}. The permissive base-only "
            "reading would have given "
            f"{basis['permissive_base_only_reading_would_give']}, so the conflict resolution did "
            "not decide the verdict.",

            "The representative's measured figures, all six satisfied conditions included: total "
            f"return {pct(candidate['conditions'][0]['measured'])} base and "
            f"{pct(candidate['stress_evaluation']['conditions'][0]['measured'])} stressed; maximum "
            f"drawdown {dd_pct(candidate['conditions'][1]['measured'])} base and "
            f"{dd_pct(candidate['stress_evaluation']['conditions'][1]['measured'])} stressed against a "
            "15% limit; profit factor "
            f"{candidate['conditions'][2]['measured']} base and "
            f"{candidate['stress_evaluation']['conditions'][2]['measured']} stressed against 1.10; "
            f"closed trades {candidate['conditions'][3]['measured']} against 30; "
            f"best-trade-removed return {candidate['conditions'][4]['measured']} base; neighbour "
            f"sign agreement {candidate['conditions'][6]['measured']}.",

            "Grid-wide, descriptive only and no input to any decision: "
            f"{base_positive} of {len(table)} variants returned positive on the base run and "
            f"{stress_positive} of {len(table)} on the stressed run; base total return ranged "
            f"{pct(min(base_returns))} to {pct(max(base_returns))} and stressed "
            f"{pct(min(stress_returns))} to {pct(max(stress_returns))}; deepest maximum drawdown "
            f"{dd_pct(max(base_dd))} base and {dd_pct(max(stress_dd))} stressed, both inside the 15% "
            f"limit; research_shutdown_events summed to {shutdowns} across all "
            f"{len(table)} variants. The best base return was "
            f"{pct(best_base['base_total_return'])} at {best_base['variant_id']}, which is not the "
            "representative and was never eligible to become one.",

            f"Window guard: latest session loaded {window['latest_session_loaded']}, development "
            f"bound {window['development_bound']}, run span "
            f"{window['run_span']['run_start']} to {window['run_span']['run_end']} over "
            f"{window['run_span']['sessions']} sessions, binding symbol "
            f"{window['run_span']['binding_symbol']} (inception "
            f"{window['run_span']['binding_symbol_inception']}). "
            f"validation_read={window['validation_read']}, "
            f"generation_1_holdout_read={window['generation_1_holdout_read']}, "
            f"generation_2_holdout_read={window['generation_2_holdout_read']}. The run span was "
            "recomputed from the loaded series before the first variant ran and asserted equal to "
            f"the sealed value, written to {ev['run_span_recheck']['written_to']} with "
            f"differences={ev['run_span_recheck']['differences']}.",

            f"Reconciliation: {ev['reconciliation']['runs_reconciled']} runs, "
            f"{ev['reconciliation']['single_leg_compared_total']} single legs compared, "
            f"mismatches_total={ev['reconciliation']['mismatches_total']}, "
            f"vacuous_runs={ev['reconciliation']['vacuous_runs']}. Determinism: "
            f"{ev['determinism']['runs_compared']} runs re-executed and compared on "
            f"{len(ev['determinism']['fields_compared'])} fields including four content digests, "
            f"all_identical={ev['determinism']['all_identical']}.",

            "Immutability of the two closed attempts, re-hashed rather than asserted: "
            f"{modules['module_count']} modules verified "
            f"({modules['attempt_1_module_count']} from Attempt 1, "
            f"{modules['attempt_2_module_count']} from Attempt 2), "
            f"modules_that_moved={modules['modules_that_moved']}, digest source "
            f"{modules['digest_source']}. {modules['excluded_and_why']}",

            "Adaptation disclosure carriage: the sealed paragraph is "
            f"{carriage['characters']} characters with sha256 {carriage['sha256_of_utf8']}, "
            f"agreeing with the evidence ({carriage['digest_agrees_with_evidence']}). "
            f"all_carriers_verbatim={carriage['all_carriers_verbatim']}, "
            f"carriers_requiring_normalisation={carriage['carriers_requiring_normalisation']} — "
            "empty, unlike Attempt 2, because every Markdown carrier of this attempt stores the "
            "paragraph unwrapped. The decision record this build writes is the fifth carrier and is "
            "necessarily absent at check time.",

            f"Evidence self-digest {ev['evidence_digest']} recomputed from the written file before "
            f"the build, over {ev['evidence_digest_covers']}. The four Generation 2 checksum "
            "records that this attempt stands on — the partition lock, the RA3 protocol, and both "
            "closed attempts' protocols — re-verified to OK on every listed path.",

            "G2A3-CONFLICT-30, asserted in both directions: of "
            f"{membership['covered_path_count']} paths inside the repo_state_id patterns, "
            f"this attempt's governance artifacts are absent "
            f"({membership['all_outside_as_expected']}) and its config artifacts are present "
            f"({membership['all_inside_as_expected']}). The governance subtree is therefore held by "
            "its own checksum record and this package's manifest alone.",

            f"Tests: {tests['collected']} collected, {tests['passed']} passed, {tests['failed']} "
            f"failed, {tests['skipped']} skipped, {tests['errors']} errors, parsed from "
            f"{PYTEST_CAPTURE} at build time. The single failure is Generation 1's permanent "
            "S4-CONFLICT-7 marker, "
            "tests/unit/test_stage4_preregistration.py::"
            "test_no_stage_4_module_can_reach_restricted_data_or_a_broker, which is designed to "
            "stay red and was not touched.",
        ],
        limitations=[
            protocol["adaptation_disclosure_verbatim"],
            lock["validation_reuse_disclosure"],
            protocol["multiple_comparisons_disclosure"]["adaptive_design_note"],
            "Cumulative multiplicity across the hypothesis family now stands at "
            f"{mcd['cumulative_variants_this_hypothesis_family']} variants and "
            f"{mcd['cumulative_runs_this_hypothesis_family']} runs over three attempts, with no "
            "multiplicity correction applied at any of them. Any final assessment of this family "
            "must carry that figure, and it is large enough that a marginal pass at a later attempt "
            "would not be interpretable.",
            "This attempt cannot isolate cause even though it failed. Two things changed at once — "
            "the ladder reverted to Generation 1's spacing and the selection rule was replaced — so "
            "the observed recovery of ordinary-market return (18 of 18 variants positive on base, "
            "against Attempt 2's representative at about 0.4%) is attributable to the pair and not "
            "to either change alone. The ladder statistics establish that RA3 throttled less; they "
            "do not establish that the throttle was the whole of Attempt 2's problem.",
            "The failing condition is one no risk-architecture change addresses. S3-C6 measures "
            "how concentrated the profit is in a single instrument, and a top-k relative-strength "
            "rotation over 34 ETFs with k=2 will concentrate whenever one instrument dominates the "
            "ranking for long stretches. Nothing in RA3 or SEL-2 was designed to affect it, and "
            "nothing in this attempt's evidence suggests a variant that would satisfy it exists in "
            "this grid.",
            "The representative was selected by a margin of 0.000048608 in instability score over "
            "the runner-up. The rule is deterministic and the margin is real, but a difference that "
            "small means the selection is sensitive to any future change in how the four counters "
            "are computed. It is recorded here so a later reader does not treat the choice as "
            "robustly separated.",
            "SEL-2's degenerate case, declared before the run as SC-7, partly obtained: three of "
            "the four scored quantities are small integers on this grid and fill_count dominates "
            "the score, which makes SEL-2 closer to Attempt 2's turnover rule than its description "
            "suggests. The per-quantity components are reported so this is visible rather than "
            "inferred, and the rule was not reweighted after the fact.",
            "Development-window evidence only. Nothing here has been validated, and the Generation "
            "2 validation window has never been read by this attempt. Generation 1's validation "
            "read is spent, Generation 1's holdout is spent and prohibited, and Generation 2's "
            "holdout is sealed. A development FAIL says nothing about out-of-sample behaviour "
            "because there is no out-of-sample evidence to say it with.",
            "Costs, slippage and the minimum-notional throttle are modelled, not observed. No order "
            "was ever placed, no broker or credential was reachable from any module in this "
            "attempt, and the fills are the engine's own simulation under a frozen cost model.",
        ],
        blockers=[],
        conflicts_found=[
            "G2A3-CONFLICT-19 (supersedes G2A2-CONFLICT-18's scope): one of RA2's three ladder "
            "rungs is gone, so the engineered component of any MET verdict here is smaller than "
            "Attempt 2's by exactly that rung and no more. Recorded in the sealed criteria before "
            "the run.",
            "G2A3-CONFLICT-21: the Attempt 3 operating instruction names no verdict token at all, "
            "which is a change from both prior attempts. The token was therefore derived from "
            f"{CRITERIA}'s verdict_token_derivation, which is the disk, and this builder asserts "
            "the derived string against the evidence's own rather than restating a literal.",
            "G2A3-CONFLICT-22: across three attempts the same hypothesis family has now been run "
            "under three ladder geometries — none at all, 5/8/10, and 8/10 — which is a search over "
            "risk architectures and not a robustness test of one. Disclosed, not repaired.",
            "G2A3-CONFLICT-24: candidate index 3 is the only live candidate, so the constitution's "
            "cross-candidate disjunction is taken over a one-member set. The gate is decided by the "
            "admissible_candidate_exists row alone and the seven condition rows settle nothing on "
            "their own.",
            "G2A2-CONFLICT-25, inherited and resolved the same way: SE100-CFG-3105 scopes the gate "
            "across both runs while SE100-CFG-3106 lists the stress run as reported-but-not-gating "
            "for S3-C1 and S3-C4. Neither outranks the other, so the more restrictive reading "
            "governs and both readings are reported in full. Here the readings agree — "
            f"permissive_base_only_reading_would_give={basis['permissive_base_only_reading_would_give']}.",
            "G2A3-CONFLICT-26: SEL-2 reads dispersion across a neighbourhood where Attempt 2's rule "
            "read a level, and the sealed protocol states plainly that Attempt 2's rule was the "
            "more conservative of the two. This is the reason Attempt 3 required its own "
            "pre-registration rather than a re-run.",
            "G2A3-CONFLICT-27: the operating instruction describes neighbourhoods of 2, 3 or 4 "
            "variants; the sealed geometry on this grid gives 3, 4 or 5, and the representative has "
            f"{score['neighbour_count']}. The sealed geometry governs and the instruction's counts "
            "are not repeated as fact anywhere in this package.",
            "G2A3-CONFLICT-28: SE100-CFG-3103's closure sentence is satisfied by the operating "
            "instruction, which authorizes one attempt and no more.",
            "G2A3-CONFLICT-29: removing a rung moves RA3 strictly toward Attempt 1 on the one axis "
            "that produced Attempt 1's failure mode, so a larger drawdown was the declared cost of "
            "the change. The outcome was that no variant breached the research shutdown and the "
            "deepest maximum drawdown was "
            f"{dd_pct(max(max(base_dd), max(stress_dd)))} against a 15% limit — the declared risk "
            "did "
            "not materialise, which is a result and not a vindication of the reasoning.",
            "G2A3-CONFLICT-30: governance/* is single-level and config/** is recursive, so this "
            "attempt's subtree splits down the middle. Both directions are asserted at build time "
            "and both hold; widening the patterns is not available because the patterns are "
            "themselves sealed by every earlier stage's digest.",
            "G2A3-CONFLICT-31: RotationEngineRA3 subclasses RotationEngineRA1 and re-derives "
            "exactly the risk and sessions-in-band state, which an AST test enforces. The "
            "subclassing reads the closed module without modifying it.",
            "G2A3-CONFLICT-32: the dissimilarity denominator carries a floor of 1, so a pair that "
            "is zero on both sides scores 0 rather than dividing by zero. Disclosed, not repaired; "
            "for the selected representative no pair was zero on both sides.",
            "G2A3-CONFLICT-33: this is the third disclosed adaptation on one hypothesis family, and "
            "a PASS here would not on its own have distinguished which of the two changes produced "
            "it. The attempt failed, so the question is moot for this result and remains live for "
            "the family.",
            "G2A3-CONFLICT-34: seventeen prior-attempt modules are held immutable, not the nine the "
            f"operating instruction implies. The count is read from the seal ({modules['module_count']}) "
            "rather than typed here, so a silently shortened list fails loudly.",
            "G2A3-CONFLICT-35 (supersedes G2A2-CONFLICT-6's scope): this pre-registration was "
            "written after TWO attempts' development results were known, and both of its changes "
            "were chosen in response to the second. Pre-registration constrains what happens after "
            "the seal; it cannot undo what was known before. The adaptation is disclosed verbatim in "
            "five carriers and the multiplicity is quantified as "
            f"{protocol['multiple_comparisons_disclosure']['cumulative_variants_this_hypothesis_family']} "
            "variants and "
            f"{protocol['multiple_comparisons_disclosure']['cumulative_runs_this_hypothesis_family']} "
            "runs on one hypothesis family, with no threshold adjusted in either direction to "
            "compensate.",
            "G2A3-CONFLICT-36: both fail routes of this attempt emit the same token, so the route "
            f"is recorded separately — fail_route={declared['fail_route']}, which is the "
            "gate-reached-and-missed route and not Attempt 1's no-representative route.",
            "G2A3-CONFLICT-37 (supersedes G2A2-CONFLICT-8's scope): Attempt 2's operating prompt "
            "named verdict tokens that existed in no artifact. Attempt 3's names none at all and "
            "directs that the sealed criteria file be grepped instead, so the prompt and the sealed "
            "derivation cannot disagree - the failure mode is removed rather than resolved a second "
            f"time. The tokens are minted once, in {CRITERIA}'s verdict_token_derivation, and the "
            "four belonging to Attempts 1 and 2 are asserted absent from every Attempt 3 verdict "
            "field.",
            "G2A3-CONFLICT-38: Attempt 2's sealed pre-registration states that no Attempt 3 is "
            "authorized. A stage artifact's self-imposed closure rule is not a constitutional "
            "provision and does not outrank the operator; what it does outrank is a silent "
            "reopening, which is not what happened — the adaptation is disclosed verbatim in five "
            "carriers and this package carries it in the sixth.",
            "G2A3-CONFLICT-39: the sealed mechanics_carried_unchanged.method states that only the "
            "variant id format and the variant ids themselves differ from Attempt 2's. Compared "
            "pointer by pointer, four further pointers differ - three additive provenance notes and "
            "one changed pointer that could not have been otherwise, gate_evaluation_scope."
            "criteria_source, which must name this attempt's own criteria file. None of the four is "
            "a mechanic. The seal is not edited; check_mechanics_carried_unchanged implements the "
            "true predicate - no pointer removed, none changed outside a declared list, none added "
            "outside a declared list - and reports the unused entries of both allow-lists, so a "
            "list that only ever widens shows up as evidence rather than passing quietly.",
            "G2A3-CONFLICT-40: two prose pointers were renamed between Attempt 2's criteria seal "
            "and Attempt 3's (S3-C3 attempt_2_note to attempt_3_note, and S3-C6 "
            "scope_interpretation.attempt_2_significance to attempt_3_significance). Both are "
            "evidence text read by no predicate. Rather than fork Attempt 2's evaluators, they are "
            "called unmodified against an adapted view binding the old names to the new values, and "
            "check_prose_alias_adapter proves the view differs from the seal in exactly those two "
            "pointers, that both aliases carry byte-identical values to their RA3 originals, and "
            "that the sealed object itself is unmutated.",
            "G2A3-CONFLICT-41: three lists of banned selection-input substrings exist and no two are "
            "equal - the seal's AT-I prose names eight words, "
            "g2_selection_v2.FORBIDDEN_FIELD_SUBSTRINGS enforces fourteen, and the runner's "
            "_assert_selection_surface enforces seven. 'ratio' and 'factor' are named in the prose "
            "and enforced by neither, so a field named information_ratio would pass every substring "
            "check. Widening an implemented list to match a prompt's prose is the one repair this "
            "project forbids, so the gap is asserted rather than closed; the frozen dataclass makes "
            "it moot on this attempt, because the selection surface carries exactly six fields and "
            "no return field can reach it whatever the substring lists say.",
            "G2A3-CONFLICT-42: the sealed adaptation disclosure reasons that the removed rung had "
            "suppressed ordinary-market returns as well as crisis losses. Half of that reasoning is "
            "confirmed by this attempt's own measurement and half is refuted. The throttle did "
            "loosen - ladder descents fell from "
            f"{ev['ladder_engagement_comparison']['per_statistic']['ladder_descents']['attempt_2_total']} "
            "to "
            f"{ev['ladder_engagement_comparison']['per_statistic']['ladder_descents']['attempt_3_total']} "
            "across the same 36 runs - but grid returns did not improve: Attempt 2's grid was "
            "already positive on every base run and its maximum exceeded this attempt's "
            f"({sum(1 for row in table if Decimal(row['base_total_return']) > 0)} of {len(table)} "
            f"positive here, best {pct(max(Decimal(row['base_total_return']) for row in table))}), "
            "and the representative moved off the grid floor because SEL-2 replaced the "
            "lowest-turnover rule, not because a rung was removed - the lowest-turnover variant "
            "under RA3 is still the weakest-returning one in the grid. Section 12 of the research "
            "report carries the three-way measurement against both prior attempts. The sealed text "
            "is not edited; its reasoning is recorded as partly refuted, and the attribution of the "
            "representative's improvement to the selection rule rather than to the risk "
            "architecture is what this conflict exists to preserve.",
        ],
        produced=PRODUCED,
        frozen_inputs=FROZEN_INPUTS,
        body={
            "verdict_semantics": VERDICT_SEMANTICS,
            "verdict_token_derivation": derivation,
            "adaptation_disclosure_verbatim": protocol["adaptation_disclosure_verbatim"],
            "adaptation_disclosure_carriage": carriage,
            "attempt": ev["attempt"],
            "generation": ev["generation"],
            "preregistration": {
                "protocol_artifact_id": protocol["artifact_id"],
                "criteria_artifact_id": criteria["artifact_id"],
                "strategy_id": ev["strategy_id"],
                "candidate_index": ev["candidate_index"],
                "family": ev["family"],
                "generation_id": ev["generation_id"],
                "hypothesis": ev["hypothesis"],
                "sealed_inputs": ev["sealed_inputs"],
                "structural_consequences_declared_before_running": ev[
                    "structural_consequences_declared_before_running"
                ],
                "what_this_attempt_changes_from_attempt_2": ev[
                    "what_this_attempt_changes_from_attempt_2"
                ],
                "what_this_attempt_adds_over_attempt_1": ev[
                    "what_this_attempt_adds_over_attempt_1"
                ],
                "mechanics_carried_unchanged": ev["mechanics_carried_unchanged"],
            },
            "risk_architecture": ev["risk_architecture"],
            "ladder_engagement_comparison": ladder,
            "partition": {
                "window": window,
                "run_span_recheck": ev["run_span_recheck"],
                "generation_1_holdout_state": lock["generation_1_holdout_state"],
                "generation_2_holdout_state": lock["holdout_state"],
            },
            "universe": ev["universe"],
            "representative_selection_rule": ev["representative_selection_rule"],
            "selection": selection,
            "selection_determinism": ev["selection_determinism"],
            "gate_evaluation_scope": ev["gate_evaluation_scope"],
            "gate_scope": ev["gate_scope"],
            "candidate_results": ev["candidate_results"],
            "stage_verdict": declared,
            "reconciliation": ev["reconciliation"],
            "determinism": {
                key: value
                for key, value in ev["determinism"].items()
                if key != "run_digests"
            },
            "grid_results_descriptive_only": {
                "declaration": ev["variant_table_is_descriptive_only"],
                "coverage": ev["reported_for_every_variant_coverage"],
                "variants": len(table),
                "base_returns_positive": base_positive,
                "stress_returns_positive": stress_positive,
                "base_total_return_min": str(min(base_returns)),
                "base_total_return_max": str(max(base_returns)),
                "stress_total_return_min": str(min(stress_returns)),
                "stress_total_return_max": str(max(stress_returns)),
                "base_max_drawdown_deepest": str(max(base_dd)),
                "stress_max_drawdown_deepest": str(max(stress_dd)),
                "research_shutdown_events_total": shutdowns,
                "best_base_return_variant": best_base["variant_id"],
                "best_base_return": best_base["base_total_return"],
                "representative_is_not_the_best": (
                    best_base["variant_id"] != result["selected_variant_id"]
                ),
                "table": table,
            },
            "prior_attempt_module_verification": modules,
            "prior_attempt_modules_immutable": ev["prior_attempt_modules_immutable"],
            "repo_state_pattern_membership": membership,
            "multiple_comparisons_disclosure": mcd,
            "conflicts_declared_in_the_gate_criteria": ev[
                "conflicts_declared_in_the_gate_criteria"
            ],
            "refs_reverified": ev["refs_reverified"],
            "evidence_file": {
                "path": EVIDENCE,
                "artifact_id": ev["artifact_id"],
                "generated_utc": ev["generated_utc"],
                "evidence_digest": ev["evidence_digest"],
                "evidence_digest_covers": ev["evidence_digest_covers"],
                "recomputed_by_this_builder": recomputed,
                "digest_agrees": recomputed == ev["evidence_digest"],
                "command": ev["command"],
            },
            "authorization": {
                "explicit_non_authorizations": ev["explicit_non_authorizations"],
                "live_trading_authorized": ev["live_trading_authorized"],
            },
        },
        tests=tests,
        authorization_state={
            "live_trading_authorized": "false",
            "broker_access_attempted": "false",
            "credential_read": "false",
            "order_placed_cancelled_or_replaced": "false",
            "unattended_scheduling_configured": "false",
            "validation_window_read": "false",
            "generation_1_holdout_read": "false",
            "generation_2_holdout_read": "false",
        },
        next_authorized_stage=(
            "None. Generation 2 Stage 3 has now failed three times and this attempt closes on the "
            "same terms as the previous two: the sealed criteria state that a FAIL does not license "
            "a nineteenth variant, a re-run under a different grid, a loosened risk constant, a "
            "third selection rule, or promotion of the runner-up. Stage 4 validation is not "
            "authorized and was not run. Any Attempt 4 requires a further adaptation, disclosed in "
            "writing and authorised by a human in a later session, and would carry forward the "
            f"cumulative multiplicity recorded here ({mcd['cumulative_variants_this_hypothesis_family']} "
            f"variants, {mcd['cumulative_runs_this_hypothesis_family']} runs). "
            "live_trading_authorized remains false."
        ),
        dataset_hashes={},
        universe_version=protocol["eligible_universe"]["universe_version"],
        date_range=[protocol["run_span"]["run_start"], protocol["run_span"]["run_end"]],
        holdout_state="LOCKED",
        config_hash=sha256_file(PROJECT_ROOT / PROTOCOL),
        random_seed=None,
        run_notes=[
            "Built last, after the research report, the README update, the test summary and the "
            "pytest capture were all final. This module lives in src/, which repo_state_id covers, "
            "so any later edit to it — including a prose-only edit to one evidence bullet — would "
            "invalidate both the digest recorded here and the pytest capture parsed above.",
            "The produced list carries eight entries where Attempt 2's carried fifteen. This is a "
            "structural difference in how the attempt was written, not missing work: Attempt 3's "
            "evidence writer inlines the grid table, selection inputs, selection record, gate "
            "record, stage verdict and prior-attempt module verification into the single "
            "977-kilobyte evidence document rather than emitting six side files. Everything Attempt "
            "2 recorded separately is present here, inside one artifact that the manifest and "
            "checksum record cover.",
            "The verdict token was derived from the sealed verdict_token_derivation and asserted "
            "against the evidence's own, never restated as a literal. All four tokens belonging to "
            "Attempts 1 and 2 are refused, and the refusal list is cross-checked against both the "
            "seal's prose and the evidence's withheld list so that shortening it fails the build.",
            "The adaptation disclosure was required byte-exact from every carrier. Attempt 2 needed "
            "a normalisation allowance for one hard-wrapped Markdown carrier (G2A2-CONFLICT-29); "
            "this build's allowance is empty and the guard refuses any carrier that needs "
            "normalisation, which is a strictly tighter check than the one it was copied from.",
            "Four Generation 2 checksum records were re-verified from project-root-relative paths: "
            "the partition lock, the RA3 protocol, and the frozen protocols of both closed "
            "attempts. Neither closed attempt's artifacts were opened for writing at any point, and "
            "the seventeen prior-attempt modules were re-hashed and none moved.",
            "G2A3-CONFLICT-30 was checked in both directions at build time rather than argued in "
            "prose — the governance artifacts of this attempt are outside the repo_state_id "
            "patterns and its config artifacts are inside them. The tree digest itself is recorded "
            "only in this decision record and the appended runs/ record, never in a governance "
            "document that would then be part of the tree it digests.",
            "No data at or after 2021-08-01 was read by any module in this attempt. The Generation "
            "1 validation window, the Generation 1 holdout and the Generation 2 holdout were all "
            "untouched, and the window guard recomputed the run span from the loaded series before "
            "the first variant ran.",
            "No broker endpoint, credential or order path was reachable. No secret value was "
            "printed, logged or written, and the adaptation disclosure was never written to the "
            "cp1252 console, which would have raised UnicodeEncodeError on its minus sign.",
        ],
    )

    result_out = build_stage_package(decision)
    print(f"verdict          {VERDICT}")
    print(f"run_id           {result_out.run_id}")
    print(f"repo_state_id    {result_out.repo_state_id}")
    print(f"timestamp_utc    {result_out.timestamp_utc}")
    print(f"stage0 freeze    {result_out.freeze_ok}")
    print(f"tests            {tests}")
    print(f"decision         {result_out.decision_path.relative_to(PROJECT_ROOT)}")
    print(f"manifest         {result_out.manifest_path.relative_to(PROJECT_ROOT)}")
    print(f"checksums        {result_out.checksum_path.relative_to(PROJECT_ROOT)}")
    print(f"checksum_digest  {result_out.checksum_digest}")
    print(f"run record       {result_out.run_record_path.relative_to(PROJECT_ROOT)}")
    if not result_out.freeze_ok:
        print("STAGE 0 FREEZE VERIFICATION FAILED")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
