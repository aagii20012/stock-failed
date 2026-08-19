"""Post-write verification of the two Attempt 3 config seals.

Checks the bytes on disk, not the in-memory object the builder had.
"""

import hashlib
import json
import pathlib

FILES = [
    "config/generation_2/g2_rotation_ra3_protocol.json",
    "config/generation_2/g2_gate_criteria_ra3.json",
]
TEMPLATE = "config/generation_2/g2_rotation_ra1_protocol.json"

for rel in FILES + [TEMPLATE]:
    p = pathlib.Path(rel)
    raw = p.read_bytes()
    print("\n== %s" % rel)
    print("   sha256      :", hashlib.sha256(raw).hexdigest())
    print("   bytes       :", len(raw))
    print("   CRLF        :", raw.count(b"\r\n"), "| bare CR:", raw.count(b"\r"))
    print("   trailing NL :", raw.endswith(b"\n"))
    print("   non-ascii   :", sum(1 for b in raw if b > 127))
    obj = json.loads(raw.decode("utf-8"))
    print("   top keys    :", len(obj))
    print("   round-trip  :",
          (json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode("utf-8") == raw)

proto = json.loads(pathlib.Path(FILES[0]).read_text(encoding="utf-8"))
crit = json.loads(pathlib.Path(FILES[1]).read_text(encoding="utf-8"))
tmpl = json.loads(pathlib.Path(TEMPLATE).read_text(encoding="utf-8"))

print("\n== mutual reference")
print("   protocol.artifact_id      :", proto["artifact_id"])
print("   criteria.artifact_id      :", crit["artifact_id"])
print("   protocol.gate_criteria_ref:", proto["gate_criteria_ref"])
print("   criteria.protocol_ref     :", crit.get("protocol_ref"))
print("   ids agree                 :",
      FILES[1].split("/")[-1] in proto["gate_criteria_ref"]
      and "SE100-CFG-3105" in str(crit.get("protocol_ref")))

print("\n== strategy id agreement")
sid = proto["strategy_id"]
print("   protocol strategy_id:", sid)
print("   criteria mentions it:", json.dumps(crit).count(sid))
print("   candidate_index     :", proto["candidate_index"])

print("\n== thresholds unchanged from Attempt 2")
a2 = json.loads(pathlib.Path("config/generation_2/g2_gate_criteria_ra1.json").read_text("utf-8"))


def thresholds(o):
    return {c["id"]: c.get("threshold", c.get("value")) for c in o.get("conditions", [])}


t3, t2 = thresholds(crit), thresholds(a2)
print("   attempt2:", json.dumps(t2, sort_keys=True))
print("   attempt3:", json.dumps(t3, sort_keys=True))
print("   identical:", t3 == t2)

print("\n== mechanics copied verbatim from the sealed Attempt 2 protocol")
for k in ["eligible_universe", "ranking_signal", "ranking_rule", "position_count", "rebalance",
          "execution", "position_sizing", "concentration_ceiling", "window", "runs_per_variant",
          "serialisation"]:
    print("   %-24s identical: %s" % (k, proto[k] == tmpl[k]))
print("   %-24s identical: %s (expected False)" % ("run_span", proto["run_span"] == tmpl["run_span"]))
print("   run_span minus the new key:",
      {k: v for k, v in proto["run_span"].items() if k != "reverification_required"}
      == tmpl["run_span"])

print("\n== grid")
g3, g2 = proto["grid"], tmpl["grid"]
print("   axes identical      :", g3["axes"] == g2["axes"])
print("   size                :", g3["size"], "| variants:", len(g3["variants"]))
same = all(
    {k: v for k, v in a.items() if k != "variant_id"} == {k: v for k, v in b.items() if k != "variant_id"}
    for a, b in zip(g3["variants"], g2["variants"])
)
print("   variants identical except variant_id:", same)
print("   any RA1/C2 id leaked:", any("C2-ROTATION-RA1" in v["variant_id"] for v in g3["variants"]))

print("\n== RA3 ladder")
bands = proto["risk_architecture"]["components"]["RA3-4"]["bands"]
print("   bands:", json.dumps(bands))
print("   components:", sorted(proto["risk_architecture"]["components"]))
print("   no band boundary below 0.08:",
      not any(float(b["dd_from"]) < 0.08 and b["band"] > 0 for b in bands))
ra2b = tmpl["risk_architecture"]["components"]["RA2-4"]["bands"]
print("   RA2 bands (for contrast):", json.dumps(ra2b))
print("   RA3 = RA2 minus band 1, renumbered:",
      [(b["dd_from"], b["dd_to_exclusive"], b["scalar"]) for b in bands]
      == [(b["dd_from"], b["dd_to_exclusive"], b["scalar"]) for b in ra2b if b["band"] != 1])

print("\n== disclosure string")
disc = proto["adaptation_disclosure_verbatim"]
print("   sha256 :", hashlib.sha256(disc.encode("utf-8")).hexdigest())
print("   len    :", len(disc), "| em U+2014:", disc.count("—"),
      "| minus U+2212:", disc.count("−"))
print("   no ASCII hyphen before 5%:", "-5%" not in disc)
print("   carriage targets:", len(proto["adaptation_disclosure_carriage_requirement"]
                                  ["must_appear_verbatim_in"]))
for t in proto["adaptation_disclosure_carriage_requirement"]["must_appear_verbatim_in"]:
    print("     -", t, "| exists:", pathlib.Path(t).exists())

print("\n== prior-attempt immutability list")
pm = proto["prior_attempt_modules_immutable"]
mods = pm["attempt_1_modules"] + pm["attempt_2_modules"]
print("   declared count:", pm["count"], "| listed:", len(mods), "| unique:", len(set(mods)))
missing = [m for m in mods if not pathlib.Path(m).exists()]
print("   all exist:", not missing, missing)

print("\n== contamination predicate (pre-seal state)")
hits = []
for p in list(pathlib.Path("src/stockedge100").rglob("*.py")) + list(
    pathlib.Path("tests").rglob("*.py")
):
    if sid in p.read_text(encoding="utf-8", errors="replace"):
        hits.append(str(p))
print("   .py files naming %s: %d %s" % (sid, len(hits), hits))

print("\n== conflict numbering")
pc = [c["id"] for c in proto["conflicts_found"]]
cc = [c["id"] for c in crit["conflicts_found"]]
print("   protocol:", pc)
print("   criteria:", cc)
print("   overlap :", sorted(set(pc) & set(cc)))
print("   live_trading_authorized:", proto["live_trading_authorized"], crit.get("live_trading_authorized"))
