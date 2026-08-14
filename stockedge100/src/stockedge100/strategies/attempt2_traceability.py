"""The field-by-field map from every sealed Attempt 2 rule to the code that implements it.

The operating prompt requires this before any performance evaluation runs: "Build an explicit
field-by-field traceability map from every sealed rule to its implementation." A prose table would
satisfy the letter of that and nothing else, because a prose table cannot notice that the sealed field
it names was renamed, or that the function it points at was deleted. So the map is data, and
:func:`verify` resolves both ends of every row:

* the **sealed** end by walking the path into the digest-verified sealed document, so a row naming a
  field the seal does not carry raises rather than reading as covered;
* the **implementation** end by importing the module and walking the attribute chain, so a row naming
  code that does not exist raises the same way.

:func:`missing_coverage` then works the other direction, which is the direction that actually catches
an omission: it lists the sealed rule paths in :data:`REQUIRED_COVERAGE` that no row claims. A map is
only a traceability map if something fails when a rule is left out of it.

Three things this module deliberately does not do.

It does not compare a sealed rule's *text* against a docstring. Text equality between a specification
and a comment is not evidence that the code obeys the specification; the §12 unit, property and
adversarial tests are that evidence, and :attr:`Trace.verified_by` names them so the two artifacts
point at each other. The test module asserts those names resolve inside itself — this package never
imports ``tests``.

It does not hold a rule's text at all. Every string a reader needs is in the sealed file, reachable by
the row's own path, and :func:`resolved_rows` reads it from there at build time. Copying sealed prose
into ``src/`` would create a second copy able to drift from the seal, which is the failure mode the
project has already paid for twice.

It does not judge. A row asserts "this sealed field is implemented here"; whether the implementation
is *correct* is decided by the tests and, for the seven conditions, by
:mod:`stockedge100.strategies.gate` reading the seal itself.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from stockedge100.backtest.errors import ConfigViolation
from stockedge100.strategies.attempt2_candidates import C1, C2, C3
from stockedge100.strategies.attempt2_config import Attempt2Config

#: The three sealed documents a row may cite, and the :class:`Attempt2Config` attribute each is
#: loaded from. Every one is digest-verified by :func:`~.attempt2_config.load_attempt2_config`
#: before this module can resolve a single path against it.
DOCUMENTS: dict[str, str] = {
    "SE100-CFG-3003": "protocol",
    "SE100-CFG-3004": "binding",
    "SE100-CFG-3002": "criteria",
}

CANDIDATE_IDS: tuple[str, str, str] = (C1, C2, C3)

#: Per-candidate ``target`` implementations. The signal is the only rule that differs between the
#: three candidates; RA1 is shared, which is the whole point of ``risk_architecture.why_shared``.
_TARGET: dict[str, str] = {
    C1: "stockedge100.strategies.attempt2_candidates:PullbackRa1.target",
    C2: "stockedge100.strategies.attempt2_candidates:MeanReversionRa1.target",
    C3: "stockedge100.strategies.attempt2_candidates:DefensiveRegimeRa1.target",
}

_CLASS: dict[str, str] = {
    C1: "stockedge100.strategies.attempt2_candidates:PullbackRa1",
    C2: "stockedge100.strategies.attempt2_candidates:MeanReversionRa1",
    C3: "stockedge100.strategies.attempt2_candidates:DefensiveRegimeRa1",
}


@dataclass(frozen=True)
class Trace:
    """One sealed field, the code that implements it, and the tests that check the implementation."""

    document: str
    path: tuple[str, ...]
    implementation: tuple[str, ...]
    verified_by: tuple[str, ...]
    note: str

    def __post_init__(self) -> None:
        if self.document not in DOCUMENTS:
            raise ConfigViolation(
                f"{self.key}: {self.document!r} is not one of the sealed documents "
                f"{sorted(DOCUMENTS)}"
            )
        if not self.path:
            raise ConfigViolation(f"{self.document}: a trace row needs a sealed path")
        if not self.implementation:
            raise ConfigViolation(f"{self.key}: a trace row needs at least one implementation")
        if not self.verified_by:
            raise ConfigViolation(f"{self.key}: a trace row needs at least one verifying test")

    @property
    def key(self) -> str:
        return f"{self.document}:{'.'.join(self.path)}"

    def to_json(self) -> dict[str, Any]:
        return {
            "sealed_document": self.document,
            "sealed_path": list(self.path),
            "implementation": list(self.implementation),
            "verified_by": list(self.verified_by),
            "note": self.note,
        }


def _walk(root: Any, path: Sequence[str], key: str) -> Any:
    """Resolve a sealed path. A list segment matches on ``experiment_id`` or ``id``.

    Matching a list element by its own identifier rather than by index is deliberate: an index would
    keep resolving to *something* if the sealed order ever differed from what this map was written
    against, and would silently trace the wrong candidate's rule.
    """

    node = root
    for depth, segment in enumerate(path):
        where = f"{key} at {'.'.join(path[: depth + 1])}"
        if isinstance(node, dict):
            if segment not in node:
                raise ConfigViolation(f"{where}: the seal carries no such field")
            node = node[segment]
        elif isinstance(node, list):
            matches = [
                item
                for item in node
                if isinstance(item, dict)
                and segment in (item.get("experiment_id"), item.get("id"))
            ]
            if len(matches) != 1:
                raise ConfigViolation(
                    f"{where}: {len(matches)} list entries carry that experiment_id or id"
                )
            node = matches[0]
        else:
            raise ConfigViolation(f"{where}: cannot descend into a {type(node).__name__}")
    return node


def resolve_code(reference: str) -> Any:
    """``module:qualname`` to the live object, or a refusal naming what was missing.

    A dataclass field declared without a default is not a class attribute, so ``getattr`` cannot see
    it. ``Ra1Parameters`` declares all seven of its parameters that way on purpose — a default would
    be exactly the "implementation default that can change sealed behaviour" §7 requires be
    impossible. The field descriptor is the resolution in that case, which keeps a row able to name
    the parameter it traces rather than pointing vaguely at the class.
    """

    module_name, separator, qualname = reference.partition(":")
    if not separator or not qualname:
        raise ConfigViolation(f"{reference!r} is not a module:qualname reference")
    try:
        node: Any = importlib.import_module(module_name)
    except ImportError as exc:  # pragma: no cover - a missing module is a hard stop
        raise ConfigViolation(f"{reference}: {exc}") from exc
    walked = module_name
    for attribute in qualname.split("."):
        if hasattr(node, attribute):
            node = getattr(node, attribute)
        else:
            declared = getattr(node, "__dataclass_fields__", {})
            if attribute not in declared:
                raise ConfigViolation(f"{reference}: {walked} has no attribute {attribute!r}")
            node = declared[attribute]
        walked = f"{walked}.{attribute}"
    return node


def _document(config: Attempt2Config, name: str) -> dict[str, Any]:
    return getattr(config, DOCUMENTS[name])


def sealed_value(config: Attempt2Config, trace: Trace) -> Any:
    return _walk(_document(config, trace.document), trace.path, trace.key)


def _shared(name: str, implementation: Iterable[str], tests: Iterable[str], note: str) -> Trace:
    return Trace(
        document="SE100-CFG-3003",
        path=("shared_rules", "adopted_text_restated_for_readability", name),
        implementation=tuple(implementation),
        verified_by=tuple(tests),
        note=note,
    )


def _ra1(rung: str, field: str, implementation: Iterable[str], tests: Iterable[str], note: str) -> Trace:
    return Trace(
        document="SE100-CFG-3003",
        path=("risk_architecture", rung, field),
        implementation=tuple(implementation),
        verified_by=tuple(tests),
        note=note,
    )


def _candidate_traces() -> list[Trace]:
    """The per-candidate rows, generated over the three sealed ids.

    Generating them rather than writing three near-identical blocks means a field cannot be traced
    for two candidates and forgotten for the third — which is exactly the omission
    :func:`missing_coverage` exists to catch, caught one layer earlier.
    """

    rows: list[Trace] = []
    for candidate in CANDIDATE_IDS:
        base = ("experiments", candidate)
        planner = "stockedge100.strategies.attempt2_runner:plan_candidate"
        rows.extend(
            [
                Trace(
                    document="SE100-CFG-3003",
                    path=base + ("universe",),
                    implementation=(
                        "stockedge100.strategies.attempt2_runner:variant_specs",
                        "stockedge100.strategies.attempt2_candidates:traded_symbols",
                        "stockedge100.strategies.attempt2_runner:required_symbols",
                    ),
                    verified_by=(
                        "test_variant_specs_reproduce_the_sealed_universe",
                        "test_c3_defensive_null_neighbour_keeps_the_declared_universe",
                    ),
                    note=(
                        "The declared universe governs the run start for every variant; "
                        "traded_symbols narrows only what a variant may buy."
                    ),
                ),
                Trace(
                    document="SE100-CFG-3003",
                    path=base + ("warmup_sessions",),
                    implementation=(
                        "stockedge100.strategies.attempt2_runner:largest_lookback",
                        planner,
                    ),
                    verified_by=("test_warmup_reproduces_the_sealed_derivation",),
                    note="Recomputed from the variant grid, then compared with the sealed figure.",
                ),
                Trace(
                    document="SE100-CFG-3003",
                    path=base + ("warmup_derivation",),
                    implementation=("stockedge100.strategies.attempt2_runner:largest_lookback",),
                    verified_by=("test_warmup_reproduces_the_sealed_derivation",),
                    note="The derivation's maximum is recomputed, not restated.",
                ),
                Trace(
                    document="SE100-CFG-3003",
                    path=base + ("eligibility_rules",),
                    implementation=(
                        "stockedge100.strategies.runner:run_start_for",
                        planner,
                    ),
                    verified_by=("test_run_start_requires_warmup_for_every_declared_symbol",),
                    note="Adopted unchanged from Attempt 1's run_start_rule implementation.",
                ),
                Trace(
                    document="SE100-CFG-3003",
                    path=base + ("signal_timing",),
                    implementation=(
                        "stockedge100.backtest.engine:BacktestEngine.run",
                        "stockedge100.backtest.market:MarketView",
                    ),
                    verified_by=("test_decision_reads_no_bar_after_the_decision_session",),
                    note="Gate 2 validated timing; Attempt 2 adds no path that could bypass it.",
                ),
                Trace(
                    document="SE100-CFG-3003",
                    path=base + ("primary_parameters",),
                    implementation=(
                        "stockedge100.strategies.attempt2_runner:variant_specs",
                        "stockedge100.strategies.attempt2_risk:Ra1Parameters.from_parameters",
                    ),
                    verified_by=(
                        "test_primary_parameters_match_the_seal_exactly",
                        "test_ra1_parameters_have_no_defaults",
                    ),
                    note="Every RA1 key is required; no implementation default can supply one.",
                ),
                Trace(
                    document="SE100-CFG-3003",
                    path=base + ("signal_target_rule",),
                    implementation=(_TARGET[candidate],),
                    verified_by=(f"test_signal_target_rule_{candidate.split('-')[2].lower()}",),
                    note="The only rule that differs between the three candidates.",
                ),
                Trace(
                    document="SE100-CFG-3003",
                    path=base + ("entry_rule",),
                    implementation=(
                        "stockedge100.strategies.attempt2_risk:Ra1Candidate._entry_decision",
                        "stockedge100.strategies.attempt2_risk:Ra1Candidate._entry_budget",
                    ),
                    verified_by=(
                        "test_entry_emits_one_order_sized_by_ra1_2",
                        "test_lockout_blocks_entry_without_substitution",
                    ),
                    note="Shared, because every candidate's entry is RA1-2 plus its own target.",
                ),
                Trace(
                    document="SE100-CFG-3003",
                    path=base + ("exit_rule",),
                    implementation=(
                        "stockedge100.strategies.attempt2_risk:Ra1Candidate._exit_decision",
                        "stockedge100.strategies.attempt2_risk:Ra1Candidate._exit",
                    ),
                    verified_by=(
                        "test_exit_precedence_is_loss_control_then_max_hold_then_signal",
                    ),
                    note="Signal exits come from the candidate's own target returning something else.",
                ),
                Trace(
                    document="SE100-CFG-3003",
                    path=base + ("maximum_holding_period",),
                    implementation=(
                        "stockedge100.strategies.attempt2_risk:Ra1Parameters.max_hold",
                        "stockedge100.strategies.attempt2_risk:Ra1Candidate._exit_decision",
                    ),
                    verified_by=("test_max_hold_counts_decision_sessions_inclusively",),
                    note="H differs per candidate; the counting rule does not.",
                ),
                Trace(
                    document="SE100-CFG-3003",
                    path=base + ("position_sizing_rule",),
                    implementation=(
                        "stockedge100.strategies.attempt2_risk:Ra1Candidate._entry_budget",
                        "stockedge100.strategies.attempt2_risk:Ra1Candidate.entry_order",
                    ),
                    verified_by=(
                        "test_entry_emits_one_order_sized_by_ra1_2",
                        "test_attempt_1_entry_order_default_is_unreachable",
                    ),
                    note=(
                        "entry_order is overridden to raise, so the Attempt 1 95%-of-equity default "
                        "cannot size an Attempt 2 entry even by accident."
                    ),
                ),
                Trace(
                    document="SE100-CFG-3003",
                    path=base + ("maximum_exposure",),
                    implementation=(
                        "stockedge100.strategies.attempt2_risk:Ra1Parameters.f_base",
                        "stockedge100.strategies.attempt2_risk:Ra1Parameters.f_cap",
                    ),
                    verified_by=("test_no_entry_fraction_exceeds_f_base",),
                    note="Checked as an invariant inside _entry_budget as well as by the test.",
                ),
                Trace(
                    document="SE100-CFG-3003",
                    path=base + ("cash_allocation_rule",),
                    implementation=(
                        "stockedge100.backtest.engine:BacktestEngine",
                        "stockedge100.backtest.costs:CostModel.__init__",
                    ),
                    verified_by=("test_cash_is_the_residual_and_the_buffer_holds",),
                    note="The engine's cash accounting, unchanged from Gate 2.",
                ),
                Trace(
                    document="SE100-CFG-3003",
                    path=base + ("stop_or_shutdown_rule",),
                    implementation=(
                        "stockedge100.backtest.engine:BacktestEngine.run",
                        "stockedge100.strategies.attempt2_runner:shutdown_exits",
                    ),
                    verified_by=("test_shutdown_liquidates_and_never_rearms",),
                    note="The candidate never reads the ceiling; the engine enforces it.",
                ),
                Trace(
                    document="SE100-CFG-3003",
                    path=base + ("reentry_rule_after_a_stop",),
                    implementation=(
                        "stockedge100.strategies.attempt2_risk:Ra1Candidate.locked_out",
                        "stockedge100.strategies.attempt2_risk:Ra1Candidate._exit",
                    ),
                    verified_by=("test_lockout_lasts_five_decision_sessions_after_a_risk_exit",),
                    note="Set on the session that scheduled the exit, per RA1-6.",
                ),
                Trace(
                    document="SE100-CFG-3003",
                    path=base + ("conflict_rule",),
                    implementation=(
                        "stockedge100.strategies.attempt2_risk:Ra1Candidate.decide",
                        "stockedge100.strategies.base:Candidate.exit_order",
                    ),
                    verified_by=("test_flat_first_emits_only_the_sell_on_a_switch",),
                    note="decide returns the exit alone while a position is open.",
                ),
                Trace(
                    document="SE100-CFG-3003",
                    path=base + ("robustness_neighbours",),
                    implementation=("stockedge100.strategies.attempt2_runner:variant_specs",),
                    verified_by=(
                        "test_four_neighbours_per_candidate_exactly_as_registered",
                        "test_no_neighbour_is_ever_promoted",
                    ),
                    note="Four per candidate, diagnostic only, never promoted.",
                ),
                Trace(
                    document="SE100-CFG-3003",
                    path=base + ("max_variants",),
                    implementation=("stockedge100.strategies.attempt2_runner:variant_specs",),
                    verified_by=("test_variant_count_is_checked_against_the_seal",),
                    note="variant_specs refuses a count that differs from the sealed figure.",
                ),
                Trace(
                    document="SE100-CFG-3003",
                    path=base + ("gate_3_conditions_applied",),
                    implementation=("stockedge100.strategies.gate:evaluate_candidate",),
                    verified_by=("test_all_seven_conditions_are_evaluated_for_every_candidate",),
                    note=(
                        "All seven are evaluated for every candidate; C1 and C2 reach "
                        "NOT_APPLICABLE_BY_CONDITION_TEXT on S3-C6 rather than skipping it."
                    ),
                ),
                Trace(
                    document="SE100-CFG-3003",
                    path=base + ("experiment_id",),
                    implementation=(
                        _CLASS[candidate],
                        "stockedge100.strategies.attempt2_candidates:build_candidate",
                        "stockedge100.strategies.attempt2_candidates:ATTEMPT_2_EXPERIMENT_IDS",
                    ),
                    verified_by=(
                        "test_exactly_three_candidate_ids_are_implemented",
                        "test_an_unregistered_experiment_id_is_refused",
                    ),
                    note="build_candidate refuses any id the sealed protocol does not declare.",
                ),
            ]
        )
    return rows


TRACES: tuple[Trace, ...] = tuple(
    [
        # ---- shared rules adopted unchanged from Attempt 1 --------------------------------------
        _shared(
            "one_decision_per_session",
            ("stockedge100.backtest.engine:BacktestEngine.run",),
            ("test_one_decision_per_session_and_no_same_close_fill",),
            "Decision at the close of t, fill at the open of t+1; the engine refuses earlier.",
        ),
        _shared(
            "long_only",
            (
                "stockedge100.strategies.attempt2_risk:Ra1Candidate.decide",
                "stockedge100.backtest.costs:CostModel.__init__",
            ),
            ("test_at_most_one_open_position_and_no_short",),
            "decide never emits a BUY while a position is open.",
        ),
        _shared(
            "flat_first_rule",
            ("stockedge100.strategies.attempt2_risk:Ra1Candidate.decide",),
            ("test_flat_first_emits_only_the_sell_on_a_switch",),
            "RA1-7 is this rule; it is implemented once, in decide.",
        ),
        _shared(
            "insufficient_history_rule",
            (
                "stockedge100.strategies.attempt2_indicators:vol20",
                "stockedge100.strategies.attempt2_risk:Ra1Candidate._entry_budget",
            ),
            ("test_insufficient_history_blocks_the_entry_and_holds_cash",),
            "vol20 returns None; _entry_budget records NO_ENTRY_INSUFFICIENT_HISTORY.",
        ),
        _shared(
            "tie_break",
            ("stockedge100.strategies.attempt2_candidates:DefensiveRegimeRa1.target",),
            ("test_no_rule_depends_on_dictionary_or_file_order",),
            (
                "No Attempt 2 candidate ranks a multi-symbol set, so no tie arises; C3 selects by "
                "regime, not by comparison across symbols."
            ),
        ),
        _shared(
            "warmup_rule",
            ("stockedge100.strategies.attempt2_runner:largest_lookback",),
            ("test_warmup_reproduces_the_sealed_derivation",),
            "The maximum across the primary and all four neighbours, plus VOL20's 21 bars.",
        ),
        _shared(
            "run_start_rule",
            (
                "stockedge100.strategies.runner:run_start_for",
                "stockedge100.strategies.attempt2_runner:plan_candidate",
            ),
            ("test_run_start_requires_warmup_for_every_declared_symbol",),
            "The declared universe governs, so a neighbour dropping a symbol changes no window.",
        ),
        _shared(
            "warmup_data_source",
            ("stockedge100.strategies.attempt2_runner:plan_candidate",),
            ("test_warmup_history_comes_from_inside_the_development_window",),
            "Warm-up is drawn from inside the development window only.",
        ),
        _shared(
            "no_intraday",
            ("stockedge100.backtest.dataset:load_series",),
            ("test_only_daily_bars_are_loaded",),
            "The Stage 1 dataset is daily; no intraday source is reachable.",
        ),
        _shared(
            "no_machine_learning",
            ("stockedge100.strategies.attempt2_candidates:signal_parameter_values",),
            ("test_no_fitted_model_and_no_undeclared_parameter",),
            "Every parameter is a sealed literal; nothing is fitted.",
        ),
        _shared(
            "no_combination",
            ("stockedge100.strategies.attempt2_harness:run_all",),
            ("test_candidates_are_never_combined",),
            "Each candidate runs and is judged alone; no blend is constructed.",
        ),
        Trace(
            document="SE100-CFG-3003",
            path=("shared_rules", "replaced", "sizing_rule"),
            implementation=(
                "stockedge100.strategies.attempt2_risk:Ra1Candidate._entry_budget",
                "stockedge100.strategies.attempt2_risk:Ra1Candidate.entry_order",
            ),
            verified_by=(
                "test_entry_emits_one_order_sized_by_ra1_2",
                "test_attempt_1_entry_order_default_is_unreachable",
            ),
            note=(
                "The one shared rule Attempt 2 replaces. Direction of change is downward only, and "
                "the Attempt 1 default is made unreachable rather than merely unused."
            ),
        ),
        # ---- VOL20 --------------------------------------------------------------------------------
        Trace(
            document="SE100-CFG-3003",
            path=("indicator_definitions", "added", "VOL20"),
            implementation=(
                "stockedge100.strategies.attempt2_indicators:vol20",
                "stockedge100.strategies.attempt2_indicators:VOL20_BARS",
                "stockedge100.strategies.attempt2_indicators:VOL20_VARIANCE_DENOMINATOR",
                "stockedge100.strategies.attempt2_indicators:TRADING_DAYS_PER_YEAR",
            ),
            verified_by=(
                "test_vol20_follows_the_sealed_six_step_procedure",
                "test_vol20_is_undefined_below_twenty_one_bars",
                "test_vol20_uses_adj_close_not_close",
            ),
            note="The only indicator Attempt 2 adds. SMA and RSI are imported unchanged.",
        ),
        Trace(
            document="SE100-CFG-3003",
            path=("indicator_definitions", "adopted_text_restated_for_readability", "SMA"),
            implementation=("stockedge100.strategies.indicators:sma",),
            verified_by=("test_sma_and_rsi_are_the_sealed_attempt_1_implementations",),
            note="Imported, not re-implemented; a second copy is eventually the wrong copy.",
        ),
        Trace(
            document="SE100-CFG-3003",
            path=("indicator_definitions", "adopted_text_restated_for_readability", "RSI"),
            implementation=(
                "stockedge100.strategies.indicators:wilder_rsi",
                "stockedge100.strategies.attempt2_config:Attempt2Config.rsi_warmup_changes",
            ),
            verified_by=("test_sma_and_rsi_are_the_sealed_attempt_1_implementations",),
            note="warmup_changes is read from the digest-verified Attempt 1 protocol, not restated.",
        ),
        Trace(
            document="SE100-CFG-3003",
            path=("indicator_definitions", "not_used_by_attempt_2"),
            implementation=("stockedge100.strategies.attempt2_candidates:signal_parameter_values",),
            verified_by=("test_unused_indicators_are_not_called_by_attempt_2",),
            note="ROLLING_MAX, ROLLING_MIN and MOMENTUM are never called from Attempt 2 code.",
        ),
        # ---- RA1 -----------------------------------------------------------------------------------
        _ra1(
            "RA1-1",
            "rule",
            (
                "stockedge100.strategies.attempt2_risk:Ra1Parameters.f_base",
                "stockedge100.strategies.attempt2_risk:Ra1Candidate._entry_budget",
            ),
            ("test_no_entry_fraction_exceeds_f_base",),
            "An invariant inside _entry_budget refuses a fraction above f_base.",
        ),
        _ra1(
            "RA1-1",
            "applies_to_defensive_leg",
            ("stockedge100.strategies.attempt2_risk:Ra1Candidate._entry_budget",),
            ("test_defensive_leg_gets_no_carve_out",),
            "SHY is sized by the same code path as SPY; no instrument-specific branch exists.",
        ),
        _ra1(
            "RA1-2",
            "rule",
            (
                "stockedge100.strategies.attempt2_risk:Ra1Candidate._entry_budget",
                "stockedge100.strategies.attempt2_indicators:vol20",
            ),
            (
                "test_entry_emits_one_order_sized_by_ra1_2",
                "test_zero_volatility_blocks_entry_before_any_division",
                "test_volatility_floor_blocks_entry_below_five_percent",
                "test_size_floor_blocks_entry_below_one_dollar",
            ),
            "f = min(f_cap, f_vol); the four blocked-entry reasons are each their own branch.",
        ),
        _ra1(
            "RA1-2",
            "applies",
            ("stockedge100.strategies.attempt2_risk:Ra1Candidate._entry_decision",),
            ("test_sizing_is_read_at_entry_only",),
            "Sizing is computed at entry only and never re-read while a position is open.",
        ),
        _ra1(
            "RA1-3",
            "rule",
            (
                "stockedge100.strategies.attempt2_risk:Ra1Candidate._loss_control_triggered",
                "stockedge100.strategies.attempt2_risk:Ra1Parameters.loss_control",
            ),
            (
                "test_loss_control_triggers_at_exactly_eight_percent",
                "test_loss_control_reference_is_the_decision_close",
                "test_unfilled_entry_discards_its_reference_price",
            ),
            "P_ref is the decision close that scheduled the entry, per the sealed rule.",
        ),
        _ra1(
            "RA1-4",
            "rule",
            (
                "stockedge100.strategies.attempt2_risk:Ra1Candidate._exit_decision",
                "stockedge100.strategies.attempt2_risk:Ra1Parameters.max_hold",
            ),
            ("test_max_hold_counts_decision_sessions_inclusively",),
            "sessions_held counts decision sessions with the symbol held, current one included.",
        ),
        _ra1(
            "RA1-5",
            "rule",
            (
                "stockedge100.strategies.attempt2_risk:Ra1Parameters.f_cap",
                "stockedge100.strategies.attempt2_risk:Ra1Candidate._drawdown",
                "stockedge100.strategies.attempt2_risk:Ra1Parameters.band_of",
            ),
            (
                "test_ladder_rungs_are_threshold_inclusive",
                "test_hwm_updates_every_decision_session_whether_flat_or_not",
                "test_ladder_never_blocks_an_entry",
            ),
            "Rungs are inclusive at 0.08 and 0.10; the deepest level RA1 reacts to is 10%.",
        ),
        _ra1(
            "RA1-5",
            "equity_series_identity",
            ("stockedge100.strategies.attempt2_risk:Ra1Candidate._begin_session",),
            ("test_hwm_updates_every_decision_session_whether_flat_or_not",),
            "The hwm is taken from context.equity, the same series the shutdown reads.",
        ),
        _ra1(
            "RA1-6",
            "rule",
            (
                "stockedge100.strategies.attempt2_risk:Ra1Candidate.locked_out",
                "stockedge100.strategies.attempt2_risk:Ra1Candidate._exit",
            ),
            (
                "test_lockout_lasts_five_decision_sessions_after_a_risk_exit",
                "test_signal_exit_creates_no_lockout",
            ),
            "Release index is k + R + 1, cross-checked against RA1-7's six-session statement.",
        ),
        _ra1(
            "RA1-7",
            "rule",
            ("stockedge100.strategies.attempt2_risk:Ra1Candidate.decide",),
            ("test_flat_first_emits_only_the_sell_on_a_switch",),
            "Shared flat_first_rule, adopted unchanged.",
        ),
        _ra1(
            "RA1-8",
            "rule",
            (
                "stockedge100.strategies.attempt2_risk:Ra1Candidate._entry_decision",
                "stockedge100.strategies.base:Candidate.exit_order",
            ),
            ("test_positions_are_all_or_nothing",),
            "One order per decision, never a partial entry or a partial exit.",
        ),
        _ra1(
            "exit_precedence",
            "order",
            (
                "stockedge100.strategies.attempt2_risk:EXIT_PRECEDENCE",
                "stockedge100.strategies.attempt2_risk:Ra1Candidate._exit_decision",
            ),
            ("test_exit_precedence_is_loss_control_then_max_hold_then_signal",),
            "The short-circuit order in _exit_decision is the precedence rule.",
        ),
        _ra1(
            "engine_shutdown_relationship",
            "candidate_behaviour",
            ("stockedge100.strategies.attempt2_risk:Ra1Candidate.decide",),
            ("test_candidate_emits_nothing_while_shutdown_is_active",),
            "Belt-and-braces: the engine already blocks entries.",
        ),
        Trace(
            document="SE100-CFG-3003",
            path=("risk_architecture", "prohibition_on_mechanical_targeting"),
            implementation=(
                "stockedge100.strategies.attempt2_risk:Ra1Parameters",
                "stockedge100.strategies.attempt2_risk:Ra1Parameters.ladder_rungs",
            ),
            verified_by=("test_no_ra1_constant_references_the_fifteen_percent_ceiling",),
            note=(
                "No RA1 constant equals 0.15 or lies between 0.10 and 0.15; RA1 is not a "
                "stop-at-14.99% device."
            ),
        ),
        # ---- protocol-level rules ------------------------------------------------------------------
        Trace(
            document="SE100-CFG-3003",
            path=("partitions",),
            implementation=(
                "stockedge100.backtest.window:ResearchWindow.check",
                "stockedge100.backtest.market:MarketView",
                "stockedge100.strategies.attempt2_harness:run_all",
            ),
            verified_by=(
                "test_validation_bounds_are_refused",
                "test_holdout_bounds_are_refused",
                "test_decision_reads_no_bar_after_the_decision_session",
            ),
            note="Enforcement is structural and does not depend on a candidate behaving well.",
        ),
        Trace(
            document="SE100-CFG-3003",
            path=("excluded_symbols",),
            implementation=("stockedge100.strategies.attempt2_runner:required_symbols",),
            verified_by=("test_no_excluded_symbol_is_ever_loaded",),
            note="Only the symbols the sealed universes name are loaded.",
        ),
        Trace(
            document="SE100-CFG-3003",
            path=("iteration_budget",),
            implementation=(
                "stockedge100.strategies.attempt2_harness:run_all",
                "stockedge100.strategies.attempt2_runner:variant_specs",
            ),
            verified_by=(
                "test_declared_run_counts_are_checked_against_the_seal",
                "test_variant_count_is_checked_against_the_seal",
            ),
            note="15 gating, 3 stress, 18 total, 0 revisions; all three totals are asserted.",
        ),
        Trace(
            document="SE100-CFG-3003",
            path=("cost_stress_treatment",),
            implementation=(
                "stockedge100.strategies.attempt2_runner:stress_evidence",
                "stockedge100.strategies.attempt2_runner:STRESS_FRAGILE",
            ),
            verified_by=(
                "test_stress_run_is_never_passed_to_the_gate",
                "test_stress_fragile_flag_changes_no_verdict",
            ),
            note="Non-gating by seal; the flag can neither admit nor reject a candidate.",
        ),
        Trace(
            document="SE100-CFG-3003",
            path=("missing_or_invalid_data_rule", "missing_indicator"),
            implementation=("stockedge100.strategies.attempt2_risk:Ra1Candidate._entry_budget",),
            verified_by=("test_insufficient_history_blocks_the_entry_and_holds_cash",),
            note="Falls to cash; never shortens the window.",
        ),
        Trace(
            document="SE100-CFG-3003",
            path=("missing_or_invalid_data_rule", "missing_bar_for_a_target"),
            implementation=(
                "stockedge100.strategies.attempt2_candidates:DefensiveRegimeRa1.target",
                "stockedge100.strategies.base:Candidate.bars_at",
            ),
            verified_by=("test_missing_bar_for_a_target_falls_through_to_cash",),
            note="C3's defensive leg falls to cash when SHY has no visible bar.",
        ),
        Trace(
            document="SE100-CFG-3003",
            path=("missing_or_invalid_data_rule", "stale_or_delisted"),
            implementation=("stockedge100.backtest.engine:BacktestEngine",),
            verified_by=("test_stale_marks_follow_the_gate_2_engine",),
            note="Gate 2 engine behaviour, unchanged.",
        ),
        Trace(
            document="SE100-CFG-3003",
            path=("missing_or_invalid_data_rule", "non_positive_adjusted_close"),
            implementation=("stockedge100.strategies.attempt2_indicators:vol20",),
            verified_by=("test_non_positive_adjusted_close_traps_rather_than_imputes",),
            note="ENGINE_CONTEXT traps rather than producing an infinity; nothing is imputed.",
        ),
        Trace(
            document="SE100-CFG-3003",
            path=("missing_or_invalid_data_rule", "data_repair_prohibited"),
            implementation=("stockedge100.backtest.dataset:load_series",),
            verified_by=("test_no_price_is_imputed_or_repaired",),
            note="No imputation, interpolation, fill, winsorisation or correction exists.",
        ),
        Trace(
            document="SE100-CFG-3003",
            path=("partial_or_failed_run_rule", "neighbour_fails_to_run"),
            implementation=("stockedge100.strategies.gate:condition_7",),
            verified_by=("test_a_missing_neighbour_makes_s3_c7_fail_not_pass",),
            note="NOT_RUN is not a pass.",
        ),
        Trace(
            document="SE100-CFG-3003",
            path=("partial_or_failed_run_rule", "primary_fails_to_run"),
            implementation=("stockedge100.strategies.attempt2_runner:run_variant",),
            verified_by=("test_a_run_short_of_the_window_end_is_refused",),
            note="A short run raises rather than being reported as a result.",
        ),
        Trace(
            document="SE100-CFG-3003",
            path=("partial_or_failed_run_rule", "partial_completion"),
            implementation=("stockedge100.strategies.attempt2_runner:run_variant",),
            verified_by=("test_a_run_short_of_the_window_end_is_refused",),
            note="Never patched, never extended.",
        ),
        Trace(
            document="SE100-CFG-3003",
            path=("reproducibility_requirements", "determinism"),
            implementation=(
                "stockedge100.strategies.attempt2_harness:run_all",
                "stockedge100.strategies.attempt2_runner:DETERMINISM_SUFFIX",
            ),
            verified_by=("test_a_rerun_reproduces_both_digests",),
            note="Each primary is re-run under a fresh candidate object and both digests compared.",
        ),
        Trace(
            document="SE100-CFG-3003",
            path=("reproducibility_requirements", "arithmetic"),
            implementation=(
                "stockedge100.backtest.costs:ENGINE_CONTEXT",
                "stockedge100.backtest.costs:exact",
            ),
            verified_by=("test_no_float_in_any_signal_sizing_or_risk_path",),
            note="Exact Decimal throughout; no rounding before a threshold comparison.",
        ),
        Trace(
            document="SE100-CFG-3003",
            path=("reproducibility_requirements", "ordering"),
            implementation=("stockedge100.strategies.attempt2_runner:variant_specs",),
            verified_by=("test_no_rule_depends_on_dictionary_or_file_order",),
            note="Variant order comes from the sealed file, not from a filesystem listing.",
        ),
        Trace(
            document="SE100-CFG-3003",
            path=("reproducibility_requirements", "random_seeds"),
            implementation=("stockedge100.strategies.attempt2_harness:run_all",),
            verified_by=("test_random_seeds_are_null_and_recorded_as_null",),
            note="Null by seal, recorded as null so its absence cannot read as an omission.",
        ),
        Trace(
            document="SE100-CFG-3003",
            path=("no_retuning_rule",),
            implementation=(
                "stockedge100.strategies.attempt2_config:load_attempt2_config",
                "stockedge100.strategies.attempt2_runner:variant_specs",
            ),
            verified_by=(
                "test_every_parameter_comes_from_the_digest_verified_seal",
                "test_no_neighbour_is_ever_promoted",
            ),
            note="No parameter has a source other than the sealed file.",
        ),
        Trace(
            document="SE100-CFG-3003",
            path=("benchmarks",),
            implementation=("stockedge100.strategies.reference:candidate_benchmarks",),
            verified_by=("test_no_benchmark_becomes_a_gate_condition",),
            note="Reported for every candidate; none is a hard condition.",
        ),
        Trace(
            document="SE100-CFG-3003",
            path=("primary_decision_rule",),
            implementation=(
                "stockedge100.strategies.gate:stage_verdict",
                "stockedge100.strategies.attempt2_harness:decisive_row",
            ),
            verified_by=("test_tokens_are_read_from_the_sealed_derivation",),
            note="Both tokens are read from verdict_token_derivation, never restated as literals.",
        ),
        Trace(
            document="SE100-CFG-3003",
            path=("permitted_parameter_grid_semantics",),
            implementation=("stockedge100.strategies.attempt2_runner:variant_specs",),
            verified_by=("test_the_grid_is_declared_but_never_searched",),
            note="The grid bounds what a neighbour may be; nothing searches it.",
        ),
        # ---- the binding ---------------------------------------------------------------------------
        Trace(
            document="SE100-CFG-3004",
            path=("admissible_candidate_exists", "frozen_rule"),
            implementation=(
                "stockedge100.strategies.gate:evaluate_candidate",
                "stockedge100.strategies.gate:stage_verdict",
                "stockedge100.strategies.attempt2_harness:decisive_row",
            ),
            verified_by=(
                "test_conjunction_within_candidate_and_disjunction_across",
                "test_the_conditions_table_carries_the_decisive_row",
            ),
            note="The one row that decides Gate 3.",
        ),
        Trace(
            document="SE100-CFG-3004",
            path=("admissible_candidate_exists", "satisfied_definition"),
            implementation=("stockedge100.strategies.gate:ConditionVerdict.satisfied",),
            verified_by=("test_not_evaluable_and_not_run_are_never_satisfied",),
            note="MET or NOT_APPLICABLE_BY_CONDITION_TEXT, and nothing else.",
        ),
        Trace(
            document="SE100-CFG-3004",
            path=("admissible_candidate_exists", "per_condition_rollup_is_not_the_gate"),
            implementation=("stockedge100.strategies.attempt2_harness:condition_rollup",),
            verified_by=(
                "test_rollup_aggregates_on_satisfaction_not_on_met",
                "test_rollup_carries_three_separate_lists",
            ),
            note="Aggregates on satisfaction; the recorded Attempt 1 false-FAIL cannot recur.",
        ),
        Trace(
            document="SE100-CFG-3004",
            path=("admissible_candidate_exists", "incoherent_combinations_refused"),
            implementation=("stockedge100.strategies.attempt2_harness:_refuse_incoherent",),
            verified_by=("test_each_incoherent_combination_is_refused",),
            note="Structural refusal, not a documented intention.",
        ),
        Trace(
            document="SE100-CFG-3004",
            path=("shutdown_behaviour",),
            implementation=(
                "stockedge100.backtest.engine:BacktestEngine.run",
                "stockedge100.strategies.attempt2_runner:shutdown_exits",
                "stockedge100.strategies.gate:condition_2",
            ),
            verified_by=(
                "test_shutdown_liquidates_and_never_rearms",
                "test_s3_c2_is_met_if_and_only_if_the_shutdown_never_fires",
            ),
            note="Enforced for all 18 runs; disabled only for the labelled SPY reference account.",
        ),
        Trace(
            document="SE100-CFG-3004",
            path=("rerun_policy",),
            implementation=("stockedge100.strategies.attempt2_harness:run_all",),
            verified_by=(
                "test_no_variant_is_run_twice_for_its_result",
                "test_a_rerun_reproduces_both_digests",
            ),
            note=(
                "The only second execution is the determinism check, whose digests are compared and "
                "whose numbers are discarded."
            ),
        ),
        Trace(
            document="SE100-CFG-3004",
            path=("drawdown_ceiling_is_unchanged",),
            implementation=("stockedge100.strategies.gate:check_thresholds_against_seal",),
            verified_by=("test_the_fifteen_percent_ceiling_is_unchanged",),
            note="The gate refuses to evaluate if any threshold has drifted from the seal.",
        ),
        Trace(
            document="SE100-CFG-3004",
            path=("neighbour_status",),
            implementation=("stockedge100.strategies.gate:condition_7",),
            verified_by=("test_no_neighbour_is_ever_promoted",),
            note="Only the sign of a neighbour's net return carries gate weight.",
        ),
        # ---- the seven conditions ------------------------------------------------------------------
        *[
            Trace(
                document="SE100-CFG-3002",
                path=("conditions", f"S3-C{index}"),
                implementation=(f"stockedge100.strategies.gate:condition_{index}",),
                verified_by=(f"test_s3_c{index}_matches_the_sealed_predicate",),
                note="Adopted by digest from Attempt 1's Gate 3; the implementation is unchanged.",
            )
            for index in range(1, 8)
        ],
        Trace(
            document="SE100-CFG-3002",
            path=("verdict_token_derivation",),
            implementation=("stockedge100.strategies.gate:stage_verdict",),
            verified_by=("test_tokens_are_read_from_the_sealed_derivation",),
            note="The tokens are derived from this field at build time, never written as literals.",
        ),
        Trace(
            document="SE100-CFG-3002",
            path=("reported_but_not_gating",),
            implementation=("stockedge100.strategies.attempt2_runner:measure_variant",),
            verified_by=("test_secondary_metrics_are_reported_and_never_gating",),
            note="Extended only with RA1 diagnostics; extending disclosure adds no condition.",
        ),
    ]
    + _candidate_traces()
)


#: Sealed paths that must each be claimed by at least one row. A row may be more specific than an
#: entry here — ``("risk_architecture", "RA1-1", "rule")`` covers ``("risk_architecture", "RA1-1")``.
REQUIRED_COVERAGE: tuple[tuple[str, tuple[str, ...]], ...] = tuple(
    [("SE100-CFG-3003", ("shared_rules", "adopted_text_restated_for_readability", name)) for name in (
        "one_decision_per_session",
        "long_only",
        "flat_first_rule",
        "insufficient_history_rule",
        "tie_break",
        "warmup_rule",
        "run_start_rule",
        "warmup_data_source",
        "no_intraday",
        "no_machine_learning",
        "no_combination",
    )]
    + [
        ("SE100-CFG-3003", ("shared_rules", "replaced", "sizing_rule")),
        ("SE100-CFG-3003", ("indicator_definitions", "added", "VOL20")),
        ("SE100-CFG-3003", ("indicator_definitions", "not_used_by_attempt_2")),
        ("SE100-CFG-3003", ("partitions",)),
        ("SE100-CFG-3003", ("excluded_symbols",)),
        ("SE100-CFG-3003", ("iteration_budget",)),
        ("SE100-CFG-3003", ("cost_stress_treatment",)),
        ("SE100-CFG-3003", ("no_retuning_rule",)),
        ("SE100-CFG-3003", ("benchmarks",)),
        ("SE100-CFG-3003", ("primary_decision_rule",)),
        ("SE100-CFG-3003", ("permitted_parameter_grid_semantics",)),
        ("SE100-CFG-3004", ("admissible_candidate_exists", "frozen_rule")),
        ("SE100-CFG-3004", ("admissible_candidate_exists", "satisfied_definition")),
        ("SE100-CFG-3004", ("admissible_candidate_exists", "per_condition_rollup_is_not_the_gate")),
        ("SE100-CFG-3004", ("admissible_candidate_exists", "incoherent_combinations_refused")),
        ("SE100-CFG-3004", ("shutdown_behaviour",)),
        ("SE100-CFG-3004", ("rerun_policy",)),
        ("SE100-CFG-3004", ("drawdown_ceiling_is_unchanged",)),
        ("SE100-CFG-3004", ("neighbour_status",)),
        ("SE100-CFG-3002", ("verdict_token_derivation",)),
    ]
    + [("SE100-CFG-3003", ("risk_architecture", rung, "rule")) for rung in (
        "RA1-1", "RA1-2", "RA1-3", "RA1-4", "RA1-5", "RA1-6", "RA1-7", "RA1-8",
    )]
    + [
        ("SE100-CFG-3003", ("risk_architecture", "exit_precedence")),
        ("SE100-CFG-3003", ("risk_architecture", "engine_shutdown_relationship")),
        ("SE100-CFG-3003", ("risk_architecture", "prohibition_on_mechanical_targeting")),
    ]
    + [("SE100-CFG-3003", ("missing_or_invalid_data_rule", field)) for field in (
        "missing_indicator",
        "missing_bar_for_a_target",
        "stale_or_delisted",
        "non_positive_adjusted_close",
        "data_repair_prohibited",
    )]
    + [("SE100-CFG-3003", ("partial_or_failed_run_rule", field)) for field in (
        "neighbour_fails_to_run",
        "primary_fails_to_run",
        "partial_completion",
    )]
    + [("SE100-CFG-3003", ("reproducibility_requirements", field)) for field in (
        "determinism",
        "arithmetic",
        "ordering",
        "random_seeds",
    )]
    + [("SE100-CFG-3002", ("conditions", f"S3-C{index}")) for index in range(1, 8)]
    + [
        ("SE100-CFG-3003", ("experiments", candidate, field))
        for candidate in CANDIDATE_IDS
        for field in (
            "experiment_id",
            "universe",
            "eligibility_rules",
            "warmup_sessions",
            "signal_timing",
            "primary_parameters",
            "signal_target_rule",
            "entry_rule",
            "exit_rule",
            "maximum_holding_period",
            "position_sizing_rule",
            "maximum_exposure",
            "cash_allocation_rule",
            "stop_or_shutdown_rule",
            "reentry_rule_after_a_stop",
            "conflict_rule",
            "robustness_neighbours",
            "max_variants",
            "gate_3_conditions_applied",
        )
    ]
)


def missing_coverage() -> list[str]:
    """Required sealed paths that no row claims. Empty is the only acceptable value."""

    claimed = {(trace.document, trace.path) for trace in TRACES}
    missing: list[str] = []
    for document, path in REQUIRED_COVERAGE:
        if any(
            candidate_document == document and candidate_path[: len(path)] == path
            for candidate_document, candidate_path in claimed
        ):
            continue
        missing.append(f"{document}:{'.'.join(path)}")
    return sorted(missing)


def duplicate_rows() -> list[str]:
    """Rows that trace the same sealed path twice. A duplicate is a merge accident, not coverage."""

    seen: dict[tuple[str, tuple[str, ...]], int] = {}
    for trace in TRACES:
        seen[(trace.document, trace.path)] = seen.get((trace.document, trace.path), 0) + 1
    return sorted(
        f"{document}:{'.'.join(path)}" for (document, path), count in seen.items() if count > 1
    )


def verify(config: Attempt2Config) -> dict[str, Any]:
    """Resolve both ends of every row. Raises on the first row that does not resolve."""

    for trace in TRACES:
        sealed_value(config, trace)
        for reference in trace.implementation:
            resolve_code(reference)

    missing = missing_coverage()
    if missing:
        raise ConfigViolation(
            f"{len(missing)} sealed rule paths are not traced to an implementation: {missing}"
        )
    duplicates = duplicate_rows()
    if duplicates:
        raise ConfigViolation(f"sealed rule paths traced more than once: {duplicates}")

    return {
        "rows": len(TRACES),
        "sealed_paths_required": len(REQUIRED_COVERAGE),
        "missing_coverage": missing,
        "duplicate_rows": duplicates,
        "documents": {
            name: sum(1 for trace in TRACES if trace.document == name) for name in DOCUMENTS
        },
        "implementation_references": len(
            {reference for trace in TRACES for reference in trace.implementation}
        ),
        "tests_named": len({name for trace in TRACES for name in trace.verified_by}),
        "all_rows_resolve": True,
    }


def resolved_rows(config: Attempt2Config) -> list[dict[str, Any]]:
    """Every row with the sealed text read from the seal — the map as it appears in the evidence.

    The sealed text is read here rather than stored above so that the evidence file carries the
    specification's own words and nothing in ``src/`` holds a copy able to drift from them.
    """

    rows: list[dict[str, Any]] = []
    for trace in TRACES:
        value = sealed_value(config, trace)
        rows.append({**trace.to_json(), "sealed_value": value})
    return rows


def all_named_tests() -> list[str]:
    """Every test name any row cites, sorted. The test module asserts each one exists in itself."""

    return sorted({name for trace in TRACES for name in trace.verified_by})
