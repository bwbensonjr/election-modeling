"""Bulk retrieval across an enumerated election set, with a failure record."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import requests

from . import config, fetch


def fetch_many(
    elections: pd.DataFrame, label: str, report_name: str, force: bool = False
) -> pd.DataFrame:
    """Fetch every election in `elections`, recording failures rather than raising.

    Returns the failure report and writes it to `data/reports/`.
    """
    session = requests.Session()
    failures: list[dict] = []
    total = len(elections)
    cached = downloaded = 0

    for i, row in enumerate(elections.itertuples(index=False), start=1):
        try:
            result = fetch.fetch_election(
                int(row.election_id), session=session, force=force
            )
        except fetch.PayloadError as exc:
            failures.append(
                {
                    "election_id": row.election_id,
                    "election_date": row.election_date,
                    "office": row.office,
                    "district_display": row.district_display,
                    "reason": str(exc),
                }
            )
        else:
            if result.from_cache:
                cached += 1
            else:
                downloaded += 1
        if i % 50 == 0 or i == total:
            print(
                f"{label}: {i}/{total} "
                f"(downloaded {downloaded}, cached {cached}, failed {len(failures)})",
                flush=True,
            )

    report = pd.DataFrame(
        failures,
        columns=[
            "election_id",
            "election_date",
            "office",
            "district_display",
            "reason",
        ],
    )
    path = config.REPORT_DIR / report_name
    path.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(path, index=False)
    print(
        f"{label}: done. downloaded={downloaded} cached={cached} "
        f"failed={len(failures)} -> {path.relative_to(config.ROOT)}",
        flush=True,
    )
    return report
