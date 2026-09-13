"""Rolling-origin fold construction.

Each fold trains on every race strictly before its year and predicts that
year's races, so the training window expands and never contains the future
(model-scoring spec). Splitting by year rather than at random is what keeps a
district that recurs across cycles out of both sides of the same split.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

# Every election year from 2014 through 2024. 2019 is listed as eligible and
# drops out because the table holds no contested races for it; recording that
# is the point, since a silently absent year would be indistinguishable from a
# year nobody thought to score.
ELIGIBLE_FOLD_YEARS = tuple(range(2014, 2025))

# Races before the first fold train the first model and are never scored.
SEED_YEARS_END = 2013


@dataclass(frozen=True)
class Fold:
    year: int
    train: pd.DataFrame
    holdout: pd.DataFrame

    @property
    def n_train(self) -> int:
        return len(self.train)

    @property
    def n_holdout(self) -> int:
        return len(self.holdout)


def build(races: pd.DataFrame) -> tuple[list[Fold], list[int]]:
    """The fold schedule, and the eligible years that produced no fold."""
    folds, skipped = [], []
    for year in ELIGIBLE_FOLD_YEARS:
        holdout = races[races["election_year"] == year]
        if holdout.empty:
            skipped.append(year)
            continue
        train = races[races["election_year"] < year]
        if train.empty:
            skipped.append(year)
            continue
        folds.append(Fold(year=year, train=train, holdout=holdout))
    return folds, skipped


def schedule(races: pd.DataFrame) -> pd.DataFrame:
    """A printable summary of the fold schedule."""
    folds, skipped = build(races)
    rows = [
        {
            "fold": fold.year,
            "train_years": f"{int(fold.train['election_year'].min())}-"
            f"{int(fold.train['election_year'].max())}",
            "n_train": fold.n_train,
            "n_holdout": fold.n_holdout,
            "n_specials": int(fold.holdout["is_special"].sum()),
            "skipped": False,
        }
        for fold in folds
    ]
    rows.extend(
        {
            "fold": year,
            "train_years": "",
            "n_train": 0,
            "n_holdout": 0,
            "n_specials": 0,
            "skipped": True,
        }
        for year in skipped
    )
    return pd.DataFrame(rows).sort_values("fold", ignore_index=True)
