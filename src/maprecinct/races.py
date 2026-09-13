"""Roll the race-precinct training table up to one row per race.

The district margin and district PVI are recomputed from summed vote counts,
never averaged from the precinct values: averaging would weight a 300-vote
precinct the same as a 3,000-vote one and would not reproduce the published
district PVI (design.md, D2).
"""

from __future__ import annotations

import pandas as pd

from . import build, config, crosswalk, pvi, training

KEY = crosswalk.KEY

RACE_DIR = config.DATA_DIR / "race"
RACE_FILE = RACE_DIR / "ma_race_training_set.csv.gz"
COVERAGE_REPORT = RACE_DIR / "race_pvi_coverage.csv"

# Race attributes that must be identical across a race's precinct rows. They
# describe the contest, not the precinct, so a disagreement means the precinct
# table is inconsistent and the rollup must not paper over it.
CARRIED = [
    "election_date",
    "election_year",
    "redistricting_cycle",
    "office",
    "district",
    "district_display",
    "incumbent_status",
    "pres_elec",
    "is_special",
    "num_candidates",
    "no_dem_candidate",
    "dem_candidate",
    "opponent_candidate",
    "opponent_party",
    "dem_candidate_count",
    "pvi_year",
]

RACE_COLUMNS = [
    "election_id",
    "election_date",
    "election_year",
    "redistricting_cycle",
    "office",
    "district",
    "district_display",
    "dem_margin",
    "PVI_N",
    "incumbent_status",
    "pres_elec",
    "is_special",
    "num_candidates",
    "no_dem_candidate",
    "dem_candidate",
    "opponent_candidate",
    "opponent_party",
    "dem_candidate_count",
    "dem_votes",
    "opponent_votes",
    "candidate_votes",
    "total_votes",
    "n_precincts",
    "pvi_year",
    "pvi_dem_votes",
    "pvi_gop_votes",
    "pvi_two_party_votes",
    "pvi_coverage",
    "pvi_interpolated_share",
    "precincts_split_across_districts",
]


class InconsistentRaceError(ValueError):
    """A race's precinct rows disagree on an attribute that describes the race."""


def carry_attributes(rows: pd.DataFrame) -> pd.DataFrame:
    """One row per race carrying the race-level attributes, or fail.

    `dem_candidate` is allowed to be absent throughout a no-Democrat race, so
    the uniqueness test counts distinct non-null values rather than requiring
    one everywhere.
    """
    grouped = rows.groupby("election_id", sort=False)
    disagreements = []
    for column in CARRIED:
        distinct = grouped[column].nunique(dropna=True)
        bad = distinct[distinct > 1]
        for election_id in bad.index:
            values = sorted(
                str(v) for v in rows.loc[rows["election_id"] == election_id, column].dropna().unique()
            )
            disagreements.append(f"  election {election_id}: {column} = {values}")
    if disagreements:
        raise InconsistentRaceError(
            "precinct rows disagree on race-level attributes:\n"
            + "\n".join(disagreements)
        )
    return grouped[CARRIED].first().reset_index()


def district_margin(rows: pd.DataFrame) -> pd.DataFrame:
    """Vote-summed district margin, in percentage points.

    `dem_votes` holds whichever candidate occupies the Democratic side of the
    comparison, including the negated no-Democrat case the precinct table
    already encodes, so one expression covers every race.
    """
    totals = rows.groupby("election_id", sort=False).agg(
        dem_votes=("dem_votes", "sum"),
        opponent_votes=("opponent_votes", "sum"),
        candidate_votes=("candidate_votes", "sum"),
        total_votes=("total_votes", "sum"),
        n_precincts=("precinct", "size"),
        precincts_split_across_districts=("precinct_split_across_districts", "sum"),
    )
    share_dem = totals["dem_votes"] / totals["candidate_votes"]
    share_opponent = totals["opponent_votes"] / totals["candidate_votes"]
    totals["dem_margin"] = (share_dem - share_opponent) * 100.0
    return totals.reset_index()


def district_pvi(rows: pd.DataFrame) -> pd.DataFrame:
    """District PVI from the summed two-party presidential votes.

    The precinct PVI table carries the vote counts behind each precinct's
    `PVI_N`; summing those over the race's precincts and applying the PVI
    formula to the district totals is the definition. A precinct with no
    two-party votes contributes zero to both sums, which is what a precinct
    that cast no presidential votes should contribute.
    """
    pvi_table = pd.read_csv(config.PVI_DIR / "ma_precinct_pvi.csv.gz")[
        [
            "pvi_year",
            "redistricting_cycle",
            "pres_year_earlier",
            "pres_year_later",
            *KEY,
            "dem_votes",
            "gop_votes",
            "provenance",
        ]
    ].rename(columns={"dem_votes": "pvi_dem_votes", "gop_votes": "pvi_gop_votes"})

    joined = rows[
        ["election_id", "pvi_year", "redistricting_cycle", *KEY]
    ].merge(pvi_table, on=["pvi_year", "redistricting_cycle", *KEY], how="left")

    joined["pvi_two_party_votes"] = (
        joined["pvi_dem_votes"].fillna(0.0) + joined["pvi_gop_votes"].fillna(0.0)
    )
    joined["contributed"] = joined["pvi_two_party_votes"] > 0
    joined["interpolated_votes"] = joined["pvi_two_party_votes"].where(
        joined["provenance"] == crosswalk.PROVENANCE_INTERPOLATED, 0.0
    )

    agg = joined.groupby("election_id", sort=False).agg(
        pvi_dem_votes=("pvi_dem_votes", "sum"),
        pvi_gop_votes=("pvi_gop_votes", "sum"),
        pvi_two_party_votes=("pvi_two_party_votes", "sum"),
        interpolated_votes=("interpolated_votes", "sum"),
        contributing=("contributed", "sum"),
        precincts=("contributed", "size"),
        pres_year_earlier=("pres_year_earlier", "max"),
        pres_year_later=("pres_year_later", "max"),
    )
    agg["pvi_coverage"] = agg["contributing"] / agg["precincts"]
    agg["pvi_interpolated_share"] = (
        agg["interpolated_votes"] / agg["pvi_two_party_votes"]
    ).where(agg["pvi_two_party_votes"] > 0)

    # The national baseline belongs to the presidential pair, so it is looked
    # up per pair rather than per race.
    shares = {}
    for earlier, later in (
        agg[["pres_year_earlier", "pres_year_later"]].dropna().drop_duplicates().itertuples(index=False)
    ):
        shares[(earlier, later)] = pvi.national_two_party_share(int(earlier), int(later))
    national = [
        shares.get((e, l)) if pd.notna(e) and pd.notna(l) else None
        for e, l in zip(agg["pres_year_earlier"], agg["pres_year_later"])
    ]

    dem_share = agg["pvi_dem_votes"] / agg["pvi_two_party_votes"]
    agg["PVI_N"] = (dem_share - pd.Series(national, index=agg.index)) * 100.0
    agg.loc[agg["pvi_two_party_votes"] <= 0, "PVI_N"] = pd.NA
    return agg.reset_index()


def build_rows(rows: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Assemble the race table and the PVI coverage report."""
    races = carry_attributes(rows)
    races = races.merge(district_margin(rows), on="election_id", how="left")
    races = races.merge(district_pvi(rows), on="election_id", how="left")

    # A race with no PVI inputs at all has no PVI_N to condition on, so it is
    # excluded rather than published with a null predictor (design.md, D3).
    zero_coverage = races["pvi_two_party_votes"] <= 0
    coverage = races[
        [
            "election_id",
            "election_date",
            "election_year",
            "office",
            "district_display",
            "pvi_year",
            "redistricting_cycle",
            "pvi_coverage",
            "pvi_interpolated_share",
            "pvi_two_party_votes",
            "n_precincts",
        ]
    ].copy()
    coverage["excluded"] = zero_coverage.values
    coverage["reason"] = [
        "no precinct in the race has two-party presidential votes for its PVI year"
        if flag
        else ""
        for flag in zero_coverage
    ]

    published = races[~zero_coverage].copy()
    published["precincts_split_across_districts"] = published[
        "precincts_split_across_districts"
    ].astype(int)
    published = published[RACE_COLUMNS].sort_values(
        ["election_date", "office", "district_display"], ignore_index=True
    )
    return published, coverage


def build_and_write() -> pd.DataFrame:
    rows = pd.read_csv(training.TRAINING_FILE)
    races, coverage = build_rows(rows)

    build.write_csv(races, RACE_FILE)

    COVERAGE_REPORT.parent.mkdir(parents=True, exist_ok=True)
    coverage.to_csv(COVERAGE_REPORT, index=False)
    excluded = int(coverage["excluded"].sum())
    partial = int(((coverage["pvi_coverage"] < 1.0) & ~coverage["excluded"]).sum())
    print(
        f"races with partial PVI coverage: {partial}; excluded for zero coverage: "
        f"{excluded} -> {COVERAGE_REPORT.relative_to(config.ROOT)}"
    )
    return races


# --- Validation against the published district-level table -------------------

MAPOLI_DISTRICT_TABLE = (
    config.ROOT.parent / "mapoli" / "model" / "ma_leg_two_party_2008_2025.csv"
)
ROLLUP_REPORT = "race_rollup_validation.csv"

MARGIN_TOLERANCE = 0.01

# The cycle each of mapoli's published PVI vintages is expressed on. Where the
# reference joined a race to PVI on a different map than the race was run
# under, the two PVI values describe different districts and are not
# comparable.
MAPOLI_PVI_CYCLE = {2008: 2001, 2012: 2011, 2016: 2011, 2020: 2011, 2022: 2021, 2024: 2021}

# Agreement thresholds follow validate.py: a national-baseline difference
# shifts every district in a vintage by the same amount, so the comparison
# separates that constant offset from the per-district spread.
NATIVE_SPREAD_TOLERANCE = 0.05
REMAPPED_SPREAD_TOLERANCE = 5.0


def _margin_category(row) -> str:
    """Why a race's margin differs from the reference, or that it agrees."""
    if abs(row["dem_margin_difference"]) <= MARGIN_TOLERANCE:
        return "agrees"
    if row["no_dem_candidate"]:
        # ma_leg_model.R's democratic_margin() multiplies the comparison share
        # by 100 before subtracting instead of after, so every no-Democrat race
        # in the reference is wrong (docs/schema.md).
        return "reference_no_democrat_precedence_bug"
    if pd.notna(row["reference_denominator"]) and abs(
        row["reference_denominator"] - row["candidate_votes"]
    ) > 1.0:
        # The published summary carries four candidate slots and leaves some
        # candidates out; its percentages then rest on a denominator that omits
        # those votes, while the precinct sum counts every named candidate.
        return "reference_omits_candidate_from_summary_slots"
    if row["dem_candidate_count"] > 1:
        # With two Democrats the precinct table compares the strongest Democrat
        # against the strongest non-Democrat; the reference compares against
        # whichever candidate occupies its write-in or third-party slot.
        return "multiple_democrats_comparison_candidate_differs"
    return "unexplained"


def validate_rollup() -> pd.DataFrame:
    """Compare the race table against mapoli's published district-level table."""
    ours = pd.read_csv(RACE_FILE)
    if not MAPOLI_DISTRICT_TABLE.exists():
        print(
            f"SKIP race rollup validation: {MAPOLI_DISTRICT_TABLE} not found "
            "(needs a sibling mapoli checkout)"
        )
        return pd.DataFrame()

    reference = pd.read_csv(MAPOLI_DISTRICT_TABLE)[
        ["election_id", "dem_margin", "PVI_N", "pvi_year", "votes_dem", "percent_dem"]
    ].rename(
        columns={
            "dem_margin": "dem_margin_reference",
            "PVI_N": "PVI_N_reference",
            "pvi_year": "pvi_year_reference",
        }
    )
    joined = ours.merge(reference, on="election_id", how="inner")

    # The denominator the reference's percentages actually rest on, recovered
    # from its own published share.
    joined["reference_denominator"] = (
        joined["votes_dem"] / joined["percent_dem"]
    ).round(0)
    joined["dem_margin_difference"] = (
        joined["dem_margin"] - joined["dem_margin_reference"]
    )
    joined["margin_category"] = joined.apply(_margin_category, axis=1)

    # PVI is compared within each (vintage, cycle) group about that group's
    # constant offset, and only where the reference used the same geography.
    joined["PVI_N_difference"] = joined["PVI_N"] - joined["PVI_N_reference"]
    joined["reference_pvi_cycle"] = joined["pvi_year_reference"].map(MAPOLI_PVI_CYCLE)
    joined["pvi_category"] = "agrees"
    joined["pvi_offset"] = pd.NA
    joined["pvi_spread"] = pd.NA

    for (pvi_year, cycle), group in joined.groupby(["pvi_year", "redistricting_cycle"]):
        index = group.index
        if (group["reference_pvi_cycle"] != cycle).any():
            joined.loc[index, "pvi_category"] = "reference_pvi_on_different_map"
            continue
        pair = pvi.required_datasets()
        pair = pair[
            (pair["pvi_year"] == pvi_year) & (pair["redistricting_cycle"] == cycle)
        ].iloc[0]
        remapped = (
            pvi.NATIVE_CYCLE[int(pair["pres_year_earlier"])] != cycle
            or pvi.NATIVE_CYCLE[int(pair["pres_year_later"])] != cycle
        )
        tolerance = REMAPPED_SPREAD_TOLERANCE if remapped else NATIVE_SPREAD_TOLERANCE
        offset = group["PVI_N_difference"].mean()
        spread = (group["PVI_N_difference"] - offset).abs()
        joined.loc[index, "pvi_offset"] = round(offset, 4)
        joined.loc[index, "pvi_spread"] = spread.round(4)
        joined.loc[index, "pvi_category"] = [
            "agrees" if value <= tolerance else "outside_tolerance" for value in spread
        ]

    report = joined[
        [
            "election_id",
            "election_year",
            "office",
            "district_display",
            "no_dem_candidate",
            "dem_candidate_count",
            "candidate_votes",
            "reference_denominator",
            "dem_margin",
            "dem_margin_reference",
            "dem_margin_difference",
            "margin_category",
            "pvi_year",
            "pvi_year_reference",
            "redistricting_cycle",
            "reference_pvi_cycle",
            "PVI_N",
            "PVI_N_reference",
            "PVI_N_difference",
            "pvi_offset",
            "pvi_spread",
            "pvi_category",
        ]
    ].sort_values(["election_year", "office", "district_display"], ignore_index=True)

    path = config.REPORT_DIR / ROLLUP_REPORT
    path.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(path, index=False)

    print(f"\nrace rollup vs mapoli district table: {len(report)} races compared")
    print("  dem_margin:")
    for category, count in report["margin_category"].value_counts().items():
        print(f"    {count:>4}  {category}")
    print("  PVI_N:")
    for category, count in report["pvi_category"].value_counts().items():
        print(f"    {count:>4}  {category}")
    print(f"-> {path.relative_to(config.ROOT)}")

    unexplained = report[report["margin_category"] == "unexplained"]
    outside = report[report["pvi_category"] == "outside_tolerance"]
    if len(unexplained):
        print(f"WARNING: {len(unexplained)} races differ on dem_margin without a known cause")
    if len(outside):
        print(f"WARNING: {len(outside)} races outside the PVI spread tolerance")
    return report
