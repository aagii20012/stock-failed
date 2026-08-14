"""Quarantine, not deletion.

The pre-registered row policy is that no row is ever silently dropped. When a row fails a sanity
rule it stays in the normalized file and a copy is written here with the reason, so the anomaly is
visible in the audit trail instead of vanishing into a cleaned dataset. Anything that removes data
without leaving a record of what was removed is the thing this module exists to prevent.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from stockedge100.audit import utc_now_iso
from stockedge100.data.config import PROJECT_ROOT

QUARANTINE_DIR = PROJECT_ROOT / "data" / "quarantine"


def quarantine(symbol: str, check_id: str, reason: str, rows: list[dict[str, Any]]) -> Path:
    """Record offending rows for ``symbol`` under ``check_id``. Returns the record path."""
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
    path = QUARANTINE_DIR / f"{symbol}.{check_id}.json"
    path.write_text(
        json.dumps(
            {
                "symbol": symbol,
                "check_id": check_id,
                "reason": reason,
                "detected_utc": utc_now_iso(),
                "rows_retained_in_normalized_output": True,
                "row_count": len(rows),
                "rows": rows[:200],
                "rows_truncated": len(rows) > 200,
            },
            indent=2,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def existing_records() -> list[str]:
    if not QUARANTINE_DIR.is_dir():
        return []
    return sorted(p.relative_to(PROJECT_ROOT).as_posix() for p in QUARANTINE_DIR.glob("*.json"))
