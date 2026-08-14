"""Stage 1 — the pre-registration seal.

Everything Stage 1 claims rests on one thing: the rules were fixed *before* the data was visible.
These tests check that claim from three independent directions — the digests recorded in the seal,
the digests pinned here, and the loader that refuses to run when they disagree.

The digests below are duplicated on purpose, exactly as the Stage 0 suite duplicates the
constitution's. If a configuration file and its checksum record were rewritten together, the
seal-versus-disk comparison would still pass; this file would not.

Nothing here writes to disk.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

import pytest

from stockedge100.audit import sha256_file
from stockedge100.data.config import load_stage1_config

PREREG_JSON = "STAGE_1_PREREGISTRATION.json"
PREREG_MD = "STAGE_1_PREREGISTRATION.md"
PREREG_RECORD = "STAGE_1_PREREGISTRATION.sha256"

DATA_SOURCE_REL = "config/stage1_data_source.json"
UNIVERSE_SPEC_REL = "config/stage1_universe_spec.json"

# Pinned independently of governance/STAGE_1_PREREGISTRATION.sha256.
EXPECTED_DIGESTS = {
    DATA_SOURCE_REL: "7c6273ca501e3aaceafd006b0902ce4f329f83a67c4a9e5190155e8edf83064f",
    UNIVERSE_SPEC_REL: "0583ef00fb5907feaedab561b13b4056c7e07e7c9ce1aae03d8ae197245f4057",
    "governance/STAGE_1_PREREGISTRATION.md": (
        "53cea32ff202a4763378a5ecedc360c7e2fa1ccf1ce969d329c2e36b1cb5caee"
    ),
}

# Pinned in tests/unit/test_stage0_governance.py as well; repeated here because the Stage 1 seal
# records its own copy, and a Stage 1 artifact must not be able to disagree with Stage 0 silently.
STAGE_0_DIGESTS = {
    "STAGE_0_CONSTITUTION.md": "b6f20176b6538722e45ae34e6f8b55a818a6e50057a23e9ddd097e0ce73ce1e5",
    "STAGE_0_CONSTITUTION.json": "af45fda6b37bed50768d5f3d01d4a91175da93e708c9daf1b630e35a981e2ff5",
}

EXPECTED_CHECKS = {
    "SESSION_IN_CALENDAR",
    "NO_DUPLICATE_SESSIONS",
    "SESSIONS_STRICTLY_INCREASING",
    "NO_FUTURE_SESSIONS",
    "OHLC_CONSISTENT",
    "VOLUME_VALID",
    "ADJ_CLOSE_POSITIVE",
    "TERMINAL_FACTOR_IS_ONE",
    "FACTOR_NON_DECREASING",
    "SPLIT_RECONCILES",
    "DIVIDEND_RECONCILES",
    "CORPORATE_ACTION_FIXTURE",
    "MISSING_SESSION_FRACTION",
    "MISSING_SESSION_RUN",
    "EXTREME_MOVE_EXPLAINED",
    "PRICE_NOT_PENNY",
}


@pytest.fixture(scope="module")
def prereg(governance_dir: Path) -> dict:
    return json.loads((governance_dir / PREREG_JSON).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def config():
    return load_stage1_config()


# --------------------------------------------------------------------------------------------
# The seal itself
# --------------------------------------------------------------------------------------------


def test_preregistration_artifacts_exist(governance_dir: Path):
    for name in (PREREG_JSON, PREREG_MD, PREREG_RECORD):
        assert (governance_dir / name).is_file(), f"missing governance/{name}"


def test_sealed_digests_match_the_files_on_disk(project_root: Path, prereg: dict):
    for rel, entry in prereg["preregistered_files"].items():
        assert sha256_file(project_root / rel) == entry["sha256"], f"{rel} changed after sealing"


def test_sealed_digests_match_the_values_pinned_here(prereg: dict):
    sealed = {rel: entry["sha256"] for rel, entry in prereg["preregistered_files"].items()}
    assert sealed == EXPECTED_DIGESTS


def test_checksum_record_is_project_root_relative_and_verifies(project_root: Path, governance_dir: Path):
    """The record uses project-root-relative paths, so it verifies from ``stockedge100/``."""
    text = (governance_dir / PREREG_RECORD).read_text(encoding="utf-8")
    entries: dict[str, str] = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        match = re.fullmatch(r"([0-9a-f]{64})\s[\s*](.+)", line)
        assert match, f"unparseable record line: {line!r}"
        entries[match.group(2).strip()] = match.group(1)

    assert entries, "checksum record is empty"
    for name, digest in entries.items():
        assert "/" in name, f"{name!r} is not project-root-relative"
        target = project_root / name
        assert target.is_file(), f"record names a missing file: {name}"
        assert sha256_file(target) == digest, f"digest mismatch for {name}"


def test_seal_records_that_no_data_existed_when_it_was_written(prereg: dict):
    """The whole point of the seal: rules first, data second."""
    assert prereg["status"] == "SEALED"
    assert prereg["sealed_before_any_data_acquired"] is True
    assert prereg["raw_data_files_present_at_seal_time"] == 0


def test_seal_verified_the_stage_0_freeze_before_declaring_anything(prereg: dict):
    assert prereg["stage_0_freeze_verified"] is True
    for name, digest in STAGE_0_DIGESTS.items():
        recorded = prereg["stage_0_freeze_verification"][name]
        assert recorded["recorded"] == digest
        assert recorded["computed"] == digest


def test_seal_does_not_contain_a_digest_of_the_tree_it_belongs_to(prereg: dict):
    """``repo_state_id`` covers ``governance/*.json``; a value written here would be stale on write."""
    assert "repo_state_id" not in prereg
    assert "runs/" in prereg["repo_state_id_location"]


def test_seal_carries_the_binding_prohibitions(prereg: dict):
    assert prereg["live_trading_authorized"] is False
    text = " ".join(prereg["binding_consequences"]).lower()
    assert "holdout" in text and "eligibility" in text
    assert "mechanically" in text


def test_declared_utc_is_a_real_utc_timestamp(prereg: dict):
    declared = dt.datetime.fromisoformat(prereg["declared_utc"].replace("Z", "+00:00"))
    assert declared.tzinfo is not None
    assert declared.utcoffset() == dt.timedelta(0)
    assert prereg["run_id"].startswith("SE100-R-")


# --------------------------------------------------------------------------------------------
# The loader every Stage 1 module goes through
# --------------------------------------------------------------------------------------------


def test_loader_recomputes_every_sealed_digest(config):
    assert config.digests == EXPECTED_DIGESTS
    assert config.config_hash == EXPECTED_DIGESTS[DATA_SOURCE_REL]


def test_battery_is_declared_in_the_sealed_file_not_in_the_code(config):
    battery = config.data_source["validation_battery"]
    assert battery["declared_before_data_seen"] is True
    ids = [check["id"] for check in battery["checks"]]
    assert len(ids) == len(set(ids)) == 16
    assert set(ids) == EXPECTED_CHECKS
    assert all(check["severity"] in {"FAIL", "WARN"} for check in battery["checks"])
    assert set(config.tolerances) == {"price_relative", "factor_relative", "dividend_relative"}
    assert all(value > 0 for value in config.tolerances.values())


def test_adjustment_semantics_were_declared_as_measured_not_assumed(config):
    semantics = config.data_source["normalization_spec"]["adjustment_semantics"]
    assert semantics["determination"] == "MEASURED_NOT_ASSUMED"


def test_universe_spec_narrows_the_research_universe_and_prohibits_stocks(config):
    scope = config.universe_spec["scope_decision"]
    assert scope["research_universe_class"] == "ETF_ONLY"
    assert scope["stock_universe_survivorship_verdict"] == "SURVIVORSHIP_BIAS_UNCONTROLLED"
    assert "PROHIBITED" in scope["stock_research_authorization"]


def test_residual_etf_bias_is_disclosed_rather_than_claimed_controlled(config):
    bias = config.universe_spec["etf_universe_bias_assessment"]
    assert bias["verdict"] == "RESIDUAL_FUND_CLOSURE_BIAS_DISCLOSED_AND_UNQUANTIFIED"
    assert bias["honest_statement"].strip()


def test_candidate_list_is_a_fixed_deduplicated_set(config):
    candidates = config.candidates
    assert len(candidates) == len(set(candidates)) == config.universe_spec["candidate_count"]
    assert config.reference_symbols == ["AAPL"]
    assert "AAPL" not in candidates, "the data-quality fixture must not be a research symbol"


def test_eligibility_measurements_are_restricted_to_the_development_window_by_declaration(config):
    rules = config.universe_spec["eligibility_rules"]
    restriction = rules["measurement_window_restriction"].lower()
    assert "validation" in restriction and "holdout" in restriction
    assert "may read" in restriction and restriction.startswith("no ")
    measured = {rule["id"] for rule in rules["measured_on_development_window_only"]}
    assert {"MIN_DEVELOPMENT_SESSIONS", "MEDIAN_DOLLAR_VOLUME", "MIN_CLOSE", "DATA_QUALITY"} <= measured


def test_broker_eligibility_is_unverified_at_stage_1(config):
    """Stage 0 forbids credential access at Stage 1, so tradability stays an open placeholder."""
    broker = config.universe_spec["eligibility_rules"]["broker_eligibility"]
    values = json.dumps(broker)
    assert "UNVERIFIED" in values
    assert "PASS" not in values
