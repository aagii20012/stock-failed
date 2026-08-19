"""Verify the Attempt 3 seal from disk, independently of the sealer that wrote it.

The sealer prints a summary; a summary is an assertion.  Everything here is recomputed from the
bytes on disk with no import of the sealer module, so a defect in the sealer's own reporting cannot
hide behind it.  Nothing is written.
"""

import hashlib
import json
import pathlib
import re

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
GOV = ROOT / "governance" / "generation_2"
MD = GOV / "STAGE_3_G2_ROTATION_RA3_PROTOCOL.md"
JS = GOV / "STAGE_3_G2_ROTATION_RA3_PROTOCOL.json"
SH = GOV / "STAGE_3_G2_ROTATION_RA3_PROTOCOL.sha256"

problems = []


def check(label, ok, detail=""):
    print("  %-58s %s %s" % (label, "OK  " if ok else "FAIL", detail))
    if not ok:
        problems.append(label)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


print("=" * 96)
print("1. the three companions exist and the payload is uniformly CRLF")
for path in (MD, JS, SH):
    check("exists  %s" % path.name, path.exists())
raw = JS.read_bytes()
lf, crlf = raw.count(b"\n"), raw.count(b"\r\n")
check("JSON is uniformly CRLF", lf == crlf and crlf > 0, "LF %d CRLF %d bare %d" % (lf, crlf, lf - crlf))
shraw = SH.read_bytes()
check("sha256 record is LF-only", shraw.count(b"\r\n") == 0,
      "LF %d CRLF %d" % (shraw.count(b"\n"), shraw.count(b"\r\n")))
mdraw = MD.read_bytes()
check("Markdown is LF-only", mdraw.count(b"\r\n") == 0,
      "%d bytes, LF %d" % (len(mdraw), mdraw.count(b"\n")))

print()
print("=" * 96)
print("2. every line of the .sha256 record re-verified against the file it names")
lines = [ln for ln in SH.read_text("utf-8").splitlines() if ln.strip()]
covered = {}
for line in lines:
    want, _, name = line.partition("  ")
    covered[name.strip()] = want.strip()
print("  record covers %d entries" % len(covered))
for name, want in sorted(covered.items()):
    target = ROOT / name
    if not target.exists():
        check("covered %s" % name, False, "MISSING from disk")
        continue
    got = digest(target)
    check("covered %s" % name, got == want, got[:16])
check("record does not hash itself", SH.name not in " ".join(covered), "%d entries" % len(covered))
check("record covers the JSON it accompanies",
      any(n.endswith("STAGE_3_G2_ROTATION_RA3_PROTOCOL.json") for n in covered))
check("record covers the Markdown it accompanies",
      any(n.endswith("STAGE_3_G2_ROTATION_RA3_PROTOCOL.md") for n in covered))

print()
print("=" * 96)
print("3. the record's own claims, recomputed")
record = json.loads(raw.decode("utf-8"))
check("top-level keys", len(record) == 52, str(len(record)))
check("artifact_id", record["artifact_id"] == "SE100-GOV-2007", record["artifact_id"])
check("attempt is 3", record["attempt"] == 3, str(record["attempt"]))
# This one is False on purpose and the assertion is written to demand exactly that.  The attempt was
# designed after both prior results were known; True here would be the dishonest value, and the
# verifier that "passed" by finding it would have certified a false claim.  The paired note is what
# makes the False disclosure rather than omission, so its presence is part of the check.
check("sealed_before_any_strategy_code is True", record["sealed_before_any_strategy_code"] is True)
check("sealed_before_any_variant_is_run is True", record["sealed_before_any_variant_is_run"] is True)
check("sealed_before_any_result_was_seen is False (honest value)",
      record["sealed_before_any_result_was_seen"] is False)
check("...and it carries its explanatory note",
      len(record.get("sealed_before_any_result_was_seen_note", "")) > 80
      and "adaptation_disclosure" in record["sealed_before_any_result_was_seen_note"])
check("live_trading_authorized is false", record["live_trading_authorized"] is False)
check("stage_4_authorized is false", record["stage_4_authorized"] is False)
check("holdout_read_authorized is false", record["holdout_read_authorized"] is False)
check("grid is 18 x 2 = 36", record["grid"]["size"] == 18 and record["grid"]["total_runs"] == 36,
      "%s x %s" % (record["grid"]["size"], record["grid"]["runs_per_variant"]))
check("ladder has 3 bands", len(record["risk_architecture"]["ladder_bands"]) == 3)
check("selection rule is SEL-2",
      record["representative_selection_rule"]["id"] == "SE100-G2-SEL-2",
      record["representative_selection_rule"]["id"])
check("SEL-2 declares exactly the 6 sealed field names",
      tuple(record["representative_selection_rule"]["structural_enforcement"]["field_names"])
      == ("variant_id", "shutdown_events", "fill_count", "ladder_descents",
          "lockout_arms", "stops_filled"))
check("selection rule is return-blind",
      record["representative_selection_rule"]["return_blind"] is True)

tokens = (record["gate"]["pass_token"], record["gate"]["fail_token"])
excluded = record["gate"]["prior_attempt_tokens_extracted_and_excluded"]
check("both tokens name ATTEMPT_3", all("ATTEMPT_3" in t for t in tokens), " / ".join(tokens))
check("tokens disjoint from the 4 excluded", not (set(tokens) & set(excluded)),
      "%d excluded" % len(excluded))
check("exactly 4 prior tokens excluded", len(excluded) == 4)

print()
print("=" * 96)
print("4. the tokens the sealer wrote are the tokens the sealed criteria file carries")
criteria = json.loads((ROOT / "config/generation_2/g2_gate_criteria_ra3.json").read_text("utf-8"))
deriv = criteria["verdict_token_derivation"]
print("  verdict_token_derivation keys: %s" % list(deriv))
on_disk = {v for v in deriv.values() if isinstance(v, str) and v.startswith("STAGE_3_G2")}
check("pass token is in the criteria file", record["gate"]["pass_token"] in on_disk)
check("fail token is in the criteria file", record["gate"]["fail_token"] in on_disk)

print()
print("=" * 96)
print("5. the mandated disclosure survived serialisation (never printed: cp1252 console)")
protocol = json.loads((ROOT / "config/generation_2/g2_rotation_ra3_protocol.json").read_text("utf-8"))
disc = record["adaptation_disclosure"]
check("length is 1507", len(disc) == 1507, str(len(disc)))
d16 = hashlib.sha256(disc.encode("utf-8")).hexdigest()[:16]
check("sha256 prefix is ce1d6476f4456231", d16 == "ce1d6476f4456231", d16)
check("byte-identical to the config", disc == protocol["adaptation_disclosure_verbatim"])
check("U+2014 count is 3", disc.count("\u2014") == 3, str(disc.count("\u2014")))
check("U+2212 count is 1", disc.count("\u2212") == 1, str(disc.count("\u2212")))
check("verbatim in the Markdown", disc.replace("\n", " ") in MD.read_text("utf-8").replace("\n", " "))

print()
print("=" * 96)
print("6. nothing hashes itself; the Markdown embeds no tree digest of its own")
mdtext = MD.read_text("utf-8")
md_digest = digest(MD)
check("Markdown does not contain its own digest", md_digest not in mdtext, md_digest[:16])
js_digest = digest(JS)
check("JSON does not contain its own digest", js_digest not in raw.decode("utf-8"), js_digest[:16])
check("JSON does not carry a repo_state_id at top level", "repo_state_id" not in record,
      "reproducibility-shaped keys: %s" % [k for k in record if "repo_state" in k])

print()
print("=" * 96)
print("7. the runs/ record was appended, and it is the only one for this stage")
STAGE = "stage_3_generation_2_rotation_attempt_3_preregistration"
found = []
for path in sorted((ROOT / "runs").glob("*.json")):
    body = json.loads(path.read_text("utf-8"))
    if body.get("stage") == STAGE:
        found.append((path, body))
check("exactly one runs/ record for this stage", len(found) == 1, str([p.name for p, _ in found]))
if found:
    path, body = found[0]
    print("  file              %s" % path.name)
    print("  run_id            %s" % body["run_id"])
    print("  timestamp_utc     %s" % body["timestamp_utc"])
    print("  repo_state_id     %s" % body["repo_state_id"])
    print("  code_hashes       %d" % len(body["code_hashes"]))
    print("  dataset_hashes    %d" % len(body["dataset_hashes"]))
    print("  notes             %d" % len(body["notes"]))
    check("holdout_state SEALED", body["holdout_state"] == "SEALED", body["holdout_state"])
    check("exit_status SEALED", body["exit_status"] == "SEALED", body["exit_status"])
    check("date_range ends 2021-07-31", body["date_range"][1] == "2021-07-31", str(body["date_range"]))
    check("run_id matches the record", body["run_id"] == record["run_id"], record["run_id"])
    check("repo_state_id is the dry-run value",
          body["repo_state_id"] == "30982ba8abb718385ddb904d94423844811f43ed2e3e00c62b6bbd2d44c7a377")

print()
print("=" * 96)
print("8. the contamination predicate still holds, re-measured from the tree")
strategy = protocol["strategy_id"]
scanned = named = 0
for base in (ROOT / "src" / "stockedge100", ROOT / "tests"):
    for path in sorted(base.rglob("*.py")):
        scanned += 1
        if strategy in path.read_text("utf-8"):
            named += 1
            print("  NAMES THE CANDIDATE: %s" % path)
check("python files scanned", scanned == 106, str(scanned))
check("no .py file names the candidate", named == 0, "%d" % named)
check("report dir still absent", not (ROOT.parent / "stockedge100" / "reports" / "stage3_g2_attempt3").exists())

print()
print("=" * 96)
print("9. the two closed attempts remain byte-identical to their own seal records")
for name in ("STAGE_3_G2_ROTATION_PROTOCOL.sha256", "STAGE_3_G2_ROTATION_RA1_PROTOCOL.sha256"):
    rec = GOV / name
    if not rec.exists():
        check(name, False, "MISSING")
        continue
    bad = 0
    entries = [ln for ln in rec.read_text("utf-8").splitlines() if ln.strip()]
    for line in entries:
        want, _, target = line.partition("  ")
        tp = ROOT / target.strip()
        if not tp.exists() or digest(tp) != want.strip():
            bad += 1
    check("%s all entries verify" % name, bad == 0, "%d entries, %d bad" % (len(entries), bad))

print()
print("=" * 96)
print("PROBLEMS: %s" % (problems or "none"))
