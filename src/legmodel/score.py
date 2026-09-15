"""Run the rolling-origin scoring and publish the scorecard.

Fits each variant once per fold, pools every fold's holdout predictions, and
writes the per-race predictions, the segmented scorecard, the posterior
coefficients and the fit diagnostics (model-scoring spec).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config, definitions, fit as fitmod, folds, metrics, variants

# Segments every variant is broken out by, beyond the per-fold breakdown.
SEGMENTS = [
    "office",
    "is_special",
    "pres_elec",
    "ballot_timing",
    "redistricting_cycle",
    "no_dem_candidate",
    "admitted_by_write_in",
]

# Every special election in the record carries `pres_elec = False`, because
# none has ever fallen on a presidential general date. So the `pres_elec`
# breakout's False level is a mixture of midterm general elections and
# specials, and a bias figure read off it silently carries a population the
# reader is not thinking about -- specials being the model's worst segment by
# a wide margin. This splits the two apart. It sits alongside the `pres_elec`
# and `is_special` breakouts rather than replacing them, so no existing
# consumer of the scorecard loses a row (model-scoring spec, "Ballot timing is
# reported in three segments").
BALLOT_TIMING_LEVELS = [
    "presidential_general",
    "midterm_general",
    "special",
]


def ballot_timing(frame: pd.DataFrame) -> pd.Series:
    """Which of the three ballot-timing populations each race belongs to."""
    special = frame["is_special"].astype(bool)
    presidential = frame["pres_elec"].astype(bool)
    return pd.Series(
        np.where(
            special,
            "special",
            np.where(presidential, "presidential_general", "midterm_general"),
        ),
        index=frame.index,
    )

# Segment values that must be reported even when a definition admits no races
# in them, so a definition that empties a segment is visible as having done so
# rather than by the row's absence.
REQUIRED_SEGMENT_VALUES = {
    "is_special": ["True", "False"],
    "ballot_timing": BALLOT_TIMING_LEVELS,
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
    variant.validate(races.columns, races)
    # Expanded against the prepared frame: a categorical's indicator columns
    # only exist once `prepare` has built them, and a derived predictor only
    # exists once `derive` has computed it.
    prepared = variants.prepare(variants.restrict(variant, races))
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
            f"{len(prepared)} races that definition {definition.name!r} admits "
            f"and variant {variant.name!r} requires, so the effect cannot be "
            "estimated under this definition"
        )
    # Nothing downstream may fill a missing predictor in: a race whose money is
    # unknown is excluded by the variant's own `requires`, never imputed.
    variants.check_complete(variant, prepared, "admitted races")


def score_composite(
    variant: "variants.CompositeVariant",
    races: pd.DataFrame,
    definition: definitions.Definition,
    eligible: list[str] | None = None,
) -> tuple:
    """Score each component over the races it predicts, then join them.

    Each component runs through the ordinary per-fold loop on its own
    restricted races, so it gets the same priors, diagnostics, knowability
    checks and confounding refusal as any other fit. What the composite adds
    is that the components' holdouts partition the race set: routing assigns
    every race to exactly one, so concatenating their predictions is the join
    (margin-model spec, "A variant may be composite").
    """
    routed = variant.route(variants.with_flags(races))
    predictions, coefficients, diagnostics, skipped = [], [], [], []
    for value, component in sorted(variant.components.items()):
        holdout_races = routed[value]
        print(
            f"    component {value} ({component.name}): predicts "
            f"{len(holdout_races)} of {len(races)} races"
        )
        # The component is fit on its own `requires` over the whole frame --
        # the special model trains on general elections too -- but only ever
        # predicts the races routed to it. Its holdout is narrowed here; its
        # training set is not.
        component_races = variants.restrict(component, races)
        keep = component_races.index.isin(holdout_races.index)
        scoreable = (
            component_races["scoreable"].astype(bool)
            if "scoreable" in component_races.columns
            else pd.Series(True, index=component_races.index)
        )
        component_races = component_races.assign(scoreable=scoreable & keep)
        part = score_variant(
            component, component_races, definition, eligible, restricted=True
        )
        part_predictions, part_coefficients, part_diagnostics, part_skipped = part
        predictions.append(part_predictions.assign(component=component.name))
        coefficients.append(part_coefficients.assign(component=component.name))
        diagnostics.append(part_diagnostics.assign(component=component.name))
        skipped.extend(part_skipped)
    # A date is skipped for the composite only if no component covered it.
    # Each component necessarily skips the other's dates -- the general model
    # has no races on a special-election date -- so the union of the two
    # would report every date as skipped.
    covered = set(pd.concat(predictions, ignore_index=True)["fold"])
    skipped = [date for date in sorted(set(skipped)) if date not in covered]
    merged = []
    for frames in (predictions, coefficients, diagnostics):
        frame = pd.concat(frames, ignore_index=True)
        frame["variant"] = variant.name
        merged.append(frame)
    joined = merged[0]
    duplicated = joined.duplicated(subset=["definition", "election_id"]).sum()
    if duplicated:
        raise variants.CompositeRoutingError(
            f"composite variant {variant.name!r} produced {duplicated} "
            "duplicate holdout prediction(s); every race must be predicted by "
            "exactly one component"
        )
    return (merged[0], merged[1], merged[2], skipped)


def score_variant(
    variant: variants.Variant,
    races: pd.DataFrame,
    definition: definitions.Definition,
    eligible: list[str] | None = None,
    restricted: bool = False,
) -> tuple:
    """Fit and predict every fold for one variant under one definition."""
    if getattr(variant, "is_composite", False):
        return score_composite(variant, races, definition, eligible)
    # A composite has already narrowed each component's frame, so restricting
    # again here would be a no-op at best and would re-widen the holdout at
    # worst.
    admitted = races if restricted else variants.restrict(variant, races)
    if len(admitted) != len(races):
        print(
            f"    {variant.name} requires [{', '.join(variant.requires)}]: "
            f"{len(admitted)} of {len(races)} races admitted, "
            f"{len(races) - len(admitted)} excluded"
        )
    built, skipped = folds.build(admitted, eligible)
    predictions, coefficients, diagnostics = [], [], []

    for fold in built:
        # A dated predictor must have been measured before the election it
        # predicts, checked per fold against that fold's own holdout races.
        variants.check_as_of(variant, fold.holdout)
        try:
            fitted = fitmod.fit(
                variant, fold.train, fold=fold.key, definition=definition.name
            )
        except variants.GroupedPredictorError as exc:
            # The fold's training window cannot separate the predictor from the
            # variant's own grouping factor. Recording it keeps the refusal
            # visible in the published outputs instead of leaving a fold that
            # simply has no rows (margin-model spec, "An exactly confounded
            # predictor is refused").
            diagnostics.append(
                {
                    "definition": definition.name,
                    "variant": variant.name,
                    "fold": fold.key,
                    "n_holdout": fold.n_holdout,
                    **fitmod.refused(
                        variant, fold.key, definition.name, fold.n_train, str(exc)
                    ).as_row(),
                }
            )
            print(
                f"  fold {fold.key}: train {fold.n_train:>3}  holdout "
                f"{fold.n_holdout:>3}  REFUSED -- {exc}"
            )
            continue
        variants.check_complete(
            variant, variants.prepare(fold.holdout), f"fold {fold.key} holdout"
        )
        draws = fitted.predict_draws(fold.holdout)
        per_race = metrics.per_race(draws, fold.holdout["response"].to_numpy())

        frame = fold.holdout[IDENTITY].reset_index(drop=True)
        frame.insert(0, "definition", definition.name)
        frame.insert(1, "variant", variant.name)
        frame.insert(2, "fold", fold.key)
        predictions.append(pd.concat([frame, per_race], axis=1))

        coefficients.append(
            fitted.coefficients().assign(fold=fold.key, definition=definition.name)
        )
        diagnostics.append(
            {
                "definition": definition.name,
                "variant": variant.name,
                "fold": fold.key,
                "n_holdout": fold.n_holdout,
                **fitted.diagnostics.as_row(),
            }
        )
        flag = "" if fitted.diagnostics.passed else "  DIAGNOSTICS FAILED"
        print(
            f"  fold {fold.key}: train {fold.n_train:>3}  holdout {fold.n_holdout:>3}  "
            f"rmse {metrics.rmse(per_race):6.2f}{flag}"
        )

    if not predictions:
        # Every fold refused. The per-fold refusal rows are the finding, so
        # they travel on the exception: a caller scoring one variant wants the
        # failure, and a full run wants to record it and carry on to the next
        # variant (design.md, D6).
        exc = fitmod.UnidentifiablePredictorError(
            f"variant {variant.name!r} under definition {definition.name!r} was "
            f"refused on every one of its {len(built)} folds, so it has no "
            "holdout predictions to score"
        )
        exc.diagnostics = pd.DataFrame(diagnostics)
        exc.variant = variant.name
        exc.definition = definition.name
        raise exc
    return (
        pd.concat(predictions, ignore_index=True),
        pd.concat(coefficients, ignore_index=True),
        pd.DataFrame(diagnostics),
        skipped,
    )


def _refusal(value) -> str:
    """The refusal reason for a fold, or "" if it was fit.

    An empty reason written to CSV reads back as NaN, and NaN is truthy, so the
    emptiness test has to be a null check rather than a falsiness one.
    """
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def scorecard(
    predictions: pd.DataFrame,
    diagnostics: pd.DataFrame,
    skipped: list,
    eligible: list[str],
) -> pd.DataFrame:
    """Pooled, per-fold and per-segment metrics for every scored variant."""
    refused = {
        (row.definition, row.variant, row.fold)
        for row in diagnostics.itertuples()
        if _refusal(getattr(row, "refused_reason", None))
    }
    # A fold that was never fit is not a fold that sampled badly, so the two
    # are reported in separate columns rather than pooled into one flag.
    failed = {
        (row.definition, row.variant, row.fold)
        for row in diagnostics.itertuples()
        if not row.diagnostics_passed
    } - refused
    predictions = predictions.assign(ballot_timing=ballot_timing(predictions))
    rows = []
    for (definition_name, variant_name), group in predictions.groupby(
        ["definition", "variant"], sort=False
    ):
        variant_failed = sorted(
            fold
            for definition, name, fold in failed
            if name == variant_name and definition == definition_name
        )
        variant_as_of = sorted(
            {
                str(row.as_of)
                for row in diagnostics.itertuples()
                if row.variant == variant_name and row.definition == definition_name
                and str(getattr(row, "as_of", "")) not in ("", "nan")
            }
        )
        variant_refused = sorted(
            fold
            for definition, name, fold in refused
            if name == variant_name and definition == definition_name
        )
        # A fold a variant's own race restriction emptied. Reported rather than
        # left to the absence of a row: "this variant excluded every race on
        # that date" and "no election was held that day" must not look the
        # same, which is the same reason `skipped_dates` exists at the
        # definition level.
        variant_absent = sorted(
            set(eligible)
            - set(group["fold"].unique())
            - set(variant_refused)
            - set(skipped)
        )

        # Pooled over races, not averaged over folds: a special-election date
        # holds one race and a general holds ninety.
        # The presidential-date bias gap, on the pooled row because it is a
        # property of the variant rather than of either segment. A variant that
        # narrows it has absorbed a swing the single pres_elec term cannot,
        # which is visible here even when pooled RMSE is unchanged.
        #
        # Computed over general elections only. Every special carries
        # `pres_elec = False`, so leaving them in would let the
        # special-election segment -- the worst-calibrated population in the
        # model -- move a figure that is supposed to measure ballot timing
        # (model-scoring spec, "the gap is computed from general elections
        # only").
        timing = ballot_timing(group)
        presidential = group[timing == "presidential_general"]
        midterm = group[timing == "midterm_general"]
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
                "bias_presidential_general": bias_presidential,
                "bias_midterm_general": bias_midterm,
                "pres_bias_gap": bias_presidential - bias_midterm,
                "folds_failing_diagnostics": ",".join(str(f) for f in variant_failed),
                "folds_refused": ",".join(str(f) for f in variant_refused),
                "folds_absent": ",".join(str(f) for f in variant_absent),
                "as_of": ",".join(variant_as_of),
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
    # Per definition, derived from the predictions: an election date in the
    # record that this definition put no race into any holdout on. Derived
    # rather than carried in from the run, because a run that rescores one
    # definition and appends to the rest would otherwise stamp its own skipped
    # list onto every definition's rows.
    covered = predictions.groupby("definition")["fold"].agg(set).to_dict()
    card["skipped_dates"] = [
        ",".join(sorted(set(eligible) - covered.get(name, set())))
        for name in card["definition"]
    ]
    ordered = [
        "definition",
        "variant",
        "segment_type",
        "segment_value",
        "n_races",
        "small_sample",
        *metrics.METRIC_COLUMNS,
        "bias_presidential_general",
        "bias_midterm_general",
        "pres_bias_gap",
        "folds_failing_diagnostics",
        "folds_refused",
        "folds_absent",
        "as_of",
        "skipped_dates",
    ]
    return card[ordered]


# Outputs that do not depend on the fold schedule, and so are never stamped or
# checked against one. Which races a definition drops is decided by the
# definition's own rules before a fold exists; there is no such thing as
# mixing two schedules in it.
SCHEDULE_INDEPENDENT = {"definition_dropped_races.csv"}


def _check_schedule(frame, path) -> None:
    """Refuse to append onto outputs built under a different fold schedule.

    An appending run keeps rows it did not rescore. If those rows were
    computed on a different schedule the result is one file holding two
    incompatible sets of figures, which no reader could untangle. The stamp
    makes that checkable instead of a matter of remembering.
    """
    if frame is None or not len(frame):
        return
    if path.name in SCHEDULE_INDEPENDENT:
        return
    if "fold_schedule" not in frame.columns:
        # Written before the schedule was stamped, so it is by definition a
        # different one: the stamp was introduced with the move to date folds.
        raise ValueError(
            f"{path} holds rows carrying no fold_schedule stamp, so they "
            f"predate the current schedule ({folds.SCHEDULE_ID}). Appending "
            "would mix two schedules in one file. Rescore without --append to "
            "replace them."
        )
    found = set(frame["fold_schedule"].dropna().unique())
    stale = found - {folds.SCHEDULE_ID}
    if stale or frame["fold_schedule"].isna().any():
        raise ValueError(
            f"{path} holds figures computed under fold schedule(s) "
            f"{sorted(stale) or ['(unstamped)']}, but this run is on "
            f"{folds.SCHEDULE_ID!r}. Appending would mix two schedules in one "
            "file. Rescore without --append to replace them."
        )


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
            # Only the rows this run is not replacing need checking: a cell
            # being rescored is about to be overwritten with current figures
            # whatever schedule produced the old ones.
            if "definition" in existing.columns:
                retained = keep(existing, has_variant)
                _check_schedule(retained, path)
                frame = pd.concat([retained, frame], ignore_index=True)
        merged.append(frame)
    return tuple(merged)


def fold_summary(
    races: pd.DataFrame,
    definition: definitions.Definition,
    eligible: list[str] | None = None,
) -> dict:
    """The holdout counts a definition produces, reported per definition."""
    built, skipped = folds.build(races, eligible)
    return {
        "definition": definition.name,
        "response": definition.response,
        "races": len(races),
        "pooled_holdout": sum(fold.n_holdout for fold in built),
        "holdout_specials": sum(
            int(fold.holdout["is_special"].astype(bool).sum()) for fold in built
        ),
        "smallest_training_fold": min((fold.n_train for fold in built), default=0),
        "folds": len(built),
        "general_dates": sum(1 for fold in built if not fold.is_special_date),
        "special_dates": sum(1 for fold in built if fold.is_special_date),
        "skipped_dates": ",".join(str(d) for d in skipped),
    }


def run(
    variant_names=None,
    definition_names=None,
    write=True,
    append=False,
    schedule_change=False,
) -> pd.DataFrame:
    """Score the selected variants under the selected definitions.

    `schedule_change` declares that the fold schedule itself has changed, so
    every variant's numbers move whether or not its model did. A run under
    that flag makes no claim that an untouched variant is unchanged --- the
    seed is derived from the fold, so there are no untouched variants --- and
    states instead that every previously published figure is superseded
    (model-scoring spec, "A schedule change supersedes every published
    figure").
    """
    races_table = config.load_races()
    roster = config.load_roster()
    # Every election date in the record, which the schedule is measured
    # against. Derived once from the unfiltered table so that a date a
    # definition or a variant's `requires` empties is reported as skipped
    # rather than silently absent from the schedule.
    eligible = folds.fold_dates(races_table)
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
        summary = fold_summary(races, definition, eligible)
        summaries.append(summary)
        all_skipped.extend(d for d in summary["skipped_dates"].split(",") if d)

        print(f"\ndefinition {definition.name}: {definition.description}")
        print(
            f"  {summary['races']} races, pooled holdout {summary['pooled_holdout']} "
            f"({summary['holdout_specials']} specials), smallest training fold "
            f"{summary['smallest_training_fold']}, "
            f"{summary['folds']} folds "
            f"({summary['general_dates']} general, {summary['special_dates']} special), "
            f"election dates with no admitted races: "
            f"{summary['skipped_dates'] or 'none'}"
        )
        print(folds.schedule(races, eligible).to_string(index=False))

        for variant in selected_variants:
            check_compatible(variant, definition, races)
            print(f"\n  {variant.name}: {variant.declared}")
            try:
                predictions, coefficients, diagnostics, _ = score_variant(
                    variant, races, definition, eligible
                )
            except fitmod.UnidentifiablePredictorError as exc:
                # A variant every fold refuses has no predictions and so no
                # scorecard row, but the refusal is a result and is published:
                # its per-fold rows go to the diagnostics, where a reader can
                # see the predictor and the grouping factor that collided
                # (margin-model spec, "An exactly confounded predictor is
                # refused"). The run continues to the next variant rather than
                # taking every other variant's rescore down with it.
                refused = getattr(exc, "diagnostics", None)
                if refused is not None and len(refused):
                    all_diagnostics.append(refused)
                print(f"    REFUSED ON EVERY FOLD -- {exc}")
                print("    recorded in fit_diagnostics; no scorecard row")
                continue
            all_predictions.append(predictions)
            all_coefficients.append(coefficients)
            all_diagnostics.append(diagnostics)

    if not all_predictions:
        raise fitmod.UnidentifiablePredictorError(
            "every selected variant was refused on every fold under every "
            "selected definition, so there is nothing to score"
        )
    predictions = pd.concat(all_predictions, ignore_index=True)
    coefficients = pd.concat(all_coefficients, ignore_index=True)
    diagnostics = pd.concat(all_diagnostics, ignore_index=True)
    card = scorecard(predictions, diagnostics, sorted(set(all_skipped)), eligible)
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
        card = scorecard(
            predictions, diagnostics, sorted(set(all_skipped)), eligible
        )

    if schedule_change:
        print(
            f"\nSCHEDULE CHANGE ({folds.SCHEDULE_ID}): folds are keyed on "
            "election_date, and fit.seed_for hashes the fold, so every fit "
            f"under the {len(selected_variants)} selected variant(s) is "
            "reseeded. No variant's figures are carried over and none is "
            "verified unchanged: every previously published figure is "
            "superseded, not reproduced."
        )

    if write:
        stamp = folds.SCHEDULE_ID
        config.write_csv(predictions.assign(fold_schedule=stamp), config.HOLDOUT_PREDICTIONS)
        config.write_csv(card.round(6).assign(fold_schedule=stamp), config.SCORECARD)
        config.write_csv(coefficients.round(6).assign(fold_schedule=stamp), config.COEFFICIENTS)
        config.write_csv(diagnostics.assign(fold_schedule=stamp), config.FIT_DIAGNOSTICS)
        config.write_csv(summary_frame.assign(fold_schedule=stamp), config.DEFINITION_SUMMARY)
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
