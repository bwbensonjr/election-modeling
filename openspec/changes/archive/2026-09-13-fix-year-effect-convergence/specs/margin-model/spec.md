## ADDED Requirements

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

## MODIFIED Requirements

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
