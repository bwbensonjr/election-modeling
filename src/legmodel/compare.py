"""Paired comparison of two variants over the same holdout races.

Two nested variants differing by one binary term will not separate by much on
424 races, so the point difference alone is not an answer. The interval is
what decides whether the data settles the question at all (design.md, D8).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config, metrics, score

BOOTSTRAP_RESAMPLES = 10000
BOOTSTRAP_SEED = 20260912
INTERVAL_PERCENTILES = (5, 95)

# Segments reported alongside the pooled difference. The special-election one
# is the point of the first comparison this harness runs.
COMPARISON_SEGMENTS = ["is_special", "office", "pres_elec", "no_dem_candidate"]


def paired_frame(predictions: pd.DataFrame, left: str, right: str) -> pd.DataFrame:
    """One row per race carrying both variants' errors.

    An inner join on `election_id` is what enforces the pairing: a race missing
    from either variant's holdout leaves the comparison entirely, rather than
    being scored for one side only.
    """
    columns = ["election_id", "fold", "squared_error", "observed", "prediction"]
    a = predictions[predictions["variant"] == left][columns + score.SEGMENTS]
    b = predictions[predictions["variant"] == right][columns]
    if a.empty or b.empty:
        raise ValueError(f"no holdout predictions for {left!r} or {right!r}")
    merged = a.merge(b, on=["election_id", "fold"], suffixes=("_left", "_right"))
    merged["squared_error_difference"] = (
        merged["squared_error_left"] - merged["squared_error_right"]
    )
    return merged


def bootstrap_difference(paired: pd.DataFrame, rng: np.random.Generator) -> np.ndarray:
    """RMSE differences over resampled races.

    Each resample draws races, then scores both variants on that same draw, so
    the pairing survives the resampling.
    """
    left = paired["squared_error_left"].to_numpy()
    right = paired["squared_error_right"].to_numpy()
    n = len(paired)
    index = rng.integers(0, n, size=(BOOTSTRAP_RESAMPLES, n))
    return np.sqrt(left[index].mean(axis=1)) - np.sqrt(right[index].mean(axis=1))


def _row(paired: pd.DataFrame, left: str, right: str, segment_type: str,
         segment_value: str, rng: np.random.Generator) -> dict:
    left_rmse = float(np.sqrt(paired["squared_error_left"].mean()))
    right_rmse = float(np.sqrt(paired["squared_error_right"].mean()))
    difference = left_rmse - right_rmse
    draws = bootstrap_difference(paired, rng)
    low, high = np.percentile(draws, INTERVAL_PERCENTILES)
    spans_zero = bool(low <= 0 <= high)
    if spans_zero:
        verdict = "undecided"
    else:
        verdict = f"{left} lower" if difference < 0 else f"{right} lower"
    return {
        "left_variant": left,
        "right_variant": right,
        "segment_type": segment_type,
        "segment_value": segment_value,
        "n_races": len(paired),
        "left_rmse": left_rmse,
        "right_rmse": right_rmse,
        "rmse_difference": difference,
        "ci_low": float(low),
        "ci_high": float(high),
        "interval_spans_zero": spans_zero,
        "verdict": verdict,
        "races_favouring_left": int((paired["squared_error_difference"] < 0).sum()),
        "races_favouring_right": int((paired["squared_error_difference"] > 0).sum()),
    }


def run(left: str, right: str) -> pd.DataFrame:
    if not config.HOLDOUT_PREDICTIONS.exists():
        raise FileNotFoundError(
            f"{config.HOLDOUT_PREDICTIONS.relative_to(config.ROOT)} is missing; "
            "run `uv run legmodel score` first"
        )
    predictions = pd.read_csv(config.HOLDOUT_PREDICTIONS)
    paired = paired_frame(predictions, left, right)

    dropped = {
        name: len(predictions[predictions["variant"] == name]) - len(paired)
        for name in (left, right)
    }
    print(
        f"paired comparison of {left!r} against {right!r} on {len(paired)} races "
        f"held out by both"
        + (f"; dropped {dropped}" if any(dropped.values()) else "")
    )

    rng = np.random.default_rng(BOOTSTRAP_SEED)
    rows = [_row(paired, left, right, "pooled", "all", rng)]
    for segment in COMPARISON_SEGMENTS:
        for value, group in paired.groupby(segment, sort=True):
            rows.append(_row(group, left, right, segment, str(value), rng))

    report = pd.DataFrame(rows)
    report["bootstrap_resamples"] = BOOTSTRAP_RESAMPLES
    report["bootstrap_seed"] = BOOTSTRAP_SEED
    config.write_csv(report.round(6), config.VARIANT_COMPARISON)

    print()
    print(
        report[
            [
                "segment_type",
                "segment_value",
                "n_races",
                "left_rmse",
                "right_rmse",
                "rmse_difference",
                "ci_low",
                "ci_high",
                "verdict",
            ]
        ]
        .round(4)
        .to_string(index=False)
    )
    pooled = report.iloc[0]
    print(
        f"\npooled: {left} {pooled['left_rmse']:.3f} vs {right} "
        f"{pooled['right_rmse']:.3f}; difference {pooled['rmse_difference']:+.3f} "
        f"[{pooled['ci_low']:+.3f}, {pooled['ci_high']:+.3f}] -> {pooled['verdict'].upper()}"
    )
    return report
