"""The remaining sealed inputs g2_gate_ra3.py has to read, dumped before anything is written against them.

`build_plan_ra3` reads CFG-3105's `run_span`; `_check_tokens_are_attempt_3s_own` reads CFG-3106's
`prior_attempt_tokens_are_not_available_here` and three counterparts; `condition_7_ra3` reads S3-C7's
`measurement`.  Attempt 2's `build_plan` hardcodes six `run["..."]` subscripts -- if CFG-3105 renamed
any of them the plan would KeyError on the first call, which is not a thing to discover at grid time.
"""

import json
import pathlib

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
P3 = json.loads((ROOT / "config/generation_2/g2_rotation_ra3_protocol.json").read_text("utf-8"))
P2 = json.loads((ROOT / "config/generation_2/g2_rotation_ra1_protocol.json").read_text("utf-8"))
C3 = json.loads((ROOT / "config/generation_2/g2_gate_criteria_ra3.json").read_text("utf-8"))
K3 = {c["id"]: c for c in C3["conditions"]}


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


print("=" * 100)
print("1. run_span -- the six subscripts build_plan() takes")
WANTED = ("run_start", "run_end", "binding_symbol", "sessions", "recheck_requirement")
run3, run2 = P3.get("run_span", {}), P2.get("run_span", {})
print("   RA3 keys: %s" % sorted(run3))
print("   Att2 keys: %s" % sorted(run2))
for key in WANTED:
    print("   %-24s RA3=%-28s Att2=%s"
          % (key, safe(run3.get(key, "*** ABSENT ***"))[:28], safe(run2.get(key, "*** ABSENT ***"))[:28]))
print("   all six present in RA3: %s" % all(k in run3 for k in WANTED))
for key in sorted(set(run3) - set(WANTED)):
    print("   extra RA3 %-22s %s" % (key, safe(run3[key])[:160]))

print()
print("=" * 100)
print("2. counterparts CFG-3106 pins")
for key in sorted(C3):
    if key.endswith("_counterpart") or key.endswith("_counterpart_sha256"):
        print("   %-40s %s" % (key, safe(C3[key])))

print()
print("=" * 100)
print("3. prior_attempt_tokens_are_not_available_here")
d = C3["verdict_token_derivation"]
print("   pass_token: %s" % d["pass_token"])
print("   fail_token: %s" % d["fail_token"])
print()
print("   %s" % safe(d["prior_attempt_tokens_are_not_available_here"]))

print()
print("=" * 100)
print("4. the four withheld tokens, read from the two prior sealed files")
withheld = []
for rel in ("config/generation_2/g2_gate_criteria.json", "config/generation_2/g2_gate_criteria_ra1.json"):
    doc = json.loads((ROOT / rel).read_text("utf-8"))
    dd = doc["verdict_token_derivation"]
    withheld += [dd["pass_token"], dd["fail_token"]]
    print("   %-46s %s / %s" % (rel.split("/")[-1], dd["pass_token"], dd["fail_token"]))
print()
for token in withheld:
    named = token in d["prior_attempt_tokens_are_not_available_here"]
    print("   %-58s named in the RA3 prose: %s" % (token, named))
print("   collision with RA3's own two: %s"
      % bool({d["pass_token"], d["fail_token"]} & set(withheld)))

print()
print("=" * 100)
print("5. S3-C7 measurement keys condition_7 dereferences")
m = K3["S3-C7"]["measurement"]
for key in ("axis_orderings", "neighbour_definition", "neighbour_count", "one_step_note",
            "what_is_read", "no_new_runs", "risk_constants_have_no_neighbours"):
    present = key in m
    print("   %-38s %s" % (key, "present" if present else "*** ABSENT ***"))
print("   axis_orderings: %s" % json.dumps(m["axis_orderings"]))
print()
print("   risk_constants_have_no_neighbours:")
print("      %s" % safe(m["risk_constants_have_no_neighbours"]))

print()
print("=" * 100)
print("6. relationship_to_attempt_2_criteria")
for key, value in sorted(C3.get("relationship_to_attempt_2_criteria", {}).items()):
    print("   %-40s %s" % (key, safe(json.dumps(value, ensure_ascii=False))[:150]))
