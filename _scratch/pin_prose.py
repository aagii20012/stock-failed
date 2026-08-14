"""Out-of-tree: dump the sealed prose the three test files will cite verbatim. No evaluation."""

import json
import sys

sys.path.insert(0, r"d:\Product\stock-trade-alpaca\stockedge100\src")

from stockedge100.strategies.attempt2_config import load_attempt2_config

config = load_attempt2_config()

print("== VOL20 ==")
print(json.dumps(config.vol20, indent=2))

print()
print("== thresholds ==")
print(json.dumps(config.thresholds, indent=2))

print()
print("== verdict_token_derivation ==")
print(json.dumps(config.criteria["verdict_token_derivation"], indent=2))

print()
print("== conditions: predicate + measurement ==")
for cond in config.gate_conditions:
    print(f"-- {cond['id']}")
    print("   predicate  :", json.dumps(cond["predicate"])[:400])
    print("   measurement:", json.dumps(cond["measurement"])[:400])

print()
print("== reproducibility_requirements ==")
print(json.dumps(config.protocol["reproducibility_requirements"], indent=2)[:1600])

print()
print("== secondary_metrics ==")
print(json.dumps(config.protocol["secondary_metrics"], indent=2)[:1800])
