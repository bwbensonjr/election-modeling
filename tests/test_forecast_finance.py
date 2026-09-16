import pandas as pd
import pytest

from legmodel import forecast, forecast_finance
from maprecinct import ocpf


def target(candidate="Jane Smith"):
    row = {
        "election_date": "2026-11-03",
        "office": "State Representative",
        "district": "Tenth Bristol",
        "district_display": "10th Bristol",
        "dem_candidate_id": "d1",
        "dem_candidate_name": candidate,
        "comparison_candidate_id": "r1",
        "comparison_candidate_name": "Robert Jones",
        "comparison_candidate_party": "Republican",
        "incumbent_status": "Dem_Incumbent",
        "PVI_N": 2.0,
        "pvi_year": 2024,
        "redistricting_cycle": 2021,
        "pvi_coverage": 1.0,
        "pvi_provenance": "exact",
        "ballot_timing": "midterm_gop_pres",
        "money_complete_60d": False,
        "money_complete_14d": False,
        "candidate_source": "primary roster",
        "candidate_source_digest": "abc",
        "candidate_data_as_of": "2026-09-14",
        "pvi_source": "precinct PVI",
        "pvi_source_digest": "def",
        "comparison_rule": "primary nominee",
        "comparison_review_status": "not required",
        "dem_nominee_basis": "primary",
        "dem_nominee_review_status": "not required",
        "comparison_nominee_basis": "primary",
        "comparison_nominee_review_status": "not required",
    }
    row["target_id"] = forecast.target_id(
        row["election_date"], row["office"], row["district"]
    )
    return pd.DataFrame([row])


def test_target_resolution_uses_shared_match_rules_without_results():
    roster = [
        {"cpf_id": 10, "filer_name": "Smith, Jane", "roster_source": "fixture"},
        {"cpf_id": 20, "filer_name": "Jones, Robert", "roster_source": "fixture"},
    ]

    resolved = forecast_finance.resolve(
        target(), roster_provider=lambda *_: roster, district_index={}
    )

    assert resolved["cpf_id"].tolist() == [10, 20]
    assert set(resolved["match_rule"]) == {"surname"}
    assert not any("vote" in column or "winner" in column for column in resolved)


def test_target_resolution_preserves_ambiguous_and_unmatched_cases():
    ambiguous_roster = [
        {"cpf_id": 10, "filer_name": "Smith, Joan"},
        {"cpf_id": 11, "filer_name": "Smith, John"},
    ]
    ambiguous = forecast_finance.resolve(
        target("J. Smith"),
        roster_provider=lambda *_: ambiguous_roster,
        district_index={},
    )
    assert ambiguous.loc[ambiguous["role"].eq("dem"), "match_rule"].iloc[0] == (
        "ambiguous"
    )

    unmatched = forecast_finance.resolve(
        target(), roster_provider=lambda *_: [], district_index={}
    )
    assert set(unmatched["match_rule"]) == {"unmatched"}


def test_60_day_collection_excludes_transactions_after_cutoff():
    resolved = forecast_finance.resolve(
        target(),
        roster_provider=lambda *_: [
            {"cpf_id": 10, "filer_name": "Smith, Jane"},
            {"cpf_id": 20, "filer_name": "Jones, Robert"},
        ],
        district_index={},
    )
    transactions = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-09-04", "2026-09-05"]),
            "amount": [10.0, 90.0],
        }
    )

    def total(cpf_id, start, end, category):
        included = transactions[
            transactions["date"].between(pd.Timestamp(start), pd.Timestamp(end))
        ]
        return ocpf.DatedTotal(
            count=len(included),
            total=float(included["amount"].sum()),
            start=str(start),
            end=str(end),
            category=category,
        )

    collected = forecast_finance.collect(resolved, "60d", total_provider=total)
    assert set(collected["cutoff"]) == {"2026-09-04"}
    assert set(collected["receipts"]) == {10.0}
    assert collected["race_complete"].all()


def test_create_once_finance_snapshot_verifies_and_refuses_change(tmp_path):
    path = tmp_path / "finance_60d.csv"
    original = pd.DataFrame([{"candidate": "A", "receipts": 10.0}])
    assert forecast_finance.publish_create_once(original, path) == "created"
    assert forecast_finance.publish_create_once(original, path) == "verified"
    with pytest.raises(forecast_finance.ForecastFinanceError, match="overwrite"):
        forecast_finance.publish_create_once(
            pd.DataFrame([{"candidate": "A", "receipts": 11.0}]), path
        )


def test_finance_dry_run_summary_names_target_cutoff_and_review_count():
    resolved = forecast_finance.resolve(
        target(), roster_provider=lambda *_: [], district_index={}
    )
    actual = forecast_finance.summary(resolved, "60d")
    assert actual == {
        "horizon": "60d",
        "cutoff": "2026-09-04",
        "candidates": 2,
        "matched_candidates": 0,
        "unresolved_review_count": 2,
    }
