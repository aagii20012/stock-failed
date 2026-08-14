"""Out-of-tree: dump the sealed shared rules, binding and parameters the two test files cite."""

import json
import sys

sys.path.insert(0, r"d:\Product\stock-trade-alpaca\stockedge100\src")

from stockedge100.strategies.attempt2_config import load_attempt2_config

config = load_attempt2_config()

print("== shared_rules keys ==")
print(json.dumps(sorted(config.shared_rules), indent=1))
print()
print("== adopted_text_restated_for_readability ==")
print(json.dumps(config.shared_rule_texts, indent=1))
print()
print("== excluded_symbols ==")
print(json.dumps(config.excluded_symbols, indent=1))
print()
print("== binding.admissible_candidate_exists ==")
print(json.dumps(config.binding["admissible_candidate_exists"], indent=1))
print()
print("== thresholds ==")
print(json.dumps(config.thresholds, indent=1))
print()
print("== verdict_token_derivation ==")
print(json.dumps(config.criteria["verdict_token_derivation"], indent=1))
print()
for experiment in config.experiments:
    print(f"== {experiment['experiment_id']} primary_parameters ==")
    print(json.dumps(experiment["primary_parameters"], indent=1))
