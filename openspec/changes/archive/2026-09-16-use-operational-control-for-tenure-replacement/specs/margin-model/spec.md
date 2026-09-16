## ADDED Requirements

### Requirement: Operational tenure-replacement variants mirror the selected forecasts

The system SHALL register `tenure_replacement_no_money` with predictors
`PVI_N` and `tenure_cap4_signed`, replacing `incumbent_status` rather than
adding to it. It SHALL register `tenure_replacement_money_14d` and
`tenure_replacement_money_60d` by adding the same horizon-matched receipts log
ratio used by the current operational money component. None of these variants
SHALL declare `incumbent_status`, `pres_elec`, or `ballot_timing`.

The system SHALL also register `forecast_tenure_replacement_14d` and
`forecast_tenure_replacement_60d` as composites. Each SHALL use the same
finance-completeness routing predicate as its current operational counterpart,
route complete-finance races to its matching tenure-and-money component, and
route incomplete-finance races to `tenure_replacement_no_money`.

#### Scenario: Tenure replaces incumbency status

- **WHEN** a tenure-replacement component is inspected
- **THEN** it declares `tenure_cap4_signed`
- **AND** it does not declare `incumbent_status`

#### Scenario: The money component preserves the information horizon

- **WHEN** the 14-day or 60-day tenure replacement is fit
- **THEN** it uses the receipts log ratio measured at that same horizon
- **AND** it does not use money observed after the declared cutoff

#### Scenario: Routing matches the operational control

- **WHEN** a holdout race is predicted by an operational control and its
  tenure-replacement challenger
- **THEN** both composites route it on the same finance-completeness value
- **AND** both produce exactly one prediction for that race

#### Scenario: The replacement imposes the declared symmetric shape

- **WHEN** Democratic and Republican incumbents have equal tenure
- **THEN** their replacement predictor values have equal magnitude and
  opposite signs
- **AND** the comparison report identifies that restriction relative to the
  two party-specific `incumbent_status` coefficients
