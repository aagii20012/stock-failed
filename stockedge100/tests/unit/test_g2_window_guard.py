"""Generation 2's window guard — the three checks sealed in ``STAGE_1_G2_PARTITION_LOCK`` §4.

``config/generation_2/g2_rotation_protocol.json`` lists three of these under
``adversarial_test_requirements.additional``:

    "the window guard rejects a window ending after 2021-07-31"
    "the window guard rejects a loaded series containing a session after 2021-07-31, detected from
     the bars rather than from the loader"
    "the window guard rejects any window intersecting 2024-08-01 .. 2026-07-31 or
     2026-08-01 .. 2028-07-31"

Each has at least one test below that fails if the guard regresses, and each is preceded by a clean
control so that a red result downstream is attributable to the injected condition rather than to the
fixture. The bounds are asserted once as hand-written literals — the point of a partition lock is
that its dates are knowable without running the code — and the boundary arithmetic is then
parametrized off the guard's own accessor so that a lock edit cannot leave a stale test passing.

Nothing here reads ``data/``. The one loader test writes its own CSV into ``tmp_path``, which is what
makes it safe to give that CSV sessions past the bound: the guard has to refuse them, so they have to
exist somewhere, and the only somewhere that cannot contaminate anything is a temporary directory.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import re
from dataclasses import replace

import pytest

from stockedge100.backtest.dataset import COLUMNS, PriceSeries, series_from_rows
from stockedge100.backtest.errors import ConfigViolation, WindowViolation
from stockedge100.backtest.window import DEVELOPMENT, ResearchWindow
from stockedge100.strategies import g2_window_guard as guard

#: Hand-written from ``STAGE_1_G2_PARTITION_LOCK.md`` §2, not read back from the lock.
DEVELOPMENT_BOUND = dt.date(2021, 7, 31)
GENERATION_1_HOLDOUT = (dt.date(2024, 8, 1), dt.date(2026, 7, 31))
GENERATION_2_HOLDOUT = (dt.date(2026, 8, 1), dt.date(2028, 7, 31))
VALIDATION = (dt.date(2021, 8, 1), dt.date(2024, 7, 31))

DAY = dt.timedelta(days=1)


def d(text: str) -> dt.date:
    return dt.date.fromisoformat(text)


def window(start: dt.date | str, end: dt.date | str, name: str = "probe") -> ResearchWindow:
    """A window built without the guard, so the guard has something to refuse."""
    return ResearchWindow(name=name, start=_date(start), end=_date(end))


def _date(value: dt.date | str) -> dt.date:
    return value if isinstance(value, dt.date) else d(value)


# -- clean controls ----------------------------------------------------------------------------


def test_control_the_lock_states_the_partition_this_test_file_was_written_against() -> None:
    """If this fails, every expectation below is measuring the wrong partition."""
    assert guard.development_bound() == DEVELOPMENT_BOUND
    assert guard.prohibited_windows() == (
        ("generation_1_holdout",) + GENERATION_1_HOLDOUT,
        ("holdout",) + GENERATION_2_HOLDOUT,
    )


def test_control_the_stage_3_window_is_accepted_and_ends_on_the_bound() -> None:
    stage_3 = guard.stage_3_window()
    assert stage_3.name == DEVELOPMENT
    assert stage_3.end <= DEVELOPMENT_BOUND
    assert guard.assert_run_window(stage_3) is stage_3


def test_control_a_window_wholly_inside_development_is_accepted() -> None:
    accepted = guard.generation_2_window("inner", "2010-01-04", "2010-12-31")
    assert guard.assert_run_window(accepted) is accepted


def test_control_the_guard_reports_the_state_it_is_enforcing() -> None:
    state = guard.guard_state()
    assert state["development_bound"] == DEVELOPMENT_BOUND.isoformat()
    assert state["holdout_read_authorized"] is False
    assert state["live_trading_authorized"] is False
    assert state["stage_4_authorized"] is False
    assert [entry["label"] for entry in state["prohibited_windows"]] == [
        "generation_1_holdout",
        "holdout",
    ]


# -- sealed check 1: "rejects a window ending after 2021-07-31" ---------------------------------


def test_a_window_ending_one_day_past_the_bound_is_rejected() -> None:
    one_day_over = window("2010-01-04", DEVELOPMENT_BOUND + DAY, name="one_day_over")
    with pytest.raises(WindowViolation, match="after the Generation 2 development bound"):
        guard.assert_run_window(one_day_over)


def test_a_window_ending_exactly_on_the_bound_is_accepted() -> None:
    """The complement of the test above. Off-by-one in the other direction is also a defect."""
    exact = window("2010-01-04", DEVELOPMENT_BOUND, name="exact")
    assert guard.assert_run_window(exact) is exact


def test_the_validation_window_is_constructible_but_not_runnable_in_stage_3() -> None:
    """Checks 1 and 3 are different checks and this window separates them.

    Generation 2's validation window does not intersect either holdout, so check 3 permits it — it
    has to, because a later authorized session must be able to build it. Check 1 refuses it anyway,
    because Stage 3 is authorized to read development data only.
    """
    validation = guard.generation_2_window("validation", *VALIDATION)
    assert validation.start == VALIDATION[0]
    with pytest.raises(WindowViolation, match="the validation window is LOCKED"):
        guard.assert_run_window(validation)


@pytest.mark.parametrize(
    "end",
    ["2021-08-01", "2021-08-02", "2022-01-03", "2024-07-31"],
    ids=["day_after", "two_days_after", "months_after", "validation_end"],
)
def test_every_post_bound_end_is_rejected_whatever_the_start(end: str) -> None:
    with pytest.raises(WindowViolation, match="after the Generation 2 development bound"):
        guard.assert_run_window(window("1993-01-29", end, name="post_bound"))


def test_a_backwards_window_is_rejected_rather_than_silently_empty() -> None:
    with pytest.raises(WindowViolation, match="runs backwards"):
        guard.assert_not_prohibited("2015-01-05", "2014-01-05")


# -- sealed check 3: "rejects any window intersecting either holdout" ---------------------------


#: ``(case id, start, end, the label the refusal must name)``. Where a window touches both
#: prohibited periods the guard names the earlier one, because it checks them in the order the lock
#: records them and stops at the first hit. That is reported rather than smoothed over: a window
#: reaching into 2026-08-01 from below has already breached Generation 1's holdout, and saying so is
#: more useful than naming the further of the two periods it also touches.
INTERSECTING_CASES: tuple[tuple[str, dt.date, dt.date, str], ...] = (
    ("g1:first_day_only", GENERATION_1_HOLDOUT[0], GENERATION_1_HOLDOUT[0], "generation_1_holdout"),
    ("g1:last_day_only", GENERATION_1_HOLDOUT[1], GENERATION_1_HOLDOUT[1], "generation_1_holdout"),
    ("g1:straddles_start", GENERATION_1_HOLDOUT[0] - DAY, GENERATION_1_HOLDOUT[0], "generation_1_holdout"),
    ("g1:straddles_end", GENERATION_1_HOLDOUT[1], GENERATION_1_HOLDOUT[1] + DAY, "generation_1_holdout"),
    ("g1:strictly_inside", GENERATION_1_HOLDOUT[0] + DAY, GENERATION_1_HOLDOUT[1] - DAY, "generation_1_holdout"),
    ("g1:one_day_of_it_at_the_far_end", d("1993-01-29"), GENERATION_1_HOLDOUT[0], "generation_1_holdout"),
    ("g2:first_day_only", GENERATION_2_HOLDOUT[0], GENERATION_2_HOLDOUT[0], "holdout"),
    ("g2:last_day_only", GENERATION_2_HOLDOUT[1], GENERATION_2_HOLDOUT[1], "holdout"),
    ("g2:straddles_end", GENERATION_2_HOLDOUT[1], GENERATION_2_HOLDOUT[1] + DAY, "holdout"),
    ("g2:strictly_inside", GENERATION_2_HOLDOUT[0] + DAY, GENERATION_2_HOLDOUT[1] - DAY, "holdout"),
    ("g2:one_day_of_it_at_the_near_end", GENERATION_2_HOLDOUT[0], d("2030-01-02"), "holdout"),
    ("both:the_seam", GENERATION_1_HOLDOUT[1], GENERATION_2_HOLDOUT[0], "generation_1_holdout"),
    ("both:one_window_over_everything", d("2021-08-01"), d("2028-07-31"), "generation_1_holdout"),
)


@pytest.mark.parametrize(
    ("start", "end", "label"),
    [(start, end, label) for _, start, end, label in INTERSECTING_CASES],
    ids=[case_id for case_id, _, _, _ in INTERSECTING_CASES],
)
def test_a_window_intersecting_a_prohibited_period_cannot_be_constructed(
    start: dt.date, end: dt.date, label: str
) -> None:
    with pytest.raises(WindowViolation, match=f"intersects the prohibited {label} period"):
        guard.generation_2_window("attempt", start, end)


def test_the_refusal_says_that_no_result_reopens_either_holdout() -> None:
    """The wording is the artifact. A guard that refuses without saying why invites a second attempt."""
    with pytest.raises(WindowViolation) as raised:
        guard.generation_2_window("attempt", *GENERATION_1_HOLDOUT)
    message = str(raised.value)
    assert "Generation 1's final holdout is spent and may never be read again in any generation" in message
    assert "sealed until that period has elapsed in real calendar time" in message
    assert "No result, and no argument about what a result would show, reopens either." in message


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (d("1993-01-29"), DEVELOPMENT_BOUND),
        VALIDATION,
        (GENERATION_1_HOLDOUT[0] - dt.timedelta(days=2), GENERATION_1_HOLDOUT[0] - DAY),
        (GENERATION_2_HOLDOUT[1] + DAY, GENERATION_2_HOLDOUT[1] + dt.timedelta(days=400)),
    ],
    ids=["development", "validation", "up_to_g1_holdout", "after_g2_holdout"],
)
def test_a_window_that_misses_both_prohibited_periods_is_constructible(
    start: dt.date, end: dt.date
) -> None:
    """The complement. A guard that rejected everything would pass every test above."""
    built = guard.generation_2_window("clear", start, end)
    assert (built.start, built.end) == (start, end)


def test_the_two_prohibited_periods_are_adjacent_with_no_gap_a_window_could_slip_through() -> None:
    """``2026-07-31`` then ``2026-08-01``: there is no unprohibited day between the holdouts."""
    assert GENERATION_2_HOLDOUT[0] == GENERATION_1_HOLDOUT[1] + DAY
    with pytest.raises(WindowViolation, match="intersects the prohibited"):
        guard.generation_2_window("seam", GENERATION_1_HOLDOUT[1], GENERATION_2_HOLDOUT[0])


# -- sealed check 2: "rejects a loaded series containing a session after 2021-07-31" ------------


def _rows(sessions: list[str]) -> list[dict[str, str]]:
    return [
        {
            "session": session,
            "open": "99.75",
            "high": "100.00",
            "low": "99.50",
            "close": "100.00",
            "adj_close": "100.00",
            "volume": "1000000",
            "dividend": "0",
            "split_ratio": "0",
        }
        for session in sessions
    ]


def _write_csv(directory, symbol: str, sessions: list[str]) -> None:
    path = directory / f"{symbol}.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(COLUMNS))
        writer.writeheader()
        writer.writerows(_rows(sessions))


IN_BOUND = ["2021-07-27", "2021-07-28", "2021-07-29", "2021-07-30"]
PAST_BOUND = ["2021-08-02", "2021-08-03", "2021-08-04"]


def test_control_a_series_wholly_inside_the_bound_passes_and_reports_its_last_session() -> None:
    series = {"AAA": series_from_rows("AAA", _rows(IN_BOUND))}
    assert guard.assert_series_within_bound(series) == {"AAA": "2021-07-30"}


def test_a_loaded_series_carrying_a_post_bound_bar_is_rejected() -> None:
    series = {"AAA": series_from_rows("AAA", _rows(IN_BOUND + PAST_BOUND))}
    with pytest.raises(WindowViolation, match=re.escape("3 loaded bar(s) fall after")) as raised:
        guard.assert_series_within_bound(series)
    assert "the first at 2021-08-02" in str(raised.value)


def test_one_post_bound_bar_among_many_is_enough_and_the_other_symbols_do_not_excuse_it() -> None:
    series = {
        "AAA": series_from_rows("AAA", _rows(IN_BOUND)),
        "BBB": series_from_rows("BBB", _rows(IN_BOUND)),
        "ZZZ": series_from_rows("ZZZ", _rows(IN_BOUND + PAST_BOUND[:1])),
    }
    with pytest.raises(WindowViolation, match="ZZZ: 1 loaded bar"):
        guard.assert_series_within_bound(series)


def test_the_check_reads_the_bar_map_not_the_session_index() -> None:
    """The sealed wording is "detected from the bars rather than from the loader".

    A loader that truncated its ``sessions`` index while leaving the post-bound bar in the map would
    satisfy an inspection of ``sessions`` alone and still be holding the data. That is the defect
    injected here, and it must be caught — as a disagreement, which is the honest description: the
    series is lying about its own contents, and which half is lying is not for the guard to decide.
    """
    honest = series_from_rows("AAA", _rows(IN_BOUND + PAST_BOUND))
    hiding = replace(honest, sessions=tuple(day for day in honest.sessions if day <= DEVELOPMENT_BOUND))

    assert max(hiding.sessions) <= DEVELOPMENT_BOUND       # the index looks clean
    assert max(hiding.bars) > DEVELOPMENT_BOUND            # the bars are not

    with pytest.raises(WindowViolation, match="hides part of its own contents"):
        guard.assert_series_within_bound({"AAA": hiding})


def test_the_inverse_disagreement_is_caught_too() -> None:
    """A session index claiming bars that were never loaded is equally a refusal."""
    honest = series_from_rows("AAA", _rows(IN_BOUND))
    inflated = replace(honest, sessions=honest.sessions + (d("2021-07-31"),))
    with pytest.raises(WindowViolation, match="hides part of its own contents"):
        guard.assert_series_within_bound({"AAA": inflated})


def test_an_empty_series_is_a_refusal_not_a_vacuous_pass() -> None:
    empty = PriceSeries(symbol="AAA", bars={}, sessions=())
    with pytest.raises(WindowViolation, match="no bars were loaded inside the development window"):
        guard.assert_series_within_bound({"AAA": empty})


def test_the_loader_stops_at_the_bound_instead_of_loading_and_discarding(tmp_path) -> None:
    """The mechanism, checked separately from the assertion that covers it.

    ``load_stage_3_series`` breaks out of the CSV read at the first post-bound session, so the bars
    never exist in memory. ``assert_series_within_bound`` then passes — but it is passing on a fact,
    not restating the loader's intention, which is why both are tested.
    """
    _write_csv(tmp_path, "AAA", IN_BOUND + PAST_BOUND)
    loaded = guard.load_stage_3_series("AAA", directory=tmp_path)

    assert loaded.sessions == tuple(d(session) for session in IN_BOUND)
    assert max(loaded.bars) == DEVELOPMENT_BOUND - DAY
    assert all(day <= DEVELOPMENT_BOUND for day in loaded.bars)
    assert guard.assert_series_within_bound({"AAA": loaded}) == {"AAA": "2021-07-30"}


def test_the_dataset_loader_verifies_what_it_loaded_before_returning_it(tmp_path) -> None:
    _write_csv(tmp_path, "AAA", IN_BOUND + PAST_BOUND)
    _write_csv(tmp_path, "BBB", IN_BOUND)
    dataset = guard.load_stage_3_dataset(["BBB", "AAA"], directory=tmp_path)
    assert sorted(dataset) == ["AAA", "BBB"]
    assert all(max(one.bars) <= DEVELOPMENT_BOUND for one in dataset.values())


def test_a_file_holding_only_post_bound_sessions_is_a_refusal_not_an_empty_series(tmp_path) -> None:
    _write_csv(tmp_path, "AAA", PAST_BOUND)
    with pytest.raises(Exception, match="no sessions on or before the development bound"):
        guard.load_stage_3_series("AAA", directory=tmp_path)


# -- the lock the guard reads its bounds from ---------------------------------------------------


@pytest.fixture()
def substituted_lock(tmp_path, monkeypatch):
    """Point the guard at a copy of the real lock that a test may edit.

    ``_lock`` is ``lru_cache``d and every accessor above depends on it, so the cache is cleared on
    both sides: an entry built from a tampered document must not survive into another test, and the
    genuine entry must not be reused in place of the tampered one.
    """

    def substitute(**edits: object) -> None:
        document = json.loads(guard.PARTITION_LOCK_PATH.read_text(encoding="utf-8"))
        for pointer, value in edits.items():
            node = document
            *parents, leaf = pointer.split("__")
            for key in parents:
                node = node[key]
            node[leaf] = value
        path = tmp_path / "STAGE_1_G2_PARTITION_LOCK.json"
        path.write_text(json.dumps(document), encoding="utf-8")
        monkeypatch.setattr(guard, "PARTITION_LOCK_PATH", path)
        guard._lock.cache_clear()

    guard._lock.cache_clear()
    yield substitute
    guard._lock.cache_clear()


def test_control_the_substitution_harness_reproduces_the_real_bounds(substituted_lock) -> None:
    """An unedited copy must behave exactly like the original, or the tests below prove nothing."""
    substituted_lock()
    assert guard.development_bound() == DEVELOPMENT_BOUND
    assert guard.prohibited_windows()[0][1:] == GENERATION_1_HOLDOUT


@pytest.mark.parametrize(
    ("edits", "message"),
    [
        ({"artifact_id": "SE100-GOV-9999"}, "declares artifact_id"),
        ({"generation": 1}, "is not a Generation 2 artifact"),
        ({"holdout_read_authorized": True}, "no longer records holdout_read_authorized as false"),
        ({"enforcement__development_bound": "2024-07-31"}, "the partition lock disagrees with itself"),
        (
            {"enforcement__prohibited_windows": [["2024-08-01", "2026-07-31"]]},
            "does not match the partition's holdout ranges",
        ),
        ({"partition__boundaries_inclusive": False}, "assumes inclusive partition boundaries"),
    ],
    ids=[
        "wrong_artifact_id",
        "wrong_generation",
        "holdout_read_authorized",
        "self_disagreement_on_the_bound",
        "prohibited_windows_narrowed",
        "boundaries_no_longer_inclusive",
    ],
)
def test_a_tampered_lock_stops_the_guard_rather_than_moving_its_bounds(
    substituted_lock, edits: dict, message: str
) -> None:
    substituted_lock(**edits)
    with pytest.raises(ConfigViolation, match=message):
        guard.development_bound()


def test_a_lock_authorizing_more_than_development_cannot_produce_a_stage_3_window(
    substituted_lock,
) -> None:
    """The one that would matter most: a lock quietly widened to admit the validation window."""
    substituted_lock(authorized_windows=["development", "validation"])
    with pytest.raises(ConfigViolation, match="authorizes .* not development alone"):
        guard.stage_3_window()
