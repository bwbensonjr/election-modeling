## Purpose

Publishes the race-grain rollup of the precinct training table, one row per
legislative race, carrying the response variable and predictors that the
district-level margin model is fit on and scored against.

## Requirements

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

### Requirement: The district margin is recomputed from summed precinct votes

`dem_margin` SHALL be computed by summing each precinct's `dem_votes`,
`opponent_votes`, and `candidate_votes` across the race and taking the
Democratic share minus the comparison candidate's share, in percentage
points. It SHALL NOT be an average of the precinct `dem_margin` values,
which would weight small precincts equally with large ones.

#### Scenario: Margin is vote-weighted, not precinct-averaged

- **WHEN** a race's precincts differ in turnout
- **THEN** the published `dem_margin` equals the margin computed from the
  race's summed vote counts
- **AND** differs from the unweighted mean of the precinct margins whenever
  turnout and margin covary

#### Scenario: The no-Democrat convention carries through

- **WHEN** a race has no Democratic candidate
- **THEN** `no_dem_candidate` is true on the race row
- **AND** `dem_margin` follows the same negated definition the precinct table
  uses, so the value is negative when the Republican won

### Requirement: District PVI is recomputed from summed presidential votes

`PVI_N` SHALL be computed by summing the two-party presidential vote counts
behind each precinct's PVI across the race's precincts and applying the PVI
formula to those district totals against the same national baseline. It
SHALL NOT be an average of the precinct `PVI_N` values.

#### Scenario: PVI uses the district's own vote totals

- **WHEN** a race's district PVI is computed
- **THEN** it is derived from the district's summed Democratic and Republican
  presidential votes for the race's PVI year and redistricting cycle

#### Scenario: PVI coverage is reported per race

- **WHEN** a race contains precincts with no presidential two-party votes for
  its PVI year
- **THEN** those precincts contribute nothing to the sum
- **AND** the row records the share of the race's precincts that contributed
  a PVI input

#### Scenario: A race with no PVI inputs at all is excluded and reported

- **WHEN** no precinct in a race has presidential two-party votes for its PVI
  year
- **THEN** the race is excluded from the published table
- **AND** it appears in a report naming the race and the reason

### Requirement: Race attributes carry through unchanged

Each row SHALL carry `election_date`, `election_year`, `redistricting_cycle`,
`office`, `district`, `district_display`, `incumbent_status`, `pres_elec`,
`is_special`, and `num_candidates` exactly as the precinct table records them
for that race.

#### Scenario: Attributes are not re-derived

- **WHEN** a race row is published
- **THEN** each carried attribute equals the value shared by every precinct
  row of that race
- **AND** the build fails rather than publishing if a race's precinct rows
  disagree on any carried attribute

### Requirement: Rows disclose the provenance of their PVI inputs

Each row SHALL record the share of its PVI input votes that came from
presidential results remapped across a redistricting boundary by areal
interpolation, so that interpolation error can be modeled or excluded at
race grain.

#### Scenario: Interpolated share is available per race

- **WHEN** a race's PVI derives partly from areally interpolated precinct
  votes
- **THEN** the row records the fraction of its two-party PVI input votes
  carrying that provenance

### Requirement: The race table agrees with the published district-level reference

For races present in both, the published `dem_margin` and `PVI_N` SHALL agree
with `mapoli`'s `ma_leg_two_party_2008_2025.csv` within a stated tolerance,
excluding races with no Democratic candidate, whose reference values are
known to be computed incorrectly.

#### Scenario: Agreement is validated and reported

- **WHEN** the race table is published
- **THEN** a validation report compares every race present in both sources
- **AND** records the count within tolerance, the count outside it, and each
  outlier with its difference

#### Scenario: No-Democrat races are excluded from the comparison

- **WHEN** a race in both sources has no Democratic candidate
- **THEN** it is excluded from the agreement counts
- **AND** listed separately as a known reference defect rather than as an
  outlier

### Requirement: The race table is published as a versioned file

The race table SHALL be written as a gzipped CSV committed to the repository
with a documented column-by-column schema, so that modeling can proceed
without re-running collection.

#### Scenario: Published output is self-contained

- **WHEN** the repository is checked out fresh
- **THEN** the race table can be read without network access or a sibling
  repository checkout

#### Scenario: Schema is documented

- **WHEN** the race table is published
- **THEN** the companion schema document describes each column, its units,
  and how it was derived from the precinct table

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

### Requirement: The race table carries campaign finance and its provenance

The race table SHALL carry, for each race, the money measures the model is to
be fit on, the as-of date they were measured to, and the quality of the
candidate-to-filer match behind them.

Money columns SHALL be derived from the candidate-grain finance table rather
than recomputed, so that the race row and the candidate rows cannot disagree.

#### Scenario: Money columns carry their as-of date

- **WHEN** the race table publishes a money column
- **THEN** the row carries the as-of date that column was accumulated to
- **AND** every row scored together shares a comparable as-of date, or the
  difference is recorded

#### Scenario: Match quality is a column, not a log line

- **WHEN** a race's money is published
- **THEN** the row carries how many candidates were matched to a filer and how
  many were not
- **AND** a downstream definition or variant can filter on it

#### Scenario: Unavailable money is distinct from zero money

- **WHEN** a race has a candidate whose filer could not be found
- **THEN** the money columns for that race record the value as missing rather
  than as zero
- **AND** a race in which every candidate was matched and raised nothing
  records zero

#### Scenario: A race row agrees with its candidate rows

- **WHEN** a race's money column is published alongside the candidate-grain
  table
- **THEN** the race figure is reproducible from the candidate rows for that
  race
- **AND** any disagreement fails the build rather than being published

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
