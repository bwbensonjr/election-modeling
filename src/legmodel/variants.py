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
        # OCPF's own feeds carry the result. `isWinner` is on both the
        # historical `finsummaries` rows and the current depository rows, and a
        # predictor built from it would be the answer to the question being
        # asked (campaign-finance spec, "An outcome field is never read as a
        # predictor").
        "is_winner",
        "isWinner",
        "dem_is_winner",
        "won",
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


# The scale of the half-normal prior on a group effect's standard deviation,
# in margin points. The quantity is the residual year-to-year swing left after
# PVI, incumbency and the national environment are accounted for, not the
# spread of the response itself: HalfNormal(5) puts about 95% of its mass
# below 10 points and its median near 3.4, which spans every swing in the
# record without licensing a hundred. Bambi's auto-scaled default here is
# derived from the intercept's scale and lands on HalfNormal(135), five times
# the response's own standard deviation (design.md, D2).
GROUP_SD_PRIOR_SCALE = 5.0


@dataclass(frozen=True)
class Prior:
    """A prior declaration, independent of the fitting library.

    Declared here rather than as a `bambi.Prior` so that the registry stays
    free of the modelling backend, and so that a declaration has one stable
    rendering to publish alongside the fit that used it (margin-model spec,
    "A variant declares the priors its fit uses"). `fit.py` translates it.
    """

    distribution: str
    # Pairs rather than a mapping, so the rendering is ordered and the
    # declaration stays hashable. A value is a number or a nested Prior, which
    # is how a hyperprior on a group-level standard deviation is spelled.
    params: tuple[tuple[str, "float | Prior"], ...] = ()

    def __str__(self) -> str:
        rendered = ", ".join(f"{name}={_render(value)}" for name, value in self.params)
        return f"{self.distribution}({rendered})"


def _render(value) -> str:
    if isinstance(value, Prior):
        return str(value)
    number = float(value)
    return str(int(number)) if number.is_integer() else str(number)


def group_intercept_prior(sigma: float = GROUP_SD_PRIOR_SCALE) -> Prior:
    """A group intercept whose standard deviation carries a declared scale."""
    return Prior(
        "Normal",
        (("mu", 0.0), ("sigma", Prior("HalfNormal", (("sigma", float(sigma)),)))),
    )


def group_term(group: str) -> str:
    """The term name a group effect's prior is declared under."""
    return f"1|{group}"


class UnknownPredictorError(ValueError):
    """A variant names a column the race table does not carry."""


# Predictors that cannot be derived before the fold year begins. Each names the
# column carrying the as-of date it was measured to, which must be published
# with every fit that uses it: a dated predictor's value is meaningless without
# its date, and the choice of date is the difference between a forecast and a
# postdiction (margin-model spec, "A predictor must be knowable before its fold
# year's election").
DATED_PREDICTORS = {}


def register_dated(predictor: str, as_of_column: str) -> None:
    """Declare that a predictor is knowable only during its fold year."""
    DATED_PREDICTORS[predictor] = as_of_column


class MissingAsOfDateError(ValueError):
    """A predictor knowable only during the fold year declared no as-of date."""


class AsOfDateAfterElectionError(ValueError):
    """A dated predictor's as-of date falls on or after the election it predicts."""


class MissingGroupPriorError(ValueError):
    """A group effect was declared without a prior for its standard deviation.

    Bambi would otherwise supply an auto-scaled default derived from the
    intercept's scale, which is the prior that left every `baseline_year` fold
    diverging. A group effect's scale has to be stated (margin-model spec, "A
    group effect without a declared scale is rejected").
    """


class UnknownVariantError(KeyError):
    """A variant name is not registered."""


class GroupedPredictorError(ValueError):
    """A predictor is spanned by the variant's own grouping factor.

    A predictor constant within every level of a group effect is a linear
    combination of that group's indicators, so the two are not separately
    identified and the sampler explores a ridge instead of estimating two
    effects (margin-model spec, "A predictor constant within a grouping level
    is rejected").
    """


# Below this many training races carrying within-group variation, a predictor
# is fit but its identifying count is published, because a coefficient resting
# on a handful of races out of hundreds should not read like one resting on all
# of them (design.md, D5). Nothing branches on the value; it is a reporting
# threshold.
SEPARATING_RACES_DISCLOSED = 30


def separating_races(frame: "pd.DataFrame", predictor: str, group: str) -> int:
    """How many races stand between `predictor` and exact confounding.

    Within each level of the group, the races that do not carry that level's
    most common value of the predictor: the smallest set whose removal would
    leave the predictor constant within every level. Those races are the entire
    basis on which the predictor's fixed effect is distinguished from the group
    effect, so this, rather than the size of the levels that happen to vary, is
    what the coefficient rests on. Zero means the two are already exactly
    confounded.
    """
    counts = frame.groupby(group)[predictor].agg(
        lambda values: len(values) - values.value_counts().max()
    )
    return int(counts.sum())


def check_grouping(variant: "Variant", prepared: "pd.DataFrame") -> dict:
    """Refuse a predictor the variant's grouping factor already contains.

    Checked against the fold's own training races rather than the full table:
    `pres_elec` varies within a year somewhere in the record, but not within
    any year an early fold trains on, and it is the early folds that fail.
    """
    counts = {}
    for group in variant.group_effects:
        if group not in prepared.columns:
            continue
        for predictor in variant.predictors:
            for column in expand(predictor):
                if column not in prepared.columns:
                    continue
                count = separating_races(prepared, column, group)
                if count == 0:
                    raise GroupedPredictorError(
                        f"variant {variant.name!r}: predictor {column!r} is "
                        f"constant within every level of {group!r} across the "
                        f"{len(prepared)} training races, so it is a linear "
                        f"combination of the {group!r} effects and the two "
                        "cannot be separately identified"
                    )
                if count < SEPARATING_RACES_DISCLOSED:
                    counts[f"{column}|{group}"] = count
    return counts


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
    # Prior declarations by term name, e.g. {"1|election_year": Prior(...)}.
    # A term absent here keeps the fitting library's own default, which is what
    # keeps a variant declaring none byte-identical to its published result.
    priors: dict = field(default_factory=dict)
    # Sampler settings. None means the module default in `fit.py`; the value
    # actually used is recorded with the fit either way, so a fit that needed a
    # raised target acceptance is distinguishable from one that did not
    # (margin-model spec, "A variant declares the sampler settings its fit
    # uses").
    target_accept: float | None = None
    tune: int | None = None
    # The as-of date every dated predictor this variant carries was measured
    # to. Required when a predictor is not knowable before the fold year, and
    # published with every fit either way.
    as_of: str = ""

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

    @property
    def prior_declaration(self) -> str:
        """The declared priors as one stable string, for publication.

        Empty when the variant declares none, which reads in the published
        diagnostics as "the fitting library's defaults" (margin-model spec, "A
        declared prior is recorded with the fit").
        """
        return "; ".join(
            f"{term} ~ {self.priors[term]}" for term in sorted(self.priors)
        )

    def validate(self, columns) -> None:
        """Fail loudly on a predictor the table does not carry."""
        for predictor in self.predictors:
            check_knowable(predictor)
        dated = [p for p in self.predictors if p in DATED_PREDICTORS]
        if dated and not self.as_of:
            raise MissingAsOfDateError(
                f"variant {self.name!r} declares {sorted(dated)}, which cannot "
                "be derived before the fold year begins, but sets no as_of "
                "date; a dated predictor's value is meaningless without the "
                "date it was measured to"
            )
        for group in self.group_effects:
            if group_term(group) not in self.priors:
                raise MissingGroupPriorError(
                    f"variant {self.name!r} declares the group effect "
                    f"{group_term(group)!r} with no prior for its group-level "
                    "standard deviation; declare one with "
                    f"group_intercept_prior(), because the auto-scaled default "
                    "is derived from the intercept's scale rather than from "
                    "the spread of the effect being estimated"
                )
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
# `pres_elec` is a property of the calendar year, so a per-year intercept
# already contains it: across the adopted definition's 610 races it varies
# within a year only in 2016 and 2020, on 8 races, and within an early fold's
# training window not at all. Carrying both asks the sampler to split one
# column between two parameters, which is the ridge the original fits diverged
# along. The year variant therefore drops it, which also stops it being nested
# in `baseline` -- a fact its comparison has to state (design.md, D3).
register(
    Variant(
        name="baseline_year",
        predictors=("PVI_N", "incumbent_status"),
        group_effects=("election_year",),
        priors={group_term("election_year"): group_intercept_prior()},
        target_accept=0.95,
        description=(
            "the baseline plus a hierarchical year intercept, minus the "
            "pres_elec term the year effect contains"
        ),
    )
)
# The contrast arm: the same variant keeping `pres_elec`, under the same prior
# and the same sampler setting, so that dropping the term is evidence rather
# than assertion. It is refused outright on the folds where the confounding is
# exact, which is itself the evidence (design.md, D3).
register(
    Variant(
        name="baseline_year_pres",
        predictors=BASELINE_PREDICTORS,
        group_effects=("election_year",),
        priors={group_term("election_year"): group_intercept_prior()},
        target_accept=0.95,
        description=(
            "the year-intercept variant retaining pres_elec, as the contrast "
            "arm for dropping it"
        ),
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


def check_as_of(variant: "Variant", election_dates) -> None:
    """Refuse a dated predictor measured on or after the election it predicts.

    The whole point of measuring money to a stated date is that the date falls
    before the votes are cast. A date on or after election day would be reading
    the result, so it is refused rather than fit (margin-model spec, "The as-of
    date is before the election it predicts").
    """
    import pandas as pd

    if not variant.as_of:
        return
    as_of = pd.Timestamp(variant.as_of)
    dates = pd.to_datetime(pd.Series(list(election_dates)).dropna())
    if dates.empty:
        return
    earliest = dates.min()
    if as_of >= earliest:
        raise AsOfDateAfterElectionError(
            f"variant {variant.name!r} declares as_of {variant.as_of}, which is "
            f"on or after the election on {earliest.date()}; a predictor "
            "measured then would be reading the result"
        )
