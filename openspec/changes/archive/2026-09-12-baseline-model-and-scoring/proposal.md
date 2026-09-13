## Why

The precinct collection pipeline published a training table but nothing
consumes it yet, and the project has no way to say whether one model is
better than another. The README plan calls for defining accuracy measurement
before rebuilding the baseline, because every later step -- demographic
variables, OCPF fundraising, alternative algorithms -- is a comparison
against a fixed yardstick. Without a scoring procedure fixed first, each
later result is argued rather than measured.

The existing model in `mapoli/model/ma_leg_model.R` is fit on the full data
set and never evaluated out of sample. Its companion `margin_model_cv.py`
does evaluate, but with a random 80/20 split, which leaks across the
temporal and district structure the README already identifies as the reason
to split by year: the same district recurs across cycles, so a random split
puts one cycle of a district in training and another in test.

## What Changes

- **Publish a race-grain training table.** Add a `races` stage to the
  collection pipeline that rolls `ma_precinct_training_set.csv.gz` up to one
  row per legislative race: 623 rows spanning 2010 through 2024. `dem_margin`
  is recomputed from summed precinct vote counts; district `PVI_N` is
  recomputed from the summed two-party presidential votes behind each
  precinct's PVI, not averaged from precinct `PVI_N` values. Race attributes
  (`incumbent_status`, `pres_elec`, `is_special`, `num_candidates`,
  `redistricting_cycle`) carry through unchanged.

- **Implement the baseline Bayesian regression** as
  `dem_margin ~ PVI_N + incumbent_status + pres_elec`, Gaussian likelihood,
  fit at race grain with Bambi/PyMC. This reproduces the `stan_glm` model in
  `mapoli/model/ma_leg_model.R` on the newly collected data, and its
  coefficients are checked against a fit on the published district-level
  table to confirm the rollup is definitionally equivalent.

- **Establish a rolling-origin holdout scoring procedure.** For each fold
  year the model trains on every race strictly before it and predicts that
  year's races. Folds are every election year from 2014 through 2024 that
  has contested races: 2014, 2015, 2016, 2017, 2018, 2020, 2021, 2022, 2023,
  2024. 2019 has none. The seed training window is 2010 through 2013 (199
  races); the pooled holdout is 424 races including 24 specials. Holdout
  predictions from all folds are pooled and scored together, with **RMSE in
  margin points as the primary score**.

  Odd-year folds are included deliberately. Restricting folds to even years
  puts only 9 of the 37 special elections into the holdout -- and none in
  2022 or 2024 -- which is too thin to decide anything about `is_special`.
  Odd-year folds are entirely special elections, which is exactly where the
  variable has to earn its place.

- **Report secondary metrics alongside RMSE.** MAE, bias, R-squared, 90%
  posterior-predictive interval coverage, and CRPS, plus win-side accuracy
  and log loss derived from the posterior probability that `dem_margin`
  exceeds zero, since the published use case is race ratings. Every metric
  is also broken out per fold and by office, `is_special`, `pres_elec`, and
  redistricting cycle.

- **Make model variants declarative and comparisons paired.** A variant is a
  named formula over the race table. Comparing two variants scores both on
  the identical fold schedule and holdout races, then reports the RMSE
  difference with a paired bootstrap interval over races, so a difference is
  reported as decided or undecided rather than as a bare number.

- **Answer the first question with the harness:** does adding `is_special`
  to the baseline lower pooled holdout RMSE? The result is recorded as a
  committed scorecard and written up, whichever way it comes out.

### Non-Goals

- No precinct-grain model. The baseline is a replication of the existing
  district-grain model; the precinct table is used only as the source of the
  rollup. Scoring is defined at race grain precisely so a precinct-grain
  model can later be scored against this same scorecard.
- No new predictors beyond those already in the training table. Demographics,
  fundraising, and a finer incumbency variable are later changes that consume
  this harness.
- No non-Bayesian algorithms. Gradient boosting and the rest come later and
  will be scored by the same procedure.
- No win-probability model as a separate fit. Win-side metrics are derived
  from the margin model's posterior, not from a separate logistic model.
- No 2026 forward prediction.

## Capabilities

### New Capabilities

- `race-training-set`: The race-grain rollup of the precinct training table,
  one row per legislative race, carrying the response and predictors the
  district-level model consumes.
- `margin-model`: The Bayesian regression on Democratic margin -- variant
  definitions, fitting, and the posterior predictions a scored model must
  produce.
- `model-scoring`: The rolling-origin holdout procedure, the metric
  definitions, the published scorecard, and the paired comparison between
  two variants.

### Modified Capabilities

None. The precinct capabilities are read-only inputs here; the `races` stage
is additive and changes no existing requirement.

## Impact

- **New code.** A `races` stage in the existing `maprecinct` package, plus a
  new `legmodel` package for fitting and scoring with its own CLI entry
  point. Collection and modeling stay separate: `legmodel` reads committed
  CSVs and never touches the network or the cache.
- **New dependencies.** `bambi`, `pymc`, `arviz`, and `numpy`, matching the
  stack `mapoli/model/margin_model_cv.py` already uses. CRPS is computed
  from posterior draws directly rather than adding a scoring library.
- **New committed data.** `data/race/ma_race_training_set.csv.gz`, and under
  `data/models/` the per-race holdout predictions, the per-fold and pooled
  scorecard, the variant comparison, and the posterior coefficient summaries.
- **Runtime.** Ten folds times two variants is twenty MCMC fits on at most
  569 rows with four or five predictors. Minutes, not hours, so the full
  scoring run is reproducible on demand rather than something to cache.
- **Reference dependency.** `mapoli/model/ma_leg_two_party_2008_2025.csv` is
  read for the coefficient parity check. Its `dem_margin` is wrong for races
  with no Democratic candidate, through the operator precedence bug already
  documented in `docs/schema.md`, so the parity check excludes those races
  rather than treating the reference as authoritative.
- **Risk.** The pooled holdout is 424 races and specials are 24 of them. A
  small RMSE difference on that base may well be undecidable, and the paired
  bootstrap exists so the writeup says so instead of reporting a winner that
  the data does not support.
