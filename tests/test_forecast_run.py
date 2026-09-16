from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from legmodel import cli, definitions, forecast, forecast_run, variants


def targets():
    rows = []
    for district, display, pvi in (
        ("Tenth Bristol", "10th Bristol", 2.0),
        ("Eighteenth Essex", "18th Essex", 10.0),
    ):
        row = {
            "election_date": "2026-11-03",
            "office": "State Representative",
            "district": district,
            "district_display": display,
            "dem_candidate_id": f"d-{display}",
            "dem_candidate_name": f"Dem {display}",
            "comparison_candidate_id": f"r-{display}",
            "comparison_candidate_name": f"Rep {display}",
            "comparison_candidate_party": "Republican",
            "incumbent_status": "No_Incumbent",
            "PVI_N": pvi,
            "pvi_year": 2024,
            "redistricting_cycle": 2021,
            "pvi_coverage": 1.0,
            "pvi_provenance": "exact",
            "ballot_timing": "midterm_gop_pres",
            "money_complete_60d": True,
            "money_complete_14d": False,
            "candidate_source": "primary",
            "candidate_source_digest": "abc",
            "candidate_data_as_of": "2026-09-14",
            "pvi_source": "precinct",
            "pvi_source_digest": "def",
            "comparison_rule": "pre-election",
            "comparison_review_status": "not required",
            "dem_nominee_basis": "primary",
            "dem_nominee_review_status": "not required",
            "comparison_nominee_basis": "primary",
            "comparison_nominee_review_status": "not required",
        }
        row["target_id"] = forecast.target_id(
            row["election_date"], row["office"], row["district"]
        )
        rows.append(row)
    return pd.DataFrame(rows)


def finance_snapshot(second_complete=True):
    rows = []
    for target_index, target_row in targets().iterrows():
        for role in ("dem", "opp"):
            available = second_complete or target_index == 0
            rows.append(
                {
                    "target_id": target_row["target_id"],
                    "role": role,
                    "horizon": "60d",
                    "cutoff": "2026-09-04",
                    "available": available,
                    "receipts": 100.0 if available else pd.NA,
                    "expenditures": 50.0 if available else pd.NA,
                }
            )
    return pd.DataFrame(rows)


class FakeFit:
    def __init__(self, seed):
        self.seed = seed
        self.diagnostics = SimpleNamespace(
            as_row=lambda: {"seed": seed, "diagnostics_passed": True}
        )

    def predict_draws(self, target):
        point = target["PVI_N"].to_numpy(dtype=float)
        return np.vstack([point - 1, point, point + 1])


def fake_fit(component, training, fold, definition, seed):
    return FakeFit(seed)


def test_full_history_training_includes_2024_and_excludes_target_date():
    training = forecast_run.historical_training(
        "2026-11-03", definitions.adopted()
    )
    assert "2024-11-05" in set(training["election_date"])
    assert pd.to_datetime(training["election_date"]).max() < pd.Timestamp("2026-11-03")


def test_stable_seed_and_predictions_ignore_target_row_order():
    first = forecast_run.generate(
        targets(),
        finance_snapshot(),
        "60d",
        "forecast_60d",
        definitions.adopted().name,
        fit_provider=fake_fit,
    )
    second = forecast_run.generate(
        targets().iloc[::-1].reset_index(drop=True),
        finance_snapshot().iloc[::-1].reset_index(drop=True),
        "60d",
        "forecast_60d",
        definitions.adopted().name,
        fit_provider=fake_fit,
    )
    pd.testing.assert_frame_equal(first[0], second[0])
    assert first[3]["components"] == second[3]["components"]


def test_horizon_validation_refuses_14_day_component_in_60_day_forecast():
    future = forecast_run.attach_finance(targets(), finance_snapshot(), "60d")
    with pytest.raises(forecast_run.ForecastRunError, match="election-14d"):
        forecast_run.validate_component_horizon(
            variants.get("baseline_money_logratio_no_timing"), future, "60d"
        )


def test_composite_routes_complete_and_fallback_races_exactly_once():
    races, chamber, _, metadata = forecast_run.generate(
        targets(),
        finance_snapshot(second_complete=False),
        "60d",
        "forecast_60d",
        definitions.adopted().name,
        fit_provider=fake_fit,
    )
    assert len(races) == len(targets())
    assert races["target_id"].is_unique
    assert set(races["component"]) == {
        "baseline_money_logratio_no_timing_wide",
        "baseline_no_timing",
    }
    counts = {row["component"]: row["target_races"] for row in metadata["components"]}
    assert counts["baseline_money_logratio_no_timing_wide"] == 1
    assert counts["baseline_no_timing"] == 1
    assert (chamber["combined_contested"] == chamber["State Representative"]).all()


def test_support_checks_name_range_and_one_election_timing_warning():
    training = forecast_run.historical_training(
        "2026-11-03", definitions.adopted()
    )
    future = forecast_run.attach_finance(targets(), finance_snapshot(), "60d")
    future.loc[future.index[0], "PVI_N"] = 100.0
    numeric = forecast_run.support_checks(
        variants.get("baseline_no_timing"), training, future
    )
    assert "numeric_above_training_range" in set(numeric["warning"])

    timing = forecast_run.support_checks(
        variants.get("baseline_timing"), training, future
    )
    timing_rows = timing[timing["predictor"].eq("ballot_timing")]
    assert set(timing_rows["training_election_dates"]) == {1}
    assert set(timing_rows["warning"]) == {"categorical_level_one_election_date"}


def test_aggregate_draws_equal_contributing_race_draws():
    target = targets()
    draws = {
        target.loc[0, "target_id"]: np.array([-1, 1, 1]),
        target.loc[1, "target_id"]: np.array([-1, -1, 1]),
    }
    actual = forecast_run.aggregate_draws(draws, target)
    assert actual["combined_contested"].tolist() == [0, 1, 2]


def test_snapshot_manifest_digests_and_create_once_bytes(tmp_path):
    source_paths = []
    for name in ("target.csv", "finance.csv", "training.csv"):
        path = tmp_path / name
        path.write_text(name)
        source_paths.append(path)
    contents = forecast_run.snapshot_contents(
        pd.DataFrame([{"target_id": "a", "point_margin": 1.0}]),
        pd.DataFrame([{"draw": 0, "combined_contested": 1}]),
        pd.DataFrame([{"target_id": "a", "warning": ""}]),
        {"horizon": "60d", "components": []},
        *source_paths,
        code_commit="abc123",
    )
    directory = tmp_path / "snapshot"
    assert forecast_run.publish_snapshot(contents, directory) == "created"
    assert forecast_run.publish_snapshot(contents, directory) == "verified"
    changed = dict(contents)
    changed["races.csv"] += b"different"
    with pytest.raises(forecast_run.ForecastRunError, match="overwrite"):
        forecast_run.publish_snapshot(changed, directory)


def test_forecast_command_routes_horizon_and_dirty_publish_is_refused(monkeypatch):
    called = []
    with monkeypatch.context() as command_patch:
        command_patch.setattr(
            forecast_run, "run", lambda horizon: called.append(horizon)
        )
        assert cli.main(["forecast", "--horizon", "60d"]) == 0
    assert called == ["60d"]

    monkeypatch.setattr(forecast_run, "clean_worktree", lambda: False)
    with pytest.raises(forecast_run.ForecastRunError, match="clean worktree"):
        forecast_run.run("60d")
