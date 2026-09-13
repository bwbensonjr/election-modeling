"""Data definitions: who counts as a candidate, and what the margin measures.

A definition is a named configuration -- an eligibility rule, a response
column, a write-in threshold, and a treatment for races with no Democratic
candidate -- selected over the published race table rather than baked into it.
Testing an alternative is a filter and a column choice, not a rebuild
(design.md, D1).

Eligibility is declared from a fixed vocabulary of criteria rather than as an
arbitrary predicate. That is what makes the outcome-blindness requirement
enforceable: each criterion names the columns it reads, and a criterion
reading a response column is refused at registration rather than at review.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import config

DEMOCRATIC = "Democratic"
REPUBLICAN = "Republican"

# The threshold the published tables were built at: every named candidate,
# write-in or not, is admitted. Recomputing at this threshold must reproduce
# the published response columns, which is the check that the recomputation
# and the pipeline have not drifted apart.
BUILD_THRESHOLD = 0.0

# Eligibility may look at who stood and how strong a write-in was. It may not
# look at what happened. Anything outside this set is refused.
ALLOWED_ELIGIBILITY_COLUMNS = frozenset(
    {
        "major_party_race",
        "no_dem_candidate",
        "contested_on_ballot_lines",
        "admitted_by_write_in",
        "num_candidates_admitted",
        "num_candidates",
        "dem_candidate_count",
        "opponent_party",
        "write_in_share",
        "top_write_in_share",
    }
)

NO_DEM_KEEP = "keep"
NO_DEM_EXCLUDE = "exclude"
NO_DEM_TRAIN_ONLY = "train_only"
NO_DEM_TREATMENTS = (NO_DEM_KEEP, NO_DEM_EXCLUDE, NO_DEM_TRAIN_ONLY)

# Responses a definition may name. `two_party_or_strongest` is derived rather
# than published: the two-party margin where both major parties stood, and the
# all-candidate margin against the strongest non-Democrat where no Republican
# did (design.md, D7).
RESPONSE_TWO_PARTY_OR_STRONGEST = "dem_margin_two_party_or_strongest"
RESPONSES = ("dem_margin", "dem_margin_two_party", RESPONSE_TWO_PARTY_OR_STRONGEST)


class UnknownDefinitionError(KeyError):
    """A definition name is not registered."""


class InvalidDefinitionError(ValueError):
    """A definition is declared in a way the rules do not allow."""


@dataclass(frozen=True)
class Criterion:
    """One eligibility test, with the columns it is allowed to read."""

    name: str
    columns: tuple[str, ...]
    test: object
    description: str

    def validate(self) -> None:
        forbidden = set(self.columns) - ALLOWED_ELIGIBILITY_COLUMNS
        if forbidden:
            raise InvalidDefinitionError(
                f"eligibility criterion {self.name!r} reads {sorted(forbidden)}, "
                "which is not a candidate-presence, party, or write-in column. "
                "Eligibility must not depend on the outcome of the race; "
                f"allowed columns are {sorted(ALLOWED_ELIGIBILITY_COLUMNS)}"
            )


CRITERIA: dict[str, Criterion] = {}


def register_criterion(criterion: Criterion) -> Criterion:
    criterion.validate()
    CRITERIA[criterion.name] = criterion
    return criterion


register_criterion(
    Criterion(
        name="contested_on_ballot_lines",
        columns=("contested_on_ballot_lines",),
        test=lambda races: races["contested_on_ballot_lines"].astype(bool),
        description="two or more ballot lines, ignoring write-ins",
    )
)
register_criterion(
    Criterion(
        name="major_party",
        columns=("major_party_race",),
        test=lambda races: races["major_party_race"].astype(bool),
        description="both a Democrat and a Republican stood",
    )
)
register_criterion(
    Criterion(
        name="has_democrat",
        columns=("no_dem_candidate",),
        test=lambda races: ~races["no_dem_candidate"].astype(bool),
        description="a Democrat stood",
    )
)


@dataclass(frozen=True)
class Definition:
    """A named answer to who counts and what the margin measures."""

    name: str
    response: str
    write_in_threshold: float
    no_dem: str
    criteria: tuple[str, ...] = ()
    description: str = ""
    adopted: bool = field(default=False)

    def validate(self) -> None:
        if self.response not in RESPONSES:
            raise InvalidDefinitionError(
                f"definition {self.name!r} names response {self.response!r}; "
                f"known responses are {list(RESPONSES)}"
            )
        if self.no_dem not in NO_DEM_TREATMENTS:
            raise InvalidDefinitionError(
                f"definition {self.name!r} declares no-Democrat treatment "
                f"{self.no_dem!r}; allowed treatments are {list(NO_DEM_TREATMENTS)}"
            )
        if not 0.0 <= self.write_in_threshold <= 1.0:
            raise InvalidDefinitionError(
                f"definition {self.name!r} has write-in threshold "
                f"{self.write_in_threshold}; it is a share and must lie in [0, 1]"
            )
        for name in self.criteria:
            if name not in CRITERIA:
                raise InvalidDefinitionError(
                    f"definition {self.name!r} names eligibility criterion "
                    f"{name!r}, which is not registered; registered criteria are "
                    f"{sorted(CRITERIA)}"
                )
            CRITERIA[name].validate()

    def required_columns(self) -> set[str]:
        columns = {"election_id", "election_year", "no_dem_candidate"}
        for name in self.criteria:
            columns.update(CRITERIA[name].columns)
        if self.response != RESPONSE_TWO_PARTY_OR_STRONGEST:
            columns.add(self.response)
        else:
            columns.update(
                {
                    "dem_margin_two_party",
                    "major_party_race",
                    "dem_votes",
                    "opponent_votes",
                }
            )
        return columns

    def as_row(self) -> dict:
        return {
            "definition": self.name,
            "response": self.response,
            "write_in_threshold": self.write_in_threshold,
            "no_dem": self.no_dem,
            "criteria": ",".join(self.criteria) or "none",
            "description": self.description,
        }


REGISTRY: dict[str, Definition] = {}


def register(definition: Definition) -> Definition:
    definition.validate()
    REGISTRY[definition.name] = definition
    return definition


register(
    Definition(
        name="current",
        response="dem_margin",
        # Every named candidate counts toward the denominator, which is what
        # the pre-change pipeline did; eligibility is then further restricted
        # to races with two ballot lines. That asymmetry is the rule the README
        # documents, reproduced here so its scorecard stays recomputable.
        write_in_threshold=BUILD_THRESHOLD,
        no_dem=NO_DEM_KEEP,
        criteria=("contested_on_ballot_lines",),
        description="the rule in force before this change",
    )
)
register(
    Definition(
        name="two_party",
        response="dem_margin_two_party",
        write_in_threshold=BUILD_THRESHOLD,
        no_dem=NO_DEM_EXCLUDE,
        criteria=("contested_on_ballot_lines", "major_party"),
        description="Democrat versus Republican only, two-party response",
    )
)
register(
    Definition(
        name="two_party_or_strongest",
        response=RESPONSE_TWO_PARTY_OR_STRONGEST,
        write_in_threshold=BUILD_THRESHOLD,
        no_dem=NO_DEM_EXCLUDE,
        criteria=("contested_on_ballot_lines", "has_democrat"),
        description=(
            "two-party where a Republican ran, strongest non-Democrat where none did"
        ),
        # Adopted. The definition comparisons came back undecided on shared
        # races (+0.111 [-0.236, +0.589] against `current`), so the choice rests
        # on the principle fixed before the numbers were seen: the response and
        # the predictor should share a denominator. This measures every admitted
        # race on a two-candidate denominator while keeping 610 races and all 24
        # holdout specials, where the strict two-party rule would drop 93 more
        # races and two specials for no measured gain. Excluding no-Democrat
        # races, which it does by construction, was separately decided a small
        # improvement. See docs/definition_result.md.
        adopted=True,
    )
)
# Question 3 in isolation: the same rule as `current` but for how races with no
# Democratic candidate are handled, so the three treatments are compared
# against one another with nothing else varying.
register(
    Definition(
        name="no_dem_excluded",
        response="dem_margin",
        write_in_threshold=BUILD_THRESHOLD,
        no_dem=NO_DEM_EXCLUDE,
        criteria=("contested_on_ballot_lines",),
        description="current, with no-Democrat races dropped from training and scoring",
    )
)
register(
    Definition(
        name="no_dem_train_only",
        response="dem_margin",
        write_in_threshold=BUILD_THRESHOLD,
        no_dem=NO_DEM_TRAIN_ONLY,
        criteria=("contested_on_ballot_lines",),
        description="current, with no-Democrat races trained on but not scored",
    )
)
register(
    Definition(
        name="write_in_5pct",
        response="dem_margin",
        write_in_threshold=0.05,
        no_dem=NO_DEM_KEEP,
        criteria=(),
        description="a write-in at or above 5% counts as a candidate",
    )
)


def get(name: str) -> Definition:
    try:
        return REGISTRY[name]
    except KeyError:
        raise UnknownDefinitionError(
            f"unknown definition {name!r}; registered definitions are "
            f"{sorted(REGISTRY)}"
        ) from None


def all_definitions() -> dict[str, Definition]:
    return dict(REGISTRY)


def adopted() -> Definition:
    """The published default, used when a run names no definition."""
    chosen = [d for d in REGISTRY.values() if d.adopted]
    if len(chosen) != 1:
        raise InvalidDefinitionError(
            f"exactly one definition must be adopted; {len(chosen)} are marked"
        )
    return chosen[0]


def resolve(names=None) -> list[Definition]:
    if names is None:
        return list(REGISTRY.values())
    return [get(name) for name in names]


# --- Applying a definition ---------------------------------------------------


def _selection_at(roster: pd.DataFrame, threshold: float) -> pd.DataFrame:
    """Recompute each race's contest at a write-in threshold.

    Mirrors the pipeline's contest selection, at race grain and over the
    admitted candidates only: the strongest Democrat against the strongest
    non-Democrat, or where no Democrat stood, the negated margin of the
    Republican over the strongest remaining candidate. The denominator is the
    admitted candidates' votes, so one threshold governs eligibility and the
    margin together (design.md, D3).
    """
    admitted = roster[(~roster["is_write_in"]) | (roster["share"] >= threshold)]
    rows = []
    for election_id, group in admitted.groupby("election_id", sort=False):
        group = group.sort_values("votes", ascending=False)
        candidate_votes = float(group["votes"].sum())
        democrats = group[group["party"] == DEMOCRATIC]
        others = group[group["party"] != DEMOCRATIC]
        republicans = group[group["party"] == REPUBLICAN]

        gop_votes = float(republicans.iloc[0]["votes"]) if len(republicans) else 0.0
        dem_party_votes = float(democrats.iloc[0]["votes"]) if len(democrats) else 0.0
        major_party = bool(len(democrats) and len(republicans))

        if len(democrats):
            no_dem = False
            dem_votes = dem_party_votes
            opponent_votes = float(others.iloc[0]["votes"]) if len(others) else np.nan
        else:
            no_dem = True
            if not len(republicans):
                dem_votes = opponent_votes = np.nan
            else:
                leader = republicans.iloc[0]
                rest = others[others["candidate"] != leader["candidate"]]
                # The leader takes the opponent side and the runner-up the
                # Democratic side, so the published margin is the negation of
                # the Republican's margin over the field.
                dem_votes = float(rest.iloc[0]["votes"]) if len(rest) else 0.0
                opponent_votes = float(leader["votes"])

        margin = (
            (dem_votes - opponent_votes) / candidate_votes * 100.0
            if candidate_votes > 0 and not pd.isna(opponent_votes)
            else np.nan
        )
        two_party = dem_party_votes + gop_votes
        rows.append(
            {
                "election_id": election_id,
                "n_admitted": len(group),
                "no_dem_candidate": no_dem,
                "major_party_race": major_party,
                "dem_margin": margin,
                "dem_margin_two_party": (
                    (dem_party_votes - gop_votes) / two_party * 100.0
                    if major_party and two_party > 0
                    else np.nan
                ),
            }
        )
    return pd.DataFrame(rows)


def _response_values(frame: pd.DataFrame, definition: Definition) -> pd.Series:
    if definition.response == RESPONSE_TWO_PARTY_OR_STRONGEST:
        # Where no Republican ran, the comparison is the Democrat against the
        # strongest non-Democrat on that pair's own two-candidate denominator
        # (design.md, D7) -- not `dem_margin`, which divides by every named
        # candidate and so reintroduces the denominator mismatch this response
        # exists to remove.
        pair_votes = frame["dem_votes"] + frame["opponent_votes"]
        two_candidate = (
            (frame["dem_votes"] - frame["opponent_votes"]) / pair_votes * 100.0
        ).where(pair_votes > 0)
        return frame["dem_margin_two_party"].where(
            frame["major_party_race"].astype(bool), two_candidate
        )
    return frame[definition.response]


def apply(
    definition: Definition,
    races: pd.DataFrame | None = None,
    roster: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Select the races a definition admits and set its response.

    Returns the admitted races, carrying a `response` column and a `scoreable`
    flag, and a report naming every race dropped and why. `scoreable` is what
    the train-only no-Democrat treatment acts on: such races stay in the frame,
    and so in every fold's training set, but are withheld from the holdout.
    """
    races = config.load_races() if races is None else races.copy()
    roster = config.load_roster() if roster is None else roster

    missing = sorted(definition.required_columns() - set(races.columns))
    if missing:
        raise InvalidDefinitionError(
            f"definition {definition.name!r} needs {missing}, which the race "
            f"table does not carry; available columns are {sorted(races.columns)}"
        )

    frame = races.copy()
    if definition.write_in_threshold != BUILD_THRESHOLD:
        # A stricter threshold changes the admitted set, the denominator and
        # therefore the response, so these are recomputed from the roster
        # rather than read from columns built at a different threshold.
        recomputed = _selection_at(roster, definition.write_in_threshold)
        frame = frame.drop(
            columns=[
                "dem_margin",
                "dem_margin_two_party",
                "no_dem_candidate",
                "major_party_race",
            ]
        ).merge(recomputed, on="election_id", how="inner")
        frame["num_candidates_admitted"] = frame["n_admitted"]
        frame["admitted_by_write_in"] = ~frame["contested_on_ballot_lines"].astype(bool)

    dropped = []

    def drop(mask, reason):
        for row in frame[mask].itertuples():
            dropped.append(
                {
                    "definition": definition.name,
                    "election_id": row.election_id,
                    "election_year": row.election_year,
                    "office": row.office,
                    "district_display": row.district_display,
                    "reason": reason,
                }
            )

    if definition.write_in_threshold != BUILD_THRESHOLD:
        uncontested = frame["n_admitted"] < 2
        drop(uncontested, f"fewer than two candidates at a "
             f"{definition.write_in_threshold:.0%} write-in threshold")
        frame = frame[~uncontested]

    for name in definition.criteria:
        criterion = CRITERIA[name]
        failing = ~criterion.test(frame)
        drop(failing, f"fails eligibility criterion {name!r}: {criterion.description}")
        frame = frame[~failing]

    if definition.no_dem == NO_DEM_EXCLUDE:
        no_dem = frame["no_dem_candidate"].astype(bool)
        drop(no_dem, "no Democratic candidate, excluded by this definition")
        frame = frame[~no_dem]

    frame = frame.copy()
    frame["response"] = _response_values(frame, definition)
    undefined = frame["response"].isna()
    drop(undefined, f"response {definition.response!r} is undefined for this race")
    frame = frame[~undefined].copy()

    # Train-only keeps the race in every fold's training set and withholds it
    # from the holdout, which tests whether such races inform the fit without
    # letting their prediction failures dominate the score.
    frame["scoreable"] = True
    if definition.no_dem == NO_DEM_TRAIN_ONLY:
        frame["scoreable"] = ~frame["no_dem_candidate"].astype(bool)

    frame["definition"] = definition.name
    return frame.reset_index(drop=True), pd.DataFrame(
        dropped,
        columns=[
            "definition",
            "election_id",
            "election_year",
            "office",
            "district_display",
            "reason",
        ],
    )
