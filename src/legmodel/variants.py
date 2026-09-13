"""Model variants, declared as a name plus a predictor list.

Adding a variant is a registry entry. Nothing in fitting or scoring knows the
names of individual predictors, so a new variable is tested by declaring it
here and rerunning (margin-model spec, "Variants are declared, not hard-coded").
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from . import config

# The canonical response column. A definition copies whichever response it
# names into this column, so fitting and scoring never need to know which
# response is in play (definitions.py).
RESPONSE = "response"

# Fixed in advance rather than inferred from the training data, so an early
# fold that happens to contain no Republican incumbents still produces a design
# matrix compatible with the holdout (design.md, D11). The first level is the
# reference: incumbency coefficients read against an open seat.
CATEGORICAL_LEVELS = {
    "incumbent_status": ["No_Incumbent", "Dem_Incumbent", "GOP_Incumbent"],
}

# Categoricals are expanded into explicit indicator columns rather than left
# to the formula's own contrast coding. Two things make this necessary:
# formulae orders a categorical's levels alphabetically, which would make
# Dem_Incumbent the reference instead of an open seat; and its C() derives the
# level set from the values actually present, so a fold whose training races
# happen to contain no Republican incumbent builds a design matrix that then
# rejects a holdout race carrying one. Naming the indicators here fixes both:
# the reference is whichever level has no indicator, and every fold gets the
# same columns whatever it happens to contain (design.md, D11).
CATEGORICAL_INDICATORS = {
    "incumbent_status": {
        "reference": "No_Incumbent",
        "levels": {
            "Dem_Incumbent": "incumbent_dem",
            "GOP_Incumbent": "incumbent_gop",
        },
    },
}


def expand(predictor: str) -> list:
    """The design-matrix columns a declared predictor contributes."""
    spec = CATEGORICAL_INDICATORS.get(predictor)
    if spec is None:
        return [predictor]
    return list(spec["levels"].values())

# Booleans enter as 0/1 slopes rather than as factors, matching how R treats a
# logical predictor in the model being replicated.
BOOLEAN_PREDICTORS = ("pres_elec", "is_special", "no_dem_candidate")

# The party holding the presidency during each legislative election year. A
# midterm or off-year electorate moves against the president's party, and
# unlike a year effect this is settled before the votes are cast, so a term
# built from it can shift a holdout year's mean and can be carried forward to
# 2026 (design.md, D10).
PRESIDENT_PARTY = {
    2010: "D", 2011: "D", 2012: "D", 2013: "D", 2014: "D", 2015: "D", 2016: "D",
    2017: "R", 2018: "R", 2019: "R", 2020: "R",
    2021: "D", 2022: "D", 2023: "D", 2024: "D",
    2025: "R", 2026: "R",
}

# Derived predictors: computed from columns the table carries rather than read
# from it. Each declares the columns it is built from, which is what the
# knowability check inspects.
DERIVED = {
    "national_env": {
        "from": ("election_year", "pres_elec"),
        "description": (
            "-1 in a non-presidential year under a Democratic president, +1 "
            "under a Republican one, 0 in a presidential year"
        ),
    },
    "pres_elec_x_incumbent_dem": {
        "from": ("pres_elec", "incumbent_status"),
        "description": "presidential-year timing interacted with Democratic incumbency",
    },
    "pres_elec_x_incumbent_gop": {
        "from": ("pres_elec", "incumbent_status"),
        "description": "presidential-year timing interacted with Republican incumbency",
    },
}

# A predictor computed from the fold year's own results would leak the outcome
# into the fit. None of the derived predictors may be built from these.
OUTCOME_COLUMNS = frozenset(
    {
        "response",
        "dem_margin",
        "dem_margin_two_party",
        "response_shift",
        "dem_votes",
        "opponent_votes",
        "gop_votes",
        "candidate_votes",
        "write_in_votes",
        "top_write_in_votes",
        "total_votes",
    }
)


class LeakingPredictorError(ValueError):
    """A predictor is computed from the results of the year it predicts."""


def check_knowable(predictor: str) -> None:
    """Refuse a predictor built from the fold year's own outcome.

    Every predictor must be derivable before its fold year begins. A predictor
    built from vote counts is knowable only once the election has happened, so
    a fit using it would be reading the answer (margin-model spec, "A predictor
    must be knowable before its fold year").
    """
    spec = DERIVED.get(predictor)
    if spec is None:
        if predictor in OUTCOME_COLUMNS:
            raise LeakingPredictorError(
                f"predictor {predictor!r} is an outcome of the race being "
                "predicted, so it is not knowable before the fold year"
            )
        return
    leaking = sorted(set(spec["from"]) & OUTCOME_COLUMNS)
    if leaking:
        raise LeakingPredictorError(
            f"derived predictor {predictor!r} is computed from {leaking}, which "
            "is only known once the fold year's elections have happened"
        )


def derive(races: "pd.DataFrame") -> "pd.DataFrame":
    """Add the derived predictor columns."""
    frame = races
    if "election_year" in frame.columns:
        party = frame["election_year"].map(PRESIDENT_PARTY)
        if party.isna().any():
            missing = sorted(
                frame.loc[party.isna(), "election_year"].unique().tolist()
            )
            raise ValueError(
                f"no recorded presidential party for election years {missing}; "
                "extend PRESIDENT_PARTY before scoring them"
            )
        midterm = ~frame["pres_elec"].astype(bool)
        frame["national_env"] = midterm.astype(int) * party.map({"D": -1, "R": 1})
    if "incumbent_status" in frame.columns:
        pres = frame["pres_elec"].astype(int)
        frame["pres_elec_x_incumbent_dem"] = pres * (
            frame["incumbent_status"] == "Dem_Incumbent"
        ).astype(int)
        frame["pres_elec_x_incumbent_gop"] = pres * (
            frame["incumbent_status"] == "GOP_Incumbent"
        ).astype(int)
    return frame


def prepare(races: "pd.DataFrame") -> "pd.DataFrame":
    """Coerce predictor columns to the encoding every fit must share.

    The level set is imposed here rather than inferred per fold, so a fold
    whose training races happen to omit a level still produces a design matrix
    that accepts a holdout race carrying it.
    """
    prepared = races.copy()
    for column, levels in CATEGORICAL_LEVELS.items():
        if column not in prepared.columns:
            continue
        unexpected = set(prepared[column].dropna().unique()) - set(levels)
        if unexpected:
            raise ValueError(
                f"{column} carries unexpected levels {sorted(unexpected)}; "
                f"expected {levels}"
            )
        spec = CATEGORICAL_INDICATORS.get(column)
        if spec is not None:
            for level, indicator in spec["levels"].items():
                prepared[indicator] = (prepared[column] == level).astype(int)
    for column in BOOLEAN_PREDICTORS:
        if column in prepared.columns:
            prepared[column] = prepared[column].astype(int)
    return derive(prepared)


class UnknownPredictorError(ValueError):
    """A variant names a column the race table does not carry."""


class UnknownVariantError(KeyError):
    """A variant name is not registered."""


@dataclass(frozen=True)
class Variant:
    """A named model specification over the race table's columns."""

    name: str
    predictors: tuple[str, ...]
    description: str = ""
    response: str = field(default=RESPONSE)
    # Grouping columns entering as a hierarchical intercept. A holdout year
    # absent from training has no fitted effect, so its effect is drawn from
    # the group-level hyperprior at prediction time rather than fixed at a
    # value that does not exist (design.md, D9).
    group_effects: tuple[str, ...] = ()

    @property
    def formula(self) -> str:
        terms = [column for p in self.predictors for column in expand(p)]
        terms += [f"(1|{group})" for group in self.group_effects]
        return f"{self.response} ~ " + " + ".join(terms)

    @property
    def declared(self) -> str:
        """The variant as declared, before categorical expansion."""
        terms = list(self.predictors) + [
            f"(1|{group})" for group in self.group_effects
        ]
        return f"{self.response} ~ " + " + ".join(terms)

    def validate(self, columns) -> None:
        """Fail loudly on a predictor the table does not carry."""
        for predictor in self.predictors:
            check_knowable(predictor)
        available = set(columns) | set(DERIVED)
        missing = [p for p in self.predictors if p not in available]
        missing += [g for g in self.group_effects if g not in set(columns)]
        if missing:
            raise UnknownPredictorError(
                f"variant {self.name!r} names {missing} which the race table "
                f"does not carry; available columns are {sorted(available)}"
            )
        if self.response not in available:
            raise UnknownPredictorError(
                f"variant {self.name!r} has response {self.response!r} which the "
                "race table does not carry"
            )


BASELINE_PREDICTORS = ("PVI_N", "incumbent_status", "pres_elec")

REGISTRY: dict[str, Variant] = {}


def register(variant: Variant) -> Variant:
    REGISTRY[variant.name] = variant
    return variant


register(
    Variant(
        name="baseline",
        predictors=BASELINE_PREDICTORS,
        description="the established model in mapoli/model/ma_leg_model.R",
    )
)
register(
    Variant(
        name="baseline_special",
        predictors=BASELINE_PREDICTORS + ("is_special",),
        description="the baseline plus a special-election term",
    )
)
# Question 5: deferred from the baseline change, one registry entry.
register(
    Variant(
        name="baseline_num_candidates",
        predictors=BASELINE_PREDICTORS + ("num_candidates",),
        description="the baseline plus the candidate count",
    )
)
# Question 4: three attempts at the presidential-year bias the single
# pres_elec term leaves in place, running 6.4 points too Republican in
# non-presidential years and 2.7 too Democratic in presidential ones.
register(
    Variant(
        name="baseline_pres_incumbent",
        predictors=BASELINE_PREDICTORS
        + ("pres_elec_x_incumbent_dem", "pres_elec_x_incumbent_gop"),
        description="the baseline plus presidential-year by incumbency interaction",
    )
)
register(
    Variant(
        name="baseline_year",
        predictors=BASELINE_PREDICTORS,
        group_effects=("election_year",),
        description="the baseline plus a hierarchical year intercept",
    )
)
register(
    Variant(
        name="baseline_national_env",
        predictors=BASELINE_PREDICTORS + ("national_env",),
        description="the baseline plus a signed national-environment term",
    )
)


def get(name: str) -> Variant:
    try:
        return REGISTRY[name]
    except KeyError:
        raise UnknownVariantError(
            f"unknown variant {name!r}; registered variants are {sorted(REGISTRY)}"
        ) from None


def all_variants() -> dict[str, Variant]:
    return dict(REGISTRY)


def resolve(names=None) -> list[Variant]:
    if names is None:
        return list(REGISTRY.values())
    return [get(name) for name in names]
