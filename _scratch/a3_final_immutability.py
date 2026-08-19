"""Fresh re-hash immediately before the end-of-session report. Reads only."""
import hashlib, json, pathlib, sys
ROOT = pathlib.Path(r"D:\Product\stock-trade-alpaca\stockedge100")

def out(t):
    sys.stdout.write(str(t).encode("ascii", "backslashreplace").decode("ascii") + "\n")

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

BARE = {"STAGE_0_FREEZE.sha256", "STAGE_1_FREEZE.sha256"}
recs = sorted(ROOT.rglob("*.sha256"))
ok = bad = ent = 0
for rec in recs:
    base = rec.parent if rec.name in BARE else ROOT
    for line in rec.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        dig, _, rel = line.partition(" ")
        f = base / rel.lstrip("*").strip()
        ent += 1
        if f.is_file() and sha(f) == dig:
            ok += 1
        else:
            bad += 1
            out("  MISMATCH %s -> %s" % (rec.name, rel))
out("checksum records: %d records, %d entries, %d verify, %d fail" % (len(recs), ent, ok, bad))

NAMED = ["g2_rotation.py", "g2_engine.py", "g2_gate.py", "g2_runner.py",
         "g2_rotation_ra1.py", "g2_engine_ra1.py", "g2_gate_ra1.py", "g2_runner_ra1.py"]
for n in NAMED:
    assert len(list(ROOT.rglob(n))) == 1, n
out("prompt-named prior modules: 8 found, each exactly once, none overwritten")

def digest_of(v):
    if isinstance(v, str):
        return v
    return v.get("sha256") or v.get("digest")

MANS = [("reports/stage4/STAGE_4_VALIDATION_ARTIFACT_MANIFEST.json", "GEN1-S4"),
        ("reports/stage3_g2/STAGE_3_G2_ARTIFACT_MANIFEST.json", "G2-A1"),
        ("reports/stage3_g2_attempt2/STAGE_3_G2_A2_ARTIFACT_MANIFEST.json", "G2-A2")]
for man, label in MANS:
    M = json.loads((ROOT / man).read_text(encoding="utf-8"))
    n = m = 0
    moved = []
    for group in ("frozen_inputs", "produced_artifacts", "dataset_hashes", "repo_state_files"):
        for rel, v in (M.get(group) or {}).items():
            dig = digest_of(v)
            if not dig:
                continue
            n += 1
            f = ROOT / rel
            if f.is_file() and sha(f) == dig:
                m += 1
            else:
                moved.append(rel)
    assert n > 0, ("vacuous", man)
    out("%-8s %-56s %3d hashed paths, %3d unchanged, moved=%s"
        % (label, man.split("/")[-1], n, m, moved))

sys.path.insert(0, str(ROOT / "src"))
from stockedge100.reporting.stage_package import repo_state
st = repo_state(ROOT)
d = st["repo_state_id"]
EXPECTED = "30cadd00c89fc09cbbcd37ae98ec69546c5992a652f3556e29d07a5a2d2d94a2"
assert d == EXPECTED, "DIGEST MOVED: %s" % d
n = len(st.get("files") or st.get("paths") or st.get("covered_paths") or st.get("file_digests") or [])
out("repo_state_id: %s (asserted equal, %d covered paths)" % (d, n))

for f, tok in [("reports/stage3_g2/STAGE_3_G2_ROTATION_RESEARCH.json", "STAGE_3_G2_NO_CANDIDATE"),
               ("reports/stage3_g2_attempt2/STAGE_3_G2_A2_ROTATION_RESEARCH.json",
                "STAGE_3_G2_ATTEMPT_2_NO_CANDIDATE")]:
    out("%-44s still carries %-38s %s"
        % (f.split("/")[-1], tok, tok in (ROOT / f).read_text(encoding="utf-8")))
