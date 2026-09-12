"""Precinct boundary layers for each redistricting cycle.

The 2011 and 2021 vintages come from the sibling mapoli checkout. The
2001-cycle layer is not published by MassGIS and is downloaded from
mggg-states/MA-shapefiles, which carries the Census Bureau's 2010 voting
tabulation districts labelled with Secretary of the Commonwealth town, ward,
and precinct identifiers (design.md, D10).
"""

from __future__ import annotations

import io
import re
import zipfile

import geopandas as gpd
import requests

from . import config
from .normalize import unabbreviate_compass

MAPOLI_GIS = config.ROOT.parent / "mapoli" / "gis"
MAPOLI_SHP = MAPOLI_GIS / "shp"

# The 2021 cycle split several precincts into sub-precincts after the MassGIS
# shapefile was published; mapoli's derived layer carries them.
SUBS_2022 = MAPOLI_GIS / "geojson" / "wards_pcts_subs_2022.geojson"

MGGG_URL = (
    "https://github.com/mggg-states/MA-shapefiles/raw/master/MA_precincts_02_10.zip"
)
MGGG_DIR = config.GIS_CACHE / "mggg_ma_precincts_02_10"
MGGG_SHP = MGGG_DIR / "MA_precincts_02_10.shp"

# "Chelsea City Ward 1 Precinct 1", "Braintree Town Precinct 5B"
WP_NAME_RE = re.compile(r"^(?P<town>.+?)\s+(?:City|Town)\s+(?:Ward\s+\S+\s+)?Precinct\b")

WORKING_CRS = 26986  # NAD83 / Massachusetts Mainland, metres


def download_mggg() -> None:
    """Download and unpack the 2001-cycle precinct layer if absent."""
    if MGGG_SHP.exists():
        return
    MGGG_DIR.mkdir(parents=True, exist_ok=True)
    response = requests.get(MGGG_URL, timeout=600)
    response.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        for member in archive.namelist():
            if "__MACOSX" in member or member.endswith("/"):
                continue
            target = MGGG_DIR / member.rsplit("/", 1)[-1]
            target.write_bytes(archive.read(member))


def _clean_key(frame: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    frame["city_town"] = frame["city_town"].map(
        lambda n: unabbreviate_compass(str(n).strip())
    )
    frame["ward"] = (
        frame["ward"].fillna("").astype(str).str.strip().replace({"": "-"})
    )
    frame["precinct"] = (
        frame["precinct"].fillna("").astype(str).str.strip().replace({"": "1"})
    )
    return frame[["city_town", "ward", "precinct", "geometry"]]


# Municipality names whose conventional form title-casing gets wrong.
NAME_FIXES = {
    "Manchester-By-The-Sea": "Manchester-by-the-Sea",
}


def _title_municipality(name: str) -> str:
    """MassGIS 2022 stores municipality names in upper case."""
    fixed = str(name).title().replace("'S", "'s")
    return NAME_FIXES.get(fixed, fixed)


def precincts(cycle: int) -> gpd.GeoDataFrame:
    """Precinct polygons for a redistricting cycle, keyed like the results."""
    if cycle == 2001:
        download_mggg()
        frame = gpd.read_file(MGGG_SHP)
        frame = frame.rename(
            columns={"TOWN": "city_town", "WARD": "ward", "PRECINCT": "precinct"}
        )
    elif cycle == 2011:
        frame = gpd.read_file(MAPOLI_SHP / "wardsprecincts2012" / "WARDSPRECINCTS_POLY.shp")
        towns = frame["WP_NAME"].map(
            lambda n: (WP_NAME_RE.match(str(n)).group("town") if WP_NAME_RE.match(str(n)) else None)
        )
        if towns.isna().any():
            unparsed = frame.loc[towns.isna(), "WP_NAME"].unique()[:5]
            raise ValueError(f"Unparsable WP_NAME values: {list(unparsed)}")
        frame["city_town"] = towns
        frame = frame.rename(columns={"WARD": "ward", "PRECINCT": "precinct"})
    elif cycle == 2021:
        if SUBS_2022.exists():
            frame = gpd.read_file(SUBS_2022)
            frame = frame.rename(columns={"Ward": "ward", "Pct": "precinct"})
        else:
            frame = gpd.read_file(
                MAPOLI_SHP / "wardsprecincts2022" / "WARDSPRECINCTS2022_POLY.shp"
            )
            frame["city_town"] = frame["TOWN"].map(_title_municipality)
            frame = frame.rename(columns={"WARD": "ward", "PRECINCT": "precinct"})
    else:
        raise ValueError(f"No precinct layer for redistricting cycle {cycle}")

    frame = _clean_key(frame.to_crs(WORKING_CRS))
    return frame
