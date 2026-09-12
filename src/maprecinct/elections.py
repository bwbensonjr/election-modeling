"""Enumerate the elections in scope for precinct-level collection.

Election identifiers come from ma-election-db's published general election
summaries rather than the electionstats search endpoint, so that the row set
and the race metadata stay consistent by construction (design.md, D2).
"""

from __future__ import annotations

import pandas as pd

from . import config

PRESIDENT = "President"

ENUMERATION_COLUMNS = [
    "election_id",
    "election_date",
    "election_year",
    "redistricting_cycle",
    "office",
    "district",
    "district_display",
    "is_special",
    "num_candidates",
]


def presidential_elections() -> pd.DataFrame:
    """One row per presidential election in scope (2004 through 2024)."""
    summaries = config.general_summaries()
    df = summaries[
        (summaries["office"] == PRESIDENT)
        & (summaries["election_year"].isin(config.PRESIDENTIAL_YEARS))
    ].copy()
    return _finalize(df)


def legislative_elections() -> pd.DataFrame:
    """Every State Rep and State Senate election 2010-2024, general and special.

    Uncontested races are included: they carry no usable margin, but their
    precinct returns are the only source for the 2001-cycle precinct-to-district
    mapping (design.md, D8).
    """
    summaries = config.general_summaries()
    df = summaries[
        summaries["office"].isin(config.LEGISLATIVE_OFFICES)
        & summaries["election_year"].isin(config.LEGISLATIVE_YEARS)
    ].copy()
    return _finalize(df)


def all_elections() -> pd.DataFrame:
    """Every election the fetch stage must retrieve."""
    return pd.concat(
        [presidential_elections(), legislative_elections()], ignore_index=True
    ).sort_values(["election_date", "office", "district_display"], ignore_index=True)


def _finalize(df: pd.DataFrame) -> pd.DataFrame:
    df["redistricting_cycle"] = df["election_year"].map(config.cycle_for_year)
    df["is_special"] = df["is_special"].astype(bool)
    missing = [c for c in ENUMERATION_COLUMNS if c not in df.columns]
    if missing:
        raise KeyError(f"Summaries are missing expected columns: {missing}")
    return df[ENUMERATION_COLUMNS].sort_values(
        ["election_date", "office", "district_display"], ignore_index=True
    )
