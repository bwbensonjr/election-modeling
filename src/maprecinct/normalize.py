"""Normalize cached electionstats payloads into a single long-format schema.

Source files differ across vintages in their candidate columns, so a wide
layout cannot share one schema. The normalized form is keyed by
`(election_id, city_town, ward, precinct, candidate)`; the precinct key is
constant across vintages and the candidate dimension absorbs the variation
(precinct-election-results spec, "normalized to a common schema").
"""

from __future__ import annotations

import csv
import io
import re

import pandas as pd

from . import config, fetch

NORMALIZED_COLUMNS = [
    "election_id",
    "city_town",
    "ward",
    "precinct",
    "candidate",
    "party",
    "row_kind",
    "votes",
]

# Trailing columns that are not candidates.
ALL_OTHERS = "All Others"
BLANKS = "Blanks"
TOTAL = "Total Votes Cast"
NON_CANDIDATE_COLUMNS = {ALL_OTHERS: "all_others", BLANKS: "blanks", TOTAL: "total"}

COMPASS = {
    "N. ": "North ",
    "E. ": "East ",
    "S. ": "South ",
    "W. ": "West ",
}


def unabbreviate_compass(name: str) -> str:
    """Expand the leading compass abbreviation used by electionstats."""
    for short, full in COMPASS.items():
        if name.startswith(short):
            return full + name[len(short) :]
    return name


def _to_votes(value: str) -> int:
    text = value.strip().replace(",", "")
    if not text:
        return 0
    return int(text)


def normalize_payload(election_id: int, text: str) -> pd.DataFrame:
    """Turn one cached payload into normalized long-format rows."""
    body = fetch.validate_payload(text)
    rows = [r for r in csv.reader(io.StringIO(text)) if any(c.strip() for c in r)]
    header = rows[0]

    # The line after the header carries party labels aligned with the candidate
    # columns; its length fixes how many of the columns are candidates.
    party_row = rows[1] if len(rows) > 1 and not rows[1][0].strip() else []
    parties = party_row[3:]
    candidate_count = len(parties)
    candidate_names = header[3 : 3 + candidate_count]

    columns: list[tuple[str, str | None, str]] = [
        (name, parties[i].strip() or None, "candidate")
        for i, name in enumerate(candidate_names)
    ]
    for index in range(3 + candidate_count, len(header)):
        label = header[index].strip()
        kind = NON_CANDIDATE_COLUMNS.get(label)
        if kind is None:
            raise ValueError(
                f"election {election_id}: unexpected trailing column {label!r}"
            )
        columns.append((label, None, kind))

    records: list[dict] = []
    for row in body:
        city_town = unabbreviate_compass(row[0].strip())
        ward = row[1].strip() or "-"
        precinct = row[2].strip() or "1"
        for offset, (label, party, kind) in enumerate(columns):
            index = 3 + offset
            if index >= len(row):
                continue
            records.append(
                {
                    "election_id": election_id,
                    "city_town": city_town,
                    "ward": ward,
                    "precinct": precinct,
                    "candidate": label.strip(),
                    "party": party,
                    "row_kind": kind,
                    "votes": _to_votes(row[index]),
                }
            )

    frame = pd.DataFrame.from_records(records, columns=NORMALIZED_COLUMNS)
    return frame


def normalize_election(election_id: int) -> pd.DataFrame:
    return normalize_payload(
        election_id, fetch.cache_path(election_id).read_text()
    )


def normalize_many(elections: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for election_id in elections["election_id"]:
        path = fetch.cache_path(int(election_id))
        if not path.exists():
            continue
        frames.append(normalize_election(int(election_id)))
    if not frames:
        return pd.DataFrame(columns=NORMALIZED_COLUMNS)
    return pd.concat(frames, ignore_index=True)
