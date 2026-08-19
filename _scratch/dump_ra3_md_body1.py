"""Narrative blocks CFG-3105 needs restated in sections 1 to 8 of the Attempt 3 Markdown."""

import json
import pathlib

proto = json.loads(
    pathlib.Path("config/generation_2/g2_rotation_ra3_protocol.json").read_text(encoding="utf-8"))


def show(label, obj):
    print("\n===== %s" % label)
    print(json.dumps(obj, indent=2, ensure_ascii=False).encode(
        "ascii", "backslashreplace").decode("ascii"))


for key in ("document", "strategy_id", "candidate_index", "attempt", "family",
            "live_trading_authorized", "declaration_note", "hypothesis",
            "candidate_index_note", "what_this_attempt_changes_from_attempt_2",
            "what_this_attempt_adds_over_attempt_1",
            "what_makes_this_genuinely_cross_sectional",
            "attempt_1_ref", "attempt_2_ref", "mechanics_carried_unchanged",
            "eligible_universe", "ranking_signal", "ranking_rule",
            "position_count", "position_sizing", "concentration_ceiling",
            "rebalance", "runs_per_variant", "execution", "window", "run_span"):
    show(key, proto.get(key, "<<ABSENT>>"))
