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

from . import build, config, filer_match, ocpf, races as races_module

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
        build.write_csv(frame, CANDIDATE_FINANCE)
    return frame


# --- Race-grain rollup -------------------------------------------------------

# The money columns the race table carries, one per role, measure and window.
MEASURES = tuple(CATEGORIES)
WINDOWS = tuple(WINDOW_LEADS)

MONEY_COLUMNS = tuple(
    f"{role}_{measure}_{window}"
    for role, _ in ROLES
    for measure in MEASURES
    for window in WINDOWS
)
AS_OF_COLUMNS = tuple(f"money_as_of_{window}" for window in WINDOWS)
MATCH_COLUMNS = ("money_candidates_matched", "money_candidates_total", "money_complete")
RACE_MONEY_COLUMNS = ("election_id",) + AS_OF_COLUMNS + MONEY_COLUMNS + MATCH_COLUMNS

# Money is compared between the two sides, so a hundredth of a dollar of
# disagreement between a race row and the candidate rows behind it is already
# a rollup that did not come from those rows.
MONEY_TOLERANCE = 0.005


class MoneyDisagreementError(ValueError):
    """A race's money columns do not follow from its candidate rows."""


class AsOfAfterElectionError(ValueError):
    """A money figure was accumulated to a date on or after its own election."""


def _one_race_money(group: pd.DataFrame) -> dict:
    """The race-grain money row for one race's candidate rows.

    An unmatched candidate contributes no money at all rather than a zero: a
    filer that was never found and a filer that raised nothing are different
    facts, and collapsing them would put a large fake zero exactly where the
    match is hardest (design.md, D4).
    """
    matched = group["match_rule"].isin(filer_match.MATCHED_RULES)
    row = {
        "election_id": int(group["election_id"].iloc[0]),
        "money_candidates_matched": int(matched.sum()),
        "money_candidates_total": int(len(group)),
        "money_complete": bool(matched.all()),
    }
    for window in WINDOWS:
        dates = group[f"as_of_{window}"].dropna().unique()
        if len(dates) > 1:
            raise MoneyDisagreementError(
                f"election {row['election_id']}: candidate rows disagree on "
                f"as_of_{window} = {sorted(dates)}"
            )
        # A race whose candidates were all unmatched has no collected window,
        # so its as-of date is recomputed from the election date rather than
        # left blank: the date the race would have been measured to is a
        # property of the race, not of whether a filer was found.
        row[f"money_as_of_{window}"] = (
            str(dates[0])
            if len(dates)
            else window_for(group["election_date"].iloc[0], WINDOW_LEADS[window])[1]
            .date()
            .isoformat()
        )
    for role, _ in ROLES:
        side = group[group["role"] == role]
        for measure in MEASURES:
            for window in WINDOWS:
                column = f"{role}_{measure}_{window}"
                values = side[f"{measure}_{window}"].dropna() if len(side) else []
                row[column] = float(values.iloc[0]) if len(values) else pd.NA
    return row


def race_money(candidates: pd.DataFrame | None = None) -> pd.DataFrame:
    """Roll the candidate finance table up to one row per race."""
    if candidates is None:
        candidates = pd.read_csv(CANDIDATE_FINANCE)
    rows = [
        _one_race_money(group)
        for _, group in candidates.groupby("election_id", sort=False)
    ]
    frame = pd.DataFrame(rows, columns=list(RACE_MONEY_COLUMNS))
    for column in MONEY_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.sort_values("election_id", ignore_index=True)


def check_as_of(races: pd.DataFrame) -> None:
    """Refuse a money figure measured on or after the election it describes."""
    election = pd.to_datetime(races["election_date"])
    for column in AS_OF_COLUMNS:
        if column not in races.columns:
            continue
        as_of = pd.to_datetime(races[column])
        late = races[as_of >= election]
        if len(late):
            first = late.iloc[0]
            raise AsOfAfterElectionError(
                f"{len(late)} races carry {column} on or after their own "
                f"election, beginning with election {first['election_id']} "
                f"({first[column]} against {first['election_date']}); a figure "
                "measured then would be reading the result"
            )


def check_consistency(races: pd.DataFrame, candidates: pd.DataFrame | None = None) -> None:
    """Fail unless every race's money follows from its own candidate rows.

    The race table is published alongside the candidate table it was built
    from, so a reader can check one against the other. This is that check run
    at build time, so a disagreement stops the build rather than being
    published (race-training-set spec, "A race row agrees with its candidate
    rows").
    """
    if not set(MONEY_COLUMNS) <= set(races.columns):
        return
    expected = race_money(candidates).set_index("election_id")
    published = races.set_index("election_id")
    shared = published.index.intersection(expected.index)
    missing = published.index.difference(expected.index)
    if len(missing):
        raise MoneyDisagreementError(
            f"{len(missing)} races carry money columns with no candidate rows "
            f"behind them, beginning with election {missing[0]}"
        )
    disagreements = []
    for column in MONEY_COLUMNS:
        left = published.loc[shared, column]
        right = expected.loc[shared, column]
        differs = (left.isna() != right.isna()) | (
            (left - right).abs() > MONEY_TOLERANCE
        ).fillna(False)
        for election_id in left.index[differs]:
            disagreements.append(
                f"  election {election_id}: {column} published "
                f"{left[election_id]!r} against {right[election_id]!r} rolled up"
            )
    for column in AS_OF_COLUMNS + MATCH_COLUMNS:
        left = published.loc[shared, column].astype(str)
        right = expected.loc[shared, column].astype(str)
        for election_id in left.index[left != right]:
            disagreements.append(
                f"  election {election_id}: {column} published "
                f"{left[election_id]!r} against {right[election_id]!r} rolled up"
            )
    if disagreements:
        raise MoneyDisagreementError(
            f"{len(disagreements)} race money values do not follow from the "
            "candidate rows behind them:\n" + "\n".join(disagreements[:20])
        )
    check_as_of(races)


def build_and_write() -> pd.DataFrame:
    """Run the whole collection, then rebuild the race table over it."""
    from . import races as races_build

    resolved = resolve()
    publish_unmatched(resolved)
    print(match_summary(resolved).to_string(index=False))
    frame = collect(resolved)
    print(ocpf.STATS.summary())
    races_build.build_and_write()
    return frame
