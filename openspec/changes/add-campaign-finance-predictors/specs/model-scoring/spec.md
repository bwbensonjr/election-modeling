## ADDED Requirements

### Requirement: A dated predictor's as-of date travels with the scores

Where a scored variant carries a predictor with an as-of date, that date SHALL
appear in the published outputs for every fit and every score it produced, so
that no published metric is ambiguous about the point in time its predictors
were measured at.

#### Scenario: The as-of date reaches the published record

- **WHEN** a variant carrying a dated predictor is scored
- **THEN** the as-of date appears in the fit diagnostics and in the scorecard
  rows for that variant
- **AND** a reader can tell, without consulting the code, how far before each
  election the predictors were measured

#### Scenario: Two as-of dates are two results

- **WHEN** the same variant is scored at two different as-of dates
- **THEN** the results are published as separate rows rather than merged
- **AND** the comparison between them is reported as a comparison of dates,
  not of model structure

### Requirement: The money sweep is reported per incumbency segment

The campaign-finance comparison SHALL be published broken out by incumbency as
well as pooled, because money is expected to behave differently in an open
seat than against an incumbent, and a pooled figure can hide an effect that is
real in one segment and absent in another.

#### Scenario: Segments are reported whether or not they agree

- **WHEN** a money variant is compared to the baseline
- **THEN** the difference is reported within open seats, Democratic-held seats
  and Republican-held seats, alongside the pooled difference
- **AND** a segment whose race count is too small to carry weight is marked as
  such rather than omitted

#### Scenario: The endogeneity caveat accompanies the result

- **WHEN** a money variant's result is published
- **THEN** the writeup states that money flows toward candidates already
  expected to win, so a coefficient may reflect expectations rather than
  influence
- **AND** the result is not presented as evidence that spending changes
  outcomes
