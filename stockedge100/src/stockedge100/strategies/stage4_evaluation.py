"""The Stage 4 validation harness: load the seal, prove C2 unchanged, run the two declared runs.

Everything here is machinery. Not one number that the gate reads is computed in this module: the
metrics come from :func:`stockedge100.strategies.runner.measure` by way of
:func:`stockedge100.strategies.attempt2_runner.measure_variant`, which is the same code path Gate 3
used and which Gate 2 validated. A second definition of ``total_return``, ``max_drawdown``,
``sharpe`` or ``profit_factor`` on disk would be a second specification of a gate input, and the
sealed ``measurement_adopted_by_digest`` block adopts SE100-CFG-2001 unchanged precisely so that no
such second definition exists.

Three constructions carry the whole stage and each is fixed by on-disk text rather than by choice.

**The engine's window is a visibility bound, not a run bound.** ``MarketView.history`` filters
visible bars on ``self._window.contains(day)``, so a window that began on 2021-08-01 would delete
the 101 warm-up sessions the sealed ``runs_declared`` entry requires — the RSI seeding distance
would collapse to one bar on the first validation session. The window handed to the engine
therefore spans ``[warmup_start, 2024-07-31]`` while the *run* spans ``[2021-08-01, 2024-07-31]``,
passed as the engine's ``start`` and ``end``. This is the same construction
:mod:`stockedge100.strategies.attempt2_runner` records for Gate 3 and it is applied here for the
same reason.

**The holdout is unreachable by construction, not by care.** ``MarketView`` shows a probe only bars
with ``day <= as_of`` that the window contains; ``as_of`` is drawn from
``sessions_between(run_start, run_end)`` and ``run_end`` is the frozen validation end. So every bar
any probe can see satisfies ``day <= 2024-07-31 < 2024-08-01``, and the holdout is outside the
object graph the engine can address. :func:`assert_holdout_unreachable` states that as an
executable check rather than a sentence.

**Warm-up reads development, which is already authorized and already read.** The sealed
``partitions.development.use_in_the_evaluation_session`` permits exactly the 101-session tail
immediately preceding the validation start, for indicator computation only. So the composite window
starts at that tail rather than at the development window start: a wider bound would be a wider
read than the seal authorizes, even though nothing would use the extra bars.

Nothing in this module writes a file, and nothing in it decides anything. The gate lives in
:mod:`stockedge100.strategies.stage4_gate`, which imports no data layer at all.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Sequence

from stockedge100.audit import sha256_file
from stockedge100.backtest.config import Stage2Config, load_stage2_config
from stockedge100.backtest.costs import BASE, STRESSED, CostModel
from stockedge100.backtest.dataset import NORMALIZED_DIR, PriceSeries, load_dataset
from stockedge100.backtest.errors import ConfigViolation, WindowViolation
from stockedge100.backtest.window import (
    HOLDOUT,
    VALIDATION,
    ResearchWindow,
    development_window,
    window_named,
)
from stockedge100.data.calendar import sessions_between
from stockedge100.strategies.attempt2_candidates import C2, traded_symbols
from stockedge100.strategies.attempt2_config import Attempt2Config, load_attempt2_config
from stockedge100.strategies.attempt2_runner import (
    VariantRun,
    largest_lookback,
    measure_variant,
    run_variant,
)
from stockedge100.strategies.runner import PRIMARY, CandidatePlan, VariantSpec, trade_pnls

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RUNS_DIR = PROJECT_ROOT / "runs"

REPRESENTATIVE = C2

PROTOCOL_REL = "config/stage4_validation_protocol.json"
CRITERIA_REL = "config/stage4_gate_criteria.json"
SELECTION_REL = "config/stage4_representative_selection.json"
PREREG_MD_REL = "governance/STAGE_4_PREREGISTRATION.md"
PREREG_JSON_REL = "governance/STAGE_4_PREREGISTRATION.json"
PREREG_RECORD_REL = "governance/STAGE_4_PREREGISTRATION.sha256"

#: The three artifacts this stage authored, and the id each must carry. Checked so that a file
#: swapped for another file of the same name fails on identity as well as on digest.
ARTIFACT_IDS = {
    PROTOCOL_REL: "SE100-CFG-4001",
    CRITERIA_REL: "SE100-CFG-4002",
    SELECTION_REL: "SE100-CFG-4003",
}

#: The thirteenth entry of the sealed recheck list. It names a module by description rather than by
#: path; :func:`resolve_strategy_module` turns it into a path using the seal's own digest table, so
#: the resolution is read from disk rather than guessed here.
#:
#: The identifier is interpolated from :data:`REPRESENTATIVE` rather than written out, for two
#: reasons. The identifier has exactly one definition in this tree — ``attempt2_candidates.C2`` — and
#: a second copy here would be a copy that can drift. More sharply, the Stage 4 sealing program
#: resolves *the strategy module implementing the representative* by searching strategy modules for
#: that identifier and requires exactly one match; a module that merely mentions it in a description
#: would become a second match and make the seal's own resolution ambiguous. Referring to the
#: constant keeps this evaluator out of that answer, which is correct: it evaluates the strategy, it
#: does not implement it.
STRATEGY_MODULE_DESCRIPTION = f"the strategy module implementing {REPRESENTATIVE}"

_SHA256 = re.compile(r"\b[0-9a-f]{64}\b")


# -- sealed configuration --------------------------------------------------------------------


@dataclass(frozen=True)
class Stage4Config:
    """The sealed Stage 4 specification, loaded only after every sealed digest recomputes.

    There is deliberately no keyword that makes the seal optional. Gate 4 evidence produced from
    a specification nobody committed to in advance is not evidence, and a bypass here would be the
    mechanism for producing exactly that.
    """

    protocol: dict[str, Any]
    criteria: dict[str, Any]
    selection: dict[str, Any]
    preregistration: dict[str, Any]
    attempt2: Attempt2Config
    stage2: Stage2Config
    digests: dict[str, str]
    strategy_module_rel: str

    # -- accessors, each raising rather than defaulting -----------------------------------------

    @property
    def sealed_representative(self) -> dict[str, Any]:
        return _require(self.protocol, "sealed_representative", PROTOCOL_REL)

    @property
    def parameters(self) -> dict[str, Any]:
        return dict(_require(self.sealed_representative, "parameters", PROTOCOL_REL))

    @property
    def declared_universe(self) -> tuple[str, ...]:
        return tuple(_require(self.sealed_representative, "declared_universe", PROTOCOL_REL))

    @property
    def warmup_sessions(self) -> int:
        return int(_require(self.sealed_representative, "declared_warmup_sessions", PROTOCOL_REL))

    @property
    def runs_declared(self) -> list[dict[str, Any]]:
        block = _require(self.protocol, "runs_declared", PROTOCOL_REL)
        return list(_require(block, "runs", PROTOCOL_REL))

    @property
    def declared_run_count(self) -> int:
        return int(_require(_require(self.protocol, "runs_declared", PROTOCOL_REL), "count", PROTOCOL_REL))

    @property
    def run_labels(self) -> tuple[str, ...]:
        return tuple(str(run["run_label"]) for run in self.runs_declared)

    @property
    def conditions(self) -> list[dict[str, Any]]:
        return list(_require(self.criteria, "conditions", CRITERIA_REL))

    @property
    def verdict_tokens(self) -> dict[str, Any]:
        return _require(self.criteria, "verdict_token_derivation", CRITERIA_REL)

    @property
    def fold_construction(self) -> dict[str, Any]:
        return _require(self.criteria, "walk_forward_fold_construction", CRITERIA_REL)

    @property
    def iteration_budget(self) -> dict[str, Any]:
        return _require(self.protocol, "iteration_budget", PROTOCOL_REL)

    @property
    def sealed_recheck_list(self) -> list[str]:
        block = _require(self.protocol, "reproducibility_requirements", PROTOCOL_REL)
        return list(_require(block, "sealed_digests_to_recheck", PROTOCOL_REL))

    @property
    def sealed_digest_entries(self) -> dict[str, str]:
        block = _require(self.preregistration, "sealed_digests_for_s4_c7", PREREG_JSON_REL)
        return dict(_require(block, "entries", PREREG_JSON_REL))

    @property
    def cost_model_raw(self) -> dict[str, Any]:
        return self.stage2.cost_model

    @property
    def stress_multiplier(self) -> Decimal:
        return Decimal(str(self.cost_model_raw["frictions"]["stress_multiplier"]))


def _require(block: dict[str, Any], key: str, where: str) -> Any:
    if key not in block:
        raise ConfigViolation(
            f"{where}: sealed key {key!r} is absent. This is a governance failure, not a bug to "
            "work around. Stop and report it."
        )
    return block[key]


def _read_json(rel: str) -> dict[str, Any]:
    path = PROJECT_ROOT / rel
    if not path.is_file():
        raise ConfigViolation(f"{rel}: sealed input is missing")
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_strategy_module(seal: dict[str, Any], protocol: dict[str, Any]) -> str:
    """Turn the recheck list's thirteenth *description* into the path the seal bound it to.

    The description is resolved by difference rather than by a literal written here: the seal's
    digest table names twelve paths, the protocol's list names twelve paths plus one description,
    and the single path present in one and absent from the other is the module. Two guards make the
    resolution fail closed — exactly one leftover on each side, and the resolved file must actually
    name the sealed representative. A hard-coded path would agree with the seal by luck.
    """

    entries = dict(seal["sealed_digests_for_s4_c7"]["entries"])
    excluded = str(seal["sealed_digests_for_s4_c7"]["own_digest_excluded"])
    declared = list(protocol["reproducibility_requirements"]["sealed_digests_to_recheck"])

    sealed_paths = set(entries) | {excluded}
    declared_paths = {item for item in declared if "/" in item and " " not in item}
    descriptions = [item for item in declared if item not in declared_paths]

    only_in_seal = sorted(sealed_paths - declared_paths)
    if len(only_in_seal) != 1 or len(descriptions) != 1:
        raise ConfigViolation(
            f"the sealed recheck set does not resolve to one strategy module: "
            f"{len(only_in_seal)} unmatched sealed path(s) {only_in_seal} against "
            f"{len(descriptions)} description(s) {descriptions}. S4-C7 is measured from this set, "
            "so an ambiguous set is a blocker, not something to disambiguate here."
        )
    if descriptions[0] != STRATEGY_MODULE_DESCRIPTION:
        raise ConfigViolation(
            f"the sealed recheck description changed: expected {STRATEGY_MODULE_DESCRIPTION!r}, "
            f"found {descriptions[0]!r}"
        )
    resolved = only_in_seal[0]
    text = (PROJECT_ROOT / resolved).read_text(encoding="utf-8") if (PROJECT_ROOT / resolved).is_file() else ""
    if REPRESENTATIVE not in text:
        raise ConfigViolation(
            f"{resolved} was resolved as the module implementing {REPRESENTATIVE} but its text does "
            "not name it. The resolution is content-checked deliberately: a path that merely looks "
            "right is not evidence."
        )
    if len(sealed_paths - declared_paths) != 1 or declared_paths - sealed_paths:
        raise ConfigViolation(
            f"the two sealed recheck lists disagree: {sorted(declared_paths - sealed_paths)} is "
            "declared in the protocol but carries no sealed digest. SE100-CFG-4002 S4-C7 requires "
            "the two to agree exactly."
        )
    return resolved


def _verify(rel: str, expected: str, digests: dict[str, str], drift: list[str]) -> None:
    path = PROJECT_ROOT / rel
    if not path.is_file():
        drift.append(f"{rel}: MISSING")
        return
    computed = sha256_file(path)
    previous = digests.get(rel)
    if previous is not None and previous != computed:
        drift.append(f"{rel}: digest changed during load, {previous} then {computed}")
    digests[rel] = computed
    if computed != expected:
        drift.append(f"{rel}: sealed {expected} but found {computed}")


def preregistration_own_digest() -> str:
    """The thirteenth sealed digest, taken from the record that carries it.

    ``governance/STAGE_4_PREREGISTRATION.json`` cannot hash itself, so its digest lives in
    ``governance/STAGE_4_PREREGISTRATION.sha256``. Parsing it here rather than recomputing and
    trusting keeps the comparison against a value written before any validation observation existed.
    """

    record = PROJECT_ROOT / PREREG_RECORD_REL
    if not record.is_file():
        raise ConfigViolation(f"{PREREG_RECORD_REL}: the checksum record carrying the "
                              "pre-registration's own digest is missing")
    for line in record.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, _, name = line.partition(" ")
        if name.strip().lstrip("*") == PREREG_JSON_REL and _SHA256.fullmatch(digest.strip()):
            return digest.strip()
    raise ConfigViolation(
        f"{PREREG_RECORD_REL} carries no entry for {PREREG_JSON_REL}; the pre-registration's own "
        "digest has no source and S4-C7 cannot be measured"
    )


def load_stage4_config() -> Stage4Config:
    """Load the seal, or refuse. Every one of the thirteen sealed digests must recompute first."""

    protocol = _read_json(PROTOCOL_REL)
    criteria = _read_json(CRITERIA_REL)
    selection = _read_json(SELECTION_REL)
    seal = _read_json(PREREG_JSON_REL)

    strategy_module_rel = resolve_strategy_module(seal, protocol)

    digests: dict[str, str] = {}
    drift: list[str] = []
    for rel, expected in sorted(seal["sealed_digests_for_s4_c7"]["entries"].items()):
        _verify(rel, expected, digests, drift)
    _verify(PREREG_JSON_REL, preregistration_own_digest(), digests, drift)

    if len(digests) != int(seal["sealed_digests_for_s4_c7"]["declared_set_size"]):
        drift.append(
            f"recomputed {len(digests)} digests against a declared set size of "
            f"{seal['sealed_digests_for_s4_c7']['declared_set_size']}"
        )
    for rel, artifact_id in ARTIFACT_IDS.items():
        found = _read_json(rel).get("artifact_id")
        if found != artifact_id:
            drift.append(f"{rel}: artifact_id is {found!r}, sealed as {artifact_id!r}")

    # The authorization state the seal itself records. A seal that did not authorize this session,
    # or that already recorded a Gate 4 result, is a blocker before anything is loaded.
    for key, expected in (
        ("declared_before_any_validation_observation_was_read", True),
        ("gate_3_passed", True),
        ("gate_4_evaluated", False),
        ("gate_4_passed", False),
        ("validation_evaluation_authorized", True),
        ("holdout_access_authorized", False),
        ("stage_5_authorized", False),
        ("paper_trading_authorized", False),
        ("shadow_live_authorized", False),
        ("capital_or_risk_expansion_authorized", False),
        ("live_trading_authorized", False),
    ):
        if seal.get(key) is not expected:
            drift.append(f"{PREREG_JSON_REL}: {key} is {seal.get(key)!r}, required {expected!r}")

    if drift:
        raise ConfigViolation(
            "the Stage 4 seal does not verify:\n  " + "\n  ".join(drift) + "\n"
            "This is a governance failure, not a bug to work around. Stop and report it."
        )

    return Stage4Config(
        protocol=protocol,
        criteria=criteria,
        selection=selection,
        preregistration=seal,
        attempt2=load_attempt2_config(),
        stage2=load_stage2_config(),
        digests=digests,
        strategy_module_rel=strategy_module_rel,
    )


def recheck_table(config: Stage4Config) -> list[dict[str, Any]]:
    """The thirteen-row S4-C7 recheck, recomputed from the files as they stand right now.

    Called twice in a session: once before the validation window is opened and once after the runs
    complete. The second call is the one S4-C7 reads. Both are recorded, because "the digests were
    equal before the run" and "the digests were equal after it" are different claims.
    """

    rows: list[dict[str, Any]] = []
    sealed = dict(config.sealed_digest_entries)
    sealed[PREREG_JSON_REL] = preregistration_own_digest()
    for rel in sorted(sealed):
        path = PROJECT_ROOT / rel
        recomputed = sha256_file(path) if path.is_file() else None
        rows.append(
            {
                "artifact": rel,
                "sealed": sealed[rel],
                "recomputed": recomputed,
                "equal": recomputed == sealed[rel],
                "digest_source": (
                    PREREG_RECORD_REL if rel == PREREG_JSON_REL
                    else f"{PREREG_JSON_REL} sealed_digests_for_s4_c7.entries"
                ),
                "resolves_description": (
                    STRATEGY_MODULE_DESCRIPTION if rel == config.strategy_module_rel else None
                ),
            }
        )
    return rows


# -- strategy invariance ---------------------------------------------------------------------


def strategy_invariance(config: Stage4Config) -> dict[str, Any]:
    """Prove C2 is the Gate 3 candidate, not merely that it is called by the same name.

    Four comparisons, all against the Gate 3 Attempt 2 protocol as the digest-verified
    :class:`~stockedge100.strategies.attempt2_config.Attempt2Config` loads it: the parameterisation,
    the declared universe, the declared warm-up and the family. The parameterisation comparison is
    the one with teeth — it is a canonical-JSON equality over the whole mapping, so a changed
    ladder rung or a widened tolerance is an inequality rather than a judgement call.

    The warm-up is additionally re-derived from the sealed lookbacks rather than only compared, so
    that a warm-up which agreed with the seal while disagreeing with the indicators would fail.
    """

    experiment = config.attempt2.experiment(REPRESENTATIVE)
    sealed_params = config.parameters
    gate3_params = dict(experiment["primary_parameters"])
    spec = _stage4_variant_spec(config)
    effective = largest_lookback((spec,), config.attempt2.rsi_warmup_changes)

    findings = {
        "representative": REPRESENTATIVE,
        "identifier_unchanged_from_gate_3": bool(
            config.sealed_representative["identifier_unchanged_from_gate_3"]
        ),
        "parameters_equal_gate_3_primary": (
            json.dumps(sealed_params, sort_keys=True) == json.dumps(gate3_params, sort_keys=True)
        ),
        "sealed_parameters": json.dumps(sealed_params, sort_keys=True),
        "gate_3_primary_parameters": json.dumps(gate3_params, sort_keys=True),
        "universe_equal_gate_3": list(config.declared_universe) == list(experiment["universe"]),
        "declared_universe": list(config.declared_universe),
        "family_equal_gate_3": config.sealed_representative["family"] == experiment.get("family"),
        "warmup_equal_gate_3": config.warmup_sessions == int(experiment["warmup_sessions"]),
        "declared_warmup_sessions": config.warmup_sessions,
        "largest_lookback_recomputed": effective,
        "warmup_matches_largest_lookback": effective == config.warmup_sessions,
        "rsi_warmup_changes": config.attempt2.rsi_warmup_changes,
        "strategy_module": config.strategy_module_rel,
        "strategy_module_digest_equal": next(
            row["equal"] for row in recheck_table(config)
            if row["artifact"] == config.strategy_module_rel
        ),
    }
    findings["all_equal"] = all(
        findings[key] for key in (
            "identifier_unchanged_from_gate_3",
            "parameters_equal_gate_3_primary",
            "universe_equal_gate_3",
            "family_equal_gate_3",
            "warmup_equal_gate_3",
            "warmup_matches_largest_lookback",
            "strategy_module_digest_equal",
        )
    )
    return findings


# -- windows ---------------------------------------------------------------------------------


def validation_window() -> ResearchWindow:
    """The frozen validation partition, from ``governance/STAGE_1_HOLDOUT_LOCK.json``."""
    return window_named(VALIDATION)


def holdout_window() -> ResearchWindow:
    return window_named(HOLDOUT)


def warmup_start(series: dict[str, PriceSeries], config: Stage4Config) -> dt.date:
    """The first of the sealed 101 development sessions immediately preceding the validation start.

    ``inside[-warmup]`` rather than a date arithmetic: "sessions" means exchange sessions on the
    frozen XNYS calendar, and counting calendar days back from 2021-08-01 would land on a different
    bar. The universe is the sealed one, so a candidate whose symbols had different histories would
    take the latest qualifying start; with a single-symbol universe that reduces to SPY, and the
    loop is written for the general case anyway because the sealed universe is data, not a constant.
    """

    development = development_window()
    warmup = config.warmup_sessions
    latest: dt.date | None = None
    for symbol in sorted(set(config.declared_universe)):
        history = series.get(symbol)
        if history is None:
            raise ConfigViolation(f"warm-up needs {symbol} but its series was not loaded")
        inside = [day for day in history.sessions if development.contains(day)]
        if len(inside) < warmup:
            raise ConfigViolation(
                f"{symbol} has only {len(inside)} sessions inside the development window; the "
                f"sealed warm-up requires {warmup}"
            )
        qualifies = inside[-warmup]
        if latest is None or qualifies > latest:
            latest = qualifies
    assert latest is not None
    return latest


def evaluation_window(series: dict[str, PriceSeries], config: Stage4Config) -> ResearchWindow:
    """``[warmup_start, validation_end]`` — the visibility bound, not the run bound.

    Named for what it is so that any artifact quoting the window name says so too. Its end is the
    frozen validation end, which is what makes the holdout structurally unreachable.
    """

    validation = validation_window()
    start = warmup_start(series, config)
    window = ResearchWindow(
        name=f"{VALIDATION}+warmup{config.warmup_sessions}",
        start=start,
        end=validation.end,
    )
    assert_window_is_authorized(window, config, series)
    return window


def assert_window_is_authorized(
    window: ResearchWindow, config: Stage4Config, series: dict[str, PriceSeries]
) -> None:
    """Every property the seal requires of the composite window, as a check rather than a claim."""

    development = development_window()
    validation = validation_window()
    holdout = holdout_window()
    problems: list[str] = []

    if not development.contains(window.start):
        problems.append(
            f"warm-up start {window.start} is not inside the development window "
            f"{development.start}..{development.end}"
        )
    if window.end != validation.end:
        problems.append(f"window end {window.end} is not the frozen validation end {validation.end}")
    if window.end >= holdout.start:
        problems.append(f"window end {window.end} reaches the sealed holdout start {holdout.start}")
    if window.start >= validation.start:
        problems.append(f"warm-up start {window.start} does not precede {validation.start}")

    for symbol in sorted(set(config.declared_universe)):
        history = series.get(symbol)
        if history is None:
            problems.append(f"{symbol}: series not loaded")
            continue
        count = len([d for d in history.sessions if window.start <= d < validation.start])
        if count != config.warmup_sessions:
            problems.append(
                f"{symbol}: {count} sessions in the warm-up segment against the sealed "
                f"{config.warmup_sessions}"
            )
    if problems:
        raise WindowViolation(
            "the Stage 4 evaluation window is not the authorized one:\n  " + "\n  ".join(problems)
        )


def assert_holdout_unreachable(window: ResearchWindow, run_end: dt.date) -> dict[str, Any]:
    """The structural holdout proof, executed.

    ``MarketView`` shows a probe only bars with ``day <= as_of`` that ``window.contains``. ``as_of``
    never exceeds ``run_end``. So if ``run_end`` and ``window.end`` both precede the holdout start,
    no holdout bar is addressable — regardless of what any probe asks for.
    """

    holdout = holdout_window()
    facts = {
        "holdout_start": holdout.start.isoformat(),
        "holdout_end": holdout.end.isoformat(),
        "window_end": window.end.isoformat(),
        "run_end": run_end.isoformat(),
        "window_end_precedes_holdout_start": window.end < holdout.start,
        "run_end_precedes_holdout_start": run_end < holdout.start,
        "mechanism": (
            "MarketView.history returns bars filtered by window.contains(day) and day <= as_of; "
            "as_of is drawn from sessions_between(run_start, run_end). With both bounds before "
            "the holdout start no holdout bar is addressable by any probe."
        ),
    }
    if not (facts["window_end_precedes_holdout_start"] and facts["run_end_precedes_holdout_start"]):
        raise WindowViolation(
            f"the holdout is not structurally unreachable: window ends {window.end}, run ends "
            f"{run_end}, holdout begins {holdout.start}. The holdout is SEALED through Gate 4."
        )
    return facts


# -- the two declared runs -------------------------------------------------------------------


def _stage4_variant_spec(config: Stage4Config) -> VariantSpec:
    """The single parameterisation, as one :class:`VariantSpec`.

    ``experiment_id`` stays the Gate 3 identifier because
    ``sealed_representative.identifier_unchanged_from_gate_3`` is true and because
    :func:`~stockedge100.strategies.attempt2_candidates.build_candidate` dispatches on it. The
    ``variant_id`` carries the Stage 4 run label stem instead, so the two declared run labels come
    out of ``variant_id + label_suffix`` rather than being typed twice.
    """

    parameters = config.parameters
    universe = config.declared_universe
    return VariantSpec(
        experiment_id=REPRESENTATIVE,
        variant_id=run_label_stem(config),
        role=PRIMARY,
        index=0,
        universe=universe,
        parameters=parameters,
        symbols=traded_symbols(REPRESENTATIVE, universe, parameters),
    )


def run_label_stem(config: Stage4Config) -> str:
    """The common prefix of the two sealed run labels, derived from them rather than restated.

    Both declared labels are the stem plus a suffix. Computing the stem by common prefix means a
    protocol whose labels did not share one fails here instead of producing a run whose label
    silently differs from the sealed string.
    """

    labels = config.run_labels
    if len(labels) != 2:
        raise ConfigViolation(f"the protocol declares {len(labels)} run labels; Gate 4 declares 2")
    first, second = labels
    stem = ""
    for a, b in zip(first, second):
        if a != b:
            break
        stem += a
    stem = stem.rstrip("#")
    if not stem or not all(label.startswith(stem + "#") for label in labels):
        raise ConfigViolation(
            f"the declared run labels {labels} share no '#'-separated stem; the run label must come "
            "from the seal, so this is a blocker rather than something to paper over"
        )
    return stem


def label_suffix_for(config: Stage4Config, run_label: str) -> str:
    """The ``#BASE`` / ``#STRESS`` tail of a *declared* run label.

    Membership is checked rather than assumed. Slicing the stem off an arbitrary string returns a
    plausible-looking suffix for a label that was never registered, which is the wrong direction for
    a stage whose iteration budget permits exactly two runs: an unregistered label should be a
    blocker at the point it is named, not a silently accepted third scenario.
    """

    if run_label not in config.run_labels:
        raise ConfigViolation(
            f"{run_label!r} is not one of the two runs declared by {config.protocol['artifact_id']}: "
            f"{list(config.run_labels)}"
        )
    return run_label[len(run_label_stem(config)):]


def costs_for(config: Stage4Config, declared: dict[str, Any]) -> CostModel:
    """BASE or STRESSED, chosen from the declared run's own friction text.

    The scenario is not inferred from the label. ``SE100-CFG-2001`` defines exactly two friction
    scenarios and the declared ``friction`` sentence says which one this run carries; a run whose
    text matched neither, or both, is a blocker.
    """

    text = str(declared["friction"]).lower()
    stressed = "multiplied by" in text and "stress_multiplier" in text
    base = "unmodified" in text
    if stressed == base:
        raise ConfigViolation(
            f"declared run {declared['run_label']!r} does not identify a friction scenario from "
            f"its sealed text: {declared['friction']!r}"
        )
    return CostModel(config.cost_model_raw, STRESSED if stressed else BASE)


@dataclass(frozen=True)
class RegisteredRun:
    """One of the two runs the seal declares, and nothing else may exist."""

    run_label: str
    scenario: str
    gates_conditions: tuple[str, ...]
    declared: dict[str, Any]
    run: VariantRun
    measure: dict[str, Any]

    @property
    def result(self):  # noqa: ANN201 - BacktestResult, kept untyped to avoid a redundant import
        return self.run.result


def stage4_plan(config: Stage4Config, window: ResearchWindow) -> CandidatePlan:
    """The run bounds: start at the frozen validation start, end at the frozen validation end.

    Deliberately *not* :func:`~stockedge100.strategies.runner.run_start_for`. That function returns
    the session at which the warm-up requirement is first met inside the window it is given, which
    for the composite window would be the last warm-up session — and the run would then open on a
    development session, contradicting ``partitions.development.use_in_the_evaluation_session``,
    which authorizes the tail for indicator computation only. The sealed ``runs_declared`` window is
    "validation, 2021-08-01 to 2024-07-31" and that is what the run is given.
    """

    validation = validation_window()
    spec = _stage4_variant_spec(config)
    effective = largest_lookback((spec,), config.attempt2.rsi_warmup_changes)
    if effective != config.warmup_sessions:
        raise ConfigViolation(
            f"sealed warmup_sessions={config.warmup_sessions} but the largest lookback the sealed "
            f"parameterisation consumes is {effective} visible bars. The seal is the specification; "
            "report the discrepancy rather than adjusting either."
        )
    if not window.contains(validation.start) or not window.contains(validation.end):
        raise WindowViolation(
            f"the evaluation window {window.start}..{window.end} does not contain the frozen "
            f"validation window {validation.start}..{validation.end}"
        )
    return CandidatePlan(
        experiment_id=REPRESENTATIVE,
        family=str(config.sealed_representative["family"]),
        declared_universe=config.declared_universe,
        warmup_sessions=config.warmup_sessions,
        effective_warmup=effective,
        run_start=validation.start,
        run_end=validation.end,
        binding_symbol=sorted(set(config.declared_universe))[0],
        variants=(spec,),
        all_symbols=tuple(sorted(spec.symbols)),
    )


def execute_registered_runs(
    config: Stage4Config,
    series: dict[str, PriceSeries],
    window: ResearchWindow,
    plan: CandidatePlan,
) -> list[RegisteredRun]:
    """Exactly the declared runs, in declared order, against one already-loaded dataset.

    ``runs_declared.count_is_a_hard_limit`` is true, so the count is asserted rather than trusted;
    ``run_variant`` builds a fresh candidate per run because ``Ra1Candidate`` carries per-run
    mutable state, and it enforces the section 5.1 shutdown on both, which the seal requires for
    every gating run.
    """

    declared = config.runs_declared
    if len(declared) != config.declared_run_count:
        raise ConfigViolation(
            f"the protocol declares count={config.declared_run_count} but lists {len(declared)} runs"
        )
    budget = int(config.iteration_budget["runs"])
    if budget != len(declared):
        raise ConfigViolation(
            f"iteration_budget.runs={budget} disagrees with runs_declared.count={len(declared)}"
        )

    spec = plan.variants[0]
    executed: list[RegisteredRun] = []
    for entry in declared:
        label = str(entry["run_label"])
        if str(entry["candidate"]) != REPRESENTATIVE:
            raise ConfigViolation(
                f"declared run {label!r} names candidate {entry['candidate']!r}; Gate 4 evaluates "
                f"only {REPRESENTATIVE}"
            )
        costs = costs_for(config, entry)
        run = run_variant(
            spec,
            plan,
            series,
            costs,
            window,
            config.attempt2.rsi_warmup_changes,
            gating=bool(entry.get("gating", True)),
            label_suffix=label_suffix_for(config, label),
        )
        if run.label != label:
            raise ConfigViolation(
                f"executed run label {run.label!r} is not the sealed {label!r}; a run whose label "
                "differs from the declared one is an unregistered run"
            )
        executed.append(
            RegisteredRun(
                run_label=label,
                scenario=run.scenario,
                gates_conditions=tuple(entry.get("gates_conditions", ())),
                declared=entry,
                run=run,
                measure=measure_variant(run, costs, config.cost_model_raw),
            )
        )
    if len(executed) != config.declared_run_count:
        raise ConfigViolation(
            f"{len(executed)} runs executed against a hard limit of {config.declared_run_count}"
        )
    return executed


def run_by_scenario(runs: Sequence[RegisteredRun], scenario: str) -> RegisteredRun:
    matches = [run for run in runs if run.scenario == scenario]
    if len(matches) != 1:
        raise ConfigViolation(
            f"{len(matches)} runs carry the {scenario} scenario; Gate 4 declares exactly one of each"
        )
    return matches[0]


# -- folds -----------------------------------------------------------------------------------


@dataclass(frozen=True)
class Fold:
    index: int
    start: dt.date
    end: dt.date


def sealed_folds(config: Stage4Config) -> tuple[Fold, ...]:
    """The twelve sealed test folds, read from the seal and checked for the sealed properties.

    The bounds are not recomputed from "three calendar months from 2021-08-01": they are read. The
    derivation is then checked against them — contiguity, non-overlap, the declared count, the
    window fit, and an empty training set — so that a seal whose table disagreed with its own rule
    would fail here rather than be silently re-derived into agreement.
    """

    block = config.fold_construction
    train = _require(block, "train_folds", CRITERIA_REL)
    if int(train["count"]) != 0 or list(train["set"]):
        raise ConfigViolation(
            f"{CRITERIA_REL}: train_folds is not empty ({train['count']}). Gate 4 re-estimates "
            "nothing; a non-empty training set would contradict S4-C7 and S4-CONFLICT-5."
        )
    test = _require(block, "test_folds", CRITERIA_REL)
    declared = list(_require(test, "folds", CRITERIA_REL))
    count = int(_require(test, "count", CRITERIA_REL))
    if len(declared) != count:
        raise ConfigViolation(f"{CRITERIA_REL}: {len(declared)} folds listed against count={count}")
    if not bool(test["boundaries_inclusive"]):
        raise ConfigViolation(f"{CRITERIA_REL}: fold boundaries are sealed inclusive")

    folds = tuple(
        Fold(
            index=int(entry["fold"]),
            start=dt.date.fromisoformat(entry["start"]),
            end=dt.date.fromisoformat(entry["end"]),
        )
        for entry in declared
    )
    validation = validation_window()
    problems: list[str] = []
    for position, fold in enumerate(folds, start=1):
        if fold.index != position:
            problems.append(f"fold {position} carries index {fold.index}")
        if fold.end < fold.start:
            problems.append(f"fold {fold.index} ends {fold.end} before it starts {fold.start}")
        if not (validation.contains(fold.start) and validation.contains(fold.end)):
            problems.append(
                f"fold {fold.index} {fold.start}..{fold.end} is not wholly inside the validation "
                f"window {validation.start}..{validation.end}"
            )
    for previous, following in zip(folds, folds[1:]):
        if following.start != previous.end + dt.timedelta(days=1):
            problems.append(
                f"folds {previous.index} and {following.index} are not contiguous: "
                f"{previous.end} then {following.start}"
            )
    if folds and folds[0].start != validation.start:
        problems.append(f"fold 1 starts {folds[0].start}, not the validation start {validation.start}")
    if folds and folds[-1].end != validation.end:
        problems.append(f"fold {len(folds)} ends {folds[-1].end}, not the validation end {validation.end}")
    if problems:
        raise ConfigViolation(
            f"{CRITERIA_REL}: the sealed fold table is not self-consistent:\n  " + "\n  ".join(problems)
        )
    return folds


def fold_returns(
    result: Any, folds: Sequence[Fold], *, starting_equity: Decimal
) -> list[dict[str, Any]]:
    """The twelve fold returns of the BASE run, per the sealed ``fold_return_definition``.

    Fold 1's baseline is the sealed starting capital — S4-INTERP-3 records that warm-up leaves
    equity unchanged, so no validation observation is needed to establish it. Every later fold's
    baseline is the previous fold's last marked equity, which is what makes the twelve returns
    chain into the run's total return rather than being twelve independent backtests.

    Completion is the sealed three-part test. Note which way the third part points: the fold's last
    *trading session* comes from the frozen calendar, and the run must have produced an equity value
    for it. A run that stopped early therefore leaves later folds incomplete, which S4-C6 turns into
    NOT_EVALUABLE rather than into a smaller denominator.
    """

    validation = validation_window()
    equity_by_session = {point.session: point.equity for point in result.equity_curve}
    rows: list[dict[str, Any]] = []
    previous_equity = starting_equity
    for fold in folds:
        calendar = sessions_between(fold.start, fold.end)
        inside_window = validation.contains(fold.start) and validation.contains(fold.end)
        last_session = calendar[-1] if calendar else None
        marked = equity_by_session.get(last_session) if last_session is not None else None
        completed = bool(inside_window and calendar and marked is not None)
        baseline = previous_equity
        row: dict[str, Any] = {
            "fold": fold.index,
            "start": fold.start.isoformat(),
            "end": fold.end.isoformat(),
            "calendar_sessions": len(calendar),
            "run_sessions": len([d for d in equity_by_session if fold.start <= d <= fold.end]),
            "last_trading_session": last_session.isoformat() if last_session else None,
            "bounds_inside_validation_window": inside_window,
            "has_at_least_one_session": bool(calendar),
            "equity_at_last_session": f"{marked:f}" if marked is not None else None,
            "baseline_equity": f"{baseline:f}",
            "baseline_source": "sealed starting capital" if fold.index == 1 else f"fold {fold.index - 1} close",
            "completed": completed,
        }
        if completed:
            fold_return = marked / baseline - Decimal(1)
            row["fold_return"] = f"{fold_return:f}"
            row["positive"] = fold_return > Decimal(0)
            previous_equity = marked
        else:
            row["fold_return"] = None
            row["positive"] = False
        rows.append(row)
    return rows


# -- loading ----------------------------------------------------------------------------------


def load_validation_series(config: Stage4Config) -> dict[str, PriceSeries]:
    """The single dataset load of the authorized session.

    S4-INTERP-2: "The validation partition is read exactly once, in one authorized session, from one
    dataset load, with both declared runs executed inside that session against that single load."
    Both declared runs are computed from the object this returns.

    Exactly the frozen universe is loaded and nothing beside it. Unlike ``SE100-CFG-3003``, the
    Stage 4 protocol declares no ``benchmarks`` block, so there are no benchmark accounts at this
    gate and no symbol is loaded to support one; ``measurement_and_gate_criteria`` names the seven
    conditions and no benchmark. The representative's universe is a single symbol which happens to
    be the Attempt 2 benchmark symbol, but it is loaded because it is the universe, not because it
    is the benchmark — a distinction that matters only if the universe ever changes, at which point
    loading a benchmark symbol Stage 4 never declared would be an unauthorized extra read.
    """

    symbols = tuple(sorted(set(config.declared_universe)))
    return load_dataset(symbols)


def dataset_digests(series: dict[str, PriceSeries]) -> dict[str, str]:
    """A digest per loaded symbol file, for the ``runs/`` record's ``dataset_hashes``."""

    digests: dict[str, str] = {}
    for symbol in sorted(series):
        path = NORMALIZED_DIR / f"{symbol}.csv"
        if path.is_file():
            digests[str(path.relative_to(PROJECT_ROOT).as_posix())] = sha256_file(path)
    return digests


# -- gate evidence ------------------------------------------------------------------------------
#
# Everything below turns an executed run into the mapping :mod:`stockedge100.strategies.stage4_gate`
# reads. It computes no metric: it selects, coerces and labels. The coercion is the substantive part
# — :func:`~stockedge100.strategies.runner.measure` reports every quantity as a decimal *string* so
# that a report never rounds one, and the sealed predicates compare against ``Decimal`` literals.
# ``Decimal(str(value))`` is exact for those strings, which is what "no rounding before comparison"
# requires; ``float`` in the same position would introduce a representation error at the boundary and
# the boundary is where every one of these conditions is decided.


def _decimal_or_none(value: Any) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def equity_points(result: Any) -> int:
    """How many sessions the run marked. Three conditions read it, so it is named once."""

    return len(result.equity_curve)


def reached_window_end(result: Any) -> bool:
    """Did the run mark equity on the final *trading session* of the validation window?

    The comparison is against the frozen calendar rather than against ``result.end``: ``result.end``
    is the end that was *requested*, so a run that stopped early would still report it and the check
    would pass by construction. ``sessions_between`` is the same calendar the fold table is measured
    on, which keeps this answer and fold 12's ``completed`` from ever disagreeing.
    """

    validation = validation_window()
    calendar = sessions_between(validation.start, validation.end)
    if not calendar or not result.equity_curve:
        return False
    return result.equity_curve[-1].session == calendar[-1]


def closed_trade_gross(result: Any) -> dict[str, str]:
    """Gross profit and gross loss over CLOSED round trips, for S4-C4's evidence.

    Reported, not gating: the profit factor itself comes from
    :func:`~stockedge100.strategies.runner.measure`, and recomputing the ratio here would put a
    second definition of a gate input on disk. Gross loss is reported as a positive magnitude
    because the sealed measurement reads "gross profit divided by gross loss"; a signed denominator
    would make the reader's own division come out negative.
    """

    pnls = trade_pnls(result)
    profit = sum((value for value in pnls if value > Decimal(0)), Decimal(0))
    loss = sum((-value for value in pnls if value < Decimal(0)), Decimal(0))
    return {"gross_profit": f"{profit:f}", "gross_loss": f"{loss:f}"}


def base_gate_evidence(config: Stage4Config, run: RegisteredRun) -> dict[str, Any]:
    """The BASE run as S4-C1, S4-C2, S4-C3 and S4-C4 read it."""

    if run.scenario != BASE:
        raise ConfigViolation(
            f"{run.run_label!r} is a {run.scenario} run; S4-C1 through S4-C4 are sealed to the "
            "BASE-cost run and the stressed run may not substitute for it"
        )
    measured = run.measure
    result = run.run.result
    gross = closed_trade_gross(result)
    metrics = config.cost_model_raw.get("metrics", {})
    return {
        "run_label": run.run_label,
        "scenario": run.scenario,
        "gating_conditions": list(run.gates_conditions),
        "equity_points": equity_points(result),
        "reached_window_end": reached_window_end(result),
        "starting_equity": measured["starting_equity"],
        "final_equity": measured["final_equity"],
        "total_return": _decimal_or_none(measured["total_return"]),
        "sharpe": _decimal_or_none(measured["sharpe"]),
        "sharpe_risk_free_annual": measured["sharpe_risk_free_annual"],
        "daily_returns": max(equity_points(result) - 1, 0),
        "max_drawdown": _decimal_or_none(measured["max_drawdown"]),
        "max_drawdown_basis": metrics.get("max_drawdown_basis"),
        "profit_factor": _decimal_or_none(measured["profit_factor"]),
        "profit_factor_note": measured["profit_factor_note"],
        "closed_trades": measured["closed_trades"],
        "gross_profit": gross["gross_profit"],
        "gross_loss": gross["gross_loss"],
        "shutdown_session": measured["shutdown_session"],
        "shutdown_fraction": str(config.cost_model_raw["risk"]["research_shutdown_drawdown_fraction"]),
    }


def stress_gate_evidence(config: Stage4Config, run: RegisteredRun) -> dict[str, Any]:
    """The STRESSED run as S4-C5 reads it, and nothing else.

    S4-C5 is the only condition the stressed run gates. Its evidence therefore carries the stressed
    total return and the facts that establish the run really was the stressed one — the scenario, the
    multiplier actually in force, and that the section 5.1 shutdown was enforced on it too.
    """

    if run.scenario != STRESSED:
        raise ConfigViolation(
            f"{run.run_label!r} is a {run.scenario} run; S4-C5 is sealed to the stressed-cost run"
        )
    measured = run.measure
    result = run.run.result
    return {
        "run_label": run.run_label,
        "scenario": run.scenario,
        "gating_conditions": list(run.gates_conditions),
        "equity_points": equity_points(result),
        "reached_window_end": reached_window_end(result),
        "starting_equity": measured["starting_equity"],
        "final_equity": measured["final_equity"],
        "total_return": _decimal_or_none(measured["total_return"]),
        "stress_multiplier": result.cost_model["stress_multiplier"],
        "sealed_stress_multiplier": f"{config.stress_multiplier:f}",
        "shutdown_enforced": True,
        "shutdown_session": measured["shutdown_session"],
    }


def validation_evaluation_run_records() -> list[str]:
    """Every ``runs/`` record that is a Stage 4 *evaluation* run, by ``strategy_id``.

    S4-C7's second clause counts these and requires exactly one. The discriminator is
    ``strategy_id == REPRESENTATIVE`` rather than a substring of the stage name, because
    :func:`~stockedge100.reporting.stage_package.build_stage_package` writes ``strategy_id: None``
    into every package record it emits — including the two Stage 4 pre-registration records, which
    name the representative in their notes and would match any text search. Only a run that actually
    evaluated the representative sets the field, so the count is exact rather than approximate.
    """

    hits: list[str] = []
    if not RUNS_DIR.is_dir():
        return hits
    for path in sorted(RUNS_DIR.glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict) and record.get("strategy_id") == REPRESENTATIVE:
            hits.append(path.name)
    return hits


def invariance_gate_evidence(
    config: Stage4Config,
    *,
    digest_rows: Sequence[dict[str, Any]],
    invariance: dict[str, Any],
    run_records: Sequence[str],
    engine_runs: int,
) -> dict[str, Any]:
    """The four S4-C7 clauses, each as a measured value rather than an assertion.

    ``parameters_unchanged`` is taken from :func:`strategy_invariance`'s canonical-JSON equality
    against the Gate 3 primary parameterisation. S4-CONFLICT-6 is carried in the evidence because the
    sealed clause names ``config/stage4_representative_selection.json`` as the home of the
    parameterisation and that file does not carry one; the values live in the validation protocol,
    both files are inside the thirteen-artifact digest set, and clause 1 already forbids either from
    changing.
    """

    return {
        "all_digests_equal": all(bool(row["equal"]) for row in digest_rows),
        "digests_equal": len([row for row in digest_rows if row["equal"]]),
        "digests_total": len(digest_rows),
        "digest_rows": [dict(row) for row in digest_rows],
        "validation_evaluation_run_records": len(run_records),
        "validation_evaluation_run_record_names": list(run_records),
        "validation_window_engine_runs": engine_runs,
        "declared_run_count": config.declared_run_count,
        "parameters_unchanged": bool(invariance["parameters_equal_gate_3_primary"]),
        "parameter_comparison": {
            "sealed_parameters": invariance["sealed_parameters"],
            "gate_3_primary_parameters": invariance["gate_3_primary_parameters"],
            "equal": bool(invariance["parameters_equal_gate_3_primary"]),
            "source_of_the_sealed_parameterisation": (
                f"{PROTOCOL_REL} sealed_representative.parameters"
            ),
        },
        "strategy_invariance": {
            key: value for key, value in invariance.items()
            if key not in ("sealed_parameters", "gate_3_primary_parameters")
        },
        "conflict_note": (
            "S4-CONFLICT-6: the sealed clause names config/stage4_representative_selection.json as "
            "the home of the parameterisation; that file carries none and the values are in "
            f"{PROTOCOL_REL}. Both are inside the thirteen-artifact digest set."
        ),
    }
