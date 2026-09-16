"""Run the pre-declared incumbency-tenure experiment."""

from __future__ import annotations

import pandas as pd

from . import compare, config, definitions, score, variants

REFERENCE_VARIANT = "baseline"
TENURE_VARIANTS = [
    "baseline_tenure_cap4",
    "baseline_tenure_cap2",
    "baseline_tenure_cap6",
]


def run(write: bool = True) -> pd.DataFrame:
    """Score and compare the primary tenure arm and both sensitivities."""
    definition_names = list(definitions.all_definitions())
    score.run(
        [REFERENCE_VARIANT, *TENURE_VARIANTS],
        definition_names,
        write=write,
        append=write,
    )

    reports, sensitivities = [], []
    for definition_name in definition_names:
        for variant_name in TENURE_VARIANTS:
            result = compare.run(
                REFERENCE_VARIANT, variant_name, definition_name, write=False
            )
            reports.append(result)
            sensitivities.append(result.attrs["sensitivity"])
            result.attrs = {}

    report = pd.concat(reports, ignore_index=True).round(6)
    sensitivity = pd.concat(sensitivities, ignore_index=True).round(6)
    if write:
        report = config.merge_cells(
            report,
            config.VARIANT_COMPARISON,
            ["definition", "left_variant", "right_variant"],
        )
        sensitivity = config.merge_cells(
            sensitivity,
            config.VARIANT_COMPARISON_SENSITIVITY,
            ["definition", "left_variant", "right_variant"],
        )
        config.write_csv(report, config.VARIANT_COMPARISON)
        config.write_csv(sensitivity, config.VARIANT_COMPARISON_SENSITIVITY)
    return report
