"""Dry-run of the Attempt 3 sealer's document check, before the sealer exists.

`check_document_agreement` is the refusal most likely to fire, because it compares a hand-framed
1240-line Markdown against measured values.  Running its predicate list here costs one command;
discovering a miss inside `build()` costs a half-written seal.  Every required string below is the
one the sealer will require, taken from the same source the sealer will take it from.

Reports a PASS/MISS per item and prints no protocol prose to the console - the cp1252 console
cannot render the disclosure's em dashes, and the disclosure must never be printed anyway.
"""

import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.reporting.g2_partition_lock import (  # noqa: E402
    CHARTER_ID,
    DEVELOPMENT_END,
    DEVELOPMENT_START,
    GENERATION_1_HOLDOUT_END,
    GENERATION_1_HOLDOUT_START,
    HOLDOUT_END,
    HOLDOUT_START,
    UNIVERSE_VERSION,
    VALIDATION_END,
    VALIDATION_START,
    VALIDATION_REUSE_DISCLOSURE,
    generation_identity,
    normalised_prose,
)

P = json.loads((ROOT / "config/generation_2/g2_rotation_ra3_protocol.json")
               .read_text(encoding="utf-8"))
C = json.loads((ROOT / "config/generation_2/g2_gate_criteria_ra3.json")
               .read_text(encoding="utf-8"))
MD_PATH = ROOT / "governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.md"
DOC = MD_PATH.read_text(encoding="utf-8")
FLAT = normalised_prose(DOC)
RAW = re.sub(r"\s+", " ", DOC)

DER = C["verdict_token_derivation"]

REQUIRED = {
    "document id": "SE100-GOV-2007",
    "charter id": CHARTER_ID,
    "partition lock id": "SE100-GOV-2002",
    "attempt 1 document id": "SE100-GOV-2003",
    "attempt 2 document id": "SE100-GOV-2005",
    "generation id": generation_identity()["generation_id"],
    "strategy id": P["strategy_id"],
    "family": P["family"],
    "development start": DEVELOPMENT_START,
    "development end": DEVELOPMENT_END,
    "validation start": VALIDATION_START,
    "validation end": VALIDATION_END,
    "generation 1 holdout start": GENERATION_1_HOLDOUT_START,
    "generation 1 holdout end": GENERATION_1_HOLDOUT_END,
    "holdout start": HOLDOUT_START,
    "holdout end": HOLDOUT_END,
    "universe version": UNIVERSE_VERSION,
    "pass token": DER["pass_token"],
    "fail token": DER["fail_token"],
    "attempt 1 verdict": P["attempt_1_ref"]["verdict"].replace(" - ", " \u2014 "),
    "attempt 2 verdict": P["attempt_2_ref"]["verdict"].replace(" - ", " \u2014 "),
    "selection rule id": P["representative_selection_rule"]["id"],
    "risk architecture id": P["risk_architecture"]["id"],
}

fails = []
print("-- required strings (prose form) " + "-" * 56)
for label, value in REQUIRED.items():
    ok = bool(value) and value in FLAT
    print("  %-30s %-8s %s" % (label, "PASS" if ok else "MISS", value))
    if not ok:
        fails.append(label)

print()
print("-- the two mandated disclosures " + "-" * 57)
for label, text in (("adaptation", P["adaptation_disclosure_verbatim"]),
                    ("validation reuse", VALIDATION_REUSE_DISCLOSURE)):
    ok = normalised_prose(text) in FLAT
    print("  %-30s %-8s (%d chars, sha256 %s)"
          % (label, "PASS" if ok else "MISS", len(text),
             hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]))
    if not ok:
        fails.append("disclosure:" + label)

print()
print("-- the seventeen immutable prior-attempt modules " + "-" * 40)
modules = (list(P["prior_attempt_modules_immutable"]["attempt_1_modules"])
           + list(P["prior_attempt_modules_immutable"]["attempt_2_modules"]))
missing_mod = [m for m in modules if "`%s`" % m not in RAW]
print("  listed %d, named in the Markdown %d, missing %s"
      % (len(modules), len(modules) - len(missing_mod), missing_mod or "none"))
if missing_mod:
    fails.append("modules")

print()
print("-- every conflict id the config declares " + "-" * 48)
declared = sorted({e["id"] for e in P.get("conflicts_found", [])})
missing_c = [c for c in declared if c not in FLAT]
print("  declared %d, carried %d, missing %s"
      % (len(declared), len(declared) - len(missing_c), missing_c or "none"))
if missing_c:
    fails.append("conflicts")

print()
print("-- section 13 blockquote equals the sealed predicate " + "-" * 36)
q = re.search(r"\n((?:> .*\n)+)", DOC[DOC.index("## 13.") :])


def norm_pred(t):
    return re.sub(r"\s+", " ", t.replace("`", "").replace("/ ", " ")).strip().rstrip(".")


if q is None:
    print("  MISS  no blockquote in section 13")
    fails.append("predicate")
else:
    got = " ".join(ln[2:].strip() for ln in q.group(1).strip().splitlines())
    ok = norm_pred(got) == norm_pred(P["declared_before_any_strategy_code_measurement"]["predicate"])
    print("  %-6s markdown=%r" % ("PASS" if ok else "MISS", norm_pred(got)))
    print("         sealed  =%r" % norm_pred(
        P["declared_before_any_strategy_code_measurement"]["predicate"]))
    if not ok:
        fails.append("predicate")

print()
print("-- the Markdown carries no digest of itself " + "-" * 45)
own = hashlib.sha256(MD_PATH.read_bytes()).hexdigest()
print("  own digest %s embedded=%s" % (own[:16], own in DOC))
if own in DOC:
    fails.append("self digest")

print()
print("-- prior-attempt tokens are extractable and exclude this attempt's " + "-" * 22)
prose = DER["prior_attempt_tokens_are_not_available_here"]
found = sorted(set(re.findall(r"STAGE_3_G2_[A-Z0-9_]+", prose)))
print("  extracted %d: %s" % (len(found), found))
overlap = {DER["pass_token"], DER["fail_token"]} & set(found)
print("  overlap with this attempt's tokens: %s" % (sorted(overlap) or "none"))
if len(found) < 4 or overlap:
    fails.append("token exclusion")

print()
print("=" * 90)
print("MISSES: %s" % (fails or "none - check_document_agreement would return []"))
