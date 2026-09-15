"""Variable importance for a fitted variant, measured three ways.

A coefficient alone does not say how much a predictor matters. A large
coefficient on a near-constant predictor moves nothing, and a well-identified
coefficient can still cost accuracy out of sample -- which is exactly what
`pres_elec` does here. So three measures are reported side by side:

- **the marginal effect**, the coefficient itself: the change in the response
  per unit of the predictor, holding the others constant, which is exact
  rather than approximate because the model is linear and additive;
- **the contribution spread**, the standard deviation of the term's own
  contribution to the fitted response, which folds the coefficient and the
  predictor's real spread into one comparable number;
- **the drop-one cost**, the change in pooled holdout RMSE when the predictor
  is removed and the rest refit over the same folds and the same races, with
  the same paired bootstrap interval every other comparison in this project
  uses (model-scoring spec, "Two variants are compared on identical folds and
  races").

The drop-one arms are analysis fits: they are not registered variants and they
write nothing into the scorecard. Every arm keeps the full variant's `requires`
so all of them score identical races, which is what makes the comparison
paired.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import compare, config, definitions as definitions_module, score, variants

REPORT = config.MODEL_DIR / "variable_importance.csv"

COLUMNS = [
    "definition",
    "variant",
    "predictor",
    "parameter",
    "coefficient",
    "eti89_lb",
    "eti89_ub",
    "fold_min",
    "fold_max",
    "contribution_sd",
    "contribution_iqr",
    "predictor_sd",
    "drop_one_rmse",
    "drop_one_cost",
    "ci_low",
    "ci_high",
    "decided",
]


def _arm(variant: variants.Variant, dropped: str) -> variants.Variant:
    """The variant with one declared predictor removed.

    The as-of declaration goes with it when the dropped predictor was the only
    dated one, because a variant declaring a date and carrying nothing measured
    to it is refused -- correctly.
    """
    kept = tuple(p for p in variant.predictors if p != dropped)
    dated = any(p in variants.DATED_PREDICTORS for p in kept)
    return variants.Variant(
        name=f"{variant.name}__drop_{dropped}",
        predictors=kept,
        response=variant.response,
        group_effects=variant.group_effects,
        priors=variant.priors,
        target_accept=variant.target_accept,
        tune=variant.tune,
        as_of=variant.as_of if dated else "",
        requires=variant.requires,
        description=f"{variant.name} without {dropped}, for drop-one importance",
    )


def contribution(frame: pd.DataFrame, predictor: str, coefficients: pd.Series):
    """The spread of one declared predictor's contribution to the fitted response.

    A categorical contributes through every indicator it expands to, so the
    indicators are summed before the spread is taken: the quantity of interest
    is what `incumbent_status` moves, not what `incumbent_gop` moves on its own.
    """
    total = np.zeros(len(frame), dtype=float)
    for column in variants.expand(predictor):
        total = total + coefficients[column] * frame[column].to_numpy(dtype=float)
    q1, q3 = np.percentile(total, [25, 75])
    return float(total.std()), float(q3 - q1)


def run(
    variant_name: str = "baseline_money_logratio",
    definition_name: str | None = None,
    write: bool = True,
    append: bool = False,
) -> pd.DataFrame:
    """Fit the full variant and every drop-one arm, and report all three measures."""
    variant = variants.get(variant_name)
    definition = (
        definitions_module.adopted()
        if definition_name is None
        else definitions_module.get(definition_name)
    )
    races, _ = definitions_module.apply(definition)
    fitted_races = variants.prepare(variants.restrict(variant, races))

    print(f"\nvariable importance for {variant.name}: {variant.declared}")
    print(f"  definition {definition.name}, {len(fitted_races)} races fit")

    print(f"\n=== full model ===")
    full_predictions, coefficients, _, _ = score.score_variant(
        variant, races, definition
    )
    folds = sorted(coefficients["fold"].unique())
    final = coefficients[coefficients["fold"] == folds[-1]].set_index("parameter")
    spread = coefficients.groupby("parameter")["mean"].agg(["min", "max"])
    full_rmse = float(np.sqrt(full_predictions["squared_error"].mean()))
    print(
        f"  pooled holdout {len(full_predictions)} races over {len(folds)} folds, "
        f"rmse {full_rmse:.3f}; coefficients from the final fold ({folds[-1]})"
    )

    rng = np.random.default_rng(compare.BOOTSTRAP_SEED)
    rows = []
    for predictor in variant.predictors:
        print(f"\n=== without {predictor} ===")
        arm = _arm(variant, predictor)
        arm_predictions, _, _, _ = score.score_variant(arm, races, definition)
        paired = full_predictions[["election_id", "fold", "squared_error"]].merge(
            arm_predictions[["election_id", "fold", "squared_error"]],
            on=["election_id", "fold"],
            suffixes=("_left", "_right"),
        )
        if len(paired) != len(full_predictions):
            raise RuntimeError(
                f"dropping {predictor!r} changed the holdout from "
                f"{len(full_predictions)} races to {len(paired)}; the comparison "
                "would not be paired"
            )
        without = float(np.sqrt(paired["squared_error_right"].mean()))
        cost = without - full_rmse
        # `bootstrap_difference` returns full-minus-arm; the cost of losing the
        # predictor is the other sign.
        draws = -compare.bootstrap_difference(paired, rng)
        low, high = np.percentile(draws, compare.INTERVAL_PERCENTILES)
        sd, iqr = contribution(fitted_races, predictor, final["mean"])

        for parameter in variants.expand(predictor):
            row = final.loc[parameter]
            rows.append(
                {
                    "definition": definition.name,
                    "variant": variant.name,
                    "predictor": predictor,
                    "parameter": parameter,
                    "coefficient": row["mean"],
                    "eti89_lb": row["eti89_lb"],
                    "eti89_ub": row["eti89_ub"],
                    "fold_min": spread.loc[parameter, "min"],
                    "fold_max": spread.loc[parameter, "max"],
                    "contribution_sd": sd,
                    "contribution_iqr": iqr,
                    "predictor_sd": float(
                        fitted_races[parameter].to_numpy(dtype=float).std()
                    ),
                    "drop_one_rmse": without,
                    "drop_one_cost": cost,
                    "ci_low": float(low),
                    "ci_high": float(high),
                    "decided": not (low <= 0 <= high),
                }
            )

    report = pd.DataFrame(rows, columns=COLUMNS).sort_values(
        "drop_one_cost", ascending=False, ignore_index=True
    )
    if write:
        rounded = report.round(6)
        if append:
            # Measuring one variant's importance must not delete another's
            # published rows, the same posture `score --append` takes.
            rounded = config.merge_cells(rounded, REPORT, ["definition", "variant"])
        config.write_csv(rounded, REPORT)

    print(f"\nfull model rmse {full_rmse:.3f} on {len(full_predictions)} holdout races")
    print("\ndrop-one cost in pooled RMSE (positive means the model needs it):")
    print(
        report.drop_duplicates("predictor")[
            ["predictor", "drop_one_rmse", "drop_one_cost", "ci_low", "ci_high",
             "contribution_sd", "decided"]
        ]
        .round(3)
        .to_string(index=False)
    )
    print("\nmarginal effect per unit of predictor, holding the others constant:")
    print(
        report[["parameter", "coefficient", "eti89_lb", "eti89_ub", "fold_min",
                "fold_max"]]
        .round(3)
        .to_string(index=False)
    )
    return report
