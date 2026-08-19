"""Generate STAGE_3_G2_ROTATION_RA3_PROTOCOL.md from the sealed configs.

Every value in the emitted document is read from SE100-CFG-3105, SE100-CFG-3106,
Generation 1's sealed protocol config, or computed here and validated against an
artifact already on disk.  Only the section framing is authored in this file.
That is deliberate: CLAUDE.md records that a Stage 3 draft once reproduced a
determinism table from memory and every digest in it was invented.  Nothing here
is typed from memory.

Emits to _scratch/RA3_PROTOCOL_DRAFT.md.  The console output is ASCII only and
never contains the document body, because stdout is cp1252 and the document
carries U+2014 and U+2212.
"""

import hashlib
import json
import pathlib
import re
import sys
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_EVEN

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
OUT = pathlib.Path("d:/Product/stock-trade-alpaca/_scratch/RA3_PROTOCOL_DRAFT.md")

DOCUMENT_ID = "SE100-GOV-2007"
ADAPTATION_DISCLOSURE_SHA256 = (
    "ce1d6476f44562310fb059c5817645baa25477cc4f6168b414f3423834c8e925")

EM = "\u2014"

P = json.loads((ROOT / "config/generation_2/g2_rotation_ra3_protocol.json")
               .read_text(encoding="utf-8"))
C = json.loads((ROOT / "config/generation_2/g2_gate_criteria_ra3.json")
               .read_text(encoding="utf-8"))
G1 = json.loads((ROOT / "config/stage3_attempt2_strategy_protocol.json")
                .read_text(encoding="utf-8"))
SEALED_A2_MD = (ROOT / "governance/generation_2/STAGE_3_G2_ROTATION_RA1_PROTOCOL.md"
                ).read_text(encoding="utf-8")

RA = P["risk_architecture"]
COMP = RA["components"]
SEL = P["representative_selection_rule"]
GRID = P["grid"]

NOTES = []


def note(msg):
    NOTES.append(msg)


# --------------------------------------------------------------------------
# small renderers
# --------------------------------------------------------------------------

def cell(v):
    """A value flattened to one table cell."""
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    return s.replace("|", "\\|").replace("\n", " ").strip()


def label(k):
    s = k.replace("_", " ")
    for a, b in (("ra3", "RA3"), ("ra2", "RA2"), ("ra1", "RA1"),
                 ("sha256", "SHA-256"), ("json", "JSON"), ("md ", "Markdown "),
                 ("sel 2", "SEL-2")):
        s = s.replace(a, b)
    return s[:1].upper() + s[1:]


def field_table(pairs, header=("Field", "Value")):
    out = ["| %s | %s |" % header, "|---|---|"]
    for k, v in pairs:
        out.append("| %s | %s |" % (k, v))
    return "\n".join(out)


def deep_bullets(node, depth=0):
    """A JSON subtree as nested Markdown bullets.

    The gate criteria's condition bodies are not flat: S3-C5's measurement is a
    dict of a basis, a four-step procedure and five prose qualifications, and
    S3-C7's is a dict of nine.  Flattening those through cell() emits a
    single-line JSON blob, which is exactly the shape a reader cannot audit -
    and this document exists to be audited.  Rendered structurally instead, at
    the cost of nothing, since the source is still the file.

    Short string lists stay inline: a list of seven condition ids reads better
    as one line than as seven bullets.
    """
    pad = "  " * depth
    if isinstance(node, dict):
        out = []
        for k, v in node.items():
            flat = _inline(v)
            if flat is None:
                out.append("%s- *%s*" % (pad, label(k)))
                out.append(deep_bullets(v, depth + 1))
            else:
                out.append("%s- *%s* %s %s" % (pad, label(k), EM, flat))
        return "\n".join(out)
    if isinstance(node, list):
        out = []
        for item in node:
            flat = _inline(item)
            if flat is None:
                out.append("%s-" % pad)
                out.append(deep_bullets(item, depth + 1))
            else:
                out.append("%s- %s" % (pad, flat))
        return "\n".join(out)
    return "%s- %s" % (pad, cell(node))


def _inline(v):
    """One line for v, or None if v must be rendered structurally."""
    if isinstance(v, str):
        return cell(v)
    if isinstance(v, (bool, int, float)) or v is None:
        return "`%s`" % json.dumps(v, ensure_ascii=False)
    if isinstance(v, list) and v and all(
            isinstance(x, (str, int, float, bool)) and len(str(x)) <= 48 for x in v):
        return ", ".join("`%s`" % (x if isinstance(x, str)
                                   else json.dumps(x, ensure_ascii=False)) for x in v)
    if isinstance(v, list) and not v:
        return "(empty)"
    return None


# Every render call registers which keys of which node it consumed, so the run
# reports both keys asked for that do not exist and keys that exist and were
# never rendered.  A silently dropped field is the failure mode this catches.
CONSUMED = {}
MISSING = []
PATHMAP = {}


def index_paths(node, prefix):
    """id(node) -> dotted path, so a render call names itself without the call
    site having to repeat the path."""
    if isinstance(node, dict):
        PATHMAP.setdefault(id(node), prefix)
        for k, v in node.items():
            index_paths(v, "%s.%s" % (prefix, k) if prefix else k)
    elif isinstance(node, list):
        PATHMAP.setdefault(id(node), prefix)
        for i, v in enumerate(node):
            index_paths(v, "%s[%d]" % (prefix, i))


index_paths(P, "protocol")
index_paths(C, "criteria")


NODES = {}


def track(d, keys, name):
    key = id(d)
    name = PATHMAP.get(key, name)
    NODES[key] = (name, d)
    got = CONSUMED.setdefault(key, set())
    present = []
    for k in keys:
        if isinstance(d, dict) and k in d:
            got.add(k)
            present.append(k)
        else:
            MISSING.append("%s.%s" % (name, k))
    return present


def keys_table(d, keys, header=("Field", "Value"), name="?"):
    keys = track(d, keys, name)
    return field_table([(label(k), cell(d[k])) for k in keys], header)


def paras(d, keys, name="?"):
    """Long prose fields as labelled paragraphs, lists as bullets."""
    keys = track(d, keys, name)
    out = []
    for k in keys:
        v = d[k]
        if isinstance(v, list):
            body = "\n".join("- %s" % (x if isinstance(x, str)
                                       else json.dumps(x, ensure_ascii=False))
                             for x in v)
            out.append("**%s.**\n\n%s" % (label(k), body))
        elif isinstance(v, dict):
            body = "\n".join("- *%s* %s %s" % (label(kk), EM, cell(vv))
                             for kk, vv in v.items())
            out.append("**%s.**\n\n%s" % (label(k), body))
        elif v is None:
            out.append("**%s.** `null`" % label(k))
        elif isinstance(v, bool):
            out.append("**%s.** `%s`" % (label(k), str(v).lower()))
        else:
            out.append("**%s.** %s" % (label(k), v))
    return "\n\n".join(out)


def dec(v):
    return Decimal(str(v))


def d9(v):
    return dec(v).quantize(Decimal("0.000000001"), rounding=ROUND_HALF_EVEN)


def d3(v):
    """The sealed Attempt 2 tables print an absolute ceiling to three decimals.
    Comparison stays at nine; only presentation is narrowed, and narrowing it is
    what makes the row-for-row check against that table possible."""
    return dec(v).quantize(Decimal("0.000"), rounding=ROUND_HALF_EVEN)


def sha256_text(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# the two mandated disclosures, taken from their sealed sources
# --------------------------------------------------------------------------

ADAPTATION = P["adaptation_disclosure_verbatim"]
got = sha256_text(ADAPTATION)
assert got == ADAPTATION_DISCLOSURE_SHA256, "adaptation disclosure digest moved: %s" % got
note("adaptation disclosure  : digest matches (%d chars, %d words)"
     % (len(ADAPTATION), len(ADAPTATION.split())))

# Imported unconditionally, not inside a try.  An earlier revision wrapped this
# in try/except and fell back to the sealed blockquote, which meant a mistyped
# module path (backtest/ instead of reporting/) silently downgraded the
# agreement assertion below to a no-op for two whole runs.  The module is a
# governed file; if it ever moves, this generator must stop rather than quietly
# accept a single unchecked source.
sys.path.insert(0, str(ROOT / "src"))
from stockedge100.reporting.g2_partition_lock import (  # noqa: E402
    VALIDATION_REUSE_DISCLOSURE as VALIDATION_REUSE,
)

note("validation-reuse text  : imported from reporting/g2_partition_lock.py")

block = re.search(r"### 14\.2[^\n]*\n(.*?)(?=\n## |\n\*Machine companion)",
                  SEALED_A2_MD, re.S)
assert block, "could not locate section 14.2 in the sealed Attempt 2 document"
quoted = "\n".join(ln[2:] if ln.startswith("> ") else ln[1:] if ln.startswith(">") else ln
                   for ln in block.group(1).splitlines() if ln.startswith(">"))
quoted = quoted.strip()
assert quoted, "section 14.2 blockquote came back empty"
assert VALIDATION_REUSE.strip(), "the module constant is empty"
same = " ".join(VALIDATION_REUSE.split()) == " ".join(quoted.split())
note("validation-reuse text  : module (%d ch) vs sealed blockquote (%d ch) agree = %s"
     % (len(VALIDATION_REUSE.strip()), len(quoted), same))
assert same, "the module constant and the sealed Attempt 2 blockquote disagree"


def blockquote(text):
    return "\n".join(("> " + ln).rstrip() if ln else ">"
                     for ln in text.splitlines())


def verdict(v):
    """Render a config verdict string the way the sealed documents render it.

    The configs store verdicts ASCII-safe (`FAIL - TOKEN`) so that no JSON artifact depends on a
    non-ASCII byte; SE100-GOV-2003 and SE100-GOV-2005 both render the separator as an em dash in
    prose.  The Attempt 3 sealer reverses this substitution to check the document, so passing a
    config value through unrendered is a refusal, not a cosmetic difference.
    """
    return v.replace(" - ", " %s " % EM)


# --------------------------------------------------------------------------
# Generation 1's sealed RA1-5 ladder, parsed from its own config
# --------------------------------------------------------------------------

G1_LADDER = G1["risk_architecture"]["RA1-5"]
g1_rungs = []
for line in G1_LADDER["rule"]:
    m = re.match(r"^(.*?): f_cap = ([0-9.]+)\.$", line.strip())
    if not m:
        continue
    cond, fcap = m.group(1).strip(), dec(m.group(2))
    lo = re.match(r"^([0-9.]+) <= dd", cond)
    hi = re.search(r"dd < ([0-9.]+)$", cond)
    ge = re.match(r"^dd >= ([0-9.]+)$", cond)
    if ge:
        lower, upper = dec(ge.group(1)), None
    else:
        lower = dec(lo.group(1)) if lo else Decimal("0.00")
        upper = dec(hi.group(1)) if hi else None
    g1_rungs.append({"cond": cond, "f_cap": fcap, "lower": lower, "upper": upper})
assert len(g1_rungs) == 3, "expected three Generation 1 rungs, parsed %d" % len(g1_rungs)
note("G1 RA1-5 rungs parsed  : %s"
     % ", ".join("%s -> %s" % (r["cond"], r["f_cap"]) for r in g1_rungs))

F_BASE = dec(COMP["RA3-1"]["value"])
note("RA3-1 f_base           : %s" % F_BASE)

RA3_BANDS = COMP["RA3-4"]["bands"]
assert len(RA3_BANDS) == 3, "RA3-4 must carry three bands, carries %d" % len(RA3_BANDS)


def band_bounds(b):
    lo = dec(b["dd_from"])
    hi = None if b["dd_to_exclusive"] is None else dec(b["dd_to_exclusive"])
    return lo, hi


prov_rows = []
all_same = True
for b in RA3_BANDS:
    lo, hi = band_bounds(b)
    scalar = dec(b["scalar"])
    ceiling = d9(F_BASE * scalar)
    match = [r for r in g1_rungs if r["lower"] == lo and r["upper"] == hi]
    same = bool(match) and d9(match[0]["f_cap"]) == ceiling
    all_same = all_same and same
    cond = ("`dd < %s`" % hi) if lo == 0 else (
        "`dd >= %s`" % lo if hi is None else "`%s <= dd < %s`" % (lo, hi))
    g1_cell = ("%s (`%s`)" % (d3(match[0]["f_cap"]), match[0]["cond"])) if match else "no rung"
    prov_rows.append("| %d | %s | %s | %s | %s | %s |"
                     % (b["band"], cond, scalar, d3(ceiling), g1_cell, "yes" if same else "**no**"))
note("provenance rows        : %d, all same = %s" % (len(prov_rows), all_same))
assert all_same, "RA3-4 does not reproduce Generation 1's RA1-5 ceilings"


# --------------------------------------------------------------------------
# the worst-case ladder walk, validated against the sealed Attempt 2 table
# --------------------------------------------------------------------------

STOP = dec(COMP["RA3-3"]["value"])
note("RA3-3 stop             : %s" % STOP)

try:
    A2 = json.loads((ROOT / "config/generation_2/g2_rotation_ra1_protocol.json")
                    .read_text(encoding="utf-8"))
    ra2_bands = A2["risk_architecture"]["components"]["RA2-4"]["bands"]
    RA2_WALK = [(dec(b["dd_from"]),
                 None if b["dd_to_exclusive"] is None else dec(b["dd_to_exclusive"]),
                 d9(F_BASE * dec(b["scalar"])), str(b["band"])) for b in ra2_bands]
    note("RA2 bands              : read from SE100-CFG-3103 (%d)" % len(RA2_WALK))
except Exception as exc:  # noqa: BLE001
    RA2_WALK = [(Decimal("0.00"), Decimal("0.05"), Decimal("0.500"), "0"),
                (Decimal("0.05"), Decimal("0.08"), Decimal("0.375"), "1"),
                (Decimal("0.08"), Decimal("0.10"), Decimal("0.250"), "2"),
                (Decimal("0.10"), None, Decimal("0.125"), "3")]
    note("RA2 bands              : config read failed (%s), using the "
         "previously validated literals" % type(exc).__name__)

RA3_WALK = [(band_bounds(b)[0], band_bounds(b)[1],
             d9(F_BASE * dec(b["scalar"])), str(b["band"])) for b in RA3_BANDS]

BREACH = Decimal("0.15")


def pct(x, places="0.0001"):
    return (x * 100).quantize(Decimal(places), rounding=ROUND_HALF_EVEN)


def walk(bands, limit=40):
    equity, rows = Decimal(1), []
    for trip in range(1, limit + 1):
        dd_before = Decimal(1) - equity
        scalar, lab = next((s, l) for lo, hi, s, l in bands
                           if dd_before >= lo and (hi is None or dd_before < hi))
        loss = scalar * STOP
        equity *= (Decimal(1) - loss)
        dd_after = Decimal(1) - equity
        rows.append((trip, dd_before, lab, scalar, loss, dd_after, dd_after >= BREACH))
        if dd_after >= BREACH:
            break
    return rows


def render_walk(rows, dash):
    out = []
    for trip, dd_before, lab, scalar, loss, dd_after, breached in rows:
        after = ("**%s%% %s breach**" % (pct(dd_after), dash)) if breached \
            else "%s%%" % pct(dd_after)
        out.append("| %d | %s%% | %s | %s | %s%% | %s |"
                   % (trip, pct(dd_before), lab, d3(scalar), pct(loss, "0.000"), after))
    return out


sealed_block = re.search(r"\| Trip \| `dd` before \|.*?\n\n", SEALED_A2_MD, re.S).group(0)
sealed_rows = [ln.replace(EM, "-") for ln in sealed_block.splitlines()
               if ln.startswith("| ") and not ln.startswith("| Trip")]
ra2_rows = render_walk(walk(RA2_WALK), "-")
assert len(ra2_rows) == len(sealed_rows), (
    "walk model row count %d != sealed %d" % (len(ra2_rows), len(sealed_rows)))
bad = [i for i, (g, w) in enumerate(zip(ra2_rows, sealed_rows), 1) if g != w]
assert not bad, "walk model disagrees with the sealed Attempt 2 table at rows %s" % bad
note("walk model             : VALIDATED against the sealed Attempt 2 table (%d rows)"
     % len(ra2_rows))

ra3_walk = walk(RA3_WALK)
RA3_TRIPS, RA2_TRIPS = len(ra3_walk), len(ra2_rows)
ra3_walk_rows = render_walk(ra3_walk, EM)
touched = sorted({r[2] for r in ra3_walk})
skipped = sorted({str(b["band"]) for b in RA3_BANDS} - set(touched))
note("RA3 walk               : %d trips to breach (RA2 %d), bands touched %s, skipped %s"
     % (RA3_TRIPS, RA2_TRIPS, touched, skipped or ["none"]))


# --------------------------------------------------------------------------
# the SE100-G2-SEL-2 neighbourhood, enumerated from the sealed grid
# --------------------------------------------------------------------------

VARIANTS = GRID["variants"]
assert len(VARIANTS) == GRID["size"] == 18, "grid size moved"
LOOKBACKS = GRID["axes"]["lookback_months"]
KS = GRID["axes"]["top_k"]
FREQS = GRID["axes"]["rebalance_frequency"]

by_key = {(v["lookback_months"], v["top_k"], v["rebalance_frequency"]): v for v in VARIANTS}
assert len(by_key) == 18, "grid keys are not unique"


def neighbours(v):
    out = []
    lb, k, fq = v["lookback_months"], v["top_k"], v["rebalance_frequency"]
    i, j = LOOKBACKS.index(lb), KS.index(k)
    for step in (-1, 1):
        if 0 <= i + step < len(LOOKBACKS):
            out.append(by_key[(LOOKBACKS[i + step], k, fq)])
        if 0 <= j + step < len(KS):
            out.append(by_key[(lb, KS[j + step], fq)])
    other = FREQS[1 - FREQS.index(fq)]
    out.append(by_key[(lb, k, other)])
    return sorted(out, key=lambda x: x["variant_id"])


NEIGHBOURS = {v["variant_id"]: [n["variant_id"] for n in neighbours(v)] for v in VARIANTS}
for vid, ns in NEIGHBOURS.items():
    assert len(set(ns)) == len(ns), "duplicate neighbour for %s" % vid
    assert vid not in ns, "%s is its own neighbour" % vid
asym = [(a, b) for a, ns in NEIGHBOURS.items() for b in ns if a not in NEIGHBOURS[b]]
assert not asym, "neighbour relation is not symmetric: %s" % asym[:3]

partition = {}
for ns in NEIGHBOURS.values():
    partition[len(ns)] = partition.get(len(ns), 0) + 1
note("neighbour partition    : %s (symmetric, %d variants)"
     % (dict(sorted(partition.items())), len(NEIGHBOURS)))
assert sorted(partition.items()) == [(3, 8), (4, 8), (5, 2)], (
    "computed partition %s does not match the sealed 8/8/2" % sorted(partition.items()))
note("neighbour partition    : matches the sealed 3->8, 4->8, 5->2")

nb_rows = ["| %d | %d | %s |" % (n, partition[n],
                                ", ".join("`%s`" % v for v in sorted(
                                    vid for vid, ns in NEIGHBOURS.items() if len(ns) == n)[:2])
                                + (", ..." if partition[n] > 2 else ""))
           for n in sorted(partition)]


# --------------------------------------------------------------------------
# section bodies
# --------------------------------------------------------------------------

AUTHORED = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
note("authored (UTC)         : %s  [read from the system clock at emit time]" % AUTHORED)

S = []


def sec(text):
    S.append(text.rstrip())


sec("# Stage 3 (Generation 2, Attempt 3) %s cross-sectional rotation under risk architecture "
    "RA3 and representative-selection rule SE100-G2-SEL-2" % EM)

sec(field_table([
    ("Document id", "`%s`" % DOCUMENT_ID),
    ("Status", "`SEALED`"),
    ("Project", P["project"]),
    ("Generation", str(P["generation"])),
    ("Generation id", "`%s`" % P["generation_id"]),
    ("Stage", str(P["stage"])),
    ("Gate", "3 %s development admissibility" % EM),
    ("Attempt", str(P["attempt"])),
    ("Authored (UTC)", AUTHORED),
    ("Charter", "[STAGE_10_GENERATION_2_CHARTER.md](STAGE_10_GENERATION_2_CHARTER.md) "
                "(`SE100-GOV-2001`)"),
    ("Partition lock", "[STAGE_1_G2_PARTITION_LOCK.md](STAGE_1_G2_PARTITION_LOCK.md) "
                       "(`SE100-GOV-2002`)"),
    ("Attempt 1 protocol", "[STAGE_3_G2_ROTATION_PROTOCOL.md](STAGE_3_G2_ROTATION_PROTOCOL.md) "
                           "(`SE100-GOV-2003`) %s closed, read-only" % EM),
    ("Attempt 2 protocol",
     "[STAGE_3_G2_ROTATION_RA1_PROTOCOL.md](STAGE_3_G2_ROTATION_RA1_PROTOCOL.md) "
     "(`SE100-GOV-2005`) %s closed, read-only" % EM),
    ("Constitution", "`SE100-GOV-0001` %s" % P["constitution_ref"].split("sections", 1)[-1].strip()
     if "sections" in P["constitution_ref"] else "`%s`" % P["constitution_ref"]),
    ("Machine companion", "`STAGE_3_G2_ROTATION_RA3_PROTOCOL.json`, sealed by "
                          "`STAGE_3_G2_ROTATION_RA3_PROTOCOL.sha256`"),
    ("Source of record", "`config/generation_2/g2_rotation_ra3_protocol.json` "
                         "(`%s`)" % P["artifact_id"]),
    ("Gate criteria", "`%s` (`%s`)" % (P["gate_criteria_ref"], C["artifact_id"])),
    ("`live_trading_authorized`", "`%s`" % str(P["live_trading_authorized"]).lower()),
]))

sec(P["declaration_note"])

sec("This is the third attempt at Gate 3 in Generation 2 and the third disclosed adaptation on "
    "one hypothesis family. It changes exactly two things from Attempt 2 %s the de-risk ladder "
    "and the representative-selection rule %s and nothing else. Section 1 states both changes, "
    "section 14.1 carries the mandated adaptation disclosure verbatim, and section 12 declares "
    "the structural consequences of both changes before any variant is run." % (EM, EM))

# ---- 1 -------------------------------------------------------------------
sec("## 1. What is pre-registered")

sec(field_table([
    ("Strategy id", "`%s`" % P["strategy_id"]),
    ("Candidate index", str(P["candidate_index"])),
    ("Family", P["family"]),
    ("Attempt", str(P["attempt"])),
    ("Risk architecture", "`%s` %s %s" % (RA["id"], EM, RA["name"])),
    ("Selection rule", "`%s`" % SEL["id"]),
    ("Declared before any strategy code", "`%s`"
     % str(P["declared_before_any_strategy_code"]).lower()),
    ("Currency", P["currency"]),
]))

sec(paras(P, ["hypothesis", "candidate_index_note",
              "what_this_attempt_changes_from_attempt_2",
              "what_this_attempt_adds_over_attempt_1",
              "what_this_attempt_adds_over_attempt_1_carriage",
              "what_makes_this_genuinely_cross_sectional"]))

sec("### 1.1 Frozen inputs, re-verified at seal time")

digest_rows = [
    ("`governance/STAGE_0_CONSTITUTION.md`", P["constitution_md_sha256"]),
    ("`governance/STAGE_0_CONSTITUTION.json`", P["constitution_json_sha256"]),
    ("`%s`" % P["charter_ref"], P["charter_md_sha256"]),
    ("`%s`" % P["partition_lock_ref"], P["partition_lock_md_sha256"]),
    ("`%s` (JSON companion)" % P["partition_lock_ref"], P["partition_lock_json_sha256"]),
    ("`%s`" % P["cost_model_derivation_ref"], P["cost_model_derivation_sha256"]),
]
for ref_name, ref in (("Attempt 1", P["attempt_1_ref"]), ("Attempt 2", P["attempt_2_ref"])):
    for k, v in ref.items():
        if k.endswith("_sha256") and isinstance(v, str) and re.fullmatch(r"[0-9a-f]{64}", v):
            base = ref[k[:-len("_sha256")]] if k[:-len("_sha256")] in ref else k[:-len("_sha256")]
            digest_rows.append(("`%s` (%s)" % (base, ref_name), v))
sec(field_table(digest_rows, ("Artifact", "SHA-256")))
note("digest rows            : %d" % len(digest_rows))

sec(paras(P, ["refs_reverified"]))

sec("### 1.2 Mechanics carried unchanged")
sec(paras(P["mechanics_carried_unchanged"], ["method", "why_this_matters"]))
sec("\n".join("- `%s`" % b for b in P["mechanics_carried_unchanged"]["blocks"]))
track(P["mechanics_carried_unchanged"], ["blocks"], "mechanics_carried_unchanged")

sec("### 1.3 Serialisation")
sec(keys_table(P["serialisation"], list(P["serialisation"])))

# ---- 2 -------------------------------------------------------------------
EU = P["eligible_universe"]
sec("## 2. Eligible universe")
sec(keys_table(EU, ["source", "source_sha256", "universe_version",
                    "universe_identity_sha256", "member_count",
                    "unchanged_from_attempt_1"]))
members = EU["members"]
assert len(members) == EU["member_count"] == 34, "universe size moved"
half = len(members) // 2
sec("```\n" + "\n".join("%-8s %s" % (members[i], members[i + half]) for i in range(half)) + "\n```")
sec(paras(EU, ["eligibility_recheck_convention"]))
sec("**Excluded symbols.**\n\n"
    + "\n".join("- `%s` %s %s" % (k, EM, cell(v)) for k, v in EU["excluded_symbols"].items()))

# ---- 3 -------------------------------------------------------------------
RS = P["ranking_signal"]
sec("## 3. Ranking signal")
sec(keys_table(RS, ["name", "unchanged_from_attempt_1", "implementation_reuse"]))
sec("```\n%s\n```" % RS["formula"])
sec(paras(RS, ["look_ahead_note", "undefined_result"]))
sec(keys_table(P["ranking_rule"], ["sort_key", "tie_break", "unchanged_from_attempt_1"]))

# ---- 4 -------------------------------------------------------------------
PS = P["position_sizing"]
CC = P["concentration_ceiling"]
sec("## 4. Portfolio construction and position sizing")
sec(keys_table(P["position_count"], ["axis", "values", "unchanged_from_attempt_1"]))
sec(paras(PS, ["target_weight_formula", "changed_from_attempt_1", "attempt_1_formula",
               "why_changed"]))

weight_rows = ["| k | Target weight per position | Target gross exposure |", "|---|---|---|"]
for k in sorted(PS["target_weights"], key=int):
    weight_rows.append("| %s | %s | %s |"
                       % (k, d9(PS["target_weights"][k]), d9(PS["target_gross_exposure"][k])))
sec("\n".join(weight_rows))

sec(paras(PS, ["round_down_note", "equal_weight_is_an_entry_rule",
               "budget_evaluated_at_the_open", "attempt_1_k1_half_cash_bias_neutralised"]))
sec("### 4.1 Concentration ceiling")
sec(keys_table(CC, ["value", "source", "source_sha256", "scope", "unchanged_from_attempt_1"]))
sec(paras(CC, ["non_binding_note"]))

# ---- 5 -------------------------------------------------------------------
sec("## 5. Risk architecture `%s`" % RA["id"])
sec(keys_table(RA, ["id", "name", "frozen_before_any_variant_is_run",
                    "not_part_of_the_grid", "derived_from"]))
sec(paras(RA, ["provenance", "single_difference_from_ra2", "why_not_gridded"]))

sec("### 5.1 Provenance of the constants")
sec("The de-risk ladder is the one component that changed, and it changed by reverting. The table "
    "below is computed at generation time: the absolute ceiling column is `f_base * scalar` from "
    "this document's own band table, and the Generation 1 column is parsed out of "
    "`config/stage3_attempt2_strategy_protocol.json`'s sealed `RA1-5` rule list. The `Same?` "
    "column is the comparison of those two, not an assertion about them.")
sec("\n".join(
    ["| Band | Drawdown from HWM | Scalar | Absolute ceiling | Generation 1 `RA1-5` | Same? |",
     "|---|---|---|---|---|---|"] + prov_rows))
sec("Every row answers yes. Under RA2 the corresponding table had four rows and one of them "
    "answered no: band 1, `0.05 <= dd < 0.08` at scalar 0.75, which Generation 1's ladder did not "
    "have. Deleting it is this attempt's architectural change, and it leaves RA3 with no "
    "post-Attempt-1 degree of freedom in it at all.")

order = ["RA3-1", "RA3-2", "RA3-3", "RA3-4", "RA3-5"]
assert set(order) == set(COMP), "component set moved: %s" % sorted(COMP)

sec("### 5.2 `RA3-1` %s %s" % (EM, COMP["RA3-1"]["name"]))
sec(keys_table(COMP["RA3-1"], ["value", "unit", "purpose", "inherited_unchanged_from"]))
sec(paras(COMP["RA3-1"], ["definition"]))
for part, body in COMP["RA3-1"]["enforcement"].items():
    sec("**%s.**\n\n%s" % (label(part), "\n".join(
        "- *%s* %s %s" % (label(kk), EM, cell(vv)) for kk, vv in body.items())))
sec(paras(COMP["RA3-1"], ["carriage"]))

sec("### 5.3 `RA3-2` %s %s" % (EM, COMP["RA3-2"]["name"]))
sec(keys_table(COMP["RA3-2"], ["value", "unit", "purpose", "measured_on",
                               "inherited_unchanged_from"]))
sec(paras(COMP["RA3-2"], ["definition", "shape_note",
                          "why_the_equity_curve_and_not_a_price_series", "scalar",
                          "undefined_before_21_points", "run_start_note", "self_reference",
                          "carriage"]))

sec("### 5.4 `RA3-3` %s %s" % (EM, COMP["RA3-3"]["name"]))
sec(keys_table(COMP["RA3-3"], ["value", "unit", "purpose", "reference_price",
                               "inherited_unchanged_from"]))
sec(paras(COMP["RA3-3"], ["reference_price_definition", "condition", "evaluated_at", "exit_at",
                          "interaction_with_rebalance", "no_re_entry_bar", "measurement",
                          "carriage"]))

sec("### 5.5 `RA3-4` %s %s" % (EM, COMP["RA3-4"]["name"]))
sec(paras(COMP["RA3-4"], ["purpose", "derived_from", "inherited_unchanged_from",
                          "drawdown_definition"]))
sec("`Inherited unchanged from` is `null` for this component alone. The other four name the RA2 "
    "component they are byte-equal to; this one cannot, because it is the component that changed.")
sec("\n".join(["| Band | Condition | `f_ladder` |", "|---|---|---|"] + [
    "| %d | `%s` | %s |" % (
        b["band"],
        ("%s <= dd < %s" % (b["dd_from"], b["dd_to_exclusive"]))
        if b["dd_to_exclusive"] is not None else "dd >= %s" % b["dd_from"],
        b["scalar"])
    for b in RA3_BANDS]))
sec(paras(COMP["RA3-4"], ["boundary_convention", "descent", "recovery", "hysteresis_note",
                          "scalar", "measurement"]))
sec("**Provenance.**\n\n" + "\n".join(
    "- *%s* %s %s" % (label(kk), EM, cell(vv))
    for kk, vv in COMP["RA3-4"]["provenance"].items()))
sec("**Relationship to the shutdown threshold.**\n\n" + "\n".join(
    "- *%s* %s %s" % (label(kk), EM, cell(vv))
    for kk, vv in COMP["RA3-4"]["relationship_to_the_shutdown_threshold"].items()))

sec("The worst case is worth writing down before it is observed rather than after. Take a run "
    "that does nothing but lose the full %s per-position stop on the full permitted aggregate "
    "exposure, round trip after round trip, with no recovery between them. The equity compounds "
    "down and the ladder tightens as it goes. The table below is computed by the same model that "
    "reproduces Attempt 2's sealed nine-row table row for row; only the band table differs."
    % STOP)
sec("\n".join(["| Trip | `dd` before | Band | `f_cap` | Loss this trip | `dd` after |",
               "|---|---|---|---|---|---|"] + ra3_walk_rows))
sec("Under RA3 that walk reaches the 15%% research-shutdown threshold on trip **%d**; under RA2's "
    "four rungs it took **%d**. RA3 is the shallower brake and it is meant to be. Two things are "
    "worth noting. Band **%s** is never visited in this walk %s the run steps from %s%% straight "
    "to %s%%, jumping the whole of `[%s, %s)` %s so a band can be sealed, correct, and still "
    "never bind on a fast drawdown. And the walk is a bound, not a forecast: it assumes every "
    "position stops out every time with no winning trade in between."
    % (RA3_TRIPS, RA2_TRIPS, skipped[0] if skipped else "n/a", EM,
       pct(ra3_walk[2][1]), pct(ra3_walk[2][5]),
       RA3_BANDS[1]["dd_from"], RA3_BANDS[1]["dd_to_exclusive"], EM))

sec("### 5.6 `RA3-5` %s %s" % (EM, COMP["RA3-5"]["name"]))
sec(keys_table(COMP["RA3-5"], ["value", "unit", "purpose", "inherited_unchanged_from"]))
sec(paras(COMP["RA3-5"], ["armed_by", "not_armed_by", "gates", "counted_in_sessions_not_days",
                          "measurement", "carriage"]))

sec("### 5.7 The combined scalar")
CS = RA["combined_scalar"]
sec("```\n%s\n```" % CS["formula"])
sec(paras(CS, ["multiplicative_not_minimum", "range"]))
sec("\n".join(["| Applies to | Does not apply to |", "|---|---|"] + [
    "| %s | %s |" % (cell(CS["applies_to"][i]) if i < len(CS["applies_to"]) else "",
                     cell(CS["does_not_apply_to"][i]) if i < len(CS["does_not_apply_to"]) else "")
    for i in range(max(len(CS["applies_to"]), len(CS["does_not_apply_to"])))]))

sec("### 5.8 Where the risk state lives")
sec(paras(RA["state_ownership"], list(RA["state_ownership"])))

# ---- 6 -------------------------------------------------------------------
RB = P["rebalance"]
MC = RB["measured_counts"]
sec("## 6. Rebalance calendar")
sec(paras(RB, ["axis", "values", "rule", "backward_looking_note", "unchanged_from_attempt_1"]))
cal = ["| Frequency | Rebalance sessions | First three | Last |", "|---|---|---|---|"]
for freq in FREQS:
    lo = freq.lower()
    cal.append("| `%s` | %s | %s | %s |"
               % (freq, MC[lo], ", ".join(MC["%s_first_three" % lo]), MC["%s_last" % lo]))
sec("\n".join(cal))
sec(paras(MC, ["carried_from", "carried_from_sha256", "recheck_requirement"]))
sec(paras(RB, ["attempt_2_note"]))

# ---- 7 -------------------------------------------------------------------
W = P["window"]
RSp = P["run_span"]
sec("## 7. Window, run span, and the guard")
sec(field_table([
    ("Development window", "%s %s %s" % (W["development"]["from"], EM, W["development"]["to"])),
    ("Last development session", W["development"]["last_session"]),
    ("Run start", "%s (%s)" % (RSp["run_start"], RSp["run_start_weekday"])),
    ("Run end", RSp["run_end"]),
    ("Sessions", str(RSp["sessions"])),
    ("Development union sessions", str(RSp["development_union_sessions"])),
    ("Binding symbol", "`%s`, inception %s" % (RSp["binding_symbol"],
                                               RSp["binding_symbol_inception"])),
    ("Members missing a bar at run start", str(len(RSp["members_missing_a_bar_at_run_start"]))),
    ("Symbols ending before run end", str(len(RSp["symbols_ending_before_run_end"]))),
]))
sec(paras(RSp, ["carried_from", "carried_from_sha256", "recheck_requirement", "why_unchanged",
                "reverification_required"]))
sec(paras(W, ["enforcement", "unchanged_from_attempt_1"]))

# ---- 8 -------------------------------------------------------------------
EX = P["execution"]
sec("## 8. Execution")
sec("\n".join(["| Event | Timing |", "|---|---|"] + [
    "| %s | %s |" % (label(k), cell(EX[k])) for k in ("fill_timing", "entry", "signal_exit")]))

sec("### 8.1 Order kinds this attempt may issue")
ok = ["| Tag | Side | When | Quantity |", "|---|---|---|---|"]
for row in EX["order_kinds_this_attempt_may_issue"]:
    ok.append("| `%s` | %s | %s | %s |"
              % (row["tag"], row["side"], cell(row["when"]), cell(row["quantity"])))
sec("\n".join(ok))
issued = [r for r in EX["order_kinds_this_attempt_may_issue"] if "issued_by" in r]
if issued:
    sec("\n".join("`%s` is issued by %s" % (r["tag"], r["issued_by"]) for r in issued))

sec("### 8.2 Attempt 1's `no_discretionary_exits` clause is narrowed, not weakened")
sec(paras(EX["no_discretionary_exits_superseded"], list(EX["no_discretionary_exits_superseded"])))

sec("### 8.3 One order per symbol per session")
sec(paras(EX["one_order_per_symbol_per_session"], list(EX["one_order_per_symbol_per_session"])))

sec("### 8.4 Execution lag")
sec(paras(EX["execution_lag"], list(EX["execution_lag"])))

# ---- 9 -------------------------------------------------------------------
sec("## 9. The grid")
sec(paras(GRID, ["size", "unchanged_from_attempt_1", "unchanged_from_attempt_2", "not_widened",
                 "enumeration_order", "variant_id_format", "zero_padding_note",
                 "variant_id_change_note"]))
grid_rows = ["| Index | Variant id | Lookback (months) | k | Rebalance | Target weight "
             "| Target gross | Scheduled sessions |",
             "|---|---|---|---|---|---|---|---|"]
for row in VARIANTS:
    gross = d9(dec(row["target_weight_per_position"]) * row["top_k"])
    counted = MC[row["rebalance_frequency"].lower()]
    assert row["scheduled_rebalance_sessions"] == counted, (
        "variant %s scheduled sessions %s != measured %s"
        % (row["variant_id"], row["scheduled_rebalance_sessions"], counted))
    grid_rows.append("| %d | `%s` | %d | %d | %s | %s | %s | %d |"
                     % (row["index"], row["variant_id"], row["lookback_months"], row["top_k"],
                        row["rebalance_frequency"], row["target_weight_per_position"], gross,
                        row["scheduled_rebalance_sessions"]))
sec("\n".join(grid_rows))
note("grid rows              : %d, scheduled-session cross-check passed" % len(VARIANTS))

sec("### 9.1 Multiplicity")
MCD = P["multiple_comparisons_disclosure"]
sec(field_table([(label(k), cell(MCD[k])) for k in MCD if k not in
                 ("statement", "adaptive_design_note", "third_attempt_note",
                  "no_correction_applied")]))
sec(paras(MCD, ["no_correction_applied", "adaptive_design_note", "third_attempt_note",
                "statement"]))

# ---- 10 ------------------------------------------------------------------
sec("## 10. Representative selection rule `%s`" % SEL["id"])
sec(keys_table(SEL, ["id", "frozen_before_any_variant_is_run", "return_blind",
                     "unchanged_from_attempt_1", "unchanged_from_attempt_2", "replaces"]))
sec(paras(SEL, ["why_it_changes"]))

steps_rows = ["| Order | Criterion | Scope |", "|---|---|---|"]
for st in SEL["steps"]:
    track(st, ["order", "criterion"], "step")
    desc = next((st[k] for k in ("scope", "neighbours", "definition", "purpose") if k in st), "")
    steps_rows.append("| %s | `%s` | %s |" % (st["order"], st["criterion"], cell(desc)))
sec("\n".join(steps_rows))

sec(paras(SEL["steps"][0], ["scope", "eliminates", "unchanged_from_attempt_2"]))
sec(paras(SEL["steps"][2], ["definition", "role_change"]))
sec(paras(SEL["steps"][3], ["purpose"]))

sec("### 10.1 Structural enforcement")
SE = SEL["structural_enforcement"]
sec(paras(SE, ["mechanism", "frozen_dataclass", "import_time_assertion",
               "what_is_still_excluded"]))
sec("```\n%s\n```" % "\n".join(SE["field_names"]))

sec("### 10.2 The neighbourhood")
step2 = SEL["steps"][1]
sec(paras(step2, ["neighbours", "neighbour_counts", "neighbour_counts_provenance", "symmetry",
                  "neighbour_count_conflict", "quantities", "quantity_basis",
                  "per_pair_dissimilarity", "score", "arithmetic", "denominator_floor_note",
                  "eligibility_of_neighbours"]))
sec("The partition below is enumerated from the sealed grid at generation time, not counted by "
    "hand, and the neighbour relation is asserted symmetric over all eighteen variants before "
    "the table is written.")
sec("\n".join(["| Neighbours | Variants | Examples |", "|---|---|---|"] + nb_rows))

sec("### 10.3 The two fail routes")
sec("\n".join(["| Route | Condition | Verdict |", "|---|---|---|"] + [
    "| No eligible variant | %s | `%s` |" % (cell(SEL["no_candidate_path"]["condition"]),
                                             verdict(SEL["no_candidate_path"]["verdict"])),
    "| Representative fails Gate 3 | %s | `%s` |" % (cell(SEL["second_fail_path"]["condition"]),
                                                    verdict(SEL["second_fail_path"]["verdict"]))]))
sec(paras(SEL["no_candidate_path"], ["attempt_closes", "live_possibility_note"]))
sec(paras(SEL["second_fail_path"], ["same_token_note", "runner_up_not_promoted", "conflict_ref"]))
sec(paras(SEL, ["retrospective_check_disclosure", "no_reselection"]))

# ---- 11 ------------------------------------------------------------------
GES = P["gate_evaluation_scope"]
VTD = C["verdict_token_derivation"]
sec("## 11. Gate 3 evaluation")
sec(keys_table(GES, list(GES)))
sec(paras(P, ["gate_criteria_sha256_not_recorded_here"]))

sec("### 11.1 The frozen gate text and its companion")
sec("The gate text below is the constitution's own, carried verbatim through `%s`. The seven "
    "conditions that follow are its decomposition; no threshold in either is Attempt 3's to set."
    % P["gate_criteria_ref"])
sec(blockquote(C["frozen_gate_text_verbatim"]))
FGJ = C["frozen_gate_json_companion_verbatim"]
sec(field_table([("Gate id", str(FGJ["id"])), ("Gate name", "`%s`" % FGJ["name"]),
                 ("Fail result", "`%s`" % FGJ["fail_result"])]
                + [(label(k), cell(v)) for k, v in FGJ["thresholds"].items()],
                ("Frozen companion field", "Value")))
sec(paras(C, ["adaptation_disclosure_carried"]))

sec("### 11.2 Relationship to the three earlier criteria files")
for rk in ("relationship_to_generation_1_criteria", "relationship_to_attempt_1_criteria",
           "relationship_to_attempt_2_criteria"):
    sec("**%s.**\n\n%s" % (label(rk), deep_bullets(C[rk])))
track(C, ["frozen_gate_text_verbatim", "frozen_gate_json_companion_verbatim", "gate_name",
          "relationship_to_generation_1_criteria", "relationship_to_attempt_1_criteria",
          "relationship_to_attempt_2_criteria"], "criteria")

sec("### 11.3 The seven conditions")
SUMMARY_KEYS = ("id", "required_verbatim", "attempt_3_status")
cond_rows = ["| Id | Required (verbatim) | Status |", "|---|---|---|"]
for cnd in C["conditions"]:
    track(cnd, list(SUMMARY_KEYS), "condition")
    cond_rows.append("| `%s` | %s | %s |" % (cnd["id"], cell(cnd["required_verbatim"]),
                                             cell(cnd["attempt_3_status"])))
sec("\n".join(cond_rows))
note("gate conditions        : %d" % len(C["conditions"]))

sec("Each condition's remaining fields follow. They are reproduced from `%s` in full rather than "
    "summarised, so a reader of this document alone can reconstruct the gate arithmetic; the "
    "criteria file remains the source of record and the sealer asserts the two agree. The field "
    "set differs between conditions %s every key each condition actually carries is rendered, so "
    "a field cannot be dropped by a renderer that expected a fixed shape."
    % (P["gate_criteria_ref"], EM))
for cnd in C["conditions"]:
    rest = [k for k in cnd if k not in SUMMARY_KEYS]
    sec("**`%s`.**\n\n%s" % (cnd["id"], deep_bullets({k: cnd[k] for k in rest})))
    track(cnd, rest, "condition")

sec("### 11.4 Verdict tokens")
sec("\n".join(["| Outcome | Token |", "|---|---|",
               "| Admitted | `%s` |" % VTD["pass_token"],
               "| Rejected | `%s` |" % VTD["fail_token"]]))
sec(paras(VTD, ["pass_condition", "fail_condition", "conjunctive_note",
                "constitutional_fail_result_equivalent", "token_naming_note",
                "prior_attempt_tokens_are_not_available_here", "other_tokens_available",
                "fail_is_a_deliverable", "neither_token_is_a_stage_verdict_for_any_other_stage"]))

sec("### 11.5 Evaluation integrity rules")
sec("\n".join("%d. %s" % (i, r) for i, r in enumerate(C["evaluation_integrity_rules"], 1)))
note("integrity rules        : %d" % len(C["evaluation_integrity_rules"]))

sec("### 11.6 Reported for every variant, gating nothing")
PBNG = P["reported_for_every_variant_but_not_gating"]
sec("\n".join("- %s" % x for x in PBNG))
rbng = C["reported_but_not_gating"]
extra = [x for x in rbng if x not in PBNG]
shared = [x for x in rbng if x in PBNG]
track(C, ["reported_but_not_gating"], "criteria")
assert PBNG, "the protocol's reported_for_every_variant_but_not_gating list is empty"
assert rbng, "the criteria file's reported_but_not_gating list is empty"
assert len(shared) + len(extra) == len(rbng), "shared/extra partition does not cover rbng"
sec("`%s` carries its own list of %d non-gating quantities against this document's %d. The two "
    "lists were written independently and share **%d** entries by exact string %s each file "
    "names the same measurements in its own wording. That is not a disagreement to reconcile: "
    "neither list gates anything, no condition in section 11.3 reads from either, and the sealer "
    "asserts only that both are non-empty. The criteria file's %d entries are reproduced below "
    "so that neither document has to be read through the other."
    % (P["gate_criteria_ref"], len(rbng), len(PBNG), len(shared), EM, len(extra)))
if extra:
    sec("\n".join("- %s" % x for x in extra))
note("non-gating quantities  : protocol %d, criteria %d, shared %d, criteria-only %d"
     % (len(PBNG), len(rbng), len(shared), len(extra)))

# ---- 12 ------------------------------------------------------------------
sec("## 12. Structural consequences, declared before running")
SCS = P["structural_consequences_declared_before_running"]
for sc_id in sorted(SCS, key=lambda x: int(x.split("-")[1])):
    body = SCS[sc_id]
    lead = body.get("statement", "")
    rest = [k for k in body if k != "statement"]
    chunk = "**%s.** %s" % (sc_id, lead)
    if rest:
        chunk += "\n\n" + "\n".join("- *%s* %s %s" % (label(k), EM, cell(body[k])) for k in rest)
    sec(chunk)
note("structural consequences: %d (%s)" % (len(SCS), ", ".join(sorted(SCS))))

# ---- 13 ------------------------------------------------------------------
DBM = P["declared_before_any_strategy_code_measurement"]
PAM = P["prior_attempt_modules_immutable"]
sec("## 13. Contamination measurement")
# The blockquote carries the predicate verbatim, matching section 13 of SE100-GOV-2005: the quoted
# block is the claim being asserted, not a label for it.  The Attempt 3 sealer extracts the first
# blockquote after this heading and compares it to the sealed predicate, so quoting the
# `CONTENT_BASED` label here instead would be a refusal.
track(DBM, ["predicate", "contamination_predicate"],
      "protocol.declared_before_any_strategy_code_measurement")
sec(blockquote(DBM["predicate"]))
sec("**Predicate type.** `%s`" % DBM["contamination_predicate"])
sec(paras(DBM, ["why_not_path_based", "paired_immutability_check",
                "sealer_indirection_note", "conflict_ref", "supersedes_in_scope"]))
mod_rows = ["| Path | Sealed by |", "|---|---|"]
for m in PAM["attempt_1_modules"]:
    mod_rows.append("| `%s` | Attempt 1 |" % m)
for m in PAM["attempt_2_modules"]:
    mod_rows.append("| `%s` | Attempt 2 |" % m)
sec("\n".join(mod_rows))
total_modules = len(PAM["attempt_1_modules"]) + len(PAM["attempt_2_modules"])
assert total_modules == PAM["count"] == 17, (
    "module count %d != declared %s" % (total_modules, PAM["count"]))
note("immutable modules      : %d (declared %s)" % (total_modules, PAM["count"]))
sec(paras(PAM, ["count", "attempt_1_list_source", "attempt_2_list_source",
                "g2_partition_lock_excluded", "digests_recorded_by",
                "digests_not_recorded_here"]))

# ---- 14 ------------------------------------------------------------------
sec("## 14. Windows referenced, and the two mandated disclosures")
win_rows = ["| Span | State | Note |", "|---|---|---|",
            "| %s %s %s | `DEVELOPMENT` | the only window this attempt reads |"
            % (W["development"]["from"], EM, W["development"]["to"])]
for pw in W["prohibited"]:
    win_rows.append("| %s %s %s | `%s` | %s |"
                    % (pw["from"], EM, pw["to"], pw["state"], cell(pw["note"])))
sec("\n".join(win_rows))

CW = C["windows"]
cw_dev = CW["development_window"]
assert list(cw_dev) == [W["development"]["from"], W["development"]["to"]], (
    "the criteria file's development window %s disagrees with the protocol's %s"
    % (list(cw_dev), [W["development"]["from"], W["development"]["to"]]))
note("window cross-check     : criteria development window == protocol's (%s)"
     % " to ".join(cw_dev))
sec("`%s` carries the same windows independently. Its development window was compared against the "
    "one above at generation time and agrees. Its holdout and validation states:"
    % P["gate_criteria_ref"])
sec(paras(CW, ["authorized", "validation_window_state", "generation_1_holdout_state",
               "holdout_window_state", "enforcement", "disclosed_limitation_reference",
               "generation_1_holdout", "generation_2_holdout"]))
track(CW, ["development_window"], "criteria.windows")

ADC = P["adaptation_disclosure_carriage_requirement"]
sec("### 14.1 The adaptation disclosure")
sec("Carried verbatim, byte for byte, into every artifact listed below. The sealer refuses to "
    "seal if any of them disagrees with this text.")
sec(blockquote(ADAPTATION))
sec("\n".join("- `%s`" % x for x in ADC["must_appear_verbatim_in"]))
sec(paras(ADC, ["enforcement", "encoding_note", "attempt_3_encoding_addendum", "source"]))

sec("### 14.2 The validation-reuse disclosure")
sec(blockquote(VALIDATION_REUSE))

# ---- 15 ------------------------------------------------------------------
sec("## 15. Conflicts and interpretations")
cf_rows = ["| Id | Conflict | Resolution | Provenance |", "|---|---|---|---|"]
for cf in P["conflicts_found"]:
    prov = []
    if cf.get("carried_from"):
        prov.append("carried from %s" % cell(cf["carried_from"]))
    if cf.get("supersedes_in_scope"):
        prov.append("supersedes in scope: %s" % cell(cf["supersedes_in_scope"]))
    if cf.get("see"):
        prov.append("see %s" % cell(cf["see"]))
    cf_rows.append("| `%s` | %s | %s | %s |"
                   % (cf["id"], cell(cf.get("summary", cf.get("description", ""))),
                      cell(cf.get("resolution", cf.get("why_it_is_safe", ""))),
                      "; ".join(prov) or "declared here"))
    track(cf, ["id", "summary", "resolution", "see"], "conflict")
sec("\n".join(cf_rows))
new_here = [c["id"] for c in P["conflicts_found"] if not c.get("carried_from")]
note("protocol conflicts     : %d (%d new here: %s)"
     % (len(P["conflicts_found"]), len(new_here), ", ".join(new_here)))
sec(paras(P["conflicts_declared_in_the_gate_criteria"],
          ["note", "declared_in_g2_gate_criteria_ra3",
           "inherited_and_restated_in_g2_gate_criteria_ra3"]))

# ---- 16 ------------------------------------------------------------------
ATR = P["adversarial_test_requirements"]
sec("## 16. Adversarial tests required")
sec(paras(ATR, ["note"]))
at_rows = ["| Id | Requirement |", "|---|---|"]
at_ids = [k for k in ATR if re.fullmatch(r"AT-[A-Z]", k)]
for k in at_ids:
    at_rows.append("| `%s` | %s |" % (k, cell(ATR[k])))
sec("\n".join(at_rows))
note("adversarial tests      : %d (%s .. %s)" % (len(at_ids), at_ids[0], at_ids[-1]))
sec(paras(ATR, ["regression_floor"]))

sec("### 16.1 Reproducibility")
sec(paras(P["reproducibility_requirements"], list(P["reproducibility_requirements"])))

# ---- 17 ------------------------------------------------------------------
sec("## 17. Binding rules")
BINDING = [
    "This document is sealed on write. %s %s applies equally to %s."
    % (P["post_seal_defect_rule"]["rule"], EM,
       cell(P["post_seal_defect_rule"]["applies_equally_to"])),
    "**Attempt 1 and Attempt 2 are closed.** Attempt 1's verdict `%s` and Attempt 2's verdict "
    "`%s` stand permanently against the figures their own records describe. Generation 1, "
    "Generation 2 Attempt 1 and Generation 2 Attempt 2 are read-only: nothing in this attempt "
    "edits, deletes, reopens, re-runs, loosens or supersedes any of their artifacts or modules. "
    "All %s prior-attempt modules listed in section 13 are re-hashed at seal time and again at "
    "package time, and a single changed digest is a blocker. They are pinned so that a change to "
    "any of them is **detectable**, not so that any of them may be changed."
    % (verdict(P["attempt_1_ref"]["verdict"]),
       verdict(P["attempt_2_ref"]["verdict"]), PAM["count"]),
    "**Attempt 2's own binding rule 7 forbids this attempt**, and is not edited. Section 17 of "
    "`SE100-GOV-2005` reads \"No Attempt 3 is authorized. If Attempt 2 fails, the attempt "
    "closes.\" That rule bound the attempt that wrote it in the absence of any further "
    "authorization; its force is to require a new authorization, not to make one impossible. The "
    "authorization for this attempt is external and human, and the adaptation it authorizes is "
    "disclosed verbatim in section 14.1. The rule this file writes about an Attempt 4 in section "
    "17.1 is to be read the same way. See `G2A3-CONFLICT-38`.",
    "The grid is not widened. %s" % GRID["not_widened"],
    "`%s` is frozen before any variant is run and is not part of the grid. %s"
    % (RA["id"], RA["why_not_gridded"]),
    "`%s` is frozen before any variant is run and is return-blind by construction, enforced "
    "at import time. %s" % (SEL["id"], SE["import_time_assertion"]),
    "Gate 3 thresholds are unchanged from Generation 1, Attempt 1 and Attempt 2. No threshold "
    "is adjusted in either direction to compensate for either change.",
    "No window at or after %s is read, by this document or by any code it governs. The "
    "prohibited windows are listed in section 14." % W["prohibited"][0]["from"],
    "The adaptation disclosure of section 14.1 is carried verbatim into all "
    "%d artifacts listed there." % len(ADC["must_appear_verbatim_in"]),
    "`live_trading_authorized` is `%s` and this document does not change it."
    % str(P["live_trading_authorized"]).lower(),
]
sec("\n".join("%d. %s" % (i, r) for i, r in enumerate(BINDING, 1)))

sec("### 17.1 Explicit non-authorizations")
sec("\n".join("- %s" % x for x in P["explicit_non_authorizations"]))
note("non-authorizations     : %d" % len(P["explicit_non_authorizations"]))

sec("*Machine companion: `STAGE_3_G2_ROTATION_RA3_PROTOCOL.json`, sealed by "
    "`STAGE_3_G2_ROTATION_RA3_PROTOCOL.sha256`. The tree digest `repo_state_id` for the sealing "
    "run is recorded in `runs/`, deliberately not in this document %s `repo_state_id` covers "
    "files in this tree, and a document that carried it would invalidate it on write.*" % EM)

# --------------------------------------------------------------------------
DOC = "\n\n".join(S) + "\n"

# Default target is the scratch draft.  `--emit` writes the governed artifact
# instead; nothing else about the run changes, so the reviewed draft and the
# sealed document are the same bytes apart from the emit-time timestamp.
if "--emit" in sys.argv:
    OUT = ROOT / "governance/generation_2/STAGE_3_G2_ROTATION_RA3_PROTOCOL.md"
    assert not OUT.exists(), "refusing to overwrite an existing %s" % OUT.name

# write_bytes, never write_text.  Path.write_text() on Windows applies newline
# translation and turns every \n into \r\n, which changes the sha256 of the
# file without changing a single character of its content - the same hazard
# CLAUDE.md documents for git's core.autocrlf, undocumented for Python.  The
# encode-then-write form cannot do that, and the readback below proves it.
BLOB = DOC.encode("utf-8")
OUT.write_bytes(BLOB)

ON_DISK = OUT.read_bytes()
assert ON_DISK == BLOB, "what landed on disk is not what was assembled"
assert ON_DISK.count(b"\r") == 0, "CRLF found in the written file"
assert hashlib.sha256(ON_DISK).hexdigest() == sha256_text(DOC)

print("=" * 74)
for n in NOTES:
    print(n)
print("=" * 74)
print("written                : %s" % OUT)
print("bytes                  : %d" % len(DOC.encode("utf-8")))
print("lines                  : %d" % DOC.count("\n"))
print("sha256                 : %s" % sha256_text(DOC))
print("adaptation present     : %s" % (ADAPTATION in DOC))
print("validation reuse       : %s" % (VALIDATION_REUSE.splitlines()[0][:40] in DOC))
print("CRLF                   : %d" % DOC.count("\r"))
print("em dashes (U+2014)     : %d" % DOC.count("\u2014"))
print("minus signs (U+2212)   : %d" % DOC.count("\u2212"))
print("64-hex digests present : %d" % len(re.findall(r"\b[0-9a-f]{64}\b", DOC)))
print("h2 sections            : %d" % len(re.findall(r"^## ", DOC, re.M)))
print("h3 sections            : %d" % len(re.findall(r"^### ", DOC, re.M)))
print("own digest embedded    : %s" % (sha256_text(DOC) in DOC))

print("-" * 74)
print("KEYS ASKED FOR THAT DO NOT EXIST (%d)" % len(MISSING))
for m in MISSING:
    print("   %s" % m)

leftovers = []
for key, (name, d) in sorted(NODES.items(), key=lambda kv: kv[1][0]):
    rest = [k for k in d if k not in CONSUMED[key]]
    if rest:
        leftovers.append("   %-58s %s" % (name, ", ".join(rest)))
print("-" * 74)
print("KEYS THAT EXIST AND WERE NEVER RENDERED (%d nodes)" % len(leftovers))
for line in leftovers:
    print(line)

top_rendered = {p.split(".", 1)[1].split(".")[0].split("[")[0]
                for key, (p, _) in NODES.items() if p.startswith("protocol.")}
top_missing = [k for k in P if k not in top_rendered
               and "protocol.%s" % k not in [n for _, (n, _) in NODES.items()]]
print("-" * 74)
print("TOP-LEVEL PROTOCOL KEYS NOT VISIBLY TOUCHED (%d)" % len(top_missing))
print("   " + ", ".join(top_missing))
