"""Precinct-level Partisan Voter Index.

A PVI record is keyed by the PVI year, which names the later presidential
election of the pair, and by the redistricting cycle whose precinct geography
it is expressed on. The same pair evaluated on two cycles yields two distinct
datasets, which matters because off-year special elections are run on the
outgoing cycle's districts (design.md, D6).
"""

from __future__ import annotations

import functools

import pandas as pd

from . import build, config, crosswalk

KEY = crosswalk.KEY
PVI_DATASETS = config.PVI_DIR / "ma_precinct_pvi.csv.gz"
MISSING_REPORT = "pvi_missing_precincts.csv"

# Which redistricting cycle each presidential election was natively cast on.
NATIVE_CYCLE = {2004: 2001, 2008: 2001, 2012: 2011, 2016: 2011, 2020: 2011, 2024: 2021}


@functools.cache
def national_baseline() -> pd.DataFrame:
    return pd.read_csv(
        config.REFERENCE_DIR / "national_presidential_baseline.csv"
    ).set_index("election_year")


def required_datasets() -> pd.DataFrame:
    """The (pvi_year, cycle) combinations the race window consumes."""
    mapping = config.race_year_pvi()
    combos = mapping[
        ["pvi_year", "pres_year_earlier", "pres_year_later", "redistricting_cycle"]
    ].drop_duplicates()
    return combos.sort_values(
        ["pvi_year", "redistricting_cycle"], ignore_index=True
    )


@functools.cache
def _presidential_votes() -> pd.DataFrame:
    return pd.read_csv(build.PRESIDENTIAL_VOTE)


@functools.cache
def votes_on_cycle(election_year: int, cycle: int) -> tuple:
    """Presidential votes for one year expressed on `cycle`'s precincts."""
    votes = _presidential_votes()
    year_votes = votes[votes["election_year"] == election_year]
    native = NATIVE_CYCLE[election_year]
    remapped, unresolved = crosswalk.remap(year_votes, native, cycle)
    return remapped, unresolved


def national_two_party_share(earlier: int, later: int) -> float:
    baseline = national_baseline()
    dem = baseline.loc[earlier, "dem_votes"] + baseline.loc[later, "dem_votes"]
    gop = baseline.loc[earlier, "gop_votes"] + baseline.loc[later, "gop_votes"]
    return dem / (dem + gop)


def compute_pvi(earlier: int, later: int, cycle: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Precinct PVI for one presidential pair on one cycle's geography."""
    early_votes, early_unresolved = votes_on_cycle(earlier, cycle)
    late_votes, late_unresolved = votes_on_cycle(later, cycle)

    merged = early_votes.merge(
        late_votes, on=KEY, how="outer", suffixes=("_earlier", "_later")
    )
    for column in (
        "dem_votes_earlier",
        "gop_votes_earlier",
        "dem_votes_later",
        "gop_votes_later",
    ):
        merged[column] = merged[column].fillna(0.0)

    merged["dem_votes"] = merged["dem_votes_earlier"] + merged["dem_votes_later"]
    merged["gop_votes"] = merged["gop_votes_earlier"] + merged["gop_votes_later"]
    merged["two_party_votes"] = merged["dem_votes"] + merged["gop_votes"]

    national = national_two_party_share(earlier, later)
    share = merged["dem_votes"] / merged["two_party_votes"]
    merged["PVI_N"] = (share - national) * 100.0
    merged.loc[merged["two_party_votes"] <= 0, "PVI_N"] = pd.NA

    # A precinct is interpolated if either election's votes for it were.
    provenance = merged[["provenance_earlier", "provenance_later"]].fillna("missing")
    merged["provenance"] = provenance.apply(
        lambda r: crosswalk.PROVENANCE_INTERPOLATED
        if crosswalk.PROVENANCE_INTERPOLATED in set(r)
        else sorted(set(r))[0],
        axis=1,
    )

    merged["pvi_year"] = later
    merged["redistricting_cycle"] = cycle
    merged["pres_year_earlier"] = earlier
    merged["pres_year_later"] = later

    columns = [
        "pvi_year",
        "redistricting_cycle",
        "pres_year_earlier",
        "pres_year_later",
        *KEY,
        "dem_votes",
        "gop_votes",
        "two_party_votes",
        "PVI_N",
        "provenance",
    ]
    result = merged[columns].sort_values(
        ["pvi_year", "redistricting_cycle", *KEY], ignore_index=True
    )
    missing = result[result["PVI_N"].isna()].copy()
    unresolved = pd.concat([early_unresolved, late_unresolved], ignore_index=True)
    return result, pd.concat([missing, unresolved], ignore_index=True)


def build_all() -> pd.DataFrame:
    """Produce every required PVI dataset and write the published file."""
    frames, reports = [], []
    for row in required_datasets().itertuples(index=False):
        frame, missing = compute_pvi(
            int(row.pres_year_earlier),
            int(row.pres_year_later),
            int(row.redistricting_cycle),
        )
        interpolated = (
            frame["provenance"] == crosswalk.PROVENANCE_INTERPOLATED
        ).sum()
        print(
            f"PVI {row.pvi_year} on cycle {row.redistricting_cycle} "
            f"({row.pres_year_earlier}+{row.pres_year_later}): "
            f"{len(frame)} precincts, {interpolated} interpolated, "
            f"{int(frame['PVI_N'].isna().sum())} missing"
        )
        frames.append(frame)
        reports.append(missing)

    combined = pd.concat(frames, ignore_index=True)
    build.write_csv(combined, PVI_DATASETS)

    report = pd.concat(reports, ignore_index=True)
    path = config.REPORT_DIR / MISSING_REPORT
    report.to_csv(path, index=False)
    print(f"missing/unresolved PVI precincts: {len(report)} -> {path.relative_to(config.ROOT)}")
    return combined
