"""Run the rolling-origin scoring and publish the scorecard.

Fits each variant once per fold, pools every fold's holdout predictions, and
writes the per-race predictions, the segmented scorecard, the posterior
coefficients and the fit diagnostics (model-scoring spec).
"""

from __future__ import annotations

import pandas as pd

from . import config, definitions, fit as fitmod, folds, metrics, variants

# Segments every variant is broken out by, beyond the per-fold breakdown.
SEGMENTS = [
    "office",
    "is_special",
    "pres_elec",
    "redistricting_cycle",
    "no_dem_candidate",
    "admitted_by_write_in",
]

# Segment values that must be reported even when a definition admits no races
# in them, so a definition that empties a segment is visible as having done so
# rather than by the row's absence.
REQUIRED_SEGMENT_VALUES = {
    "is_special": ["True", "False"],
    "pres_elec": ["True", "False"],
    "no_dem_candidate": ["True", "False"],
    "admitted_by_write_in": ["True", "False"],
    "office": ["State Representative", "State Senate"],
}

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
    "admitted_by_write_in",
]


def check_compatible(
    variant: variants.Variant, definition: definitions.Definition, races: pd.DataFrame
) -> None:
    """Refuse a variant whose predictor carries no information under a definition.

    A definition that excludes every no-Democrat race leaves `no_dem_candidate`
    constant, and a constant predictor has no estimable effect. Catching it here
    names both the predictor and the definition, rather than letting the fit
    fail later on one fold with only the predictor named.
    """
    variant.validate(races.columns)
    # Expanded against the prepared frame: a categorical's indicator columns
    # only exist once `prepare` has built them.
    prepared = variants.prepare(races)
    degenerate = [
        column
        for predictor in variant.predictors
        for column in variants.expand(predictor)
        if prepared[column].nunique(dropna=False) < 2
    ]
    if degenerate:
        raise fitmod.UnidentifiablePredictorError(
            f"variant {variant.name!r} names {degenerate}, which "
            f"{'is' if len(degenerate) == 1 else 'are'} constant across all "
            f"{len(races)} races that definition {definition.name!r} admits, so "
            "the effect cannot be estimated under this definition"
        )


def score_variant(
    variant: variants.Variant,
    races: pd.DataFrame,
    definition: definitions.Definition,
) -> tuple:
    """Fit and predict every fold for one variant under one definition."""
    built, skipped = folds.build(races)
    predictions, coefficients, diagnostics = [], [], []

    for fold in built:
        fitted = fitmod.fit(
            variant, fold.train, fold=fold.year, definition=definition.name
        )
        draws = fitted.predict_draws(fold.holdout)
        per_race = metrics.per_race(draws, fold.holdout["response"].to_numpy())

        frame = fold.holdout[IDENTITY].reset_index(drop=True)
        frame.insert(0, "definition", definition.name)
        frame.insert(1, "variant", variant.name)
        frame.insert(2, "fold", fold.year)
        predictions.append(pd.concat([frame, per_race], axis=1))

        coefficients.append(
            fitted.coefficients().assign(fold=fold.year, definition=definition.name)
        )
        diagnostics.append(
            {
                "definition": definition.name,
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
        (row.definition, row.variant, row.fold)
        for row in diagnostics.itertuples()
        if not row.diagnostics_passed
    }
    rows = []
    for (definition_name, variant_name), group in predictions.groupby(
        ["definition", "variant"], sort=False
    ):
        variant_failed = sorted(
            fold
            for definition, name, fold in failed
            if name == variant_name and definition == definition_name
        )

        # Pooled over races, not averaged over folds: the 2023 fold holds one
        # race and the 2014 fold holds 95.
        # The presidential-year bias gap, on the pooled row because it is a
        # property of the variant rather than of either segment. A variant that
        # narrows it has absorbed a swing the single pres_elec term cannot,
        # which is visible here even when pooled RMSE is unchanged.
        presidential = group[group["pres_elec"].astype(bool)]
        midterm = group[~group["pres_elec"].astype(bool)]
        bias_presidential = (
            float(presidential["error"].mean()) if len(presidential) else float("nan")
        )
        bias_midterm = float(midterm["error"].mean()) if len(midterm) else float("nan")
        rows.append(
            {
                "definition": definition_name,
                "variant": variant_name,
                "segment_type": "pooled",
                "segment_value": "all",
                **metrics.aggregate(group),
                "bias_presidential_years": bias_presidential,
                "bias_non_presidential_years": bias_midterm,
                "pres_bias_gap": bias_presidential - bias_midterm,
                "folds_failing_diagnostics": ",".join(str(f) for f in variant_failed),
            }
        )
        for fold, fold_group in group.groupby("fold", sort=True):
            rows.append(
                {
                    "definition": definition_name,
                    "variant": variant_name,
                    "segment_type": "fold",
                    "segment_value": str(fold),
                    **metrics.aggregate(fold_group),
                    "folds_failing_diagnostics": str(fold) if fold in variant_failed else "",
                }
            )
        for segment in SEGMENTS:
            seen = set()
            for value, segment_group in group.groupby(segment, sort=True):
                seen.add(str(value))
                rows.append(
                    {
                        "definition": definition_name,
                        "variant": variant_name,
                        "segment_type": segment,
                        "segment_value": str(value),
                        **metrics.aggregate(segment_group),
                        "folds_failing_diagnostics": "",
                    }
                )
            # A segment a definition empties is reported with a count of zero,
            # not dropped: "two_party admits no no-Democrat races" and "nobody
            # broke that segment out" must not look the same in the scorecard.
            for value in REQUIRED_SEGMENT_VALUES.get(segment, []):
                if value in seen:
                    continue
                rows.append(
                    {
                        "definition": definition_name,
                        "variant": variant_name,
                        "segment_type": segment,
                        "segment_value": value,
                        **metrics.aggregate(group.iloc[0:0]),
                        "folds_failing_diagnostics": "",
                    }
                )

    card = pd.DataFrame(rows)
    card["small_sample"] = card["n_races"] < SMALL_SAMPLE
    card["skipped_years"] = ",".join(str(y) for y in skipped)
    ordered = [
        "definition",
        "variant",
        "segment_type",
        "segment_value",
        "n_races",
        "small_sample",
        *metrics.METRIC_COLUMNS,
        "bias_presidential_years",
        "bias_non_presidential_years",
        "pres_bias_gap",
        "folds_failing_diagnostics",
        "skipped_years",
    ]
    return card[ordered]


def _merge_existing(predictions, coefficients, diagnostics, summary, dropped):
    """Replace the scored cells in the committed outputs, keeping the rest."""
    fresh = set(zip(predictions["definition"], predictions["variant"]))

    def keep(frame, has_variant=True):
        if has_variant:
            mask = [
                (d, v) not in fresh
                for d, v in zip(frame["definition"], frame["variant"])
            ]
        else:
            mask = [d not in {d for d, _ in fresh} for d in frame["definition"]]
        return frame[mask]

    pairs = [
        (config.HOLDOUT_PREDICTIONS, predictions, True),
        (config.COEFFICIENTS, coefficients, True),
        (config.FIT_DIAGNOSTICS, diagnostics, True),
        (config.DEFINITION_SUMMARY, summary, False),
        (config.DEFINITION_DROPPED, dropped, False),
    ]
    merged = []
    for path, frame, has_variant in pairs:
        if path.exists():
            existing = pd.read_csv(path)
            if "definition" in existing.columns:
                frame = pd.concat(
                    [keep(existing, has_variant), frame], ignore_index=True
                )
        merged.append(frame)
    return tuple(merged)


def fold_summary(races: pd.DataFrame, definition: definitions.Definition) -> dict:
    """The holdout counts a definition produces, reported per definition."""
    built, skipped = folds.build(races)
    return {
        "definition": definition.name,
        "response": definition.response,
        "races": len(races),
        "pooled_holdout": sum(fold.n_holdout for fold in built),
        "holdout_specials": sum(
            int(fold.holdout["is_special"].sum()) for fold in built
        ),
        "smallest_training_fold": min((fold.n_train for fold in built), default=0),
        "folds": len(built),
        "skipped_years": ",".join(str(y) for y in skipped),
    }


def run(
    variant_names=None, definition_names=None, write=True, append=False
) -> pd.DataFrame:
    races_table = config.load_races()
    roster = config.load_roster()
    selected_variants = variants.resolve(variant_names)
    selected_definitions = (
        [definitions.adopted()]
        if definition_names is None
        else definitions.resolve(definition_names)
    )

    all_predictions, all_coefficients, all_diagnostics = [], [], []
    summaries, all_dropped, all_skipped = [], [], []

    for definition in selected_definitions:
        races, dropped = definitions.apply(definition, races_table, roster)
        all_dropped.append(dropped)
        summary = fold_summary(races, definition)
        summaries.append(summary)
        all_skipped.extend(int(y) for y in summary["skipped_years"].split(",") if y)

        print(f"\ndefinition {definition.name}: {definition.description}")
        print(
            f"  {summary['races']} races, pooled holdout {summary['pooled_holdout']} "
            f"({summary['holdout_specials']} specials), smallest training fold "
            f"{summary['smallest_training_fold']}, "
            f"eligible years with no races: {summary['skipped_years'] or 'none'}"
        )
        print(folds.schedule(races).to_string(index=False))

        for variant in selected_variants:
            check_compatible(variant, definition, races)
            print(f"\n  {variant.name}: {variant.declared}")
            predictions, coefficients, diagnostics, _ = score_variant(
                variant, races, definition
            )
            all_predictions.append(predictions)
            all_coefficients.append(coefficients)
            all_diagnostics.append(diagnostics)

    predictions = pd.concat(all_predictions, ignore_index=True)
    coefficients = pd.concat(all_coefficients, ignore_index=True)
    diagnostics = pd.concat(all_diagnostics, ignore_index=True)
    card = scorecard(predictions, diagnostics, sorted(set(all_skipped)))
    summary_frame = pd.DataFrame(summaries)
    dropped_frame = pd.concat(all_dropped, ignore_index=True)

    if append:
        # Adds these (definition, variant) cells to the committed outputs
        # instead of replacing them, so the pruned grid in design.md D12 can be
        # built up run by run rather than as one full cross.
        (
            predictions,
            coefficients,
            diagnostics,
            summary_frame,
            dropped_frame,
        ) = _merge_existing(
            predictions, coefficients, diagnostics, summary_frame, dropped_frame
        )
        card = scorecard(predictions, diagnostics, sorted(set(all_skipped)))

    if write:
        config.write_csv(predictions, config.HOLDOUT_PREDICTIONS)
        config.write_csv(card.round(6), config.SCORECARD)
        config.write_csv(coefficients.round(6), config.COEFFICIENTS)
        config.write_csv(diagnostics, config.FIT_DIAGNOSTICS)
        config.write_csv(summary_frame, config.DEFINITION_SUMMARY)
        config.write_csv(dropped_frame, config.DEFINITION_DROPPED)

    print("\ndefinition holdout counts:")
    print(summary_frame.to_string(index=False))
    print("\npooled holdout scores:")
    pooled_rows = card[card["segment_type"] == "pooled"]
    print(
        pooled_rows[["definition", "variant", "n_races", *metrics.METRIC_COLUMNS]]
        .round(4)
        .to_string(index=False)
    )
    return card
