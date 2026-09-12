"""Derive precinct-to-district mappings from precinct-level legislative returns.

Each district's result file enumerates exactly the precincts that district
contains, so the union of a cycle's returns is a complete mapping. This is the
only available source for the 2001 cycle, which no sibling repository covers
(precinct-crosswalk spec).
"""

from __future__ import annotations

import pandas as pd

from . import build, config, crosswalk

KEY = crosswalk.KEY
OFFICE_COLUMN = {"State Representative": "state_rep", "State Senate": "state_senate"}

MAPPING_FILE = config.PRECINCT_DIR / "ma_precinct_district.csv.gz"
CONFLICT_REPORT = "precinct_district_conflicts.csv"


def _assignments(results: pd.DataFrame) -> pd.DataFrame:
    """One row per (cycle, office, precinct, district) observed in the returns."""
    rows = results[results["row_kind"] == "total"][
        ["redistricting_cycle", "office", "district_display", "election_year", *KEY]
    ].drop_duplicates()
    return rows


def build_mapping(results: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (precinct-to-district mapping, conflict report).

    A conflict is a precinct assigned to more than one district for the same
    office within one redistricting cycle. Where a conflict arises because a
    municipality renumbered precincts mid-cycle, the most recent election's
    assignment wins and the conflict is still reported.
    """
    assignments = _assignments(results)
    conflicts = []
    frames = []

    for office, column in OFFICE_COLUMN.items():
        office_rows = assignments[assignments["office"] == office]
        grouped = office_rows.groupby(
            ["redistricting_cycle", *KEY], as_index=False
        ).agg(
            districts=("district_display", lambda s: sorted(set(s))),
            latest_year=("election_year", "max"),
        )
        multi = grouped[grouped["districts"].map(len) > 1]
        for row in multi.itertuples(index=False):
            conflicts.append(
                {
                    "redistricting_cycle": row.redistricting_cycle,
                    "office": office,
                    "city_town": row.city_town,
                    "ward": row.ward,
                    "precinct": row.precinct,
                    "districts": "; ".join(row.districts),
                }
            )

        # Resolve by taking the assignment from the most recent election.
        office_rows = office_rows.sort_values("election_year")
        resolved = office_rows.drop_duplicates(
            subset=["redistricting_cycle", *KEY], keep="last"
        )[["redistricting_cycle", *KEY, "district_display"]].rename(
            columns={"district_display": column}
        )
        frames.append(resolved.set_index(["redistricting_cycle", *KEY]))

    mapping = pd.concat(frames, axis=1).reset_index()
    conflict_report = pd.DataFrame(
        conflicts,
        columns=[
            "redistricting_cycle",
            "office",
            "city_town",
            "ward",
            "precinct",
            "districts",
        ],
    )
    return mapping.sort_values(["redistricting_cycle", *KEY], ignore_index=True), conflict_report


def build_and_write() -> pd.DataFrame:
    results = pd.read_csv(build.LEGISLATIVE_RESULTS)
    mapping, conflicts = build_mapping(results)
    build.write_csv(mapping, MAPPING_FILE)
    path = config.REPORT_DIR / CONFLICT_REPORT
    conflicts.to_csv(path, index=False)
    print(
        f"precinct-district conflicts: {len(conflicts)} "
        f"-> {path.relative_to(config.ROOT)}"
    )
    return mapping
