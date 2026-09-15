"""Paths and shared constants for the modelling package."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = ROOT / "data"
RACE_DIR = DATA_DIR / "race"
MODEL_DIR = DATA_DIR / "models"
REPORT_DIR = DATA_DIR / "reports"

RACE_TRAINING_SET = RACE_DIR / "ma_race_training_set.csv.gz"
RACE_CANDIDATE_ROSTER = RACE_DIR / "ma_race_candidates.csv.gz"

HOLDOUT_PREDICTIONS = MODEL_DIR / "holdout_predictions.csv.gz"
SCORECARD = MODEL_DIR / "scorecard.csv"
VARIANT_COMPARISON = MODEL_DIR / "variant_comparison.csv"
COEFFICIENTS = MODEL_DIR / "coefficients.csv"
FIT_DIAGNOSTICS = MODEL_DIR / "fit_diagnostics.csv"
DEFINITION_SUMMARY = MODEL_DIR / "definition_summary.csv"
DEFINITION_DROPPED = MODEL_DIR / "definition_dropped_races.csv"
DEFINITION_COMPARISON = MODEL_DIR / "definition_comparison.csv"
THRESHOLD_SWEEP = MODEL_DIR / "threshold_sweep.csv"

RESPONSE = "dem_margin"

# mapoli's district-level table, read only for the coefficient parity check.
MAPOLI_DISTRICT_TABLE = (
    ROOT.parent / "mapoli" / "model" / "ma_leg_two_party_2008_2025.csv"
)


def load_races() -> "pd.DataFrame":  # noqa: F821
    """The committed race-grain training table."""
    import pandas as pd

    if not RACE_TRAINING_SET.exists():
        raise FileNotFoundError(
            f"{RACE_TRAINING_SET.relative_to(ROOT)} is missing; "
            "run `uv run maprecinct races` first"
        )
    return pd.read_csv(RACE_TRAINING_SET)


def load_roster() -> "pd.DataFrame":  # noqa: F821
    """The committed race candidate roster.

    A write-in threshold is a query on this: it carries every named candidate's
    district votes and share, so an admitted set is exact rather than inferred
    from the race table's aggregate write-in columns.
    """
    import pandas as pd

    if not RACE_CANDIDATE_ROSTER.exists():
        raise FileNotFoundError(
            f"{RACE_CANDIDATE_ROSTER.relative_to(ROOT)} is missing; "
            "run `uv run maprecinct races` first"
        )
    return pd.read_csv(RACE_CANDIDATE_ROSTER)


def merge_cells(report, path, key):
    """Replace the reported cells in a committed output, keeping the rest.

    The same posture `score --append` takes: a run that recomputes some cells
    of a published table must not delete the cells it did not recompute. The
    key names what a cell is -- a comparison is identified by its two sides and
    the definition it ran under -- and every row of the committed file matching
    one of the reported cells is dropped before the fresh rows are added.
    """
    if not path.exists():
        return report
    import pandas as pd

    existing = pd.read_csv(path)
    if not set(key) <= set(existing.columns):
        # Written before this key existed, so nothing in it can be matched
        # against the fresh cells; replacing wholesale is the only honest
        # option and the caller sees the row count change.
        return report
    fresh = {tuple(row) for row in report[key].astype(str).to_numpy().tolist()}
    keep = [
        tuple(row) not in fresh
        for row in existing[key].astype(str).to_numpy().tolist()
    ]
    return pd.concat([existing[keep], report], ignore_index=True)


def write_csv(frame, path, compress: bool | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if compress is None:
        compress = path.name.endswith(".gz")
    frame.to_csv(path, index=False, compression="gzip" if compress else None)
    print(f"wrote {len(frame):>7} rows -> {path.relative_to(ROOT)}")
