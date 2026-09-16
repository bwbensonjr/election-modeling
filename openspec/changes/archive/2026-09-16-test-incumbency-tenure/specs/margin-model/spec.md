## ADDED Requirements

### Requirement: Diminishing-returns incumbency-tenure variants are declared

The system SHALL register `baseline_tenure_cap4`, defined as the baseline plus
a signed tenure term whose magnitude is
`min(incumbent_tenure_years, 4)`. The term SHALL be positive for a Democratic
incumbent, negative for a Republican incumbent, and zero for an open seat. The
existing `incumbent_status` terms SHALL remain in the variant so that the new
coefficient measures change within incumbents rather than replacing the
open-seat contrast.

The system SHALL also register otherwise identical `baseline_tenure_cap2` and
`baseline_tenure_cap6` sensitivity variants. The four-year cap SHALL be the
pre-declared primary hypothesis; the sensitivity variants SHALL NOT be searched
to choose an empirically optimal cap on the same holdout record.

#### Scenario: One and four years remain distinguishable

- **WHEN** two incumbents of the same party have served one and four years
- **THEN** `baseline_tenure_cap4` assigns them different signed tenure values
- **AND** their difference is three signed tenure years

#### Scenario: Ten and twelve years are equivalent in the primary variant

- **WHEN** two incumbents of the same party have served ten and twelve years
- **THEN** `baseline_tenure_cap4` assigns both the same magnitude of four
- **AND** the model does not estimate a difference between them from tenure

#### Scenario: Party orientation follows Democratic margin

- **WHEN** Democratic and Republican incumbents have equal tenure
- **THEN** their signed tenure values have equal magnitude and opposite signs
- **AND** a positive tenure coefficient moves the predicted margin toward the
  incumbent's party in both cases

#### Scenario: The baseline remains unchanged

- **WHEN** tenure variants are registered and scored
- **THEN** `baseline` still declares exactly `PVI_N`, `incumbent_status`, and
  `pres_elec`
- **AND** its reproduced scores remain the comparison yardstick

#### Scenario: A cap is valid for a left-censored incumbent

- **WHEN** an incumbent's tenure is left-censored
- **THEN** a capped tenure variant may use the row only if the published lower
  bound is at least that variant's cap
- **AND** otherwise that variant is refused for the row rather than treating
  the lower bound as exact
