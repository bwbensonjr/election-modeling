"""Assemble the race-precinct training table.

One row per (election, precinct) carrying the model's response and predictors
at precinct grain. The definitions follow mapoli/model/ma_leg_model.R so that a
district rollup of this table is comparable to the existing district-level
table (precinct-training-set spec).
"""

from __future__ import annotations

import pandas as pd

from . import build, config, crosswalk, pvi

KEY = crosswalk.KEY

TRAINING_FILE = config.PRECINCT_DIR / "ma_precinct_training_set.csv.gz"
EXCLUDED_REPORT = "training_excluded_races.csv"
MISSING_PVI_REPORT = "training_missing_pvi.csv"

# Legislative elections held on a presidential general election day.
PRESIDENTIAL_ELECTION_DATES = {
    "2012-11-06",
    "2016-11-08",
    "2020-11-03",
    "2024-11-05",
}

DEMOCRATIC = "Democratic"
REPUBLICAN = "Republican"

TRAINING_COLUMNS = [
    "election_id",
    "election_date",
    "election_year",
    "redistricting_cycle",
    "office",
    "district",
    "district_display",
    "city_town",
    "ward",
    "precinct",
    "dem_margin",
    "PVI_N",
    "incumbent_status",
    "pres_elec",
    "is_special",
    "num_candidates",
    "no_dem_candidate",
    "candidate_count",
    "dem_candidate_count",
    "dem_candidate",
    "opponent_candidate",
    "opponent_party",
    "dem_votes",
    "opponent_votes",
    "candidate_votes",
    "total_votes",
    "pvi_year",
    "pvi_provenance",
    "precinct_split_across_districts",
]


def incumbent_status(party_incumbent) -> str:
    """Classify a race's incumbent, following ma_leg_model.R.

    An unenrolled incumbent is grouped with GOP incumbents, as in the
    established model.
    """
    if pd.isna(party_incumbent):
        return "No_Incumbent"
    if party_incumbent == DEMOCRATIC:
        return "Dem_Incumbent"
    return "GOP_Incumbent"


def _race_candidates(race_rows: pd.DataFrame) -> pd.DataFrame:
    """District-level totals per candidate for one race."""
    return (
        race_rows[race_rows["row_kind"] == "candidate"]
        .groupby(["candidate", "party"], as_index=False, dropna=False)["votes"]
        .sum()
        .sort_values("votes", ascending=False, ignore_index=True)
    )


def _select_contest(totals: pd.DataFrame) -> tuple[dict | None, dict | None]:
    """Pick the Democrat and the strongest non-Democrat, once per race.

    Selecting the comparison candidate from district totals rather than
    per precinct keeps `dem_margin` coherent across a race's precincts
    (design.md, D7).
    """
    democrats = totals[totals["party"] == DEMOCRATIC]
    others = totals[totals["party"] != DEMOCRATIC]
    dem = democrats.iloc[0].to_dict() if len(democrats) else None
    if dem is None:
        # No Democrat: the Republican leads and the margin is negated, as in
        # ma_leg_model.R's democratic_margin().
        republicans = totals[totals["party"] == REPUBLICAN]
        if not len(republicans):
            return None, None
        leader = republicans.iloc[0].to_dict()
        rest = others[others["candidate"] != leader["candidate"]]
        runner_up = rest.iloc[0].to_dict() if len(rest) else None
        return None, (leader, runner_up)
    opponent = others.iloc[0].to_dict() if len(others) else None
    return dem, opponent


def _precinct_votes(race_rows: pd.DataFrame, candidate: str) -> pd.Series:
    rows = race_rows[
        (race_rows["row_kind"] == "candidate") & (race_rows["candidate"] == candidate)
    ]
    return rows.set_index([*KEY])["votes"]


def build_rows(results: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build training rows from normalized legislative results."""
    summaries = config.general_summaries().set_index("election_id")
    frames, excluded = [], []

    for election_id, race in results.groupby("election_id", sort=False):
        meta = summaries.loc[election_id]
        num_candidates = int(meta["num_candidates"])
        if num_candidates < 2:
            excluded.append(
                {
                    "election_id": election_id,
                    "election_date": meta["election_date"],
                    "office": meta["office"],
                    "district_display": meta["district_display"],
                    "reason": "uncontested: fewer than two candidates",
                }
            )
            continue

        totals = _race_candidates(race)
        dem, opponent = _select_contest(totals)
        if opponent is None:
            excluded.append(
                {
                    "election_id": election_id,
                    "election_date": meta["election_date"],
                    "office": meta["office"],
                    "district_display": meta["district_display"],
                    "reason": "no usable two-candidate contest",
                }
            )
            continue

        precinct_totals = (
            race[race["row_kind"] == "total"].set_index([*KEY])["votes"].rename("total")
        )
        # ma-election-db's percent_dem and percent_gop are shares of the votes
        # cast for named candidates, not of all votes cast: blanks and the
        # all-others bucket are excluded from the denominator. The precinct
        # margin uses the same base so the two are comparable.
        precinct_candidate_votes = (
            race[race["row_kind"] == "candidate"]
            .groupby([*KEY])["votes"]
            .sum()
            .rename("candidate_votes")
        )

        if dem is None:
            leader, runner_up = opponent
            leader_votes = _precinct_votes(race, leader["candidate"])
            other_votes = (
                _precinct_votes(race, runner_up["candidate"])
                if runner_up
                else pd.Series(0, index=leader_votes.index)
            )
            frame = pd.DataFrame({"total": precinct_totals}).join(
                [
                    precinct_candidate_votes,
                    leader_votes.rename("lead"),
                    other_votes.rename("other"),
                ]
            )
            frame[["lead", "other"]] = frame[["lead", "other"]].fillna(0)
            share_lead = frame["lead"] / frame["candidate_votes"]
            share_other = frame["other"] / frame["candidate_votes"]
            frame["dem_margin"] = -((share_lead - share_other) * 100)
            frame["no_dem_candidate"] = True
            # With no Democrat on the ballot the margin negates the leader's
            # margin over the strongest remaining candidate, so that candidate
            # occupies the Democratic side of the comparison. Recording it in
            # `dem_votes` keeps the margin recoverable by the same arithmetic
            # for every row in the table.
            frame["dem_candidate"] = runner_up["candidate"] if runner_up else pd.NA
            frame["opponent_candidate"] = leader["candidate"]
            frame["opponent_party"] = leader["party"]
            frame["dem_votes"] = frame["other"]
            frame["opponent_votes"] = frame["lead"]
        else:
            dem_votes = _precinct_votes(race, dem["candidate"])
            opp_votes = _precinct_votes(race, opponent["candidate"])
            frame = pd.DataFrame({"total": precinct_totals}).join(
                [
                    precinct_candidate_votes,
                    dem_votes.rename("dem"),
                    opp_votes.rename("opp"),
                ]
            )
            frame[["dem", "opp"]] = frame[["dem", "opp"]].fillna(0)
            share_dem = frame["dem"] / frame["candidate_votes"]
            share_opp = frame["opp"] / frame["candidate_votes"]
            frame["dem_margin"] = (share_dem - share_opp) * 100
            frame["no_dem_candidate"] = False
            frame["dem_candidate"] = dem["candidate"]
            frame["opponent_candidate"] = opponent["candidate"]
            frame["opponent_party"] = opponent["party"]
            frame["dem_votes"] = frame["dem"]
            frame["opponent_votes"] = frame["opp"]

        frame = frame.reset_index()
        frame["total_votes"] = frame["total"]
        frame["election_id"] = election_id
        frame["election_date"] = meta["election_date"]
        frame["election_year"] = int(meta["election_year"])
        frame["redistricting_cycle"] = config.cycle_for_year(int(meta["election_year"]))
        frame["office"] = meta["office"]
        frame["district"] = meta["district"]
        frame["district_display"] = meta["district_display"]
        frame["incumbent_status"] = incumbent_status(meta["party_incumbent"])
        frame["pres_elec"] = meta["election_date"] in PRESIDENTIAL_ELECTION_DATES
        frame["is_special"] = bool(meta["is_special"])
        frame["num_candidates"] = num_candidates
        # Counted from the precinct returns, which list every candidate. The
        # published summary carries only four candidate slots, so these can
        # exceed what a district-level row can represent.
        frame["candidate_count"] = len(totals)
        frame["dem_candidate_count"] = int((totals["party"] == DEMOCRATIC).sum())
        frames.append(frame)

    if not frames:
        return pd.DataFrame(columns=TRAINING_COLUMNS), pd.DataFrame(excluded)

    rows = pd.concat(frames, ignore_index=True)
    return rows, pd.DataFrame(
        excluded,
        columns=["election_id", "election_date", "office", "district_display", "reason"],
    )


def attach_split_flag(rows: pd.DataFrame) -> pd.DataFrame:
    """Flag rows whose precinct is divided between two districts.

    Where a precinct straddles a district line, each district's returns report
    its own portion under the same precinct label. The margin is then computed
    over part of the precinct while `PVI_N` covers all of it, so the two do not
    describe the same voters. Such rows are usable but not on the same footing
    as the rest, and this serves the same purpose as `pvi_provenance`: telling
    the modeller which rows carry a known compromise.
    """
    from . import districts

    conflicts = pd.read_csv(config.REPORT_DIR / districts.CONFLICT_REPORT)
    if conflicts.empty:
        rows["precinct_split_across_districts"] = False
        return rows

    split = set(
        zip(
            conflicts["redistricting_cycle"],
            conflicts["office"],
            conflicts["city_town"],
            conflicts["ward"].astype(str),
            conflicts["precinct"].astype(str),
        )
    )
    rows["precinct_split_across_districts"] = [
        (cycle, office, city_town, str(ward), str(precinct)) in split
        for cycle, office, city_town, ward, precinct in zip(
            rows["redistricting_cycle"],
            rows["office"],
            rows["city_town"],
            rows["ward"],
            rows["precinct"],
        )
    ]
    return rows


def attach_pvi(rows: pd.DataFrame) -> pd.DataFrame:
    """Join PVI on presidential pair and redistricting cycle."""
    mapping = config.race_year_pvi()[
        ["race_year", "pvi_year", "redistricting_cycle"]
    ].rename(columns={"race_year": "election_year"})
    rows = rows.merge(mapping, on=["election_year", "redistricting_cycle"], how="left")

    pvi_table = pd.read_csv(config.PVI_DIR / "ma_precinct_pvi.csv.gz")[
        ["pvi_year", "redistricting_cycle", *KEY, "PVI_N", "provenance"]
    ].rename(columns={"provenance": "pvi_provenance"})

    return rows.merge(
        pvi_table, on=["pvi_year", "redistricting_cycle", *KEY], how="left"
    )


def build_and_write() -> pd.DataFrame:
    results = pd.read_csv(build.LEGISLATIVE_RESULTS)
    rows, excluded = build_rows(results)
    rows = attach_split_flag(rows)
    rows = attach_pvi(rows)
    rows = rows[TRAINING_COLUMNS].sort_values(
        ["election_date", "office", "district_display", *KEY], ignore_index=True
    )

    build.write_csv(rows, TRAINING_FILE)

    excluded_path = config.REPORT_DIR / EXCLUDED_REPORT
    excluded.to_csv(excluded_path, index=False)
    print(f"excluded races: {len(excluded)} -> {excluded_path.relative_to(config.ROOT)}")

    split_count = int(rows["precinct_split_across_districts"].sum())
    print(
        f"rows in precincts split across districts: {split_count} of {len(rows)} "
        f"({100 * split_count / max(len(rows), 1):.2f}%)"
    )

    missing = rows[rows["PVI_N"].isna()]
    missing_path = config.REPORT_DIR / MISSING_PVI_REPORT
    missing.to_csv(missing_path, index=False)
    print(
        f"rows with missing PVI_N: {len(missing)} of {len(rows)} "
        f"({100 * len(missing) / max(len(rows), 1):.2f}%) "
        f"-> {missing_path.relative_to(config.ROOT)}"
    )
    return rows
