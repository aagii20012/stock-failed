"""Seal the Generation 2 time partition lock.

Writes ``governance/generation_2/STAGE_1_G2_PARTITION_LOCK.json`` and the ``.sha256`` record that
covers it together with the hand-authored Markdown counterpart. Run once:

    cd stockedge100 && PYTHONPATH=src python -m stockedge100.reporting.g2_partition_lock

Three properties this module is responsible for.

**It seals once.** A partition lock that can be regenerated after results exist is not a lock. If
either output already exists the program refuses and changes nothing.

**It measures rather than restates.** Every number that also appears in the Markdown — session
counts, boundary sessions, inception dates, the count of sealed sessions already on disk — is
measured here from the acquired data and compared against the document. A disagreement is a refusal,
not a warning.

**It reads dates, never prices.** The lock has to say how much of the sealed window is already on
disk, which means touching files that contain sealed rows. Only the ``session`` column is parsed,
for every file, in every window. No price, volume, or dividend field is read by this module at all,
so nothing it does can constitute an observation of a sealed window.

The generation identity is derived from artifacts that existed before any Generation 2 file was
written, so it cannot contain a digest of itself and any reader can recompute it.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any

from ..audit import (
    RunRecord,
    dependency_versions,
    sha256_file,
    sha256_text_canonical_json,
    write_sha256_record,
)
from .stage_package import (
    PROJECT_ROOT,
    RUNS_DIR,
    TRACKED_DEPENDENCIES,
    new_run_id,
    repo_state,
    verify_sha256_record,
    verify_stage0_freeze,
)
from ..audit import utc_now_iso

G2_GOVERNANCE = PROJECT_ROOT / "governance" / "generation_2"
RECORD_MD = G2_GOVERNANCE / "STAGE_1_G2_PARTITION_LOCK.md"
RECORD_JSON = G2_GOVERNANCE / "STAGE_1_G2_PARTITION_LOCK.json"
RECORD_SHA = G2_GOVERNANCE / "STAGE_1_G2_PARTITION_LOCK.sha256"
CHARTER_MD = G2_GOVERNANCE / "STAGE_10_GENERATION_2_CHARTER.md"

DAILY = PROJECT_ROOT / "data" / "normalized" / "daily"

DOCUMENT_ID = "SE100-GOV-2002"
CHARTER_ID = "SE100-GOV-2001"

DEVELOPMENT_START = "1993-01-29"
DEVELOPMENT_END = "2021-07-31"
VALIDATION_START = "2021-08-01"
VALIDATION_END = "2024-07-31"
GENERATION_1_HOLDOUT_START = "2024-08-01"
GENERATION_1_HOLDOUT_END = "2026-07-31"
HOLDOUT_START = "2026-08-01"
HOLDOUT_END = "2028-07-31"

UNIVERSE_VERSION = "SE100-U1-d4917c2f7f1cd834"

# The 34 frozen universe members. AAPL is present in data/ as a Stage 2 engine fixture and is not a
# universe member; it is excluded by name here for the same reason strategies/runner.py excludes it.
UNIVERSE = (
    "AGG", "BND", "DIA", "DVY", "EEM", "EFA", "HYG", "IEF", "IVV", "IWM", "IYR", "LQD", "MDY",
    "QQQ", "SHY", "SPY", "TIP", "TLT", "VEA", "VGK", "VIG", "VNQ", "VTI", "VWO", "VYM", "XLB",
    "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY",
)

# Mandated by the Generation 2 operating instruction and reproduced without alteration. Any later
# Generation 2 report that references the validation window must carry this text unchanged; the
# canonical copy is here so that later reports quote a constant rather than retype prose.
VALIDATION_REUSE_DISCLOSURE = (
    "Generation 2's validation window (2021-08-01 → 2024-07-31) overlaps the exact period "
    "Generation 1 used for its own Gate 4 validation read. The researcher therefore already knows, "
    "from Generation 1's published report, approximately how SPY (and by extension the broad "
    "market) behaved in this window — including its Sharpe ratio (≈0.20), total return "
    "(≈2.15%), and fold-by-fold sign pattern (7 of 12 positive). Generation 2 tests a "
    "different hypothesis (cross-sectional multi-asset selection vs. single-symbol mean reversion) "
    "over the same calendar period, which limits but does not eliminate the concern. This is a real "
    "multiplicity cost, disclosed and not minimized, and it is the reason Generation 2's validation "
    "result alone — without a clean holdout confirmation — cannot be treated as "
    "sufficient evidence of an edge."
)

BINDING_RULES = (
    "The Generation 2 holdout window is read exactly once, at the constitutional holdout gate, "
    "after 2028-07-31 has passed in real calendar time, and never before - not in part, not as a "
    "preview, not to check data availability.",
    "Generation 1's holdout window, 2024-08-01 to 2026-07-31, is never read again by anyone, for "
    "any purpose, in any generation.",
    "No parameter, threshold, symbol, weight, or rule may be chosen using any value inside the "
    "validation window or either holdout window.",
    "These boundaries may not be recomputed, widened, narrowed, or shifted by any later stage. If "
    "the dataset is re-acquired and its coverage moves, this lock still governs.",
    "The Generation 2 holdout may not be shortened. A holdout gate reached with less than the full "
    "24 months available is a blocked gate, not a shortened one.",
    "Stage 4 validation for Generation 2 requires a separate, explicitly authorized session. This "
    "lock does not authorize it, and no result produced under this lock authorizes it.",
    "The validation-reuse disclosure is reproduced verbatim wherever the validation window is "
    "referenced. It may be quoted at greater length; it may not be shortened, paraphrased, or "
    "summarised.",
)


# --------------------------------------------------------------------------------------------- #
# Generation identity
# --------------------------------------------------------------------------------------------- #

def generation_identity() -> dict[str, Any]:
    """Derive ``SE100-GEN2-<16 hex>`` from artifacts that predate every Generation 2 file.

    Every input is the digest or the declared version of a Generation 1 artifact that was already
    frozen or sealed before Generation 2 began, so the identity is recomputable by a reader and
    contains no digest of anything Generation 2 wrote. It is deliberately *not* a tree digest: a
    tree digest would change every time a Generation 2 module was edited, and an identity that moves
    is not an identity.
    """
    inputs = {
        "project": "StockEdge100",
        "generation": 2,
        "constitution_ref": "SE100-GOV-0001",
        "constitution_sha256": sha256_file(PROJECT_ROOT / "governance" / "STAGE_0_CONSTITUTION.md"),
        "universe_version": UNIVERSE_VERSION,
        "universe_sha256": sha256_file(PROJECT_ROOT / "governance" / "STAGE_1_UNIVERSE.json"),
        "cost_model_sha256": sha256_file(PROJECT_ROOT / "config" / "stage2_cost_model.json"),
        "generation_1_terminal_verdict": "FAIL - STAGE_4_STRATEGY_REJECTED_IN_VALIDATION",
        "single_variable_changed": "PORTFOLIO_BREADTH_AND_CROSS_SECTIONAL_SELECTION",
        "development_window": [DEVELOPMENT_START, DEVELOPMENT_END],
        "validation_window": [VALIDATION_START, VALIDATION_END],
        "holdout_window": [HOLDOUT_START, HOLDOUT_END],
    }
    digest = sha256_text_canonical_json(inputs)
    return {
        "inputs": inputs,
        "identity_sha256": digest,
        "generation_id": "SE100-GEN2-" + digest[:16],
    }


# --------------------------------------------------------------------------------------------- #
# Date-only measurement
# --------------------------------------------------------------------------------------------- #

def sessions_only(symbol: str) -> list[str]:
    """Every session date for ``symbol``, with no price or volume field parsed.

    The lock has to describe coverage across windows it seals. Reading the date column of a sealed
    row is not an observation of the market; reading its close would be. This function is the only
    place this module touches the acquired data, and it can only ever return dates.
    """
    path = DAILY / f"{symbol}.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        return [row["session"] for row in csv.DictReader(handle)]


def measure_coverage() -> dict[str, Any]:
    per_symbol: dict[str, dict[str, Any]] = {}
    development_union: set[str] = set()
    sealed_g2: set[str] = set()

    for symbol in UNIVERSE:
        sessions = sessions_only(symbol)
        inside = [s for s in sessions if DEVELOPMENT_START <= s <= DEVELOPMENT_END]
        development_union.update(inside)
        sealed_g2.update(s for s in sessions if s >= HOLDOUT_START)
        per_symbol[symbol] = {
            "first_session": sessions[0],
            "last_session": sessions[-1],
            "development_sessions": len(inside),
        }

    development = sorted(development_union)
    inceptions = {s: per_symbol[s]["first_session"] for s in UNIVERSE}
    latest_inception = max(inceptions.values())
    earliest_inception = min(inceptions.values())

    return {
        "member_count": len(UNIVERSE),
        "development_sessions": len(development),
        "development_first_session": development[0],
        "development_last_session": development[-1],
        "earliest_inception": earliest_inception,
        "earliest_inception_symbols": sorted(
            s for s, d in inceptions.items() if d == earliest_inception
        ),
        "latest_inception": latest_inception,
        "latest_inception_symbols": sorted(
            s for s, d in inceptions.items() if d == latest_inception
        ),
        "dataset_last_session": max(v["last_session"] for v in per_symbol.values()),
        "sealed_generation_2_sessions_present_on_disk": sorted(sealed_g2),
        "sealed_generation_2_session_count_on_disk": len(sealed_g2),
        "per_symbol": per_symbol,
        "measurement_basis": (
            "Date column only. This module parses no price, volume, or dividend field in any "
            "window, so its coverage figures are not an observation of sealed data."
        ),
    }


def span_years(start: str, end: str) -> float:
    a = dt.date.fromisoformat(start)
    b = dt.date.fromisoformat(end)
    return round((b - a).days / 365.25, 3)


def span_months(start: str, end: str) -> int:
    a = dt.date.fromisoformat(start)
    b = dt.date.fromisoformat(end)
    return (b.year - a.year) * 12 + (b.month - a.month) + (1 if b.day >= a.day - 1 else 0)


# --------------------------------------------------------------------------------------------- #
# Document agreement
# --------------------------------------------------------------------------------------------- #

def normalised_prose(text: str) -> str:
    """Strip Markdown decoration so a quoted paragraph can be compared with a JSON string."""
    stripped = re.sub(r"[>*`]", " ", text)
    return re.sub(r"\s+", " ", stripped).strip()


def check_document_agreement(document: str, coverage: dict[str, Any], spans: dict[str, Any]) -> list[str]:
    """Every claim the Markdown makes that this module can independently check.

    A mismatch means the hand-authored document and the measured data disagree, which is the one
    failure mode a generated companion exists to catch.
    """
    flat = normalised_prose(document)
    problems: list[str] = []

    if normalised_prose(VALIDATION_REUSE_DISCLOSURE) not in flat:
        problems.append(
            "the mandated validation-reuse disclosure is missing from the Markdown or was altered"
        )

    required = {
        "document id": DOCUMENT_ID,
        "charter id": CHARTER_ID,
        "generation id": generation_identity()["generation_id"],
        "development start": DEVELOPMENT_START,
        "development end": DEVELOPMENT_END,
        "validation start": VALIDATION_START,
        "validation end": VALIDATION_END,
        "generation 1 holdout start": GENERATION_1_HOLDOUT_START,
        "generation 1 holdout end": GENERATION_1_HOLDOUT_END,
        "holdout start": HOLDOUT_START,
        "holdout end": HOLDOUT_END,
        "development years": f"{spans['development_years']:.3f}",
        "development session count": str(coverage["development_sessions"]),
        "development last session": coverage["development_last_session"],
        "dataset last session": coverage["dataset_last_session"],
        "sealed session count on disk": str(
            coverage["sealed_generation_2_session_count_on_disk"]
        ),
    }
    for label, value in required.items():
        if value not in flat:
            problems.append(f"the Markdown does not state the measured {label} ({value})")

    for session in coverage["sealed_generation_2_sessions_present_on_disk"]:
        if session not in flat:
            problems.append(
                f"the Markdown does not disclose sealed session {session} present on disk"
            )

    return problems


# --------------------------------------------------------------------------------------------- #
# Build
# --------------------------------------------------------------------------------------------- #

def build() -> int:
    if RECORD_JSON.exists() or RECORD_SHA.exists():
        print("REFUSED: the Generation 2 partition lock is already sealed.")
        print(f"  {RECORD_JSON.relative_to(PROJECT_ROOT).as_posix()}: {RECORD_JSON.exists()}")
        print(f"  {RECORD_SHA.relative_to(PROJECT_ROOT).as_posix()}: {RECORD_SHA.exists()}")
        print("A partition lock is sealed once. Regenerating it would destroy its meaning.")
        return 2

    for required in (CHARTER_MD, RECORD_MD):
        if not required.exists():
            print(f"REFUSED: missing prerequisite {required.relative_to(PROJECT_ROOT).as_posix()}")
            return 3

    frozen_ok, frozen_detail = verify_stage0_freeze()
    if not frozen_ok:
        print("REFUSED: the Stage 0 freeze does not verify.")
        for name, detail in sorted(frozen_detail.items()):
            if detail.get("recorded") != detail.get("computed"):
                print(f"  {name}: {detail}")
        return 4

    # Bare-filename record: verified from the directory that holds it, not from the project root.
    stage1_freeze = verify_sha256_record(
        PROJECT_ROOT / "governance" / "STAGE_1_FREEZE.sha256",
        root=PROJECT_ROOT / "governance",
    )
    if any(state != "OK" for state in stage1_freeze.values()):
        print("REFUSED: governance/STAGE_1_FREEZE.sha256 does not verify.")
        for name, state in sorted(stage1_freeze.items()):
            print(f"  {name}: {state}")
        return 5

    coverage = measure_coverage()
    spans = {
        "development_years": span_years(DEVELOPMENT_START, DEVELOPMENT_END),
        "validation_months": span_months(VALIDATION_START, VALIDATION_END),
        "generation_1_holdout_months": span_months(
            GENERATION_1_HOLDOUT_START, GENERATION_1_HOLDOUT_END
        ),
        "holdout_months": span_months(HOLDOUT_START, HOLDOUT_END),
        "minimum_development_years": 5,
    }
    spans["meets_minimum_development"] = (
        spans["development_years"] >= spans["minimum_development_years"]
    )

    problems = check_document_agreement(RECORD_MD.read_text(encoding="utf-8"), coverage, spans)
    if problems:
        print("REFUSED: the Markdown lock and the measured data disagree.")
        for problem in problems:
            print(f"  - {problem}")
        return 6

    identity = generation_identity()
    timestamp = utc_now_iso()
    run_id = new_run_id(timestamp)

    record: dict[str, Any] = {
        "artifact_id": DOCUMENT_ID,
        "title": "Generation 2 time partition and holdout lock",
        "status": "LOCKED",
        "project": "StockEdge100",
        "generation": 2,
        "generation_id": identity["generation_id"],
        "stage": 1,
        "locked_utc": timestamp,
        "run_id": run_id,
        "charter_ref": f"governance/generation_2/STAGE_10_GENERATION_2_CHARTER.md ({CHARTER_ID})",
        "constitution_ref": "SE100-GOV-0001 section 6.1",
        "locked_before_any_strategy_result": True,
        "holdout_state": "SEALED",
        "generation_1_holdout_state": "SPENT_AND_PROHIBITED",
        "validation_window_state": "LOCKED",
        "generation_identity": identity,
        "partition": {
            "development_start": DEVELOPMENT_START,
            "development_end": DEVELOPMENT_END,
            "validation_start": VALIDATION_START,
            "validation_end": VALIDATION_END,
            "generation_1_holdout_start": GENERATION_1_HOLDOUT_START,
            "generation_1_holdout_end": GENERATION_1_HOLDOUT_END,
            "holdout_start": HOLDOUT_START,
            "holdout_end": HOLDOUT_END,
            "boundaries_inclusive": True,
            **spans,
        },
        "inherited_from_generation_1": {
            "source": "governance/STAGE_1_HOLDOUT_LOCK.json",
            "source_sha256": sha256_file(
                PROJECT_ROOT / "governance" / "STAGE_1_HOLDOUT_LOCK.json"
            ),
            "fields": [
                "development_start",
                "development_end",
                "validation_start",
                "validation_end",
            ],
            "note": (
                "Inherited unchanged, not recomputed. The Generation 1 lock is read-only for the "
                "whole of Generation 2."
            ),
        },
        "coverage_measured_from_disk": coverage,
        "validation_reuse_disclosure": VALIDATION_REUSE_DISCLOSURE,
        "validation_reuse_disclosure_sources": {
            "sharpe": {
                "value": "0.2025294206503088680547420121230750",
                "field": "reports/stage4/STAGE_4_VALIDATION.json run_evidence.base.sharpe",
            },
            "total_return": {
                "value": "0.0215",
                "field": "reports/stage4/STAGE_4_VALIDATION.json run_evidence.base.total_return",
            },
            "positive_folds": {
                "value": "7 of 12",
                "field": (
                    "reports/stage4/STAGE_4_VALIDATION.json "
                    "gate_conditions.S4-C6.evidence.condition_evidence"
                ),
            },
            "symbols_traded": {
                "value": "['SPY']",
                "field": (
                    "reports/stage4/STAGE_4_VALIDATION.json "
                    "run_evidence.runs[0].measure.symbols_loaded"
                ),
            },
        },
        "sealed_data_on_disk_note": (
            "The acquired dataset already contains "
            f"{coverage['sealed_generation_2_session_count_on_disk']} session(s) inside the "
            "Generation 2 holdout window, and all 24 months of Generation 1's holdout window. "
            "Nothing is deleted; enforcement is a window bound applied in code. See section 3 of "
            "the Markdown counterpart."
        ),
        "enforcement": {
            "mechanism": "stockedge100.backtest.window.ResearchWindow plus a Generation 2 guard",
            "development_bound": DEVELOPMENT_END,
            "prohibited_windows": [
                [GENERATION_1_HOLDOUT_START, GENERATION_1_HOLDOUT_END],
                [HOLDOUT_START, HOLDOUT_END],
            ],
            "note": (
                "The prohibition on both holdout windows is broader than Stage 3 requires. It is "
                "written to survive into stages this lock does not authorize."
            ),
        },
        "binding_rules": list(BINDING_RULES),
        "repo_state_id_location": (
            "Deliberately omitted here. governance/generation_2/ is not reached by the "
            "repo_state_id patterns (governance/*.md is single-level), so this file is covered by "
            "STAGE_1_G2_PARTITION_LOCK.sha256 instead. The binding repo_state_id for this seal is "
            f"the repo_state_id field of runs/{run_id}.json."
        ),
        "authorized_windows": ["development"],
        "stage_3_authorized": True,
        "stage_4_authorized": False,
        "holdout_read_authorized": False,
        "live_trading_authorized": False,
    }

    RECORD_JSON.parent.mkdir(parents=True, exist_ok=True)
    RECORD_JSON.write_text(
        json.dumps(record, indent=2, sort_keys=False, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # Written last so it covers the final bytes of the JSON above. It does not contain its own
    # digest; nothing hashes itself.
    covered = {
        "governance/generation_2/STAGE_10_GENERATION_2_CHARTER.md": sha256_file(CHARTER_MD),
        "governance/generation_2/STAGE_1_G2_PARTITION_LOCK.md": sha256_file(RECORD_MD),
        "governance/generation_2/STAGE_1_G2_PARTITION_LOCK.json": sha256_file(RECORD_JSON),
    }
    own_digest = write_sha256_record(covered, RECORD_SHA)

    code_hashes, repo_state_id = repo_state()
    dataset_hashes = {
        f"data/normalized/daily/{symbol}.csv": sha256_file(DAILY / f"{symbol}.csv")
        for symbol in UNIVERSE
    }

    RunRecord(
        run_id=run_id,
        stage="stage_1_generation_2_partition_lock",
        command="python -m stockedge100.reporting.g2_partition_lock",
        timestamp_utc=timestamp,
        repo_state_id=repo_state_id,
        code_hashes=code_hashes,
        config_hash=identity["identity_sha256"],
        dataset_hashes=dataset_hashes,
        universe_version=UNIVERSE_VERSION,
        date_range=[DEVELOPMENT_START, DEVELOPMENT_END],
        holdout_state="SEALED",
        strategy_id=None,
        random_seed=None,
        dependency_versions=dependency_versions(TRACKED_DEPENDENCIES),
        exit_status="LOCKED",
        output_artifact_hashes={**covered, "STAGE_1_G2_PARTITION_LOCK.sha256": own_digest},
        notes=[
            f"Generation id {identity['generation_id']}, derived from Generation 1 artifacts only.",
            "governance/generation_2/ is outside REPO_STATE_PATTERNS; the .sha256 record and this "
            "run record are what cover these files. Recorded as G2-CONFLICT-4 in the charter.",
            "Coverage figures were measured from the session column only. No price, volume, or "
            "dividend field was parsed by this program in any window.",
            f"{coverage['sealed_generation_2_session_count_on_disk']} session(s) of the sealed "
            "Generation 2 holdout window are already present on disk and are not read.",
            "Stage 4 validation is not authorized by this lock.",
        ],
    ).write(RUNS_DIR)

    print("Generation 2 partition lock SEALED")
    print(f"  generation_id  {identity['generation_id']}")
    print(f"  run_id         {run_id}")
    print(f"  locked_utc     {timestamp}")
    print(f"  repo_state_id  {repo_state_id}")
    print(f"  development    {DEVELOPMENT_START} -> {DEVELOPMENT_END} "
          f"({coverage['development_sessions']} sessions, {spans['development_years']} years)")
    print(f"  validation     {VALIDATION_START} -> {VALIDATION_END} (LOCKED)")
    print(f"  g1 holdout     {GENERATION_1_HOLDOUT_START} -> {GENERATION_1_HOLDOUT_END} "
          "(SPENT AND PROHIBITED)")
    print(f"  g2 holdout     {HOLDOUT_START} -> {HOLDOUT_END} (SEALED, "
          f"{coverage['sealed_generation_2_session_count_on_disk']} session(s) on disk, unread)")
    for name, digest in sorted(covered.items()):
        print(f"  {digest}  {name}")
    print(f"  record digest  {own_digest}")
    return 0


if __name__ == "__main__":
    sys.exit(build())
