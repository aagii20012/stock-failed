"""Pre-seal checks on config/generation_2/g2_rotation_ra1_protocol.json.

ASCII output only: the console is cp1252 and the disclosure string carries em dashes,
so this script compares strings and prints booleans, never the strings themselves.
"""
from __future__ import annotations

import json
import pathlib
import sys
from decimal import ROUND_DOWN, Decimal, localcontext

ROOT = pathlib.Path(__file__).resolve().parents[1] / "stockedge100"
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.backtest.costs import ENGINE_CONTEXT  # noqa: E402
from stockedge100.backtest.config import dec  # noqa: E402

CFG = ROOT / "config" / "generation_2" / "g2_rotation_ra1_protocol.json"
A1 = ROOT / "config" / "generation_2" / "g2_rotation_protocol.json"

# The operating prompt's text, retyped here independently of the config file so that
# equality is evidence rather than a tautology.
EXPECTED_DISCLOSURE = (
    "This pre-registration was designed after Attempt 1's development results were known. "
    "All eighteen Attempt 1 variants recorded at least one research-shutdown event, "
    "clustered at 2008-10 through 2011-10 (thirteen of eighteen), with additional single "
    "occurrences in mid-2010, January 2016, and March 2020 — periods of acute market "
    "stress that an unconstrained rotation strategy had no mechanism to survive. Attempt 2 "
    "adds risk architecture explicitly informed by this observation. The development window "
    "is no longer pristine for this hypothesis family. This adaptation increases researcher "
    "degrees of freedom and cumulative multiplicity across both attempts. No successful "
    "development result from Attempt 2 can, by itself, establish a trading edge — this "
    "mirrors exactly the disclosure Generation 1 made between its own Attempt 1 and Attempt 2."
)

fails: list[str] = []
ran: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print("%-4s %s%s" % ("OK" if ok else "FAIL", label, ("  " + detail) if detail else ""))
    ran.append(label)
    if not ok:
        fails.append(label)


body = json.loads(CFG.read_text(encoding="utf-8"))
a1 = json.loads(A1.read_text(encoding="utf-8"))

check("json parses", True, "%d top-level keys" % len(body))

# --- the verbatim disclosure -------------------------------------------------
got = body["adaptation_disclosure_verbatim"]
check("disclosure byte-identical to source", got == EXPECTED_DISCLOSURE,
      "len=%d expected=%d" % (len(got), len(EXPECTED_DISCLOSURE)))
check("disclosure carries 2 em dashes", got.count("—") == 2,
      "count=%d" % got.count("—"))
check("disclosure names Attempt 1 result", "no longer pristine" in got)

# --- target weights: recompute, do not trust the table -----------------------
CEILING = dec("0.50")
QUANTUM = Decimal("0.000000001")
declared = body["position_sizing"]["target_weights"]
gross_declared = body["position_sizing"]["target_gross_exposure"]
with localcontext(ENGINE_CONTEXT):
    for k in (1, 2, 3):
        w = min(CEILING / k, CEILING).quantize(QUANTUM, rounding=ROUND_DOWN)
        g = w * k
        check("w(%d) recomputed" % k, str(w) == declared[str(k)],
              "computed=%s declared=%s" % (w, declared[str(k)]))
        check("gross(%d) recomputed" % k, str(g) == gross_declared[str(k)],
              "computed=%s declared=%s" % (g, gross_declared[str(k)]))
        check("gross(%d) <= ceiling" % k, g <= CEILING, "%s <= %s" % (g, CEILING))
        # At k=1, min(A/k, C) with A == C == 0.50 is the SAME number under both attempts;
        # only k=2 and k=3 move. Asserting "all three differ" would be false and was.
        a1w = a1["position_sizing"]["target_weights"][str(k)]
        if k == 1:
            check("w(1) unchanged from Attempt 1 (A == C binds identically)",
                  declared["1"] == a1w, "a1=%s a2=%s" % (a1w, declared["1"]))
        else:
            check("w(%d) strictly below Attempt 1" % k, Decimal(declared[str(k)]) < Decimal(a1w),
                  "a1=%s a2=%s" % (a1w, declared[str(k)]))

# The claim the config makes in attempt_1_k1_half_cash_bias_neutralised: Attempt 1's
# gross exposure was NOT uniform across k, Attempt 2's is. Check both halves.
a1g = [a1["position_sizing"]["target_gross_exposure"][str(k)] for k in (1, 2, 3)]
a2g = [gross_declared[str(k)] for k in (1, 2, 3)]
check("Attempt 1 gross was non-uniform across k", len(set(a1g)) > 1, "a1=%s" % a1g)
check("Attempt 2 gross is uniform to within one ulp",
      max(Decimal(x) for x in a2g) - min(Decimal(x) for x in a2g) == Decimal("0.000000002"),
      "a2=%s" % a2g)

# --- grid ---------------------------------------------------------------------
variants = body["grid"]["variants"]
check("grid size 18", len(variants) == 18 == body["grid"]["size"], "n=%d" % len(variants))
check("indices 1..18 in order", [v["index"] for v in variants] == list(range(1, 19)))
check("variant ids unique", len({v["variant_id"] for v in variants}) == 18)

rebuilt = []
for lb in body["grid"]["axes"]["lookback_months"]:
    for k in body["grid"]["axes"]["top_k"]:
        for f in body["grid"]["axes"]["rebalance_frequency"]:
            rebuilt.append("SE100-G2-S3-C2-ROTATION-RA1-L%02d-K%d-%s" % (lb, k, f))
check("grid rebuilt from axes matches", rebuilt == [v["variant_id"] for v in variants])

check("each variant weight matches the k table",
      all(v["target_weight_per_position"] == declared[str(v["top_k"])] for v in variants))
check("rebalance session counts consistent",
      all(v["scheduled_rebalance_sessions"] == (157 if v["rebalance_frequency"] == "MONTHLY" else 53)
          for v in variants))

# lexicographic tiebreak must not be defeated by zero-padding
ids = [v["variant_id"] for v in variants]
check("L03 sorts before L12 lexicographically",
      sorted(ids).index([i for i in ids if "-L03-K1-MONTHLY" in i][0])
      < sorted(ids).index([i for i in ids if "-L12-K1-MONTHLY" in i][0]))

# --- candidate id must be C2, and must not collide with Attempt 1 -------------
sid = body["strategy_id"]
check("strategy id is C2", sid == "SE100-G2-S3-C2-ROTATION-RA1", sid)
check("strategy id differs from Attempt 1", sid != a1["strategy_id"], "a1=%s" % a1["strategy_id"])
check("no variant id collides with Attempt 1's",
      not ({v["variant_id"] for v in variants} & {v["variant_id"] for v in a1["grid"]["variants"]}))

# --- pinned digests must actually match what is on disk -----------------------
import hashlib  # noqa: E402


def sha(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


pins = {
    "config/generation_2/g2_rotation_protocol.json": body["attempt_1_ref"]["protocol_config_sha256"],
    "config/generation_2/g2_gate_criteria.json": body["attempt_1_ref"]["gate_criteria_config_sha256"],
    "governance/generation_2/STAGE_3_G2_ROTATION_PROTOCOL.md": body["attempt_1_ref"]["protocol_md_sha256"],
    "governance/generation_2/STAGE_3_G2_ROTATION_PROTOCOL.json": body["attempt_1_ref"]["protocol_json_sha256"],
    "governance/generation_2/STAGE_3_G2_ROTATION_PROTOCOL.sha256": body["attempt_1_ref"]["protocol_sha256_record_sha256"],
    "governance/generation_2/STAGE_3_G2_ROTATION_RESEARCH_REPORT.md": body["attempt_1_ref"]["research_report_md_sha256"],
    "reports/stage3_g2/STAGE_3_G2_ROTATION_RESEARCH.json": body["attempt_1_ref"]["research_json_sha256"],
    "reports/stage3_g2/STAGE_3_G2_DEVELOPMENT_ADMISSIBILITY.json": body["attempt_1_ref"]["decision_json_sha256"],
    "reports/stage3_g2/STAGE_3_G2_ARTIFACT_MANIFEST.json": body["attempt_1_ref"]["manifest_json_sha256"],
    "governance/STAGE_0_CONSTITUTION.md": body["constitution_md_sha256"],
    "governance/STAGE_0_CONSTITUTION.json": body["constitution_json_sha256"],
    "governance/generation_2/STAGE_1_G2_PARTITION_LOCK.md": body["partition_lock_md_sha256"],
    "governance/generation_2/STAGE_1_G2_PARTITION_LOCK.json": body["partition_lock_json_sha256"],
    "governance/generation_2/STAGE_10_GENERATION_2_CHARTER.md": body["charter_md_sha256"],
    "config/generation_2/g2_cost_model.json": body["cost_model_derivation_sha256"],
    "governance/STAGE_1_UNIVERSE.json": body["eligible_universe"]["source_sha256"],
    "config/stage3_attempt2_strategy_protocol.json": body["concentration_ceiling"]["source_sha256"],
}
check("pin count", len(pins) == 17, "n=%d" % len(pins))
for rel, pinned in sorted(pins.items()):
    actual = sha(rel)
    check("pin %s" % rel, actual == pinned, "" if actual == pinned else "disk=%s pinned=%s" % (actual, pinned))

# --- universe ------------------------------------------------------------------
uni = json.loads((ROOT / "governance" / "STAGE_1_UNIVERSE.json").read_text(encoding="utf-8"))
check("universe_version matches disk",
      body["eligible_universe"]["universe_version"] == uni["universe_version"])
check("universe_identity_sha256 matches disk",
      body["eligible_universe"]["universe_identity_sha256"] == uni["universe_identity_sha256"])
check("member count 34", len(body["eligible_universe"]["members"]) == 34)
check("members match Attempt 1 exactly",
      body["eligible_universe"]["members"] == a1["eligible_universe"]["members"])
check("members sorted", body["eligible_universe"]["members"] == sorted(body["eligible_universe"]["members"]))
check("AAPL not a member", "AAPL" not in body["eligible_universe"]["members"])

# --- risk architecture constants must be exactly the prompt's -----------------
ra = body["risk_architecture"]["components"]
check("RA2-1 ceiling 0.50", ra["RA2-1"]["value"] == "0.50")
check("RA2-2 vol target 0.10", ra["RA2-2"]["value"] == "0.10")
check("RA2-3 stop 0.08", ra["RA2-3"]["value"] == "0.08")
check("RA2-5 lockout 10", ra["RA2-5"]["value"] == 10)
bands = ra["RA2-4"]["bands"]
check("ladder 4 bands", len(bands) == 4)
check("ladder thresholds -5/-8/-10",
      [b["dd_from"] for b in bands] == ["0.00", "0.05", "0.08", "0.10"])
check("ladder scalars 100/75/50/25",
      [b["scalar"] for b in bands] == ["1.00", "0.75", "0.50", "0.25"])
check("ladder bands contiguous",
      all(bands[i]["dd_to_exclusive"] == bands[i + 1]["dd_from"] for i in range(3)))
check("deepest rung inside the 15% shutdown", Decimal(bands[3]["dd_from"]) < Decimal("0.15"))
check("risk constants not gridded", body["risk_architecture"]["not_part_of_the_grid"] is True)
check("risk constants frozen pre-run", body["risk_architecture"]["frozen_before_any_variant_is_run"] is True)

# --- conflicts ------------------------------------------------------------------
conflicts = body["conflicts_found"]
ids = [c["id"] for c in conflicts]
check("conflict ids unique", len(set(ids)) == len(ids), "n=%d" % len(ids))
check("conflict ids contiguous G2A2-CONFLICT-1..N",
      ids == ["G2A2-CONFLICT-%d" % i for i in range(1, len(ids) + 1)], "n=%d" % len(ids))
check("conflict prefix does not overload Attempt 1's series",
      all(not i.startswith("G2-CONFLICT-") for i in ids))
check("every conflict has a resolution", all(c.get("resolution") for c in conflicts))

# --- posture --------------------------------------------------------------------
check("live_trading_authorized false", body["live_trading_authorized"] is False)
check("declared_before_any_strategy_code true", body["declared_before_any_strategy_code"] is True)
check("contamination predicate is content-based",
      body["declared_before_any_strategy_code_measurement"]["contamination_predicate"] == "CONTENT_BASED")
check("holdout windows declared prohibited",
      {w["from"] for w in body["window"]["prohibited"]} == {"2021-08-01", "2024-08-01", "2026-08-01"})
check("no non-authorization list is empty", len(body["explicit_non_authorizations"]) >= 10,
      "n=%d" % len(body["explicit_non_authorizations"]))
check("gate criteria ref points at the RA1 file",
      body["gate_criteria_ref"] == "config/generation_2/g2_gate_criteria_ra1.json")

# --- this file must not carry a tree digest or its own ---------------------------
raw = CFG.read_text(encoding="utf-8")
own = hashlib.sha256(CFG.read_bytes()).hexdigest()
check("does not contain its own digest", own not in raw)
import re  # noqa: E402
hits = set(re.findall(r"\b[0-9a-f]{64}\b", raw))
unresolved = hits - set(pins.values()) - {uni["universe_identity_sha256"]}
check("every 64-hex string resolves to a pinned file",
      not unresolved, "hits=%d unresolved=%d" % (len(hits), len(unresolved)))
for u in sorted(unresolved):
    print("     unresolved: %s" % u)

print("\n%d checks, %d failed" % (len(ran), len(fails)))
if fails:
    print("FAILED: %s" % ", ".join(fails))
    sys.exit(1)
print("ALL CHECKS PASSED")
