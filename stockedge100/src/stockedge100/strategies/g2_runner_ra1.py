"""Attempt 2's grid runner: thirty-six runs, one return-blind selection, one gate input set.

This is Attempt 1's ``g2_runner`` re-derived against Attempt 2's seal, not copied from it. The two
seals disagree on four key names and on one substantive rule, and every one of those differences is
a place where a copied line would have gone on doing Attempt 1's thing while claiming to do
Attempt 2's:

============================  ==============================  =====================================
what                          Attempt 1 (``SE100-CFG-3101``)   Attempt 2 (``SE100-CFG-3103``)
============================  ==============================  =====================================
selection step key            ``name``                        ``criterion``
run span session count key    ``run_sessions``                ``sessions``
cost scenarios                derived from the label alone    also declared as ``scenarios``
gate scope                    ``#BASE`` run only              "across both of its runs"
============================  ==============================  =====================================

The fourth is not a rename. It is a contradiction between two co-sealed Attempt 2 artifacts, and
:func:`gate_inputs` resolves it in the only direction a governance document may be resolved. See
``G2A2-CONFLICT-25`` below.

What this module adds over Attempt 1's runner
---------------------------------------------

``verify_attempt_1_modules``
    AT-H. The nine Attempt 1 modules re-hash to the digests the sealed governance JSON recorded.
    The seal names three parties who must check this — "the sealer, **the runner** and the post-build
    sweep" — so the check runs at the head of :func:`run_grid`, before a single session is stepped,
    rather than being left to the report.

``recheck_run_span``
    The seal's ``run_span.recheck_requirement`` is "The runner recomputes every value below from the
    loaded series and refuses to run if any differs." Recomputed from the guard-loaded series **in
    memory**, then cross-checked against
    :func:`~stockedge100.reporting.g2_rotation_preregistration.measure_span`, which derives the same
    quantities independently from the partition lock's session lists. Two derivations that agree are
    evidence; one derivation is an assumption.

the episode ledger, on every run
    ``evaluation_integrity_rules`` §8 (index 7) says the reconciliation runs "on every run, not only
    on the representative's". A ledger is therefore built and reconciled for all thirty-six runs
    inside :func:`run_one`, and a §8 failure halts the grid where it happens rather than surfacing
    thirty-five runs later as a gate anomaly.

``G2A2-CONFLICT-25`` — the gate is scoped by two seals that disagree
-------------------------------------------------------------------

``SE100-CFG-3103`` says the gate is "evaluated on the selected representative variant only, across
both of its runs", and that "a variant satisfies a gate condition only if both of its runs satisfy
it. The stressed cost model is not a sensitivity check that may be waived."

``SE100-CFG-3104`` measures S3-C1 over "the representative's **base run**", measures S3-C4 the same
way, and lists "the representative's stress run, in full" under ``reported_but_not_gating`` with the
sentence "the stress cost assumption **gates nothing at Gate 3**".

Both were sealed in the same session and neither outranks the other. ``CLAUDE.md``'s precedence rule
resolves a conflict between documents of *different* rank by adopting the more restrictive value;
generalised to two seals of equal rank, the reading that cannot manufacture a pass wins. So:

* admission requires all seven conditions satisfied on ``#BASE`` **and** S3-C1..S3-C6 satisfied on
  ``#STRESS``;
* S3-C7 is evaluated **once, on base runs**, because its own ``what_is_read`` fixes the neighbour
  side to "each neighbour's base-run equity-curve total return and its sign. Nothing else about a
  neighbour enters this condition." A stress-side S3-C7 would need either a mixed-basis comparison
  or a neighbour figure the seal forbids reading;
* both condition sets are reported in full, so a reader can see exactly what the permissive
  base-only reading would have given. The restriction narrows what passes; it hides nothing.

Attempt 1 had no such ambiguity — its protocol said "the selected representative's #BASE run only"
with ``stress_run_treatment: "reported, not gating"`` — which is why this is disclosed as an
Attempt 2 conflict rather than carried from one.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, fields
from typing import Any, Callable, Sequence

from stockedge100.audit import sha256_file
from stockedge100.backtest.config import PROJECT_ROOT
from stockedge100.backtest.costs import SCENARIOS
from stockedge100.backtest.dataset import PriceSeries
from stockedge100.backtest.errors import ConfigViolation, InvariantViolation
from stockedge100.backtest.g2_costs import derive_mapping, rotation_cost_model
from stockedge100.backtest.g2_engine_ra1 import RotationEngineRA1
from stockedge100.backtest.g2_episodes_ra1 import EpisodeLedger, build_episode_ledger
from stockedge100.data.calendar import sessions_between
from stockedge100.reporting.g2_rotation_preregistration import (
    QUARTER_MONTHS,
    measure_span,
    month_offset,
)
from stockedge100.strategies import g2_window_guard as guard
from stockedge100.strategies.g2_gate_ra1 import (
    assert_reconciliation_non_vacuous,
    load_criteria,
    neighbours_of,
)
from stockedge100.strategies.g2_rotation_ra1 import (
    RotationCandidateRA1,
    RotationVariantRA1,
    build_candidate,
    eligible_universe,
    load_protocol,
    rotation_variants,
    variant_by_id,
)
from stockedge100.strategies.runner import measure, trade_ledger

__all__ = [
    "GATE_RUN_LABEL",
    "SELECTION_FIELD_NAMES",
    "STRESS_RUN_LABEL",
    "GridRunRA1",
    "SelectionInputRA1",
    "gate_inputs",
    "grid_report",
    "load_grid_dataset",
    "recheck_run_span",
    "run_for",
    "run_grid",
    "run_labels",
    "run_one",
    "scenario_for_label",
    "sealed_steps",
    "select_representative",
    "selection_inputs",
    "verify_attempt_1_modules",
]

#: The only fields the representative selection is permitted to see. AT-I asserts at import that the
#: dataclass below carries exactly these and nothing else.
SELECTION_FIELD_NAMES = ("variant_id", "shutdown_events", "fill_count", "per_run")

#: The run label whose figures every Gate 3 condition reads. The stress label gates S3-C1..S3-C6 too
#: under ``G2A2-CONFLICT-25``; it is never the basis for S3-C7's neighbour comparison.
GATE_RUN_LABEL = "#BASE"
STRESS_RUN_LABEL = "#STRESS"

#: The sealed governance record of the Attempt 1 module digests. ``config/`` deliberately does not
#: carry them — see ``attempt_1_modules_immutable.digests_not_recorded_here`` — so AT-H reads them
#: from here.
GOVERNANCE_PROTOCOL_PATH = (
    PROJECT_ROOT / "governance" / "generation_2" / "STAGE_3_G2_ROTATION_RA1_PROTOCOL.json"
)
GOVERNANCE_PROTOCOL_ID = "SE100-GOV-2005"


def _governance_protocol() -> dict[str, Any]:
    import json

    document = json.loads(GOVERNANCE_PROTOCOL_PATH.read_text(encoding="utf-8"))
    if document.get("artifact_id") != GOVERNANCE_PROTOCOL_ID:
        raise ConfigViolation(
            f"{GOVERNANCE_PROTOCOL_PATH.name} declares artifact_id "
            f"{document.get('artifact_id')!r}; {GOVERNANCE_PROTOCOL_ID!r} is required"
        )
    return document


# -- AT-H: Attempt 1 is not touched ----------------------------------------------------------------


def verify_attempt_1_modules() -> dict[str, Any]:
    """AT-H. Every module in ``attempt_1_modules_immutable`` re-hashes to its recorded digest.

    Two lists are compared, not one. ``config/`` declares *which* modules are immutable and
    ``governance/`` records *what* they hashed to at seal time; a module dropped from one and not the
    other is itself a finding, so disagreement between the lists refuses before any file is read.

    A difference is a governance failure, not a value to update. The seal is explicit: "Any
    difference is a governance failure, not a value to update."
    """
    declared = load_protocol()["attempt_1_modules_immutable"]
    recorded = _governance_protocol()["contamination_measurement"]["attempt_1_module_digests"]

    listed = list(declared["modules"])
    if sorted(listed) != sorted(recorded):
        raise ConfigViolation(
            "the config seal lists Attempt 1 modules "
            f"{sorted(set(listed) - set(recorded))} that the governance seal does not record, and "
            f"the governance seal records {sorted(set(recorded) - set(listed))} that the config seal "
            "does not list"
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
            "AT-H: Attempt 1 is closed and must not be touched. "
            f"missing={missing} digest_changed={moved}. "
            f"Recorded by {GOVERNANCE_PROTOCOL_ID} at seal time; a difference is a governance "
            "failure, not a value to update."
        )

    return {
        "requirement": "AT-H",
        "digest_source": f"{GOVERNANCE_PROTOCOL_ID} contamination_measurement.attempt_1_module_digests",
        "module_count": len(listed),
        "modules_verified": checked,
        "modules_that_moved": [],
        "note": declared["note"],
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
    """Map a sealed run label onto a cost scenario by two independent derivations that must agree.

    Attempt 1 had one derivation available: strip the ``#`` and require exactly one member of
    :data:`~stockedge100.backtest.costs.SCENARIOS` prefixed by what remains, which refuses an
    ambiguous or invented label instead of guessing. Attempt 2's seal adds an explicit positional
    ``scenarios`` list, so the label's index into ``labels`` gives a second answer.

    Both are computed and required to match. A hand-written table would have had neither; one
    derivation checked against a seal that agrees with it is worth more than either alone, because
    the failure mode being guarded is precisely a seal that was read wrong.
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
    partition-lock file, no seal — so that the result is an independent measurement of what is
    actually in memory rather than a restatement of what was declared.
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

    missing_at_start = sorted(
        symbol for symbol in symbols if run_start not in series[symbol].bars
    )

    return {
        "member_count": len(symbols),
        "run_start": run_start.isoformat(),
        "run_start_weekday": run_start.strftime("%A"),
        "run_start_lookback_reference": month_offset(run_start, -12).isoformat(),
        "session_before_run_start": None if previous is None else previous.isoformat(),
        "run_end": run_end.isoformat(),
        "run_sessions": len(run_sessions),
        "exchange_calendar_sessions": len(calendar),
        "session_lists_agree": [d.isoformat() for d in run_sessions]
        == [d.isoformat() for d in calendar],
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
    }


#: What ``run_span`` in the config seal calls each quantity, against what :func:`_span_from_series`
#: calls it. The session count is the one that bites: the config seal says ``sessions`` where the
#: governance seal and Attempt 1 both say ``run_sessions``.
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


def recheck_run_span(
    series: dict[str, PriceSeries], *, protocol: dict[str, Any] | None = None
) -> dict[str, Any]:
    """The seal's ``recheck_requirement``, three ways.

    "The runner recomputes every value below from the loaded series and refuses to run if any
    differs." So: recompute from the loaded series; compare against the config seal's ``run_span``;
    compare against the governance seal's fuller ``run_span_measured_from_disk``, which also carries
    the two rebalance calendars; and cross-check against
    :func:`~stockedge100.reporting.g2_rotation_preregistration.measure_span`, which derives the same
    quantities from the partition lock's session lists without loading a bar.

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
            differences.append(
                f"run_span.{sealed_key}: seal {want!r} vs recomputed {got!r}"
            )

    governance = _governance_protocol()["run_span_measured_from_disk"]
    for key in (
        "member_count",
        "run_start",
        "run_start_weekday",
        "run_start_lookback_reference",
        "session_before_run_start",
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
    ):
        want, got = governance[key], measured[key]
        if isinstance(want, list):
            want, got = list(want), list(got)
        if want != got:
            differences.append(
                f"run_span_measured_from_disk.{key}: seal {want!r} vs recomputed {got!r}"
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
            "the recomputed run span differs from the seal, and the seal's recheck_requirement is "
            "that the runner 'refuses to run if any differs':\n  - " + "\n  - ".join(differences)
        )

    return {
        "requirement": protocol["run_span"]["recheck_requirement"],
        "recomputed_from": "the guard-loaded PriceSeries in memory",
        "cross_checked_against": [
            f"{protocol['artifact_id']} run_span",
            f"{GOVERNANCE_PROTOCOL_ID} run_span_measured_from_disk",
            "reporting.g2_rotation_preregistration.measure_span()",
        ],
        "independent_derivation_keys_compared": shared,
        "differences": [],
        "measured": measured,
    }


# -- one run ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class GridRunRA1:
    """One completed run of one variant under one cost scenario, with its risk evidence.

    ``ledger`` is the episode ledger of ``evaluation_integrity_rules`` §8, built and reconciled for
    **every** run rather than only the representative's. ``trades`` is Attempt 1's flat trade ledger,
    kept because the grid report's Attempt 1 columns are defined against it and because the two
    disagreeing would itself be a finding.
    """

    variant: RotationVariantRA1
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
    variant: RotationVariantRA1,
    label: str,
    series: dict[str, PriceSeries],
    *,
    protocol: dict[str, Any] | None = None,
) -> GridRunRA1:
    """Execute one declared run under RA2.

    A fresh :class:`~stockedge100.strategies.g2_rotation_ra1.RotationCandidateRA1` is built per run,
    through :func:`~stockedge100.strategies.g2_rotation_ra1.build_candidate` so that the cost model is
    derived from ``(k, scenario)`` rather than chosen here. The candidate accumulates the ranking hash
    and the rebalance counters as it runs, so reusing one across two runs would blend two runs'
    evidence into one digest and destroy the determinism claim AT-F gates on.

    The engine is likewise fresh. RA2's band, lockout counter and volatility state are engine state;
    a reused engine would start Attempt 2's stress run inside the base run's drawdown ladder.
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
    engine = RotationEngineRA1(
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

    return GridRunRA1(
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
    variants: Sequence[RotationVariantRA1] | None = None,
    labels: Sequence[str] | None = None,
    progress: Callable[[int, int, GridRunRA1], None] | None = None,
    verify: bool = True,
) -> tuple[GridRunRA1, ...]:
    """Every declared run, unconditionally.

    The loop is variant-major and label-minor purely so a progress log reads in grid order. Nothing
    downstream depends on that order, and nothing in the loop inspects a completed run: the seal
    declares all thirty-six in advance and none is conditional on another's outcome.

    ``verify`` runs AT-H and the run-span recheck before the first session is stepped. It exists as a
    parameter only so that a unit test can drive one cell of the grid against a fixture series; the
    real grid run leaves it at ``True``.

    ``variants`` and ``labels`` are likewise for tests that need one cell. When both are left at
    their defaults the full cross product runs and the sealed ``total_runs`` is asserted.
    """
    protocol = load_protocol()
    if verify:
        verify_attempt_1_modules()
    if series is None:
        series = load_grid_dataset()
    if verify:
        recheck_run_span(series, protocol=protocol)

    full = variants is None and labels is None
    grid = tuple(rotation_variants()) if variants is None else tuple(variants)
    which = run_labels() if labels is None else tuple(labels)

    total = len(grid) * len(which)
    runs: list[GridRunRA1] = []
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


@dataclass(frozen=True)
class SelectionInputRA1:
    """Everything the selection is permitted to know about one variant.

    Four fields, and every one is return-blind: an identifier, a count of research-shutdown events, a
    count of fills, and the same two counts split per declared run. There is deliberately no field
    for return, drawdown, profit factor, Sharpe, equity, win rate or trade P&L, and no reference to
    the :class:`GridRunRA1` that produced it — so no step of :func:`select_representative` can reach a
    performance figure even by accident.

    Attempt 2's two new counters are absent for the same reason, and the seal says so outright:
    "The de-risk ladder activation count and the re-entry lockout trigger count are reported for
    every variant and are NOT selection inputs." They are risk-architecture outcomes, and screening
    on them would be selecting on how the architecture behaved rather than on the frozen rule.
    """

    variant_id: str
    shutdown_events: int
    fill_count: int
    per_run: tuple[tuple[str, int, int], ...]

    def to_json(self) -> dict[str, Any]:
        return {
            "variant_id": self.variant_id,
            "research_shutdown_events": self.shutdown_events,
            "fill_count": self.fill_count,
            "per_run": [
                {"label": label, "research_shutdown_events": events, "fills": fills}
                for label, events, fills in self.per_run
            ],
        }


#: AT-I, at import rather than at call time. The seal's ``structural_enforcement`` requires an
#: assertion that "the dataclass's actual field tuple equals the declared SELECTION_FIELD_NAMES";
#: raising here means a field added to sneak a performance figure into the selection cannot be
#: imported at all, let alone run.
_ACTUAL_SELECTION_FIELDS = tuple(field.name for field in fields(SelectionInputRA1))
if _ACTUAL_SELECTION_FIELDS != SELECTION_FIELD_NAMES:
    raise ConfigViolation(
        f"SelectionInputRA1 carries fields {list(_ACTUAL_SELECTION_FIELDS)}; the sealed "
        f"return-blind projection is exactly {list(SELECTION_FIELD_NAMES)}. A field outside that "
        "tuple could carry a performance figure into a selection the seal requires to be blind to "
        "one."
    )


def selection_inputs(runs: Sequence[GridRunRA1]) -> tuple[SelectionInputRA1, ...]:
    """Project the completed runs down to what the sealed rule may read.

    This is the single place a :class:`GridRunRA1` is touched on the way to a selection, and it reads
    exactly three things off each one: the variant id, whether the research shutdown fired, and how
    many fills there were. Grouping is by variant, and every declared label must be present exactly
    once — a variant missing its ``#STRESS`` run would otherwise pass the zero-shutdown screen on
    half the evidence the seal requires, since step 1's scope is "across BOTH runs of the variant".
    """
    declared_labels = run_labels()
    grouped: dict[str, dict[str, GridRunRA1]] = {}
    for run in runs:
        by_label = grouped.setdefault(run.variant.variant_id, {})
        if run.label in by_label:
            raise ConfigViolation(f"{run.run_id} was supplied more than once")
        by_label[run.label] = run

    inputs: list[SelectionInputRA1] = []
    for variant_id in sorted(grouped):
        by_label = grouped[variant_id]
        missing = [label for label in declared_labels if label not in by_label]
        extra = sorted(set(by_label) - set(declared_labels))
        if missing or extra:
            raise ConfigViolation(
                f"{variant_id}: the sealed rule screens across BOTH declared runs "
                f"{list(declared_labels)}; missing={missing} unexpected={extra}"
            )
        per_run = tuple(
            (label, 1 if by_label[label].shutdown_fired else 0, by_label[label].fill_count)
            for label in declared_labels
        )
        inputs.append(
            SelectionInputRA1(
                variant_id=variant_id,
                shutdown_events=sum(events for _, events, _ in per_run),
                fill_count=sum(fills for _, _, fills in per_run),
                per_run=per_run,
            )
        )
    return tuple(inputs)


# -- the sealed selection --------------------------------------------------------------------------

#: The sealed step order this module implements, keyed by ``order`` and valued by ``criterion``.
#: Restating it is a cross-check, not a source: if the seal's steps were read in a different order,
#: or a step renamed, the code below would go on applying the rule it was written for while claiming
#: to apply the sealed one. :func:`sealed_steps` refuses instead.
#:
#: The key is ``criterion``. Attempt 1's seal called it ``name``, and reading ``name`` here would
#: raise a ``KeyError`` rather than silently mis-apply — but only because the key is absent. That is
#: luck, not design, so the mapping is stated explicitly.
EXPECTED_STEP_CRITERIA = {
    1: "zero_research_shutdown_events",
    2: "lowest_turnover",
    3: "lexicographic_variant_id",
}


def sealed_steps(rule: dict[str, Any]) -> dict[int, dict[str, Any]]:
    """The three selection steps keyed by their declared ``order``, checked against what this module
    implements."""
    steps: dict[int, dict[str, Any]] = {}
    for entry in rule["steps"]:
        order = int(entry["order"])
        if order in steps:
            raise ConfigViolation(f"the sealed selection rule declares order {order} twice")
        steps[order] = entry
    if sorted(steps) != sorted(EXPECTED_STEP_CRITERIA):
        raise ConfigViolation(
            f"the sealed selection rule declares steps {sorted(steps)}; this module implements "
            f"{sorted(EXPECTED_STEP_CRITERIA)}"
        )
    for order, criterion in EXPECTED_STEP_CRITERIA.items():
        if steps[order]["criterion"] != criterion:
            raise ConfigViolation(
                f"sealed selection step {order} is {steps[order]['criterion']!r}; this module "
                f"implements {criterion!r}"
            )
    return steps


def select_representative(
    inputs: Sequence[SelectionInputRA1],
    *,
    protocol: dict[str, Any] | None = None,
    require_full_grid: bool = True,
) -> dict[str, Any]:
    """Apply the frozen three-step rule and record how it decided.

    Step 1 screens on zero research-shutdown events across **both** declared runs. Step 2 takes the
    lowest fill count summed over both runs. Step 3 breaks a remaining tie on the lexicographically
    smallest variant id — arbitrary on purpose, because an arbitrary tiebreak cannot be steered.

    Step 2's meaning widened in Attempt 2 and the rule did not widen with it. A fill count now
    includes STOP and THROTTLE legs, so a variant whose risk architecture worked hard looks like a
    high-turnover variant. The seal declares this rather than compensating for it: "disclosed as SC-4
    and the rule is not changed to compensate". Changing the tiebreak after seeing which variants the
    architecture acted on is exactly the degree of freedom the pre-registration exists to remove.

    If nothing survives step 1 the sealed ``no_candidate_path`` applies and no representative is
    returned. The grid is not loosened and the screen is not narrowed to the base run: the caller
    takes that verdict to :func:`~stockedge100.strategies.g2_gate_ra1.stage_verdict_ra1` with
    ``representative_exists=False``.
    """
    protocol = load_protocol() if protocol is None else protocol
    rule = protocol["representative_selection_rule"]
    steps = sealed_steps(rule)
    step_1, step_2, step_3 = steps[1], steps[2], steps[3]

    supplied = [entry.variant_id for entry in inputs]
    if len(set(supplied)) != len(supplied):
        raise ConfigViolation(f"duplicate variant ids in the selection inputs: {sorted(supplied)}")
    if require_full_grid:
        declared = sorted(variant.variant_id for variant in rotation_variants())
        if sorted(supplied) != declared:
            raise ConfigViolation(
                "the selection runs over the complete declared grid; supplied "
                f"{len(supplied)} of {len(declared)} variants, "
                f"missing={sorted(set(declared) - set(supplied))} "
                f"unexpected={sorted(set(supplied) - set(declared))}"
            )

    ordered = tuple(sorted(inputs, key=lambda entry: entry.variant_id))
    eligible = tuple(entry for entry in ordered if entry.shutdown_events == 0)
    ineligible = tuple(entry for entry in ordered if entry.shutdown_events != 0)

    record: dict[str, Any] = {
        "rule_ref": f"{protocol['artifact_id']} representative_selection_rule",
        "frozen_before_any_variant_is_run": rule["frozen_before_any_variant_is_run"],
        "return_blind": rule["return_blind"],
        "unchanged_from_attempt_1": rule["unchanged_from_attempt_1"],
        "structural_enforcement": rule["structural_enforcement"],
        "return_blind_enforcement": (
            "select_representative receives only SelectionInputRA1 records, whose fields are "
            f"{list(SELECTION_FIELD_NAMES)} and are asserted equal to that tuple at import. No "
            "BacktestResult, measurement, equity curve, trade P&L, ladder activation count or "
            "lockout trigger count is in scope at the point the representative is decided."
        ),
        "variants_considered": len(ordered),
        "inputs": [entry.to_json() for entry in ordered],
        "step_1": {
            "order": 1,
            "criterion": step_1["criterion"],
            "scope": step_1["scope"],
            "eliminates": step_1["eliminates"],
            "eligible": [entry.variant_id for entry in eligible],
            "ineligible": [
                {"variant_id": entry.variant_id, "research_shutdown_events": entry.shutdown_events}
                for entry in ineligible
            ],
            "eligible_count": len(eligible),
        },
    }

    if not eligible:
        no_candidate = rule["no_candidate_path"]
        record.update(
            {
                "representative_variant_id": None,
                "representative_exists": False,
                "decided_at_step": None,
                "decided_by": "no_candidate_path",
                "step_2": None,
                "step_3": None,
                "no_candidate_path": no_candidate,
                "selection_note": (
                    f"All {len(ordered)} declared variants recorded at least one research-shutdown "
                    "event across their two declared runs, so no variant is eligible under step 1. "
                    "The sealed no_candidate_path applies: the grid is not loosened, the shutdown "
                    "threshold is not raised, the screen is not narrowed to the base run, the risk "
                    "constants are not retuned, and the rule is not revised post hoc."
                ),
            }
        )
        return record

    lowest = min(entry.fill_count for entry in eligible)
    tied = tuple(entry for entry in eligible if entry.fill_count == lowest)
    chosen = min(tied, key=lambda entry: entry.variant_id)

    if len(eligible) == 1:
        decided_at, decided_by = 1, "zero_research_shutdown_events"
        note = (
            f"Exactly one variant, {chosen.variant_id}, recorded zero research-shutdown events "
            f"across both declared runs; the other {len(ineligible)} did not. Step 1 decided; steps "
            "2 and 3 were not reached."
        )
    elif len(tied) == 1:
        decided_at, decided_by = 2, "lowest_turnover"
        note = (
            f"{len(eligible)} variants recorded zero research-shutdown events across both declared "
            f"runs. Among them {chosen.variant_id} had the lowest turnover, {lowest} fills summed "
            "over its two runs, and no other eligible variant matched that count. Step 2 decided; "
            "step 3 was not reached."
        )
    else:
        decided_at, decided_by = 3, "lexicographic_variant_id"
        note = (
            f"{len(eligible)} variants recorded zero research-shutdown events across both declared "
            f"runs, and {len(tied)} of them tied at the lowest turnover of {lowest} fills. The "
            f"lexicographically smallest variant id among the tie, {chosen.variant_id}, advanced."
        )

    record.update(
        {
            "representative_variant_id": chosen.variant_id,
            "representative_exists": True,
            "decided_at_step": decided_at,
            "decided_by": decided_by,
            "step_2": {
                "order": 2,
                "criterion": step_2["criterion"],
                "definition": step_2["definition"],
                "why_not_gross_notional": step_2["why_not_gross_notional"],
                "attempt_2_note": step_2["attempt_2_note"],
                "fill_counts": {entry.variant_id: entry.fill_count for entry in eligible},
                "lowest_fill_count": lowest,
                "tied_at_lowest": [entry.variant_id for entry in tied],
                "reached": decided_at >= 2,
            },
            "step_3": {
                "order": 3,
                "criterion": step_3["criterion"],
                "purpose": step_3["purpose"],
                "reached": decided_at == 3,
                "ordering": [
                    entry.variant_id for entry in sorted(tied, key=lambda e: e.variant_id)
                ],
            },
            "no_reselection": rule["no_reselection"],
            "second_fail_path": rule["second_fail_path"],
            "selection_note": note,
        }
    )
    return record


# -- what the gate is given ------------------------------------------------------------------------


def run_for(runs: Sequence[GridRunRA1], variant_id: str, label: str) -> GridRunRA1:
    """The one completed run matching ``(variant_id, label)``, or a refusal."""
    found = [run for run in runs if run.variant.variant_id == variant_id and run.label == label]
    if len(found) != 1:
        raise ConfigViolation(
            f"expected exactly one run for {variant_id}{label}; found {len(found)}"
        )
    return found[0]


def gate_inputs(
    runs: Sequence[GridRunRA1],
    variant_id: str,
    *,
    criteria: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble exactly what Gate 3 evaluates, under the ``G2A2-CONFLICT-25`` resolution.

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

    The neighbour set is not chosen here.
    :func:`~stockedge100.strategies.g2_gate_ra1.neighbours_of` derives it from the grid axes, and
    ``condition_7_ra1`` re-derives it and refuses a set that differs.
    """
    criteria = load_criteria() if criteria is None else criteria
    protocol = load_protocol()
    scope = protocol["gate_evaluation_scope"]
    both_gate = protocol["runs_per_variant"]["both_gate"]

    # The scope sentence is read rather than assumed, exactly as Attempt 1 read its own. Attempt 1
    # asserted that the sentence names #BASE; Attempt 2's does not name a label at all, so what is
    # asserted here is that it scopes the gate to more than one run and that the both_gate rule is
    # present to say which. A seal that had quietly reverted to Attempt 1's wording would fail this.
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
        for member in neighbours_of(variant, criteria)
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
        "scope_resolution": (
            "SE100-CFG-3103 scopes the gate across both runs and states that a condition is "
            "satisfied only if both runs satisfy it; SE100-CFG-3104 measures S3-C1 and S3-C4 on the "
            "base run and lists the stress run as reported_but_not_gating. Both were sealed in the "
            "same session and neither outranks the other, so the more restrictive reading is "
            "adopted: all seven conditions on #BASE, and S3-C1..S3-C6 also on #STRESS. S3-C7 is "
            "evaluated once, on base runs, because its own what_is_read fixes the neighbour side to "
            "base-run total return and gives no sealed basis for a stress-side comparison. Both "
            "condition sets are reported in full."
        ),
    }


# -- the descriptive record ------------------------------------------------------------------------


def grid_report(runs: Sequence[GridRunRA1]) -> list[dict[str, Any]]:
    """The descriptive record the seal requires for all eighteen variants, in grid order.

    ``reported_for_every_variant_but_not_gating`` lists sixteen quantities, every one of them "both
    runs", and this function is where they are produced. They are produced *after* the selection and
    are not an input to it: the standing of these figures is descriptive, and the two Attempt 2 ones
    — ladder activations and lockout triggers — are the two the seal names outright as non-inputs.
    """
    by_key = {(run.variant.variant_id, run.label): run for run in runs}
    rows: list[dict[str, Any]] = []
    for variant in rotation_variants():
        for label in run_labels():
            run = by_key.get((variant.variant_id, label))
            if run is None:
                continue
            metrics = run.measurement
            risk = run.risk
            ladder = risk["ladder"]
            lockout = risk["lockout"]
            stops = risk["stops"]
            throttle = risk["throttle"]
            combined = risk["combined_scalar"]
            rows.append(
                {
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
                    # -- RA2, the thing this attempt exists to test
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
            )
    return rows
