"""Out-of-tree smoke check for attempt2_traceability. Collects every failure; runs no evaluation."""

import sys

sys.path.insert(0, r"d:\Product\stock-trade-alpaca\stockedge100\src")

from stockedge100.backtest.errors import ConfigViolation
from stockedge100.strategies import attempt2_traceability as T
from stockedge100.strategies.attempt2_config import load_attempt2_config

config = load_attempt2_config()

print(f"== {len(T.TRACES)} rows; resolving both ends of each ==")

sealed_failures = []
code_failures = []
for trace in T.TRACES:
    try:
        T.sealed_value(config, trace)
    except ConfigViolation as exc:
        sealed_failures.append(str(exc))
    for reference in trace.implementation:
        try:
            T.resolve_code(reference)
        except ConfigViolation as exc:
            code_failures.append(str(exc))

print(f"\n-- sealed path failures: {len(sealed_failures)}")
for message in sealed_failures:
    print("   ", message)

print(f"\n-- code reference failures: {len(dict.fromkeys(code_failures))}")
for message in dict.fromkeys(code_failures):
    print("   ", message)

print(f"\n-- missing coverage: {len(T.missing_coverage())}")
for message in T.missing_coverage():
    print("   ", message)

print(f"\n-- duplicate rows: {T.duplicate_rows()}")

print(f"\n-- distinct tests named: {len(T.all_named_tests())}")

if not sealed_failures and not code_failures:
    print("\n== verify() ==")
    import json

    print(json.dumps(T.verify(config), indent=2))
    rows = T.resolved_rows(config)
    print(f"\nresolved_rows: {len(rows)}")
    sample = rows[0]
    print("sample row:", sample["sealed_document"], ".".join(sample["sealed_path"]))
    print("sample sealed_value:", repr(sample["sealed_value"])[:300])
    print("\nTRACEABILITY OK - no evaluation was executed")
else:
    raise SystemExit("traceability map does not resolve yet")
