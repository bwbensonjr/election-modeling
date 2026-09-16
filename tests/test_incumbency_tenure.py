from __future__ import annotations

import pandas as pd
import pytest

from maprecinct.incumbency import IncumbentTenureError, derive_incumbent_tenure


def candidate(
    election_id: int,
    election_date: str,
    district_id: int,
    *,
    candidate_id: int = 7,
    is_winner: bool = True,
    is_incumbent: bool = False,
    district_id_prev=None,
    is_first_cycle: bool = False,
    first_cycle_date=None,
    party: str = "Democratic",
) -> dict:
    return {
        "election_id": election_id,
        "election_date": election_date,
        "office_id": 8,
        "district_id": district_id,
        "candidate_id": candidate_id,
        "is_winner": is_winner,
        "is_incumbent": is_incumbent,
        "district_id_prev": district_id_prev,
        "is_first_cycle": is_first_cycle,
        "first_cycle_date": first_cycle_date,
        "party": party,
    }


def summary(
    election_id: int,
    *,
    incumbent_id=7,
    party="Democratic",
    num_incumbents: int = 1,
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "election_id": [election_id],
            "id_incumbent": [incumbent_id],
            "party_incumbent": [party],
            "num_incumbents": [num_incumbents],
        }
    )


def tenure(rows: list[dict], current_id: int) -> pd.Series:
    result = derive_incumbent_tenure(summary(current_id), pd.DataFrame(rows))
    return result.iloc[0]


def test_regular_reelection_measures_from_first_uninterrupted_win():
    result = tenure(
        [
            candidate(1, "2018-11-06", 10),
            candidate(2, "2020-11-03", 10, is_incumbent=True, district_id_prev=10),
            candidate(3, "2022-11-08", 10, is_incumbent=True, district_id_prev=10),
        ],
        3,
    )
    assert result["incumbent_tenure_years"] == pytest.approx(4.0056, abs=0.001)
    assert not result["incumbent_tenure_left_censored"]


def test_current_outcome_does_not_change_tenure():
    rows = [
        candidate(1, "2020-11-03", 10),
        candidate(
            2,
            "2022-11-08",
            10,
            is_winner=False,
            is_incumbent=True,
            district_id_prev=10,
        ),
    ]
    result = tenure(rows, 2)
    assert result["incumbent_tenure_years"] == pytest.approx(2.0124, abs=0.001)


def test_special_election_starts_partial_term_tenure():
    result = tenure(
        [
            candidate(1, "2021-11-30", 10),
            candidate(2, "2022-11-08", 10, is_incumbent=True, district_id_prev=10),
        ],
        2,
    )
    assert result["incumbent_tenure_years"] == pytest.approx(0.9391, abs=0.001)


def test_career_gap_resets_tenure_at_nonincumbent_victory():
    result = tenure(
        [
            candidate(1, "2012-11-06", 10),
            candidate(2, "2020-11-03", 10),
            candidate(3, "2022-11-08", 10, is_incumbent=True, district_id_prev=10),
        ],
        3,
    )
    assert result["incumbent_tenure_years"] == pytest.approx(2.0124, abs=0.001)


def test_redistricting_follows_predecessor_district():
    result = tenure(
        [
            candidate(1, "2018-11-06", 10),
            candidate(2, "2020-11-03", 10, is_incumbent=True, district_id_prev=10),
            candidate(3, "2022-11-08", 20, is_incumbent=True, district_id_prev=10),
        ],
        3,
    )
    assert result["incumbent_tenure_years"] == pytest.approx(4.0056, abs=0.001)


def test_open_seat_has_zero_uncensored_tenure():
    summaries = summary(2, incumbent_id=pd.NA, party=pd.NA, num_incumbents=0)
    rows = [candidate(2, "2022-11-08", 10, candidate_id=8, is_winner=False)]
    result = derive_incumbent_tenure(summaries, pd.DataFrame(rows)).iloc[0]
    assert result["incumbent_tenure_years"] == 0.0
    assert not result["incumbent_tenure_left_censored"]


def test_first_cycle_chain_is_left_censored():
    result = tenure(
        [
            candidate(1, "1990-11-06", 10, is_first_cycle=True),
            candidate(2, "1992-11-03", 10, is_incumbent=True, district_id_prev=10),
        ],
        2,
    )
    assert result["incumbent_tenure_left_censored"]


def test_filtered_first_cycle_predecessor_is_left_censored():
    result = tenure(
        [
            candidate(
                1,
                "1992-11-03",
                10,
                is_incumbent=True,
                district_id_prev=10,
                first_cycle_date="1990-11-06",
            ),
            candidate(2, "1994-11-08", 10, is_incumbent=True, district_id_prev=10),
        ],
        2,
    )
    assert result["incumbent_tenure_left_censored"]
    assert result["incumbent_tenure_years"] == pytest.approx(2.0124, abs=0.001)


@pytest.mark.parametrize(
    "rows,summaries,match",
    [
        (
            [candidate(2, "2022-11-08", 10, is_incumbent=True, district_id_prev=10)],
            summary(2),
            "has no earlier victory",
        ),
        (
            [
                candidate(1, "2020-11-03", 10),
                candidate(1, "2020-11-03", 10),
                candidate(2, "2022-11-08", 10, is_incumbent=True, district_id_prev=10),
            ],
            summary(2),
            "2 victories",
        ),
        (
            [candidate(2, "2022-11-08", 10, district_id_prev=10)],
            summary(2),
            "not marked incumbent",
        ),
        (
            [candidate(2, "2022-11-08", 10, is_incumbent=True, district_id_prev=10)],
            summary(2, party="Republican"),
            "does not match summary party",
        ),
    ],
)
def test_invalid_incumbent_histories_fail_with_identity(rows, summaries, match):
    with pytest.raises(IncumbentTenureError, match=match) as excinfo:
        derive_incumbent_tenure(summaries, pd.DataFrame(rows))
    assert "election 2, candidate 7" in str(excinfo.value)
