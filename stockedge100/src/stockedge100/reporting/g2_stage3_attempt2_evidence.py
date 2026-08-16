"""Generation 2 Stage 3 **Attempt 2** development evidence — run the declared grid, write what it did.

A writer, not a judge, exactly as Attempt 1's counterpart was. Every figure comes from
:mod:`stockedge100.strategies.g2_runner_ra1`, every condition verdict from
:mod:`stockedge100.strategies.g2_gate_ra1`, and the representative — if one exists — from the sealed
three-step return-blind rule in ``config/generation_2/g2_rotation_ra1_protocol.json``. Nothing in
this module can change a verdict.

The ordering below is load-bearing and mirrors the seal:

  1. verify Attempt 1's nine modules are byte-unmoved, and recheck the run span against the seal;
  2. load the development dataset through the Generation 2 window guard;
  3. run all thirty-six declared runs unconditionally — none is conditional on another's outcome;
  4. project them to the return-blind ``SelectionInputRA1`` records;
  5. apply the frozen selection rule;
  6. only then evaluate Gate 3, and only on the variant step 5 produced.

Steps 5 and 6 are in that order by construction rather than by convention: the selection is decided
from records carrying no performance figure at all, so no return computed in step 3 can reach it.
The descriptive eighteen-variant table is built last, after the verdict is already settled, for the
same reason — the seal requires it to be reported for every variant and to gate nothing.

Three things differ from Attempt 1's evidence module and each is deliberate:

``runs``
    built from :func:`~stockedge100.strategies.g2_runner_ra1.grid_report` rather than from a
    per-run ``to_json``. ``GridRunRA1`` deliberately has no ``to_json``; the grid report is the
    single place the sixteen sealed reported-but-not-gating quantities are produced, and having one
    producer is what keeps the run record and the variant table from disagreeing.

``determinism``
    compares a fourth digest, ``risk_state_digest``. ``reproducibility_requirements.determinism``
    requires byte-identical trade payloads, equity payloads, ranking digests **and risk-architecture
    state traces**; a rerun that reproduced identical trades from a different ladder history would
    satisfy Attempt 1's three-digest claim and violate Attempt 2's.

``candidate_results``
    carries the ``G2A2-CONFLICT-25`` restrictive resolution. SE100-CFG-3103 scopes the gate across
    both runs; SE100-CFG-3104 measures S3-C1 and S3-C4 on the base run. Neither outranks the other,
    so all seven conditions must hold on ``#BASE`` and S3-C1..S3-C6 must *also* hold on ``#STRESS``.
    Both condition sets are recorded in full, and the permissive base-only reading is recorded
    alongside so a reader can see what the looser reading would have given.

``generated_utc`` is read from the system clock at write time and never hand-typed.
``evidence_digest`` covers the body with ``generated_utc`` and ``evidence_digest`` themselves
removed, and :func:`finalize` puts every covered field in place — **including
``evidence_digest_covers`` itself** — before taking the digest.

The evidence lands in ``reports/``, outside the ``repo_state_id`` patterns, so writing it does not
perturb the digest the decision package will later record.

Usage::

    cd stockedge100 && PYTHONPATH=src python -m stockedge100.reporting.g2_stage3_attempt2_evidence
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from stockedge100.audit import (
    sha256_bytes,
    sha256_file,
    sha256_text_canonical_json,
    utc_now_iso,
)
from stockedge100.backtest.errors import ConfigViolation
from stockedge100.backtest.g2_engine_ra1 import load_risk_architecture
from stockedge100.strategies import g2_gate_ra1 as gate
from stockedge100.strategies import g2_runner_ra1 as runner
from stockedge100.strategies import g2_window_guard as guard

PROJECT_ROOT = Path(__file__).resolve().parents[3]

#: The seal names this exact path in ``adaptation_disclosure_carriage_requirement``. It is asserted
#: against that list rather than merely matching it by convention.
EVIDENCE_REL = "reports/stage3_g2_attempt2/STAGE_3_G2_A2_DEVELOPMENT_ADMISSIBILITY.json"

COMMAND = (
    "cd stockedge100 && PYTHONPATH=src python -m "
    "stockedge100.reporting.g2_stage3_attempt2_evidence"
)

#: Attempt 1's Generation 2 evidence is SE100-EVID-3101; Generation 1's Stage 3 evidence was
#: SE100-EVID-3001. 3102 is the next free id in the series and belongs to Attempt 2.
ARTIFACT_ID = "SE100-EVID-3102"

PROTOCOL_REL = "config/generation_2/g2_rotation_ra1_protocol.json"
CRITERIA_REL = "config/generation_2/g2_gate_criteria_ra1.json"
COST_MODEL_REL = "config/generation_2/g2_cost_model.json"
PARTITION_LOCK_REL = "governance/generation_2/STAGE_1_G2_PARTITION_LOCK.json"
CHARTER_REL = "governance/generation_2/STAGE_10_GENERATION_2_CHARTER.md"
GOVERNANCE_PROTOCOL_REL = "governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.json"
GOVERNANCE_PROTOCOL_MD_REL = "governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.md"

EXCLUDED_FROM_DIGEST = ("generated_utc", "evidence_digest")

DIGEST_COVERS = (
    "every field of this file except generated_utc and evidence_digest, as canonical JSON"
)

#: The four digests the sealed determinism requirement names, plus four scalars. The scalars are not
#: redundant: a digest proves the payload is identical, and a payload can be identical while the
#: measurement derived from it is not, if a measurement path changed between the two passes.
RUN_IDENTITY_FIELDS = (
    "trades_digest",
    "equity_digest",
    "ranking_digest",
    "risk_state_digest",
    "fills",
    "closed_trades",
    "total_return",
    "shutdown_session",
)


def evidence_digest(body: dict[str, Any]) -> str:
    """The digest of the findings, with the two non-finding fields removed."""

    return sha256_text_canonical_json(
        {key: value for key, value in body.items() if key not in EXCLUDED_FROM_DIGEST}
    )


def finalize(body: dict[str, Any], generated_utc: str) -> dict[str, Any]:
    """Add the three fields the run does not produce, then seal the body with its own digest."""

    body = dict(body)
    body["generated_utc"] = generated_utc
    body["command"] = COMMAND
    body["evidence_digest_covers"] = DIGEST_COVERS
    body["evidence_digest"] = evidence_digest(body)
    return body


def carried_disclosure(protocol: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """The adaptation disclosure, carried byte-identically, with its carriage obligation restated.

    The seal's ``enforcement`` reads "The sealer and the package builder both assert byte-equality of
    this string against the value in this file. A paraphrase is a failure, not a stylistic choice."
    This module is one of the five carriers the requirement names, so it checks that it is on the
    list rather than assuming it. The string carries em dashes as UTF-8 and is never printed to a
    console; only its length and its digest are.
    """
    text = protocol["adaptation_disclosure_verbatim"]
    requirement = protocol["adaptation_disclosure_carriage_requirement"]
    carriers = list(requirement["must_appear_verbatim_in"])
    if EVIDENCE_REL not in carriers:
        raise ConfigViolation(
            f"{EVIDENCE_REL} is not among the sealed carriers of the adaptation disclosure "
            f"{carriers!r}; either this module writes to the wrong path or the seal changed"
        )
    if not isinstance(text, str) or not text.strip():
        raise ConfigViolation("the sealed adaptation disclosure is empty or not a string")
    return text, {
        "must_appear_verbatim_in": carriers,
        "this_file_is_a_required_carrier": True,
        "enforcement": requirement["enforcement"],
        "encoding_note": requirement["encoding_note"],
        "characters": len(text),
        "sha256_of_utf8": sha256_bytes(text.encode("utf-8")),
        "sha256_covers": (
            "the disclosure encoded as UTF-8, with no quoting and no trailing newline, so a reader "
            "can extract the string and reproduce the digest with sha256sum"
        ),
        "carried_byte_identically_from": PROTOCOL_REL,
    }


def _run_digests(row: dict[str, Any]) -> dict[str, Any]:
    """The identity of one run, taken from its grid-report row.

    Four digests and three scalars. Digests alone would not catch a run that produced the same
    trades from a different ranking or a different ladder history; scalars alone would not catch a
    reordering. Reading them off the grid report rather than off the run object means the determinism
    claim is made about the same numbers the descriptive table publishes.
    """
    return {field: row[field] for field in RUN_IDENTITY_FIELDS}


def _by_run_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {f"{row['variant_id']}{row['label']}": row for row in rows}


#: What the variant table carries for each of a variant's two runs, taken from the grid report.
_PER_RUN_COLUMNS = (
    "total_return",
    "max_drawdown",
    "profit_factor",
    "closed_trades",
    "closed_episodes",
    "fills",
    "research_shutdown_events",
    "shutdown_session",
    "ladder_descents",
    "ladder_ascents",
    "ladder_deepest_band",
    "ladder_final_band",
    "ladder_sessions_in_band",
    "lockout_arms",
    "lockout_recoveries_blocked",
    "stops_triggered",
    "stops_filled",
    "stops_preempted_by_signal_exit",
    "throttle_legs_scheduled",
    "throttle_legs_below_min_notional",
    "throttle_sessions_breaching_ceiling",
    "max_gross_fraction_observed",
    "max_gross_fraction_session",
    "combined_scalar_minimum",
    "combined_scalar_mean",
    "combined_scalar_sessions_below_one",
    "volatility_scalar_minimum",
    "ranking_digest",
    "cagr",
    "sharpe",
    "exposure_fraction",
    "win_rate",
    "distinct_symbols_traded",
)

#: The two extra columns per run that ``grid_report`` cannot supply, computed in
#: :func:`reported_only_extras`.
_PER_RUN_EXTRA_COLUMNS = ("best_trade_removed_return", "stop_exits")

#: Each of the sixteen sealed reported-for-every-variant-but-not-gating quantities, mapped to the
#: table columns that carry it. The mapping exists so that the coverage claim is checkable against
#: the table rather than asserted in prose: :func:`variant_table` verifies every column named here
#: is present on every row, and the mapping is written into the evidence beside the table.
#:
#: Two of the sixteen are why :func:`reported_only_extras` exists at all. ``grid_report`` reports
#: stop *counts*, not the realized loss at each stop, and reports no best-trade-removed return for
#: any variant — that figure is a gate measurement, produced by ``condition_5_ra1``, which the gate
#: runs only for the representative. The seal requires both for every variant, so both are computed
#: for all thirty-six runs after the verdict is settled.
REPORTED_COVERAGE = (
    ("net return, both runs", ("total_return",)),
    ("maximum drawdown, both runs", ("max_drawdown",)),
    ("profit factor, both runs", ("profit_factor",)),
    ("closed trade count, both runs", ("closed_trades", "closed_episodes")),
    ("best-trade-removed return, both runs", ("best_trade_removed_return",)),
    (
        "research-shutdown event count and the session of each, both runs",
        ("research_shutdown_events", "shutdown_session"),
    ),
    ("total fill count, both runs", ("fills",)),
    ("de-risk ladder activations (downward transitions), both runs", ("ladder_descents",)),
    (
        "de-risk ladder upward transitions and deepest band reached, both runs",
        ("ladder_ascents", "ladder_deepest_band"),
    ),
    ("sessions spent in each ladder band, both runs", ("ladder_sessions_in_band",)),
    (
        "re-entry lockout arms and sessions on which a recovery was blocked by it, both runs",
        ("lockout_arms", "lockout_recoveries_blocked"),
    ),
    (
        "stop exits and the realized loss at each, both runs",
        ("stops_triggered", "stops_filled", "stops_preempted_by_signal_exit", "stop_exits"),
    ),
    (
        "throttle legs issued and throttle legs skipped below minimum notional, both runs",
        ("throttle_legs_scheduled", "throttle_legs_below_min_notional"),
    ),
    (
        "maximum observed gross exposure fraction, both runs",
        ("max_gross_fraction_observed", "max_gross_fraction_session"),
    ),
    (
        "minimum and mean combined risk scalar, and sessions on which it was below 1, both runs",
        ("combined_scalar_minimum", "combined_scalar_mean", "combined_scalar_sessions_below_one"),
    ),
    ("ranking digest, both runs", ("ranking_digest",)),
)


def reported_only_extras(
    runs: list[Any], criteria: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    """The two sealed reported-for-every-variant quantities the grid report cannot supply.

    ``best_trade_removed_return`` is S3-C5's measurement. For the representative it is a gate
    condition; for the other seventeen variants it is a descriptive figure the seal requires and
    nothing reads. Computing it here rather than in the gate is what keeps that distinction intact —
    ``condition_5_ra1`` is called on every run, its verdict is recorded, and only the
    representative's verdict is ever consulted by :func:`_combine_base_and_stress`.

    ``stop_exits`` is ``risk_summary()["stops"]["fills"]`` verbatim: one record per filled stop
    carrying the trigger close, the cost-basis reference price, and the drop at trigger and at fill.
    That is the "realized loss at each" the seal asks for.

    Called after the representative is chosen and the verdict is settled. Nothing computed here can
    reach the selection, which reads only ``SelectionInputRA1``'s four return-blind fields.
    """
    extras: dict[str, dict[str, Any]] = {}
    for run in runs:
        verdict = gate.condition_5_ra1(run.result, run.ledger, criteria)
        extras[run.run_id] = {
            "best_trade_removed_return": {
                "verdict": verdict.verdict,
                "measured": verdict.measured,
                "threshold": verdict.threshold,
                "note": verdict.note,
                "removals": verdict.evidence,
                "gating_for_this_variant": False,
            },
            "stop_exits": list(run.risk["stops"]["fills"]),
        }
    return extras


def variant_table(
    rows: list[dict[str, Any]], extras: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """The eighteen-variant descriptive table the seal requires and the gate ignores.

    One row per variant, with both declared runs side by side, built from the thirty-six grid-report
    rows so that the two records cannot disagree. Built after the verdict is settled; nothing here is
    an input to anything. ``research_shutdown_events`` is the sum across the two runs, which is the
    figure step 1 of the selection rule screens on — repeated here so a reader can check the
    selection against the table without recomputing it.

    The last loop is the coverage check. Every column named in :data:`REPORTED_COVERAGE` must be
    present, for both runs, on every row; a sealed quantity that silently went missing raises here
    rather than being discovered by a reader of the finished evidence.
    """
    by_variant: dict[str, dict[str, dict[str, Any]]] = {}
    order: dict[str, int] = {}
    for row in rows:
        by_variant.setdefault(row["variant_id"], {})[row["label"]] = row
        order[row["variant_id"]] = row["grid_index"]

    table: dict[str, Any]
    out: list[dict[str, Any]] = []
    for variant_id in sorted(by_variant, key=lambda v: order[v]):
        pair = by_variant[variant_id]
        base = pair[runner.GATE_RUN_LABEL]
        table = {
            "grid_index": base["grid_index"],
            "variant_id": variant_id,
            "lookback_months": base["lookback_months"],
            "top_k": base["top_k"],
            "rebalance_frequency": base["rebalance_frequency"],
            "research_shutdown_events": sum(
                int(run["research_shutdown_events"]) for run in pair.values()
            ),
            "fill_count_both_runs": sum(int(run["fills"]) for run in pair.values()),
            "ladder_descents_both_runs": sum(int(run["ladder_descents"]) for run in pair.values()),
            "lockout_arms_both_runs": sum(int(run["lockout_arms"]) for run in pair.values()),
            "stops_filled_both_runs": sum(int(run["stops_filled"]) for run in pair.values()),
        }
        for label, row in sorted(pair.items()):
            short = label.lstrip("#").lower()
            for column in _PER_RUN_COLUMNS:
                table[f"{short}_{column}"] = row[column]
            for column in _PER_RUN_EXTRA_COLUMNS:
                table[f"{short}_{column}"] = extras[f"{variant_id}{label}"][column]
        out.append(table)

    labels = sorted({row["label"].lstrip("#").lower() for row in rows})
    for row in out:
        for quantity, columns in REPORTED_COVERAGE:
            for column in columns:
                for short in labels:
                    if f"{short}_{column}" not in row:
                        raise ConfigViolation(
                            f"{row['variant_id']}: the sealed reported-for-every-variant quantity "
                            f"{quantity!r} names column {short}_{column}, which the table does not "
                            "carry"
                        )
    return out


def _combine_base_and_stress(
    base_eval: dict[str, Any], stress_eval: dict[str, Any], scope: dict[str, Any]
) -> dict[str, Any]:
    """Apply the ``G2A2-CONFLICT-25`` restrictive resolution and record both readings.

    All seven conditions must be satisfied on ``#BASE``. S3-C1..S3-C6 must *also* be satisfied on
    ``#STRESS``, because ``runs_per_variant.both_gate`` says a variant satisfies a condition only if
    both of its runs satisfy it. S3-C7 is evaluated once, on base runs: its own ``what_is_read``
    fixes the neighbour side to base-run total return, so a stress-side answer would compare a
    stress-run return against base-run neighbours — a mixed basis the seal gives no authority for. It
    is computed, recorded, and not used.

    Satisfaction rather than ``verdict == "MET"`` is what aggregates, because
    ``NOT_APPLICABLE_BY_CONDITION_TEXT`` is satisfied without being met. Aggregating on ``MET``
    produced a false ``FAIL`` for S3-C6 in Generation 1's Stage 3 and is not repeated here.
    """
    stress_gating = [c for c in stress_eval["conditions"] if c["id"] != "S3-C7"]
    stress_reported_only = [c for c in stress_eval["conditions"] if c["id"] == "S3-C7"]
    if len(stress_gating) != 6 or len(stress_reported_only) != 1:
        raise ConfigViolation(
            f"the stress evaluation returned {len(stress_eval['conditions'])} conditions of which "
            f"{len(stress_reported_only)} are S3-C7; the restrictive resolution was written against "
            "seven conditions of which exactly one is S3-C7"
        )

    base_ok = bool(base_eval["admitted"])
    stress_ok = all(c["satisfied"] for c in stress_gating)

    combined = dict(base_eval)
    combined["admitted"] = base_ok and stress_ok
    combined["admission_basis"] = {
        "conflict_ref": scope["conflict_ref"],
        "resolution": scope["scope_resolution"],
        "evaluated_on": scope["evaluated_on"],
        "conjunctive": scope["conjunctive"],
        "both_gate": scope["both_gate"],
        "criteria_source": scope["criteria_source"],
        "neighbour_run_label": scope["neighbour_run_label"],
        "base_all_seven_satisfied": base_ok,
        "stress_first_six_satisfied": stress_ok,
        "base_conditions_not_satisfied": sorted(
            c["id"] for c in base_eval["conditions"] if not c["satisfied"]
        ),
        "stress_conditions_not_satisfied": sorted(
            c["id"] for c in stress_gating if not c["satisfied"]
        ),
        "s3_c7_stress_side_reported_not_gating": stress_reported_only[0],
        "permissive_base_only_reading_would_give": base_ok,
        "aggregated_on": (
            "satisfied, not verdict == MET; NOT_APPLICABLE_BY_CONDITION_TEXT is satisfied without "
            "being met"
        ),
    }
    combined["stress_evaluation"] = stress_eval
    return combined


def run_all_g2_attempt2() -> dict[str, Any]:
    """Execute the stage and assemble the body. No field here is hand-typed."""

    protocol = runner.load_protocol()
    criteria = gate.load_criteria()
    architecture = load_risk_architecture(protocol)
    window = guard.stage_3_window()
    bound = guard.development_bound()
    disclosure, carriage = carried_disclosure(protocol)

    # AT-H first: if any Attempt 1 module moved, nothing this session measures is trustworthy and
    # the run should stop before it reads a single bar.
    module_verification = runner.verify_attempt_1_modules()
    if module_verification["modules_that_moved"]:
        raise ConfigViolation(
            "Attempt 1 modules moved: " + repr(module_verification["modules_that_moved"])
        )

    series = runner.load_grid_dataset()
    latest = max(one.sessions[-1] for one in series.values())
    if latest > bound:
        raise guard.WindowViolation(
            f"a bar dated {latest} survived the guarded load; the development bound is {bound}"
        )
    span_recheck = runner.recheck_run_span(series, protocol=protocol)

    runs = runner.run_grid(series, verify=True)
    rows = runner.grid_report(runs)
    inputs = runner.selection_inputs(runs)
    selection = runner.select_representative(inputs)

    candidate_results: list[dict[str, Any]] = []
    gate_scope: dict[str, Any] | None = None
    if selection["representative_exists"]:
        scope = runner.gate_inputs(
            runs, selection["representative_variant_id"], criteria=criteria
        )
        gate_scope = {
            "variant_id": scope["variant"].variant_id,
            "evaluated_on": scope["evaluated_on"],
            "conjunctive": scope["conjunctive"],
            "both_gate": scope["both_gate"],
            "criteria_source": scope["criteria_source"],
            "conflict_ref": scope["conflict_ref"],
            "scope_resolution": scope["scope_resolution"],
            "neighbour_run_label": scope["neighbour_run_label"],
            "neighbours": [member.variant_id for member, _ in scope["neighbours"]],
        }
        base_eval = gate.evaluate_representative_ra1(
            variant=scope["variant"],
            primary=scope["primary"],
            neighbours=scope["neighbours"],
            criteria=criteria,
            ledger=scope["primary_run"].ledger,
        )
        stress_eval = gate.evaluate_representative_ra1(
            variant=scope["variant"],
            primary=scope["stress"],
            neighbours=scope["neighbours"],
            criteria=criteria,
            ledger=scope["stress_run"].ledger,
        )
        candidate_results.append(_combine_base_and_stress(base_eval, stress_eval, scope))

    verdict = gate.stage_verdict_ra1(
        candidate_results,
        criteria,
        representative_exists=selection["representative_exists"],
        selection_note=selection["selection_note"],
    )

    # Only now, with the verdict settled, are the two descriptive quantities computed that the gate
    # itself produces for one variant. Their position in this function is the argument that they
    # could not have influenced anything.
    extras = reported_only_extras(runs, criteria)

    # Determinism is claimed for the whole grid, not for a sample: the dataset is reloaded from disk
    # and every run repeated on fresh strategy and engine objects. RA2's band, lockout counter and
    # volatility state are engine state, so a reused engine would begin the replay inside the first
    # pass's drawdown ladder and the comparison would be worthless.
    replay_rows = runner.grid_report(runner.run_grid(runner.load_grid_dataset(), verify=True))
    first = {run_id: _run_digests(row) for run_id, row in _by_run_id(rows).items()}
    second = {run_id: _run_digests(row) for run_id, row in _by_run_id(replay_rows).items()}
    mismatched = sorted(
        key for key in first if key not in second or first[key] != second[key]
    )
    mismatched += sorted(key for key in second if key not in first)

    reconciliation = {
        "rule": "evaluation_integrity_rules section 8, run on every run and not only the representative's",
        "runs_reconciled": len(runs),
        "single_leg_compared_total": sum(int(r["reconciliation_single_leg_compared"]) for r in rows),
        "mismatches_total": sum(int(r["reconciliation_mismatches"]) for r in rows),
        "vacuous_runs": sorted(
            f"{r['variant_id']}{r['label']}" for r in rows if r["reconciliation_vacuous"]
        ),
        "conflict_ref": "G2A2-CONFLICT-26",
        "vacuity_rule_as_implemented": (
            "assert_reconciliation_non_vacuous halts only when closed_episodes > 0 and "
            "single_leg_compared == 0; a run that closed no episode at all is vacuous without being "
            "a defect, and is recorded rather than raised on"
        ),
    }

    return {
        "artifact_id": ARTIFACT_ID,
        "project": "StockEdge100",
        "generation": 2,
        "generation_id": protocol["generation_id"],
        "attempt": protocol["attempt"],
        "stage": "STAGE_3_G2_ATTEMPT_2_ROTATION_RA1_DEVELOPMENT",
        "gate": {"constitution_gate_id": 3, "name": "development_admissibility"},
        "strategy_id": protocol["strategy_id"],
        "candidate_index": protocol["candidate_index"],
        "family": protocol["family"],
        "hypothesis": protocol["hypothesis"],
        "what_this_attempt_adds_over_attempt_1": protocol[
            "what_this_attempt_adds_over_attempt_1"
        ],
        "adaptation_disclosure_verbatim": disclosure,
        "adaptation_disclosure_carriage": carriage,
        "attempt_1_ref": protocol["attempt_1_ref"],
        "attempt_1_module_verification": module_verification,
        "sealed_inputs": {
            "protocol": PROTOCOL_REL,
            "protocol_artifact_id": protocol["artifact_id"],
            "protocol_sha256": sha256_file(PROJECT_ROOT / PROTOCOL_REL),
            "criteria": CRITERIA_REL,
            "criteria_artifact_id": criteria["artifact_id"],
            "criteria_sha256": sha256_file(PROJECT_ROOT / CRITERIA_REL),
            "governance_protocol_json": GOVERNANCE_PROTOCOL_REL,
            "governance_protocol_json_sha256": sha256_file(
                PROJECT_ROOT / GOVERNANCE_PROTOCOL_REL
            ),
            "governance_protocol_md": GOVERNANCE_PROTOCOL_MD_REL,
            "governance_protocol_md_sha256": sha256_file(
                PROJECT_ROOT / GOVERNANCE_PROTOCOL_MD_REL
            ),
            "cost_model": COST_MODEL_REL,
            "cost_model_sha256": sha256_file(PROJECT_ROOT / COST_MODEL_REL),
            "partition_lock": PARTITION_LOCK_REL,
            "partition_lock_sha256": sha256_file(PROJECT_ROOT / PARTITION_LOCK_REL),
            "charter": CHARTER_REL,
            "charter_sha256": sha256_file(PROJECT_ROOT / CHARTER_REL),
            "declared_before_any_strategy_code": protocol["declared_before_any_strategy_code"],
            "declared_before_any_strategy_code_measurement": protocol[
                "declared_before_any_strategy_code_measurement"
            ],
        },
        "window": {
            "name": window.name,
            "start": window.start.isoformat(),
            "end": window.end.isoformat(),
            "development_bound": bound.isoformat(),
            "run_span": protocol["run_span"],
            "latest_session_loaded": latest.isoformat(),
            "validation_read": False,
            "generation_1_holdout_read": False,
            "generation_2_holdout_read": False,
            "enforcement": (
                "load_grid_dataset truncates at the development bound and then audits the loaded "
                "bars separately, so a session dated 2021-08-01 or later would have to survive both "
                "a truncating loader and an independent check of its output"
            ),
        },
        "run_span_recheck": span_recheck,
        "universe": {
            "universe_version": protocol["eligible_universe"]["universe_version"],
            "universe_identity_sha256": protocol["eligible_universe"]["universe_identity_sha256"],
            "symbols_declared": protocol["eligible_universe"]["member_count"],
            "symbols_loaded": len(series),
            "symbols_missing": sorted(
                set(protocol["eligible_universe"]["members"]) - set(series)
            ),
            "unchanged_from_attempt_1": protocol["eligible_universe"]["unchanged_from_attempt_1"],
            "eligibility_recheck_convention": protocol["eligible_universe"][
                "eligibility_recheck_convention"
            ],
            "excluded_symbols": protocol["eligible_universe"]["excluded_symbols"],
        },
        "risk_architecture": {
            "sealed": protocol["risk_architecture"],
            "as_loaded": architecture.to_json(),
            "frozen_before_any_variant_is_run": protocol["risk_architecture"][
                "frozen_before_any_variant_is_run"
            ],
            "not_part_of_the_grid": protocol["risk_architecture"]["not_part_of_the_grid"],
            "gridded": False,
            "tuned_after_seeing_a_result": False,
        },
        "grid": {
            "axes": protocol["grid"]["axes"],
            "variants_declared": protocol["grid"]["size"],
            "runs_per_variant": protocol["runs_per_variant"],
            "runs_executed": len(runs),
            "all_declared_runs_executed": len(runs)
            == int(protocol["runs_per_variant"]["total_runs"]),
            "revisions_after_seeing_a_result": 0,
            "grid_widened_from_attempt_1": False,
        },
        "runs": rows,
        "selection_inputs": [entry.to_json() for entry in inputs],
        "selection": selection,
        "gate_scope": gate_scope,
        "candidate_results": candidate_results,
        "stage_verdict": verdict,
        "reconciliation": reconciliation,
        "determinism": {
            "method": (
                "the dataset was reloaded from disk and all thirty-six runs repeated on fresh "
                "strategy and engine objects; each run is compared on its trade digest, equity "
                "digest, ranking digest, risk-architecture state digest, fill count, closed-trade "
                "count, total return and shutdown session"
            ),
            "requirement": protocol["reproducibility_requirements"]["determinism"],
            "fields_compared": list(RUN_IDENTITY_FIELDS),
            "runs_compared": len(first),
            "all_identical": not mismatched,
            "mismatched_runs": mismatched,
            "run_digests": first,
        },
        "variant_table": variant_table(rows, extras),
        "variant_table_is_descriptive_only": protocol[
            "reported_for_every_variant_but_not_gating"
        ],
        "reported_for_every_variant_coverage": {
            "rule": (
                "each sealed reported-but-not-gating quantity, and the variant_table columns "
                "carrying it for each of the two declared runs; verified against every row of the "
                "table at build time, not asserted"
            ),
            "quantities": len(REPORTED_COVERAGE),
            "quantities_sealed": len(protocol["reported_for_every_variant_but_not_gating"]),
            "map": [
                {"quantity": quantity, "columns": list(columns)}
                for quantity, columns in REPORTED_COVERAGE
            ],
            "not_supplied_by_grid_report": {
                "columns": list(_PER_RUN_EXTRA_COLUMNS),
                "reason": (
                    "grid_report reports stop counts but not the realized loss at each stop, and "
                    "reports no best-trade-removed return for any variant because that figure is a "
                    "gate measurement the gate runs only for the representative; both are required "
                    "for every variant, so both are computed for all thirty-six runs after the "
                    "verdict was settled"
                ),
                "source": (
                    "stop_exits is risk_summary()['stops']['fills'] verbatim; "
                    "best_trade_removed_return is condition_5_ra1 called per run"
                ),
                "gating_for_any_variant_other_than_the_representative": False,
            },
        },
        "multiple_comparisons_disclosure": protocol["multiple_comparisons_disclosure"],
        "representative_selection_rule": protocol["representative_selection_rule"],
        "gate_evaluation_scope": protocol["gate_evaluation_scope"],
        "structural_consequences_declared_before_running": protocol[
            "structural_consequences_declared_before_running"
        ],
        "explicit_non_authorizations": protocol["explicit_non_authorizations"],
        "live_trading_authorized": False,
    }


def build() -> int:
    body = finalize(run_all_g2_attempt2(), utc_now_iso())

    path = PROJECT_ROOT / EVIDENCE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    print(f"generated_utc     {body['generated_utc']}")
    print(f"evidence_digest   {body['evidence_digest']}")
    print(f"runs_executed     {body['grid']['runs_executed']}")
    print(f"determinism       {body['determinism']['all_identical']}")
    print(f"disclosure_chars  {body['adaptation_disclosure_carriage']['characters']}")
    print(f"representative    {body['selection']['representative_variant_id']}")
    print(f"decided_at_step   {body['selection']['decided_at_step']}")
    for row in body["variant_table"]:
        print(
            f"  {row['variant_id']:<48} shutdowns={row['research_shutdown_events']} "
            f"fills={row['fill_count_both_runs']:<5} ladder={row['ladder_descents_both_runs']:<4} "
            f"lockouts={row['lockout_arms_both_runs']:<4} base_return={row['base_total_return']}"
        )
    if body["candidate_results"]:
        basis = body["candidate_results"][0]["admission_basis"]
        print(f"base_not_satisfied   {basis['base_conditions_not_satisfied']}")
        print(f"stress_not_satisfied {basis['stress_conditions_not_satisfied']}")
        print(f"admitted             {body['candidate_results'][0]['admitted']}")
    print(
        f"stage_verdict     {body['stage_verdict']['verdict']} "
        f"{body['stage_verdict']['verdict_token']}"
    )
    print(f"route             {body['stage_verdict']['route']}")
    print(f"wrote             {EVIDENCE_REL}")

    # The stage verdict is a finding, not an error. A FAIL here is the outcome the sealed
    # second_fail_path anticipated, and the file is the deliverable either way.
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
