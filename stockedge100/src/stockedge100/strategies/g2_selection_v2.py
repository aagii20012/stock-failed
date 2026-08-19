"""``SE100-G2-SEL-2`` — Attempt 3's representative-selection rule, return-blind by construction.

Attempt 2 selected on lowest turnover and got the quarterly k=1 corner: the parameterisation that by
construction takes the fewest decisions and holds the fewest positions. That variant earned about
0.4% over thirteen years and failed Gate 3 on return, profit factor, best-trade-removed return and
concentration. SEL-2 replaces the primary criterion with a *stability* one — prefer the variant whose
immediate grid neighbours behave as it does — and demotes turnover to the tiebreak.

**Return-blindness is structural, not a convention.** The scoring function accepts
:class:`SelectionInputV2` and nothing else, and that dataclass has six fields: a variant id, the
eligibility counter, and four risk-behaviour counters. There is no field a return, drawdown, profit
factor, Sharpe ratio, trade count or equity figure could travel in. Three independent guards run at
import, because the interesting failure is a *future* edit rather than this one:

1. the dataclass's actual field tuple must equal :data:`SELECTION_V2_FIELD_NAMES`, in order — the
   mechanism ``SE100-CFG-3103`` required of Attempt 2's ``SelectionInput``, extended to six fields;
2. no field name may contain performance vocabulary. This is not redundant with (1): guard (1)
   compares the class against a constant in this same module, and an editor adding a field would
   naturally edit both together. Guard (2) tests the *names themselves* and would still fire;
3. every counter is validated as a non-negative ``int`` at construction, so a ``float`` or
   ``Decimal`` return figure cannot be passed positionally into ``fill_count`` even once.

:func:`check_seal_agreement` adds a fourth, read off disk rather than restated: the module's field
tuple must equal the one sealed in ``representative_selection_rule.structural_enforcement``.

**Two sealed properties this module asserts rather than assumes.** The neighbour counts are 3, 4 or
5 — not the 2/3/4 of a two-axis grid — because the rebalance-frequency axis contributes exactly one
neighbour to every variant. Over the eighteen the partition is 8/8/2. And the neighbour relation is
symmetric. Both are measured in :func:`check_neighbourhood_structure`; the seal records that a hand
count of the partition was wrong on the first pass, which is why it is computed here and never typed.

**What the score cannot distinguish (``G2A3-CONFLICT-32``).** The sealed dissimilarity
``abs(a - b) / max(abs(a), abs(b), 1)`` returns 0 when a quantity is zero for both a variant and its
neighbour. That reads as perfect stability where in fact nothing fired. The formula is sealed as the
operating instruction specifies it and is **not** repaired here. Instead :func:`score_neighbourhood`
reports, per variant and per quantity, both the mean dissimilarity and the number of neighbour pairs
that were zero on both sides, so a reader can see how much of a low score is agreement and how much
is absence.

Neighbours are **structural**: a variant's score uses all of its grid neighbours whether or not those
neighbours passed the eligibility screen, because the score measures the smoothness of the parameter
region and an ineligible neighbour is part of that region. Only the variant being scored must itself
be eligible to be selectable.
"""

from __future__ import annotations

import dataclasses
import re
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal
from functools import lru_cache
from typing import Any, Iterable, Mapping, Sequence

from stockedge100.backtest.costs import exact
from stockedge100.backtest.errors import ConfigViolation
from stockedge100.backtest.g2_engine_ra1 import SCALAR_DECIMALS, SPELLED_DECIMALS
from stockedge100.backtest.g2_engine_ra3 import load_ra3_protocol
from stockedge100.strategies.g2_rotation_ra3 import RotationVariantRA3, rotation_variants

__all__ = [
    "FORBIDDEN_FIELD_SUBSTRINGS",
    "QUANTITIES",
    "SCORE_DECIMALS",
    "SELECTION_RULE_ID",
    "SELECTION_V2_FIELD_NAMES",
    "NeighbourhoodScore",
    "SelectionInputV2",
    "SelectionResultV2",
    "check_neighbourhood_structure",
    "check_seal_agreement",
    "dissimilarity",
    "load_selection_rule",
    "neighbours_of",
    "score_neighbourhood",
    "select_representative_v2",
]

SELECTION_RULE_ID = "SE100-G2-SEL-2"

#: The dataclass's field tuple, in order. Asserted against the class at import and against the seal
#: in :func:`check_seal_agreement`.
SELECTION_V2_FIELD_NAMES = (
    "variant_id",
    "shutdown_events",
    "fill_count",
    "ladder_descents",
    "lockout_arms",
    "stops_filled",
)

#: The four risk-behaviour quantities the score is computed over, summed across a variant's two runs.
QUANTITIES = ("fill_count", "ladder_descents", "lockout_arms", "stops_filled")

#: Vocabulary that may not appear in a field name. Deliberately spelled ``drawdown`` rather than
#: ``down``: ``shutdown_events`` is an eligibility counter, not a performance figure, and a substring
#: list that rejected it would have to be relaxed — and a guard that gets relaxed to pass is not a
#: guard. Each entry is the name of a quantity the selector must never see.
FORBIDDEN_FIELD_SUBSTRINGS = (
    "return",
    "drawdown",
    "profit",
    "sharpe",
    "sortino",
    "equity",
    "pnl",
    "cagr",
    "alpha",
    "yield",
    "gain",
    "loss",
    "trade",
    "win",
)

#: The four steps, keyed by their sealed ``order``. Attempt 2's step 3 node carried
#: ``why_not_gross_notional`` and ``attempt_2_note``; Attempt 3's carries ``definition`` and
#: ``role_change`` instead, so a near-copy of Attempt 2's reader would raise ``KeyError`` here.
EXPECTED_STEP_CRITERIA = {
    1: "zero_research_shutdown_events",
    2: "lowest_neighbourhood_instability_score",
    3: "lowest_turnover",
    4: "lexicographic_variant_id",
}

SCORE_DECIMALS = SCALAR_DECIMALS
SCORE_QUANTUM = Decimal(1).scaleb(-SCORE_DECIMALS)


# -- the input, and the three import-time guards --------------------------------------------------


@dataclass(frozen=True)
class SelectionInputV2:
    """Everything SEL-2 is permitted to know about one variant.

    Frozen, so a field cannot be reassigned between scoring and selection either. Every counter is
    summed across the variant's two runs (``#BASE`` and ``#STRESS``) before it arrives, so a variant
    contributes one integer per quantity.
    """

    variant_id: str
    shutdown_events: int
    fill_count: int
    ladder_descents: int
    lockout_arms: int
    stops_filled: int

    def __post_init__(self) -> None:
        if not isinstance(self.variant_id, str) or not self.variant_id:
            raise ConfigViolation(f"variant_id must be a non-empty string, got {self.variant_id!r}")
        for name in SELECTION_V2_FIELD_NAMES[1:]:
            value = getattr(self, name)
            # bool is a subclass of int and would pass a naive isinstance check; a counter that is
            # True rather than 1 is a bug worth failing on. The float rejection is the load-bearing
            # one: it is what stops a return or drawdown figure being passed positionally into a
            # counter slot, which is the one way a performance quantity could reach the score
            # despite the field names being clean.
            if isinstance(value, bool) or not isinstance(value, int):
                raise ConfigViolation(
                    f"{self.variant_id}: {name} must be a plain int, got {type(value).__name__} "
                    f"{value!r}. SEL-2 scores integer event counters; a non-integer here is either a "
                    "performance figure in a counter slot or a counter that was averaged."
                )
            if value < 0:
                raise ConfigViolation(f"{self.variant_id}: {name} is negative ({value})")

    def quantity(self, name: str) -> int:
        if name not in QUANTITIES:
            raise ConfigViolation(f"{name!r} is not one of the four scored quantities {QUANTITIES}")
        return int(getattr(self, name))


def _assert_structural_enforcement() -> None:
    """The two import-time guards. Raised as :class:`ConfigViolation`, not ``AssertionError``.

    ``python -O`` strips ``assert``. A selection rule whose return-blindness evaporates under an
    optimisation flag is not structurally enforced, so this raises unconditionally.
    """
    actual = tuple(field.name for field in dataclasses.fields(SelectionInputV2))
    if actual != SELECTION_V2_FIELD_NAMES:
        raise ConfigViolation(
            f"SelectionInputV2's fields are {actual}, but SEL-2 declares "
            f"{SELECTION_V2_FIELD_NAMES}. A field added, removed or reordered here changes what the "
            "selector can see, which is the one property this rule exists to guarantee."
        )
    for name in actual:
        lowered = name.lower()
        for banned in FORBIDDEN_FIELD_SUBSTRINGS:
            if banned in lowered:
                raise ConfigViolation(
                    f"SelectionInputV2 field {name!r} contains the performance term {banned!r}. "
                    "SEL-2 is return-blind: no field may name a return, drawdown, profit factor, "
                    "Sharpe ratio, trade count or equity figure."
                )


_assert_structural_enforcement()


# -- the seal -------------------------------------------------------------------------------------


@lru_cache(maxsize=1)
def load_selection_rule() -> dict[str, Any]:
    """The sealed ``representative_selection_rule`` node, verified before it is used."""
    rule = load_ra3_protocol()["representative_selection_rule"]
    check_seal_agreement(rule)
    return rule


def _sealed_step(order: int) -> Mapping[str, Any]:
    """Step ``order`` by its declared ``order`` field, never by list position.

    ``steps[1]`` would be step 2. The off-by-one reads correct and would quietly attribute one step's
    prose to another, so the lookup is by the value that is actually sealed.
    """
    for step in load_selection_rule()["steps"]:
        if int(step["order"]) == order:
            return step
    raise ConfigViolation(f"the sealed rule has no step of order {order}")


def check_seal_agreement(rule: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """This module's constants against the sealed rule. The fourth return-blindness guard.

    Reads the sealed field names, step criteria, quantities, dissimilarity formula and rounding, and
    requires each to match what this module implements. A constant edited here and nowhere else fails;
    so does a seal that describes a rule this module does not implement.
    """
    rule = load_ra3_protocol()["representative_selection_rule"] if rule is None else rule

    if rule["id"] != SELECTION_RULE_ID:
        raise ConfigViolation(f"the sealed rule identifies as {rule['id']!r}, not {SELECTION_RULE_ID}")
    for flag in ("frozen_before_any_variant_is_run", "return_blind"):
        if rule.get(flag) is not True:
            raise ConfigViolation(f"the sealed rule does not record {flag} as true")
    if rule.get("unchanged_from_attempt_2") is not False:
        raise ConfigViolation(
            "the sealed rule claims to be unchanged from Attempt 2, but SEL-2 replaces Attempt 2's "
            "primary criterion. A rule that claims continuity it does not have is the failure mode "
            "G2A3-CONFLICT-26 exists to prevent."
        )

    sealed_fields = tuple(rule["structural_enforcement"]["field_names"])
    if sealed_fields != SELECTION_V2_FIELD_NAMES:
        raise ConfigViolation(
            f"the seal declares fields {sealed_fields} but this module implements "
            f"{SELECTION_V2_FIELD_NAMES}"
        )

    steps = {int(step["order"]): step for step in rule["steps"]}
    if sorted(steps) != sorted(EXPECTED_STEP_CRITERIA):
        raise ConfigViolation(
            f"the sealed rule has steps {sorted(steps)}; this module implements "
            f"{sorted(EXPECTED_STEP_CRITERIA)}"
        )
    for order, criterion in EXPECTED_STEP_CRITERIA.items():
        if steps[order]["criterion"] != criterion:
            raise ConfigViolation(
                f"sealed step {order} is {steps[order]['criterion']!r}, this module implements "
                f"{criterion!r}"
            )
    if steps[1].get("unchanged_from_attempt_2") is not True:
        raise ConfigViolation("the sealed eligibility screen no longer claims continuity with Attempt 2")
    if "fill count" not in steps[3]["definition"]:
        raise ConfigViolation(
            f"the sealed tiebreak is defined as {steps[3]['definition']!r}, which does not name fill "
            "count. Turnover measured as gross notional would be a partial return proxy."
        )

    step2 = steps[2]
    sealed_quantities = tuple(step2["quantities"])
    if sealed_quantities != QUANTITIES:
        raise ConfigViolation(
            f"the seal scores {sealed_quantities} but this module scores {QUANTITIES}"
        )
    formula = step2["per_pair_dissimilarity"]
    if formula.replace(" ", "") != "abs(a-b)/max(abs(a),abs(b),1)":
        raise ConfigViolation(f"the sealed dissimilarity formula is {formula!r}, not the one implemented")
    arithmetic = step2["arithmetic"]
    spelled = SPELLED_DECIMALS[SCORE_DECIMALS]
    if f"{spelled} decimal places" not in arithmetic or "ROUND_HALF_EVEN" not in arithmetic:
        raise ConfigViolation(
            f"the sealed arithmetic does not quantize to {spelled} decimal places ROUND_HALF_EVEN: "
            f"{arithmetic!r}"
        )
    denominator = re.search(r"divided by (\d+) \* len\(neighbours\)", step2["score"])
    if denominator is None or int(denominator.group(1)) != len(QUANTITIES):
        raise ConfigViolation(
            f"the sealed score does not divide by {len(QUANTITIES)} * len(neighbours): "
            f"{step2['score']!r}"
        )

    return {
        "rule_id": rule["id"],
        "field_names": list(sealed_fields),
        "quantities": list(sealed_quantities),
        "steps": {order: steps[order]["criterion"] for order in sorted(steps)},
        "dissimilarity": formula,
        "score_decimals": SCORE_DECIMALS,
        "forbidden_field_substrings": list(FORBIDDEN_FIELD_SUBSTRINGS),
        "no_reselection": rule["no_reselection"],
        "no_candidate_verdict": rule["no_candidate_path"]["verdict"],
        "second_fail_verdict": rule["second_fail_path"]["verdict"],
    }


# -- neighbours -----------------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _axes() -> tuple[tuple[int, ...], tuple[int, ...], tuple[str, ...]]:
    """The three ordered axes, from the seal. ``rotation_variants()`` has already verified the grid."""
    axes = load_ra3_protocol()["grid"]["axes"]
    lookbacks = tuple(int(v) for v in axes["lookback_months"])
    ks = tuple(int(v) for v in axes["top_k"])
    frequencies = tuple(str(v) for v in axes["rebalance_frequency"])
    if len(frequencies) != 2:
        raise ConfigViolation(
            f"the frequency axis has {len(frequencies)} values {frequencies}; the sealed neighbour "
            "counts of 3/4/5 assume it has exactly two, contributing one neighbour to every variant"
        )
    for label, axis in (("lookback_months", lookbacks), ("top_k", ks)):
        if len(axis) != 3:
            raise ConfigViolation(
                f"the {label} axis has {len(axis)} values {axis}; the sealed 8/8/2 partition assumes "
                "three ordered values"
            )
    return lookbacks, ks, frequencies


@lru_cache(maxsize=1)
def _by_key() -> dict[tuple[int, int, str], RotationVariantRA3]:
    return {(v.lookback_months, v.top_k, v.frequency): v for v in rotation_variants()}


@lru_cache(maxsize=None)
def neighbours_of(variant_id: str) -> tuple[str, ...]:
    """The variants reachable from ``variant_id`` by exactly one single-axis step, sorted.

    Ordered axes step to the adjacent *positions*, not to every other value: from a 3-month lookback
    the neighbour is 6, not 6 and 12. The frequency axis has two values, so it flips.
    """
    lookbacks, ks, frequencies = _axes()
    variant = next((v for v in rotation_variants() if v.variant_id == variant_id), None)
    if variant is None:
        raise ConfigViolation(f"{variant_id!r} is not one of the eighteen declared variants")

    by_key = _by_key()
    found: list[str] = []
    lb_index = lookbacks.index(variant.lookback_months)
    k_index = ks.index(variant.top_k)
    for step in (-1, 1):
        for index, axis, key in (
            (lb_index + step, lookbacks, "lookback"),
            (k_index + step, ks, "k"),
        ):
            if not 0 <= index < len(axis):
                continue
            if key == "lookback":
                candidate = (axis[index], variant.top_k, variant.frequency)
            else:
                candidate = (variant.lookback_months, axis[index], variant.frequency)
            found.append(by_key[candidate].variant_id)
    for frequency in frequencies:
        if frequency != variant.frequency:
            found.append(by_key[(variant.lookback_months, variant.top_k, frequency)].variant_id)

    if variant_id in found:
        raise ConfigViolation(f"{variant_id} was enumerated as its own neighbour")
    if len(set(found)) != len(found):
        raise ConfigViolation(f"{variant_id} has duplicate neighbours: {sorted(found)}")
    return tuple(sorted(found))


def check_neighbourhood_structure() -> dict[str, Any]:
    """The sealed 3/4/5 counts, the 8/8/2 partition and symmetry, computed over all eighteen.

    The seal records that a hand count of the partition was wrong on the first pass. It is therefore
    enumerated here and compared against the sealed prose, never typed as a literal expectation that
    happens to agree.
    """
    variants = rotation_variants()
    neighbours = {v.variant_id: neighbours_of(v.variant_id) for v in variants}

    counts = {vid: len(n) for vid, n in neighbours.items()}
    partition: dict[int, int] = {}
    for count in counts.values():
        partition[count] = partition.get(count, 0) + 1

    if sorted(partition) != [3, 4, 5]:
        raise ConfigViolation(
            f"neighbour counts are {sorted(partition)}; the seal declares 3, 4 or 5. The frequency "
            "axis contributes exactly one neighbour to every variant, which is what makes the "
            "operating instruction's 2/3/4 wrong (G2A3-CONFLICT-27)."
        )
    if partition != {3: 8, 4: 8, 5: 2}:
        raise ConfigViolation(
            f"the neighbour-count partition is {partition}; the seal declares 8 with three, 8 with "
            "four and 2 with five"
        )

    asymmetric = [
        (a, b)
        for a, ns in neighbours.items()
        for b in ns
        if a not in neighbours[b]
    ]
    if asymmetric:
        raise ConfigViolation(
            f"the neighbour relation is not symmetric: {asymmetric[:5]}. A one-step change is its own "
            "inverse, so an asymmetry means the enumeration is wrong in one direction."
        )

    unknown = sorted({b for ns in neighbours.values() for b in ns} - set(counts))
    if unknown:
        raise ConfigViolation(f"neighbours name variants outside the grid: {unknown}")

    return {
        "variant_count": len(variants),
        "neighbours": {vid: list(ns) for vid, ns in neighbours.items()},
        "counts": counts,
        "partition": partition,
        "symmetric": True,
        "total_directed_pairs": sum(counts.values()),
        "sealed_partition_prose": _sealed_step(2)["neighbour_counts"],
        "instruction_conflict_ref": "G2A3-CONFLICT-27",
    }


# -- the score ------------------------------------------------------------------------------------


@dataclass(frozen=True)
class NeighbourhoodScore:
    """One variant's instability score, with enough detail to audit it rather than trust it."""

    variant_id: str
    score: Decimal
    neighbours: tuple[str, ...]
    per_quantity_mean: dict[str, Decimal]
    per_quantity_both_zero: dict[str, int]
    own_quantities: dict[str, int]

    def to_json(self) -> dict[str, Any]:
        return {
            "variant_id": self.variant_id,
            "instability_score": f"{self.score:f}",
            "neighbours": list(self.neighbours),
            "neighbour_count": len(self.neighbours),
            "per_quantity_mean_dissimilarity": {
                q: f"{v:f}" for q, v in sorted(self.per_quantity_mean.items())
            },
            "per_quantity_pairs_zero_on_both_sides": dict(sorted(self.per_quantity_both_zero.items())),
            "own_quantities": dict(sorted(self.own_quantities.items())),
        }


@exact
def dissimilarity(a: int, b: int) -> Decimal:
    """``abs(a - b) / max(abs(a), abs(b), 1)``, exactly as sealed.

    The ``max(..., 1)`` floor means two zeros score 0 — perfect stability where nothing fired. Sealed
    as the operating instruction specifies it and not repaired; :func:`score_neighbourhood` counts
    those pairs separately so the ambiguity is visible rather than silent. See ``G2A3-CONFLICT-32``.
    """
    numerator = Decimal(abs(int(a) - int(b)))
    denominator = Decimal(max(abs(int(a)), abs(int(b)), 1))
    return numerator / denominator


@exact
def score_neighbourhood(inputs: Iterable[SelectionInputV2]) -> dict[str, NeighbourhoodScore]:
    """Score every variant against its structural neighbours. Return-blind by the type it accepts.

    Requires all eighteen: a score computed against a partial grid would silently use fewer
    neighbours for the variants at the edge of whatever subset was passed, which is a different
    statistic wearing the same name.
    """
    by_id: dict[str, SelectionInputV2] = {}
    for item in inputs:
        if not isinstance(item, SelectionInputV2):
            raise ConfigViolation(
                f"score_neighbourhood accepts SelectionInputV2 only, got {type(item).__name__}. The "
                "type is the return-blindness guarantee; a duck-typed object could carry anything."
            )
        if item.variant_id in by_id:
            raise ConfigViolation(f"{item.variant_id} was supplied twice")
        by_id[item.variant_id] = item

    declared = {v.variant_id for v in rotation_variants()}
    missing = sorted(declared - set(by_id))
    extra = sorted(set(by_id) - declared)
    if missing or extra:
        raise ConfigViolation(
            f"score_neighbourhood needs exactly the eighteen declared variants; missing {missing}, "
            f"unexpected {extra}"
        )

    check_neighbourhood_structure()

    scores: dict[str, NeighbourhoodScore] = {}
    for variant_id, mine in sorted(by_id.items()):
        neighbours = neighbours_of(variant_id)
        per_quantity_total = {q: Decimal(0) for q in QUANTITIES}
        per_quantity_zero = {q: 0 for q in QUANTITIES}
        for neighbour_id in neighbours:
            theirs = by_id[neighbour_id]
            for quantity in QUANTITIES:
                a, b = mine.quantity(quantity), theirs.quantity(quantity)
                per_quantity_total[quantity] += dissimilarity(a, b)
                if a == 0 and b == 0:
                    per_quantity_zero[quantity] += 1

        pairs = len(QUANTITIES) * len(neighbours)
        if pairs == 0:
            raise ConfigViolation(f"{variant_id} has no neighbours; the score would divide by zero")
        total = sum(per_quantity_total.values(), Decimal(0))
        scores[variant_id] = NeighbourhoodScore(
            variant_id=variant_id,
            score=(total / pairs).quantize(SCORE_QUANTUM, rounding=ROUND_HALF_EVEN),
            neighbours=neighbours,
            per_quantity_mean={
                q: (per_quantity_total[q] / len(neighbours)).quantize(
                    SCORE_QUANTUM, rounding=ROUND_HALF_EVEN
                )
                for q in QUANTITIES
            },
            per_quantity_both_zero=dict(per_quantity_zero),
            own_quantities={q: mine.quantity(q) for q in QUANTITIES},
        )
    return scores


# -- selection ------------------------------------------------------------------------------------


@dataclass(frozen=True)
class SelectionResultV2:
    """The outcome of SEL-2, including the losers, so the choice can be re-derived from the record."""

    selected: str | None
    eligible: tuple[str, ...]
    ineligible: tuple[str, ...]
    ranking: tuple[dict[str, Any], ...]
    scores: dict[str, NeighbourhoodScore]
    decided_at_step: int | None

    def to_json(self) -> dict[str, Any]:
        return {
            "rule_id": SELECTION_RULE_ID,
            "selected_variant_id": self.selected,
            "decided_at_step": self.decided_at_step,
            "eligible_variants": list(self.eligible),
            "ineligible_variants": list(self.ineligible),
            "eligible_count": len(self.eligible),
            "ranking": [dict(row) for row in self.ranking],
            "all_scores": {vid: s.to_json() for vid, s in sorted(self.scores.items())},
        }


def select_representative_v2(inputs: Sequence[SelectionInputV2]) -> SelectionResultV2:
    """Apply SEL-2's four steps and return the representative, or ``None`` if none is eligible.

    Scores are computed over all eighteen before the eligibility screen is applied to the *candidates*,
    because neighbours are structural: an ineligible neighbour is still part of the parameter region
    whose smoothness the score measures.

    ``decided_at_step`` records which criterion actually broke the tie, so a report can say "chosen on
    stability" or "chosen on turnover" from the record rather than from an assumption.
    """
    load_selection_rule()
    scores = score_neighbourhood(inputs)
    by_id = {item.variant_id: item for item in inputs}

    eligible = tuple(sorted(vid for vid, item in by_id.items() if item.shutdown_events == 0))
    ineligible = tuple(sorted(set(by_id) - set(eligible)))

    ranking = []
    for variant_id in sorted(by_id):
        item = by_id[variant_id]
        ranking.append(
            {
                "variant_id": variant_id,
                "eligible": variant_id in eligible,
                "shutdown_events": item.shutdown_events,
                "instability_score": f"{scores[variant_id].score:f}",
                "fill_count": item.fill_count,
            }
        )
    ranking.sort(
        key=lambda row: (
            not row["eligible"],
            Decimal(row["instability_score"]),
            row["fill_count"],
            row["variant_id"],
        )
    )

    if not eligible:
        return SelectionResultV2(
            selected=None,
            eligible=(),
            ineligible=ineligible,
            ranking=tuple(ranking),
            scores=scores,
            decided_at_step=1,
        )

    ordered = [
        (scores[vid].score, by_id[vid].fill_count, vid) for vid in eligible
    ]
    ordered.sort()
    best = ordered[0]
    # Which criterion actually decided it: step 2 unless the leader tied on score, step 3 unless it
    # also tied on turnover. Reporting "chosen on stability" when the score was tied would misdescribe
    # the rule that did the work.
    tied_on_score = [row for row in ordered if row[0] == best[0]]
    if len(eligible) == 1:
        decided_at = 1
    elif len(tied_on_score) == 1:
        decided_at = 2
    elif len([row for row in tied_on_score if row[1] == best[1]]) == 1:
        decided_at = 3
    else:
        decided_at = 4

    return SelectionResultV2(
        selected=best[2],
        eligible=eligible,
        ineligible=ineligible,
        ranking=tuple(ranking),
        scores=scores,
        decided_at_step=decided_at,
    )
