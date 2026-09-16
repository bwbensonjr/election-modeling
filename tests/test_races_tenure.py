from __future__ import annotations

import pandas as pd
import pytest

from maprecinct import races


def precinct_rows(tenures=(3.5, 3.5)) -> pd.DataFrame:
    values = {
        "election_date": "2022-11-08",
        "election_year": 2022,
        "redistricting_cycle": 2021,
        "office": "State Representative",
        "district": "First Example",
        "district_display": "1st Example",
        "incumbent_status": "Dem_Incumbent",
        "incumbent_tenure_left_censored": False,
        "pres_elec": False,
        "is_special": False,
        "num_candidates": 2,
        "no_dem_candidate": False,
        "dem_candidate": "A Democrat",
        "opponent_candidate": "A Republican",
        "opponent_party": "Republican",
        "dem_candidate_count": 1,
        "major_party_race": True,
        "contested_on_ballot_lines": True,
        "admitted_by_write_in": False,
        "num_candidates_admitted": 2,
        "write_in_share": 0.0,
        "top_write_in_share": 0.0,
        "pvi_year": 2020,
    }
    return pd.DataFrame(
        [
            {
                "election_id": 1,
                **values,
                "incumbent_tenure_years": tenure,
            }
            for tenure in tenures
        ]
    )


def test_race_rollup_carries_tenure():
    result = races.carry_attributes(precinct_rows())
    assert result.loc[0, "incumbent_tenure_years"] == 3.5
    assert not result.loc[0, "incumbent_tenure_left_censored"]


def test_race_rollup_rejects_tenure_disagreement():
    with pytest.raises(races.InconsistentRaceError, match="incumbent_tenure_years"):
        races.carry_attributes(precinct_rows((3.5, 4.0)))
