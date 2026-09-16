## ADDED Requirements

### Requirement: Incumbent tenure measures uninterrupted service before the race

The precinct training table SHALL publish `incumbent_tenure_years` and
`incumbent_tenure_left_censored` as race-level attributes repeated unchanged on
every precinct row. For an incumbent, tenure SHALL be the elapsed days from the
victory that began the incumbent's current uninterrupted chain of service to
the current election date, divided by 365.2425. The current election's result
MUST NOT contribute to the value.

The chain SHALL follow the selected incumbent's stable upstream candidate
identity backward through victories in the same office, using the upstream
prior-district linkage across redistricting and including both regular and
special elections. It SHALL stop at a loss, a race the candidate did not win,
a gap in holding the office, or the beginning of upstream history. Re-election
after a break SHALL begin a new chain.

#### Scenario: A special-election winner accumulates partial-term tenure

- **WHEN** a candidate wins a special election and is the incumbent in a later
  election
- **THEN** `incumbent_tenure_years` measures from the special-election date
- **AND** the later election's outcome is not consulted

#### Scenario: A career gap resets tenure

- **WHEN** an incumbent previously held the office but the uninterrupted chain
  of victories ends before the current term began
- **THEN** tenure measures only from the first victory in the current chain
- **AND** service before the gap is not added

#### Scenario: Redistricting does not reset continuous service

- **WHEN** the upstream history links an incumbent to a prior district across a
  redistricting boundary
- **THEN** the chain follows that prior district
- **AND** tenure is not reset solely because the district identifier changed

#### Scenario: Open seats have zero tenure

- **WHEN** `incumbent_status` is `No_Incumbent`
- **THEN** `incumbent_tenure_years` is `0`
- **AND** `incumbent_tenure_left_censored` is false

#### Scenario: Source-boundary tenure is disclosed

- **WHEN** an incumbent's uninterrupted chain reaches the first election
  available from the upstream source without establishing the true start
- **THEN** the published tenure is a lower bound measured from that first
  available victory
- **AND** `incumbent_tenure_left_censored` is true

#### Scenario: Incumbent identity cannot be resolved safely

- **WHEN** the selected incumbent lacks a stable identity or the upstream
  linkage produces more than one possible predecessor
- **THEN** the build fails with the affected election and candidate identified
- **AND** it does not infer tenure from candidate name text

### Requirement: Published tenure is reproducible without upstream access

The committed precinct training table and its schema SHALL contain the tenure
value, censoring flag, units, derivation rule, and upstream source provenance.
Rebuilding may read `ma-election-db`, but fitting and scoring SHALL NOT require
that sibling repository.

#### Scenario: Modeling uses the committed value

- **WHEN** a model is fit from a fresh checkout without `ma-election-db`
- **THEN** every eligible race's tenure fields are available from committed
  inputs
- **AND** the model does not reconstruct candidate history during fitting
