"""Fitting a variant and producing posterior predictive draws.

A fit is deterministic given the variant, the training races and a recorded
seed, and it reports its sampling diagnostics rather than failing silently
(margin-model spec). The scoring harness only ever asks a fit for draws, so
swapping in a different model family later means implementing `predict_draws`
(design.md, Non-Goals).
"""

from __future__ import annotations

import hashlib
import os
import re
import warnings
from dataclasses import dataclass


def _configure_pytensor_backend() -> str:
    """Fall back to pytensor's Python backend when its C backend cannot build.

    On current macOS toolchains pytensor adds a `-ld64` flag that the linker no
    longer accepts, so every C compilation fails. The models here are small
    enough that the Python backend costs seconds, so falling back is better
    than failing. An explicit PYTENSOR_FLAGS is left alone.
    """
    import contextlib
    import io

    import pytensor

    if os.environ.get("PYTENSOR_FLAGS"):
        return "explicit"
    if not pytensor.config.cxx:
        return "python"
    # The probe prints its own compiler diagnostics on failure; the fallback is
    # expected here, so it is reported once by the caller instead.
    with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
        try:
            from pytensor.link.c.lazylinker_c import CLazyLinker  # noqa: F401
        except Exception:
            pytensor.config.cxx = ""
            return "python"
    return "c"


BACKEND = _configure_pytensor_backend()

import arviz as az  # noqa: E402
import bambi as bmb  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from . import variants  # noqa: E402

DRAWS = 2000
TUNE = 1000
CHAINS = 4

# Diagnostic thresholds (design.md, D10).
RHAT_MAX = 1.01
ESS_MIN = 400.0


def seed_for(variant_name: str, fold: object, definition: str = "current") -> int:
    """A stable seed per fit, so a single fit can be reproduced in isolation.

    Derived from the variant name, the definition and the fold rather than
    drawn from a counter, so it does not depend on how many fits ran before it.
    The definition is part of the key because the same variant under two
    definitions is two different fits, and naming a seed has to identify one.
    """
    digest = hashlib.sha256(f"{variant_name}|{definition}|{fold}".encode()).digest()
    return int.from_bytes(digest[:4], "big") % (2**31 - 1)


class UnidentifiablePredictorError(ValueError):
    """A predictor is constant in the training races, so it has no data."""


@dataclass
class Diagnostics:
    max_rhat: float
    min_ess_bulk: float
    min_ess_tail: float
    divergences: int
    seed: int
    n_train: int

    @property
    def passed(self) -> bool:
        return (
            self.max_rhat <= RHAT_MAX
            and self.min_ess_bulk >= ESS_MIN
            and self.min_ess_tail >= ESS_MIN
            and self.divergences == 0
        )

    def as_row(self) -> dict:
        return {
            "max_rhat": round(float(self.max_rhat), 4),
            "min_ess_bulk": round(float(self.min_ess_bulk), 1),
            "min_ess_tail": round(float(self.min_ess_tail), 1),
            "divergences": int(self.divergences),
            "seed": int(self.seed),
            "n_train": int(self.n_train),
            "diagnostics_passed": bool(self.passed),
        }


def _response_name(model: bmb.Model) -> str:
    """The response variable's name, across bambi versions."""
    term = getattr(model, "response_term", None)
    if term is None:
        term = model.response_component.term
    return term.name


def tidy_parameter(name: str) -> str:
    """Strip the contrast wrapper from a coefficient name.

    `C(incumbent_status, Treatment('No_Incumbent'))[Dem_Incumbent]` is how the
    formula spells the term; `incumbent_status[Dem_Incumbent]` is what it
    means, and is what gets published.
    """
    match = re.fullmatch(r"C\(\s*([^,\)]+?)\s*,.*?\)(\[.*\])?", name)
    if match:
        return match.group(1) + (match.group(2) or "")
    return name


@dataclass
class Fit:
    variant: variants.Variant
    model: bmb.Model
    idata: object
    diagnostics: Diagnostics

    def predict_draws(self, races: pd.DataFrame) -> np.ndarray:
        """Posterior predictive draws of the response, shape (draws, races).

        These are draws of the outcome, not of its mean: interval coverage and
        win probabilities have to account for residual scatter, not only for
        uncertainty about the regression line.
        """
        extra = {}
        if self.variant.group_effects:
            # The fold year is by construction absent from training, so it has
            # no fitted group effect. Drawing it from the group-level
            # hyperprior is what makes the year term predictive rather than
            # undefined: the point estimate stays near the pooled one and the
            # interval widens to admit that the year is unobserved
            # (design.md, D9).
            extra["sample_new_groups"] = True
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            predicted = self.model.predict(
                self.idata,
                kind="response",
                data=variants.prepare(races),
                inplace=False,
                random_seed=self.diagnostics.seed,
                **extra,
            )
        response = predicted.posterior_predictive[_response_name(self.model)]
        stacked = response.stack(sample=("chain", "draw"))
        values = stacked.transpose("sample", ...).values
        if values.shape[1] != len(races):
            raise RuntimeError(
                f"expected {len(races)} predicted races, got {values.shape[1]}"
            )
        return values

    def coefficients(self) -> pd.DataFrame:
        """Posterior summary of the fitted parameters."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            summary = az.summary(self.idata, kind="stats", round_to="none")
        summary = summary.reset_index().rename(columns={"index": "parameter"})
        summary["parameter"] = summary["parameter"].map(tidy_parameter)
        summary.insert(0, "variant", self.variant.name)
        return summary


def fit(
    variant: variants.Variant,
    train: pd.DataFrame,
    fold: object = "full",
    definition: str = "current",
) -> Fit:
    """Fit one variant to one set of races, under one definition."""
    variant.validate(train.columns)
    seed = seed_for(variant.name, fold, definition)
    prepared = variants.prepare(train)

    # A predictor with one value in training carries no information about its
    # effect. Dropping it would let the fit proceed and then predict a holdout
    # race carrying that level as though it were the reference level, which is
    # a confidently wrong answer rather than a missing one.
    constant = [
        column
        for predictor in variant.predictors
        for column in variants.expand(predictor)
        if prepared[column].nunique(dropna=False) < 2
    ]
    if constant:
        raise UnidentifiablePredictorError(
            f"variant {variant.name!r} on fold {fold}: {constant} are constant "
            f"across the {len(prepared)} training races, so their effects cannot "
            "be estimated"
        )

    model = bmb.Model(variant.formula, data=prepared, family="gaussian")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        idata = model.fit(
            draws=DRAWS,
            tune=TUNE,
            chains=CHAINS,
            random_seed=seed,
            progressbar=False,
        )

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        rhat = az.rhat(idata)
        ess_bulk = az.ess(idata, method="bulk")
        ess_tail = az.ess(idata, method="tail")

    def _extreme(dataset, reducer):
        values = [reducer(v.values) for v in dataset.data_vars.values() if v.size]
        return float(reducer(values)) if values else float("nan")

    divergences = 0
    if "sample_stats" in idata and "diverging" in idata.sample_stats:
        divergences = int(idata.sample_stats["diverging"].values.sum())

    diagnostics = Diagnostics(
        max_rhat=_extreme(rhat, np.max),
        min_ess_bulk=_extreme(ess_bulk, np.min),
        min_ess_tail=_extreme(ess_tail, np.min),
        divergences=divergences,
        seed=seed,
        n_train=len(train),
    )
    return Fit(variant=variant, model=model, idata=idata, diagnostics=diagnostics)
