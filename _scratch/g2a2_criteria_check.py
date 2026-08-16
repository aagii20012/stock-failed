"""Pre-seal verification of SE100-CFG-3104 (Attempt 2 Gate 3 criteria).

Every "required_verbatim" and "frozen_*_verbatim" claim in the new file is checked byte-for-byte
against the artifact it claims to quote -- Attempt 1's SE100-CFG-3102 and, behind it, the frozen
constitution itself. Nothing here is asserted from memory: each expected value is read from disk
in this process. ASCII output only (cp1252 console).
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1] / "stockedge100"

NEW = ROOT / "config/generation_2/g2_gate_criteria_ra1.json"
A1 = ROOT / "config/generation_2/g2_gate_criteria.json"
G1 = ROOT / "config/stage3_gate_criteria.json"
PROTO = ROOT / "config/generation_2/g2_rotation_ra1_protocol.json"
CONST_JSON = ROOT / "governance/STAGE_0_CONSTITUTION.json"

ran: list[str] = []
fails: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    ran.append(label)
    if not ok:
        fails.append(label)
    print("%-4s %s%s" % ("OK" if ok else "FAIL", label, ("  [%s]" % detail) if detail else ""))


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


raw = NEW.read_text(encoding="utf-8")
new = json.loads(raw)
a1 = json.loads(A1.read_text(encoding="utf-8"))
g1 = json.loads(G1.read_text(encoding="utf-8"))
proto = json.loads(PROTO.read_text(encoding="utf-8"))
const = json.loads(CONST_JSON.read_text(encoding="utf-8"))

print("=== A. identity and provenance ===")
check("artifact_id is SE100-CFG-3104", new["artifact_id"] == "SE100-CFG-3104", new["artifact_id"])
check("attempt is 2", new["attempt"] == 2)
check("stage is 3 and gate_id is 3", (new["stage"], new["gate_id"]) == (3, 3))
check("generation is 2", new["generation"] == 2)
check("generation_id matches Attempt 1's", new["generation_id"] == a1["generation_id"], new["generation_id"])
check("gate_name matches Attempt 1's", new["gate_name"] == a1["gate_name"], new["gate_name"])
check("declared_before_any_strategy_code is true", new["declared_before_any_strategy_code"] is True)
check("live_trading_authorized is false", new["live_trading_authorized"] is False)

print("\n=== B. counterpart digests recomputed from disk ===")
check("attempt_1_counterpart_sha256 matches g2_gate_criteria.json",
      new["attempt_1_counterpart_sha256"] == sha(A1), sha(A1))
check("generation_1_counterpart_sha256 matches stage3_gate_criteria.json",
      new["generation_1_counterpart_sha256"] == sha(G1), sha(G1))
check("counterpart artifact ids are named correctly",
      "SE100-CFG-3102" in new["attempt_1_counterpart"] and "SE100-CFG-3002" in new["generation_1_counterpart"])

print("\n=== C. the seven condition texts, byte-equal to the seal ===")
new_conds = {c["id"]: c for c in new["conditions"]}
a1_conds = {c["id"]: c for c in a1["conditions"]}
g1_conds = {c["id"]: c for c in g1["conditions"]} if isinstance(g1.get("conditions"), list) else {}

EXPECTED_IDS = ["S3-C%d" % i for i in range(1, 8)]
check("condition ids are exactly S3-C1..S3-C7 in order",
      [c["id"] for c in new["conditions"]] == EXPECTED_IDS)
check("Attempt 1 carries the same seven ids",
      sorted(a1_conds) == sorted(EXPECTED_IDS))

for cid in EXPECTED_IDS:
    mine = new_conds[cid]["required_verbatim"]
    theirs = a1_conds[cid]["required_verbatim"]
    check("%s required_verbatim byte-equal to SE100-CFG-3102" % cid, mine == theirs,
          "%d chars" % len(mine) if mine == theirs else "mine=%r theirs=%r" % (mine, theirs))
    if cid in g1_conds and "required_verbatim" in g1_conds[cid]:
        check("%s required_verbatim byte-equal to Generation 1's SE100-CFG-3002" % cid,
              mine == g1_conds[cid]["required_verbatim"])

print("\n=== D. frozen gate text, traced back to the constitution ===")
check("frozen_gate_text_verbatim byte-equal to SE100-CFG-3102",
      new["frozen_gate_text_verbatim"] == a1["frozen_gate_text_verbatim"],
      "%d chars" % len(new["frozen_gate_text_verbatim"]))
check("frozen_gate_text_verbatim byte-equal to Generation 1's SE100-CFG-3002",
      new["frozen_gate_text_verbatim"] == g1["frozen_gate_text_verbatim"])

# Locate gate 3 in the constitution by identity, not by shape or index.
gate3 = None
def walk(node):
    global gate3
    if isinstance(node, dict):
        if node.get("id") == 3 and node.get("name") == "development_admissibility":
            gate3 = node
        for v in node.values():
            walk(v)
    elif isinstance(node, list):
        for v in node:
            walk(v)

walk(const)
check("gate 3 located in the frozen constitution JSON by identity", gate3 is not None)
comp = new["frozen_gate_json_companion_verbatim"]
check("companion id/name/fail_result equal the constitution's",
      (comp["id"], comp["name"], comp["fail_result"]) == (gate3["id"], gate3["name"], gate3["fail_result"]),
      gate3["fail_result"])
check("companion thresholds deep-equal the constitution's",
      comp["thresholds"] == gate3["thresholds"], json.dumps(gate3["thresholds"], sort_keys=True))
check("companion deep-equal to Attempt 1's copy",
      comp == a1["frozen_gate_json_companion_verbatim"])
check("companion deep-equal to the constitution's gate 3 object entire",
      comp == gate3, "keys=%s" % sorted(gate3))
# S3-CONFLICT-1's evidence: the JSON companion carries FOUR keys and no prose at all, so the
# seven conditions exist only in the Markdown. Assert that directly rather than hunting for a
# prose field that was never there -- the absence IS the conflict.
check("constitution gate 3 JSON has exactly four keys and no prose field",
      set(gate3) == {"id", "name", "fail_result", "thresholds"}, sorted(gate3))
check("constitution gate 3 JSON carries no condition text at all",
      not any(isinstance(v, str) and len(v) > 60 for v in gate3.values()))
check("S3-CONFLICT-1 is the entry that records exactly this",
      any(c["id"] == "S3-CONFLICT-1" and "five thresholds" in c["description"]
          and "seven conditions" in c["description"] for c in new["conflicts_found"]))

# Trace the prose to the FROZEN MARKDOWN, which is where it actually lives.
const_md = (ROOT / "governance/STAGE_0_CONSTITUTION.md").read_text(encoding="utf-8")
lines = const_md.splitlines()
anchor = next(i for i, ln in enumerate(lines) if ln.startswith("This gate rejects obviously weak"))
bullets = []
for ln in lines[anchor:]:
    if ln.startswith("- "):
        bullets.append(re.sub(r"\*\*", "", ln[2:]).rstrip(";.").strip())
    elif bullets and not ln.strip():
        continue
    elif bullets:
        break
check("seven gate 3 bullets extracted from the frozen Markdown",
      len(bullets) == 7, "%d bullets at line %d" % (len(bullets), anchor + 1))
for cid, bullet in zip(EXPECTED_IDS, bullets):
    check("%s required_verbatim byte-equal to the frozen Markdown bullet" % cid,
          new_conds[cid]["required_verbatim"] == bullet,
          "" if new_conds[cid]["required_verbatim"] == bullet
          else "mine=%r md=%r" % (new_conds[cid]["required_verbatim"], bullet))
check("the Markdown lead sentence opens frozen_gate_text_verbatim",
      new["frozen_gate_text_verbatim"].startswith(lines[anchor]))
check("the Markdown fail verdict closes frozen_gate_text_verbatim",
      new["frozen_gate_text_verbatim"].rstrip().endswith(
          "Fail verdict: %s." % gate3["fail_result"]))

for cid in EXPECTED_IDS:
    txt = new_conds[cid]["required_verbatim"]
    check("%s text is a literal substring of frozen_gate_text_verbatim" % cid,
          txt in new["frozen_gate_text_verbatim"])

print("\n=== E. thresholds: none moved ===")
comp = new["frozen_gate_json_companion_verbatim"]["thresholds"]
check("net_return_positive still true", comp["net_return_positive"] is True)
check("max_drawdown_pct still 15", comp["max_drawdown_pct"] == 15)
check("profit_factor_min still 1.1", comp["profit_factor_min"] == 1.1)
check("closed_trades_min still 30", comp["closed_trades_min"] == 30)
check("best_trade_removed_return_positive still true", comp["best_trade_removed_return_positive"] is True)
check("relationship_to_generation_1_criteria.thresholds_changed == none",
      new["relationship_to_generation_1_criteria"]["thresholds_changed"] == "none")
check("relationship_to_attempt_1_criteria.thresholds_changed == none",
      new["relationship_to_attempt_1_criteria"]["thresholds_changed"] == "none")
# "predicates_changed" is checked against the seven strings on disk, not against the word "none".
rel_pred = new["relationship_to_attempt_1_criteria"]
renamed = rel_pred["predicate_operand_renamed"]
diff = [cid for cid in EXPECTED_IDS if new_conds[cid]["predicate"] != a1_conds[cid]["predicate"]]
check("exactly one predicate string differs from Attempt 1's", len(diff) == 1, str(diff))
check("the one that differs is the one the file declares",
      diff == [k for k in renamed if k.startswith("S3-C")], str(diff))
check("S3-C4 is the declared rename", diff == ["S3-C4"], str(diff))
check("the rename keeps the relation and the threshold",
      new_conds["S3-C4"]["predicate"].split(">=")[1].strip()
      == a1_conds["S3-C4"]["predicate"].split(">=")[1].strip() == "30"
      and ">=" in new_conds["S3-C4"]["predicate"])
check("the rename is trades -> episodes and nothing else",
      new_conds["S3-C4"]["predicate"] == a1_conds["S3-C4"]["predicate"].replace("closed_trades", "closed_episodes"),
      new_conds["S3-C4"]["predicate"])
check("the declared rename text quotes both predicate strings",
      a1_conds["S3-C4"]["predicate"] in renamed["S3-C4"]
      and new_conds["S3-C4"]["predicate"] in renamed["S3-C4"])
check("predicates_changed does not claim 'none'",
      rel_pred["predicates_changed"] != "none")
check("predicates_changed asserts no relation and no threshold moved",
      "No relation and no threshold changed" in rel_pred["predicates_changed"])
for cid in [c for c in EXPECTED_IDS if c not in diff]:
    check("%s predicate string character-identical to Attempt 1's" % cid,
          new_conds[cid]["predicate"] == a1_conds[cid]["predicate"])
for key in ("carried_over_unchanged", "redefined_for_generation_2", "thresholds_changed"):
    check("relationship_to_generation_1_criteria.%s equals Attempt 1's" % key,
          new["relationship_to_generation_1_criteria"][key] == a1["relationship_to_generation_1_criteria"][key])
check("S3-C4 exception_invoked is false", new_conds["S3-C4"]["exception_invoked"] is False)
check("S3-C4 exception_invoked matches Attempt 1's", new_conds["S3-C4"]["exception_invoked"] == a1_conds["S3-C4"]["exception_invoked"])
check("S3-C2 boundary is inclusive, as in Attempt 1",
      new_conds["S3-C2"]["boundary"] == a1_conds["S3-C2"]["boundary"])

print("\n=== F. the measurement-basis split is total, disjoint and correct ===")
rel = new["relationship_to_attempt_1_criteria"]
changed = set(rel["measurement_basis_changed"])
unchanged = set(rel["measurement_basis_unchanged"])
check("changed and unchanged partition all seven conditions",
      changed | unchanged == set(EXPECTED_IDS), "union=%s" % sorted(changed | unchanged))
check("changed and unchanged are disjoint", not (changed & unchanged), "overlap=%s" % sorted(changed & unchanged))
check("the changed set is exactly the trade-reading conditions",
      changed == {"S3-C3", "S3-C4", "S3-C5", "S3-C6"}, sorted(changed))
check("the unchanged set is exactly the equity-curve-reading conditions",
      unchanged == {"S3-C1", "S3-C2", "S3-C7"}, sorted(unchanged))
# Each changed condition must actually cite the conflict; each unchanged one must not claim to.
def names_ledger(text: str) -> bool:
    """'episode ledger' and 'episode-ledger' are the same claim; a hyphen is not a difference."""
    return "episode ledger" in text.replace("-", " ")


for cid in sorted(changed):
    blob = json.dumps(new_conds[cid])
    check("%s cites G2A2-CONFLICT-18 in its own body" % cid, "G2A2-CONFLICT-18" in blob)
    check("%s attempt_2_status records the generalisation" % cid,
          names_ledger(new_conds[cid]["attempt_2_status"]),
          repr(new_conds[cid]["attempt_2_status"][:80]))
    # Not a word-search for "unchanged": S3-C5 has no numeric threshold to leave alone. The
    # checkable claim is that the predicate string itself did not move, which section E proves.
    check("%s attempt_2_status names the conflict that authorises the change" % cid,
          "G2A2-CONFLICT-18" in new_conds[cid]["attempt_2_status"]
          or "G2A2-CONFLICT-18" in json.dumps(new_conds[cid]["measurement"]))
for cid in sorted(unchanged):
    check("%s attempt_2_status does NOT claim the episode-ledger basis" % cid,
          not names_ledger(new_conds[cid]["attempt_2_status"]),
          repr(new_conds[cid]["attempt_2_status"][:80]))

print("\n=== G. conflict numbering does not collide with the protocol ===")
ids = [c["id"] for c in new["conflicts_found"]]
check("every conflict entry has a resolution",
      all(("resolution" in c and c["resolution"]) for c in new["conflicts_found"]))
check("every conflict entry has an action_taken",
      all(("action_taken" in c and c["action_taken"]) for c in new["conflicts_found"]))
check("conflict ids are unique", len(ids) == len(set(ids)), "%d entries" % len(ids))

new_series = sorted(int(m.group(1)) for m in (re.match(r"G2A2-CONFLICT-(\d+)$", i) for i in ids) if m)
check("this file's G2A2 series is 18..24 contiguous",
      new_series == list(range(18, 25)), str(new_series))

proto_raw = PROTO.read_text(encoding="utf-8")
proto_series = sorted({int(n) for n in re.findall(r"G2A2-CONFLICT-(\d+)\b", proto_raw)})
check("the protocol's G2A2 series is 1..17 contiguous",
      proto_series == list(range(1, 18)), str(proto_series))
check("the two series do not overlap",
      not (set(proto_series) & set(new_series)),
      "overlap=%s" % sorted(set(proto_series) & set(new_series)))
check("the two series are jointly contiguous 1..24",
      sorted(set(proto_series) | set(new_series)) == list(range(1, 25)))

inherited = [i for i in ids if not i.startswith("G2A2-")]
check("inherited conflicts are the five Attempt 1 carried them from",
      sorted(inherited) == sorted(["S3-CONFLICT-1", "S3-CONFLICT-3", "G2-CONFLICT-6",
                                   "G2-CONFLICT-7", "G2-CONFLICT-15"]), str(sorted(inherited)))
a1_ids = {c["id"] for c in a1["conflicts_found"]}
check("every inherited conflict id really exists in SE100-CFG-3102",
      set(inherited) <= a1_ids, "missing=%s" % sorted(set(inherited) - a1_ids))
check("the inherited set is non-empty (guard against a vacuous subset test)", len(inherited) > 0)

print("\n=== H. verdict tokens: sealed here, distinct from Attempt 1's ===")
vtd = new["verdict_token_derivation"]
PASS_T = "STAGE_3_G2_ATTEMPT_2_STRATEGY_ADMITTED_IN_DEVELOPMENT"
FAIL_T = "STAGE_3_G2_ATTEMPT_2_NO_CANDIDATE"
check("pass_token is the Attempt 2 pass token", vtd["pass_token"] == PASS_T)
check("fail_token is the Attempt 2 fail token", vtd["fail_token"] == FAIL_T)
check("the two tokens differ", vtd["pass_token"] != vtd["fail_token"])
a1_vtd = a1["verdict_token_derivation"]
check("pass_token is NOT Attempt 1's pass token", vtd["pass_token"] != a1_vtd["pass_token"], a1_vtd["pass_token"])
check("fail_token is NOT Attempt 1's fail token", vtd["fail_token"] != a1_vtd["fail_token"], a1_vtd["fail_token"])
check("constitutional_fail_result_equivalent equals the constitution's fail_result",
      vtd["constitutional_fail_result_equivalent"] == new["frozen_gate_json_companion_verbatim"]["fail_result"])
check("fail_is_a_deliverable is present and non-empty", bool(vtd.get("fail_is_a_deliverable")))
check("fail_is_a_deliverable forbids a nineteenth variant",
      "nineteenth variant" in vtd["fail_is_a_deliverable"])

proto_tokens = set(re.findall(r"STAGE_3_G2_ATTEMPT_2_[A-Z_]+", proto_raw))
check("the protocol names the same two tokens and no others",
      proto_tokens == {PASS_T, FAIL_T}, str(sorted(proto_tokens)))
check("this file names those two tokens too",
      set(re.findall(r"STAGE_3_G2_ATTEMPT_2_[A-Z_]+", raw)) == {PASS_T, FAIL_T})

# The reason this file exists: before it, the tokens were on disk in exactly one place.
hits = []
for p in ROOT.rglob("*"):
    if p.is_file() and p.suffix in {".md", ".json", ".py", ".sha256", ".txt", ".yaml", ".toml"}:
        try:
            if "STAGE_3_G2_ATTEMPT_2" in p.read_text(encoding="utf-8", errors="ignore"):
                hits.append(p.relative_to(ROOT).as_posix())
        except OSError:
            pass
check("the Attempt 2 tokens now live in exactly the two files written this session",
      sorted(hits) == ["config/generation_2/g2_gate_criteria_ra1.json",
                       "config/generation_2/g2_rotation_ra1_protocol.json"], str(sorted(hits)))

print("\n=== I. cross-references resolve ===")
check("protocol_ref names SE100-CFG-3103", "SE100-CFG-3103" in new["protocol_ref"])
check("the protocol's gate_criteria_ref points at this file",
      proto["gate_criteria_ref"] == "config/generation_2/g2_gate_criteria_ra1.json",
      proto["gate_criteria_ref"])
check("the referenced path exists on disk", (ROOT / proto["gate_criteria_ref"]).is_file())
check("S3-C6 scope names the Attempt 2 candidate id",
      proto["strategy_id"] in new_conds["S3-C6"]["scope_interpretation"]["applies_to"],
      proto["strategy_id"])
check("S3-C6 scope does NOT name Attempt 1's candidate",
      "SE100-G2-S3-C1-ROTATION" not in new_conds["S3-C6"]["scope_interpretation"]["applies_to"])
check("S3-C6 applies unconditionally, as in Attempt 1",
      new_conds["S3-C6"]["scope_interpretation"]["applies_to"].endswith("unconditionally.")
      and a1_conds["S3-C6"]["scope_interpretation"]["applies_to"].endswith("unconditionally."))
check("development_window equals Attempt 1's",
      new["windows"]["development_window"] == a1["windows"]["development_window"],
      str(new["windows"]["development_window"]))
check("development window ends 2021-07-31", new["windows"]["development_window"][1] == "2021-07-31")
check("authorized windows are development only", new["windows"]["authorized"] == ["development"])
check("validation window LOCKED, holdout SEALED",
      (new["windows"]["validation_window_state"], new["windows"]["holdout_window_state"]) == ("LOCKED", "SEALED"))
check("Generation 1 holdout recorded SPENT_AND_PROHIBITED",
      new["windows"]["generation_1_holdout_state"] == "SPENT_AND_PROHIBITED")
check("Generation 2 holdout dates recorded and never authorized",
      "2026-08-01" in new["windows"]["generation_2_holdout"]
      and "2028-07-31" in new["windows"]["generation_2_holdout"]
      and "Never read" in new["windows"]["generation_2_holdout"])

print("\n=== J. S3-C5 keeps the stricter Generation 1 reading ===")
c5 = new_conds["S3-C5"]["measurement"]
a1c5 = a1_conds["S3-C5"]["measurement"]
check("both removals still required", "BOTH" in c5["which_trade_is_removed"])
check("j1 is the largest multiple, j2 the largest absolute P&L",
      "largest equity multiple" in c5["which_trade_is_removed"]
      and "largest absolute P&L" in c5["which_trade_is_removed"])
check("tie handling is still earliest-by-index", "earliest by index" in c5["tie_handling"])
check("the r[i] formula is carried over from Attempt 1 verbatim in form",
      "1 + pnl[i] / E_entry[i]" in c5["procedure"][1] and "1 + pnl[i] / E_entry[i]" in a1c5["procedure"][1])
check("starting equity is still 100.00", "100.00" in c5["procedure"][0])
check("S3-C5 predicate requires BOTH removals positive",
      new_conds["S3-C5"]["predicate"] == "best_trade_removed_return > 0 for BOTH removals")

print("\n=== K. no condition can pass on absent evidence ===")
# Test for the VALUE, not the field name: S3-C6 declares its NOT_EVALUABLE case inline in
# `measurement` rather than in a dedicated field, and a field-name predicate reports a violation
# that is not there.
DECL_FIELDS = ("not_evaluable_treatment", "undefined_cases")
DECL_TOKENS = ("NOT_EVALUABLE", "NOT_RUN")
for cid in EXPECTED_IDS:
    c = new_conds[cid]
    blob = json.dumps(c)
    by_field = [f for f in DECL_FIELDS if f in c]
    by_value = [t for t in DECL_TOKENS if t in blob]
    check("%s declares how absent/undefined evidence is treated" % cid,
          bool(by_field or by_value), "field=%s inline=%s" % (by_field, by_value))

# An addition is fine; a silent DROP is not. Attempt 2 must retain every declaration Attempt 1 made.
a1_declared = {cid: {f for f in DECL_FIELDS if f in a1_conds[cid]} for cid in EXPECTED_IDS}
check("Attempt 1 declared at least one such field (guard against a vacuous subset test)",
      sum(len(v) for v in a1_declared.values()) > 0,
      "%d fields across %d conditions" % (sum(len(v) for v in a1_declared.values()),
                                          sum(1 for v in a1_declared.values() if v)))
for cid in EXPECTED_IDS:
    check("%s retains every absent-evidence field Attempt 1 declared" % cid,
          a1_declared[cid] <= set(new_conds[cid]),
          "dropped=%s" % sorted(a1_declared[cid] - set(new_conds[cid])))
added = sorted(cid for cid in EXPECTED_IDS
               if {f for f in DECL_FIELDS if f in new_conds[cid]} - a1_declared[cid])
check("the conditions where Attempt 2 ADDS a declaration are exactly S3-C2 and S3-C4",
      added == ["S3-C2", "S3-C4"], str(added))
check("both additions state the condition is otherwise always evaluable",
      all("always evaluable" in new_conds[cid]["not_evaluable_treatment"] for cid in added))
check("neither addition changes that condition's relation or threshold",
      new_conds["S3-C2"]["predicate"] == a1_conds["S3-C2"]["predicate"]
      and new_conds["S3-C4"]["predicate"].split(">=")[1].strip() == "30")
check("S3-C3 no-closed-episodes case FAILS",
      "FAILS" in new_conds["S3-C3"]["undefined_cases"]["no_closed_episodes"])
check("S3-C3 no-losses case preserves the raw null",
      "null" in new_conds["S3-C3"]["undefined_cases"]["no_losing_episodes"]
      and "infinity" in new_conds["S3-C3"]["undefined_cases"]["no_losing_episodes"])
check("conjunctive_note states NOT_RUN/UNKNOWN/NOT_EVALUABLE are not a pass",
      all(t in vtd["conjunctive_note"] for t in ("NOT_RUN", "UNKNOWN", "NOT_EVALUABLE")))
check("evaluation_integrity_rules forbid a vacuous reconciliation",
      any("vacuously" in r or "non-empty" in r for r in new["evaluation_integrity_rules"]))
check("evaluation_integrity_rules require the reconciliation to halt on mismatch",
      any("halts evaluation" in r for r in new["evaluation_integrity_rules"]))
check("evaluation_integrity_rules require exact Decimal comparison",
      any("floating point" in r for r in new["evaluation_integrity_rules"]))
check("evaluation_integrity_rules place selection before evaluation",
      any("before any condition is evaluated" in r and "return-blind" in r
          for r in new["evaluation_integrity_rules"]))

print("\n=== L. the risk-architecture counters gate nothing ===")
gating_blob = json.dumps(new["conditions"]) + json.dumps(new["verdict_token_derivation"])
for term in ("ladder activation", "lockout trigger", "throttle trim", "de-risk ladder activations"):
    check("no gating text is expressed in terms of '%s'" % term, term not in gating_blob)
rep = json.dumps(new["reported_but_not_gating"])
for term in ("ladder activations", "lockout triggers", "maximum gross exposure"):
    check("'%s' is declared reported-but-not-gating" % term, term in rep)
check("the Attempt-1 shutdown-date comparison is declared non-gating",
      "shutdown-trigger dates against Attempt 1" in rep)

print("\n=== M. self-digest and tree-digest hygiene ===")
own = sha(NEW)
check("the file does not contain its own digest", own not in raw, own)
hex64 = set(re.findall(r"\b[0-9a-f]{64}\b", raw))
declared = {new["attempt_1_counterpart_sha256"], new["generation_1_counterpart_sha256"]}
check("every 64-hex string in the file is a declared counterpart digest",
      hex64 == declared, "unresolved=%s" % sorted(hex64 - declared))
check("both declared digests resolve to a file on disk",
      sha(A1) in declared and sha(G1) in declared)
check("no repo_state_id value appears", "repo_state_id" not in raw)
check("the file carries no credential-shaped key", not re.search(r"[A-Z0-9]{20,}K[A-Z0-9]{4,}", raw))
check("adaptation disclosure is referenced, not paraphrased",
      "adaptation_disclosure_verbatim" in new["adaptation_disclosure_carried"]
      and "SE100-CFG-3103" in new["adaptation_disclosure_carried"])
check("the disclosure text itself is NOT duplicated here",
      proto["adaptation_disclosure_verbatim"] not in raw)

print("\n%d checks, %d failed" % (len(ran), len(fails)))
if fails:
    print("\nFAILED:")
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("ALL CHECKS PASSED")
