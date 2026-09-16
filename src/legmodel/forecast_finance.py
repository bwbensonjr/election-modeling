"""Candidate-grain OCPF finance snapshots for future forecast targets."""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd

from maprecinct import filer_match, finance, ocpf

from . import config, forecast

HORIZONS = {"60d": 60, "14d": 14}
ROLES = (
    ("dem", "dem_candidate_id", "dem_candidate_name"),
    ("opp", "comparison_candidate_id", "comparison_candidate_name"),
)


class ForecastFinanceError(ValueError):
    """Forecast finance cannot be resolved, reconstructed, or published."""


def candidate_view(target: pd.DataFrame) -> pd.DataFrame:
    """Expand a response-free race target to its two finance candidates."""
    target = forecast.validate_target(target)
    rows = []
    for race in target.itertuples(index=False):
        for role, id_column, name_column in ROLES:
            rows.append(
                {
                    "target_id": race.target_id,
                    "election_date": race.election_date,
                    "election_year": int(str(race.election_date)[:4]),
                    "office": race.office,
                    "district": race.district,
                    "district_display": race.district_display,
                    "is_special": False,
                    "role": role,
                    "candidate_id": getattr(race, id_column),
                    "candidate": getattr(race, name_column),
                }
            )
    return pd.DataFrame(rows).sort_values(
        ["office", "district", "role"], ignore_index=True
    )


def resolve(
    target: pd.DataFrame,
    roster_provider=ocpf.race_roster,
    district_index: dict | None = None,
) -> pd.DataFrame:
    """Resolve future candidates through the historical filer matcher."""
    candidates = candidate_view(target)
    index = ocpf.district_index() if district_index is None else district_index
    rows = []
    for (_, office, district_display), group in candidates.groupby(
        ["election_year", "office", "district_display"], sort=False
    ):
        year = int(group["election_year"].iloc[0])
        error = ""
        try:
            roster = roster_provider(year, office, district_display, False, index)
        except ocpf.RosterUnavailable as exc:
            roster = []
            error = str(exc).replace("\n", " ")[:200]
        for candidate in group.to_dict("records"):
            match = filer_match.match_candidate(candidate["candidate"], roster)
            rows.append(
                {
                    **candidate,
                    "cpf_id": match.cpf_id,
                    "filer_name": match.filer_name,
                    "match_rule": match.rule,
                    "filers_considered": match.considered,
                    "roster_source": roster[0].get("roster_source", "")
                    if roster
                    else "",
                    "roster_error": error,
                }
            )
    return pd.DataFrame(rows).sort_values(
        ["office", "district", "role"], ignore_index=True
    )


def horizon_window(election_date: str, horizon: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    if horizon not in HORIZONS:
        raise ForecastFinanceError(
            f"unknown finance horizon {horizon!r}; choose from {sorted(HORIZONS)}"
        )
    return finance.window_for(election_date, HORIZONS[horizon])


def collect(
    resolved: pd.DataFrame,
    horizon: str,
    total_provider=ocpf.dated_total,
) -> pd.DataFrame:
    """Collect one exact-horizon finance row for each target candidate."""
    rows = []
    for candidate in resolved.to_dict("records"):
        start, cutoff = horizon_window(candidate["election_date"], horizon)
        matched = candidate["match_rule"] in filer_match.MATCHED_RULES
        values = {}
        for label, category in finance.CATEGORIES.items():
            values[f"{label}_cache_identity"] = (
                ocpf.dated_total_cache_identity(
                    candidate["cpf_id"], start, cutoff, category
                )
                if matched
                else ""
            )
            if matched:
                total = total_provider(candidate["cpf_id"], start, cutoff, category)
                values[label] = total.total
                values[f"{label}_items"] = total.count
            else:
                values[label] = pd.NA
                values[f"{label}_items"] = pd.NA
        rows.append(
            {
                **candidate,
                "horizon": horizon,
                "window_start": start.date().isoformat(),
                "cutoff": cutoff.date().isoformat(),
                "available": matched,
                **values,
            }
        )
    frame = pd.DataFrame(rows)
    complete = frame.groupby("target_id")["available"].transform(
        lambda values: len(values) == 2 and bool(values.all())
    )
    frame["race_complete"] = complete
    return frame.sort_values(["office", "district", "role"], ignore_index=True)


def _csv_bytes(frame: pd.DataFrame) -> bytes:
    buffer = io.StringIO(newline="")
    frame.to_csv(buffer, index=False, lineterminator="\n")
    return buffer.getvalue().encode("utf-8")


def publish_create_once(frame: pd.DataFrame, path: Path) -> str:
    """Create a finance snapshot once; later runs may only verify it."""
    content = _csv_bytes(frame)
    if path.exists():
        if path.read_bytes() != content:
            raise ForecastFinanceError(
                f"refusing to overwrite different forecast finance snapshot: {path}"
            )
        return "verified"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return "created"


def path_for(horizon: str) -> Path:
    if horizon == "60d":
        return config.FORECAST_2026_FINANCE_60D
    if horizon == "14d":
        return config.FORECAST_2026_FINANCE_14D
    raise ForecastFinanceError(f"unknown finance horizon {horizon!r}")


def summary(resolved: pd.DataFrame, horizon: str) -> dict:
    matched = resolved["match_rule"].isin(filer_match.MATCHED_RULES)
    _, cutoff = horizon_window(resolved["election_date"].iloc[0], horizon)
    return {
        "horizon": horizon,
        "cutoff": cutoff.date().isoformat(),
        "candidates": len(resolved),
        "matched_candidates": int(matched.sum()),
        "unresolved_review_count": int((~matched).sum()),
    }


def run(horizon: str, dry_run: bool = False, cache_only: bool = False) -> pd.DataFrame:
    """Resolve, collect, and create or verify one 2026 finance horizon."""
    target = forecast.load_target()
    prior_cache_only = ocpf.CACHE_ONLY
    ocpf.CACHE_ONLY = cache_only
    try:
        resolved = resolve(target)
        details = summary(resolved, horizon)
        print(f"target: {config.FORECAST_2026_TARGET.relative_to(config.ROOT)}")
        for key, value in details.items():
            print(f"{key}: {value}")
        unresolved = resolved[
            ~resolved["match_rule"].isin(filer_match.MATCHED_RULES)
        ]
        if len(unresolved):
            print(
                unresolved[
                    ["office", "district_display", "role", "candidate", "match_rule"]
                ].to_string(index=False)
            )
        if dry_run:
            return resolved
        frame = collect(resolved, horizon)
        path = path_for(horizon)
        result = publish_create_once(frame, path)
        print(f"{result} {len(frame)} rows -> {path.relative_to(config.ROOT)}")
        return frame
    finally:
        ocpf.CACHE_ONLY = prior_cache_only
