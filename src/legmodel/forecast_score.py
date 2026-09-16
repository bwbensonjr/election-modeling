"""Prospective scoring of locked forecast snapshots without refitting."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import config, forecast_run

CALIBRATION_EDGES = np.linspace(0.0, 1.0, 11)


class ProspectiveScoreError(ValueError):
    """Certified results cannot be reconciled or scored as supplied."""


def result_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def reconcile_results(
    locked_races: pd.DataFrame, results: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Join certified results to locked identities with missing/extra reports."""
    required = {"target_id", "dem_votes", "comparison_votes"}
    missing_columns = sorted(required - set(results.columns))
    if missing_columns:
        raise ProspectiveScoreError(
            f"certified results are missing columns: {missing_columns}"
        )
    duplicate = results.duplicated("target_id", keep=False)
    if duplicate.any():
        ids = sorted(results.loc[duplicate, "target_id"].astype(str).unique())
        raise ProspectiveScoreError(f"certified results duplicate target IDs: {ids}")
    locked_ids = set(locked_races["target_id"])
    result_ids = set(results["target_id"])
    extra = results[results["target_id"].isin(result_ids - locked_ids)].copy()
    missing = locked_races[locked_races["target_id"].isin(locked_ids - result_ids)][
        ["target_id", "office", "district", "district_display"]
    ].copy()
    missing["reason"] = "certified result missing"
    shared = results[results["target_id"].isin(locked_ids & result_ids)]
    scored = locked_races.merge(shared, on="target_id", how="inner", validate="one_to_one")
    return scored, missing, extra


def _race_scores(joined: pd.DataFrame) -> pd.DataFrame:
    frame = joined.copy()
    total = frame["dem_votes"] + frame["comparison_votes"]
    if total.le(0).any():
        raise ProspectiveScoreError("certified result has no two-candidate votes")
    frame["observed_margin"] = (
        (frame["dem_votes"] - frame["comparison_votes"]) / total * 100
    )
    frame["error"] = frame["point_margin"] - frame["observed_margin"]
    frame["absolute_error"] = frame["error"].abs()
    frame["covered_90"] = frame["observed_margin"].between(
        frame["lower_90"], frame["upper_90"]
    )
    frame["dem_won"] = frame["observed_margin"].gt(0)
    probability = frame["dem_win_probability"].clip(1e-12, 1 - 1e-12)
    outcome = frame["dem_won"].astype(float)
    frame["brier"] = (probability - outcome) ** 2
    frame["log_loss"] = -(
        outcome * np.log(probability) + (1 - outcome) * np.log(1 - probability)
    )
    columns = [
        "target_id",
        "election_date",
        "office",
        "district",
        "district_display",
        "component",
        "point_margin",
        "lower_90",
        "upper_90",
        "dem_win_probability",
        "dem_votes",
        "comparison_votes",
        "observed_margin",
        "error",
        "absolute_error",
        "covered_90",
        "dem_won",
        "brier",
        "log_loss",
    ]
    return frame[columns].sort_values("target_id", ignore_index=True)


def _metric_row(frame: pd.DataFrame, segment: str, value: str) -> dict:
    return {
        "row_type": "race_metrics",
        "segment": segment,
        "value": value,
        "n_scored": len(frame),
        "rmse": float(np.sqrt(np.mean(frame["error"] ** 2))) if len(frame) else pd.NA,
        "mae": float(frame["absolute_error"].mean()) if len(frame) else pd.NA,
        "bias": float(frame["error"].mean()) if len(frame) else pd.NA,
        "coverage_90": float(frame["covered_90"].mean()) if len(frame) else pd.NA,
        "brier": float(frame["brier"].mean()) if len(frame) else pd.NA,
        "log_loss": float(frame["log_loss"].mean()) if len(frame) else pd.NA,
    }


def score_metrics(
    races: pd.DataFrame,
    chamber_draws: pd.DataFrame,
    expected_counts: dict[str, int] | None = None,
) -> pd.DataFrame:
    """Pooled, component, office, and aggregate-seat prospective scores."""
    rows = [_metric_row(races, "all", "all")]
    for segment in ("component", "office"):
        for value, group in races.groupby(segment):
            rows.append(_metric_row(group, segment, str(value)))
    metrics = pd.DataFrame(rows)
    aggregate = []
    for office, column in (
        ("State Representative", "State Representative"),
        ("State Senate", "State Senate"),
        ("combined_contested", "combined_contested"),
    ):
        scored_count = (
            len(races)
            if office == "combined_contested"
            else int(races["office"].eq(office).sum())
        )
        complete = expected_counts is None or scored_count == expected_counts[office]
        actual = (
            int(races["dem_won"].sum())
            if office == "combined_contested"
            else int(races.loc[races["office"].eq(office), "dem_won"].sum())
        )
        draws = chamber_draws[column]
        aggregate.append(
            {
                "row_type": "aggregate_seats",
                "segment": "office",
                "value": office,
                "n_scored": scored_count,
                "seat_mean": float(draws.mean()),
                "seat_lower_90": float(draws.quantile(0.05)),
                "seat_upper_90": float(draws.quantile(0.95)),
                "actual_seats": actual if complete else pd.NA,
                "seat_error": float(draws.mean() - actual) if complete else pd.NA,
                "seat_covered_90": (
                    bool(
                        actual >= draws.quantile(0.05)
                        and actual <= draws.quantile(0.95)
                    )
                    if complete
                    else pd.NA
                ),
            }
        )
    return pd.concat([metrics, pd.DataFrame(aggregate)], ignore_index=True)


def calibration(races: pd.DataFrame) -> pd.DataFrame:
    bins = pd.IntervalIndex.from_breaks(CALIBRATION_EDGES, closed="right")
    assigned = pd.cut(
        races["dem_win_probability"],
        CALIBRATION_EDGES,
        include_lowest=True,
        right=True,
    )
    rows = []
    for index, interval in enumerate(bins):
        group = races[assigned.cat.codes.eq(index)]
        rows.append(
            {
                "bin": f"{interval.left:.1f}-{interval.right:.1f}",
                "lower": interval.left,
                "upper": interval.right,
                "n_races": len(group),
                "mean_forecast": (
                    float(group["dem_win_probability"].mean()) if len(group) else pd.NA
                ),
                "observed_frequency": (
                    float(group["dem_won"].mean()) if len(group) else pd.NA
                ),
                "small_sample": len(group) < 10,
            }
        )
    return pd.DataFrame(rows)


def score_snapshot(
    snapshot_directory: Path, results: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    locked = pd.read_csv(snapshot_directory / "races.csv")
    chamber = pd.read_csv(snapshot_directory / "chamber_draws.csv.gz")
    joined, missing, extra = reconcile_results(locked, results)
    races = _race_scores(joined)
    expected_counts = locked.groupby("office").size().to_dict()
    expected_counts["combined_contested"] = len(locked)
    metrics = score_metrics(races, chamber, expected_counts)
    return races, metrics, calibration(races), pd.concat(
        [missing.assign(report_type="missing"), extra.assign(report_type="extra")],
        ignore_index=True,
        sort=False,
    )


def score_contents(
    snapshot_directory: Path,
    result_path: Path,
    result_source: str,
) -> dict[str, bytes]:
    results = pd.read_csv(result_path)
    races, metrics, probability, unresolved = score_snapshot(
        snapshot_directory, results
    )
    contents = {
        "race_scores.csv": races.to_csv(index=False, lineterminator="\n").encode(),
        "metrics.csv": metrics.to_csv(index=False, lineterminator="\n").encode(),
        "calibration.csv": probability.to_csv(index=False, lineterminator="\n").encode(),
        "unresolved.csv": unresolved.to_csv(index=False, lineterminator="\n").encode(),
    }
    manifest = {
        "snapshot_manifest_digest": forecast_run.file_digest(
            snapshot_directory / "manifest.json"
        ),
        "result_source": result_source,
        "result_digest": result_digest(result_path),
        "scored_races": len(races),
        "unscored_races": int(unresolved["report_type"].eq("missing").sum())
        if len(unresolved)
        else 0,
        "extra_results": int(unresolved["report_type"].eq("extra").sum())
        if len(unresolved)
        else 0,
        "files": {
            name: forecast_run.bytes_digest(content)
            for name, content in contents.items()
        },
    }
    contents["manifest.json"] = (
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    ).encode()
    return contents


def run(horizon: str, result_path: Path, result_source: str) -> None:
    snapshot = config.FORECAST_2026_SNAPSHOTS / horizon
    if not (snapshot / "manifest.json").exists():
        raise ProspectiveScoreError(f"forecast snapshot is missing: {snapshot}")
    before = {
        name: forecast_run.file_digest(snapshot / name)
        for name in forecast_run.SNAPSHOT_FILES
    }
    contents = score_contents(snapshot, result_path, result_source)
    result = forecast_run.publish_snapshot(contents, snapshot / "score")
    after = {
        name: forecast_run.file_digest(snapshot / name)
        for name in forecast_run.SNAPSHOT_FILES
    }
    if before != after:
        raise ProspectiveScoreError("prospective scoring mutated the forecast snapshot")
    print(f"{result} prospective score -> {(snapshot / 'score').relative_to(config.ROOT)}")
