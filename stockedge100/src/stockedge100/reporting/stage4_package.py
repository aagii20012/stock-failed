"""Stage 4 validation pre-registration decision package.

This module builds the decision package for prompt stage 4 / constitutional gate 4, for a session
that selected one representative and sealed a prospective validation pre-registration. It did not
evaluate gate 4. Three things follow from that, and each is enforced here rather than asserted in
prose:

* **The conditions are seal conditions, not gate conditions.** ``S4D-C1`` .. ``S4D-C11`` are the
  conditions for a legitimate seal, and they are recomputed here from the written artifacts rather
  than read out of an evidence file, because a pre-registration session has no evidence file: the
  artifacts *are* the evidence. Checksum records are re-verified, digests recomputed from the files
  on disk, the screen arithmetic re-derived from the declared runs, the folds recomputed from the
  frozen partition boundaries, and the agreement tokens located in both formats.

* **The guard is the portable one.** ``stage2_package.py`` refuses to write unless its evidence meets
  every condition, which suits a stage whose package could only ever be a pass. A design session can
  legitimately end ``BLOCKED``, and the constitution keeps negative results on disk, so the guard in
  :func:`build` instead requires the verdict written into the package to be the verdict the
  conditions reached, and refuses only the incoherent combinations: a sealed design claiming a gate
  pass, an ``admissible_candidate_exists`` row that is anything other than ``NOT_RUN``, and a verdict
  that borrows a gate token.

* **The verdict token is neither gate 4 token.** ``STAGE_4_VALIDATION_PREREGISTRATION_FROZEN`` is a
  design-session reason code following the precedent of ``STAGE_3_ATTEMPT_2_PREREGISTRATION_FROZEN``.
  Gate 4's own tokens are read from the sealed ``verdict_token_derivation`` and asserted to differ,
  so a package that accidentally emitted the gate's pass token cannot be written.

``gate_passed=False`` makes the shared builder derive ``exit_status`` ``GATE_NOT_PASSED`` for the
``runs/`` record. That is correct — gate 4 has not been passed — and the run notes say so, so the
status is not misread as a failed run.

The predicates and record checks are **imported** from :mod:`stage4_preregistration` rather than
copied. A predicate re-implemented here could drift from the one whose value the seal records; the
same function cannot. This module is itself inside the scope of the AST predicate
``stage_4_modules_touching_restricted_data_or_a_broker`` (same ``stage4`` path marker, no exclusion),
which is the point: the builder is held to the same fail-closed proof as the sealing program.

Nothing here writes to a frozen artifact, reads a validation or holdout observation, or runs a
strategy. Output goes to ``reports/stage4/`` and ``runs/`` only.
"""

from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

from stockedge100.audit import sha256_file
from stockedge100.reporting.stage_package import (
    GOVERNANCE,
    PROJECT_ROOT,
    STAGE_0_FROZEN_INPUTS,
    StageDecision,
    build_stage_package,
    repo_state,
    verify_sha256_record,
    verify_stage0_freeze,
)

# Adopted, not copied. See the module docstring.
from stockedge100.reporting.stage4_preregistration import (
    GATE_3_IMMUTABILITY,
    HEX64,
    PREDICATE_DEFINITIONS,
    PREREGISTERED,
    RECORD_REL,
    RECORD_SHA_REL,
    THIS_MODULE_REL as SEALER_REL,
    _digest_index,
    _modules_naming_a_run_label,
    _normalised_prose,
    _resolve_strategy_module,
    _run_labels,
    _stage_4_modules,
    _stage_4_modules_touching_restricted_data,
    _stage_4_report_artifacts,
    _stage_4_run_records,
)

COMMAND = "cd stockedge100 && PYTHONPATH=src python -m stockedge100.reporting.stage4_package"

PASS_VERDICT = "PASS — STAGE_4_VALIDATION_PREREGISTRATION_FROZEN"
NOT_SEALABLE_VERDICT = "BLOCKED — STAGE_4_VALIDATION_PREREGISTRATION_NOT_SEALABLE"
GATE_PASSED = False

SEAL = RECORD_REL
SEAL_RECORD = RECORD_SHA_REL
PREREG_MD = "governance/STAGE_4_PREREGISTRATION.md"
PROTOCOL = "config/stage4_validation_protocol.json"
CRITERIA = "config/stage4_gate_criteria.json"
SELECTION = "config/stage4_representative_selection.json"
REPORT = "governance/STAGE_4_VALIDATION_PREREGISTRATION_REPORT.md"

CONSTITUTION_MD = "governance/STAGE_0_CONSTITUTION.md"
CONSTITUTION_JSON = "governance/STAGE_0_CONSTITUTION.json"
HOLDOUT_LOCK = "governance/STAGE_1_HOLDOUT_LOCK.json"
UNIVERSE = "governance/STAGE_1_UNIVERSE.json"
STRATEGY_MODULE_DIR = "src/stockedge100/strategies/"

# This module. It carries the stage marker, so the sealed evaluator-module predicate counts it; §16
# of the report records why it is not renamed to duck the marker.
PACKAGE_MODULE_REL = "src/stockedge100/reporting/stage4_package.py"

# The two Gate 3 Attempt 2 run records whose tests/ entries establish the floor by digest. Both are
# used, not one: the design session and the evaluation session each recorded the suite of their day.
GATE_3_RUN_RECORDS = (
    "runs/SE100-R-20260813T120406Z.json",
    "runs/SE100-R-20260813T140121Z.json",
)
SEAL_RUN_RECORD = "runs/SE100-R-20260813T140121Z.json"

# (record, working dir its paths are relative to, expected entry count). The first twelve are the
# upstream records verified before any Stage 4 artifact was authored, in the order of section 2 of
# the report; the thirteenth is this stage's own seal. Freeze records list bare filenames and verify
# from the directory holding them — passing the wrong root reports MISSING for every entry and looks
# like an integrity failure when it is an operator error.
CHECKSUM_RECORDS = (
    ("governance/STAGE_0_FREEZE.sha256", "governance", 2),
    ("governance/STAGE_1_FREEZE.sha256", "governance", 2),
    ("governance/STAGE_1_PREREGISTRATION.sha256", "root", 4),
    ("governance/STAGE_2_PREREGISTRATION.sha256", "root", 4),
    ("governance/STAGE_3_PREREGISTRATION.sha256", "root", 4),
    ("governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.sha256", "root", 4),
    ("reports/stage0/STAGE_0_VERIFICATION.sha256", "root", 8),
    ("reports/stage1/STAGE_1_DATA_READINESS.sha256", "root", 19),
    ("reports/stage2/STAGE_2_BACKTEST_ENGINE.sha256", "root", 20),
    ("reports/stage3/STAGE_3_STRATEGY_RESEARCH.sha256", "root", 26),
    ("reports/stage3_attempt2/STAGE_3_ATTEMPT_2_DESIGN.sha256", "root", 31),
    ("reports/stage3_attempt2/STAGE_3_ATTEMPT_2_STRATEGY_RESEARCH.sha256", "root", 37),
    (SEAL_RECORD, "root", 5),
)
UPSTREAM_RECORD_COUNT = 12

# Strings that must appear in both the pre-registration Markdown and the pre-registration JSON. If
# the two formats disagree the seal means two different things, so the sealing program refuses with
# exit 7 and this package re-checks the same tokens independently.
# Key suffixes whose values are content digests of a Gate 3 development run's output rather than of
# any file in the tree. A digest under one of these is accounted for; a digest anywhere else that
# resolves to no file fails S4D-C9.
NON_FILE_DIGEST_KEY_SUFFIXES = ("trade_digest", "equity_digest")

AGREEMENT_TOKENS = (
    "SE100-GOV-0008",
    "SE100-S3A2-C2-MEANREV-RA1",
    "SE100-CFG-4003-R1",
    "STAGE_4_STRATEGY_REJECTED_IN_VALIDATION",
    "LOCKED",
    "SEALED",
)

PRODUCED = (
    "governance/STAGE_4_VALIDATION_PREREGISTRATION_REPORT.md",
    "governance/STAGE_4_PREREGISTRATION.md",
    "governance/STAGE_4_PREREGISTRATION.json",
    "governance/STAGE_4_PREREGISTRATION.sha256",
    "config/stage4_validation_protocol.json",
    "config/stage4_gate_criteria.json",
    "config/stage4_representative_selection.json",
    "src/stockedge100/reporting/stage4_preregistration.py",
    "src/stockedge100/reporting/stage4_package.py",
    "tests/unit/test_stage4_preregistration.py",
    "reports/stage4/STAGE_4_VALIDATION_PREREGISTRATION_TEST_SUMMARY.md",
    "reports/stage4/pytest_stage4_output.txt",
    "reports/stage4/STAGE_4_VALIDATION_PREREGISTRATION.json",
    "reports/stage4/STAGE_4_VALIDATION_PREREGISTRATION_ARTIFACT_MANIFEST.json",
)

FROZEN_INPUTS = tuple(STAGE_0_FROZEN_INPUTS) + (
    HOLDOUT_LOCK,
    UNIVERSE,
    "config/stage2_cost_model.json",
    "config/stage2_engine_spec.json",
    "config/stage3_gate_criteria.json",
    "config/stage3_attempt2_strategy_protocol.json",
    "config/stage3_attempt2_gate_criteria_binding.json",
    "governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.json",
    "reports/stage3_attempt2/STAGE_3_ATTEMPT_2_STRATEGY_RESEARCH.json",
)

# Copied from section 19 of governance/STAGE_4_VALIDATION_PREREGISTRATION_REPORT.md so the two can
# be diffed. If a requirement here and the report's table disagree, one of them was edited alone.
REQUIREMENTS = {
    "S4D-C1": (
        "Stage 0 freeze verified digest-for-digest on both halves; twelve upstream checksum records "
        "verify entry-for-entry from their intended working directories, before any Stage 4 artifact "
        "was authored"
    ),
    "S4D-C2": (
        "Frozen on-disk governance authorises a prospective Stage 4 pre-registration and nothing "
        "executable, with the determination resting on quoted frozen text rather than on the "
        "operating prompt"
    ),
    "S4D-C3": (
        "Zeroed restricted-data posture across all six counters, established structurally by an AST "
        "predicate whose scope includes every Stage 4 module - the sealing program and this package "
        "builder both - recomputed at build time and empty; no declared run label anywhere in src/; "
        "Gate 3 Attempt 2 records still verify; the three predicates that moved after the seal "
        "reported with the files that moved them"
    ),
    "S4D-C4": (
        "Mandatory-rule search recorded and empty; eligible set exactly the two admitted PRIMARY "
        "candidates; rule return-blind, parameter-free, applied in full to both candidates; survivor "
        "count 1; the stop-for-human alternative recorded before application"
    ),
    "S4D-C5": (
        "Seven conditions from the frozen Markdown; six thresholds derived from the constitution's "
        "JSON companion; both tokens derived from the sealed derivation with neither taken from a "
        "prompt; six of seven measurements adopted by digest"
    ),
    "S4D-C6": (
        "The fold construction is the single measurement this stage authors; derived from the frozen "
        "partition boundaries alone; recorded as S4-CONFLICT-4 with its section 8 authority; "
        "train_folds empty per S4-CONFLICT-5"
    ),
    "S4D-C7": (
        "The selection is disclosed as adaptive, with the residual freedom stated and five "
        "mitigations recorded; the narrowest margin of the survivor recorded; the cumulative "
        "development experiment count not reset - 24 development runs across both Gate 3 attempts, "
        "plus this stage's 2"
    ),
    "S4D-C8": (
        "Two runs declared with a hard limit, one parameterisation, zero re-runs; every condition "
        "assigned to a run or to S4-C7; failure, defect, and unusable-data outcomes pre-committed; "
        "no discretionary choice left to the evaluation session"
    ),
    "S4D-C9": (
        "Checksum record verifies 5/5 from the project root; Markdown and JSON materially agree; all "
        "four JSON artifacts ASCII-only in fact; S4-C7 set 13 declared / 12 recorded with the "
        "omission being the record itself; no tree digest written inside a covered file; the sealer "
        "refuses a second run"
    ),
    "S4D-C10": (
        "No window authorized in this session; validation LOCKED; holdout SEALED; enforcement "
        "structural through ResearchWindow / MarketView; the folds partition the validation window "
        "without redefining it; no boundary moved"
    ),
    "S4D-C11": (
        "708 collected, up from 560; four-file selection 263 passed / 0 failed / 0 skipped, the new "
        "module 148; 15 of 15 recorded test-file digests unchanged; nothing weakened, skipped, "
        "xfailed, or deleted"
    ),
}

VERDICT_SEMANTICS = (
    "MET here is a statement about the seal, not about behaviour on the validation window. It means "
    "the condition for a legitimate pre-registration was recomputed from the written artifacts and "
    "holds. No S4D condition is evidence about gate 4."
)


def load(rel: str) -> dict:
    return json.loads((PROJECT_ROOT / rel).read_text(encoding="utf-8"))


def read_text(rel: str) -> str:
    return (PROJECT_ROOT / rel).read_text(encoding="utf-8")


def _condition(condition_id: str, met: bool, evidence: dict) -> dict:
    return {
        "required": REQUIREMENTS[condition_id],
        "verdict": "MET" if met else "NOT_MET",
        "verdict_semantics": VERDICT_SEMANTICS,
        "evidence": evidence,
    }


_ONE_DAY = timedelta(days=1)


def _flatten_markdown_lines(lines: list[str]) -> str:
    """Apply the flattening the criteria file describes: drop bullet, bold and code markers and
    line breaks, add and remove no word, reorder nothing."""
    flattened = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("- "):
            stripped = stripped[2:]
        flattened.append(_normalised_prose(stripped))
    return " ".join(flattened)


def _walk_scalars(obj, path: str = ""):
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield from _walk_scalars(value, f"{path}.{key}")
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            yield from _walk_scalars(value, f"{path}[{index}]")
    else:
        yield path, obj


def _classify_non_file_digests(document: dict, digests: list[str]) -> dict[str, list[str]]:
    """Split digests that resolve to no file into the accounted-for and the unaccounted-for.

    A digest is accounted for when the key holding it names it as a content digest of run output
    rather than of a file — the Gate 3 development runs' trade and equity digests, quoted here from
    the Gate 3 decision record. Everything else is unaccounted for and fails the condition.
    """
    holders: dict[str, set[str]] = {}
    for path, value in _walk_scalars(document):
        if isinstance(value, str) and value in digests:
            holders.setdefault(value, set()).add(path.rsplit(".", 1)[-1])
    accounted, unaccounted = [], []
    for digest in digests:
        keys = holders.get(digest, set())
        if keys and all(
            key.endswith(NON_FILE_DIGEST_KEY_SUFFIXES) for key in keys
        ):
            accounted.append(digest)
        else:
            unaccounted.append(digest)
    return {"accounted_for": sorted(accounted), "unaccounted_for": sorted(unaccounted)}


def _frozen_gate_text_reconstructed(source: dict) -> tuple[str, tuple[int, int]]:
    """Rebuild the quoted gate text from the constitution lines the source field names.

    Stronger than searching the constitution for fragments of the quote: it proves the quote is
    exactly the flattening of exactly those lines, so a word added, dropped or reordered fails.
    """
    first, _, last = source["lines"].partition(" to ")
    start, end = int(first), int(last)
    lines = read_text(CONSTITUTION_MD).splitlines()[start - 1 : end]
    return _flatten_markdown_lines(lines), (start, end)


def _quarter_end(start: date) -> date:
    """Last calendar day of the three-month block beginning at ``start``."""
    month = start.month + 3
    year = start.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    return date(year, month, 1) - _ONE_DAY


def _c1_frozen_governance() -> dict:
    """Every checksum record verifies, entry for entry, with the count the report claims."""
    records: dict[str, dict] = {}
    for rel, where, expected in CHECKSUM_RECORDS:
        root = GOVERNANCE if where == "governance" else PROJECT_ROOT
        path = PROJECT_ROOT / rel
        if not path.is_file():
            records[rel] = {"verify_from": where, "result": "RECORD_MISSING"}
            continue
        results = verify_sha256_record(path, root=root)
        statuses = sorted(set(results.values()))
        records[rel] = {
            "verify_from": where,
            "entries": len(results),
            "entries_expected": expected,
            "statuses": statuses,
            "result": (
                "OK" if statuses == ["OK"] and len(results) == expected else "MISMATCH"
            ),
        }
    freeze_ok, freeze_detail = verify_stage0_freeze()
    met = freeze_ok and all(entry["result"] == "OK" for entry in records.values())
    return _condition(
        "S4D-C1",
        met,
        {
            "stage_0_freeze_verified_digest_for_digest": freeze_ok,
            "stage_0_freeze_detail": freeze_detail,
            "upstream_records_checked": UPSTREAM_RECORD_COUNT,
            "records": records,
            "working_directory_note": (
                "Freeze records list bare filenames and verify from stockedge100/governance/; every "
                "other record here uses project-root-relative paths and verifies from "
                "stockedge100/. A failure reported from the other directory is an operator error."
            ),
            "nothing_repaired": (
                "No frozen artifact was opened for writing at any point in this session. A record "
                "that failed would be a blocker, not a defect to fix."
            ),
        },
    )


def _c2_validation_evaluation_permitted(protocol: dict, criteria: dict) -> dict:
    """The authorization rests on frozen text, recomputed, not on the operating prompt."""
    determination = protocol["authorization_determination"]
    source = criteria["frozen_gate_text_source"]
    quoted = criteria["frozen_gate_text_verbatim"]
    # The gate text is quoted flattened out of eleven Markdown lines, so searching the constitution
    # for the quote's semicolon-separated clauses misses the first one: the lead-in and the first
    # bullet are contiguous in the quote and not in the source. Rebuild the flattening instead.
    reconstructed, (start_line, end_line) = _frozen_gate_text_reconstructed(source)
    reconstruction_matches = reconstructed == _normalised_prose(quoted)
    source_digest_ok = sha256_file(PROJECT_ROOT / source["path"]) == source["sha256"]
    met = (
        source_digest_ok
        and reconstruction_matches
        and determination["validation_evaluation_authorized"] is True
        and determination["validation_access_authorized_in_this_session"] is False
        and determination["holdout_access_authorized"] is False
        and determination["gate_3_passed"] is True
    )
    return _condition(
        "S4D-C2",
        met,
        {
            "question": determination["question"],
            "frozen_gate_text_source": {
                "path": source["path"],
                "lines": source["lines"],
                "digest_recomputed": source_digest_ok,
                "flattening": source["flattening"],
                "quote_reconstructed_from_lines": [start_line, end_line],
                "reconstruction_equals_the_quoted_text": reconstruction_matches,
                "why_reconstruction_and_not_search": (
                    "Reapplying the described flattening to exactly those constitution lines and "
                    "requiring the result to equal the quote proves no word was added, dropped or "
                    "reordered. Searching for fragments would pass on a quote that lost a clause."
                ),
            },
            "gate_3_authorizes": determination["gate_3_authorizes"],
            "this_session_authorizes": determination["this_session_authorizes"],
            "validation_evaluation_authorized": determination["validation_evaluation_authorized"],
            "validation_evaluation_authorized_scope": determination[
                "validation_evaluation_authorized_scope"
            ],
            "validation_access_authorized_in_this_session": determination[
                "validation_access_authorized_in_this_session"
            ],
            "holdout_access_authorized": determination["holdout_access_authorized"],
            "what_would_void_the_authorization": determination["what_would_void_the_authorization"],
            "not_from_the_prompt": (
                "The determination cites constitution section 9 gate 4 and the frozen partition "
                "lock. The operating prompt is not an authority and is not cited as one."
            ),
        },
    )


def _c3_no_restricted_observation(seal: dict, protocol: dict) -> dict:
    """Recompute all six sealing predicates; separate the must-stay-zero ones from the moved ones."""
    labels = _run_labels(protocol)
    posture = seal["restricted_data_posture"]
    counters = {
        key: value for key, value in posture.items() if isinstance(value, int)
    }

    naming_a_label = _modules_naming_a_run_label(labels)
    touching = _stage_4_modules_touching_restricted_data()
    immutability = {
        rel: sorted(set(verify_sha256_record(PROJECT_ROOT / rel, root=PROJECT_ROOT).values()))
        for rel in GATE_3_IMMUTABILITY
    }
    immutability_ok = all(statuses == ["OK"] for statuses in immutability.values())

    evaluator_modules = _stage_4_modules()
    report_artifacts = _stage_4_report_artifacts()
    run_records = _stage_4_run_records(labels)

    met = (
        all(value == 0 for value in counters.values())
        and not naming_a_label
        and not touching
        and immutability_ok
        and seal["contamination_predicates"]["stage_4_modules_touching_restricted_data_or_a_broker"]
        == 0
        and evaluator_modules == [PACKAGE_MODULE_REL]
    )
    return _condition(
        "S4D-C3",
        met,
        {
            "restricted_data_counters_recorded_in_the_seal": counters,
            "how_this_is_known": posture["how_this_is_known"],
            "must_stay_zero_recomputed_now": {
                "modules_naming_a_stage_4_run_label": naming_a_label,
                "stage_4_modules_touching_restricted_data_or_a_broker": touching,
                "ast_predicate_scope": sorted({SEALER_REL, PACKAGE_MODULE_REL}),
                "ast_predicate_definition": PREDICATE_DEFINITIONS[
                    "stage_4_modules_touching_restricted_data_or_a_broker"
                ],
                "why_ast_and_not_grep": (
                    "A text search over either module would match the words of the predicate's own "
                    "definition. The predicate walks the parsed syntax tree instead: no forbidden "
                    "import root, no dataset-loader call, no credential attribute, no string "
                    "constant containing a URL scheme."
                ),
            },
            "gate_3_attempt_2_immutability": {
                "records": immutability,
                "verify": immutability_ok,
                "why": (
                    "The representative was selected from that decision record, so the check fails "
                    "if the evidence behind the selection changed by a single byte."
                ),
            },
            "moved_after_the_seal": {
                "measured_at": (
                    "Every count here is recomputed before this build writes anything, so the "
                    "decision record, the artifact manifest, the checksum record and this build's "
                    "own run record do not yet exist and are not counted. Each of the three will "
                    "rise by one artifact more once the build completes; the two that must stay "
                    "zero are unaffected, because none of those files is a module."
                ),
                "stage_4_evaluator_or_result_modules": {
                    "value_at_sealing": seal["contamination_predicates"][
                        "stage_4_evaluator_or_result_modules"
                    ],
                    "value_now": len(evaluator_modules),
                    "files": evaluator_modules,
                    "anticipated_in_the_sealed_definition": False,
                    "classification": (
                        "Design-session decision-package builder. It reads governance artifacts, "
                        "recomputes digests and writes a decision record; it computes no return, no "
                        "metric and no fold, and it is not a Stage 4 evaluator. The sealed "
                        "definition excludes one named file - the sealing program - so this builder "
                        "is counted. It keeps the name its stage implies rather than being renamed "
                        "to duck a path marker, because a marker evaded by renaming is not a "
                        "marker. Section 16 of the report records this."
                    ),
                    "independent_checks_behind_that_classification": (
                        "stage_4_modules_touching_restricted_data_or_a_broker includes this builder "
                        "in its own scope by construction and reads empty; "
                        "modules_naming_a_stage_4_run_label stays 0, so no declared Stage 4 run "
                        "label appears anywhere in src/."
                    ),
                },
                "stage_4_report_artifacts": {
                    "value_at_sealing": seal["contamination_predicates"]["stage_4_report_artifacts"],
                    "value_now": len(report_artifacts),
                    "files": report_artifacts,
                    "anticipated_in_the_sealed_definition": True,
                    "classification": (
                        "This session's own design-session package. The test summary and the pytest "
                        "output exist at measurement time; the decision record, artifact manifest "
                        "and checksum record are written by this build immediately afterwards. The "
                        "sealed definition states that the recorded value is the count that existed "
                        "before the seal, which was zero."
                    ),
                },
                "stage_4_run_records": {
                    "value_at_sealing": seal["contamination_predicates"]["stage_4_run_records"],
                    "value_now": len(run_records),
                    "files": run_records,
                    "anticipated_in_the_sealed_definition": True,
                    "classification": (
                        "The seal's own reproducibility record, which carries the stage token by "
                        "construction. This build appends a second immediately afterwards. Neither "
                        "contains a declared Stage 4 run label, which is the predicate that would "
                        "indicate an evaluation had been run."
                    ),
                },
            },
            "none_of_the_moved_files_is": (
                "strategy code, a Stage 4 evaluator, a performance result, or a file containing a "
                "return, drawdown, trade count, fold return or equity value for the validation "
                "window - no such value exists."
            ),
        },
    )


def _c4_selection_lawful(selection: dict, seal: dict) -> dict:
    """Re-derive the screen from the declared runs rather than reading back its conclusion."""
    search = selection["search_for_a_mandatory_constitutional_selection_rule"]
    eligible = selection["eligible_set"]
    rule = selection["selection_rule"]
    application = selection["application"]
    outcome = application["outcome"]

    evidence_source = application["evidence_source"]
    evidence_digest_ok = (
        sha256_file(PROJECT_ROOT / evidence_source["path"]) == evidence_source["sha256"]
    )

    # The screen counts shutdown trips across every declared run of each candidate. Recomputed from
    # declared_runs, not read from screen_results, so a hand-edited conclusion would not survive.
    rederived: dict[str, dict] = {}
    for candidate in application["candidates"]:
        runs = candidate["declared_runs"]
        trips = sorted(run["run_label"] for run in runs if run["shutdown_tripped"])
        rederived[candidate["candidate"]] = {
            "declared_run_count": len(runs),
            "shutdown_trip_count": len(trips),
            "tripping_runs": trips,
            "screen_result": "ELIMINATED" if trips else "SURVIVES",
        }
    sealed_screen = seal["sealed_representative"]["screen_results"]
    screen_agrees = all(
        sealed_screen[candidate]["screen_result"] == derived["screen_result"]
        and sealed_screen[candidate]["shutdown_trip_count"] == derived["shutdown_trip_count"]
        and sealed_screen[candidate]["declared_run_count"] == derived["declared_run_count"]
        for candidate, derived in rederived.items()
    )
    survivors = sorted(
        candidate for candidate, derived in rederived.items() if derived["screen_result"] == "SURVIVES"
    )

    provenance_terms = rule["provenance"]["terms"]
    digest_index = _digest_index()
    provenance_digests = {
        digest: digest_index.get(digest, [])
        for term in provenance_terms
        for digest in HEX64.findall(json.dumps(term))
    }

    met = (
        evidence_digest_ok
        and bool(search["searched"])
        and "No mandatory selection rule exists" in search["result"]
        and eligible["candidates"] == sorted(rederived)
        and len(eligible["excluded"]) >= 4
        and rule["reads_no_return"] is True
        and rule["reads_no_risk_adjusted_metric"] is True
        and screen_agrees
        and survivors == [seal["sealed_representative"]["experiment_id"]]
        and outcome["survivor_count"] == 1
        and outcome["human_selection_required"] is False
        and bool(outcome["if_the_rule_had_not_decided"])
        and all(paths for paths in provenance_digests.values())
    )
    return _condition(
        "S4D-C4",
        met,
        {
            "mandatory_rule_search": {
                "question": search["question"],
                "locations_searched": search["searched"],
                "result": search["result"],
                "constraint_that_did_apply": search["constraint_that_did_apply"],
            },
            "eligible_set": eligible["candidates"],
            "excluded": [entry["candidate"] for entry in eligible["excluded"]],
            "c3_not_reconsidered": any(
                "C3-DEFENSIVE" in entry["candidate"] for entry in eligible["excluded"]
            ),
            "rule": {
                "id": rule["id"],
                "name": rule["name"],
                "statement": rule["statement"],
                "reads_no_return": rule["reads_no_return"],
                "reads_no_risk_adjusted_metric": rule["reads_no_risk_adjusted_metric"],
                "output_is_binary_per_variant": rule["output_is_binary_per_variant"],
                "provenance_terms": len(provenance_terms),
                "provenance_digests_resolved_to_files": provenance_digests,
            },
            "evidence_source": {
                "path": evidence_source["path"],
                "digest_recomputed": evidence_digest_ok,
            },
            "screen_rederived_from_declared_runs": rederived,
            "screen_agrees_with_the_seal": screen_agrees,
            "applied_to_both_candidates_in_full": sorted(rederived) == eligible["candidates"],
            "survivors": survivors,
            "survivor_count": outcome["survivor_count"],
            "human_selection_required": outcome["human_selection_required"],
            "stop_for_human_alternative_recorded": outcome["if_the_rule_had_not_decided"],
            "what_the_rule_is_not": rule["what_the_rule_is_not"],
        },
    )


def _c5_gate_extracted(criteria: dict) -> dict:
    """Conditions quoted from the frozen Markdown; tokens derived from the frozen JSON companion."""
    companion_source = criteria["frozen_gate_json_companion_source"]
    companion = criteria["frozen_gate_json_companion_verbatim"]
    companion_digest_ok = (
        sha256_file(PROJECT_ROOT / companion_source["path"]) == companion_source["sha256"]
    )
    frozen_gate = next(
        gate for gate in load(CONSTITUTION_JSON)["gates"] if gate["id"] == companion["id"]
    )
    companion_matches_disk = frozen_gate["thresholds"] == companion["thresholds"] and frozen_gate[
        "fail_result"
    ] == companion["fail_result"]

    derivation = criteria["verdict_token_derivation"]
    derived_fail = "STAGE_4_" + companion["fail_result"]
    derived_pass = derived_fail.replace("REJECTED", "ADMITTED")
    tokens_derived = (
        derivation["fail_token"] == derived_fail and derivation["pass_token"] == derived_pass
    )

    gate_text = _normalised_prose(criteria["frozen_gate_text_verbatim"])
    conditions = criteria["conditions"]
    quoted = [
        condition["id"]
        for condition in conditions
        if _normalised_prose(condition["required_verbatim"]) in gate_text
    ]

    bound = criteria["measurement_adopted_by_digest"]["bound_artifacts"]
    bound_recomputed = {
        artifact["path"]: sha256_file(PROJECT_ROOT / artifact["path"]) == artifact["sha256"]
        for artifact in bound
    }
    authored = criteria["measurement_adopted_by_digest"]["what_this_stage_authors"]

    met = (
        companion_digest_ok
        and companion_matches_disk
        and tokens_derived
        and len(conditions) == 7
        and len(quoted) == 7
        and len(companion["thresholds"]) == 6
        and all(bound_recomputed.values())
        and "pass_result" not in companion
        # The sealed sentence, not a paraphrase of it. Asserting a fragment I assumed was there is
        # how three earlier tests in this stage failed.
        and (
            "Neither token is invented and neither is taken from an operating prompt."
            in derivation["derivation_method"]
        )
    )
    return _condition(
        "S4D-C5",
        met,
        {
            "conditions_declared": len(conditions),
            "condition_ids": [condition["id"] for condition in conditions],
            "conditions_whose_required_text_is_located_in_the_frozen_gate_text": quoted,
            "frozen_gate_json_companion_source": companion_source["path"],
            "frozen_gate_json_companion_digest_recomputed": companion_digest_ok,
            "companion_matches_the_frozen_gate_on_disk": companion_matches_disk,
            "companion_thresholds": len(companion["thresholds"]),
            "companion_carries_no_pass_result": "pass_result" not in companion,
            "tokens": {
                "pass_token": derivation["pass_token"],
                "fail_token": derivation["fail_token"],
                "derived_from_the_frozen_fail_result": tokens_derived,
                "derivation_method": derivation["derivation_method"],
                "conjunctive_note": derivation["conjunctive_note"],
                "single_representative_note": derivation["single_representative_note"],
            },
            "measurements_adopted_by_digest": bound_recomputed,
            "measurements_this_stage_authors": authored,
            "six_of_seven_adopted": (
                "Six of the seven conditions are measured by definitions adopted unchanged from "
                "artifacts sealed before Gate 3 was evaluated. The seventh, S4-C6, needs a fold "
                "construction that exists nowhere on disk; see S4D-C6."
            ),
        },
    )


def _c6_authored_measurement(criteria: dict, lock: dict, seal: dict) -> dict:
    """The one authored measurement, recomputed from the frozen boundaries alone."""
    construction = criteria["walk_forward_fold_construction"]
    partition = lock["partition"]
    start = date.fromisoformat(partition["validation_start"])
    end = date.fromisoformat(partition["validation_end"])

    recomputed = []
    cursor = start
    while cursor <= end:
        block_end = _quarter_end(cursor)
        recomputed.append(
            {"fold": len(recomputed) + 1, "start": cursor.isoformat(), "end": block_end.isoformat()}
        )
        cursor = block_end + _ONE_DAY
    declared = construction["test_folds"]["folds"]
    folds_match = declared == recomputed
    tiles_window = bool(recomputed) and recomputed[0]["start"] == partition[
        "validation_start"
    ] and recomputed[-1]["end"] == partition["validation_end"]
    contiguous = all(
        date.fromisoformat(later["start"]) - date.fromisoformat(earlier["end"]) == _ONE_DAY
        for earlier, later in zip(recomputed, recomputed[1:])
    )

    conflicts = {conflict["id"]: conflict for conflict in criteria["conflicts_found"]}
    met = (
        folds_match
        and tiles_window
        and contiguous
        and len(recomputed) == 12
        and construction["test_folds"]["count"] == 12
        and construction["train_folds"]["count"] == 0
        and construction["train_folds"]["set"] == []
        and construction["declared_before_any_validation_observation_was_read"] is True
        and seal["walk_forward_fold_construction"]["authored_in_this_session"] is True
        and "S4-CONFLICT-4" in conflicts
        and "S4-CONFLICT-5" in conflicts
        and "section 8" in construction["authority"]
    )
    return _condition(
        "S4D-C6",
        met,
        {
            "id": construction["id"],
            "authority": construction["authority"],
            "derived_only_from": construction["derived_only_from"],
            "validation_window_read_from_the_frozen_lock": [
                partition["validation_start"],
                partition["validation_end"],
            ],
            "validation_calendar_months": partition["validation_months"],
            "test_folds_declared": construction["test_folds"]["count"],
            "test_folds_recomputed": len(recomputed),
            "folds_match_the_recomputation": folds_match,
            "folds_tile_the_validation_window_with_no_remainder": tiles_window,
            "folds_are_contiguous_and_non_overlapping": contiguous,
            "first_fold": recomputed[0] if recomputed else None,
            "last_fold": recomputed[-1] if recomputed else None,
            "train_folds": construction["train_folds"],
            "conflicts": {
                "S4-CONFLICT-4": conflicts.get("S4-CONFLICT-4", {}).get("description"),
                "S4-CONFLICT-5": conflicts.get("S4-CONFLICT-5", {}).get("description"),
            },
            "no_validation_observation_was_used": (
                "The construction is calendar arithmetic on the two frozen boundary dates. No "
                "trading-session count, price, indicator value or coverage statistic from the "
                "validation partition was read to build it."
            ),
        },
    )


def _c7_adaptation_disclosed(selection: dict, protocol: dict) -> dict:
    """The adaptive step is disclosed with its residual freedom, not argued away."""
    disclosure = selection["adaptation_disclosure"]
    margin = selection["application"]["honest_qualification_of_the_margin"]
    cumulative = protocol["cumulative_experiment_count"]
    met = (
        bool(disclosure["statement"])
        and bool(disclosure["what_is_independent"])
        and bool(disclosure["what_is_not_independent"])
        and len(disclosure["how_it_is_mitigated"]) == 5
        and bool(disclosure["not_concealed"])
        and bool(margin["statement"])
        and cumulative["gate_3_total_across_both_attempts"] == "24 development runs."
        and cumulative["stage_4"] == 2
        and "does not reset" in cumulative["rule"]
        and len(protocol["adaptive_research_disclosure"]) == 10
        and len(protocol["multiple_comparisons_disclosure"]) == 3
    )
    return _condition(
        "S4D-C7",
        met,
        {
            "statement": disclosure["statement"],
            "what_is_independent": disclosure["what_is_independent"],
            "what_is_not_independent": disclosure["what_is_not_independent"],
            "mitigations": disclosure["how_it_is_mitigated"],
            "not_concealed": disclosure["not_concealed"],
            "narrowest_margin_of_the_survivor": margin,
            "cumulative_experiment_count": cumulative,
            "adaptive_research_disclosure_items": len(protocol["adaptive_research_disclosure"]),
            "multiple_comparisons_disclosure": protocol["multiple_comparisons_disclosure"],
            "no_multiplicity_correction_is_applied": (
                "Gate 4 specifies none and this protocol invents none. The cumulative count is "
                "carried forward for any later statistical interpretation instead."
            ),
        },
    )


def _c8_specification_complete(protocol: dict, criteria: dict) -> dict:
    """Every gate condition is assigned to a declared run, and every outcome is pre-committed."""
    runs_declared = protocol["runs_declared"]
    budget = protocol["iteration_budget"]
    condition_ids = {condition["id"] for condition in criteria["conditions"]}
    assigned = {
        condition
        for run in runs_declared["runs"]
        for condition in run["gates_conditions"]
    }
    # S4-C7 is an integrity condition scored from digests rather than from a run, so it is assigned
    # to the recheck rule instead of to a run. Everything else must land on a declared run.
    unassigned = sorted(condition_ids - assigned - {"S4-C7"})
    met = (
        runs_declared["count"] == 2
        and len(runs_declared["runs"]) == 2
        and runs_declared["count_is_a_hard_limit"] is True
        and all(run["gating"] for run in runs_declared["runs"])
        and budget["parameterisations"] == 1
        and budget["runs"] == 2
        and budget["sessions_reading_validation"] == 1
        and budget["re_runs_permitted_after_a_valid_completed_run"] == 0
        and not unassigned
        and bool(protocol["missing_or_invalid_data_rule"]["rule"])
        and bool(protocol["post_seal_defect_rule"]["rule"])
        and bool(protocol["partial_or_failed_run_rule"]["rule"])
        and bool(protocol["no_retuning_rule"]["rule"])
        and len(protocol["explicit_non_authorizations"]) == 7
        and len(protocol["stage_5_remains_prohibited_conditions"]) == 9
        and len(criteria["incoherent_combinations_refused"]) == 6
        and len(criteria["evaluation_integrity_rules"]) == 7
    )
    return _condition(
        "S4D-C8",
        met,
        {
            "runs_declared": runs_declared["count"],
            "run_count_is_a_hard_limit": runs_declared["count_is_a_hard_limit"],
            "run_labels": [run["run_label"] for run in runs_declared["runs"]],
            "every_declared_run_is_gating": [run["gating"] for run in runs_declared["runs"]],
            "no_neighbour_runs": runs_declared["no_neighbour_runs"],
            "iteration_budget": budget,
            "gate_conditions": sorted(condition_ids),
            "conditions_assigned_to_a_declared_run": sorted(assigned),
            "conditions_assigned_elsewhere": {
                "S4-C7": "Scored by recomputing the sealed digest set, not by a run."
            },
            "conditions_unassigned": unassigned,
            "pre_committed_outcomes": {
                "missing_or_invalid_data": protocol["missing_or_invalid_data_rule"]["rule"],
                "post_seal_defect": protocol["post_seal_defect_rule"]["rule"],
                "partial_or_failed_run": protocol["partial_or_failed_run_rule"]["rule"],
                "no_retuning": protocol["no_retuning_rule"]["rule"],
                "fail_is_a_deliverable": criteria["verdict_token_derivation"]["fail_is_a_deliverable"],
            },
            "incoherent_combinations_refused": len(criteria["incoherent_combinations_refused"]),
            "evaluation_integrity_rules": len(criteria["evaluation_integrity_rules"]),
            "explicit_non_authorizations": len(protocol["explicit_non_authorizations"]),
            "stage_5_remains_prohibited_conditions": len(
                protocol["stage_5_remains_prohibited_conditions"]
            ),
            "no_discretion_left": (
                "One parameterisation, two runs, one session, zero re-runs, every condition "
                "assigned, every failure mode pre-committed. The evaluation session executes; it "
                "does not choose."
            ),
        },
    )


def _c9_sealing_integrity(seal: dict, repo_state_id: str) -> dict:
    """Recompute the seal from the files it seals, and confirm nothing hashes itself or its tree."""
    record_results = verify_sha256_record(PROJECT_ROOT / SEAL_RECORD, root=PROJECT_ROOT)
    record_statuses = sorted(set(record_results.values()))

    preregistered = {
        rel: {
            "recorded": seal["preregistered_files"][rel]["sha256"],
            "recomputed": sha256_file(PROJECT_ROOT / rel),
        }
        for rel in PREREGISTERED
    }
    for entry in preregistered.values():
        entry["match"] = entry["recorded"] == entry["recomputed"]

    seal_text = read_text(SEAL)
    md_text = read_text(PREREG_MD)
    md_prose = _normalised_prose(md_text)
    agreement = {
        token: {"in_json": token in seal_text, "in_markdown": token in md_prose}
        for token in AGREEMENT_TOKENS
    }

    json_artifacts = (SEAL, PROTOCOL, CRITERIA, SELECTION)
    ascii_only = {rel: read_text(rel).isascii() for rel in json_artifacts}

    s4_c7 = seal["sealed_digests_for_s4_c7"]
    s4_c7_recomputed = {
        rel: sha256_file(PROJECT_ROOT / rel) == recorded
        for rel, recorded in s4_c7["entries"].items()
    }

    covered = (SEAL, PREREG_MD, PROTOCOL, CRITERIA, SELECTION, REPORT)
    tree_digest_in = {rel: repo_state_id in read_text(rel) for rel in covered}
    # A covered file may legitimately pin an individual frozen file's digest; what it may not carry
    # is a digest of a tree that includes it, or its own. So resolve every hit rather than counting
    # them — but a digest that resolves to no file is not automatically a violation either. Two of
    # these files quote the Gate 3 development runs' trade and equity content digests, which are
    # digests of run output and of no file in the tree. Those are accounted for by the key that
    # holds them, not waved through.
    digest_index = _digest_index()
    resolution: dict[str, dict] = {}
    for rel in covered:
        own = sha256_file(PROJECT_ROOT / rel)
        hits = sorted(set(HEX64.findall(read_text(rel))))
        unresolved = [digest for digest in hits if digest not in digest_index]
        if rel.endswith(".json"):
            classified = _classify_non_file_digests(load(rel), unresolved)
        else:
            classified = {"accounted_for": [], "unaccounted_for": unresolved}
        resolution[rel] = {
            "hex64_strings": len(hits),
            "resolve_to_a_tracked_file": len(hits) - len(unresolved),
            "not_a_file_digest_but_accounted_for": classified["accounted_for"],
            "unaccounted_for": classified["unaccounted_for"],
            "own_digest_present": [digest for digest in hits if digest == own],
        }
    unaccounted = {
        rel: detail["unaccounted_for"] for rel, detail in resolution.items() if detail["unaccounted_for"]
    }
    self_digest = {
        rel: detail["own_digest_present"] for rel, detail in resolution.items() if detail["own_digest_present"]
    }

    sealer_refuses_second_run = (PROJECT_ROOT / SEAL).is_file() and (
        PROJECT_ROOT / SEAL_RECORD
    ).is_file()

    met = (
        record_statuses == ["OK"]
        and len(record_results) == 5
        and all(entry["match"] for entry in preregistered.values())
        and all(flags["in_json"] and flags["in_markdown"] for flags in agreement.values())
        and all(ascii_only.values())
        and all(s4_c7_recomputed.values())
        and s4_c7["declared_set_size"] == 13
        and s4_c7["recorded_here"] == 12
        and s4_c7["own_digest_excluded"] == SEAL
        and not any(tree_digest_in.values())
        and not unaccounted
        and not self_digest
        and sealer_refuses_second_run
    )
    return _condition(
        "S4D-C9",
        met,
        {
            "checksum_record": {
                "path": SEAL_RECORD,
                "path_convention": seal["checksum_record"]["path_convention"],
                "verify_from": seal["checksum_record"]["verify_from"],
                "entries": len(record_results),
                "statuses": record_statuses,
                "does_not_name_itself": SEAL_RECORD not in record_results,
            },
            "preregistered_file_digests_recomputed": preregistered,
            "markdown_json_agreement_tokens": agreement,
            "json_artifacts_ascii_only_in_fact": ascii_only,
            "markdown_encoding": (
                "governance/STAGE_4_PREREGISTRATION.md is UTF-8; its digest is pinned in the seal, "
                "so its encoding cannot drift silently."
            ),
            "s4_c7_digest_set": {
                "declared_set_size": s4_c7["declared_set_size"],
                "recorded_in_the_seal": s4_c7["recorded_here"],
                "own_digest_excluded": s4_c7["own_digest_excluded"],
                "own_digest_location": s4_c7["own_digest_location"],
                "recomputed": s4_c7_recomputed,
            },
            "no_tree_digest_inside_a_covered_file": {
                "repo_state_id_present_in": tree_digest_in,
                "per_file_resolution": resolution,
                "files_with_an_unaccounted_for_digest": unaccounted,
                "files_carrying_their_own_digest": self_digest,
                "non_file_digest_keys_accepted": NON_FILE_DIGEST_KEY_SUFFIXES,
                "note": (
                    "Every 64-hex string in every covered file is either the digest of a tracked "
                    "file on disk or the content digest of a Gate 3 development run's trades or "
                    "equity curve, held under a key named for what it is. None is a tree digest and "
                    "none is the file's own. A bare count would prove nothing; the resolution is "
                    "the check."
                ),
            },
            "sealing_is_unrepeatable": {
                "record_exists": sealer_refuses_second_run,
                "consequence": (
                    "Re-invoking the sealing program returns exit 2 because the record already "
                    "exists. A pre-registration is sealed once; regenerating it would destroy its "
                    "meaning."
                ),
            },
        },
    )


def _c10_partitions_unchanged(seal: dict, protocol: dict, criteria: dict, lock: dict) -> dict:
    """No window was authorized, no boundary moved, and the lock digest still recomputes."""
    partition = lock["partition"]
    partitions = protocol["partitions"]
    windows = criteria["windows"]
    lock_digest = sha256_file(PROJECT_ROOT / HOLDOUT_LOCK)
    bound_lock = next(
        artifact
        for artifact in criteria["measurement_adopted_by_digest"]["bound_artifacts"]
        if artifact["path"] == HOLDOUT_LOCK
    )
    boundaries_match = (
        partitions["development"]["start"] == partition["development_start"]
        and partitions["development"]["end"] == partition["development_end"]
        and partitions["validation"]["start"] == partition["validation_start"]
        and partitions["validation"]["end"] == partition["validation_end"]
        and partitions["holdout"]["start"] == partition["holdout_start"]
        and partitions["holdout"]["end"] == partition["holdout_end"]
    )
    met = (
        seal["authorized_windows_in_this_session"] == []
        and seal["validation_window_state"] == "LOCKED"
        and seal["holdout_window_state"] == "SEALED"
        and lock["holdout_state"] == "SEALED"
        and lock_digest == bound_lock["sha256"]
        and boundaries_match
        and partitions["validation"]["state_now"] == "LOCKED"
        and partitions["holdout"]["state"] == "SEALED"
        and bool(windows["enforcement"])
        and bool(partitions["boundaries_not_recomputed"])
    )
    return _condition(
        "S4D-C10",
        met,
        {
            "authorized_windows_in_this_session": seal["authorized_windows_in_this_session"],
            "validation_window_state": seal["validation_window_state"],
            "holdout_window_state": seal["holdout_window_state"],
            "holdout_lock_digest_matches_the_adopted_value": lock_digest == bound_lock["sha256"],
            "boundaries_match_the_frozen_lock": boundaries_match,
            "boundaries": {
                "development": [partition["development_start"], partition["development_end"]],
                "validation": [partition["validation_start"], partition["validation_end"]],
                "holdout": [partition["holdout_start"], partition["holdout_end"]],
            },
            "boundaries_not_recomputed": partitions["boundaries_not_recomputed"],
            "enforcement": windows["enforcement"],
            "state_in_the_pre_registration_session": windows[
                "state_in_the_pre_registration_session"
            ],
            "state_in_the_authorized_evaluation_session": windows[
                "state_in_the_authorized_evaluation_session"
            ],
            "folds_do_not_redefine_the_window": (
                "The twelve folds partition the validation window into consecutive three-month "
                "blocks anchored on its frozen start. They tile it exactly; they do not move either "
                "boundary and they are not a new window."
            ),
        },
    )


def _c11_test_floor() -> dict:
    """Assert the floor by digest, because this session may not execute the whole suite."""
    recorded: dict[str, str] = {}
    for rel in GATE_3_RUN_RECORDS:
        record = load(rel)
        for path, digest in record["code_hashes"].items():
            if path.startswith("tests/"):
                recorded[path] = digest

    unchanged, changed, missing = [], [], []
    for path, digest in sorted(recorded.items()):
        target = PROJECT_ROOT / path
        if not target.is_file():
            missing.append(path)
        elif sha256_file(target) == digest:
            unchanged.append(path)
        else:
            changed.append(path)

    live = sorted(
        p.relative_to(PROJECT_ROOT).as_posix() for p in (PROJECT_ROOT / "tests").rglob("*.py")
    )
    added = [path for path in live if path not in recorded]

    met = (
        bool(recorded)
        and not changed
        and not missing
        and len(unchanged) == len(recorded)
        and len(live) == len(recorded) + len(added)
        and len(added) == 1
    )
    return _condition(
        "S4D-C11",
        met,
        {
            "collected_before": 560,
            "collected_now": 708,
            "collected_command": "cd stockedge100 && python -m pytest tests --collect-only -q",
            "executed_selection": (
                "cd stockedge100 && python -m pytest tests/unit/test_stage0_governance.py "
                "tests/unit/test_stage1_preregistration.py "
                "tests/unit/test_stage3_attempt2_preregistration.py "
                "tests/unit/test_stage4_preregistration.py -q"
            ),
            "executed_selection_result": {"passed": 263, "failed": 0, "skipped": 0},
            "new_module_result": {"passed": 148, "failed": 0, "skipped": 0},
            "why_the_whole_suite_was_not_run": (
                "Two integration modules read the normalised dataset and drive the engine over it, "
                "which a pre-registration session may not do. Collection imports every module but "
                "executes no body, so the floor count is safe to take that way."
            ),
            "floor_asserted_by_digest": {
                "source_run_records": list(GATE_3_RUN_RECORDS),
                "recorded": len(recorded),
                "unchanged": len(unchanged),
                "changed": changed,
                "missing": missing,
                "live_test_files": len(live),
                "added_since": added,
                "conftest_verified_and_untouched": "tests/conftest.py" in unchanged,
            },
            "nothing_subtracted": (
                "No test was weakened, skipped, xfailed or deleted. A weakened or deleted test "
                "would appear above as changed or missing."
            ),
        },
    )


def gate_conditions(
    seal: dict, protocol: dict, criteria: dict, selection: dict, lock: dict, repo_state_id: str
) -> dict:
    conditions = {
        "S4D-C1": _c1_frozen_governance(),
        "S4D-C2": _c2_validation_evaluation_permitted(protocol, criteria),
        "S4D-C3": _c3_no_restricted_observation(seal, protocol),
        "S4D-C4": _c4_selection_lawful(selection, seal),
        "S4D-C5": _c5_gate_extracted(criteria),
        "S4D-C6": _c6_authored_measurement(criteria, lock, seal),
        "S4D-C7": _c7_adaptation_disclosed(selection, protocol),
        "S4D-C8": _c8_specification_complete(protocol, criteria),
        "S4D-C9": _c9_sealing_integrity(seal, repo_state_id),
        "S4D-C10": _c10_partitions_unchanged(seal, protocol, criteria, lock),
        "S4D-C11": _c11_test_floor(),
    }
    derivation = criteria["verdict_token_derivation"]
    conditions["gate_4_admissible_candidate_exists"] = {
        "required": (
            "Whether the representative satisfies all seven Gate 4 conditions on the validation "
            "window. " + derivation["pass_condition"]
        ),
        "verdict": "NOT_RUN",
        "verdict_semantics": (
            "This entry, and only this entry, is the gate 4 determination. NOT_RUN is not a pass "
            "and is not a fail: no validation observation was read, no Stage 4 evaluator exists, "
            "and no fold return, drawdown or Sharpe ratio for the validation window has ever been "
            "computed. This entry exists so that this package cannot be read as a gate 4 result."
        ),
        "evidence": {
            "gate_4_evaluated": False,
            "gate_4_passed": False,
            "validation_rows_read": seal["restricted_data_posture"]["validation_rows_read"],
            "dataset_loads_in_this_session": seal["restricted_data_posture"][
                "dataset_loads_in_this_session"
            ],
            "across_candidates": seal["gate"]["across_candidates"],
            "single_representative_note": derivation["single_representative_note"],
            "decided_by": (
                "A later, separately authorized session that runs exactly the two declared runs of "
                "the sealed representative on the locked validation window and emits one of the two "
                "sealed gate 4 tokens."
            ),
        },
    }
    return conditions


def build() -> int:
    seal = load(SEAL)
    protocol = load(PROTOCOL)
    criteria = load(CRITERIA)
    selection = load(SELECTION)
    lock = load(HOLDOUT_LOCK)
    universe = load(UNIVERSE)

    # Taken before the build so a drift can be reported. The builder writes only into reports/ and
    # runs/, neither of which is inside the repo_state patterns, so the two should agree.
    _, repo_state_id = repo_state()

    conditions = gate_conditions(seal, protocol, criteria, selection, lock, repo_state_id)

    # The portable guard. A design session can legitimately end BLOCKED and the constitution keeps
    # negative results on disk, so an unmet condition does not suppress the deliverable — it changes
    # the verdict the deliverable carries. What is refused is a package that disagrees with its own
    # conditions.
    unmet = [
        cid
        for cid, condition in conditions.items()
        if cid.startswith("S4D-") and condition["verdict"] != "MET"
    ]
    verdict = PASS_VERDICT if not unmet else NOT_SEALABLE_VERDICT
    if unmet:
        print(f"SEAL CONDITIONS NOT MET: {', '.join(unmet)} — verdict is {verdict!r}", flush=True)

    if verdict == PASS_VERDICT and GATE_PASSED:
        print("A SEALED PRE-REGISTRATION IS NOT A GATE 4 PASS — no package written", flush=True)
        return 3
    if conditions["gate_4_admissible_candidate_exists"]["verdict"] != "NOT_RUN":
        print("GATE 4 WAS NOT EVALUATED IN THIS SESSION — no package written", flush=True)
        return 3
    derivation = criteria["verdict_token_derivation"]
    gate_4_tokens = (derivation["pass_token"], derivation["fail_token"])
    if verdict.split(" ", 2)[-1] in gate_4_tokens:
        print(f"VERDICT USES A GATE 4 TOKEN {gate_4_tokens} — no package written", flush=True)
        return 3

    representative = seal["sealed_representative"]
    strategy_modules = _resolve_strategy_module(representative["experiment_id"])
    if strategy_modules != [representative["strategy_module"]]:
        print(
            f"REPRESENTATIVE DOES NOT RESOLVE TO ONE STRATEGY MODULE: {strategy_modules}",
            flush=True,
        )
        return 3

    decision = StageDecision(
        stage="STAGE_4_VALIDATION_PREREGISTRATION",
        stage_slug="stage4",
        decision_basename="STAGE_4_VALIDATION_PREREGISTRATION",
        manifest_basename="STAGE_4_VALIDATION_PREREGISTRATION_ARTIFACT_MANIFEST",
        gate_id=4,
        gate_name="validation_robustness",
        verdict=verdict,
        gate_passed=GATE_PASSED,
        command=COMMAND,
        gate_conditions=conditions,
        evidence=[
            f"Stage 0 freeze verified digest-for-digest on both halves; "
            f"{UPSTREAM_RECORD_COUNT} upstream checksum records verified entry-for-entry from their "
            f"intended working directories before any Stage 4 artifact was authored, plus this "
            f"stage's own record at {len(verify_sha256_record(PROJECT_ROOT / SEAL_RECORD))} entries.",
            f"No mandatory constitutional selection rule exists: "
            f"{len(selection['search_for_a_mandatory_constitutional_selection_rule']['searched'])} "
            f"locations searched and the result recorded. The one constraint that did apply is "
            f"SE100-CFG-3004's neighbour prohibition, which fixes the eligible set at the two "
            f"admitted PRIMARY candidates.",
            f"The selection rule {representative['selection_rule_id']} "
            f"({representative['selection_rule_name']}) reads no return and no risk-adjusted "
            f"metric. Re-derived from declared_runs rather than read back from screen_results: "
            f"C1 tripped the section 5.1 research shutdown on "
            f"{seal['sealed_representative']['screen_results']['SE100-S3A2-C1-PULLBACK-RA1']['shutdown_trip_count']} "
            f"of 6 declared runs and is ELIMINATED; the survivor tripped it on 0 of 6. Survivor "
            f"count {representative['survivor_count']}.",
            f"The sealed representative is {representative['experiment_id']}, resolved to exactly "
            f"one strategy module by content rather than named by hand: {strategy_modules[0]}.",
            f"Gate 4 was extracted, not invented: {len(criteria['conditions'])} conditions whose "
            f"required text is located in the frozen constitution's gate 4 paragraph, "
            f"{len(criteria['frozen_gate_json_companion_verbatim']['thresholds'])} thresholds taken "
            f"from the constitution's JSON companion, and both verdict tokens derived from its "
            f"fail_result rather than from the operating prompt.",
            f"{len(criteria['measurement_adopted_by_digest']['bound_artifacts'])} measurement "
            f"artifacts adopted by digest and recomputed at build time; the single measurement this "
            f"stage authors is the walk-forward fold construction, and its "
            f"{criteria['walk_forward_fold_construction']['test_folds']['count']} folds were "
            f"recomputed here from the frozen validation boundaries alone.",
            f"{len(criteria['conflicts_found'])} conflicts recorded, including the operating "
            f"prompt's gate 4 tokens, which exist in no artifact on disk.",
            f"The seal's checksum record verifies 5/5 from the project root; all four preregistered "
            f"digests recompute; all four JSON artifacts are ASCII-only in fact; the S4-C7 recheck "
            f"set is {seal['sealed_digests_for_s4_c7']['declared_set_size']} declared and "
            f"{seal['sealed_digests_for_s4_c7']['recorded_here']} recorded, the omission being the "
            f"record itself, because nothing hashes itself.",
            "Six sealing predicates recomputed at build time. The two that must stay zero are zero, "
            "including the AST predicate whose scope covers both the sealing program and this "
            "package builder; three moved after the seal and each moved file is classified in the "
            "S4D-C3 evidence, two of the three moves having been anticipated in the sealed "
            "definitions.",
            "Restricted-data posture is zero on all six counters and structural rather than "
            "asserted: no module on the pre-registration path imports the data layer or calls a "
            "dataset loader.",
            "The test floor rose from 560 to 708 collected. Because the whole suite may not be "
            "executed in this session, 'unmodified' is asserted by recomputing every tests/ digest "
            "in both Gate 3 Attempt 2 run records against disk.",
        ],
        limitations=[
            "Gate 4 is not passed and not evaluated. A sealed pre-registration is a specification, "
            "not evidence.",
            "A Gate 4 FAIL is a live and arguably likely outcome, and it is recorded as an "
            "expectation before any validation observation exists: neither Gate 3 admitted candidate "
            "reached the frozen Sharpe floor of 0.50 on development data at the same sealed 0% cash "
            "rate.",
            "The selected representative has little drawdown headroom. Its largest non-breaching "
            "development neighbour sat 34 basis points below the 15% level that is simultaneously "
            "the section 5.1 shutdown and S4-C3's ceiling.",
            "The selection is adaptive. Return-blindness constrains the rule's output, not the "
            "choice of predicate; a different return-blind predicate might have selected "
            "differently. Five mitigations are recorded and none of them removes that freedom.",
            "The 0% documented cash rate makes S4-C2 easier to pass than a real short-rate series "
            "would. It was sealed in SE100-CFG-2001 before Gate 3 was evaluated and is not chosen "
            "here, but any Gate 4 pass must travel with that qualification.",
            "The fold construction is authored in this session. It is derived from frozen "
            "boundaries and fixed before any fold return exists, but it is the one Gate 4 "
            "measurement not adopted by digest from a pre-existing artifact.",
            "No multiplicity correction is applied. The cumulative count for any later statistical "
            "interpretation is 24 development runs across both Gate 3 attempts plus this stage's 2.",
            "One validation window is one window: three years, one instrument, one macro regime, "
            "evaluated once.",
            "Drawdown is measured at session closes. The project holds no intraday data, so every "
            "measured drawdown is a lower bound on the true intraday figure.",
            "The whole test suite was not executed, so 'unmodified' for the 15 pre-existing test "
            "files is asserted by digest recomputation rather than by a green run.",
            "scipy and pyarrow are not installed, and no Stage 4 rule requires either.",
            "No test covers this decision package and none can: tests/**/*.py is one of the "
            "patterns repo_state_id is computed over, so a test asserting that digest would "
            "invalidate the value it asserts. The package is verified by rerunning the "
            "recomputation.",
        ],
        blockers=[],
        conflicts_found=[
            f"{conflict['id']}: {conflict['description']} Resolution: {conflict['resolution']}"
            for conflict in criteria["conflicts_found"]
        ],
        produced=list(PRODUCED),
        frozen_inputs=list(FROZEN_INPUTS),
        body={
            "session_type": (
                "Representative selection and prospective validation pre-registration. No "
                "validation read, no engine run, no evaluator code, no broker contact."
            ),
            "gate_4_evaluated": False,
            "gate_4_passed": False,
            "gate_3_passed": True,
            "validation_evaluation_authorized": True,
            "validation_evaluation_authorized_for": seal["validation_evaluation_authorized_for"],
            "validation_access_authorized_in_this_session": False,
            "holdout_access_authorized": False,
            "stage_5_authorized": False,
            "paper_trading_authorized": False,
            "shadow_live_authorized": False,
            "capital_or_risk_expansion_authorized": False,
            "verdict_meaning": (
                "One representative was selected from the two Gate 3 admitted candidates by a "
                "return-blind, parameter-free rule applied in full to both and recorded with its "
                "limitation; the seven frozen gate 4 conditions were extracted from frozen text, "
                "adopted by digest where they already existed and specified prospectively in the "
                "one place where they did not; and the whole procedure was sealed before any "
                "validation observation was read, which is measured rather than asserted. It is "
                "not a gate 4 pass, not a gate 4 evaluation, not a prediction that the "
                "representative will be admitted, and not an authorization for holdout access, "
                "stage 5, paper trading, shadow-live or live trading."
            ),
            "verdict_token_is_not_a_gate_4_token": {
                "gate_4_pass_token": criteria["verdict_token_derivation"]["pass_token"],
                "gate_4_fail_token": criteria["verdict_token_derivation"]["fail_token"],
                "this_session_issued": verdict,
                "why": (
                    "PASS is one of the seven primary verdicts in constitution section 10. "
                    "STAGE_4_VALIDATION_PREREGISTRATION_FROZEN is a design-session reason code "
                    "following the precedent of STAGE_3_ATTEMPT_2_PREREGISTRATION_FROZEN. Emitting "
                    "the gate's pass token would claim a gate this session did not evaluate, and "
                    "emitting its fail token would record a rejection on evidence that does not "
                    "exist. Both belong to the evaluation session and to no other, and the builder "
                    "refuses to write a package whose verdict borrows either."
                ),
            },
            "preregistration": {
                "document_id": seal["document_id"],
                "status": seal["status"],
                "declared_utc": seal["declared_utc"],
                "run_id": seal["run_id"],
                "declared_before_any_validation_observation_was_read": seal[
                    "declared_before_any_validation_observation_was_read"
                ],
                "checksum_record": seal["checksum_record"],
                "simultaneous_seal_note": seal["simultaneous_seal_note"],
                "binding_consequences": len(seal["binding_consequences"]),
                "artifacts": {
                    "SE100-CFG-4001": PROTOCOL,
                    "SE100-CFG-4002": CRITERIA,
                    "SE100-CFG-4003": SELECTION,
                    "SE100-GOV-0008": SEAL,
                    "SE100-GOV-4000": REPORT,
                },
            },
            "representative": {
                "experiment_id": representative["experiment_id"],
                "selection_rule_id": representative["selection_rule_id"],
                "selection_rule_name": representative["selection_rule_name"],
                "survivor_count": representative["survivor_count"],
                "human_selection_required": representative["human_selection_required"],
                "eliminated_by_the_rule": representative["eliminated_by_the_rule"],
                "screen_results": representative["screen_results"],
                "strategy_module": representative["strategy_module"],
                "strategy_module_resolution": representative["strategy_module_resolution"],
                "eligible_set": selection["eligible_set"]["candidates"],
                "ineligible": [
                    entry["candidate"] for entry in selection["eligible_set"]["excluded"]
                ],
            },
            "gate": seal["gate"],
            "walk_forward_fold_construction": seal["walk_forward_fold_construction"],
            "runs_declared": seal["runs_declared"],
            "iteration_budget": protocol["iteration_budget"],
            "cumulative_experiment_count": protocol["cumulative_experiment_count"],
            "multiple_comparisons_disclosure": protocol["multiple_comparisons_disclosure"],
            "adaptation_disclosure": selection["adaptation_disclosure"],
            "no_selection_in_this_stage": protocol["no_selection_in_this_stage"],
            "windows": {
                "development": protocol["partitions"]["development"],
                "validation": protocol["partitions"]["validation"],
                "holdout": protocol["partitions"]["holdout"],
                "authorized_in_this_session": seal["authorized_windows_in_this_session"],
                "enforcement": criteria["windows"]["enforcement"],
            },
            "contamination": {
                "predicates_recomputed_at_build_time": True,
                "must_stay_zero": [
                    "modules_naming_a_stage_4_run_label",
                    "stage_4_modules_touching_restricted_data_or_a_broker",
                ],
                "moved_after_the_seal": [
                    "stage_4_evaluator_or_result_modules",
                    "stage_4_report_artifacts",
                    "stage_4_run_records",
                ],
                "files_making_the_moved_predicates_non_zero": (
                    "Enumerated with a classification each in the S4D-C3 evidence and in section 18 "
                    "of the report. None is strategy code, a Stage 4 evaluator, or a performance "
                    "result."
                ),
                "no_broker_or_credential_access": (
                    "An AST finding, not a grep finding: no forbidden import root, no dataset "
                    "loader call, no credential attribute and no string constant containing a URL "
                    "scheme in any Stage 4 module, this builder included."
                ),
            },
            "scope": {
                "what_this_session_did": [
                    "Selected one representative from the two Gate 3 admitted candidates.",
                    "Wrote and sealed the prospective Stage 4 validation pre-registration.",
                    "Built and verified this decision package.",
                ],
                "what_this_session_did_not_do": [
                    "Read a validation row or price.",
                    "Compute a validation-period indicator or count a validation-period trade.",
                    "Run the representative, or anything else, on validation data.",
                    "Inspect the holdout.",
                    "Run another development backtest.",
                    "Implement any part of the Stage 4 evaluator.",
                    "Contact a broker, read a credential, or reach the network.",
                ],
            },
            "integrity": {
                "upstream_records_verified": UPSTREAM_RECORD_COUNT,
                "adopted_artifacts_recomputed": len(seal["inputs_bound_recomputed"]),
                "gate_3_attempt_2_immutability_records": seal[
                    "gate_3_attempt_2_immutability_records"
                ],
                "nothing_repaired": (
                    "No frozen artifact was opened for writing. A failing record would have been "
                    "reported as a blocker."
                ),
            },
        },
        tests={"passed": 263, "failed": 0, "skipped": 0, "collected": 708},
        authorization_state={
            "gate_3_passed": "true",
            "gate_4_evaluated": "false",
            "gate_4_passed": "false",
            "validation_evaluation_authorized": (
                "true — for the sealed representative under the frozen procedure only, in a later "
                "separately authorized session"
            ),
            "validation_access_authorized_in_this_session": "false",
            "holdout_access_authorized": "false",
            "stage_5_authorized": "false",
            "paper_trading_authorized": "false",
            "shadow_live_authorized": "false",
            "capital_or_risk_expansion_authorized": "false",
            "live_trading_authorized": "false",
            "alpaca_paper_endpoint": "LOCKED",
            "alpaca_live_endpoint": "LOCKED",
            "order_submitting_code_in_this_repository": "none exists and none was written",
            "trade_ready": "no — StockEdge100 is not trade-ready and may not be described as such",
        },
        next_authorized_stage=(
            "STAGE_4_VALIDATION_EVALUATION — a separate session that evaluates only "
            + representative["experiment_id"]
            + ", only on the locked validation window "
            + lock["partition"]["validation_start"]
            + " to "
            + lock["partition"]["validation_end"]
            + ", in exactly the two runs declared in SE100-GOV-0008, from one dataset load, at the "
            "sealed parameterisation, scored against the seven sealed Gate 4 conditions and the "
            "twelve sealed folds, emitting one of the two sealed Gate 4 tokens. Nothing else is "
            "authorized: no parameter change, no neighbour run, no run of the other admitted "
            "candidate, no re-run after a valid completed run, and no second session."
        ),
        dataset_hashes={},
        universe_version=universe["universe_version"],
        date_range=None,
        holdout_state=lock["holdout_state"],
        config_hash=sha256_file(PROJECT_ROOT / PROTOCOL),
        random_seed=None,
        run_notes=[
            "Design and pre-registration session. No validation or holdout observation was read, no "
            "engine was run, and no performance value for the validation window exists.",
            "exit_status is GATE_NOT_PASSED because gate_passed is false. That is correct and is "
            "not a failed run: gate 4 was not evaluated in this session, so it cannot have been "
            "passed.",
            "The single gate 4 determination in the decision record is the "
            "gate_4_admissible_candidate_exists condition, recorded NOT_RUN.",
            "The verdict token is a design-session reason code and is neither of gate 4's own "
            "tokens; the builder refuses to write a package whose verdict borrows either.",
            "date_range and random_seed are null and dataset_hashes is empty because no dataset was "
            "loaded. universe_version and holdout_state are read from the frozen Stage 1 artifacts.",
            "config_hash is the sha256 of config/stage4_validation_protocol.json.",
            "Three sealing predicates moved after the seal; two of the moves were anticipated in "
            "the sealed definitions and the third, this package builder, is classified in the "
            "S4D-C3 evidence rather than dodged by renaming the file.",
            "live_trading_authorized remains false.",
        ],
    )

    result = build_stage_package(decision)
    if not result.freeze_ok:
        print("STAGE 0 FREEZE VERIFICATION FAILED — see the decision record", flush=True)
        return 2
    if result.repo_state_id != repo_state_id:
        print(
            f"repo_state_id MOVED DURING THE BUILD: {repo_state_id} -> {result.repo_state_id}",
            flush=True,
        )

    print(f"verdict       {verdict}")
    print(f"run_id        {result.run_id}")
    print(f"repo_state_id {result.repo_state_id}")
    print(f"timestamp     {result.timestamp_utc}")
    print(f"freeze_ok     {result.freeze_ok}")
    for path in (result.decision_path, result.manifest_path, result.checksum_path, result.run_record_path):
        print(f"wrote         {Path(path).relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(build())
