"""Sweep the write-in threshold across its candidate values.

A single threshold test would answer the wrong question. What matters is where
the threshold stops making a difference: between two values that admit the same
races and produce the same denominators, the choice is arbitrary, and saying so
is more honest than defending one of them (model-scoring spec, "Write-in
thresholds are reported as a sweep").
"""

from __future__ import annotations

import pandas as pd

from . import config, definitions, metrics, score, variants

# The values the README tabulates, plus the build threshold. 15% admits no
# further races, which is what makes it the top of a useful range.
THRESHOLDS = (0.0, 0.02, 0.05, 0.08, 0.10, 0.15)


def _definition_for(threshold: float) -> definitions.Definition:
    return definitions.Definition(
        name=f"write_in_{threshold:.0%}".replace("%", "pct"),
        response="dem_margin",
        write_in_threshold=threshold,
        no_dem=definitions.NO_DEM_KEEP,
        criteria=(),
        description=f"a write-in at or above {threshold:.0%} counts as a candidate",
    )


def run(variant_name: str = "baseline", score_each: bool = True) -> pd.DataFrame:
    races, roster = config.load_races(), config.load_roster()
    variant = variants.get(variant_name)
    baseline_ballot_line, _ = definitions.apply(
        definitions.get("current"), races, roster
    )
    ballot_line_ids = set(baseline_ballot_line["election_id"])

    rows = []
    for threshold in THRESHOLDS:
        definition = _definition_for(threshold)
        definition.validate()
        admitted, dropped = definitions.apply(definition, races, roster)
        summary = score.fold_summary(admitted, definition)
        added = sorted(set(admitted["election_id"]) - ballot_line_ids)
        # `races_admitted` counts publishable races. It runs below the raw
        # contested count the README tabulates (16/10/3/1/1/0 over the
        # ballot-line rule) because six all-Democratic fields are contested but
        # carry no non-Democratic candidate to measure a margin against, so the
        # roster -- which covers published races only -- never sees them.
        row = {
            "threshold": threshold,
            "races_admitted": len(admitted),
            "added_over_ballot_line_rule": len(added),
            "races_dropped": len(dropped),
            "pooled_holdout": summary["pooled_holdout"],
            "holdout_specials": summary["holdout_specials"],
            "smallest_training_fold": summary["smallest_training_fold"],
        }
        if score_each:
            print(f"\nthreshold {threshold:.0%}: {len(admitted)} races")
            predictions, _, _, _ = score.score_variant(variant, admitted, definition)
            row.update(
                {"variant": variant.name, **metrics.aggregate(predictions)}
            )
        rows.append(row)

    frame = pd.DataFrame(rows)

    # Where consecutive thresholds admit the same races, the choice between
    # them changes nothing and should not be presented as a finding.
    frame["same_races_as_previous"] = (
        frame["races_admitted"].diff().fillna(-1).eq(0)
    )
    settled = frame[frame["same_races_as_previous"]]["threshold"]
    frame["admissions_settle_at"] = float(settled.iloc[0]) if len(settled) else float("nan")
    return frame
