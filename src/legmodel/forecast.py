"""Response-free forecast targets and prospective forecast plumbing."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pandas as pd

from maprecinct import crosswalk
from maprecinct.ocpf import normalize_district

from . import config

TARGET_KEY = ["election_date", "office", "district"]
TARGET_OFFICES = {"State Representative", "State Senate"}
PRIMARY_DATE_2026 = "2026-09-01"
GENERAL_DATE_2026 = "2026-11-03"
TARGET_REQUIRED = [
    "target_id",
    *TARGET_KEY,
    "district_display",
    "dem_candidate_id",
    "dem_candidate_name",
    "comparison_candidate_id",
    "comparison_candidate_name",
    "comparison_candidate_party",
    "incumbent_status",
    "PVI_N",
    "pvi_year",
    "redistricting_cycle",
    "pvi_coverage",
    "pvi_provenance",
    "ballot_timing",
    "money_complete_60d",
    "money_complete_14d",
    "candidate_source",
    "candidate_source_digest",
    "candidate_data_as_of",
    "pvi_source",
    "pvi_source_digest",
    "comparison_rule",
    "comparison_review_status",
    "dem_nominee_basis",
    "dem_nominee_review_status",
    "comparison_nominee_basis",
    "comparison_nominee_review_status",
]
RESULT_COLUMN_PARTS = (
    "result",
    "winner",
    "vote_total",
    "num_votes",
    "margin",
    "observed",
)


class TargetValidationError(ValueError):
    """A forecast target violates the response-free target contract."""


class TargetReviewRequired(TargetValidationError):
    """A target matchup needs an explicit pre-election candidate selection."""


def target_id(election_date: str, office: str, district: str) -> str:
    """Stable identity derived only from the target's natural key."""
    value = "|".join([str(election_date), str(office), str(district)])
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:20]


def source_candidate_id(
    primary_date: str, office: str, district: str, party: str, name: str
) -> str:
    """Stable source identity for a primary candidate without an upstream ID."""
    value = f"{primary_date}|{office}|{district}|{party}|{name}"
    return "sec-" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:20]


def source_digest(paths: list[Path]) -> str:
    """Digest the ordered bytes of every published source artifact."""
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.read_bytes())
    return "sha256:" + digest.hexdigest()


def _name_key(value: str) -> str:
    """First and last name key used by the published primary roster."""
    suffixes = {"jr", "sr", "ii", "iii", "iv"}
    tokens = [
        token
        for token in re.sub(r"[.,]", " ", str(value).lower()).split()
        if token not in suffixes
    ]
    if len(tokens) >= 2:
        return f"{tokens[0]} {tokens[-1]}"
    return tokens[0] if tokens else ""


def _truthy(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    return series.astype(str).str.lower().isin({"1", "true", "yes"})


def build_target_candidates(
    primary_roster: pd.DataFrame,
    primary_results: pd.DataFrame,
    primary_date: str = PRIMARY_DATE_2026,
) -> pd.DataFrame:
    """Build the candidate-grain pre-general roster from primary artifacts.

    Names and incumbency come from the Secretary roster where available. Final
    primary results identify nominees and also retain a write-in nominee who
    was necessarily absent from the pre-primary roster.
    """
    roster = primary_roster[
        primary_roster["office"].isin(TARGET_OFFICES)
        & primary_roster["election_date"].astype(str).eq(primary_date)
    ].copy()
    results = primary_results[
        primary_results["office"].isin(TARGET_OFFICES)
        & primary_results["election_date"].astype(str).eq(primary_date)
        & _truthy(primary_results["is_winner"])
    ].copy()
    results["_name_key"] = results["name"].map(_name_key)
    roster["_name_key"] = roster["name"].map(_name_key)
    join_key = ["office", "district", "party", "_name_key"]
    joined = results.merge(
        roster,
        on=join_key,
        how="left",
        suffixes=("_result", "_roster"),
        validate="one_to_one",
        indicator=True,
    )
    joined["candidate_name"] = joined["name_roster"].fillna(joined["name_result"])
    joined["district_display"] = joined["district_display_roster"].fillna(
        joined["district_display_result"]
    )
    joined["candidate_id"] = [
        source_candidate_id(primary_date, office, district, party, name)
        for office, district, party, name in joined[
            ["office", "district", "party", "candidate_name"]
        ].itertuples(index=False, name=None)
    ]
    joined["is_incumbent"] = joined["is_incumbent"].fillna(0).astype(bool)
    result_only = joined["_merge"].eq("left_only")
    contested = joined["num_candidates"].fillna(1).astype(int).gt(1)
    write_in = _truthy(joined["is_write_in"])
    joined["nominee_basis"] = "uncontested_primary"
    joined.loc[contested, "nominee_basis"] = "final_primary_nominee"
    joined.loc[result_only | write_in, "nominee_basis"] = (
        "final_primary_write_in_nominee"
    )
    joined["nominee_review_status"] = "not_required_uncontested_primary"
    joined.loc[contested, "nominee_review_status"] = "confirmed_final_primary"
    joined.loc[result_only | write_in, "nominee_review_status"] = (
        "confirmed_final_primary_result_only"
    )
    columns = [
        "office",
        "district",
        "district_display",
        "party",
        "candidate_id",
        "candidate_name",
        "is_incumbent",
        "nominee_basis",
        "nominee_review_status",
    ]
    return joined[columns].sort_values(
        ["office", "district", "party"], ignore_index=True
    )


def select_comparison_candidate(
    candidates: pd.DataFrame, reviewed_candidate_id: str | None = None
) -> tuple[pd.Series, str]:
    """Select a non-Democrat without consulting general-election outcomes."""
    comparison = candidates[candidates["party"].ne("Democratic")]
    if len(comparison) == 1:
        return comparison.iloc[0], "not_required_one_non_democratic_candidate"
    if comparison.empty:
        raise TargetValidationError("race has no non-Democratic comparison candidate")
    if reviewed_candidate_id is None:
        names = comparison[["candidate_id", "candidate_name", "party"]].to_dict(
            "records"
        )
        raise TargetReviewRequired(
            "race has several non-Democratic candidates; explicit review is "
            f"required: {names}"
        )
    selected = comparison[comparison["candidate_id"].eq(reviewed_candidate_id)]
    if len(selected) != 1:
        raise TargetValidationError(
            f"reviewed comparison candidate is not unique: {reviewed_candidate_id}"
        )
    return selected.iloc[0], "explicit_pre_election_review"


def rollup_target_pvi(
    precinct_pvi: pd.DataFrame,
    precinct_district: pd.DataFrame,
    national_baseline: pd.DataFrame,
    pvi_year: int = 2024,
    redistricting_cycle: int = 2021,
) -> pd.DataFrame:
    """Recompute district PVI and coverage from published precinct inputs."""
    pvi = precinct_pvi[
        precinct_pvi["pvi_year"].eq(pvi_year)
        & precinct_pvi["redistricting_cycle"].eq(redistricting_cycle)
    ]
    mapping = precinct_district[
        precinct_district["redistricting_cycle"].eq(redistricting_cycle)
    ]
    key = ["redistricting_cycle", *crosswalk.KEY]
    joined = mapping.merge(pvi, on=key, how="left", validate="one_to_one")
    baseline = national_baseline.set_index("election_year")
    years = sorted(pvi[["pres_year_earlier", "pres_year_later"]].stack().unique())
    dem = baseline.loc[years, "dem_votes"].sum()
    gop = baseline.loc[years, "gop_votes"].sum()
    national_share = dem / (dem + gop)
    rows = []
    for office, column in (
        ("State Representative", "state_rep"),
        ("State Senate", "state_senate"),
    ):
        for district_display, district_rows in joined.dropna(subset=[column]).groupby(
            column
        ):
            two_party = district_rows["dem_votes"].fillna(0) + district_rows[
                "gop_votes"
            ].fillna(0)
            total = two_party.sum()
            interpolated = two_party.where(
                district_rows["provenance"].eq(crosswalk.PROVENANCE_INTERPOLATED),
                0,
            ).sum()
            pvi_value = (
                (district_rows["dem_votes"].sum() / total - national_share) * 100
                if total > 0
                else pd.NA
            )
            rows.append(
                {
                    "office": office,
                    "district_key": normalize_district(district_display),
                    "PVI_N": pvi_value,
                    "pvi_year": pvi_year,
                    "redistricting_cycle": redistricting_cycle,
                    "pvi_coverage": float(two_party.gt(0).mean()),
                    "pvi_interpolated_share": (
                        float(interpolated / total) if total > 0 else pd.NA
                    ),
                    "pvi_provenance": (
                        "2024_precinct_rollup_with_interpolation"
                        if interpolated > 0
                        else "2024_precinct_rollup_exact_only"
                    ),
                }
            )
    return pd.DataFrame(rows).sort_values(
        ["office", "district_key"], ignore_index=True
    )


def expected_target_matchups(
    candidates: pd.DataFrame,
    reviews: dict[tuple[str, str], str] | None = None,
) -> pd.DataFrame:
    """One outcome-blind matchup for every contested legislative race."""
    reviews = reviews or {}
    rows = []
    for (office, district), race in candidates.groupby(["office", "district"]):
        democrats = race[race["party"].eq("Democratic")]
        others = race[race["party"].ne("Democratic")]
        if democrats.empty or others.empty:
            continue
        if len(democrats) != 1:
            raise TargetReviewRequired(
                f"race has {len(democrats)} Democratic nominees: {office} {district}"
            )
        comparison, review_status = select_comparison_candidate(
            race, reviews.get((office, district))
        )
        dem = democrats.iloc[0]
        rows.append(
            {
                "office": office,
                "district": district,
                "district_display": dem["district_display"],
                "dem_candidate_id": dem["candidate_id"],
                "dem_candidate_name": dem["candidate_name"],
                "comparison_candidate_id": comparison["candidate_id"],
                "comparison_candidate_name": comparison["candidate_name"],
                "comparison_candidate_party": comparison["party"],
                "incumbent_status": (
                    "Dem_Incumbent"
                    if dem["is_incumbent"]
                    else "GOP_Incumbent"
                    if comparison["is_incumbent"]
                    else "No_Incumbent"
                ),
                "comparison_rule": "primary_nominee_then_pre_election_review",
                "comparison_review_status": review_status,
                "dem_nominee_basis": dem["nominee_basis"],
                "dem_nominee_review_status": dem["nominee_review_status"],
                "comparison_nominee_basis": comparison["nominee_basis"],
                "comparison_nominee_review_status": comparison[
                    "nominee_review_status"
                ],
            }
        )
    return pd.DataFrame(rows).sort_values(["office", "district"], ignore_index=True)


def verify_target_sources(
    target: pd.DataFrame,
    candidates: pd.DataFrame,
    district_pvi: pd.DataFrame,
    tolerance: float = 1e-10,
) -> None:
    """Verify target coverage, locked candidates, and recomputed district PVI."""
    target = validate_target(target)
    expected = expected_target_matchups(candidates)
    key = ["office", "district"]
    identity = [
        "dem_candidate_id",
        "dem_candidate_name",
        "comparison_candidate_id",
        "comparison_candidate_name",
        "comparison_candidate_party",
    ]
    matched = target.merge(
        expected[key + identity], on=key, how="outer", suffixes=("", "_expected"), indicator=True
    )
    if not matched["_merge"].eq("both").all():
        missing = matched.loc[matched["_merge"].ne("both"), key + ["_merge"]]
        raise TargetValidationError(
            "forecast target does not cover the authoritative candidate roster: "
            f"{missing.to_dict('records')}"
        )
    disagreements = []
    for column in identity:
        bad = matched[column].astype(str).ne(matched[f"{column}_expected"].astype(str))
        disagreements.extend(
            matched.loc[bad, key].assign(column=column).to_dict("records")
        )
    if disagreements:
        raise TargetValidationError(
            f"forecast target candidate matchup disagrees with source: {disagreements}"
        )
    with_key = target.assign(
        district_key=target["district"].map(normalize_district)
    ).merge(district_pvi, on=["office", "district_key"], suffixes=("", "_expected"))
    if len(with_key) != len(target):
        raise TargetValidationError("forecast target has a district without recomputable PVI")
    numeric = ["PVI_N", "pvi_coverage", "pvi_interpolated_share"]
    for column in numeric:
        difference = (with_key[column] - with_key[f"{column}_expected"]).abs()
        if difference.gt(tolerance).any():
            races = with_key.loc[difference.gt(tolerance), key].to_dict("records")
            raise TargetValidationError(
                f"forecast target {column} disagrees with precinct rollup: {races}"
            )


def validate_target(target: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize a response-free legislative forecast target."""
    leaking = [
        column
        for column in target.columns
        if any(part in column.lower() for part in RESULT_COLUMN_PARTS)
    ]
    if leaking:
        raise TargetValidationError(
            "forecast target contains result-bearing column(s): "
            + ", ".join(sorted(leaking))
        )
    missing = [column for column in TARGET_REQUIRED if column not in target.columns]
    if missing:
        raise TargetValidationError(
            "forecast target is missing required column(s): "
            + ", ".join(missing)
        )
    duplicate = target.duplicated(TARGET_KEY, keep=False)
    if duplicate.any():
        keys = target.loc[duplicate, TARGET_KEY].drop_duplicates().to_dict("records")
        raise TargetValidationError(f"forecast target has duplicate key(s): {keys}")
    unsupported = sorted(set(target["office"].dropna()) - TARGET_OFFICES)
    if unsupported:
        raise TargetValidationError(
            f"forecast target has unsupported office(s): {unsupported}"
        )
    provenance = [
        "candidate_source",
        "candidate_source_digest",
        "pvi_source",
        "pvi_source_digest",
        "pvi_provenance",
        "comparison_rule",
        "comparison_review_status",
    ]
    absent_provenance = [
        column
        for column in provenance
        if target[column].isna().any()
        or target[column].astype(str).str.strip().eq("").any()
    ]
    if absent_provenance:
        raise TargetValidationError(
            "forecast target has missing provenance in: "
            + ", ".join(absent_provenance)
        )
    expected = pd.Series(
        [target_id(*row) for row in target[TARGET_KEY].itertuples(index=False, name=None)],
        index=target.index,
    )
    mismatched = target["target_id"].astype(str) != expected
    if mismatched.any():
        raise TargetValidationError(
            "forecast target_id does not match election date, office, and district"
        )
    return target.sort_values(TARGET_KEY, ignore_index=True)


def load_target(path=config.FORECAST_2026_TARGET) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"forecast target is missing: {path}")
    return validate_target(pd.read_csv(path))
