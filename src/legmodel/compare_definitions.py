"""Compare two data definitions, which is not the same as comparing variants.

`legmodel compare` pairs two variants on identical holdout races. Two
definitions do not share a holdout, and they may not even share a response, so
a single difference would hide three changes at once: which races are scored,
which races the models trained on, and what the response measures.

This reports all three (design.md, D8):

1. the paired RMSE difference over the races both definitions hold out,
2. what each definition admits that the other does not, with each side's score
   over its own exclusive races,
3. how far the response itself moved over the shared races.

A difference in (1) is not attributable to the response alone whenever (3) is
non-zero, and the report says so rather than leaving it to be inferred.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import compare, config, definitions

# A shared race whose response moves by more than this is counted as one the
# choice of definition actually relocates.
SHIFT_THRESHOLD = 1.0


def _rmse(frame: pd.DataFrame) -> float:
    return float(np.sqrt(frame["squared_error"].mean())) if len(frame) else float("nan")


def paired_across(
    predictions: pd.DataFrame, left: str, right: str, variant: str
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Shared holdout races, and each definition's exclusive ones."""
    columns = ["election_id", "fold", "squared_error", "observed", "prediction"]
    a = predictions[
        (predictions["definition"] == left) & (predictions["variant"] == variant)
    ]
    b = predictions[
        (predictions["definition"] == right) & (predictions["variant"] == variant)
    ]
    if a.empty or b.empty:
        raise ValueError(
            f"variant {variant!r} has no holdout predictions under "
            f"{left!r} or {right!r}; score both definitions first"
        )
    shared = a[columns].merge(b[columns], on="election_id", suffixes=("_left", "_right"))
    shared["squared_error_difference"] = (
        shared["squared_error_left"] - shared["squared_error_right"]
    )
    # The response each definition scored this race against. Where they differ,
    # part of any error difference is the target moving rather than the model
    # improving.
    shared["response_shift"] = shared["observed_right"] - shared["observed_left"]
    only_left = a[~a["election_id"].isin(shared["election_id"])]
    only_right = b[~b["election_id"].isin(shared["election_id"])]
    return shared, only_left, only_right


def _bootstrap(shared: pd.DataFrame, rng: np.random.Generator) -> np.ndarray:
    left = shared["squared_error_left"].to_numpy()
    right = shared["squared_error_right"].to_numpy()
    n = len(shared)
    index = rng.integers(0, n, size=(compare.BOOTSTRAP_RESAMPLES, n))
    return np.sqrt(left[index].mean(axis=1)) - np.sqrt(right[index].mean(axis=1))


def run(
    left: str,
    right: str,
    variant: str = "baseline",
    dropped: pd.DataFrame | None = None,
) -> pd.DataFrame:
    if not config.HOLDOUT_PREDICTIONS.exists():
        raise FileNotFoundError(
            f"{config.HOLDOUT_PREDICTIONS.relative_to(config.ROOT)} is missing; "
            "run `uv run legmodel score` first"
        )
    left_def, right_def = definitions.get(left), definitions.get(right)
    predictions = pd.read_csv(config.HOLDOUT_PREDICTIONS)
    shared, only_left, only_right = paired_across(predictions, left, right, variant)

    if dropped is None and config.DEFINITION_DROPPED.exists():
        dropped = pd.read_csv(config.DEFINITION_DROPPED)

    rng = np.random.default_rng(compare.BOOTSTRAP_SEED)
    left_rmse = float(np.sqrt(shared["squared_error_left"].mean()))
    right_rmse = float(np.sqrt(shared["squared_error_right"].mean()))
    difference = left_rmse - right_rmse
    draws = _bootstrap(shared, rng)
    low, high = np.percentile(draws, compare.INTERVAL_PERCENTILES)
    spans_zero = bool(low <= 0 <= high)

    shift = shared["response_shift"].abs()
    same_response = left_def.response == right_def.response

    rows = [
        {
            "section": "paired_on_shared_races",
            "left_definition": left,
            "right_definition": right,
            "variant": variant,
            "n_shared": len(shared),
            "left_rmse": left_rmse,
            "right_rmse": right_rmse,
            "rmse_difference": difference,
            "ci_low": float(low),
            "ci_high": float(high),
            "interval_spans_zero": spans_zero,
            "verdict": (
                "undecided"
                if spans_zero
                else (f"{left} lower" if difference < 0 else f"{right} lower")
            ),
            "races_favouring_left": int((shared["squared_error_difference"] < 0).sum()),
            "races_favouring_right": int((shared["squared_error_difference"] > 0).sum()),
            # Both models also trained on different race sets, so the paired
            # difference isolates neither the response nor the eligibility rule.
            "training_sets_differ": True,
            "response_columns_differ": not same_response,
            "note": (
                "the two models trained on different race sets, so this "
                "difference isolates neither the response nor the eligibility "
                "rule on its own"
            ),
        },
        {
            "section": "response_shift_on_shared_races",
            "left_definition": left,
            "right_definition": right,
            "variant": variant,
            "n_shared": len(shared),
            "left_response": left_def.response,
            "right_response": right_def.response,
            "response_columns_differ": not same_response,
            "shift_median": float(shift.median()),
            "shift_p95": float(shift.quantile(0.95)),
            "shift_max": float(shift.max()),
            "races_shifted_over_threshold": int((shift > SHIFT_THRESHOLD).sum()),
            "shift_threshold": SHIFT_THRESHOLD,
            "note": (
                "both definitions score the same response, so this comparison "
                "isolates the eligibility rule"
                if same_response
                else "part of the RMSE difference is the target moving, not accuracy"
            ),
        },
    ]
    for name, other, exclusive in (
        (left, right, only_left),
        (right, left, only_right),
    ):
        reasons = ""
        if dropped is not None and len(exclusive):
            why = dropped[
                (dropped["definition"] == other)
                & (dropped["election_id"].isin(exclusive["election_id"]))
            ]
            reasons = "; ".join(
                f"{count} {reason}" for reason, count in why["reason"].value_counts().items()
            )
        if not reasons and len(exclusive):
            # A train-only definition does not drop these races -- it trains on
            # them and withholds them from the holdout -- so they never reach
            # the dropped report. Saying "no reason recorded" would misdescribe
            # a deliberate treatment as a gap.
            other_definition = definitions.get(other)
            if other_definition.no_dem == definitions.NO_DEM_TRAIN_ONLY:
                withheld = int(exclusive["no_dem_candidate"].astype(bool).sum())
                reasons = (
                    f"{withheld} trained on but withheld from scoring by the "
                    f"{other!r} no-Democrat treatment"
                )
            else:
                reasons = "not held out by this definition; no drop reason recorded"
        rows.append(
            {
                "section": "exclusive_races",
                "left_definition": name,
                "right_definition": other,
                "variant": variant,
                "n_exclusive": len(exclusive),
                "exclusive_rmse": _rmse(exclusive),
                "exclusive_specials": int(exclusive["is_special"].sum())
                if len(exclusive)
                else 0,
                "note": f"held out by {name} and not by {other}",
                "excluded_because": reasons,
            }
        )

    report = pd.DataFrame(rows)
    report["bootstrap_resamples"] = compare.BOOTSTRAP_RESAMPLES
    report["bootstrap_seed"] = compare.BOOTSTRAP_SEED

    print(
        f"definition comparison: {left!r} against {right!r} using variant "
        f"{variant!r}\n"
        f"  shared holdout races: {len(shared)}\n"
        f"  {left} {left_rmse:.3f} vs {right} {right_rmse:.3f}; difference "
        f"{difference:+.3f} [{float(low):+.3f}, {float(high):+.3f}] -> "
        f"{rows[0]['verdict'].upper()}\n"
        f"  response shift on shared races: median {shift.median():.3f}, "
        f"{int((shift > SHIFT_THRESHOLD).sum())} beyond {SHIFT_THRESHOLD:.0f} point, "
        f"max {shift.max():.1f}"
        + ("  (same response column)" if same_response else "")
        + f"\n  exclusive to {left}: {len(only_left)} races (rmse "
        f"{_rmse(only_left):.3f}); exclusive to {right}: {len(only_right)} races "
        f"(rmse {_rmse(only_right):.3f})\n"
        "  both models also trained on different race sets"
    )
    return report
