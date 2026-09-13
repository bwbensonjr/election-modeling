## Purpose

Defines how a margin model's accuracy is measured: the rolling-origin
holdout schedule, the metrics computed over pooled holdout predictions, the
published scorecard, and how two variants are compared so that a difference
is reported as decided or undecided.

## Requirements

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

Every metric SHALL be reported for the pooled holdout, for each fold year, and
for each level of `office`, `is_special`, `pres_elec`, `redistricting_cycle`,
`no_dem_candidate`, and whether the race was admitted on a write-in, so that a
pooled result can be traced to where the model succeeds or fails. A segment
that a definition empties SHALL be reported as empty rather than omitted.

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

#### Scenario: Presidential-year bias is visible as a segment

- **WHEN** a variant is scored
- **THEN** the mean signed error within presidential years and within
  non-presidential years is reported separately
- **AND** the gap between them is reported, since it is the quantity a bias
  variant sets out to close

#### Scenario: Small segments are reported with their counts

- **WHEN** a segment contains fewer races than a stated minimum
- **THEN** its metrics are still reported
- **AND** the row is marked as resting on a small sample

#### Scenario: A segment emptied by a definition is reported as empty

- **WHEN** a definition admits no races in a segment, such as no-Democrat
  races under a two-party definition
- **THEN** the segment appears with a count of zero
- **AND** it is not silently dropped from the scorecard

### Requirement: Two variants are compared on identical folds and races

Comparing two variants SHALL score both on the same fold schedule and the
same holdout races, and SHALL report the difference in pooled RMSE together
with a per-race paired comparison. Where the two variants are not nested ---
where one adds a term and also removes one --- the comparison SHALL state
that, so the difference is not read as the effect of a single term.

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

#### Scenario: A non-nested comparison is labelled as such

- **WHEN** two compared variants do not stand in a subset relation on their
  predictors
- **THEN** the published comparison names the terms added and the terms
  removed
- **AND** it is not described as isolating a single term

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

A scoring run SHALL be reproducible from committed inputs, a named definition,
recorded seeds, and the recorded sampler settings and prior declarations, and
its outputs SHALL be committed as versioned files.

#### Scenario: A rerun reproduces the scorecard

- **WHEN** a scoring run is repeated from the same committed race table, the
  same definition, the same recorded seeds and the same recorded sampler
  settings
- **THEN** the published metrics are identical

#### Scenario: Per-race predictions are published, not only summaries

- **WHEN** a scoring run completes
- **THEN** the per-race holdout predictions are published, carrying the race
  identity, the definition, the fold, the variant, the point prediction, the
  interval bounds, the win probability, and the observed response
- **AND** any metric in the scorecard can be recomputed from them

#### Scenario: Definition-comparison outputs are published alongside

- **WHEN** two definitions are compared
- **THEN** the comparison is committed as a versioned file carrying the paired
  difference, its interval, the label, the shared and exclusive race counts,
  and the response-shift summary

#### Scenario: Fit diagnostics travel with the scores

- **WHEN** a fold's fit fails its sampling diagnostics
- **THEN** the scorecard marks the affected definition, fold, and variant
- **AND** the pooled result discloses that it includes a fold whose fit was
  flagged

#### Scenario: Sampler settings travel with the diagnostics

- **WHEN** the fit diagnostics are published
- **THEN** each row carries the sampler settings and the prior declaration
  that produced it
- **AND** a reader can tell whether a passing fit required settings different
  from the defaults

### Requirement: A rescoring reports what it changed and what it did not

Rescoring one variant SHALL leave every other variant's published metrics
unchanged, and the run SHALL verify that rather than assert it. Where a
rescoring does change another variant's numbers, the change SHALL be reported
with the reason, since the scorecard is the yardstick later work is measured
against.

#### Scenario: An untouched variant is verified unchanged

- **WHEN** one variant is rescored and its rows in the published outputs are
  replaced
- **THEN** every other variant's rows under every definition are byte-for-byte
  identical to the committed ones
- **AND** any difference is reported with the variant, the definition and the
  fold it occurred on

#### Scenario: A superseded result is not silently overwritten

- **WHEN** a variant's published result is replaced by a rescoring under a
  corrected specification
- **THEN** the writeup states that the earlier figures were produced by fits
  that failed diagnostics, and are superseded rather than reproduced

### Requirement: A scoring run is performed under a named definition

Every scoring run SHALL be performed under exactly one data definition, which
determines the races eligible for training and holdout and the response scored
against. The definition SHALL be recorded in every output the run produces.

#### Scenario: Scores are never reported without their definition

- **WHEN** a scorecard row is published
- **THEN** it names the definition as well as the variant and the fold
- **AND** a metric from one definition cannot be read as comparable to one
  from another without the comparison procedure below

#### Scenario: The fold schedule is unchanged by the definition

- **WHEN** a definition is applied
- **THEN** the fold years remain every election year from 2014 through 2024
  that the definition admits races in
- **AND** a fold year the definition empties is recorded as skipped rather
  than omitted silently

#### Scenario: Holdout counts are published per definition

- **WHEN** a scoring run completes
- **THEN** the pooled holdout race count, the holdout special-election count,
  and the smallest training fold size under that definition are reported
- **AND** a definition that shrinks the holdout is visible as having done so

### Requirement: Two definitions are compared on the intersection of their holdouts

Comparing two definitions SHALL score each on its own holdout, then compare
them on the races both hold out, and SHALL report separately what each
definition admits that the other does not. A pooled score from one
definition's holdout SHALL NOT be reported as a difference against the
other's.

#### Scenario: The comparison is paired on shared races

- **WHEN** two definitions are compared
- **THEN** the difference is computed over the races present in both holdout
  sets
- **AND** it is accompanied by an interval obtained by resampling those
  shared races, and labelled undecided when that interval contains zero

#### Scenario: What each side drops is reported, not hidden

- **WHEN** two definitions are compared
- **THEN** the races each admits that the other excludes are reported with
  their count and the reason for exclusion
- **AND** each definition's score over its own exclusive races is reported, so
  the cost of narrowing the race set is visible

#### Scenario: Training sets differing is disclosed

- **WHEN** two definitions are compared on shared holdout races
- **THEN** the report states that the two models were also trained on
  different race sets
- **AND** the difference is not described as isolating the response
  definition alone

### Requirement: A definition comparison discloses how far the response moved

Because two definitions may measure different responses on the same race, a
comparison SHALL report the distribution of the difference between the two
responses over the shared holdout races, so that a change in error is not
read as a change in accuracy when part of it is the target moving.

#### Scenario: Response shift accompanies the error difference

- **WHEN** two definitions with different response columns are compared
- **THEN** the median and the tail of the per-race response difference over
  the shared races are reported alongside the RMSE difference
- **AND** the count of shared races whose response moved by more than a stated
  number of points is reported

#### Scenario: A comparison of two definitions sharing a response says so

- **WHEN** two definitions differ only in eligibility and share a response
  column
- **THEN** the response shift over the shared races is zero
- **AND** the comparison is reported as isolating the eligibility rule

### Requirement: The open questions are answered and published

The system SHALL run the comparisons needed to answer the deferred data and
variant questions and publish each result, whichever direction it falls: the
two-party response against the current one, each candidate write-in threshold
against the others, each no-Democrat treatment against the others, each
presidential-year bias variant against the baseline, and the candidate-count
variant against the baseline.

#### Scenario: Each question's answer names its evidence

- **WHEN** a question's result is published
- **THEN** it states the pooled difference, its interval, the holdout counts
  behind it, and the segment breakdown that motivated the question
- **AND** every figure in the writeup is present in a committed scorecard or
  comparison file

#### Scenario: Write-in thresholds are reported as a sweep, not a single test

- **WHEN** the write-in threshold is evaluated
- **THEN** the races admitted and the resulting scores are reported at each
  candidate threshold
- **AND** the threshold at which the admitted races stop changing is
  identified, so a threshold is not chosen from a range where it makes no
  difference

#### Scenario: The no-Democrat segment is reported against its own baseline

- **WHEN** a no-Democrat treatment is evaluated
- **THEN** its RMSE and interval coverage over holdout races with no
  Democratic candidate are reported against the published baseline figures
  for that segment
- **AND** a treatment that only removes those races from scoring is reported
  as having removed them rather than as having improved on them

#### Scenario: An undecided result is published as undecided

- **WHEN** a comparison's interval contains zero
- **THEN** the published conclusion states that the data does not separate the
  alternatives
- **AND** any subsequent adoption is attributed to a stated principle rather
  than to the measurement
