"""The pre-registered Stage 1 validation battery.

Run from ``stockedge100/``::

    python -m stockedge100.data.validate

The sixteen checks and their severities were sealed in ``config/stage1_data_source.json`` before any
data was acquired, and this module reads them from that sealed file rather than restating them, so a
check cannot be quietly dropped or reworded after seeing a failure. It executes them; it does not
define them.

Two scope rules apply and are enforced here rather than trusted:

* **Integrity checks run over the whole series, including the holdout.** Confirming that a session
  key is a real trading day or that a split reconciles is not a research result, and Gate 1 requires
  the manifests to be complete. What is forbidden is reading holdout values to make a *decision*.
* **Eligibility measurements run on development-window data only.** ``PRICE_NOT_PENNY`` is the one
  check in this battery that is a threshold on values rather than a structural assertion, so it is
  restricted to the development window; the rest of the eligibility screen lives in the universe
  module under the same restriction.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from dataclasses import dataclass, asdict
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from stockedge100.audit import sha256_file, utc_now_iso
from stockedge100.data.calendar import (
    calendar_bounds,
    longest_missing_run,
    missing_sessions,
    sessions_between,
)
from stockedge100.data.config import PROJECT_ROOT, load_stage1_config
from stockedge100.data.normalize import NORMALIZED_MANIFEST_PATH
from stockedge100.data.partition import compute_partition
from stockedge100.data.quarantine import existing_records as quarantine_records
from stockedge100.data.quarantine import quarantine

VALIDATION_REPORT_PATH = PROJECT_ROOT / "data" / "manifests" / "STAGE_1_VALIDATION_REPORT.json"

MISSING_FRACTION_LIMIT = 0.01
MISSING_RUN_LIMIT = 5
EXTREME_MOVE_LIMIT = 0.50
PENNY_PRICE_FLOOR = 5.00


@dataclass
class CheckResult:
    check_id: str
    severity: str
    status: str
    detail: str
    evidence: dict[str, Any]

    @property
    def failed(self) -> bool:
        return self.status == "FAIL"

    @property
    def warned(self) -> bool:
        return self.status == "WARN"


def _result(check_id: str, severity: str, ok: bool, detail: str, evidence: dict[str, Any]) -> CheckResult:
    status = "PASS" if ok else severity
    return CheckResult(check_id, severity, status, detail, evidence)


def _dates(frame: pd.DataFrame) -> list[dt.date]:
    return [dt.date.fromisoformat(s) for s in frame["session"]]


def _factor(frame: pd.DataFrame) -> pd.Series:
    return frame["adj_close"] / frame["close"]


def run_checks(
    symbol: str,
    frame: pd.DataFrame,
    *,
    severities: dict[str, str],
    tolerances: dict[str, float],
    semantics: dict[str, Any],
    expected_actions: list[dict[str, Any]],
    acquisition_date: dt.date,
    partition,
) -> list[CheckResult]:
    price_tol = float(tolerances["price_relative"])
    factor_tol = float(tolerances["factor_relative"])
    div_tol = float(tolerances["dividend_relative"])

    sessions = _dates(frame)
    factor = _factor(frame)
    results: list[CheckResult] = []

    def sev(check_id: str) -> str:
        return severities[check_id]

    # --- session structure -------------------------------------------------------------------
    lo, hi = calendar_bounds()
    in_bounds = [d for d in sessions if lo <= d <= hi]
    calendar_days = set(sessions_between(min(sessions), max(sessions)))
    phantom = [d.isoformat() for d in sessions if d not in calendar_days]
    results.append(
        _result(
            "SESSION_IN_CALENDAR",
            sev("SESSION_IN_CALENDAR"),
            not phantom and len(in_bounds) == len(sessions),
            f"{len(phantom)} session(s) are not XNYS trading days",
            {"phantom_sessions": phantom[:20], "phantom_count": len(phantom)},
        )
    )

    duplicates = frame["session"][frame["session"].duplicated()].tolist()
    results.append(
        _result(
            "NO_DUPLICATE_SESSIONS",
            sev("NO_DUPLICATE_SESSIONS"),
            not duplicates,
            f"{len(duplicates)} duplicated session key(s)",
            {"duplicates": duplicates[:20]},
        )
    )

    non_increasing = [
        sessions[i].isoformat() for i in range(1, len(sessions)) if sessions[i] <= sessions[i - 1]
    ]
    results.append(
        _result(
            "SESSIONS_STRICTLY_INCREASING",
            sev("SESSIONS_STRICTLY_INCREASING"),
            not non_increasing,
            f"{len(non_increasing)} session(s) not strictly after their predecessor",
            {"offenders": non_increasing[:20]},
        )
    )

    future = [d.isoformat() for d in sessions if d > acquisition_date]
    results.append(
        _result(
            "NO_FUTURE_SESSIONS",
            sev("NO_FUTURE_SESSIONS"),
            not future,
            f"{len(future)} session(s) later than the acquisition date {acquisition_date}",
            {"future_sessions": future[:20], "acquisition_date_new_york": acquisition_date.isoformat()},
        )
    )

    # --- bar sanity --------------------------------------------------------------------------
    prices = frame[["open", "high", "low", "close"]]
    finite_positive = prices.apply(lambda c: c.gt(0) & c.notna() & c.abs().ne(float("inf"))).all(axis=1)
    ordered = (frame["low"] <= frame[["open", "close"]].min(axis=1)) & (
        frame[["open", "close"]].max(axis=1) <= frame["high"]
    )
    bad_ohlc = frame.index[~(finite_positive & ordered)]
    if len(bad_ohlc):
        quarantine(
            symbol,
            "OHLC_CONSISTENT",
            "low<=min(open,close)<=max(open,close)<=high violated, or a non-finite/non-positive price",
            frame.loc[bad_ohlc].to_dict("records"),
        )
    results.append(
        _result(
            "OHLC_CONSISTENT",
            sev("OHLC_CONSISTENT"),
            len(bad_ohlc) == 0,
            f"{len(bad_ohlc)} bar(s) violate OHLC ordering or positivity",
            {
                "violation_count": int(len(bad_ohlc)),
                "examples": frame.loc[bad_ohlc, "session"].head(10).tolist(),
            },
        )
    )

    bad_volume = frame.index[~(frame["volume"].notna() & (frame["volume"] >= 0))]
    results.append(
        _result(
            "VOLUME_VALID",
            sev("VOLUME_VALID"),
            len(bad_volume) == 0,
            f"{len(bad_volume)} bar(s) with missing or negative volume",
            {
                "violation_count": int(len(bad_volume)),
                "zero_volume_sessions": int((frame["volume"] == 0).sum()),
            },
        )
    )

    bad_adj = frame.index[~(frame["adj_close"].notna() & (frame["adj_close"] > 0))]
    results.append(
        _result(
            "ADJ_CLOSE_POSITIVE",
            sev("ADJ_CLOSE_POSITIVE"),
            len(bad_adj) == 0,
            f"{len(bad_adj)} bar(s) with non-positive or missing adj_close",
            {"violation_count": int(len(bad_adj))},
        )
    )

    # --- adjustment arithmetic ---------------------------------------------------------------
    terminal = float(factor.iloc[-1])
    results.append(
        _result(
            "TERMINAL_FACTOR_IS_ONE",
            sev("TERMINAL_FACTOR_IS_ONE"),
            abs(terminal - 1.0) <= price_tol,
            f"terminal adjustment factor {terminal:.12f}",
            {
                "terminal_factor": terminal,
                "terminal_session": frame["session"].iloc[-1],
                "tolerance": price_tol,
            },
        )
    )

    step = factor.to_numpy()[1:] / factor.to_numpy()[:-1]
    decreasing = [
        {"session": frame["session"].iloc[i + 1], "factor_step": float(step[i])}
        for i in range(len(step))
        if step[i] < 1.0 - factor_tol
    ]
    results.append(
        _result(
            "FACTOR_NON_DECREASING",
            sev("FACTOR_NON_DECREASING"),
            not decreasing,
            f"{len(decreasing)} backward step(s) in the adjustment factor",
            {
                "violation_count": len(decreasing),
                "worst": min((d["factor_step"] for d in decreasing), default=None),
                "examples": decreasing[:10],
                "tolerance": factor_tol,
            },
        )
    )

    # Splits. The expectation is derived from the measured semantics, not assumed: because OHLC and
    # adj_close are both already back-adjusted for splits, a split must leave the factor unchanged
    # AND must leave the adjusted price step at an ordinary daily magnitude. If the vendor had
    # failed to back-adjust, the step would sit near 1/ratio, which is what this rejects.
    ohlc_split_adjusted = bool(semantics.get("ohlc_split_adjusted"))
    split_rows = frame.index[frame["split_ratio"] != 0]
    split_detail: list[dict[str, Any]] = []
    split_ok = True
    for i in split_rows:
        if i == 0:
            split_detail.append({"session": frame["session"].iloc[i], "status": "FIRST_ROW_NO_PRIOR_BAR"})
            continue
        ratio = float(frame["split_ratio"].iloc[i])
        observed_factor_step = float(factor.iloc[i] / factor.iloc[i - 1])
        expected_factor_step = 1.0 if ohlc_split_adjusted else 1.0 / ratio
        adj_step = float(frame["adj_close"].iloc[i] / frame["adj_close"].iloc[i - 1])
        as_traded_step = 1.0 / ratio
        factor_ok = abs(observed_factor_step - expected_factor_step) <= factor_tol * expected_factor_step
        # a split-sized cliff in the adjusted series means the split was never applied
        price_ok = abs(adj_step - as_traded_step) > 0.10 * as_traded_step
        ok = factor_ok and price_ok
        split_ok = split_ok and ok
        split_detail.append(
            {
                "session": frame["session"].iloc[i],
                "recorded_ratio": ratio,
                "observed_factor_step": round(observed_factor_step, 10),
                "expected_factor_step": round(expected_factor_step, 10),
                "adjusted_price_step": round(adj_step, 10),
                "step_if_split_were_unapplied": round(as_traded_step, 10),
                "status": "PASS" if ok else "FAIL",
            }
        )
    results.append(
        _result(
            "SPLIT_RECONCILES",
            sev("SPLIT_RECONCILES"),
            split_ok,
            f"{len(split_rows)} recorded split(s); expectation derived from measured semantics "
            f"(ohlc_split_adjusted={ohlc_split_adjusted})",
            {"split_count": int(len(split_rows)), "splits": split_detail},
        )
    )

    # Dividends. Yahoo scales every bar before the ex-date by (1 - D / prior close), so the factor
    # step on the ex-date must be the reciprocal of that.
    dividend_rows = frame.index[frame["dividend"] != 0]
    div_offenders: list[dict[str, Any]] = []
    for i in dividend_rows:
        if i == 0:
            continue
        amount = float(frame["dividend"].iloc[i])
        prior_close = float(frame["close"].iloc[i - 1])
        if prior_close <= 0 or amount >= prior_close:
            continue
        expected = 1.0 / (1.0 - amount / prior_close)
        observed = float(factor.iloc[i] / factor.iloc[i - 1])
        relative = abs(observed - expected) / expected
        if relative > div_tol:
            div_offenders.append(
                {
                    "session": frame["session"].iloc[i],
                    "dividend": amount,
                    "prior_close": prior_close,
                    "expected_factor_step": round(expected, 10),
                    "observed_factor_step": round(observed, 10),
                    "relative_error": round(relative, 8),
                }
            )
    if div_offenders:
        quarantine(
            symbol,
            "DIVIDEND_RECONCILES",
            "adjustment-factor step on an ex-dividend session disagrees with the recorded amount",
            div_offenders,
        )
    results.append(
        _result(
            "DIVIDEND_RECONCILES",
            sev("DIVIDEND_RECONCILES"),
            not div_offenders,
            f"{len(div_offenders)} of {len(dividend_rows)} dividend event(s) outside tolerance",
            {
                "dividend_events": int(len(dividend_rows)),
                "offender_count": len(div_offenders),
                "worst_relative_error": max((d["relative_error"] for d in div_offenders), default=0.0),
                "examples": div_offenders[:10],
                "tolerance": div_tol,
            },
        )
    )

    # --- declared corporate-action fixture ---------------------------------------------------
    if expected_actions:
        fixture: list[dict[str, Any]] = []
        fixture_ok = True
        for action in expected_actions:
            session, ratio = action["session"], float(action["ratio"])
            match = frame.index[frame["session"] == session]
            if len(match) != 1:
                fixture.append({"session": session, "status": "SESSION_ABSENT"})
                fixture_ok = False
                continue
            i = int(match[0])
            recorded = float(frame["split_ratio"].iloc[i])
            adj_step = float(frame["adj_close"].iloc[i] / frame["adj_close"].iloc[i - 1])
            ratio_ok = abs(recorded - ratio) <= factor_tol * ratio
            continuous = abs(adj_step - 1.0 / ratio) > 0.10 / ratio
            fixture_ok = fixture_ok and ratio_ok and continuous
            fixture.append(
                {
                    "session": session,
                    "declared_ratio": ratio,
                    "recorded_ratio": recorded,
                    "adjusted_price_step": round(adj_step, 10),
                    "step_if_split_were_unapplied": round(1.0 / ratio, 10),
                    "status": "PASS" if (ratio_ok and continuous) else "FAIL",
                }
            )
        results.append(
            _result(
                "CORPORATE_ACTION_FIXTURE",
                sev("CORPORATE_ACTION_FIXTURE"),
                fixture_ok,
                f"{len(expected_actions)} declared reference action(s) checked",
                {"actions": fixture},
            )
        )
    else:
        results.append(
            CheckResult(
                "CORPORATE_ACTION_FIXTURE",
                sev("CORPORATE_ACTION_FIXTURE"),
                "NOT_APPLICABLE",
                "no corporate action declared for this symbol; the fixture is carried by the "
                "reference symbols and by SPLIT_RECONCILES on this one",
                {},
            )
        )

    # --- completeness ------------------------------------------------------------------------
    first, last = min(sessions), max(sessions)
    expected_sessions = sessions_between(first, last)
    missing = missing_sessions(sessions, first, last)
    fraction = len(missing) / max(len(expected_sessions), 1)
    if missing:
        quarantine(
            symbol,
            "MISSING_SESSION",
            "XNYS trading sessions absent from the provider series inside the symbol's own range",
            [{"session": d.isoformat()} for d in missing],
        )
    results.append(
        _result(
            "MISSING_SESSION_FRACTION",
            sev("MISSING_SESSION_FRACTION"),
            fraction <= MISSING_FRACTION_LIMIT,
            f"{len(missing)} of {len(expected_sessions)} expected sessions absent ({fraction:.4%})",
            {
                "expected_sessions": len(expected_sessions),
                "missing_count": len(missing),
                "missing_fraction": round(fraction, 6),
                "limit": MISSING_FRACTION_LIMIT,
                "examples": [d.isoformat() for d in missing[:10]],
            },
        )
    )

    run = longest_missing_run(missing, first, last)
    results.append(
        _result(
            "MISSING_SESSION_RUN",
            sev("MISSING_SESSION_RUN"),
            run <= MISSING_RUN_LIMIT,
            f"longest run of consecutive missing sessions is {run}",
            {"longest_missing_run": run, "limit": MISSING_RUN_LIMIT},
        )
    )

    # --- extreme moves -----------------------------------------------------------------------
    adj_return = frame["adj_close"].pct_change()
    extreme = frame.index[adj_return.abs() > EXTREME_MOVE_LIMIT]
    unexplained: list[dict[str, Any]] = []
    for i in extreme:
        explained = float(frame["split_ratio"].iloc[i]) != 0 or float(frame["dividend"].iloc[i]) != 0
        if not explained:
            unexplained.append(
                {
                    "session": frame["session"].iloc[i],
                    "adjusted_return": round(float(adj_return.iloc[i]), 8),
                    "close": float(frame["close"].iloc[i]),
                    "prior_close": float(frame["close"].iloc[i - 1]) if i else None,
                }
            )
    if unexplained:
        quarantine(
            symbol,
            "EXTREME_MOVE_EXPLAINED",
            "adjusted close-to-close return above 50% with no recorded split or dividend",
            unexplained,
        )
    results.append(
        _result(
            "EXTREME_MOVE_EXPLAINED",
            sev("EXTREME_MOVE_EXPLAINED"),
            not unexplained,
            f"{len(unexplained)} unexplained move(s) above {EXTREME_MOVE_LIMIT:.0%}",
            {
                "extreme_move_count": int(len(extreme)),
                "unexplained_count": len(unexplained),
                "examples": unexplained[:10],
                "largest_absolute_return": round(float(adj_return.abs().max()), 8),
            },
        )
    )

    # --- price floor, development window only ------------------------------------------------
    dev = frame[
        (frame["session"] >= partition.development_start)
        & (frame["session"] <= partition.development_end)
    ]
    if dev.empty:
        results.append(
            CheckResult(
                "PRICE_NOT_PENNY",
                sev("PRICE_NOT_PENNY"),
                "NOT_APPLICABLE",
                "no development-window sessions; handled by the universe eligibility screen instead",
                {"development_sessions": 0},
            )
        )
    else:
        minimum = float(dev["close"].min())
        results.append(
            _result(
                "PRICE_NOT_PENNY",
                sev("PRICE_NOT_PENNY"),
                minimum >= PENNY_PRICE_FLOOR,
                f"minimum development-window close {minimum:.4f}",
                {
                    "minimum_close": minimum,
                    "floor": PENNY_PRICE_FLOOR,
                    "development_sessions": int(len(dev)),
                    "window": [partition.development_start, partition.development_end],
                },
            )
        )

    return results


def validate() -> int:
    config = load_stage1_config()
    if not NORMALIZED_MANIFEST_PATH.is_file():
        print("normalized manifest missing; run stockedge100.data.normalize first", file=sys.stderr)
        return 2

    normalized = json.loads(NORMALIZED_MANIFEST_PATH.read_text(encoding="utf-8"))
    battery = config.data_source["validation_battery"]
    severities = {c["id"]: c["severity"] for c in battery["checks"]}
    tolerances = config.tolerances
    semantics = normalized["adjustment_semantics"]

    raw_manifest = json.loads(
        (PROJECT_ROOT / normalized["source_manifest"]["path"]).read_text(encoding="utf-8")
    )
    acquisition_date = (
        dt.datetime.fromisoformat(raw_manifest["acquisition_finished_utc"].replace("Z", "+00:00"))
        .astimezone(ZoneInfo("America/New_York"))
        .date()
    )

    frames: dict[str, pd.DataFrame] = {}
    for symbol, entry in normalized["symbols"].items():
        if entry.get("status") != "NORMALIZED":
            continue
        path = PROJECT_ROOT / entry["path"]
        if sha256_file(path) != entry["sha256"]:
            print(f"  NORMALIZED DIGEST MISMATCH {symbol}", file=sys.stderr)
            return 3
        frames[symbol] = pd.read_csv(path, dtype={"session": str})

    candidates = [s for s in config.candidates if s in frames]
    cutoff = max(dt.date.fromisoformat(frames[s]["session"].iloc[-1]) for s in candidates)
    earliest = min(dt.date.fromisoformat(frames[s]["session"].iloc[0]) for s in candidates)
    partition = compute_partition(cutoff, earliest)

    expected_by_symbol = {
        entry["symbol"]: entry.get("expected_actions", [])
        for entry in config.universe_spec["reference_symbols"]["symbols"]
    }

    truncated = {
        symbol
        for symbol, entry in raw_manifest["symbols"].items()
        if entry.get("requested_window") != "max"
    }
    research = set(candidates)

    per_symbol: dict[str, Any] = {}
    failing_symbols: list[str] = []
    warning_symbols: list[str] = []
    scope_gaps: list[dict[str, Any]] = []
    check_totals: dict[str, dict[str, int]] = {c["id"]: {"PASS": 0, "FAIL": 0, "WARN": 0, "NOT_APPLICABLE": 0} for c in battery["checks"]}

    for symbol, frame in frames.items():
        results = run_checks(
            symbol,
            frame,
            severities=severities,
            tolerances=tolerances,
            semantics=semantics,
            expected_actions=expected_by_symbol.get(symbol, []),
            acquisition_date=acquisition_date,
            partition=partition,
        )
        fails = [r.check_id for r in results if r.failed]
        warns = [r.check_id for r in results if r.warned]

        # TERMINAL_FACTOR_IS_ONE presumes the last row is the provider's terminal session. For a
        # reference fixture whose acquisition window was deliberately truncated by pre-registration,
        # that premise is false by construction, and the raw manifest recorded the truncation before
        # this battery ever ran. The sealed check is left exactly as written and the FAIL is left on
        # the record; the gap is in the pre-registration, and it is reported as such rather than
        # repaired by editing a sealed file after seeing the result.
        for check in list(fails):
            if (
                check == "TERMINAL_FACTOR_IS_ONE"
                and symbol in truncated
                and symbol not in research
            ):
                scope_gaps.append(
                    {
                        "symbol": symbol,
                        "check_id": check,
                        "classification": "PREREGISTRATION_SCOPE_GAP",
                        "premise_of_the_check": "the final row is the provider's terminal session",
                        "why_the_premise_is_false": (
                            "the raw manifest records requested_window "
                            f"{raw_manifest['symbols'][symbol]['requested_window']} for this symbol, "
                            "a truncation declared in the sealed universe spec so that a data-quality "
                            "fixture never touches validation or holdout data"
                        ),
                        "in_research_universe": False,
                        "sealed_check_amended": False,
                        "disposition": (
                            "recorded as a defect in the Stage 1 pre-registration, which failed to "
                            "scope this check to untruncated series"
                        ),
                    }
                )

        if fails:
            failing_symbols.append(symbol)
        if warns:
            warning_symbols.append(symbol)
        for r in results:
            check_totals[r.check_id][r.status] += 1
        per_symbol[symbol] = {
            "role": normalized["symbols"][symbol]["role"],
            "rows": int(len(frame)),
            "failed_checks": fails,
            "warned_checks": warns,
            "checks": [asdict(r) for r in results],
        }
        flag = "FAIL" if fails else ("WARN" if warns else "PASS")
        print(f"  {flag:4s} {symbol:6s} {'' if not fails else ' '.join(fails)}{'' if not warns else ' (warn: ' + ' '.join(warns) + ')'}")

    research_failures = {s for s in failing_symbols if s in research}
    classified = {(g["symbol"], g["check_id"]) for g in scope_gaps}
    unclassified = {
        f"{symbol}:{check}"
        for symbol in failing_symbols
        for check in per_symbol[symbol]["failed_checks"]
        if (symbol, check) not in classified
    }

    report = {
        "report_id": "SE100-DATA-1003",
        "report_type": "VALIDATION_BATTERY",
        "project": "StockEdge100",
        "generation": 1,
        "stage": 1,
        "generated_utc": utc_now_iso(),
        "battery_source": {
            "path": "config/stage1_data_source.json",
            "sha256": config.config_hash,
            "declared_before_data_seen": battery["declared_before_data_seen"],
            "check_count": len(battery["checks"]),
        },
        "normalized_manifest": {
            "path": NORMALIZED_MANIFEST_PATH.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": sha256_file(NORMALIZED_MANIFEST_PATH),
        },
        "calendar": {
            "source": "exchange_calendars",
            "name": "XNYS",
            "independent_of_price_provider": True,
            "bounds": [d.isoformat() for d in calendar_bounds()],
        },
        "adjustment_semantics": semantics,
        "scope_rules": {
            "integrity_checks_cover_full_series_including_holdout": True,
            "why": (
                "Confirming a session key or a split reconciliation is not a research result. Gate 1 "
                "requires complete manifests; what is forbidden is using holdout values to make a "
                "decision."
            ),
            "value_threshold_checks_restricted_to_development_window": ["PRICE_NOT_PENNY"],
        },
        "partition_used_for_window_restricted_checks": partition.to_json(),
        "acquisition_date_new_york": acquisition_date.isoformat(),
        "symbol_count": len(frames),
        "research_universe_symbols": sorted(research),
        "reference_fixture_symbols": sorted(set(frames) - research),
        "symbols_with_failures": failing_symbols,
        "symbols_with_warnings": warning_symbols,
        "check_totals": check_totals,
        "battery_passed": not failing_symbols,
        "research_universe_battery_passed": not research_failures,
        "research_universe_failures": sorted(research_failures),
        "preregistration_scope_gaps": scope_gaps,
        "unclassified_failures": sorted(unclassified),
        "quarantine_records": quarantine_records(),
        "per_symbol": per_symbol,
    }
    VALIDATION_REPORT_PATH.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")

    print()
    print(f"symbols           {len(frames)} ({len(research)} research, {len(frames) - len(research)} fixture)")
    print(f"research failures {len(research_failures)} {sorted(research_failures)}")
    print(f"warnings          {len(warning_symbols)} {warning_symbols}")
    print(f"scope gaps        {len(scope_gaps)} {[g['symbol'] + ':' + g['check_id'] for g in scope_gaps]}")
    print(f"unclassified      {len(unclassified)} {sorted(unclassified)}")
    print(f"report            {VALIDATION_REPORT_PATH.relative_to(PROJECT_ROOT).as_posix()}")
    return 0 if not research_failures and not unclassified else 1


if __name__ == "__main__":
    raise SystemExit(validate())
