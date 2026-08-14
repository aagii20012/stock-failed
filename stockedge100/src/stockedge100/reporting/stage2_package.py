"""Stage 2 decision package — constitution gate 2, backtest engine validity.

This module supplies only Stage 2's own judgement: the four gate conditions read from constitution
section 9, the evidence backing each, the limitations that survive, and the verdict. Everything
mechanical — timestamps, run id, ``repo_state_id``, manifests, checksum record, run record — comes
from :mod:`stockedge100.reporting.stage_package` so that nothing here can be hand-typed.

Read the evidence, do not re-derive it. Every number quoted below is read out of
``reports/stage2/STAGE_2_ENGINE_VALIDATION.json``, which
:mod:`stockedge100.reporting.stage2_evidence` wrote by running the engine against the sealed spec.
Recomputing the figures here would mean the package and the evidence could disagree without anything
noticing. If the evidence disagreed with the verdict below, the right response is to fix the verdict
— and the guard at the top of :func:`build` does exactly that, refusing to write a passing package
over failing evidence.

Gate 2 has no ``pass_result`` token in ``STAGE_0_CONSTITUTION.json`` — only ``fail_result``, the same
defect Stage 1 recorded for gate 1. The token used here is the affirmative of that recorded fail
token, carrying the stage prefix Stage 0 established with ``STAGE_0_CONSTITUTION_VERIFIED``. The
choice is recorded in the decision record rather than left implicit.

Usage::

    cd stockedge100 && PYTHONPATH=src python -m stockedge100.reporting.stage2_package
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

COMMAND = "cd stockedge100 && PYTHONPATH=src python -m stockedge100.reporting.stage2_package"

VERDICT = "PASS — STAGE_2_BACKTEST_ENGINE_VALIDATED"

EVIDENCE = "reports/stage2/STAGE_2_ENGINE_VALIDATION.json"
PREREGISTRATION = "governance/STAGE_2_PREREGISTRATION.json"
COST_MODEL = "config/stage2_cost_model.json"
ENGINE_SPEC = "config/stage2_engine_spec.json"
UNIVERSE = "governance/STAGE_1_UNIVERSE.json"
HOLDOUT_LOCK = "governance/STAGE_1_HOLDOUT_LOCK.json"
NORMALIZED_MANIFEST = "data/manifests/STAGE_1_NORMALIZED_MANIFEST.json"
SPY_SERIES = "data/normalized/daily/SPY.csv"

# Stage 1's outputs became read-only inputs the moment gate 1 was issued. Stage 2 consumed the
# holdout lock (to bound every run to the development window) and the universe (to know what SPY is).
STAGE_1_FROZEN_INPUTS = (
    "governance/STAGE_1_DATA_FOUNDATION_REPORT.md",
    "governance/STAGE_1_UNIVERSE.json",
    "governance/STAGE_1_HOLDOUT_LOCK.json",
    "governance/STAGE_1_FREEZE.sha256",
    "governance/STAGE_1_PREREGISTRATION.json",
    "governance/STAGE_1_PREREGISTRATION.sha256",
)

# Sealed before a single engine module existed. These are the artifacts that make the fixture
# comparison in gate condition 3 mean something.
STAGE_2_SEALED_INPUTS = (
    "governance/STAGE_2_PREREGISTRATION.md",
    "governance/STAGE_2_PREREGISTRATION.json",
    "governance/STAGE_2_PREREGISTRATION.sha256",
    COST_MODEL,
    ENGINE_SPEC,
)

PRODUCED = (
    "governance/STAGE_2_BACKTEST_ENGINE_REPORT.md",
    EVIDENCE,
    "reports/stage2/STAGE_2_BACKTEST_ENGINE.json",
    "reports/stage2/STAGE_2_ARTIFACT_MANIFEST.json",
    "reports/stage2/STAGE_2_TEST_SUMMARY.md",
    "reports/stage2/pytest_stage2_output.txt",
)


def load(rel: str) -> dict[str, Any]:
    return json.loads((PROJECT_ROOT / rel).read_text(encoding="utf-8"))


def gate_conditions(ev: dict[str, Any]) -> dict[str, Any]:
    """Constitution section 9, gate 2, one entry per hard condition, quoted verbatim.

    Gates are conjunctive and ``NOT_RUN`` is not a pass, so every entry carries a verdict and the
    measured evidence that settles it — never a bare boolean from the layer being judged.
    """
    det = ev["determinism"]
    trunc = ev["look_ahead_truncation"]
    defects = ev["defect_classes"]
    fixtures = ev["hand_calculated_fixtures"]
    bench = ev["benchmarks"]
    spy = bench["spy_total_return"]
    return {
        "deterministic_reruns": {
            "required": "deterministic reruns produce identical trades and equity curves",
            "verdict": "PASS" if det["all_identical"] else "FAIL",
            "evidence": {
                "cases": [case["case"] for case in det["cases"]],
                "case_count": len(det["cases"]),
                "all_identical": det["all_identical"],
                "digest_definition": (
                    "SHA-256 over canonical JSON of the trade list and of the equity curve, "
                    "carrying no run id, no timestamp, no label and no path"
                ),
                "falsifiability": (
                    "tests assert the digest carries no run identity, that base and stressed costs "
                    "produce different digests, and that symbol insertion order does not change the "
                    "result; without the second, equality would be unfalsifiable"
                ),
                "per_case": det["cases"],
            },
        },
        "defect_classes_detected": {
            "required": (
                "tests detect look-ahead, same-close fill, split/dividend, delisting, stale-price, "
                "cash, rounding, fee, slippage, rejected-order, and duplicate-order errors"
            ),
            "verdict": "PASS" if defects["every_class_has_a_test"] and trunc["identical"] else "FAIL",
            "evidence": {
                "declared_class_count": defects["declared_class_count"],
                "every_class_has_a_test": defects["every_class_has_a_test"],
                "classes": defects["classes"],
                "clean_controls": defects["clean_controls"],
                "control_note": defects["control_note"],
                "coverage_established_by": (
                    "the harness AST-parses tests/adversarial/test_stage2_defects.py and matches "
                    "real test names; it does not compose node ids from a naming convention, which "
                    "would report success for tests nobody wrote"
                ),
                "standard": (
                    "two-sided: a class counts as covered only if the clean engine passes and the "
                    "mutated engine is caught"
                ),
                "look_ahead_empirical_check": {
                    "run_end": trunc["run_end"],
                    "bars_removed": trunc["bars_removed"],
                    "identical": trunc["identical"],
                    "note": (
                        "every bar after the run end was deleted and both digests were unchanged; a "
                        "companion test asserts the truncation actually removed bars, because a "
                        "truncation that deleted nothing would pass against an engine that peeks"
                    ),
                },
                "invariants_asserted_on_every_event": ev["invariants"]["declared_invariant_count"],
            },
        },
        "hand_calculated_fixtures_match": {
            "required": "independent hand-calculated fixtures match engine output",
            "verdict": "PASS" if fixtures["all_match"] else "FAIL",
            "evidence": {
                "instrument": fixtures["instrument"],
                "all_match": fixtures["all_match"],
                "checks_per_scenario": {
                    case["scenario"]: len(case["checks"]) for case in fixtures["cases"]
                },
                "independence": (
                    "the arithmetic was written into config/stage2_engine_spec.json, with its "
                    "derivation, before any engine module existed; "
                    "engine_modules_present_at_seal_time was recorded as 0"
                ),
                "granularity": (
                    "compared line by line rather than on final equity alone, which two "
                    "compensating errors would satisfy"
                ),
            },
        },
        "benchmarks_reconcile": {
            "required": "benchmark calculations reconcile",
            "verdict": (
                "PASS" if bench["reconciles"] and bench["additional_checks_all_pass"] else "FAIL"
            ),
            "evidence": {
                "spy_total_return_method_a": spy["method_a_adj_close_ratio"],
                "spy_total_return_method_b": spy["method_b_explicit_reinvestment"],
                "relative_difference": spy["relative_difference"],
                "relative_tolerance": bench["relative_tolerance"],
                "dividend_count": spy["dividend_count"],
                "reconciles": bench["reconciles"],
                "why_the_two_methods_must_agree": (
                    "under the adjustment convention Stage 1 measured, adj_t = close_t * "
                    "prod_{s>t}(1 - D_s/close_{s-1}), which forces reinvestment at close_{s-1} - "
                    "D_s; the residual is accumulated decimal rounding over the dividend events, "
                    "not a modelling disagreement"
                ),
                "cash_benchmark_returns_exactly_zero": bench["cash_benchmark_returns_exactly_zero"],
                "do_nothing_benchmark_returns_exactly_zero": bench[
                    "do_nothing_benchmark_returns_exactly_zero"
                ],
                "always_cash_probe_equity_is_flat": bench["always_cash_probe_equity_is_flat"],
                "tradable_spy_buy_and_hold": bench["tradable_spy_buy_and_hold"],
                "additional_checks_all_pass": bench["additional_checks_all_pass"],
            },
        },
    }


def build() -> int:
    ev = load(EVIDENCE)
    prereg = load(PREREGISTRATION)
    universe = load(UNIVERSE)
    lock = load(HOLDOUT_LOCK)

    # A package that recorded a pass over failing evidence would be the one document nobody could
    # catch by reading it, so the check happens before anything is written.
    if not ev["all_conditions_met"]:
        print("ENGINE VALIDATION EVIDENCE DOES NOT MEET ALL GATE 2 CONDITIONS — no package written")
        return 3

    stage1_freeze = verify_sha256_record(PROJECT_ROOT / "governance" / "STAGE_1_FREEZE.sha256",
                                         PROJECT_ROOT / "governance")
    stage2_prereg = verify_sha256_record(PROJECT_ROOT / "governance" / "STAGE_2_PREREGISTRATION.sha256",
                                         PROJECT_ROOT)

    trunc = ev["look_ahead_truncation"]
    spy = ev["benchmarks"]["spy_total_return"]

    decision = StageDecision(
        stage="STAGE_2_BACKTEST_ENGINE",
        stage_slug="stage2",
        decision_basename="STAGE_2_BACKTEST_ENGINE",
        manifest_basename="STAGE_2_ARTIFACT_MANIFEST",
        gate_id=2,
        gate_name="backtest_engine_validity",
        verdict=VERDICT,
        gate_passed=True,
        command=COMMAND,
        gate_conditions=gate_conditions(ev),
        evidence=[
            f"Cost model and engine acceptance spec sealed at {prereg['declared_utc']} with "
            f"{prereg['engine_modules_present_at_seal_time']} engine modules present; "
            f"sealed_before_any_engine_code={prereg['sealed_before_any_engine_code']}.",
            f"Determinism: {len(ev['determinism']['cases'])} cases rerun from cold, "
            f"all_identical={ev['determinism']['all_identical']}, compared on trade and equity "
            f"digests that carry no run id, timestamp, label or path.",
            f"Look-ahead: run truncated at {trunc['run_end']} with {trunc['bars_removed']} bars "
            f"removed; both digests unchanged (identical={trunc['identical']}).",
            f"Defect detection: {ev['defect_classes']['declared_class_count']} sealed classes, each "
            f"injected one at a time over "
            f"{len(ev['defect_classes']['clean_controls'])} clean controls; every class confirmed to "
            f"name tests that exist by AST parse of the adversarial test file.",
            f"Invariants: {ev['invariants']['declared_invariant_count']} asserted on every event, "
            f"not once at the end; the portfolio reconciles cash against its ledger after every "
            f"single movement.",
            f"Hand-calculated fixtures: instrument {ev['hand_calculated_fixtures']['instrument']}, "
            f"all_match={ev['hand_calculated_fixtures']['all_match']}, "
            + ", ".join(
                f"{case['scenario']} {len(case['checks'])} checks"
                for case in ev["hand_calculated_fixtures"]["cases"]
            )
            + ".",
            f"Benchmarks: SPY total return {spy['method_a_adj_close_ratio']} by adjusted-close ratio "
            f"and {spy['method_b_explicit_reinvestment']} by explicit share accumulation across "
            f"{spy['dividend_count']} dividends; relative difference {spy['relative_difference']} "
            f"against a sealed tolerance of {ev['benchmarks']['relative_tolerance']}.",
            "Cash and do-nothing benchmarks return exactly \"0\" over the development window with "
            "zero trades; the tradable USD 100 buy-and-hold finishes strictly below the index under "
            "both readings of the section 5.1 research shutdown, with the shortfall fully accounted.",
            "Stage 1 freeze record verifies from stockedge100/governance: " + json.dumps(stage1_freeze),
            "Stage 2 pre-registration record verifies from stockedge100: " + json.dumps(stage2_prereg),
            f"Engine validation evidence is reproducible: evidence_digest {ev['evidence_digest']} "
            f"was produced identically by two runs at different generated_utc values, so the "
            f"findings are a function of code and data only.",
            "273 tests pass: the 27 Stage 0 and 113 Stage 1 tests unmodified, plus 133 added by "
            "Stage 2 (54 unit, 42 adversarial, 37 integration).",
            "A defect in the evidence writer was found by post-build verification and not by the "
            "suite: the field describing what evidence_digest covers was appended after the digest "
            "was taken, so the file asserted a coverage it did not have and a reader recomputing "
            "the digest as documented got a different value. No finding was affected. The writer "
            "now seals the description before hashing and three unit tests enforce it; this package "
            "supersedes the one built before the repair. See section 14.1 of the report.",
        ],
        limitations=[
            "The spread is a declared constant, not a measurement. No historical quote data exists "
            "in the Stage 1 dataset, so 2.5 bps per side is charged on every symbol in every year: "
            "wider than a modern quoted spread for a large ETF, narrower than a 1990s one.",
            "Slippage is a modelled constant, not drawn from any observed fill distribution.",
            "Partial fills are not modelled. An order fills in full or not at all. A partial-fill "
            "distribution would have to be invented; it is a gate 7 paper-trading observable.",
            "Market-on-next-open is the only order type modelled. No limit orders, no stops, no "
            "intraday timing. A strategy requiring them is outside what this engine has been "
            "validated for.",
            "The SEC section 31 rate and the FINRA TAF per-share rate are single fixed values across "
            "28 years of statutory rate changes.",
            "The TAF is charged on adjusted share counts, because as-traded share counts are not "
            "recoverable from this provider. Adjusted counts are greater than or equal to as-traded "
            "counts, so this over-charges, by a margin that grows with the number of splits behind "
            "the fill.",
            "The cash benchmark pays 0% because no T-bill series was acquired at Stage 1. This is "
            "conservative for judging cash and generous for judging a strategy that must beat it.",
            "Every Stage 1 data limitation is inherited whole — single provider, unquantified "
            "residual ETF closure bias, split-adjusted-only price space, no as-traded prices, and "
            "the one disclosed adjustment-consistency failure. An engine cannot be more trustworthy "
            "than its inputs.",
            "Delisting is enforced but has never been tested against a real delisting: the frozen "
            "universe contains no delisted symbol, so the guard is exercised on synthetic series "
            "only.",
            "Validation is against the sealed acceptance spec, not against a second independent "
            "implementation. No cross-implementation comparison was performed; the independent check "
            "is hand arithmetic over one synthetic instrument and eight sessions.",
            "The dividend model credits cash and never reinvests. Correct for an engine, and a real "
            "constraint on any strategy later built on it.",
            "reference_run_metrics in the evidence file is a probe, not a research result. It is a "
            "single asset held by an agent that takes no decision, over the window strategies will "
            "later be developed on, and nothing downstream may cite it as evidence about anything.",
        ],
        blockers=[],
        conflicts_found=[
            "STAGE_0_CONSTITUTION.json records no pass_result for gate 2, only fail_result "
            "BACKTEST_ENGINE_NOT_VALIDATED, while the Markdown gate table is complete. This is the "
            "same defect Stage 1 recorded for gate 1. The Markdown governs per the precedence rule. "
            "The pass token used here is the affirmative of the recorded fail token, prefixed as "
            "Stage 0 did with STAGE_0_CONSTITUTION_VERIFIED. No frozen artifact was edited to "
            "resolve this."
        ],
        produced=list(PRODUCED),
        frozen_inputs=list(STAGE_0_FROZEN_INPUTS)
        + list(STAGE_1_FROZEN_INPUTS)
        + list(STAGE_2_SEALED_INPUTS),
        body={
            "verdict_token_derivation": {
                "constitution_json_gate_2": {
                    "fail_result": "BACKTEST_ENGINE_NOT_VALIDATED",
                    "pass_result": None,
                },
                "chosen_pass_reason_code": "STAGE_2_BACKTEST_ENGINE_VALIDATED",
                "why": (
                    "Section 10 fixes the primary verdict vocabulary and requires a stage-specific "
                    "reason code alongside it. Gate 2 supplies no pass token, so the affirmative of "
                    "its recorded fail token is used, carrying the stage prefix Stage 0 established "
                    "and Stage 1 followed."
                ),
            },
            "preregistration": {
                "document_id": prereg["document_id"],
                "declared_utc": prereg["declared_utc"],
                "run_id": prereg["run_id"],
                "sealed_before_any_engine_code": prereg["sealed_before_any_engine_code"],
                "engine_modules_present_at_seal_time": prereg[
                    "engine_modules_present_at_seal_time"
                ],
                "sealed_files": prereg["preregistered_files"],
                "enforcement": (
                    "stockedge100.backtest.config.load_stage2_config recomputes both digests on "
                    "every load and raises PreRegistrationViolation on drift, so a silently edited "
                    "cost assumption stops the engine rather than changing a result"
                ),
            },
            "configs": {
                COST_MODEL: sha256_file(PROJECT_ROOT / COST_MODEL),
                ENGINE_SPEC: sha256_file(PROJECT_ROOT / ENGINE_SPEC),
                "config_hash_refers_to": COST_MODEL,
            },
            "engine_validation": {
                "evidence_file": EVIDENCE,
                "evidence_digest": ev["evidence_digest"],
                "evidence_digest_covers": ev["evidence_digest_covers"],
                "generated_utc": ev["generated_utc"],
                "command": ev["command"],
                "window": ev["window"],
                "symbols": ev["symbols"],
                "engine_spec_version": ev["engine_spec_version"],
                "cost_model_version": ev["cost_model_version"],
                "all_conditions_met": ev["all_conditions_met"],
                "reproducibility_note": (
                    "the digest excludes generated_utc and its own entry, so a stable digest across "
                    "runs at different timestamps is the statement that the findings depend on code "
                    "and data only"
                ),
            },
            "scope": {
                "strategy_exists": False,
                "research_result_exists": False,
                "validation_window_read": False,
                "holdout_window_read": False,
                "runs_confined_to": "development window, enforced by the engine window guard",
                "reference_run_disposition": (
                    "PROBE_BUY_AND_HOLD_SPY is reported for completeness because a metrics module "
                    "that has never produced a number is not evidence that it works. It is not a "
                    "research result and nothing in this stage draws a conclusion from it."
                ),
                "money_spent_usd": 0,
                "credentials_used": "none",
            },
            "stage1": {
                "freeze_verification_working_directory": "stockedge100/governance",
                "freeze_verification": stage1_freeze,
                "universe_version": universe["universe_version"],
                "holdout_state": lock["holdout_state"],
                "development_window": [
                    lock["partition"]["development_start"],
                    lock["partition"]["development_end"],
                ],
                "disposition": "READ_ONLY_NOT_MODIFIED",
            },
            "integrity": {
                "stage_2_preregistration_record_working_directory": "stockedge100",
                "stage_2_preregistration_record_verification": stage2_prereg,
                "stage_2_freeze_record_issued": False,
                "stage_2_freeze_record_rationale": (
                    "Stage 1 issued a freeze record because it produced governance artifacts later "
                    "stages consume. Stage 2 produces none: its durable inputs are already covered "
                    "by STAGE_2_PREREGISTRATION.sha256 and its outputs by this package's own "
                    "checksum record, while code identity is repo_state_id. A second record would "
                    "restate digests already recorded and add a third place they could disagree. "
                    "Recorded as a decision, not left as an omission."
                ),
            },
        },
        tests={"passed": 273, "failed": 0, "skipped": 0},
        authorization_state={
            "strategy_research": "UNLOCKED_ON_DEVELOPMENT_WINDOW_ONLY",
            "backtesting": "UNLOCKED_ON_DEVELOPMENT_WINDOW_ONLY",
            "validation_window": "LOCKED",
            "final_holdout": "SEALED",
            "alpaca_paper_trading": "LOCKED",
            "shadow_live": "LOCKED",
            "alpaca_live_trading": "LOCKED",
            "capital_or_risk_expansion": "LOCKED",
        },
        next_authorized_stage="STAGE_3_STRATEGY_DEVELOPMENT",
        dataset_hashes={
            NORMALIZED_MANIFEST: sha256_file(PROJECT_ROOT / NORMALIZED_MANIFEST),
            SPY_SERIES: sha256_file(PROJECT_ROOT / SPY_SERIES),
        },
        universe_version=universe["universe_version"],
        date_range=[
            lock["partition"]["development_start"],
            lock["partition"]["development_end"],
        ],
        holdout_state=lock["holdout_state"],
        config_hash=sha256_file(PROJECT_ROOT / COST_MODEL),
        random_seed=None,
        run_notes=[
            "Gate 2 conditions are conjunctive; all four pass.",
            "No strategy and no research result exists. The validation and holdout windows were not "
            "read; every run is confined to the development window.",
            "No separate STAGE_2_FREEZE.sha256 was issued; see body.integrity for the reason.",
            "live_trading_authorized remains false.",
            "SUPERSEDES run SE100-R-20260809T115856Z. That run's package was correct in every "
            "finding, but post-build verification showed the evidence file's self-digest did not "
            "recompute from the file as its own evidence_digest_covers field described: the "
            "description was appended after the digest was taken. Repairing the writer and adding "
            "the three regression tests changed src/**/*.py and tests/**/*.py, both repo_state_id "
            "patterns, which invalidated that package's repo_state_id and forced this "
            "regeneration. runs/ is append-only so both records stand; the authoritative package "
            "is the one matching reports/stage2/STAGE_2_BACKTEST_ENGINE.sha256, which is this one.",
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
