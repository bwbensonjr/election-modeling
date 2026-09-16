## MODIFIED Requirements

### Requirement: Secondary metrics accompany the primary score

Each scored variant SHALL also report mean absolute error, mean signed error
as a bias measure, the coefficient of determination, the empirical coverage
of its 90% posterior predictive intervals, and the continuous ranked
probability score. Because the published use of the model is race ratings, it
SHALL also report win-side accuracy, Brier score, and log loss from the
posterior probability that `dem_margin` exceeds zero, together with probability
calibration summaries whose bins and counts are published.

#### Scenario: Calibration is measured, not assumed

- **WHEN** a variant is scored
- **THEN** the fraction of holdout races whose observed margin fell inside
  the 90% posterior predictive interval is reported
- **AND** a variant whose coverage departs from 90% is identifiable as
  miscalibrated even if its RMSE is competitive

#### Scenario: Win-side metrics come from the margin posterior

- **WHEN** win-side accuracy, Brier score, and log loss are computed
- **THEN** each race's predicted probability is the posterior predictive
  probability that `dem_margin` exceeds zero
- **AND** the observed outcome is whether the observed `dem_margin` exceeds
  zero

#### Scenario: Probability calibration retains its sample size

- **WHEN** predicted win probabilities are grouped for a calibration summary
- **THEN** each group reports its mean forecast probability, observed win
  frequency, and race count
- **AND** an empty or small group is not presented as precise evidence

### Requirement: Two variants are compared on identical folds and races

Comparing two variants SHALL score both on the same fold schedule and the
same holdout races, and SHALL report the difference in pooled race-weighted
RMSE together with a paired comparison. Its uncertainty interval SHALL
resample whole election-date clusters, preserving the paired races and their
shared election environment, rather than treating races held on one date as
independent evidence. Where the two variants are not nested --- where one adds
a term and also removes one --- the comparison SHALL state that, so the
difference is not read as the effect of a single term.

A composite variant, which predicts different races from different component
fits, SHALL be comparable to a single-fit variant on this procedure provided
every race in the comparison is predicted exactly once by exactly one
component. A comparison involving a composite variant SHALL name the
components and state which races each one predicted.

#### Scenario: The comparison is paired by race

- **WHEN** two variants are compared
- **THEN** the point difference is computed over the same races for both
  variants
- **AND** a race dropped from one variant's holdout for any reason is dropped
  from the other's before comparing

#### Scenario: A composite variant is compared race by race

- **WHEN** a composite variant is compared to a single-fit variant
- **THEN** each race's error for the composite comes from whichever component
  predicted it
- **AND** the published comparison names the components and the race
  population each one covered
- **AND** it is labelled non-nested, since the two arms do not stand in a
  subset relation on their predictors

#### Scenario: The comparison reports an interval, not only a point

- **WHEN** an interval for a paired RMSE difference is computed
- **THEN** each resample selects election dates and carries all paired races
  held on each selected date together
- **AND** the point estimate remains the RMSE difference over equally weighted
  races rather than an equally weighted mean of fold scores

#### Scenario: One election date cannot establish comparison uncertainty

- **WHEN** a comparison segment contains paired races from fewer than two
  election dates
- **THEN** its clustered interval is reported as not estimable
- **AND** the segment is labelled undecided rather than receiving a degenerate
  interval from repeated copies of the same election

#### Scenario: A variant is not declared better on a pooled difference alone

- **WHEN** one variant has a lower pooled RMSE but the clustered interval spans
  zero
- **THEN** the published conclusion states that the election dates do not
  separate them, rather than naming a winner

#### Scenario: A non-nested comparison is labelled as such

- **WHEN** two compared variants do not stand in a subset relation on their
  predictors
- **THEN** the published comparison names the terms added and the terms
  removed
- **AND** it is not described as isolating a single term

### Requirement: Two definitions are compared on the intersection of their holdouts

Comparing two definitions SHALL score each on its own holdout, then compare
them on the races both hold out, and SHALL report separately what each
definition admits that the other does not. The paired uncertainty interval on
shared races SHALL resample whole election-date clusters. A pooled score from
one definition's holdout SHALL NOT be reported as a difference against the
other's.

#### Scenario: The comparison is paired on shared races

- **WHEN** two definitions are compared
- **THEN** the point difference is computed over the races present in both
  holdout sets
- **AND** its interval resamples the election dates carrying those shared
  races and is labelled undecided when it contains zero

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

## ADDED Requirements

### Requirement: A comparison discloses election-date sensitivity

Every comparison covering general elections SHALL report its result after
omitting each general-election date in turn. The report SHALL identify a sign
change, a verdict change, or a result whose apparent gain is concentrated in
one date, rather than leaving that dependence hidden behind the pooled race
count.

#### Scenario: A one-election gain is visible

- **WHEN** a variant's pooled advantage disappears or reverses after one
  general-election date is omitted
- **THEN** that date and the leave-one-date-out result are published
- **AND** the variant is not described as robust across election cycles

#### Scenario: Sensitivity uses the same paired races

- **WHEN** one date is omitted
- **THEN** both variants lose the same paired races from that date
- **AND** all other comparison restrictions remain unchanged

### Requirement: Forecast-facing evaluation matches the target use

The published evaluation of an operational general-election forecast SHALL
report general elections separately from specials, the latest available
general-election fold, each office and incumbency level, finance-complete and
fallback races, and competitive bands defined only from pre-election inputs or
cross-fitted predictions. It SHALL also compare the target predictors with
historical support.

#### Scenario: The latest election cannot disappear into the pooled score

- **WHEN** an operational forecast variant is evaluated
- **THEN** its most recent general-election RMSE, bias, coverage, Brier score,
  and log loss appear beside its pooled general-election values

#### Scenario: Competitive races are selected without outcomes

- **WHEN** performance is reported for a competitive band
- **THEN** membership is determined from information available before that
  race's election
- **AND** the observed margin or winner is not used to choose the band

#### Scenario: Fallback performance is visible

- **WHEN** an operational composite routes incomplete-finance races to a
  fallback
- **THEN** scores for the money and fallback components are reported
  separately as well as pooled
- **AND** full coverage is not credited without showing fallback quality

### Requirement: Corrected comparison results supersede race-bootstrap verdicts

All affected variant, definition, and variable-importance comparisons SHALL be
recomputed with election-date-clustered uncertainty. Published writeups SHALL
distinguish an unchanged point estimate from a changed interval or verdict and
SHALL retain the previous race-bootstrap result only as superseded history.

#### Scenario: A timing verdict changes after clustering

- **WHEN** the clustered interval for a previously decided timing comparison
  spans zero
- **THEN** the current result is published as undecided
- **AND** the earlier decided label is explicitly marked superseded

#### Scenario: Comparison metadata names the resampling unit

- **WHEN** any comparison row is published
- **THEN** it records the resampling unit, number of election-date clusters,
  resample count, and seed
- **AND** a race-bootstrap row cannot be mistaken for a clustered result
