import numpy as np
import pandas as pd

from legmodel import metrics, score


def test_brier_score_uses_posterior_democratic_win_probability():
    draws = np.array(
        [
            [1.0, -1.0],
            [2.0, 1.0],
            [-1.0, 2.0],
            [3.0, 4.0],
        ]
    )
    per_race = metrics.per_race(draws, np.array([1.0, -1.0]))

    np.testing.assert_allclose(per_race["win_probability"], [0.75, 0.75])
    np.testing.assert_allclose(per_race["brier_score"], [0.0625, 0.5625])
    assert metrics.aggregate(per_race)["brier_score"] == 0.3125


def scoring_predictions():
    draws = np.array(
        [
            [-2.0, 1.0, 1.0],
            [-1.0, 2.0, 2.0],
            [-3.0, -1.0, 3.0],
            [-4.0, -2.0, 4.0],
            [-5.0, -3.0, 5.0],
        ]
    )
    frame = metrics.per_race(draws, np.array([-1.0, 1.0, 1.0]))
    identity = pd.DataFrame(
        {
            "definition": ["d"] * 3,
            "variant": ["v"] * 3,
            "fold": ["2024-11-05", "2024-11-05", "2023-01-01"],
            "election_id": ["a", "b", "c"],
            "office": ["State Representative", "State Senate", "State Senate"],
            "is_special": [False, False, True],
            "pres_elec": [True, True, False],
            "ballot_timing": ["presidential", "presidential", "special"],
            "redistricting_cycle": ["2021", "2021", "2021"],
            "no_dem_candidate": [False, False, False],
            "admitted_by_write_in": [False, False, False],
            "incumbent_status": [
                "Dem_Incumbent",
                "GOP_Incumbent",
                "No_Incumbent",
            ],
            "component": ["money", "fallback", "fallback"],
        }
    )
    return pd.concat([identity, frame], axis=1)


def test_calibration_keeps_fixed_empty_and_small_bins():
    calibration = score.probability_calibration(scoring_predictions())

    assert len(calibration) == 10
    assert calibration["n_races"].sum() == 3
    empty = calibration[calibration["n_races"] == 0]
    assert len(empty) > 0
    assert empty["mean_forecast"].isna().all()
    assert empty["observed_frequency"].isna().all()
    assert calibration["small_sample"].all()


def test_operational_segments_use_general_folds_components_and_probabilities():
    predictions = scoring_predictions()
    diagnostics = pd.DataFrame()
    card = score.scorecard(
        predictions,
        diagnostics,
        skipped=[],
        eligible=["2023-01-01", "2024-11-05"],
    )

    rows = card.set_index(["segment_type", "segment_value"])
    assert rows.loc[("general_election", "all"), "n_races"] == 2
    assert rows.loc[("latest_general_fold", "2024-11-05"), "n_races"] == 2
    assert rows.loc[("finance_component", "money"), "n_races"] == 1
    assert rows.loc[("finance_component", "fallback"), "n_races"] == 2
    assert rows.loc[("cross_fitted_probability_band", "0.0-0.2"), "n_races"] == 1
    assert rows.loc[("cross_fitted_probability_band", "0.2-0.4"), "n_races"] == 1
    assert rows.loc[("cross_fitted_probability_band", "0.8-1.0"), "n_races"] == 1

    changed = predictions.copy()
    changed["observed"] = -changed["observed"]
    changed["dem_win_observed"] = ~changed["dem_win_observed"]
    changed_card = score.scorecard(
        changed,
        diagnostics,
        skipped=[],
        eligible=["2023-01-01", "2024-11-05"],
    )
    original_counts = card[card["segment_type"] == "cross_fitted_probability_band"][
        ["segment_value", "n_races"]
    ].reset_index(drop=True)
    changed_counts = changed_card[
        changed_card["segment_type"] == "cross_fitted_probability_band"
    ][["segment_value", "n_races"]].reset_index(drop=True)
    pd.testing.assert_frame_equal(original_counts, changed_counts)
