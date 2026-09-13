## Purpose

Publishes the race-grain rollup of the precinct training table, one row per
legislative race, carrying the response variable and predictors that the
district-level margin model is fit on and scored against.

## ADDED Requirements

### Requirement: The race table is keyed by election

The system SHALL publish a table with exactly one row per `election_id`,
derived entirely from the published precinct training table and covering the
same races: contested State Representative and State Senate elections from
2010 through 2024, general and special.

#### Scenario: Row grain is unique

- **WHEN** the race table is published
- **THEN** no two rows share an `election_id`

#### Scenario: Race coverage matches the precinct table

- **WHEN** the race table is published
- **THEN** the set of `election_id` values is identical to the set present in
  the precinct training table
- **AND** no race is added that the precinct table does not contain

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
