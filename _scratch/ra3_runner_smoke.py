"""Exercise g2_runner_ra3.py in ascending order of cost, stopping at the first failure.

Ordered deliberately. Import is free, the seal readers are cheap, the dataset load is seconds, and a
single backtest is the first thing that costs real time. A KeyError in `gate_inputs` found after the
thirty-six-run grid would be the worst possible place to find it, and every subscript in this module
reaches into a sealed subtree that CFG-3105 renamed at least one key of.

Nothing here prints sealed prose: cp1252 kills the process on U+2014. Booleans, counts and digests.
"""

import json
import pathlib
import sys
import traceback

ROOT = pathlib.Path("d:/Product/stock-trade-alpaca/stockedge100")
sys.path.insert(0, str(ROOT / "src"))


def safe(text):
    return "".join(c if ord(c) < 128 else "<U+%04X>" % ord(c) for c in str(text))


def step(label, fn):
    print()
    print("=" * 100)
    print(label)
    try:
        return fn()
    except Exception as exc:
        print("   *** FAILED: %s: %s" % (type(exc).__name__, safe(exc)[:400]))
        traceback.print_exc()
        raise SystemExit(1)


print("=" * 100)
print("0. import")
from stockedge100.strategies import g2_runner_ra3 as RUN
from stockedge100.strategies import g2_rotation_ra3 as R
from stockedge100.strategies import g2_selection_v2 as S
from stockedge100.strategies import g2_gate_ra3 as G

print("   imported; the SelectionInputV2 surface guard ran at import and did not refuse")
print("   __all__ %d names" % len(RUN.__all__))
missing = [n for n in RUN.__all__ if not hasattr(RUN, n)]
print("   __all__ names that do not exist: %s" % missing)


def _labels():
    labels = RUN.run_labels()
    print("   labels                     %s" % list(labels))
    for label in labels:
        print("   scenario_for_label(%-9s) %s" % (label, RUN.scenario_for_label(label)))
    print("   GATE_RUN_LABEL / STRESS    %s / %s" % (RUN.GATE_RUN_LABEL, RUN.STRESS_RUN_LABEL))
    return labels


labels = step("1. run_labels + scenario_for_label", _labels)


def _ath():
    evidence = RUN.verify_prior_attempt_modules()
    for key in ("requirement", "conflict_ref", "module_count", "attempt_1_module_count",
                "attempt_2_module_count", "modules_that_moved"):
        print("   %-28s %s" % (key, evidence[key]))
    print("   digest_source              %s" % safe(evidence["digest_source"])[:96])
    for path in sorted(evidence["modules_verified"]):
        print("      %-64s %s" % (path, evidence["modules_verified"][path][:16]))
    return evidence


ath = step("2. AT-H: seventeen prior-attempt modules re-hashed (G2A3-CONFLICT-34)", _ath)


def _negative_ath():
    # An allow-list that only ever widens is not a check. Drop a module from the config list and the
    # paired comparison must refuse before a single file is opened.
    import stockedge100.strategies.g2_rotation_ra3 as RR
    real = RR.load_protocol
    doc = json.loads(json.dumps(real()))
    doc["prior_attempt_modules_immutable"]["attempt_2_modules"].pop()
    RR.load_protocol = lambda: doc
    RUN.load_protocol = lambda: doc
    try:
        RUN.verify_prior_attempt_modules()
        print("   *** NOT REFUSED -- the paired list comparison is vacuous ***")
    except Exception as exc:
        print("   refused a shortened config list: %s" % safe(exc)[:150])
    finally:
        RR.load_protocol = real
        RUN.load_protocol = real
    print("   load_protocol restored: %s" % (RUN.load_protocol is real))
    # and a duplicated path must refuse too, since the union would silently shrink
    doc2 = json.loads(json.dumps(real()))
    doc2["prior_attempt_modules_immutable"]["attempt_2_modules"][0] = (
        doc2["prior_attempt_modules_immutable"]["attempt_1_modules"][0]
    )
    RUN.load_protocol = lambda: doc2
    try:
        RUN.verify_prior_attempt_modules()
        print("   *** NOT REFUSED -- a duplicate across the two lists is invisible ***")
    except Exception as exc:
        print("   refused a duplicated path:     %s" % safe(exc)[:150])
    finally:
        RUN.load_protocol = real


step("3. AT-H negative controls", _negative_ath)


def _counterparts():
    ev = RUN.attempt_2_counterparts()
    for key in ("attempt_2_architecture_id", "attempt_3_architecture_id", "attempt_2_band_scalars",
                "attempt_3_band_scalars", "attempt_2_full_sizing_band", "attempt_3_full_sizing_band"):
        print("   %-28s %s" % (key, safe(ev[key])))
    print("   band_indices_are_not_comparable:")
    print("      %s" % safe(ev["band_indices_are_not_comparable"])[:210])
    rows = RUN.attempt_2_grid_rows()
    print("   attempt 2 rows keyed:      %d" % len(rows))
    sample = sorted(rows)[0]
    print("   sample key                 %s" % (sample,))
    print("   sample variant_id          %s" % rows[sample]["variant_id"])
    return ev


step("4. Attempt 2's band table and grid, read-only", _counterparts)


def _dataset():
    series = RUN.load_grid_dataset()
    print("   symbols                    %d" % len(series))
    latest = max(s.sessions[-1] for s in series.values())
    print("   latest session anywhere    %s  (must be < 2021-08-01)" % latest.isoformat())
    assert latest.isoformat() < "2021-08-01", latest
    return series


series = step("5. guard-loaded development dataset", _dataset)


def _span():
    ev = RUN.recheck_run_span(series, write=False)
    for key in ("requirement", "reverification_required"):
        print("   %s:" % key)
        print("      %s" % safe(ev[key])[:280])
    print("   config keys compared       %d" % len(ev["config_keys_compared"]))
    print("   governance keys compared   %d" % len(ev["governance_keys_compared"]))
    print("   governance prose keys      %s" % ev["governance_keys_not_a_measurement"])
    print("   independent keys compared  %d %s" % (len(ev["independent_derivation_keys_compared"]),
                                                   ev["independent_derivation_keys_compared"]))
    print("   differences                %s" % ev["differences"])
    m = ev["measured"]
    for key in ("run_start", "run_end", "run_sessions", "binding_symbol", "session_lists_agree",
                "monthly_rebalance_sessions", "quarterly_rebalance_sessions",
                "session_before_run_start_lookback_reference", "monthly_first_three",
                "quarterly_last_two"):
        print("   measured.%-42s %s" % (key, safe(m[key])))
    return ev


span = step("6. run-span reverification, 25 governance keys + 9 config keys + measure_span", _span)


def _span_negative():
    # The seal-widening guard: a key the seal records and this module neither computes nor names as
    # prose must refuse, rather than being skipped by a set-intersection loop.
    real = RUN._governance_protocol
    doc = json.loads(json.dumps(real()))
    doc["run_span_measured_from_disk"]["a_key_added_after_the_seal"] = 1
    RUN._governance_protocol = lambda: doc
    try:
        RUN.recheck_run_span(series, write=False)
        print("   *** NOT REFUSED -- an added seal key is silently skipped ***")
    except Exception as exc:
        print("   refused an added seal key:   %s" % safe(exc)[:170])
    finally:
        RUN._governance_protocol = real
    # and a key that vanished from the seal must refuse too
    doc2 = json.loads(json.dumps(real()))
    doc2["run_span_measured_from_disk"].pop("monthly_first_three")
    RUN._governance_protocol = lambda: doc2
    try:
        RUN.recheck_run_span(series, write=False)
        print("   *** NOT REFUSED -- a removed seal key is invisible ***")
    except Exception as exc:
        print("   refused a removed seal key:  %s" % safe(exc)[:170])
    finally:
        RUN._governance_protocol = real
    # and a changed value must be a blocker, not a value to adopt
    doc3 = json.loads(json.dumps(real()))
    doc3["run_span_measured_from_disk"]["run_sessions"] = 3277
    RUN._governance_protocol = lambda: doc3
    try:
        RUN.recheck_run_span(series, write=False)
        print("   *** NOT REFUSED -- a changed span value is adopted ***")
    except Exception as exc:
        print("   refused a changed value:     %s" % safe(exc)[:170])
    finally:
        RUN._governance_protocol = real
    print("   _governance_protocol restored: %s" % (RUN._governance_protocol is real))


step("7. run-span negative controls", _span_negative)


def _one_run():
    variant = R.rotation_variants()[0]
    print("   variant                    %s" % variant.variant_id)
    run = RUN.run_one(variant, RUN.GATE_RUN_LABEL, series)
    print("   run_id                     %s" % run.run_id)
    print("   scenario                   %s" % run.scenario)
    print("   fills                      %d" % run.fill_count)
    print("   shutdown_fired             %s" % run.shutdown_fired)
    print("   equity sessions            %d" % len(run.result.equity_curve))
    print("   closed episodes            %d" % len(run.ledger.closed_episodes))
    print("   reconciliation             %s" % {k: run.reconciliation[k] for k in
                                                ("single_leg_compared", "mismatch_count", "vacuous")})
    risk = run.risk
    print("   ladder                     %s" % {k: risk["ladder"][k] for k in
                                                ("descents", "ascents", "deepest_band", "final_band")})
    print("   ladder sessions_in_band    %s" % risk["ladder"]["sessions_in_band"])
    print("   lockout                    %s" % risk["lockout"])
    print("   stops                      %s" % risk["stops"])
    print("   combined_scalar minimum    %s" % risk["combined_scalar"]["minimum"])
    prov = risk["architecture_provenance"]
    print("   provenance keys            %s" % list(prov))
    print("   measurement keys           %d" % len(run.measurement))
    for key in ("total_return", "max_drawdown", "profit_factor", "closed_trades",
                "shutdown_session"):
        print("   measurement.%-14s     %s" % (key, safe(run.measurement[key])[:44]))
    return run


run = step("8. one real run (the first cell of the grid, #BASE)", _one_run)


def _report_shape():
    rows = RUN.grid_report([run])
    print("   rows                       %d" % len(rows))
    row = rows[0]
    print("   columns                    %d" % len(row))
    print("   column names:")
    names = sorted(row)
    for i in range(0, len(names), 4):
        print("      %s" % "  ".join("%-30s" % n for n in names[i:i + 4]))
    print("   attempt_2 block keys       %s" % sorted(row["attempt_2"]))
    print("   selection_score present    %s" % ("selection_score" in row))
    return rows


step("9. grid_report column shape on a single run", _report_shape)


def _selection_projection():
    # selection_inputs refuses an incomplete grid on purpose, so drive the projection directly to
    # prove the six fields are populated from the run and nothing else is reachable.
    item = S.SelectionInputV2(
        variant_id=run.variant.variant_id,
        shutdown_events=1 if run.shutdown_fired else 0,
        fill_count=run.fill_count,
        ladder_descents=int(run.risk["ladder"]["descents"]),
        lockout_arms=int(run.risk["lockout"]["arms"]),
        stops_filled=int(run.risk["stops"]["filled"]),
    )
    print("   projected                  %s" % (item,))
    try:
        RUN.selection_inputs([run])
        print("   *** NOT REFUSED -- a one-run grid selected a representative ***")
    except Exception as exc:
        print("   refused a one-run grid:    %s" % safe(exc)[:140])


step("10. the return-blind projection", _selection_projection)

print()
print("=" * 100)
print("SMOKE COMPLETE -- every path except the full grid, selection and the gate has run")
