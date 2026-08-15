"""Generation 2's cost model is a derivation, and this is the test that makes that checkable.

The sealed ``adversarial_test_requirements`` in ``config/generation_2/g2_rotation_protocol.json``
lists, under ``additional``:

    "the derived cost model differs from the sealed Generation 1 model at exactly one JSON pointer"

The claim has two halves and both are tested here. The *positive* half is that
:func:`derive_mapping` really does produce a mapping whose difference set from Generation 1's sealed
model is exactly ``["/account/max_open_risky_positions"]`` — not "we only wrote one line, so surely
only one thing changed". The *negative* half is that the comparison would notice if a second
difference appeared: a difference-set walk that silently missed additions, removals, or a type
change would satisfy the positive half while proving nothing, so each of those is injected into
hand-built mappings and asserted to be caught.

Nothing here reads market data or writes outside ``tmp_path``. The tampered-declaration cases copy
``config/generation_2/g2_cost_model.json`` into ``tmp_path``, edit the copy, and redirect
``g2_costs.DECLARATION_PATH`` at it; the real declaration is opened read-only, and the ``lru_cache``
is cleared on both sides of every substitution so no tampered entry leaks into another test.

Digests are recomputed from disk rather than pasted as literals, so rewriting the sealed cost model
together with the declaration that names it still fails here.
"""

from __future__ import annotations

import copy as copy_module
import json
from decimal import Decimal

import pytest

from stockedge100.audit import sha256_file
from stockedge100.backtest import g2_costs
from stockedge100.backtest.config import PROJECT_ROOT, load_stage2_config
from stockedge100.backtest.costs import BASE, STRESSED, CostModel
from stockedge100.backtest.errors import ConfigViolation

# Hand-written, on purpose. These are the values the derivation is *supposed* to hold; reading them
# out of the declaration and asserting they equal themselves would test nothing.
OVERRIDE_POINTER = "/account/max_open_risky_positions"
SEALED_POSITION_COUNT = 1
PERMITTED_POSITION_COUNTS = (1, 2, 3)
CONCENTRATION_CEILING = Decimal("0.50")
SEALED_COST_MODEL_REL = "config/stage2_cost_model.json"


# -- clean controls ------------------------------------------------------------------------------
# Three of them, so that a failure further down is attributable to the injected defect rather than
# to a moved artifact underneath the whole file.


def test_the_declaration_loads_and_names_the_sealed_generation_1_cost_model():
    declaration = g2_costs.load_declaration()

    assert declaration["artifact_id"] == g2_costs.DECLARATION_ID == "SE100-CFG-2101"
    assert declaration["generation"] == 2
    assert declaration["no_other_field_may_differ"] is True
    assert declaration["live_trading_authorized"] is False
    assert declaration["derived_from"]["path"] == SEALED_COST_MODEL_REL

    # Recomputed, not pasted: the declaration and the file it names must agree on disk right now.
    assert declaration["derived_from"]["sha256"] == sha256_file(PROJECT_ROOT / SEALED_COST_MODEL_REL)


def test_the_declared_breadth_and_ceiling_are_what_generation_2_said_they_would_be():
    assert g2_costs.permitted_position_counts() == PERMITTED_POSITION_COUNTS
    assert g2_costs.concentration_ceiling() == CONCENTRATION_CEILING
    assert g2_costs.OVERRIDE_POINTER == OVERRIDE_POINTER
    assert g2_costs.SEALED_COST_MODEL_REL == SEALED_COST_MODEL_REL
    assert load_stage2_config().cost_model["account"]["max_open_risky_positions"] == SEALED_POSITION_COUNT


def test_a_derivation_at_k_2_changes_exactly_the_declared_pointer_and_nothing_else():
    sealed, derived, differences = g2_costs.derive_mapping(2)

    assert differences == [OVERRIDE_POINTER]
    assert derived["account"]["max_open_risky_positions"] == 2
    assert sealed["account"]["max_open_risky_positions"] == SEALED_POSITION_COUNT
    # The sealed mapping must not have been mutated in place by the derivation.
    assert g2_costs.flatten_pointers(sealed)[OVERRIDE_POINTER] == SEALED_POSITION_COUNT


# -- the positive half: exactly one pointer, at every declared k ------------------------------------


@pytest.mark.parametrize("k", PERMITTED_POSITION_COUNTS)
def test_every_permitted_position_count_differs_at_most_at_the_declared_pointer(k):
    sealed, derived, differences = g2_costs.derive_mapping(k)

    expected = [] if k == SEALED_POSITION_COUNT else [OVERRIDE_POINTER]
    assert differences == expected
    assert derived["account"]["max_open_risky_positions"] == k

    # Leaf counts equal means the override replaced a value; it did not add or drop a field.
    assert len(g2_costs.flatten_pointers(sealed)) == len(g2_costs.flatten_pointers(derived))


def test_k_equal_to_the_sealed_value_produces_no_difference_at_all():
    _, _, differences = g2_costs.derive_mapping(SEALED_POSITION_COUNT)
    assert differences == []


@pytest.mark.parametrize("k", PERMITTED_POSITION_COUNTS)
def test_the_derived_cost_model_object_differs_from_generation_1_only_in_breadth(k):
    """The pointer-level claim, restated at the level of the object the engine actually uses.

    A derivation could produce a one-pointer difference in the mapping and still hand the engine a
    ``CostModel`` that differs elsewhere — if, say, the scenario were quietly changed on the way
    through. Comparing the two constructed objects attribute by attribute closes that gap.
    """
    generation_1 = CostModel(load_stage2_config().cost_model, BASE)
    generation_2 = g2_costs.rotation_cost_model(k, BASE)

    left = {name: value for name, value in vars(generation_1).items() if name != "raw"}
    right = {name: value for name, value in vars(generation_2).items() if name != "raw"}
    assert set(left) == set(right)

    differing = {name for name in left if left[name] != right[name]}
    assert differing == (set() if k == SEALED_POSITION_COUNT else {"max_open_risky_positions"})
    assert generation_2.max_open_risky_positions == k


def test_the_stressed_scenario_scales_frictions_without_touching_breadth():
    base = g2_costs.rotation_cost_model(3, BASE)
    stressed = g2_costs.rotation_cost_model(3, STRESSED)

    assert stressed.max_open_risky_positions == base.max_open_risky_positions == 3
    assert stressed.half_spread_bps == base.half_spread_bps * 2
    assert stressed.slippage_bps == base.slippage_bps * 2
    assert stressed.sec_rate == base.sec_rate * 2
    assert stressed.taf_per_share == base.taf_per_share * 2
    # Breadth is not a friction, so the stress multiplier must not have reached it.
    assert stressed.max_gross_exposure_fraction == base.max_gross_exposure_fraction


def test_the_derivation_evidence_is_re_derivable_from_disk():
    evidence = g2_costs.derivation_evidence(3)

    assert evidence["difference_set"] == [OVERRIDE_POINTER]
    assert evidence["difference_set_size"] == 1
    assert evidence["sealed_leaf_count"] == evidence["derived_leaf_count"]
    assert evidence["sealed_value"] == SEALED_POSITION_COUNT
    assert evidence["generation_2_value"] == 3
    assert evidence["concentration_ceiling"] == "0.50"
    assert evidence["derived_from_sha256"] == sha256_file(PROJECT_ROOT / SEALED_COST_MODEL_REL)
    assert evidence["override_pointer"] == OVERRIDE_POINTER


# -- the negative half: the comparison would notice a second difference ---------------------------


def test_flatten_pointers_reaches_every_leaf_including_list_elements():
    flat = g2_costs.flatten_pointers({"a": {"b": 1}, "c": ["x", "y"], "d": None})

    assert flat == {"/a/b": 1, "/c/0": "x", "/c/1": "y", "/d": None}


def test_flatten_pointers_escapes_rfc_6901_reserved_characters():
    flat = g2_costs.flatten_pointers({"a/b": 1, "c~d": 2})

    assert flat == {"/a~1b": 1, "/c~0d": 2}


def test_an_identical_mapping_has_an_empty_difference_set():
    mapping = {"account": {"max_open_risky_positions": 1}, "frictions": {"bps": "2.5"}}

    assert g2_costs.difference_set(mapping, copy_module.deepcopy(mapping)) == []


@pytest.mark.parametrize(
    "case_id, sealed, derived, expected",
    [
        (
            "value_changed",
            {"account": {"k": 1}},
            {"account": {"k": 3}},
            ["/account/k"],
        ),
        (
            "field_added",
            {"account": {"k": 1}},
            {"account": {"k": 1}, "extra": {"nested": True}},
            ["/extra/nested"],
        ),
        (
            "field_removed",
            {"account": {"k": 1}, "risk": {"drawdown": "0.15"}},
            {"account": {"k": 1}},
            ["/risk/drawdown"],
        ),
        (
            "list_element_changed",
            {"stress_applies_to": ["a", "b"]},
            {"stress_applies_to": ["a", "c"]},
            ["/stress_applies_to/1"],
        ),
        (
            "list_shortened",
            {"stress_applies_to": ["a", "b"]},
            {"stress_applies_to": ["a"]},
            ["/stress_applies_to/1"],
        ),
        (
            "two_at_once_are_both_reported",
            {"account": {"k": 1}, "risk": {"drawdown": "0.15"}},
            {"account": {"k": 3}, "risk": {"drawdown": "0.25"}},
            ["/account/k", "/risk/drawdown"],
        ),
    ],
)
def test_the_difference_walk_reports_each_kind_of_divergence(case_id, sealed, derived, expected):
    assert g2_costs.difference_set(sealed, derived) == expected


def test_a_type_change_that_compares_equal_is_still_a_difference():
    """``True == 1`` in Python, and ``"0.15"`` is not ``0.15``.

    Without the explicit type comparison in :func:`difference_set`, a sealed integer silently
    becoming a boolean — or a decimal string becoming a float — would flatten to leaves that compare
    equal and the derivation would be certified as unchanged. This is the case that shows the type
    check is load-bearing rather than decorative.
    """
    assert g2_costs.difference_set({"k": 1}, {"k": True}) == ["/k"]
    assert g2_costs.difference_set({"k": 0}, {"k": False}) == ["/k"]
    # And the value comparison still does its own job for a same-typed change.
    assert g2_costs.difference_set({"bps": "2.5"}, {"bps": "5.0"}) == ["/bps"]


def test_a_second_difference_injected_into_the_derivation_is_refused(monkeypatch):
    """The guard, exercised through :func:`derive_mapping` rather than in isolation.

    ``derive_mapping`` deep-copies the sealed mapping before applying the override, so replacing the
    module's view of :mod:`copy` with a shim that adds one extra field is the narrowest way to make
    the derivation produce a mapping it should refuse. The shim patches the attribute on
    ``g2_costs``, not on the shared :mod:`copy` module, so nothing else in the process is affected.
    """

    class TamperingCopy:
        @staticmethod
        def deepcopy(node):
            mutated = copy_module.deepcopy(node)
            mutated["risk"]["research_shutdown_drawdown_fraction"] = "0.25"
            return mutated

    monkeypatch.setattr(g2_costs, "copy", TamperingCopy)

    with pytest.raises(ConfigViolation) as excinfo:
        g2_costs.derive_mapping(2)

    message = str(excinfo.value)
    assert "/risk/research_shutdown_drawdown_fraction" in message
    assert OVERRIDE_POINTER in message
    assert "permits exactly" in message


def test_a_derivation_that_silently_drops_a_field_is_refused(monkeypatch):
    class TruncatingCopy:
        @staticmethod
        def deepcopy(node):
            mutated = copy_module.deepcopy(node)
            del mutated["risk"]
            return mutated

    monkeypatch.setattr(g2_costs, "copy", TruncatingCopy)

    with pytest.raises(ConfigViolation) as excinfo:
        g2_costs.derive_mapping(3)

    assert "/risk/research_shutdown_drawdown_fraction" in str(excinfo.value)


# -- breadth and scenario are bounded by the declaration, not by the caller -------------------------


@pytest.mark.parametrize("k", [0, 4, 5, 18, -1])
def test_a_position_count_outside_the_declared_grid_is_refused(k):
    with pytest.raises(ConfigViolation, match="not one of the declared position counts"):
        g2_costs.derive_mapping(k)


@pytest.mark.parametrize("k", [0, 4])
def test_rotation_cost_model_refuses_the_same_counts(k):
    with pytest.raises(ConfigViolation, match="not one of the declared position counts"):
        g2_costs.rotation_cost_model(k)


@pytest.mark.parametrize("scenario", ["PAPER", "LIVE", "base", "", "STRESS"])
def test_an_undeclared_cost_scenario_is_refused(scenario):
    with pytest.raises(ConfigViolation, match="unknown cost scenario"):
        g2_costs.rotation_cost_model(2, scenario)


# -- the declaration itself is validated, not merely read ------------------------------------------


@pytest.fixture
def substituted_declaration(monkeypatch, tmp_path):
    """Redirect ``g2_costs.DECLARATION_PATH`` at an editable copy of the real declaration.

    The cache is cleared on both sides: before, so the substitution is actually loaded; after, so a
    tampered declaration cannot survive into the next test.
    """

    def substitute(mutate):
        declaration = json.loads(g2_costs.DECLARATION_PATH.read_text(encoding="utf-8"))
        mutate(declaration)
        path = tmp_path / "g2_cost_model.json"
        path.write_text(json.dumps(declaration, indent=2), encoding="utf-8")
        monkeypatch.setattr(g2_costs, "DECLARATION_PATH", path)
        g2_costs.load_declaration.cache_clear()
        return path

    g2_costs.load_declaration.cache_clear()
    yield substitute
    g2_costs.load_declaration.cache_clear()


def test_the_substitution_harness_itself_is_clean(substituted_declaration):
    """Control: an unmodified copy at a different path still loads and still derives."""
    substituted_declaration(lambda declaration: None)

    assert g2_costs.permitted_position_counts() == PERMITTED_POSITION_COUNTS
    assert g2_costs.derive_mapping(3)[2] == [OVERRIDE_POINTER]


def _set(path, value):
    def mutate(declaration):
        node = declaration
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = value

    return mutate


@pytest.mark.parametrize(
    "case_id, mutate, expected",
    [
        (
            "wrong_artifact_id",
            _set(["artifact_id"], "SE100-CFG-2999"),
            "declares artifact_id",
        ),
        (
            "wrong_generation",
            _set(["generation"], 1),
            "is not a Generation 2 artifact",
        ),
        (
            "predicate_withdrawn",
            _set(["no_other_field_may_differ"], False),
            "no longer asserts no_other_field_may_differ",
        ),
        (
            "live_trading_switched_on",
            _set(["live_trading_authorized"], True),
            "no longer records live_trading_authorized as false",
        ),
        (
            "override_pointer_moved",
            _set(["overrides", 0, "json_pointer"], "/frictions/half_spread_bps"),
            "declares overrides",
        ),
        (
            "expected_size_disagrees_with_the_override_list",
            _set(["difference_set_expected_size"], 2),
            "expects a difference set of",
        ),
        (
            "derived_from_a_different_file",
            _set(["derived_from", "path"], "config/stage3_gate_criteria.json"),
            "derives from",
        ),
        (
            "derived_from_a_digest_that_is_not_on_disk",
            _set(["derived_from", "sha256"], "0" * 64),
            "governance failure, not a value to update",
        ),
    ],
)
def test_a_tampered_declaration_is_refused(substituted_declaration, case_id, mutate, expected):
    substituted_declaration(mutate)

    with pytest.raises(ConfigViolation, match=expected):
        g2_costs.load_declaration()


def test_a_second_override_appended_to_the_declaration_is_refused(substituted_declaration):
    def mutate(declaration):
        extra = copy_module.deepcopy(declaration["overrides"][0])
        extra["json_pointer"] = "/frictions/stress_multiplier"
        declaration["overrides"].append(extra)
        declaration["difference_set_expected_size"] = 2

    substituted_declaration(mutate)

    with pytest.raises(ConfigViolation, match="this module implements exactly"):
        g2_costs.load_declaration()


def test_a_declaration_that_widens_the_permitted_breadth_widens_what_derive_mapping_accepts(
    substituted_declaration,
):
    """The permitted set is read from the declaration, not hard-coded — and this proves it.

    A hard-coded ``(1, 2, 3)`` inside the module would pass every test above while making the
    declaration decorative. Widening the declared list must widen the accepted set; the real,
    unsubstituted declaration is what keeps the grid at eighteen variants.
    """
    substituted_declaration(_set(["overrides", 0, "permitted_values"], [1, 2, 3, 4]))

    assert g2_costs.permitted_position_counts() == (1, 2, 3, 4)
    assert g2_costs.derive_mapping(4)[1]["account"]["max_open_risky_positions"] == 4


def test_a_declaration_whose_sealed_value_disagrees_with_the_sealed_file_is_refused(
    substituted_declaration,
):
    substituted_declaration(_set(["overrides", 0, "sealed_value"], 7))

    with pytest.raises(ConfigViolation, match="the derivation was declared against 7"):
        g2_costs.derive_mapping(2)


def test_a_missing_declaration_is_refused(monkeypatch, tmp_path):
    monkeypatch.setattr(g2_costs, "DECLARATION_PATH", tmp_path / "absent.json")
    g2_costs.load_declaration.cache_clear()
    try:
        with pytest.raises(ConfigViolation, match="Generation 2 cost derivation is missing"):
            g2_costs.load_declaration()
    finally:
        g2_costs.load_declaration.cache_clear()


def test_the_real_declaration_is_still_loadable_after_every_substitution():
    """Ordering guard: run last in file order, and assert the cache was not poisoned."""
    assert g2_costs.load_declaration()["artifact_id"] == g2_costs.DECLARATION_ID
    assert g2_costs.DECLARATION_PATH == PROJECT_ROOT / "config" / "generation_2" / "g2_cost_model.json"
