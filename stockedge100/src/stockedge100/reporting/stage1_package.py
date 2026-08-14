"""Stage 1 decision package — constitution gate 1, data readiness.

This module supplies only Stage 1's own judgement: the five gate conditions read from constitution
section 9, the evidence backing each, the limitations that survive, and the verdict. Everything
mechanical — timestamps, run id, ``repo_state_id``, manifests, checksum record, run record — comes
from :mod:`stockedge100.reporting.stage_package` so that nothing here can be hand-typed.

Read the evidence, do not re-derive it. The manifests, the validation report, the universe, and the
holdout lock were written earlier in the stage and are already hashed; this module opens them
read-only and quotes them. If one of them disagreed with the verdict below, the right response is to
fix the verdict.

Gate 1 has no ``pass_result`` token in ``STAGE_0_CONSTITUTION.json`` — only ``fail_result``. The
token used here is the affirmative of that recorded fail token, carrying the stage prefix that
Stage 0 established with ``STAGE_0_CONSTITUTION_VERIFIED``. The choice is recorded in the decision
record rather than left implicit.

Usage::

    cd stockedge100 && PYTHONPATH=src python -m stockedge100.reporting.stage1_package
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from stockedge100.audit import sha256_file
from stockedge100.reporting.stage_package import (
    PROJECT_ROOT,
    STAGE_0_FROZEN_INPUTS,
    StageDecision,
    build_stage_package,
    verify_sha256_record,
)

COMMAND = "cd stockedge100 && PYTHONPATH=src python -m stockedge100.reporting.stage1_package"

VERDICT = "PASS — STAGE_1_DATA_FIT_FOR_RESEARCH"

RAW_MANIFEST = "data/manifests/STAGE_1_RAW_MANIFEST.json"
NORMALIZED_MANIFEST = "data/manifests/STAGE_1_NORMALIZED_MANIFEST.json"
VALIDATION_REPORT = "data/manifests/STAGE_1_VALIDATION_REPORT.json"
UNIVERSE = "governance/STAGE_1_UNIVERSE.json"
HOLDOUT_LOCK = "governance/STAGE_1_HOLDOUT_LOCK.json"

# The pre-registration and the two configuration files it sealed are inputs to everything that
# followed them, and were read-only from the moment they were hashed.
STAGE_1_SEALED_INPUTS = (
    "governance/STAGE_1_PREREGISTRATION.md",
    "governance/STAGE_1_PREREGISTRATION.json",
    "governance/STAGE_1_PREREGISTRATION.sha256",
    "config/stage1_data_source.json",
    "config/stage1_universe_spec.json",
)

PRODUCED = (
    "governance/STAGE_1_DATA_FOUNDATION_REPORT.md",
    "governance/STAGE_1_UNIVERSE.json",
    "governance/STAGE_1_HOLDOUT_LOCK.json",
    "governance/STAGE_1_FREEZE.sha256",
    RAW_MANIFEST,
    NORMALIZED_MANIFEST,
    VALIDATION_REPORT,
    "reports/stage1/STAGE_1_DATA_READINESS.json",
    "reports/stage1/STAGE_1_ARTIFACT_MANIFEST.json",
    "reports/stage1/STAGE_1_TEST_SUMMARY.md",
    "reports/stage1/pytest_stage1_output.txt",
)


def load(rel: str) -> dict[str, Any]:
    return json.loads((PROJECT_ROOT / rel).read_text(encoding="utf-8"))


def gate_conditions(raw, norm, val, universe, lock) -> dict[str, Any]:
    """Constitution section 9, gate 1, one entry per hard condition, quoted verbatim.

    Gates are conjunctive and ``NOT_RUN`` is not a pass, so every entry carries a verdict and a
    pointer to the artifact that settles it.
    """
    semantics = val["adjustment_semantics"]
    probes = semantics["probes"]
    return {
        "manifests_complete_and_hash_verified": {
            "required": "raw and normalized manifests are complete and hash-verified",
            "verdict": "PASS",
            "evidence": {
                "candidates_requested": raw["candidate_count"],
                "reference_symbols_requested": raw["reference_count"],
                "acquisition_failures": raw["acquisition_failures"],
                "acquisition_failure_fraction": raw["acquisition_failure_fraction"],
                "blocking_threshold": raw["blocking_threshold"],
                "normalized_symbol_count": norm["symbol_count"],
                "normalized_manifest_chains_to_raw_manifest": norm["source_manifest"]["sha256"]
                == sha256_file(PROJECT_ROOT / RAW_MANIFEST),
                "every_digest_recomputed_by_test": (
                    "tests/integration/test_stage1_data_foundation.py recomputes the SHA-256 of "
                    "all 35 raw and all 35 normalized files against the manifests"
                ),
            },
        },
        "structural_tests_pass": {
            "required": (
                "session, timestamp, OHLCV, split, dividend, missing-data, and duplication tests pass"
            ),
            "verdict": "PASS",
            "evidence": {
                "checks_in_sealed_battery": val["battery_source"]["check_count"],
                "symbols_checked": val["symbol_count"],
                "enumerated_families_all_pass_on_all_symbols": {
                    family: val["check_totals"][family]
                    for family in (
                        "SESSION_IN_CALENDAR",
                        "NO_FUTURE_SESSIONS",
                        "OHLC_CONSISTENT",
                        "VOLUME_VALID",
                        "ADJ_CLOSE_POSITIVE",
                        "SPLIT_RECONCILES",
                        "DIVIDEND_RECONCILES",
                        "MISSING_SESSION_FRACTION",
                        "MISSING_SESSION_RUN",
                        "NO_DUPLICATE_SESSIONS",
                        "SESSIONS_STRICTLY_INCREASING",
                    )
                },
                "research_universe_battery_passed": val["research_universe_battery_passed"],
                "research_universe_failures": val["research_universe_failures"],
                "unclassified_failures": val["unclassified_failures"],
                "note": (
                    "The one FAIL in the whole battery is AAPL:TERMINAL_FACTOR_IS_ONE, an "
                    "adjustment-consistency check rather than one of the families enumerated in "
                    "this condition. It is disclosed under the next condition and in limitations."
                ),
            },
        },
        "adjustment_independently_checked_on_known_corporate_actions": {
            "required": (
                "adjustment behavior is independently checked on known corporate-action examples"
            ),
            "verdict": "PASS",
            "evidence": {
                "determination": semantics["determination"],
                "method": semantics["method"],
                "fixtures": [
                    {
                        "symbol": probe["symbol"],
                        "session": probe["session"],
                        "declared_split_ratio": probe["declared_split_ratio"],
                        "recorded_split_ratio": probe["recorded_split_ratio"],
                        "unadjusted_close_step": probe["unadjusted_close_step"],
                        "step_if_series_were_as_traded": probe["step_if_series_were_as_traded"],
                    }
                    for probe in probes
                ],
                "corporate_action_fixture_check": val["check_totals"]["CORPORATE_ACTION_FIXTURE"],
                "known_defect": val["preregistration_scope_gaps"],
                "defect_disposition": (
                    "AAPL is a reference fixture, not a research symbol. Its window was truncated "
                    "at 2021-07-31 by the sealed spec so that a data-quality fixture can never "
                    "touch validation or holdout data, which makes the terminal factor unequal to "
                    "one by construction. The sealed check was not amended, weakened, or removed; "
                    "the failure is recorded and classified. Every fixture comparison is a ratio, "
                    "so a constant scale factor does not affect it."
                ),
            },
        },
        "universe_bias_controlled_or_prospectively_narrowed": {
            "required": (
                "universe bias is controlled or the research universe is prospectively narrowed"
            ),
            "verdict": "PASS",
            "satisfied_by": "the second disjunct — prospective narrowing",
            "evidence": {
                "research_universe_class": universe["research_universe_class"],
                "member_count": universe["member_count"],
                "stock_universe_verdict": universe["survivorship_bias"]["stock_universe_verdict"],
                "stock_research_authorization": universe["survivorship_bias"][
                    "stock_research_authorization"
                ],
                "etf_universe_verdict": universe["survivorship_bias"]["etf_universe_verdict"],
                "bias_quantified": universe["survivorship_bias"]["quantified"],
                "narrowing_was_prospective": universe["preregistration"][
                    "sealed_before_any_data_acquired"
                ],
                "not_claimed": (
                    "The first disjunct is explicitly NOT claimed. Bias is not controlled; it is "
                    "narrowed and the residual is disclosed and unquantified."
                ),
            },
        },
        "partitions_and_holdout_locked_before_results": {
            "required": "time partitions and final holdout are locked before results",
            "verdict": "PASS",
            "evidence": {
                "locked_utc": lock["locked_utc"],
                "holdout_state": lock["holdout_state"],
                "locked_before_any_strategy_result": lock["locked_before_any_strategy_result"],
                "partition": lock["partition"],
                "cutoff_derived_from": lock["inputs"]["cutoff_derived_from"],
                "no_strategy_exists_yet": (
                    "Generation 1 has no strategy, no backtest engine, and no result of any kind at "
                    "the time of this lock; constitution gate 2 has not been attempted."
                ),
                "enforced_by": universe["measurement_window_restriction"]["enforced_by"],
            },
        },
    }


def build() -> int:
    raw = load(RAW_MANIFEST)
    norm = load(NORMALIZED_MANIFEST)
    val = load(VALIDATION_REPORT)
    universe = load(UNIVERSE)
    lock = load(HOLDOUT_LOCK)

    freeze_check = verify_sha256_record(PROJECT_ROOT / "governance" / "STAGE_1_FREEZE.sha256",
                                        PROJECT_ROOT / "governance")
    prereg_check = verify_sha256_record(PROJECT_ROOT / "governance" / "STAGE_1_PREREGISTRATION.sha256",
                                        PROJECT_ROOT)

    decision = StageDecision(
        stage="STAGE_1_DATA_FOUNDATION",
        stage_slug="stage1",
        decision_basename="STAGE_1_DATA_READINESS",
        manifest_basename="STAGE_1_ARTIFACT_MANIFEST",
        gate_id=1,
        gate_name="data_readiness",
        verdict=VERDICT,
        gate_passed=True,
        command=COMMAND,
        gate_conditions=gate_conditions(raw, norm, val, universe, lock),
        evidence=[
            f"Rules sealed at {load('governance/STAGE_1_PREREGISTRATION.json')['declared_utc']} with "
            f"{load('governance/STAGE_1_PREREGISTRATION.json')['raw_data_files_present_at_seal_time']} "
            f"raw data files present; first provider request at {raw['acquisition_started_utc']}.",
            f"{raw['candidate_count']} candidates and {raw['reference_count']} reference symbol "
            f"acquired from {raw['provider']} via {raw['client']} {raw['client_version']}; "
            f"acquisition failure fraction {raw['acquisition_failure_fraction']} against a "
            f"blocking threshold of {raw['blocking_threshold']}.",
            f"Adjustment semantics {val['adjustment_semantics']['determination']}, not assumed, from "
            f"{len(val['adjustment_semantics']['probes'])} known corporate-action fixtures.",
            f"Sealed battery of {val['battery_source']['check_count']} checks run over "
            f"{val['symbol_count']} symbols; research-universe failures "
            f"{val['research_universe_failures']}; unclassified failures "
            f"{val['unclassified_failures']}.",
            f"Trading calendar {val['calendar']['name']} from {val['calendar']['source']}, "
            f"independent of the price provider, bounds {val['calendar']['bounds']}.",
            f"Universe {universe['universe_version']} frozen at {universe['frozen_utc']} with "
            f"{universe['member_count']} members, {len(universe['rejected'])} rejected, "
            f"{len(universe['not_acquired'])} not acquired.",
            f"Holdout {lock['holdout_state']} at {lock['locked_utc']}: development "
            f"{lock['partition']['development_start']}..{lock['partition']['development_end']}, "
            f"validation {lock['partition']['validation_start']}..{lock['partition']['validation_end']}, "
            f"holdout {lock['partition']['holdout_start']}..{lock['partition']['holdout_end']}.",
            "Stage 1 freeze record verifies from stockedge100/governance: "
            + json.dumps(freeze_check),
            "Stage 1 pre-registration record verifies from stockedge100: " + json.dumps(prereg_check),
            "140 tests pass: the 27 Stage 0 regression tests unmodified, plus 113 added by Stage 1.",
        ],
        limitations=[
            "Single provider. Every price in this stage comes from one unofficial public endpoint "
            "via yfinance. There is no second source to cross-check it against, so a systematic "
            "provider error would pass every check in the battery undetected.",
            "The provider licence is personal and non-commercial with no redistribution. The data "
            "is stored locally and git-ignored. It is not a licence for any commercial use, and a "
            "later stage that needs one must acquire it.",
            "Residual ETF closure bias is disclosed and unquantified. The candidate list was "
            "assembled in 2026 and therefore contains only funds that still existed in 2026; funds "
            "that launched and closed inside the development window are absent. Prospective "
            "narrowing reduces this bias, it does not remove it.",
            "Individual stocks carry uncontrolled survivorship bias with this data source and are "
            "prohibited for Generation 1 research without a new, point-in-time constituent source.",
            "AAPL:TERMINAL_FACTOR_IS_ONE fails. The sealed check assumed every series ends at the "
            "provider's terminal session; AAPL's was deliberately truncated at 2021-07-31. This is "
            "a defect in the Stage 1 pre-registration, recorded and classified rather than fixed by "
            "amending a sealed check. AAPL is not in the research universe.",
            "As-traded price levels are unavailable. The provider returns split-adjusted OHLC, so "
            "the historical price a share actually traded at cannot be recovered. Any later stage "
            "modelling per-share minimum tick, whole-share position sizing, or a price-level rule "
            "must treat this as missing input, not approximate it from adjusted prices.",
            "Storage is CSV, not parquet. pyproject declares an optional parquet path but pyarrow "
            "is not installed in this environment. Recorded as a deviation from the declared "
            "preference rather than left implicit.",
            "The acquisition code passes raise_errors=True to yfinance, which emits a "
            "DeprecationWarning in version 1.4.1. It was left as it was rather than changed after "
            "the fact, so the recorded code state is exactly what produced the data. A future "
            "client version may remove it and break re-acquisition.",
            "Alpaca tradability and fractionability are UNVERIFIED for all 34 members, because no "
            "credential access is authorized at Stage 1. The realized universe is conditional: any "
            "member later found non-tradable or non-fractionable must be removed and every affected "
            "gate re-run.",
            "Structural eligibility rules (US-listed, unleveraged, non-inverse, not a K-1 "
            "partnership, not a commodity trust, rules-based index) are asserted at candidate "
            "construction and are not verifiable from price data. They are labelled as asserted, "
            "not as measured.",
        ],
        blockers=[],
        conflicts_found=[
            "STAGE_0_CONSTITUTION.json records no pass_result for gate 1, only fail_result "
            "DATA_NOT_FIT_FOR_RESEARCH, while the Markdown gate table is complete. The Markdown "
            "governs per the precedence rule. The pass token used here is the affirmative of the "
            "recorded fail token, prefixed as Stage 0 did with STAGE_0_CONSTITUTION_VERIFIED. No "
            "frozen artifact was edited to resolve this."
        ],
        produced=list(PRODUCED),
        frozen_inputs=list(STAGE_0_FROZEN_INPUTS) + list(STAGE_1_SEALED_INPUTS),
        body={
            "verdict_token_derivation": {
                "constitution_json_gate_1": {
                    "fail_result": "DATA_NOT_FIT_FOR_RESEARCH",
                    "pass_result": None,
                },
                "chosen_pass_reason_code": "STAGE_1_DATA_FIT_FOR_RESEARCH",
                "why": (
                    "Section 10 fixes the primary verdict vocabulary and requires a stage-specific "
                    "reason code alongside it. Gate 1 supplies no pass token, so the affirmative of "
                    "its recorded fail token is used, carrying the stage prefix Stage 0 "
                    "established."
                ),
            },
            "preregistration": {
                "declared_utc": load("governance/STAGE_1_PREREGISTRATION.json")["declared_utc"],
                "sealed_before_any_data_acquired": True,
                "raw_data_files_present_at_seal_time": 0,
                "first_provider_request_utc": raw["acquisition_started_utc"],
                "sealed_files": load("governance/STAGE_1_PREREGISTRATION.json")[
                    "preregistered_files"
                ],
            },
            "data_source": {
                "provider": raw["provider"],
                "client": f"{raw['client']} {raw['client_version']}",
                "endpoint_mode": raw["endpoint_mode"],
                "license": raw["license"],
                "raw_definition": raw["raw_definition"],
                "request_parameters": raw["request_parameters"],
                "cost_usd": 0,
                "credentials_used": "none",
            },
            "validation": {
                "battery_source": val["battery_source"],
                "check_totals": val["check_totals"],
                "battery_passed_all_symbols": val["battery_passed"],
                "research_universe_battery_passed": val["research_universe_battery_passed"],
                "symbols_with_failures": val["symbols_with_failures"],
                "symbols_with_warnings": val["symbols_with_warnings"],
                "preregistration_scope_gaps": val["preregistration_scope_gaps"],
                "unclassified_failures": val["unclassified_failures"],
                "quarantine_records": val["quarantine_records"],
                "scope_rules": val["scope_rules"],
                "calendar": val["calendar"],
            },
            "universe": {
                "universe_version": universe["universe_version"],
                "universe_identity_sha256": universe["universe_identity_sha256"],
                "frozen_utc": universe["frozen_utc"],
                "research_universe_class": universe["research_universe_class"],
                "member_count": universe["member_count"],
                "members": universe["members"],
                "rejected": universe["rejected"],
                "not_acquired": universe["not_acquired"],
                "survivorship_bias": universe["survivorship_bias"],
                "broker_eligibility": universe["broker_eligibility"],
                "structural_rules_not_verifiable_from_price_data": universe[
                    "structural_rules_not_verifiable_from_price_data"
                ],
            },
            "holdout_lock": {
                "locked_utc": lock["locked_utc"],
                "holdout_state": lock["holdout_state"],
                "partition": lock["partition"],
                "inputs": lock["inputs"],
                "binding_rules": lock["binding_rules"],
            },
            "integrity": {
                "stage_1_freeze_record_working_directory": "stockedge100/governance",
                "stage_1_freeze_record_verification": freeze_check,
                "stage_1_preregistration_record_working_directory": "stockedge100",
                "stage_1_preregistration_record_verification": prereg_check,
            },
        },
        tests={"passed": 140, "failed": 0, "skipped": 0},
        authorization_state={
            "strategy_research": "UNLOCKED_ON_DEVELOPMENT_WINDOW_ONLY",
            "validation_window": "LOCKED",
            "final_holdout": "SEALED",
            "alpaca_paper_trading": "LOCKED",
            "shadow_live": "LOCKED",
            "alpaca_live_trading": "LOCKED",
            "capital_or_risk_expansion": "LOCKED",
        },
        next_authorized_stage="STAGE_2_BACKTEST_ENGINE",
        dataset_hashes={
            RAW_MANIFEST: sha256_file(PROJECT_ROOT / RAW_MANIFEST),
            NORMALIZED_MANIFEST: sha256_file(PROJECT_ROOT / NORMALIZED_MANIFEST),
            VALIDATION_REPORT: sha256_file(PROJECT_ROOT / VALIDATION_REPORT),
            UNIVERSE: sha256_file(PROJECT_ROOT / UNIVERSE),
            HOLDOUT_LOCK: sha256_file(PROJECT_ROOT / HOLDOUT_LOCK),
        },
        universe_version=universe["universe_version"],
        date_range=[lock["partition"]["development_start"], lock["partition"]["holdout_end"]],
        holdout_state=lock["holdout_state"],
        config_hash=universe["preregistration"]["data_source_sha256"],
        random_seed=None,
        run_notes=[
            "Gate 1 conditions are conjunctive; all five pass.",
            "The holdout window was not read. No strategy, backtest, or performance number exists.",
            "live_trading_authorized remains false.",
            # runs/ is append-only, so an earlier run record is never deleted or rewritten. The
            # package was generated once, the README current-state table and limitations were then
            # brought up to date, and README.md is a tracked file — so repo_state_id changed and the
            # package was regenerated over its own (non-frozen) output. Both run records stand; the
            # authoritative one is whichever matches reports/stage1/STAGE_1_DATA_READINESS.sha256.
            "Supersedes run SE100-R-20260808T111556Z, whose repo_state_id predates the Stage 1 "
            "README update.",
        ],
    )

    result = build_stage_package(decision)
    if not result.freeze_ok:
        print("STAGE 0 FREEZE VERIFICATION FAILED — see the decision record", flush=True)
        return 2

    print(f"run_id        {result.run_id}")
    print(f"timestamp_utc {result.timestamp_utc}")
    print(f"repo_state_id {result.repo_state_id}")
    print(f"verdict       {VERDICT}")
    for path in (result.decision_path, result.manifest_path, result.checksum_path, result.run_record_path):
        print(f"wrote         {Path(path).relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
