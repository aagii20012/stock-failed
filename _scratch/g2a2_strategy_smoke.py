"""Adversarial smoke for ``strategies/g2_rotation_ra1.py``, Attempt 2's candidate.

Run before anything imports the module for real. It lives in ``src/``, which is a ``repo_state_id``
pattern, so a defect found after the decision package is built cannot be repaired without
invalidating the digest that package recorded.

What this harness refuses to do is confirm the module against itself. Every expected value below is
either read out of the sealed protocol on disk, derived from Attempt 1's own module, or computed here
from first principles -- never copied from ``g2_rotation_ra1.py``. A check whose expectation came from
the code under test proves only that the code equals itself.

ASCII output only: the console is cp1252 and a single arrow character kills the sweep mid-run.
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys
from decimal import Decimal

ROOT = pathlib.Path(__file__).resolve().parents[1] / "stockedge100"
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.backtest.costs import BASE, STRESSED, round_down_cent  # noqa: E402
from stockedge100.backtest.errors import ConfigViolation, InvariantViolation  # noqa: E402
from stockedge100.backtest.g2_costs import concentration_ceiling, rotation_cost_model  # noqa: E402
from stockedge100.backtest.orders import BUY, SELL  # noqa: E402
from stockedge100.strategies import g2_rotation as A1  # noqa: E402
from stockedge100.strategies import g2_rotation_ra1 as S  # noqa: E402

FAILED = 0
PASSED = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global FAILED, PASSED
    if ok:
        PASSED += 1
        print("  ok   %s%s" % (label, ("  [%s]" % detail) if detail else ""))
    else:
        FAILED += 1
        print("  FAIL %s  <- %s" % (label, detail or "predicate false"))


SEAL = json.loads((ROOT / "config" / "generation_2" / "g2_rotation_ra1_protocol.json").read_text(
    encoding="utf-8"))
UNIVERSE_FILE = json.loads((ROOT / "governance" / "STAGE_1_UNIVERSE.json").read_text(
    encoding="utf-8"))


print("=== 1. the module reads the seal, and the seal is the one it claims ===")
protocol = S.load_protocol()
check("load_protocol returns the sealed artifact", protocol["artifact_id"] == SEAL["artifact_id"],
      SEAL["artifact_id"])
check("STRATEGY_ID is the seal's, not a literal", S.STRATEGY_ID == SEAL["strategy_id"],
      SEAL["strategy_id"])
check("it is Attempt 2's strategy id, not Attempt 1's", S.STRATEGY_ID != A1.STRATEGY_ID,
      "%s vs %s" % (S.STRATEGY_ID, A1.STRATEGY_ID))
check("FAMILY is the seal's", S.FAMILY == SEAL["family"], SEAL["family"])
check("the family extends Attempt 1's rather than replacing it",
      S.FAMILY.startswith(A1.RotationCandidate.family) and S.FAMILY != A1.RotationCandidate.family,
      "%s -> %s" % (A1.RotationCandidate.family, S.FAMILY))
check("load_protocol is cached, so the file is read once", S.load_protocol() is protocol)


print()
print("=== 2. the universe is Stage 1's, checked against the frozen artifact ===")
universe = S.eligible_universe()
check("34 members", len(universe) == 34, str(len(universe)))
check("sorted and unique", list(universe) == sorted(set(universe)))
check("identical to the frozen STAGE_1_UNIVERSE.json member list",
      list(universe) == sorted(UNIVERSE_FILE["members"]))
check("identical to Attempt 1's universe -- nothing added, dropped or substituted",
      universe == A1.eligible_universe())
check("AAPL is excluded, as the seal records",
      "AAPL" not in universe and "AAPL" in SEAL["eligible_universe"]["excluded_symbols"])
check("the frozen artifact's identity digest is carried, not invented",
      SEAL["eligible_universe"]["universe_identity_sha256"]
      == UNIVERSE_FILE["universe_identity_sha256"],
      UNIVERSE_FILE["universe_identity_sha256"][:16] + "...")


print()
print("=== 3. w(k) derives from RA2-1's ceiling and agrees with the seal ===")
ceiling = S.load_risk_architecture().exposure_ceiling
check("the ceiling is read from the risk architecture", ceiling == Decimal("0.50"), str(ceiling))
# An earlier draft of this check read SEAL["risk_architecture"]["constants"], which does not exist --
# the block is keyed "components" -- and guarded itself with an isinstance() that fell through to
# True. It reported ok having compared nothing. Locate the component by its declared id, assert the
# lookup found something, and only then compare.
COMPONENTS = SEAL["risk_architecture"]["components"]
check("the risk architecture block is RA2's", SEAL["risk_architecture"]["id"] == "RA2"
      and len(COMPONENTS) == 5, "%s, %d components" % (SEAL["risk_architecture"]["id"],
                                                       len(COMPONENTS)))
ra2_1 = [c for c in COMPONENTS.values() if c["name"] == "aggregate_exposure_ceiling"]
check("RA2-1 is present exactly once in the seal", len(ra2_1) == 1)
check("the ceiling the module sizes against is RA2-1's declared value",
      ceiling == Decimal(ra2_1[0]["value"]) and ra2_1[0]["unit"] == "fraction of equity",
      "%s %s" % (ra2_1[0]["value"], ra2_1[0]["unit"]))
check("and it is strictly tighter than the constitutional gross ceiling Attempt 1 used",
      ceiling < rotation_cost_model(1, BASE).max_gross_exposure_fraction,
      "%s < %s" % (ceiling, rotation_cost_model(1, BASE).max_gross_exposure_fraction))

for k, expected_weight, expected_gross in ((1, "0.500000000", "0.500000000"),
                                           (2, "0.250000000", "0.500000000"),
                                           (3, "0.166666666", "0.499999998")):
    for scenario in (BASE, STRESSED):
        costs = rotation_cost_model(k, scenario)
        w = S.target_weight(k, costs)
        # computed here, not read from the module: min(A/k, C) truncated at nine places
        want = min(ceiling / k, concentration_ceiling()).quantize(Decimal("1E-9"),
                                                                 rounding="ROUND_DOWN")
        check("w(%d) under %s derives independently to %s" % (k, scenario, expected_weight),
              w == want == Decimal(expected_weight), "%f" % w)
        check("w(%d) x %d = %s does not exceed the ceiling under %s"
              % (k, k, expected_gross, scenario), k * w == Decimal(expected_gross) <= ceiling,
              "%f" % (k * w))
    check("w(%d) matches the seal's declared target_weights" % k,
          Decimal(SEAL["position_sizing"]["target_weights"][str(k)]) == Decimal(expected_weight))
    check("w(%d) matches the seal's declared target_gross_exposure" % k,
          Decimal(SEAL["position_sizing"]["target_gross_exposure"][str(k)])
          == Decimal(expected_gross))

check("k=3 is deliberately one ulp short of a third",
      Decimal("0.500000000") - 3 * S.target_weight(3, rotation_cost_model(3, BASE))
      == Decimal("0.000000002"),
      "shortfall 2e-9")


print()
print("=== 4. the sizing check is not vacuous: it refuses a seal that disagrees ===")


def rejects_weight(label: str, mutate) -> None:
    payload = json.loads(json.dumps(protocol))
    mutate(payload)
    real = S.load_protocol
    S.load_protocol = lambda: payload  # type: ignore[assignment]
    try:
        S.target_weight(2, rotation_cost_model(2, BASE))
    except (ConfigViolation, InvariantViolation, KeyError) as exc:
        check("rejects: %s" % label, True, type(exc).__name__)
    else:
        check("rejects: %s" % label, False, "sized against a seal it should have refused")
    finally:
        S.load_protocol = real  # type: ignore[assignment]


rejects_weight("a declared weight that disagrees with the derivation",
               lambda p: p["position_sizing"]["target_weights"].__setitem__("2", "0.300000000"))
rejects_weight("a declared gross that disagrees with k * w",
               lambda p: p["position_sizing"]["target_gross_exposure"].__setitem__("2", "0.9"))
rejects_weight("a formula that no longer says ROUND_DOWN",
               lambda p: p["position_sizing"].__setitem__(
                   "target_weight_formula",
                   p["position_sizing"]["target_weight_formula"].replace("ROUND_DOWN", "ROUND_UP")))
rejects_weight("a formula that no longer quantizes to nine places",
               lambda p: p["position_sizing"].__setitem__(
                   "target_weight_formula",
                   p["position_sizing"]["target_weight_formula"].replace("nine", "four")))
rejects_weight("a seal that stopped recording the sizing change from Attempt 1",
               lambda p: p["position_sizing"].__setitem__("changed_from_attempt_1", False))
rejects_weight("a missing weight for this k",
               lambda p: p["position_sizing"]["target_weights"].pop("2"))
check("and the unperturbed derivation still works",
      S.target_weight(2, rotation_cost_model(2, BASE)) == Decimal("0.250000000"))


print()
print("=== 5. the protocol validators are not vacuous either ===")


def rejects_protocol(label: str, mutate) -> None:
    payload = json.loads(json.dumps(protocol))
    mutate(payload)
    for verifier in (S._verify_universe, S._verify_family, S._verify_order_kinds,
                     S._verify_rebalance):
        try:
            verifier(payload)
        except (ConfigViolation, InvariantViolation, KeyError, IndexError) as exc:
            check("rejects: %s" % label, True, "%s in %s" % (type(exc).__name__, verifier.__name__))
            return
    check("rejects: %s" % label, False, "every verifier accepted it")


rejects_protocol("a member list that drifted from the frozen artifact",
                 lambda p: p["eligible_universe"]["members"].append("AAPL"))
rejects_protocol("a member count that disagrees with the list",
                 lambda p: p["eligible_universe"].__setitem__("member_count", 33))
rejects_protocol("a source digest that does not match the file on disk",
                 lambda p: p["eligible_universe"].__setitem__("source_sha256", "0" * 64))
rejects_protocol("a universe version that drifted",
                 lambda p: p["eligible_universe"].__setitem__("universe_version", "SE100-U1-dead"))
rejects_protocol("a universe identity digest that drifted",
                 lambda p: p["eligible_universe"].__setitem__("universe_identity_sha256", "f" * 64))
rejects_protocol("a universe no longer claimed unchanged from Attempt 1",
                 lambda p: p["eligible_universe"].__setitem__("unchanged_from_attempt_1", False))
rejects_protocol("a different strategy family",
                 lambda p: p.__setitem__("family", "MEAN_REVERSION"))
rejects_protocol("an ENTRY tag that fires between rebalances",
                 lambda p: [e for e in p["execution"]["order_kinds_this_attempt_may_issue"]
                            if e["tag"] == "ENTRY"][0].__setitem__("when", "any session close"))
rejects_protocol("an EXIT tag that fires between rebalances",
                 lambda p: [e for e in p["execution"]["order_kinds_this_attempt_may_issue"]
                            if e["tag"] == "EXIT"][0].__setitem__("when", "any session close"))
rejects_protocol("an EXIT leg that carries a partial quantity",
                 lambda p: [e for e in p["execution"]["order_kinds_this_attempt_may_issue"]
                            if e["tag"] == "EXIT"][0].__setitem__("quantity", "half the position"))
rejects_protocol("an ENTRY that became a sale",
                 lambda p: [e for e in p["execution"]["order_kinds_this_attempt_may_issue"]
                            if e["tag"] == "ENTRY"][0].__setitem__("side", SELL))
rejects_protocol("a sixth order kind",
                 lambda p: p["execution"]["order_kinds_this_attempt_may_issue"].append(
                     {"tag": "HEDGE", "side": SELL, "when": "any", "quantity": "any"}))
rejects_protocol("a dropped order kind",
                 lambda p: p["execution"]["order_kinds_this_attempt_may_issue"].pop())
rejects_protocol("a SHUTDOWN leg this attempt claims to issue itself",
                 lambda p: [e for e in p["execution"]["order_kinds_this_attempt_may_issue"]
                            if e["tag"] == "SHUTDOWN"][0].pop("issued_by"))
rejects_protocol("a rebalance calendar no longer claimed unchanged",
                 lambda p: p["rebalance"].__setitem__("unchanged_from_attempt_1", False))
rejects_protocol("a third rebalance frequency",
                 lambda p: p["rebalance"]["values"].append("WEEKLY"))
rejects_protocol("a quarterly rule that changed its months",
                 lambda p: p["rebalance"].__setitem__(
                     "rule", p["rebalance"]["rule"].replace("January, April, July and October",
                                                            "February, May, August and November")))
check("and the unperturbed protocol still passes every verifier",
      all(v(json.loads(json.dumps(protocol))) is None for v in
          (S._verify_universe, S._verify_family, S._verify_order_kinds, S._verify_rebalance)))


print()
print("=== 6. the eighteen variants are rebuilt from the axes, not read through ===")
variants = S.rotation_variants()
check("eighteen", len(variants) == 18, str(len(variants)))
check("indices 1..18 in order", [v.index for v in variants] == list(range(1, 19)))
check("ids unique", len({v.variant_id for v in variants}) == 18)
declared_ids = [e["variant_id"] for e in SEAL["grid"]["variants"]]
check("ids and order match the seal exactly", [v.variant_id for v in variants] == declared_ids)
check("every id carries Attempt 2's strategy id",
      all(v.variant_id.startswith(S.STRATEGY_ID + "-") for v in variants))
check("no id is an Attempt 1 id", not any(v.variant_id.startswith(A1.STRATEGY_ID + "-")
                                          for v in variants))
check("lookback is zero-padded so L12 sorts after L03",
      sorted(v.variant_id for v in variants)[0].split("-L")[1].startswith("03"),
      sorted(v.variant_id for v in variants)[0].rsplit("-", 3)[-3])
check("the axes are the sealed three-by-three-by-two",
      sorted({v.lookback_months for v in variants}) == [3, 6, 12]
      and sorted({v.top_k for v in variants}) == [1, 2, 3]
      and sorted({v.frequency for v in variants}) == ["MONTHLY", "QUARTERLY"])
check("each parameter triple appears exactly once",
      len({(v.lookback_months, v.top_k, v.frequency) for v in variants}) == 18)
check("rebalance session counts are the sealed 157 / 53",
      {v.frequency: v.scheduled_rebalance_sessions for v in variants}
      == {"MONTHLY": 157, "QUARTERLY": 53})
check("every variant's weight is w(top_k)",
      all(v.target_weight == S.target_weight(v.top_k, rotation_cost_model(v.top_k, BASE))
          for v in variants))
check("rotation_variants is cached", S.rotation_variants() is variants)
check("variant_by_id round-trips", all(S.variant_by_id(v.variant_id) is v for v in variants))
try:
    S.variant_by_id(A1.rotation_variants()[0].variant_id)
except ConfigViolation:
    check("variant_by_id refuses an Attempt 1 id", True)
else:
    check("variant_by_id refuses an Attempt 1 id", False, "accepted it")
check("to_json round-trips against the seal",
      all(v.to_json() == e for v, e in zip(variants, SEAL["grid"]["variants"])))


print()
print("=== 7. the grid really is Attempt 1's, and the weights really are smaller ===")
agree = S.attempt_1_grid_agreement()
check("the seal declares the grid unchanged", agree["declared_unchanged"] is True)
check("and every axis independently agrees with Attempt 1's protocol",
      agree["all_axes_agree"] is True and len(agree["axes_agree"]) == 3, str(agree["axes_agree"]))
check("size agrees at eighteen", agree["size_agrees"] is True)
check("all eighteen parameter rows agree", agree["parameter_rows_agree"] is True)
check("only the ids differ, by construction",
      agree["ids_differ_by_construction"]["attempt_1"]
      != agree["ids_differ_by_construction"]["attempt_2"])

comp = S.attempt_1_weight_comparison()
check("three rows compared", len(comp["rows"]) == 3)
check("Attempt 2 never sizes larger than Attempt 1",
      all(Decimal(r["attempt_2_weight"]) <= Decimal(r["attempt_1_weight"]) for r in comp["rows"]))
check("they coincide only at k=1, where both hit the 0.50 concentration ceiling",
      comp["coincident_at"] == [1],
      str(comp["coincident_at"]))
# Attempt 1 sized against the constitutional 0.95 ceiling, so its k=2 and k=3 gross both land at
# 0.95 less the truncation residue -- 0.949999998 at k=3, not 0.95 exactly and not the 0.999999999 an
# earlier draft of this check expected, which was simply bad arithmetic (0.95/3 x 3, not 1/3 x 3).
check("Attempt 1's gross was 0.95 at k=2 and k=3; Attempt 2's is 0.50",
      [r["attempt_1_gross"] for r in comp["rows"][1:]] == ["0.950000000", "0.949999998"]
      and [r["attempt_2_gross"] for r in comp["rows"][1:]] == ["0.500000000", "0.499999998"],
      str([(r["attempt_1_gross"], r["attempt_2_gross"]) for r in comp["rows"]]))
check("so Attempt 2 halves the book at k=2 and k=3, and leaves k=1 alone",
      [Decimal(r["attempt_1_gross"]) - Decimal(r["attempt_2_gross"]) for r in comp["rows"]]
      == [Decimal("0"), Decimal("0.450000000"), Decimal("0.450000000")])
check("the comparison quotes both sealed formulas verbatim",
      comp["attempt_1_formula"] == SEAL["position_sizing"]["attempt_1_formula"]
      and comp["attempt_2_formula"] == SEAL["position_sizing"]["target_weight_formula"])


print()
print("=== 8. the candidate mirrors Attempt 1's state and inherits its decisions ===")
mirrored = S._attempt1_init_state()
check("Attempt 1's constructor state was read from source, non-empty", len(mirrored) >= 9,
      "%d attributes: %s" % (len(mirrored), ", ".join(sorted(mirrored))))
check("it includes the attributes the inherited decide/evidence reach",
      {"variant", "weight", "_previous_session", "_ranking_hash", "scheduled_rebalances",
       "executed_rebalances", "rebalances_blocked_by_shutdown", "exclusions",
       "selection_log"} <= mirrored)

cand = S.build_candidate(variants[0])
check("build_candidate returns Attempt 2's candidate",
      isinstance(cand, S.RotationCandidateRA1) and cand.experiment_id == S.STRATEGY_ID)
check("it is not an instance of Attempt 1's candidate class",
      not isinstance(cand, A1.RotationCandidate))
check("every mirrored attribute is actually set", not (mirrored - set(vars(cand))),
      str(sorted(mirrored - set(vars(cand)))))
check("the decision methods ARE Attempt 1's function objects, not copies",
      S.RotationCandidateRA1.decide is A1.RotationCandidate.decide
      and S.RotationCandidateRA1.rank is A1.RotationCandidate.rank)
check("total_return is Attempt 1's function object, called unmodified",
      S.total_return is A1.total_return)
check("the calendar is Attempt 1's too",
      A1.is_scheduled_rebalance(dt.date(2008, 7, 28), None, "QUARTERLY") is True)
check("the candidate carries the risk architecture id in its parameters",
      cand.parameters["risk_architecture_id"] == S.load_risk_architecture().architecture_id,
      cand.parameters["risk_architecture_id"])
check("the candidate's weight is the variant's", cand.weight == variants[0].target_weight,
      "%f" % cand.weight)

# variants[0] is k=1. w(1) = 0.50 under a k=2 cost model too -- neither ceiling in w(k) varies with
# the model's breadth -- so the weight check alone accepts the mismatch and the engine would then
# refuse legs the variant declared. Establish first that the weight really does agree, so that the
# refusal below is demonstrably the breadth guard doing the work and not the weight guard.
check("w(1) is the same under a k=2 cost model, so the weight guard cannot see the mismatch",
      S.target_weight(1, rotation_cost_model(2, BASE)) == variants[0].target_weight)
for wrong_k in (2, 3):
    try:
        S.RotationCandidateRA1(variants[0], rotation_cost_model(wrong_k, BASE))
    except ConfigViolation as exc:
        check("a k=1 variant handed a k=%d cost model is refused" % wrong_k, True,
              "max_open_risky_positions" in str(exc) and type(exc).__name__ or type(exc).__name__)
    else:
        check("a k=1 variant handed a k=%d cost model is refused" % wrong_k, False, "accepted")
check("and every variant built through build_candidate gets its own k's model",
      all(S.build_candidate(v).costs.max_open_risky_positions == v.top_k for v in variants))


print()
print("=== 9. the two order legs carry the sealed tags and the right shapes ===")


class Ctx:
    def __init__(self, equity: Decimal, session: dt.date, open_symbols=()):
        self.equity = equity
        self.session = session
        self.open_symbols = tuple(open_symbols)
        self.shutdown_active = False


k3 = S.build_candidate(S.variant_by_id(
    [v.variant_id for v in variants if v.top_k == 3][0]))
entry = k3.entry_order("SPY", Ctx(Decimal("100000.00"), dt.date(2010, 1, 4)))
check("ENTRY is a BUY tagged ENTRY", entry.side == BUY and entry.tag == "ENTRY", entry.tag)
check("ENTRY is budgeted, not sized", entry.budget is not None and entry.quantity is None)
check("the budget is w(3) x equity rounded down to the cent",
      entry.budget == round_down_cent(Decimal("0.166666666") * Decimal("100000.00"))
      == Decimal("16666.66"), "%f" % entry.budget)
check("the tag is NOT the experiment id, as Attempt 1's was",
      entry.tag != k3.experiment_id and A1.RotationCandidate.entry_order(
          k3, "SPY", Ctx(Decimal("100000.00"), dt.date(2010, 1, 4))).tag == k3.experiment_id)
exit_leg = k3.exit_order("SPY")
check("EXIT is a SELL tagged EXIT", exit_leg.side == SELL and exit_leg.tag == "EXIT", exit_leg.tag)
check("EXIT carries no quantity, so the engine's merger will accept it",
      exit_leg.quantity is None and exit_leg.budget is None)
check("three positions at w(3) request less than the RA2-1 ceiling of equity",
      3 * entry.budget <= Decimal("0.50") * Decimal("100000.00"),
      "%f vs 50000.00" % (3 * entry.budget))

ev = cand.evidence()
check("evidence carries Attempt 1's fields plus Attempt 2's",
      {"variant", "universe_size", "scheduled_rebalances", "executed_rebalances",
       "rebalances_blocked_by_shutdown", "exclusion_events", "excluded_symbols", "ranking_digest",
       "distinct_symbols_targeted", "risk_architecture", "target_weight_per_position",
       "order_tags_issued"} <= set(ev), str(sorted(ev)))
check("evidence's order tags are exactly the two this candidate issues",
      ev["order_tags_issued"] == ["ENTRY", "EXIT"])
check("evidence's risk architecture is the sealed one",
      ev["risk_architecture"]["architecture_id"] == S.load_risk_architecture().architecture_id)
check("the ranking digest of an unused candidate is the empty-input digest",
      ev["ranking_digest"] == __import__("hashlib").sha256().hexdigest())


print()
print("=== 10. nothing Attempt 1 owns was perturbed ===")
check("Attempt 1's strategy id is untouched", A1.STRATEGY_ID == "SE100-G2-S3-C1-ROTATION")
check("Attempt 1 still sizes at 0.95/k",
      A1.target_weight(2, rotation_cost_model(2, BASE)) == Decimal("0.475000000"),
      "%f" % A1.target_weight(2, rotation_cost_model(2, BASE)))
check("Attempt 1's eighteen variants still build", len(A1.rotation_variants()) == 18)
a1_cand = A1.RotationCandidate(A1.rotation_variants()[0], rotation_cost_model(1, BASE))
check("an Attempt 1 candidate still tags with its experiment id",
      a1_cand.entry_order("SPY", Ctx(Decimal("1000"), dt.date(2010, 1, 4))).tag == A1.STRATEGY_ID)
check("Attempt 1's family is unchanged",
      A1.RotationCandidate.family == "CROSS_SECTIONAL_RELATIVE_STRENGTH")
check("the two protocols are different files",
      S.PROTOCOL_PATH != A1.PROTOCOL_PATH and S.PROTOCOL_ID != A1.PROTOCOL_ID,
      "%s vs %s" % (S.PROTOCOL_ID, A1.PROTOCOL_ID))


print()
print("=" * 78)
print("SMOKE %s -- %d passed, %d failed" % ("CLEAN" if not FAILED else "DIRTY", PASSED, FAILED))
raise SystemExit(1 if FAILED else 0)
