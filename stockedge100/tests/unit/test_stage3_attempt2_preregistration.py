"""Stage 3 Attempt 2 — the pre-registration seal.

Attempt 2 is an *adaptive* second attempt: Attempt 1's results were known when these candidates were
designed. That makes the ordering claim weaker than Attempt 1's and more important to pin down. The
claim is not "nobody had seen any results" — it is the narrower one that no Attempt 2 implementation
or Attempt 2 result existed when the specification was sealed, and that Attempt 1 was not modified to
make Attempt 2 look better.

Attempt 1 could prove its ordering with two counts of zero over ``strategies/`` and ``reports/``.
Both directories are now legitimately non-empty and may not be emptied, so Attempt 2 proves it with
four narrower predicates plus an immutability check. Those predicates are the load-bearing part of
this file, and they are tested in **both** directions: a predicate that always returns nothing would
also have recorded four zeros.

Digests are pinned here independently of ``governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.sha256``, so
rewriting an artifact together with its checksum record still fails this file.

Nothing here runs a backtest, loads a market observation, reads validation or holdout data, or writes
outside ``tmp_path``.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

import pytest

from stockedge100.audit import sha256_file
from stockedge100.backtest.errors import WindowViolation
from stockedge100.backtest.window import development_window
from stockedge100.reporting import stage3_attempt2_preregistration as sealer

PREREG_JSON = "STAGE_3_ATTEMPT_2_PREREGISTRATION.json"
PREREG_MD = "STAGE_3_ATTEMPT_2_PREREGISTRATION.md"
PREREG_RECORD = "STAGE_3_ATTEMPT_2_PREREGISTRATION.sha256"

PROTOCOL_REL = "config/stage3_attempt2_strategy_protocol.json"
BINDING_REL = "config/stage3_attempt2_gate_criteria_binding.json"
DOCUMENT_REL = "governance/STAGE_3_ATTEMPT_2_PREREGISTRATION.md"

# Pinned independently of the checksum record.
EXPECTED_DIGESTS = {
    PROTOCOL_REL: "77f1451c20e37640bd2843ff86d69eb54cbc0ebb592a696972fbdea6e05b5433",
    BINDING_REL: "a482f499173c0d7e2b0ca158b2edf7cb2e25a516ac2eb361e1441b2964006c8e",
    DOCUMENT_REL: "d9e34b3ce61f5998fe91c0b7b551a29a778fdb410330e60d6919c0a94ec447c6",
}

# Attempt 2 binds Gate 3 by digest rather than copying it. If the criteria file were edited, the
# binding would point at bytes that no longer exist and every Attempt 2 claim of "unchanged" would be
# false. Pinned here as well as in the binding, for the same reason as above.
GATE_CRITERIA_REL = "config/stage3_gate_criteria.json"
GATE_CRITERIA_DIGEST = "310f1c978380f4a1d6b98b8c368975b1515476b032c123afb06f1dd597e3e18d"

CANDIDATE_IDS = [
    "SE100-S3A2-C1-PULLBACK-RA1",
    "SE100-S3A2-C2-MEANREV-RA1",
    "SE100-S3A2-C3-DEFENSIVE-RA1",
]

GATE_CONDITIONS = ["S3-C1", "S3-C2", "S3-C3", "S3-C4", "S3-C5", "S3-C6", "S3-C7"]

# Every field a later implementation session must not be free to choose. The prompt's requirement is
# that no discretionary choice can be made on an observed result; this list is that requirement
# turned into an assertion.
REQUIRED_CANDIDATE_FIELDS = [
    "experiment_id",
    "family",
    "family_authorised_by",
    "hypothesis",
    "economic_rationale",
    "distinction_from_attempt_1",
    "required_inputs",
    "universe",
    "exclusions",
    "eligibility_rules",
    "warmup_sessions",
    "signal_timing",
    "primary_parameters",
    "entry_rule",
    "exit_rule",
    "maximum_holding_period",
    "position_sizing_rule",
    "maximum_exposure",
    "cash_allocation_rule",
    "stop_or_shutdown_rule",
    "reentry_rule_after_a_stop",
    "conflict_rule",
    "permitted_parameter_grid",
    "robustness_neighbours",
    "max_variants",
    "primary_metric",
    "secondary_metrics",
    "gate_3_conditions_applied",
    "rejection_conditions",
    "not_evaluable_conditions",
    "retrospective_change_prohibited",
]


@pytest.fixture(scope="module")
def prereg(governance_dir: Path) -> dict:
    return json.loads((governance_dir / PREREG_JSON).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def protocol(project_root: Path) -> dict:
    return json.loads((project_root / PROTOCOL_REL).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def binding(project_root: Path) -> dict:
    return json.loads((project_root / BINDING_REL).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def document(project_root: Path) -> str:
    return (project_root / DOCUMENT_REL).read_text(encoding="utf-8")


# --------------------------------------------------------------------------------------------
# Clean controls. If anything below these fails, the failure is the injected defect, not the harness.
# --------------------------------------------------------------------------------------------


def test_control_the_three_sealed_artifacts_are_present(project_root: Path, governance_dir: Path):
    for rel in (PROTOCOL_REL, BINDING_REL):
        assert (project_root / rel).is_file(), f"missing {rel}"
    for name in (PREREG_JSON, PREREG_MD, PREREG_RECORD):
        assert (governance_dir / name).is_file(), f"missing governance/{name}"


def test_control_the_seal_parses_and_declares_itself_sealed(prereg: dict):
    assert prereg["document_id"] == "SE100-GOV-0007"
    assert prereg["record_type"] == "PRE_REGISTRATION"
    assert prereg["status"] == "SEALED"
    assert prereg["attempt"] == 2
    assert prereg["attempt_id"] == "SE100-S3-A2"


def test_control_a_synthetic_all_satisfied_candidate_is_admissible(binding: dict):
    """The complement of the rejection tests below.

    Attempt 1 rejected six of six. If the admissibility rule as sealed could not admit anything, the
    rejections would be uninformative. This exercises the rule as the binding *writes* it, so an edit
    that dropped ``NOT_APPLICABLE_BY_CONDITION_TEXT`` from the satisfied set would fail here.
    """
    satisfied = _satisfied_values(binding)
    all_met = {cid: dict.fromkeys(GATE_CONDITIONS, "MET") for cid in CANDIDATE_IDS}
    assert _admissible(all_met, satisfied) == CANDIDATE_IDS

    with_inapplicable = {CANDIDATE_IDS[0]: dict(all_met[CANDIDATE_IDS[0]], **{"S3-C6": "NOT_APPLICABLE_BY_CONDITION_TEXT"})}
    assert _admissible(with_inapplicable, satisfied) == [CANDIDATE_IDS[0]], (
        "NOT_APPLICABLE_BY_CONDITION_TEXT is satisfied without being met"
    )


# --------------------------------------------------------------------------------------------
# The seal: digests, checksum record, self-reference
# --------------------------------------------------------------------------------------------


def test_sealed_digests_match_the_files_on_disk(project_root: Path, prereg: dict):
    for rel, entry in prereg["preregistered_files"].items():
        assert sha256_file(project_root / rel) == entry["sha256"], f"{rel} changed after sealing"


def test_sealed_digests_match_the_values_pinned_here(prereg: dict):
    sealed = {rel: entry["sha256"] for rel, entry in prereg["preregistered_files"].items()}
    assert sealed == EXPECTED_DIGESTS


def test_checksum_record_is_project_root_relative_and_verifies(project_root: Path, governance_dir: Path):
    """Project-root-relative paths, so it verifies from ``stockedge100/``.

    ``STAGE_0_FREEZE.sha256`` uses bare filenames and verifies from ``governance/``. Mixing the two
    conventions up reports MISSING for every entry, which looks like an integrity failure and is an
    operator error. This test also pins the convention so the distinction stays deliberate.
    """
    entries = _parse_record(governance_dir / PREREG_RECORD)
    assert entries, "checksum record is empty"
    for name, digest in entries.items():
        assert "/" in name, f"{name!r} is not project-root-relative"
        target = project_root / name
        assert target.is_file(), f"record names a missing file: {name}"
        assert sha256_file(target) == digest, f"digest mismatch for {name}"


def test_checksum_record_covers_the_seal_json_but_not_itself(governance_dir: Path):
    """Nothing hashes itself; the record covers the JSON written immediately before it."""
    entries = _parse_record(governance_dir / PREREG_RECORD)
    assert f"governance/{PREREG_JSON}" in entries
    assert f"governance/{PREREG_RECORD}" not in entries
    assert set(entries) == set(EXPECTED_DIGESTS) | {f"governance/{PREREG_JSON}"}


def test_seal_carries_no_digest_of_the_tree_it_belongs_to(governance_dir: Path, prereg: dict):
    """``repo_state_id`` covers ``governance/*.json``, so a value written here is stale on write.

    Tested as a search for the *value*, not the field name: the seal is expected to name
    ``repo_state_id`` in the prose that says where the value actually lives.
    """
    text = (governance_dir / PREREG_JSON).read_text(encoding="utf-8")
    found = set(re.findall(r"\b[0-9a-f]{64}\b", text))
    permitted = set(EXPECTED_DIGESTS.values()) | {GATE_CRITERIA_DIGEST}
    permitted |= {
        v
        for entry in prereg["stage_0_freeze_verification"].values()
        if isinstance(entry, dict)
        for v in entry.values()
        if isinstance(v, str) and len(v) == 64
    }
    assert found <= permitted, f"unexplained digest(s) in the seal: {sorted(found - permitted)}"
    assert '"repo_state_id"' not in text, "the seal must not carry a repo_state_id field"
    assert "runs/" in prereg["repo_state_id_location"], "prose must point at the run record"


def test_document_carries_no_digest_at_all(document: str):
    assert not re.search(r"\b[0-9a-f]{64}\b", document), (
        "the Markdown pre-registration must point at the JSON rather than restating digests"
    )


def test_declared_utc_is_a_real_utc_timestamp(prereg: dict):
    declared = dt.datetime.strptime(prereg["declared_utc"], "%Y-%m-%dT%H:%M:%SZ")
    assert declared.year >= 2026
    assert prereg["run_id"] == "SE100-R-" + declared.strftime("%Y%m%dT%H%M%SZ")


def test_run_record_exists_and_agrees_with_the_seal(project_root: Path, prereg: dict):
    run = json.loads(
        (project_root / "runs" / f"{prereg['run_id']}.json").read_text(encoding="utf-8")
    )
    assert run["stage"] == "STAGE_3_ATTEMPT_2_PRE_REGISTRATION"
    assert run["timestamp_utc"] == prereg["declared_utc"]
    assert run["holdout_state"] == "SEALED"
    assert run["strategy_id"] is None, "no candidate had been run when the seal was written"
    assert re.fullmatch(r"[0-9a-f]{64}", run["repo_state_id"])


def test_serialisation_is_deterministic_and_declared(prereg: dict, protocol: dict, binding: dict):
    """Same bytes on a re-read, and the convention is declared rather than implicit."""
    for artifact in (protocol, binding):
        assert artifact["serialisation"], "serialisation convention must be declared"
    for rel in EXPECTED_DIGESTS:
        assert EXPECTED_DIGESTS[rel] == prereg["preregistered_files"][rel]["sha256"]


# --------------------------------------------------------------------------------------------
# Contamination predicates, both directions
# --------------------------------------------------------------------------------------------


def test_seal_recorded_all_four_predicates_at_zero(prereg: dict):
    predicates = prereg["contamination_predicates"]
    assert predicates["attempt_2_strategy_modules"] == 0
    assert predicates["modules_naming_an_attempt_2_candidate"] == 0
    assert predicates["attempt_2_report_artifacts"] == 0
    assert predicates["attempt_2_run_records"] == 0
    assert predicates["attempt_1_records_verify"] is True
    assert prereg["sealed_before_any_attempt_2_strategy_code"] is True


def test_every_predicate_carries_its_own_definition(prereg: dict):
    """Attempt 1 recorded two bare integers. A count whose definition is absent is not evidence."""
    predicates = prereg["contamination_predicates"]
    definitions = predicates["definitions"]
    counted = [k for k in predicates if k not in ("definitions", "why_not_attempt_1_predicates")]
    assert set(definitions) == set(counted)
    for name, text in definitions.items():
        assert len(text) > 80, f"{name} definition is too thin to check against"


@pytest.fixture
def synthetic_tree(monkeypatch, tmp_path: Path) -> Path:
    """Point the sealer's path constants at an empty synthetic tree under ``tmp_path``."""
    src = tmp_path / "src" / "stockedge100"
    for sub in ("strategies", "reporting"):
        (src / sub).mkdir(parents=True)
    (tmp_path / "reports" / "stage3").mkdir(parents=True)
    (tmp_path / "runs").mkdir()
    monkeypatch.setattr(sealer, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(sealer, "SRC_DIR", src)
    monkeypatch.setattr(sealer, "STRATEGY_DIR", src / "strategies")
    monkeypatch.setattr(sealer, "REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setattr(sealer, "RUNS_DIR", tmp_path / "runs")
    return tmp_path


def test_predicates_read_empty_on_a_clean_tree(synthetic_tree: Path):
    src = synthetic_tree / "src" / "stockedge100"
    (src / "strategies" / "base.py").write_text("class Strategy:\n    pass\n", encoding="utf-8")
    (src / "strategies" / "families.py").write_text("F1 = 'SE100-S3-F1-TREND'\n", encoding="utf-8")
    (synthetic_tree / "reports" / "stage3" / "RESEARCH.json").write_text("{}\n", encoding="utf-8")
    (synthetic_tree / "runs" / "r.json").write_text(
        '{"stage": "STAGE_3_STRATEGY_RESEARCH"}\n', encoding="utf-8"
    )
    assert sealer._attempt_2_strategy_modules() == []
    assert sealer._modules_naming_a_candidate(CANDIDATE_IDS) == []
    assert sealer._attempt_2_report_artifacts() == []
    assert sealer._attempt_2_run_records(CANDIDATE_IDS) == []


def test_predicate_1_catches_an_attempt_2_module_by_path(synthetic_tree: Path):
    target = synthetic_tree / "src" / "stockedge100" / "strategies" / "attempt2_pullback.py"
    target.write_text("# an Attempt 2 implementation\n", encoding="utf-8")
    assert sealer._attempt_2_strategy_modules() == [
        "src/stockedge100/strategies/attempt2_pullback.py"
    ]


def test_predicate_1_exempts_reporting_and_says_so(synthetic_tree: Path, prereg: dict):
    """The sealing program is itself ``reporting/stage3_attempt2_preregistration.py``.

    Without the exemption the predicate counts itself and can never read zero. The exemption is a
    real narrowing of the check, so the sealed definition has to disclose it.
    """
    reporting = synthetic_tree / "src" / "stockedge100" / "reporting"
    (reporting / "stage3_attempt2_preregistration.py").write_text("# sealer\n", encoding="utf-8")
    (reporting / "attempt2_helper.py").write_text("# also exempt\n", encoding="utf-8")
    assert sealer._attempt_2_strategy_modules() == []
    definition = prereg["contamination_predicates"]["definitions"]["attempt_2_strategy_modules"]
    assert "reporting/" in definition and "EXCLUDING" in definition


def test_predicate_2_catches_a_candidate_id_inside_an_existing_module(synthetic_tree: Path):
    """The path predicate would miss an Attempt 2 rule bolted into an Attempt 1 module."""
    target = synthetic_tree / "src" / "stockedge100" / "strategies" / "runner.py"
    target.write_text(f"CANDIDATE = {CANDIDATE_IDS[1]!r}\n", encoding="utf-8")
    assert sealer._modules_naming_a_candidate(CANDIDATE_IDS) == [
        "src/stockedge100/strategies/runner.py"
    ]


def test_predicate_3_catches_an_attempt_2_result_artifact(synthetic_tree: Path):
    outdir = synthetic_tree / "reports" / "stage3_attempt2"
    outdir.mkdir()
    (outdir / "ADMISSIBILITY.json").write_text("{}\n", encoding="utf-8")
    assert sealer._attempt_2_report_artifacts() == ["reports/stage3_attempt2/ADMISSIBILITY.json"]


def test_predicate_4_catches_both_an_attempt_2_token_and_a_candidate_id(synthetic_tree: Path):
    runs = synthetic_tree / "runs"
    (runs / "a.json").write_text('{"stage": "STAGE_3_ATTEMPT_2_STRATEGY_RESEARCH"}\n', encoding="utf-8")
    (runs / "b.json").write_text(f'{{"strategy_id": "{CANDIDATE_IDS[0]}"}}\n', encoding="utf-8")
    assert sealer._attempt_2_run_records(CANDIDATE_IDS) == ["runs/a.json", "runs/b.json"]


def test_predicate_4_definition_discloses_that_it_excludes_this_seals_own_record(prereg: dict):
    """The seal's own run record contains ``ATTEMPT_2``, so a later re-verification counts 1."""
    definition = prereg["contamination_predicates"]["definitions"]["attempt_2_run_records"]
    assert "BEFORE this seal writes its own run record" in definition


@pytest.mark.parametrize(
    "predicate",
    [
        "_attempt_2_strategy_modules",
        "_modules_naming_a_candidate",
        "_attempt_2_report_artifacts",
        "_attempt_2_run_records",
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
    assert not (tmp_path / "must_not_appear.json").exists()
    assert not (tmp_path / "must_not_appear.sha256").exists()


def test_a_sealed_preregistration_is_never_regenerated():
    """The record exists, so the real program must refuse. Sealing twice destroys the meaning."""
    assert sealer.RECORD_JSON.is_file() and sealer.RECORD_SHA.is_file()
    assert sealer.build() == 2


# --------------------------------------------------------------------------------------------
# Attempt 1 immutability
# --------------------------------------------------------------------------------------------


def test_attempt_1_preregistration_and_decision_records_still_verify(project_root: Path):
    """Attempt 2 may not improve its own standing by editing the attempt it follows."""
    for rel in (
        "governance/STAGE_3_PREREGISTRATION.sha256",
        "reports/stage3/STAGE_3_STRATEGY_RESEARCH.sha256",
    ):
        entries = _parse_record(project_root / rel)
        assert entries, f"{rel} is empty"
        for name, digest in entries.items():
            assert sha256_file(project_root / name) == digest, f"{name} changed under {rel}"


def test_attempt_1_verdict_is_carried_forward_as_a_failure_not_reopened(protocol: dict):
    prior = json.dumps(protocol["known_prior_evidence"])
    assert "STAGE_3_STRATEGY_REJECTED_IN_DEVELOPMENT" in prior
    assert protocol["attempt"] == 2


def test_attempt_2_does_not_claim_to_supersede_attempt_1(prereg: dict):
    assert prereg["supersedes"] is None
    relationship = prereg["relationship_to_attempt_1"]
    assert relationship.startswith(
        "None of Attempt 1 is modified, superseded, re-run, or repaired."
    )
    assert "SE100-GOV-0006" in relationship, "the attempt being followed is named, not implied"


# --------------------------------------------------------------------------------------------
# Gate 3, unchanged
# --------------------------------------------------------------------------------------------


def test_gate_criteria_are_bound_by_digest_and_the_digest_still_matches(
    project_root: Path, binding: dict
):
    bound = binding["bound_artifact"]
    assert bound["path"] == GATE_CRITERIA_REL
    assert bound["sha256"] == GATE_CRITERIA_DIGEST
    assert sha256_file(project_root / GATE_CRITERIA_REL) == GATE_CRITERIA_DIGEST
    assert bound["adoption"] == "ADOPTED_UNCHANGED"


def test_drawdown_ceiling_is_unchanged_at_15_percent(binding: dict, prereg: dict, project_root: Path):
    frozen = json.loads((project_root / GATE_CRITERIA_REL).read_text(encoding="utf-8"))
    ceiling = binding["drawdown_ceiling_is_unchanged"]["value"]
    assert ceiling == "0.15"
    assert prereg["gate"]["max_drawdown_ceiling"] == "0.15"
    assert prereg["gate"]["max_drawdown_ceiling_changed"] is False
    frozen_text = json.dumps(frozen)
    assert "0.15" in frozen_text, "the ceiling must still be 0.15 in the artifact being bound"


def test_all_seven_conditions_are_adopted_unchanged(binding: dict, prereg: dict):
    """Every condition starts from "unchanged"; two carry a re-derivation annotation.

    S3-C6 and S3-C7 name a candidate set by enumeration, and Attempt 2's candidate set is different,
    so the enumeration had to be re-derived. Those two are annotated rather than silently rewritten,
    and the annotation must be the only thing distinguishing them.
    """
    adopted = {entry["id"]: entry["adopted"] for entry in binding["conditions_adopted"]}
    assert sorted(adopted) == GATE_CONDITIONS
    for condition, text in adopted.items():
        assert text.startswith("unchanged"), f"{condition} is not adopted unchanged: {text!r}"
    annotated = sorted(c for c, text in adopted.items() if text != "unchanged")
    rederived = sorted(entry["condition"] for entry in binding["rederivations"])
    assert annotated == rederived == ["S3-C6", "S3-C7"], (
        "an annotated condition must have a matching rederivation entry, and vice versa"
    )
    assert prereg["gate"]["conditions_evaluated"] == 7
    assert prereg["gate"]["criteria_changed_for_attempt_2"] is False


def test_only_the_two_candidate_set_enumerations_are_rederived(binding: dict, prereg: dict):
    ids = [entry["id"] for entry in binding["rederivations"]]
    assert ids == ["A2-REDERIVE-1", "A2-REDERIVE-2"]
    assert prereg["gate"]["rederivations"] == ids
    for entry in binding["rederivations"]:
        # The re-derivation quotes the sealed text it re-derives from, and states separately what it
        # left alone. Without the quotation there is nothing to check the re-derivation against.
        assert entry["sealed_text_quoted"], f"{entry['id']} does not quote the text it re-derives"
        assert entry["why_rederivation_is_necessary"]
        assert entry["unchanged"], f"{entry['id']} does not state what it left unchanged"
    assert binding["nothing_else_changed"], "the binding must state what it did not change"


def test_conjunction_is_within_a_candidate_and_disjunction_is_across(binding: dict, prereg: dict):
    rule = binding["admissible_candidate_exists"]
    assert rule["within_candidate"].startswith("CONJUNCTIVE")
    assert rule["across_candidates"].startswith("DISJUNCTIVE")
    assert rule["how_many_admissible_candidates_are_required"]["answer"] == "Exactly one."
    assert prereg["gate"]["within_candidate"] == "CONJUNCTIVE"
    assert prereg["gate"]["across_candidates"] == "DISJUNCTIVE"
    assert prereg["gate"]["admissible_candidates_required"] == 1


def test_satisfied_is_wider_than_met_and_never_includes_a_missing_result(binding: dict):
    rule = binding["admissible_candidate_exists"]
    assert rule["satisfied_definition"] == "verdict in (MET, NOT_APPLICABLE_BY_CONDITION_TEXT)"
    for never_a_pass in ("NOT_MET", "NOT_EVALUABLE", "NOT_RUN", "UNKNOWN"):
        assert never_a_pass in rule["not_satisfied_values"]


@pytest.mark.parametrize(
    "verdicts, expected_admissible",
    [
        (dict.fromkeys(GATE_CONDITIONS, "MET"), True),
        ({**dict.fromkeys(GATE_CONDITIONS, "MET"), "S3-C6": "NOT_APPLICABLE_BY_CONDITION_TEXT"}, True),
        ({**dict.fromkeys(GATE_CONDITIONS, "MET"), "S3-C2": "NOT_MET"}, False),
        ({**dict.fromkeys(GATE_CONDITIONS, "MET"), "S3-C2": "NOT_EVALUABLE"}, False),
        ({**dict.fromkeys(GATE_CONDITIONS, "MET"), "S3-C4": "NOT_RUN"}, False),
        ({**dict.fromkeys(GATE_CONDITIONS, "MET"), "S3-C5": "UNKNOWN"}, False),
        ({k: v for k, v in dict.fromkeys(GATE_CONDITIONS, "MET").items() if k != "S3-C3"}, False),
    ],
)
def test_admissibility_rule_as_sealed_decides_both_ways(
    binding: dict, verdicts: dict, expected_admissible: bool
):
    """One ``NOT_MET`` sinks a candidate; a missing condition is not a pass either."""
    satisfied = _satisfied_values(binding)
    got = _admissible({"X": verdicts}, satisfied) == ["X"]
    assert got is expected_admissible


def test_a_per_condition_rollup_row_is_not_the_gate(binding: dict):
    """Attempt 1 produced a false ``FAIL`` for S3-C6 by aggregating on ``MET`` across candidates."""
    satisfied = _satisfied_values(binding)
    # Every condition is satisfied by *someone*, yet no single candidate satisfies all of them.
    verdicts = {
        "A": {**dict.fromkeys(GATE_CONDITIONS, "MET"), "S3-C2": "NOT_MET"},
        "B": {**dict.fromkeys(GATE_CONDITIONS, "MET"), "S3-C4": "NOT_MET"},
    }
    for condition in GATE_CONDITIONS:
        assert any(v[condition] in satisfied for v in verdicts.values()), (
            f"{condition} is satisfied by at least one candidate"
        )
    assert _admissible(verdicts, satisfied) == [], (
        "a table of green rollup rows can still mean zero admissible candidates"
    )


def test_neighbours_are_diagnostic_and_never_promoted(binding: dict, prereg: dict, protocol: dict):
    status = binding["neighbour_status"]
    assert status["are_neighbours_diagnostic_or_independently_selectable"]["answer"] == (
        "Diagnostic only."
    )
    assert status["can_a_neighbour_become_the_representative_of_its_candidate"]["answer"].startswith(
        "No."
    )
    assert status["is_a_neighbour_separately_admissible_at_gate_3"]["answer"].startswith("No.")
    assert prereg["robustness_neighbours_per_candidate"] == 4
    for experiment in protocol["experiments"]:
        assert len(experiment["robustness_neighbours"]) == 4


def test_shutdown_breach_liquidates_and_never_rearms(binding: dict):
    """S3-C2 and the section 5.1 research shutdown are the same 15% on the same series."""
    shutdown = json.dumps(binding["shutdown_behaviour"])
    assert "LIQUIDATE_AT_NEXT_OPEN_AND_BLOCK_ENTRIES" in shutdown
    assert "re-arm" in shutdown or "rearm" in shutdown or "never" in shutdown.lower()


def test_no_result_may_be_rerun_after_a_valid_completed_evaluation(binding: dict):
    policy = binding["rerun_policy"]
    assert policy["may_a_result_be_rerun_after_a_valid_completed_evaluation"]["answer"] == "No."
    assert policy["prohibited"]
    assert policy["no_specification_change_ever_follows_a_result"]


# --------------------------------------------------------------------------------------------
# Candidate specification completeness
# --------------------------------------------------------------------------------------------


def test_candidate_ids_are_unique_and_match_the_seal(protocol: dict, prereg: dict):
    ids = [experiment["experiment_id"] for experiment in protocol["experiments"]]
    assert ids == CANDIDATE_IDS
    assert len(set(ids)) == len(ids)
    assert prereg["candidate_ids"] == CANDIDATE_IDS
    assert prereg["candidates_declared"] == 3


def test_every_candidate_is_fully_specified(protocol: dict):
    """No field a later session could otherwise choose after seeing a number."""
    for experiment in protocol["experiments"]:
        missing = [f for f in REQUIRED_CANDIDATE_FIELDS if not experiment.get(f)]
        assert not missing, f"{experiment['experiment_id']} under-specified: {missing}"


def test_every_candidate_declares_its_distinction_from_attempt_1(protocol: dict):
    for experiment in protocol["experiments"]:
        distinction = experiment["distinction_from_attempt_1"]
        assert len(json.dumps(distinction)) > 200, (
            f"{experiment['experiment_id']} must say more than 'new code' to be a new hypothesis"
        )


def test_counts_are_capped_before_implementation(protocol: dict, prereg: dict):
    budget = protocol["iteration_budget"]
    assert budget["candidates"] == 3
    assert budget["max_variants_per_candidate"] == 5
    assert budget["total_declared_gating_variants"] == 15
    assert budget["total_declared_runs"] == 18
    assert budget["revisions_permitted"] == 0
    for experiment in protocol["experiments"]:
        assert experiment["max_variants"] == 5
        assert 1 + len(experiment["robustness_neighbours"]) == experiment["max_variants"]
    assert prereg["declared_gating_variants"] == 15
    assert prereg["declared_runs"] == 18
    assert prereg["revisions_permitted"] == 0


def test_the_permitted_grid_is_a_boundary_not_a_search_space(protocol: dict):
    semantics = json.dumps(protocol["permitted_parameter_grid_semantics"])
    assert "not" in semantics.lower()
    for experiment in protocol["experiments"]:
        grid = experiment["permitted_parameter_grid"]
        for name, value in experiment["primary_parameters"].items():
            if name in grid:
                assert value in grid[name], (
                    f"{experiment['experiment_id']} primary {name}={value!r} is outside its own grid"
                )


def test_excluded_families_are_recorded_with_a_prospective_reason(protocol: dict, prereg: dict):
    excluded = protocol["families_excluded"]
    assert [entry["family"] for entry in excluded["excluded"]] == [
        "trend/momentum",
        "breakout",
        "ETF rotation",
    ]
    for entry in excluded["excluded"]:
        assert entry.get("reason") or entry.get("prospective_reason"), (
            f"{entry['family']} was excluded without a recorded reason"
        )
    assert prereg["families_excluded"] == [e["family"] for e in excluded["excluded"]]
    assert len(prereg["families_retained"]) == 3


def test_no_candidate_combines_rejected_families(protocol: dict):
    """Constitution section 8 requires independent testing before any combination."""
    for experiment in protocol["experiments"]:
        assert isinstance(experiment["family"], str), "one family per candidate"
    families = [experiment["family"] for experiment in protocol["experiments"]]
    assert len(set(families)) == len(families), "no family is tried twice under two names"


def test_the_one_new_indicator_declares_its_arithmetic(protocol: dict):
    """A 19-versus-20 denominator choice made after a result is a tuning knob."""
    vol20 = protocol["indicator_definitions"]["added"]["VOL20"]
    text = json.dumps(vol20)
    assert "19" in text, "the variance denominator must be fixed before implementation"
    assert "252" in text


# --------------------------------------------------------------------------------------------
# Adaptive-research disclosure
# --------------------------------------------------------------------------------------------


def test_the_adaptation_is_disclosed_rather_than_hidden_behind_new_ids(protocol: dict, prereg: dict):
    """Every disclosure the adaptation requires, checked as a distinct statement.

    Asserted as substrings of the sealed items rather than a single blob search, so removing any one
    of them fails on its own line.
    """
    assert prereg["is_adaptive_second_attempt"] is True
    disclosure = " ".join(protocol["adaptive_research_disclosure"]["items"])
    for required in (
        "adaptive second attempt",  # the adaptation itself
        "All six Attempt 1 candidates breached the 15% maximum-drawdown ceiling",
        "no longer pristine",  # development data
        "Researcher degrees of freedom are higher",
        "false-discovery risk",
        "cumulative count across both attempts",
        "independent confirmation",  # new code is not confirmation
        "remains LOCKED",
        "remains SEALED",
        "not evidence of a trading edge",
        "not concealed behind a new strategy identifier",
    ):
        assert required in disclosure, f"the adaptation disclosure omits {required!r}"


def test_cumulative_experiment_count_spans_both_attempts(protocol: dict, prereg: dict):
    cumulative = protocol["cumulative_experiment_count"]
    assert cumulative["cumulative_candidates"] == 9
    assert cumulative["cumulative_gating_variants"] == 45
    assert cumulative["cumulative_total_runs"] == 48
    assert prereg["cumulative_experiment_count"]["cumulative_candidates"] == 9
    assert prereg["cumulative_experiment_count"]["cumulative_gating_variants"] == 45
    binding_number = cumulative["binding_number_for_interpretation"]
    assert "9" in binding_number and "45" in binding_number


def test_development_data_is_declared_no_longer_pristine(protocol: dict):
    disclosure = json.dumps(protocol["adaptive_research_disclosure"]).lower()
    assert "pristine" in disclosure or "no longer" in disclosure


# --------------------------------------------------------------------------------------------
# Partitions: development only, validation locked, holdout sealed
# --------------------------------------------------------------------------------------------


def test_only_the_development_window_is_authorized(protocol: dict, binding: dict, prereg: dict):
    assert protocol["partitions"]["permitted"] == [
        "development window only, bounds read from governance/STAGE_1_HOLDOUT_LOCK.json"
    ]
    assert binding["windows"]["authorized"] == ["development"]
    assert binding["windows"]["validation"] == "LOCKED"
    assert binding["windows"]["holdout"] == "SEALED"
    assert prereg["authorized_windows"] == ["development"]
    assert prereg["validation_window_state"] == "LOCKED"
    assert prereg["holdout_window_state"] == "SEALED"


def test_prohibited_partitions_are_named_including_the_split_fixture_symbol(protocol: dict):
    prohibited = json.dumps(protocol["partitions"]["prohibited"])
    assert "validation" in prohibited and "holdout" in prohibited
    assert "AAPL" in prohibited, "the Stage 1 split fixture is not a universe member"
    assert "AAPL" in protocol["excluded_symbols"]


def test_the_window_guard_is_structural_and_still_refuses_a_later_session(prereg: dict):
    """A validation-dated session must raise. Dates only — no observation is read."""
    window = development_window()
    beyond = dt.date.fromisoformat(window.to_json()["end"]) + dt.timedelta(days=1)
    assert not window.contains(beyond)
    with pytest.raises(WindowViolation):
        window.check(beyond, what="session")
    assert prereg["holdout_window_state"] == "SEALED"


def test_the_holdout_lock_is_untouched_and_still_sealed(governance_dir: Path):
    lock = json.loads((governance_dir / "STAGE_1_HOLDOUT_LOCK.json").read_text(encoding="utf-8"))
    assert lock["status"] == "LOCKED"
    assert lock["holdout_state"] == "SEALED"


# --------------------------------------------------------------------------------------------
# Authorization: nothing is unlocked by sealing a design
# --------------------------------------------------------------------------------------------


def test_sealing_a_design_authorizes_no_trading_and_no_later_stage(prereg: dict, protocol: dict):
    for flag in (
        "stage_4_authorized",
        "paper_trading_authorized",
        "shadow_live_authorized",
        "live_trading_authorized",
    ):
        assert prereg[flag] is False, f"{flag} must remain false"
    assert protocol["live_trading_authorized"] is False


def test_the_only_thing_authorized_is_implementing_exactly_this_design(prereg: dict):
    authorized = prereg["strategy_research_authorized_for"]
    assert "three candidates sealed here" in authorized
    assert "Nothing else." in authorized


def test_stage_4_remains_prohibited_with_its_conditions_recorded(protocol: dict, binding: dict):
    assert protocol["stage_4_remains_prohibited_conditions"]
    assert binding["stage_4_authorization"]
    assert "false" in json.dumps(binding["stage_4_authorization"]).lower() or (
        "not authorized" in json.dumps(binding["stage_4_authorization"]).lower()
    )


def test_explicit_non_authorizations_are_carried_in_both_formats(protocol: dict, document: str):
    non_auth = protocol["explicit_non_authorizations"]
    assert len(non_auth) >= 8
    assert "live_trading_authorized" in document
    assert "false" in document


def test_the_seal_records_the_abandonment_and_defect_rules(protocol: dict):
    """What happens on a bad outcome has to be fixed before the outcome is known."""
    for key in (
        "attempt_level_abandonment_rule",
        "missing_or_invalid_data_rule",
        "post_seal_defect_rule",
        "partial_or_failed_run_rule",
        "no_retuning_rule",
        "reproducibility_requirements",
    ):
        assert protocol[key], f"{key} must be declared before any result exists"


def test_reproducibility_declares_no_seed_because_nothing_is_stochastic(protocol: dict):
    requirements = json.dumps(protocol["reproducibility_requirements"])
    assert "seed" in requirements.lower()


# --------------------------------------------------------------------------------------------
# Markdown and JSON must agree
# --------------------------------------------------------------------------------------------


def test_document_names_every_candidate_and_the_attempt(document: str, protocol: dict):
    for candidate_id in CANDIDATE_IDS:
        assert candidate_id in document, f"{candidate_id} is not named in the document"
    assert protocol["attempt_id"] in document


def test_document_and_protocol_state_the_same_research_question(document: str, protocol: dict):
    normalised = sealer._normalised_prose(document)
    assert sealer._normalised_prose(protocol["research_question"]) in normalised


def test_document_names_the_risk_architecture_and_all_eight_mechanisms(document: str, protocol: dict):
    architecture = protocol["risk_architecture"]
    assert architecture["id"] in document
    for key in architecture:
        if re.fullmatch(r"RA1-\d+", key):
            assert key in document, f"{key} is specified in the protocol but absent from the document"


def test_document_reproduces_the_attempt_1_trade_counts_it_relies_on(document: str, protocol: dict):
    """The only Attempt 1 numbers carried into Attempt 2's reasoning are three trade counts."""
    for entry in protocol["families_excluded"]["excluded"]:
        count = str(entry.get("attempt_1_closed_trades", ""))
        if count:
            assert count in document, f"{entry['family']}'s trade count is not in the document"


# --------------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------------


def _parse_record(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        match = re.fullmatch(r"([0-9a-f]{64})\s[\s*](.+)", line)
        assert match, f"unparseable record line in {path.name}: {line!r}"
        entries[match.group(2).strip()] = match.group(1)
    return entries


def _satisfied_values(binding: dict) -> frozenset[str]:
    """Read the satisfied set out of the sealed definition instead of restating it here."""
    definition = binding["admissible_candidate_exists"]["satisfied_definition"]
    match = re.fullmatch(r"verdict in \(([A-Z_, ]+)\)", definition)
    assert match, f"unrecognised satisfied_definition: {definition!r}"
    return frozenset(token.strip() for token in match.group(1).split(","))


def _admissible(verdicts: dict[str, dict[str, str]], satisfied: frozenset[str]) -> list[str]:
    """Apply the sealed rule: conjunctive within a candidate, disjunctive across candidates."""
    return [
        candidate
        for candidate, per_condition in verdicts.items()
        if all(per_condition.get(condition) in satisfied for condition in GATE_CONDITIONS)
    ]
