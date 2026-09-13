## Purpose

Defines how a margin model's accuracy is measured: the rolling-origin
holdout schedule, the metrics computed over pooled holdout predictions, the
published scorecard, and how two variants are compared so that a difference
is reported as decided or undecided.

## ADDED Requirements

### Requirement: Evaluation is rolling-origin with an expanding training window

The system SHALL evaluate a variant by fitting it once per fold year on every
race strictly preceding that year and predicting only the races held in that
year. The training window SHALL expand with each successive fold rather than
sliding.

#### Scenario: A fold trains only on prior years

- **WHEN** the fold for year `Y` is run
- **THEN** the training races are every race in the table with
  `election_year` less than `Y`
- **AND** the holdout races are every race in the table with
  `election_year` equal to `Y`
- **AND** no race in year `Y` or later appears in the training set

#### Scenario: Splitting by year rather than randomly

- **WHEN** folds are constructed
- **THEN** every race of a given year falls on the same side of the split
- **AND** a district that recurs across cycles never has one of its races in
  training and another in the same fold's holdout

### Requirement: The fold schedule covers every election year from 2014 onward

The fold years SHALL be 2014, 2015, 2016, 2017, 2018, 2020, 2021, 2022,
2023, and 2024. 2019 SHALL NOT be a fold because the table contains no
contested races for it. Races from 2010 through 2013 SHALL form the seed
training window and SHALL NOT be scored.

#### Scenario: Odd years are scored

- **WHEN** the fold schedule is constructed
- **THEN** 2015, 2017, 2021, and 2023 are fold years
- **AND** their holdout races, which are entirely special elections, enter
  the pooled holdout

#### Scenario: A year with no races produces no fold

- **WHEN** an otherwise eligible year contains no races in the table
- **THEN** no fold is created for it
- **AND** its absence is recorded in the published scorecard rather than
  passing unremarked

#### Scenario: Seed years are training-only

- **WHEN** the fold schedule is run
- **THEN** no race from 2010 through 2013 appears in any holdout set

### Requirement: Holdout predictions from all folds are pooled and scored together

The primary score SHALL be computed over the union of every fold's holdout
predictions, with each race weighted equally regardless of which fold
produced it or how many races that fold held out.

#### Scenario: Each holdout race is predicted exactly once

- **WHEN** a scoring run completes
- **THEN** every race in a fold year has exactly one holdout prediction
- **AND** no race in the seed window has any

#### Scenario: Pooling is by race, not by fold

- **WHEN** the pooled score is computed
- **THEN** it is computed from the full set of holdout races directly
- **AND** not as an average of the per-fold scores, which would over-weight
  the one-race and two-race odd-year folds

### Requirement: RMSE in margin points is the primary score

The primary accuracy score SHALL be the root mean squared error between
predicted and observed `dem_margin` over the pooled holdout races, expressed
in percentage points of margin.

#### Scenario: RMSE is reported for every scored variant

- **WHEN** a variant is scored
- **THEN** its pooled holdout RMSE is reported
- **AND** the number of holdout races it was computed over is reported with it

### Requirement: Secondary metrics accompany the primary score

Each scored variant SHALL also report mean absolute error, mean signed error
as a bias measure, the coefficient of determination, the empirical coverage
of its 90% posterior predictive intervals, and the continuous ranked
probability score. Because the published use of the model is race ratings, it
SHALL also report win-side accuracy and log loss from the posterior
probability that `dem_margin` exceeds zero.

#### Scenario: Calibration is measured, not assumed

- **WHEN** a variant is scored
- **THEN** the fraction of holdout races whose observed margin fell inside
  the 90% posterior predictive interval is reported
- **AND** a variant whose coverage departs from 90% is identifiable as
  miscalibrated even if its RMSE is competitive

#### Scenario: Win-side metrics come from the margin posterior

- **WHEN** win-side accuracy and log loss are computed
- **THEN** each race's predicted probability is the posterior predictive
  probability that `dem_margin` exceeds zero
- **AND** the observed outcome is whether the observed `dem_margin` exceeds
  zero

### Requirement: Scores are broken out per fold and per segment

Every metric SHALL be reported for the pooled holdout, for each fold year,
and for each level of `office`, `is_special`, `pres_elec`,
`redistricting_cycle`, and `no_dem_candidate`, so that a pooled result can be
traced to where the model succeeds or fails.

#### Scenario: Special elections are scored separately

- **WHEN** a variant is scored
- **THEN** its RMSE over the holdout special elections is reported apart from
  its RMSE over the holdout general elections
- **AND** the race count behind each is reported

#### Scenario: Races with no Democratic candidate are visible as a segment

- **WHEN** a variant is scored
- **THEN** its RMSE over holdout races with no Democratic candidate is
  reported apart from the rest
- **AND** the pooled figure discloses how much of its squared error those
  races contribute

#### Scenario: Small segments are reported with their counts

- **WHEN** a segment contains fewer races than a stated minimum
- **THEN** its metrics are still reported
- **AND** the row is marked as resting on a small sample

### Requirement: Two variants are compared on identical folds and races

Comparing two variants SHALL score both on the same fold schedule and the
same holdout races, and SHALL report the difference in pooled RMSE together
with a per-race paired comparison.

#### Scenario: The comparison is paired by race

- **WHEN** two variants are compared
- **THEN** the difference is computed from the two variants' errors on the
  same set of races
- **AND** a race dropped from one variant's holdout for any reason is dropped
  from the other's before comparing

#### Scenario: The comparison reports an interval, not only a point

- **WHEN** the RMSE difference between two variants is reported
- **THEN** it is accompanied by an interval obtained by resampling the
  holdout races
- **AND** the comparison is labelled undecided when that interval contains
  zero

#### Scenario: A variant is not declared better on a pooled difference alone

- **WHEN** one variant has a lower pooled RMSE but the interval spans zero
- **THEN** the published conclusion states that the data does not separate
  them, rather than naming a winner

### Requirement: The is_special comparison is run and published

The system SHALL run the comparison between the `baseline` and
`baseline_special` variants under this procedure and publish its result,
whichever direction it falls.

#### Scenario: The result is recorded either way

- **WHEN** the `is_special` comparison completes
- **THEN** the scorecard records both variants' pooled and segmented metrics,
  the paired difference, and its interval
- **AND** a written conclusion accompanies it, including when the conclusion
  is that adding `is_special` does not measurably help

#### Scenario: The special-election segment is examined explicitly

- **WHEN** the `is_special` comparison is published
- **THEN** the two variants' RMSE over holdout special elections is reported
  alongside the pooled figures
- **AND** the count of holdout special elections is stated, so the weight of
  the evidence is visible

### Requirement: Scoring runs are reproducible and published

A scoring run SHALL be reproducible from committed inputs and recorded seeds,
and its outputs SHALL be committed as versioned files.

#### Scenario: A rerun reproduces the scorecard

- **WHEN** a scoring run is repeated from the same committed race table with
  the same recorded seeds
- **THEN** the published metrics are identical

#### Scenario: Per-race predictions are published, not only summaries

- **WHEN** a scoring run completes
- **THEN** the per-race holdout predictions are published, carrying the race
  identity, the fold, the variant, the point prediction, the interval bounds,
  the win probability, and the observed margin
- **AND** any metric in the scorecard can be recomputed from them

#### Scenario: Fit diagnostics travel with the scores

- **WHEN** a fold's fit fails its sampling diagnostics
- **THEN** the scorecard marks the affected fold and variant
- **AND** the pooled result discloses that it includes a fold whose fit was
  flagged
