## Why

The hierarchical year intercept is the best-calibrated variant the sweep
tested -- coverage rises from 0.898 to 0.927 and RMSE falls 0.510
[+0.349, +0.672] -- but **every fold fails sampling diagnostics**: 9 of 10
folds under `current`, 10 of 10 under each other definition, all on divergent
transitions. Its fits are therefore not publishable, and the README carries
this as the first open issue to resolve.

The README's stated next step is wrong, and that is why this needs a change
rather than a patch. It proposes a non-centred parameterisation first, but
bambi already builds group effects non-centred by default
(`Model(..., noncentered=True)`, and the sampler's variable list names
`1|election_year_offset`). Reaching for the standard fix would have produced
no change and no explanation.

Two causes are identified instead, both confirmed against the committed
tables:

1. **The group-SD hyperprior is auto-scaled to five times the response's own
   spread.** Bambi builds `1|election_year ~ Normal(0, HalfNormal(135.03))`
   from the intercept's scale, against a response whose standard deviation is
   25.2 points. A prior putting real mass on a between-year SD of 100+ points,
   estimated from 4 to 14 year groups of which six hold 7 races or fewer
   (2011:3, 2013:7, 2015:3, 2017:5, 2021:2, 2023:1), leaves the upper tail of
   `sigma_year` almost entirely prior-driven.

2. **`pres_elec` is collinear with the year grouping.** `pres_elec` is a
   property of the calendar year, so a free per-year intercept absorbs it
   almost exactly: across all 610 races under the adopted definition it varies
   within a year only in 2016 and 2020, on 8 races total. In the early folds
   the confounding is *exact* -- fold 2014 trains on 2010-2013, where
   `pres_elec` is precisely the 2012 indicator. Those are the folds with the
   worst diagnostics: 729 divergences and an R-hat of 1.18 on fold 2014, 392
   and 1.09 on fold 2017, against 2 and 1.0036 on fold 2022.

The divergence counts track the diagnosis rather than the sample size: they
fall from the hundreds to single digits once the training window holds enough
years to identify a between-year SD and enough within-year variation to
separate `pres_elec` from it.

Both causes are properties of how the variant is *specified*, not of the data
it is fit to, so both are fixable. Fixing them matters beyond this one
variant: the priors here are bambi's auto-scaled defaults everywhere, and the
year-level collinearity applies equally to `national_env`, the term the sweep
adopted. Any later hierarchical structure -- district effects, a
year-by-office interaction -- inherits the same geometry.

## What Changes

- **Declare priors instead of inheriting auto-scaled ones.** A variant may
  declare priors for its group effects, scaled to the response rather than to
  the intercept, and the declaration is published with the fit. The default
  for a hierarchical intercept becomes a half-normal on the group SD scaled to
  the response's own spread, which encodes what is actually believed -- that
  year-to-year swings are a few points, not a hundred.

- **Make sampler settings a declared, recorded property of a variant.**
  `target_accept` and `tune` are fixed in `fit.py` today and appear in no
  output. A variant may set them, the values used are written to
  `fit_diagnostics.csv`, and a fit is reproducible from the published record
  alone. Raising `target_accept` is a legitimate response to divergences only
  if the setting travels with the result.

- **Settle whether a year-level predictor may coexist with a year intercept.**
  The candidate resolution is that `baseline_year` drops `pres_elec`, because
  the year intercept already contains it and the 8 races that separate them
  cannot identify it. This makes `baseline_year` no longer nested in
  `baseline`, which the comparison machinery and the writeups must state
  rather than paper over. The alternative -- keep the term and let the
  hierarchical prior do the separating -- is scored too, so the choice is
  evidence rather than assertion.

- **Refuse the silent version of this failure.** A variant whose predictor is
  constant within the levels of its own grouping factor is flagged with both
  names, in the same spirit as the existing constant-predictor and leaking-
  predictor checks. Fold 2014 fit a model whose design matrix could not
  separate two of its terms and reported only "divergences".

- **Re-score `baseline_year` and publish the outcome, including a negative
  one.** The variant is adopted only if every fold under every scored
  definition passes diagnostics *and* the calibration gain survives. If the
  gain was an artifact of a badly-sampled posterior, that is the finding, and
  the README's open issue closes as "withdrawn" rather than "fixed".

- **BREAKING** for published outputs, confined to one variant:
  `baseline_year`'s rows in `scorecard.csv`, `variant_comparison.csv`,
  `coefficients.csv`, `fit_diagnostics.csv` and `holdout_predictions.csv.gz`
  are recomputed and will not match the committed ones. Every other variant's
  numbers are unchanged by construction -- a variant that declares no priors
  and no sampler settings keeps today's defaults and today's seeds -- and the
  change is not complete until that has been verified rather than assumed.

### Non-Goals

- No new predictors, no new definitions, no change to the fold schedule, the
  metric set or the pooling rule. The yardstick does not move while a fit is
  being repaired against it.
- No change to `baseline_national_env`, which passes diagnostics on every fold
  and remains the variant to use until this one is cleared.
- No switch of sampler backend (`nutpie`, `numpyro`) and no new dependency.
  If the fits still diverge after the specification is corrected, that is a
  finding to report, not a reason to change samplers inside this change.
- No re-collection and no rebuild of the training tables.

## Capabilities

### Modified Capabilities

- `margin-model`: a variant may declare the priors and sampler settings its
  fit uses, and both are recorded with the fit; a predictor constant within
  the levels of the variant's own grouping factor is rejected rather than fit;
  the year-effect variant's declared structure is fixed by this change.
- `model-scoring`: fit diagnostics publish the sampler settings and prior
  declaration that produced them, so a flagged fit can be reproduced and
  re-examined from the committed outputs; a variant not nested in `baseline`
  is compared and reported as such.

## Impact

- **Code.** `legmodel/variants.py` for the prior and sampler declarations on
  `Variant` and the grouping-collinearity check; `legmodel/fit.py` to pass
  them through to `bmb.Model` and `model.fit` and to record them in
  `Diagnostics`; `legmodel/score.py` for the added diagnostic columns;
  `legmodel/compare.py` where nesting is assumed.
- **Data.** `fit_diagnostics.csv` gains columns (`target_accept`, `tune`,
  `draws`, `chains`, and the group-prior declaration). `baseline_year`'s rows
  in the five published model outputs are recomputed.
- **Docs.** `docs/scoring.md` for the recorded sampler settings;
  `docs/variant_results.md` for the corrected `baseline_year` result and for
  the nesting caveat; `README.md`'s open issue replaced by its resolution,
  including the correction that the non-centred fix was already in place.
- **Runtime.** Ten folds times four definitions for one variant, plus the
  contrast arm, on at most 570 rows. Minutes, at a higher `target_accept`.
- **Risk.** The most likely negative outcome is that a correctly specified
  year effect is a *smaller* improvement than the badly-sampled one, because
  divergences concentrated in the early folds inflate predictive spread and
  spread is what coverage rewards. The change is written so that this result
  is publishable rather than a failure.
- **Dependency.** None added.
