"""Dry-run the Generation 2 Stage 3 Attempt 2 package builder without letting it write anything.

``build_stage_package`` is replaced with a stub that captures the ``StageDecision``, so every guard,
every recomputation and the whole assembled gate-conditions block can be inspected before the real
build records a ``repo_state_id`` that a later fix to this module would invalidate. The module lives
in ``src/``, which is a ``repo_state_id`` pattern, so a defect found after the real build cannot be
repaired without regenerating the package.

Beyond printing the assembly, this script diffs the assembled gate conditions against the report's
own section 14 table, and re-resolves every literal figure the builder's prose asserts back to the
evidence file. ASCII output only.

    python _scratch/g2a2_dryrun_package.py
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
ROOT = WORKSPACE / "stockedge100"
sys.path.insert(0, str(ROOT / "src"))

from stockedge100.reporting import g2_stage3_attempt2_package as mod  # noqa: E402

CAPTURED: dict = {}
problems: list[str] = []


def bad(label: str, detail: str) -> None:
    problems.append("%s: %s" % (label, detail))
    print("  FAIL %-52s %s" % (label, detail))


def ok(label: str, detail: str = "") -> None:
    print("  OK   %-52s %s" % (label, detail))


@dataclass
class FakeResult:
    run_id: str = "SE100-R-DRYRUN"
    repo_state_id: str = "<not computed in a dry run>"
    timestamp_utc: str = "<not read in a dry run>"
    checksum_digest: str = "<not computed in a dry run>"
    freeze_ok: bool = True
    decision_path: Path = ROOT / "reports/stage3_g2_attempt2/DRYRUN.json"
    manifest_path: Path = ROOT / "reports/stage3_g2_attempt2/DRYRUN_MANIFEST.json"
    checksum_path: Path = ROOT / "reports/stage3_g2_attempt2/DRYRUN.sha256"
    run_record_path: Path = ROOT / "runs/DRYRUN.json"


def stub(decision):
    CAPTURED["decision"] = decision
    return FakeResult()


mod.build_stage_package = stub

print("=== 1. the builder runs, and its guards do not refuse ===")
rc = mod.build()
print("  return code %d" % rc)
if rc != 0 or "decision" not in CAPTURED:
    raise SystemExit("BUILDER REFUSED OR DID NOT REACH build_stage_package -- rc=%d" % rc)
d = CAPTURED["decision"]

ev = json.loads((ROOT / mod.EVIDENCE).read_text(encoding="utf-8"))
report = (ROOT / mod.REPORT).read_text(encoding="utf-8")

print()
print("=== 2. identity ===")
for field in ("stage", "stage_slug", "decision_basename", "manifest_basename", "gate_id",
              "gate_name", "verdict", "gate_passed", "generation", "universe_version",
              "date_range", "holdout_state"):
    print("  %-22s %s" % (field, getattr(d, field)))

print()
print("=== 3. assembled gate conditions ===")
conds = d.gate_conditions
for cid, row in conds.items():
    if cid == "admissible_candidate_exists":
        continue
    print("  %-8s %-28s satisfied=%-5s gating=%s" % (
        cid, row["verdict"], row["satisfied"], ",".join(row["gating_runs"])))
    print("           met_by=%-14s not_met_by=%-14s not_applicable_for=%s"
          % (row["met_by"], row["not_met_by"], row["not_applicable_for"]))
    print("           measured=%s threshold=%s" % (row["measured"], row["threshold"]))
    if row["reported_not_gating"]:
        print("           reported_not_gating=%s" % row["reported_not_gating"])
gate = conds["admissible_candidate_exists"]
print("  %-8s %-28s value=%s representative=%s"
      % ("GATE", gate["verdict"], gate["value"], gate["representative"]))

print()
print("=== 4. the gate row is present, correct, and decides alone ===")
if "admissible_candidate_exists" not in conds:
    bad("gate row present", "missing -- the table would read as though the gate were irrelevant")
else:
    ok("gate row present")
if gate["verdict"] == "NOT_MET" and gate["value"] is False:
    ok("gate row NOT_MET", "matches the FAIL verdict")
else:
    bad("gate row NOT_MET", "verdict=%s value=%s" % (gate["verdict"], gate["value"]))
declared_not_met = sorted(c for c, r in conds.items()
                          if c != "admissible_candidate_exists" and not r["satisfied"])
cand = ev["candidate_results"][0]
basis = cand["admission_basis"]
# candidate_results[0]["conditions"] and ["conditions_not_met"] are the BASE-run evaluation; the
# both-gate reading adopted under G2A2-CONFLICT-25 lives in admission_basis, which reports the two
# run-scoped lists separately. The assembled table must equal their union, not the base list alone.
base_not_sat = sorted(basis["base_conditions_not_satisfied"])
stress_not_sat = sorted(basis["stress_conditions_not_satisfied"])
union_not_sat = sorted(set(base_not_sat) | set(stress_not_sat))
print("  assembled not-satisfied     %s" % declared_not_met)
print("  evidence base_not_satisfied %s" % base_not_sat)
print("  evidence stress_not_satisfied %s" % stress_not_sat)
print("  both-gate union             %s" % union_not_sat)
print("  evidence conditions_not_met %s (base-run field)" % sorted(cand["conditions_not_met"]))
if declared_not_met == union_not_sat:
    ok("assembled table is the both-gate union", basis["conflict_ref"])
else:
    bad("assembled table is the both-gate union",
        "assembled %s vs union %s" % (declared_not_met, union_not_sat))
if sorted(cand["conditions_not_met"]) == base_not_sat:
    ok("evidence conditions_not_met is the base-run list", "as admission_basis describes")
else:
    bad("evidence conditions_not_met is the base-run list",
        "%s vs %s" % (sorted(cand["conditions_not_met"]), base_not_sat))
# The stricter reading may only ever ADD conditions, never drop one the base run already failed.
if set(base_not_sat) <= set(declared_not_met):
    ok("strict reading never drops a base failure",
       "adds %s" % sorted(set(declared_not_met) - set(base_not_sat)))
else:
    bad("strict reading never drops a base failure",
        "missing %s" % sorted(set(base_not_sat) - set(declared_not_met)))
# S3-C7 is the one condition the sealed criteria evaluate on base only; every other gating row must
# name both runs, or the assembled scope has drifted from admission_basis.
for cid, row in sorted(conds.items()):
    if cid == "admissible_candidate_exists":
        continue
    expected = ["#BASE"] if cid == "S3-C7" else ["#BASE", "#STRESS"]
    if sorted(row["gating_runs"]) != expected:
        bad("%s gating scope" % cid, "gates on %s, expected %s" % (row["gating_runs"], expected))
ok("gating scope matches admission_basis", "S3-C7 base-only, S3-C1..S3-C6 both runs")
if basis["permissive_base_only_reading_would_give"] is False:
    ok("permissive reading fails too", "the verdict does not turn on the conflict resolution")
else:
    bad("permissive reading fails too",
        "base-only reading gives %r" % basis["permissive_base_only_reading_would_give"])

print()
print("=== 5. diff against the report's own section 14 table ===")
sec14 = report.split("\n## 14.", 1)[1].split("\n## ", 1)[0]
rows = {}
for line in sec14.splitlines():
    m = re.match(r"^\|\s*`?(S3-C\d|admissible_candidate_exists)`?\s*\|", line.strip())
    if m:
        cells = [c.strip().strip("`*") for c in line.strip().strip("|").split("|")]
        rows[m.group(1)] = cells
if not rows:
    bad("section 14 rows parsed", "no rows matched -- the diff would pass vacuously")
else:
    ok("section 14 rows parsed", "%d rows: %s" % (len(rows), sorted(rows)))
for cid, cells in sorted(rows.items()):
    verdicts = [c for c in cells if c in ("MET", "NOT_MET", "SATISFIED_WITHOUT_BEING_MET",
                                          "NOT_RUN", "NOT_EVALUABLE", "UNKNOWN")]
    assembled = conds.get(cid, {}).get("verdict")
    if not verdicts:
        print("  ?    %-30s report row carries no verdict token; cells=%s" % (cid, cells[:4]))
        continue
    if assembled in verdicts:
        ok("%s report vs assembled" % cid, "%s" % assembled)
    else:
        bad("%s report vs assembled" % cid,
            "report says %s, builder assembled %s" % (verdicts, assembled))
missing_from_report = sorted(set(conds) - set(rows))
if missing_from_report:
    bad("every assembled row appears in section 14", "absent: %s" % missing_from_report)
else:
    ok("every assembled row appears in section 14")

print()
print("=== 6. literal figures in the builder's prose, re-resolved from the evidence ===")
prose = " ".join(d.evidence) + " " + " ".join(d.limitations) + " " + " ".join(d.conflicts_found)
vt = ev["variant_table"]

# Stored as high-precision decimal strings, so coerce rather than assuming float.
gross = [float(r["base_max_gross_fraction_observed"]) for r in vt]
gross += [float(r["stress_max_gross_fraction_observed"]) for r in vt]
base_gross = [float(r["base_max_gross_fraction_observed"]) for r in vt]
lo, hi = min(gross), max(gross)
base_lo = min(base_gross)
print("  grid-wide gross fraction %.6f to %.6f over %d runs" % (lo, hi, len(gross)))
print("  base-only minimum        %.6f (the section 16 table's own minimum)" % base_lo)
# Three figures are legitimately quotable: the grid-wide endpoints and the base-only minimum,
# which round to 0.5043, 0.5184 and 0.5044 respectively. Anything else is invented.
allowed = {round(lo, 4), round(hi, 4), round(base_lo, 4)}
for literal in sorted(set(re.findall(r"0\.5\d{3}", prose))):
    if round(float(literal), 4) in allowed:
        ok("prose figure %s" % literal, "resolves to a measured endpoint")
    else:
        bad("prose figure %s" % literal,
            "matches none of the measured figures %s" % sorted(allowed))
if round(lo, 4) != 0.5043 or round(hi, 4) != 0.5184 or round(base_lo, 4) != 0.5044:
    bad("gross-fraction figures are what the report says",
        "measured %.4f/%.4f/%.4f" % (lo, hi, base_lo))
else:
    ok("gross-fraction figures agree with report sections 16 and 17.7")

rep_id = ev["selection"]["representative_variant_id"]
rep = [r for r in vt if r["variant_id"] == rep_id][0]
best = max(vt, key=lambda r: float(r["base_total_return"]))
print("  representative %s" % rep_id)
print("  best by base return %s at %.6f" % (best["variant_id"], float(best["base_total_return"])))

# Anything the prose asserts about these two variants must resolve; a literal the prose does not
# assert is simply not its claim to make, so absence is reported, never failed.
resolvable = {
    "63.15": 100 * float(best["base_total_return"]),
    "0.6315": float(best["base_total_return"]),
    "1.9341": float(best["base_profit_factor"]),
    "0.1116": float(best["base_max_drawdown"]),
    "105": float(best["base_closed_trades"]),
    "0.42": 100 * float(rep["base_total_return"]),
    "36": float(rep["base_closed_trades"]),
    "189": float(rep["fill_count_both_runs"]),
}
for literal, measured in resolvable.items():
    if literal not in prose:
        print("  --   prose does not assert %-12s (measured %s)" % (literal, measured))
        continue
    if abs(float(literal) - measured) < max(5e-5, abs(measured) * 1e-6):
        ok("prose literal %s" % literal, "resolves to %s" % measured)
    else:
        bad("prose literal %s" % literal, "measured value is %s" % measured)

for vid in re.findall(r"RA1-L\d\d-K\d-(?:MONTHLY|QUARTERLY)", prose):
    known = {r["variant_id"].split("RA1-")[-1] for r in vt}
    tail = vid.split("RA1-")[-1]
    if tail in known:
        ok("prose names variant %s" % tail, "present in the grid")
    else:
        bad("prose names variant %s" % tail, "no such variant in the grid")

at_keys = sorted(k for k in json.loads(
    (ROOT / mod.PROTOCOL).read_text(encoding="utf-8"))["adversarial_test_requirements"]
    if re.fullmatch(r"AT-[A-Z]", k))
body_tests = d.body["engine_capability_added"]["adversarial_tests"]
span = re.search(r"AT-([A-Z]) through AT-([A-Z])", body_tests)
if not span:
    bad("adversarial-test span", "no 'AT-x through AT-y' phrase found in the prose")
else:
    claimed_lo, claimed_hi = "AT-%s" % span.group(1), "AT-%s" % span.group(2)
    if (claimed_lo, claimed_hi) == (at_keys[0], at_keys[-1]):
        ok("adversarial-test span", "%s..%s, matching the %d sealed requirements"
           % (claimed_lo, claimed_hi, len(at_keys)))
    else:
        bad("adversarial-test span", "prose claims %s..%s but the seal declares %s"
            % (claimed_lo, claimed_hi, at_keys))
# The span is only honest if the named file really carries every requirement.
carrier = re.search(r"(tests/\S+\.py) covers", body_tests)
if not carrier:
    bad("adversarial-test carrier named", "no 'tests/....py covers' phrase found")
else:
    carrier_text = (ROOT / carrier.group(1)).read_text(encoding="utf-8")
    absent = [k for k in at_keys if k not in carrier_text]
    if absent:
        bad("carrier covers every requirement",
            "%s does not mention %s" % (carrier.group(1), absent))
    else:
        ok("carrier covers every requirement", "%s marks all %d" % (carrier.group(1), len(at_keys)))
# The number word in the prose, if any, must equal the sealed count.
words = {"seven": 7, "eight": 8, "nine": 9, "ten": 10}
for word, n in words.items():
    if re.search(r"\b%s\b sealed requirements|all %s sealed" % (word, word), body_tests):
        if n == len(at_keys):
            ok("spelled-out requirement count", "'%s' == %d sealed" % (word, len(at_keys)))
        else:
            bad("spelled-out requirement count",
                "prose says '%s' but %d are sealed" % (word, len(at_keys)))

print()
print("=== 7. tests, disclosure carriage and authorization ===")
print("  tests %s" % d.tests)
carriage = d.body["adaptation_disclosure_carriage"]
print("  disclosure characters   %s" % carriage["characters"])
print("  digest agrees w/evidence %s" % carriage["digest_agrees_with_evidence"])
for rel, state in sorted(carriage["carriers"].items()):
    print("    %-62s verbatim=%-5s byte_exact=%s"
          % (rel.split("/")[-1], state["carries_verbatim"], state["carries_byte_exact"]))
if carriage["characters"] == 842:
    ok("disclosure is 842 characters")
else:
    bad("disclosure is 842 characters", "measured %s" % carriage["characters"])

# The relaxation must cover exactly the one frozen hard-wrapped carrier, and be justified by a
# difference that is only line breaks -- not a paraphrase.
relaxed = carriage["carriers_requiring_normalisation"]
expected_relaxed = ["governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.md"]
if relaxed == expected_relaxed:
    ok("normalisation scoped to one frozen carrier", relaxed[0].split("/")[-1])
else:
    bad("normalisation scoped to one frozen carrier", "relaxed=%s" % relaxed)

sealed_str = json.loads((ROOT / mod.PROTOCOL).read_text(encoding="utf-8"))[
    "adaptation_disclosure_verbatim"]
md = (ROOT / expected_relaxed[0]).read_text(encoding="utf-8")
start = md.index(sealed_str[:40])
# The stored copy is the SHORTEST slice that unwraps to the sealed string with no rstrip; an
# rstripped comparison trails into the blank line that follows the paragraph and overcounts by two.
exact = [n for n in range(len(sealed_str), len(sealed_str) + 128)
         if re.sub(r"\n>?[ \t]*", " ", md[start:start + n]) == sealed_str]
stored = md[start:start + exact[0]] if exact else ""
markers = re.findall(r"\n>?[ \t]*", stored)
extra = sorted(set(markers))
if stored and len(stored) == 858 and extra == ["\n> "] and len(markers) == 8:
    ok("the difference is line breaks only",
       "%d stored vs %d sealed = 8 x '\\n> ' replacing 8 spaces" % (len(stored), len(sealed_str)))
else:
    bad("the difference is line breaks only",
        "stored %d chars, markers %s" % (len(stored), extra))
# The conflict text states that length; it must not be a hand-typed number.
if stored and ("858" in " ".join(d.conflicts_found) and "842" in " ".join(d.conflicts_found)):
    ok("G2A2-CONFLICT-29 quotes the measured lengths", "858 stored, 842 sealed")
else:
    bad("G2A2-CONFLICT-29 quotes the measured lengths", "one of 858/842 is missing from the text")
others = [rel for rel, s in carriage["carriers"].items()
          if s["present"] and rel not in expected_relaxed]
if all(carriage["carriers"][rel]["carries_byte_exact"] for rel in others):
    ok("every other present carrier is byte-exact", "%d carriers" % len(others))
else:
    bad("every other present carrier is byte-exact",
        "%s" % [r for r in others if not carriage["carriers"][r]["carries_byte_exact"]])
if "G2A2-CONFLICT-29" in " ".join(d.conflicts_found):
    ok("G2A2-CONFLICT-29 is disclosed in the package")
else:
    bad("G2A2-CONFLICT-29 is disclosed in the package", "no such conflict recorded")
for key, value in sorted(d.authorization_state.items()):
    if value != "false":
        bad("authorization_state %s" % key, "is %r, expected 'false'" % value)
print("  all authorization_state values 'false': %s"
      % all(v == "false" for v in d.authorization_state.values()))
print("  live_trading_authorized  %s" % d.authorization_state["live_trading_authorized"])

print()
print("=== 8. produced and frozen paths all exist ===")
for rel in mod.FROZEN_INPUTS:
    if not (ROOT / rel).is_file():
        bad("frozen input exists", rel)
pending = "reports/stage3_g2_attempt2/STAGE_3_G2_A2_ROTATION_RESEARCH.json"
for rel in mod.PRODUCED:
    if (ROOT / rel).is_file():
        continue
    if rel.startswith("reports/stage3_g2_attempt2/STAGE_3_G2_A2_"):
        print("  --   %-64s written by the build itself" % rel)
    else:
        bad("produced path exists before the build", rel)
ok("frozen inputs: %d" % len(mod.FROZEN_INPUTS))
ok("produced: %d" % len(mod.PRODUCED))

print()
print("=== RESULT ===")
if problems:
    print("%d PROBLEM(S) -- fix before the real build:" % len(problems))
    for p in problems:
        print("  - %s" % p)
    raise SystemExit(1)
print("no problems found; the builder is safe to run for real")
