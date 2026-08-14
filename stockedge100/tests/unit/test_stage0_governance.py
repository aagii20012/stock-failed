"""Stage 0 — re-runnable verification of the frozen constitution.

These tests are the executable form of ``governance/STAGE_0_VERIFICATION_REPORT.md``. They must
keep passing for the entire life of Generation 1: any later stage that finds them failing has
found evidence that a frozen artifact was altered, and must stop.

Nothing here writes to disk.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from stockedge100.audit import sha256_file

FREEZE_FILE = "STAGE_0_FREEZE.sha256"
MD_FILE = "STAGE_0_CONSTITUTION.md"
JSON_FILE = "STAGE_0_CONSTITUTION.json"

# Digests as recorded at the original freeze. Duplicated here on purpose: if both the constitution
# and its freeze record were rewritten together, the hash-vs-record test would still pass, but this
# one would not.
EXPECTED_DIGESTS = {
    MD_FILE: "b6f20176b6538722e45ae34e6f8b55a818a6e50057a23e9ddd097e0ce73ce1e5",
    JSON_FILE: "af45fda6b37bed50768d5f3d01d4a91175da93e708c9daf1b630e35a981e2ff5",
}


@pytest.fixture(scope="module")
def freeze_record(governance_dir: Path) -> dict[str, str]:
    """Parse the coreutils-format freeze record into ``{filename: digest}``."""
    text = (governance_dir / FREEZE_FILE).read_text(encoding="utf-8")
    entries: dict[str, str] = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        match = re.fullmatch(r"([0-9a-f]{64})\s[\s*](.+)", line)
        assert match, f"unparseable freeze line: {line!r}"
        entries[match.group(2).strip()] = match.group(1)
    return entries


@pytest.fixture(scope="module")
def constitution(governance_dir: Path) -> dict:
    return json.loads((governance_dir / JSON_FILE).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def constitution_md(governance_dir: Path) -> str:
    return (governance_dir / MD_FILE).read_text(encoding="utf-8")


# --------------------------------------------------------------------------------------------
# Presence and integrity
# --------------------------------------------------------------------------------------------


@pytest.mark.parametrize("name", [MD_FILE, JSON_FILE, FREEZE_FILE])
def test_required_stage0_artifact_exists(governance_dir: Path, name: str) -> None:
    path = governance_dir / name
    assert path.is_file(), f"missing frozen artifact: {path}"
    assert path.stat().st_size > 0, f"frozen artifact is empty: {path}"


def test_freeze_record_covers_both_constitution_files(freeze_record: dict[str, str]) -> None:
    assert set(freeze_record) == {MD_FILE, JSON_FILE}


def test_freeze_record_paths_are_relative_to_governance_dir(freeze_record: dict[str, str]) -> None:
    """The record uses bare filenames, so verification must run from ``governance/``.

    Pinning this stops a future maintainer from "fixing" a verification failure that is really a
    wrong-working-directory mistake.
    """
    for name in freeze_record:
        assert "/" not in name and "\\" not in name


@pytest.mark.parametrize("name", [MD_FILE, JSON_FILE])
def test_file_matches_freeze_record(governance_dir: Path, freeze_record: dict[str, str], name: str) -> None:
    assert sha256_file(governance_dir / name) == freeze_record[name]


@pytest.mark.parametrize("name", [MD_FILE, JSON_FILE])
def test_file_matches_independently_pinned_digest(governance_dir: Path, name: str) -> None:
    assert sha256_file(governance_dir / name) == EXPECTED_DIGESTS[name]


# --------------------------------------------------------------------------------------------
# Machine-readable validity
# --------------------------------------------------------------------------------------------


def test_constitution_json_is_valid_and_identifies_itself(constitution: dict) -> None:
    assert constitution["document_id"] == "SE100-GOV-0001"
    assert constitution["project"] == "StockEdge100"
    assert constitution["version"] == "1.0.0"
    assert constitution["status"] == "FROZEN"
    assert constitution["stage"] == 0


def test_gate_ids_are_complete_and_unique(constitution: dict) -> None:
    ids = [gate["id"] for gate in constitution["gates"]]
    assert ids == sorted(ids)
    assert len(ids) == len(set(ids))
    assert set(ids) == set(range(10))


def test_every_gate_declares_a_failure_or_default_result(constitution: dict) -> None:
    for gate in constitution["gates"]:
        assert gate.get("fail_result") or gate.get("default_result"), gate


# --------------------------------------------------------------------------------------------
# Human vs machine agreement. Each assertion pairs a JSON value with the literal text that
# expresses the same rule in the Markdown, so the two cannot silently drift apart.
# --------------------------------------------------------------------------------------------


def _gate(constitution: dict, gate_id: int) -> dict:
    return next(gate for gate in constitution["gates"] if gate["id"] == gate_id)


def test_scope_rules_agree(constitution: dict, constitution_md: str) -> None:
    gen1 = constitution["generation_1"]
    assert gen1["long_only"] is True and "Long-only" in constitution_md
    assert gen1["cash_account_only"] is True and "USD 100 cash account" in constitution_md
    assert gen1["max_risky_positions"] == 1
    assert "One open risky position in Generation 1" in constitution_md
    assert gen1["max_gross_exposure_pct"] == 95
    assert "Maximum 95% of current equity" in constitution_md
    assert gen1["fractional_shares_required"] is True and "Fractional shares" in constitution_md
    assert constitution["capital_usd"] == 100.0


def test_prohibited_product_list_agrees(constitution: dict, constitution_md: str) -> None:
    prohibited = set(constitution["generation_1"]["prohibited"])
    assert prohibited == {
        "options", "futures", "CFDs", "short_sales", "margin",
        "leveraged_ETFs", "inverse_ETFs", "OTC_securities", "penny_stocks", "crypto",
    }
    for token in ["Options", "futures", "CFDs", "OTC securities", "penny stocks", "short sales", "margin", "crypto"]:
        assert token in constitution_md, token


def test_risk_thresholds_agree(constitution: dict, constitution_md: str) -> None:
    risk = constitution["risk"]
    assert risk["research_max_drawdown_pct"] == 15
    assert "15% below its running high-water mark" in constitution_md
    assert risk["live_soft_halt_drawdown_pct"] == 8
    assert "Soft risk halt at **8%**" in constitution_md
    assert risk["live_hard_halt_drawdown_pct"] == 10
    assert "Hard risk halt at **10%**" in constitution_md


def test_time_partition_agrees(constitution: dict, constitution_md: str) -> None:
    part = constitution["time_partition"]
    assert part["exclude_incomplete_cutoff_month"] is True
    assert "Exclude the incomplete cutoff month" in constitution_md
    assert part["holdout_complete_months"] == 24
    assert "**24 complete calendar months** as the final holdout" in constitution_md
    assert part["validation_complete_months"] == 36
    assert "**36 complete calendar months** as validation" in constitution_md
    assert part["minimum_development_years"] == 5
    assert "minimum of five years" in constitution_md
    assert part["calculate_before_strategy_results"] is True


def test_cost_policy_agrees(constitution: dict, constitution_md: str) -> None:
    costs = constitution["costs"]
    assert costs["stressed_cost_multiplier"] == 2.0
    assert "**2× the complete base trading-friction assumption**" in constitution_md
    for key in ["base_costs_required", "spread_required", "slippage_required", "fees_required"]:
        assert costs[key] is True


def test_gate3_development_thresholds_agree(constitution: dict, constitution_md: str) -> None:
    thresholds = _gate(constitution, 3)["thresholds"]
    assert thresholds["max_drawdown_pct"] == 15
    assert thresholds["profit_factor_min"] == 1.10
    assert thresholds["closed_trades_min"] == 30
    assert thresholds["net_return_positive"] is True
    assert thresholds["best_trade_removed_return_positive"] is True
    assert "no worse than **15%**" in constitution_md
    assert "at least **1.10**" in constitution_md
    assert "at least **30 closed trades**" in constitution_md


def test_gate4_validation_thresholds_agree(constitution: dict, constitution_md: str) -> None:
    thresholds = _gate(constitution, 4)["thresholds"]
    assert thresholds["sharpe_min"] == 0.50
    assert thresholds["profit_factor_min"] == 1.15
    assert thresholds["max_drawdown_pct"] == 15
    assert thresholds["stressed_cost_return_positive"] is True
    assert thresholds["positive_walk_forward_folds_pct_min"] == 70
    assert "at least **0.50**" in constitution_md
    assert "at least **70%**" in constitution_md


def test_gate5_holdout_thresholds_agree(constitution: dict, constitution_md: str) -> None:
    gate = _gate(constitution, 5)
    thresholds = gate["thresholds"]
    assert thresholds["max_drawdown_pct"] == 12
    assert thresholds["profit_factor_min"] == 1.15
    assert thresholds["closed_trades_min"] == 20
    assert thresholds["beats_cash"] is True
    assert thresholds["stressed_cost_return_nonnegative"] is True
    assert gate["insufficient_result"] == "INSUFFICIENT_HOLDOUT_EVIDENCE"
    assert gate["pass_result"] == "ELIGIBLE_FOR_PAPER_TRADING"
    assert "no worse than **12%**" in constitution_md
    assert "at least **20**" in constitution_md
    assert "`INSUFFICIENT_HOLDOUT_EVIDENCE`" in constitution_md


def test_gate7_paper_thresholds_agree(constitution: dict, constitution_md: str) -> None:
    thresholds = _gate(constitution, 7)["thresholds"]
    assert thresholds["calendar_days_min"] == 90
    assert thresholds["calendar_days_max_if_trade_shortfall"] == 180
    assert thresholds["closed_trades_min"] == 30
    assert thresholds["max_drawdown_pct"] == 10
    assert thresholds["profit_factor_min"] == 1.10
    assert "**90 calendar days and 30 closed trades**" in constitution_md
    assert "**180 calendar days**" in constitution_md


def test_gate8_shadow_thresholds_agree(constitution: dict, constitution_md: str) -> None:
    thresholds = _gate(constitution, 8)["thresholds"]
    assert thresholds["calendar_days_min"] == 60
    assert thresholds["intended_round_trips_min"] == 20
    assert thresholds["observation_rule"] == "whichever_is_longer"
    assert "**20 intended round trips or 60 calendar days**, whichever is longer" in constitution_md


# --------------------------------------------------------------------------------------------
# Live-trading lock. These are the tests that must never be "fixed" to make a gate pass.
# --------------------------------------------------------------------------------------------


def test_live_trading_default_is_locked(constitution: dict, constitution_md: str) -> None:
    gate9 = _gate(constitution, 9)
    assert gate9["default_result"] == "LIVE_TRADING_LOCKED"
    assert gate9["manual_written_approval_required"] is True
    assert "`LIVE_TRADING_LOCKED`" in constitution_md
    assert "cannot be passed by software automatically" in constitution_md


def test_no_live_authorization_artifact_exists(project_root: Path) -> None:
    """A live authorization must be an explicit, dated, human-created artifact.

    Until such a file exists and is reviewed, no code path may treat live trading as authorized.
    """
    candidates = list(project_root.glob("governance/*LIVE*AUTHORIZATION*"))
    candidates += list(project_root.glob("deployment/*LIVE*AUTHORIZATION*"))
    assert candidates == [], f"unexpected live-authorization artifact present: {candidates}"


def test_constitution_declares_stage0_pass(constitution: dict, constitution_md: str) -> None:
    assert constitution["stage_0_verdict"] == "PASS"
    assert constitution["stage_0_reason"] == "STAGE_0_CONSTITUTION_FROZEN"
    assert "`PASS — STAGE_0_CONSTITUTION_FROZEN`" in constitution_md


def test_next_authorized_activity_is_stage1(constitution: dict) -> None:
    assert constitution["next_authorized_activity"].startswith("Stage 1")


# --------------------------------------------------------------------------------------------
# Repository hygiene
# --------------------------------------------------------------------------------------------


SECRET_PATTERNS = [
    re.compile(r"\bPK[A-Z0-9]{16,}\b"),            # Alpaca key id shape
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),           # AWS key id shape
    re.compile(r"(?i)\b(api[_-]?secret|secret[_-]?key)\s*[:=]\s*['\"][^'\"]{12,}"),
]


def test_no_secret_material_in_governance_or_source(project_root: Path) -> None:
    scanned = 0
    for path in sorted(project_root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".md", ".json", ".py", ".toml", ".yaml", ".yml", ".txt", ".cfg", ".sha256"}:
            continue
        if "data" in path.relative_to(project_root).parts[:1]:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        scanned += 1
        for pattern in SECRET_PATTERNS:
            assert not pattern.search(text), f"possible secret material in {path}"
    assert scanned > 0
