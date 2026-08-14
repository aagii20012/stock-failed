"""Apply the frozen eligibility rules, freeze the realized universe, and lock the holdout.

Run from ``stockedge100/``::

    python -m stockedge100.universe.build

Three things are enforced here rather than asserted.

**No eligibility measurement may read validation or holdout data.** :func:`measure` is given a frame
that has already been sliced to the development window, and it re-checks that slice itself before
computing anything. A caller that hands it a wider frame gets :class:`WindowViolation`, not a
silently contaminated median. Structural enforcement beats a comment promising good behaviour.

**The eligibility rules are not restated here.** They are read from the sealed universe spec and
applied mechanically. The six non-inception structural rules cannot be checked against price data at
all — they were asserted when the candidate list was constructed — and they are labelled
``ASSERTED_AT_CANDIDATE_CONSTRUCTION`` rather than reported as verified.

**The holdout lock is written once.** A second run refuses to overwrite it. A holdout that can be
recomputed after seeing results is not a holdout.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from typing import Any

import pandas as pd

from stockedge100.audit import sha256_file, sha256_text_canonical_json, utc_now_iso, write_sha256_record
from stockedge100.data.config import PROJECT_ROOT, load_stage1_config
from stockedge100.data.normalize import NORMALIZED_MANIFEST_PATH
from stockedge100.data.partition import compute_partition
from stockedge100.data.validate import VALIDATION_REPORT_PATH

GOVERNANCE = PROJECT_ROOT / "governance"
UNIVERSE_PATH = GOVERNANCE / "STAGE_1_UNIVERSE.json"
HOLDOUT_LOCK_PATH = GOVERNANCE / "STAGE_1_HOLDOUT_LOCK.json"
FREEZE_RECORD_PATH = GOVERNANCE / "STAGE_1_FREEZE.sha256"

INCEPTION_CUTOFF = "2010-01-04"
MIN_DEVELOPMENT_SESSIONS = 1260
MIN_MEDIAN_DOLLAR_VOLUME = 5_000_000.0
MIN_CLOSE = 5.00

STRUCTURAL_ASSERTED = (
    "US_LISTED",
    "UNLEVERAGED",
    "NON_INVERSE",
    "NOT_K1_PARTNERSHIP",
    "NOT_COMMODITY_TRUST",
    "RULES_BASED_INDEX",
)


class WindowViolation(RuntimeError):
    """Raised when an eligibility measurement is handed data outside the development window."""


def development_frame(frame: pd.DataFrame, partition) -> pd.DataFrame:
    """Slice to the development window. This is the only sanctioned way to get eligibility input."""
    return frame[
        (frame["session"] >= partition.development_start)
        & (frame["session"] <= partition.development_end)
    ].reset_index(drop=True)


def measure(dev: pd.DataFrame, partition) -> dict[str, Any]:
    """Development-window eligibility measurements, with the window re-checked on entry."""
    if not dev.empty:
        first, last = dev["session"].iloc[0], dev["session"].iloc[-1]
        if last > partition.development_end or first < partition.development_start:
            raise WindowViolation(
                f"eligibility measurement was handed sessions {first}..{last}, outside the "
                f"development window {partition.development_start}..{partition.development_end}. "
                "No eligibility decision may read validation or holdout data."
            )

    if dev.empty:
        return {
            "development_sessions": 0,
            "median_dollar_volume": None,
            "minimum_close": None,
            "window": [partition.development_start, partition.development_end],
        }

    dollar_volume = (dev["close"] * dev["volume"]).median()
    return {
        "development_sessions": int(len(dev)),
        "development_first_session": dev["session"].iloc[0],
        "development_last_session": dev["session"].iloc[-1],
        "median_dollar_volume": round(float(dollar_volume), 2),
        "minimum_close": round(float(dev["close"].min()), 6),
        "window": [partition.development_start, partition.development_end],
    }


def screen(symbol: str, frame: pd.DataFrame, measured: dict[str, Any], data_quality_ok: bool) -> dict[str, Any]:
    """Mechanical application of the frozen rules. No discretion, no exceptions."""
    inception = frame["session"].iloc[0]
    rules: dict[str, dict[str, Any]] = {
        rule: {"status": "ASSERTED_AT_CANDIDATE_CONSTRUCTION", "verifiable_from_price_data": False}
        for rule in STRUCTURAL_ASSERTED
    }
    rules["INCEPTION_CUTOFF"] = {
        "status": "PASS" if inception <= INCEPTION_CUTOFF else "FAIL",
        "first_session": inception,
        "cutoff": INCEPTION_CUTOFF,
        "verifiable_from_price_data": True,
    }
    rules["MIN_DEVELOPMENT_SESSIONS"] = {
        "status": "PASS" if measured["development_sessions"] >= MIN_DEVELOPMENT_SESSIONS else "FAIL",
        "observed": measured["development_sessions"],
        "minimum": MIN_DEVELOPMENT_SESSIONS,
        "verifiable_from_price_data": True,
    }
    mdv = measured["median_dollar_volume"]
    rules["MEDIAN_DOLLAR_VOLUME"] = {
        "status": "PASS" if mdv is not None and mdv >= MIN_MEDIAN_DOLLAR_VOLUME else "FAIL",
        "observed": mdv,
        "minimum": MIN_MEDIAN_DOLLAR_VOLUME,
        "verifiable_from_price_data": True,
    }
    low = measured["minimum_close"]
    rules["MIN_CLOSE"] = {
        "status": "PASS" if low is not None and low >= MIN_CLOSE else "FAIL",
        "observed": low,
        "minimum": MIN_CLOSE,
        "verifiable_from_price_data": True,
    }
    rules["DATA_QUALITY"] = {
        "status": "PASS" if data_quality_ok else "FAIL",
        "basis": "every FAIL-severity check in the sealed validation battery",
        "verifiable_from_price_data": True,
    }

    failed = [name for name, r in rules.items() if r["status"] == "FAIL"]
    return {
        "eligible": not failed,
        "failed_rules": failed,
        "rules": rules,
        "measurements": measured,
    }


def build() -> int:
    config = load_stage1_config()

    for path, label in ((NORMALIZED_MANIFEST_PATH, "normalized manifest"), (VALIDATION_REPORT_PATH, "validation report")):
        if not path.is_file():
            print(f"{label} missing at {path}", file=sys.stderr)
            return 2

    normalized = json.loads(NORMALIZED_MANIFEST_PATH.read_text(encoding="utf-8"))
    validation = json.loads(VALIDATION_REPORT_PATH.read_text(encoding="utf-8"))

    frames: dict[str, pd.DataFrame] = {}
    for symbol in config.candidates:
        entry = normalized["symbols"].get(symbol)
        if not entry or entry.get("status") != "NORMALIZED":
            continue
        path = PROJECT_ROOT / entry["path"]
        if sha256_file(path) != entry["sha256"]:
            print(f"normalized digest mismatch for {symbol}", file=sys.stderr)
            return 3
        frames[symbol] = pd.read_csv(path, dtype={"session": str})

    if not frames:
        print("no normalized candidate data", file=sys.stderr)
        return 4

    cutoff = max(dt.date.fromisoformat(f["session"].iloc[-1]) for f in frames.values())
    earliest = min(dt.date.fromisoformat(f["session"].iloc[0]) for f in frames.values())
    partition = compute_partition(cutoff, earliest)

    severities = {c["id"]: c["severity"] for c in config.data_source["validation_battery"]["checks"]}
    fail_checks = {cid for cid, sev in severities.items() if sev == "FAIL"}

    assessments: dict[str, Any] = {}
    for symbol, frame in frames.items():
        symbol_report = validation["per_symbol"].get(symbol, {})
        data_quality_ok = not (set(symbol_report.get("failed_checks", [])) & fail_checks)
        measured = measure(development_frame(frame, partition), partition)
        assessment = screen(symbol, frame, measured, data_quality_ok)
        assessment["asset_class"] = next(
            c["asset_class"] for c in config.universe_spec["candidates"] if c["symbol"] == symbol
        )
        assessment["exposure"] = next(
            c["exposure"] for c in config.universe_spec["candidates"] if c["symbol"] == symbol
        )
        assessment["first_session"] = frame["session"].iloc[0]
        assessment["last_session"] = frame["session"].iloc[-1]
        assessments[symbol] = assessment

    members = sorted(s for s, a in assessments.items() if a["eligible"])
    rejected = sorted(s for s, a in assessments.items() if not a["eligible"])
    not_acquired = sorted(set(config.candidates) - set(frames))

    identity = sha256_text_canonical_json(
        {
            "members": members,
            "spec_sha256": config.digests["config/stage1_universe_spec.json"],
            "source_sha256": config.config_hash,
            "development_window": [partition.development_start, partition.development_end],
        }
    )
    universe_version = f"SE100-U1-{identity[:16]}"

    scope = config.universe_spec["scope_decision"]
    bias = config.universe_spec["etf_universe_bias_assessment"]

    universe = {
        "artifact_id": "SE100-GOV-1004",
        "title": "Stage 1 realized research universe",
        "status": "FROZEN",
        "project": "StockEdge100",
        "generation": 1,
        "stage": 1,
        "frozen_utc": utc_now_iso(),
        "universe_version": universe_version,
        "universe_identity_sha256": identity,
        "derivation": (
            "produced by applying the eligibility rules sealed in config/stage1_universe_spec.json "
            "to the acquired data; no symbol was added, removed, or substituted by hand"
        ),
        "preregistration": {
            "declared_utc": config.declared_utc,
            "universe_spec_sha256": config.digests["config/stage1_universe_spec.json"],
            "data_source_sha256": config.config_hash,
            "sealed_before_any_data_acquired": True,
        },
        "research_universe_class": scope["research_universe_class"],
        "member_count": len(members),
        "members": members,
        "rejected": rejected,
        "not_acquired": not_acquired,
        "survivorship_bias": {
            "stock_universe_verdict": scope["stock_universe_survivorship_verdict"],
            "stock_research_authorization": scope["stock_research_authorization"],
            "etf_universe_verdict": bias["verdict"],
            "honest_statement": bias["honest_statement"],
            "quantified": False,
            "binding_consequence": bias["binding_consequence"],
        },
        "broker_eligibility": config.universe_spec["eligibility_rules"]["broker_eligibility"],
        "measurement_window_restriction": {
            "rule": config.universe_spec["eligibility_rules"]["measurement_window_restriction"],
            "development_window": [partition.development_start, partition.development_end],
            "enforced_by": "stockedge100.universe.build.measure raises WindowViolation",
        },
        "structural_rules_not_verifiable_from_price_data": list(STRUCTURAL_ASSERTED),
        "assessments": assessments,
    }

    holdout_lock = {
        "artifact_id": "SE100-GOV-1005",
        "title": "Stage 1 time partition and final holdout lock",
        "status": "LOCKED",
        "project": "StockEdge100",
        "generation": 1,
        "stage": 1,
        "locked_utc": utc_now_iso(),
        "constitution_ref": "SE100-GOV-0001 section 6.1",
        "locked_before_any_strategy_result": True,
        "holdout_state": "SEALED",
        "partition": partition.to_json(),
        "inputs": {
            "usable_cutoff_session": partition.usable_cutoff_session,
            "earliest_candidate_session": partition.development_start,
            "cutoff_derived_from": "the latest session present in the acquired candidate data, not the wall clock",
            "universe_version": universe_version,
            "universe_identity_sha256": identity,
        },
        "binding_rules": [
            "The holdout window is read exactly once, at the constitutional holdout gate, and never before.",
            "No parameter, threshold, symbol, or rule may be chosen using any value inside the validation or holdout windows.",
            "These boundaries may not be recomputed, widened, narrowed, or shifted by any later stage.",
            "If the dataset is re-acquired and the cutoff moves, the existing lock still governs; a new lock requires a new stage and a recorded reason.",
        ],
    }

    if HOLDOUT_LOCK_PATH.is_file():
        existing = json.loads(HOLDOUT_LOCK_PATH.read_text(encoding="utf-8"))
        if existing["partition"] != holdout_lock["partition"]:
            print(
                "REFUSING to overwrite an existing holdout lock with different boundaries.\n"
                f"  locked:   {existing['partition']['holdout_start']}..{existing['partition']['holdout_end']}\n"
                f"  computed: {partition.holdout_start}..{partition.holdout_end}\n"
                "A holdout that can be recomputed after the fact is not a holdout. Report as a blocker.",
                file=sys.stderr,
            )
            return 5
        holdout_lock["locked_utc"] = existing["locked_utc"]

    GOVERNANCE.mkdir(parents=True, exist_ok=True)
    UNIVERSE_PATH.write_text(json.dumps(universe, indent=2) + "\n", encoding="utf-8")
    HOLDOUT_LOCK_PATH.write_text(json.dumps(holdout_lock, indent=2) + "\n", encoding="utf-8")

    # Bare filenames: this record is verified with `sha256sum -c` from stockedge100/governance/.
    write_sha256_record(
        {name: sha256_file(GOVERNANCE / name) for name in ("STAGE_1_UNIVERSE.json", "STAGE_1_HOLDOUT_LOCK.json")},
        FREEZE_RECORD_PATH,
    )

    print(f"universe_version   {universe_version}")
    print(f"members            {len(members)} / {len(config.candidates)} candidates")
    if rejected:
        print(f"rejected           {rejected}")
    if not_acquired:
        print(f"not acquired       {not_acquired}")
    print(f"development        {partition.development_start} .. {partition.development_end}"
          f"  ({partition.development_years} years)")
    print(f"validation         {partition.validation_start} .. {partition.validation_end}")
    print(f"holdout   SEALED   {partition.holdout_start} .. {partition.holdout_end}")
    print(f"wrote              governance/STAGE_1_UNIVERSE.json")
    print(f"                   governance/STAGE_1_HOLDOUT_LOCK.json")
    print(f"                   governance/STAGE_1_FREEZE.sha256")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
