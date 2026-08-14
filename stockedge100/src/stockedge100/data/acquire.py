"""Acquire raw daily bars under the sealed Stage 1 protocol.

Run from ``stockedge100/``::

    python -m stockedge100.data.acquire

Behaviour that is not negotiable, because it is pre-registered:

* the sealed configuration is verified before the first request; altered rules abort the run;
* one symbol per request, sequential, with the declared spacing and backoff;
* raw payloads are **write-once**. An existing file is never overwritten. If the provider now
  returns different bytes, the original is kept and the new payload is quarantined as
  ``PROVIDER_REVISION`` — a silently updated history is exactly the failure mode immutable raw
  storage exists to catch;
* reference symbols are truncated to the development window declared in the universe spec, so a
  data-quality fixture can never touch validation or holdout data.

No credential is read. No order of any kind is placed.
"""

from __future__ import annotations

import json
import sys
import time
from typing import Any

from stockedge100.audit import sha256_bytes, sha256_file, utc_now_iso
from stockedge100.data.config import PROJECT_ROOT, load_stage1_config

RAW_DIR = PROJECT_ROOT / "data" / "raw" / "yahoo"
QUARANTINE_DIR = PROJECT_ROOT / "data" / "quarantine"
MANIFEST_PATH = PROJECT_ROOT / "data" / "manifests" / "STAGE_1_RAW_MANIFEST.json"

LICENSE_NOTE = (
    "Yahoo Finance data, personal and non-commercial use only, no redistribution. "
    "Stored locally, git-ignored, never committed or published."
)


def _serialize(frame) -> bytes:
    """Serialize the provider frame without altering a single value.

    ``to_csv`` with no float formatting writes pandas' full round-trip repr, so the bytes are a
    lossless record of what the client returned and are reproducible from the same input.
    """
    return frame.to_csv(lineterminator="\n").encode("utf-8")


def fetch_one(symbol: str, params: dict[str, Any], window: tuple[str, str] | None):
    """One symbol, honouring the pre-registered retry and backoff policy."""
    import yfinance as yf

    attempts = int(params["per_symbol_attempts"])
    backoff = list(params["backoff_seconds"])
    request = dict(params["request_parameters"])
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            ticker = yf.Ticker(symbol)
            kwargs: dict[str, Any] = dict(
                interval=request["interval"],
                auto_adjust=request["auto_adjust"],
                back_adjust=request["back_adjust"],
                actions=request["actions"],
                repair=request["repair"],
                rounding=request["rounding"],
                prepost=request["prepost"],
                timeout=request["timeout_seconds"],
                raise_errors=True,
            )
            if window is None:
                kwargs["period"] = "max"
            else:
                kwargs["start"], kwargs["end"] = window
            frame = ticker.history(**kwargs)
            if frame is None or frame.empty:
                raise RuntimeError("provider returned an empty frame")
            return frame
        except Exception as exc:  # noqa: BLE001 - the policy is to retry then record, not to guess
            last_error = exc
            if attempt < attempts:
                time.sleep(backoff[min(attempt - 1, len(backoff) - 1)])

    raise RuntimeError(f"{symbol}: acquisition failed after {attempts} attempts: {last_error}")


def acquire() -> int:
    config = load_stage1_config()
    source = config.data_source
    protocol = source["acquisition_protocol"]
    fallback = source["provider_decision"]["fallback_policy"]

    params = {
        "per_symbol_attempts": fallback["per_symbol_attempts"],
        "backoff_seconds": fallback["backoff_seconds"],
        "request_parameters": dict(protocol["request_parameters"], interval=protocol["interval"]),
    }

    spacing = 1.0
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)

    reference = config.universe_spec["reference_symbols"]
    ref_window = (reference["session_range_limit"]["start"], reference["session_range_limit"]["end"])
    ref_symbols = set(config.reference_symbols)

    targets = [(sym, None) for sym in config.candidates]
    targets += [(sym, ref_window) for sym in config.reference_symbols]

    import yfinance as yf

    started = utc_now_iso()
    entries: dict[str, dict[str, Any]] = {}
    failures: list[str] = []
    revisions: list[str] = []

    for index, (symbol, window) in enumerate(targets):
        target = RAW_DIR / f"{symbol}.csv"
        role = "reference" if symbol in ref_symbols else "candidate"

        if index:
            time.sleep(spacing)

        try:
            frame = fetch_one(symbol, params, window)
        except Exception as exc:  # noqa: BLE001
            print(f"  FAIL   {symbol:6s} {exc}", file=sys.stderr)
            failures.append(symbol)
            entries[symbol] = {
                "role": role,
                "status": "ACQUISITION_FAILED",
                "error": str(exc)[:400],
                "retrieved_utc": utc_now_iso(),
            }
            continue

        payload = _serialize(frame)
        digest = sha256_bytes(payload)
        status = "WRITTEN"

        if target.exists():
            existing = sha256_file(target)
            if existing == digest:
                status = "UNCHANGED_EXISTING_PRESERVED"
            else:
                status = "PROVIDER_REVISION_QUARANTINED"
                stamp = utc_now_iso().replace(":", "").replace("-", "")
                quarantined = QUARANTINE_DIR / f"{symbol}.{stamp}.provider_revision.csv"
                quarantined.write_bytes(payload)
                (QUARANTINE_DIR / f"{symbol}.{stamp}.provider_revision.json").write_text(
                    json.dumps(
                        {
                            "anomaly": "PROVIDER_REVISION",
                            "symbol": symbol,
                            "detected_utc": utc_now_iso(),
                            "preserved_original_sha256": existing,
                            "new_payload_sha256": digest,
                            "action": "original kept, new payload quarantined, nothing overwritten",
                            "explanation_required": True,
                        },
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                revisions.append(symbol)
                digest = existing
        else:
            target.write_bytes(payload)

        sessions = [str(ts)[:10] for ts in frame.index]
        entries[symbol] = {
            "role": role,
            "status": status,
            "path": target.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": digest,
            "bytes": target.stat().st_size,
            "rows": int(len(frame)),
            "first_session": sessions[0] if sessions else None,
            "last_session": sessions[-1] if sessions else None,
            "columns": [str(c) for c in frame.columns],
            "source_timezone": str(getattr(frame.index, "tz", None)),
            "requested_window": list(window) if window else "max",
            "retrieved_utc": utc_now_iso(),
        }
        print(f"  {status:30s} {symbol:6s} rows={len(frame):5d}  {sessions[0]}..{sessions[-1]}")

    candidate_failures = [s for s in failures if s not in ref_symbols]
    fail_fraction = len(candidate_failures) / max(len(config.candidates), 1)
    blocked = fail_fraction > float(fallback["candidate_failure_fraction_that_blocks_the_stage"])

    manifest = {
        "manifest_id": "SE100-DATA-1001",
        "manifest_type": "RAW_ACQUISITION",
        "project": "StockEdge100",
        "generation": 1,
        "stage": 1,
        "provider": "yahoo_finance",
        "client": "yfinance",
        "client_version": getattr(yf, "__version__", "UNKNOWN"),
        "endpoint_mode": "unofficial public chart endpoint via the yfinance client",
        "license": LICENSE_NOTE,
        "raw_definition": (
            "The client does not expose the underlying HTTP payload, so 'raw' here means the frame "
            "the client returned, serialised to CSV with no value altered, rounded, reordered, or "
            "dropped. This is recorded rather than glossed over."
        ),
        "request_parameters": params["request_parameters"],
        "preregistration": {
            "declared_utc": config.declared_utc,
            "config_sha256": config.config_hash,
            "universe_spec_sha256": config.digests["config/stage1_universe_spec.json"],
        },
        "acquisition_started_utc": started,
        "acquisition_finished_utc": utc_now_iso(),
        "candidate_count": len(config.candidates),
        "reference_count": len(config.reference_symbols),
        "acquisition_failures": candidate_failures,
        "acquisition_failure_fraction": round(fail_fraction, 4),
        "blocking_threshold": fallback["candidate_failure_fraction_that_blocks_the_stage"],
        "stage_blocked_by_acquisition": blocked,
        "provider_revisions_quarantined": revisions,
        "symbols": entries,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    print()
    print(f"candidates      {len(config.candidates)}")
    print(f"failures        {len(candidate_failures)} ({fail_fraction:.1%})")
    print(f"revisions       {len(revisions)}")
    print(f"manifest        {MANIFEST_PATH.relative_to(PROJECT_ROOT).as_posix()}")
    if blocked:
        print("STAGE BLOCKED: acquisition failure fraction exceeds the pre-registered threshold.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(acquire())
