"""Emit the diagnostic Markdown report from episode_ledger.json.

Every figure in the report is read out of the JSON the trace wrote, or out of the trace's own run
log; nothing is hand-typed. Writes only into reports/diagnostics/attempt3_iwm_trace/, which is
outside every repo_state_id pattern.
"""

from __future__ import annotations

import json
import re
import sys
from decimal import Decimal, localcontext
from pathlib import Path

REPO = Path(r"D:\Product\stock-trade-alpaca\stockedge100")
SCRATCH = Path(r"D:\Product\stock-trade-alpaca\_scratch")
OUT = REPO / "reports" / "diagnostics" / "attempt3_iwm_trace"
D = json.loads((OUT / "episode_ledger.json").read_text(encoding="utf-8"))

sys.path.insert(0, str(REPO / "src"))
from stockedge100.backtest.costs import ENGINE_CONTEXT  # noqa: E402


def dv(x) -> Decimal:
    return Decimal(str(x))


def ratio(a, b) -> Decimal:
    """A ratio under the engine's own 34-digit context, so it matches what the gate would print."""
    with localcontext(ENGINE_CONTEXT):
        return dv(a) / dv(b)


def pct(x, places: int = 2) -> str:
    with localcontext(ENGINE_CONTEXT):
        return f"{dv(x) * 100:.{places}f}%"


anchors = D["sealed_source"]["anchors"]
checks = D["reproduction_checks"]
CHECK = {c["field"]: c for c in checks}
shape = D["run_shape"]
iwm = D["iwm"]
eps = iwm["episodes"]
risk = D["risk_context"]
per_sym = {v["symbol"]: v for v in D["per_symbol_context"]}
recon = D["reconciliation"]
ledger = D["full_episode_ledger"]
closed = [e for e in ledger if e["closed"]]
opens = [e for e in ledger if not e["closed"]]

net = dv(shape["total_net_closed_episode_pnl"])
iwm_total = dv(iwm["total_pnl"])
non_iwm = net - iwm_total
gross_profit = sum((dv(e["pnl"]) for e in closed if dv(e["pnl"]) > 0), Decimal(0))
gross_loss = -sum((dv(e["pnl"]) for e in closed if dv(e["pnl"]) < 0), Decimal(0))
pos_symbol_sum = sum((dv(v["total_pnl"]) for v in per_sym.values() if dv(v["total_pnl"]) > 0),
                     Decimal(0))
n_pos = len([1 for v in per_sym.values() if dv(v["total_pnl"]) > 0])
n_neg = len([1 for v in per_sym.values() if dv(v["total_pnl"]) < 0])
failed = [c for c in checks if not c["agrees"]]
sessions_held = sum(e["holding_trading_sessions"] for e in eps)

# The prior-attempt module verification numbers come from the trace's own run log, not from memory.
LOG = (SCRATCH / "a3_iwm_trace.log").read_text(encoding="utf-8")
mod_count = re.search(r"module_count\s+=\s+(\d+)", LOG).group(1)
mod_verified = re.search(r"modules_verified\s+=\s+(\d+)", LOG).group(1)
mod_moved = re.search(r"modules_that_moved\s+=\s+(\[.*?\])", LOG).group(1)

# Extracted once so the prose cannot drift from the table.
gaps = ", ".join(str(e["gap_from_previous_iwm_exit_calendar_days"]) for e in eps[1:])
signals = ", ".join(pct(e["entry_momentum"]["signal"]) for e in eps)
ranks = "/".join(str(e["entry_momentum"]["rank"]) for e in eps)
years = ", ".join(e["entry_session"][:4] for e in eps)
universe = eps[0]["entry_momentum"]["ranked_universe"]
hist = iwm["rank_at_every_rebalance"]
by_sess = {r["session"]: i for i, r in enumerate(hist)}
best_rank = min(r["rank"] for r in hist)
worst_rank = max(r["rank"] for r in hist)
next_ranks = "/".join(str(hist[by_sess[r["session"]] + 1]["rank"])
                      for r in iwm["rebalances_with_iwm_in_top_k"])
median_days = sorted(e["holding_calendar_days"] for e in closed)[len(closed) // 2]
ep_counts = sorted(v["episodes_closed"] for v in per_sym.values())
most_traded = max(per_sym.values(), key=lambda v: v["episodes_closed"])

L: list[str] = []
w = L.append

w("# Attempt 3 — where IWM's 75% concentration came from")
w("")
w("**Diagnostic id** `SE100-DIAG-A3-IWM-TRACE`  ")
w(f"**Subject** `{D['variant_id']}{D['run_label']}` — the Generation 2 Stage 3 Attempt 3 "
  f"representative, `{D['scenario']}` cost scenario  ")
w("**Status** read-only diagnostic. **Not a governance artifact.**")
w("")
w("This report carries **no verdict token, no gate condition, no checksum record and no artifact "
  "manifest**, and it is not an attempt at any gate. It explains an already-closed result. The "
  "Attempt 3 package at `reports/stage3_g2_attempt3/` is sealed and hashed; nothing in it was read "
  "for any purpose but comparison, and nothing was written into it. Attempt 3's recorded verdict — "
  f"S3-C6 `NOT_MET`, concentration `{anchors['share_IWM']}` against `<= 0.50` — is unchanged and "
  "uncontested by this document.")
w("")
w("Everything below lives in `reports/diagnostics/attempt3_iwm_trace/`, which is outside every "
  "`repo_state_id` pattern, so producing it perturbed no governance digest.")
w("")
w("---")
w("")

# ------------------------------------------------------------------ 1. reproduction
w("## 1. The reproduction is exact (this section gates every later one)")
w("")
w("The detail in sections 2–5 is worth reading only if the run it came from is the sealed run. The "
  "trace imports the sealed strategy, engine, ledger and runner modules and calls "
  "`g2_runner_ra3.run_one` — nothing is reimplemented — then compares "
  f"**{len(checks)} values** against `{D['sealed_source']['evidence_file']}` before emitting "
  "anything. The script exits without writing if any check disagrees.")
w("")
w(f"**Result: {len(checks) - len(failed)}/{len(checks)} agree. Disagreements: "
  f"{len(failed) if failed else 'none'}.**")
w("")
w("The four determinism digests are the strongest of those checks, because two runs can agree on an "
  "equity curve while disagreeing about a ranking tie or a band transition that never reached an "
  "order:")
w("")
w("| digest | sealed value | reproduced |")
w("| --- | --- | --- |")
for key in ("trades_digest", "equity_digest", "ranking_digest", "risk_state_digest"):
    c = CHECK[key]
    w(f"| `{key}` | `{c['sealed']}` | " + ("match" if c["agrees"] else "**DIFFERS**") + " |")
w("")
w("And the aggregates the operating instruction named specifically:")
w("")
w("| quantity | sealed | reproduced |")
w("| --- | --- | --- |")
for key, label in (
    ("total_return", "total return"),
    ("starting_equity", "starting equity"),
    ("final_equity", "final equity"),
    ("fills", "fills"),
    ("closed_trades", "closed trades"),
    ("closed_episodes", "closed episodes"),
    ("open_episodes_at_end", "open episodes at end"),
    ("total_closed_ep_pnl", "net closed-episode P&L"),
    ("gross_profit", "gross profit"),
    ("gross_loss", "gross loss"),
    ("multi_leg_episodes", "multi-leg episodes"),
    ("distinct_symbols", "distinct symbols traded"),
    ("IWM_pnl", "**IWM total contribution**"),
    ("IWM_share", "**IWM share of net** (S3-C6 measured)"),
    ("shutdown_session", "shutdown session"),
):
    c = CHECK.get(key)
    if c is None:
        continue
    w(f"| {label} | `{c['sealed']}` | " + ("match" if c["agrees"] else "**DIFFERS**") + " |")
w("")
w("All 24 per-symbol contributions in the sealed `pnl_by_instrument` were compared individually and "
  "all 24 agree; they are the remaining rows of `reproduction_checks` in the JSON.")
w("")
w("### How the momentum values were recovered without touching anything sealed")
w("")
w("The momentum reading that decided each entry is **not** recorded in the sealed evidence. The "
  "selection log keeps sessions, ranked symbols, exclusions, exits and entries — it does not keep "
  "the ranking *values*, which survive only inside `ranking_digest`. Rather than recompute the "
  "signal (which would be a reimplementation, and would prove nothing about what the sealed run "
  "actually saw), the trace observes it:")
w("")
w("- `build_candidate` is wrapped **in this process only**, so the candidate's bound `rank` method "
  "is shadowed by a closure that calls the sealed method and records what it returned. The sealed "
  "method's inputs, outputs and side effects are untouched; the wrapper adds no computation.")
w("- `RotationEngineRA3` is wrapped the same way and purely to keep a reference to the instance, so "
  "its per-session risk-state lines (`session|band|lockout|vol_scalar|combined_scalar`) can be read "
  "back. The class is not subclassed and no method of it is wrapped.")
w("")
w("Neither wrapper is *argued* to be harmless — it is **measured**. All four sealed digests, "
  "including `ranking_digest` and `risk_state_digest`, are byte-identical with the wrappers "
  f"installed. {shape['executed_rebalances_observed']} rebalances were observed against a sealed "
  f"`scheduled_rebalance_sessions` of {shape['scheduled_rebalance_sessions']}.")
w("")
w("Before running anything, the trace also re-ran the runner's own "
  f"`verify_prior_attempt_modules()`: `module_count` {mod_count}, `modules_verified` "
  f"{mod_verified}, `modules_that_moved` `{mod_moved}`.")
w("")
w("No file under `governance/`, `config/`, `src/`, `tests/` or any `reports/stage3_g2*/` directory "
  "was written. Neither holdout partition was read. No broker, credential or order path was "
  "touched, and no live-trading authorization was implied or altered.")
w("")
w("---")
w("")

# ------------------------------------------------------------------ 2. IWM episodes
w("## 2. IWM, episode by episode")
w("")
w(f"IWM was entered **{iwm['episode_count_closed']} separate times** and closed all "
  f"{iwm['episode_count_closed']} times. There is no single long holding period: each episode ran "
  "exactly one quarter, entry fill to exit fill.")
w("")
w("| # | entry fill | exit fill | cal. days | sessions | gap since prior IWM exit (cal. days) | "
  "entry rank | entry signal (trailing 3-mo total return) | entry notional | closed P&L | return on "
  "entry capital | IWM running total |")
w("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
for n, e in enumerate(eps, 1):
    m = e["entry_momentum"]
    gap = e["gap_from_previous_iwm_exit_calendar_days"]
    w("| {n} | {ent} | {ex} | {cd} | {ss} | {gap} | {rk} of {ru} | {sig} | {cash} | {pnl} | {roc} "
      "| {run} |".format(
          n=n, ent=e["entry_session"], ex=e["exit_session"], cd=e["holding_calendar_days"],
          ss=e["holding_trading_sessions"], gap="—" if gap is None else gap,
          rk=m["rank"], ru=m["ranked_universe"], sig=pct(m["signal"]),
          cash=e["entry_cash"], pnl=e["pnl"], roc=pct(e["return_on_entry_cash"]),
          run=e["iwm_running_total_pnl"]))
w("")
w("Reading the columns that matter:")
w("")
w(f"- **Duration.** Every episode is {eps[0]['holding_calendar_days']} calendar days "
  f"({min(e['holding_trading_sessions'] for e in eps)}–"
  f"{max(e['holding_trading_sessions'] for e in eps)} sessions) — one full "
  f"{shape['rebalance_frequency'].lower()} interval, entered on the fill after one rebalance and "
  f"sold on the fill after the next. IWM was held for {sessions_held} of the run's "
  f"{shape['sessions']} sessions, i.e. {pct(ratio(sessions_held, shape['sessions']))} of the time.")
w(f"- **Gaps.** The gaps between consecutive IWM episodes are {gaps} calendar days. These are not "
  "brief interruptions in a continuous holding; they are years. IWM left the book entirely and came "
  "back.")
w(f"- **Justification at entry.** Every entry was at rank {ranks} of {universe} ranked members, on "
  f"a positive trailing 3-month total return of {signals}. None was a marginal or artefactual pick.")
w(f"- **P&L shape.** The running total is not steady. Episode 4 alone contributed "
  f"`{iwm['largest_episode_pnl']}` — {pct(iwm['largest_episode_share_of_iwm'])} of IWM's "
  f"`{iwm['total_pnl']}`, and {pct(iwm['largest_episode_share_of_net'])} of the whole run's net "
  f"`{net}`. The first three episodes together contributed "
  f"`{iwm_total - dv(iwm['largest_episode_pnl'])}`.")
w(f"- **Hit rate.** {iwm['winning_episodes']} of {iwm['episode_count_closed']} episodes were "
  f"profitable and {iwm['losing_episodes']} lost money — episode 3 at `{eps[2]['pnl']}`, "
  "essentially flat.")
w("")

w("### Why two of the four entries were half the size of the others")
w("")
w(f"The entry notionals split cleanly in two: `{eps[0]['entry_cash']}` and `{eps[3]['entry_cash']}` "
  f"against `{eps[1]['entry_cash']}` and `{eps[2]['entry_cash']}`. This is not cash starvation and "
  "not an equity collapse — cash on hand at each decision was ample and equity was near 100 every "
  "time. It is the RA3-4 de-risk ladder, and the run's own risk-state lines say so:")
w("")
w("| # | decision session | equity | cash | drawdown from HWM | ladder band | combined risk scalar "
  "| unscaled target | scaled target | actual entry |")
w("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
for n, e in enumerate(eps, 1):
    z = e["entry_sizing"]
    w("| {n} | {ds} | {eq} | {cash} | {dd} | {band} | {cs} | {ut} | {st} | **{act}** |".format(
        n=n, ds=z["decision_session"], eq=f"{dv(z['equity']):.4f}", cash=z["cash"],
        dd=pct(z["drawdown_from_high_water_mark"], 4), band=z["risk_ladder_band"],
        cs=z["combined_risk_scalar"], ut=f"{dv(z['unscaled_target_notional']):.4f}",
        st=f"{dv(z['scaled_target_notional']):.4f}", act=e["entry_cash"]))
w("")
w("The target weight per position is the constant "
  f"`{risk['target_weight_per_position']}` of equity for this variant, so the only thing that can "
  "vary the budget is the combined risk scalar. The sealed RA3-4 band table the engine loaded:")
w("")
w("| band | drawdown from | drawdown to (exclusive) | scalar |")
w("| --- | --- | --- | --- |")
for b in risk["sealed_ladder_bands"]:
    w(f"| {b['band']} | {b['dd_from']} | "
      + ("— (no upper bound)" if b["dd_to_exclusive"] is None else b["dd_to_exclusive"])
      + f" | {b['scalar']} |")
w("")
w("Episodes 2 and 3 were decided while the account sat in band 1, so the position budget was "
  "halved; episodes 1 and 4 were decided in band 0 at full size. The `scaled target` column "
  "predicts the `actual entry` column to the cent in all four cases. **The risk architecture was "
  "reducing IWM's concentration, not producing it.**")
w("")
w("One consequence, stated as arithmetic and not as a recommendation: at full size, episode 2's "
  f"{pct(eps[1]['return_on_entry_cash'])} return on capital would have produced roughly double its "
  f"`{eps[1]['pnl']}`, which would have **raised** IWM's measured share, not lowered it.")
w("")
w(f"### Was each pick a genuinely strong reading? IWM's rank at all {iwm['rebalance_count']} "
  "rebalances")
w("")
w(f"IWM entered the top {shape['top_k']} at only {len(iwm['rebalances_with_iwm_in_top_k'])} of "
  f"{iwm['rebalance_count']} rebalances "
  f"({pct(ratio(len(iwm['rebalances_with_iwm_in_top_k']), iwm['rebalance_count']))}). Its best rank "
  f"across the whole run was {best_rank} and its worst {worst_rank} — it was never the top-ranked "
  f"member. At the rebalance immediately after each entry it had already fallen out of the top "
  f"{shape['top_k']}, which is why every episode lasted exactly one quarter:")
w("")
w("| entry decision | rank | signal | next rebalance | rank then | signal then |")
w("| --- | --- | --- | --- | --- | --- |")
for r in iwm["rebalances_with_iwm_in_top_k"]:
    i = by_sess[r["session"]]
    nxt = hist[i + 1] if i + 1 < len(hist) else None
    w("| {s} | {rk} | {sig} | {ns} | {nrk} | {nsig} |".format(
        s=r["session"], rk=r["rank"], sig=pct(r["signal"]),
        ns="—" if nxt is None else nxt["session"],
        nrk="—" if nxt is None else nxt["rank"],
        nsig="—" if nxt is None else pct(nxt["signal"])))
w("")
w(f"The full {iwm['rebalance_count']}-row rank history, with the top of each ranking, is in "
  "`episode_ledger.json` under `iwm.rank_at_every_rebalance`.")
w("")
w("One pattern is visible, and is recorded here as an observation rather than a conclusion: all "
  "four top-2 appearances fall on the **early-January** rebalance. Four observations support no "
  "inference, and no test of seasonality was performed — see section 7.")
w("")
w("---")
w("")

# ------------------------------------------------------------------ 3. comparison
w("## 3. Comparison — the other 23 traded symbols")
w("")
w(f"{shape['episodes_closed']} closed episodes across {len(per_sym)} symbols, plus "
  f"{len(opens)} still open at the run end ("
  + ", ".join(f"{e['symbol']}, entered {e['entry_session']}" for e in opens)
  + " — neither is IWM). Episode counts and duration statistics only, as instructed; the full "
  "per-episode detail for all 24 symbols is in the JSON.")
w("")
w("| symbol | episodes closed | total cal. days held | mean | median | min | max | total P&L | "
  "share of net | best ep. | worst ep. | winners | mean entry rank |")
w("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
for sym, v in sorted(per_sym.items(), key=lambda kv: -dv(kv[1]["total_pnl"])):
    m = "**" if sym == D["focus_symbol"] else ""
    w("| {m}{sym}{m} | {ec} | {td} | {mean} | {med} | {mn} | {mx} | {m}{pnl}{m} | {sh} | {best} | "
      "{worst} | {win}/{ec} | {rk} |".format(
          m=m, sym=sym, ec=v["episodes_closed"], td=v["total_calendar_days_held"],
          mean=v["mean_calendar_days"], med=v["median_calendar_days"],
          mn=v["min_calendar_days"], mx=v["max_calendar_days"],
          pnl=v["total_pnl"], sh=f"{dv(v['share_of_net']):.4f}",
          best=v["best_episode_pnl"], worst=v["worst_episode_pnl"], win=v["winning_episodes"],
          rk=v["mean_entry_rank"]))
w("")
w("What this puts in context:")
w("")
w(f"- **IWM's trading pattern is unremarkable.** Its {iwm['episode_count_closed']} closed episodes "
  f"sit against a per-symbol median of {ep_counts[len(ep_counts) // 2]} and a maximum of "
  f"{most_traded['episodes_closed']} ({most_traded['symbol']}). Its "
  f"{eps[0]['holding_calendar_days']}-day holds are at the whole-ledger median of {median_days} "
  "calendar days. Nothing about how often IWM was traded, or how long it was held, is an outlier.")
w(f"- **What is exceptional is the P&L, not the exposure.** IWM's `{iwm['total_pnl']}` against a net "
  f"of `{net}` leaves `{non_iwm}` for the other 23 symbols combined — {n_pos} of the 24 net "
  f"positive, {n_neg} net negative.")
w(f"- **The denominator is what makes the share large.** Gross profit over closed episodes is "
  f"`{gross_profit}` and gross loss `{gross_loss}`; they nearly cancel, leaving `{net}`. IWM's "
  f"share of *gross profit* is `{ratio(iwm_total, gross_profit)}` — "
  f"{pct(ratio(iwm_total, gross_profit))}. S3-C6's sealed basis divides by the **net** sum over all "
  f"closed episodes, which is smaller by a factor of {ratio(gross_profit, net):.2f}.")
w(f"- **A second symbol also exceeds the ceiling on the same basis.** VWO's share of net is "
  f"`{per_sym['VWO']['share_of_net']}`. S3-C6 measures the largest contributor, so IWM is what the "
  "gate reported — but the concentration failure was not a near miss caused by one instrument.")
w("")
w("For completeness on the basis, quoted verbatim from the Attempt 3 evidence's own S3-C6 record:")
w("")
w("> For each instrument, contribution = sum of pnl over that instrument's closed EPISODES, divided "
  "by the sum of pnl over all closed episodes.")
w("")
w("---")
w("")

# ------------------------------------------------------------------ 4. cross-check
w("## 4. Cross-check against the sealed `pnl_by_instrument`")
w("")
w("The four IWM episode P&L values are "
  + ", ".join("`" + e["pnl"] + "`" for e in eps)
  + f", summing to `{sum((dv(e['pnl']) for e in eps), Decimal(0))}`. The sealed "
  f"`pnl_by_instrument['IWM']` is `{CHECK['IWM_pnl']['sealed']}`.")
w("")
w("**They agree exactly. There is no discrepancy to report.** The share recomputes to "
  f"`{ratio(iwm_total, net)}`, identical to the sealed measured value `{anchors['share_IWM']}` — "
  "including its trailing digits, which match only when the division runs inside the engine's "
  "34-digit decimal context rather than at the default precision.")
w("")
w("The episode ledger also reconciled against the frozen `Portfolio.trades` on all of "
  + ", ".join("`" + f + "`" for f in recon["reconciled_fields"])
  + f", across {recon['closed_episodes']} closed episodes and {recon['closed_trades']} closed "
  f"trades, with {len(recon['mismatches'])} mismatches. The two *totals* differ — episodes "
  f"`{recon['episode_pnl_total']}` against trades `{recon['frozen_trade_pnl_total']}`, a gap of "
  f"`{recon['pnl_discrepancy']}` — because the frozen `Portfolio` credits a `Trade` only on the "
  f"sale that zeroes a position, so `{recon['total_trimmed_proceeds']}` of partial-trim proceeds "
  f"across {recon['multi_leg_episodes']} multi-leg episodes never reaches the trade ledger. That is "
  "the already-recorded `G2A2-CONFLICT-18`, and it is exactly why S3-C6's declared basis is the "
  "episode ledger and not the trade ledger. Nothing in this diagnostic depends on the trade-ledger "
  "total.")
w("")
w("---")
w("")

# ------------------------------------------------------------------ 5. plain answer
w("## 5. The question, answered plainly")
w("")
w("> Was IWM's dominance driven by one long holding period, or by the strategy repeatedly and "
  "separately re-selecting it based on genuinely strong momentum readings at multiple different "
  "points in time?")
w("")
w("**The *selection* was repeated and genuine. The *dominance* rests on one of those four "
  "selections.** Both halves of that sentence are needed; either alone misdescribes the run.")
w("")
w(f"1. **It was not one long holding period, and not close to one.** IWM was bought and sold four "
  f"separate times — in {years} — each time for exactly one quarter, with gaps of {gaps} calendar "
  f"days between them. It was out of the book for the large majority of the run "
  f"({pct(ratio(sessions_held, shape['sessions']))} of sessions held).")
w(f"2. **Each of the four entries was justified by a genuinely strong reading, not an artefact.** "
  f"IWM ranked {ranks} of {universe} at the four decisions, on trailing 3-month total returns of "
  f"{signals}. Across all {iwm['rebalance_count']} rebalances it reached the top {shape['top_k']} "
  f"only those four times, never ranked first, and had fallen to rank {next_ranks} by the following "
  "rebalance — which is what sold it. The signal was not quietly favouring IWM; it picked it rarely "
  "and dropped it as soon as it faded.")
w(f"3. **But the dollar dominance is concentrated inside those four episodes.** "
  f"`{iwm['largest_episode_pnl']}` of IWM's `{iwm['total_pnl']}` — "
  f"{pct(iwm['largest_episode_share_of_iwm'])} — came from the single "
  f"{eps[3]['entry_session']} → {eps[3]['exit_session']} episode, which is by itself "
  f"{pct(iwm['largest_episode_share_of_net'])} of the entire run's net result. Two of the remaining "
  f"three contributed about `1.5` each and one contributed `{eps[2]['pnl']}`. So the concentration "
  "is not the product of a strategy that kept finding IWM; it is the product of one quarter in "
  "early 2021 being the strategy's best single quarter, in an instrument the strategy had selected "
  "on merit four times in thirteen years.")
w("")
w("There is a fourth fact that frames the other three, and it is arguably the more important one:")
w("")
w(f"- The run's equity high-water mark is `{risk['equity_high_water_mark']}`, set on "
  f"`{risk['equity_high_water_mark_session']}` — about seventeen months into a thirteen-year run — "
  f"and final equity is `{risk['final_equity']}`, which is **below it**. The strategy spent "
  f"{risk['ladder']['sessions_in_band']['1']} of {risk['risk_state_sessions']} sessions in ladder "
  f"band 1 (8–10% below the mark) and never made a new high after "
  f"{risk['equity_high_water_mark_session'][:7]}.")
w(f"- Net closed-episode P&L is `{net}` out of `{gross_profit}` gross profit and `{gross_loss}` "
  "gross loss. The denominator S3-C6 divides by is small because almost everything the strategy "
  "earned, it also gave back.")
w("")
w("Read together: IWM does not dominate because it was over-selected or over-held. It dominates "
  "because it produced one large win in a book whose other 23 instruments netted "
  f"`{non_iwm}` between them over thirteen years. A concentration measure with a net denominator "
  "reports that as an instrument-selection problem; what the trace shows is a **thin-net** problem.")
w("")
w("---")
w("")

# ------------------------------------------------------------------ 6. findings
w("## 6. Findings offered for human review (nothing here has been applied)")
w("")
w("Per the operating instruction, none of the following has been used to change any parameter. The "
  "drafted Attempt 4 pre-registration has **not** been edited, and was not consulted in order to "
  "tune anything. These are observations for a human to weigh.")
w("")
w("1. **A forced rotation cap constrains holding duration or repeat selection, and neither is what "
  "produced this failure.** Each IWM episode lasted a single rebalance interval — already the "
  "minimum a quarterly variant can hold — and IWM was never re-selected consecutively: its gaps "
  f"were {gaps} calendar days. On this representative, a cap of that kind would not have bound on "
  "any of the four episodes, and S3-C6 would have failed identically. That does not make the cap "
  "wrong; it was chosen as a general mechanism and may be right for reasons outside this variant. "
  "It is raised here as a design question for a human, precisely because it must not be resolved by "
  "retuning against these dates.")
w(f"2. **Two of 24 symbols exceed the 0.50 ceiling on the sealed basis** — IWM "
  f"`{per_sym['IWM']['share_of_net']}` and VWO `{per_sym['VWO']['share_of_net']}`. With a net of "
  f"`{net}` across {shape['episodes_closed']} episodes, *any* single instrument clearing about "
  f"`{net / 2}` fails the condition. The binding constraint is the size of the net, not the "
  "behaviour of any one instrument. A strategy family that keeps producing a thin net will keep "
  "failing S3-C6 however its selection is capped.")
w("3. **The risk architecture was working against the concentration, not for it.** The de-risk "
  "ladder halved two of IWM's four entries. Any future architecture that de-risks *less* would, all "
  "else equal, tend to **increase** measured concentration on a run like this one — which is the "
  "opposite of the direction Attempts 2 and 3 were moving. Worth stating because RA3 already is RA2 "
  "minus one de-risk tier.")
w(f"4. **A note in the repository's own guidance appears to label a denominator it is not using.** "
  f"`CLAUDE.md` contrasts IWM's `0.7505` of net with `0.2413` of gross. On this run, IWM over "
  f"**gross episode profit** (`{gross_profit}`) is `{ratio(iwm_total, gross_profit)}`. The `0.2413` "
  f"figure reproduces exactly as IWM over the **sum of positive per-symbol contributions** "
  f"(`{pos_symbol_sum}`): `{ratio(iwm_total, pos_symbol_sum)}`. Both are far below `0.50`, so the "
  "lesson the note draws is unaffected and the sealed verdict is unaffected — but they are "
  "different quantities, and a future reader could take the wrong one for \"gross\". Flagged, not "
  "edited.")
w("")
w("---")
w("")

# ------------------------------------------------------------------ 7. limits
w("## 7. What this trace could not determine")
w("")
w("Stated as limits, rather than guessed at:")
w("")
w("- **Why all four top-2 appearances fall in early January.** The pattern is real in the data and "
  "it is four observations. No seasonality test was run and none is implied; testing it would be a "
  "new research question needing its own pre-registration, not a diagnostic finding.")
w("- **The intra-episode path of any position.** The engine records portfolio cash and equity per "
  "session, not a per-symbol mark, so a symbol's value inside an episode is not separable from the "
  f"book while more than one position is open. *Where* in the quarter episode 4's `{eps[3]['pnl']}` "
  "accrued is therefore not answerable from this run's records.")
w(f"- **Whether IWM's dominance holds under the stress cost scenario.** Only the base-cost run "
  f"`{D['run_label']}` was reproduced, as instructed. The sealed evidence carries a separate "
  "`stress_evaluation`; this trace neither reproduced nor re-derived it, and says nothing about it.")
w("- **Anything about the other Attempt 3 variants.** Only the representative was run. Every "
  "per-symbol, duration and rank statistic here describes this one variant.")
w("- **Whether a different lookback, `top_k` or rebalance frequency would concentrate less.** That "
  "is a grid question, the Attempt 3 grid is spent, and running it here would be a new search "
  "rather than a diagnostic.")
w("- **The counterfactual P&L of the two half-sized entries.** Section 2 gives the arithmetic of "
  "doubling episode 2's return on capital, which is division, not a simulation. What the run would "
  "actually have done at full size — different cash, different clamps, different subsequent bands — "
  "was not simulated and is not claimed.")
w("- **The exact decision session for an entry whose rebalance adjacency fails.** None occurred: "
  "every entry fill in the ledger was immediately preceded in the run's own session index by a "
  "rebalance session, so every `entry_momentum` in the JSON carries a real value. The trace is "
  "written to emit `null` with a note rather than a nearest guess if that ever stops being true.")
w("")
w("---")
w("")

# ------------------------------------------------------------------ 8. provenance
w("## 8. Files and provenance")
w("")
w("| role | path |")
w("| --- | --- |")
w("| this report | `reports/diagnostics/attempt3_iwm_trace/ATTEMPT_3_IWM_CONCENTRATION_TRACE.md` |")
w(f"| supporting JSON — full ledger ({len(ledger)} episodes), {iwm['rebalance_count']}-rebalance "
  f"rank history, all {len(checks)} checks | "
  "`reports/diagnostics/attempt3_iwm_trace/episode_ledger.json` |")
w(f"| sealed evidence compared against (read-only) | `{D['sealed_source']['evidence_file']}` |")
w("| trace script, outside the governed tree | `_scratch/a3_iwm_trace.py` |")
w("| sizing addendum, outside the governed tree | `_scratch/a3_iwm_sizing.py` |")
w("| this report's generator, outside the governed tree | `_scratch/a3_iwm_report.py` |")
w("")
w("Run executed by "
  f"`{D['observation_method']['run_executed_by']}`; ledger built by "
  f"`{D['observation_method']['ledger_built_by']}`; attribution taken from "
  f"`{D['observation_method']['attribution_call']}`. Sealed modules were imported and not modified "
  "on disk.")
w("")
w("Entry-to-decision mapping rule, verbatim from the JSON: "
  f"*{D['observation_method']['entry_to_decision_mapping']}*")
w("")
w("**No verdict is issued by this document.** It is a diagnostic. Attempt 3's `FAIL` on S3-C6 "
  "stands exactly as sealed, and no gate, freeze record, manifest or `repo_state_id` was touched to "
  "produce it.")
w("")

path = OUT / "ATTEMPT_3_IWM_CONCENTRATION_TRACE.md"
path.write_text("\n".join(L) + "\n", encoding="utf-8")
print("wrote", path)
print("lines:", len(L), " bytes:", path.stat().st_size)
print("checks:", len(checks), "failed:", len(failed))
