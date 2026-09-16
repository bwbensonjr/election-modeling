import numpy as np
import pandas as pd

from legmodel import compare, compare_definitions, config, importance, score, variants


class FixedRng:
    def __init__(self, index):
        self.index = np.asarray(index, dtype=int)

    def integers(self, low, high, size):
        assert low == 0
        assert high == 2
        assert size == self.index.shape
        return self.index


def paired_fixture():
    return pd.DataFrame(
        {
            "election_id": ["a1", "a2", "b1"],
            "fold": ["2020-11-03", "2020-11-03", "2022-11-08"],
            "is_special": [False, False, False],
            "squared_error_left": [1.0, 9.0, 4.0],
            "squared_error_right": [4.0, 4.0, 1.0],
            "squared_error_difference": [-3.0, 5.0, 3.0],
        }
    )


def test_cluster_bootstrap_matches_hand_computed_race_weighted_draws(monkeypatch):
    monkeypatch.setattr(compare, "BOOTSTRAP_RESAMPLES", 3)
    rng = FixedRng([[0, 1], [0, 0], [1, 1]])

    actual = compare.bootstrap_difference(paired_fixture(), rng)

    expected = np.array(
        [
            np.sqrt(14.0 / 3.0) - np.sqrt(9.0 / 3.0),
            np.sqrt(10.0 / 2.0) - np.sqrt(8.0 / 2.0),
            np.sqrt(4.0) - np.sqrt(1.0),
        ]
    )
    np.testing.assert_allclose(actual, expected)
    assert np.isclose(
        compare.point_difference(paired_fixture()), expected[0]
    )


def test_one_cluster_interval_is_unavailable_and_undecided():
    paired = paired_fixture().iloc[:2]

    row = compare._row(
        paired,
        "left",
        "right",
        "pooled",
        "all",
        np.random.default_rng(1),
    )

    assert not row["interval_available"]
    assert np.isnan(row["ci_low"])
    assert np.isnan(row["ci_high"])
    assert row["verdict"] == "undecided"
    assert row["n_clusters"] == 1


def test_comparison_row_identifies_cluster_procedure(monkeypatch):
    monkeypatch.setattr(compare, "BOOTSTRAP_RESAMPLES", 3)
    row = compare._row(
        paired_fixture(),
        "left",
        "right",
        "pooled",
        "all",
        FixedRng([[0, 1], [0, 0], [1, 1]]),
    )

    assert row["resampling_unit"] == "election_date"
    assert row["n_clusters"] == 2
    assert row["bootstrap_resamples"] == 3
    assert row["bootstrap_seed"] == compare.BOOTSTRAP_SEED


def prediction_rows(definition, variant, ids):
    rows = []
    segments = score.SEGMENTS + [
        name for name in compare.COMPARISON_SEGMENTS if name not in score.SEGMENTS
    ]
    for election_id, fold, is_special in ids:
        row = {
            "definition": definition,
            "variant": variant,
            "election_id": election_id,
            "fold": fold,
            "squared_error": 1.0,
            "observed": 1.0,
            "prediction": 0.0,
            "is_special": is_special,
            "ballot_timing": "presidential",
        }
        for segment in segments:
            row.setdefault(segment, False)
        rows.append(row)
    return rows


def test_all_comparison_paths_preserve_their_paired_race_sets():
    common = [("shared", "2022-11-08", False)]
    predictions = pd.DataFrame(
        prediction_rows("d", "left", common + [("left_only", "2023-01-01", True)])
        + prediction_rows("d", "right", common)
        + prediction_rows("a", "model", common + [("a_only", "2023-01-01", True)])
        + prediction_rows("b", "model", common + [("b_only", "2023-02-01", True)])
    )

    variant_paired = compare.paired_frame(predictions, "left", "right", "d")
    definition_paired, only_a, only_b = compare_definitions.paired_across(
        predictions, "a", "b", "model"
    )
    full = pd.DataFrame(
        prediction_rows("d", "full", common)
    )
    arm = pd.DataFrame(prediction_rows("d", "arm", common))
    importance_paired = importance.paired_predictions(full, arm)

    assert variant_paired["election_id"].tolist() == ["shared"]
    assert definition_paired["election_id"].tolist() == ["shared"]
    assert only_a["election_id"].tolist() == ["a_only"]
    assert only_b["election_id"].tolist() == ["b_only"]
    assert importance_paired["election_id"].tolist() == ["shared"]


def test_timing_sensitivity_identifies_2018_as_sign_changing():
    predictions = pd.read_csv(config.HOLDOUT_PREDICTIONS, low_memory=False)
    paired = compare.paired_frame(
        predictions, "baseline", "baseline_timing", "two_party_or_strongest"
    )

    sensitivity = compare.leave_one_general_date_out(paired).set_index("omitted_date")

    assert bool(sensitivity.loc["2018-11-06", "sign_change"])


def test_tenure_bands_use_predeclared_boundaries():
    frame = pd.DataFrame(
        {
            "election_id": ["open", "new", "two", "four"],
            "incumbent_status": [
                "No_Incumbent",
                "Dem_Incumbent",
                "GOP_Incumbent",
                "Dem_Incumbent",
            ],
            "incumbent_tenure_years": [0.0, 1.999, 2.0, 4.0],
        }
    )
    assert compare.tenure_band(frame).tolist() == [
        "open",
        "gt0_lt2",
        "2_to_lt4",
        "ge4",
    ]


def test_empty_tenure_segment_is_reported_as_undecided():
    row = compare._row(
        paired_fixture().iloc[0:0],
        "baseline",
        "baseline_tenure_cap4",
        "incumbent_tenure_band",
        "gt0_lt2",
        np.random.default_rng(1),
    )
    assert row["n_races"] == 0
    assert not row["interval_available"]
    assert row["verdict"] == "undecided"


def test_tenure_experiment_roles_cannot_label_a_sensitivity_cap_primary():
    assert variants.TENURE_VARIANT_ROLES["baseline_tenure_cap4"] == "primary"
    for name in ("baseline_tenure_cap2", "baseline_tenure_cap6"):
        assert variants.TENURE_VARIANT_ROLES[name] == "sensitivity"


def test_tenure_pairing_carries_bands_and_censoring():
    ids = [("short", "2020-11-03", False), ("old", "2022-11-08", False)]
    predictions = pd.DataFrame(
        prediction_rows("d", "baseline", ids)
        + prediction_rows("d", "baseline_tenure_cap4", ids)
    )
    predictions["incumbent_status"] = "Dem_Incumbent"
    predictions["incumbent_tenure_years"] = [1.0, 10.0, 1.0, 10.0]
    predictions["incumbent_tenure_left_censored"] = [False, True, False, True]
    paired = compare.paired_frame(
        predictions, "baseline", "baseline_tenure_cap4", "d"
    )
    assert paired["incumbent_tenure_band"].tolist() == ["gt0_lt2", "ge4"]
    assert paired["incumbent_tenure_left_censored"].tolist() == [False, True]


def test_tenure_pairing_ignores_unrelated_predictions_without_provenance():
    ids = [("race", "2022-11-08", False)]
    predictions = pd.DataFrame(
        prediction_rows("d", "baseline", ids)
        + prediction_rows("d", "baseline_tenure_cap4", ids)
        + prediction_rows("d", "legacy_variant", ids)
    )
    predictions["incumbent_status"] = "Dem_Incumbent"
    predictions["incumbent_tenure_years"] = [1.0, 1.0, np.nan]
    predictions["incumbent_tenure_left_censored"] = [False, False, np.nan]

    paired = compare.paired_frame(
        predictions, "baseline", "baseline_tenure_cap4", "d"
    )

    assert paired["election_id"].tolist() == ["race"]


def test_comparison_row_includes_secondary_metrics():
    paired = paired_fixture().assign(
        observed_left=[1.0, 2.0, 3.0],
        absolute_error_left=[1.0, 3.0, 2.0],
        absolute_error_right=[2.0, 2.0, 1.0],
        error_left=[1.0, -3.0, 2.0],
        error_right=[2.0, -2.0, 1.0],
        within_interval_90_left=[True, False, True],
        within_interval_90_right=[True, True, True],
        crps_left=[1.0, 2.0, 1.0],
        crps_right=[2.0, 1.0, 1.0],
        win_correct_left=[True, False, True],
        win_correct_right=[True, True, True],
        brier_score_left=[0.1, 0.4, 0.2],
        brier_score_right=[0.2, 0.2, 0.1],
        win_log_loss_left=[0.2, 0.8, 0.3],
        win_log_loss_right=[0.3, 0.3, 0.2],
    )
    row = compare._row(
        paired, "baseline", "baseline_tenure_cap4", "pooled", "all",
        np.random.default_rng(1),
    )
    for metric in (
        "mae", "bias", "r2", "coverage_90", "crps", "win_accuracy",
        "brier_score", "win_log_loss",
    ):
        assert f"{metric}_difference" in row
