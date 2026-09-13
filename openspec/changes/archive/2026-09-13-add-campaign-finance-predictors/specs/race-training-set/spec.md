## ADDED Requirements

### Requirement: The race table carries campaign finance and its provenance

The race table SHALL carry, for each race, the money measures the model is to
be fit on, the as-of date they were measured to, and the quality of the
candidate-to-filer match behind them.

Money columns SHALL be derived from the candidate-grain finance table rather
than recomputed, so that the race row and the candidate rows cannot disagree.

#### Scenario: Money columns carry their as-of date

- **WHEN** the race table publishes a money column
- **THEN** the row carries the as-of date that column was accumulated to
- **AND** every row scored together shares a comparable as-of date, or the
  difference is recorded

#### Scenario: Match quality is a column, not a log line

- **WHEN** a race's money is published
- **THEN** the row carries how many candidates were matched to a filer and how
  many were not
- **AND** a downstream definition or variant can filter on it

#### Scenario: Unavailable money is distinct from zero money

- **WHEN** a race has a candidate whose filer could not be found
- **THEN** the money columns for that race record the value as missing rather
  than as zero
- **AND** a race in which every candidate was matched and raised nothing
  records zero

#### Scenario: A race row agrees with its candidate rows

- **WHEN** a race's money column is published alongside the candidate-grain
  table
- **THEN** the race figure is reproducible from the candidate rows for that
  race
- **AND** any disagreement fails the build rather than being published
