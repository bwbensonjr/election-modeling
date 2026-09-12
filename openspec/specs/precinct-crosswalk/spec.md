## Purpose

Maps Massachusetts precincts across the 2001, 2011, and 2021 redistricting
cycles so that presidential votes cast under one precinct geography can be
attributed to the precincts and districts a later legislative race was run
under.

## Requirements

### Requirement: Each election is assigned a redistricting cycle

The system SHALL assign every collected election to the redistricting cycle
in force on its election date: 2001 for elections from 2002 through 2011,
2011 for elections from 2012 through 2021, and 2021 for elections from 2022
onward. A cycle's districts remain in force for off-year special elections
held after the last general election run under them, so the cycle boundary
falls between the odd year and the following general, not at the general.

#### Scenario: Cycle assignment by election date

- **WHEN** the 2008 presidential election is processed
- **THEN** it is assigned the 2001 redistricting cycle
- **AND** the 2012 presidential election is assigned the 2011 cycle
- **AND** the 2024 presidential election is assigned the 2021 cycle

#### Scenario: Off-year specials stay in the outgoing cycle

- **WHEN** a special election held in 2011 or in 2021 is processed
- **THEN** it is assigned the 2001 cycle and the 2011 cycle respectively,
  matching the districts it was run under rather than the cycle that took
  effect the following year

### Requirement: Precinct-to-district mapping is available for every cycle

The system SHALL provide, for each redistricting cycle, a mapping from each
precinct to the State Representative and State Senate district containing
it. For the 2001 cycle this mapping SHALL be derived from the precinct-level
legislative result files, in which each district's returns enumerate the
precincts that district contains.

#### Scenario: 2001-cycle mapping is derived from legislative returns

- **WHEN** the precinct-level State Representative results for a 2001-cycle
  election are processed
- **THEN** every precinct appearing in a district's returns is mapped to that district

#### Scenario: Each precinct maps to exactly one district per office

- **WHEN** the mapping for a cycle is assembled
- **THEN** no precinct is assigned to more than one district for the same office
- **AND** any precinct assigned to multiple districts is reported as a conflict

### Requirement: Identifier-stable precincts are carried across cycles exactly

Where a precinct's `(city_town, ward, precinct)` identifier is unchanged
across a redistricting boundary, the system SHALL carry its vote totals
forward unmodified rather than interpolating them.

#### Scenario: Stable precinct keeps integer vote totals

- **WHEN** a precinct's identifier is present in both the source and target cycles
- **THEN** its presidential vote totals in the target cycle equal the source
  totals exactly
- **AND** the totals remain whole numbers

#### Scenario: Split precincts are combined before matching

- **WHEN** a precinct in the source cycle was subdivided into child precincts
  in the target cycle, or the reverse
- **THEN** the affected precincts are combined to their common parent before
  identifiers are compared

### Requirement: Unmatched precincts are resolved by areal interpolation

Precincts whose identifiers cannot be matched across a redistricting
boundary SHALL have their votes reallocated to target-cycle precincts by
area-weighted interpolation between the two cycles' precinct boundaries.

#### Scenario: Renumbered precinct is interpolated

- **WHEN** a precinct's identifier is absent from the target cycle
- **THEN** its votes are distributed across the overlapping target-cycle precincts
- **AND** the sum of the distributed votes equals the source total within rounding

#### Scenario: Interpolated totals may be fractional

- **WHEN** votes are reallocated by interpolation
- **THEN** the resulting vote totals are stored as real numbers rather than integers

### Requirement: Every precinct is resolved or reported

The system MUST NOT silently drop a precinct. Every source precinct SHALL be
either matched by identifier, interpolated, or reported as unresolved with
the reason.

#### Scenario: Unresolvable precinct is reported

- **WHEN** a precinct can be neither matched by identifier nor interpolated
  because boundary geometry is unavailable for its cycle
- **THEN** the precinct is listed in an unresolved report with its identifier and cycle
- **AND** the pipeline surfaces the count of unresolved precincts

#### Scenario: Statewide totals are preserved across a remap

- **WHEN** presidential votes are remapped from one cycle to another
- **THEN** the statewide Democratic and Republican totals after the remap
  match the totals before it, within rounding tolerance

### Requirement: Vote provenance is recorded

Each remapped precinct vote record SHALL record how it was produced, so that
downstream consumers can distinguish exact carry-over from interpolated
estimates.

#### Scenario: Provenance distinguishes exact from interpolated

- **WHEN** a remapped vote record is written
- **THEN** it carries a provenance value indicating either exact identifier
  match or areal interpolation
- **AND** records native to their own cycle are marked as requiring no remap
