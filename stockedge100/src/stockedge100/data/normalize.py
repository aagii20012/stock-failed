"""Normalize raw provider payloads into the pre-registered daily schema.

Run from ``stockedge100/``::

    python -m stockedge100.data.normalize

Two things here are worth reading carefully.

**The session key.** The provider returns a timezone-aware instant per bar. A daily bar is not an
instant; it is a trading session. The instant is converted to ``America/New_York`` and reduced to its
calendar date, and the local clock time is checked to be midnight on every row rather than assumed —
a bar landing at 01:00 or 23:00 local is the signature of a timezone bug, and it is recorded, not
smoothed over.

**Adjustment semantics are measured, not assumed.** ``stage1_data_source.json`` pre-registered
``determination: MEASURED_NOT_ASSUMED``. The normalizer therefore establishes, from the reference
fixture's known splits, whether the provider's *unadjusted* OHLC series is already retroactively
split-adjusted, and records the measurement. Every downstream split reconciliation derives its
expectation from that measured answer instead of hardcoding a belief about the vendor.
"""

from __future__ import annotations

import json
import sys
from typing import Any

import pandas as pd

from stockedge100.audit import sha256_file, utc_now_iso
from stockedge100.data.acquire import MANIFEST_PATH as RAW_MANIFEST_PATH
from stockedge100.data.acquire import RAW_DIR
from stockedge100.data.config import PROJECT_ROOT, load_stage1_config

NORMALIZED_DIR = PROJECT_ROOT / "data" / "normalized" / "daily"
NORMALIZED_MANIFEST_PATH = PROJECT_ROOT / "data" / "manifests" / "STAGE_1_NORMALIZED_MANIFEST.json"

SESSION_TZ = "America/New_York"
COLUMNS = ["session", "open", "high", "low", "close", "adj_close", "volume", "dividend", "split_ratio"]
FLOAT_FORMAT = "%.10f"

RAW_TO_NORMALIZED = {
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Adj Close": "adj_close",
    "Volume": "volume",
    "Dividends": "dividend",
    "Stock Splits": "split_ratio",
}


def read_raw(symbol: str) -> pd.DataFrame:
    return pd.read_csv(RAW_DIR / f"{symbol}.csv")


def normalize_frame(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Raw provider frame -> the pre-registered schema, plus timezone observations."""
    instants = pd.to_datetime(raw["Date"], utc=True, format="ISO8601")
    local = instants.dt.tz_convert(SESSION_TZ)

    midnight = (local.dt.hour == 0) & (local.dt.minute == 0) & (local.dt.second == 0)
    offsets = sorted({str(v) for v in local.dt.strftime("%z")})

    out = pd.DataFrame({"session": local.dt.strftime("%Y-%m-%d")})
    for source, target in RAW_TO_NORMALIZED.items():
        out[target] = raw[source]

    out["volume"] = out["volume"].fillna(0).astype("int64")
    out = out[COLUMNS].sort_values("session", kind="mergesort").reset_index(drop=True)

    observations = {
        "rows_in": int(len(raw)),
        "rows_out": int(len(out)),
        "local_midnight_rows": int(midnight.sum()),
        "non_midnight_rows": int((~midnight).sum()),
        "non_midnight_examples": [
            str(v) for v in local[~midnight].head(5).astype(str).tolist()
        ],
        "distinct_utc_offsets": offsets,
        "capital_gains_column_present": "Capital Gains" in raw.columns,
        "capital_gains_total": (
            float(raw["Capital Gains"].abs().sum()) if "Capital Gains" in raw.columns else 0.0
        ),
    }
    return out, observations


def write_normalized(symbol: str, frame: pd.DataFrame) -> dict[str, Any]:
    NORMALIZED_DIR.mkdir(parents=True, exist_ok=True)
    path = NORMALIZED_DIR / f"{symbol}.csv"
    payload = frame.to_csv(index=False, float_format=FLOAT_FORMAT, lineterminator="\n")
    path.write_text(payload, encoding="utf-8", newline="")
    return {
        "path": path.relative_to(PROJECT_ROOT).as_posix(),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def measure_adjustment_semantics(config, frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """Decide, from evidence, whether the provider's OHLC is already split-adjusted.

    The test is a known large split in the reference fixture. If the unadjusted close-to-close step
    across the split date is close to ``1 / ratio``, the series is as-traded. If it is an ordinary
    daily move, the vendor has already back-adjusted the whole history.
    """
    spec = config.universe_spec["reference_symbols"]
    probes: list[dict[str, Any]] = []

    for entry in spec["symbols"]:
        symbol = entry["symbol"]
        frame = frames.get(symbol)
        if frame is None:
            continue
        for action in entry.get("expected_actions", []):
            if action.get("type") != "split":
                continue
            session = action["session"]
            ratio = float(action["ratio"])
            index = frame.index[frame["session"] == session]
            if len(index) != 1 or index[0] == 0:
                probes.append({"symbol": symbol, "session": session, "status": "SESSION_NOT_FOUND"})
                continue
            i = int(index[0])
            close_ratio = float(frame.at[i, "close"]) / float(frame.at[i - 1, "close"])
            adj_ratio = float(frame.at[i, "adj_close"]) / float(frame.at[i - 1, "adj_close"])
            probes.append(
                {
                    "symbol": symbol,
                    "session": session,
                    "declared_split_ratio": ratio,
                    "recorded_split_ratio": float(frame.at[i, "split_ratio"]),
                    "unadjusted_close_step": round(close_ratio, 8),
                    "adjusted_close_step": round(adj_ratio, 8),
                    "step_if_series_were_as_traded": round(1.0 / ratio, 8),
                    "ohlc_appears_split_adjusted": abs(close_ratio - 1.0) < 0.25,
                }
            )

    usable = [p for p in probes if "ohlc_appears_split_adjusted" in p]
    votes = {p["ohlc_appears_split_adjusted"] for p in usable}
    if not usable:
        determination, adjusted = "UNDETERMINED_NO_FIXTURE", None
    elif len(votes) == 1:
        adjusted = votes.pop()
        determination = "MEASURED"
    else:
        determination, adjusted = "INCONSISTENT_ACROSS_FIXTURES", None

    return {
        "determination": determination,
        "ohlc_split_adjusted": adjusted,
        "adj_close_split_and_dividend_adjusted": adjusted is not None,
        "method": (
            "close-to-close step across a known split in the reference fixture, compared against "
            "the 1/ratio step an as-traded series would show"
        ),
        "probes": probes,
        "consequence_for_split_reconciliation": (
            "expected adjustment-factor step at a split is 1.0 (splits are already in both series)"
            if adjusted
            else "expected adjustment-factor step at a split is 1/ratio"
        ),
        "constitution_6_note": (
            "A truly as-traded (split-unadjusted) price series is not obtainable from this provider "
            "when OHLC is already back-adjusted. Constitution section 6 is satisfied by retaining "
            "the immutable raw payload plus a measured, documented transformation between the two "
            "retained series, and the unavailability of as-traded price levels is recorded as a "
            "limitation rather than papered over."
        ),
    }


def normalize() -> int:
    config = load_stage1_config()
    if not RAW_MANIFEST_PATH.is_file():
        print("raw manifest missing; run stockedge100.data.acquire first", file=sys.stderr)
        return 2
    raw_manifest = json.loads(RAW_MANIFEST_PATH.read_text(encoding="utf-8"))

    symbols = [s for s, e in raw_manifest["symbols"].items() if e["status"] != "ACQUISITION_FAILED"]
    frames: dict[str, pd.DataFrame] = {}
    entries: dict[str, dict[str, Any]] = {}

    for symbol in symbols:
        raw_entry = raw_manifest["symbols"][symbol]
        raw_path = PROJECT_ROOT / raw_entry["path"]
        if sha256_file(raw_path) != raw_entry["sha256"]:
            print(f"  RAW DIGEST MISMATCH {symbol}", file=sys.stderr)
            entries[symbol] = {"status": "RAW_DIGEST_MISMATCH", "role": raw_entry["role"]}
            continue

        frame, observations = normalize_frame(read_raw(symbol))
        frames[symbol] = frame
        written = write_normalized(symbol, frame)
        entries[symbol] = {
            "role": raw_entry["role"],
            "status": "NORMALIZED",
            "raw_sha256": raw_entry["sha256"],
            "rows": int(len(frame)),
            "first_session": frame["session"].iloc[0],
            "last_session": frame["session"].iloc[-1],
            "dividend_events": int((frame["dividend"] != 0).sum()),
            "split_events": int((frame["split_ratio"] != 0).sum()),
            "observations": observations,
            **written,
        }
        print(f"  {symbol:6s} rows={len(frame):5d}  {frame['session'].iloc[0]}..{frame['session'].iloc[-1]}")

    semantics = measure_adjustment_semantics(config, frames)

    manifest = {
        "manifest_id": "SE100-DATA-1002",
        "manifest_type": "NORMALIZED",
        "project": "StockEdge100",
        "generation": 1,
        "stage": 1,
        "generated_utc": utc_now_iso(),
        "source_manifest": {
            "path": RAW_MANIFEST_PATH.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": sha256_file(RAW_MANIFEST_PATH),
        },
        "preregistration": {
            "declared_utc": config.declared_utc,
            "config_sha256": config.config_hash,
        },
        "schema": {
            "columns": COLUMNS,
            "session_key": "calendar date of the provider instant expressed in America/New_York",
            "session_key_timezone_naive": True,
            "float_format": FLOAT_FORMAT,
            "line_terminator": "\\n",
            "storage_format": "csv",
            "storage_format_note": (
                "pyproject declares an optional parquet path, but pyarrow is not installed in this "
                "environment, so CSV is used. Recorded as a deviation, not left implicit."
            ),
        },
        "adjustment_semantics": semantics,
        "symbol_count": len(entries),
        "symbols": entries,
    }
    NORMALIZED_MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    NORMALIZED_MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print()
    print(f"normalized      {len(frames)} / {len(symbols)}")
    print(f"ohlc split-adjusted: {semantics['ohlc_split_adjusted']} ({semantics['determination']})")
    print(f"manifest        {NORMALIZED_MANIFEST_PATH.relative_to(PROJECT_ROOT).as_posix()}")
    return 0 if len(frames) == len(symbols) else 1


if __name__ == "__main__":
    raise SystemExit(normalize())
