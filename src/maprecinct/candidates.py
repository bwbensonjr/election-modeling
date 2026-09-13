"""Match precinct-return candidates to their published candidate records.

The precinct returns name a candidate as the returns spell it; the published
candidate table names the same person as the candidate record spells it. The
two disagree for 58 of 2,389 race-candidate pairs -- mojibake from a UTF-8
string read as latin-1 (`Chang-DÃ­az`), a familiar form against a legal one
(`Jack Hart`), a dropped terminal period (`Humason, Jr`), a write-in marker
carried into the name (`Kevin Patrick McKeown (W)`).

This matters because `is_write_in` lives only on the candidate record, and the
write-in threshold (design.md, D3) needs it for every named candidate. A
candidate that fails to match would silently lose its write-in flag and be
treated as a ballot line, so the match is layered and then asserted rather
than left partial.
"""

from __future__ import annotations

import re
import unicodedata

import pandas as pd

from . import config

DEMOCRATIC = "Democratic"
REPUBLICAN = "Republican"


class UnmatchedCandidateError(ValueError):
    """A candidate in the precinct returns has no published candidate record."""


def normalize_name(name) -> str:
    """A name reduced to the part both sources agree on.

    Repairs the latin-1/UTF-8 mojibake first, then strips accents, case, and
    every non-letter, so `Sonia Rosa Chang-DÃ­az` and `Sonia Chang-Diaz`
    reduce toward the same string and `Humason, Jr` matches `Humason, Jr.`.
    """
    if not isinstance(name, str):
        return ""
    if "Ã" in name:
        # A UTF-8 byte string that was decoded as latin-1 somewhere upstream.
        # Round-tripping it back recovers the intended characters; if it does
        # not decode cleanly the original is kept rather than mangled further.
        try:
            name = name.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))
    name = re.sub(r"[^a-z ]", " ", name.lower())
    return " ".join(name.split())


def _records() -> pd.DataFrame:
    """Published candidate records for the legislative general elections."""
    records = config.general_candidates()
    records = records[
        records["office"].isin(config.LEGISLATIVE_OFFICES)
        & (records["party_primary"] == False)  # noqa: E712 -- a column, not a bool
    ]
    records = records[
        ["election_id", "name", "is_write_in", "party_role", "num_votes"]
    ].copy()
    records["is_write_in"] = records["is_write_in"].astype(bool)
    records["normalized_name"] = records["name"].map(normalize_name)
    return records


def _match_by_votes(unmatched: pd.DataFrame, records: pd.DataFrame) -> dict:
    """Resolve a name mismatch by its district vote total within the race.

    A candidate whose name did not match still has to have the same number of
    votes in both sources, and within a single race that total is very nearly
    unique. Only an unambiguous single match is accepted; anything else is
    left unmatched and reported.
    """
    by_race = {
        election_id: group for election_id, group in records.groupby("election_id")
    }
    resolved = {}
    for row in unmatched.itertuples(index=False):
        group = by_race.get(row.election_id)
        if group is None:
            continue
        hits = group[group["num_votes"] == row.votes]
        if len(hits) == 1:
            resolved[(row.election_id, row.candidate)] = hits.iloc[0]
    return resolved


def race_candidate_totals(results: pd.DataFrame) -> pd.DataFrame:
    """District totals per candidate per race, carrying the write-in flag.

    One row per `(election_id, candidate, party)` with the candidate's district
    vote total, its share of votes cast for named candidates, and whether the
    candidate was a write-in. Sorted strongest first within a race, which is
    the order the contest selection relies on.
    """
    totals = (
        results[results["row_kind"] == "candidate"]
        .groupby(["election_id", "candidate", "party"], as_index=False, dropna=False)[
            "votes"
        ]
        .sum()
    )

    records = _records()
    duplicate = records.duplicated(["election_id", "normalized_name"], keep=False)
    if duplicate.any():
        # Two candidates in one race whose names reduce to the same string would
        # make the name join ambiguous; drop them to the vote-total layer rather
        # than letting the merge multiply rows.
        records = records[~duplicate]

    totals["normalized_name"] = totals["candidate"].map(normalize_name)
    merged = totals.merge(
        records[["election_id", "normalized_name", "is_write_in", "party_role"]],
        on=["election_id", "normalized_name"],
        how="left",
    )
    if len(merged) != len(totals):
        raise UnmatchedCandidateError(
            "the candidate-record join multiplied rows; a race carries two "
            "records reducing to the same normalized name"
        )

    unresolved = merged["is_write_in"].isna()
    if unresolved.any():
        resolved = _match_by_votes(merged[unresolved], _records())
        for index, row in merged[unresolved].iterrows():
            record = resolved.get((row["election_id"], row["candidate"]))
            if record is not None:
                merged.at[index, "is_write_in"] = bool(record["is_write_in"])
                merged.at[index, "party_role"] = record["party_role"]

    still_missing = merged[merged["is_write_in"].isna()]
    if len(still_missing):
        listing = "\n".join(
            f"  election {row.election_id}: {row.candidate!r} ({row.votes} votes)"
            for row in still_missing.itertuples(index=False)
        )
        raise UnmatchedCandidateError(
            f"{len(still_missing)} candidate(s) in the precinct returns have no "
            f"published candidate record, so their write-in status is unknown:\n"
            f"{listing}"
        )

    merged["is_write_in"] = merged["is_write_in"].astype(bool)

    named_votes = merged.groupby("election_id")["votes"].transform("sum")
    merged["named_votes"] = named_votes
    merged["share"] = (merged["votes"] / named_votes).where(named_votes > 0, 0.0)

    return merged.sort_values(
        ["election_id", "votes"], ascending=[True, False], ignore_index=True
    )


def admitted(totals: pd.DataFrame, threshold: float) -> pd.Series:
    """Which candidates count, at a write-in threshold (design.md, D3).

    A ballot-line candidate always counts. A write-in counts when its share of
    votes cast for named candidates reaches the threshold. The share is a
    district total, so a write-in that clears the threshold is admitted in
    every precinct of the race, including ones where it drew no votes.
    """
    return (~totals["is_write_in"]) | (totals["share"] >= threshold)
