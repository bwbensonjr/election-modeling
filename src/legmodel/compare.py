"""Paired comparison of two variants over the same holdout races.

Two nested variants differing by one binary term will not separate by much on
424 races, so the point difference alone is not an answer. The interval is
what decides whether the data settles the question at all (design.md, D8).

Not every comparison is nested. Where one variant adds a term and removes
another, the difference is the combined effect of both, and the report says so
rather than letting it read as the effect of the addition.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config, metrics, score, variants as variants_module

BOOTSTRAP_RESAMPLES = 10000
BOOTSTRAP_SEED = 20260912
INTERVAL_PERCENTILES = (5, 95)

# Segments reported alongside the pooled difference. The special-election one
# is the point of the first comparison this harness runs; `incumbent_status` is
# the point of the money comparisons, where the prior is specific -- money
# should matter most in an open seat and least against an entrenched incumbent,
# and a pooled null that hid an open-seat effect would be a wrong conclusion
# rather than an incomplete one (model-scoring spec, "The money sweep is
# reported per incumbency segment").
COMPARISON_SEGMENTS = [
    "is_special",
    "ballot_timing",
    "office",
    "pres_elec",
    "no_dem_candidate",
    "incumbent_status",
]


def term_difference(left: str, right: str) -> tuple[list, list]:
    """The terms `right` adds to `left`, and the terms it removes.

    A comparison between two variants is only the effect of one term when one
    predictor set contains the other. Where it does not, the difference mixes
    an addition with a removal and cannot be read as either (model-scoring
    spec, "A non-nested comparison is labelled as such").
    """

    def terms(name: str) -> set:
        variant = variants_module.get(name)
        return set(variant.predictors) | {
            variants_module.group_term(group) for group in variant.group_effects
        }

    left_terms, right_terms = terms(left), terms(right)
    return sorted(right_terms - left_terms), sorted(left_terms - right_terms)


def _components(name: str) -> str:
    """A composite's components and the population each predicts, or ""."""
    variant = variants_module.get(name)
    if not getattr(variant, "is_composite", False):
        return ""
    return "; ".join(
        f"{variant.route_on}={value}: {component.name}"
        + (f" (requires {','.join(component.requires)})" if component.requires else "")
        for value, component in sorted(variant.components.items())
    )


def nesting_label(left: str, right: str) -> tuple[str, str, str]:
    """How the two variants are related, as (label, added, removed).

    A composite is never nested in a single-fit variant, whatever their
    predictor sets look like: it is two fits over two populations, so the
    difference cannot be read as the effect of a term either of them carries
    (margin-model spec, "A composite variant is compared race by race").
    """
    added, removed = term_difference(left, right)
    composites = [name for name in (left, right) if _components(name)]
    if composites:
        return (
            "non-nested",
            ",".join(added),
            ",".join(removed),
        )
    if not added and not removed:
        label = "identical"
    elif added and removed:
        label = "non-nested"
    else:
        label = "nested"
    return label, ",".join(added), ",".join(removed)


def paired_frame(
    predictions: pd.DataFrame, left: str, right: str, definition: str
) -> pd.DataFrame:
    """One row per race carrying both variants' errors, within one definition.

    An inner join on `election_id` is what enforces the pairing: a race missing
    from either variant's holdout leaves the comparison entirely, rather than
    being scored for one side only. Both sides are taken from the same
    definition, so this compares variants; comparing definitions is a different
    operation with different hazards (compare_definitions.py).
    """
    predictions = predictions[predictions["definition"] == definition]
    # Read from the predictions where they carry the level the race's own
    # predictor held, and derived by the same function where they predate the
    # column, so the comparison's segments and the variant's coefficients are
    # labelled alike (design.md, D5).
    predictions = predictions.assign(
        ballot_timing=score.ballot_timing(predictions)
    )
    columns = ["election_id", "fold", "squared_error", "observed", "prediction"]
    segments = score.SEGMENTS + [
        s for s in COMPARISON_SEGMENTS if s not in score.SEGMENTS
    ]
    a = predictions[predictions["variant"] == left][columns + segments]
    b = predictions[predictions["variant"] == right][columns]
    if a.empty or b.empty:
        raise ValueError(f"no holdout predictions for {left!r} or {right!r}")
    merged = a.merge(b, on=["election_id", "fold"], suffixes=("_left", "_right"))
    merged["squared_error_difference"] = (
        merged["squared_error_left"] - merged["squared_error_right"]
    )
    return merged


def bootstrap_difference(paired: pd.DataFrame, rng: np.random.Generator) -> np.ndarray:
    """Race-weighted RMSE differences over resampled election-date clusters.

    A bootstrap draw samples the observed fold keys with replacement and
    carries every paired race from each selected fold. Cluster sizes therefore
    continue to determine the weight of their races in each resampled RMSE.
    """
    clusters = (
        paired.groupby("fold", sort=True)
        .agg(
            n_races=("fold", "size"),
            left_sum=("squared_error_left", "sum"),
            right_sum=("squared_error_right", "sum"),
        )
        .reset_index(drop=True)
    )
    n_clusters = len(clusters)
    if n_clusters < 2:
        return np.array([], dtype=float)
    index = rng.integers(
        0, n_clusters, size=(BOOTSTRAP_RESAMPLES, n_clusters)
    )
    counts = clusters["n_races"].to_numpy(dtype=float)[index].sum(axis=1)
    left = clusters["left_sum"].to_numpy(dtype=float)[index].sum(axis=1)
    right = clusters["right_sum"].to_numpy(dtype=float)[index].sum(axis=1)
    return np.sqrt(left / counts) - np.sqrt(right / counts)


def point_difference(paired: pd.DataFrame) -> float:
    """Race-weighted left-minus-right RMSE difference."""
    left = float(np.sqrt(paired["squared_error_left"].mean()))
    right = float(np.sqrt(paired["squared_error_right"].mean()))
    return left - right


def leave_one_general_date_out(paired: pd.DataFrame) -> pd.DataFrame:
    """Sensitivity of a paired comparison to each general-election date."""
    required = {"fold", "is_special", "squared_error_left", "squared_error_right"}
    missing = required - set(paired.columns)
    if missing:
        raise ValueError(
            "leave-one-general-date-out requires " + ", ".join(sorted(missing))
        )
    general_dates = sorted(
        paired.loc[~paired["is_special"].astype(bool), "fold"].astype(str).unique()
    )
    full = point_difference(paired)
    rows = []
    for omitted in general_dates:
        remaining = paired[paired["fold"].astype(str) != omitted]
        difference = point_difference(remaining)
        rows.append(
            {
                "omitted_date": omitted,
                "remaining_races": len(remaining),
                "remaining_clusters": int(remaining["fold"].nunique()),
                "rmse_difference": difference,
                "full_rmse_difference": full,
                "sign_change": bool(np.sign(difference) != np.sign(full)),
            }
        )
    return pd.DataFrame(rows)


def _row(paired: pd.DataFrame, left: str, right: str, segment_type: str,
         segment_value: str, rng: np.random.Generator) -> dict:
    left_rmse = float(np.sqrt(paired["squared_error_left"].mean()))
    right_rmse = float(np.sqrt(paired["squared_error_right"].mean()))
    difference = left_rmse - right_rmse
    draws = bootstrap_difference(paired, rng)
    n_clusters = int(paired["fold"].nunique())
    interval_available = len(draws) > 0
    if interval_available:
        low, high = np.percentile(draws, INTERVAL_PERCENTILES)
        spans_zero = bool(low <= 0 <= high)
    else:
        low, high = float("nan"), float("nan")
        spans_zero = pd.NA
    if not interval_available or spans_zero:
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
        "interval_available": interval_available,
        "verdict": verdict,
        "races_favouring_left": int((paired["squared_error_difference"] < 0).sum()),
        "races_favouring_right": int((paired["squared_error_difference"] > 0).sum()),
        # Marked rather than omitted: a segment too small to carry weight is
        # still evidence about where a variant helps, and suppressing it would
        # hide the special-date folds, which are the special-election
        # evidence. Under a date schedule most folds are one of those: 17 of
        # the 23 hold a single special election apiece.
        "small_sample": len(paired) < score.SMALL_SAMPLE,
        "resampling_unit": "election_date",
        "n_clusters": n_clusters,
        "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
        "bootstrap_seed": BOOTSTRAP_SEED,
    }


def run(
    left: str,
    right: str,
    definition: str | None = None,
    write: bool = True,
) -> pd.DataFrame:
    from . import definitions as definitions_module

    if not config.HOLDOUT_PREDICTIONS.exists():
        raise FileNotFoundError(
            f"{config.HOLDOUT_PREDICTIONS.relative_to(config.ROOT)} is missing; "
            "run `uv run legmodel score` first"
        )
    definition = definition or definitions_module.adopted().name
    predictions = pd.read_csv(config.HOLDOUT_PREDICTIONS)
    scoped = predictions[predictions["definition"] == definition]
    if scoped.empty:
        raise ValueError(
            f"no holdout predictions under definition {definition!r}; "
            f"scored definitions are {sorted(predictions['definition'].unique())}"
        )
    paired = paired_frame(predictions, left, right, definition)

    dropped = {
        name: len(scoped[scoped["variant"] == name]) - len(paired)
        for name in (left, right)
    }
    print(
        f"paired comparison of {left!r} against {right!r} under definition "
        f"{definition!r} on {len(paired)} races held out by both"
        + (f"; dropped {dropped}" if any(dropped.values()) else "")
    )

    nesting, added, removed = nesting_label(left, right)
    for name in (left, right):
        detail = _components(name)
        if detail:
            print(f"  COMPOSITE {name!r}: {detail}")
    if nesting == "non-nested":
        # Said before the numbers, because the numbers are what invite the
        # misreading: this difference is not the effect of a single term.
        print(
            f"  NON-NESTED: {right!r} adds [{added}] and removes [{removed}] "
            f"relative to {left!r}, so the difference below is the combined "
            "effect of both, not of one term"
        )

    rows = [
        _row(
            paired,
            left,
            right,
            "pooled",
            "all",
            np.random.default_rng(BOOTSTRAP_SEED),
        )
    ]
    for segment in COMPARISON_SEGMENTS:
        for value, group in paired.groupby(segment, sort=True):
            rows.append(
                _row(
                    group,
                    left,
                    right,
                    segment,
                    str(value),
                    np.random.default_rng(BOOTSTRAP_SEED),
                )
            )

    report = pd.DataFrame(rows)
    report.insert(0, "definition", definition)
    report["nesting"] = nesting
    report["terms_added"] = added
    report["terms_removed"] = removed
    report["left_components"] = _components(left)
    report["right_components"] = _components(right)
    sensitivity = leave_one_general_date_out(paired)
    if not sensitivity.empty:
        sensitivity.insert(0, "definition", definition)
        sensitivity.insert(1, "left_variant", left)
        sensitivity.insert(2, "right_variant", right)
    report.attrs["sensitivity"] = sensitivity
    if write:
        config.write_csv(report.round(6), config.VARIANT_COMPARISON)
        config.write_csv(
            sensitivity.round(6), config.VARIANT_COMPARISON_SENSITIVITY
        )

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
                "small_sample",
            ]
        ]
        .round(4)
        .to_string(index=False)
    )
    pooled = report.iloc[0]
    print(
        f"\npooled: {left} {pooled['left_rmse']:.3f} vs {right} "
        f"{pooled['right_rmse']:.3f}; difference {pooled['rmse_difference']:+.3f} "
        + (
            f"[{pooled['ci_low']:+.3f}, {pooled['ci_high']:+.3f}]"
            if pooled["interval_available"]
            else "[not estimable]"
        )
        + f" -> {pooled['verdict'].upper()}"
    )
    if nesting == "non-nested":
        print(
            f"  this is a non-nested comparison: [{added}] added, "
            f"[{removed}] removed"
        )
    return report
