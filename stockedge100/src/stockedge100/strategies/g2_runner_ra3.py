"""Generation 2 Stage 3 Attempt 3: run the eighteen-variant grid under RA3 and select under SEL-2.

This is a new module standing beside ``g2_runner_ra1.py``, which is closed. Nothing here imports a
name *from* Attempt 2's runner: that module's behaviour is pinned by AT-H's digest check, and a
subclass of it would make Attempt 3's result depend on a file no one may touch to fix.

What is inherited is inherited deliberately and by import, not by copy: the frozen episode ledger
(``g2_episodes_ra1``), its non-vacuity assertion (``g2_gate_ra1.assert_reconciliation_non_vacuous``),
the cost model, the window guard, and ``runner.measure`` / ``runner.trade_ledger``. RA3's engine is a
subclass of RA2's, so every mechanism the seal calls unchanged is unchanged by construction.

Seven differences from ``g2_runner_ra1.py``, each measured from the seals rather than assumed:

===================================  ==========================================================
Attempt 2                            Attempt 3
===================================  ==========================================================
``attempt_1_modules_immutable``      ``prior_attempt_modules_immutable``: two config lists
  ``.modules`` (9 paths)               (9 + 8 = 17) against ``GOV-2007``'s
                                       ``prior_attempt_module_digests``. ``G2A3-CONFLICT-34``.
``run_span.recheck_requirement``     both that key and the new ``reverification_required``,
                                       which additionally names the file the recomputation is
                                       written to. Both are honoured.
20 governance span keys compared     25 compared; the 26th (``measurement_basis``) is prose and
                                       is named as such, and a key belonging to neither set
                                       refuses rather than being skipped.
three-step turnover selection        ``SE100-G2-SEL-2``, four steps, implemented in
                                       ``g2_selection_v2`` and *delegated to* here.
``SelectionInputRA1`` (4 fields)     ``SelectionInputV2`` (6 fields), asserted again at this
                                       module's import so the consumption site has its own guard.
``RotationEngineRA1``                ``RotationEngineRA3``: same four RA2 mechanisms, one band
                                       table. ``risk_summary`` gains ``architecture_provenance``.
16 non-gating reported quantities    18. The two additions are SEL-2's stability score with its
                                       four components and every neighbour's score, and the
                                       Attempt 2 counterpart of each ladder, lockout and stop
                                       statistic.
===================================  ==========================================================

``G2A2-CONFLICT-25`` is **not** renumbered. CFG-3106 carries it forward by name with
``status: "inherited from Attempt 2 and resolved the same way"``, so citing a fresh number here
would invent a second identity for one sealed finding. The resolution it records is the one this
module implements: all seven conditions on ``#BASE`` **and** S3-C1..S3-C6 also on ``#STRESS``, with
S3-C7 evaluated once on base runs because its own ``what_is_read`` fixes the neighbour side to
base-run total return. Both readings are reported; the restrictive one governs admission.

Nothing in this module reads a bar dated 2021-08-01 or later. The dataset arrives through
:mod:`stockedge100.strategies.g2_window_guard`, which truncates as it parses and then re-audits its
own result, and no holdout window is opened by any path reachable from here.
"""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass, fields
from decimal import Decimal
from typing import Any

from stockedge100.audit import sha256_file
from stockedge100.backtest.config import PROJECT_ROOT
from stockedge100.backtest.costs import SCENARIOS
from stockedge100.backtest.dataset import PriceSeries
from stockedge100.backtest.errors import ConfigViolation, InvariantViolation
from stockedge100.backtest.g2_costs import derive_mapping, rotation_cost_model
from stockedge100.backtest.g2_engine_ra3 import RotationEngineRA3
from stockedge100.backtest.g2_episodes_ra1 import EpisodeLedger, build_episode_ledger
from stockedge100.data.calendar import sessions_between
from stockedge100.reporting.g2_rotation_preregistration import (
    QUARTER_MONTHS,
    measure_span,
    month_offset,
)
from stockedge100.strategies import g2_window_guard as guard
from stockedge100.strategies.g2_gate_ra1 import assert_reconciliation_non_vacuous
from stockedge100.strategies.g2_gate_ra3 import load_criteria_ra3, neighbours_of_ra3
from stockedge100.strategies.g2_rotation_ra3 import (
    RotationVariantRA3,
    attempt_2_grid_agreement,
    build_candidate,
    check_mechanics_carried_unchanged,
    eligible_universe,
    load_protocol,
    rotation_variants,
    variant_by_id,
)
from stockedge100.strategies.g2_selection_v2 import (
    QUANTITIES,
    SELECTION_RULE_ID,
    SELECTION_V2_FIELD_NAMES,
    SelectionInputV2,
    SelectionResultV2,
    check_neighbourhood_structure,
    check_seal_agreement,
    load_selection_rule,
    select_representative_v2,
)
from stockedge100.strategies.runner import measure, trade_ledger

__all__ = [
    "ATTEMPT_2_GRID_PATH",
    "GATE_RUN_LABEL",
    "GOVERNANCE_PROTOCOL_ID",
    "GOVERNANCE_PROTOCOL_PATH",
    "RECHECK_REPORT_PATH",
    "STRESS_RUN_LABEL",
    "GridRunRA3",
    "attempt_2_counterparts",
    "attempt_2_grid_rows",
    "gate_inputs",
    "grid_report",
    "ladder_engagement_comparison",
    "load_grid_dataset",
    "recheck_run_span",
    "run_for",
    "run_grid",
    "run_labels",
    "run_one",
    "scenario_for_label",
    "select_representative_ra3",
    "selection_inputs",
    "verify_prior_attempt_modules",
    "write_run_span_recheck",
]

#: The run label whose figures every Gate 3 condition reads. The stress label additionally gates
#: S3-C1..S3-C6 under ``G2A2-CONFLICT-25``; it is never the basis for S3-C7's neighbour comparison.
GATE_RUN_LABEL = "#BASE"
STRESS_RUN_LABEL = "#STRESS"

#: The sealed governance record of the seventeen prior-attempt module digests. ``config/``
#: deliberately does not carry them — see ``prior_attempt_modules_immutable.digests_not_recorded_here``
#: — so AT-H reads them from here.
GOVERNANCE_PROTOCOL_PATH = (
    PROJECT_ROOT / "governance" / "generation_2" / "STAGE_3_G2_ROTATION_RA3_PROTOCOL.json"
)
GOVERNANCE_PROTOCOL_ID = "SE100-GOV-2007"

#: Where ``run_span.reverification_required`` says the recomputation is written. ``reports/`` is
#: outside every ``repo_state_id`` pattern, so writing it perturbs no digest.
RECHECK_REPORT_PATH = (
    PROJECT_ROOT / "reports" / "stage3_g2_attempt3" / "run_span_recheck.json"
)

#: Attempt 2's grid, read-only, for the counterpart columns the seal now requires beside RA3's own.
ATTEMPT_2_GRID_PATH = PROJECT_ROOT / "reports" / "stage3_g2_attempt2" / "grid_results.json"

#: The ladder, lockout and stop statistics that have an Attempt 2 counterpart. Band *indices* are
#: excluded from the comparable set on purpose — see :func:`attempt_2_counterparts`.
_RISK_COUNTERPART_KEYS = (
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
)

#: The subset of the above that is an integer count of an event, and therefore comparable across two
#: architectures whose band tables differ. ``ladder_engagement_comparison`` aggregates these.
_LADDER_ENGAGEMENT_KEYS = (
    "ladder_descents",
    "ladder_ascents",
    "lockout_arms",
    "lockout_recoveries_blocked",
    "stops_triggered",
    "stops_filled",
)


def _assert_selection_surface() -> None:
    """The consumption site's own copy of SEL-2's structural guard.

    ``g2_selection_v2`` asserts this at its import too. Duplicating it is not redundant: this module
    is what *populates* the dataclass, so an added field would be filled here first, and a guard that
    lives only in the module being called cannot fail before the caller has already built the object.
    Raised, not asserted, because ``python -O`` strips ``assert``.
    """
    actual = tuple(field.name for field in fields(SelectionInputV2))
    if actual != SELECTION_V2_FIELD_NAMES:
        raise ConfigViolation(
            f"SelectionInputV2 carries {actual}; the runner populates {SELECTION_V2_FIELD_NAMES}. "
            "A field added, removed or reordered between the two changes what SEL-2 can see, which "
            "is the one property the rule exists to guarantee."
        )
    for name in actual:
        lowered = name.lower()
        for banned in ("return", "drawdown", "profit", "sharpe", "equity", "pnl", "p_l"):
            if banned in lowered:
                raise ConfigViolation(
                    f"SelectionInputV2 field {name!r} names the performance term {banned!r}; the "
                    "runner refuses to populate a selection input that is not return-blind"
                )


_assert_selection_surface()


def _governance_protocol() -> dict[str, Any]:
    document = json.loads(GOVERNANCE_PROTOCOL_PATH.read_text(encoding="utf-8"))
    if document.get("artifact_id") != GOVERNANCE_PROTOCOL_ID:
        raise ConfigViolation(
            f"{GOVERNANCE_PROTOCOL_PATH.name} declares artifact_id "
            f"{document.get('artifact_id')!r}; {GOVERNANCE_PROTOCOL_ID!r} is required"
        )
    return document


# -- AT-H: neither prior attempt is touched --------------------------------------------------------


def verify_prior_attempt_modules() -> dict[str, Any]:
    """AT-H. All seventeen prior-attempt modules re-hash to their recorded digests.

    Two lists are compared, not one. ``config/`` declares *which* modules are immutable — now in two
    lists, Attempt 1's nine and Attempt 2's eight — and ``governance/`` records *what* they hashed to
    at seal time. A module dropped from one and not the other is itself a finding, so disagreement
    between the lists refuses before any file is read.

    ``G2A3-CONFLICT-34``: the check covers seventeen modules where Attempt 2's covered nine. The
    concatenation is checked for duplicates first, because a path appearing in both config lists
    would silently shrink the union while the count still looked right.

    A difference is a governance failure, not a value to update.
    """
    declared = load_protocol()["prior_attempt_modules_immutable"]
    recorded = _governance_protocol()["contamination_measurement"]["prior_attempt_module_digests"]

    first = list(declared["attempt_1_modules"])
    second = list(declared["attempt_2_modules"])
    listed = first + second

    duplicates = sorted({path for path in listed if listed.count(path) > 1})
    if duplicates:
        raise ConfigViolation(
            f"the two config lists share {duplicates}; the union would be smaller than the declared "
            f"count {declared['count']} while the concatenation still looked complete"
        )
    if len(listed) != int(declared["count"]):
        raise ConfigViolation(
            f"the seal declares count={declared['count']} immutable modules but lists "
            f"{len(first)} + {len(second)} = {len(listed)}"
        )
    if sorted(listed) != sorted(recorded):
        raise ConfigViolation(
            "the config seal lists prior-attempt modules "
            f"{sorted(set(listed) - set(recorded))} that the governance seal does not record, and "
            f"the governance seal records {sorted(set(recorded) - set(listed))} that the config "
            "seal does not list"
        )

    checked: dict[str, str] = {}
    moved: list[str] = []
    missing: list[str] = []
    for relative in listed:
        path = PROJECT_ROOT / relative
        if not path.is_file():
            missing.append(relative)
            continue
        digest = sha256_file(path)
        checked[relative] = digest
        if digest != recorded[relative]:
            moved.append(relative)

    if missing or moved:
        raise ConfigViolation(
            "AT-H: Attempts 1 and 2 are closed and must not be touched. "
            f"missing={missing} digest_changed={moved}. "
            f"Recorded by {GOVERNANCE_PROTOCOL_ID} at seal time; a difference is a governance "
            "failure, not a value to update."
        )

    return {
        "requirement": "AT-H",
        "conflict_ref": "G2A3-CONFLICT-34",
        "digest_source": (
            f"{GOVERNANCE_PROTOCOL_ID} contamination_measurement.prior_attempt_module_digests"
        ),
        "module_count": len(listed),
        "attempt_1_module_count": len(first),
        "attempt_2_module_count": len(second),
        "attempt_1_list_source": declared["attempt_1_list_source"],
        "attempt_2_list_source": declared["attempt_2_list_source"],
        "excluded_and_why": declared["g2_partition_lock_excluded"],
        "modules_verified": checked,
        "modules_that_moved": [],
    }


# -- the sealed run labels -------------------------------------------------------------------------


def run_labels() -> tuple[str, ...]:
    """The declared run labels, cross-checked against every count the seal states about them."""
    declared = load_protocol()["runs_per_variant"]
    labels = tuple(declared["labels"])
    if len(labels) != int(declared["count"]):
        raise ConfigViolation(
            f"the seal declares count={declared['count']} run(s) per variant but lists "
            f"{len(labels)} label(s) {list(labels)}"
        )
    if len(set(labels)) != len(labels):
        raise ConfigViolation(f"the sealed run labels are not distinct: {list(labels)}")
    if len(tuple(declared["scenarios"])) != len(labels):
        raise ConfigViolation(
            f"the seal lists {len(labels)} run label(s) and "
            f"{len(tuple(declared['scenarios']))} cost scenario(s); the two lists are positional "
            "and must be the same length"
        )
    expected = len(rotation_variants()) * len(labels)
    if expected != int(declared["total_runs"]):
        raise ConfigViolation(
            f"{len(rotation_variants())} variants x {len(labels)} labels is {expected} runs; the "
            f"seal declares total_runs={declared['total_runs']}"
        )
    return labels


def scenario_for_label(label: str) -> str:
    """Map a sealed run label onto a cost scenario by two derivations that must agree.

    Strip the ``#`` and require exactly one member of :data:`~stockedge100.backtest.costs.SCENARIOS`
    prefixed by what remains; independently, index the seal's positional ``scenarios`` list by the
    label's position in ``labels``. Both are computed and required to match, because the failure mode
    being guarded is precisely a seal that was read wrong.
    """
    declared = load_protocol()["runs_per_variant"]
    labels = run_labels()
    if label not in labels:
        raise ConfigViolation(f"{label!r} is not one of the sealed run labels {list(labels)}")

    token = label.lstrip("#")
    matches = [scenario for scenario in SCENARIOS if scenario.startswith(token)]
    if len(matches) != 1:
        raise ConfigViolation(
            f"the sealed run label {label!r} resolves to {matches!r} among the declared cost "
            f"scenarios {list(SCENARIOS)}; exactly one is required"
        )
    derived = matches[0]

    positional = tuple(declared["scenarios"])[labels.index(label)]
    if positional not in SCENARIOS:
        raise ConfigViolation(
            f"the seal pairs run label {label!r} with cost scenario {positional!r}, which is not "
            f"one of {list(SCENARIOS)}"
        )
    if positional != derived:
        raise ConfigViolation(
            f"run label {label!r} derives to cost scenario {derived!r} by prefix and to "
            f"{positional!r} by the seal's positional scenarios list; the two must agree"
        )
    return derived


# -- the dataset, and the span it must have --------------------------------------------------------


def load_grid_dataset() -> dict[str, PriceSeries]:
    """The development-window dataset, loaded through the Generation 2 window guard.

    Both calls matter, and this is AT-G's path. ``load_stage_3_dataset`` stops reading at the
    development bound as it parses; ``assert_series_within_bound`` re-inspects the loaded bar map
    *and* the session index of every symbol afterwards. A bar dated 2021-08-01 or later would have to
    survive a truncating loader and then a separate audit of its result.
    """
    series = guard.load_stage_3_dataset(eligible_universe())
    guard.assert_series_within_bound(series)
    return series


def _span_from_series(series: dict[str, PriceSeries]) -> dict[str, Any]:
    """Recompute the run span and both rebalance calendars from the loaded series alone.

    Deliberately reads nothing but ``PriceSeries.sessions`` and the exchange calendar — no
    partition-lock file, no seal — so the result is an independent measurement of what is actually in
    memory rather than a restatement of what was declared.

    Five quantities beyond Attempt 2's twenty are computed here, because ``GOV-2007``'s
    ``run_span_measured_from_disk`` records twenty-six and ``reverification_required`` asks for
    equality with *every* field. The five are the lookback reference of the session before the run
    start, and the first three / last two sessions of each rebalance calendar.
    """
    symbols = sorted(series)
    first = {symbol: series[symbol].sessions[0] for symbol in symbols}
    last = {symbol: series[symbol].sessions[-1] for symbol in symbols}

    union_dates = sorted({session for symbol in symbols for session in series[symbol].sessions})

    latest_inception = max(first.values())
    binding = sorted(symbol for symbol in symbols if first[symbol] == latest_inception)
    earliest_inception = min(first.values())
    earliest_symbols = sorted(symbol for symbol in symbols if first[symbol] == earliest_inception)

    run_end = max(last.values())
    ends_early = sorted(symbol for symbol in symbols if last[symbol] != run_end)

    run_start = None
    previous = None
    for session in union_dates:
        if month_offset(session, -12) >= latest_inception:
            run_start = session
            break
        previous = session
    if run_start is None:
        raise InvariantViolation(
            "no loaded session satisfies the twelve-month lookback requirement against the latest "
            f"inception {latest_inception.isoformat()}; the run span cannot be recomputed"
        )

    run_sessions = [s for s in union_dates if run_start <= s <= run_end]
    calendar = list(sessions_between(run_start, run_end))

    monthly = [run_sessions[0]]
    quarterly = [run_sessions[0]]
    for prior, session in zip(run_sessions, run_sessions[1:]):
        if session.month != prior.month:
            monthly.append(session)
            if session.month in QUARTER_MONTHS:
                quarterly.append(session)

    missing_at_start = sorted(symbol for symbol in symbols if run_start not in series[symbol].bars)

    def dates(values: Sequence[dt.date]) -> list[str]:
        return [value.isoformat() for value in values]

    return {
        "member_count": len(symbols),
        "run_start": run_start.isoformat(),
        "run_start_weekday": run_start.strftime("%A"),
        "run_start_lookback_reference": month_offset(run_start, -12).isoformat(),
        "session_before_run_start": None if previous is None else previous.isoformat(),
        "session_before_run_start_lookback_reference": (
            None if previous is None else month_offset(previous, -12).isoformat()
        ),
        "run_end": run_end.isoformat(),
        "run_sessions": len(run_sessions),
        "exchange_calendar_sessions": len(calendar),
        "session_lists_agree": dates(run_sessions) == dates(calendar),
        # ``None`` when more than one member shares the latest inception, matching ``measure_span``.
        # A tie means no single symbol binds the run start, and naming one of them arbitrarily would
        # make the cross-check agree by construction on the very case it exists to catch.
        "binding_symbol": binding[0] if len(binding) == 1 else None,
        "binding_symbols": binding,
        "binding_symbol_inception": latest_inception.isoformat(),
        "earliest_inception": earliest_inception.isoformat(),
        "earliest_inception_symbols": earliest_symbols,
        "members_missing_a_bar_at_run_start": missing_at_start,
        "symbols_ending_before_run_end": ends_early,
        "development_union_sessions": len(union_dates),
        "development_union_span": [union_dates[0].isoformat(), union_dates[-1].isoformat()],
        "monthly_rebalance_sessions": len(monthly),
        "quarterly_rebalance_sessions": len(quarterly),
        "monthly_first_three": dates(monthly[:3]),
        "monthly_last_two": dates(monthly[-2:]),
        "quarterly_first_three": dates(quarterly[:3]),
        "quarterly_last_two": dates(quarterly[-2:]),
    }


#: What ``run_span`` in the config seal calls each quantity, against what :func:`_span_from_series`
#: calls it. The session count is the one that bites: the config seal says ``sessions`` where the
#: governance seal and both prior attempts say ``run_sessions``.
_CONFIG_SPAN_KEYS = {
    "run_start": "run_start",
    "run_start_weekday": "run_start_weekday",
    "run_end": "run_end",
    "sessions": "run_sessions",
    "binding_symbol": "binding_symbol",
    "binding_symbol_inception": "binding_symbol_inception",
    "members_missing_a_bar_at_run_start": "members_missing_a_bar_at_run_start",
    "symbols_ending_before_run_end": "symbols_ending_before_run_end",
    "development_union_sessions": "development_union_sessions",
}

#: The twenty-five keys of ``GOV-2007.run_span_measured_from_disk`` that are measurements, and the
#: one that is prose about how they were measured. Enumerated as two literals so that a key belonging
#: to neither refuses: a comparison loop written over ``set(governance) & set(measured)`` would
#: silently skip any field the seal recorded and this module does not compute, which is exactly the
#: field a widened seal would add.
_GOVERNANCE_SPAN_MEASURED_KEYS = (
    "member_count",
    "run_start",
    "run_start_weekday",
    "run_start_lookback_reference",
    "session_before_run_start",
    "session_before_run_start_lookback_reference",
    "run_end",
    "run_sessions",
    "exchange_calendar_sessions",
    "session_lists_agree",
    "binding_symbol",
    "binding_symbols",
    "binding_symbol_inception",
    "earliest_inception",
    "earliest_inception_symbols",
    "members_missing_a_bar_at_run_start",
    "symbols_ending_before_run_end",
    "development_union_sessions",
    "development_union_span",
    "monthly_rebalance_sessions",
    "quarterly_rebalance_sessions",
    "monthly_first_three",
    "monthly_last_two",
    "quarterly_first_three",
    "quarterly_last_two",
)
_GOVERNANCE_SPAN_PROSE_KEYS = ("measurement_basis",)


def recheck_run_span(
    series: dict[str, PriceSeries],
    *,
    protocol: dict[str, Any] | None = None,
    write: bool = False,
) -> dict[str, Any]:
    """The seal's ``recheck_requirement`` and its ``reverification_required``, four ways.

    "The span above is carried from Attempt 2 and must not be assumed. The Attempt 3 runner
    recomputes it from the loaded data before the first variant runs, asserts equality with every
    field recorded here, and writes the recomputation to
    ``reports/stage3_g2_attempt3/run_span_recheck.json``. A mismatch is a blocker, not a value to
    adopt."

    So: recompute from the loaded series; compare against the config seal's ``run_span``; compare
    against ``GOV-2007``'s twenty-five measured ``run_span_measured_from_disk`` fields; and
    cross-check against :func:`~stockedge100.reporting.g2_rotation_preregistration.measure_span`,
    which derives the same quantities from the partition lock's session lists without loading a bar.

    The last is not redundant. The in-memory recomputation and the seal could agree because both
    descend from the same truncating loader; ``measure_span`` reaches the dates by a different path,
    so agreement between them is evidence that the loader did not quietly reshape the window.
    """
    protocol = load_protocol() if protocol is None else protocol
    measured = _span_from_series(series)

    declared = protocol["run_span"]
    differences: list[str] = []
    for sealed_key, measured_key in _CONFIG_SPAN_KEYS.items():
        want, got = declared[sealed_key], measured[measured_key]
        if isinstance(want, list):
            want, got = list(want), list(got)
        elif not isinstance(want, str):
            want, got = int(want), int(got)
        if want != got:
            differences.append(f"run_span.{sealed_key}: seal {want!r} vs recomputed {got!r}")

    governance = _governance_protocol()["run_span_measured_from_disk"]
    accounted = set(_GOVERNANCE_SPAN_MEASURED_KEYS) | set(_GOVERNANCE_SPAN_PROSE_KEYS)
    unaccounted = sorted(set(governance) - accounted)
    if unaccounted:
        raise ConfigViolation(
            f"{GOVERNANCE_PROTOCOL_ID} run_span_measured_from_disk records {unaccounted}, which this "
            "module neither recomputes nor names as prose. 'Asserts equality with every field "
            "recorded here' cannot be satisfied by skipping the fields it does not know about."
        )
    absent = sorted(accounted - set(governance))
    if absent:
        raise ConfigViolation(
            f"{GOVERNANCE_PROTOCOL_ID} run_span_measured_from_disk does not record {absent}, which "
            "this module expects to compare against; a seal that shrank is a finding, not a value "
            "to skip"
        )
    for key in _GOVERNANCE_SPAN_MEASURED_KEYS:
        want, got = governance[key], measured[key]
        if isinstance(want, list):
            want, got = list(want), list(got)
        if want != got:
            differences.append(
                f"run_span_measured_from_disk.{key}: seal {want!r} vs recomputed {got!r}"
            )
    for key in _GOVERNANCE_SPAN_PROSE_KEYS:
        if not isinstance(governance[key], str) or not governance[key].strip():
            differences.append(
                f"run_span_measured_from_disk.{key} is prose describing the measurement basis and "
                "must be a non-empty string"
            )

    independent = measure_span()
    shared = sorted(set(independent) & set(measured))
    for key in shared:
        want, got = independent[key], measured[key]
        if isinstance(want, list):
            want, got = list(want), list(got)
        if want != got:
            differences.append(
                f"measure_span().{key}: partition-lock derivation {want!r} vs loaded-series "
                f"derivation {got!r}"
            )

    if not measured["session_lists_agree"]:
        differences.append(
            "the loaded session union and the exchange calendar disagree over the run span"
        )

    if differences:
        raise InvariantViolation(
            "the recomputed run span differs from the seal, and the seal's reverification_required "
            "is that 'a mismatch is a blocker, not a value to adopt':\n  - "
            + "\n  - ".join(differences)
        )

    evidence = {
        "requirement": declared["recheck_requirement"],
        "reverification_required": declared["reverification_required"],
        "recomputed_from": "the guard-loaded PriceSeries in memory",
        "cross_checked_against": [
            f"{protocol['artifact_id']} run_span",
            f"{GOVERNANCE_PROTOCOL_ID} run_span_measured_from_disk",
            "reporting.g2_rotation_preregistration.measure_span()",
        ],
        "config_keys_compared": sorted(_CONFIG_SPAN_KEYS),
        "governance_keys_compared": list(_GOVERNANCE_SPAN_MEASURED_KEYS),
        "governance_keys_not_a_measurement": list(_GOVERNANCE_SPAN_PROSE_KEYS),
        "independent_derivation_keys_compared": shared,
        "differences": [],
        "measured": measured,
    }
    if write:
        evidence["written_to"] = write_run_span_recheck(evidence)
    return evidence


def write_run_span_recheck(evidence: dict[str, Any]) -> str:
    """Write the recomputation where ``reverification_required`` says it goes.

    ``write_bytes`` rather than ``write_text``: on Windows the latter would translate every ``\\n``
    to ``\\r\\n``, and a report artifact whose newlines depend on the operating system that produced
    it is not reproducible. ``reports/`` is outside every ``repo_state_id`` pattern, so this writes
    nothing the digest covers.
    """
    RECHECK_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(evidence, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    RECHECK_REPORT_PATH.write_bytes(payload.encode("utf-8"))
    return str(RECHECK_REPORT_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/")


# -- one run ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class GridRunRA3:
    """One completed run of one variant under one cost scenario, with its risk evidence.

    ``ledger`` is the episode ledger of ``evaluation_integrity_rules`` section 8, built and
    reconciled for **every** run rather than only the representative's. ``trades`` is Attempt 1's
    flat trade ledger, kept because the grid report's Attempt 1 columns are defined against it and
    because the two disagreeing would itself be a finding.
    """

    variant: RotationVariantRA3
    label: str
    scenario: str
    result: Any
    measurement: dict[str, Any]
    strategy_evidence: dict[str, Any]
    clamps: dict[str, Any]
    risk: dict[str, Any]
    trades: list[dict[str, Any]]
    ledger: EpisodeLedger
    reconciliation: dict[str, Any]

    @property
    def run_id(self) -> str:
        return f"{self.variant.variant_id}{self.label}"

    @property
    def fill_count(self) -> int:
        return len(self.result.fills)

    @property
    def shutdown_fired(self) -> bool:
        return self.result.shutdown_session is not None


def run_one(
    variant: RotationVariantRA3,
    label: str,
    series: dict[str, PriceSeries],
    *,
    protocol: dict[str, Any] | None = None,
) -> GridRunRA3:
    """Execute one declared run under RA3.

    A fresh :class:`~stockedge100.strategies.g2_rotation_ra3.RotationCandidateRA3` is built per run,
    through :func:`~stockedge100.strategies.g2_rotation_ra3.build_candidate` so that the cost model is
    derived from ``(k, scenario)`` rather than chosen here. The candidate accumulates the ranking hash
    and the rebalance counters as it runs, so reusing one across two runs would blend two runs'
    evidence into one digest and destroy the determinism claim AT-F gates on.

    The engine is likewise fresh. RA3 inherits RA2's band, lockout counter and volatility state as
    engine state; a reused engine would start the stress run inside the base run's drawdown ladder.
    """
    protocol = load_protocol() if protocol is None else protocol
    if label not in run_labels():
        raise ConfigViolation(f"{label!r} is not one of the sealed run labels {list(run_labels())}")

    scenario = scenario_for_label(label)
    candidate = build_candidate(variant, scenario)
    costs = candidate.costs

    # ``rotation_cost_model`` constructs a fresh CostModel per call, so identity proves nothing and
    # CostModel defines no __eq__. What is compared is the four things that decide what a run costs:
    # the scenario, the breadth the sizing derives from, the stress multiplier, and the raw mapping
    # every rate is read out of. A candidate built against the wrong breadth or the wrong scenario
    # would differ in at least one of them.
    reference = rotation_cost_model(variant.top_k, scenario)
    divergent = [
        name
        for name in ("scenario", "max_open_risky_positions", "stress_multiplier", "raw")
        if getattr(costs, name) != getattr(reference, name)
    ]
    if divergent:
        raise ConfigViolation(
            f"{variant.variant_id}{label}: the candidate's cost model differs from "
            f"rotation_cost_model({variant.top_k}, {scenario!r}) in {divergent}"
        )
    _, raw, _ = derive_mapping(variant.top_k)

    span = protocol["run_span"]
    engine = RotationEngineRA3(
        series,
        costs,
        guard.stage_3_window(),
        candidate,
        start=dt.date.fromisoformat(span["run_start"]),
        end=dt.date.fromisoformat(span["run_end"]),
        label=f"{variant.variant_id}{label}",
        budget_weight=candidate.weight,
    )
    result = engine.run()

    sessions = len(result.equity_curve)
    if sessions != int(span["sessions"]):
        raise InvariantViolation(
            f"{variant.variant_id}{label}: the run covered {sessions} sessions; the sealed run span "
            f"declares {span['sessions']}. Every variant shares one run start and one run end, so a "
            "differing session count means the dataset, not the strategy, changed."
        )

    # evaluation_integrity_rules section 8: on every run, not only the representative's. Both calls
    # can halt — build_episode_ledger on a value or count disagreement with Portfolio.trades, and
    # assert_reconciliation_non_vacuous when episodes closed and not one was single-leg.
    ledger = build_episode_ledger(result)
    reconciliation = assert_reconciliation_non_vacuous(ledger)

    return GridRunRA3(
        variant=variant,
        label=label,
        scenario=scenario,
        result=result,
        measurement=measure(result, costs, raw),
        strategy_evidence=candidate.evidence(),
        clamps=engine.clamp_summary(),
        risk=engine.risk_summary(),
        trades=trade_ledger(result),
        ledger=ledger,
        reconciliation=reconciliation,
    )


def run_grid(
    series: dict[str, PriceSeries] | None = None,
    *,
    variants: Sequence[RotationVariantRA3] | None = None,
    labels: Sequence[str] | None = None,
    progress: Callable[[int, int, GridRunRA3], None] | None = None,
    verify: bool = True,
    write_recheck: bool = False,
) -> tuple[GridRunRA3, ...]:
    """Every declared run, unconditionally.

    The loop is variant-major and label-minor purely so a progress log reads in grid order. Nothing
    downstream depends on that order, and nothing in the loop inspects a completed run: the seal
    declares all thirty-six in advance and none is conditional on another's outcome.

    ``verify`` runs AT-H, the mechanics-unchanged check, the grid-agreement check, SEL-2's two seal
    checks and the run-span reverification before the first session is stepped. It exists as a
    parameter only so a unit test can drive one cell of the grid against a fixture series; the real
    grid run leaves it at ``True``.

    ``variants`` and ``labels`` are likewise for tests that need one cell. When both are left at
    their defaults the full cross product runs and the sealed ``total_runs`` is asserted.
    """
    protocol = load_protocol()
    if verify:
        verify_prior_attempt_modules()
        check_mechanics_carried_unchanged(protocol)
        attempt_2_grid_agreement()
        # SEL-2's seal is checked before the grid, not at selection time. A rule that disagrees with
        # its seal is a reason not to spend thirty-six backtests, and discovering it afterwards would
        # leave a completed grid with no admissible way to choose from it.
        load_selection_rule()
        check_seal_agreement()
        check_neighbourhood_structure()
    if series is None:
        series = load_grid_dataset()
    if verify:
        recheck_run_span(series, protocol=protocol, write=write_recheck)

    full = variants is None and labels is None
    grid = tuple(rotation_variants()) if variants is None else tuple(variants)
    which = run_labels() if labels is None else tuple(labels)

    total = len(grid) * len(which)
    runs: list[GridRunRA3] = []
    for variant in grid:
        for label in which:
            run = run_one(variant, label, series, protocol=protocol)
            runs.append(run)
            if progress is not None:
                progress(len(runs), total, run)

    if full and len(runs) != int(protocol["runs_per_variant"]["total_runs"]):
        raise InvariantViolation(
            f"the grid produced {len(runs)} runs; the seal declares "
            f"{protocol['runs_per_variant']['total_runs']}"
        )
    return tuple(runs)


# -- the return-blind projection -------------------------------------------------------------------


def selection_inputs(runs: Sequence[GridRunRA3]) -> tuple[SelectionInputV2, ...]:
    """Project the completed grid onto SEL-2's six fields, and nothing else.

    Every counter is summed across the variant's two runs, as sealed: SEL-2's step 2 scores
    ``{fill_count, ladder_descent_count, lockout_arm_count, stops_filled_count}`` "summed across base
    and stress runs". The eligibility screen is likewise across both runs, so a variant that shut
    down on stress alone is ineligible.

    Each variant must contribute every declared label exactly once. A missing stress run would
    otherwise halve that variant's counters and make it look like the most stable point on the grid —
    a silent selection bias with no symptom.

    Note what is *not* read: ``run.measurement``, ``run.ledger`` and ``run.result.equity_curve`` are
    never touched. The only fields consulted are the fill list's length, the shutdown session's
    nullity, and three integer counters out of ``risk_summary``.
    """
    labels = run_labels()
    grouped: dict[str, list[GridRunRA3]] = {}
    for run in runs:
        grouped.setdefault(run.variant.variant_id, []).append(run)

    declared = {variant.variant_id for variant in rotation_variants()}
    missing = sorted(declared - set(grouped))
    extra = sorted(set(grouped) - declared)
    if missing or extra:
        raise ConfigViolation(
            f"the grid is incomplete for selection: missing {missing}, unexpected {extra}"
        )

    inputs: list[SelectionInputV2] = []
    for variant_id in sorted(grouped):
        members = grouped[variant_id]
        seen = sorted(run.label for run in members)
        if seen != sorted(labels):
            raise ConfigViolation(
                f"{variant_id} contributed runs {seen}; the seal declares exactly {list(labels)}. "
                "A variant scored over fewer runs than its neighbours would be compared on a "
                "different statistic wearing the same name."
            )
        inputs.append(
            SelectionInputV2(
                variant_id=variant_id,
                shutdown_events=sum(1 for run in members if run.shutdown_fired),
                fill_count=sum(run.fill_count for run in members),
                ladder_descents=sum(int(run.risk["ladder"]["descents"]) for run in members),
                lockout_arms=sum(int(run.risk["lockout"]["arms"]) for run in members),
                stops_filled=sum(int(run.risk["stops"]["filled"]) for run in members),
            )
        )
    return tuple(inputs)


def select_representative_ra3(runs: Sequence[GridRunRA3]) -> dict[str, Any]:
    """Apply SE100-G2-SEL-2, and record enough to re-derive the choice from the record.

    The rule itself is not reimplemented here. ``g2_selection_v2`` owns the four steps, the frozen
    six-field input, the neighbour relation and the score; this function's whole job is to build the
    projection, hand it over, and package the result with the sealed step text beside it.

    The ``no_candidate_path`` branch is the seal's own: "If all eighteen variants record at least one
    research-shutdown event, no variant is eligible and the attempt fails." That is Attempt 1's
    outcome exactly, and it is reachable again.
    """
    rule = load_selection_rule()
    inputs = selection_inputs(runs)
    result: SelectionResultV2 = select_representative_v2(inputs)

    record: dict[str, Any] = {
        "rule_id": SELECTION_RULE_ID,
        "rule_source": f"{load_protocol()['artifact_id']} representative_selection_rule",
        "return_blind": rule["return_blind"],
        "frozen_before_any_variant_is_run": rule["frozen_before_any_variant_is_run"],
        "steps": [
            {
                "order": int(step["order"]),
                "criterion": step["criterion"],
                "scope": step.get("scope"),
            }
            for step in sorted(rule["steps"], key=lambda step: int(step["order"]))
        ],
        "selection_input_fields": list(SELECTION_V2_FIELD_NAMES),
        "scored_quantities": list(QUANTITIES),
        "inputs": [
            {
                "variant_id": item.variant_id,
                "shutdown_events": item.shutdown_events,
                "fill_count": item.fill_count,
                "ladder_descents": item.ladder_descents,
                "lockout_arms": item.lockout_arms,
                "stops_filled": item.stops_filled,
            }
            for item in inputs
        ],
        "result": result.to_json(),
        "selected_variant_id": result.selected,
        "decided_at_step": result.decided_at_step,
    }

    if result.selected is None:
        record["outcome"] = "no_candidate"
        record["no_candidate_path"] = rule["no_candidate_path"]
        record["note"] = (
            f"All {len(inputs)} variants recorded at least one research-shutdown event across their "
            "two runs, so step 1 eliminated the whole grid and no representative exists."
        )
        return record

    chosen = result.scores[result.selected]
    record["outcome"] = "representative_selected"
    record["selected_score"] = chosen.to_json()
    # The neighbours' own scores, not merely their identities: the seal now requires that every
    # neighbour's identity *and* score is reported, so the choice can be checked rather than trusted.
    record["neighbour_scores"] = [
        result.scores[neighbour_id].to_json() for neighbour_id in chosen.neighbours
    ]
    step = {int(item["order"]): item for item in rule["steps"]}[int(result.decided_at_step)]
    record["note"] = (
        f"{result.selected} was selected at step {result.decided_at_step} "
        f"({step['criterion']}) with instability score {chosen.score:f} over "
        f"{len(chosen.neighbours)} neighbours, from {len(result.eligible)} eligible of "
        f"{len(inputs)} variants."
    )
    record["no_reselection"] = rule["no_reselection"]
    return record


# -- what the gate is given ------------------------------------------------------------------------


def run_for(runs: Sequence[GridRunRA3], variant_id: str, label: str) -> GridRunRA3:
    """The one completed run matching ``(variant_id, label)``, or a refusal."""
    found = [run for run in runs if run.variant.variant_id == variant_id and run.label == label]
    if len(found) != 1:
        raise ConfigViolation(
            f"expected exactly one run for {variant_id}{label}; found {len(found)}"
        )
    return found[0]


def gate_inputs(
    runs: Sequence[GridRunRA3],
    variant_id: str,
    *,
    criteria: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble exactly what Gate 3 evaluates, under the inherited ``G2A2-CONFLICT-25`` resolution.

    Three things are handed to the gate:

    ``primary``
        the representative's ``#BASE`` run, which every condition reads;
    ``stress``
        the representative's ``#STRESS`` run, which S3-C1..S3-C6 must *also* satisfy because
        ``runs_per_variant.both_gate`` says "a variant satisfies a gate condition only if both of its
        runs satisfy it";
    ``neighbours``
        the structural neighbours' ``#BASE`` runs, and only those. S3-C7's ``what_is_read`` is "each
        neighbour's base-run equity-curve total return and its sign. Nothing else about a neighbour
        enters this condition", so there is no sealed stress-side neighbour figure to compare and one
        is not invented.

    The neighbour set is not chosen here. :func:`~stockedge100.strategies.g2_gate_ra3.neighbours_of_ra3`
    derives it from the grid axes and ``condition_7_ra3`` re-derives it and refuses a set that differs.

    The conflict is cited by its Attempt 2 number because CFG-3106 carries it forward under that
    number with ``status: "inherited from Attempt 2 and resolved the same way"``. Allocating a fresh
    ``G2A3-`` number would give one sealed finding two identities.
    """
    criteria = load_criteria_ra3() if criteria is None else criteria
    protocol = load_protocol()
    scope = protocol["gate_evaluation_scope"]
    both_gate = protocol["runs_per_variant"]["both_gate"]

    # The scope sentence is read rather than assumed. What is asserted is that it scopes the gate to
    # more than one run and that the both_gate rule is present to say which; a seal that had quietly
    # reverted to Attempt 1's single-run wording would fail here rather than silently narrow the gate.
    if "both of its runs" not in scope["evaluated_on"]:
        raise ConfigViolation(
            f"the sealed gate scope is {scope['evaluated_on']!r}, which does not scope the gate "
            "across both runs; G2A2-CONFLICT-25's restrictive resolution was written against a seal "
            "that does, and refusing is safer than guessing which run the gate reads"
        )
    if "only if both of its runs satisfy it" not in both_gate:
        raise ConfigViolation(
            f"runs_per_variant.both_gate is {both_gate!r}, which does not state the conjunction "
            "across runs that this module implements"
        )

    variant = variant_by_id(variant_id)
    primary = run_for(runs, variant_id, GATE_RUN_LABEL)
    stress = run_for(runs, variant_id, STRESS_RUN_LABEL)
    neighbours = [
        (member, run_for(runs, member.variant_id, GATE_RUN_LABEL).result)
        for member in neighbours_of_ra3(variant, criteria)
    ]
    return {
        "variant": variant,
        "primary": primary.result,
        "primary_run": primary,
        "stress": stress.result,
        "stress_run": stress,
        "neighbours": neighbours,
        "neighbour_run_label": GATE_RUN_LABEL,
        "evaluated_on": scope["evaluated_on"],
        "conjunctive": scope["conjunctive"],
        "both_gate": both_gate,
        "criteria_source": scope["criteria_source"],
        "conflict_ref": "G2A2-CONFLICT-25",
        "conflict_status": "inherited from Attempt 2 and resolved the same way",
        "scope_resolution": (
            "SE100-CFG-3105 scopes the gate across both runs and states that a condition is "
            "satisfied only if both runs satisfy it; SE100-CFG-3106 measures S3-C1 and S3-C4 on the "
            "base run and lists the stress run as reported_but_not_gating. Both were sealed in the "
            "same session and neither outranks the other, so the more restrictive reading is "
            "adopted: all seven conditions on #BASE, and S3-C1..S3-C6 also on #STRESS. S3-C7 is "
            "evaluated once, on base runs, because its own what_is_read fixes the neighbour side to "
            "base-run total return and gives no sealed basis for a stress-side comparison. Both "
            "condition sets are reported in full, so a reader can see exactly what the permissive "
            "base-only reading would have given. The Attempt 3 operating instruction states the "
            "conjunctive rule as 'all conditions on the base run' and then directs that the "
            "restrictive reading also be evaluated and both readings reported, citing this conflict "
            "by name; the instruction and the sealed resolution therefore agree."
        ),
    }


# -- Attempt 2's counterparts ----------------------------------------------------------------------


def attempt_2_grid_rows() -> dict[tuple[int, int, str, str], dict[str, Any]]:
    """Attempt 2's thirty-six grid rows, keyed by grid coordinates rather than by variant id.

    The ids cannot be matched directly: Attempt 2's carry ``-C2-ROTATION-RA1-`` where Attempt 3's
    carry ``-C3-ROTATION-RA3-``. What is shared is the parameterisation, so the key is
    ``(lookback_months, top_k, rebalance_frequency, label)`` — the grid is unchanged between the two
    attempts by seal, which is what makes the comparison meaningful at all.

    Read-only. Attempt 2 is closed; this opens its report for reading and writes nothing.
    """
    if not ATTEMPT_2_GRID_PATH.is_file():
        raise ConfigViolation(
            f"{ATTEMPT_2_GRID_PATH} is absent. The seal requires the Attempt 2 counterpart of each "
            "ladder, lockout and stop statistic beside the Attempt 3 figure; without that file the "
            "comparison the attempt exists to make cannot be produced."
        )
    rows = json.loads(ATTEMPT_2_GRID_PATH.read_text(encoding="utf-8"))
    keyed: dict[tuple[int, int, str, str], dict[str, Any]] = {}
    for row in rows:
        key = (
            int(row["lookback_months"]),
            int(row["top_k"]),
            str(row["rebalance_frequency"]),
            str(row["label"]),
        )
        if key in keyed:
            raise ConfigViolation(f"Attempt 2's grid carries {key} twice")
        keyed[key] = row
    expected = len(rotation_variants()) * len(run_labels())
    if len(keyed) != expected:
        raise ConfigViolation(
            f"Attempt 2's grid holds {len(keyed)} rows; Attempt 3's grid shape implies {expected}. "
            "The two attempts share a grid by seal, so a different row count means the comparison "
            "would be between different things."
        )
    return keyed


def _band_scalars(architecture: dict[str, Any]) -> dict[str, str]:
    """``{band index: sizing scalar}`` from a sealed de-risk ladder, as strings."""
    for component in architecture.get("components", {}).values():
        if component.get("name") == "de_risk_ladder":
            return {str(band["band"]): str(band["scalar"]) for band in component["bands"]}
    raise ConfigViolation("the risk architecture declares no de_risk_ladder component")


def _full_sizing_band(scalars: dict[str, str]) -> str:
    """The one band whose scalar is exactly 1, or a refusal if there is not exactly one."""
    full = [band for band, scalar in scalars.items() if Decimal(scalar) == 1]
    if len(full) != 1:
        raise ConfigViolation(
            f"the ladder has {len(full)} bands at full sizing {full}; exactly one is required for "
            "'sessions at full sizing' to name a single quantity"
        )
    return full[0]


def attempt_2_counterparts() -> dict[str, Any]:
    """The two attempts' band tables, and what may and may not be compared between them.

    Band *indices* are not comparable and this says so rather than quietly comparing them. RA2 has
    four bands and RA3 has three, so RA2's ``deepest_band = 3`` and an RA3 run's ``deepest_band = 2``
    can denote the same drawdown depth. What is comparable is the sizing **scalar** each index maps
    to, and the session count in the single full-sizing band — which is precisely the quantity RA3's
    one change was expected to move, since RA2 throttled to 75% from a 5% drawdown and RA3 holds full
    sizing to 8%.
    """
    ra3 = load_protocol()["risk_architecture"]
    ra2 = json.loads(
        (PROJECT_ROOT / "config" / "generation_2" / "g2_rotation_ra1_protocol.json").read_text(
            encoding="utf-8"
        )
    )["risk_architecture"]
    ra3_scalars = _band_scalars(ra3)
    ra2_scalars = _band_scalars(ra2)
    return {
        "attempt_2_architecture_id": ra2["id"],
        "attempt_3_architecture_id": ra3["id"],
        "attempt_2_band_scalars": ra2_scalars,
        "attempt_3_band_scalars": ra3_scalars,
        "attempt_2_full_sizing_band": _full_sizing_band(ra2_scalars),
        "attempt_3_full_sizing_band": _full_sizing_band(ra3_scalars),
        "band_indices_are_not_comparable": (
            f"RA2 declares {len(ra2_scalars)} bands and RA3 declares {len(ra3_scalars)}, so the same "
            "integer index denotes a different drawdown band in each. Compare the sizing scalar an "
            "index maps to, or the session count in the full-sizing band; do not compare the index."
        ),
        "source": "config/generation_2/g2_rotation_ra1_protocol.json (read-only, Attempt 2 closed)",
    }


def ladder_engagement_comparison(runs: Sequence[GridRunRA3]) -> dict[str, Any]:
    """The section 4.3 requirement: show that RA3's ladder behaviour is not RA2's.

    Six integer event counters are compared run by run against Attempt 2's recorded values, plus the
    session count in the full-sizing band, which is the quantity the one architectural change targets
    directly.

    If **every** counter matched on **every** run this would raise rather than report. RA3's whole
    content is a band table that stops throttling below an 8% drawdown where RA2 throttled from 5%;
    identical ladder statistics across thirty-six runs would mean the new table never took effect,
    which is a defect in the engine wiring and not a result about the strategy.
    """
    counterparts = attempt_2_counterparts()
    prior = attempt_2_grid_rows()
    ra3_full = counterparts["attempt_3_full_sizing_band"]
    ra2_full = counterparts["attempt_2_full_sizing_band"]

    per_statistic: dict[str, dict[str, Any]] = {
        key: {"attempt_3_total": 0, "attempt_2_total": 0, "runs_differing": 0}
        for key in _LADDER_ENGAGEMENT_KEYS
    }
    full_sizing = {"attempt_3_total": 0, "attempt_2_total": 0, "runs_differing": 0}
    identical_runs: list[str] = []
    compared = 0

    for run in runs:
        key = (run.variant.lookback_months, run.variant.top_k, run.variant.frequency, run.label)
        row = prior.get(key)
        if row is None:
            raise ConfigViolation(f"Attempt 2 recorded no run at grid coordinates {key}")
        compared += 1
        mine = _risk_columns(run)
        differed = False
        for name in _LADDER_ENGAGEMENT_KEYS:
            a, b = int(mine[name]), int(row[name])
            per_statistic[name]["attempt_3_total"] += a
            per_statistic[name]["attempt_2_total"] += b
            if a != b:
                per_statistic[name]["runs_differing"] += 1
                differed = True
        a = int(mine["ladder_sessions_in_band"].get(ra3_full, 0))
        b = int(row["ladder_sessions_in_band"].get(ra2_full, 0))
        full_sizing["attempt_3_total"] += a
        full_sizing["attempt_2_total"] += b
        if a != b:
            full_sizing["runs_differing"] += 1
            differed = True
        if not differed:
            identical_runs.append(run.run_id)

    for stats in per_statistic.values():
        stats["differs"] = stats["runs_differing"] > 0
    full_sizing["differs"] = full_sizing["runs_differing"] > 0

    any_differs = full_sizing["differs"] or any(s["differs"] for s in per_statistic.values())
    if not any_differs:
        raise InvariantViolation(
            f"RA3 reproduced every one of Attempt 2's ladder, lockout and stop statistics across all "
            f"{compared} runs. RA3's only content is a band table that holds full sizing to an 8% "
            "drawdown where RA2 throttled from 5%; identical statistics mean the new table did not "
            "take effect, which is an engine defect rather than a result."
        )

    return {
        "requirement": (
            "Operating instruction section 4.3: run the grid fresh under RA3 and verify that at "
            "least the ladder-engagement statistics differ from Attempt 2's."
        ),
        "runs_compared": compared,
        "attempt_2_source": str(ATTEMPT_2_GRID_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "statistics_compared": list(_LADDER_ENGAGEMENT_KEYS),
        "per_statistic": per_statistic,
        "sessions_at_full_sizing": dict(
            full_sizing,
            attempt_3_band=ra3_full,
            attempt_2_band=ra2_full,
            note=(
                "The band index differs between the two architectures; the comparison is between "
                "the sessions spent at sizing scalar 1.00 on each side, which is the same quantity."
            ),
        ),
        "runs_identical_on_every_compared_statistic": identical_runs,
        "at_least_one_statistic_differs": any_differs,
        "band_indices_are_not_comparable": counterparts["band_indices_are_not_comparable"],
    }


# -- the descriptive record ------------------------------------------------------------------------


def _risk_columns(run: GridRunRA3) -> dict[str, Any]:
    """The ten ladder, lockout and stop statistics, in the column names Attempt 2 used."""
    ladder = run.risk["ladder"]
    lockout = run.risk["lockout"]
    stops = run.risk["stops"]
    return {
        "ladder_descents": ladder["descents"],
        "ladder_ascents": ladder["ascents"],
        "ladder_deepest_band": ladder["deepest_band"],
        "ladder_final_band": ladder["final_band"],
        "ladder_sessions_in_band": dict(ladder["sessions_in_band"]),
        "lockout_arms": lockout["arms"],
        "lockout_recoveries_blocked": lockout["recoveries_blocked"],
        "stops_triggered": stops["triggered"],
        "stops_filled": stops["filled"],
        "stops_preempted_by_signal_exit": stops["preempted_signal_exit"],
    }


def grid_report(
    runs: Sequence[GridRunRA3],
    *,
    selection: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """The descriptive record the seal requires for all eighteen variants, in grid order.

    ``reported_for_every_variant_but_not_gating`` lists eighteen quantities, every one of them "both
    runs", and this function is where they are produced. They are produced *after* the selection and
    are not an input to it. The two Attempt 2 quantities the seal names outright as non-inputs —
    ladder activations and lockout triggers — are here for the same reason they were there.

    Two of the eighteen are new to Attempt 3. ``selection``, when supplied, adds SEL-2's stability
    score for the row's variant with its four per-quantity components and every neighbour's identity
    and score; ``attempt_2`` carries the counterpart of each ladder, lockout and stop statistic, so
    the comparison the attempt turns on is on the same row as the figure it compares.
    """
    by_key = {(run.variant.variant_id, run.label): run for run in runs}
    prior = attempt_2_grid_rows()
    scores = (selection or {}).get("result", {}).get("all_scores", {})
    rows: list[dict[str, Any]] = []
    for variant in rotation_variants():
        for label in run_labels():
            run = by_key.get((variant.variant_id, label))
            if run is None:
                continue
            metrics = run.measurement
            risk = run.risk
            throttle = risk["throttle"]
            combined = risk["combined_scalar"]
            columns = _risk_columns(run)
            key = (variant.lookback_months, variant.top_k, variant.frequency, label)
            counterpart = prior[key]
            row = {
                "grid_index": variant.index,
                "variant_id": variant.variant_id,
                "lookback_months": variant.lookback_months,
                "top_k": variant.top_k,
                "rebalance_frequency": variant.frequency,
                "label": label,
                "scenario": run.scenario,
                # -- the five gate quantities, reported for every variant
                "total_return": metrics["total_return"],
                "max_drawdown": metrics["max_drawdown"],
                "profit_factor": metrics["profit_factor"],
                "closed_trades": metrics["closed_trades"],
                "closed_episodes": len(run.ledger.closed_episodes),
                # -- shutdown, the selection screen
                "research_shutdown_events": 1 if run.shutdown_fired else 0,
                "shutdown_session": metrics["shutdown_session"],
                "fills": run.fill_count,
                # -- RA3, the thing this attempt exists to test
                **columns,
                "throttle_legs_scheduled": throttle["legs_scheduled"],
                "throttle_legs_below_min_notional": throttle["legs_below_min_notional"],
                "throttle_sessions_breaching_ceiling": throttle["sessions_breaching_ceiling"],
                "max_gross_fraction_observed": risk["max_gross_fraction_observed"],
                "max_gross_fraction_session": risk["max_gross_fraction_session"],
                "combined_scalar_minimum": combined["minimum"],
                "combined_scalar_mean": combined["mean"],
                "combined_scalar_sessions_below_one": combined["sessions_below_one"],
                "volatility_scalar_minimum": risk["volatility_scalar"]["minimum"],
                "volatility_scalar_sessions_below_one": risk["volatility_scalar"][
                    "sessions_below_one"
                ],
                # -- Attempt 2's counterpart of each of the above ten, on the same row
                "attempt_2": {
                    "variant_id": counterpart["variant_id"],
                    "matched_on": [
                        "lookback_months",
                        "top_k",
                        "rebalance_frequency",
                        "label",
                    ],
                    **{name: counterpart[name] for name in _RISK_COUNTERPART_KEYS},
                    "combined_scalar_minimum": counterpart["combined_scalar_minimum"],
                    "combined_scalar_sessions_below_one": counterpart[
                        "combined_scalar_sessions_below_one"
                    ],
                    # Named on the row rather than only in the surrounding evidence, because these
                    # three are the ones a reader would otherwise diff as integers. RA2 has four
                    # bands and RA3 three; see attempt_2_counterparts() for the scalar mapping.
                    "columns_that_are_not_comparable_as_integers": [
                        "ladder_deepest_band",
                        "ladder_final_band",
                        "ladder_sessions_in_band",
                    ],
                },
                # -- Attempt 1's descriptive columns, carried unchanged
                "cagr": metrics["cagr"],
                "sharpe": metrics["sharpe"],
                "daily_return_stdev": metrics["daily_return_stdev"],
                "exposure_fraction": metrics["exposure_fraction"],
                "win_rate": metrics["win_rate"],
                "average_win": metrics["average_win"],
                "average_loss": metrics["average_loss"],
                "longest_flat_streak_sessions": metrics["longest_flat_streak_sessions"],
                # "Traded" is counted off the fills, not off the closed trades: a position still
                # open at the run end contributes a fill and no trade, and the seal asks for
                # distinct symbols traded, not distinct symbols realised.
                "distinct_symbols_traded": len({f.fill.symbol for f in run.result.fills}),
                "distinct_symbols_with_closed_trades": len(metrics["contribution_by_symbol"]),
                # -- digests, for AT-F
                "trades_digest": metrics["trades_digest"],
                "equity_digest": metrics["equity_digest"],
                "ranking_digest": run.strategy_evidence["ranking_digest"],
                "risk_state_digest": risk["risk_state_digest"],
                "risk_state_sessions": risk["risk_state_sessions"],
                "scheduled_rebalances": run.strategy_evidence["scheduled_rebalances"],
                "executed_rebalances": run.strategy_evidence["executed_rebalances"],
                # -- the section 8 reconciliation, per run
                "reconciliation_single_leg_compared": run.reconciliation["single_leg_compared"],
                "reconciliation_mismatches": run.reconciliation["mismatch_count"],
                "reconciliation_vacuous": run.reconciliation["vacuous"],
            }
            # SEL-2's score is per variant, not per run — the counters it scores are already summed
            # across both runs — so the same block appears on the variant's base and stress rows.
            if variant.variant_id in scores:
                mine = scores[variant.variant_id]
                row["selection_score"] = {
                    "rule_id": SELECTION_RULE_ID,
                    "instability_score": mine["instability_score"],
                    "per_quantity_mean_dissimilarity": mine["per_quantity_mean_dissimilarity"],
                    "per_quantity_pairs_zero_on_both_sides": mine[
                        "per_quantity_pairs_zero_on_both_sides"
                    ],
                    "own_quantities_summed_across_runs": mine["own_quantities"],
                    "neighbours": [
                        {
                            "variant_id": neighbour_id,
                            "instability_score": scores[neighbour_id]["instability_score"],
                        }
                        for neighbour_id in mine["neighbours"]
                    ],
                    "is_selected_representative": (
                        variant.variant_id == (selection or {}).get("selected_variant_id")
                    ),
                }
            rows.append(row)
    return rows
