"""Stage 1 — adversarial tests: prove the guards fire.

A battery that has only ever seen clean data is untested. Everything here injects a defect that
Gate 1 exists to catch and asserts the corresponding guard reports it. The controls at the top
matter as much as the failures: they establish that a clean synthetic series passes every check, so
each failure below is caused by the injected defect and not by the harness.

Nothing here touches the real evidence. Synthetic frames are built in memory, quarantine output is
redirected to ``tmp_path``, and the two tests that exercise real modules redirect every write.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pandas as pd
import pytest

from stockedge100.data import config as config_module
from stockedge100.data import quarantine as quarantine_module
from stockedge100.data.calendar import sessions_between
from stockedge100.data.config import PreRegistrationViolation, load_stage1_config
from stockedge100.data.normalize import COLUMNS
from stockedge100.data.partition import compute_partition
from stockedge100.data.validate import run_checks
from stockedge100.universe import build as universe_build
from stockedge100.universe.build import WindowViolation, development_frame, measure

# Development window 2015-01-02..2016-07-31, so the synthetic quarter below sits inside it.
PARTITION = compute_partition(dt.date(2021, 7, 30), dt.date(2015, 1, 2))
ACQUISITION_DATE = dt.date(2021, 7, 30)
SEMANTICS = {"ohlc_split_adjusted": True}

FIRST, LAST = dt.date(2015, 1, 2), dt.date(2015, 3, 31)


@pytest.fixture(scope="module")
def config():
    return load_stage1_config()


@pytest.fixture(autouse=True)
def isolated_quarantine(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Never let an adversarial fixture write into the real quarantine directory."""
    target = tmp_path / "quarantine"
    monkeypatch.setattr(quarantine_module, "QUARANTINE_DIR", target)
    return target


def clean_frame() -> pd.DataFrame:
    """A flat, defect-free daily series on real XNYS sessions."""
    sessions = [day.isoformat() for day in sessions_between(FIRST, LAST)]
    frame = pd.DataFrame(
        {
            "session": sessions,
            "open": 100.0,
            "high": 100.0,
            "low": 100.0,
            "close": 100.0,
            "adj_close": 100.0,
            "volume": 1_000_000,
            "dividend": 0.0,
            "split_ratio": 0.0,
        }
    )
    return frame[COLUMNS]


def statuses(
    config,
    frame: pd.DataFrame,
    *,
    acquisition_date: dt.date = ACQUISITION_DATE,
    expected_actions: list | None = None,
) -> dict[str, str]:
    battery = config.data_source["validation_battery"]
    results = run_checks(
        "SYNTH",
        frame.reset_index(drop=True),
        severities={check["id"]: check["severity"] for check in battery["checks"]},
        tolerances=config.tolerances,
        semantics=SEMANTICS,
        expected_actions=expected_actions or [],
        acquisition_date=acquisition_date,
        partition=PARTITION,
    )
    return {result.check_id: result.status for result in results}


# --------------------------------------------------------------------------------------------
# Controls
# --------------------------------------------------------------------------------------------


def test_a_clean_series_passes_every_check(config):
    result = statuses(config, clean_frame())
    assert result["CORPORATE_ACTION_FIXTURE"] == "NOT_APPLICABLE"
    assert {check: status for check, status in result.items() if status not in {"PASS", "NOT_APPLICABLE"}} == {}


def test_a_correctly_applied_split_passes(config):
    """Control for the split guard: recorded ratio, factor unchanged, no cliff in adjusted prices."""
    frame = clean_frame()
    frame.loc[30, "split_ratio"] = 2.0
    assert statuses(config, frame)["SPLIT_RECONCILES"] == "PASS"


def test_a_correctly_applied_dividend_passes(config):
    """Control for the dividend guard: pre-ex bars scaled by exactly (1 - D / prior close)."""
    frame = clean_frame()
    frame.loc[20, "dividend"] = 1.0
    frame.loc[:19, "adj_close"] = 99.0
    assert statuses(config, frame)["DIVIDEND_RECONCILES"] == "PASS"


# --------------------------------------------------------------------------------------------
# Session structure
# --------------------------------------------------------------------------------------------


def test_a_phantom_session_is_caught(config):
    """2015-01-03 is a Saturday. No amount of provider confidence makes it a trading day."""
    frame = clean_frame()
    phantom = frame.iloc[[0]].copy()
    phantom["session"] = "2015-01-03"
    corrupted = pd.concat([frame, phantom]).sort_values("session").reset_index(drop=True)
    result = statuses(config, corrupted)
    assert result["SESSION_IN_CALENDAR"] == "FAIL"
    assert result["MISSING_SESSION_FRACTION"] == "PASS", "no real session was removed"


def test_a_duplicated_session_is_caught(config):
    frame = clean_frame()
    corrupted = pd.concat([frame, frame.iloc[[10]]]).sort_values("session").reset_index(drop=True)
    result = statuses(config, corrupted)
    assert result["NO_DUPLICATE_SESSIONS"] == "FAIL"
    assert result["SESSIONS_STRICTLY_INCREASING"] == "FAIL"


def test_sessions_after_the_acquisition_date_are_caught(config):
    """A bar dated after the data was fetched is fabricated, whatever the provider says."""
    result = statuses(config, clean_frame(), acquisition_date=dt.date(2015, 3, 20))
    assert result["NO_FUTURE_SESSIONS"] == "FAIL"


def test_a_short_gap_trips_the_fraction_limit_but_not_the_run_limit(config):
    frame = clean_frame().drop(index=[20, 21])
    result = statuses(config, frame)
    assert result["MISSING_SESSION_FRACTION"] == "FAIL"
    assert result["MISSING_SESSION_RUN"] == "PASS"


def test_a_long_gap_trips_the_run_limit(config):
    frame = clean_frame().drop(index=list(range(20, 26)))
    result = statuses(config, frame)
    assert result["MISSING_SESSION_RUN"] == "FAIL"
    assert result["MISSING_SESSION_FRACTION"] == "FAIL"


# --------------------------------------------------------------------------------------------
# Bar sanity
# --------------------------------------------------------------------------------------------


def test_an_impossible_bar_is_caught_and_quarantined_not_deleted(config, isolated_quarantine: Path):
    frame = clean_frame()
    frame.loc[10, "high"] = 50.0  # high below the close
    result = statuses(config, frame)
    assert result["OHLC_CONSISTENT"] == "FAIL"

    record_path = isolated_quarantine / "SYNTH.OHLC_CONSISTENT.json"
    assert record_path.is_file(), "the offending bar was not recorded"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["rows_retained_in_normalized_output"] is True
    assert record["row_count"] == 1
    assert record["rows"][0]["session"] == frame.loc[10, "session"]
    assert len(frame) == len(clean_frame()), "the row must stay in the series"


def test_negative_volume_is_caught(config):
    frame = clean_frame()
    frame.loc[5, "volume"] = -1
    assert statuses(config, frame)["VOLUME_VALID"] == "FAIL"


@pytest.mark.filterwarnings("ignore:divide by zero:RuntimeWarning")
def test_non_positive_adjusted_close_is_caught(config):
    """A zero adjusted close also makes the factor ratio divide by zero; the guard still reports."""
    frame = clean_frame()
    frame.loc[5, "adj_close"] = 0.0
    assert statuses(config, frame)["ADJ_CLOSE_POSITIVE"] == "FAIL"


# --------------------------------------------------------------------------------------------
# Adjustment arithmetic
# --------------------------------------------------------------------------------------------


def test_a_backward_step_in_the_adjustment_factor_is_caught(config):
    """The factor may only rise going forward; a dip means the adjustment series is inconsistent."""
    frame = clean_frame()
    frame.loc[30, "adj_close"] = 99.0
    result = statuses(config, frame)
    assert result["FACTOR_NON_DECREASING"] == "FAIL"
    assert result["TERMINAL_FACTOR_IS_ONE"] == "PASS"


def test_a_terminal_factor_away_from_one_is_caught(config):
    frame = clean_frame()
    frame.loc[len(frame) - 1, "adj_close"] = 101.0
    assert statuses(config, frame)["TERMINAL_FACTOR_IS_ONE"] == "FAIL"


def test_a_split_recorded_but_never_applied_is_caught(config):
    """The falsifiable part of the measured semantics: no 1/ratio cliff in the adjusted series."""
    frame = clean_frame()
    frame.loc[30, "split_ratio"] = 2.0
    frame.loc[30:, "adj_close"] = 50.0
    assert statuses(config, frame)["SPLIT_RECONCILES"] == "FAIL"


def test_a_split_whose_factor_step_is_wrong_is_caught(config):
    frame = clean_frame()
    frame.loc[30, "split_ratio"] = 2.0
    frame.loc[:29, "adj_close"] = 80.0  # a factor step no split should produce
    assert statuses(config, frame)["SPLIT_RECONCILES"] == "FAIL"


def test_a_dividend_that_does_not_reconcile_is_recorded_as_a_warning_not_swallowed(
    config, isolated_quarantine: Path
):
    """DIVIDEND_RECONCILES was sealed at WARN severity, so it reports without failing the stage."""
    frame = clean_frame()
    frame.loc[20, "dividend"] = 20.0  # 20% of the prior close, with no matching factor step
    assert statuses(config, frame)["DIVIDEND_RECONCILES"] == "WARN"
    assert (isolated_quarantine / "SYNTH.DIVIDEND_RECONCILES.json").is_file()


def test_an_unexplained_extreme_move_is_flagged(config):
    frame = clean_frame()
    frame.loc[40:, ["close", "adj_close"]] = 300.0  # tripled overnight, no split, no dividend
    assert statuses(config, frame)["EXTREME_MOVE_EXPLAINED"] == "WARN"


def test_a_declared_corporate_action_that_is_absent_is_caught(config):
    frame = clean_frame()
    result = statuses(
        config,
        frame,
        expected_actions=[{"type": "split", "session": "2015-02-17", "ratio": 7.0}],
    )
    assert result["CORPORATE_ACTION_FIXTURE"] == "FAIL", "the declared ratio was never recorded"


# --------------------------------------------------------------------------------------------
# Value thresholds
# --------------------------------------------------------------------------------------------


def test_a_penny_priced_series_is_caught_in_the_development_window(config):
    frame = clean_frame()
    frame[["open", "high", "low", "close", "adj_close"]] = 2.0
    assert statuses(config, frame)["PRICE_NOT_PENNY"] == "FAIL"


# --------------------------------------------------------------------------------------------
# The window restriction is structural, not a promise
# --------------------------------------------------------------------------------------------


def test_measuring_eligibility_on_data_past_the_development_window_raises():
    """Handing the eligibility measurement validation-window data must be an error, not a number."""
    frame = clean_frame()
    frame["session"] = [
        day.isoformat() for day in sessions_between(dt.date(2016, 7, 1), dt.date(2016, 9, 30))
    ][: len(frame)]
    with pytest.raises(WindowViolation) as excinfo:
        measure(frame, PARTITION)
    assert "outside the development window" in str(excinfo.value)


def test_the_sanctioned_slice_never_produces_a_violation():
    sessions = [day.isoformat() for day in sessions_between(dt.date(2015, 1, 2), dt.date(2017, 6, 30))]
    frame = pd.DataFrame(
        {"session": sessions, "close": 100.0, "volume": 1_000_000, "adj_close": 100.0}
    )
    sliced = development_frame(frame, PARTITION)
    assert sliced["session"].iloc[-1] <= PARTITION.development_end
    measured = measure(sliced, PARTITION)
    assert measured["development_last_session"] <= PARTITION.development_end
    assert measured["window"] == [PARTITION.development_start, PARTITION.development_end]


def test_an_empty_development_slice_measures_nothing_rather_than_guessing():
    frame = pd.DataFrame({"session": [], "close": [], "volume": []})
    measured = measure(frame, PARTITION)
    assert measured["development_sessions"] == 0
    assert measured["median_dollar_volume"] is None
    assert measured["minimum_close"] is None


# --------------------------------------------------------------------------------------------
# The holdout lock cannot be moved
# --------------------------------------------------------------------------------------------


def test_the_builder_refuses_to_overwrite_a_lock_with_different_boundaries(
    monkeypatch: pytest.MonkeyPatch, governance_dir: Path, tmp_path: Path, capsys
):
    """A holdout that can be recomputed after seeing results is not a holdout."""
    out = tmp_path / "governance"
    out.mkdir()
    lock = json.loads((governance_dir / "STAGE_1_HOLDOUT_LOCK.json").read_text(encoding="utf-8"))
    lock["partition"]["holdout_start"] = "2025-01-01"  # someone "corrects" the boundary
    (out / "STAGE_1_HOLDOUT_LOCK.json").write_text(json.dumps(lock, indent=2), encoding="utf-8")

    monkeypatch.setattr(universe_build, "GOVERNANCE", out)
    monkeypatch.setattr(universe_build, "UNIVERSE_PATH", out / "STAGE_1_UNIVERSE.json")
    monkeypatch.setattr(universe_build, "HOLDOUT_LOCK_PATH", out / "STAGE_1_HOLDOUT_LOCK.json")
    monkeypatch.setattr(universe_build, "FREEZE_RECORD_PATH", out / "STAGE_1_FREEZE.sha256")

    assert universe_build.build() == 5
    assert "REFUSING to overwrite" in capsys.readouterr().err
    assert not (out / "STAGE_1_UNIVERSE.json").exists(), "the builder wrote output despite refusing"
    assert json.loads((out / "STAGE_1_HOLDOUT_LOCK.json").read_text(encoding="utf-8")) == lock


# --------------------------------------------------------------------------------------------
# The pre-registration seal
# --------------------------------------------------------------------------------------------


def sealed_tree(project_root: Path, tmp_path: Path) -> Path:
    """A throwaway copy of the sealed files, so tampering never touches the real ones."""
    root = tmp_path / "tree"
    (root / "config").mkdir(parents=True)
    (root / "governance").mkdir(parents=True)
    for rel in (
        "config/stage1_data_source.json",
        "config/stage1_universe_spec.json",
        "governance/STAGE_1_PREREGISTRATION.json",
        "governance/STAGE_1_PREREGISTRATION.md",
    ):
        (root / rel).write_bytes((project_root / rel).read_bytes())
    return root


def point_loader_at(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    monkeypatch.setattr(config_module, "PROJECT_ROOT", root)
    monkeypatch.setattr(config_module, "PREREGISTRATION_JSON", root / "governance" / "STAGE_1_PREREGISTRATION.json")


@pytest.mark.parametrize(
    "tampered",
    ["config/stage1_data_source.json", "config/stage1_universe_spec.json", "governance/STAGE_1_PREREGISTRATION.md"],
)
def test_editing_a_sealed_rule_after_the_fact_stops_the_loader(
    monkeypatch: pytest.MonkeyPatch, project_root: Path, tmp_path: Path, tampered: str
):
    """One byte is enough: rules changed after they were declared invalidate everything downstream."""
    root = sealed_tree(project_root, tmp_path)
    target = root / tampered
    target.write_bytes(target.read_bytes() + b" ")
    point_loader_at(monkeypatch, root)

    with pytest.raises(PreRegistrationViolation) as excinfo:
        config_module.load_stage1_config()
    message = str(excinfo.value)
    assert tampered in message
    assert "governance failure" in message


def test_a_deleted_sealed_file_stops_the_loader(
    monkeypatch: pytest.MonkeyPatch, project_root: Path, tmp_path: Path
):
    root = sealed_tree(project_root, tmp_path)
    (root / "governance" / "STAGE_1_PREREGISTRATION.md").unlink()
    point_loader_at(monkeypatch, root)

    with pytest.raises(PreRegistrationViolation) as excinfo:
        config_module.load_stage1_config()
    assert "MISSING" in str(excinfo.value)


def test_a_missing_seal_stops_the_loader(
    monkeypatch: pytest.MonkeyPatch, project_root: Path, tmp_path: Path
):
    root = sealed_tree(project_root, tmp_path)
    (root / "governance" / "STAGE_1_PREREGISTRATION.json").unlink()
    point_loader_at(monkeypatch, root)

    with pytest.raises(PreRegistrationViolation) as excinfo:
        config_module.load_stage1_config()
    assert "never sealed" in str(excinfo.value)


def test_the_unsealed_path_returns_no_digests_so_it_cannot_be_mistaken_for_a_verified_load(
    monkeypatch: pytest.MonkeyPatch, project_root: Path, tmp_path: Path
):
    """``require_seal=False`` exists only for the sealer itself, which runs before the seal exists."""
    root = sealed_tree(project_root, tmp_path)
    (root / "config" / "stage1_data_source.json").write_bytes(
        (root / "config" / "stage1_data_source.json").read_bytes() + b" "
    )
    point_loader_at(monkeypatch, root)

    unsealed = config_module.load_stage1_config(require_seal=False)
    assert unsealed.digests == {}
    assert unsealed.preregistration == {}
