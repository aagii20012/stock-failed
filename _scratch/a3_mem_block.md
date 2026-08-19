**Generation 2 Gate 3 Attempt 3 also failed, on 2026-08-19** — `FAIL —
STAGE_3_G2_ATTEMPT_3_NO_CANDIDATE`, package run `SE100-R-20260819T104543Z`, ending `repo_state_id`
`30cadd00c89fc09cbbcd37ae98ec69546c5992a652f3556e29d07a5a2d2d94a2` over 165 files, 1264 passed / 1
failed by design of 1265. Same 18-variant grid, two disclosed adaptations: **RA3** (RA2 minus the
−5% de-risk tier, ladder back to Generation 1's <8 / 8–10 / ≥10 spacing) and **SEL-2** (neighborhood
stability over `{fill_count, ladder_descent_count, lockout_arm_count, stops_filled_count}` replacing
lowest turnover). Winner `SE100-G2-S3-C3-ROTATION-RA3-L03-K2-QUARTERLY`, instability `0.215471404`,
margin over the runner-up `0.000048608`.

**RA3 fixed what Attempt 2 broke and hit a different wall.** Returns recovered to **+10.34% base /
+8.11% stress**, still with **0 shutdowns in 36 runs**, and the required ladder-difference check
passed 36/36 (`sessions_at_full_sizing` 36886 → 53671). Six of seven conditions MET. **S3-C6 alone
missed: 0.750503 / 0.977151 against ≤ 0.50.** So the three attempts fail three different ways —
A1 never reached the gate (36/36 shutdowns), A2 reached it and starved (4 conditions missed at
+0.42%), A3 reached it healthy and concentrated (1 condition missed).

**S3-C6 is now the binding constraint for this whole family, and the reason is its denominator.** The
sealed `measurement` (byte-identical in `g2_gate_criteria_ra1.json` and `..._ra3.json`, implemented at
`g2_gate_ra1.py:697`) divides one instrument's episode P&L by the **net** sum over all closed episodes
— not gross profit. With 11 of 24 instruments net-negative (base; 12 of 24 stressed) the losers shrink
the denominator, so a single winner trivially exceeds 50%. On a *gross* denominator the same run
measures `0.241268 / 0.253222` and **the gate would have passed**. The gate follows the seal, so the
FAIL is correct — but two prose sentences in the built report (`STAGE_3_G2_ROTATION_RA3_RESEARCH_REPORT.md`
lines 82 and 639) mis-name it "gross profit". That is **disclosed in the session report, not fixed**:
the report is already hashed into the manifest and checksum record. Do not repair it in place; any
future reference must name the net denominator. Same condition alone rejected Gen 1's
`C3-DEFENSIVE` (0.9796) and Gen 2 A2 (>1.0).

Cumulative multiplicity across the three attempts is **54 variants / 108 runs**, no correction
applied. **No Attempt 4 without a further disclosed adaptation authorized in a later session.** Stage 4
was not run and is not authorized; both holdouts remain unread.
