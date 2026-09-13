"""Run the rolling-origin scoring and publish the scorecard.

Fits each variant once per fold, pools every fold's holdout predictions, and
writes the per-race predictions, the segmented scorecard, the posterior
coefficients and the fit diagnostics (model-scoring spec).
"""

from __future__ import annotations

import pandas as pd

from . import config, fit as fitmod, folds, metrics, variants

# Segments every variant is broken out by, beyond the per-fold breakdown.
SEGMENTS = [
    "office",
    "is_special",
    "pres_elec",
    "redistricting_cycle",
    "no_dem_candidate",
]

# Below this a segment's metrics rest on too few races to carry weight. They
# are still reported; the marker is what stops them being read as if they did.
SMALL_SAMPLE = 10

IDENTITY = [
    "election_id",
    "election_year",
    "election_date",
    "office",
    "district_display",
    "redistricting_cycle",
    "incumbent_status",
    "pres_elec",
    "is_special",
    "no_dem_candidate",
]


def score_variant(variant: variants.Variant, races: pd.DataFrame) -> tuple:
    """Fit and predict every fold for one variant."""
    built, skipped = folds.build(races)
    predictions, coefficients, diagnostics = [], [], []

    for fold in built:
        fitted = fitmod.fit(variant, fold.train, fold=fold.year)
        draws = fitted.predict_draws(fold.holdout)
        per_race = metrics.per_race(draws, fold.holdout["dem_margin"].to_numpy())

        frame = fold.holdout[IDENTITY].reset_index(drop=True)
        frame.insert(0, "variant", variant.name)
        frame.insert(1, "fold", fold.year)
        predictions.append(pd.concat([frame, per_race], axis=1))

        coefficients.append(fitted.coefficients().assign(fold=fold.year))
        diagnostics.append(
            {
                "variant": variant.name,
                "fold": fold.year,
                "n_holdout": fold.n_holdout,
                **fitted.diagnostics.as_row(),
            }
        )
        flag = "" if fitted.diagnostics.passed else "  DIAGNOSTICS FAILED"
        print(
            f"  fold {fold.year}: train {fold.n_train:>3}  holdout {fold.n_holdout:>3}  "
            f"rmse {metrics.rmse(per_race):6.2f}{flag}"
        )

    return (
        pd.concat(predictions, ignore_index=True),
        pd.concat(coefficients, ignore_index=True),
        pd.DataFrame(diagnostics),
        skipped,
    )


def scorecard(
    predictions: pd.DataFrame, diagnostics: pd.DataFrame, skipped: list
) -> pd.DataFrame:
    """Pooled, per-fold and per-segment metrics for every scored variant."""
    failed = {
        (row.variant, row.fold)
        for row in diagnostics.itertuples()
        if not row.diagnostics_passed
    }
    rows = []
    for variant_name, group in predictions.groupby("variant", sort=False):
        variant_failed = sorted(fold for name, fold in failed if name == variant_name)

        # Pooled over races, not averaged over folds: the 2023 fold holds one
        # race and the 2014 fold holds 95.
        rows.append(
            {
                "variant": variant_name,
                "segment_type": "pooled",
                "segment_value": "all",
                **metrics.aggregate(group),
                "folds_failing_diagnostics": ",".join(str(f) for f in variant_failed),
            }
        )
        for fold, fold_group in group.groupby("fold", sort=True):
            rows.append(
                {
                    "variant": variant_name,
                    "segment_type": "fold",
                    "segment_value": str(fold),
                    **metrics.aggregate(fold_group),
                    "folds_failing_diagnostics": str(fold) if fold in variant_failed else "",
                }
            )
        for segment in SEGMENTS:
            for value, segment_group in group.groupby(segment, sort=True):
                rows.append(
                    {
                        "variant": variant_name,
                        "segment_type": segment,
                        "segment_value": str(value),
                        **metrics.aggregate(segment_group),
                        "folds_failing_diagnostics": "",
                    }
                )

    card = pd.DataFrame(rows)
    card["small_sample"] = card["n_races"] < SMALL_SAMPLE
    card["skipped_years"] = ",".join(str(y) for y in skipped)
    ordered = [
        "variant",
        "segment_type",
        "segment_value",
        "n_races",
        "small_sample",
        *metrics.METRIC_COLUMNS,
        "folds_failing_diagnostics",
        "skipped_years",
    ]
    return card[ordered]


def run(variant_names=None) -> pd.DataFrame:
    races = config.load_races()
    selected = variants.resolve(variant_names)

    schedule = folds.schedule(races)
    print("fold schedule:")
    print(schedule.to_string(index=False))
    built, skipped = folds.build(races)
    pooled = sum(fold.n_holdout for fold in built)
    print(
        f"\npooled holdout: {pooled} races, "
        f"{sum(int(f.holdout['is_special'].sum()) for f in built)} specials; "
        f"eligible years with no races: {skipped or 'none'}\n"
    )

    all_predictions, all_coefficients, all_diagnostics = [], [], []
    for variant in selected:
        print(f"{variant.name}: {variant.declared}")
        predictions, coefficients, diagnostics, _ = score_variant(variant, races)
        all_predictions.append(predictions)
        all_coefficients.append(coefficients)
        all_diagnostics.append(diagnostics)

    predictions = pd.concat(all_predictions, ignore_index=True)
    coefficients = pd.concat(all_coefficients, ignore_index=True)
    diagnostics = pd.concat(all_diagnostics, ignore_index=True)
    card = scorecard(predictions, diagnostics, skipped)

    config.write_csv(predictions, config.HOLDOUT_PREDICTIONS)
    config.write_csv(card.round(6), config.SCORECARD)
    config.write_csv(coefficients.round(6), config.COEFFICIENTS)
    config.write_csv(diagnostics, config.FIT_DIAGNOSTICS)

    print("\npooled holdout scores:")
    pooled_rows = card[card["segment_type"] == "pooled"]
    print(pooled_rows[["variant", "n_races", *metrics.METRIC_COLUMNS]].round(4).to_string(index=False))
    return card
