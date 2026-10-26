import pandas as pd
import pytest

from legmodel import config, forecast
from maprecinct import training
from maprecinct.ocpf import normalize_district


def valid_target():
    row = {
        "election_date": "2026-11-03",
        "office": "State Representative",
        "district": "Fifth Essex",
        "district_display": "5th Essex",
        "dem_candidate_id": "d1",
        "dem_candidate_name": "Dem Candidate",
        "dem_candidate_municipality": "Example",
        "dem_candidate_incumbent": False,
        "comparison_candidate_id": "r1",
        "comparison_candidate_name": "Other Candidate",
        "comparison_candidate_party": "Republican",
        "comparison_candidate_municipality": "Example",
        "comparison_candidate_incumbent": False,
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


def test_missing_candidate_municipality_is_refused():
    target = valid_target()
    target["comparison_candidate_municipality"] = ""
    with pytest.raises(forecast.TargetValidationError, match="municipality"):
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
                "municipality": "Example",
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
                "municipality": "Example",
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
                "municipality": "Example",
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
    assert matchups.loc[0, "dem_candidate_municipality"] == "Example"
    assert matchups.loc[0, "comparison_candidate_municipality"] == "Example"
    assert (
        matchups.loc[0, "comparison_nominee_basis"]
        == "final_primary_write_in_nominee"
    )
    assert matchups.loc[0, "incumbent_status"] == "Dem_Incumbent"


def supplement_row(**overrides):
    row = {
        "office": "State Representative",
        "district": "Tenth Bristol",
        "district_display": "10th Bristol",
        "party": "Unenrolled",
        "name": "Una Enrolled",
        "municipality": "Example",
        "is_incumbent": False,
        "source_url": "https://www.sec.state.ma.us/example.htm",
        "source_as_of": "2026-10-26",
    }
    row.update(overrides)
    return row


def test_supplement_candidate_joins_primary_nominees():
    roster, results = primary_sources()
    primary = forecast.build_target_candidates(roster, results)
    supplement = forecast.build_supplement_candidates(
        pd.DataFrame([supplement_row()]), primary
    )

    assert supplement.loc[0, "nominee_basis"] == "nomination_paper"
    assert (
        supplement.loc[0, "nominee_review_status"]
        == "confirmed_secretary_general_candidate_list"
    )
    assert supplement.loc[0, "candidate_id"] == forecast.source_candidate_id(
        "2026-11-03", "State Representative", "Tenth Bristol", "Unenrolled", "Una Enrolled"
    )
    assert list(supplement.columns) == list(primary.columns)


@pytest.mark.parametrize(
    "column", ["district", "name", "party", "municipality", "source_as_of"]
)
def test_supplement_row_missing_field_is_refused(column):
    roster, results = primary_sources()
    primary = forecast.build_target_candidates(roster, results)
    with pytest.raises(forecast.TargetValidationError, match=column):
        forecast.build_supplement_candidates(
            pd.DataFrame([supplement_row(**{column: ""})]), primary
        )


def test_supplement_row_duplicating_primary_nominee_is_refused():
    roster, results = primary_sources()
    primary = forecast.build_target_candidates(roster, results)
    row = supplement_row(name="Mark Sylvia", party="Democratic")
    with pytest.raises(forecast.TargetValidationError, match="primary nominee"):
        forecast.build_supplement_candidates(pd.DataFrame([row]), primary)


def test_supplement_candidate_without_democrat_creates_no_matchup():
    roster, results = primary_sources()
    primary = forecast.build_target_candidates(roster, results)
    row = supplement_row(district="Second Franklin", district_display="2nd Franklin")
    supplement = forecast.build_supplement_candidates(pd.DataFrame([row]), primary)
    matchups = forecast.expected_target_matchups(
        pd.concat([primary, supplement], ignore_index=True)
    )

    assert matchups["district"].tolist() == ["Tenth Bristol"]


def race(*parties):
    return pd.DataFrame(
        [
            {
                "candidate_id": f"c{i}",
                "candidate_name": f"Candidate {i}",
                "party": party,
            }
            for i, party in enumerate(parties)
        ]
    )


def test_republican_is_chosen_over_third_candidate_without_review():
    selected, status = forecast.select_comparison_candidate(
        race("Democratic", "Republican", "Unenrolled")
    )

    assert selected["party"] == "Republican"
    assert status == "not_required_republican_present"


def test_sole_non_republican_opponent_is_chosen_without_review():
    selected, status = forecast.select_comparison_candidate(
        race("Democratic", "Workers Party")
    )

    assert selected["party"] == "Workers Party"
    assert status == "not_required_one_non_democratic_candidate"


def test_several_non_republican_opponents_require_review_and_ignore_vote_order():
    candidates = race("Democratic", "Unenrolled", "Independent")
    with pytest.raises(forecast.TargetReviewRequired, match="explicit review"):
        forecast.select_comparison_candidate(candidates)

    candidates["eventual_votes"] = [100, 20, 80]
    selected, status = forecast.select_comparison_candidate(candidates, "c1")
    candidates["eventual_votes"] = [100, 90, 10]
    reordered, _ = forecast.select_comparison_candidate(candidates, "c1")
    assert selected["candidate_id"] == reordered["candidate_id"] == "c1"
    assert status == "explicit_pre_election_review"


def test_non_democratic_incumbent_opponent_is_coded_gop_incumbent():
    roster, results = primary_sources()
    primary = forecast.build_target_candidates(roster, results)
    primary = primary[primary["party"].eq("Democratic")].assign(is_incumbent=False)
    supplement = forecast.build_supplement_candidates(
        pd.DataFrame([supplement_row(party="Independent", is_incumbent=True)]), primary
    )
    matchups = forecast.expected_target_matchups(
        pd.concat([primary, supplement], ignore_index=True)
    )

    assert matchups.loc[0, "comparison_candidate_party"] == "Independent"
    assert matchups.loc[0, "incumbent_status"] == "GOP_Incumbent"
    assert training.incumbent_status("Independent") == "GOP_Incumbent"


def verifiable_target():
    roster, results = primary_sources()
    candidates = forecast.build_target_candidates(roster, results)
    matchups = forecast.expected_target_matchups(candidates)
    pvi = pd.DataFrame(
        [
            {
                "office": "State Representative",
                "district_key": normalize_district("Tenth Bristol"),
                "PVI_N": 1.0,
                "pvi_coverage": 1.0,
                "pvi_interpolated_share": 0.0,
            }
        ]
    )
    base = valid_target().drop(
        columns=[column for column in matchups.columns if column != "office"]
        + ["target_id"],
        errors="ignore",
    )
    target = matchups.merge(base, on="office").assign(
        election_date="2026-11-03", PVI_N=1.0, pvi_interpolated_share=0.0
    )
    target["target_id"] = [
        forecast.target_id(*row)
        for row in target[forecast.TARGET_KEY].itertuples(index=False, name=None)
    ]
    return target, candidates, pvi


def test_matching_target_passes_source_verification():
    target, candidates, pvi = verifiable_target()
    forecast.verify_target_sources(target, candidates, pvi)


def test_stale_comparison_rule_fails_source_verification():
    target, candidates, pvi = verifiable_target()
    target["comparison_rule"] = "republican_nominee_from_2026_primary"
    with pytest.raises(forecast.TargetValidationError, match="comparison_rule"):
        forecast.verify_target_sources(target, candidates, pvi)


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


REVISION_ADDED_DISTRICTS = {
    ("State Representative", "First Barnstable"),
    ("State Representative", "Second Bristol"),
    ("State Representative", "First Franklin"),
    ("State Representative", "Fifth Hampden"),
    ("State Representative", "Fifth Norfolk"),
    ("State Representative", "Fourth Suffolk"),
    ("State Representative", "Tenth Suffolk"),
    ("State Representative", "Second Worcester"),
    ("State Senate", "Norfolk and Plymouth"),
    ("State Senate", "Suffolk and Middlesex"),
    ("State Senate", "Worcester and Middlesex"),
}
# Columns the revision is expected to restate for the 46 original races: the
# candidate provenance and comparison-rule naming changed, and 14-day finance
# was collected after the original target was written.
REVISION_RESTATED = {
    "candidate_source",
    "candidate_source_digest",
    "candidate_data_as_of",
    "comparison_rule",
    "comparison_review_status",
    "money_complete_14d",
}
PVI_COLUMNS = ["PVI_N", "pvi_coverage", "pvi_interpolated_share"]


def test_revised_target_keeps_original_races_and_adds_nomination_paper_races():
    original = forecast.load_target(config.forecast_revision("14d").target)
    revised = forecast.load_target(config.forecast_revision("14d-r2").target)
    added = revised[~revised["target_id"].isin(original["target_id"])]

    assert set(original["target_id"]) <= set(revised["target_id"])
    assert set(zip(added["office"], added["district"], strict=True)) == (
        REVISION_ADDED_DISTRICTS
    )
    assert added["comparison_candidate_party"].ne("Republican").all()
    assert added["comparison_nominee_basis"].eq("nomination_paper").all()
    assert revised.groupby("office").size().to_dict() == {
        "State Representative": 47,
        "State Senate": 10,
    }

    kept = original.merge(revised, on="target_id", suffixes=("", "_revised"))
    for column in original.columns:
        if column in REVISION_RESTATED or column == "target_id":
            continue
        if column in PVI_COLUMNS:
            difference = (kept[column] - kept[f"{column}_revised"]).abs()
            assert difference.max() < 1e-10, column
        else:
            assert kept[column].astype(str).eq(
                kept[f"{column}_revised"].astype(str)
            ).all(), column
    assert kept["comparison_rule_revised"].eq(forecast.COMPARISON_RULE).all()


def test_supplement_district_missing_from_district_map_is_refused():
    district_pvi = pd.DataFrame(
        [{"office": "State Representative", "district_key": "10th bristol"}]
    )
    good = pd.DataFrame([supplement_row()])
    forecast.check_supplement_districts(good, district_pvi)

    typo = pd.DataFrame([supplement_row(district="Tenth Bristoll")])
    with pytest.raises(forecast.TargetValidationError, match="unknown district"):
        forecast.check_supplement_districts(typo, district_pvi)
