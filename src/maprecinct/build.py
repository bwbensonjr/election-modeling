"""Assemble normalized precinct results and write the published CSVs."""

from __future__ import annotations

import pandas as pd

from . import config, elections, fetch, normalize

RESULT_COLUMNS = [
    "election_id",
    "election_date",
    "election_year",
    "redistricting_cycle",
    "office",
    "district",
    "district_display",
    "is_special",
    "city_town",
    "ward",
    "precinct",
    "candidate",
    "party",
    "row_kind",
    "votes",
]

PRESIDENTIAL_RESULTS = config.PRECINCT_DIR / "ma_precinct_presidential_results.csv.gz"
LEGISLATIVE_RESULTS = config.PRECINCT_DIR / "ma_precinct_legislative_results.csv.gz"
PRESIDENTIAL_VOTE = config.PRECINCT_DIR / "ma_precinct_presidential_vote.csv.gz"


def normalized_results(election_set: pd.DataFrame) -> pd.DataFrame:
    """Normalize every cached election in `election_set`, with race metadata."""
    frames = []
    for row in election_set.itertuples(index=False):
        election_id = int(row.election_id)
        if not fetch.cache_path(election_id).exists():
            continue
        frame = normalize.normalize_election(election_id)
        frame["election_date"] = row.election_date
        frame["election_year"] = row.election_year
        frame["redistricting_cycle"] = row.redistricting_cycle
        frame["office"] = row.office
        frame["district"] = row.district
        frame["district_display"] = row.district_display
        frame["is_special"] = row.is_special
        frames.append(frame)
    if not frames:
        return pd.DataFrame(columns=RESULT_COLUMNS)
    return pd.concat(frames, ignore_index=True)[RESULT_COLUMNS]


def presidential_two_party(results: pd.DataFrame) -> pd.DataFrame:
    """Collapse presidential results to per-precinct two-party vote totals."""
    candidates = results[results["row_kind"] == "candidate"]
    major = candidates[candidates["party"].isin(["Democratic", "Republican"])]

    wide = (
        major.pivot_table(
            index=[
                "election_year",
                "redistricting_cycle",
                "city_town",
                "ward",
                "precinct",
            ],
            columns="party",
            values="votes",
            aggfunc="sum",
            fill_value=0,
        )
        .rename(columns={"Democratic": "dem_votes", "Republican": "gop_votes"})
        .reset_index()
    )
    wide.columns.name = None
    totals = (
        results[results["row_kind"] == "total"]
        .groupby(
            ["election_year", "redistricting_cycle", "city_town", "ward", "precinct"],
            as_index=False,
        )["votes"]
        .sum()
        .rename(columns={"votes": "total_votes"})
    )
    merged = wide.merge(
        totals,
        on=["election_year", "redistricting_cycle", "city_town", "ward", "precinct"],
        how="left",
    )
    return merged.sort_values(
        ["election_year", "city_town", "ward", "precinct"], ignore_index=True
    )


def write_csv(frame: pd.DataFrame, path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, compression="gzip")
    print(f"wrote {len(frame):>7} rows -> {path.relative_to(config.ROOT)}")


def build_presidential() -> pd.DataFrame:
    results = normalized_results(elections.presidential_elections())
    write_csv(results, PRESIDENTIAL_RESULTS)
    write_csv(presidential_two_party(results), PRESIDENTIAL_VOTE)
    return results


def build_legislative() -> pd.DataFrame:
    results = normalized_results(elections.legislative_elections())
    write_csv(results, LEGISLATIVE_RESULTS)
    return results
