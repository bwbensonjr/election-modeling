## ADDED Requirements

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

## RENAMED Requirements

- FROM: `### Requirement: A predictor must be knowable before its fold year`
- TO: `### Requirement: A predictor must be knowable before its fold year's election`

## MODIFIED Requirements

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
