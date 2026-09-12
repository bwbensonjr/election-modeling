"""Reconcile normalized precinct sums against published district totals.

Candidate naming differs between the two sources - the precinct payload heads
a presidential column "Kerry/ Edwards" where ma-election-db records
"John F. Kerry" - so reconciliation compares the vote quantities rather than
the names: total votes cast, blanks, all others, and the sorted candidate
totals. A race that agrees on all four has lost no precincts.
"""

from __future__ import annotations

import pandas as pd

from . import config, fetch, normalize

REPORT_COLUMNS = [
    "election_id",
    "election_date",
    "office",
    "district_display",
    "measure",
    "precinct_sum",
    "published",
    "difference",
]


def _published(election_id: int) -> dict:
    summaries = config.general_summaries()
    row = summaries.loc[summaries["election_id"] == election_id]
    if row.empty:
        return {}
    row = row.iloc[0]
    candidates = config.general_candidates()
    cand = candidates.loc[candidates["election_id"] == election_id, "num_votes"]
    return {
        "total": int(row["total_votes"]),
        "blanks": int(row["blank_votes"]),
        "all_others": int(row["all_other_votes"]),
        "candidates": sorted(int(v) for v in cand.dropna()),
    }


def reconcile_election(election_id: int, frame: pd.DataFrame | None = None) -> list[dict]:
    """Return zero or more mismatch records for one election."""
    frame = normalize.normalize_election(election_id) if frame is None else frame
    published = _published(election_id)
    if not published:
        return [
            {
                "election_id": election_id,
                "measure": "published_row",
                "precinct_sum": None,
                "published": None,
                "difference": None,
            }
        ]

    sums = frame.groupby("row_kind")["votes"].sum()
    observed = {
        "total": int(sums.get("total", 0)),
        "blanks": int(sums.get("blanks", 0)),
        "all_others": int(sums.get("all_others", 0)),
        "candidates": sorted(
            int(v)
            for v in frame.loc[frame["row_kind"] == "candidate"]
            .groupby("candidate")["votes"]
            .sum()
        ),
    }

    issues = []
    for measure in ("total", "blanks", "all_others"):
        if observed[measure] != published[measure]:
            issues.append(
                {
                    "election_id": election_id,
                    "measure": measure,
                    "precinct_sum": observed[measure],
                    "published": published[measure],
                    "difference": observed[measure] - published[measure],
                }
            )
    if observed["candidates"] != published["candidates"]:
        issues.append(
            {
                "election_id": election_id,
                "measure": "candidate_totals",
                "precinct_sum": str(observed["candidates"]),
                "published": str(published["candidates"]),
                "difference": None,
            }
        )
    return issues


def reconcile_many(elections: pd.DataFrame, report_name: str) -> pd.DataFrame:
    """Reconcile every cached election in `elections` and write the report."""
    meta = elections.set_index("election_id")
    issues: list[dict] = []
    checked = skipped = 0
    for election_id in elections["election_id"]:
        election_id = int(election_id)
        if not fetch.cache_path(election_id).exists():
            skipped += 1
            continue
        checked += 1
        for issue in reconcile_election(election_id):
            row = meta.loc[election_id]
            issue.update(
                {
                    "election_date": row["election_date"],
                    "office": row["office"],
                    "district_display": row["district_display"],
                }
            )
            issues.append(issue)

    report = pd.DataFrame(issues, columns=REPORT_COLUMNS)
    path = config.REPORT_DIR / report_name
    path.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(path, index=False)
    print(
        f"reconciled {checked} elections ({skipped} not cached): "
        f"{len(report)} mismatches -> {path.relative_to(config.ROOT)}"
    )
    return report
