## ADDED Requirements

### Requirement: Race rows carry incumbent tenure unchanged

Each race row SHALL carry `incumbent_tenure_years` and
`incumbent_tenure_left_censored` exactly as recorded on the race's precinct
rows. These fields SHALL be available to model declarations without reading
candidate-level or precinct-level inputs.

#### Scenario: Precinct tenure agrees within a race

- **WHEN** a race is rolled up from precinct rows
- **THEN** all precinct rows have identical tenure and censoring values
- **AND** disagreement fails the build rather than choosing one value

#### Scenario: Race tenure retains its documented meaning

- **WHEN** a race row is published
- **THEN** its schema identifies tenure as years of uninterrupted service as of
  `election_date`
- **AND** its censoring flag distinguishes an exact value from a lower bound
