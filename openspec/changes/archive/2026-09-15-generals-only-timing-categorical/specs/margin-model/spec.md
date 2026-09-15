## MODIFIED Requirements

### Requirement: A predictor constant within a grouping level is rejected

A variant carrying a hierarchical group effect SHALL NOT also carry a
predictor that is constant within every level of that grouping factor in the
training races. Such a predictor is a linear combination of the group
indicators, so the group effect and the predictor are not separately
identified, and the fit explores a ridge rather than estimating two effects.

A variant SHALL equally not carry two predictors that are exactly collinear in
a fold's training races --- where one is constant within every level of the
other, or is an exact affine function of it. The defect is the same one: two
parameters over one column, not separately identified. It SHALL be refused on
the same terms and reported the same way, so that a collinear pair of fixed
effects is no more admissible than a predictor its own grouping factor spans.

Where a predictor varies within only a small number of grouping levels, the
system SHALL report how many training races carry that variation, since that
count is what identifies the predictor.

This test SHALL be applied per fold against that fold's own training races.
A predictor SHALL NOT be refused, nor admitted, on the grounds of a general
claim about what determines its value; only the training data of the fold
being fit decides it.

#### Scenario: An exactly confounded predictor is refused

- **WHEN** a variant declares a group effect and a predictor whose value is
  constant within every level of that group in a fold's training races
- **THEN** the fit is refused with an error naming both the predictor and the
  grouping factor
- **AND** the refusal is recorded for that fold rather than silently skipped

#### Scenario: Two exactly collinear predictors are refused

- **WHEN** a variant declares two predictors and one is constant within every
  level of the other across a fold's training races
- **THEN** the fit is refused with an error naming both predictors and the
  fold
- **AND** the refusal is recorded for that fold rather than silently skipped
- **AND** a fold whose training races do separate the two is fit normally

#### Scenario: A weakly identified predictor is fit but disclosed

- **WHEN** a predictor varies within at least one level of the grouping
  factor, but within fewer than a stated number of training races
- **THEN** the fit proceeds
- **AND** the published diagnostics record the number of races that separate
  the predictor from the group effect

#### Scenario: The test is per fold, not per variant

- **WHEN** the same variant is fit across several folds
- **THEN** a fold whose training races separate the predictor from the group
  effect is fit
- **AND** a fold whose training races do not is refused
- **AND** the two outcomes are recorded per fold rather than resolved into a
  single verdict for the variant

### Requirement: Variants addressing the presidential-date bias are registered

The system SHALL register variants intended to absorb the bias that the
single `pres_elec` term leaves in place, which runs in opposite directions on
presidential-date and non-presidential-date general elections. At minimum
these SHALL include an interaction between presidential-date timing and
incumbency, a hierarchical timing effect meeting the knowability requirement,
and a term distinguishing midterm electorates by the party holding the
presidency.

`pres_elec` is a property of a race's election date, not of its calendar
year: a special election held in a presidential year but on its own date
carries `False`. It is nonetheless near-constant within a calendar year in the
present record, because no special election has ever fallen on a presidential
general date, so the only races separating it from a calendar-year effect are
special elections. Where a variant carries both `pres_elec` and a grouping
factor, whether the two are separately identified SHALL be decided per fold
from the training races under the requirement above, and SHALL NOT be asserted
from the calendar.

A variant SHALL NOT express ballot timing as two booleans whose joint level
set has to be reconstructed by the reader. Where the distinction between a
presidential ballot and a midterm ballot, and between midterms under each
party's presidency, are both wanted, they SHALL be declared as one categorical
predictor over those levels.

#### Scenario: Each bias variant is nested against or comparable to the baseline

- **WHEN** a bias variant is scored
- **THEN** it is compared to the baseline on the same folds, races, and
  definition
- **AND** its effect on the presidential-date and non-presidential-date
  general-election segments is reported separately, not only its pooled effect

#### Scenario: Success is measured on the bias, not only on RMSE

- **WHEN** a bias variant is evaluated
- **THEN** the mean signed error within presidential-date general elections
  and within non-presidential-date general elections is reported for it and
  for the baseline
- **AND** a variant that narrows the gap between those two figures is
  identifiable as such even if its pooled RMSE is unchanged

#### Scenario: A timing term dropped for confounding is dropped on evidence

- **WHEN** a variant drops `pres_elec` because a grouping factor it carries
  spans it
- **THEN** the count of training races separating the two is published for
  each fold
- **AND** a contrast arm retaining the term under the same prior and sampler
  settings is scored alongside, so the removal rests on a measurement
- **AND** the comparison against the baseline is published as non-nested,
  naming both the term added and the term removed

#### Scenario: A signed midterm term is not carried alongside pres_elec

- **WHEN** a variant distinguishes midterm electorates by the party holding
  the presidency
- **THEN** it declares one categorical over the timing levels rather than a
  signed term alongside `pres_elec`
- **AND** a variant declaring both is refused on every fold whose training
  races leave them collinear

#### Scenario: A year effect is publishable only if its fits are clean

- **WHEN** a hierarchical timing variant is scored
- **THEN** its result is reported as adoptable only if every fold under every
  scored definition passes sampling diagnostics
- **AND** if the calibration gain does not survive fits that pass
  diagnostics, that outcome is published rather than the variant being
  quietly retained

## ADDED Requirements

### Requirement: Ballot timing is a declared categorical

The system SHALL provide a `ballot_timing` predictor: a categorical over the
kind of electorate a race was decided by, with `presidential` as the reference
level. Its levels SHALL be

- `presidential` --- a general election on a presidential ballot,
- `midterm_dem_pres` --- a general election off the presidential ballot, under
  a Democratic president,
- `midterm_gop_pres` --- the same, under a Republican president,
- `special` --- a special election, whatever year or ballot it fell on.

A special election SHALL take the `special` level and SHALL NOT be assigned a
midterm level. No special election in the record has fallen on a presidential
general date, so every one of them carries `pres_elec = False`; assigning them
a midterm level by the president's party would describe them as an electorate
they are not.

The level set SHALL be fixed in advance rather than derived from the races a
fold happens to train on, so that every fold produces a design matrix
accepting any holdout race.

#### Scenario: Timing is one predictor, not two booleans

- **WHEN** `ballot_timing` is declared by a variant
- **THEN** it supplies the whole timing contrast, and the variant declares
  neither `pres_elec` nor a signed midterm term alongside it
- **AND** its coefficients read against a presidential ballot

#### Scenario: A special election takes its own level

- **WHEN** a special election's `ballot_timing` is computed
- **THEN** it is `special`, whichever party held the presidency and whichever
  calendar year it fell in
- **AND** it is not assigned `midterm_dem_pres` or `midterm_gop_pres`

#### Scenario: The level set does not depend on the fold

- **WHEN** a fold's training races carry only some of the levels
- **THEN** the design matrix still carries an indicator for every level
- **AND** a holdout race carrying an absent level is predicted rather than
  rejected

### Requirement: A categorical level absent from training is fit from its prior and disclosed

Where a fold's training races carry no instance of a declared categorical
level, that level's coefficient SHALL be drawn from its prior rather than
estimated, and the fit SHALL proceed. The system SHALL publish, per fold and
per level, how many training races carried it, so that a prediction resting on
a prior is identifiable as one rather than being indistinguishable from a
fitted estimate.

Such a fold SHALL NOT be refused. A level unobserved in training is a
statement about what the record holds, not a defect in the variant, and the
widened interval is the honest expression of it.

#### Scenario: An unobserved level does not refuse the fold

- **WHEN** a fold's training races carry no race at a declared level and its
  holdout carries races at that level
- **THEN** the fit proceeds and every holdout race receives a prediction
- **AND** the unobserved level's coefficient comes from its prior

#### Scenario: The predictive interval widens rather than borrowing

- **WHEN** a holdout race carries a level unobserved in training
- **THEN** its predictive interval reflects the prior's spread on that level
- **AND** the prediction does not silently take another level's fitted value

#### Scenario: Level counts travel with the fit

- **WHEN** a fit using a categorical predictor is published
- **THEN** its diagnostics record the number of training races at each level
- **AND** a level with a count of zero is visible as such
