## MODIFIED Requirements

### Requirement: Scores are broken out per fold and per segment

Every metric SHALL be reported for the pooled holdout, for each fold date, and
for each level of `office`, `is_special`, `pres_elec`, `ballot_timing`,
`redistricting_cycle`, `no_dem_candidate`, and whether the race was admitted on
a write-in, so that a pooled result can be traced to where the model succeeds
or fails. A segment that a definition empties SHALL be reported as empty rather
than omitted.

Because every special election in the record falls off the presidential
general date, `pres_elec` and `is_special` are not independent: the
`pres_elec = False` races are a mixture of midterm general elections and
special elections. Metrics broken out by ballot timing SHALL therefore
distinguish those populations rather than blending them, so that neither
figure silently carries the other.

The segment SHALL use the same level set as the `ballot_timing` predictor, so
that a segment row and a coefficient describing the same population cannot
disagree about what that population is. A definition that scores no special
election SHALL report the `special` level with a count of zero rather than
omitting it.

#### Scenario: Ballot timing is reported by its declared levels

- **WHEN** a variant is scored
- **THEN** its metrics are reported separately for each `ballot_timing` level
- **AND** the count behind each is reported
- **AND** no published figure describes the union of midterm generals and
  specials as "non-presidential" without saying so

#### Scenario: The segment and the predictor agree on their levels

- **WHEN** a variant declaring `ballot_timing` is scored
- **THEN** the segment rows and the variant's coefficients are labelled with
  the same level names
- **AND** a race contributes to the segment row matching the level its own
  predictor carried

#### Scenario: Special elections are scored separately

- **WHEN** a variant is scored
- **THEN** its RMSE over the holdout special elections is reported apart from
  its RMSE over the holdout general elections
- **AND** the race count behind each is reported
- **AND** a definition that scores none reports that count as zero

#### Scenario: Races with no Democratic candidate are visible as a segment

- **WHEN** a variant is scored
- **THEN** its RMSE over holdout races with no Democratic candidate is
  reported apart from the rest
- **AND** the pooled figure discloses how much of its squared error those
  races contribute

#### Scenario: Presidential-year bias is visible as a segment

- **WHEN** a variant is scored
- **THEN** the mean signed error within presidential-date general elections
  and within non-presidential-date general elections is reported separately
- **AND** the gap between them is reported, since it is the quantity a bias
  variant sets out to close
- **AND** the gap is computed from general elections only, so that the
  special-election segment cannot move it

#### Scenario: Small segments are reported with their counts

- **WHEN** a segment contains fewer races than a stated minimum
- **THEN** its metrics are still reported
- **AND** the row is marked as resting on a small sample

#### Scenario: A segment emptied by a definition is reported as empty

- **WHEN** a definition admits no races in a segment, such as no-Democrat
  races under a two-party definition
- **THEN** the segment appears with a count of zero
- **AND** it is not silently dropped from the scorecard

## ADDED Requirements

### Requirement: A generals-only run reports the population it scored

A scoring run under a definition that marks special elections train-only SHALL
report that its holdout is general elections only, together with the count of
special elections retained in training. A reader SHALL be able to tell from the
published outputs alone that the pooled figure covers general elections and
what the model was fit on.

#### Scenario: The holdout population is stated, not inferred

- **WHEN** a run under the generals-only definition completes
- **THEN** its published summary states the holdout race count, that it holds
  no special elections by declaration, and the count of special elections in
  the training sets
- **AND** that is distinguishable from a run whose holdout happens to contain
  no specials

#### Scenario: A pooled figure is not compared across holdout populations

- **WHEN** a generals-only pooled figure is placed beside one from a
  definition that scores specials
- **THEN** the comparison is made on the races both hold out, under the
  existing definition-comparison procedure
- **AND** the races exclusive to each side are reported separately, so a
  definition that declines to score its hardest segment is not credited for
  the resulting lower error
