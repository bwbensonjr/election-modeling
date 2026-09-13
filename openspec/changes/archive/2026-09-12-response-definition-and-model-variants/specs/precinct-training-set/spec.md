## ADDED Requirements

### Requirement: Each row carries a two-party response alongside the established one

Each row SHALL carry `dem_margin_two_party`, the Democratic share of the
combined Democratic and Republican vote minus the Republican share, in
percentage points, in addition to `dem_margin`. This response is measured on
the same denominator `PVI_N` is, so that response and predictor are
definitionally parallel.

#### Scenario: Both responses are published for every eligible row

- **WHEN** a training row is published for a race carrying both a Democrat and
  a Republican
- **THEN** `dem_margin` and `dem_margin_two_party` are both numeric
- **AND** the two agree exactly when no candidate outside the two major
  parties received votes in that precinct

#### Scenario: The two-party response is absent where it is undefined

- **WHEN** a race carries no Democrat, or no Republican, so that one side of
  the two-party denominator is empty
- **THEN** `dem_margin_two_party` is published as missing rather than as zero
  or as a fallback to `dem_margin`

#### Scenario: Two-party vote counts are published, not only the share

- **WHEN** a training row is published
- **THEN** it carries the Democratic and Republican vote counts behind the
  two-party response
- **AND** the race-grain two-party margin is recoverable by summing those
  counts across the race's precincts

### Requirement: Rows disclose write-in participation

Each row SHALL record the votes cast for write-in candidates named in the
returns and the write-in share of named-candidate votes for its race, taking
the write-in designation from the published candidate records rather than
inferring it from the vote pattern.

#### Scenario: A write-in candidate is identifiable as such

- **WHEN** a race includes a candidate recorded as a write-in
- **THEN** that candidate's votes are separable from ballot-line votes in the
  published row
- **AND** the race's write-in share of named-candidate votes is recorded

#### Scenario: The unnamed all-others bucket is not treated as a write-in candidate

- **WHEN** a precinct's returns include an aggregate all-others total with no
  candidate attached
- **THEN** it does not count toward any write-in candidate's share
- **AND** it remains outside the response denominator, as before

### Requirement: Rows carry the flags an eligibility rule selects on

Each row SHALL carry, for its race, whether both a Democrat and a Republican
are present, whether the race would be contested on ballot lines alone, and
the strongest admitted write-in's share, so that any eligibility rule can be
applied to the published table without recollection.

#### Scenario: A definition is applied from published columns alone

- **WHEN** an eligibility rule is applied to the published table
- **THEN** every input the rule needs is a column the table carries
- **AND** no candidate-level source outside the table is consulted

## MODIFIED Requirements

### Requirement: Uncontested races are excluded

Races SHALL be excluded from the training table unless they carry at least two
candidates, where a write-in counts as a candidate when its share of
named-candidate votes reaches a stated threshold. The threshold SHALL be
recorded with the published table. A race carrying a single ballot line and no
write-in at or above the threshold SHALL be excluded.

#### Scenario: Single-candidate race produces no rows

- **WHEN** a legislative race has only one candidate, counting admitted
  write-ins
- **THEN** no rows for that race appear in the training table

#### Scenario: A write-in above the threshold makes a race contested

- **WHEN** a race carries one ballot line and a write-in whose share of
  named-candidate votes is at or above the threshold
- **THEN** the race is admitted to the training table
- **AND** the row records that the race was admitted on a write-in rather
  than on ballot lines

#### Scenario: A protest write-in below the threshold does not

- **WHEN** a race carries one ballot line and a write-in below the threshold
- **THEN** the race remains excluded
- **AND** it appears in the excluded-races report with the write-in's share

#### Scenario: The threshold is recorded, not implicit

- **WHEN** the training table is published
- **THEN** the threshold in force is recorded alongside it
- **AND** the count of races admitted by a write-in at that threshold is
  reported

### Requirement: Precinct margin follows the established district definition

`dem_margin` SHALL be the Democratic candidate's vote share in the precinct
minus the share of the strongest non-Democratic candidate in that race,
expressed in percentage points, on a denominator of votes cast for named
candidates whose write-ins meet the threshold. Where the race has no
Democratic candidate, the margin SHALL be the negation of the Republican share
minus the strongest remaining share.

#### Scenario: The comparison candidate is fixed at race level

- **WHEN** the strongest non-Democratic candidate is determined for a race
- **THEN** the same candidate is used as the comparison for every precinct in
  that race, rather than being re-selected per precinct

#### Scenario: An admitted write-in counts in the denominator

- **WHEN** a race carries a write-in at or above the threshold
- **THEN** that write-in's votes are included in the denominator of every
  precinct's share
- **AND** the write-in is eligible to be the comparison candidate on the same
  terms as a ballot-line candidate

#### Scenario: A write-in below the threshold is excluded from the denominator

- **WHEN** a race carries a write-in below the threshold
- **THEN** its votes are excluded from the denominator, so that the same
  threshold governs eligibility and the margin consistently
- **AND** the excluded votes remain published on the row, so the alternative
  margin is recoverable

#### Scenario: Margin aggregates to the published district margin

- **WHEN** a race's precinct vote counts are summed to the district and the
  margin recomputed
- **THEN** the result matches the district-level `dem_margin` derived from
  `ma-election-db` for that race, within rounding tolerance, for races whose
  candidate set is unaffected by the threshold
- **AND** a race whose candidate set the threshold changes is reported as a
  deliberate divergence rather than as a validation failure
