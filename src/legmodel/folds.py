"""Rolling-origin fold construction, one fold per election date.

Each fold trains on every race held strictly before its election date and
predicts the races held on that date, so the training window expands and never
contains the future (model-scoring spec). A fold is an election, not a
calendar year: a special election held in March is in the training set of the
November general that follows it, because its result was known before that
general was decided.

Splitting by date rather than at random is what keeps a district that recurs
across cycles out of both sides of the same split. Splitting by date rather
than by year is what stops several unrelated elections being scored as one
event, and what stops a result a real forecaster would have had being
discarded because it shares a calendar year with the race being predicted.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

# Races held before this date form the seed training window and are never
# scored. It is the start of 2014 rather than the first general election of
# 2014 so that the seed window is exactly the 2010-2013 races the year-based
# schedule used, leaving the holdout population unchanged by the refold.
SEED_CUTOFF = "2014-01-01"

# Identifies the fold schedule that produced a set of outputs. Stamped into
# every published file so figures computed under two different schedules
# cannot be silently mixed by an appending run -- the failure mode the
# supersession notice exists to prevent, made checkable rather than asserted.
SCHEDULE_ID = f"election_date>={SEED_CUTOFF}"


@dataclass(frozen=True)
class Fold:
    # The election date this fold predicts, as an ISO-8601 string. A string
    # rather than a timestamp because that is what the race table holds, it
    # sorts correctly, it round-trips through CSV without a parsing step, and
    # it hashes stably into `fit.seed_for` -- a Timestamp's repr has changed
    # across pandas versions and would silently reseed every fit.
    key: str
    train: pd.DataFrame
    holdout: pd.DataFrame

    @property
    def n_train(self) -> int:
        return len(self.train)

    @property
    def n_holdout(self) -> int:
        return len(self.holdout)

    @property
    def is_special_date(self) -> bool:
        """Whether this date carried only special elections."""
        return bool(self.holdout["is_special"].astype(bool).all())


def fold_dates(races: pd.DataFrame) -> list[str]:
    """Every election date eligible to be a fold, in order.

    Derived from the table rather than enumerated, so adding an election year
    adds folds without a code change, and a year the table holds no races for
    contributes no dates rather than needing a stated exception.
    """
    dates = races.loc[races["election_date"] >= SEED_CUTOFF, "election_date"]
    return sorted(dates.unique().tolist())


def build(
    races: pd.DataFrame, eligible: list[str] | None = None
) -> tuple[list[Fold], list[str]]:
    """The fold schedule, and the eligible dates that produced no fold.

    A race a definition marks unscoreable still trains -- that is what the
    train-only no-Democrat treatment means -- but never enters a holdout, so
    the `scoreable` flag is applied to the holdout side only.

    `eligible` is the date list the schedule is measured against, normally
    derived from the unfiltered race table. Passing it is what lets a date a
    definition or a variant's `requires` empties be reported as skipped rather
    than vanish: a date absent from `races` is invisible to a schedule derived
    from `races` alone, and "this definition admitted nobody that day" must not
    look like "no election was held that day" (model-scoring spec, "A fold date
    the definition empties is recorded as skipped").
    """
    scoreable = (
        races["scoreable"].astype(bool)
        if "scoreable" in races.columns
        else pd.Series(True, index=races.index)
    )
    dates = fold_dates(races) if eligible is None else sorted(eligible)
    folds, skipped = [], []
    for date in dates:
        holdout = races[(races["election_date"] == date) & scoreable]
        if holdout.empty:
            skipped.append(date)
            continue
        train = races[races["election_date"] < date]
        if train.empty:
            skipped.append(date)
            continue
        folds.append(Fold(key=date, train=train, holdout=holdout))
    return folds, skipped


def schedule(
    races: pd.DataFrame, eligible: list[str] | None = None
) -> pd.DataFrame:
    """A printable summary of the fold schedule."""
    folds, skipped = build(races, eligible)
    rows = [
        {
            "fold": fold.key,
            "train_dates": f"{fold.train['election_date'].min()}-"
            f"{fold.train['election_date'].max()}",
            "n_train": fold.n_train,
            "n_holdout": fold.n_holdout,
            "n_specials": int(fold.holdout["is_special"].astype(bool).sum()),
            "date_type": "special" if fold.is_special_date else "general",
            "skipped": False,
        }
        for fold in folds
    ]
    rows.extend(
        {
            "fold": date,
            "train_dates": "",
            "n_train": 0,
            "n_holdout": 0,
            "n_specials": 0,
            "date_type": "",
            "skipped": True,
        }
        for date in skipped
    )
    return pd.DataFrame(rows).sort_values("fold", ignore_index=True)


def summary(races: pd.DataFrame, eligible: list[str] | None = None) -> dict:
    """Schedule size, so a missing election is visible as an absent date.

    A derived schedule has no constant list to check itself against, so the
    shape of what was built is published instead: how many folds, how they
    split between general and special dates, and how many races sit on each
    side. Combined with `eligible`, which names the dates the schedule was
    measured against, that is what the enumerated year list used to provide.
    """
    built, skipped = build(races, eligible)
    general = [fold for fold in built if not fold.is_special_date]
    special = [fold for fold in built if fold.is_special_date]
    return {
        "n_folds": len(built),
        "n_general_dates": len(general),
        "n_special_dates": len(special),
        "general_races": sum(fold.n_holdout for fold in general),
        "special_races": sum(fold.n_holdout for fold in special),
        "holdout_races": sum(fold.n_holdout for fold in built),
        "seed_races": int((races["election_date"] < SEED_CUTOFF).sum()),
        "smallest_training_fold": min((fold.n_train for fold in built), default=0),
        "skipped_dates": skipped,
    }
