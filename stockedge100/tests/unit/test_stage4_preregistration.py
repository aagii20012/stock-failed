"""Adversarial tests for the Stage 4 validation-evaluation pre-registration.

The Stage 4 seal is the last artifact written before anything reads the locked validation window, so
these tests carry two jobs that no later test can do.

The first is the ordinary one: prove the sealed record says what its four pre-registered files say,
that its digests are the digests on disk, that Gate 4's seven conditions were extracted rather than
invented, and that the representative was selected by a rule that decides rather than by a
preference. Every threshold assertion evaluates the **sealed predicate string** instead of a
restatement of it, in both directions, so a predicate that drifted from its boundary text fails here.

The second is fail-closed proof. A pre-registration session may not read a validation observation, so
the tests that prove it cannot may not read one either. They therefore assert on **dates alone**: the
frozen window boundaries, which SE100-GOV-1005 publishes as metadata, and the guards that refuse a
session outside the authorized window. Nothing here loads a dataset, and the AST predicate proves
structurally that nothing on the pre-registration path could.

``EXPECTED_DIGESTS`` is written out independently of
``governance/STAGE_4_PREREGISTRATION.sha256``, so rewriting an artifact together with its checksum
record still fails this module.
"""

from __future__ import annotations

import ast
import datetime as dt
import json
import re
from decimal import Decimal
from pathlib import Path

import pytest

from stockedge100.backtest.errors import LookAheadError
from stockedge100.backtest.market import MarketView
from stockedge100.backtest.window import (
    DEVELOPMENT,
    HOLDOUT,
    VALIDATION,
    WindowViolation,
    development_window,
    load_partition_bounds,
    window_named,
)
from stockedge100.reporting import stage4_preregistration as sealer

# Pinned by hand from the sealed files, not read out of the checksum record they are supposed to
# corroborate.
EXPECTED_DIGESTS = {
    "config/stage4_validation_protocol.json": (
        "2c9eeb7cf1123430e2d9b1163478d6923879c68fdc17e44b45b5910137a0acea"
    ),
    "config/stage4_gate_criteria.json": (
        "2191e905121b5fcaf768224fd79577dee3f8b3d5653836843fa1a3514e2c4c0d"
    ),
    "config/stage4_representative_selection.json": (
        "fb4f3eb506989a80a08dda752f83d390589f1f3126effece91257e43f899d3dc"
    ),
    "governance/STAGE_4_PREREGISTRATION.md": (
        "952897926fa281b85ee11eefde825e04a7d9cd483d22aef2fee568c5b5672fd1"
    ),
    "governance/STAGE_4_PREREGISTRATION.json": (
        "aa33202aa98b5d48839e17d47557e61684ec08b82e992fd8862222582b2a246b"
    ),
}

REPRESENTATIVE = "SE100-S3A2-C2-MEANREV-RA1"
ELIMINATED = "SE100-S3A2-C1-PULLBACK-RA1"
INELIGIBLE = "SE100-S3A2-C3-DEFENSIVE-RA1"
CONDITION_IDS = ("S4-C1", "S4-C2", "S4-C3", "S4-C4", "S4-C5", "S4-C6", "S4-C7")

HEX64 = re.compile(r"\b[0-9a-f]{64}\b")
RECORD_LINE = re.compile(r"([0-9a-f]{64})\s[\s*](.+)")


# --------------------------------------------------------------------------------------------
# Fixtures. Defined here rather than in tests/conftest.py, which is hashed in the Stage 0 manifest.
# --------------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def prereg(governance_dir: Path) -> dict:
    return json.loads((governance_dir / "STAGE_4_PREREGISTRATION.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def protocol(project_root: Path) -> dict:
    return json.loads(
        (project_root / "config" / "stage4_validation_protocol.json").read_text(encoding="utf-8")
    )


@pytest.fixture(scope="module")
def criteria(project_root: Path) -> dict:
    return json.loads(
        (project_root / "config" / "stage4_gate_criteria.json").read_text(encoding="utf-8")
    )


@pytest.fixture(scope="module")
def selection(project_root: Path) -> dict:
    return json.loads(
        (project_root / "config" / "stage4_representative_selection.json").read_text(
            encoding="utf-8"
        )
    )


@pytest.fixture(scope="module")
def document(governance_dir: Path) -> str:
    return (governance_dir / "STAGE_4_PREREGISTRATION.md").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def bounds() -> dict[str, str]:
    """The frozen partition boundaries. Dates only; SE100-GOV-1005 publishes them as metadata."""
    return load_partition_bounds()


def _parse_record(text: str) -> dict[str, str]:
    entries = {}
    for line in text.splitlines():
        match = RECORD_LINE.match(line.strip())
        if match:
            entries[match.group(2).strip()] = match.group(1)
    return entries


def _evaluate(predicate: str, **values: Decimal) -> bool:
    """Evaluate a sealed predicate string, so the test exercises the seal and not a paraphrase."""
    return bool(eval(predicate, {"Decimal": Decimal, "__builtins__": {}}, dict(values)))


def _condition(criteria: dict, condition_id: str) -> dict:
    return next(item for item in criteria["conditions"] if item["id"] == condition_id)


def _plus_months(date: dt.date, months: int) -> dt.date:
    month_index = date.month - 1 + months
    return dt.date(date.year + month_index // 12, month_index % 12 + 1, date.day)


def _gate_4_verdict(verdicts: dict[str, str], derivation: dict) -> str:
    """The sealed conjunction: every hard condition MET, all seven present, or the gate fails."""
    if set(verdicts) != set(CONDITION_IDS):
        return derivation["fail_token"]
    if all(verdict == "MET" for verdict in verdicts.values()):
        return derivation["pass_token"]
    return derivation["fail_token"]


# --------------------------------------------------------------------------------------------
# Clean controls. A failure below these is attributable to the assertion, not to the harness.
# --------------------------------------------------------------------------------------------


def test_control_the_four_preregistered_files_and_the_seal_are_on_disk(project_root: Path):
    for rel in (*sealer.PREREGISTERED, sealer.RECORD_REL, sealer.RECORD_SHA_REL):
        assert (project_root / rel).is_file(), rel


def test_control_the_seal_parses_and_declares_itself_sealed(prereg: dict):
    assert prereg["document_id"] == "SE100-GOV-0008"
    assert prereg["record_type"] == "PRE_REGISTRATION"
    assert prereg["status"] == "SEALED"
    assert prereg["stage"] == 4
    assert prereg["supersedes"] is None
    assert prereg["declared_before_any_validation_observation_was_read"] is True


def test_control_a_synthetic_all_met_representative_is_a_gate_4_pass(criteria: dict):
    """Without this control, an evaluator hard-wired to FAIL would look identical to a real FAIL."""
    derivation = criteria["verdict_token_derivation"]
    all_met = {condition_id: "MET" for condition_id in CONDITION_IDS}
    assert _gate_4_verdict(all_met, derivation) == derivation["pass_token"]
    assert derivation["pass_token"] == "STAGE_4_STRATEGY_ADMITTED_IN_VALIDATION"


def test_control_the_frozen_development_window_still_admits_its_own_last_session(bounds: dict):
    development_window().check(dt.date.fromisoformat(bounds["development_end"]))


# --------------------------------------------------------------------------------------------
# The seal: digests, coverage, and nothing hashing itself
# --------------------------------------------------------------------------------------------


def test_pinned_digests_match_the_files_on_disk(project_root: Path):
    from stockedge100.audit import sha256_file

    for rel, digest in EXPECTED_DIGESTS.items():
        assert sha256_file(project_root / rel) == digest, rel


def test_the_checksum_record_covers_five_files_and_not_itself(project_root: Path):
    entries = _parse_record((project_root / sealer.RECORD_SHA_REL).read_text(encoding="utf-8"))
    assert set(entries) == set(EXPECTED_DIGESTS)
    assert entries == EXPECTED_DIGESTS
    assert sealer.RECORD_SHA_REL not in entries


def test_the_checksum_record_is_project_root_relative_and_says_so(prereg: dict):
    record = prereg["checksum_record"]
    assert record["path"] == sealer.RECORD_SHA_REL
    assert record["path_convention"] == "project-root-relative"
    assert record["verify_from"] == "stockedge100/"
    assert record["command"].endswith(sealer.RECORD_SHA_REL)


def test_the_seal_records_the_digest_of_every_preregistered_file(prereg: dict):
    recorded = {rel: entry["sha256"] for rel, entry in prereg["preregistered_files"].items()}
    assert set(recorded) == set(sealer.PREREGISTERED)
    for rel, digest in recorded.items():
        assert digest == EXPECTED_DIGESTS[rel], rel


def test_the_seal_carries_no_digest_of_the_tree_it_belongs_to(prereg: dict, project_root: Path):
    """A tree digest resolves to no file. Counting hex strings would prove nothing; resolving does."""
    permitted = set(EXPECTED_DIGESTS.values()) - {
        EXPECTED_DIGESTS["governance/STAGE_4_PREREGISTRATION.json"]
    }
    permitted |= {entry["sha256"] for entry in prereg["inputs_bound_recomputed"].values()}
    permitted |= set(prereg["sealed_digests_for_s4_c7"]["entries"].values())
    permitted |= set(HEX64.findall(json.dumps(prereg["stage_0_freeze_verification"])))
    found = set(HEX64.findall(json.dumps(prereg)))
    assert found <= permitted, sorted(found - permitted)
    assert EXPECTED_DIGESTS["governance/STAGE_4_PREREGISTRATION.json"] not in found


def test_the_seal_omits_repo_state_id_and_points_at_the_run_record(prereg: dict):
    assert "repo_state_id" not in prereg
    location = prereg["repo_state_id_location"]
    assert "runs/" + prereg["run_id"] + ".json" in location
    assert "stale on write" in location


def test_the_simultaneous_seal_note_explains_why_no_file_binds_another(prereg: dict):
    note = prereg["simultaneous_seal_note"]
    for rel in sealer.PREREGISTERED:
        assert rel in note
    assert sealer.RECORD_SHA_REL in note


def test_every_digest_pinned_in_the_document_resolves_to_a_live_file(document: str):
    index = sealer._digest_index()
    pinned = set(HEX64.findall(document))
    assert pinned, "the document pins no digest at all; it adopts its inputs by digest"
    unresolved = sorted(digest for digest in pinned if digest not in index)
    assert unresolved == []
    assert EXPECTED_DIGESTS["governance/STAGE_4_PREREGISTRATION.md"] not in pinned


def test_the_declaration_timestamp_and_run_id_agree(prereg: dict):
    declared = prereg["declared_utc"]
    dt.datetime.strptime(declared, "%Y-%m-%dT%H:%M:%SZ")
    compact = declared.replace("-", "").replace(":", "")
    assert prereg["run_id"] == "SE100-R-" + compact


def test_the_run_record_agrees_with_the_seal_field_for_field(project_root: Path, prereg: dict):
    record = json.loads(
        (project_root / "runs" / f"{prereg['run_id']}.json").read_text(encoding="utf-8")
    )
    assert record["stage"] == "STAGE_4_VALIDATION_PRE_REGISTRATION"
    assert record["timestamp_utc"] == prereg["declared_utc"]
    assert record["exit_status"] == "OK"
    assert record["holdout_state"] == "SEALED"
    assert record["dataset_hashes"] == {}, "no dataset was loaded, so none may be hashed"
    assert record["date_range"] is None
    assert record["strategy_id"] is None
    assert record["random_seed"] is None
    assert len(HEX64.findall(record["repo_state_id"])) == 1
    assert (
        record["output_artifact_hashes"][sealer.RECORD_REL]
        == EXPECTED_DIGESTS["governance/STAGE_4_PREREGISTRATION.json"]
    )


def test_the_run_record_predates_this_test_module(project_root: Path, prereg: dict):
    """The seal was written before its tests existed, which is the only order that proves nothing
    was tuned to make the seal pass. ``repo_state()`` covers ``tests/**/*.py``, so this file cannot
    appear in a record captured before it was written."""
    record = json.loads(
        (project_root / "runs" / f"{prereg['run_id']}.json").read_text(encoding="utf-8")
    )
    assert "tests/unit/test_stage3_attempt2_preregistration.py" in record["code_hashes"]
    assert "tests/unit/test_stage4_preregistration.py" not in record["code_hashes"]


# --------------------------------------------------------------------------------------------
# Representative selection
# --------------------------------------------------------------------------------------------


def test_the_eligible_set_is_exactly_the_two_gate_3_admitted_candidates(selection: dict):
    assert selection["eligible_set"]["candidates"] == [ELIMINATED, REPRESENTATIVE]


def test_the_rejected_candidate_is_excluded_and_not_reconsidered(selection: dict):
    excluded = {entry["candidate"]: entry["reason"] for entry in selection["eligible_set"]["excluded"]}
    assert INELIGIBLE in excluded
    assert "not reconsidered" in excluded[INELIGIBLE].lower()
    assert any("neighbour" in candidate for candidate in excluded)
    assert any("Attempt 1" in candidate for candidate in excluded)


def test_the_search_for_a_mandatory_selection_rule_is_recorded_and_came_back_empty(
    selection: dict,
):
    """The constitution is searched first, and the negative result is what licenses constructing a
    rule at all. Recording only the constructed rule would hide that step."""
    search = selection["search_for_a_mandatory_constitutional_selection_rule"]
    searched = " ".join(search["searched"])
    for where in (
        "governance/STAGE_0_CONSTITUTION.md",
        "governance/STAGE_0_CONSTITUTION.json",
        "config/*.json",
        "reports/stage3_attempt2/*",
    ):
        assert where in searched, where
    assert search["result"].startswith("No mandatory selection rule exists.")
    assert "says nothing about choosing among candidates that pass" in search["result"]
    assert "section 8 permits it" in search["consequence"]
    assert "must not be a rationalisation of a preferred outcome" in search["consequence"]


def test_the_one_constraint_the_search_did_find_is_the_neighbour_prohibition(selection: dict):
    """A search that returns nothing at all is indistinguishable from a search that was not run."""
    constraint = selection["search_for_a_mandatory_constitutional_selection_rule"][
        "constraint_that_did_apply"
    ]
    assert "SE100-CFG-3004" in constraint["source"]
    assert constraint["answer_verbatim"] == "No. Never. Under no result."
    assert "exactly the two admitted PRIMARY candidates" in constraint["effect"]


def test_the_selection_rule_is_return_blind(selection: dict):
    rule = selection["selection_rule"]
    assert rule["id"] == "SE100-CFG-4003-R1"
    assert rule["reads_no_return"] is True
    assert rule["reads_no_risk_adjusted_metric"] is True
    assert "Development-window evidence only" in rule["applied_to"]
    assert "does not compare magnitudes" in rule["output_is_binary_per_variant"]


def test_every_term_of_the_rule_is_bound_to_a_frozen_artifact(selection: dict):
    """Five terms, each traced to a named frozen or sealed artifact. Two cite a specific sealed
    field rather than a whole-file digest, which is why the check is 'names an artifact' plus 'every
    digest it does cite still resolves' rather than 'carries a digest'."""
    provenance = selection["selection_rule"]["provenance"]
    index = sealer._digest_index()
    assert "Nothing in it is a number this stage picked." in provenance["principle"]
    terms = provenance["terms"]
    assert len(terms) == 5
    for term in terms:
        source = term["source"]
        assert re.search(r"(governance|config)/[A-Za-z0-9_]+\.(md|json)", source), term["term"]
        assert term["note"], term["term"]
        for digest in HEX64.findall(source):
            assert digest in index, (term["term"], digest)
    assert sum(bool(HEX64.search(term["source"])) for term in terms) >= 3


def test_the_fifteen_percent_level_is_adopted_from_two_frozen_sources_that_agree(selection: dict):
    """The level appears twice upstream. The rule adopts both statements rather than picking one."""
    term = next(
        item
        for item in selection["selection_rule"]["provenance"]["terms"]
        if item["term"] == "the 15% level"
    )
    assert "governance/STAGE_0_CONSTITUTION.md section 5.1" in term["source"]
    assert "config/stage2_cost_model.json risk.research_shutdown_drawdown_fraction 0.15" in term["source"]
    assert len(HEX64.findall(term["source"])) == 2
    assert "falls 15% below its running high-water mark" in term["note"]
    assert "does not choose a level" in term["note"]


def test_the_rule_decides_and_decides_the_representative_it_names(selection: dict):
    outcome = selection["application"]["outcome"]
    assert outcome["selected_representative"] == REPRESENTATIVE
    assert outcome["survivors"] == [REPRESENTATIVE]
    assert outcome["survivor_count"] == 1
    assert outcome["rule_decides"] is True
    assert outcome["human_selection_required"] is False


def test_reapplying_the_rule_to_the_sealed_evidence_reproduces_the_outcome(selection: dict):
    """The screen is arithmetic over booleans, so the test can redo it rather than trust it."""
    survivors, eliminated = [], []
    for entry in selection["application"]["candidates"]:
        trips = [run for run in entry["declared_runs"] if run["shutdown_tripped"]]
        assert entry["shutdown_trip_count"] == len(trips), entry["candidate"]
        assert entry["declared_run_count"] == len(entry["declared_runs"]), entry["candidate"]
        (eliminated if trips else survivors).append(entry["candidate"])
        assert entry["screen_result"] == ("ELIMINATED" if trips else "SURVIVES")
    assert survivors == [REPRESENTATIVE]
    assert eliminated == [ELIMINATED]


def test_the_screen_eliminates_on_any_trip_including_the_stressed_run(selection: dict):
    entry = next(
        item
        for item in selection["application"]["candidates"]
        if item["candidate"] == ELIMINATED
    )
    assert entry["shutdown_trip_count"] == 2
    assert entry["declared_run_count"] == 6
    assert any("#STRESS" in trip for trip in entry["trips_at"])
    assert any("#N1" in trip for trip in entry["trips_at"])


def test_the_screen_counts_the_declared_variant_set_and_nothing_wider(selection: dict):
    for entry in selection["application"]["candidates"]:
        kinds = [run["kind"] for run in entry["declared_runs"]]
        assert kinds.count("primary") == 1
        assert kinds.count("declared robustness neighbour") == 4
        assert len(kinds) == 6


def test_the_selection_read_only_gate_3_development_evidence_bound_by_digest(selection: dict):
    source = selection["application"]["evidence_source"]
    assert source["path"] == "reports/stage3_attempt2/STAGE_3_ATTEMPT_2_STRATEGY_RESEARCH.json"
    assert HEX64.fullmatch(source["sha256"])
    assert "Development window only" in source["fields_read"]
    assert "validation" not in source["fields_read"].lower()


def test_the_selection_evidence_is_the_file_that_is_still_on_disk(project_root: Path, selection: dict):
    from stockedge100.audit import sha256_file

    source = selection["application"]["evidence_source"]
    assert sha256_file(project_root / source["path"]) == source["sha256"]
    corroboration = source["corroborated_by"]
    assert sha256_file(project_root / corroboration["path"]) == corroboration["sha256"]


def test_the_margin_is_qualified_rather_than_advertised(selection: dict):
    qualification = selection["application"]["honest_qualification_of_the_margin"]
    assert len(qualification["statement"]) > 80


def test_the_adaptive_step_is_disclosed_rather_than_denied(selection: dict):
    disclosure = selection["adaptation_disclosure"]
    assert "adaptive step" in disclosure["statement"]
    assert disclosure["what_is_not_independent"]


def test_substitution_is_prohibited_after_the_seal_including_after_a_fail(selection: dict):
    prohibited = " ".join(selection["prohibited_after_this_seal"])
    assert "including a Gate 4 FAIL" in prohibited
    assert ELIMINATED in prohibited
    assert INELIGIBLE in prohibited
    assert "robustness neighbour" in prohibited
    assert "risk overlay" in prohibited


def test_the_seal_records_the_selection_arithmetic_not_only_its_conclusion(prereg: dict):
    sealed = prereg["sealed_representative"]
    assert sealed["experiment_id"] == REPRESENTATIVE
    assert sealed["eliminated_by_the_rule"] == [ELIMINATED]
    assert sealed["screen_results"][ELIMINATED] == {
        "declared_run_count": 6,
        "shutdown_trip_count": 2,
        "screen_result": "ELIMINATED",
    }
    assert sealed["screen_results"][REPRESENTATIVE] == {
        "declared_run_count": 6,
        "shutdown_trip_count": 0,
        "screen_result": "SURVIVES",
    }


def test_the_strategy_module_was_resolved_by_content_and_still_matches(
    project_root: Path, prereg: dict
):
    from stockedge100.audit import sha256_file

    sealed = prereg["sealed_representative"]
    assert sealer._resolve_strategy_module(REPRESENTATIVE) == [sealed["strategy_module"]]
    assert sha256_file(project_root / sealed["strategy_module"]) == sealed["strategy_module_sha256"]
    assert "Resolved by content" in sealed["strategy_module_resolution"]


# --------------------------------------------------------------------------------------------
# Gate 4, extracted rather than invented
# --------------------------------------------------------------------------------------------


def test_the_gate_is_constitutional_gate_4_with_seven_conditions(criteria: dict, prereg: dict):
    assert criteria["gate_id"] == 4
    assert [item["id"] for item in criteria["conditions"]] == list(CONDITION_IDS)
    assert prereg["gate"]["constitutional_gate"] == 4
    assert prereg["gate"]["condition_ids"] == list(CONDITION_IDS)
    assert prereg["gate"]["conditions_evaluated"] == 7
    assert prereg["gate"]["prompt_stage"] == 4


def test_every_condition_quotes_the_frozen_gate_text_it_implements(criteria: dict):
    frozen = criteria["frozen_gate_text_verbatim"]
    for condition in criteria["conditions"]:
        assert condition["required_verbatim"] in frozen, condition["id"]


def test_every_condition_carries_a_predicate_a_boundary_and_a_not_evaluable_treatment(
    criteria: dict,
):
    for condition in criteria["conditions"]:
        assert condition["predicate"], condition["id"]
        assert condition["boundary"], condition["id"]
        assert "NOT_EVALUABLE" in json.dumps(condition), condition["id"]


@pytest.mark.parametrize(
    "condition_id,variable,passing,failing",
    [
        ("S4-C1", "total_return", "0.0000001", "0"),
        ("S4-C2", "sharpe", "0.50", "0.4999999"),
        ("S4-C3", "max_drawdown", "0.15", "0.1500001"),
        ("S4-C4", "profit_factor", "1.15", "1.1499999"),
        ("S4-C5", "stressed_total_return", "0.0000001", "0"),
    ],
)
def test_each_sealed_threshold_predicate_holds_exactly_at_its_boundary(
    criteria: dict, condition_id: str, variable: str, passing: str, failing: str
):
    """Evaluates the sealed predicate string itself, in both directions, at the boundary the sealed
    ``boundary`` text claims. A predicate that drifted from its prose fails here."""
    predicate = _condition(criteria, condition_id)["predicate"]
    assert _evaluate(predicate, **{variable: Decimal(passing)}) is True
    assert _evaluate(predicate, **{variable: Decimal(failing)}) is False


def test_the_strict_and_inclusive_boundaries_are_not_harmonised(criteria: dict):
    assert "Strict" in _condition(criteria, "S4-C1")["boundary"]
    assert "Strict" in _condition(criteria, "S4-C5")["boundary"]
    for condition_id in ("S4-C2", "S4-C3", "S4-C4", "S4-C6"):
        assert "Inclusive" in _condition(criteria, condition_id)["boundary"], condition_id


def test_the_documented_cash_rate_is_zero_quoted_from_the_frozen_cost_model(criteria: dict):
    cash = _condition(criteria, "S4-C2")["documented_cash_rate"]
    assert cash["value"] == "0.00"
    assert "SE100-CFG-2001" in cash["source"]
    assert "cannot make this condition harder to pass" in cash["direction_of_bias"]
    assert cash["no_substitute_may_be_introduced_later"]


def test_six_thresholds_are_adopted_by_digest_and_still_bind(project_root: Path, criteria: dict):
    from stockedge100.audit import sha256_file

    bound = criteria["measurement_adopted_by_digest"]["bound_artifacts"]
    assert len(bound) == 3
    for entry in bound:
        assert sha256_file(project_root / entry["path"]) == entry["sha256"], entry["path"]


def test_every_protocol_input_adopted_by_digest_still_binds(project_root: Path, protocol: dict):
    from stockedge100.audit import sha256_file

    bound = protocol["inputs_bound"]["bound_by_digest"]
    assert len(bound) == 9
    for entry in bound:
        assert sha256_file(project_root / entry["path"]) == entry["sha256"], entry["path"]


def test_the_seal_recomputed_every_bound_digest_at_seal_time(prereg: dict):
    recomputed = prereg["inputs_bound_recomputed"]
    assert len(recomputed) == 9 + 3 - 3, "the two sources overlap on three artifacts"
    for rel, entry in recomputed.items():
        assert HEX64.fullmatch(entry["sha256"]), rel
        assert entry["bound_by"] in sealer.PREREGISTERED


def test_the_verdict_tokens_are_derived_from_the_frozen_gate_and_not_from_a_prompt(
    project_root: Path, criteria: dict
):
    """Derives both tokens from the companion the way the sealed derivation says it did, rather than
    restating them. A token that had drifted from the constitution's ``fail_result`` fails here."""
    from stockedge100.audit import sha256_file

    source = criteria["frozen_gate_json_companion_source"]
    assert sha256_file(project_root / source["path"]) == source["sha256"]
    companion = criteria["frozen_gate_json_companion_verbatim"]
    assert companion["id"] == 4
    assert companion["name"] == "validation_robustness"
    assert companion["fail_result"] == "STRATEGY_REJECTED_IN_VALIDATION"
    assert "pass_result" not in companion, "the companion has no pass token; that is S4-CONFLICT-2"

    derivation = criteria["verdict_token_derivation"]
    assert derivation["fail_token"] == "STAGE_4_" + companion["fail_result"]
    assert derivation["pass_token"] == derivation["fail_token"].replace("REJECTED", "ADMITTED")
    assert derivation["pass_token"] == "STAGE_4_STRATEGY_ADMITTED_IN_VALIDATION"
    assert "SE100-CFG-3002" in derivation["derivation_method"]
    assert (
        "Neither token is invented and neither is taken from an operating prompt."
        in derivation["derivation_method"]
    )


@pytest.mark.parametrize(
    "condition_id,threshold_key,scale",
    [
        ("S4-C2", "sharpe_min", Decimal(1)),
        ("S4-C3", "max_drawdown_pct", Decimal(100)),
        ("S4-C4", "profit_factor_min", Decimal(1)),
        ("S4-C6", "positive_walk_forward_folds_pct_min", Decimal(100)),
    ],
)
def test_each_numeric_threshold_is_the_constitution_s_own_number(
    criteria: dict, condition_id: str, threshold_key: str, scale: Decimal
):
    """The predicate's literal must equal the frozen companion's threshold, converted only by the
    percent-to-fraction scale the condition declares. This is the 'extracted, not invented' check."""
    thresholds = criteria["frozen_gate_json_companion_verbatim"]["thresholds"]
    predicate = _condition(criteria, condition_id)["predicate"]
    literals = re.findall(r"Decimal\('([0-9.]+)'\)", predicate)
    assert len(literals) == 1, predicate
    assert Decimal(literals[0]) == Decimal(str(thresholds[threshold_key])) / scale


@pytest.mark.parametrize(
    "condition_id,threshold_key", [("S4-C1", "net_return_positive"), ("S4-C5", "stressed_cost_return_positive")]
)
def test_the_two_boolean_thresholds_became_strict_positivity(
    criteria: dict, condition_id: str, threshold_key: str
):
    thresholds = criteria["frozen_gate_json_companion_verbatim"]["thresholds"]
    assert thresholds[threshold_key] is True
    predicate = _condition(criteria, condition_id)["predicate"]
    assert "> Decimal('0')" in predicate


def test_the_seal_carries_the_tokens_from_the_criteria_and_names_their_source(
    prereg: dict, criteria: dict
):
    derivation = criteria["verdict_token_derivation"]
    gate = prereg["gate"]
    assert gate["pass_token"] == derivation["pass_token"]
    assert gate["fail_token"] == derivation["fail_token"]
    assert gate["token_source"] == sealer.CRITERIA_REL + " verdict_token_derivation"


def test_gate_4_is_conjunctive_within_the_candidate_with_no_disjunction_across(
    prereg: dict, criteria: dict
):
    assert prereg["gate"]["within_candidate"] == "CONJUNCTIVE"
    assert prereg["gate"]["across_candidates"] == "NOT_APPLICABLE_EXACTLY_ONE_REPRESENTATIVE"
    note = criteria["verdict_token_derivation"]["conjunctive_note"]
    assert "Gate 4 has no disjunction" in note
    assert "no second candidate whose result could rescue it" in note


@pytest.mark.parametrize("failing", ["NOT_MET", "NOT_EVALUABLE", "NOT_RUN", "UNKNOWN"])
def test_one_non_met_condition_fails_the_whole_gate(criteria: dict, failing: str):
    derivation = criteria["verdict_token_derivation"]
    verdicts = {condition_id: "MET" for condition_id in CONDITION_IDS}
    verdicts["S4-C6"] = failing
    assert _gate_4_verdict(verdicts, derivation) == derivation["fail_token"]
    if failing != "NOT_MET":
        assert failing in derivation["fail_condition"]


def test_a_missing_condition_is_not_a_pass(criteria: dict):
    derivation = criteria["verdict_token_derivation"]
    verdicts = {condition_id: "MET" for condition_id in CONDITION_IDS if condition_id != "S4-C7"}
    assert _gate_4_verdict(verdicts, derivation) == derivation["fail_token"]
    assert "evidence is missing" in derivation["fail_condition"]


def test_missing_evidence_may_not_be_converted_to_a_pass(criteria: dict):
    other = criteria["verdict_token_derivation"]["other_tokens_available"]
    assert "may never be converted to PASS" in other
    for token in ("BLOCKED_BY_DATA", "INSUFFICIENT_EVIDENCE", "NOT_RUN"):
        assert token in other


def test_a_fail_is_a_deliverable_rather_than_a_reason_to_retune(criteria: dict, protocol: dict):
    assert "kept on disk" in criteria["verdict_token_derivation"]["fail_is_a_deliverable"]
    assert protocol["no_retuning_rule"]


def test_all_five_conflicts_are_recorded_with_a_resolution(criteria: dict, prereg: dict):
    ids = [item["id"] for item in criteria["conflicts_found"]]
    assert ids == [f"S4-CONFLICT-{n}" for n in range(1, 6)]
    assert prereg["gate"]["conflicts_recorded"] == ids
    for conflict in criteria["conflicts_found"]:
        for key in ("description", "resolution", "action_taken"):
            assert conflict[key], (conflict["id"], key)


def test_the_missing_pass_token_conflict_refuses_to_borrow_gate_5s(criteria: dict):
    conflict = next(
        item for item in criteria["conflicts_found"] if item["id"] == "S4-CONFLICT-2"
    )
    assert "has NO pass_result key" in conflict["description"]
    assert "Reported, not repaired" in conflict["action_taken"]
    assert "none exists in governance/, config/, src/, tests/ or reports/" in conflict["action_taken"]
    not_borrowed = conflict["explicitly_not_borrowed"]
    assert "ELIGIBLE_FOR_PAPER_TRADING is NOT Gate 4's pass token" in not_borrowed
    assert "claiming a gate it did not evaluate" in not_borrowed


def test_the_stressed_run_changes_status_from_non_gating_to_gating(criteria: dict):
    change = criteria["stressed_cost_status_change"]
    assert "NON-GATING" in change["at_gate_3"]
    assert change["at_gate_4"].startswith("GATING")
    assert "2.0" in change["stress_multiplier_is_not_re_chosen"]
    assert "does not select a stress level" in change["stress_multiplier_is_not_re_chosen"]
    assert _condition(criteria, "S4-C5")["status"].startswith("GATING")


def test_the_two_fifteen_percent_numbers_are_reconciled_not_duplicated(criteria: dict, prereg: dict):
    interaction = _condition(criteria, "S4-C3")["interaction"]
    assert "S4-CONFLICT-3" in interaction
    assert "if and only if the shutdown never fires" in interaction
    assert any("if and only if the shutdown never fires" in line for line in prereg["binding_consequences"])


def test_gate_5_is_not_unlocked_by_this_file(criteria: dict):
    gate_5 = criteria["gate_5_is_not_unlocked_by_this_file"]
    assert "ELIGIBLE_FOR_PAPER_TRADING" in json.dumps(gate_5)
    assert "ELIGIBLE_FOR_PAPER_TRADING" != criteria["verdict_token_derivation"]["pass_token"]


# --------------------------------------------------------------------------------------------
# The one measurement authored here: the walk-forward fold construction
# --------------------------------------------------------------------------------------------


def test_the_folds_tile_the_frozen_validation_window_exactly(criteria: dict, bounds: dict):
    """Dates only. The construction is a function of the frozen boundaries and nothing else."""
    folds = criteria["walk_forward_fold_construction"]["test_folds"]["folds"]
    assert [fold["fold"] for fold in folds] == list(range(1, 13))
    assert folds[0]["start"] == bounds["validation_start"]
    assert folds[-1]["end"] == bounds["validation_end"]
    for previous, current in zip(folds, folds[1:]):
        previous_end = dt.date.fromisoformat(previous["end"])
        current_start = dt.date.fromisoformat(current["start"])
        assert current_start == previous_end + dt.timedelta(days=1), current["fold"]
        assert _plus_months(dt.date.fromisoformat(previous["start"]), 3) == current_start


def test_the_fold_count_is_the_number_of_folds_enumerated(criteria: dict):
    construction = criteria["walk_forward_fold_construction"]
    assert construction["test_folds"]["count"] == len(construction["test_folds"]["folds"]) == 12
    assert construction["test_folds"]["boundaries_inclusive"] is True


def test_there_are_no_training_folds_because_nothing_may_be_refitted(criteria: dict, prereg: dict):
    train = criteria["walk_forward_fold_construction"]["train_folds"]
    assert train["count"] == 0 and train["set"] == []
    assert "prohibited" in train["reason"]
    assert prereg["walk_forward_fold_construction"]["train_folds"] == 0


def test_the_folds_were_derived_from_frozen_boundaries_and_read_no_validation_observation(
    criteria: dict,
):
    construction = criteria["walk_forward_fold_construction"]
    assert construction["declared_before_any_validation_observation_was_read"] is True
    derived = construction["derived_only_from"]
    assert "SE100-GOV-1005" in derived
    assert "No trading-session count" in derived
    assert "no coverage statistic" in derived
    assert "NOT recorded here" in construction["test_folds"]["session_assignment"]


def test_the_fold_ratio_predicate_passes_at_nine_of_twelve_and_fails_at_eight(criteria: dict):
    predicate = _condition(criteria, "S4-C6")["predicate"]
    assert (
        _evaluate(predicate, positive_fold_count=Decimal(9), completed_fold_count=Decimal(12))
        is True
    )
    assert (
        _evaluate(predicate, positive_fold_count=Decimal(8), completed_fold_count=Decimal(12))
        is False
    )
    assert "smallest passing count is 9" in _condition(criteria, "S4-C6")["boundary"]


def test_fewer_than_twelve_completed_folds_is_not_evaluable_and_not_a_pass(criteria: dict):
    completion = criteria["walk_forward_fold_construction"]["completed_fold_definition"]
    assert completion["expected_completed_count"] == 12
    assert "NOT_EVALUABLE" in completion["incomplete_run_is_not_a_pass"]
    assert "re-run in full" in completion["incomplete_run_is_not_a_pass"]


def test_a_fold_return_of_exactly_zero_is_not_positive(criteria: dict):
    definition = criteria["walk_forward_fold_construction"]["fold_return_definition"]
    assert definition["positive_means"].startswith("strictly greater than zero")
    assert "Exactly zero is NOT positive" in definition["positive_means"]
    assert "not twelve independent accounts" in definition["continuity"]


def test_the_fold_construction_is_sealed_and_may_not_be_changed_after_a_result(
    criteria: dict, prereg: dict
):
    immutability = criteria["walk_forward_fold_construction"]["immutability"]
    assert "may not be changed after any validation observation is read" in immutability
    assert "not a repair" in immutability
    sealed = prereg["walk_forward_fold_construction"]
    assert sealed["id"] == "SE100-CFG-4002-WF1"
    assert sealed["authored_in_this_session"] is True
    assert "S4-CONFLICT-4" in sealed["why_authored_here"]


# --------------------------------------------------------------------------------------------
# The declared runs, the single-read rule and the iteration budget
# --------------------------------------------------------------------------------------------


def test_exactly_two_runs_are_declared_and_the_count_is_a_hard_limit(protocol: dict, prereg: dict):
    declared = protocol["runs_declared"]
    assert declared["count"] == len(declared["runs"]) == 2
    assert declared["count_is_a_hard_limit"] is True
    assert prereg["runs_declared"]["count"] == 2
    assert prereg["runs_declared"]["count_is_a_hard_limit"] is True


def test_the_two_runs_are_the_base_and_stressed_variants_of_the_representative(protocol: dict):
    """The run labels are Stage 4 labels; the Gate 3 experiment id lives in ``candidate``. Asserting
    the id is in the label would be asserting a naming convention the artifact does not use."""
    runs = protocol["runs_declared"]["runs"]
    labels = sealer._run_labels(protocol)
    assert labels == [run["run_label"] for run in runs]
    assert [label.rsplit("#", 1)[1] for label in labels] == ["BASE", "STRESS"]
    for run in runs:
        assert run["candidate"] == REPRESENTATIVE
        assert "C2-MEANREV-RA1" in run["run_label"]
        assert "#VALIDATION#" in run["run_label"]
        assert run["window"].startswith("validation")
        assert run["gating"] is True
    serialised = json.dumps(runs)
    assert ELIMINATED not in serialised and INELIGIBLE not in serialised


def test_the_two_runs_between_them_gate_six_conditions_and_only_s4_c7_is_cross_run(protocol: dict):
    """S4-C7 is the reproducibility condition, so it belongs to no single run. Every other condition
    must be assigned to exactly one, or a condition could go unevaluated with nothing detecting it."""
    runs = protocol["runs_declared"]["runs"]
    base, stress = runs
    assert base["gates_conditions"] == ["S4-C1", "S4-C2", "S4-C3", "S4-C4", "S4-C6"]
    assert stress["gates_conditions"] == ["S4-C5"]
    assigned = base["gates_conditions"] + stress["gates_conditions"]
    assert len(assigned) == len(set(assigned)) == 6
    assert set(assigned) | {"S4-C7"} == set(CONDITION_IDS)


def test_the_stressed_run_never_disables_the_shutdown(protocol: dict):
    _, stress = protocol["runs_declared"]["runs"]
    assert "never disabled for a gating run" in stress["shutdown"]
    assert "multiplied by 2.0" in stress["friction"]
    assert "FINRA TAF per-order cap" in stress["friction"]
    assert "non-gating by SE100-CFG-3004" in stress["status_change_from_gate_3"]


def test_no_neighbour_runs_are_declared_and_their_absence_is_argued_not_assumed(protocol: dict):
    absence = protocol["runs_declared"]["no_neighbour_runs"]
    assert absence["declared"] is False
    assert "Gate 4 requires none" in absence["reason"]
    assert "not a gap in the evidence" in absence["reason"]


def test_the_validation_partition_is_read_exactly_once(protocol: dict, prereg: dict):
    rule = protocol["single_validation_read_rule"]
    assert "exactly once" in rule["rule"]
    assert "one session, one load" in rule["what_counts_as_one_read"].lower()
    prohibited = " ".join(rule["what_is_prohibited"])
    assert "A second session reading the validation window" in prohibited
    assert "exploratory query" in prohibited
    assert "row count" in prohibited
    assert any("Two runs over one load is one read" in line for line in prereg["binding_consequences"])


def test_the_iteration_budget_authorizes_no_exploration(protocol: dict, prereg: dict):
    budget = protocol["iteration_budget"]
    assert budget["parameterisations"] == 1
    assert budget["runs"] == 2
    assert budget["sessions_reading_validation"] == 1
    assert budget["re_runs_permitted_after_a_valid_completed_run"] == 0
    assert "no exploration is authorized" in budget["note"]
    assert prereg["runs_declared"]["sessions_reading_validation"] == 1
    assert prereg["runs_declared"]["re_runs_permitted_after_a_valid_completed_run"] == 0


def test_no_selection_happens_in_the_evaluation_stage(protocol: dict):
    assert protocol["no_selection_in_this_stage"]
    assert protocol["cumulative_experiment_count"]
    assert protocol["multiple_comparisons_disclosure"]


def test_a_partial_or_failed_run_is_recorded_rather_than_retried_into_a_result(protocol: dict):
    assert protocol["partial_or_failed_run_rule"]
    assert protocol["post_seal_defect_rule"]
    assert protocol["missing_or_invalid_data_rule"]


# --------------------------------------------------------------------------------------------
# S4-C7: the sealed digest set that makes "no change in response to a result" mechanical
# --------------------------------------------------------------------------------------------


def test_the_recheck_list_and_s4_c7_enumerate_the_same_thirteen_item_set(
    protocol: dict, criteria: dict
):
    recheck = protocol["reproducibility_requirements"]["sealed_digests_to_recheck"]
    measurement = _condition(criteria, "S4-C7")["measurement"]
    assert len(recheck) == 13
    assert "13-item" in measurement
    for item in recheck:
        covered = (
            item in measurement
            or sealer.S4_C7_COVERING_PHRASES.get(item, "\x00") in measurement
            or (item.startswith("the strategy module") and "the strategy module" in measurement)
        )
        assert covered, item


def test_the_seal_records_twelve_of_the_thirteen_and_excludes_its_own(prereg: dict):
    sealed = prereg["sealed_digests_for_s4_c7"]
    assert sealed["declared_set_size"] == 13
    assert sealed["recorded_here"] == 12 == len(sealed["entries"])
    assert sealed["own_digest_excluded"] == sealer.RECORD_REL
    assert sealer.RECORD_REL not in sealed["entries"]
    assert sealer.RECORD_SHA_REL in sealed["own_digest_location"]


def test_every_sealed_digest_still_recomputes_to_its_sealed_value(project_root: Path, prereg: dict):
    from stockedge100.audit import sha256_file

    for rel, digest in prereg["sealed_digests_for_s4_c7"]["entries"].items():
        assert sha256_file(project_root / rel) == digest, rel


def test_the_sealed_set_covers_the_strategy_module_by_path_not_by_role(prereg: dict):
    entries = prereg["sealed_digests_for_s4_c7"]["entries"]
    assert not any(rel.startswith("the strategy module") for rel in entries)
    assert prereg["sealed_representative"]["strategy_module"] in entries


def test_s4_c7_has_no_immateriality_tolerance(criteria: dict):
    boundary = _condition(criteria, "S4-C7")["boundary"]
    assert "no tolerance" in boundary
    assert "whitespace edit" in boundary


# --------------------------------------------------------------------------------------------
# Fail-closed: validation and holdout observations cannot be reached from this session.
# Every assertion below is about dates, guards, or syntax trees. None loads a dataset.
# --------------------------------------------------------------------------------------------


def test_the_development_window_guard_refuses_a_validation_dated_session(bounds: dict):
    guard = development_window()
    with pytest.raises(WindowViolation):
        guard.check(dt.date.fromisoformat(bounds["validation_start"]))
    with pytest.raises(WindowViolation):
        guard.check(dt.date.fromisoformat(bounds["validation_end"]))


def test_the_development_window_guard_refuses_a_holdout_dated_session(bounds: dict):
    guard = development_window()
    with pytest.raises(WindowViolation):
        guard.check(dt.date.fromisoformat(bounds["holdout_start"]))
    with pytest.raises(WindowViolation):
        guard.check(dt.date.fromisoformat(bounds["holdout_end"]))


def test_a_market_view_cannot_be_constructed_at_a_validation_as_of(bounds: dict):
    """No series is supplied: the refusal happens on the date, before any observation is involved."""
    with pytest.raises(WindowViolation):
        MarketView({}, dt.date.fromisoformat(bounds["validation_start"]), development_window())


def test_a_development_bounded_view_refuses_to_be_widened_to_validation(bounds: dict):
    view = MarketView({}, dt.date.fromisoformat(bounds["development_end"]), development_window())
    with pytest.raises(LookAheadError):
        view._check("SPY", dt.date.fromisoformat(bounds["validation_start"]))
    with pytest.raises(LookAheadError):
        view.as_of = dt.date.fromisoformat(bounds["validation_start"])


def test_the_window_boundaries_are_read_from_the_lock_and_the_holdout_is_still_sealed(
    project_root: Path, bounds: dict, protocol: dict
):
    lock = json.loads(
        (project_root / "governance" / "STAGE_1_HOLDOUT_LOCK.json").read_text(encoding="utf-8")
    )
    assert lock["holdout_state"] == "SEALED"
    assert bounds == lock["partition"]
    for name in (DEVELOPMENT, VALIDATION, HOLDOUT):
        guard = window_named(name)
        assert guard.start.isoformat() == bounds[f"{name}_start"]
        assert guard.end.isoformat() == bounds[f"{name}_end"]
    assert protocol["partitions"]["validation"]["state_now"] == "LOCKED"
    assert protocol["partitions"]["holdout"]["state"] == "SEALED"


def test_the_seal_records_the_window_posture_of_this_session(prereg: dict):
    assert prereg["authorized_windows_in_this_session"] == []
    assert prereg["validation_window_state"] == "LOCKED"
    assert prereg["holdout_window_state"] == "SEALED"


def test_the_restricted_data_posture_is_all_zeros_and_structurally_known(prereg: dict):
    posture = prereg["restricted_data_posture"]
    for field in (
        "validation_rows_read",
        "validation_prices_read",
        "validation_indicators_computed",
        "validation_trades_counted",
        "holdout_observations_read",
        "dataset_loads_in_this_session",
    ):
        assert posture[field] == 0, field
    assert "Structural, not asserted" in posture["how_this_is_known"]
    assert "stage_4_modules_touching_restricted_data_or_a_broker" in posture["how_this_is_known"]


def test_no_stage_4_module_can_reach_restricted_data_or_a_broker():
    """The three zeros, as an AST question. A text sweep of ``src/`` for these names returns a wall
    of false hits — prose recording Alpaca as LOCKED, the tracked-dependency list, a local variable
    called ``requests`` — so the predicate walks the parsed tree instead."""
    assert sealer._stage_4_modules_touching_restricted_data() == []


def test_the_sealing_program_is_itself_in_scope_of_that_predicate(prereg: dict):
    """The path-based predicate exempts the sealer; this one deliberately does not, so the program
    that writes the seal is proved unable to read what the seal forbids."""
    assert sealer.STAGE_MARKER in sealer.THIS_MODULE_REL.lower()
    definition = prereg["contamination_predicates"]["definitions"][
        "stage_4_modules_touching_restricted_data_or_a_broker"
    ]
    assert "this sealing program INCLUDED" in definition
    assert "AST question, not a text search" in definition
    assert sealer._restricted_access_findings(sealer.PROJECT_ROOT / sealer.THIS_MODULE_REL) == []


def test_the_url_marker_table_is_composed_so_the_predicate_does_not_flag_itself(project_root: Path):
    """A literal ``http`` + ``://`` here would be a string constant containing a URL scheme inside a
    file the predicate walks. The first dry-run of the sealer failed exactly that way."""
    assert len(sealer.URL_MARKERS) == 5
    assert all(marker.endswith("://") for marker in sealer.URL_MARKERS)
    source = (project_root / sealer.THIS_MODULE_REL).read_text(encoding="utf-8")
    constants = [
        node.value
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]
    assert not any(marker in constant for constant in constants for marker in sealer.URL_MARKERS)


# --------------------------------------------------------------------------------------------
# Contamination predicates, in both directions
# --------------------------------------------------------------------------------------------


def test_the_seal_recorded_five_zeros_and_one_verification(prereg: dict):
    predicates = prereg["contamination_predicates"]
    for name in (
        "stage_4_evaluator_or_result_modules",
        "modules_naming_a_stage_4_run_label",
        "stage_4_report_artifacts",
        "stage_4_run_records",
        "stage_4_modules_touching_restricted_data_or_a_broker",
    ):
        assert predicates[name] == 0, name
    assert predicates["gate_3_attempt_2_records_verify"] is True
    assert prereg["sealed_before_any_stage_4_evaluator_code"] is True


def test_every_predicate_carries_its_own_definition(prereg: dict):
    predicates = prereg["contamination_predicates"]
    definitions = predicates["definitions"]
    counted = [
        key
        for key in predicates
        if key not in ("definitions", "why_not_stage_3_predicates")
    ]
    assert set(definitions) == set(counted)
    for name, text in definitions.items():
        assert len(text) > 80, f"{name} definition is too thin to check against"
        assert ("Must be 0" in text) ^ ("Must be true" in text), name


def test_the_definitions_disclose_what_they_exclude(prereg: dict):
    definitions = prereg["contamination_predicates"]["definitions"]
    assert sealer.THIS_MODULE_REL in definitions["stage_4_evaluator_or_result_modules"]
    assert "EXCLUDING exactly" in definitions["stage_4_evaluator_or_result_modules"]
    assert "BEFORE this seal writes its own run record" in definitions["stage_4_run_records"]
    assert "AFTER this seal" in definitions["stage_4_report_artifacts"]
    assert "Stage 3" in prereg["contamination_predicates"]["why_not_stage_3_predicates"]


@pytest.fixture
def synthetic_tree(monkeypatch, tmp_path: Path) -> Path:
    """Point the sealer's path constants at an empty synthetic tree under ``tmp_path``."""
    src = tmp_path / "src" / "stockedge100"
    for sub in ("strategies", "reporting", "backtest"):
        (src / sub).mkdir(parents=True)
    (tmp_path / "reports" / "stage3_attempt2").mkdir(parents=True)
    (tmp_path / "runs").mkdir()
    monkeypatch.setattr(sealer, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(sealer, "SRC_DIR", src)
    monkeypatch.setattr(sealer, "STRATEGY_DIR", src / "strategies")
    monkeypatch.setattr(sealer, "REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setattr(sealer, "RUNS_DIR", tmp_path / "runs")
    return tmp_path


def test_predicates_read_empty_on_a_clean_tree(synthetic_tree: Path, protocol: dict):
    labels = sealer._run_labels(protocol)
    src = synthetic_tree / "src" / "stockedge100"
    (src / "strategies" / "attempt2_candidates.py").write_text(
        f"CANDIDATE = {REPRESENTATIVE!r}\n", encoding="utf-8"
    )
    (src / "reporting" / "stage3_attempt2_package.py").write_text("# earlier stage\n", encoding="utf-8")
    (synthetic_tree / "reports" / "stage3_attempt2" / "RESEARCH.json").write_text(
        "{}\n", encoding="utf-8"
    )
    (synthetic_tree / "runs" / "r.json").write_text(
        '{"stage": "STAGE_3_ATTEMPT_2_STRATEGY_RESEARCH"}\n', encoding="utf-8"
    )
    assert sealer._stage_4_modules() == []
    assert sealer._modules_naming_a_run_label(labels) == []
    assert sealer._stage_4_report_artifacts() == []
    assert sealer._stage_4_run_records(labels) == []
    assert sealer._stage_4_modules_touching_restricted_data() == []
    assert sealer._resolve_strategy_module(REPRESENTATIVE) == [
        "src/stockedge100/strategies/attempt2_candidates.py"
    ]


def test_predicate_1_catches_a_stage_4_evaluator_anywhere_in_src(synthetic_tree: Path):
    src = synthetic_tree / "src" / "stockedge100"
    (src / "backtest" / "stage4_evaluator.py").write_text("# an evaluator\n", encoding="utf-8")
    (src / "reporting" / "stage4_package.py").write_text("# a package builder\n", encoding="utf-8")
    assert sealer._stage_4_modules() == [
        "src/stockedge100/backtest/stage4_evaluator.py",
        "src/stockedge100/reporting/stage4_package.py",
    ]


def test_predicate_1_exempts_exactly_one_named_file(synthetic_tree: Path):
    """The exemption is the sealing program, not the directory it lives in. A Stage 4 evaluator
    dropped next to it under ``reporting/`` is still counted."""
    reporting = synthetic_tree / "src" / "stockedge100" / "reporting"
    (reporting / "stage4_preregistration.py").write_text("# the sealer\n", encoding="utf-8")
    assert sealer._stage_4_modules() == []
    (reporting / "stage4_evaluator.py").write_text("# not exempt\n", encoding="utf-8")
    assert sealer._stage_4_modules() == ["src/stockedge100/reporting/stage4_evaluator.py"]


def test_predicate_2_catches_a_run_label_bolted_into_an_existing_module(
    synthetic_tree: Path, protocol: dict
):
    labels = sealer._run_labels(protocol)
    target = synthetic_tree / "src" / "stockedge100" / "backtest" / "runner.py"
    target.write_text(f"RUN = {labels[0]!r}\n", encoding="utf-8")
    assert sealer._modules_naming_a_run_label(labels) == ["src/stockedge100/backtest/runner.py"]


def test_predicate_3_catches_a_stage_4_result_artifact(synthetic_tree: Path):
    outdir = synthetic_tree / "reports" / "stage4"
    outdir.mkdir()
    (outdir / "VALIDATION_RESULTS.json").write_text("{}\n", encoding="utf-8")
    assert sealer._stage_4_report_artifacts() == ["reports/stage4/VALIDATION_RESULTS.json"]


def test_predicate_4_catches_both_a_stage_4_token_and_a_run_label(
    synthetic_tree: Path, protocol: dict
):
    labels = sealer._run_labels(protocol)
    runs = synthetic_tree / "runs"
    (runs / "a.json").write_text('{"stage": "STAGE_4_VALIDATION_EVALUATION"}\n', encoding="utf-8")
    (runs / "b.json").write_text(f'{{"strategy_id": "{labels[1]}"}}\n', encoding="utf-8")
    assert sealer._stage_4_run_records(labels) == ["runs/a.json", "runs/b.json"]


@pytest.mark.parametrize(
    "body,expected",
    [
        ("from stockedge100.data import load_series\n", "from stockedge100.data import ..."),
        ("import stockedge100.datasets\n", "import stockedge100.datasets"),
        ("import requests\n", "import requests"),
        ("from alpaca.trading import TradingClient\n", "from alpaca.trading import ..."),
        ("prices = load_dataset(('SPY',))\n", "call load_dataset()"),
        ("import os\nKEY = os.environ['APCA_API_KEY_ID']\n", "attribute .environ"),
        ("ENDPOINT = 'https' + '://api.example.test'\n", None),
    ],
)
def test_predicate_5_catches_every_restricted_access_shape(
    synthetic_tree: Path, body: str, expected: str | None
):
    """The last case is the control: a URL assembled at runtime is not a string constant, so the
    predicate does not claim it. Overclaiming would make the count unfalsifiable."""
    target = synthetic_tree / "src" / "stockedge100" / "backtest" / "stage4_evaluator.py"
    target.write_text(body, encoding="utf-8")
    findings = sealer._restricted_access_findings(target)
    if expected is None:
        assert findings == []
        assert sealer._stage_4_modules_touching_restricted_data() == []
    else:
        assert expected in findings
        assert sealer._stage_4_modules_touching_restricted_data() == [
            f"src/stockedge100/backtest/stage4_evaluator.py: {', '.join(findings)}"
        ]


def test_predicate_5_catches_a_literal_url_constant(synthetic_tree: Path):
    target = synthetic_tree / "src" / "stockedge100" / "backtest" / "stage4_broker.py"
    target.write_text("BASE = 'https://paper-api.example.test'\n", encoding="utf-8")
    assert sealer._restricted_access_findings(target) == [
        "string constant containing a URL scheme"
    ]


def test_predicate_6_verifies_the_gate_3_attempt_2_records_that_the_selection_rests_on(
    project_root: Path,
):
    from stockedge100.reporting.stage_package import verify_sha256_record

    for rel in sealer.GATE_3_IMMUTABILITY:
        results = verify_sha256_record(project_root / rel, root=project_root)
        assert results and set(results.values()) == {"OK"}, rel


@pytest.mark.parametrize(
    "predicate",
    [
        "_stage_4_modules",
        "_modules_naming_a_run_label",
        "_stage_4_report_artifacts",
        "_stage_4_run_records",
        "_stage_4_modules_touching_restricted_data",
    ],
)
def test_any_non_empty_predicate_refuses_to_seal_and_writes_nothing(
    monkeypatch, tmp_path: Path, predicate: str
):
    monkeypatch.setattr(sealer, predicate, lambda *a, **k: ["synthetic/contamination.py"])
    monkeypatch.setattr(sealer, "RECORD_JSON", tmp_path / "must_not_appear.json")
    monkeypatch.setattr(sealer, "RECORD_SHA", tmp_path / "must_not_appear.sha256")
    monkeypatch.setattr(sealer, "RUNS_DIR", tmp_path / "runs")
    assert sealer.build() == 3
    assert list(tmp_path.iterdir()) == []


def test_a_sealed_preregistration_is_never_regenerated():
    """The record exists, so the real program must refuse. Sealing twice destroys the meaning."""
    assert sealer.RECORD_JSON.is_file() and sealer.RECORD_SHA.is_file()
    assert sealer.build() == 2


# --------------------------------------------------------------------------------------------
# The refusals after the contamination gate
# --------------------------------------------------------------------------------------------


@pytest.fixture
def past_the_contamination_gate(monkeypatch, tmp_path: Path) -> Path:
    """Let ``build()`` reach the refusals that come after the contamination gate.

    Two of the five counting predicates are legitimately non-empty once this seal has run: ``runs/``
    holds the seal's own run record, which carries ``STAGE_4`` by construction, and ``reports/stage4/``
    holds this session's design package. Both sealed definitions disclose exactly that. All five are
    neutralised here so these tests keep testing the later refusals rather than silently collapsing
    into the contamination refusal; each is exercised directly, in both directions, above.
    """
    for predicate in (
        "_stage_4_modules",
        "_modules_naming_a_run_label",
        "_stage_4_report_artifacts",
        "_stage_4_run_records",
        "_stage_4_modules_touching_restricted_data",
    ):
        monkeypatch.setattr(sealer, predicate, lambda *a, **k: [])
    monkeypatch.setattr(sealer, "RECORD_JSON", tmp_path / "must_not_appear.json")
    monkeypatch.setattr(sealer, "RECORD_SHA", tmp_path / "must_not_appear.sha256")
    monkeypatch.setattr(sealer, "RUNS_DIR", tmp_path / "runs")
    return tmp_path


def test_a_missing_preregistered_file_refuses_to_seal(monkeypatch, past_the_contamination_gate: Path):
    monkeypatch.setattr(sealer, "PREREGISTERED", sealer.PREREGISTERED + ("config/absent.json",))
    assert sealer.build() == 5
    assert list(past_the_contamination_gate.iterdir()) == []


def test_a_failing_stage_0_freeze_refuses_to_seal(monkeypatch, past_the_contamination_gate: Path):
    monkeypatch.setattr(sealer, "verify_stage0_freeze", lambda: (False, {"reason": "synthetic"}))
    assert sealer.build() == 4
    assert list(past_the_contamination_gate.iterdir()) == []


def test_a_drifted_bound_digest_refuses_to_seal(monkeypatch, past_the_contamination_gate: Path):
    """Stage 4 adopts its measurements by reference, so a drifted digest means the measurements it
    claims to adopt are not the ones on disk."""
    real = sealer.sha256_file

    def drifting(path: Path) -> str:
        return "0" * 64 if Path(path).name == "stage2_cost_model.json" else real(path)

    monkeypatch.setattr(sealer, "sha256_file", drifting)
    assert sealer.build() == 6
    assert list(past_the_contamination_gate.iterdir()) == []


def test_an_ambiguous_strategy_module_refuses_to_seal(monkeypatch, past_the_contamination_gate: Path):
    monkeypatch.setattr(sealer, "_resolve_strategy_module", lambda _: ["a.py", "b.py"])
    assert sealer.build() == 8
    assert list(past_the_contamination_gate.iterdir()) == []


def test_a_document_that_disagrees_with_the_specification_refuses_to_seal(
    monkeypatch, past_the_contamination_gate: Path
):
    """Removing the covering phrases makes two entries of the 13-item S4-C7 set unfindable in the
    condition text, which is the disagreement the check exists to catch."""
    monkeypatch.setattr(sealer, "S4_C7_COVERING_PHRASES", {})
    assert sealer.build() == 7
    assert list(past_the_contamination_gate.iterdir()) == []


# --------------------------------------------------------------------------------------------
# Authorization posture
# --------------------------------------------------------------------------------------------


def test_the_seal_authorizes_exactly_one_validation_evaluation_and_nothing_else(prereg: dict):
    assert prereg["validation_evaluation_authorized"] is True
    authorized_for = prereg["validation_evaluation_authorized_for"]
    assert authorized_for.startswith("Exactly one evaluation of " + REPRESENTATIVE)
    assert sealer.PROTOCOL_REL in authorized_for
    assert sealer.CRITERIA_REL in authorized_for
    assert authorized_for.rstrip().endswith("Nothing else.")


@pytest.mark.parametrize(
    "flag",
    [
        "validation_access_authorized_in_this_session",
        "holdout_access_authorized",
        "gate_4_evaluated",
        "gate_4_passed",
        "stage_5_authorized",
        "paper_trading_authorized",
        "shadow_live_authorized",
        "capital_or_risk_expansion_authorized",
        "live_trading_authorized",
    ],
)
def test_every_forward_authorization_is_false(prereg: dict, flag: str):
    assert prereg[flag] is False, flag


def test_gate_3_is_the_highest_gate_passed(prereg: dict):
    assert prereg["gate_3_passed"] is True
    assert prereg["gate"]["gate_4_evaluated"] is False
    assert prereg["gate"]["gate_4_passed"] is False


def test_all_three_configs_record_live_trading_unauthorized(
    protocol: dict, criteria: dict, selection: dict
):
    for config in (protocol, criteria, selection):
        assert config["live_trading_authorized"] is False


def test_the_seven_non_authorizations_name_what_this_session_may_not_do(protocol: dict):
    explicit = protocol["explicit_non_authorizations"]
    assert len(explicit) == 7
    for item in explicit:
        assert item.startswith("This protocol does not authorize"), item
    joined = " ".join(explicit)
    for phrase in (
        "reading the validation window in the session that wrote it",
        "implementing the Stage 4 evaluator",
        "empty or placeholder Stage 4 evaluator or result files",
        "development backtest, re-run, or re-measurement",
        "Treasury-bill series",
        "Alpaca or broker interaction, credential read, or network access",
        "second Gate 4 attempt",
    ):
        assert phrase in joined, phrase


def test_the_forward_prohibitions_survive_any_validation_result(protocol: dict, prereg: dict):
    """The forward flags belong to ``stage_5_remains_prohibited_conditions``, not to the
    session-scoped non-authorizations above. Each must be unconditional on the Gate 4 outcome."""
    forward = protocol["stage_5_remains_prohibited_conditions"]
    assert len(forward) == 9
    joined = " ".join(forward)
    for flag in (
        "paper_trading_authorized",
        "shadow_live_authorized",
        "live_trading_authorized",
        "capital_or_risk_expansion_authorized",
    ):
        assert f"{flag} remains false regardless of any validation result" in joined, flag
    assert "holdout window remains SEALED regardless of the Gate 4 verdict" in joined
    assert "Gate 4 may not emit that token" in joined
    assert "not trade-ready and may not be described as trade-ready" in joined
    assert "No order-submitting code exists in this repository" in joined
    assert prereg["binding_consequences"][-1] == "live_trading_authorized remains false."


def test_the_binding_consequences_state_what_a_fail_does_not_authorize(prereg: dict):
    consequences = " ".join(prereg["binding_consequences"])
    assert "may not change for any reason" in consequences
    assert "not a reason to retune" in consequences
    assert "no neighbour runs" in consequences
    assert "There is no search at Gate 4" in consequences


def test_the_upstream_records_verified_at_seal_time_are_all_recorded(prereg: dict):
    verified = prereg["upstream_records_verified"]
    expected = {rel: count for _, rel, count in sealer.FREEZE_RECORDS + sealer.ROOT_RECORDS}
    assert verified == expected
    assert prereg["stage_0_freeze_verified"] is True
    assert list(prereg["gate_3_attempt_2_immutability_records"]) == list(sealer.GATE_3_IMMUTABILITY)


# --------------------------------------------------------------------------------------------
# The document and the machine-readable specification say the same thing
# --------------------------------------------------------------------------------------------


def test_the_document_names_the_representative_the_tokens_and_both_runs(
    document: str, criteria: dict, protocol: dict
):
    assert REPRESENTATIVE in document
    for role in ("pass_token", "fail_token"):
        assert criteria["verdict_token_derivation"][role] in document
    for label in sealer._run_labels(protocol):
        assert label in document


def test_the_document_reproduces_the_sealed_sentences_verbatim(
    document: str, criteria: dict, protocol: dict, selection: dict
):
    normalised = sealer._normalised_prose(document)
    for text in (
        protocol["research_question"],
        criteria["frozen_gate_text_verbatim"],
        selection["selection_rule"]["statement"],
        protocol["single_validation_read_rule"]["rule"],
    ):
        assert sealer._normalised_prose(text) in normalised


def test_the_document_states_the_fold_count_and_the_ineligible_candidate(
    document: str, criteria: dict
):
    assert str(criteria["walk_forward_fold_construction"]["test_folds"]["count"]) in document
    assert INELIGIBLE in document
    assert "contamination" in document.lower()


def test_the_document_is_ascii_only(document: str):
    """Console stdout is cp1252 and the frozen constitution's own em dash is not repaired. Every
    artifact this project authors stays inside ASCII so nothing depends on the console encoding."""
    offenders = sorted({character for character in document if ord(character) > 127})
    assert offenders == []
