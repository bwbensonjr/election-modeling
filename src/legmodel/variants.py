"""Model variants, declared as a name plus a predictor list.

Adding a variant is a registry entry. Nothing in fitting or scoring knows the
names of individual predictors, so a new variable is tested by declaring it
here and rerunning (margin-model spec, "Variants are declared, not hard-coded").
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from . import config

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
    return prepared


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
    response: str = field(default=config.RESPONSE)

    @property
    def formula(self) -> str:
        terms = [column for p in self.predictors for column in expand(p)]
        return f"{self.response} ~ " + " + ".join(terms)

    @property
    def declared(self) -> str:
        """The variant as declared, before categorical expansion."""
        return f"{self.response} ~ " + " + ".join(self.predictors)

    def validate(self, columns) -> None:
        """Fail loudly on a predictor the table does not carry."""
        available = set(columns)
        missing = [p for p in self.predictors if p not in available]
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
