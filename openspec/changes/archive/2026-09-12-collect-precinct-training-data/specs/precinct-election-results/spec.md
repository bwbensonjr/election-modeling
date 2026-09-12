## Purpose

Retrieves and normalizes precinct-level general election results from the
Massachusetts Commonwealth Election Statistics site, so that presidential
and legislative returns are available at precinct grain for modeling.

## ADDED Requirements

### Requirement: Presidential precinct results are collected for 2004 through 2024

The system SHALL collect precinct-level presidential general election
results for 2004, 2008, 2012, 2016, 2020, and 2024. Each year's results
SHALL cover every Massachusetts precinct reporting for that election.

#### Scenario: All six presidential elections are retrieved

- **WHEN** the collection pipeline runs for presidential elections
- **THEN** precinct results exist for each of 2004, 2008, 2012, 2016, 2020, and 2024
- **AND** each year contains at least 2,100 precinct rows

#### Scenario: Statewide totals reconcile with the published district-level summary

- **WHEN** precinct vote totals for a presidential election are summed statewide
- **THEN** the Democratic and Republican totals match the corresponding
  `ma-election-db` general election summary totals for that election

### Requirement: Legislative precinct results are collected for 2010 through 2024

The system SHALL collect precinct-level State Representative and State
Senate results for every district in every legislative election held from
2010 through 2024, including special elections as well as the biennial
November generals.

#### Scenario: Every district in a cycle is retrieved

- **WHEN** the collection pipeline runs for a legislative office and cycle
- **THEN** precinct results exist for every district listed in the
  `ma-election-db` general election summaries for that office and election date

#### Scenario: Special elections are retrieved

- **WHEN** a legislative special election was held between 2010 and 2024
- **THEN** its precinct results are collected alongside the general elections
- **AND** the election is marked as special

#### Scenario: Uncontested races are still collected

- **WHEN** a legislative race has a single candidate
- **THEN** its precinct results are still collected, because they establish
  which precincts the district contains

#### Scenario: District vote totals reconcile

- **WHEN** precinct vote totals for a legislative race are summed across the district
- **THEN** each candidate's total matches the district-level total published
  for that candidate in `ma-election-db`
- **AND** any race that does not reconcile is reported as a collection error

### Requirement: Responses without precinct detail are rejected

The upstream endpoint returns municipality-level rows with empty ward and
precinct fields for elections that predate precinct reporting, rather than
returning an error. The system SHALL detect this and MUST NOT treat such a
response as a successful precinct-level collection.

#### Scenario: Municipality-level response is refused

- **WHEN** a fetched result contains no rows with a populated precinct value
- **THEN** the system reports the election as lacking precinct data
- **AND** the result is excluded from the normalized output

#### Scenario: Non-CSV response is refused

- **WHEN** the endpoint returns an HTML error page or a non-200 status
- **THEN** the system reports the failure with the election identifier
- **AND** no partial result is written to the normalized output

### Requirement: Collected results are normalized to a common schema

The system SHALL normalize every collected result to a single schema keyed
by `(election_id, city_town, ward, precinct)` with per-candidate vote
counts, regardless of the header conventions used by the source file for
that vintage.

#### Scenario: Single-precinct municipalities are given explicit identifiers

- **WHEN** a source row has empty ward and precinct fields because the
  municipality has one precinct
- **THEN** the normalized row carries a ward of `-` and a precinct of `1`

#### Scenario: Aggregate rows are excluded

- **WHEN** a source file contains a `TOTALS` row or a party-label row
- **THEN** those rows are absent from the normalized output

#### Scenario: Municipality names are normalized

- **WHEN** a source row abbreviates a compass direction in a municipality name
- **THEN** the normalized row carries the unabbreviated name, matching the
  spelling used by the census and GIS inputs

### Requirement: Collection is re-runnable without refetching

The system SHALL cache raw upstream responses and SHALL reuse the cache on
subsequent runs, so that the normalized outputs can be rebuilt without
issuing roughly 1,600 network requests again.

#### Scenario: Second run uses cached responses

- **WHEN** the pipeline is run a second time with the cache populated
- **THEN** no upstream requests are issued for elections already cached
- **AND** the normalized outputs are byte-identical to the first run

#### Scenario: Requests are throttled

- **WHEN** the pipeline issues uncached requests
- **THEN** requests are rate-limited rather than issued concurrently without delay
