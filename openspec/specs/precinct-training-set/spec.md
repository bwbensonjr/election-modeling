## Purpose

Assembles the published training table for the legislative margin model, one
row per legislative race per precinct, carrying the model's response variable
and predictors at precinct grain.

## Requirements

### Requirement: The training table is keyed by race and precinct

The system SHALL publish a table with exactly one row per
`(election_id, city_town, ward, precinct)` combination, covering State
Representative and State Senate elections from 2010 through 2024, both
general and special.

#### Scenario: Row grain is unique

- **WHEN** the training table is published
- **THEN** no two rows share the same election identifier and precinct identifier

#### Scenario: Coverage spans the full window

- **WHEN** the training table is published
- **THEN** it contains rows for both legislative offices in each general
  election from 2010 through 2024
- **AND** contested special elections held in that window are present, with
  `is_special` set
- **AND** every precinct in a district's returns for an included race appears as a row

### Requirement: Each row carries the model's response and predictors

Each row SHALL carry `dem_margin` and `PVI_N` computed at precinct grain,
together with `incumbent_status`, `pres_elec`, `is_special`, and
`num_candidates` for the race the precinct belongs to.

#### Scenario: Predictors are present and typed

- **WHEN** a training row is published
- **THEN** `dem_margin` and `PVI_N` are numeric
- **AND** `incumbent_status` is one of `No_Incumbent`, `Dem_Incumbent`, or `GOP_Incumbent`
- **AND** `pres_elec` and `is_special` are boolean
- **AND** `num_candidates` is an integer

#### Scenario: District attributes are repeated across the district's precincts

- **WHEN** two rows belong to the same race
- **THEN** they carry identical `incumbent_status`, `pres_elec`, `is_special`,
  and `num_candidates` values

### Requirement: Precinct margin follows the established district definition

`dem_margin` SHALL be the Democratic candidate's vote share in the precinct
minus the share of the strongest non-Democratic candidate in that race,
expressed in percentage points. Where the race has no Democratic candidate,
the margin SHALL be the negation of the Republican share minus the strongest
remaining share.

#### Scenario: The comparison candidate is fixed at race level

- **WHEN** the strongest non-Democratic candidate is determined for a race
- **THEN** the same candidate is used as the comparison for every precinct in
  that race, rather than being re-selected per precinct

#### Scenario: Margin aggregates to the published district margin

- **WHEN** a race's precinct vote counts are summed to the district and the
  margin recomputed
- **THEN** the result matches the district-level `dem_margin` derived from
  `ma-election-db` for that race, within rounding tolerance

### Requirement: Uncontested races are excluded

Races with fewer than two candidates SHALL be excluded from the training
table, matching the filter the existing district-level model applies.

#### Scenario: Single-candidate race produces no rows

- **WHEN** a legislative race has only one candidate
- **THEN** no rows for that race appear in the training table

### Requirement: Incumbency follows the established classification

`incumbent_status` SHALL be derived from the incumbent's party as published
in `ma-election-db`, with an unenrolled incumbent classified as
`GOP_Incumbent` and a race with no incumbent classified as `No_Incumbent`.

#### Scenario: Unenrolled incumbent is classified as GOP

- **WHEN** a race's incumbent has an unenrolled party affiliation
- **THEN** the row's `incumbent_status` is `GOP_Incumbent`

### Requirement: PVI is joined by presidential pair and redistricting cycle

Each race SHALL be joined to the PVI record for the two presidential
elections completed before that race, expressed on the precinct geography of
the race's own redistricting cycle. Both halves of the key are required: a
race MUST NOT be joined to PVI computed on a different cycle's precincts.

#### Scenario: Join key assignment by race year

- **WHEN** rows are assembled for races in 2010 and 2011
- **THEN** they join to the 2004 + 2008 pair on the 2001 cycle
- **AND** 2012 races join to the 2004 + 2008 pair on the 2011 cycle
- **AND** races from 2013 through 2016 join to the 2008 + 2012 pair on the 2011 cycle
- **AND** races from 2017 through 2020 join to the 2012 + 2016 pair on the 2011 cycle
- **AND** races in 2021 join to the 2016 + 2020 pair on the 2011 cycle
- **AND** races from 2022 through 2024 join to the 2016 + 2020 pair on the 2021 cycle

#### Scenario: An off-year special uses its own cycle's geography

- **WHEN** a special election held in 2021 is assembled
- **THEN** it joins to PVI expressed on 2011-cycle precincts, matching the
  districts it was actually run under, rather than the 2021-cycle geography
  that took effect the following year

#### Scenario: A race precinct with no PVI is reported

- **WHEN** a precinct in an included race has no PVI value for the joined PVI year
- **THEN** the row is published with a missing `PVI_N` and flagged
- **AND** the count of such rows is reported

### Requirement: Rows disclose the provenance of their PVI inputs

Each row SHALL indicate whether its PVI was computed from presidential votes
native to the race's precinct geography or from votes remapped across a
redistricting boundary, so that interpolation error can be modeled or
excluded.

#### Scenario: Remapped rows are identifiable

- **WHEN** a row's PVI derives from presidential votes reallocated by areal
  interpolation
- **THEN** the row carries a provenance value marking it as interpolated

### Requirement: Outputs are published as versioned files

The training table and its intermediate stages SHALL be written as gzipped
CSV files committed to the repository, so that modeling work can proceed
without re-running collection.

#### Scenario: Published outputs are self-contained

- **WHEN** the repository is checked out fresh
- **THEN** the training table can be read without network access or a
  sibling repository checkout

#### Scenario: Schema is documented

- **WHEN** the training table is published
- **THEN** a companion document describes each column, its units, and its source
