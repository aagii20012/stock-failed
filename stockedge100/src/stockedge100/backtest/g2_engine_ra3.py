"""Risk architecture RA3: Attempt 2's RA2 with one ladder tier deleted, and nothing else changed.

RA3 is not a new risk architecture. It is RA2 with the ``[0.05, 0.08)`` de-risk tier removed, which
restores Generation 1's own original RA1-5 ladder — the one that held full sizing flat until an 8%
drawdown. Attempt 2 had added that tier beyond what Generation 1 sealed, and its own evidence showed
the combined sizing scalar running as low as 0.19 with the ladder descending over a thousand times
across 36 runs. A 5%-from-peak dip is ordinary market behaviour, so a rung that fires there throttles
ordinary markets as well as crises.

What this module is, and is not
--------------------------------------------------

It is a **band table and its loader**. :class:`RotationEngineRA3` subclasses
:class:`~stockedge100.backtest.g2_engine_ra1.RotationEngineRA1` and overrides no method at all. The
four RA2 mechanisms the operating prompt keeps exactly — the 50% aggregate exposure ceiling, the 10%
annualized volatility target, the 8% per-position stop, the 10-session re-entry lockout — are
inherited code paths, not re-implementations. So are the drawdown-from-high-water computation, the
immediate-descent / one-band-recovery transition rule, the lockout gating, and every measurement
counter. A fork would have let RA3 drift from RA2 in some second place while claiming a single
difference; a subclass cannot.

The single difference therefore lives in exactly one place: what
:func:`load_risk_architecture_ra3` returns. ``RotationEngineRA1.__init__`` assigns ``self.risk`` from
RA2's loader and derives ``self.sessions_in_band`` from it. ``RotationEngineRA3.__init__`` calls
``super().__init__`` and then re-derives those two attributes, and *only* those two, from RA3's seal.

``G2A3-CONFLICT-31``: re-deriving state a base class already set is a code smell in general, and it
is used here deliberately, because the alternative is worse. Passing the architecture into
``RotationEngineRA1.__init__`` would mean editing a frozen Attempt 2 module, which the constitution
forbids; copying its 1100 lines would mean two ladders that must be kept in agreement by hand. The
smell is contained by making the claim checkable rather than asserted:
:func:`attributes_derived_from_risk` parses ``RotationEngineRA1.__init__`` with :mod:`ast` and
returns every ``self.X`` whose assignment depends on ``self.risk``. The module asserts at import that
this set is exactly ``{"risk", "sessions_in_band"}``. If the frozen base class ever derived a third
attribute from the architecture, the import fails here rather than a variant silently running with
one RA2-shaped counter.

Provenance is checked, not asserted
--------------------------------------------------

RA3's three bands are stated as scalars relative to the 50% ceiling: 1.00, 0.50, 0.25. Generation 1's
RA1-5 states its ladder as absolute exposure caps: 0.50, 0.25, 0.125. Those are the same ladder, and
:func:`check_generation_1_provenance` multiplies through and compares band for band rather than
taking the seal's word for it. The pre-registration ``SE100-GOV-2007`` performed the same check
independently at seal time; this one runs against whatever is on disk when a variant actually runs.
"""

from __future__ import annotations

import ast
import datetime as dt
import inspect
import json
import re
from decimal import Decimal

from stockedge100.backtest.config import PROJECT_ROOT, dec
from stockedge100.backtest.costs import CostModel
from stockedge100.backtest.dataset import PriceSeries
from stockedge100.backtest.engine import Probe
from stockedge100.backtest.errors import ConfigViolation
from stockedge100.backtest.g2_engine_ra1 import (
    CLAMP_NAMES_RA2,
    SCALAR_DECIMALS,
    SPELLED_DECIMALS,
    LadderBand,
    RiskArchitecture,
    RotationEngineRA1,
    _require,
    _validate_architecture,
    quantize_scalar,
)
from stockedge100.backtest.window import ResearchWindow

__all__ = [
    "DELETED_RA2_TIER",
    "GENERATION_1_PROTOCOL_PATH",
    "PROTOCOL_ID",
    "PROTOCOL_PATH",
    "RA3_BAND_COUNT",
    "RA3_SHALLOWEST_ENGAGEMENT",
    "RISK_DERIVED_ATTRIBUTES",
    "STRATEGY_ID",
    "RotationEngineRA3",
    "attributes_derived_from_risk",
    "check_generation_1_provenance",
    "load_ra3_protocol",
    "load_risk_architecture_ra3",
]

#: The sealed Attempt 3 protocol. Read, never written, and checked for identity before believed.
PROTOCOL_PATH = PROJECT_ROOT / "config" / "generation_2" / "g2_rotation_ra3_protocol.json"
PROTOCOL_ID = "SE100-CFG-3105"
STRATEGY_ID = "SE100-G2-S3-C3-ROTATION-RA3"

#: Attempt 2's sealed protocol, read only to recompute the single-difference claim.
ATTEMPT_2_PROTOCOL_PATH = PROJECT_ROOT / "config" / "generation_2" / "g2_rotation_ra1_protocol.json"

#: Generation 1's sealed protocol, read only to recompute the ladder's provenance.
GENERATION_1_PROTOCOL_PATH = (
    PROJECT_ROOT / "config" / "stage3_attempt2_strategy_protocol.json"
)

#: RA3's ladder has exactly three rungs. Stated as a constant because "three" is the whole change:
#: a four-band RA3 is RA2 wearing a different name, and a two-band one has lost a rung Generation 1
#: sealed. Neither should be able to load.
RA3_BAND_COUNT = 3

#: No ladder step may engage below this drawdown. This is the sentence the attempt exists to test.
RA3_SHALLOWEST_ENGAGEMENT = Decimal("0.08")

#: The RA2 rung RA3 removes, as ``(dd_from, dd_to_exclusive, scalar)``. Checked against RA2's own
#: seal by :func:`check_single_difference_from_ra2`, never trusted as a literal.
DELETED_RA2_TIER = (Decimal("0.05"), Decimal("0.08"), Decimal("0.75"))

#: The attributes ``RotationEngineRA1.__init__`` derives from the risk architecture, and therefore the
#: exact set ``RotationEngineRA3`` must re-derive. Asserted against the base class's AST at import.
RISK_DERIVED_ATTRIBUTES = frozenset({"risk", "sessions_in_band"})


def load_ra3_protocol() -> dict[str, object]:
    """The sealed Attempt 3 protocol, checked for identity before any field of it is believed.

    Mirrors :func:`stockedge100.backtest.g2_engine_ra1.load_ra1_protocol`, with ``attempt`` at 3. A
    protocol that says ``attempt: 2`` is Attempt 2's file and would silently give this engine RA2's
    four-band ladder back.
    """
    if not PROTOCOL_PATH.is_file():
        raise ConfigViolation(f"the Attempt 3 rotation protocol is missing at {PROTOCOL_PATH}")
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))

    for field, expected in (
        ("artifact_id", PROTOCOL_ID),
        ("generation", 2),
        ("stage", 3),
        ("attempt", 3),
        ("strategy_id", STRATEGY_ID),
    ):
        if protocol.get(field) != expected:
            raise ConfigViolation(
                f"{PROTOCOL_PATH.name} declares {field}={protocol.get(field)!r}; this module "
                f"implements {expected!r}"
            )
    if protocol.get("declared_before_any_strategy_code") is not True:
        raise ConfigViolation(
            f"{PROTOCOL_PATH.name} no longer asserts declared_before_any_strategy_code. The whole "
            "point of that file is that it predates this one."
        )
    if protocol.get("live_trading_authorized") is not False:
        raise ConfigViolation(
            f"{PROTOCOL_PATH.name} does not declare live_trading_authorized false; this is a "
            "development-window research module and may never run against a broker"
        )
    return protocol


def _bands_of(architecture_node: dict[str, object], component: str) -> tuple[LadderBand, ...]:
    """Parse a ``bands`` array from either generation's protocol into the shared band type."""
    bands: list[LadderBand] = []
    for index, entry in enumerate(architecture_node["components"][component]["bands"]):
        _require(
            entry["band"] == index,
            f"the sealed {component} bands are not indexed 0..n-1 in order",
        )
        upper = entry["dd_to_exclusive"]
        bands.append(
            LadderBand(
                band=index,
                dd_from=dec(entry["dd_from"]),
                dd_to_exclusive=None if upper is None else dec(upper),
                scalar=dec(entry["scalar"]),
            )
        )
    return tuple(bands)


def load_risk_architecture_ra3(protocol: dict[str, object] | None = None) -> RiskArchitecture:
    """Parse and validate RA3 from its seal.

    Deliberately a near-copy of RA2's loader rather than a call to it: RA2's loader hardcodes its own
    protocol path and its own ``RA2-n`` component names, and reaching into it with a swapped path
    would mean editing a frozen module. Every predicate RA2's loader applies is applied here, plus
    the three that make RA3 RA3 — three bands, the shallowest engagement at 0.08, and the deleted
    tier genuinely absent.
    """
    protocol = protocol if protocol is not None else load_ra3_protocol()
    architecture = protocol["risk_architecture"]

    _require(architecture["id"] == "RA3", "the sealed risk architecture is not RA3")
    _require(
        architecture["frozen_before_any_variant_is_run"] is True,
        "the sealed risk architecture no longer asserts it was frozen before any variant was run",
    )
    _require(
        architecture["not_part_of_the_grid"] is True,
        "the sealed risk architecture no longer asserts its constants are not grid axes",
    )

    components = architecture["components"]
    combined = architecture["combined_scalar"]
    _require(
        "f_vol(t) * f_ladder(t)" in combined["formula"],
        "the sealed combined scalar is no longer the product of the two terms; this module "
        "multiplies them and would silently implement a different rule",
    )
    _require(
        f"{SPELLED_DECIMALS[SCALAR_DECIMALS]} decimal places" in combined["formula"]
        and "ROUND_DOWN" in combined["formula"],
        f"the sealed combined scalar no longer quantizes to {SCALAR_DECIMALS} places ROUND_DOWN",
    )
    _require(
        any("research shutdown" in item for item in combined["does_not_apply_to"]),
        "the sealed combined scalar no longer exempts the constitutional research shutdown",
    )

    ra1 = components["RA3-1"]
    _require(
        tuple(ra1["enforcement"]["part_a_entry_clamp"]["clamp_names"]) == CLAMP_NAMES_RA2,
        f"the sealed clamp names {ra1['enforcement']['part_a_entry_clamp']['clamp_names']} are not "
        f"the ones this engine applies {list(CLAMP_NAMES_RA2)}",
    )
    exposure_ceiling = dec(ra1["value"])

    ra2 = components["RA3-2"]
    _require(
        ra2["measured_on"] == "THE_EQUITY_CURVE",
        "the sealed volatility target is no longer measured on the equity curve",
    )
    volatility_target = dec(ra2["value"])

    ra3 = components["RA3-3"]
    _require(
        ra3["reference_price"] == "cost_basis / quantity",
        "the sealed stop reference price is no longer cost_basis / quantity",
    )
    stop_fraction = dec(ra3["value"])

    bands = _bands_of(architecture, "RA3-4")

    ra5 = components["RA3-5"]
    lockout_sessions = ra5["value"]
    _require(
        isinstance(lockout_sessions, int) and not isinstance(lockout_sessions, bool),
        "the sealed re-entry lockout is not an integer number of sessions",
    )
    _require(
        ra5["counted_in_sessions_not_days"].startswith("Trading sessions"),
        "the sealed re-entry lockout is no longer counted in trading sessions",
    )

    architecture_object = RiskArchitecture(
        architecture_id=architecture["id"],
        exposure_ceiling=exposure_ceiling,
        volatility_target=volatility_target,
        stop_fraction=stop_fraction,
        bands=bands,
        lockout_sessions=lockout_sessions,
    )

    # Everything RA2's loader checks about ladder shape: contiguity, strict monotonicity, band 0 at
    # full weight from zero, the deepest band unbounded above, every scalar in (0, 1].
    _validate_architecture(architecture_object)

    # The three predicates that are RA3's alone.
    _require(
        len(bands) == RA3_BAND_COUNT,
        f"RA3's ladder has {len(bands)} bands, not {RA3_BAND_COUNT}. Four bands is RA2 under a new "
        "name; two has lost a rung Generation 1 sealed.",
    )
    _require(
        bands[0].dd_to_exclusive == RA3_SHALLOWEST_ENGAGEMENT,
        f"RA3's full-sizing band ends at {bands[0].dd_to_exclusive}, not "
        f"{RA3_SHALLOWEST_ENGAGEMENT}. The single change this attempt makes is that no ladder step "
        "engages below an 8 percent drawdown; a band ending anywhere else is a different attempt.",
    )
    for band in bands[1:]:
        _require(
            band.dd_from >= RA3_SHALLOWEST_ENGAGEMENT,
            f"RA3 ladder band {band.band} engages at a drawdown of {band.dd_from}, below the "
            f"{RA3_SHALLOWEST_ENGAGEMENT} floor this attempt is defined by",
        )

    return architecture_object


#: A number and nothing after it. Generation 1's ladder is stated in prose sentences that end in a
#: period, so a greedy pattern hands ``Decimal`` the string ``"0.50."`` and the failure surfaces far
#: from its cause. This bug has been written twice in this project already.
_NUMBER = r"[0-9]+(?:\.[0-9]+)?"

#: The three sentences of ``RA1-5.rule`` that state the ladder, each paired with the function that
#: turns its captured groups into a ``(dd_from, dd_to_exclusive, absolute_cap)`` triple. Matching the
#: whole sentence rather than scanning it for numbers means a reworded rule fails loudly instead of
#: being parsed into something plausible.
#:
#: The three sentences do not share a shape, and that is the trap: ``dd < 0.08`` states the band's
#: *upper* bound, while ``dd >= 0.10`` states its lower one. Reading "the first number" out of each
#: uniformly gives the shallowest band a floor of 0.08, which is wrong and which compares cleanly
#: against the wrong RA3 band.
_GENERATION_1_RULE_PATTERNS = (
    (
        rf"^dd < ({_NUMBER}): f_cap = ({_NUMBER})\.$",
        lambda g: (dec("0.00"), dec(g[0]), dec(g[1])),
    ),
    (
        rf"^({_NUMBER}) <= dd < ({_NUMBER}): f_cap = ({_NUMBER})\.$",
        lambda g: (dec(g[0]), dec(g[1]), dec(g[2])),
    ),
    (
        rf"^dd >= ({_NUMBER}): f_cap = ({_NUMBER})\.$",
        lambda g: (dec(g[0]), None, dec(g[1])),
    ),
)


def _plain(value: Decimal | None) -> str | None:
    """Render a Decimal without trailing-zero noise, so two spellings of one number compare equal.

    ``quantize_scalar`` returns nine decimal places, so the converted RA3 cap is ``0.500000000``
    while Generation 1 sealed ``0.50``. Those are the same number and must read as the same string
    in the report, or a reader has to do the arithmetic again to see that they match.
    """
    return None if value is None else f"{value.normalize():f}"


def _generation_1_ladder_from_prose(
    node: dict[str, object],
) -> list[tuple[Decimal, Decimal | None, Decimal]]:
    """Parse ``RA1-5.rule``'s three sentences into ``(dd_from, dd_to_exclusive, cap)`` triples."""
    sentences = [str(line).strip() for line in node["RA1-5"]["rule"]]
    parsed: list[tuple[Decimal, Decimal | None, Decimal]] = []
    for pattern, build in _GENERATION_1_RULE_PATTERNS:
        matches = [m for m in (re.match(pattern, s) for s in sentences) if m is not None]
        _require(
            len(matches) == 1,
            f"Generation 1's RA1-5 rule has {len(matches)} sentences matching {pattern!r}; RA3's "
            "provenance claim is that it restores that exact ladder, and a reworded rule must not "
            "be parsed into a plausible substitute",
        )
        parsed.append(build(matches[0].groups()))

    # The sentences are read independently, so their contiguity is a finding rather than an
    # assumption: three tiers that happened not to abut would not be a ladder at all.
    for lower, upper in zip(parsed, parsed[1:]):
        _require(
            lower[1] == upper[0],
            f"Generation 1's RA1-5 tiers are not contiguous: one ends at {lower[1]}, the next "
            f"begins at {upper[0]}",
        )
    return parsed


def check_generation_1_provenance(architecture: RiskArchitecture) -> dict[str, object]:
    """Recompute the claim that RA3's ladder *is* Generation 1's original RA1-5 ladder.

    Generation 1 states its ladder twice in one file: as three prose sentences in ``RA1-5.rule``, and
    as ``ladder_rungs`` pairs on each of its three experiments. Both are read, and they are required
    to agree with each other before either is compared against RA3 — a single reading that happened
    to match would leave open which statement RA3 was restoring.

    The two generations also speak different units. Generation 1 states absolute exposure caps
    (0.50, 0.25, 0.125); RA3 states scalars against the 50% ceiling (1.00, 0.50, 0.25). Multiplying
    through is the only way to compare them, and comparing them is the only way the provenance claim
    is evidence rather than an assertion.

    Returns the worked comparison for the report; raises :class:`ConfigViolation` if the two ladders
    are not the same ladder.
    """
    if not GENERATION_1_PROTOCOL_PATH.is_file():
        raise ConfigViolation(
            f"Generation 1's sealed protocol is missing at {GENERATION_1_PROTOCOL_PATH}; RA3's "
            "provenance claim cannot be checked and must not be asserted"
        )
    generation_1 = json.loads(GENERATION_1_PROTOCOL_PATH.read_text(encoding="utf-8"))

    prose = _generation_1_ladder_from_prose(generation_1["risk_architecture"])

    # The experiments state only the two engaged tiers; the full-sizing tier is RA1-1's own ceiling,
    # which is the first prose sentence's cap.
    per_experiment = {
        experiment["experiment_id"]: [
            (dec(threshold), dec(cap))
            for threshold, cap in experiment["primary_parameters"]["ladder_rungs"]
        ]
        for experiment in generation_1["experiments"]
    }
    _require(
        len(per_experiment) == len(generation_1["experiments"]) and len(per_experiment) > 0,
        "Generation 1's experiments do not have distinct ids; the ladder agreement check would "
        "silently compare fewer experiments than the file contains",
    )
    distinct = {tuple(rungs) for rungs in per_experiment.values()}
    _require(
        len(distinct) == 1,
        f"Generation 1's {len(per_experiment)} experiments disagree about the RA1 ladder rungs: "
        f"{sorted(str(entry) for entry in distinct)}",
    )
    # The experiments state only the two engaged tiers, as (threshold, cap); the prose states all
    # three as full bands. Compare the part they have in common.
    rungs = list(distinct.pop())
    prose_engaged = [(dd_from, cap) for dd_from, _, cap in prose[1:]]
    _require(
        rungs == prose_engaged,
        f"Generation 1 states its own ladder two ways and they disagree: RA1-5's prose gives "
        f"{[(str(a), str(b)) for a, b in prose_engaged]} for the engaged tiers, the experiments' "
        f"ladder_rungs give {[(str(a), str(b)) for a, b in rungs]}. RA3 cannot claim to restore a "
        "ladder its own source states inconsistently.",
    )

    ra3_bands = [
        (
            band.dd_from,
            band.dd_to_exclusive,
            quantize_scalar(band.scalar * architecture.exposure_ceiling),
        )
        for band in architecture.bands
    ]
    _require(
        len(ra3_bands) == len(prose),
        f"RA3 declares {len(ra3_bands)} ladder tiers; Generation 1's RA1-5 sealed {len(prose)}",
    )
    for (ra3_from, ra3_to, ra3_cap), (g1_from, g1_to, g1_cap) in zip(ra3_bands, prose):
        _require(
            ra3_from == g1_from and ra3_to == g1_to and ra3_cap == g1_cap,
            f"RA3's tier [{ra3_from}, {ra3_to}) caps exposure at {ra3_cap}; Generation 1's RA1-5 "
            f"tier [{g1_from}, {g1_to}) capped it at {g1_cap}. RA3 claims to restore that ladder "
            "and does not.",
        )

    def render(triples):
        return [[_plain(a), _plain(b), _plain(c)] for a, b, c in triples]

    return {
        "generation_1_protocol": GENERATION_1_PROTOCOL_PATH.name,
        "generation_1_ladder_from_ra1_5_prose": render(prose),
        "generation_1_ladder_rungs_per_experiment": {
            experiment_id: [[_plain(a), _plain(b)] for a, b in pairs]
            for experiment_id, pairs in sorted(per_experiment.items())
        },
        "generation_1_states_it_twice_and_they_agree": True,
        "ra3_bands_as_absolute_caps": render(ra3_bands),
        "exposure_ceiling_used_to_convert": _plain(architecture.exposure_ceiling),
        "ladders_are_identical": True,
    }


def check_single_difference_from_ra2(architecture: RiskArchitecture) -> dict[str, object]:
    """Recompute "RA3 differs from RA2 in exactly one place" against RA2's own sealed bands.

    Set difference, not narrative. RA2's four rungs minus RA3's three must leave exactly the deleted
    tier, and RA3's three minus RA2's four must leave exactly the widened full-sizing band — which
    must itself be RA2's band 0 stretched to the deleted tier's upper bound, at RA2's band 0 scalar.
    Every rung at or below the deleted tier must be untouched.
    """
    if not ATTEMPT_2_PROTOCOL_PATH.is_file():
        raise ConfigViolation(
            f"Attempt 2's sealed protocol is missing at {ATTEMPT_2_PROTOCOL_PATH}; the "
            "single-difference claim cannot be checked and must not be asserted"
        )
    attempt_2 = json.loads(ATTEMPT_2_PROTOCOL_PATH.read_text(encoding="utf-8"))
    ra2_bands = _bands_of(attempt_2["risk_architecture"], "RA2-4")

    def triples(bands):
        return [(b.dd_from, b.dd_to_exclusive, b.scalar) for b in bands]

    ra2_triples = triples(ra2_bands)
    ra3_triples = triples(architecture.bands)
    removed = [t for t in ra2_triples if t not in ra3_triples]
    added = [t for t in ra3_triples if t not in ra2_triples]

    _require(
        len(removed) == 2 and len(added) == 1,
        f"RA3 removes {len(removed)} RA2 rungs and adds {len(added)}; the sealed claim is that it "
        "deletes one tier and widens the band above it, which is exactly two removals and one "
        "addition",
    )
    deleted = removed[1]
    _require(
        deleted == DELETED_RA2_TIER,
        f"the RA2 rung RA3 deletes is {deleted}, not the sealed {DELETED_RA2_TIER}",
    )
    _require(
        added[0] == (ra2_triples[0][0], deleted[1], ra2_triples[0][2]),
        f"RA3's widened full-sizing band {added[0]} is not RA2's band 0 extended to the deleted "
        f"tier's upper bound at RA2's own scalar",
    )
    tail_ra2 = [t for t in ra2_triples if t[0] >= deleted[1]]
    tail_ra3 = [t for t in ra3_triples if t[0] >= deleted[1]]
    _require(
        tail_ra2 == tail_ra3,
        f"the rungs at or beyond the deleted tier differ: RA2 {tail_ra2}, RA3 {tail_ra3}. The "
        "sealed claim is that only the shallow end changed.",
    )

    def render(items):
        return [
            [f"{lo:f}", None if hi is None else f"{hi:f}", f"{scalar:f}"] for lo, hi, scalar in items
        ]

    return {
        "attempt_2_protocol": ATTEMPT_2_PROTOCOL_PATH.name,
        "ra2_bands": render(ra2_triples),
        "ra3_bands": render(ra3_triples),
        "bands_removed_from_ra2": render(removed),
        "bands_added_by_ra3": render(added),
        "deleted_tier": render([deleted])[0],
        "bands_at_or_beyond_the_deleted_tier_unchanged": True,
    }


def attributes_derived_from_risk(cls: type = RotationEngineRA1) -> frozenset[str]:
    """Every ``self.X`` in ``cls.__init__`` whose assignment depends on ``self.risk``.

    The point of ``RotationEngineRA3`` is that overriding two attributes is sufficient. That is a
    claim about a frozen base class, and a claim about code is checkable by reading the code. This
    reads it — with :mod:`ast`, so a comment mentioning ``self.risk`` does not count and a genuine
    dependency buried in a comprehension does.

    ``self.risk`` itself is included: it is the root of the dependency, assigned from the loader
    rather than from itself, so a search for *dependents* alone would miss it.

    All three assignment nodes are walked, not just :class:`ast.Assign`. The base class writes
    ``self.sessions_in_band: dict[int, int] = {...}`` with an annotation, which is an
    :class:`ast.AnnAssign`; a walker that handled only bare assignment would have missed the very
    attribute this check exists to find, and would have reported a smaller derived set as fact.
    """
    source = inspect.getsource(cls.__init__)
    tree = ast.parse(_dedent(source))

    derived: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            targets, value = [node.target], node.value
        else:
            continue
        if value is None:  # a bare `self.x: T` annotation binds nothing
            continue
        attributes = {
            target.attr
            for target in targets
            if isinstance(target, ast.Attribute)
            and isinstance(target.value, ast.Name)
            and target.value.id == "self"
        }
        if not attributes:
            continue
        reads_risk = any(
            isinstance(inner, ast.Attribute)
            and inner.attr == "risk"
            and isinstance(inner.value, ast.Name)
            and inner.value.id == "self"
            for inner in ast.walk(value)
        )
        if reads_risk or "risk" in attributes:
            derived |= attributes
    return frozenset(derived)


def _dedent(source: str) -> str:
    """``inspect.getsource`` of a method keeps its class indentation, which :mod:`ast` rejects."""
    lines = source.splitlines()
    pad = min((len(line) - len(line.lstrip()) for line in lines if line.strip()), default=0)
    return "\n".join(line[pad:] if len(line) >= pad else line for line in lines) + "\n"


_MEASURED = attributes_derived_from_risk()
if _MEASURED != RISK_DERIVED_ATTRIBUTES:
    raise ConfigViolation(
        "RotationEngineRA1.__init__ derives "
        f"{sorted(_MEASURED)} from the risk architecture; RotationEngineRA3 re-derives "
        f"{sorted(RISK_DERIVED_ATTRIBUTES)}. The two must agree exactly, or a variant runs with an "
        "RA2-shaped attribute under an RA3 ladder. G2A3-CONFLICT-31."
    )


class RotationEngineRA3(RotationEngineRA1):
    """The Attempt 1 rotation engine under RA3.

    Overrides no method. The only difference from Attempt 2 is the ladder band table, and it is
    installed by re-deriving the two attributes ``RotationEngineRA1.__init__`` computes from the
    architecture. Everything else — the exposure ceiling, the volatility target, the stop, the
    lockout, the transition rule, the shutdown, every counter and the risk-state digest — is
    Attempt 2's code running unmodified.
    """

    def __init__(
        self,
        series: dict[str, PriceSeries],
        cost_model: CostModel,
        window: ResearchWindow,
        probe: Probe,
        *,
        start: dt.date | None = None,
        end: dt.date | None = None,
        label: str = "",
        enforce_research_shutdown: bool = True,
        budget_weight: Decimal | None = None,
    ) -> None:
        super().__init__(
            series,
            cost_model,
            window,
            probe,
            start=start,
            end=end,
            label=label,
            enforce_research_shutdown=enforce_research_shutdown,
            budget_weight=budget_weight,
        )

        # The one substitution. `super().__init__` has just loaded RA2 and keyed `sessions_in_band`
        # by RA2's four bands; both are replaced here, and the import-time AST assertion above is
        # what makes "both" mean "all of them".
        self.risk = load_risk_architecture_ra3()
        self.sessions_in_band = {band.band: 0 for band in self.risk.bands}

        if self._band != 0 or self.deepest_band != 0:
            raise ConfigViolation(
                f"the base engine started at ladder band {self._band} (deepest {self.deepest_band}); "
                "RA3 substitutes its band table before any session runs and cannot correct a band "
                "index that already refers to RA2's ladder"
            )

        self.generation_1_provenance = check_generation_1_provenance(self.risk)
        self.single_difference_from_ra2 = check_single_difference_from_ra2(self.risk)

    def risk_summary(self) -> dict[str, object]:
        """Attempt 2's risk evidence, plus the two provenance recomputations RA3 owes the report."""
        summary = super().risk_summary()
        summary["architecture_provenance"] = {
            "generation_1_ladder_restored": self.generation_1_provenance,
            "single_difference_from_ra2": self.single_difference_from_ra2,
        }
        return summary
