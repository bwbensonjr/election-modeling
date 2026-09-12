"""Validate precinct PVI by rolling it up to districts and comparing to mapoli.

mapoli's published district PVI for a given year may rest on a different
national baseline than the FEC totals this pipeline uses. A baseline
difference shifts every district in a year by the same amount, so the
comparison separates the constant offset from the per-district spread: the
offset is a documented definitional difference, the spread is what would
indicate a data problem.
"""

from __future__ import annotations

import pandas as pd

from . import config, normalize, pvi

MAPOLI_PVI = config.ROOT.parent / "mapoli" / "pvi"
REPORT = "pvi_district_rollup_validation.csv"

# Agreement thresholds, set from observed behaviour (design.md, Open Questions).
# Natively-mapped cycles involve no estimation and must agree almost exactly.
NATIVE_SPREAD_TOLERANCE = 0.05
# Remapped cycles carry areal interpolation, which mapoli performs with a
# different implementation and layer, so districts containing split precincts
# legitimately differ by a few points.
REMAPPED_SPREAD_TOLERANCE = 5.0

# (our pvi_year, our cycle, mapoli pvi_year, whether our side was remapped)
COMPARISONS = [
    (2016, 2011, 2016, False),
    (2020, 2011, 2020, False),
    (2020, 2021, 2022, True),
    (2024, 2021, 2024, True),
]

OFFICES = [("State Senate", "State Senate"), ("State Representative", "State Rep")]


def _district_map(cycle: int) -> pd.DataFrame:
    """mapoli's own precinct-to-district mapping, used so that this check
    isolates the PVI computation from our district derivation."""
    if cycle == 2011:
        frame = pd.read_csv(MAPOLI_PVI / "ma_precincts_districts_16_20_pres.csv")
        frame = frame.rename(
            columns={"City/Town": "city_town", "Ward": "ward", "Pct": "precinct"}
        )
    elif cycle == 2021:
        frame = pd.read_csv(MAPOLI_PVI / "ma_precincts_districts_pres_2024.csv")
        frame = frame.rename(
            columns={"State_Rep": "State Rep", "State_Senate": "State Senate"}
        )
    else:
        raise ValueError(f"mapoli publishes no precinct-district map for cycle {cycle}")

    frame["city_town"] = frame["city_town"].map(
        lambda n: normalize.unabbreviate_compass(str(n).strip())
    )
    frame["ward"] = (
        frame["ward"].fillna("-").astype(str).str.strip().replace({"": "-", "nan": "-"})
    )
    frame["precinct"] = frame["precinct"].fillna("1").astype(str).str.strip()
    return frame[["city_town", "ward", "precinct", "State Rep", "State Senate"]]


def run() -> pd.DataFrame:
    ours = pd.read_csv(config.PVI_DIR / "ma_precinct_pvi.csv.gz")
    published = pd.read_csv(MAPOLI_PVI / "ma_state_leg_pvi_2008_2024.csv")
    rows = []

    for pvi_year, cycle, mapoli_year, remapped in COMPARISONS:
        subset = ours[
            (ours["pvi_year"] == pvi_year) & (ours["redistricting_cycle"] == cycle)
        ]
        joined = subset.merge(
            _district_map(cycle), on=["city_town", "ward", "precinct"], how="inner"
        )
        national = pvi.national_two_party_share(
            int(subset["pres_year_earlier"].iloc[0]),
            int(subset["pres_year_later"].iloc[0]),
        )
        for office, column in OFFICES:
            agg = joined.groupby(column, as_index=False)[["dem_votes", "gop_votes"]].sum()
            agg["ours"] = (
                agg["dem_votes"] / (agg["dem_votes"] + agg["gop_votes"]) - national
            ) * 100
            theirs = published[
                (published["pvi_year"] == mapoli_year) & (published["office"] == office)
            ]
            # District names appear in word-ordinal form in some mapoli files
            # and numeric-ordinal form in others; take whichever joins better.
            best = None
            for name_column in ("district", "district_display"):
                candidate = agg.merge(
                    theirs[[name_column, "PVI_N"]],
                    left_on=column,
                    right_on=name_column,
                    how="inner",
                )
                if best is None or len(candidate) > len(best):
                    best = candidate
            difference = best["ours"] - best["PVI_N"]
            offset = difference.mean()
            spread = (difference - offset).abs().max()
            tolerance = (
                REMAPPED_SPREAD_TOLERANCE if remapped else NATIVE_SPREAD_TOLERANCE
            )
            rows.append(
                {
                    "pvi_year": pvi_year,
                    "redistricting_cycle": cycle,
                    "mapoli_pvi_year": mapoli_year,
                    "office": office,
                    "districts_matched": len(best),
                    "districts_published": len(theirs),
                    "baseline_offset": round(offset, 4),
                    "max_spread_about_offset": round(spread, 4),
                    "tolerance": tolerance,
                    "within_tolerance": bool(spread <= tolerance),
                    "outliers": int((difference - offset).abs().gt(tolerance).sum()),
                }
            )

    report = pd.DataFrame(rows)
    path = config.REPORT_DIR / REPORT
    path.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(path, index=False)
    print(report.to_string(index=False))
    print(f"\n-> {path.relative_to(config.ROOT)}")
    failures = report[~report["within_tolerance"]]
    if len(failures):
        print(f"WARNING: {len(failures)} comparisons outside tolerance")
    return report
