## ADDED Requirements

### Requirement: Forecast candidates are matched across information horizons

The system SHALL register forecast-candidate variants that separate the ballot
timing question from the finance-horizon question. At both 60 and 14 days
before the election, the candidate set SHALL include a log-ratio receipts model
with the declared ballot-timing categorical and a corresponding log-ratio
receipts model carrying neither `ballot_timing` nor `pres_elec`.

#### Scenario: Both timing choices exist at 60 days

- **WHEN** the 60-day forecast candidates are listed
- **THEN** a timing-plus-money variant and a no-timing money variant are both
  present
- **AND** both use the 60-day receipts contrast and otherwise comparable
  predictors, priors, and sampler settings

#### Scenario: Both timing choices exist at 14 days

- **WHEN** the 14-day forecast candidates are listed
- **THEN** a timing-plus-money variant and a no-timing money variant are both
  present
- **AND** both use the 14-day receipts contrast and otherwise comparable
  predictors, priors, and sampler settings

#### Scenario: Horizon and timing effects are not conflated

- **WHEN** two forecast candidates are compared
- **THEN** the report identifies whether they differ in information horizon,
  ballot timing, or both
- **AND** no comparison differing in both is described as isolating either one

### Requirement: An operational forecast variant covers incomplete finance

Each forecast horizon SHALL have one named operational composite whose routing
predicate is finance completeness at that horizon. Its complete-finance
component SHALL be the money candidate selected under the declared comparison
rule, and its fallback component SHALL omit dated money while retaining every
other predictor the selected structure can validly use.

#### Scenario: The money component trains only on complete finance

- **WHEN** an operational forecast composite is fit
- **THEN** its money component trains only on races with complete candidate
  finance at the matching horizon
- **AND** it predicts only target races complete at that horizon

#### Scenario: The fallback trains without imputing money

- **WHEN** the fallback component is fit
- **THEN** it uses eligible historical races without a money predictor
- **AND** unavailable finance is neither zeroed nor otherwise imputed

#### Scenario: The operational choice names its evidence

- **WHEN** a candidate structure is selected for an operational horizon
- **THEN** the declaration cites its election-date-clustered comparison and
  leave-one-election sensitivity
- **AND** an undecided choice is attributed to a stated tie-break rather than
  to an accuracy claim

### Requirement: Forecast fits use a target-independent seed

A full-history forecast fit SHALL use a stable seed determined by the variant,
definition, training cutoff, target election, and information horizon. The
seed SHALL NOT depend on target row order or on an outcome unavailable at
forecast time.

#### Scenario: Reordering target races does not reseed the fit

- **WHEN** the same forecast target rows are supplied in a different order
- **THEN** the full-history fit uses the same seed
- **AND** predictions join back to the same race identities

#### Scenario: Two horizons are distinguishable

- **WHEN** the 60-day and 14-day fits use otherwise identical declarations
- **THEN** their seeds and records identify their distinct information
  horizons
