"""Throttled, cached retrieval of precinct-level results from electionstats.

The upstream endpoint is quiet about failure: it returns municipality-level
rows with empty ward and precinct fields for elections that predate precinct
reporting, and HTML error pages on error, both with a 200 status. Validation
therefore inspects the payload rather than trusting the status code
(design.md, D4; precinct-election-results spec).
"""

from __future__ import annotations

import csv
import io
import time
from dataclasses import dataclass
from pathlib import Path

import requests

from . import config

DOWNLOAD_URL = (
    "https://electionstats.state.ma.us/elections/download/"
    "{election_id}/precincts_include:1/"
)

REQUEST_DELAY_SECONDS = 1.0
REQUEST_TIMEOUT_SECONDS = 90
MAX_ATTEMPTS = 3

# Rows that are not precinct observations: the party label line that follows
# the header, and the trailing aggregate.
AGGREGATE_FIRST_FIELDS = {"", "TOTALS"}


class PayloadError(Exception):
    """The response body is not usable precinct-level CSV."""


@dataclass(frozen=True)
class FetchResult:
    election_id: int
    path: Path
    from_cache: bool


def cache_path(election_id: int) -> Path:
    return config.ELECTIONSTATS_CACHE / f"{election_id}.csv"


def validate_payload(text: str) -> list[list[str]]:
    """Return the precinct data rows, or raise PayloadError.

    Rejects HTML error pages, empty bodies, and municipality-level responses
    from elections that predate precinct reporting.
    """
    stripped = text.lstrip()
    if not stripped:
        raise PayloadError("empty response body")
    if stripped[:1] == "<":
        raise PayloadError("response is HTML, not CSV")

    rows = [r for r in csv.reader(io.StringIO(text)) if any(c.strip() for c in r)]
    if not rows:
        raise PayloadError("no parsable CSV rows")

    header = rows[0]
    if header[:3] != ["City/Town", "Ward", "Pct"]:
        raise PayloadError(f"unexpected header: {header[:3]}")

    body = [
        r
        for r in rows[1:]
        if len(r) > 2 and r[0].strip() not in AGGREGATE_FIRST_FIELDS
    ]
    if not body:
        raise PayloadError("no data rows outside the aggregate rows")

    if not any(r[2].strip() for r in body):
        raise PayloadError(
            "no populated precinct values: results are municipality-level only"
        )
    return body


def fetch_election(
    election_id: int, session: requests.Session | None = None, force: bool = False
) -> FetchResult:
    """Retrieve one election, using the cache unless `force` is set."""
    path = cache_path(election_id)
    if path.exists() and not force:
        validate_payload(path.read_text())
        return FetchResult(election_id, path, from_cache=True)

    session = session or requests.Session()
    url = DOWNLOAD_URL.format(election_id=election_id)
    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = session.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
            if response.status_code != 200:
                raise PayloadError(f"HTTP {response.status_code}")
            validate_payload(response.text)
        except (requests.RequestException, PayloadError) as exc:
            last_error = exc
            # A payload that is structurally wrong will not improve on retry.
            if isinstance(exc, PayloadError) and "precinct" in str(exc):
                break
            if attempt < MAX_ATTEMPTS:
                time.sleep(REQUEST_DELAY_SECONDS * attempt)
            continue
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(response.text)
            time.sleep(REQUEST_DELAY_SECONDS)
            return FetchResult(election_id, path, from_cache=False)

    raise PayloadError(f"election {election_id}: {last_error}")
