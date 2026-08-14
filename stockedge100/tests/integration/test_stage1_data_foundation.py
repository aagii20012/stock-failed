"""Stage 1 — the evidence chain, re-verified from the artifacts on disk.

Gate 1 asks whether the data foundation is fit for research. These tests read the artifacts the
stage actually produced and check that they still hang together: every digest recomputes, every
manifest points at the file it claims, the universe re-derives from the sealed rules, and the locked
partition is the one section 6.1 arithmetic produces from the data that exists.

They are integration tests because they touch ``data/``. They still write nothing: the one test that
runs the universe builder redirects all of its outputs into ``tmp_path``.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

import pandas as pd
import pytest

from stockedge100.audit import sha256_file, sha256_text_canonical_json
from stockedge100.data.calendar import sessions_between
from stockedge100.data.config import load_stage1_config
from stockedge100.data.normalize import NORMALIZED_MANIFEST_PATH
from stockedge100.data.partition import compute_partition
from stockedge100.data.validate import VALIDATION_REPORT_PATH
from stockedge100.universe import build as universe_build

RAW_MANIFEST_REL = "data/manifests/STAGE_1_RAW_MANIFEST.json"
FREEZE_RECORD = "STAGE_1_FREEZE.sha256"

FIXTURE_SYMBOL = "AAPL"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def config():
    return load_stage1_config()


@pytest.fixture(scope="module")
def raw_manifest(project_root: Path) -> dict:
    return load(project_root / RAW_MANIFEST_REL)


@pytest.fixture(scope="module")
def normalized_manifest() -> dict:
    return load(NORMALIZED_MANIFEST_PATH)


@pytest.fixture(scope="module")
def validation_report() -> dict:
    return load(VALIDATION_REPORT_PATH)


@pytest.fixture(scope="module")
def universe(governance_dir: Path) -> dict:
    return load(governance_dir / "STAGE_1_UNIVERSE.json")


@pytest.fixture(scope="module")
def holdout_lock(governance_dir: Path) -> dict:
    return load(governance_dir / "STAGE_1_HOLDOUT_LOCK.json")


@pytest.fixture(scope="module")
def frames(project_root: Path, normalized_manifest: dict) -> dict[str, pd.DataFrame]:
    return {
        symbol: pd.read_csv(project_root / entry["path"], dtype={"session": str})
        for symbol, entry in normalized_manifest["symbols"].items()
        if entry.get("status") == "NORMALIZED"
    }


def utc(text: str) -> dt.datetime:
    return dt.datetime.fromisoformat(text.replace("Z", "+00:00"))


# --------------------------------------------------------------------------------------------
# Ordering: rules first, then data
# --------------------------------------------------------------------------------------------


def test_rules_were_sealed_before_the_first_request_was_sent(governance_dir: Path, raw_manifest: dict):
    prereg = load(governance_dir / "STAGE_1_PREREGISTRATION.json")
    declared = utc(prereg["declared_utc"])
    started = utc(raw_manifest["acquisition_started_utc"])
    finished = utc(raw_manifest["acquisition_finished_utc"])
    assert declared < started < finished
    assert raw_manifest["preregistration"]["config_sha256"] == prereg["preregistered_files"][
        "config/stage1_data_source.json"
    ]["sha256"]


def test_acquisition_used_the_sealed_request_parameters(config, raw_manifest: dict):
    sealed = config.data_source["acquisition_protocol"]["request_parameters"]
    recorded = raw_manifest["request_parameters"]
    for key, value in sealed.items():
        assert recorded[key] == value, f"request parameter {key} departed from the sealed protocol"
    assert recorded["interval"] == config.data_source["acquisition_protocol"]["interval"]


# --------------------------------------------------------------------------------------------
# Raw layer
# --------------------------------------------------------------------------------------------


def test_raw_manifest_is_complete_and_every_payload_hashes_to_its_recorded_digest(
    project_root: Path, config, raw_manifest: dict
):
    symbols = raw_manifest["symbols"]
    assert set(symbols) == set(config.candidates) | set(config.reference_symbols)
    for symbol, entry in symbols.items():
        assert entry["status"] == "WRITTEN", f"{symbol} was not written"
        path = project_root / entry["path"]
        assert path.is_file(), f"raw payload missing for {symbol}"
        assert sha256_file(path) == entry["sha256"], f"raw payload for {symbol} changed after acquisition"
        assert entry["rows"] > 0
        assert entry["source_timezone"] == "America/New_York"


def test_acquisition_failure_fraction_is_below_the_sealed_blocking_threshold(config, raw_manifest: dict):
    fallback = config.data_source["provider_decision"]["fallback_policy"]
    assert raw_manifest["blocking_threshold"] == fallback["candidate_failure_fraction_that_blocks_the_stage"]
    assert raw_manifest["acquisition_failure_fraction"] <= raw_manifest["blocking_threshold"]
    assert raw_manifest["stage_blocked_by_acquisition"] is False
    assert raw_manifest["provider_revisions_quarantined"] == []


def test_raw_manifest_records_the_licence_and_what_raw_actually_means(raw_manifest: dict):
    """The client hides the HTTP payload; the manifest says so instead of implying byte fidelity."""
    assert "non-commercial" in raw_manifest["license"]
    assert "never committed" in raw_manifest["license"]
    assert "does not expose the underlying HTTP payload" in raw_manifest["raw_definition"]


# --------------------------------------------------------------------------------------------
# Normalized layer
# --------------------------------------------------------------------------------------------


def test_normalized_manifest_chains_to_the_raw_manifest_it_was_built_from(
    project_root: Path, normalized_manifest: dict
):
    source = normalized_manifest["source_manifest"]
    assert source["path"] == RAW_MANIFEST_REL
    assert sha256_file(project_root / source["path"]) == source["sha256"]


def test_every_normalized_file_hashes_to_its_recorded_digest(project_root: Path, normalized_manifest: dict):
    for symbol, entry in normalized_manifest["symbols"].items():
        assert entry["status"] == "NORMALIZED", f"{symbol} was not normalized"
        path = project_root / entry["path"]
        assert sha256_file(path) == entry["sha256"], f"normalized file for {symbol} changed"
        assert entry["raw_sha256"], "normalized entry does not name the raw payload it came from"


def test_normalized_schema_matches_the_sealed_specification(config, normalized_manifest: dict, frames):
    spec = config.data_source["normalization_spec"]
    schema = normalized_manifest["schema"]
    assert schema["columns"] == spec["columns"]
    for frame in frames.values():
        assert list(frame.columns) == spec["columns"]


def test_storage_format_deviation_is_recorded_rather_than_left_implicit(normalized_manifest: dict):
    """pyarrow is absent in this environment, so CSV was used; that is a deviation, and it is stated."""
    schema = normalized_manifest["schema"]
    assert schema["storage_format"] == "csv"
    assert "pyarrow is not installed" in schema["storage_format_note"]


def test_session_key_is_a_local_calendar_date_on_every_row(normalized_manifest: dict):
    """A bar landing at 01:00 or 23:00 local is the signature of a timezone bug."""
    for symbol, entry in normalized_manifest["symbols"].items():
        observations = entry["observations"]
        assert observations["non_midnight_rows"] == 0, f"{symbol} has non-midnight bar instants"
        assert observations["local_midnight_rows"] == observations["rows_in"]
        assert observations["rows_out"] == observations["rows_in"], f"{symbol} lost or gained rows"


def test_normalization_dropped_no_rows_relative_to_the_raw_payload(raw_manifest: dict, normalized_manifest: dict):
    for symbol, entry in normalized_manifest["symbols"].items():
        assert entry["rows"] == raw_manifest["symbols"][symbol]["rows"]


def test_adjustment_semantics_were_measured_from_the_fixture_not_assumed(normalized_manifest: dict, config):
    semantics = normalized_manifest["adjustment_semantics"]
    assert semantics["determination"] == "MEASURED"
    assert semantics["ohlc_split_adjusted"] is True
    assert semantics["adj_close_split_and_dividend_adjusted"] is True

    declared = {
        (entry["symbol"], action["session"])
        for entry in config.universe_spec["reference_symbols"]["symbols"]
        for action in entry.get("expected_actions", [])
        if action.get("type") == "split"
    }
    probed = {(probe["symbol"], probe["session"]) for probe in semantics["probes"]}
    assert declared <= probed, "a declared reference split was never probed"

    for probe in semantics["probes"]:
        # The measurement: an ordinary daily step across a 7:1 or 4:1 split proves the vendor had
        # already back-adjusted the whole history. A step near 1/ratio would prove the opposite.
        assert abs(probe["unadjusted_close_step"] - 1.0) < 0.25
        assert abs(probe["unadjusted_close_step"] - probe["step_if_series_were_as_traded"]) > 0.5


def test_unavailability_of_as_traded_prices_is_recorded_as_a_limitation(normalized_manifest: dict):
    note = normalized_manifest["adjustment_semantics"]["constitution_6_note"]
    assert "not obtainable from this provider" in note
    assert "limitation" in note


def test_every_session_key_in_every_file_is_a_real_xnys_trading_day(frames):
    """Re-run independently of the battery, against the same externally maintained calendar."""
    for symbol, frame in frames.items():
        sessions = [dt.date.fromisoformat(s) for s in frame["session"]]
        calendar = set(sessions_between(min(sessions), max(sessions)))
        phantom = [s.isoformat() for s in sessions if s not in calendar]
        assert not phantom, f"{symbol} carries non-trading days: {phantom[:5]}"
        assert sessions == sorted(set(sessions)), f"{symbol} sessions are not strictly increasing"


# --------------------------------------------------------------------------------------------
# Validation battery
# --------------------------------------------------------------------------------------------


def test_validation_report_ran_the_sealed_battery_and_nothing_else(config, validation_report: dict):
    source = validation_report["battery_source"]
    assert source["sha256"] == config.config_hash
    assert source["declared_before_data_seen"] is True
    sealed_ids = {check["id"] for check in config.data_source["validation_battery"]["checks"]}
    assert set(validation_report["check_totals"]) == sealed_ids
    assert source["check_count"] == len(sealed_ids)


def test_every_research_symbol_passed_every_check(validation_report: dict, universe: dict):
    assert validation_report["research_universe_battery_passed"] is True
    assert validation_report["research_universe_failures"] == []
    assert validation_report["unclassified_failures"] == []
    for symbol in universe["members"]:
        report = validation_report["per_symbol"][symbol]
        assert report["failed_checks"] == [], f"{symbol} has failing checks"


def test_the_one_recorded_failure_is_the_fixture_and_is_classified_not_amended_away(
    raw_manifest: dict, validation_report: dict, config
):
    """The sealed check was left exactly as written; the gap is in the pre-registration."""
    assert validation_report["symbols_with_failures"] == [FIXTURE_SYMBOL]
    gaps = validation_report["preregistration_scope_gaps"]
    assert len(gaps) == 1
    gap = gaps[0]
    assert (gap["symbol"], gap["check_id"]) == (FIXTURE_SYMBOL, "TERMINAL_FACTOR_IS_ONE")
    assert gap["classification"] == "PREREGISTRATION_SCOPE_GAP"
    assert gap["sealed_check_amended"] is False
    assert gap["in_research_universe"] is False

    # The premise the classification rests on was recorded before the battery ever ran.
    assert FIXTURE_SYMBOL not in config.candidates
    assert raw_manifest["symbols"][FIXTURE_SYMBOL]["requested_window"] != "max"


def test_integrity_checks_covered_the_full_series_and_value_thresholds_did_not(validation_report: dict):
    scope = validation_report["scope_rules"]
    assert scope["integrity_checks_cover_full_series_including_holdout"] is True
    assert scope["value_threshold_checks_restricted_to_development_window"] == ["PRICE_NOT_PENNY"]


def test_calendar_used_for_validation_is_independent_of_the_price_provider(validation_report: dict):
    calendar = validation_report["calendar"]
    assert calendar["source"] == "exchange_calendars"
    assert calendar["name"] == "XNYS"
    assert calendar["independent_of_price_provider"] is True


def test_quarantine_records_referenced_by_the_report_exist(project_root: Path, validation_report: dict):
    for rel in validation_report["quarantine_records"]:
        assert (project_root / rel).is_file(), f"report references a missing quarantine record: {rel}"


# --------------------------------------------------------------------------------------------
# Realized universe
# --------------------------------------------------------------------------------------------


def test_universe_is_the_mechanical_result_of_the_sealed_rules(config, universe: dict):
    assert universe["status"] == "FROZEN"
    assert universe["research_universe_class"] == "ETF_ONLY"
    assert set(universe["members"]) <= set(config.candidates)
    assert set(universe["members"]) | set(universe["rejected"]) | set(universe["not_acquired"]) == set(
        config.candidates
    )
    assert universe["member_count"] == len(universe["members"])
    assert FIXTURE_SYMBOL not in universe["members"]
    for symbol in universe["members"]:
        assert universe["assessments"][symbol]["eligible"] is True
        assert universe["assessments"][symbol]["failed_rules"] == []


def test_universe_version_recomputes_from_its_declared_inputs(config, universe: dict, holdout_lock: dict):
    partition = holdout_lock["partition"]
    identity = sha256_text_canonical_json(
        {
            "members": universe["members"],
            "spec_sha256": config.digests["config/stage1_universe_spec.json"],
            "source_sha256": config.config_hash,
            "development_window": [partition["development_start"], partition["development_end"]],
        }
    )
    assert identity == universe["universe_identity_sha256"]
    assert universe["universe_version"] == f"SE100-U1-{identity[:16]}"


def test_no_eligibility_measurement_read_past_the_development_window(universe: dict, holdout_lock: dict):
    """The hard rule of the stage, checked against the numbers that were actually recorded."""
    partition = holdout_lock["partition"]
    for symbol, assessment in universe["assessments"].items():
        measured = assessment["measurements"]
        assert measured["window"] == [partition["development_start"], partition["development_end"]]
        assert measured["development_last_session"] <= partition["development_end"], symbol
        assert measured["development_first_session"] >= partition["development_start"], symbol
        assert measured["development_last_session"] < partition["validation_start"], symbol


def test_structural_rules_are_labelled_asserted_not_verified(universe: dict):
    """Six of the rules cannot be checked against price data at all, and the artifact says so."""
    asserted = set(universe["structural_rules_not_verifiable_from_price_data"])
    assert asserted == {
        "US_LISTED",
        "UNLEVERAGED",
        "NON_INVERSE",
        "NOT_K1_PARTNERSHIP",
        "NOT_COMMODITY_TRUST",
        "RULES_BASED_INDEX",
    }
    for assessment in universe["assessments"].values():
        for rule in asserted:
            entry = assessment["rules"][rule]
            assert entry["status"] == "ASSERTED_AT_CANDIDATE_CONSTRUCTION"
            assert entry["verifiable_from_price_data"] is False


def test_survivorship_position_is_two_explicit_verdicts_not_a_claim_of_control(universe: dict):
    bias = universe["survivorship_bias"]
    assert bias["stock_universe_verdict"] == "SURVIVORSHIP_BIAS_UNCONTROLLED"
    assert "PROHIBITED" in bias["stock_research_authorization"]
    assert bias["etf_universe_verdict"] == "RESIDUAL_FUND_CLOSURE_BIAS_DISCLOSED_AND_UNQUANTIFIED"
    assert bias["quantified"] is False


def test_broker_eligibility_remains_unverified_in_the_frozen_universe(universe: dict):
    broker = universe["broker_eligibility"]
    assert broker["alpaca_tradable"] == "UNVERIFIED"
    assert broker["alpaca_fractionable"] == "UNVERIFIED"
    assert "conditional" in broker["binding_consequence"]


# --------------------------------------------------------------------------------------------
# Holdout lock
# --------------------------------------------------------------------------------------------


def test_locked_partition_is_what_section_6_1_produces_from_the_data_that_exists(
    config, frames, holdout_lock: dict
):
    candidates = [s for s in config.candidates if s in frames]
    cutoff = max(dt.date.fromisoformat(frames[s]["session"].iloc[-1]) for s in candidates)
    earliest = min(dt.date.fromisoformat(frames[s]["session"].iloc[0]) for s in candidates)
    assert compute_partition(cutoff, earliest).to_json() == holdout_lock["partition"]


def test_holdout_is_sealed_and_locked_before_any_strategy_result(holdout_lock: dict):
    assert holdout_lock["status"] == "LOCKED"
    assert holdout_lock["holdout_state"] == "SEALED"
    assert holdout_lock["locked_before_any_strategy_result"] is True
    assert holdout_lock["constitution_ref"] == "SE100-GOV-0001 section 6.1"
    rules = " ".join(holdout_lock["binding_rules"]).lower()
    assert "read exactly once" in rules
    assert "may not be recomputed" in rules


def test_cutoff_came_from_the_data_not_the_wall_clock(frames, holdout_lock: dict):
    latest = max(frame["session"].iloc[-1] for frame in frames.values())
    assert holdout_lock["inputs"]["usable_cutoff_session"] == latest
    assert "not the wall clock" in holdout_lock["inputs"]["cutoff_derived_from"]


def test_lock_and_universe_agree_on_the_universe_they_describe(universe: dict, holdout_lock: dict):
    assert holdout_lock["inputs"]["universe_version"] == universe["universe_version"]
    assert holdout_lock["inputs"]["universe_identity_sha256"] == universe["universe_identity_sha256"]
    assert universe["measurement_window_restriction"]["development_window"] == [
        holdout_lock["partition"]["development_start"],
        holdout_lock["partition"]["development_end"],
    ]


# --------------------------------------------------------------------------------------------
# Freeze record and reproducibility
# --------------------------------------------------------------------------------------------


def test_stage_1_freeze_record_uses_bare_filenames_and_verifies(governance_dir: Path):
    text = (governance_dir / FREEZE_RECORD).read_text(encoding="utf-8")
    entries: dict[str, str] = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        match = re.fullmatch(r"([0-9a-f]{64})\s[\s*](.+)", line)
        assert match, f"unparseable freeze line: {line!r}"
        entries[match.group(2).strip()] = match.group(1)

    assert set(entries) == {"STAGE_1_UNIVERSE.json", "STAGE_1_HOLDOUT_LOCK.json"}
    for name, digest in entries.items():
        assert "/" not in name, "the record is verified from governance/, so paths must be bare"
        assert sha256_file(governance_dir / name) == digest, f"{name} changed after freezing"


def test_freeze_record_does_not_hash_itself(governance_dir: Path):
    text = (governance_dir / FREEZE_RECORD).read_text(encoding="utf-8")
    assert FREEZE_RECORD not in text


def test_rebuilding_the_universe_from_the_same_evidence_reproduces_it_byte_for_byte(
    monkeypatch: pytest.MonkeyPatch, governance_dir: Path, tmp_path: Path, universe: dict, holdout_lock: dict
):
    """The builder is mechanical: same sealed rules plus same data must give the same universe.

    Every output is redirected into ``tmp_path`` so the frozen artifacts are never touched.
    """
    out = tmp_path / "governance"
    out.mkdir()
    (out / "STAGE_1_HOLDOUT_LOCK.json").write_text(
        (governance_dir / "STAGE_1_HOLDOUT_LOCK.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    monkeypatch.setattr(universe_build, "GOVERNANCE", out)
    monkeypatch.setattr(universe_build, "UNIVERSE_PATH", out / "STAGE_1_UNIVERSE.json")
    monkeypatch.setattr(universe_build, "HOLDOUT_LOCK_PATH", out / "STAGE_1_HOLDOUT_LOCK.json")
    monkeypatch.setattr(universe_build, "FREEZE_RECORD_PATH", out / "STAGE_1_FREEZE.sha256")

    assert universe_build.build() == 0

    rebuilt = load(out / "STAGE_1_UNIVERSE.json")
    assert rebuilt["members"] == universe["members"]
    assert rebuilt["universe_version"] == universe["universe_version"]
    assert {k: v for k, v in rebuilt.items() if k != "frozen_utc"} == {
        k: v for k, v in universe.items() if k != "frozen_utc"
    }

    relocked = load(out / "STAGE_1_HOLDOUT_LOCK.json")
    assert relocked["partition"] == holdout_lock["partition"]
    assert relocked["locked_utc"] == holdout_lock["locked_utc"], "an existing lock keeps its original timestamp"
