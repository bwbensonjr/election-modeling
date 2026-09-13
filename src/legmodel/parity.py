"""Check the baseline fit against the same fit on mapoli's district table.

The race table is newly built from precinct returns, so before its scores mean
anything it has to be shown to carry the same model. Fitting the identical
variant on the reference table restricted to the same races isolates the data
from the model: a coefficient that moves is a difference in the table, not in
the formula (margin-model spec, "Baseline coefficients match a fit on the
reference table").
"""

from __future__ import annotations

import pandas as pd

from . import config, fit as fitmod, variants

PARITY_REPORT = config.MODEL_DIR / "coefficient_parity.csv"

# Posterior means from two independent MCMC runs differ a little by chance even
# on identical data, so the tolerance is a fraction of each coefficient's own
# posterior standard deviation rather than an absolute number of points.
TOLERANCE_SD_FRACTION = 0.25

ROLLUP_REPORT = config.REPORT_DIR / "race_rollup_validation.csv"


def concordant_races(races: pd.DataFrame) -> set:
    """Races where the two tables carry the same margin and the same PVI.

    The rollup validation shows the tables differ on 27 margins and 77 PVI
    values, every one for a documented reason. Fitting both sides on the races
    where they do agree separates the question "is this the same model" from
    the question "is this the same data".
    """
    if not ROLLUP_REPORT.exists():
        return set()
    report = pd.read_csv(ROLLUP_REPORT)
    agreeing = report[
        (report["margin_category"] == "agrees") & (report["pvi_category"] == "agrees")
    ]
    return set(agreeing["election_id"])


def pvi_offsets() -> pd.DataFrame:
    """The constant PVI shift per vintage, from the rollup validation.

    This pipeline normalises PVI against FEC national two-party totals; mapoli
    used a slightly different national baseline. That shifts every district in
    a PVI vintage by the same amount, so it moves the intercept of any fit on
    the reference table without saying anything about the model.
    """
    if not ROLLUP_REPORT.exists():
        return pd.DataFrame(columns=["election_id", "pvi_offset"])
    report = pd.read_csv(ROLLUP_REPORT)
    return report[["election_id", "pvi_offset"]].dropna()


def reference_races(races: pd.DataFrame) -> pd.DataFrame:
    """mapoli's district table, restricted to the races this table covers.

    Its `dem_margin` is wrong for the no-Democrat races through the operator
    precedence bug documented in docs/schema.md, so those races are dropped
    from both sides: keeping them would compare our model against a fit on
    known-bad response values.
    """
    reference = pd.read_csv(config.MAPOLI_DISTRICT_TABLE)
    usable = races.loc[~races["no_dem_candidate"], "election_id"]
    reference = reference[reference["election_id"].isin(usable)].copy()
    reference["incumbent_status"] = pd.Categorical(
        reference["incumbent_status"], categories=variants.CATEGORICAL_LEVELS["incumbent_status"]
    )
    return reference.dropna(subset=["dem_margin", "PVI_N", "incumbent_status"])


def _compare(variant, ours, reference, scope: str) -> pd.DataFrame:
    """Fit the variant on both tables over the same races and compare."""
    left = fitmod.fit(variant, ours, fold=f"parity_ours_{scope}").coefficients()
    right = fitmod.fit(variant, reference, fold=f"parity_ref_{scope}").coefficients()
    report = pd.DataFrame(
        {
            "variant": variant.name,
            "scope": scope,
            "n_races": len(ours),
            "race_table_mean": left.set_index("parameter")["mean"],
            "race_table_sd": left.set_index("parameter")["sd"],
            "reference_mean": right.set_index("parameter")["mean"],
            "reference_sd": right.set_index("parameter")["sd"],
        }
    ).reset_index()
    worst_sd = report[["race_table_sd", "reference_sd"]].max(axis=1)
    report["difference"] = report["race_table_mean"] - report["reference_mean"]
    report["difference_in_sd"] = report["difference"] / worst_sd
    report["tolerance"] = TOLERANCE_SD_FRACTION * worst_sd
    report["within_tolerance"] = report["difference"].abs() <= report["tolerance"]
    return report


def run(variant_name: str = "baseline") -> pd.DataFrame:
    variant = variants.get(variant_name)
    races = config.load_races()

    if not config.MAPOLI_DISTRICT_TABLE.exists():
        print(
            f"SKIP parity check: {config.MAPOLI_DISTRICT_TABLE} not found "
            "(needs a sibling mapoli checkout)"
        )
        return pd.DataFrame()

    reference = reference_races(races)
    ours = races[races["election_id"].isin(reference["election_id"])]
    print(
        f"parity check on {len(ours)} races present in both tables "
        f"({len(races) - len(ours)} excluded: no-Democrat races, whose reference "
        "margin is known wrong)"
    )

    reports = [_compare(variant, ours, reference, "all_comparable")]

    # The same fit restricted to the races where the two tables carry identical
    # inputs. If the model is the same, these coefficients must coincide, and
    # whatever remains in the full-sample comparison is the documented data
    # difference rather than a difference in the model.
    concordant = concordant_races(races) & set(ours["election_id"])
    if concordant:
        print(
            f"and on the {len(concordant)} of those races where the two tables "
            "carry identical margin and PVI"
        )
        reports.append(
            _compare(
                variant,
                ours[ours["election_id"].isin(concordant)],
                reference[reference["election_id"].isin(concordant)],
                "concordant_inputs",
            )
        )

    # Finally, the same races with the reference's PVI shifted onto this
    # pipeline's national baseline. With the one documented definitional
    # difference removed, coefficients that still disagree would be a real
    # disagreement about the model.
    offsets = pvi_offsets()
    if concordant and len(offsets):
        adjusted = reference[reference["election_id"].isin(concordant)].merge(
            offsets, on="election_id", how="left"
        )
        adjusted["PVI_N"] = adjusted["PVI_N"] + adjusted["pvi_offset"].fillna(0.0)
        print(
            "and again with the reference's PVI shifted onto this pipeline's "
            "national baseline"
        )
        reports.append(
            _compare(
                variant,
                ours[ours["election_id"].isin(concordant)],
                adjusted,
                "concordant_baseline_aligned",
            )
        )

    report = pd.concat(reports, ignore_index=True)
    config.write_csv(report.round(6), PARITY_REPORT)

    for scope, group in report.groupby("scope", sort=False):
        outside = group[~group["within_tolerance"]]
        print(f"\n-- {scope} ({group['n_races'].iloc[0]} races) --")
        print(
            group[
                [
                    "parameter",
                    "race_table_mean",
                    "reference_mean",
                    "difference",
                    "difference_in_sd",
                    "within_tolerance",
                ]
            ]
            .round(4)
            .to_string(index=False)
        )
        if len(outside):
            print(
                f"   {len(outside)} of {len(group)} outside "
                f"{TOLERANCE_SD_FRACTION} posterior SD: {list(outside['parameter'])}"
            )
        else:
            print(
                f"   all {len(group)} coefficients agree within "
                f"{TOLERANCE_SD_FRACTION} posterior SD"
            )
    return report
