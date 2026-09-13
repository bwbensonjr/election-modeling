"""Validate the training table's district rollup against the existing table.

Most races agree exactly. The divergences are definitional rather than
arithmetic, and each is categorised so that the report distinguishes a data
problem from a deliberate difference.
"""

from __future__ import annotations

import pandas as pd

from . import config, training

REFERENCE = config.ROOT.parent / "mapoli" / "model" / "ma_leg_two_party_2008_2025.csv"
REPORT = "training_rollup_validation.csv"
TOLERANCE = 0.01  # percentage points

CATEGORY_AGREES = "agrees"
CATEGORY_NO_DEM = "reference_no_democrat_precedence_bug"
CATEGORY_MULTI_DEM = "reference_compares_against_second_democrat"
CATEGORY_SLOT_LIMIT = "reference_denominator_omits_candidates"
# The write-in threshold changed which races are contested, so these races
# exist here and not in the reference at all. That is the intended effect of
# design.md D2, not a disagreement about a race both sources carry, and it is
# named rather than left to vanish in an inner join.
CATEGORY_WRITE_IN_ADMITTED = "admitted_by_write_in_absent_from_reference"
CATEGORY_ABSENT = "absent_from_reference"
CATEGORY_UNEXPLAINED = "unexplained"

# The published summary can describe at most four candidates per race.
SLOT_VOTE_COLUMNS = [
    "votes_dem",
    "votes_gop",
    "votes_third_party",
    "votes_write_in",
]


def run(rows: pd.DataFrame | None = None) -> pd.DataFrame:
    rows = (
        pd.read_csv(training.TRAINING_FILE, low_memory=False) if rows is None else rows
    )
    reference = pd.read_csv(REFERENCE)
    summaries = config.general_summaries()

    rolled = rows.groupby(
        [
            "election_id",
            "no_dem_candidate",
            "admitted_by_write_in",
            "office",
            "district_display",
            "election_year",
        ],
        as_index=False,
    )[["dem_votes", "opponent_votes", "candidate_votes"]].sum()
    rolled["rollup_margin"] = (
        rolled["dem_votes"] / rolled["candidate_votes"]
        - rolled["opponent_votes"] / rolled["candidate_votes"]
    ) * 100

    merged = rolled.merge(
        reference[["election_id", "dem_margin"]], on="election_id", how="left"
    ).merge(
        summaries[["election_id", *SLOT_VOTE_COLUMNS]],
        on="election_id",
        how="left",
    )
    first = rows.groupby("election_id")[
        ["opponent_candidate", "dem_candidate_count", "candidate_count"]
    ].first()
    merged = merged.join(first, on="election_id")
    merged["slot_votes"] = merged[SLOT_VOTE_COLUMNS].fillna(0).sum(axis=1)
    merged["difference"] = merged["rollup_margin"] - merged["dem_margin"]

    def categorise(row) -> str:
        if pd.isna(row["dem_margin"]):
            # The reference does not carry this race, so there is nothing to
            # disagree with. A race the write-in threshold admitted is the
            # expected case; anything else is a real gap worth seeing.
            return (
                CATEGORY_WRITE_IN_ADMITTED
                if row["admitted_by_write_in"]
                else CATEGORY_ABSENT
            )
        if abs(row["difference"]) <= TOLERANCE:
            return CATEGORY_AGREES
        if row["no_dem_candidate"]:
            return CATEGORY_NO_DEM
        # The reference's percentages are shares of the votes its four slots
        # record. Where a race has more candidates than that, its denominator
        # is short and every percentage in the row is inflated.
        if row["slot_votes"] != row["candidate_votes"]:
            return CATEGORY_SLOT_LIMIT
        if row["dem_candidate_count"] > 1:
            return CATEGORY_MULTI_DEM
        return CATEGORY_UNEXPLAINED

    merged["category"] = merged.apply(categorise, axis=1)

    report = merged[
        [
            "election_id",
            "election_year",
            "office",
            "district_display",
            "rollup_margin",
            "dem_margin",
            "difference",
            "category",
            "opponent_candidate",
            "candidate_count",
            "dem_candidate_count",
            "no_dem_candidate",
            "admitted_by_write_in",
        ]
    ].sort_values("difference", key=abs, ascending=False, ignore_index=True)

    path = config.REPORT_DIR / REPORT
    path.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(path, index=False)

    counts = report["category"].value_counts()
    print(f"races compared: {len(report)}")
    for category, count in counts.items():
        print(f"  {category:<45} {count:>4}")
    unexplained = int(counts.get(CATEGORY_UNEXPLAINED, 0))
    print(f"\n-> {path.relative_to(config.ROOT)}")
    if unexplained:
        print(f"WARNING: {unexplained} unexplained divergences")
    return report
