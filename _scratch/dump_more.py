"""Out-of-tree: dump the remaining sealed subtrees the two test files cite."""

import json
import sys

sys.path.insert(0, r"d:\Product\stock-trade-alpaca\stockedge100\src")

from stockedge100.strategies.attempt2_config import load_attempt2_config

config = load_attempt2_config()

print("== protocol top-level keys ==")
print(json.dumps(sorted(config.protocol), indent=1))
print()
print("== shared_rules.replaced ==")
print(json.dumps(config.shared_rules["replaced"], indent=1))
print()
print("== missing_or_invalid_data_rule ==")
print(json.dumps(config.protocol["missing_or_invalid_data_rule"], indent=1))
print()
print("== partitions ==")
print(json.dumps(config.protocol["partitions"], indent=1))
print()
print("== iteration_budget ==")
print(json.dumps(config.iteration_budget, indent=1))
print()
print("== binding keys ==")
print(json.dumps(sorted(config.binding), indent=1))
