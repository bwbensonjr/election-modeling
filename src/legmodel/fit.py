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
# pymc's own NUTS default. Recorded rather than passed: a variant declaring no
# setting is sampled by exactly the call that produced the committed results,
# so its published numbers stay reproducible, while the value it ran under is
# still written out (margin-model spec, "Settings are published, not only
# applied").
DEFAULT_TARGET_ACCEPT = 0.8

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


def _bambi_prior(declared: "variants.Prior") -> bmb.Prior:
    """Translate a declared prior into the fitting library's own type."""
    params = {
        name: _bambi_prior(value) if isinstance(value, variants.Prior) else value
        for name, value in declared.params
    }
    return bmb.Prior(declared.distribution, **params)


def _bambi_priors(variant: "variants.Variant") -> dict | None:
    """The priors to hand the model, or None to keep the library's defaults.

    Returning None rather than an empty mapping matters: it is the difference
    between "this variant declares nothing" and "this variant declares nothing
    for any term", and only the first reproduces a published result unchanged.
    """
    if not variant.priors:
        return None
    return {term: _bambi_prior(prior) for term, prior in variant.priors.items()}


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
    # What the sampler actually ran under, whether declared or defaulted. A
    # passing fit that needed a raised target acceptance is a different claim
    # from one that passed at the default, and the published record has to be
    # able to tell them apart.
    target_accept: float = DEFAULT_TARGET_ACCEPT
    tune: int = TUNE
    draws: int = DRAWS
    chains: int = CHAINS
    group_prior: str = ""
    # The as-of date of any dated predictor the variant carries. Published so
    # that no metric is ambiguous about the point in time its predictors were
    # measured at (model-scoring spec, "A dated predictor's as-of date travels
    # with the scores").
    as_of: str = ""
    # Training races carrying within-group variation for a predictor that is
    # nearly spanned by the variant's grouping factor. Empty when the variant
    # has no group effect, or when nothing is close to confounded.
    separating_races: str = ""
    # Set when the fold was refused before sampling, so a fold that was never
    # fit is distinguishable in the published record from one that was fit and
    # sampled badly.
    refused_reason: str = ""

    @property
    def passed(self) -> bool:
        if self.refused_reason:
            return False
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
            "target_accept": float(self.target_accept),
            "tune": int(self.tune),
            "draws": int(self.draws),
            "chains": int(self.chains),
            # Spelled out rather than left blank: an empty cell in a published
            # CSV reads as missing data, and "this fit used the library's own
            # priors" is a fact about the fit, not an absence of one.
            "group_prior": self.group_prior or "library defaults",
            "as_of": self.as_of or "not dated",
            "separating_races": self.separating_races or "none",
            "refused_reason": self.refused_reason,
        }


def refused(
    variant: "variants.Variant",
    fold: object,
    definition: str,
    n_train: int,
    reason: str,
) -> Diagnostics:
    """Diagnostics for a fold whose fit was refused before it was sampled.

    A refusal is not a sampling failure and should not read like one: the
    sampling fields are absent rather than zero, and the reason travels with
    the row (margin-model spec, "An exactly confounded predictor is refused").
    """
    nan = float("nan")
    return Diagnostics(
        max_rhat=nan,
        min_ess_bulk=nan,
        min_ess_tail=nan,
        divergences=0,
        seed=seed_for(variant.name, fold, definition),
        n_train=n_train,
        target_accept=(
            DEFAULT_TARGET_ACCEPT
            if variant.target_accept is None
            else variant.target_accept
        ),
        tune=TUNE if variant.tune is None else variant.tune,
        group_prior=variant.prior_declaration,
        as_of=variant.as_of,
        refused_reason=reason,
    )


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
            # The fold's own grouping level is by construction absent from
            # training, so it has no fitted group effect. Drawing it from the
            # group-level hyperprior is what makes the term predictive rather
            # than undefined: the point estimate stays near the pooled one and
            # the interval widens to admit that the level is unobserved
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

    # A predictor the grouping factor already contains is a specification
    # error, not a sampling one: the fit would return numbers describing a
    # ridge. Checked per fold, because the confounding is exact only in the
    # early windows (design.md, D5).
    separating = variants.check_grouping(variant, prepared)

    model = bmb.Model(
        variant.formula,
        data=prepared,
        family="gaussian",
        priors=_bambi_priors(variant),
    )
    target_accept = variant.target_accept
    tune = TUNE if variant.tune is None else variant.tune
    # A variant declaring no target acceptance is sampled by exactly the call
    # that produced the committed results, rather than by the same call with
    # the default written out, so its published numbers stay reproducible.
    sampler_kwargs = {} if target_accept is None else {"target_accept": target_accept}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        idata = model.fit(
            draws=DRAWS,
            tune=tune,
            chains=CHAINS,
            random_seed=seed,
            progressbar=False,
            **sampler_kwargs,
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
        target_accept=(
            DEFAULT_TARGET_ACCEPT if target_accept is None else target_accept
        ),
        tune=tune,
        draws=DRAWS,
        chains=CHAINS,
        group_prior=variant.prior_declaration,
        as_of=variant.as_of,
        separating_races=", ".join(
            f"{term}={count}" for term, count in sorted(separating.items())
        ),
    )
    return Fit(variant=variant, model=model, idata=idata, diagnostics=diagnostics)
