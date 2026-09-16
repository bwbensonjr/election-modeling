"""Model variants, declared as a name plus a predictor list.

Adding a variant is a registry entry. Nothing in fitting or scoring knows the
names of individual predictors, so a new variable is tested by declaring it
here and rerunning (margin-model spec, "Variants are declared, not hard-coded").
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
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
    # The kind of electorate a race was decided by. One categorical rather than
    # `pres_elec` alongside a signed midterm term, because restricted to
    # general elections those two booleans have three joint levels and stating
    # them as two hides both the saturation and which level the record barely
    # holds (design.md, D1). The first level is the reference: every timing
    # coefficient reads against a presidential ballot.
    "ballot_timing": [
        "presidential",
        "midterm_dem_pres",
        "midterm_gop_pres",
        "special",
    ],
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
    "ballot_timing": {
        "reference": "presidential",
        "levels": {
            "midterm_dem_pres": "timing_midterm_dem_pres",
            "midterm_gop_pres": "timing_midterm_gop_pres",
            "special": "timing_special",
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
    # Knowable before the race: `is_special` and the election date are fixed
    # when the election is called, and which party holds the presidency is
    # settled by an election held two or four years earlier. Nothing here is
    # read from the result.
    "ballot_timing": {
        "from": ("is_special", "pres_elec", "election_year"),
        "description": (
            "the kind of electorate the race was decided by: presidential "
            "ballot, midterm under a Democratic or a Republican president, or "
            "a special election"
        ),
    },
}

# The money windows the race table carries, each named by how far before a
# race's own election it was measured. The window is trailing rather than
# calendar year-to-date, so a January special is measured over the year its
# campaign was actually funded in (design.md, D2).
MONEY_WINDOWS = {
    "primary": "14 days before the election",
    "wide": "60 days before the election",
}

# The two sides of a committee's ledger, both collected over both windows. Each
# maps to the prefix its derived predictors carry: the receipts predictors keep
# the `money_` names their published results were recorded under, and spending
# is `spend_`. Receipts were scored first because spending is closer to the
# outcome in time and more likely to respond to a race already tightening
# (design.md, D5); that is a reason to read the two differently, not a reason
# to leave one unmeasured.
MONEY_MEASURES = {
    "receipts": {"prefix": "money", "noun": "receipts", "verb": "raised"},
    "expenditures": {"prefix": "spend", "noun": "spending", "verb": "spent"},
}

# The measure whose predictors the bare helpers default to.
MONEY_MEASURE = "receipts"

# In thousands of dollars, so the coefficient on an absolute advantage is
# readable in margin points per thousand rather than per dollar.
MONEY_DIFF_SCALE = 1000.0


def money_columns(window: str, measure: str = MONEY_MEASURE) -> tuple[str, str]:
    """The race table's Democratic and opponent money columns for a window."""
    return (f"dem_{measure}_{window}", f"opp_{measure}_{window}")


def money_as_of_column(window: str) -> str:
    return f"money_as_of_{window}"


# Four contrasts over the same two columns, all oriented so that a larger value
# is a Democratic advantage, because the response is a margin and a predictor
# tracking one candidate's fundraising alone measures race salience rather than
# advantage (design.md, D5). Which of them the data separates is the scoring
# harness's question, not one to settle by argument here.
for _measure, _spec in MONEY_MEASURES.items():
    _p, _noun, _verb = _spec["prefix"], _spec["noun"], _spec["verb"]
    for _window, _when in MONEY_WINDOWS.items():
        _dem, _opp = money_columns(_window, _measure)
        DERIVED.update(
            {
                f"{_p}_share_{_window}": {
                    "from": (_dem, _opp),
                    "description": (
                        f"the Democratic share of the race's total {_noun} as of "
                        f"{_when}; 0.5 when the two sides {_verb} the same"
                    ),
                },
                f"{_p}_logratio_{_window}": {
                    "from": (_dem, _opp),
                    "description": (
                        f"log of the ratio of Democratic to opponent {_noun} as of "
                        f"{_when}, each offset by a dollar so a genuine zero is "
                        f"admitted; 0 when the two sides {_verb} the same"
                    ),
                },
                f"{_p}_diff_{_window}": {
                    "from": (_dem, _opp),
                    "description": (
                        f"Democratic minus opponent {_noun} as of "
                        f"{_when}, in thousands of dollars; 0 when the two sides "
                        f"{_verb} the same"
                    ),
                },
                f"{_p}_log_dem_{_window}": {
                    "from": (_dem,),
                    "description": f"log1p of Democratic {_noun} as of {_when}",
                },
                f"{_p}_log_opp_{_window}": {
                    "from": (_opp,),
                    "description": f"log1p of opponent {_noun} as of {_when}",
                },
            }
        )
del _measure, _spec, _p, _noun, _verb, _window, _when, _dem, _opp

# A predictor computed from the fold's own results would leak the outcome
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
    """Refuse a predictor built from the fold's own outcome.

    Every predictor must be derivable before its fold's election date. A predictor
    built from vote counts is knowable only once the election has happened, so
    a fit using it would be reading the answer (margin-model spec, "A predictor
    must be knowable before its fold's election date").
    """
    spec = DERIVED.get(predictor)
    if spec is None:
        if predictor in OUTCOME_COLUMNS:
            raise LeakingPredictorError(
                f"predictor {predictor!r} is an outcome of the race being "
                "predicted, so it is not knowable before its election date"
            )
        return
    leaking = sorted(set(spec["from"]) & OUTCOME_COLUMNS)
    if leaking:
        raise LeakingPredictorError(
            f"derived predictor {predictor!r} is computed from {leaking}, which "
            "is only known once the fold's election has happened"
        )


def president_party(frame: "pd.DataFrame") -> "pd.Series":
    """The party holding the presidency for each race's election year."""
    party = frame["election_year"].map(PRESIDENT_PARTY)
    if party.isna().any():
        missing = sorted(frame.loc[party.isna(), "election_year"].unique().tolist())
        raise ValueError(
            f"no recorded presidential party for election years {missing}; "
            "extend PRESIDENT_PARTY before scoring them"
        )
    return party


# The columns `ballot_timing` is computed from. A frame missing any of them
# simply does not get the column, which is what lets the synthetic frames the
# refusal tests build stay as small as the refusal they exercise.
BALLOT_TIMING_INPUTS = ("is_special", "pres_elec", "election_year")


def ballot_timing_levels(frame: "pd.DataFrame") -> "pd.Series":
    """Each race's ballot-timing level.

    The single place a race is assigned a timing level. The predictor reads it
    through `derive`, and the scorecard's segment reads the same column, so a
    segment row and a coefficient cannot come to describe different races
    (design.md, D5).

    A special election takes `special` whatever year or ballot it fell on. No
    special in the record has fallen on a presidential general date, so every
    one of them carries `pres_elec = False`; coding them by the president's
    party would describe a March special as the midterm-backlash electorate it
    is not.
    """
    party = president_party(frame)
    special = frame["is_special"].astype(bool)
    presidential = frame["pres_elec"].astype(bool)
    midterm = np.where(party == "D", "midterm_dem_pres", "midterm_gop_pres")
    return pd.Series(
        np.where(special, "special", np.where(presidential, "presidential", midterm)),
        index=frame.index,
    )


def derive(races: "pd.DataFrame") -> "pd.DataFrame":
    """Add the derived predictor columns."""
    frame = races
    if "election_year" in frame.columns:
        party = president_party(frame)
        midterm = ~frame["pres_elec"].astype(bool)
        frame["national_env"] = midterm.astype(int) * party.map({"D": -1, "R": 1})
    if set(BALLOT_TIMING_INPUTS) <= set(frame.columns):
        frame["ballot_timing"] = ballot_timing_levels(frame)
    if "incumbent_status" in frame.columns:
        pres = frame["pres_elec"].astype(int)
        frame["pres_elec_x_incumbent_dem"] = pres * (
            frame["incumbent_status"] == "Dem_Incumbent"
        ).astype(int)
        frame["pres_elec_x_incumbent_gop"] = pres * (
            frame["incumbent_status"] == "GOP_Incumbent"
        ).astype(int)
    for measure, spec in MONEY_MEASURES.items():
        prefix = spec["prefix"]
        for window in MONEY_WINDOWS:
            dem_column, opp_column = money_columns(window, measure)
            if dem_column not in frame.columns or opp_column not in frame.columns:
                continue
            # Missing money stays missing through every contrast. A race whose
            # filer was never found must not arrive at the fit as a candidate
            # who raised nothing (design.md, D4), and a variant carrying one of
            # these predictors is refused before it can (`check_complete`).
            dem, opp = frame[dem_column], frame[opp_column]
            total = dem + opp
            frame[f"{prefix}_share_{window}"] = (dem / total).where(total > 0)
            frame[f"{prefix}_logratio_{window}"] = np.log((dem + 1.0) / (opp + 1.0))
            frame[f"{prefix}_diff_{window}"] = (dem - opp) / MONEY_DIFF_SCALE
            frame[f"{prefix}_log_dem_{window}"] = np.log1p(dem)
            frame[f"{prefix}_log_opp_{window}"] = np.log1p(opp)
    return frame


def prepare(races: "pd.DataFrame") -> "pd.DataFrame":
    """Coerce predictor columns to the encoding every fit must share.

    The level set is imposed here rather than inferred per fold, so a fold
    whose training races happen to omit a level still produces a design matrix
    that accepts a holdout race carrying it.
    """
    # Derived before the categoricals are expanded, because `ballot_timing` is
    # both: a column computed from the table and a categorical whose indicators
    # the design matrix carries.
    prepared = derive(with_flags(races.copy()))
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
    return prepared


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


# The scale of the normal prior on a ballot-timing coefficient, in margin
# points. Unlike most coefficients this one cannot be left to the fitting
# library: a level the fold's training window never held has a flat likelihood,
# so its posterior *is* its prior, and fold 2018-11-06 predicts 71 races on a
# `midterm_gop_pres` coefficient of exactly that kind. Normal(0, 10) puts about
# 95% of its mass within 20 margin points of no timing effect, which spans
# every timing swing the record holds without licensing a hundred-point one.
# Bambi's auto-scaled default is derived from the response's own spread and is
# several times wider, which is a choice nobody made (design.md, D3).
TIMING_PRIOR_SCALE = 10.0


def timing_priors(sigma: float = TIMING_PRIOR_SCALE) -> dict:
    """An explicit prior on every `ballot_timing` coefficient."""
    prior = Prior("Normal", (("mu", 0.0), ("sigma", float(sigma))))
    return {column: prior for column in expand("ballot_timing")}


def level_counts(variant, prepared: "pd.DataFrame") -> dict:
    """Training races at each declared level of each categorical declared.

    Every declared level appears, including one no training race carries. A
    zero here is the signal that the corresponding coefficient was drawn from
    its prior rather than estimated, and it is only a signal if the level is
    present to carry it (margin-model spec, "Level counts travel with the
    fit").
    """
    counts = {}
    for predictor in variant.predictors:
        levels = CATEGORICAL_LEVELS.get(predictor)
        if levels is None or predictor not in prepared.columns:
            continue
        observed = prepared[predictor].value_counts()
        counts[predictor] = {
            level: int(observed.get(level, 0)) for level in levels
        }
    return counts


def render_level_counts(counts: dict) -> str:
    """The level counts as one stable string, for publication."""
    return "; ".join(
        f"{predictor}: "
        + ", ".join(f"{level}={n}" for level, n in levels.items())
        for predictor, levels in sorted(counts.items())
    )


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


# Every money contrast is knowable only during the election year, and the date
# it was measured to is a property of the race rather than of the run: the
# window ends a fixed number of days before each race's own election, so the
# calendar date differs from race to race and is carried in the table.
for _measure in MONEY_MEASURES.values():
    for _window in MONEY_WINDOWS:
        for _form in ("share", "logratio", "diff", "log_dem", "log_opp"):
            register_dated(
                f"{_measure['prefix']}_{_form}_{_window}",
                money_as_of_column(_window),
            )
del _measure, _window, _form

# What a variant writes in `as_of` when its predictors were measured a fixed
# distance before each race's own election rather than on one calendar date.
# The per-race dates are in the column `DATED_PREDICTORS` names.
RELATIVE_AS_OF = {
    window: f"election-{lead}d"
    for window, lead in (("primary", 14), ("wide", 60))
}


class MissingPredictorValueError(ValueError):
    """A variant's predictor is missing for a race it would be fit on.

    A money figure is missing where the candidate could not be matched to a
    filer, which is a different fact from a candidate who raised nothing. A
    variant carrying such a predictor has to say what it does about those
    races -- filter them out, or carry an explicit unknown indicator -- and is
    refused here rather than allowed to impute (campaign-finance spec, "A
    filer with no money is distinct from no filer").
    """


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


class CoarseGroupingError(ValueError):
    """A grouping factor's levels span more than one fold.

    A fold is one election date, so a factor coarser than that -- a calendar
    year, say -- has levels holding races from several folds. The holdout's own
    level is then partially observed: predicting a November general, the year
    effect would be estimated from the specials held earlier that year and
    applied to the whole chamber. That is not a modelling trade-off, it is an
    effect estimated from the wrong population, so it is refused rather than
    disclosed (margin-model spec, "A group effect groups no coarser than the
    fold").
    """


# The column a fold is keyed on. A grouping factor must be determined by it:
# each level of the factor must lie inside a single election date.
FOLD_GRAIN = "election_date"


def check_grouping_grain(variant: "Variant", races: "pd.DataFrame") -> None:
    """Refuse a grouping factor coarser than the fold.

    Unlike `check_grouping`, which genuinely depends on which races a fold
    trains on, this is a property of the table: whether a factor's levels can
    span two election dates does not change fold by fold. So it is checked once
    against the whole table, and a variant declaring `election_year` fails at
    registration rather than 23 times over.
    """
    if FOLD_GRAIN not in races.columns:
        return
    for group in variant.group_effects:
        if group not in races.columns or group == FOLD_GRAIN:
            continue
        spanning = races.groupby(group)[FOLD_GRAIN].nunique()
        offenders = spanning[spanning > 1]
        if not offenders.empty:
            example = offenders.index[0]
            raise CoarseGroupingError(
                f"variant {variant.name!r} groups on {group!r}, whose levels "
                f"span more than one election date ({len(offenders)} of "
                f"{len(spanning)} do; {example!r} spans "
                f"{int(offenders.iloc[0])}). A fold is one election date, so "
                f"the holdout's own {group!r} level would be partially "
                f"observed from races the fold trains on. Group on "
                f"{FOLD_GRAIN!r} instead."
            )


class GroupedPredictorError(ValueError):
    """A predictor is spanned by the variant's own grouping factor.

    A predictor constant within every level of a group effect is a linear
    combination of that group's indicators, so the two are not separately
    identified and the sampler explores a ridge instead of estimating two
    effects (margin-model spec, "A predictor constant within a grouping level
    is rejected").
    """


class CollinearPredictorError(ValueError):
    """Two of a variant's own predictors are exactly collinear in a fold.

    The same defect as a predictor its grouping factor spans -- two parameters
    competing for one column, not separately identified -- arrived at without a
    group effect. `national_env` is `pres_elec - 1` on every training window
    whose midterms all fell under a Democratic president, and nothing refused
    it while the confounding test only ever looked at grouping factors
    (margin-model spec, "Two exactly collinear predictors are refused").
    """


# Below this many training races carrying within-group variation, a predictor
# is fit but its identifying count is published, because a coefficient resting
# on a handful of races out of hundreds should not read like one resting on all
# of them (design.md, D5). Nothing branches on the value; it is a reporting
# threshold.
SEPARATING_RACES_DISCLOSED = 30

# A pair of predictors is tested by grouping on the coarser of the two, which
# is only meaningful while that column behaves as a factor. Group by a column
# whose values are nearly all distinct and every level is a singleton, so the
# other column is constant within each of them and `separating_races` returns
# zero for any pair whatever -- `baseline` would be refused for carrying PVI_N
# beside anything. Above this many distinct values a column is not a grouping,
# and the pair is judged by exact linear dependence instead, which is the other
# half of what the requirement names: "or is an exact affine function of it".
PAIRWISE_GROUPING_LEVELS = 10


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


def exactly_affine(frame: "pd.DataFrame", a: str, b: str) -> bool:
    """Whether one column is an exact affine function of the other.

    Exact linear dependence, not a strong relationship: a correlation of one in
    magnitude means the two columns differ by a scale and a shift and so span a
    single direction of the design matrix. Anything short of that is a
    collinearity to report, not a specification error to refuse.
    """
    for column in (a, b):
        if not pd.api.types.is_numeric_dtype(frame[column]):
            return False
        if frame[column].isna().any():
            return False
    with np.errstate(invalid="ignore", divide="ignore"):
        matrix = np.corrcoef(
            frame[a].to_numpy(dtype=float), frame[b].to_numpy(dtype=float)
        )
    return bool(np.isclose(abs(matrix[0, 1]), 1.0, atol=1e-10))


def collinear_pair(frame: "pd.DataFrame", a: str, b: str) -> str:
    """Why `a` and `b` are exactly collinear here, or "" if they are not.

    A column with no variation in the training races is skipped rather than
    refused. That is the unobserved-level case: a categorical level the fold's
    training window never held has an all-zero indicator, which is a statement
    about what the record holds and is disclosed through the published level
    counts (design.md, D3).
    """
    if frame[a].nunique(dropna=False) < 2 or frame[b].nunique(dropna=False) < 2:
        return ""
    group, other = (a, b) if frame[a].nunique() <= frame[b].nunique() else (b, a)
    if frame[group].nunique() <= PAIRWISE_GROUPING_LEVELS:
        if separating_races(frame, other, group) == 0:
            return (
                f"{other!r} is constant within every level of {group!r}, so the "
                "two are a single column carrying two parameters"
            )
    if exactly_affine(frame, a, b):
        return f"{a!r} is an exact affine function of {b!r}"
    return ""


def check_collinear(
    variant: "Variant", prepared: "pd.DataFrame", fold: object = None
) -> None:
    """Refuse a variant carrying two exactly collinear predictors.

    Pairwise over the expanded design columns rather than a rank test on the
    whole matrix: a rank deficiency says the matrix is singular without saying
    which two terms to name, and the error message is the point. Pairwise also
    leaves the all-zero indicator of an unobserved level alone, which a rank
    test would not (design.md, D2).
    """
    columns = [
        column
        for predictor in variant.predictors
        for column in expand(predictor)
        if column in prepared.columns
    ]
    where = f" on fold {fold}" if fold is not None else ""
    for i, a in enumerate(columns):
        for b in columns[i + 1 :]:
            reason = collinear_pair(prepared, a, b)
            if reason:
                raise CollinearPredictorError(
                    f"variant {variant.name!r}{where}: predictors {a!r} and "
                    f"{b!r} are exactly collinear across the "
                    f"{len(prepared)} training races -- {reason} -- so they "
                    "are not separately identified"
                )


def check_grouping(
    variant: "Variant", prepared: "pd.DataFrame", fold: object = None
) -> dict:
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
    # A grouping factor is one way two parameters end up over one column; two
    # fixed effects are another, and the refusal is the same either way
    # (margin-model spec, "Two exactly collinear predictors are refused").
    check_collinear(variant, prepared, fold)
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
    # published with every fit either way. Either a calendar date, or one of
    # the `RELATIVE_AS_OF` declarations, for a predictor measured a fixed
    # distance before each race's own election.
    as_of: str = ""
    # Boolean columns a race must carry for this variant to be fit on it. This
    # is how a variant says what it does about races whose predictor is
    # unavailable: it excludes them, and its holdout count is published
    # alongside the baseline's so the cost of excluding them is visible
    # (design.md, D4).
    requires: tuple[str, ...] = ()

    @property
    def is_composite(self) -> bool:
        return False

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

    def validate(self, columns, races: "pd.DataFrame | None" = None) -> None:
        """Fail loudly on a predictor the table does not carry.

        `races` is optional because the per-fold validation in `fit.py` has
        only the training columns to hand. When a caller does have the frame,
        the grouping factor's grain is checked against it too -- a property of
        the table rather than of a fold, so checking it once at the top of a
        scoring run beats failing identically on every fold.
        """
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
        requirable = set(columns) | set(DERIVED_FLAGS)
        missing = [p for p in self.predictors if p not in available]
        missing += [g for g in self.group_effects if g not in set(columns)]
        missing += [c for c in self.requires if c not in requirable]
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
        if races is not None:
            check_grouping_grain(self, races)


BASELINE_PREDICTORS = ("PVI_N", "incumbent_status", "pres_elec")

class CompositeRoutingError(ValueError):
    """A race matched no component of a composite variant, or more than one."""


@dataclass(frozen=True)
class CompositeVariant:
    """Two component variants plus a predicate saying which predicts what.

    The components are ordinary `Variant`s, so priors, sampler settings,
    diagnostics, the knowability checks and the confounding refusal are all
    the machinery a single-fit variant already uses. What a composite adds is
    only the routing: each holdout race is predicted by exactly one component,
    chosen by its own value of `route_on`.

    This exists for `special_split`, where the question is not which term to
    add but whether special elections belong in the general-election fit at
    all. A component may be fit on a subset of the fold's training races, which
    it declares through its own `requires` (margin-model spec, "A variant may
    be composite").
    """

    name: str
    # Keyed by the value of `route_on` the component predicts. Boolean keys,
    # since the predicate is a boolean column.
    components: dict
    route_on: str
    description: str = ""

    @property
    def is_composite(self) -> bool:
        return True

    @property
    def declared(self) -> str:
        parts = [
            f"{value}: {component.declared}"
            for value, component in sorted(self.components.items())
        ]
        return f"route on {self.route_on} -- " + "; ".join(parts)

    @property
    def prior_declaration(self) -> str:
        return "; ".join(
            f"{value}: {component.prior_declaration}"
            for value, component in sorted(self.components.items())
            if component.prior_declaration
        )

    @property
    def requires(self) -> tuple:
        """What the composite as a whole needs on every race it scores.

        The intersection of its components' requirements, not the union: a
        column one component needs is not needed by races the other predicts.
        Each component's own `requires` still restricts its own fit.
        """
        sets = [set(c.requires) for c in self.components.values()]
        common = set.intersection(*sets) if sets else set()
        return tuple(sorted(common))

    @property
    def as_of(self) -> str:
        declared = {c.as_of for c in self.components.values() if c.as_of}
        return sorted(declared)[0] if len(declared) == 1 else ""

    @property
    def target_accept(self):
        return None

    @property
    def tune(self):
        return None

    @property
    def group_effects(self) -> tuple:
        return ()

    @property
    def predictors(self) -> tuple:
        """Every predictor either component declares, for reporting only.

        A composite has no single design matrix, so this is the union rather
        than a formula. Nothing fits against it.
        """
        seen = []
        for component in self.components.values():
            for predictor in component.predictors:
                if predictor not in seen:
                    seen.append(predictor)
        return tuple(seen)

    def validate(self, columns, races: "pd.DataFrame | None" = None) -> None:
        if self.route_on not in set(columns):
            raise UnknownPredictorError(
                f"composite variant {self.name!r} routes on {self.route_on!r}, "
                f"which the race table does not carry; available columns are "
                f"{sorted(set(columns))}"
            )
        if len(self.components) < 2:
            raise UnknownPredictorError(
                f"composite variant {self.name!r} declares "
                f"{len(self.components)} component(s); a composite is two or "
                "more, or it is just a variant"
            )
        for component in self.components.values():
            component.validate(columns, races)

    def route(self, races: "pd.DataFrame") -> dict:
        """Split races by the routing predicate, one group per component.

        Every race must match exactly one component. A race matching none is
        named rather than dropped, and an overlap is impossible by
        construction here but checked anyway, because a silently doubled
        prediction would corrupt the pooled score rather than fail
        (margin-model spec, "Every holdout race is routed to exactly one
        component").
        """
        if self.route_on not in races.columns:
            raise CompositeRoutingError(
                f"composite variant {self.name!r} routes on "
                f"{self.route_on!r}, absent from the frame being routed"
            )
        values = races[self.route_on].astype(bool)
        groups, assigned = {}, pd.Series(0, index=races.index)
        for value, component in self.components.items():
            mask = values == bool(value)
            assigned += mask.astype(int)
            groups[value] = races[mask]
        unmatched = races[assigned == 0]
        doubled = races[assigned > 1]
        if len(unmatched) or len(doubled):
            bad = pd.concat([unmatched, doubled])
            names = ", ".join(str(v) for v in bad["election_id"].head(5))
            raise CompositeRoutingError(
                f"composite variant {self.name!r} routed {len(unmatched)} "
                f"race(s) to no component and {len(doubled)} to more than "
                f"one, on {self.route_on!r}; first affected: {names}"
            )
        return groups


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
# The three special-election handling arms. Every special election in the
# record carries `pres_elec = False` -- none has ever fallen on a presidential
# general date -- so specials sit inside the `pres_elec` segment and inside
# the identification of `pres_elec` itself. Whether they belong in the
# general-election fit at all is therefore a question, not an assumption, and
# it is settled by comparing three arms rather than by adding one term
# (margin-model spec, "The three special-election handling arms are
# registered").
#
# Arm A: specials in training and holdout, distinguished by a term. This is
# the former `baseline_special`, renamed.
register(
    Variant(
        name="special_pooled_term",
        predictors=BASELINE_PREDICTORS + ("is_special",),
        description="specials pooled into one fit, with an is_special term",
    )
)
# Arm B: specials in training and holdout, undistinguished. Identical in
# substance to `baseline`; registered under its own name so the three arms
# read as a set, and asserted equal to `baseline` as a regression test on the
# composite plumbing (tasks 3.6).
register(
    Variant(
        name="special_pooled_plain",
        predictors=BASELINE_PREDICTORS,
        description="specials pooled into one fit, with no is_special term",
    )
)
# Arm C: two fits. The general component never sees a special election, in
# training or in holdout. The special component trains on everything -- the
# general races are the prior information its handful of specials cannot
# supply alone -- and is only ever asked about specials.
register(
    CompositeVariant(
        name="special_split",
        components={
            False: Variant(
                name="special_split_general",
                predictors=BASELINE_PREDICTORS,
                requires=("not_special",),
                description="general elections only, fit without specials",
            ),
            True: Variant(
                name="special_split_special",
                predictors=BASELINE_PREDICTORS + ("is_special",),
                description="all races, with an is_special term, predicting specials",
            ),
        },
        route_on="is_special",
        description=(
            "a general-election model excluding specials entirely, and a "
            "special-election model fit on all races, each predicting its own"
        ),
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
# A hierarchical intercept per election date. It groups on the date rather
# than the calendar year because a fold is one election date: a year-level
# effect would leave the holdout's own level partially observed from races the
# fold trains on -- predicting the 2016 general, the 2016 effect would come
# from three specials held six months earlier and apply to 59 general races.
# Grouping at the fold's own grain keeps the holdout level unobserved and drawn
# from the hyperprior, which is the forward-prediction posture the variant
# claims anyway (margin-model spec, "A group effect groups no coarser than the
# fold").
#
# It drops `pres_elec`, which is a property of the election date and so is
# constant within every level of this grouping by construction. That is checked
# per fold from the training races rather than asserted here; the contrast arm
# below is what makes the removal a measurement. Dropping it also stops the
# variant being nested in `baseline` -- a fact its comparison has to state.
register(
    Variant(
        name="baseline_year",
        predictors=("PVI_N", "incumbent_status"),
        group_effects=("election_date",),
        priors={group_term("election_date"): group_intercept_prior()},
        target_accept=0.95,
        description=(
            "the baseline plus a hierarchical election-date intercept, minus "
            "the pres_elec term that intercept contains"
        ),
    )
)
# The contrast arm: the same variant keeping `pres_elec`, under the same prior
# and the same sampler setting, so that dropping the term is evidence rather
# than assertion. Under a date grouping the confounding is exact on every fold
# rather than only the early ones, so this arm is expected to be refused
# throughout -- which is the same evidence the year-grouped arm gave, stated
# more sharply.
register(
    Variant(
        name="baseline_year_pres",
        predictors=BASELINE_PREDICTORS,
        group_effects=("election_date",),
        priors={group_term("election_date"): group_intercept_prior()},
        target_accept=0.95,
        description=(
            "the date-intercept variant retaining pres_elec, as the contrast "
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
# The same three timing groups `pres_elec` and `national_env` between them
# described, declared as one categorical instead of two booleans. Restricted to
# general elections there are exactly three of them, so intercept plus two
# booleans was already saturated; stating them as two hid both that and the
# fact that the third group is the single 2018 election. The categorical adds a
# fourth level for special elections, which stay in training and would
# otherwise have to be coded by the president's party -- the miscoding this
# change exists to remove (design.md, D1).
#
# `pres_elec` and `national_env` are absent by construction: the categorical
# supplies the whole timing contrast, and declaring either beside it is the
# collinear pair the refusal now catches.
TIMING_PREDICTORS = ("PVI_N", "incumbent_status", "ballot_timing")

register(
    Variant(
        name="baseline_timing",
        predictors=TIMING_PREDICTORS,
        # An unobserved level's posterior is its prior, and fold 2018-11-06
        # predicts 71 races on one. Left to the library the scale would be
        # derived from the response's spread rather than from any judgement
        # about plausible timing shifts (design.md, D3).
        priors=timing_priors(),
        description=(
            "the baseline with ballot timing as one four-level categorical in "
            "place of the pres_elec boolean"
        ),
    )
)
register(
    Variant(
        name="baseline_timing_money",
        predictors=TIMING_PREDICTORS + ("money_logratio_primary",),
        requires=("money_complete",),
        as_of=RELATIVE_AS_OF["primary"],
        priors=timing_priors(),
        description=(
            "the timing categorical plus the log ratio of Democratic to "
            "opponent receipts, measured 14 days before the election"
        ),
    )
)
register(
    Variant(
        name="baseline_timing_money_wide",
        predictors=TIMING_PREDICTORS + ("money_logratio_wide",),
        requires=("money_complete",),
        as_of=RELATIVE_AS_OF["wide"],
        priors=timing_priors(),
        description=(
            "the timing categorical plus the log ratio of Democratic to "
            "opponent receipts, measured 60 days before the election"
        ),
    )
)
register(
    Variant(
        name="baseline_no_timing",
        predictors=("PVI_N", "incumbent_status"),
        description="the baseline without an election-level timing term",
    )
)
register(
    Variant(
        name="baseline_money_logratio_no_timing",
        predictors=("PVI_N", "incumbent_status", "money_logratio_primary"),
        requires=("money_complete",),
        as_of=RELATIVE_AS_OF["primary"],
        description=(
            "PVI, incumbency, and the 14-day receipts log ratio, without "
            "ballot timing or pres_elec"
        ),
    )
)
register(
    Variant(
        name="baseline_money_logratio_no_timing_wide",
        predictors=("PVI_N", "incumbent_status", "money_logratio_wide"),
        requires=("money_complete",),
        as_of=RELATIVE_AS_OF["wide"],
        description=(
            "PVI, incumbency, and the 60-day receipts log ratio, without "
            "ballot timing or pres_elec"
        ),
    )
)
register(
    CompositeVariant(
        name="forecast_60d",
        components={
            False: REGISTRY["baseline_no_timing"],
            True: REGISTRY["baseline_money_logratio_no_timing_wide"],
        },
        route_on="money_complete",
        description=(
            "the 60-day operational composite selected by the clustered "
            "timing comparison and the predeclared no-timing simplicity "
            "tie-break; incomplete finance uses baseline_no_timing"
        ),
    )
)
register(
    CompositeVariant(
        name="forecast_14d",
        components={
            False: REGISTRY["baseline_no_timing"],
            True: REGISTRY["baseline_money_logratio_no_timing"],
        },
        route_on="money_complete",
        description=(
            "the 14-day operational composite selected by the clustered "
            "timing comparison and the predeclared no-timing simplicity "
            "tie-break; incomplete finance uses baseline_no_timing"
        ),
    )
)


# The money sweep. Four contrasts over the same two columns, registered rather
# than reasoned down to one, because which of them the data separates is the
# question the harness exists to answer and the standing rule is that a
# comparison whose interval spans zero is published as undecided rather than
# settled by argument (design.md, D5).
#
# Each is registered at both windows. The primary window ends 14 days before
# each race's election -- late enough to have captured the campaign, early
# enough to be a forecast, and just before the pre-election reporting deadline
# rather than after it. The second exists so the sensitivity of any result to
# that cutoff is measurable rather than assumed (design.md, D2).
MONEY_FORMS = {
    "share": ("{prefix}_share_{window}",),
    "logratio": ("{prefix}_logratio_{window}",),
    "diff": ("{prefix}_diff_{window}",),
    "both": ("{prefix}_log_dem_{window}", "{prefix}_log_opp_{window}"),
}

MONEY_FORM_DESCRIPTIONS = {
    "share": "the Democratic share of the race's total {noun}",
    "logratio": "the log ratio of Democratic to opponent {noun}",
    "diff": "the Democratic {noun} advantage in thousands of dollars",
    "both": "log {noun} for each side as separate terms",
}

# The same four contrasts over each side of the ledger. Spending is registered
# as its own family rather than replacing receipts, because the two are
# different claims: a committee's receipts say who could afford a campaign, its
# expenditures say what was actually put into the field, and the second is
# closer in time to the outcome it is being asked to predict.
for _measure in MONEY_MEASURES.values():
    _prefix, _noun = _measure["prefix"], _measure["noun"]
    for _window in MONEY_WINDOWS:
        _suffix = "" if _window == "primary" else f"_{_window}"
        for _form, _terms in MONEY_FORMS.items():
            register(
                Variant(
                    name=f"baseline_{_prefix}_{_form}{_suffix}",
                    predictors=BASELINE_PREDICTORS
                    + tuple(
                        term.format(prefix=_prefix, window=_window)
                        for term in _terms
                    ),
                    # Races where a candidate could not be matched to a filer
                    # are excluded rather than imputed: a missing filer and a
                    # candidate who raised nothing are different facts, and a
                    # fake zero would land exactly where the match is hardest
                    # (design.md, D4).
                    requires=("money_complete",),
                    as_of=RELATIVE_AS_OF[_window],
                    description=(
                        "the baseline plus "
                        + MONEY_FORM_DESCRIPTIONS[_form].format(noun=_noun)
                        + f", measured {MONEY_WINDOWS[_window]}"
                    ),
                )
            )
del _measure, _prefix, _noun, _window, _suffix, _form, _terms


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


# Boolean flags a variant may name in `requires` that the race table does not
# carry directly. They exist so a component of a composite variant can say
# which population it is fit on through the mechanism that already restricts
# the money variants, rather than through a second one: the general-election
# component of `special_split` declares `requires=("not_special",)` and is
# thereby excluded from special elections in training and holdout alike.
DERIVED_FLAGS = {
    "not_special": {
        "from": ("is_special",),
        "compute": lambda frame: ~frame["is_special"].astype(bool),
        "description": "the race is a general election, not a special",
    },
}


def with_flags(races: "pd.DataFrame") -> "pd.DataFrame":
    """Add the derived boolean flags a variant may require.

    Computed before `restrict` rather than in `prepare`, because a variant's
    `requires` is applied to the race table ahead of fold construction and so
    runs before anything has been prepared.
    """
    frame = races
    for name, spec in DERIVED_FLAGS.items():
        if name in frame.columns:
            continue
        if not set(spec["from"]) <= set(frame.columns):
            continue
        if frame is races:
            frame = races.copy()
        frame[name] = spec["compute"](frame)
    return frame


def restrict(variant: "Variant", races: "pd.DataFrame") -> "pd.DataFrame":
    """The races a variant's declared requirements admit.

    Applied before the folds are built, so a variant that excludes a race
    excludes it from training as well as from scoring, and its published
    holdout count is the count it was actually scored on.
    """
    if not variant.requires:
        return races
    races = with_flags(races)
    keep = pd.Series(True, index=races.index)
    for column in variant.requires:
        if column not in races.columns:
            raise UnknownPredictorError(
                f"variant {variant.name!r} requires column {column!r}, which "
                "the race table does not carry"
            )
        keep &= races[column].astype(bool)
    return races[keep].copy()


def check_complete(variant: "Variant", prepared: "pd.DataFrame", where: str) -> None:
    """Refuse a variant whose predictor is missing for a race it would use."""
    incomplete = {}
    for predictor in variant.predictors:
        for column in expand(predictor):
            if column not in prepared.columns:
                continue
            missing = int(prepared[column].isna().sum())
            if missing:
                incomplete[column] = missing
    if incomplete:
        detail = ", ".join(f"{c} on {n} races" for c, n in sorted(incomplete.items()))
        raise MissingPredictorValueError(
            f"variant {variant.name!r} has missing predictor values in its "
            f"{where}: {detail}. Declare `requires` so the variant excludes "
            "those races, or carry an explicit unknown indicator; the one "
            "thing it may not do is impute"
        )


def check_as_of(variant: "Variant", holdout) -> None:
    """Refuse a dated predictor measured on or after the election it predicts.

    The whole point of measuring money to a stated date is that the date falls
    before the votes are cast. A date on or after election day would be reading
    the result, so it is refused rather than fit (margin-model spec, "The as-of
    date is before the election it predicts").

    A variant declaring a calendar date is checked against the earliest
    election it predicts. A variant whose predictors were measured a fixed
    distance before each race's own election has a different date per race, so
    it is checked per race against the column carrying them -- which is the
    stronger check, since it reaches every race rather than only the earliest.
    """
    if not variant.as_of:
        return
    frame = holdout if isinstance(holdout, pd.DataFrame) else None
    dates = pd.Series(
        list(frame["election_date"]) if frame is not None else list(holdout)
    )
    dates = pd.to_datetime(dates.dropna())
    if dates.empty:
        return

    if variant.as_of not in RELATIVE_AS_OF.values():
        as_of = pd.Timestamp(variant.as_of)
        earliest = dates.min()
        if as_of >= earliest:
            raise AsOfDateAfterElectionError(
                f"variant {variant.name!r} declares as_of {variant.as_of}, which is "
                f"on or after the election on {earliest.date()}; a predictor "
                "measured then would be reading the result"
            )
        return

    dated = [p for p in variant.predictors if p in DATED_PREDICTORS]
    if not dated:
        raise MissingAsOfDateError(
            f"variant {variant.name!r} declares the relative as_of "
            f"{variant.as_of!r} but carries no dated predictor to measure"
        )
    if frame is None:
        raise AsOfDateAfterElectionError(
            f"variant {variant.name!r} declares the relative as_of "
            f"{variant.as_of!r}, whose date differs per race, so it cannot be "
            "checked against election dates alone"
        )
    for column in sorted({DATED_PREDICTORS[p] for p in dated}):
        if column not in frame.columns:
            raise MissingAsOfDateError(
                f"variant {variant.name!r} names dated predictors measured to "
                f"{column!r}, which the race table does not carry"
            )
        measured = pd.to_datetime(frame[column])
        late = measured >= pd.to_datetime(frame["election_date"])
        if late.any():
            first = frame[late].iloc[0]
            raise AsOfDateAfterElectionError(
                f"variant {variant.name!r} would be fit on {int(late.sum())} "
                f"races whose {column} falls on or after their own election, "
                f"beginning with election {first['election_id']} "
                f"({first[column]} against {first['election_date']}); a "
                "predictor measured then would be reading the result"
            )
