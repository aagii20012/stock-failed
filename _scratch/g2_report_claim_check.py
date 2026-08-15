"""Check the prose claims in the Stage 3 G2 report against the artifacts on disk. ASCII only.

The report is the human half of the package and the evidence JSON is the machine half. A number that
disagrees between them is the defect this checks for -- and it must be found *before* the build,
because the report lives in ``governance/`` and the package hashes it.

Every predicate is written against the evidence file's *actual* shape, enumerated first by
``g2_evidence_keys.py``. The first draft of this script guessed ``grid["size"]`` and
``ev["runs"]["runs_declared"]``; ``grid`` carries ``variants_declared`` and ``runs`` is a list of 36.
Every check prints the disk value beside the claim, so a pass cannot be produced by finding nothing.
"""

from __future__ import annotations

import json
import re
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stockedge100"
REPORT = ROOT / "governance/generation_2/STAGE_3_G2_ROTATION_RESEARCH_REPORT.md"
EVIDENCE = ROOT / "reports/stage3_g2/STAGE_3_G2_DEVELOPMENT_ADMISSIBILITY.json"
CRITERIA = ROOT / "config/generation_2/g2_gate_criteria.json"
PROTOCOL = ROOT / "config/generation_2/g2_rotation_protocol.json"
LOCK = ROOT / "governance/generation_2/STAGE_1_G2_PARTITION_LOCK.json"

failures: list[str] = []


def check(label: str, claim, disk) -> None:
    ok = claim == disk
    if not ok:
        failures.append(label)
    print(f"   {'OK  ' if ok else 'FAIL'} {label:44s} report={claim!r} disk={disk!r}")


def contains(label: str, needle: str, text: str) -> None:
    ok = needle in text
    if not ok:
        failures.append(label)
    print(f"   {'OK  ' if ok else 'FAIL'} {label:44s} present={ok} (needle {len(needle)} chars)")


def norm(s: str) -> str:
    return re.sub(r"[\s>]+", " ", s).strip()


def main() -> int:
    report = REPORT.read_text(encoding="utf-8")
    nreport = norm(report)
    ev = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    crit = json.loads(CRITERIA.read_text(encoding="utf-8"))
    proto = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    lock = json.loads(LOCK.read_text(encoding="utf-8"))

    print("== identity ==")
    check("generation_id", "SE100-GEN2-7394207c543401e2", ev["generation_id"])
    check("strategy_id", "SE100-G2-S3-C1-ROTATION", ev["strategy_id"])
    check("evidence artifact_id", "SE100-EVID-3101", ev["artifact_id"])
    check("generation", 2, ev["generation"])

    print()
    print("== grid and runs ==")
    grid = ev["grid"]
    check("variants declared 18", 18, grid["variants_declared"])
    check("runs executed 36", 36, grid["runs_executed"])
    check("total runs 36", 36, grid["runs_per_variant"]["total_runs"])
    check("all declared runs executed", True, grid["all_declared_runs_executed"])
    check("revisions after a result 0", 0, grid["revisions_after_seeing_a_result"])
    check("runs array length 36", 36, len(ev["runs"]))
    check("lookback axis", [3, 6, 12], grid["axes"]["lookback_months"])
    check("top_k axis", [1, 2, 3], grid["axes"]["top_k"])
    check("rebalance axis", ["MONTHLY", "QUARTERLY"], grid["axes"]["rebalance_frequency"])

    print()
    print("== window ==")
    w = ev["window"]
    check("latest session loaded", "2021-07-30", w["latest_session_loaded"])
    check("development bound", "2021-07-31", w["development_bound"])
    check("validation_read false", False, w["validation_read"])
    check("generation_1_holdout_read false", False, w["generation_1_holdout_read"])
    check("generation_2_holdout_read false", False, w["generation_2_holdout_read"])
    rs = w["run_span"]
    check("run start", "2008-07-28", rs["run_start"])
    check("run end", "2021-07-30", rs["run_end"])
    check("run sessions 3276", 3276, rs["run_sessions"])
    check("binding symbol VEA", "VEA", rs["binding_symbol"])
    check("binding inception", "2007-07-26", rs["binding_symbol_inception"])
    check("development union sessions", 7178, rs["development_union_sessions"])

    print()
    print("== universe ==")
    u = ev["universe"]
    check("universe version", "SE100-U1-d4917c2f7f1cd834", u["universe_version"])
    check("symbols declared 34", 34, len(u["symbols_declared"])
          if isinstance(u["symbols_declared"], list) else u["symbols_declared"])
    check("symbols loaded 34", 34, len(u["symbols_loaded"])
          if isinstance(u["symbols_loaded"], list) else u["symbols_loaded"])
    check("symbols missing 0", 0, len(u["symbols_missing"]))
    check("AAPL excluded", True, "AAPL" in u["excluded_symbols"])

    print()
    print("== selection ==")
    sel = ev["selection"]
    check("representative_exists false", False, sel["representative_exists"])
    check("representative_variant_id none", None, sel["representative_variant_id"])
    check("eligible_count 0", 0, sel["step_1"]["eligible_count"])
    check("variants_considered 18", 18, sel["variants_considered"])
    check("decided_at_step none", None, sel["decided_at_step"])
    check("decided_by", "no_candidate_path", sel["decided_by"])
    check("selection inputs 18", 18, len(sel["inputs"]))
    check("return_blind true", True, sel["return_blind"])
    fields = sorted({k for row in sel["inputs"] for k in row})
    check("selection input fields",
          ["fill_count", "per_run", "research_shutdown_events", "variant_id"], fields)
    check("candidate_results empty", 0, len(ev["candidate_results"]))

    note = sel["selection_note"]
    print(f"   sealed selection_note length {len(note)}")
    ok = norm(note) in nreport
    if not ok:
        failures.append("selection note quoted")
    print(f"   {'OK  ' if ok else 'FAIL'} selection note quoted in report (normalised)")

    print()
    print("== verdict and gate ==")
    # stage_verdict splits the token from the outcome word: verdict='FAIL', verdict_token=the token.
    # The composite "FAIL - <token>" the report prints is assembled, not stored.
    sv = ev["stage_verdict"]
    check("stage verdict word", "FAIL", sv["verdict"])
    check("stage verdict token", "STAGE_3_G2_NO_CANDIDATE", sv["verdict_token"])
    check("fail_route", "NO_REPRESENTATIVE_EXISTS", sv["fail_route"])
    check("route mirrors fail_route", sv["fail_route"], sv["route"])
    check("candidates_evaluated 0", 0, sv["candidates_evaluated"])
    check("admitted_candidates empty", 0, len(sv["admitted_candidates"]))
    # fail_is_a_deliverable is prose, not a flag: bool() on it would pass on any non-empty string.
    check("fail_is_a_deliverable names the token",
          True, sv["verdict_token"] in sv["fail_is_a_deliverable"])
    der = crit["verdict_token_derivation"]
    print(f"   sealed pass_token = {der['pass_token']!r}")
    print(f"   sealed fail_token = {der['fail_token']!r}")
    check("evidence fail_token matches seal", sv["fail_token"], der["fail_token"])
    contains("report emits the sealed fail token", der["fail_token"], report)
    pass_absent = der["pass_token"] not in report
    if not pass_absent:
        failures.append("report must not emit the pass token")
    print(f"   {'OK  ' if pass_absent else 'FAIL'} "
          f"{'report does NOT emit the pass token':44s} absent={pass_absent}")

    print()
    print("== determinism ==")
    det = ev["determinism"]
    check("runs compared 36", 36, det["runs_compared"])
    check("all identical", True, det["all_identical"])
    check("mismatched runs 0", 0, len(det["mismatched_runs"]))
    check("run digests 36", 36, len(det["run_digests"]))

    print()
    print("== sealed disclosures verbatim ==")
    contains("validation reuse disclosure", lock["validation_reuse_disclosure"], report)
    contains("multiple comparisons disclosure", proto["multiple_comparisons_disclosure"], report)
    check("multiplicity text same in evidence",
          proto["multiple_comparisons_disclosure"], ev["multiple_comparisons_disclosure"])

    print()
    print("== variant table cross-check ==")
    table = ev["variant_table"]
    check("variant_table rows 18", 18, len(table))
    shutdowns = sorted({row["research_shutdown_events"] for row in table})
    check("distinct shutdown counts", [2], shutdowns)

    short_missing = [r["variant_id"] for r in table
                     if "-".join(r["variant_id"].split("-")[-3:]) not in report]
    print(f"   variant ids absent from report: {short_missing}")
    if short_missing:
        failures.append("all 18 variant ids appear in the report")

    # Every base and stress return, drawdown, trade count and shutdown session in the table must
    # appear in the report's grid tables. This is the check that catches a hand-transcribed digit,
    # which is how those tables were written. Numeric fields are stored as decimal *strings* to keep
    # them exact, so they are compared as text -- drawdowns are compared on their 8-digit prefix,
    # which is the precision the report tabulates.
    # The report tabulates at 4 decimal places and renders negatives with U+2212 MINUS SIGN, so the
    # probe must round the same way and fold the minus. Comparing raw strings reported 53 spurious
    # misses against a report that was correct -- the probe was wrong, not the tables.
    def q4(v) -> str:
        return str(Decimal(str(v)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))

    folded = report.replace("−", "-")

    missing_nums: list[str] = []
    for r in table:
        probes = [
            ("base_total_return", q4(r["base_total_return"])),
            ("stress_total_return", q4(r["stress_total_return"])),
            ("base_max_drawdown", q4(r["base_max_drawdown"])),
            ("stress_max_drawdown", q4(r["stress_max_drawdown"])),
            ("base_profit_factor", q4(r["base_profit_factor"])),
            ("stress_profit_factor", q4(r["stress_profit_factor"])),
            ("base_closed_trades", str(r["base_closed_trades"])),
            ("stress_closed_trades", str(r["stress_closed_trades"])),
            ("base_shutdown_session", str(r["base_shutdown_session"])),
            ("stress_shutdown_session", str(r["stress_shutdown_session"])),
            ("fill_count_both_runs", str(r["fill_count_both_runs"])),
        ]
        for field, s in probes:
            if s not in folded:
                missing_nums.append(f"{r['variant_id'].split('-', 5)[-1]}.{field}={s}")
    print(f"   table values not found in report text: {len(missing_nums)}")
    for m in missing_nums[:20]:
        print(f"        {m}")
    if missing_nums:
        failures.append("every variant table value appears in the report")

    fills = {r["variant_id"]: r["fill_count_both_runs"] for r in table}
    print(f"   fill_count_both_runs total {sum(fills.values())}, "
          f"min {min(fills.values())}, max {max(fills.values())}")

    print()
    print("== window prohibitions stated in prose ==")
    for phrase in ("2021-07-31", "2021-08-01", "2024-07-31", "2026-08-01", "2028-07-31"):
        contains(f"report names {phrase}", phrase, report)

    print()
    print(f"RESULT {'OK' if not failures else 'FAILED: ' + '; '.join(failures)}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
