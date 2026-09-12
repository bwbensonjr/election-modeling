## Purpose

Computes a Partisan Voter Index value for each precinct from the two most
recent presidential elections, normalized against the national two-party
result, matching the definition the existing legislative model consumes at
district level.

## Requirements

### Requirement: PVI is computed from two consecutive presidential elections

For a given presidential pair, the system SHALL compute each precinct's
Democratic share of the combined two-party presidential vote across the two
elections, and SHALL subtract the national Democratic share computed the same
way, expressed in percentage points.

#### Scenario: Precinct PVI matches the established formula

- **WHEN** PVI is computed for a precinct from a presidential pair
- **THEN** the value equals the precinct's combined two-party Democratic share
  across the two elections minus the national combined two-party Democratic
  share, multiplied by 100

#### Scenario: Only Democratic and Republican votes are counted

- **WHEN** a precinct's presidential results include third-party, write-in,
  or blank votes
- **THEN** those votes are excluded from both the numerator and the denominator

### Requirement: PVI is keyed by presidential pair and redistricting cycle

A presidential pair yields different precinct values depending on the
precinct geography it is evaluated on, so the system SHALL key every PVI
record by both the PVI year, which names the later election of the pair, and
the redistricting cycle whose precinct geography it is expressed on.

#### Scenario: The same pair appears under two cycles

- **WHEN** the 2016 and 2020 presidential pair is computed for both the 2011
  and 2021 redistricting cycles
- **THEN** two distinct sets of precinct records exist, one per cycle
- **AND** each is identified by the same PVI year and a different cycle

### Requirement: Every PVI combination the training window requires is produced

The system SHALL produce precinct-level PVI for each combination of
presidential pair and redistricting cycle consumed by a race in scope:

| PVI year | Presidential pair | Cycle | Races served |
|---|---|---|---|
| 2008 | 2004 + 2008 | 2001 | 2010, 2011 |
| 2008 | 2004 + 2008 | 2011 | 2012 |
| 2012 | 2008 + 2012 | 2011 | 2013 through 2016 |
| 2016 | 2012 + 2016 | 2011 | 2017 through 2020 |
| 2020 | 2016 + 2020 | 2011 | 2021 |
| 2020 | 2016 + 2020 | 2021 | 2022 through 2024 |
| 2024 | 2020 + 2024 | 2021 | 2025 onward |

#### Scenario: All required combinations are present

- **WHEN** the PVI stage completes
- **THEN** precinct PVI records exist for every row of the table above

#### Scenario: A race with no matching combination is reported

- **WHEN** a race in scope has no PVI record for its presidential pair and cycle
- **THEN** the gap is reported rather than the race being silently joined to
  another cycle's geography

### Requirement: PVI is computed on the geography of the races that consume it

Each PVI record SHALL be expressed on the precinct geography of the
redistricting cycle in force for the legislative races that use it, with
presidential votes cast under an earlier cycle remapped to that geography.

#### Scenario: Earlier presidential votes are remapped before computation

- **WHEN** the 2008 + 2012 pair is computed for the 2011 cycle
- **THEN** the 2008 presidential votes it consumes have been remapped from
  2001-cycle to 2011-cycle precincts
- **AND** the 2012 votes, already native to the 2011 cycle, are used unmodified

### Requirement: National baselines are explicit and auditable

The national two-party vote totals used to normalize each pair SHALL be
stored as data with their source, not embedded as unexplained constants.

#### Scenario: Baseline totals are published

- **WHEN** the PVI stage completes
- **THEN** a baseline record exists for each presidential election from 2004
  through 2024 giving the national Democratic and Republican totals and the
  source they were taken from

### Requirement: Precinct PVI aggregates to published district PVI

Aggregating precinct presidential votes to district level and computing PVI
SHALL reproduce the district-level values already published in `mapoli`,
within a stated tolerance, for the combinations both cover.

#### Scenario: District rollup is validated against published values

- **WHEN** precinct presidential votes for the 2012 + 2016 pair on the 2011
  cycle are summed to State Senate districts and PVI is computed
- **THEN** each district's value agrees with the published
  `ma_state_leg_pvi_2008_2024.csv` value for PVI year 2016 within the stated tolerance
- **AND** any district outside tolerance is reported

#### Scenario: Precincts with no two-party votes are reported

- **WHEN** a precinct has zero combined Democratic and Republican presidential
  votes across both elections
- **THEN** its PVI is recorded as missing rather than computed
- **AND** the precinct is listed in a data quality report
