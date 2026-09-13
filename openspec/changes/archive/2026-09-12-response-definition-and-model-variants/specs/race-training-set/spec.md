## ADDED Requirements

### Requirement: The two-party race margin is recomputed from summed precinct votes

`dem_margin_two_party` SHALL be computed by summing each precinct's
Democratic and Republican vote counts across the race and taking the
Democratic share of that two-party total minus the Republican share, in
percentage points. It SHALL NOT be an average of the precinct
`dem_margin_two_party` values.

#### Scenario: The two-party margin is vote-weighted

- **WHEN** a race's precincts differ in turnout
- **THEN** the published `dem_margin_two_party` equals the margin computed
  from the race's summed two-party vote counts
- **AND** differs from the unweighted mean of the precinct two-party margins
  whenever turnout and margin covary

#### Scenario: The two-party margin and PVI share a denominator

- **WHEN** a race carries both `dem_margin_two_party` and `PVI_N`
- **THEN** both are two-party quantities computed on the same kind of
  denominator, differing only in which election supplied the votes

#### Scenario: The two-party margin is missing where one major party is absent

- **WHEN** a race carries no Democrat, or no Republican
- **THEN** `dem_margin_two_party` is missing on the race row
- **AND** the row's `major_party_race` flag is false

### Requirement: Rows carry the flags a definition selects on

Each row SHALL carry whether the race pairs a Democrat against a Republican,
whether it was admitted on ballot lines alone or on an admitted write-in, the
share of named-candidate votes taken by write-ins, the count of candidates
counting admitted write-ins, and the existing no-Democrat indicator. The race
table and its companion candidate roster SHALL together be sufficient to apply
any declared definition.

#### Scenario: Every definition is evaluable at race grain

- **WHEN** a definition is applied for fitting or scoring
- **THEN** every column its eligibility rule and response choice reference is
  present on the race table or on the companion roster
- **AND** the precinct table is not read

#### Scenario: A threshold is resolved from the roster, not approximated

- **WHEN** a definition applies a write-in threshold other than the one the
  table was built at
- **THEN** the admitted candidate set and the response denominator are
  recomputed from the roster's per-candidate district votes
- **AND** recomputing at the threshold the table was built at reproduces the
  published response columns exactly

#### Scenario: Both responses travel together

- **WHEN** a race row is published
- **THEN** it carries both `dem_margin` and, where defined,
  `dem_margin_two_party`
- **AND** switching definitions changes which is used, not which is available

### Requirement: The shift between responses is quantified at publication

The system SHALL publish, alongside the race table, how far each race's
two-party margin differs from its all-candidate margin, so that a later
comparison between definitions can separate a change in model accuracy from a
change in the target being measured.

#### Scenario: Response shift is reported per race and in aggregate

- **WHEN** the race table is published
- **THEN** the per-race difference between the two responses is available
- **AND** the count of races shifting by more than a stated number of points
  is reported

## MODIFIED Requirements

### Requirement: The race table is keyed by election

The system SHALL publish a table with exactly one row per `election_id`,
derived entirely from the published precinct training table and covering the
same races: State Representative and State Senate elections from 2010 through
2024, general and special, that the precinct table's eligibility rule admits.
The table SHALL be definition-neutral: it SHALL carry every race any declared
definition admits, and SHALL NOT itself apply a definition's eligibility
filter.

#### Scenario: Row grain is unique

- **WHEN** the race table is published
- **THEN** no two rows share an `election_id`

#### Scenario: Race coverage matches the precinct table

- **WHEN** the race table is published
- **THEN** the set of `election_id` values is identical to the set present in
  the precinct training table
- **AND** no race is added that the precinct table does not contain

#### Scenario: No definition is baked into the published table

- **WHEN** the race table is published
- **THEN** it contains races that some declared definitions exclude, carrying
  the flags by which those definitions exclude them
- **AND** changing the adopted definition does not require republishing the
  table
