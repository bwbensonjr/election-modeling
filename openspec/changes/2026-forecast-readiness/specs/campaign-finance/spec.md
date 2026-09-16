## ADDED Requirements

### Requirement: Finance can be collected before an election has results

The system SHALL collect candidate finance from a validated future race roster
without requiring that any target race appear in the historical results or
training tables. Candidate identity, district, office, party, election date,
and comparison role SHALL be sufficient to resolve filers and request dated
money.

#### Scenario: A future roster drives collection

- **WHEN** a target roster names the candidates in a future legislative
  election
- **THEN** each candidate is resolved and collected by the same recorded rules
  used for historical candidates
- **AND** no vote total, winner, or election result is required

#### Scenario: An unmatched future candidate remains unavailable

- **WHEN** a target candidate cannot be resolved uniquely to an OCPF filer
- **THEN** the candidate is published in the match-review output
- **AND** the race is marked finance-incomplete rather than assigned zero

### Requirement: Forecast finance is frozen at declared horizons

For a target election the system SHALL publish separate candidate-grain
finance snapshots ending 60 days and 14 days before Election Day. Each value
SHALL use the same accumulation rule as the corresponding historical feature,
and a later collection run SHALL NOT alter an already published horizon.

#### Scenario: The historical and target windows are comparable

- **WHEN** a target candidate's 60-day or 14-day amount is produced
- **THEN** its start and end rules match the historical predictor carrying the
  same horizon name
- **AND** the exact target cutoff date is stored with the amount

#### Scenario: Activity after the cutoff is excluded

- **WHEN** OCPF contains a transaction after a forecast horizon's cutoff
- **THEN** that transaction contributes nothing to the frozen snapshot
- **AND** it may appear only in a later eligible horizon

#### Scenario: A rerun verifies rather than overwrites

- **WHEN** collection is repeated for a horizon already published
- **THEN** the reconstructed snapshot must match the committed snapshot
- **AND** any difference fails with the affected candidate and source record
  identified

### Requirement: Future finance provenance is publishable per candidate

Each future candidate row SHALL carry the filer identifier, match rule, source
requests or cache keys, accumulation window, cutoff, receipts and expenditures,
and availability status needed to audit its race-level contrast.

#### Scenario: A race contrast traces to both candidates

- **WHEN** a forecast uses a candidate-finance contrast
- **THEN** the Democratic and comparison-candidate amounts can each be traced
  to their candidate-grain rows
- **AND** the race-level completeness flag agrees with those rows

#### Scenario: Cache-only reproduction remains possible

- **WHEN** the future finance collection is rerun against its populated cache
- **THEN** it reproduces the frozen candidate rows without contacting OCPF
