"""Run the operational tenure-replacement or legacy tenure experiment."""

from __future__ import annotations

import pandas as pd

from . import compare, config, definitions, score, variants

LEGACY_REFERENCE_VARIANT = "baseline"
LEGACY_TENURE_VARIANTS = [
    "baseline_tenure_cap4",
    "baseline_tenure_cap2",
    "baseline_tenure_cap6",
]
OPERATIONAL_VARIANTS = [
    "forecast_14d",
    "forecast_tenure_replacement_14d",
    "forecast_60d",
    "forecast_tenure_replacement_60d",
]


def _publish(reports: list[pd.DataFrame], write: bool) -> pd.DataFrame:
    """Publish selected comparisons while preserving unrelated cells."""
    sensitivities = [report.attrs["sensitivity"] for report in reports]
    for report in reports:
        report.attrs = {}
    output = pd.concat(reports, ignore_index=True).round(6)
    sensitivity = pd.concat(sensitivities, ignore_index=True).round(6)
    if write:
        output = config.merge_cells(
            output,
            config.VARIANT_COMPARISON,
            ["definition", "left_variant", "right_variant"],
        )
        sensitivity = config.merge_cells(
            sensitivity,
            config.VARIANT_COMPARISON_SENSITIVITY,
            ["definition", "left_variant", "right_variant"],
        )
        historical = {
            LEGACY_REFERENCE_VARIANT,
            *LEGACY_TENURE_VARIANTS,
        }
        legacy_rows = (
            output["left_variant"].isin(historical)
            & output["right_variant"].isin(historical)
            & (
                output["left_variant"].isin(LEGACY_TENURE_VARIANTS)
                | output["right_variant"].isin(LEGACY_TENURE_VARIANTS)
            )
        )
        output.loc[legacy_rows, "left_experiment_role"] = "historical_benchmark"
        output.loc[legacy_rows, "right_experiment_role"] = "historical_benchmark"
        output.loc[legacy_rows, "experiment"] = "legacy_baseline_tenure"
        output.loc[legacy_rows, "comparison_role"] = "historical_benchmark"
        output.loc[legacy_rows, "decision_row"] = False
        output.loc[legacy_rows, "adoption_decision"] = (
            "historical_not_operational_decision"
        )
        config.write_csv(output, config.VARIANT_COMPARISON)
        config.write_csv(sensitivity, config.VARIANT_COMPARISON_SENSITIVITY)
    return output


def run_legacy(write: bool = True) -> pd.DataFrame:
    """Reproduce the incremental-tenure historical benchmark."""
    definition_names = list(definitions.all_definitions())
    score.run(
        [LEGACY_REFERENCE_VARIANT, *LEGACY_TENURE_VARIANTS],
        definition_names,
        write=write,
        append=write,
    )

    reports = []
    for definition_name in definition_names:
        for variant_name in LEGACY_TENURE_VARIANTS:
            result = compare.run(
                LEGACY_REFERENCE_VARIANT, variant_name, definition_name, write=False
            )
            reports.append(result)
    return _publish(reports, write)


def run(write: bool = True) -> pd.DataFrame:
    """Score the frozen controls and both tenure-replacement challengers."""
    variants.validate_tenure_replacement_experiment()
    definition_name = variants.TENURE_REPLACEMENT_DEFINITION
    score.run(
        OPERATIONAL_VARIANTS,
        [definition_name],
        write=write,
        append=write,
    )
    reports = []
    for declaration in variants.TENURE_REPLACEMENT_EXPERIMENT[
        "comparisons"
    ].values():
        reports.append(
            compare.run(
                declaration["control"],
                declaration["challenger"],
                definition_name,
                write=False,
            )
        )
    return _publish(reports, write)
