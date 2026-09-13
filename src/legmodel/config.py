"""Paths and shared constants for the modelling package."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = ROOT / "data"
RACE_DIR = DATA_DIR / "race"
MODEL_DIR = DATA_DIR / "models"
REPORT_DIR = DATA_DIR / "reports"

RACE_TRAINING_SET = RACE_DIR / "ma_race_training_set.csv.gz"

HOLDOUT_PREDICTIONS = MODEL_DIR / "holdout_predictions.csv.gz"
SCORECARD = MODEL_DIR / "scorecard.csv"
VARIANT_COMPARISON = MODEL_DIR / "variant_comparison.csv"
COEFFICIENTS = MODEL_DIR / "coefficients.csv"
FIT_DIAGNOSTICS = MODEL_DIR / "fit_diagnostics.csv"

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


def write_csv(frame, path, compress: bool | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if compress is None:
        compress = path.name.endswith(".gz")
    frame.to_csv(path, index=False, compression="gzip" if compress else None)
    print(f"wrote {len(frame):>7} rows -> {path.relative_to(ROOT)}")
