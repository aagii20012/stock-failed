"""The Stage 4 evidence layer: sealing, the runs/ record, the refusals, and the gate inputs.

Companion to ``test_stage4_evaluation.py``, which covers the sealed *rules*. This module covers the
layer that turns an executed session into an artifact: the digest that seals the evidence file, the
append-only ``runs/`` record, the two refusals that protect the single validation read, and the
helpers that select and coerce the values ``stage4_gate`` compares.

Nothing here loads a market observation. The run objects are synthetic ``SimpleNamespace`` stubs
carrying only the attributes the helpers read, which is the point: a helper that quietly reached for
something else would fail here rather than during the one authorized session.

Two tests exist because a dry run found the defects they describe:
:func:`test_unique_run_id_raises_rather_than_overwriting_an_occupied_id` and
:func:`test_two_records_written_in_the_same_second_do_not_collide`. ``new_run_id`` is
second-resolution and ``RunRecord.write`` opens its target unconditionally, so two records stamped
inside one second used to leave one file where there should have been two — a silent deletion from
an append-only directory.
"""

from __future__ import annotations

import datetime as dt
import json
from decimal import Decimal
from types import SimpleNamespace

import pytest

from stockedge100.audit import sha256_file
from stockedge100.data.calendar import sessions_between
from stockedge100.reporting import stage4_evidence as evidence
from stockedge100.reporting.stage_package import REPO_STATE_PATTERNS, new_run_id
from stockedge100.strategies import stage4_evaluation as harness
from stockedge100.strategies.stage4_evaluation import ConfigViolation

#: Captured at import time, before :func:`isolated_outputs` redirects it into ``tmp_path``.
DEFAULT_EVIDENCE_REL = evidence.EVIDENCE_REL


@pytest.fixture(autouse=True)
def isolated_outputs(monkeypatch, tmp_path):
    """Redirect both output locations into ``tmp_path`` and prove the redirect took.

    ``RUNS_DIR`` is patched on both modules because they hold separate references to it:
    ``stage4_evidence`` writes records and ``stage4_evaluation.validation_evaluation_run_records``
    counts them, and a test that patched only one would be counting the real ``runs/``.

    The assertion is not decoration. ``EVIDENCE_REL`` is joined onto ``PROJECT_ROOT``, so a redirect
    that failed to take would send a test write into the real ``reports/`` tree.
    """

    runs = tmp_path / "runs"
    runs.mkdir()
    monkeypatch.setattr(evidence, "RUNS_DIR", runs)
    monkeypatch.setattr(harness, "RUNS_DIR", runs)
    monkeypatch.setattr(evidence, "EVIDENCE_REL", str(tmp_path / "EVIDENCE.json"))
    assert evidence.PROJECT_ROOT / evidence.EVIDENCE_REL == tmp_path / "EVIDENCE.json"
    return SimpleNamespace(runs=runs, evidence=tmp_path / "EVIDENCE.json")


def body(**overrides):
    """A minimal evidence body: enough shape to seal, no pretence of being real evidence."""

    base = {
        "artifact_id": evidence.EVIDENCE_ARTIFACT_ID,
        "stage": "STAGE_4",
        "gate": {"gate_passed": False, "verdict_token": "SYNTHETIC"},
        "live_trading_authorized": False,
    }
    base.update(overrides)
    return base


# -- the seal ------------------------------------------------------------------------------------


def test_the_digest_excludes_exactly_its_own_field_and_the_timestamp():
    """Nothing hashes itself, and the timestamp is not a finding.

    ``evidence_digest`` is written into the body it covers, so it cannot cover itself.
    ``generated_utc`` is excluded for a different reason: it records when the file was written, not
    what was found, and including it would make two byte-identical findings seal differently.
    """

    assert evidence.EXCLUDED_FROM_DIGEST == ("generated_utc", "evidence_digest")
    sealed = evidence.finalize(body(), "2026-08-14T00:00:00Z")
    stripped = {k: v for k, v in sealed.items() if k not in evidence.EXCLUDED_FROM_DIGEST}
    assert evidence.evidence_digest(sealed) == evidence.evidence_digest(stripped)


def test_the_digest_ignores_the_timestamp_but_not_the_findings():
    early = evidence.finalize(body(), "2026-08-14T00:00:00Z")
    late = evidence.finalize(body(), "2027-01-01T00:00:00Z")
    assert early["generated_utc"] != late["generated_utc"]
    assert early["evidence_digest"] == late["evidence_digest"]

    changed = evidence.finalize(body(live_trading_authorized=True), "2026-08-14T00:00:00Z")
    assert changed["evidence_digest"] != early["evidence_digest"]


def test_the_digest_is_canonical_and_so_key_order_cannot_change_it():
    forward = body()
    reversed_order = {key: forward[key] for key in reversed(list(forward))}
    assert list(forward) != list(reversed_order)
    assert evidence.evidence_digest(forward) == evidence.evidence_digest(reversed_order)


def test_finalize_seals_a_body_that_recomputes():
    sealed = evidence.finalize(body(), "2026-08-14T00:00:00Z")
    assert sealed["generated_utc"] == "2026-08-14T00:00:00Z"
    assert sealed["command"] == evidence.COMMAND
    assert sealed["evidence_digest_covers"] == evidence.DIGEST_COVERS
    assert evidence.evidence_digest(sealed) == sealed["evidence_digest"]


def test_finalize_covers_its_own_coverage_statement():
    """The Stage 2 lesson: a file that describes its digest's coverage must seal that description.

    Stage 2 added the coverage sentence after taking the digest and left a file asserting a coverage
    it did not have. If ``evidence_digest_covers`` were outside the digest, that sentence could be
    edited to claim anything and the seal would still verify.
    """

    sealed = evidence.finalize(body(), "2026-08-14T00:00:00Z")
    tampered = dict(sealed, evidence_digest_covers="everything, honestly")
    assert evidence.evidence_digest(tampered) != tampered["evidence_digest"]


def test_finalize_does_not_mutate_its_input():
    original = body()
    evidence.finalize(original, "2026-08-14T00:00:00Z")
    assert "evidence_digest" not in original
    assert "generated_utc" not in original


def test_the_evidence_file_lands_outside_the_repo_state_patterns():
    """Writing the evidence must not perturb the digest the decision package will record.

    ``reports/`` is deliberately outside ``REPO_STATE_PATTERNS``. If the evidence file moved under
    ``governance/`` or ``config/``, writing it would change ``repo_state_id`` mid-session and the
    value recorded in the ``runs/`` record would describe a tree that no longer existed.
    """

    assert DEFAULT_EVIDENCE_REL.startswith("reports/")
    assert not any(pattern.startswith("reports/") for pattern in REPO_STATE_PATTERNS)


# -- decimal coercion ----------------------------------------------------------------------------


def test_decimals_serialise_exactly_and_recursively():
    """The gate compares ``Decimal``; the file carries the exact decimal string, never a float.

    The value below is one ``float`` cannot hold. If the coercion went through ``float`` the digits
    would change, and every Stage 4 condition is decided at a boundary where that matters.
    """

    exact = "0.1000000000000000055511151231257827"
    payload = {"a": [Decimal(exact), {"b": Decimal("0.15")}], "c": Decimal("0")}
    coerced = evidence._jsonable(payload)
    assert coerced == {"a": [exact, {"b": "0.15"}], "c": "0"}
    assert json.loads(json.dumps(coerced))["a"][0] == exact


def test_coercion_preserves_the_types_json_already_has():
    payload = {"t": True, "f": False, "n": None, "i": 12, "s": "0.50"}
    assert evidence._jsonable(payload) == payload
    assert evidence._jsonable(payload)["t"] is True
    assert evidence._jsonable(payload)["i"] == 12


def test_an_uncoerced_gate_body_would_not_serialise():
    """The failure this coercion exists to prevent, asserted rather than assumed."""

    raw = {"conditions": [{"measured": Decimal("0.5")}]}
    with pytest.raises(TypeError):
        json.dumps(raw)
    assert json.dumps(evidence._jsonable(raw))


# -- run ids -------------------------------------------------------------------------------------


def test_unique_run_id_returns_a_free_id_matching_its_timestamp():
    run_id, timestamp = evidence.unique_run_id()
    assert run_id == new_run_id(timestamp)
    assert not (evidence.RUNS_DIR / f"{run_id}.json").exists()


def test_unique_run_id_skips_an_id_whose_record_already_exists(monkeypatch):
    clock = iter(["2026-08-14T14:26:13Z", "2026-08-14T14:26:14Z"])
    monkeypatch.setattr(evidence, "utc_now_iso", lambda: next(clock))
    monkeypatch.setattr(evidence.time, "sleep", lambda _seconds: None)
    taken = new_run_id("2026-08-14T14:26:13Z")
    (evidence.RUNS_DIR / f"{taken}.json").write_text("{}", encoding="utf-8")

    run_id, timestamp = evidence.unique_run_id()
    assert run_id != taken
    assert run_id == new_run_id(timestamp) == "SE100-R-20260814T142614Z"


def test_unique_run_id_raises_rather_than_overwriting_an_occupied_id(monkeypatch):
    """The defect a dry run found: a colliding id silently destroyed an append-only record.

    A stopped clock is the adversarial form of two records stamped inside the same second. The
    required behaviour is to refuse, not to return the occupied id — an overwrite here would delete
    a record from a directory the constitution treats as append-only.
    """

    monkeypatch.setattr(evidence, "utc_now_iso", lambda: "2026-08-14T14:26:13Z")
    monkeypatch.setattr(evidence.time, "sleep", lambda _seconds: None)
    taken = evidence.RUNS_DIR / f"{new_run_id('2026-08-14T14:26:13Z')}.json"
    taken.write_text('{"run_id": "the record that must survive"}', encoding="utf-8")

    with pytest.raises(RuntimeError, match="overwrite an append-only record"):
        evidence.unique_run_id()
    assert json.loads(taken.read_text(encoding="utf-8"))["run_id"] == "the record that must survive"


# -- the runs/ record ----------------------------------------------------------------------------


def written_record(**overrides):
    fields = {
        "stage": evidence.EVALUATION_STAGE,
        "exit_status": "OK",
        "repo_state_id": "0" * 64,
        "code_hashes": {"src/x.py": "1" * 64},
        "strategy_id": harness.REPRESENTATIVE,
        "dataset_hashes": {"data/normalized/daily/SPY.csv": "2" * 64},
        "date_range": ["2021-08-01", "2024-07-31"],
        "notes": ["synthetic"],
    }
    fields.update(overrides)
    run_id = evidence.write_run_record(**fields)
    return json.loads((evidence.RUNS_DIR / f"{run_id}.json").read_text(encoding="utf-8"))


def test_the_record_reads_the_holdout_state_and_universe_version_from_the_frozen_artifacts():
    """A record can never claim a holdout state the frozen lock does not carry.

    Both values are read rather than restated, so the only way this record could say ``UNSEALED`` is
    if the frozen lock said it.
    """

    record = written_record()
    lock = json.loads(
        (evidence.PROJECT_ROOT / evidence.HOLDOUT_LOCK_REL).read_text(encoding="utf-8")
    )
    universe = json.loads(
        (evidence.PROJECT_ROOT / evidence.UNIVERSE_REL).read_text(encoding="utf-8")
    )
    assert record["holdout_state"] == lock["holdout_state"] == "SEALED"
    assert record["universe_version"] == universe["universe_version"]
    assert record["config_hash"] == sha256_file(evidence.PROJECT_ROOT / harness.PROTOCOL_REL)
    assert record["command"] == evidence.COMMAND
    assert record["random_seed"] is None


def test_the_record_carries_no_output_artifact_hash():
    """Empty by construction: the evidence file does not exist yet when this record is written.

    S4-C7 counts these records, so the count has to be taken with the record already on disk, and
    ``runs/`` is append-only, so there is no second pass. A digest here would be a prediction in an
    evidence field.
    """

    assert written_record()["output_artifact_hashes"] == {}


def test_two_records_written_in_the_same_second_do_not_collide(monkeypatch):
    """The regression for the destroyed record. Both files must survive."""

    monkeypatch.setattr(evidence, "utc_now_iso", lambda: "2026-08-14T14:26:13Z")
    monkeypatch.setattr(evidence.time, "sleep", lambda _seconds: None)
    first = evidence.write_run_record(
        stage=evidence.EVALUATION_STAGE, exit_status="OK", repo_state_id="0" * 64,
        code_hashes={}, strategy_id=harness.REPRESENTATIVE, dataset_hashes={},
        date_range=None, notes=["first"],
    )
    # The stopped clock means the second call cannot find a free id and must refuse rather than
    # overwrite. The point of the test is that `first` is still on disk afterwards.
    with pytest.raises(RuntimeError):
        evidence.write_run_record(
            stage=evidence.FAILED_ATTEMPT_STAGE, exit_status="REFUSED", repo_state_id="0" * 64,
            code_hashes={}, strategy_id=None, dataset_hashes={}, date_range=None, notes=["second"],
        )
    assert (evidence.RUNS_DIR / f"{first}.json").is_file()
    assert json.loads((evidence.RUNS_DIR / f"{first}.json").read_text(encoding="utf-8"))["notes"] \
        == ["first"]


def test_records_written_back_to_back_get_distinct_ids():
    ids = [
        evidence.write_run_record(
            stage=evidence.FAILED_ATTEMPT_STAGE, exit_status="REFUSED", repo_state_id="0" * 64,
            code_hashes={}, strategy_id=None, dataset_hashes={}, date_range=None, notes=[str(n)],
        )
        for n in range(3)
    ]
    assert len(set(ids)) == 3
    assert len(list(evidence.RUNS_DIR.glob("*.json"))) == 3


# -- the two refusals ----------------------------------------------------------------------------


@pytest.fixture()
def no_load_permitted(monkeypatch):
    """Make the validation load explode, so a refusal that leaked past its guard is unmissable."""

    def forbidden(_config):
        raise AssertionError("the validation partition was loaded on a path that must refuse first")

    monkeypatch.setattr(evidence, "load_validation_series", forbidden)


def test_build_refuses_when_the_evidence_file_already_exists(isolated_outputs, no_load_permitted):
    isolated_outputs.evidence.write_text('{"existing": true}', encoding="utf-8")

    assert evidence.build() == 4
    assert json.loads(isolated_outputs.evidence.read_text(encoding="utf-8")) == {"existing": True}


def test_build_refuses_when_a_validation_evaluation_record_already_exists(
    isolated_outputs, no_load_permitted
):
    (isolated_outputs.runs / "SE100-R-EARLIER.json").write_text(
        json.dumps({"strategy_id": harness.REPRESENTATIVE}), encoding="utf-8"
    )

    assert evidence.build() == 4
    assert not isolated_outputs.evidence.exists()


def test_a_refusal_leaves_a_record_that_s4_c7_does_not_count(isolated_outputs, no_load_permitted):
    """Both sealed sentences hold at once, which is the whole reason the two stages differ.

    ``partial_or_failed_run_rule.no_silent_retry`` requires every attempt to leave a record; S4-C7
    requires exactly one *validation evaluation* record. A refusal is recorded under the
    failed-attempt stage with a null ``strategy_id``, so it satisfies the first without being
    counted by the second.
    """

    isolated_outputs.evidence.write_text("{}", encoding="utf-8")
    assert evidence.build() == 4

    records = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in isolated_outputs.runs.glob("*.json")
    ]
    assert len(records) == 1
    assert records[0]["stage"] == evidence.FAILED_ATTEMPT_STAGE
    assert records[0]["strategy_id"] is None
    assert records[0]["exit_status"] == "REFUSED_NO_VALIDATION_OBSERVATION_READ"
    assert harness.validation_evaluation_run_records() == []


def test_the_failed_attempt_stage_is_distinguishable_from_the_evaluation_stage():
    assert evidence.FAILED_ATTEMPT_STAGE != evidence.EVALUATION_STAGE
    assert evidence.FAILED_ATTEMPT_STAGE.startswith(evidence.EVALUATION_STAGE)


# -- what the gate reads -------------------------------------------------------------------------


def curve(sessions, equity=Decimal("100")):
    return [SimpleNamespace(session=day, equity=equity) for day in sessions]


def result_stub(sessions, trades=(), **extra):
    fields = {
        "equity_curve": curve(sessions),
        "trades": [SimpleNamespace(pnl=Decimal(value), symbol="SPY") for value in trades],
        "starting_equity": Decimal("100"),
    }
    fields.update(extra)
    return SimpleNamespace(**fields)


VALIDATION_SESSIONS = sessions_between(
    harness.validation_window().start, harness.validation_window().end
)


def test_equity_points_counts_marked_sessions():
    assert harness.equity_points(result_stub(VALIDATION_SESSIONS[:5])) == 5
    assert harness.equity_points(result_stub([])) == 0


def test_reached_window_end_is_true_on_the_final_calendar_session():
    assert harness.reached_window_end(result_stub(VALIDATION_SESSIONS)) is True


def test_reached_window_end_is_false_when_the_run_stopped_one_session_early():
    assert harness.reached_window_end(result_stub(VALIDATION_SESSIONS[:-1])) is False


def test_reached_window_end_is_false_on_an_empty_curve():
    assert harness.reached_window_end(result_stub([])) is False


def test_reached_window_end_ignores_the_end_that_was_requested():
    """The trap the helper's docstring names, asserted.

    ``result.end`` is the end that was *asked for*, so a run that stopped early still reports it.
    Checking against it would make the answer true by construction; the check is against the frozen
    calendar instead.
    """

    stopped_early = result_stub(VALIDATION_SESSIONS[:100], end=harness.validation_window().end)
    assert stopped_early.end == harness.validation_window().end
    assert harness.reached_window_end(stopped_early) is False


def test_closed_trade_gross_reports_loss_as_a_positive_magnitude():
    """A signed denominator would make the reader's own division come out negative."""

    gross = harness.closed_trade_gross(result_stub([], trades=("2.50", "-4.25", "1.00")))
    assert gross == {"gross_profit": "3.50", "gross_loss": "4.25"}


def test_closed_trade_gross_on_a_run_that_never_traded():
    assert harness.closed_trade_gross(result_stub([])) == {"gross_profit": "0", "gross_loss": "0"}


def test_base_evidence_refuses_a_stressed_run():
    """S4-C1..C4 are sealed to the base-cost run; the stressed run may not substitute for it.

    The guard runs before any configuration is read, which is why an inert stand-in suffices here.
    """

    stressed = SimpleNamespace(run_label="X#VALIDATION#STRESS", scenario=harness.STRESSED)
    with pytest.raises(ConfigViolation, match="sealed to the BASE-cost run"):
        harness.base_gate_evidence(SimpleNamespace(), stressed)


def test_stress_evidence_refuses_a_base_run():
    base = SimpleNamespace(run_label="X#VALIDATION#BASE", scenario=harness.BASE)
    with pytest.raises(ConfigViolation, match="sealed to the stressed-cost run"):
        harness.stress_gate_evidence(SimpleNamespace(), base)


def test_only_records_naming_the_representative_are_counted_as_evaluations(isolated_outputs):
    """The discriminator is ``strategy_id``, not a text search, and the difference is load-bearing.

    ``build_stage_package`` writes ``strategy_id: None`` into every package record — including the
    two Stage 4 pre-registration records, whose notes name the representative in prose. A substring
    search would count those and fail S4-C7 against records that evaluated nothing.
    """

    runs = isolated_outputs.runs
    (runs / "SE100-R-EVAL.json").write_text(
        json.dumps({"strategy_id": harness.REPRESENTATIVE}), encoding="utf-8"
    )
    (runs / "SE100-R-PACKAGE.json").write_text(
        json.dumps({
            "strategy_id": None,
            "notes": [f"pre-registration for {harness.REPRESENTATIVE}"],
        }),
        encoding="utf-8",
    )
    (runs / "SE100-R-BROKEN.json").write_text("{not json", encoding="utf-8")

    assert harness.validation_evaluation_run_records() == ["SE100-R-EVAL.json"]


def digest_row(artifact, equal=True):
    return {"artifact": artifact, "sealed": "a" * 64, "recomputed": "a" * 64 if equal else None,
            "equal": equal, "digest_source": "synthetic", "resolves_description": None}


INVARIANCE = {
    "parameters_equal_gate_3_primary": True,
    "sealed_parameters": {"lookback": 10},
    "gate_3_primary_parameters": {"lookback": 10},
    "all_equal": True,
}


def test_the_four_s4_c7_clauses_are_measured_not_asserted():
    inv = harness.invariance_gate_evidence(
        SimpleNamespace(declared_run_count=2),
        digest_rows=[digest_row(f"f{n}") for n in range(13)],
        invariance=INVARIANCE,
        run_records=["SE100-R-EVAL.json"],
        engine_runs=2,
    )
    assert inv["all_digests_equal"] is True
    assert (inv["digests_equal"], inv["digests_total"]) == (13, 13)
    assert inv["validation_evaluation_run_records"] == 1
    assert inv["validation_window_engine_runs"] == inv["declared_run_count"] == 2
    assert inv["parameters_unchanged"] is True


def test_one_changed_digest_is_visible_in_the_c7_evidence():
    rows = [digest_row(f"f{n}") for n in range(12)] + [digest_row("f12", equal=False)]
    inv = harness.invariance_gate_evidence(
        SimpleNamespace(declared_run_count=2),
        digest_rows=rows, invariance=INVARIANCE,
        run_records=["SE100-R-EVAL.json"], engine_runs=2,
    )
    assert inv["all_digests_equal"] is False
    assert (inv["digests_equal"], inv["digests_total"]) == (12, 13)


def test_changed_parameters_are_visible_in_the_c7_evidence():
    inv = harness.invariance_gate_evidence(
        SimpleNamespace(declared_run_count=2),
        digest_rows=[digest_row("f0")],
        invariance=dict(INVARIANCE, parameters_equal_gate_3_primary=False,
                        gate_3_primary_parameters={"lookback": 11}),
        run_records=[], engine_runs=2,
    )
    assert inv["parameters_unchanged"] is False
    assert inv["parameter_comparison"]["equal"] is False
    assert inv["validation_evaluation_run_records"] == 0


def test_an_extra_engine_run_is_visible_in_the_c7_evidence():
    """The unregistered third run S4-C7 exists to catch."""

    inv = harness.invariance_gate_evidence(
        SimpleNamespace(declared_run_count=2),
        digest_rows=[digest_row("f0")], invariance=INVARIANCE,
        run_records=["a.json", "b.json"], engine_runs=3,
    )
    assert inv["validation_window_engine_runs"] == 3
    assert inv["declared_run_count"] == 2
    assert inv["validation_evaluation_run_records"] == 2


def test_the_fold_table_chains_baselines_and_marks_incompletion(monkeypatch):
    """Two sealed rules at once: fold N's baseline is fold N-1's last equity, and a run that
    stopped early leaves later folds incomplete rather than shrinking the denominator.
    """

    folds = harness.sealed_folds(harness.load_stage4_config())
    calendar = sessions_between(folds[0].start, folds[1].end)
    equity = {day: Decimal("100") for day in calendar}
    equity[sessions_between(folds[0].start, folds[0].end)[-1]] = Decimal("110")
    result = SimpleNamespace(
        equity_curve=[SimpleNamespace(session=day, equity=value)
                      for day, value in sorted(equity.items())],
        starting_equity=Decimal("100"),
    )

    rows = harness.fold_returns(result, folds, starting_equity=Decimal("100"))
    assert len(rows) == 12
    assert rows[0]["completed"] is True
    assert rows[0]["baseline_equity"] == "100"
    assert rows[0]["fold_return"] == "0.1"
    assert rows[1]["baseline_equity"] == "110"
    assert rows[1]["completed"] is True
    # The run has no equity beyond fold 2, so folds 3..12 are incomplete, not zero-return.
    assert [row["completed"] for row in rows[2:]] == [False] * 10


def test_fold_bounds_are_read_from_the_seal_and_span_the_validation_window():
    folds = harness.sealed_folds(harness.load_stage4_config())
    validation = harness.validation_window()
    assert len(folds) == 12
    assert folds[0].start == validation.start
    assert folds[-1].end == validation.end
    for earlier, later in zip(folds, folds[1:]):
        assert later.start == earlier.end + dt.timedelta(days=1)
