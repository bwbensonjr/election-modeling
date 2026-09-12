"""Paths, constants, and reference data shared across pipeline stages."""

from __future__ import annotations

import functools
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

CACHE_DIR = ROOT / "cache"
ELECTIONSTATS_CACHE = CACHE_DIR / "electionstats"
GIS_CACHE = CACHE_DIR / "gis"

DATA_DIR = ROOT / "data"
PRECINCT_DIR = DATA_DIR / "precinct"
PVI_DIR = DATA_DIR / "pvi"
REPORT_DIR = DATA_DIR / "reports"
REFERENCE_DIR = DATA_DIR / "reference"

# Published ma-election-db artifacts. A local sibling checkout is preferred so
# the pipeline can run offline; the published URL is the fallback.
MA_ELECTION_DB = ROOT.parent / "ma-election-db"
MA_ELECTION_DB_URL = "https://bwbensonjr.github.io/ma-election-db/"
GENERAL_SUMMARIES = "data/ma_general_election_summaries.csv.gz"
GENERAL_CANDIDATES = "data/ma_general_election_candidates.csv.gz"

LEGISLATIVE_OFFICES = ("State Representative", "State Senate")

# Scope, per the proposal.
LEGISLATIVE_YEARS = range(2010, 2025)
PRESIDENTIAL_YEARS = (2004, 2008, 2012, 2016, 2020, 2024)


def _read(relative: str) -> pd.DataFrame:
    """Read a published ma-election-db artifact, preferring a local checkout."""
    local = MA_ELECTION_DB / relative
    if local.exists():
        return pd.read_csv(local)
    return pd.read_csv(MA_ELECTION_DB_URL + relative)


@functools.cache
def general_summaries() -> pd.DataFrame:
    df = _read(GENERAL_SUMMARIES)
    df["election_year"] = df["election_date"].str.slice(0, 4).astype(int)
    return df


@functools.cache
def general_candidates() -> pd.DataFrame:
    return _read(GENERAL_CANDIDATES)


@functools.cache
def race_year_pvi() -> pd.DataFrame:
    """Race year -> presidential pair and redistricting cycle."""
    return pd.read_csv(REFERENCE_DIR / "race_year_pvi.csv")


@functools.cache
def redistricting_cycles() -> pd.DataFrame:
    return pd.read_csv(REFERENCE_DIR / "redistricting_cycle.csv")


def cycle_for_year(year: int) -> int:
    """The redistricting cycle in force for an election held in `year`."""
    cycles = redistricting_cycles()
    for _, row in cycles.iterrows():
        last = row["last_election_year"]
        if year >= row["first_election_year"] and (pd.isna(last) or year <= last):
            return int(row["redistricting_cycle"])
    raise ValueError(f"No redistricting cycle covers election year {year}")
