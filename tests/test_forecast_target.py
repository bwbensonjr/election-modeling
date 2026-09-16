import pandas as pd
import pytest

from legmodel import forecast
from maprecinct.ocpf import normalize_district


def valid_target():
    row = {
        "election_date": "2026-11-03",
        "office": "State Representative",
        "district": "Fifth Essex",
        "district_display": "5th Essex",
        "dem_candidate_id": "d1",
        "dem_candidate_name": "Dem Candidate",
        "comparison_candidate_id": "r1",
        "comparison_candidate_name": "Other Candidate",
        "comparison_candidate_party": "Republican",
        "incumbent_status": "No_Incumbent",
        "PVI_N": 5.0,
        "pvi_year": 2024,
        "redistricting_cycle": 2021,
        "pvi_coverage": 1.0,
        "pvi_provenance": "published precinct rollup",
        "ballot_timing": "midterm_dem_pres",
        "money_complete_60d": False,
        "money_complete_14d": False,
        "candidate_source": "ma-election-db general candidates",
        "candidate_source_digest": "abc",
        "candidate_data_as_of": "2026-09-15",
        "pvi_source": "ma_precinct_pvi.csv.gz",
        "pvi_source_digest": "def",
        "comparison_rule": "republican_then_pre_election_review",
        "comparison_review_status": "not_required",
        "dem_nominee_basis": "uncontested_primary",
        "dem_nominee_review_status": "not_required_uncontested_primary",
        "comparison_nominee_basis": "uncontested_primary",
        "comparison_nominee_review_status": "not_required_uncontested_primary",
    }
    row["target_id"] = forecast.target_id(
        row["election_date"], row["office"], row["district"]
    )
    return pd.DataFrame([row])


def test_valid_response_free_target_passes():
    actual = forecast.validate_target(valid_target())
    assert actual["target_id"].is_unique


def test_duplicate_target_key_is_refused():
    target = pd.concat([valid_target(), valid_target()], ignore_index=True)
    with pytest.raises(forecast.TargetValidationError, match="duplicate"):
        forecast.validate_target(target)


def test_unsupported_office_is_refused():
    target = valid_target()
    target["office"] = "Governor"
    with pytest.raises(forecast.TargetValidationError, match="unsupported office"):
        forecast.validate_target(target)


def test_missing_provenance_is_refused():
    target = valid_target()
    target["candidate_source_digest"] = ""
    with pytest.raises(forecast.TargetValidationError, match="missing provenance"):
        forecast.validate_target(target)


@pytest.mark.parametrize(
    "column", ["num_votes", "is_winner", "dem_margin", "certified_result"]
)
def test_any_result_bearing_column_is_refused(column):
    target = valid_target()
    target[column] = 0
    with pytest.raises(forecast.TargetValidationError, match=column):
        forecast.validate_target(target)


def primary_sources():
    roster = pd.DataFrame(
        [
            {
                "election_date": "2026-09-01",
                "office": "State Representative",
                "district": "Tenth Bristol",
                "district_display": "10th Bristol",
                "party": "Democratic",
                "name": "Mark D. Sylvia",
                "is_incumbent": 1,
            }
        ]
    )
    results = pd.DataFrame(
        [
            {
                "election_date": "2026-09-01",
                "office": "State Representative",
                "district": "Tenth Bristol",
                "district_display": "10th Bristol",
                "party": "Democratic",
                "name": "Mark D. Sylvia",
                "candidate_id": 1,
                "num_candidates": 1,
                "is_winner": True,
                "is_write_in": False,
            },
            {
                "election_date": "2026-09-01",
                "office": "State Representative",
                "district": "Tenth Bristol",
                "district_display": "10th Bristol",
                "party": "Republican",
                "name": "Brendalee A. Smith",
                "candidate_id": 2,
                "num_candidates": 1,
                "is_winner": True,
                "is_write_in": True,
            },
        ]
    )
    return roster, results


def test_primary_builder_retains_result_only_write_in_nominee_without_general_result():
    roster, results = primary_sources()
    candidates = forecast.build_target_candidates(roster, results)
    matchups = forecast.expected_target_matchups(candidates)

    assert len(matchups) == 1
    assert matchups.loc[0, "comparison_candidate_name"] == "Brendalee A. Smith"
    assert (
        matchups.loc[0, "comparison_nominee_basis"]
        == "final_primary_write_in_nominee"
    )
    assert matchups.loc[0, "incumbent_status"] == "Dem_Incumbent"


def test_comparison_selection_requires_review_and_ignores_eventual_vote_order():
    candidates = pd.DataFrame(
        [
            {"candidate_id": "d", "candidate_name": "D", "party": "Democratic"},
            {"candidate_id": "r", "candidate_name": "R", "party": "Republican"},
            {"candidate_id": "u", "candidate_name": "U", "party": "Unenrolled"},
        ]
    )
    with pytest.raises(forecast.TargetReviewRequired, match="explicit review"):
        forecast.select_comparison_candidate(candidates)

    candidates["eventual_votes"] = [100, 20, 80]
    selected, status = forecast.select_comparison_candidate(candidates, "r")
    candidates["eventual_votes"] = [100, 90, 10]
    reordered, _ = forecast.select_comparison_candidate(candidates, "r")
    assert selected["candidate_id"] == reordered["candidate_id"] == "r"
    assert status == "explicit_pre_election_review"


def test_target_pvi_recomputes_from_precinct_votes_and_tracks_interpolation():
    precinct_pvi = pd.DataFrame(
        [
            {
                "pvi_year": 2024,
                "redistricting_cycle": 2021,
                "pres_year_earlier": 2020,
                "pres_year_later": 2024,
                "city_town": "Example",
                "ward": "-",
                "precinct": "1",
                "dem_votes": 60,
                "gop_votes": 40,
                "provenance": "exact_identifier",
            },
            {
                "pvi_year": 2024,
                "redistricting_cycle": 2021,
                "pres_year_earlier": 2020,
                "pres_year_later": 2024,
                "city_town": "Example",
                "ward": "-",
                "precinct": "2",
                "dem_votes": 20,
                "gop_votes": 30,
                "provenance": "areal_interpolation",
            },
        ]
    )
    mapping = pd.DataFrame(
        [
            {
                "redistricting_cycle": 2021,
                "city_town": "Example",
                "ward": "-",
                "precinct": "1",
                "state_rep": "10th Bristol",
                "state_senate": "First Example",
            },
            {
                "redistricting_cycle": 2021,
                "city_town": "Example",
                "ward": "-",
                "precinct": "2",
                "state_rep": "10th Bristol",
                "state_senate": "First Example",
            },
        ]
    )
    baseline = pd.DataFrame(
        [
            {"election_year": 2020, "dem_votes": 50, "gop_votes": 50},
            {"election_year": 2024, "dem_votes": 50, "gop_votes": 50},
        ]
    )

    actual = forecast.rollup_target_pvi(precinct_pvi, mapping, baseline)
    house = actual[actual["office"].eq("State Representative")].iloc[0]
    assert house["PVI_N"] == pytest.approx((80 / 150 - 0.5) * 100)
    assert house["pvi_coverage"] == 1.0
    assert house["pvi_interpolated_share"] == pytest.approx(50 / 150)
    assert house["pvi_provenance"] == "2024_precinct_rollup_with_interpolation"


def test_compound_word_ordinal_uses_numeric_district_key():
    assert normalize_district("Thirty-Fifth Middlesex") == "35th middlesex"
    assert normalize_district("Twenty-Second Middlesex") == "22nd middlesex"
