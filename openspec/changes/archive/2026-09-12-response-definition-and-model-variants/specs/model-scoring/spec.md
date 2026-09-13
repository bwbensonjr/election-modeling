## ADDED Requirements

### Requirement: A scoring run is performed under a named definition

Every scoring run SHALL be performed under exactly one data definition, which
determines the races eligible for training and holdout and the response scored
against. The definition SHALL be recorded in every output the run produces.

#### Scenario: Scores are never reported without their definition

- **WHEN** a scorecard row is published
- **THEN** it names the definition as well as the variant and the fold
- **AND** a metric from one definition cannot be read as comparable to one
  from another without the comparison procedure below

#### Scenario: The fold schedule is unchanged by the definition

- **WHEN** a definition is applied
- **THEN** the fold years remain every election year from 2014 through 2024
  that the definition admits races in
- **AND** a fold year the definition empties is recorded as skipped rather
  than omitted silently

#### Scenario: Holdout counts are published per definition

- **WHEN** a scoring run completes
- **THEN** the pooled holdout race count, the holdout special-election count,
  and the smallest training fold size under that definition are reported
- **AND** a definition that shrinks the holdout is visible as having done so

### Requirement: Two definitions are compared on the intersection of their holdouts

Comparing two definitions SHALL score each on its own holdout, then compare
them on the races both hold out, and SHALL report separately what each
definition admits that the other does not. A pooled score from one
definition's holdout SHALL NOT be reported as a difference against the
other's.

#### Scenario: The comparison is paired on shared races

- **WHEN** two definitions are compared
- **THEN** the difference is computed over the races present in both holdout
  sets
- **AND** it is accompanied by an interval obtained by resampling those
  shared races, and labelled undecided when that interval contains zero

#### Scenario: What each side drops is reported, not hidden

- **WHEN** two definitions are compared
- **THEN** the races each admits that the other excludes are reported with
  their count and the reason for exclusion
- **AND** each definition's score over its own exclusive races is reported, so
  the cost of narrowing the race set is visible

#### Scenario: Training sets differing is disclosed

- **WHEN** two definitions are compared on shared holdout races
- **THEN** the report states that the two models were also trained on
  different race sets
- **AND** the difference is not described as isolating the response
  definition alone

### Requirement: A definition comparison discloses how far the response moved

Because two definitions may measure different responses on the same race, a
comparison SHALL report the distribution of the difference between the two
responses over the shared holdout races, so that a change in error is not
read as a change in accuracy when part of it is the target moving.

#### Scenario: Response shift accompanies the error difference

- **WHEN** two definitions with different response columns are compared
- **THEN** the median and the tail of the per-race response difference over
  the shared races are reported alongside the RMSE difference
- **AND** the count of shared races whose response moved by more than a stated
  number of points is reported

#### Scenario: A comparison of two definitions sharing a response says so

- **WHEN** two definitions differ only in eligibility and share a response
  column
- **THEN** the response shift over the shared races is zero
- **AND** the comparison is reported as isolating the eligibility rule

### Requirement: The open questions are answered and published

The system SHALL run the comparisons needed to answer the deferred data and
variant questions and publish each result, whichever direction it falls: the
two-party response against the current one, each candidate write-in threshold
against the others, each no-Democrat treatment against the others, each
presidential-year bias variant against the baseline, and the candidate-count
variant against the baseline.

#### Scenario: Each question's answer names its evidence

- **WHEN** a question's result is published
- **THEN** it states the pooled difference, its interval, the holdout counts
  behind it, and the segment breakdown that motivated the question
- **AND** every figure in the writeup is present in a committed scorecard or
  comparison file

#### Scenario: Write-in thresholds are reported as a sweep, not a single test

- **WHEN** the write-in threshold is evaluated
- **THEN** the races admitted and the resulting scores are reported at each
  candidate threshold
- **AND** the threshold at which the admitted races stop changing is
  identified, so a threshold is not chosen from a range where it makes no
  difference

#### Scenario: The no-Democrat segment is reported against its own baseline

- **WHEN** a no-Democrat treatment is evaluated
- **THEN** its RMSE and interval coverage over holdout races with no
  Democratic candidate are reported against the published baseline figures
  for that segment
- **AND** a treatment that only removes those races from scoring is reported
  as having removed them rather than as having improved on them

#### Scenario: An undecided result is published as undecided

- **WHEN** a comparison's interval contains zero
- **THEN** the published conclusion states that the data does not separate the
  alternatives
- **AND** any subsequent adoption is attributed to a stated principle rather
  than to the measurement

## MODIFIED Requirements

### Requirement: Scores are broken out per fold and per segment

Every metric SHALL be reported for the pooled holdout, for each fold year, and
for each level of `office`, `is_special`, `pres_elec`, `redistricting_cycle`,
`no_dem_candidate`, and whether the race was admitted on a write-in, so that a
pooled result can be traced to where the model succeeds or fails. A segment
that a definition empties SHALL be reported as empty rather than omitted.

#### Scenario: Special elections are scored separately

- **WHEN** a variant is scored
- **THEN** its RMSE over the holdout special elections is reported apart from
  its RMSE over the holdout general elections
- **AND** the race count behind each is reported

#### Scenario: Races with no Democratic candidate are visible as a segment

- **WHEN** a variant is scored
- **THEN** its RMSE over holdout races with no Democratic candidate is
  reported apart from the rest
- **AND** the pooled figure discloses how much of its squared error those
  races contribute

#### Scenario: Presidential-year bias is visible as a segment

- **WHEN** a variant is scored
- **THEN** the mean signed error within presidential years and within
  non-presidential years is reported separately
- **AND** the gap between them is reported, since it is the quantity a bias
  variant sets out to close

#### Scenario: Small segments are reported with their counts

- **WHEN** a segment contains fewer races than a stated minimum
- **THEN** its metrics are still reported
- **AND** the row is marked as resting on a small sample

#### Scenario: A segment emptied by a definition is reported as empty

- **WHEN** a definition admits no races in a segment, such as no-Democrat
  races under a two-party definition
- **THEN** the segment appears with a count of zero
- **AND** it is not silently dropped from the scorecard

### Requirement: Scoring runs are reproducible and published

A scoring run SHALL be reproducible from committed inputs, a named definition,
and recorded seeds, and its outputs SHALL be committed as versioned files.

#### Scenario: A rerun reproduces the scorecard

- **WHEN** a scoring run is repeated from the same committed race table, the
  same definition, and the same recorded seeds
- **THEN** the published metrics are identical

#### Scenario: Per-race predictions are published, not only summaries

- **WHEN** a scoring run completes
- **THEN** the per-race holdout predictions are published, carrying the race
  identity, the definition, the fold, the variant, the point prediction, the
  interval bounds, the win probability, and the observed response
- **AND** any metric in the scorecard can be recomputed from them

#### Scenario: Definition-comparison outputs are published alongside

- **WHEN** two definitions are compared
- **THEN** the comparison is committed as a versioned file carrying the paired
  difference, its interval, the label, the shared and exclusive race counts,
  and the response-shift summary

#### Scenario: Fit diagnostics travel with the scores

- **WHEN** a fold's fit fails its sampling diagnostics
- **THEN** the scorecard marks the affected definition, fold, and variant
- **AND** the pooled result discloses that it includes a fold whose fit was
  flagged
