import numpy as np
import pandas as pd

from legmodel import compare, compare_definitions, config, importance, score


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
    predictions = pd.read_csv(config.HOLDOUT_PREDICTIONS)
    paired = compare.paired_frame(
        predictions, "baseline", "baseline_timing", "two_party_or_strongest"
    )

    sensitivity = compare.leave_one_general_date_out(paired).set_index("omitted_date")

    assert bool(sensitivity.loc["2018-11-06", "sign_change"])
