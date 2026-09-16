"""Full-history fitting and immutable forecast snapshot publication."""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from . import config, definitions, forecast, variants
from . import fit as fitmod

HORIZON_WINDOWS = {"60d": "wide", "14d": "primary"}
HORIZON_DAYS = {"60d": 60, "14d": 14}
SNAPSHOT_FILES = (
    "races.csv",
    "chamber_draws.csv.gz",
    "support_warnings.csv",
    "manifest.json",
)


class ForecastRunError(ValueError):
    """A forecast run violates its horizon, coverage, or snapshot contract."""


def file_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def bytes_digest(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def historical_training(
    target_date: str,
    definition: definitions.Definition,
    races: pd.DataFrame | None = None,
    roster: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Definition-admitted completed races held strictly before the target."""
    admitted, _ = definitions.apply(definition, races, roster)
    training = admitted[
        pd.to_datetime(admitted["election_date"]) < pd.Timestamp(target_date)
    ].copy()
    if training.empty:
        raise ForecastRunError(f"no completed training races precede {target_date}")
    return training.sort_values(["election_date", "election_id"], ignore_index=True)


def seed_inputs(
    variant: str,
    component: str,
    definition: str,
    training_cutoff: str,
    target_election: str,
    horizon: str,
) -> dict:
    return {
        "variant": variant,
        "component": component,
        "definition": definition,
        "training_cutoff": training_cutoff,
        "target_election": target_election,
        "horizon": horizon,
    }


def stable_seed(**inputs: str) -> int:
    payload = json.dumps(inputs, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % (2**31 - 1)


def attach_finance(
    target: pd.DataFrame, finance: pd.DataFrame, horizon: str
) -> pd.DataFrame:
    """Attach the candidate snapshot to the target in historical column form."""
    if horizon not in HORIZON_WINDOWS:
        raise ForecastRunError(f"unknown forecast horizon {horizon!r}")
    target = forecast.validate_target(target).copy()
    expected_cutoff = (
        pd.Timestamp(target["election_date"].iloc[0])
        - pd.Timedelta(days=HORIZON_DAYS[horizon])
    ).date().isoformat()
    if set(finance["horizon"].astype(str)) != {horizon}:
        raise ForecastRunError("finance snapshot horizon does not match forecast")
    if set(finance["cutoff"].astype(str)) != {expected_cutoff}:
        raise ForecastRunError(
            f"finance snapshot cutoff is not {expected_cutoff} for {horizon}"
        )
    duplicates = finance.duplicated(["target_id", "role"], keep=False)
    if duplicates.any():
        raise ForecastRunError("finance snapshot has duplicate target candidate rows")
    if set(finance["role"]) != {"dem", "opp"}:
        raise ForecastRunError("finance snapshot must carry dem and opp roles")
    window = HORIZON_WINDOWS[horizon]
    values = finance.pivot(index="target_id", columns="role")
    attached = target.set_index("target_id")
    for measure in ("receipts", "expenditures"):
        for role in ("dem", "opp"):
            attached[f"{role}_{measure}_{window}"] = pd.to_numeric(
                values[measure][role], errors="coerce"
            )
    complete = finance.groupby("target_id")["available"].agg(
        lambda flags: len(flags) == 2 and bool(flags.all())
    )
    attached["money_complete"] = complete
    attached[f"money_complete_{horizon}"] = complete
    attached[f"money_as_of_{window}"] = expected_cutoff
    attached = attached.reset_index()
    attached["election_year"] = attached["election_date"].astype(str).str[:4].astype(int)
    attached["is_special"] = False
    attached["pres_elec"] = False
    return attached


def validate_component_horizon(
    component: variants.Variant, target: pd.DataFrame, horizon: str
) -> None:
    expected = f"election-{HORIZON_DAYS[horizon]}d"
    if component.as_of and component.as_of != expected:
        raise ForecastRunError(
            f"component {component.name!r} declares {component.as_of}, not {expected}"
        )
    dated = [p for p in component.predictors if p in variants.DATED_PREDICTORS]
    for predictor in dated:
        column = variants.DATED_PREDICTORS[predictor]
        measured = pd.to_datetime(target[column])
        expected_dates = pd.to_datetime(target["election_date"]) - pd.Timedelta(
            days=HORIZON_DAYS[horizon]
        )
        if not measured.eq(expected_dates).all():
            raise ForecastRunError(
                f"component {component.name!r} predictor {predictor!r} does not "
                f"use the exact {horizon} target cutoff"
            )


def support_checks(
    component: variants.Variant,
    training: pd.DataFrame,
    target: pd.DataFrame,
) -> pd.DataFrame:
    """Per-race predictor support with explicit ranges and date counts."""
    train = variants.prepare(training)
    future = variants.prepare(target)
    rows = []
    for predictor in component.predictors:
        if predictor in variants.CATEGORICAL_LEVELS:
            for row_index, value in future[predictor].items():
                matching = train[train[predictor].astype(str).eq(str(value))]
                races = len(matching)
                dates = matching["election_date"].nunique()
                warning = (
                    "categorical_level_unobserved"
                    if races == 0
                    else "categorical_level_one_election_date"
                    if dates == 1
                    else ""
                )
                rows.append(
                    {
                        "target_id": future.loc[row_index, "target_id"],
                        "component": component.name,
                        "predictor": predictor,
                        "target_value": value,
                        "training_min": pd.NA,
                        "training_max": pd.NA,
                        "training_races": races,
                        "training_election_dates": dates,
                        "warning": warning,
                    }
                )
            continue
        for column in variants.expand(predictor):
            if column not in train or column not in future:
                continue
            if not pd.api.types.is_numeric_dtype(train[column]):
                continue
            minimum = float(train[column].min())
            maximum = float(train[column].max())
            for row_index, value in future[column].items():
                warning = ""
                if value < minimum:
                    warning = "numeric_below_training_range"
                elif value > maximum:
                    warning = "numeric_above_training_range"
                rows.append(
                    {
                        "target_id": future.loc[row_index, "target_id"],
                        "component": component.name,
                        "predictor": column,
                        "target_value": value,
                        "training_min": minimum,
                        "training_max": maximum,
                        "training_races": len(train),
                        "training_election_dates": train["election_date"].nunique(),
                        "warning": warning,
                    }
                )
    columns = [
        "target_id",
        "component",
        "predictor",
        "target_value",
        "training_min",
        "training_max",
        "training_races",
        "training_election_dates",
        "warning",
    ]
    return pd.DataFrame(rows, columns=columns).sort_values(
        ["target_id", "predictor"], ignore_index=True
    )


def aggregate_draws(draws_by_target: dict[str, np.ndarray], target: pd.DataFrame) -> pd.DataFrame:
    """Aligned posterior Democratic seat draws by office and combined target."""
    if set(draws_by_target) != set(target["target_id"]):
        raise ForecastRunError("race draws do not cover the target exactly")
    lengths = {len(draws) for draws in draws_by_target.values()}
    if len(lengths) != 1:
        raise ForecastRunError("component posterior samples are not alignable")
    count = lengths.pop()
    offices = sorted(target["office"].unique())
    rows = []
    for draw_index in range(count):
        wins = {
            target_id: int(draws[draw_index] > 0)
            for target_id, draws in draws_by_target.items()
        }
        row = {"draw": draw_index}
        for office in offices:
            ids = target.loc[target["office"].eq(office), "target_id"]
            row[office] = sum(wins[target_id] for target_id in ids)
        row["combined_contested"] = sum(wins.values())
        rows.append(row)
    return pd.DataFrame(rows)


def generate(
    target: pd.DataFrame,
    finance: pd.DataFrame,
    horizon: str,
    variant_name: str,
    definition_name: str,
    races: pd.DataFrame | None = None,
    roster: pd.DataFrame | None = None,
    fit_provider=fitmod.fit,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    """Fit every routed component and return snapshot-ready forecast artifacts."""
    variant = variants.get(variant_name)
    if not getattr(variant, "is_composite", False):
        raise ForecastRunError("operational forecast variant must be composite")
    definition = definitions.get(definition_name)
    future = attach_finance(target, finance, horizon)
    target_date_values = future["election_date"].astype(str).unique()
    if len(target_date_values) != 1:
        raise ForecastRunError("a forecast snapshot must have one target election date")
    target_date = target_date_values[0]
    training = historical_training(target_date, definition, races, roster)
    training_cutoff = str(training["election_date"].max())
    routed = variant.route(future)
    predictions = []
    support = []
    draws_by_target = {}
    fit_records = []
    for route_value, component in sorted(variant.components.items()):
        target_part = routed[route_value].sort_values("target_id", ignore_index=True)
        if target_part.empty:
            fit_records.append(
                {
                    "route_value": bool(route_value),
                    "component": component.name,
                    "target_races": 0,
                    "training_races": 0,
                    "seed": None,
                    "declaration": component.declared,
                }
            )
            continue
        validate_component_horizon(component, target_part, horizon)
        component_training = variants.restrict(component, training)
        variants.check_complete(
            component, variants.prepare(component_training), "forecast training"
        )
        inputs = seed_inputs(
            variant.name,
            component.name,
            definition.name,
            training_cutoff,
            target_date,
            horizon,
        )
        seed = stable_seed(**inputs)
        fitted = fit_provider(
            component,
            component_training,
            fold=f"forecast-{target_date}-{horizon}",
            definition=definition.name,
            seed=seed,
        )
        variants.check_complete(
            component, variants.prepare(target_part), "forecast target"
        )
        draws = fitted.predict_draws(target_part)
        if draws.shape[1] != len(target_part):
            raise ForecastRunError("component prediction count does not match routing")
        for column_index, target_id_value in enumerate(target_part["target_id"]):
            race_draws = draws[:, column_index]
            if target_id_value in draws_by_target:
                raise ForecastRunError(f"target race was multiply routed: {target_id_value}")
            draws_by_target[target_id_value] = race_draws
            predictions.append(
                {
                    "target_id": target_id_value,
                    "election_date": target_part.loc[column_index, "election_date"],
                    "office": target_part.loc[column_index, "office"],
                    "district": target_part.loc[column_index, "district"],
                    "district_display": target_part.loc[
                        column_index, "district_display"
                    ],
                    "dem_candidate_name": target_part.loc[
                        column_index, "dem_candidate_name"
                    ],
                    "comparison_candidate_name": target_part.loc[
                        column_index, "comparison_candidate_name"
                    ],
                    "variant": variant.name,
                    "component": component.name,
                    "fallback_reason": (
                        "finance unavailable at horizon" if not route_value else ""
                    ),
                    "point_margin": float(np.mean(race_draws)),
                    "lower_90": float(np.quantile(race_draws, 0.05)),
                    "upper_90": float(np.quantile(race_draws, 0.95)),
                    "dem_win_probability": float(np.mean(race_draws > 0)),
                }
            )
        support.append(support_checks(component, component_training, target_part))
        fit_records.append(
            {
                "route_value": bool(route_value),
                "component": component.name,
                "target_races": len(target_part),
                "training_races": len(component_training),
                "seed": seed,
                "seed_inputs": inputs,
                "declaration": component.declared,
                "diagnostics": fitted.diagnostics.as_row(),
            }
        )
    if set(draws_by_target) != set(future["target_id"]):
        missing = sorted(set(future["target_id"]) - set(draws_by_target))
        raise ForecastRunError(f"forecast did not cover target races: {missing}")
    race_frame = pd.DataFrame(predictions).sort_values("target_id", ignore_index=True)
    support_frame = pd.concat(support, ignore_index=True) if support else pd.DataFrame()
    chamber = aggregate_draws(draws_by_target, future)
    metadata = {
        "variant": variant.name,
        "variant_declaration": variant.declared,
        "definition": definition.name,
        "target_election": target_date,
        "horizon": horizon,
        "finance_cutoff": str(finance["cutoff"].iloc[0]),
        "training_cutoff": training_cutoff,
        "training_races": len(training),
        "components": fit_records,
        "aggregate_limitation": (
            "Aligned draws preserve represented posterior dependence but do not "
            "add a shared statewide election shock or correlation between fits."
        ),
    }
    return race_frame, chamber, support_frame, metadata


def _csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False, lineterminator="\n").encode("utf-8")


def _gzip_csv_bytes(frame: pd.DataFrame) -> bytes:
    raw = _csv_bytes(frame)
    output = io.BytesIO()
    with gzip.GzipFile(fileobj=output, mode="wb", mtime=0) as compressed:
        compressed.write(raw)
    return output.getvalue()


def git_commit() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    )
    return completed.stdout.strip()


def clean_worktree() -> bool:
    completed = subprocess.run(
        ["git", "status", "--porcelain"], capture_output=True, text=True, check=True
    )
    return not completed.stdout.strip()


def snapshot_contents(
    races: pd.DataFrame,
    chamber_draws: pd.DataFrame,
    support: pd.DataFrame,
    metadata: dict,
    target_path: Path,
    finance_path: Path,
    training_path: Path,
    code_commit: str,
) -> dict[str, bytes]:
    contents = {
        "races.csv": _csv_bytes(races),
        "chamber_draws.csv.gz": _gzip_csv_bytes(chamber_draws),
        "support_warnings.csv": _csv_bytes(support),
    }
    manifest = {
        **metadata,
        "code_commit": code_commit,
        "target_digest": file_digest(target_path),
        "finance_digest": file_digest(finance_path),
        "training_digest": file_digest(training_path),
        "files": {name: bytes_digest(content) for name, content in contents.items()},
    }
    contents["manifest.json"] = (
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    return contents


def publish_snapshot(contents: dict[str, bytes], directory: Path) -> str:
    """Create a snapshot directory once or verify every existing byte."""
    existing = {path.name for path in directory.iterdir()} if directory.exists() else set()
    if existing:
        if existing != set(contents):
            raise ForecastRunError(
                f"snapshot directory has conflicting files: {directory}"
            )
        different = [
            name for name, content in contents.items() if (directory / name).read_bytes() != content
        ]
        if different:
            raise ForecastRunError(
                f"refusing to overwrite different snapshot files: {different}"
            )
        return "verified"
    directory.mkdir(parents=True, exist_ok=True)
    for name, content in contents.items():
        (directory / name).write_bytes(content)
    return "created"


def run(horizon: str, variant_name: str | None = None) -> dict[str, bytes]:
    """Generate and publish one horizon from a committed clean revision."""
    if not clean_worktree():
        raise ForecastRunError("forecast publication requires a clean worktree")
    variant_name = variant_name or f"forecast_{horizon}"
    target_path = config.FORECAST_2026_TARGET
    finance_path = (
        config.FORECAST_2026_FINANCE_60D
        if horizon == "60d"
        else config.FORECAST_2026_FINANCE_14D
    )
    races, chamber, support, metadata = generate(
        forecast.load_target(target_path),
        pd.read_csv(finance_path),
        horizon,
        variant_name,
        definitions.adopted().name,
    )
    directory = config.FORECAST_2026_SNAPSHOTS / horizon
    manifest_path = directory / "manifest.json"
    code_commit = (
        json.loads(manifest_path.read_text())["code_commit"]
        if manifest_path.exists()
        else git_commit()
    )
    contents = snapshot_contents(
        races,
        chamber,
        support,
        metadata,
        target_path,
        finance_path,
        config.RACE_TRAINING_SET,
        code_commit,
    )
    result = publish_snapshot(contents, directory)
    print(f"{result} forecast snapshot -> {directory.relative_to(config.ROOT)}")
    print(f"target races: {len(races)}; posterior draws: {len(chamber)}")
    warnings = int(support["warning"].astype(bool).sum()) if len(support) else 0
    print(f"support warnings: {warnings}")
    return contents
