"""Out-of-tree: dump the sealed RA1 block verbatim so the adversarial tests cite real wording."""

import json
import sys

sys.path.insert(0, r"d:\Product\stock-trade-alpaca\stockedge100\src")

from stockedge100.strategies.attempt2_config import load_attempt2_config

config = load_attempt2_config()
print(json.dumps(config.risk_architecture, indent=1))
