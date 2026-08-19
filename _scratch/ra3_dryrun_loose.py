"""Loose dry-run of g2_stage3_attempt3_package.build().

Purpose: exercise every field dereference the builder makes *before* the research report and the
pytest capture exist, so a wrong field name is found now — while the module is still free to edit —
rather than after the real build has recorded a repo_state_id that a later fix would invalidate.

Three things are stubbed, and only three:
  * build_stage_package  -> captures the StageDecision instead of writing anything
  * read_text            -> serves a synthetic pytest capture (the real one must postdate every
                            src/ and tests/ byte, so it cannot exist yet)
  * disclosure_carriage  -> the real function runs; the still-missing research report and the
                            pending decision record are then marked OK so the guard proceeds to the
                            code under test. The real carriage state is printed separately.

Everything else — every guard, every checksum record, both directions of G2A3-CONFLICT-30, the
evidence self-digest recomputation — runs for real.

ASCII output only: limitations[0] is the sealed disclosure and carries U+2212, which cp1252 cannot
encode.
"""

import dataclasses
import json
import pathlib
import sys
import traceback

SRC = "d:/Product/stock-trade-alpaca/stockedge100/src"
OUT = pathlib.Path("d:/Product/stock-trade-alpaca/_scratch")
sys.path.insert(0, SRC)

import stockedge100.reporting.g2_stage3_attempt3_package as g2p  # noqa: E402


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


SYNTHETIC_CAPTURE = (
    "$ cd stockedge100 && python -m pytest tests -q --collect-only\n"
    "1266 tests collected in 1.50s\n"
    "\n"
    "$ cd stockedge100 && python -m pytest tests -q\n"
    "1 failed, 1265 passed in 33.00s\n"
)

captured = {}


class FakeResult:
    run_id = "SE100-R-DRYRUN"
    repo_state_id = "0" * 64
    timestamp_utc = "DRY-RUN-NO-CLOCK-READ"
    freeze_ok = True
    checksum_digest = "0" * 64

    def __init__(self, root):
        self.decision_path = root / "reports/DRYRUN/decision.json"
        self.manifest_path = root / "reports/DRYRUN/manifest.json"
        self.checksum_path = root / "reports/DRYRUN/record.sha256"
        self.run_record_path = root / "runs/DRYRUN.json"


def fake_build_stage_package(decision):
    captured["decision"] = decision
    return FakeResult(g2p.PROJECT_ROOT)


real_read_text = g2p.read_text


def fake_read_text(rel):
    if rel == g2p.PYTEST_CAPTURE:
        return SYNTHETIC_CAPTURE
    return real_read_text(rel)


real_carriage = g2p.disclosure_carriage


def fake_carriage(protocol, ev):
    state = real_carriage(protocol, ev)
    captured["carriage_real"] = json.loads(json.dumps(state))
    pending = (
        "reports/stage3_g2_attempt3/STAGE_3_G2_A3_ROTATION_RESEARCH.json",
        g2p.REPORT,
    )
    for rel in pending:
        if rel in state["carriers"]:
            state["carriers"][rel] = {
                "present": True,
                "carries_verbatim": True,
                "carries_byte_exact": True,
                "how": "DRY RUN STUB",
                "file_sha256": "0" * 64,
            }
    state["all_carriers_verbatim"] = all(
        c["carries_verbatim"] for c in state["carriers"].values()
    )
    state["all_carriers_byte_exact"] = all(
        c["carries_byte_exact"] for c in state["carriers"].values()
    )
    state["carriers_requiring_normalisation"] = [
        rel
        for rel, c in state["carriers"].items()
        if c["present"] and c["carries_verbatim"] and not c["carries_byte_exact"]
    ]
    return state


g2p.build_stage_package = fake_build_stage_package
g2p.read_text = fake_read_text
g2p.disclosure_carriage = fake_carriage

print("== real carriage state (before the stub) ==")
try:
    real_state = real_carriage(
        g2p.load(g2p.PROTOCOL), g2p.load(g2p.EVIDENCE)
    )
    print("  characters                %d" % real_state["characters"])
    print("  sha256_of_utf8            %s" % real_state["sha256_of_utf8"])
    print("  digest_agrees_with_ev     %s" % real_state["digest_agrees_with_evidence"])
    for rel, c in real_state["carriers"].items():
        print(
            "  %-72s present=%-5s verbatim=%-5s byte_exact=%s"
            % (rel, c["present"], c["carries_verbatim"], c["carries_byte_exact"])
        )
except Exception:
    print(safe(traceback.format_exc()))

print("\n== build() under the stubs ==")
code = None
try:
    code = g2p.build()
    print("  return code: %s" % code)
except Exception:
    print(safe(traceback.format_exc()))

decision = captured.get("decision")
if decision is None:
    print("\nNO StageDecision WAS ASSEMBLED - fix the failure above and re-run")
    raise SystemExit(1)

body = dataclasses.asdict(decision)
text = json.dumps(body, indent=1, default=str, ensure_ascii=False)
(OUT / "ra3_dryrun_decision.json").write_text(text, encoding="utf-8", newline="\n")

lines = []
lines.append("=== StageDecision scalars ===")
for key in sorted(body):
    value = body[key]
    if isinstance(value, (str, int, float, bool)) or value is None:
        lines.append("%-28s %s" % (key, safe(value)[:400]))
    else:
        lines.append("%-28s <%s len=%d>" % (key, type(value).__name__, len(value)))

lines.append("")
lines.append("=== gate_conditions: keys in order ===")
for key in body["gate_conditions"]:
    lines.append("  %s" % key)

lines.append("")
lines.append("=== gate_conditions: the seven hard rows ===")
for key, row in body["gate_conditions"].items():
    if key == "admissible_candidate_exists":
        continue
    lines.append("  --- %s ---" % key)
    for field in (
        "verdict",
        "satisfied",
        "gating_runs",
        "satisfied_by",
        "met_by",
        "not_met_by",
        "not_evaluable_for",
        "not_applicable_for",
        "measured",
        "threshold",
        "reported_not_gating",
        "predicate",
    ):
        lines.append("      %-22s %s" % (field, safe(json.dumps(row[field], default=str))[:400]))
    lines.append("      %-22s %s" % ("required_verbatim", safe(row["required_verbatim"])[:400]))

lines.append("")
lines.append("=== gate_conditions.admissible_candidate_exists ===")
row = body["gate_conditions"]["admissible_candidate_exists"]
for field in sorted(row):
    lines.append("  %-44s %s" % (field, safe(json.dumps(row[field], default=str))[:900]))

lines.append("")
lines.append("=== evidence bullets (%d) ===" % len(body["evidence"]))
for i, bullet in enumerate(body["evidence"], 1):
    lines.append("  [%02d] %s" % (i, safe(bullet)))
    lines.append("")

lines.append("=== limitations (%d) ===" % len(body["limitations"]))
for i, item in enumerate(body["limitations"], 1):
    lines.append("  [%02d] %s" % (i, safe(item)[:600]))
    lines.append("")

lines.append("=== conflicts_found (%d) ===" % len(body["conflicts_found"]))
for i, item in enumerate(body["conflicts_found"], 1):
    lines.append("  [%02d] %s" % (i, safe(item)))
    lines.append("")

lines.append("=== run_notes (%d) ===" % len(body["run_notes"]))
for i, item in enumerate(body["run_notes"], 1):
    lines.append("  [%02d] %s" % (i, safe(item)))
    lines.append("")

lines.append("=== body keys ===")
for key in sorted(body["body"]):
    value = body["body"][key]
    if isinstance(value, (str, int, float, bool)) or value is None:
        lines.append("  %-46s %s" % (key, safe(value)[:200]))
    else:
        lines.append("  %-46s <%s len=%d>" % (key, type(value).__name__, len(value)))

lines.append("")
lines.append("=== lint: a dict or a Python repr rendered into prose ===")
lines.append("  (some are deliberate - own_quantities, bands_removed_from_ra2 - so each is judged,")
lines.append("   not merely counted; what this catches is a scalar field name that is really a node)")
hits = 0
for field in ("evidence", "limitations", "conflicts_found", "run_notes"):
    for i, item in enumerate(body[field], 1):
        for marker in ("{'", '{"', ": '", "': "):
            if marker in item:
                start = max(0, item.index(marker) - 60)
                lines.append(
                    "  %-16s [%02d] %r ... %s"
                    % (field, i, marker, safe(item[start:start + 200]))
                )
                hits += 1
                break
lines.append("  total flagged: %d" % hits)

lines.append("")
lines.append("=== lint: every 64-hex string in the prose fields ===")
import re  # noqa: E402

for field in ("evidence", "limitations", "conflicts_found", "run_notes"):
    for i, item in enumerate(body[field], 1):
        for digest in re.findall(r"\b[0-9a-f]{64}\b", item):
            lines.append("  %-16s [%02d] %s" % (field, i, digest))

lines.append("")
lines.append("=== tests / dates / config ===")
lines.append("  tests            %s" % safe(body["tests"]))
lines.append("  date_range       %s" % safe(body["date_range"]))
lines.append("  universe_version %s" % safe(body["universe_version"]))
lines.append("  config_hash      %s" % safe(body["config_hash"]))
lines.append("  holdout_state    %s" % safe(body["holdout_state"]))
lines.append("  gate_id          %s" % safe(body["gate_id"]))
lines.append("  gate_name        %s" % safe(body["gate_name"]))
lines.append("  gate_passed      %s" % safe(body["gate_passed"]))
lines.append("  generation       %s" % safe(body["generation"]))
lines.append("  return_code      %s" % code)

(OUT / "ra3_dryrun_report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
print("\nwrote _scratch/ra3_dryrun_report.txt (%d lines) and ra3_dryrun_decision.json (%d chars)"
      % (len(lines), len(text)))
