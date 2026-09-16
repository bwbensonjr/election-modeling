"""Derive uninterrupted incumbent tenure from ma-election-db history."""

from __future__ import annotations

import pandas as pd

YEARS_PER_DAY = 1.0 / 365.2425


class IncumbentTenureError(ValueError):
    """The upstream incumbent history cannot support one unambiguous chain."""


def _election_label(election_id, candidate_id) -> str:
    return f"election {int(election_id)}, candidate {int(candidate_id)}"


def _selected_candidate(
    candidates: pd.DataFrame, election_id, candidate_id
) -> pd.Series:
    matches = candidates[
        (candidates["election_id"] == election_id)
        & (candidates["candidate_id"] == candidate_id)
    ]
    label = _election_label(election_id, candidate_id)
    if len(matches) != 1:
        raise IncumbentTenureError(
            f"{label}: expected one selected incumbent row, found {len(matches)}"
        )
    return matches.iloc[0]


def _previous_victory(
    winners: pd.DataFrame,
    current: pd.Series,
    predecessor_district_id,
) -> pd.Series | None:
    earlier = winners[
        (winners["office_id"] == current["office_id"])
        & (winners["candidate_id"] == current["candidate_id"])
        & (winners["district_id"] == predecessor_district_id)
        & (winners["election_date"] < current["election_date"])
    ]
    label = _election_label(current["election_id"], current["candidate_id"])
    if earlier.empty:
        if _is_source_boundary(current):
            return None
        raise IncumbentTenureError(
            f"{label}: incumbent predecessor district {predecessor_district_id} "
            "has no earlier victory"
        )
    previous_date = earlier["election_date"].max()
    matches = earlier[earlier["election_date"] == previous_date]
    if len(matches) != 1:
        raise IncumbentTenureError(
            f"{label}: predecessor district {predecessor_district_id} has "
            f"{len(matches)} victories on {previous_date.date()}"
        )
    return matches.iloc[0]


def _is_source_boundary(row: pd.Series) -> bool:
    """Whether a missing predecessor is explained by filtered first-cycle data."""
    if bool(row.get("is_first_cycle", False)):
        return True
    first_cycle = pd.to_datetime(row.get("first_cycle_date"), errors="coerce")
    if pd.isna(first_cycle):
        return False
    # Legislative terms are two years. The next regular election can be a few
    # days over two calendar years later, and an intervening special remains
    # within this conservative three-year boundary window.
    return (pd.Timestamp(row["election_date"]) - first_cycle).days <= 3 * 366


def derive_incumbent_tenure(
    summaries: pd.DataFrame, candidates: pd.DataFrame
) -> pd.DataFrame:
    """Return one tenure record per summary election.

    The current election supplies identity and incumbent status only. Its
    outcome is never used: the chain begins at the selected incumbent's most
    recent earlier victory and follows upstream predecessor links backward.
    """
    history = candidates.copy()
    history["election_date"] = pd.to_datetime(history["election_date"])
    winners = history[history["is_winner"].fillna(False).astype(bool)]
    records = []

    for summary in summaries.itertuples(index=False):
        incumbent_id = getattr(summary, "id_incumbent")
        election_id = getattr(summary, "election_id")
        party = getattr(summary, "party_incumbent")
        num_incumbents = int(getattr(summary, "num_incumbents"))
        has_summary_incumbent = not pd.isna(incumbent_id)

        current_rows = history[history["election_id"] == election_id]
        upstream_incumbents = current_rows[
            current_rows["is_incumbent"].fillna(False).astype(bool)
        ]
        if not has_summary_incumbent:
            if num_incumbents != 0 or len(upstream_incumbents) != 0:
                raise IncumbentTenureError(
                    f"election {int(election_id)}: summary selects no incumbent "
                    f"but reports {num_incumbents} and candidate history marks "
                    f"{len(upstream_incumbents)}"
                )
            records.append(
                {
                    "election_id": election_id,
                    "incumbent_tenure_years": 0.0,
                    "incumbent_tenure_left_censored": False,
                }
            )
            continue

        current = _selected_candidate(history, election_id, incumbent_id)
        label = _election_label(election_id, incumbent_id)
        if not bool(current["is_incumbent"]):
            raise IncumbentTenureError(
                f"{label}: summary-selected incumbent is not marked incumbent"
            )
        if num_incumbents != len(upstream_incumbents):
            raise IncumbentTenureError(
                f"{label}: summary reports {num_incumbents} incumbents but "
                f"candidate history marks {len(upstream_incumbents)}"
            )
        if pd.isna(current["candidate_id"]) or pd.isna(current["district_id_prev"]):
            raise IncumbentTenureError(
                f"{label}: selected incumbent lacks a stable identity or "
                "predecessor district"
            )
        if current["party"] != party:
            raise IncumbentTenureError(
                f"{label}: selected incumbent party {current['party']!r} does "
                f"not match summary party {party!r}"
            )

        previous = _previous_victory(winners, current, current["district_id_prev"])
        if previous is None:
            start = current["election_date"]
            left_censored = True
        else:
            start = previous["election_date"]
            left_censored = bool(previous["is_first_cycle"])
        while previous is not None and bool(previous["is_incumbent"]):
            if pd.isna(previous["district_id_prev"]):
                raise IncumbentTenureError(
                    f"{_election_label(previous['election_id'], incumbent_id)}: "
                    "incumbent victory lacks a predecessor district"
                )
            predecessor = _previous_victory(
                winners, previous, previous["district_id_prev"]
            )
            if predecessor is None:
                left_censored = True
                break
            previous = predecessor
            start = previous["election_date"]

        current_date = pd.Timestamp(current["election_date"])
        tenure_years = (current_date - start).days * YEARS_PER_DAY
        records.append(
            {
                "election_id": election_id,
                "incumbent_tenure_years": tenure_years,
                "incumbent_tenure_left_censored": left_censored,
            }
        )

    return pd.DataFrame.from_records(records)
