"""Attaching OCPF campaign finance to legislative races.

Two stages. `resolve` matches every race's candidates to OCPF filers and
publishes both the resolution and its failures; `collect` reads money for the
resolved filers over an explicit pre-election window. They are separate because
the first is where the uncertainty lives: a name that resolves to the wrong
filer attributes one campaign's money to another candidate, and a name that
resolves to nothing must stay distinguishable from a candidate who raised
nothing (campaign-finance spec).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from . import config, filer_match, ocpf, races as races_module

# Parallelism for the roster stage. Modest on purpose: this is a public API and
# the work is cached after the first run.
ROSTER_WORKERS = 4

RACE_TABLE = races_module.RACE_FILE
UNMATCHED_REPORT = config.REPORT_DIR / "ocpf_unmatched_candidates.csv"
CANDIDATE_FINANCE = races_module.RACE_DIR / "ma_race_finance.csv.gz"

# The two candidates a race's response is measured between.
ROLES = (("dem", "dem_candidate"), ("opp", "opponent_candidate"))


def _roster_for(item, index):
    _, race = item
    try:
        return ocpf.race_roster(
            race.election_year, race.office, race.district_display,
            bool(race.is_special), index,
        ), ""
    except ocpf.RosterUnavailable as exc:
        return [], str(exc).replace("\n", " ")[:200]


def resolve(races: pd.DataFrame | None = None) -> pd.DataFrame:
    """Match every race's candidates to OCPF filers, at candidate grain."""
    races = pd.read_csv(RACE_TABLE) if races is None else races
    index = ocpf.district_index()
    items = list(races.iterrows())
    with ThreadPoolExecutor(max_workers=ROSTER_WORKERS) as pool:
        fetched = list(pool.map(lambda item: _roster_for(item, index), items))

    rows = []
    for (_, race), (roster, error) in zip(items, fetched):
        for role, column in ROLES:
            candidate = getattr(race, column)
            if pd.isna(candidate):
                continue
            match = filer_match.match_candidate(candidate, roster)
            rows.append(
                {
                    "election_id": race.election_id,
                    "election_year": race.election_year,
                    "election_date": race.election_date,
                    "office": race.office,
                    "district_display": race.district_display,
                    "is_special": bool(race.is_special),
                    "role": role,
                    "candidate": candidate,
                    "cpf_id": match.cpf_id,
                    "filer_name": match.filer_name,
                    "match_rule": match.rule,
                    "filers_considered": match.considered,
                    "roster_source": roster[0]["roster_source"] if roster else "",
                    "roster_error": error,
                }
            )
    return pd.DataFrame(rows)


def publish_unmatched(resolved: pd.DataFrame) -> pd.DataFrame:
    """Write the review file of candidates no filer was found for.

    Written even when empty, so its absence means the stage did not run rather
    than that nothing failed (campaign-finance spec, "An unmatched candidate is
    published, not zeroed").
    """
    unmatched = resolved[~resolved["match_rule"].isin(filer_match.MATCHED_RULES)]
    columns = [
        "election_id", "election_year", "election_date", "office",
        "district_display", "is_special", "role", "candidate", "match_rule",
        "filers_considered", "roster_source", "roster_error",
    ]
    config.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    frame = unmatched[columns].sort_values(["election_year", "district_display"])
    frame.to_csv(UNMATCHED_REPORT, index=False)
    print(f"wrote {len(frame):>7} rows -> {UNMATCHED_REPORT.relative_to(config.ROOT)}")
    return frame


def match_summary(resolved: pd.DataFrame) -> pd.DataFrame:
    """Match rate per year, so an era-specific failure is visible."""
    matched = resolved["match_rule"].isin(filer_match.MATCHED_RULES)
    return (
        resolved.assign(matched=matched)
        .groupby("election_year")
        .agg(candidates=("matched", "size"), matched=("matched", "sum"))
        .assign(rate=lambda f: (f["matched"] / f["candidates"]).round(4))
        .reset_index()
    )


# The pre-election windows money is measured over. Each is 365 days ending
# `lead` days before the race's own election date -- trailing rather than
# calendar year-to-date, because a special election held in January is funded
# in the previous calendar year, and relative to the election rather than to a
# fixed date, because a race held in March has no October (design.md, D2).
WINDOW_DAYS = 365
WINDOW_LEADS = {"primary": 14, "wide": 60}

CATEGORIES = {
    "receipts": ocpf.CATEGORY_RECEIPTS,
    "expenditures": ocpf.CATEGORY_EXPENDITURES,
}


def window_for(election_date, lead_days: int) -> tuple:
    """The closed window a race's money is accumulated over."""
    election = pd.Timestamp(election_date)
    end = election - pd.Timedelta(days=lead_days)
    return end - pd.Timedelta(days=WINDOW_DAYS), end


def collect(resolved: pd.DataFrame | None = None, write: bool = True) -> pd.DataFrame:
    """Money for every resolved candidate, over every window and category.

    Only matched candidates are asked about. An unmatched candidate has no
    filer to ask, and recording a zero for one would make a lookup failure
    indistinguishable from a candidate who raised nothing.
    """
    resolved = resolve() if resolved is None else resolved
    matched = resolved[resolved["match_rule"].isin(filer_match.MATCHED_RULES)]

    def one(row):
        out = {}
        for window, lead in WINDOW_LEADS.items():
            start, end = window_for(row.election_date, lead)
            out[f"as_of_{window}"] = end.date().isoformat()
            for label, category in CATEGORIES.items():
                total = ocpf.dated_total(row.cpf_id, start, end, category)
                out[f"{label}_{window}"] = total.total
                out[f"{label}_{window}_items"] = total.count
        return out

    with ThreadPoolExecutor(max_workers=ROSTER_WORKERS) as pool:
        money = list(pool.map(one, (r for _, r in matched.iterrows())))

    frame = pd.concat(
        [matched.reset_index(drop=True), pd.DataFrame(money)], axis=1
    )
    # Unmatched candidates stay in the published table with their money absent,
    # so the race rollup can tell "no filer found" from "raised nothing".
    unmatched = resolved[~resolved["match_rule"].isin(filer_match.MATCHED_RULES)]
    frame = pd.concat([frame, unmatched], ignore_index=True)
    frame = frame.sort_values(["election_year", "election_id", "role"])
    if write:
        config.write_csv(frame, CANDIDATE_FINANCE) if hasattr(config, "write_csv") else None
        if not hasattr(config, "write_csv"):
            CANDIDATE_FINANCE.parent.mkdir(parents=True, exist_ok=True)
            frame.to_csv(CANDIDATE_FINANCE, index=False, compression="gzip")
            print(f"wrote {len(frame):>7} rows -> "
                  f"{CANDIDATE_FINANCE.relative_to(config.ROOT)}")
    return frame
