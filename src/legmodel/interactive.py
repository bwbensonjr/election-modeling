"""Portable race-level draw bundles for the static forecast application."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import config, definitions, forecast, forecast_run, variants
from . import fit as fitmod

SCHEMA_VERSION = 1
SUMMARY_TOLERANCES = {
    "point_margin": 1e-9,
    "lower_90": 1e-9,
    "upper_90": 1e-9,
    "dem_win_probability": 1e-12,
}


class InteractiveBundleError(ValueError):
    """An interactive bundle disagrees with its locked source forecast."""


def json_bytes(value: object) -> bytes:
    """Canonical JSON bytes used for content digests and create-once checks."""
    def clean(item):
        if isinstance(item, dict):
            return {str(key): clean(child) for key, child in item.items()}
        if isinstance(item, (list, tuple)):
            return [clean(child) for child in item]
        if isinstance(item, np.generic):
            item = item.item()
        if item is pd.NA or isinstance(item, float) and not np.isfinite(item):
            return None
        return item

    return (
        json.dumps(clean(value), sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode("utf-8")


def summarize(draws: np.ndarray) -> dict[str, float]:
    """The race summaries used by both forecast publication and the web bundle."""
    values = np.asarray(draws, dtype=float)
    if values.ndim != 1 or not len(values) or not np.isfinite(values).all():
        raise InteractiveBundleError("race draws must be a finite one-dimensional array")
    return {
        "point_margin": float(np.mean(values)),
        "lower_90": float(np.quantile(values, 0.05)),
        "upper_90": float(np.quantile(values, 0.95)),
        "dem_win_probability": float(np.mean(values > 0)),
    }


def scenario_draws(
    published_draws: np.ndarray,
    published_incumbency: str,
    scenario_incumbency: str,
    terms: dict[str, np.ndarray],
    published_money_logratio: float | None = None,
    scenario_money_logratio: float | None = None,
    money_predictor: str | None = None,
) -> np.ndarray:
    """Apply paired coefficient deltas to published predictive draws."""
    indicators = {
        "No_Incumbent": (0, 0),
        "Dem_Incumbent": (1, 0),
        "GOP_Incumbent": (0, 1),
    }
    try:
        published_dem, published_gop = indicators[published_incumbency]
        scenario_dem, scenario_gop = indicators[scenario_incumbency]
    except KeyError as exc:
        raise InteractiveBundleError(f"unsupported incumbency {exc.args[0]!r}") from exc
    values = np.asarray(published_draws, dtype=float).copy()
    for name in ("incumbent_dem", "incumbent_gop"):
        if name not in terms or len(terms[name]) != len(values):
            raise InteractiveBundleError(f"missing aligned {name!r} coefficient draws")
    values += (scenario_dem - published_dem) * np.asarray(terms["incumbent_dem"])
    values += (scenario_gop - published_gop) * np.asarray(terms["incumbent_gop"])
    if money_predictor:
        if published_money_logratio is None or scenario_money_logratio is None:
            raise InteractiveBundleError("money scenario requires both log ratios")
        if money_predictor not in terms or len(terms[money_predictor]) != len(values):
            raise InteractiveBundleError(
                f"missing aligned {money_predictor!r} coefficient draws"
            )
        values += (
            scenario_money_logratio - published_money_logratio
        ) * np.asarray(terms[money_predictor])
    return values


def _finance_path(horizon: str) -> Path:
    if horizon == "60d":
        return config.FORECAST_2026_FINANCE_60D
    if horizon == "14d":
        return config.FORECAST_2026_FINANCE_14D
    raise InteractiveBundleError(f"unknown forecast horizon {horizon!r}")


def _money_columns(predictor: str) -> tuple[str, str]:
    if predictor == "money_logratio_wide":
        return "dem_receipts_wide", "opp_receipts_wide"
    if predictor == "money_logratio_primary":
        return "dem_receipts_primary", "opp_receipts_primary"
    raise InteractiveBundleError(f"unsupported interactive money predictor {predictor!r}")


def _assert_source_matches(
    generated: pd.DataFrame, official: pd.DataFrame, capture: dict
) -> None:
    generated = generated.set_index("target_id").sort_index()
    official = official.set_index("target_id").sort_index()
    if generated.index.tolist() != official.index.tolist():
        missing = sorted(set(official.index) - set(generated.index))
        extra = sorted(set(generated.index) - set(official.index))
        raise InteractiveBundleError(
            f"interactive export race identities disagree; missing={missing}, extra={extra}"
        )
    for target_id in official.index:
        for column in ("component", "variant", "office", "district"):
            if str(generated.loc[target_id, column]) != str(official.loc[target_id, column]):
                raise InteractiveBundleError(
                    f"{target_id}: generated {column} disagrees with locked snapshot"
                )
        draw_summary = summarize(capture["races"][target_id])
        for column, tolerance in SUMMARY_TOLERANCES.items():
            locked = float(official.loc[target_id, column])
            generated_value = float(generated.loc[target_id, column])
            if not np.isclose(generated_value, locked, rtol=0, atol=tolerance):
                raise InteractiveBundleError(
                    f"{target_id}: generated {column} {generated_value} disagrees "
                    f"with locked value {locked}"
                )
            if not np.isclose(draw_summary[column], locked, rtol=0, atol=tolerance):
                raise InteractiveBundleError(
                    f"{target_id}: draw {column} {draw_summary[column]} disagrees "
                    f"with locked value {locked}"
                )


def validate_contents(contents: dict[str, bytes]) -> dict:
    """Validate a complete in-memory bundle and return its manifest."""
    if "manifest.json" not in contents:
        raise InteractiveBundleError("interactive bundle is missing manifest.json")
    manifest = json.loads(contents["manifest.json"])
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise InteractiveBundleError("interactive bundle has an unsupported schema version")
    races = manifest.get("races", [])
    target_ids = [race.get("target_id") for race in races]
    if not target_ids or len(target_ids) != len(set(target_ids)):
        raise InteractiveBundleError("interactive bundle has missing or duplicate targets")
    draw_count = manifest.get("draw_count")
    if not isinstance(draw_count, int) or draw_count <= 0:
        raise InteractiveBundleError("interactive bundle has an invalid draw count")
    assets = manifest.get("assets", {})
    expected_files = {"manifest.json", *assets}
    if set(contents) != expected_files:
        raise InteractiveBundleError("interactive bundle file set disagrees with manifest")
    for path, expected_digest in assets.items():
        if forecast_run.bytes_digest(contents[path]) != expected_digest:
            raise InteractiveBundleError(f"interactive bundle asset digest mismatch: {path}")
    components = manifest.get("components", {})
    for component_name, component_meta in components.items():
        component = json.loads(contents[component_meta["asset"]])
        if component.get("component") != component_name:
            raise InteractiveBundleError(f"component identity mismatch: {component_name}")
        terms = component.get("terms", {})
        for term in component_meta.get("scenario_terms", []):
            if term not in terms or len(terms[term]) != draw_count:
                raise InteractiveBundleError(
                    f"component {component_name!r} has an invalid {term!r} draw array"
                )
    for race in races:
        if race.get("component") not in components:
            raise InteractiveBundleError(
                f"{race.get('target_id')}: component is absent from bundle"
            )
        asset = json.loads(contents[race["asset"]])
        if asset.get("target_id") != race["target_id"]:
            raise InteractiveBundleError(f"race identity mismatch: {race['target_id']}")
        if len(asset.get("draws", [])) != draw_count:
            raise InteractiveBundleError(
                f"{race['target_id']}: predictive draw count is inconsistent"
            )
    return manifest


def build_contents(
    horizon: str,
    target: pd.DataFrame,
    finance: pd.DataFrame,
    official: pd.DataFrame,
    snapshot_manifest: dict,
    snapshot_support: pd.DataFrame,
    races: pd.DataFrame | None = None,
    roster: pd.DataFrame | None = None,
    fit_provider=fitmod.fit,
) -> dict[str, bytes]:
    """Create a validated interactive bundle without writing it."""
    capture: dict = {}
    generated, _, _, metadata = forecast_run.generate(
        target,
        finance,
        horizon,
        snapshot_manifest["variant"],
        snapshot_manifest["definition"],
        races,
        roster,
        fit_provider,
        capture,
    )
    _assert_source_matches(generated, official, capture)
    future = variants.prepare(forecast_run.attach_finance(target, finance, horizon))
    future = future.set_index("target_id")
    official_by_id = official.set_index("target_id")
    support_by_id = {
        target_id: rows.to_dict("records")
        for target_id, rows in snapshot_support.groupby("target_id", sort=False)
    }
    contents: dict[str, bytes] = {}
    component_manifest = {}
    draw_counts = set()
    for component_name, component in sorted(capture["components"].items()):
        term_values = {
            name: np.asarray(values, dtype=float).tolist()
            for name, values in sorted(component["terms"].items())
        }
        draw_counts.update(len(values) for values in term_values.values())
        component_path = f"components/{component_name}.json"
        component_payload = {
            "schema_version": SCHEMA_VERSION,
            "component": component_name,
            "predictors": component["predictors"],
            "terms": term_values,
            "numeric_support": component["numeric_support"],
            "categorical_support": component["categorical_support"],
        }
        contents[component_path] = json_bytes(component_payload)
        component_manifest[component_name] = {
            "asset": component_path,
            "predictors": component["predictors"],
            "scenario_terms": sorted(term_values),
            "numeric_support": component["numeric_support"],
            "categorical_support": component["categorical_support"],
        }
    race_manifest = []
    for target_id in sorted(capture["races"]):
        values = np.asarray(capture["races"][target_id], dtype=float)
        draw_counts.add(len(values))
        row = future.loc[target_id]
        locked = official_by_id.loc[target_id]
        component = component_manifest[str(locked["component"])]
        money_predictors = [
            predictor
            for predictor in component["predictors"]
            if predictor.startswith("money_logratio_")
        ]
        if len(money_predictors) > 1:
            raise InteractiveBundleError(
                f"{target_id}: several interactive money predictors are unsupported"
            )
        money_predictor = money_predictors[0] if money_predictors else None
        dem_receipts = None
        opponent_receipts = None
        money_logratio = None
        if money_predictor:
            dem_column, opponent_column = _money_columns(money_predictor)
            dem_receipts = float(row[dem_column])
            opponent_receipts = float(row[opponent_column])
            money_logratio = float(row[money_predictor])
        race_path = f"races/{target_id}.json"
        contents[race_path] = json_bytes(
            {
                "schema_version": SCHEMA_VERSION,
                "target_id": target_id,
                "draws": values.tolist(),
            }
        )
        race_manifest.append(
            {
                "target_id": target_id,
                "election_date": str(row["election_date"]),
                "office": str(row["office"]),
                "district": str(row["district"]),
                "district_display": str(row["district_display"]),
                "dem_candidate_name": str(row["dem_candidate_name"]),
                "comparison_candidate_name": str(row["comparison_candidate_name"]),
                "component": str(locked["component"]),
                "asset": race_path,
                "published": {
                    name: float(locked[name]) for name in SUMMARY_TOLERANCES
                },
                "inputs": {
                    "PVI_N": float(row["PVI_N"]),
                    "incumbent_status": str(row["incumbent_status"]),
                    "dem_receipts": dem_receipts,
                    "opponent_receipts": opponent_receipts,
                    "money_predictor": money_predictor,
                    "money_logratio": money_logratio,
                },
                "support": support_by_id.get(target_id, []),
            }
        )
    if len(draw_counts) != 1:
        raise InteractiveBundleError(
            f"interactive assets have inconsistent draw counts: {sorted(draw_counts)}"
        )
    draw_count = draw_counts.pop()
    assets = {
        path: forecast_run.bytes_digest(content)
        for path, content in sorted(contents.items())
    }
    source_commit = snapshot_manifest["code_commit"]
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "election": snapshot_manifest["target_election"],
        "horizon": horizon,
        "variant": snapshot_manifest["variant"],
        "variant_declaration": snapshot_manifest["variant_declaration"],
        "definition": snapshot_manifest["definition"],
        "training_cutoff": snapshot_manifest["training_cutoff"],
        "finance_cutoff": snapshot_manifest["finance_cutoff"],
        "source_code_commit": source_commit,
        "source_snapshot": f"data/forecast/2026/snapshots/{horizon}",
        "source_snapshot_url": (
            "https://github.com/bwbensonjr/election-modeling/tree/"
            f"{source_commit}/data/forecast/2026/snapshots/{horizon}"
        ),
        "source_digests": {
            "target": snapshot_manifest["target_digest"],
            "finance": snapshot_manifest["finance_digest"],
            "training": snapshot_manifest["training_digest"],
        },
        "summary_tolerances": SUMMARY_TOLERANCES,
        "draw_count": draw_count,
        "components": component_manifest,
        "races": race_manifest,
        "assets": assets,
        "generation": {
            "training_races": metadata["training_races"],
            "components": metadata["components"],
        },
    }
    contents["manifest.json"] = json_bytes(manifest)
    validate_contents(contents)
    return contents


def publish_contents(contents: dict[str, bytes], directory: Path) -> str:
    """Create a bundle once or verify every existing byte."""
    validate_contents(contents)
    existing = (
        {
            str(path.relative_to(directory))
            for path in directory.rglob("*")
            if path.is_file()
        }
        if directory.exists()
        else set()
    )
    if existing:
        if existing != set(contents):
            raise InteractiveBundleError(
                f"interactive directory has conflicting files: {directory}"
            )
        different = [
            path
            for path, content in contents.items()
            if (directory / path).read_bytes() != content
        ]
        if different:
            raise InteractiveBundleError(
                f"refusing to overwrite different interactive files: {different}"
            )
        return "verified"
    for path, content in contents.items():
        destination = directory / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
    return "created"


def load_contents(directory: Path) -> dict[str, bytes]:
    """Read and validate an existing bundle directory."""
    contents = {
        str(path.relative_to(directory)): path.read_bytes()
        for path in directory.rglob("*")
        if path.is_file()
    }
    validate_contents(contents)
    return contents


def run(horizon: str) -> dict[str, bytes]:
    """Refit, validate, and publish one locked forecast as interactive data."""
    if not forecast_run.clean_worktree():
        raise InteractiveBundleError(
            "interactive publication requires a clean worktree"
        )
    snapshot_directory = config.FORECAST_2026_SNAPSHOTS / horizon
    required = {"manifest.json", "races.csv", "support_warnings.csv"}
    missing = sorted(name for name in required if not (snapshot_directory / name).exists())
    if missing:
        raise InteractiveBundleError(
            f"locked {horizon} snapshot is incomplete; missing {missing}"
        )
    snapshot_manifest = json.loads((snapshot_directory / "manifest.json").read_text())
    contents = build_contents(
        horizon,
        forecast.load_target(config.FORECAST_2026_TARGET),
        pd.read_csv(_finance_path(horizon)),
        pd.read_csv(snapshot_directory / "races.csv"),
        snapshot_manifest,
        pd.read_csv(snapshot_directory / "support_warnings.csv"),
    )
    directory = config.FORECAST_2026_INTERACTIVE / horizon
    result = publish_contents(contents, directory)
    manifest = json.loads(contents["manifest.json"])
    print(f"{result} interactive bundle -> {directory.relative_to(config.ROOT)}")
    print(f"target races: {len(manifest['races'])}; draws: {manifest['draw_count']}")
    return contents
