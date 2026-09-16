"""Cached access to the OCPF campaign-finance API.

Money is never read from a published cumulative figure. Fetched after a cycle,
OCPF's "year to date" fields report the whole calendar year -- 411 of 428 rows
in 2020 carry a bank report end date of 12/31 -- so they include money raised
after the polls closed. `dated_total` reconstructs a figure bounded by an
explicit window from report line items instead, which is both pre-election and
uniform across the era seam at 2020 (campaign-finance spec, "Money is measured
as of a stated date"; design.md, D1).
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import requests

from . import config

BASE_URL = "https://api.ocpf.us/"

REQUEST_DELAY_SECONDS = 0.2
REQUEST_TIMEOUT_SECONDS = 60
MAX_ATTEMPTS = 3

# `SearchTypeCategory` selects the record kind, and the endpoint fails open:
# any unrecognised value silently returns receipts rather than erroring, so a
# typo produces a plausible wrong answer. Only these two are ever sent, and
# anything else raises before a request is made (tasks 1.3).
CATEGORY_RECEIPTS = "R"
CATEGORY_EXPENDITURES = "B"
CATEGORIES = frozenset({CATEGORY_RECEIPTS, CATEGORY_EXPENDITURES})

# Feed paths. The two rosters cover disjoint eras; see `roster_path`.
SEARCH_ITEMS_PATH = "search/items"
DISTRICTS_PATH = "districts"
FINSUMMARIES_PATH = "onballot/finsummaries/{year}/{code}"
DEPOSITORY_PATH = "reports/legislative/depository/ytd/{year}"

# The last year the historical district-scoped feed carries money, and the
# first year the current legislative feed does. Probed year by year: the
# depository feed returns 0-13 rows before 2020 and 428 in 2020; finsummaries
# is populated 2010-2018 and empty from 2020.
FINSUMMARIES_LAST_YEAR = 2018
DEPOSITORY_FIRST_YEAR = 2020


class OcpfError(Exception):
    """A failure talking to the OCPF API."""


class UnknownCategoryError(ValueError):
    """A search category other than receipts or expenditures was requested."""


@dataclass
class Stats:
    """Cache hits and network fetches, reported when a collection finishes."""

    hits: int = 0
    fetches: int = 0

    def summary(self) -> str:
        total = self.hits + self.fetches
        return (
            f"{total} OCPF requests: {self.hits} from cache, "
            f"{self.fetches} fetched"
        )


STATS = Stats()
CACHE_ONLY = False


def _cache_path(path: str, params: dict | None):
    """A stable file per (path, params) pair.

    The key is hashed rather than built from the query string so that a long
    parameter set stays a legal filename; the readable path prefix is kept so
    the cache can be browsed.
    """
    payload = json.dumps(
        {"path": path, "params": {k: str(v) for k, v in sorted((params or {}).items())}},
        sort_keys=True,
    )
    digest = hashlib.sha256(payload.encode()).hexdigest()[:20]
    slug = path.strip("/").replace("/", "_")[:60]
    return config.OCPF_CACHE / f"{slug}__{digest}.json"


def get_json(path: str, params: dict | None = None, *, refresh: bool = False):
    """GET a path from the OCPF API, caching the parsed body on disk."""
    cached = _cache_path(path, params)
    if cached.exists() and not refresh:
        STATS.hits += 1
        return json.loads(cached.read_text())
    if CACHE_ONLY:
        raise OcpfError(f"cache-only mode is missing {cached.name}")

    url = BASE_URL + path.lstrip("/")
    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.get(
                url, params=params, timeout=REQUEST_TIMEOUT_SECONDS
            )
            if response.status_code >= 400:
                raise OcpfError(f"HTTP {response.status_code} for {path}")
            body = response.json()
            break
        except (requests.RequestException, ValueError, OcpfError) as exc:
            last_error = exc
            if attempt == MAX_ATTEMPTS:
                raise OcpfError(f"{path} failed after {MAX_ATTEMPTS} attempts: {exc}")
            time.sleep(REQUEST_DELAY_SECONDS * attempt)
    else:  # pragma: no cover - loop always breaks or raises
        raise OcpfError(str(last_error))

    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_text(json.dumps(body))
    STATS.fetches += 1
    time.sleep(REQUEST_DELAY_SECONDS)
    return body


def parse_currency(value) -> float:
    """`"$1,234.56"` -> `1234.56`. Blank and None read as zero."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace("$", "").replace(",", "")
    if not text:
        return 0.0
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1]
    try:
        amount = float(text)
    except ValueError:
        return 0.0
    return -amount if negative else amount


def as_ocpf_date(value) -> str:
    """A date in the `M/D/YYYY` form the API's date filters expect."""
    import pandas as pd

    stamp = pd.Timestamp(value)
    return f"{stamp.month}/{stamp.day}/{stamp.year}"


@dataclass(frozen=True)
class DatedTotal:
    """A money total accumulated over an explicit, closed date window."""

    count: int
    total: float
    start: str
    end: str
    category: str


def dated_total(cpf_id, start, end, category: str = CATEGORY_RECEIPTS) -> DatedTotal:
    """Money a filer reported between two dates, inclusive.

    One request per window: `withSummary` returns the count and total for the
    whole filtered set, so nothing has to be paged to add it up.
    """
    if category not in CATEGORIES:
        raise UnknownCategoryError(
            f"category {category!r} is not one of {sorted(CATEGORIES)}; the "
            "endpoint silently returns receipts for an unrecognised value, so "
            "it is rejected here rather than sent"
        )
    start_text, end_text = as_ocpf_date(start), as_ocpf_date(end)
    params = dated_total_params(cpf_id, start, end, category)
    payload = get_json(SEARCH_ITEMS_PATH, params)
    summary = (payload or {}).get("summary") or {}
    return DatedTotal(
        count=int(summary.get("count") or 0),
        total=parse_currency(summary.get("total", summary.get("totalDisplay"))),
        start=start_text,
        end=end_text,
        category=category,
    )


def dated_total_params(cpf_id, start, end, category: str) -> dict:
    """Exact API parameters and cache identity inputs for a dated total."""
    return {
        "SearchTypeCategory": category,
        "CpfId": int(cpf_id),
        "StartDate": as_ocpf_date(start),
        "EndDate": as_ocpf_date(end),
        "PageSize": 1,
        "StartIndex": 1,
        "withSummary": "true",
    }


def dated_total_cache_identity(cpf_id, start, end, category: str) -> str:
    """Repo-relative cache file backing a dated total."""
    path = _cache_path(
        SEARCH_ITEMS_PATH, dated_total_params(cpf_id, start, end, category)
    )
    return str(path.relative_to(config.ROOT))


# The race table's office labels against OCPF's.
OFFICE_TO_OCPF = {"State Senate": "Senate", "State Representative": "House"}


# The race table spells some ordinals as words ("First Plymouth & Norfolk")
# where OCPF always uses digits ("1st Plymouth and Norfolk").
ORDINAL_WORDS = {
    "first": "1st", "second": "2nd", "third": "3rd", "fourth": "4th",
    "fifth": "5th", "sixth": "6th", "seventh": "7th", "eighth": "8th",
    "ninth": "9th", "tenth": "10th", "eleventh": "11th", "twelfth": "12th",
    "thirteenth": "13th", "fourteenth": "14th", "fifteenth": "15th",
    "sixteenth": "16th", "seventeenth": "17th", "eighteenth": "18th",
    "nineteenth": "19th", "twentieth": "20th",
}
ORDINAL_TENS = {"twenty": 20, "thirty": 30, "forty": 40}
ORDINAL_ONES = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
    "seventh": 7,
    "eighth": 8,
    "ninth": 9,
}


def _ordinal(number: int) -> str:
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def normalize_district(text: str) -> str:
    """A district description reduced to comparable words.

    `&` and `and` are the same separator to OCPF, the two sides disagree about
    punctuation, and ordinals appear as words on one side and digits on the
    other, so all three are normalized before comparison.
    """
    import re

    lowered = str(text).lower().replace("&", " and ")
    words = re.sub(r"[^a-z0-9 ]", " ", lowered).split()
    normalized = []
    index = 0
    while index < len(words):
        word = words[index]
        if (
            word in ORDINAL_TENS
            and index + 1 < len(words)
            and words[index + 1] in ORDINAL_ONES
        ):
            normalized.append(
                _ordinal(ORDINAL_TENS[word] + ORDINAL_ONES[words[index + 1]])
            )
            index += 2
            continue
        normalized.append(ORDINAL_WORDS.get(word, word))
        index += 1
    return " ".join(normalized)


# Districts the election results and OCPF enumerate differently. Both name the
# same seat; they disagree about which counties to list. Keyed and valued on
# the normalized form, and kept deliberately small -- an alias is a claim that
# two names are the same seat, which is worth making one at a time rather than
# inferring from county overlap.
DISTRICT_ALIASES = {
    # 2016 Senate, won by Adam Hinds. The results table lists three counties,
    # OCPF four (code 154). The value is the name as OCPF spells it, because it
    # is passed through to the CLI rather than compared.
    "berkshire hampshire and franklin": "Berkshire, Hampshire, Franklin and Hampden",
}


def ocpf_name(district_display: str) -> str:
    """The name OCPF uses for a district the results table names differently."""
    return DISTRICT_ALIASES.get(
        normalize_district(district_display), str(district_display)
    )


def legislative_districts() -> list[dict]:
    """Every House and Senate district OCPF knows, with its code."""
    payload = get_json(DISTRICTS_PATH)
    rows = payload if isinstance(payload, list) else []
    return [row for row in rows if row.get("office") in ("House", "Senate")]


def district_index() -> dict:
    """`(ocpf office, normalized description)` -> district code."""
    return {
        (row["office"], normalize_district(row.get("description", ""))): row["code"]
        for row in legislative_districts()
    }


def resolve_district(office: str, district_display: str, index: dict | None = None):
    """The OCPF district code for a race, or None if it does not resolve.

    Codes are stable enough across redistricting that the current district list
    retrieves filers for 2010; the mapping is by description, not by boundary.
    """
    index = district_index() if index is None else index
    ocpf_office = OFFICE_TO_OCPF.get(office)
    if ocpf_office is None:
        return None
    return index.get((ocpf_office, normalize_district(district_display)))


# --- Rosters, via the `ocpf` CLI -------------------------------------------
#
# Who ran in a district-year is the hard part of this collection, and it is
# solved in `ocpf` rather than here. Three problems make a hand-rolled version
# wrong in ways that are quiet: districts retired at redistricting are absent
# from the API's `districts` reference, which is the present map only; years
# with no regular election carry no roster in any on-ballot feed, which is
# exactly where special elections live; and a district's code for a past year
# can only be recovered by tallying its filers and discarding those who have
# since sought a different seat. `ocpf` 0.4 does all three.
#
# The CLI's `--json` output is the interface, not its internals. Output is
# cached per invocation, so a rerun costs no subprocess and no network.

CLI_COMMAND = "ocpf"
CLI_TIMEOUT_SECONDS = 600


class RosterUnavailable(Exception):
    """The CLI could not resolve a race's roster, with its reason."""


def _cli_cache_path(args: list) -> Path:
    payload = json.dumps(args, sort_keys=True)
    digest = hashlib.sha256(payload.encode()).hexdigest()[:20]
    return config.OCPF_CACHE / "cli" / f"race__{digest}.json"


def _run_cli(args: list) -> list:
    """Run `ocpf ... --json`, caching stdout and the failure alike.

    A refusal is cached too: an ambiguous district name is a property of the
    question, not a transient failure, and re-asking costs a subprocess to get
    the same answer.
    """
    cached = _cli_cache_path(args)
    if cached.exists():
        STATS.hits += 1
        payload = json.loads(cached.read_text())
    else:
        if CACHE_ONLY:
            raise RosterUnavailable(f"cache-only mode is missing {cached.name}")
        completed = subprocess.run(
            [CLI_COMMAND, *args, "--json"],
            capture_output=True,
            text=True,
            timeout=CLI_TIMEOUT_SECONDS,
            check=False,
        )
        try:
            rows = json.loads(completed.stdout) if completed.stdout.strip() else None
        except json.JSONDecodeError:
            rows = None
        payload = {
            "rows": rows,
            "error": None if rows is not None else (completed.stderr or "").strip(),
        }
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_text(json.dumps(payload))
        STATS.fetches += 1
    if payload["rows"] is None:
        raise RosterUnavailable(payload["error"] or "ocpf returned no JSON")
    return payload["rows"]


def _normalize_cli_row(row: dict, source: str = "") -> dict:
    """One CLI candidate row in this pipeline's shape.

    The regular and special paths name the filer differently -- `filerName` and
    `name` -- so both are accepted rather than assuming either.
    """
    return {
        "cpf_id": row.get("cpfId"),
        "filer_name": row.get("filerName") or row.get("name") or "",
        "party": row.get("partyAffiliation", ""),
        "district_code": row.get("districtCodeSought") or row.get("districtCode"),
        "stage": row.get("stage", ""),
        "roster_source": source,
    }


def race_roster(year: int, office: str, district_display: str,
                is_special: bool = False, index: dict | None = None) -> list[dict]:
    """The candidates OCPF lists for one race, with their cpfIds.

    The district is named by its code where the current map still has it, and
    by name otherwise. The code matters because a name alone can be ambiguous:
    `1st Suffolk` is both a Senate and a House district, and the CLI refuses to
    guess between them -- correctly, but a caller that knows the chamber should
    not be asking an ambiguous question in the first place.
    """
    def keep(rows, source):
        return [
            candidate
            for candidate in (_normalize_cli_row(row, source) for row in rows)
            if candidate["cpf_id"]
        ]

    if not is_special:
        # For a regular race in a year the legislative feed covers, the feed
        # answers directly and exactly. Going through the CLI here would ask a
        # question it cannot express: it resolves a retired district by name
        # but rejects the very code it prints for one, so a retired district
        # whose name is also a prefix of two current ones -- `Plymouth and
        # Norfolk` -- is unreachable either way.
        direct = _depository_rows(year, office, district_display)
        if direct:
            return keep(direct, "legislative-feed")

    code = resolve_district(office, district_display, index)
    target = str(code) if code is not None else ocpf_name(district_display)
    args = ["race", target, "--year", str(int(year))]
    if is_special:
        args.append("--special")
    try:
        return keep(_run_cli(args), "special" if is_special else "regular")
    except RosterUnavailable:
        if not is_special:
            raise
        # OCPF's special-election log does not name every special. Where it
        # does not, the same year's ordinary roster still holds the filers --
        # in a year with no regular election those rows *are* the special's
        # candidates. It is a candidate pool to match known names against, not
        # an assertion about which contest each filer ran in, so a wider pool
        # costs nothing; the fallback is recorded so a match made from one is
        # auditable.
        direct = _depository_rows(year, office, district_display)
        if direct:
            return keep(direct, "legislative-feed-fallback")
        fallback = ["race", target, "--year", str(int(year))]
        return keep(_run_cli(fallback), "regular-fallback")


# The legislative feed pairs an era-correct `officeSought` string with a usable
# `districtCodeSought` on every row, so a district retired since can still be
# named for a year the feed covers. Coverage starts abruptly at 2020.
DEPOSITORY_PATH = "reports/legislative/depository/ytd/{year}"


def _depository_rows(year: int, office: str, district_display: str) -> list[dict]:
    """Legislative-feed rows whose era-correct district name matches exactly."""
    if year < DEPOSITORY_FIRST_YEAR:
        return []
    ocpf_office = OFFICE_TO_OCPF.get(office)
    wanted = normalize_district(district_display)
    payload = get_json(DEPOSITORY_PATH.format(year=int(year)))
    rows = payload.get("reports", []) if isinstance(payload, dict) else []
    matched = []
    for row in rows:
        sought = str(row.get("officeSought", ""))
        if "," not in sought:
            continue
        head, description = sought.split(",", 1)
        if head.strip() != ocpf_office:
            continue
        if normalize_district(description) == wanted:
            matched.append(row)
    return matched


def era_code(year: int, office: str, district_display: str):
    """The code a district had in a year the legislative feed covers.

    Resolution is by exact normalized description, never substring: `ocpf`
    matches a district name loosely and rightly refuses when the name is
    ambiguous, but `Plymouth and Norfolk` is a real retired district whose name
    is a prefix of two current ones. Asking by code avoids posing the ambiguous
    question at all.
    """
    if year < DEPOSITORY_FIRST_YEAR:
        return None
    for row in _depository_rows(year, office, district_display):
        code = row.get("districtCodeSought")
        if code:
            return code
    return None
