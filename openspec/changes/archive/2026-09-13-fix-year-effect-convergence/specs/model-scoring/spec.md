## ADDED Requirements

### Requirement: A rescoring reports what it changed and what it did not

Rescoring one variant SHALL leave every other variant's published metrics
unchanged, and the run SHALL verify that rather than assert it. Where a
rescoring does change another variant's numbers, the change SHALL be reported
with the reason, since the scorecard is the yardstick later work is measured
against.

#### Scenario: An untouched variant is verified unchanged

- **WHEN** one variant is rescored and its rows in the published outputs are
  replaced
- **THEN** every other variant's rows under every definition are byte-for-byte
  identical to the committed ones
- **AND** any difference is reported with the variant, the definition and the
  fold it occurred on

#### Scenario: A superseded result is not silently overwritten

- **WHEN** a variant's published result is replaced by a rescoring under a
  corrected specification
- **THEN** the writeup states that the earlier figures were produced by fits
  that failed diagnostics, and are superseded rather than reproduced

## MODIFIED Requirements

### Requirement: Two variants are compared on identical folds and races

Comparing two variants SHALL score both on the same fold schedule and the
same holdout races, and SHALL report the difference in pooled RMSE together
with a per-race paired comparison. Where the two variants are not nested ---
where one adds a term and also removes one --- the comparison SHALL state
that, so the difference is not read as the effect of a single term.

#### Scenario: The comparison is paired by race

- **WHEN** two variants are compared
- **THEN** the difference is computed from the two variants' errors on the
  same set of races
- **AND** a race dropped from one variant's holdout for any reason is dropped
  from the other's before comparing

#### Scenario: The comparison reports an interval, not only a point

- **WHEN** the RMSE difference between two variants is reported
- **THEN** it is accompanied by an interval obtained by resampling the
  holdout races
- **AND** the comparison is labelled undecided when that interval contains
  zero

#### Scenario: A variant is not declared better on a pooled difference alone

- **WHEN** one variant has a lower pooled RMSE but the interval spans zero
- **THEN** the published conclusion states that the data does not separate
  them, rather than naming a winner

#### Scenario: A non-nested comparison is labelled as such

- **WHEN** two compared variants do not stand in a subset relation on their
  predictors
- **THEN** the published comparison names the terms added and the terms
  removed
- **AND** it is not described as isolating a single term

### Requirement: Scoring runs are reproducible and published

A scoring run SHALL be reproducible from committed inputs, a named definition,
recorded seeds, and the recorded sampler settings and prior declarations, and
its outputs SHALL be committed as versioned files.

#### Scenario: A rerun reproduces the scorecard

- **WHEN** a scoring run is repeated from the same committed race table, the
  same definition, the same recorded seeds and the same recorded sampler
  settings
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

#### Scenario: Sampler settings travel with the diagnostics

- **WHEN** the fit diagnostics are published
- **THEN** each row carries the sampler settings and the prior declaration
  that produced it
- **AND** a reader can tell whether a passing fit required settings different
  from the defaults
