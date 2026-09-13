"""Metric definitions over holdout predictions.

Everything is computed per race first and aggregated afterwards, so every
figure in the scorecard can be recomputed from the published per-race
predictions (model-scoring spec, "Per-race predictions are published, not only
summaries").
"""

from __future__ import annotations

import numpy as np
import pandas as pd

INTERVAL = 0.90
LOWER_PERCENTILE = 100 * (1 - INTERVAL) / 2
UPPER_PERCENTILE = 100 * (1 + INTERVAL) / 2

METRIC_COLUMNS = [
    "rmse",
    "mae",
    "bias",
    "r2",
    "coverage_90",
    "crps",
    "win_accuracy",
    "win_log_loss",
]


def crps_from_draws(draws: np.ndarray, observed: np.ndarray) -> np.ndarray:
    """Continuous ranked probability score per race, from posterior draws.

    Uses the sorted-sample identity for E|X - X'| rather than forming the
    pairwise differences, which would be 64 million terms per race at this
    draw count.
    """
    draws = np.asarray(draws, dtype=float)
    observed = np.asarray(observed, dtype=float)
    n_draws = draws.shape[0]
    absolute_error = np.abs(draws - observed[None, :]).mean(axis=0)
    ordered = np.sort(draws, axis=0)
    weights = (2 * np.arange(1, n_draws + 1) - n_draws - 1)[:, None]
    spread = (2.0 / n_draws**2) * (weights * ordered).sum(axis=0)
    return absolute_error - 0.5 * spread


def per_race(draws: np.ndarray, observed: np.ndarray) -> pd.DataFrame:
    """The per-race quantities every metric is built from."""
    draws = np.asarray(draws, dtype=float)
    observed = np.asarray(observed, dtype=float)
    n_draws = draws.shape[0]

    prediction = draws.mean(axis=0)
    lower = np.percentile(draws, LOWER_PERCENTILE, axis=0)
    upper = np.percentile(draws, UPPER_PERCENTILE, axis=0)
    win_probability = (draws > 0).mean(axis=0)

    # A probability of exactly 0 or 1 is an artefact of a finite draw count,
    # not a claim of certainty, so it is clipped to what the draws can resolve.
    epsilon = 1.0 / (2 * n_draws)
    clipped = np.clip(win_probability, epsilon, 1 - epsilon)
    dem_win = observed > 0

    error = prediction - observed
    return pd.DataFrame(
        {
            "prediction": prediction,
            "observed": observed,
            "error": error,
            "squared_error": error**2,
            "absolute_error": np.abs(error),
            "interval_lower": lower,
            "interval_upper": upper,
            "within_interval_90": (observed >= lower) & (observed <= upper),
            "crps": crps_from_draws(draws, observed),
            "win_probability": win_probability,
            "dem_win_observed": dem_win,
            "win_correct": (win_probability > 0.5) == dem_win,
            "win_log_loss": -(
                dem_win * np.log(clipped) + (~dem_win) * np.log(1 - clipped)
            ),
        }
    )


def aggregate(frame: pd.DataFrame) -> dict:
    """Pool the per-race quantities into the metric set.

    Pooling is over races, so every race weighs the same whichever fold
    produced it. `r2` is skill against predicting the mean of the races being
    scored, which makes it a within-segment figure and not comparable across
    segments of different composition.
    """
    if frame.empty:
        return {"n_races": 0, **{name: float("nan") for name in METRIC_COLUMNS}}

    observed = frame["observed"].to_numpy(dtype=float)
    residual = float(frame["squared_error"].sum())
    total = float(((observed - observed.mean()) ** 2).sum())
    return {
        "n_races": len(frame),
        "rmse": float(np.sqrt(frame["squared_error"].mean())),
        "mae": float(frame["absolute_error"].mean()),
        "bias": float(frame["error"].mean()),
        "r2": float(1 - residual / total) if total > 0 else float("nan"),
        "coverage_90": float(frame["within_interval_90"].mean()),
        "crps": float(frame["crps"].mean()),
        "win_accuracy": float(frame["win_correct"].mean()),
        "win_log_loss": float(frame["win_log_loss"].mean()),
    }


def rmse(frame: pd.DataFrame) -> float:
    return float(np.sqrt(frame["squared_error"].mean()))
