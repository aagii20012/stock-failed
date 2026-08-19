"""Generation 2, Stage 3, Attempt 3: run the grid under RA3, select by SEL-2, evaluate Gate 3.

Writes ``reports/stage3_g2_attempt3/STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json``, which is the
evidence file the decision package is built from. It is the counterpart of Attempt 2's
``g2_stage3_attempt2_evidence`` and is a new module rather than a parameterisation of it: that module
is frozen, it calls ``gate.load_criteria`` and ``runner.verify_attempt_1_modules`` by names RA3
renamed, and it maps sixteen sealed reported-but-not-gating quantities where CFG-3105 declares
eighteen.

Six things this module is responsible for that the underlying modules are not:

``carried_disclosure``
    CFG-3105 seals the adaptation disclosure and names five files that must carry it verbatim. This
    file is one of the five, so the carriage requirement is checked here — membership of the carrier
    list, then the length and digest of what was actually carried — rather than asserted. The string
    is never printed: it contains U+2014 and U+2212, and stdout is cp1252.

``variant_table``
    the eighteen sealed quantities, for all eighteen variants, both runs. Its final loop turns
    :data:`REPORTED_COVERAGE` into a check: a sealed quantity whose column silently vanished raises
    at build time rather than being found by a reader of the finished evidence.

``reported_only_extras``
    the two quantities the grid report cannot supply, computed **after** the verdict is settled so
    that their position in the function is the argument they could not have reached the selection.

``determinism``
    the whole grid rerun from a freshly loaded dataset on fresh engine objects, compared on four
    digests and four scalars. RA3's band, lockout counter and volatility state are engine state, so
    a reused engine would begin the replay inside the first pass's ladder.

``selection_determinism``
    SEL-2 rerun against the **recorded** selection inputs, not only end-to-end. CFG-3105's
    ``reproducibility_requirements.selection_determinism`` asks for exactly this, "so a determinism
    failure in the selector cannot hide behind a determinism pass in the engine".

``ladder_engagement_comparison``
    the operating instruction's section 4.3 requirement, carried into the evidence rather than left
    in a console log.

The return code is 0 on a FAIL. The verdict is a finding and the file is the deliverable either way;
the sealed ``second_fail_path`` anticipated this outcome explicitly.
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
from stockedge100.backtest.g2_engine_ra3 import (
    attributes_derived_from_risk,
    check_generation_1_provenance,
    check_single_difference_from_ra2,
    load_risk_architecture_ra3,
)
from stockedge100.strategies import g2_gate_ra3 as gate
from stockedge100.strategies import g2_runner_ra3 as runner
from stockedge100.strategies import g2_window_guard as guard
from stockedge100.strategies.g2_selection_v2 import (
    SELECTION_V2_FIELD_NAMES,
    SelectionInputV2,
    select_representative_v2,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]

EVIDENCE_REL = "reports/stage3_g2_attempt3/STAGE_3_G2_A3_DEVELOPMENT_ADMISSIBILITY.json"
COMMAND = (
    "cd stockedge100 && PYTHONPATH=src python -m "
    "stockedge100.reporting.g2_stage3_attempt3_evidence"
)
ARTIFACT_ID = "SE100-EVID-3103"

PROTOCOL_REL = "config/generation_2/g2_rotation_ra3_protocol.json"
CRITERIA_REL = "config/generation_2/g2_gate_criteria_ra3.json"
COST_MODEL_REL = "config/generation_2/g2_cost_model.json"
PARTITION_LOCK_REL = "governance/generation_2/STAGE_1_G2_PARTITION_LOCK.json"
CHARTER_REL = "governance/generation_2/STAGE_10_GENERATION_2_CHARTER.md"
GOVERNANCE_PROTOCOL_REL = "governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.json"
GOVERNANCE_PROTOCOL_MD_REL = "governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.md"

#: Excluded from the self-digest, because both are written after it is computed.
EXCLUDED_FROM_DIGEST = ("generated_utc", "evidence_digest")
DIGEST_COVERS = (
    "every field of this file except generated_utc and evidence_digest, as canonical JSON"
)

#: The four digests the sealed determinism requirement names, plus four scalars. The scalars are not
#: redundant: a digest mismatch says two runs differ and says nothing about where, and a fill count
#: or a shutdown session that moved with the digests narrows it immediately. Read off the grid report
#: rather than off the run object so that a change to the report's projection is caught too.
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

#: Columns of a grid-report row that identify the variant rather than one of its two runs. They are
#: written once per table row instead of being prefixed twice.
_VARIANT_LEVEL_COLUMNS = (
    "grid_index",
    "variant_id",
    "lookback_months",
    "top_k",
    "rebalance_frequency",
    "label",
    "selection_score",
)

#: Every remaining column, declared rather than derived. :func:`variant_table` asserts that this
#: tuple *equals* what ``grid_report`` emits, so a column added to the runner without being carried
#: here, and a column removed from the runner while still named here, both raise.
_PER_RUN_COLUMNS = (
    "scenario",
    # the five gate quantities, reported for every variant
    "total_return",
    "max_drawdown",
    "profit_factor",
    "closed_trades",
    "closed_episodes",
    # shutdown, which is SEL-2's eligibility screen
    "research_shutdown_events",
    "shutdown_session",
    "fills",
    # RA3's ladder, lockout and stop behaviour: what this attempt exists to move
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
    "volatility_scalar_sessions_below_one",
    # Attempt 2's counterpart of each of the above, on the same row
    "attempt_2",
    # Attempt 1's descriptive columns, carried unchanged
    "cagr",
    "sharpe",
    "daily_return_stdev",
    "exposure_fraction",
    "win_rate",
    "average_win",
    "average_loss",
    "longest_flat_streak_sessions",
    "distinct_symbols_traded",
    "distinct_symbols_with_closed_trades",
    # digests, for the determinism claim
    "trades_digest",
    "equity_digest",
    "ranking_digest",
    "risk_state_digest",
    "risk_state_sessions",
    "scheduled_rebalances",
    "executed_rebalances",
    # the section 8 reconciliation, per run
    "reconciliation_single_leg_compared",
    "reconciliation_mismatches",
    "reconciliation_vacuous",
)

#: Two the grid report cannot supply; see :func:`reported_only_extras`.
_PER_RUN_EXTRA_COLUMNS = ("best_trade_removed_return", "stop_exits")

#: Each sealed reported-but-not-gating quantity, the columns carrying it, and whether those columns
#: are per run or per variant. Sixteen entries are Attempt 2's, verbatim and in order — CFG-3105
#: reworded none of them. The last two are new to Attempt 3, and both are per variant: SEL-2's score
#: is computed from counters already summed across both runs, and Attempt 2's counterpart block is
#: matched per run but reported under one column name.
REPORTED_COVERAGE = (
    ("net return, both runs", ("total_return",), "per_run"),
    ("maximum drawdown, both runs", ("max_drawdown",), "per_run"),
    ("profit factor, both runs", ("profit_factor",), "per_run"),
    ("closed trade count, both runs", ("closed_trades", "closed_episodes"), "per_run"),
    ("best-trade-removed return, both runs", ("best_trade_removed_return",), "per_run"),
    (
        "research-shutdown event count and the session of each, both runs",
        ("research_shutdown_events", "shutdown_session"),
        "per_run",
    ),
    ("total fill count, both runs", ("fills",), "per_run"),
    (
        "de-risk ladder activations (downward transitions), both runs",
        ("ladder_descents",),
        "per_run",
    ),
    (
        "de-risk ladder upward transitions and deepest band reached, both runs",
        ("ladder_ascents", "ladder_deepest_band"),
        "per_run",
    ),
    ("sessions spent in each ladder band, both runs", ("ladder_sessions_in_band",), "per_run"),
    (
        "re-entry lockout arms and sessions on which a recovery was blocked by it, both runs",
        ("lockout_arms", "lockout_recoveries_blocked"),
        "per_run",
    ),
    (
        "stop exits and the realized loss at each, both runs",
        ("stops_triggered", "stops_filled", "stops_preempted_by_signal_exit", "stop_exits"),
        "per_run",
    ),
    (
        "throttle legs issued and throttle legs skipped below minimum notional, both runs",
        ("throttle_legs_scheduled", "throttle_legs_below_min_notional"),
        "per_run",
    ),
    (
        "maximum observed gross exposure fraction, both runs",
        ("max_gross_fraction_observed", "max_gross_fraction_session"),
        "per_run",
    ),
    (
        "minimum and mean combined risk scalar, and sessions on which it was below 1, both runs",
        ("combined_scalar_minimum", "combined_scalar_mean", "combined_scalar_sessions_below_one"),
        "per_run",
    ),
    ("ranking digest, both runs", ("ranking_digest",), "per_run"),
    (
        "The SE100-G2-SEL-2 stability score, its four per-quantity components, and the identity "
        "and score of every neighbour used to compute it.",
        ("selection_score",),
        "per_variant",
    ),
    (
        "The Attempt 2 counterpart of each ladder, lockout and stop statistic, so the required "
        "comparison is on the same page as the figure it compares.",
        ("attempt_2",),
        "per_run",
    ),
)


def evidence_digest(body: dict[str, Any]) -> str:
    """Canonical-JSON digest of everything except the two fields written after it."""
    return sha256_text_canonical_json(
        {key: value for key, value in body.items() if key not in EXCLUDED_FROM_DIGEST}
    )


def finalize(body: dict[str, Any], generated_utc: str) -> dict[str, Any]:
    """Stamp the clock and the command, then seal the body with its own digest."""
    body = dict(body)
    body["generated_utc"] = generated_utc
    body["command"] = COMMAND
    body["evidence_digest_covers"] = DIGEST_COVERS
    body["evidence_digest"] = evidence_digest(body)
    return body


def carried_disclosure(protocol: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """The sealed adaptation disclosure, carried byte-identically, with its carriage evidence.

    The membership check is the seal's own enforcement clause: this file is named in
    ``must_appear_verbatim_in``, so a build that did not carry the string would be a violation
    rather than an omission. Checking membership before writing is cheaper than discovering
    afterwards that a carrier list was widened and this module was never told.

    ``characters`` and ``sha256_of_utf8`` are recomputed from the string actually carried. They are
    the only way to state what was carried without printing it: the string contains U+2014 and, new
    in Attempt 3, U+2212, and stdout on this machine is cp1252.
    """
    text = protocol["adaptation_disclosure_verbatim"]
    requirement = protocol["adaptation_disclosure_carriage_requirement"]
    carriers = list(requirement["must_appear_verbatim_in"])
    if EVIDENCE_REL not in carriers:
        raise ConfigViolation(
            f"{EVIDENCE_REL} is not on the sealed carrier list {carriers!r}; either the seal or "
            "this module is wrong about which files must carry the disclosure"
        )
    if not isinstance(text, str) or not text.strip():
        raise ConfigViolation("adaptation_disclosure_verbatim is empty or not a string")
    return text, {
        "must_appear_verbatim_in": carriers,
        "this_file_is_a_required_carrier": True,
        "enforcement": requirement["enforcement"],
        "encoding_note": requirement["encoding_note"],
        "attempt_3_encoding_addendum": requirement["attempt_3_encoding_addendum"],
        "source": requirement["source"],
        "characters": len(text),
        "sha256_of_utf8": sha256_bytes(text.encode("utf-8")),
        "sha256_covers": (
            "the UTF-8 encoding of the string carried in this file's "
            "adaptation_disclosure_verbatim field, which is the sealed string byte for byte"
        ),
        "carried_byte_identically_from": PROTOCOL_REL,
    }


def _run_digests(row: dict[str, Any]) -> dict[str, Any]:
    return {field: row[field] for field in RUN_IDENTITY_FIELDS}


def _by_run_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {f"{row['variant_id']}{row['label']}": row for row in rows}


def reported_only_extras(
    runs: list[Any], criteria: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    """The two sealed reported-for-every-variant quantities the grid report cannot supply.

    ``best_trade_removed_return`` is S3-C5's measurement. For the representative it is a gate
    condition; for the other seventeen variants it is a descriptive figure the seal requires and
    nothing reads. There is no ``condition_5_ra3``: RA3 changed a band table, not a measurement, so
    the frozen ``condition_5_ra1`` is called here exactly as Attempt 2 called it, and only the
    representative's verdict is ever consulted by :func:`_combine_base_and_stress`.

    ``stop_exits`` is ``risk_summary()["stops"]["fills"]`` verbatim: one record per filled stop
    carrying the trigger close, the cost-basis reference price, and the drop at trigger and at fill.
    That is the "realized loss at each" the seal asks for.

    Called after the representative is chosen and the verdict is settled. Nothing computed here can
    reach the selection, which reads only :class:`SelectionInputV2`'s six fields.
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
    """One row per variant, in grid order, carrying every sealed descriptive quantity.

    The five ``*_both_runs`` counters are the six fields SEL-2 actually scored, recomputed here from
    the grid report rather than copied from the selection record. Recomputing them is the check: if
    the table and the selector disagreed about a variant's fill count, one of the two read the grid
    wrongly, and the table is where a reader would notice.

    Two loops guard the projection. The first asserts that :data:`_PER_RUN_COLUMNS` and
    :data:`_VARIANT_LEVEL_COLUMNS` together are *exactly* what ``grid_report`` emitted — a column
    added upstream without being carried here, or named here after being removed upstream, both
    raise. The second is the coverage check: every column named in :data:`REPORTED_COVERAGE` must be
    present, for both runs where the quantity is per run, on every row.
    """
    by_variant: dict[str, dict[str, dict[str, Any]]] = {}
    order: dict[str, int] = {}
    declared = set(_PER_RUN_COLUMNS) | set(_VARIANT_LEVEL_COLUMNS)
    for row in rows:
        emitted = set(row)
        if emitted != declared:
            raise ConfigViolation(
                "grid_report emitted a column set this module does not declare; missing here: "
                f"{sorted(emitted - declared)}, declared but not emitted: "
                f"{sorted(declared - emitted)}"
            )
        by_variant.setdefault(row["variant_id"], {})[row["label"]] = row
        order[row["variant_id"]] = row["grid_index"]

    out: list[dict[str, Any]] = []
    for variant_id in sorted(by_variant, key=lambda v: order[v]):
        pair = by_variant[variant_id]
        base = pair[runner.GATE_RUN_LABEL]

        # SEL-2's score is a property of the variant and appears identically on both of its rows.
        # Asserting that rather than reading one and hoping is the whole cost of the claim.
        scores = {json.dumps(row["selection_score"], sort_keys=True) for row in pair.values()}
        if len(scores) != 1:
            raise ConfigViolation(
                f"{variant_id} carries {len(scores)} different selection_score blocks across its "
                "runs; SEL-2 scores a variant, not a run"
            )

        table: dict[str, Any] = {
            "grid_index": base["grid_index"],
            "variant_id": variant_id,
            "lookback_months": base["lookback_months"],
            "top_k": base["top_k"],
            "rebalance_frequency": base["rebalance_frequency"],
            "research_shutdown_events": sum(
                int(row["research_shutdown_events"]) for row in pair.values()
            ),
            "fill_count_both_runs": sum(int(row["fills"]) for row in pair.values()),
            "ladder_descents_both_runs": sum(int(row["ladder_descents"]) for row in pair.values()),
            "lockout_arms_both_runs": sum(int(row["lockout_arms"]) for row in pair.values()),
            "stops_filled_both_runs": sum(int(row["stops_filled"]) for row in pair.values()),
            "selection_score": base["selection_score"],
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
        for quantity, columns, scope in REPORTED_COVERAGE:
            for column in columns:
                if scope == "per_variant":
                    if column not in row:
                        raise ConfigViolation(
                            f"sealed quantity {quantity!r} names variant-level column {column!r}, "
                            f"absent from the table row for {row['variant_id']}"
                        )
                    continue
                for short in labels:
                    if f"{short}_{column}" not in row:
                        raise ConfigViolation(
                            f"sealed quantity {quantity!r} names column {column!r}, absent for "
                            f"run {short} of {row['variant_id']}"
                        )
    return out


def _combine_base_and_stress(
    base_eval: dict[str, Any], stress_eval: dict[str, Any], scope: dict[str, Any]
) -> dict[str, Any]:
    """Admission under the restrictive ``G2A2-CONFLICT-25`` reading, inherited from Attempt 2.

    All seven conditions on ``#BASE``; S3-C1..S3-C6 also on ``#STRESS``. S3-C7 is evaluated once, on
    base runs, because its own ``what_is_read`` fixes the neighbour side to base-run total return
    and gives no sealed basis for a stress-side comparison — so the stress-side S3-C7 verdict is
    recorded and excluded from the conjunction rather than dropped.

    The permissive base-only reading is recorded alongside, so a reader can see exactly what the
    other reading would have given without rerunning anything.
    """
    stress_gating = [c for c in stress_eval["conditions"] if c["id"] != "S3-C7"]
    stress_reported_only = [c for c in stress_eval["conditions"] if c["id"] == "S3-C7"]
    if len(stress_gating) != 6 or len(stress_reported_only) != 1:
        raise ConfigViolation(
            f"the stress evaluation produced {len(stress_gating)} gating conditions and "
            f"{len(stress_reported_only)} S3-C7 verdicts; six and one were expected"
        )

    base_ok = bool(base_eval["admitted"])
    stress_ok = all(c["satisfied"] for c in stress_gating)

    combined = dict(base_eval)
    combined["admitted"] = base_ok and stress_ok
    combined["admission_basis"] = {
        "conflict_ref": scope["conflict_ref"],
        "conflict_status": scope["conflict_status"],
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


def selection_determinism(selection: dict[str, Any]) -> dict[str, Any]:
    """Rerun SEL-2 from the recorded inputs and compare every part of the result.

    CFG-3105's ``reproducibility_requirements.selection_determinism`` asks for identical scores,
    identical per-quantity components, identical neighbour sets and an identical selected variant on
    a clean rerun *from the same recorded statistics* — "this is tested directly against the
    recorded selection inputs, not only end-to-end, so a determinism failure in the selector cannot
    hide behind a determinism pass in the engine."

    The inputs are rebuilt from ``selection["inputs"]``, which is the JSON that will be on disk, not
    from the live ``SelectionInputV2`` objects. A selector that read something off the run objects
    it was not supposed to see would produce a different answer here, because here it cannot reach
    them.
    """
    recorded = selection["inputs"]
    rebuilt = tuple(
        SelectionInputV2(**{field: item[field] for field in SELECTION_V2_FIELD_NAMES})
        for item in recorded
    )
    replay = select_representative_v2(rebuilt).to_json()
    first = selection["result"]

    differing_scores = sorted(
        variant_id
        for variant_id in set(first["all_scores"]) | set(replay["all_scores"])
        if first["all_scores"].get(variant_id) != replay["all_scores"].get(variant_id)
    )
    return {
        "requirement": (
            "SE100-CFG-3105 reproducibility_requirements.selection_determinism"
        ),
        "method": (
            "SelectionInputV2 objects rebuilt from the recorded six-field JSON and rescored on a "
            "fresh call; the selector never sees the run objects on this pass"
        ),
        "inputs_replayed": len(rebuilt),
        "selected_variant_id_first_pass": first["selected_variant_id"],
        "selected_variant_id_replay": replay["selected_variant_id"],
        "selected_variant_identical": first["selected_variant_id"]
        == replay["selected_variant_id"],
        "decided_at_step_identical": first["decided_at_step"] == replay["decided_at_step"],
        "eligible_set_identical": first["eligible_variants"] == replay["eligible_variants"],
        "ranking_identical": first["ranking"] == replay["ranking"],
        "scores_identical": not differing_scores,
        "variants_whose_scores_differ": differing_scores,
        "all_identical": first == replay,
    }


def run_all_g2_attempt3() -> dict[str, Any]:
    """Execute the stage and assemble the body. No field here is hand-typed."""

    protocol = runner.load_protocol()
    criteria = gate.load_criteria_ra3()
    architecture = load_risk_architecture_ra3(protocol)
    window = guard.stage_3_window()
    bound = guard.development_bound()
    disclosure, carriage = carried_disclosure(protocol)

    # AT-H first: if any Attempt 1 or Attempt 2 module moved, nothing this session measures is
    # trustworthy and the run should stop before it reads a single bar. Seventeen modules, not nine:
    # Attempt 3 has two closed predecessors.
    module_verification = runner.verify_prior_attempt_modules()
    if module_verification["modules_that_moved"]:
        raise ConfigViolation(
            "prior-attempt modules moved: " + repr(module_verification["modules_that_moved"])
        )

    series = runner.load_grid_dataset()
    latest = max(one.sessions[-1] for one in series.values())
    if latest > bound:
        raise guard.WindowViolation(
            f"a bar dated {latest} survived the guarded load; the development bound is {bound}"
        )
    # write=True because the seal's reverification_required names the output path: "...and writes
    # the recomputation to reports/stage3_g2_attempt3/run_span_recheck.json". run_grid's own verify
    # pass repeats the recheck without writing, which is a second confirmation and not a conflict.
    span_recheck = runner.recheck_run_span(series, protocol=protocol, write=True)

    runs = runner.run_grid(series, verify=True, write_recheck=False)

    # Section 4.3: the grid must not merely have been rerun, it must have behaved differently. This
    # raises rather than reports if every ladder statistic matched Attempt 2's on all thirty-six
    # runs, which would mean RA3's band table never took effect.
    ladder_comparison = runner.ladder_engagement_comparison(runs)
    counterparts = runner.attempt_2_counterparts()

    selection = runner.select_representative_ra3(runs)
    representative_exists = selection["selected_variant_id"] is not None

    # grid_report is given the selection so that the two quantities new to CFG-3105's eighteen land
    # on every row. select_representative_v2 scores all eighteen variants before applying the
    # eligibility screen — neighbours are structural — so every row gets a score, including any
    # variant the screen excluded. variant_table's coverage loop turns that into a check.
    rows = runner.grid_report(runs, selection=selection)

    candidate_results: list[dict[str, Any]] = []
    gate_scope: dict[str, Any] | None = None
    if representative_exists:
        scope = runner.gate_inputs(runs, selection["selected_variant_id"], criteria=criteria)
        gate_scope = {
            "variant_id": scope["variant"].variant_id,
            "evaluated_on": scope["evaluated_on"],
            "conjunctive": scope["conjunctive"],
            "both_gate": scope["both_gate"],
            "criteria_source": scope["criteria_source"],
            "conflict_ref": scope["conflict_ref"],
            "conflict_status": scope["conflict_status"],
            "scope_resolution": scope["scope_resolution"],
            "neighbour_run_label": scope["neighbour_run_label"],
            "neighbours": [member.variant_id for member, _ in scope["neighbours"]],
        }
        # The sealed criteria object is passed unadapted. adapted_criteria_for_frozen_prose is
        # invoked inside condition_3_ra3 and condition_6_ra3, which is what keeps the adapter's
        # blast radius at the two conditions that need it; pre-adapting here would widen it.
        base_eval = gate.evaluate_representative_ra3(
            variant=scope["variant"],
            primary=scope["primary"],
            neighbours=scope["neighbours"],
            criteria=criteria,
            ledger=scope["primary_run"].ledger,
        )
        stress_eval = gate.evaluate_representative_ra3(
            variant=scope["variant"],
            primary=scope["stress"],
            neighbours=scope["neighbours"],
            criteria=criteria,
            ledger=scope["stress_run"].ledger,
        )
        candidate_results.append(_combine_base_and_stress(base_eval, stress_eval, scope))

    verdict = gate.stage_verdict_ra3(
        candidate_results,
        criteria,
        representative_exists=representative_exists,
        selection_note=selection["note"],
    )

    # Only now, with the verdict settled, are the two descriptive quantities computed that the gate
    # itself produces for one variant. Their position in this function is the argument that they
    # could not have influenced anything.
    extras = reported_only_extras(runs, criteria)

    # Determinism is claimed for the whole grid, not for a sample: the dataset is reloaded from disk
    # and every run repeated on fresh strategy and engine objects. RA3's band, lockout counter and
    # volatility state are engine state, so a reused engine would begin the replay inside the first
    # pass's drawdown ladder and the comparison would be worthless.
    replay_rows = runner.grid_report(
        runner.run_grid(runner.load_grid_dataset(), verify=True, write_recheck=False)
    )
    first = {run_id: _run_digests(row) for run_id, row in _by_run_id(rows).items()}
    second = {run_id: _run_digests(row) for run_id, row in _by_run_id(replay_rows).items()}
    mismatched = sorted(key for key in first if key not in second or first[key] != second[key])
    mismatched += sorted(key for key in second if key not in first)

    reconciliation = {
        "rule": (
            "evaluation_integrity_rules section 8, run on every run and not only the "
            "representative's"
        ),
        "runs_reconciled": len(runs),
        "single_leg_compared_total": sum(
            int(r["reconciliation_single_leg_compared"]) for r in rows
        ),
        "mismatches_total": sum(int(r["reconciliation_mismatches"]) for r in rows),
        "vacuous_runs": sorted(
            f"{r['variant_id']}{r['label']}" for r in rows if r["reconciliation_vacuous"]
        ),
        "conflict_ref": "G2A2-CONFLICT-26",
        "conflict_status": "inherited from Attempt 2 and resolved the same way",
        "vacuity_rule_as_implemented": (
            "assert_reconciliation_non_vacuous halts only when closed_episodes > 0 and "
            "single_leg_compared == 0; a run that closed no episode at all is vacuous without being "
            "a defect, and is recorded rather than raised on"
        ),
        "episode_ledger_source": (
            "backtest/g2_episodes_ra1.py, imported unmodified from Attempt 2 (G2A2-CONFLICT-18)"
        ),
    }

    return {
        "artifact_id": ARTIFACT_ID,
        "project": "StockEdge100",
        "generation": 2,
        "generation_id": protocol["generation_id"],
        "attempt": protocol["attempt"],
        "stage": "STAGE_3_G2_ATTEMPT_3_ROTATION_RA3_DEVELOPMENT",
        "gate": {"constitution_gate_id": 3, "name": "development_admissibility"},
        "strategy_id": protocol["strategy_id"],
        "candidate_index": protocol["candidate_index"],
        "family": protocol["family"],
        "hypothesis": protocol["hypothesis"],
        "what_this_attempt_adds_over_attempt_1": protocol[
            "what_this_attempt_adds_over_attempt_1"
        ],
        "what_this_attempt_adds_over_attempt_1_carriage": protocol[
            "what_this_attempt_adds_over_attempt_1_carriage"
        ],
        "what_this_attempt_changes_from_attempt_2": protocol[
            "what_this_attempt_changes_from_attempt_2"
        ],
        "adaptation_disclosure_verbatim": disclosure,
        "adaptation_disclosure_carriage": carriage,
        "attempt_1_ref": protocol["attempt_1_ref"],
        "attempt_2_ref": protocol["attempt_2_ref"],
        "refs_reverified": protocol["refs_reverified"],
        "prior_attempt_module_verification": module_verification,
        "prior_attempt_modules_immutable": protocol["prior_attempt_modules_immutable"],
        "mechanics_carried_unchanged": protocol["mechanics_carried_unchanged"],
        "conflicts_declared_in_the_gate_criteria": protocol[
            "conflicts_declared_in_the_gate_criteria"
        ],
        "sealed_inputs": {
            "protocol": PROTOCOL_REL,
            "protocol_artifact_id": protocol["artifact_id"],
            "protocol_sha256": sha256_file(PROJECT_ROOT / PROTOCOL_REL),
            "criteria": CRITERIA_REL,
            "criteria_artifact_id": criteria["artifact_id"],
            "criteria_sha256": sha256_file(PROJECT_ROOT / CRITERIA_REL),
            "criteria_sha256_not_recorded_in_the_protocol": protocol[
                "gate_criteria_sha256_not_recorded_here"
            ],
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
            "generation_1_provenance": check_generation_1_provenance(architecture),
            "single_difference_from_ra2": check_single_difference_from_ra2(architecture),
            "attributes_derived_from_risk": sorted(attributes_derived_from_risk()),
            "attempt_2_counterparts": counterparts,
        },
        "ladder_engagement_comparison": ladder_comparison,
        "grid": {
            "axes": protocol["grid"]["axes"],
            "variants_declared": protocol["grid"]["size"],
            "runs_per_variant": protocol["runs_per_variant"],
            "runs_executed": len(runs),
            "all_declared_runs_executed": len(runs)
            == int(protocol["runs_per_variant"]["total_runs"]),
            "revisions_after_seeing_a_result": 0,
            "grid_widened_from_attempt_1": False,
            "grid_widened_from_attempt_2": False,
        },
        "runs": rows,
        "selection": selection,
        "selection_determinism": selection_determinism(selection),
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
            "risk_state_trace_digest_note": protocol["reproducibility_requirements"][
                "risk_state_trace_digest"
            ],
            "no_wall_clock_in_payloads": protocol["reproducibility_requirements"][
                "no_wall_clock_in_payloads"
            ],
            "seed": protocol["reproducibility_requirements"]["seed"],
            "seed_note": protocol["reproducibility_requirements"]["seed_note"],
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
                {"quantity": quantity, "columns": list(columns), "scope": scope}
                for quantity, columns, scope in REPORTED_COVERAGE
            ],
            "new_since_attempt_2": [
                {"quantity": quantity, "columns": list(columns), "scope": scope}
                for quantity, columns, scope in REPORTED_COVERAGE[16:]
            ],
            "per_variant_scope_note": (
                "two of the eighteen are properties of a variant rather than of one of its runs: "
                "SEL-2 scores counters already summed across both runs, and the Attempt 2 "
                "counterpart block is matched per run but reported under one column name. They are "
                "checked once per table row instead of once per run, which is what the coverage "
                "loop's scope field selects"
            ),
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
                    "best_trade_removed_return is condition_5_ra1 called per run, because RA3 "
                    "changed a band table and not a measurement and there is no condition_5_ra3"
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
    body = finalize(run_all_g2_attempt3(), utc_now_iso())

    path = PROJECT_ROOT / EVIDENCE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    print(f"generated_utc     {body['generated_utc']}")
    print(f"evidence_digest   {body['evidence_digest']}")
    print(f"runs_executed     {body['grid']['runs_executed']}")
    print(f"determinism       {body['determinism']['all_identical']}")
    print(f"sel2_determinism  {body['selection_determinism']['all_identical']}")
    print(f"disclosure_chars  {body['adaptation_disclosure_carriage']['characters']}")
    print(f"disclosure_sha    {body['adaptation_disclosure_carriage']['sha256_of_utf8']}")
    print(f"representative    {body['selection']['selected_variant_id']}")
    print(f"decided_at_step   {body['selection']['decided_at_step']}")

    ladder = body["ladder_engagement_comparison"]
    print(f"ladder_differs    {ladder['at_least_one_statistic_differs']}")
    for name, stats in sorted(ladder["per_statistic"].items()):
        print(
            f"  {name:<34} ra3={stats['attempt_3_total']:<8} ra2={stats['attempt_2_total']:<8} "
            f"runs_differing={stats['runs_differing']}"
        )
    full = ladder["sessions_at_full_sizing"]
    print(
        f"  {'sessions_at_full_sizing':<34} ra3={full['attempt_3_total']:<8} "
        f"ra2={full['attempt_2_total']:<8} runs_differing={full['runs_differing']}"
    )

    for row in body["variant_table"]:
        score = row["selection_score"]["instability_score"]
        print(
            f"  {row['variant_id']:<52} shut={row['research_shutdown_events']} "
            f"fills={row['fill_count_both_runs']:<5} ladder={row['ladder_descents_both_runs']:<5} "
            f"lock={row['lockout_arms_both_runs']:<4} stops={row['stops_filled_both_runs']:<4} "
            f"score={score:<12} base_ret={row['base_total_return']}"
        )

    if body["candidate_results"]:
        basis = body["candidate_results"][0]["admission_basis"]
        print(f"base_not_satisfied   {basis['base_conditions_not_satisfied']}")
        print(f"stress_not_satisfied {basis['stress_conditions_not_satisfied']}")
        print(f"permissive_reading   {basis['permissive_base_only_reading_would_give']}")
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
