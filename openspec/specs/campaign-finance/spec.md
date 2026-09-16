## Purpose

Collects Massachusetts campaign finance from OCPF at candidate grain and
attaches it to legislative races, covering how a candidate is resolved to a
filer, how a money total is measured as of a stated date rather than read from
a published cumulative figure, and how a candidate that cannot be matched is
published rather than absorbed as a zero.

## Requirements

### Requirement: Money is measured as of a stated date

A candidate's money SHALL be reported as the amount accumulated between the
start of the election year and a stated as-of date, and that date SHALL travel
with the figure. The system SHALL NOT publish a money figure whose as-of date
is unknown.

The published cumulative figures the OCPF feeds carry are not usable for this
purpose: fetched after a cycle, they report the full calendar year, which
includes money raised after the polls closed.

#### Scenario: A money column names the date it was measured on

- **WHEN** any campaign-finance figure is published
- **THEN** the as-of date it was accumulated to is published with it
- **AND** a figure whose as-of date cannot be determined is omitted rather
  than published undated

#### Scenario: The as-of date precedes the election

- **WHEN** money is collected for a race
- **THEN** the as-of date is strictly before that race's election date
- **AND** a request for an as-of date on or after the election date is refused

#### Scenario: A published cumulative figure is not used as the measure

- **WHEN** a feed reports a cumulative year-to-date or full-cycle total
- **THEN** that figure is not used as a predictor's value
- **AND** if it is published at all it is labelled as covering the whole
  reporting period, including any part of it after the election

### Requirement: One measurement method spans every cycle

Money SHALL be measured the same way for every election year in the training
range. Where the source feeds differ across eras, the system SHALL reconstruct
a comparable figure rather than concatenating figures that mean different
things.

The feeds do not agree across eras: one covers the earlier cycles and reports
final full-cycle totals, the other covers the later cycles and reports a
snapshot. Joining them directly would put a discontinuity in the middle of the
training range that the model would read as a change in the world.

#### Scenario: Figures from different eras are comparable

- **WHEN** money is collected for an early cycle and a late cycle
- **THEN** both are accumulated over the same kind of window, ending at a
  comparable as-of date
- **AND** neither is a published total whose reporting period differs from the
  other's

#### Scenario: An era with no usable source is reported, not interpolated

- **WHEN** a cycle has no source from which a dated total can be reconstructed
- **THEN** that cycle's races are published with money recorded as
  unavailable
- **AND** the unavailability is distinguishable from a candidate who raised
  nothing

### Requirement: A candidate is resolved to a filer by a recorded rule

Attaching money to a race requires matching each candidate to an OCPF filer.
The system SHALL record, for every candidate, whether a filer was found and by
which rule, and SHALL NOT treat an unmatched candidate as one who raised no
money.

#### Scenario: An unmatched candidate is published, not zeroed

- **WHEN** a candidate cannot be resolved to a filer
- **THEN** that candidate's money is recorded as unavailable rather than zero
- **AND** the candidate appears in a published review file naming the race,
  the candidate, and what was searched

#### Scenario: A race records the quality of its match

- **WHEN** a race's money is published
- **THEN** the race carries how many of its candidates were matched and how
  many were not
- **AND** a race with an incomplete match is flagged so it can be excluded
  from a fit rather than silently contributing a partial total

#### Scenario: An ambiguous match is not guessed

- **WHEN** a candidate name matches more than one filer for the district and
  year
- **THEN** the match is recorded as ambiguous rather than resolved to either
- **AND** the candidates involved appear in the review file

#### Scenario: A filer with no money is distinct from no filer

- **WHEN** a candidate is matched to a filer that reports no receipts in the
  window
- **THEN** the money is recorded as zero
- **AND** this is distinguishable in the published data from a candidate whose
  filer was never found

### Requirement: Collection is cached and reproducible

Every response the collection depends on SHALL be cached, and a repeated run
SHALL reproduce the published tables from the cache without contacting the
API.

#### Scenario: A rerun needs no network

- **WHEN** the collection is run a second time against a populated cache
- **THEN** it produces identical output
- **AND** it makes no API request

#### Scenario: The collection states what it fetched

- **WHEN** a collection run completes
- **THEN** it reports how many candidates were resolved, how many requests
  were served from cache, and how many were fetched

### Requirement: An outcome field is never read as a predictor

The OCPF feeds carry fields that encode the election result. These SHALL NOT
be used as predictors, and the system SHALL refuse a predictor derived from
them.

#### Scenario: A winner flag is refused

- **WHEN** a predictor is derived from a feed field indicating whether a
  candidate won
- **THEN** the system refuses it and names the field
- **AND** the refusal is the same mechanism that rejects any other
  outcome-derived predictor

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
