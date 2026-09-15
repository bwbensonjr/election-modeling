"""Fold construction: the boundary every published number rests on.

A fold is one election date, training on everything strictly earlier. Getting
that boundary wrong does not fail loudly -- it silently leaks a result into
the training set that predicts it, or silently discards one a forecaster would
have had. So it is tested on a synthetic frame small enough to reason about by
hand, rather than only through the committed table.
"""

from __future__ import annotations

import pandas as pd
import pytest

from legmodel import folds


def races(rows) -> pd.DataFrame:
    """A race table with only the columns fold construction reads."""
    return pd.DataFrame(
        [
            {
                "election_id": f"r{i}",
                "election_date": date,
                "is_special": special,
                **extra,
            }
            for i, (date, special, extra) in enumerate(rows)
        ]
    )


# A seed race, then a presidential year holding a March special and a November
# general -- the case the year-based schedule got wrong.
SAMPLE = races(
    [
        ("2013-06-25", True, {}),
        ("2014-11-04", False, {}),
        ("2016-03-01", True, {}),
        ("2016-03-01", True, {}),
        ("2016-11-08", False, {}),
        ("2016-11-08", False, {}),
    ]
)


def test_one_fold_per_distinct_date_after_the_cutoff():
    built, skipped = folds.build(SAMPLE)
    assert [fold.key for fold in built] == [
        "2014-11-04",
        "2016-03-01",
        "2016-11-08",
    ]
    assert skipped == []


def test_seed_races_never_enter_a_holdout():
    built, _ = folds.build(SAMPLE)
    held_out = pd.concat([fold.holdout for fold in built])
    assert (held_out["election_date"] >= folds.SEED_CUTOFF).all()
    assert "2013-06-25" not in set(held_out["election_date"])


def test_seed_races_do_train_every_fold():
    built, _ = folds.build(SAMPLE)
    for fold in built:
        assert "2013-06-25" in set(fold.train["election_date"])


def test_training_boundary_is_strictly_before_the_fold_date():
    built, _ = folds.build(SAMPLE)
    for fold in built:
        assert (fold.train["election_date"] < fold.key).all()
        assert (fold.holdout["election_date"] == fold.key).all()


def test_an_earlier_election_in_the_same_year_trains_the_fold():
    """The whole point of the refold: the March special informs November."""
    fold = next(f for f in folds.build(SAMPLE)[0] if f.key == "2016-11-08")
    assert list(fold.train["election_date"]).count("2016-03-01") == 2
    assert fold.n_train == 4
    assert fold.n_holdout == 2


def test_dates_are_not_blended_into_one_holdout():
    built, _ = folds.build(SAMPLE)
    keys = [fold.key for fold in built]
    assert "2016-03-01" in keys and "2016-11-08" in keys
    for fold in built:
        assert fold.holdout["election_date"].nunique() == 1


def test_a_date_a_definition_empties_is_reported_as_skipped():
    """Absent from the frame is not the same as no election having happened."""
    thinned = SAMPLE[SAMPLE["election_date"] != "2016-03-01"]
    eligible = folds.fold_dates(SAMPLE)
    built, skipped = folds.build(thinned, eligible)
    assert skipped == ["2016-03-01"]
    assert "2016-03-01" not in [fold.key for fold in built]


def test_without_an_eligible_list_an_emptied_date_vanishes():
    """Why `eligible` has to be passed: derived-from-self cannot see a gap."""
    thinned = SAMPLE[SAMPLE["election_date"] != "2016-03-01"]
    _, skipped = folds.build(thinned)
    assert skipped == []


def test_unscoreable_races_train_but_are_not_held_out():
    frame = SAMPLE.assign(scoreable=True)
    frame.loc[frame["election_date"] == "2016-11-08", "scoreable"] = False
    built, skipped = folds.build(frame, folds.fold_dates(frame))
    assert "2016-11-08" in skipped
    later = [f for f in built if f.key > "2016-11-08"]
    assert not later
    # Still available to train anything after it, had there been a later date.
    assert (frame["election_date"] == "2016-11-08").sum() == 2


def test_is_special_date_distinguishes_the_two_kinds():
    built, _ = folds.build(SAMPLE)
    by_key = {fold.key: fold for fold in built}
    assert by_key["2016-03-01"].is_special_date
    assert not by_key["2016-11-08"].is_special_date


def test_summary_counts_general_and_special_dates_apart():
    summary = folds.summary(SAMPLE)
    assert summary["n_folds"] == 3
    assert summary["n_general_dates"] == 2
    assert summary["n_special_dates"] == 1
    assert summary["general_races"] == 3
    assert summary["special_races"] == 2
    assert summary["holdout_races"] == 5
    assert summary["seed_races"] == 1


def test_schedule_lists_every_fold_and_every_skipped_date():
    thinned = SAMPLE[SAMPLE["election_date"] != "2016-03-01"]
    frame = folds.schedule(thinned, folds.fold_dates(SAMPLE))
    assert len(frame) == 3
    assert frame["skipped"].sum() == 1
    assert list(frame["fold"]) == sorted(frame["fold"])


def test_a_date_with_no_prior_races_produces_no_fold():
    """The earliest date in the table cannot be a fold: nothing trains it."""
    only = races([("2014-11-04", False, {})])
    built, skipped = folds.build(only)
    assert built == []
    assert skipped == ["2014-11-04"]


@pytest.mark.parametrize("cutoff_date", ["2013-12-31", "2014-01-01"])
def test_the_cutoff_is_inclusive_of_its_own_date(cutoff_date):
    frame = races([("2012-01-01", False, {}), (cutoff_date, False, {})])
    built, _ = folds.build(frame)
    keys = [fold.key for fold in built]
    assert (cutoff_date in keys) == (cutoff_date >= folds.SEED_CUTOFF)
