import json
import pathlib

for rel in [
    "config/generation_2/g2_gate_criteria_ra3.json",
    "config/generation_2/g2_rotation_ra1_protocol.json",
    "config/generation_2/g2_rotation_ra3_protocol.json",
]:
    raw = pathlib.Path(rel).read_bytes()
    obj = json.loads(raw.decode("utf-8"))
    for label, cand in [
        ("indent2+nl", (json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode("utf-8")),
        ("indent2", json.dumps(obj, indent=2, ensure_ascii=False).encode("utf-8")),
        ("indent4+nl", (json.dumps(obj, indent=4, ensure_ascii=False) + "\n").encode("utf-8")),
        ("ascii2+nl", (json.dumps(obj, indent=2) + "\n").encode("utf-8")),
    ]:
        if cand == raw:
            print("%-46s %s" % (rel.split("/")[-1], label))
            break
    else:
        c = (json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        i = next((i for i in range(min(len(c), len(raw))) if c[i] != raw[i]), min(len(c), len(raw)))
        print("%-46s NO MATCH; len raw=%d cand=%d; first diff at %d" % (
            rel.split("/")[-1], len(raw), len(c), i))
        print("   raw : %r" % raw[max(0, i - 60):i + 60])
        print("   cand: %r" % c[max(0, i - 60):i + 60])

print()
crit = json.loads(pathlib.Path("config/generation_2/g2_gate_criteria_ra3.json").read_text("utf-8"))
a2 = json.loads(pathlib.Path("config/generation_2/g2_gate_criteria_ra1.json").read_text("utf-8"))
print("criteria top-level keys:", list(crit))
print()
print("conditions[0] of attempt 3:")
print(json.dumps(crit["conditions"][0], indent=2, ensure_ascii=False)[:900])
