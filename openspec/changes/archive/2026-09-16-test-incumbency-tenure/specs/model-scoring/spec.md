## ADDED Requirements

### Requirement: The incumbency-tenure hypothesis is compared and published

The system SHALL score `baseline_tenure_cap4` against `baseline` under every
scored definition on identical rolling-origin folds and shared holdout races.
It SHALL publish the paired RMSE difference with election-date-clustered
uncertainty, secondary metrics, fit diagnostics, and leave-one-general-date-out
sensitivity. The two- and six-year cap variants SHALL be published as
pre-declared shape sensitivity checks against the same baseline.

#### Scenario: The primary hypothesis is identified in advance

- **WHEN** tenure comparisons are published
- **THEN** the four-year cap is labelled primary
- **AND** a better point estimate from another cap is not presented as though
  that cap had been selected before observing the scores

#### Scenario: An undecided tenure result retains the baseline

- **WHEN** the clustered interval for the primary RMSE difference contains
  zero
- **THEN** the tenure hypothesis is reported as undecided
- **AND** the existing baseline is retained rather than adopting tenure from
  the point estimate alone

#### Scenario: A primary loss rejects adoption

- **WHEN** the clustered interval shows higher RMSE for the primary tenure
  variant
- **THEN** the result is published as evidence against adoption
- **AND** a favorable sensitivity cap does not silently replace the primary
  hypothesis

### Requirement: Tenure results disclose where the evidence comes from

The tenure comparison SHALL report paired race counts and metrics for open
seats, tenure greater than zero and less than two years, tenure from two years
through less than four years, and tenure of at least four years. It SHALL also
report Democratic- and Republican-incumbent segments separately. Left-censored
counts and any rows excluded because a capped value is not known exactly SHALL
be reported for every variant.

#### Scenario: Early tenure is visible

- **WHEN** the tenure comparison is published
- **THEN** races below two years and races from two through less than four years
  have separate metrics and counts
- **AND** improvement among newer incumbents cannot be hidden by long-tenured
  races

#### Scenario: Saturated tenure is visible

- **WHEN** the comparison includes incumbents with at least four years of
  service
- **THEN** that segment's metrics and count are published
- **AND** the report states that the primary predictor assigns no additional
  tenure effect beyond four years

#### Scenario: Sparse segments are not overstated

- **WHEN** a tenure or party segment contains too few election-date clusters
  for a clustered interval
- **THEN** its interval is reported as not estimable and its count is shown
- **AND** it is not used alone to claim that tenure helps or hurts
