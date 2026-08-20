"""Append the measured LEAN fill convention to .claude/rules/faber-lean.md."""
import pathlib

p = pathlib.Path(".claude/rules/faber-lean.md")
txt = p.read_text(encoding="utf-8")

ANCHOR = (
    '"an old Lean CLI root folder". The free sample data has no 2007-2026 history for these\n'
    "ETFs. `quantconnect/lean:latest` is a multi-GB pull — run it as a background task, it\n"
    "exceeds a 10-minute foreground timeout.\n"
)

ADD = """
Two that cost real time:

- **A `docker pull` can report exit code 0 with no image on disk.** Verify with
  `docker image inspect quantconnect/lean:latest`, never the exit code.
- **On daily data LEAN fills market orders at that day's CLOSE**, not at the scheduled
  time. `time_rules.after_market_open` sets when the scheduled *method* runs; the order
  becomes MarketOnClose. Measured across 726 fills: 726/726 match close(D) exactly,
  while open(D) is off by 56 bps median. So a `month_start` schedule trades one trading
  day later than a harness that trades on the signal month's close, which makes LEAN
  late into every de-risking move and its drawdown the more honest number. Attribute
  such a gap from the order events, not by reading the schedule.
"""

if ANCHOR not in txt:
    raise SystemExit("anchor not found")

txt = txt.replace(ANCHOR, ANCHOR + ADD, 1)
body = txt.encode("utf-8")
body.decode("utf-8")
p.write_bytes(body)
print("patched OK, %d bytes" % len(body))
