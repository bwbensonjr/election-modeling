## Purpose

Defines the Bayesian regression on Democratic margin: how a model variant is
declared, how it is fit to a set of races, and what a fitted variant must be
able to produce so that the scoring procedure can evaluate it.

## ADDED Requirements

### Requirement: The baseline variant reproduces the established model

The system SHALL provide a variant named `baseline` whose structure is
`dem_margin ~ PVI_N + incumbent_status + pres_elec` with a Gaussian
likelihood and an identity link, fit at race grain. This matches the margin
model in `mapoli/model/ma_leg_model.R`.

#### Scenario: Baseline structure is fixed

- **WHEN** the `baseline` variant is fit
- **THEN** its predictors are exactly `PVI_N`, `incumbent_status`, and
  `pres_elec`
- **AND** `incumbent_status` enters as a categorical with `No_Incumbent` as
  the reference level, so the Democratic and Republican incumbency
  coefficients are read against an open seat

#### Scenario: Baseline coefficients match a fit on the reference table

- **WHEN** the `baseline` variant is fit on the published race table and
  separately on `mapoli`'s district-level table restricted to the same races
- **THEN** each posterior mean coefficient agrees within a stated tolerance
- **AND** any coefficient outside tolerance is reported rather than accepted

### Requirement: Variants are declared, not hard-coded

A model variant SHALL be declared as a name plus a set of predictors drawn
from the race table's columns. Adding a variant SHALL NOT require changing
the fitting or scoring procedure.

#### Scenario: A new variant is added by declaration alone

- **WHEN** a variant is declared with a new predictor set
- **THEN** it can be fit and scored through the same interface as `baseline`
- **AND** no change to the fold schedule or metric definitions is required

#### Scenario: A variant naming an absent column is rejected

- **WHEN** a variant declares a predictor that the race table does not carry
- **THEN** the system fails with an error naming the missing column, rather
  than silently dropping the predictor

### Requirement: The is_special variant is the baseline plus one term

The system SHALL provide a variant named `baseline_special` that is exactly
the `baseline` predictors plus `is_special`, so the two differ by one term
and their comparison isolates that term.

#### Scenario: Variants are nested

- **WHEN** `baseline` and `baseline_special` are compared
- **THEN** the predictor set of `baseline` is a strict subset of
  `baseline_special`
- **AND** the only difference is `is_special`

### Requirement: A fit is reproducible

Fitting SHALL be deterministic given the variant, the training races, and a
recorded random seed. The seed used for each fit SHALL be published with its
results.

#### Scenario: Repeating a fit reproduces its results

- **WHEN** the same variant is fit twice on the same races with the same
  recorded seed
- **THEN** the posterior summaries and the holdout predictions are identical

### Requirement: A fit reports its sampling diagnostics

Each fit SHALL report convergence and sampling diagnostics, and a fit that
fails them SHALL be surfaced rather than scored silently.

#### Scenario: A poorly converged fit is flagged

- **WHEN** any parameter of a fit has an R-hat above the stated threshold, an
  effective sample size below the stated threshold, or the sampler reports
  divergent transitions
- **THEN** the fit is recorded as failing diagnostics
- **AND** the failure appears in the published results alongside the scores
  it produced

### Requirement: A fitted variant produces a predictive distribution per race

For each race it predicts, a fitted variant SHALL produce posterior
predictive draws of `dem_margin`, not only a point estimate, so that interval
coverage, probabilistic scores, and win probabilities can be computed.

#### Scenario: Point prediction is the posterior predictive mean

- **WHEN** a point prediction is required for a race
- **THEN** it is the mean of that race's posterior predictive draws

#### Scenario: Win probability is derived from the same draws

- **WHEN** a win probability is required for a race
- **THEN** it is the fraction of that race's posterior predictive draws with
  `dem_margin` greater than zero
- **AND** no separate classification model is fit

### Requirement: Prediction never consults the held-out outcome

Predicting a race SHALL depend only on that race's predictors and on the
fitted model. The held-out `dem_margin` SHALL NOT be available to fitting or
to prediction.

#### Scenario: Holdout outcomes are withheld from fitting

- **WHEN** a variant is fit for a fold
- **THEN** the training data contains no race from the fold's holdout year or
  any later year
