"""Map precinct votes from the geography they were cast on onto another cycle.

Identifier matching runs first and is exact; only the residue is estimated by
area weighting (design.md, D5). Roughly 97% of precincts carry over exactly
across a redistricting boundary, so interpolation error is confined to a small,
labelled minority of rows.
"""

from __future__ import annotations

import re

import geopandas as gpd
import pandas as pd

from . import config, gis

KEY = ["city_town", "ward", "precinct"]
VOTE_COLUMNS = ["dem_votes", "gop_votes"]

# Subdivided precincts carry a suffix on a numeric or single-letter stem:
# "1A" -> "1", "3N" -> "3", "21C" -> "21", "CN" -> "C", "AE" -> "A".
# A bare stem such as "A" or "5" has no parent.
CHILD_RE = re.compile(r"^(?P<parent>\d+|[A-Za-z])(?P<suffix>[A-Za-z]+)$")

PROVENANCE_NATIVE = "native"
PROVENANCE_EXACT = "exact_identifier"
PROVENANCE_COMBINED = "combined_children"
PROVENANCE_INTERPOLATED = "areal_interpolation"


def parent_precinct(precinct: str) -> str | None:
    """The parent a subdivided precinct belongs to, if its name implies one."""
    match = CHILD_RE.match(str(precinct).strip())
    return match.group("parent") if match else None


def combine_children(votes: pd.DataFrame, target_keys: set[tuple]) -> pd.DataFrame:
    """Sum subdivided precincts into the parent the target cycle uses.

    Only applied where the parent exists in the target and the children do not,
    so the result is an exact sum rather than an estimate.
    """
    votes = votes.copy()
    votes["_parent"] = votes["precinct"].map(parent_precinct)
    eligible = votes["_parent"].notna() & votes.apply(
        lambda r: (r["city_town"], r["ward"], r["_parent"]) in target_keys
        and (r["city_town"], r["ward"], r["precinct"]) not in target_keys,
        axis=1,
    )
    if not eligible.any():
        return votes.drop(columns="_parent").assign(_combined=False)

    children = votes[eligible].copy()
    children["precinct"] = children["_parent"]
    combined = (
        children.groupby(KEY, as_index=False)[VOTE_COLUMNS].sum().assign(_combined=True)
    )
    rest = votes[~eligible].drop(columns="_parent").assign(_combined=False)
    return pd.concat([rest, combined], ignore_index=True)


def _interpolate(
    unmatched: pd.DataFrame, source_cycle: int, target_cycle: int
) -> pd.DataFrame:
    """Distribute unmatched source votes across overlapping target precincts."""
    if unmatched.empty:
        return pd.DataFrame(columns=KEY + VOTE_COLUMNS)

    source_geom = gis.precincts(source_cycle)
    target_geom = gis.precincts(target_cycle)

    donors = source_geom.merge(unmatched, on=KEY, how="inner")

    # A precinct that was subdivided after the source layer was drawn has votes
    # but no polygon of its own. Its votes are still known to have been cast
    # inside its ward, so the ward - or the municipality, where the layer does
    # not carry that ward - stands in as the donor geography.
    have = set(map(tuple, donors[KEY].values)) if not donors.empty else set()
    orphans = unmatched[[tuple(k) not in have for k in unmatched[KEY].values]]
    if not orphans.empty:
        fallbacks = []
        ward_geom = source_geom.dissolve(by=["city_town", "ward"]).reset_index()
        town_geom = source_geom.dissolve(by="city_town").reset_index()
        for row in orphans.itertuples(index=False):
            match = ward_geom[
                (ward_geom["city_town"] == row.city_town)
                & (ward_geom["ward"] == row.ward)
            ]
            if match.empty:
                match = town_geom[town_geom["city_town"] == row.city_town]
            if match.empty:
                continue
            fallbacks.append(
                {
                    "city_town": row.city_town,
                    "ward": row.ward,
                    "precinct": row.precinct,
                    "dem_votes": row.dem_votes,
                    "gop_votes": row.gop_votes,
                    "geometry": match.geometry.iloc[0],
                }
            )
        if fallbacks:
            donors = pd.concat(
                [donors, gpd.GeoDataFrame(fallbacks, crs=source_geom.crs)],
                ignore_index=True,
            )
            donors = gpd.GeoDataFrame(donors, geometry="geometry", crs=source_geom.crs)

    if donors.empty:
        return pd.DataFrame(columns=KEY + VOTE_COLUMNS)
    pieces = gpd.overlay(
        donors,
        target_geom.rename(columns={c: f"tgt_{c}" for c in KEY}),
        how="intersection",
        keep_geom_type=True,
    )
    if pieces.empty:
        return pd.DataFrame(columns=KEY + VOTE_COLUMNS)

    # Normalize each donor's shares to sum to one. The two cycles' layers come
    # from different publishers and do not agree perfectly along coastlines and
    # municipal borders, so dividing by the donor's own area would silently
    # discard the votes on any sliver that overlaps no target precinct.
    piece_area = pieces.geometry.area
    donor_total = piece_area.groupby(
        [pieces[c] for c in KEY], observed=True
    ).transform("sum")
    pieces["_share"] = piece_area / donor_total
    for column in VOTE_COLUMNS:
        pieces[column] = pieces[column] * pieces["_share"]

    allocated = (
        pieces.groupby([f"tgt_{c}" for c in KEY], as_index=False)[VOTE_COLUMNS]
        .sum()
        .rename(columns={f"tgt_{c}": c for c in KEY})
    )
    return allocated


def remap(
    votes: pd.DataFrame, source_cycle: int, target_cycle: int
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Express `votes` on the target cycle's precincts.

    Returns (remapped votes with a `provenance` column, unresolved report).
    """
    votes = votes[KEY + VOTE_COLUMNS].copy()
    if source_cycle == target_cycle:
        return votes.assign(provenance=PROVENANCE_NATIVE), _empty_unresolved()

    target_geom = gis.precincts(target_cycle)
    target_keys = set(map(tuple, target_geom[KEY].values))

    votes = combine_children(votes, target_keys)
    key_tuples = list(map(tuple, votes[KEY].values))
    matched_mask = pd.Series([k in target_keys for k in key_tuples], index=votes.index)

    matched = votes[matched_mask].copy()
    matched["provenance"] = matched["_combined"].map(
        {True: PROVENANCE_COMBINED, False: PROVENANCE_EXACT}
    )
    matched = matched.drop(columns="_combined")

    unmatched = votes[~matched_mask].drop(columns="_combined")
    interpolated = _interpolate(unmatched, source_cycle, target_cycle)

    unresolved = _unresolved_report(unmatched, source_cycle, target_cycle)

    if not interpolated.empty:
        interpolated = interpolated.assign(provenance=PROVENANCE_INTERPOLATED)
        # An interpolated allocation can land in a precinct that also matched
        # exactly; sum them and mark the row as interpolated.
        combined = pd.concat([matched, interpolated], ignore_index=True)
        summed = combined.groupby(KEY, as_index=False)[VOTE_COLUMNS].sum()
        provenance = (
            combined.groupby(KEY)["provenance"]
            .agg(
                lambda s: PROVENANCE_INTERPOLATED
                if PROVENANCE_INTERPOLATED in set(s)
                else sorted(set(s))[0]
            )
            .reset_index()
        )
        result = summed.merge(provenance, on=KEY, how="left")
    else:
        result = matched

    return result.sort_values(KEY, ignore_index=True), unresolved


def _empty_unresolved() -> pd.DataFrame:
    return pd.DataFrame(
        columns=KEY + ["source_cycle", "target_cycle", "reason", "dem_votes", "gop_votes"]
    )


def _unresolved_report(
    unmatched: pd.DataFrame, source_cycle: int, target_cycle: int
) -> pd.DataFrame:
    """Unmatched source precincts that also lack geometry to interpolate from."""
    if unmatched.empty:
        return _empty_unresolved()
    source_geom = gis.precincts(source_cycle)
    towns = set(source_geom["city_town"])
    missing = unmatched[
        [ct not in towns for ct in unmatched["city_town"].values]
    ].copy()
    if missing.empty:
        return _empty_unresolved()
    missing["source_cycle"] = source_cycle
    missing["target_cycle"] = target_cycle
    missing["reason"] = "no source geometry for this precinct identifier"
    return missing[KEY + ["source_cycle", "target_cycle", "reason"] + VOTE_COLUMNS]
