## Purpose

Defines the Bayesian regression on Democratic margin: how a model variant is
declared, how it is fit to a set of races, and what a fitted variant must be
able to produce so that the scoring procedure can evaluate it.

## Requirements

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
from the race table's columns, together with the definition or definitions it
is to be fit under. Adding a variant SHALL NOT require changing the fitting or
scoring procedure.

#### Scenario: A new variant is added by declaration alone

- **WHEN** a variant is declared with a new predictor set
- **THEN** it can be fit and scored through the same interface as `baseline`
- **AND** no change to the fold schedule or metric definitions is required

#### Scenario: A variant naming an absent column is rejected

- **WHEN** a variant declares a predictor that the race table does not carry
- **THEN** the system fails with an error naming the missing column, rather
  than silently dropping the predictor

#### Scenario: Adding a definition does not require changing variants

- **WHEN** a new definition is declared
- **THEN** existing variants can be fit under it without being redeclared
- **AND** a variant incompatible with it fails with a stated reason rather
  than being silently skipped

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

### Requirement: A variant declares the priors its fit uses

A variant SHALL be able to declare the prior distributions its fit uses, and
any prior a variant does not declare SHALL be the fitting library's default.
A declared prior SHALL be scaled to a stated quantity of the training data
rather than left implicit, and the declaration SHALL be published with the
fit that used it.

A hierarchical group effect SHALL carry a declared prior on its group-level
standard deviation. The default auto-scaled prior is not acceptable for a
group effect, because it is derived from the intercept's scale and puts
substantial mass on between-group variation several times larger than the
response's own spread.

#### Scenario: A declared prior is recorded with the fit

- **WHEN** a variant declaring priors is fit
- **THEN** the declaration is published alongside that fit's diagnostics
- **AND** the fit can be reproduced from the published record without reading
  the variant registry

#### Scenario: A group effect without a declared scale is rejected

- **WHEN** a variant declares a hierarchical group effect and no prior for its
  group-level standard deviation
- **THEN** the system fails with an error naming the group effect, rather than
  fitting it under an auto-scaled default

#### Scenario: Undeclared priors leave other variants unchanged

- **WHEN** a variant declaring no priors is fit before and after this
  capability is added
- **THEN** its posterior summaries and holdout predictions are identical

### Requirement: A variant declares the sampler settings its fit uses

A variant SHALL be able to declare the sampler settings its fit uses --- at
minimum the target acceptance probability and the number of tuning
iterations --- and the settings actually used SHALL be recorded with the fit
whether declared or defaulted.

Raising the target acceptance probability is a permitted response to
divergent transitions only when the raised value is published with the result
it produced.

#### Scenario: Settings are published, not only applied

- **WHEN** any fit completes
- **THEN** the target acceptance probability, tuning iterations, draws and
  chains it used are published with its diagnostics
- **AND** a fit reported as passing diagnostics is distinguishable from one
  that passed only at a raised target acceptance probability

#### Scenario: A variant's settings do not leak into other variants

- **WHEN** one variant declares sampler settings and another does not
- **THEN** the second is fit under the defaults
- **AND** the two are still comparable on the same folds and races

### Requirement: A fit reports its sampling diagnostics

Each fit SHALL report convergence and sampling diagnostics, and a fit that
fails them SHALL be surfaced rather than scored silently. The diagnostics
SHALL be accompanied by the sampler settings and prior declaration that
produced them, so that a flagged fit can be reproduced and re-examined from
the published record alone.

#### Scenario: A poorly converged fit is flagged

- **WHEN** any parameter of a fit has an R-hat above the stated threshold, an
  effective sample size below the stated threshold, or the sampler reports
  divergent transitions
- **THEN** the fit is recorded as failing diagnostics
- **AND** the failure appears in the published results alongside the scores
  it produced

#### Scenario: Diagnostics carry what produced them

- **WHEN** a fit's diagnostics are published
- **THEN** they carry the sampler settings and the prior declaration used
- **AND** repeating the fit from those settings, the recorded seed and the
  committed races reproduces the same diagnostics

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

### Requirement: A variant is bound to a data definition

A variant SHALL be fit and predicted under a named data definition, which
supplies the response column and the race set. The pairing of a variant with a
definition SHALL be recorded with the fit, so that no reported result is
ambiguous about which response it was fit against.

#### Scenario: The same variant under two definitions is two results

- **WHEN** a variant is fit under two different definitions
- **THEN** each fit records the definition it used
- **AND** their coefficients and scores are reported as separate results
  rather than merged

#### Scenario: The response comes from the definition, not the variant

- **WHEN** a variant is declared
- **THEN** it names predictors only
- **AND** the response column is supplied by the definition it is fit under

#### Scenario: A variant naming a predictor its definition removes is rejected

- **WHEN** a variant names a predictor that is constant or undefined under its
  definition, such as a no-Democrat indicator under a definition that
  excludes those races
- **THEN** the system fails with an error naming the predictor and the
  definition, rather than fitting a degenerate design matrix

### Requirement: A predictor must be knowable before its fold year's election

Every predictor a variant uses SHALL be derivable from information available
before its fold year's election occurs. A variant SHALL NOT use a quantity
that can only be known once that election has happened.

A predictor that is knowable before the fold year *begins* satisfies this by a
wider margin, and SHALL be treated as the stronger case. A predictor that
becomes knowable only during the fold year SHALL declare an explicit as-of
date, and that date SHALL be published with every fit that uses the predictor,
because a dated predictor's value is meaningless without it and the choice of
date is the difference between a forecast and a postdiction.

#### Scenario: A year effect is specified so the holdout year is predictable

- **WHEN** a variant carries a per-year effect and predicts a year absent from
  its training data
- **THEN** that year's effect is drawn from the distribution the fitted
  year-level effects imply, rather than from a fitted value that does not
  exist
- **AND** the resulting predictive interval widens to reflect that the year's
  effect is unobserved

#### Scenario: A national-environment term uses only prior information

- **WHEN** a variant carries a term describing the national political
  environment of the election year
- **THEN** that term is determined by facts settled before the year's
  elections, such as which party holds the presidency
- **AND** it is not derived from the outcomes of the races being predicted

#### Scenario: A leaking predictor is rejected

- **WHEN** a variant declares a predictor computed from the fold year's own
  results
- **THEN** the system refuses to score it and names the predictor

#### Scenario: A predictor knowable only during the fold year declares a date

- **WHEN** a variant declares a predictor that cannot be derived before the
  fold year begins
- **THEN** the variant declares an as-of date for it
- **AND** a variant that declares such a predictor without an as-of date is
  refused with an error naming the predictor

#### Scenario: The as-of date is before the election it predicts

- **WHEN** a dated predictor is used for a fold
- **THEN** its as-of date falls strictly before that fold's election date
- **AND** a date on or after the election date is refused rather than fit

#### Scenario: The as-of date is published with the result

- **WHEN** a fit using a dated predictor is published
- **THEN** the as-of date is carried in that fit's published record
- **AND** two fits of the same variant at different as-of dates are
  distinguishable in the published outputs

### Requirement: A predictor constant within a grouping level is rejected

A variant carrying a hierarchical group effect SHALL NOT also carry a
predictor that is constant within every level of that grouping factor in the
training races. Such a predictor is a linear combination of the group
indicators, so the group effect and the predictor are not separately
identified, and the fit explores a ridge rather than estimating two effects.

Where a predictor varies within only a small number of grouping levels, the
system SHALL report how many training races carry that variation, since that
count is what identifies the predictor.

#### Scenario: An exactly confounded predictor is refused

- **WHEN** a variant declares a group effect and a predictor whose value is
  constant within every level of that group in a fold's training races
- **THEN** the fit is refused with an error naming both the predictor and the
  grouping factor
- **AND** the refusal is recorded for that fold rather than silently skipped

#### Scenario: A weakly identified predictor is fit but disclosed

- **WHEN** a predictor varies within at least one level of the grouping
  factor, but within fewer than a stated number of training races
- **THEN** the fit proceeds
- **AND** the published diagnostics record the number of races that separate
  the predictor from the group effect

### Requirement: Variants addressing the presidential-year bias are registered

The system SHALL register variants intended to absorb the bias that the
single `pres_elec` term leaves in place, which runs in opposite directions in
presidential and non-presidential years. At minimum these SHALL include an
interaction between presidential-year timing and incumbency, a per-year
effect meeting the knowability requirement, and a signed national-environment
term.

A per-year effect SHALL NOT also carry a predictor determined by the calendar
year, because the year effect contains it. Such a variant is therefore not
nested in the baseline, and its comparison to the baseline SHALL state that
the two differ by more than one term.

#### Scenario: Each bias variant is nested against or comparable to the baseline

- **WHEN** a bias variant is scored
- **THEN** it is compared to the baseline on the same folds, races, and
  definition
- **AND** its effect on the presidential-year and non-presidential-year
  segments is reported separately, not only its pooled effect

#### Scenario: Success is measured on the bias, not only on RMSE

- **WHEN** a bias variant is evaluated
- **THEN** the mean signed error within presidential years and within
  non-presidential years is reported for it and for the baseline
- **AND** a variant that narrows the gap between those two figures is
  identifiable as such even if its pooled RMSE is unchanged

#### Scenario: The year-effect variant carries no calendar-determined term

- **WHEN** the per-year effect variant is fit
- **THEN** it carries no predictor whose value is fixed by the election year
- **AND** its comparison against the baseline is published as a
  non-nested comparison, naming both the term added and the term removed

#### Scenario: A year effect is publishable only if its fits are clean

- **WHEN** the per-year effect variant is scored
- **THEN** its result is reported as adoptable only if every fold under every
  scored definition passes sampling diagnostics
- **AND** if the calibration gain does not survive fits that pass
  diagnostics, that outcome is published rather than the variant being
  quietly retained

### Requirement: The candidate-count variant is registered

The system SHALL register a variant that is the baseline plus
`num_candidates`, so the question deferred from the baseline change is
answered by the existing scoring harness.

#### Scenario: The variant is nested in the baseline

- **WHEN** the candidate-count variant is compared to the baseline
- **THEN** the baseline's predictors are a strict subset of its predictors
- **AND** the only difference is `num_candidates`

#### Scenario: Its result is reported per definition

- **WHEN** the candidate-count variant is scored under a two-party definition
  and under an all-candidate definition
- **THEN** both results are published
- **AND** the report states whether the term carries information the two-party
  response already absorbs

### Requirement: Campaign-finance variants are registered as a contrast sweep

The system SHALL register variants carrying candidate campaign finance, and
they SHALL express the money as a contrast between the race's candidates
rather than as a single candidate's amount, so the predictor has the same
orientation as the response.

At minimum the registered contrasts SHALL include the signed difference in
money between the Democratic and Republican candidates, the Democratic share
of the race's total money, and a ratio on the log scale. Each SHALL be scored
by the existing harness under every scored definition.

#### Scenario: The money contrast is oriented like the response

- **WHEN** a money variant is declared
- **THEN** its predictor increases when the Democratic candidate has the money
  advantage
- **AND** a race with no money advantage in either direction takes a value of
  zero, or the scale's neutral point

#### Scenario: A money measure that does not separate is reported as undecided

- **WHEN** a money variant is compared to the baseline
- **THEN** the paired comparison is reported under the existing rule
- **AND** a measure whose interval spans zero is published as undecided rather
  than being dropped from the writeup

#### Scenario: A zero-money race is distinguished from an unknown-money race

- **WHEN** a race's money is unavailable because a candidate could not be
  matched
- **THEN** the race is not fit as though the candidate raised nothing
- **AND** the variant either excludes the race or carries an explicit
  indicator that the money is unknown

#### Scenario: The money effect is reported by incumbency

- **WHEN** a money variant is scored
- **THEN** its effect is reported within each incumbency segment as well as
  pooled
- **AND** a measure that helps only in open seats is identifiable as such
