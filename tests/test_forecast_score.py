import json

import pandas as pd
import pytest

from legmodel import fit, forecast_run, forecast_score


def locked_races():
    return pd.DataFrame(
        [
            {
                "target_id": "a",
                "election_date": "2026-11-03",
                "office": "State Representative",
                "district": "First Example",
                "district_display": "1st Example",
                "component": "money",
                "point_margin": 10.0,
                "lower_90": -5.0,
                "upper_90": 25.0,
                "dem_win_probability": 0.75,
            },
            {
                "target_id": "b",
                "election_date": "2026-11-03",
                "office": "State Senate",
                "district": "Second Example",
                "district_display": "2nd Example",
                "component": "fallback",
                "point_margin": -5.0,
                "lower_90": -20.0,
                "upper_90": 10.0,
                "dem_win_probability": 0.25,
            },
        ]
    )


def chamber_draws():
    return pd.DataFrame(
        {
            "draw": [0, 1, 2, 3],
            "State Representative": [0, 1, 1, 1],
            "State Senate": [0, 0, 0, 1],
            "combined_contested": [0, 1, 1, 2],
        }
    )


def results():
    return pd.DataFrame(
        [
            {"target_id": "a", "dem_votes": 60, "comparison_votes": 40},
            {"target_id": "b", "dem_votes": 40, "comparison_votes": 60},
        ]
    )


def write_snapshot(path):
    path.mkdir()
    locked_races().to_csv(path / "races.csv", index=False)
    chamber_draws().to_csv(path / "chamber_draws.csv.gz", index=False)
    pd.DataFrame([{"target_id": "a", "warning": ""}]).to_csv(
        path / "support_warnings.csv", index=False
    )
    (path / "manifest.json").write_text(json.dumps({"horizon": "60d"}) + "\n")


def test_certified_result_reconciliation_reports_missing_and_extra():
    supplied = pd.DataFrame(
        [
            {"target_id": "a", "dem_votes": 60, "comparison_votes": 40},
            {"target_id": "extra", "dem_votes": 1, "comparison_votes": 2},
        ]
    )
    scored, missing, extra = forecast_score.reconcile_results(
        locked_races(), supplied
    )
    assert scored["target_id"].tolist() == ["a"]
    assert missing["target_id"].tolist() == ["b"]
    assert extra["target_id"].tolist() == ["extra"]


def test_incomplete_results_do_not_compare_partial_seats_to_full_snapshot(tmp_path):
    snapshot = tmp_path / "snapshot"
    write_snapshot(snapshot)
    partial = results().iloc[:1]
    _, metrics, _, unresolved = forecast_score.score_snapshot(snapshot, partial)
    combined = metrics[
        metrics["row_type"].eq("aggregate_seats")
        & metrics["value"].eq("combined_contested")
    ].iloc[0]
    assert pd.isna(combined["actual_seats"])
    assert unresolved["report_type"].tolist() == ["missing"]


def test_prospective_scores_use_locked_predictions_without_fitting(tmp_path, monkeypatch):
    snapshot = tmp_path / "snapshot"
    write_snapshot(snapshot)
    monkeypatch.setattr(
        fit,
        "fit",
        lambda *_args, **_kwargs: pytest.fail("prospective scoring called fitter"),
    )
    races, metrics, probability, unresolved = forecast_score.score_snapshot(
        snapshot, results()
    )
    pooled = metrics[
        metrics["row_type"].eq("race_metrics") & metrics["segment"].eq("all")
    ].iloc[0]
    assert pooled["rmse"] == pytest.approx((162.5) ** 0.5)
    assert pooled["coverage_90"] == 1.0
    assert pooled["brier"] == pytest.approx(0.0625)
    assert len(probability) == 10
    assert len(unresolved) == 0
    assert set(races["component"]) == {"money", "fallback"}


def test_score_artifacts_are_reproducible_and_snapshot_is_unchanged(tmp_path):
    snapshot = tmp_path / "snapshot"
    write_snapshot(snapshot)
    result_path = tmp_path / "certified.csv"
    results().to_csv(result_path, index=False)
    before = {
        name: (snapshot / name).read_bytes() for name in forecast_run.SNAPSHOT_FILES
    }

    contents = forecast_score.score_contents(
        snapshot, result_path, "Secretary certified results"
    )
    score_directory = snapshot / "score"
    assert forecast_run.publish_snapshot(contents, score_directory) == "created"
    assert forecast_run.publish_snapshot(contents, score_directory) == "verified"
    assert before == {
        name: (snapshot / name).read_bytes() for name in forecast_run.SNAPSHOT_FILES
    }
    manifest = json.loads(contents["manifest.json"])
    assert manifest["scored_races"] == 2
    assert manifest["unscored_races"] == 0
    assert manifest["result_source"] == "Secretary certified results"
