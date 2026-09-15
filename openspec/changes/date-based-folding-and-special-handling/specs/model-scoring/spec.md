## MODIFIED Requirements

### Requirement: Holdout predictions from all folds are pooled and scored together

The primary score SHALL be computed over the union of every fold's holdout
predictions, with each race weighted equally regardless of which fold
produced it or how many races that fold held out.

#### Scenario: Each holdout race is predicted exactly once

- **WHEN** a scoring run completes
- **THEN** every race held on a fold date has exactly one holdout prediction
- **AND** no race in the seed window has any

#### Scenario: Pooling is by race, not by fold

- **WHEN** the pooled score is computed
- **THEN** it is computed from the full set of holdout races directly
- **AND** not as an average of the per-fold scores, which under a date
  schedule would give a one-race special-election date the same weight as a
  general election deciding the whole chamber

### Requirement: Scores are broken out per fold and per segment

Every metric SHALL be reported for the pooled holdout, for each fold date, and
for each level of `office`, `is_special`, `pres_elec`, `redistricting_cycle`,
`no_dem_candidate`, and whether the race was admitted on a write-in, so that a
pooled result can be traced to where the model succeeds or fails. A segment
that a definition empties SHALL be reported as empty rather than omitted.

Because every special election in the record falls off the presidential
general date, `pres_elec` and `is_special` are not independent: the
`pres_elec = False` races are a mixture of midterm general elections and
special elections. Metrics broken out by ballot timing SHALL therefore
distinguish three segments rather than two, so that neither figure silently
carries the other population.

#### Scenario: Ballot timing is reported in three segments

- **WHEN** a variant is scored
- **THEN** its metrics are reported separately for presidential-date general
  elections, for non-presidential-date general elections, and for special
  elections
- **AND** the count behind each is reported
- **AND** no published figure describes the union of midterm generals and
  specials as "non-presidential" without saying so

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

### Requirement: Two variants are compared on identical folds and races

Comparing two variants SHALL score both on the same fold schedule and the
same holdout races, and SHALL report the difference in pooled RMSE together
with a per-race paired comparison. Where the two variants are not nested ---
where one adds a term and also removes one --- the comparison SHALL state
that, so the difference is not read as the effect of a single term.

A composite variant, which predicts different races from different component
fits, SHALL be comparable to a single-fit variant on this procedure provided
every race in the comparison is predicted exactly once by exactly one
component. A comparison involving a composite variant SHALL name the
components and state which races each one predicted.

#### Scenario: The comparison is paired by race

- **WHEN** two variants are compared
- **THEN** the difference is computed from the two variants' errors on the
  same set of races
- **AND** a race dropped from one variant's holdout for any reason is dropped
  from the other's before comparing

#### Scenario: A composite variant is compared race by race

- **WHEN** a composite variant is compared to a single-fit variant
- **THEN** each race's error for the composite comes from whichever component
  predicted it
- **AND** the published comparison names the components and the race
  population each one covered
- **AND** it is labelled non-nested, since the two arms do not stand in a
  subset relation on their predictors

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

### Requirement: A rescoring reports what it changed and what it did not

Rescoring one variant SHALL leave every other variant's published metrics
unchanged, and the run SHALL verify that rather than assert it. Where a
rescoring does change another variant's numbers, the change SHALL be reported
with the reason, since the scorecard is the yardstick later work is measured
against.

A change to the fold schedule itself SHALL be treated as changing every
variant's numbers. Such a run SHALL NOT attempt the unchanged-variant
verification, and SHALL instead state that the schedule changed and that every
previously published figure is superseded.

#### Scenario: An untouched variant is verified unchanged

- **WHEN** one variant is rescored and its rows in the published outputs are
  replaced
- **THEN** every other variant's rows under every definition are byte-for-byte
  identical to the committed ones
- **AND** any difference is reported with the variant, the definition and the
  fold it occurred on

#### Scenario: A schedule change supersedes every published figure

- **WHEN** the fold schedule changes and every variant is rescored under it
- **THEN** the run reports that the schedule changed rather than reporting
  per-variant drift
- **AND** the published writeups state that the earlier figures were computed
  on the previous schedule and are superseded rather than reproduced

#### Scenario: A superseded result is not silently overwritten

- **WHEN** a variant's published result is replaced by a rescoring under a
  corrected specification
- **THEN** the writeup states that the earlier figures were produced by fits
  that failed diagnostics, and are superseded rather than reproduced

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
- **THEN** the fold dates remain every election date after the seed cutoff
  that the definition admits races on
- **AND** a fold date the definition empties is recorded as skipped rather
  than omitted silently

#### Scenario: Holdout counts are published per definition

- **WHEN** a scoring run completes
- **THEN** the pooled holdout race count, the holdout special-election count,
  and the smallest training fold size under that definition are reported
- **AND** a definition that shrinks the holdout is visible as having done so

## ADDED Requirements

### Requirement: Evaluation is rolling-origin over election dates

The system SHALL evaluate a variant by fitting it once per election date on
every race held strictly before that date and predicting only the races held
on that date. The training window SHALL expand with each successive fold
rather than sliding.

A fold SHALL correspond to one election date, not to one calendar year. A race
held earlier in the same calendar year as a fold's date SHALL be in that
fold's training set, because its result was known before the fold's election
occurred.

#### Scenario: A fold trains only on earlier dates

- **WHEN** the fold for election date `D` is run
- **THEN** the training races are every race in the table with
  `election_date` strictly less than `D`
- **AND** the holdout races are every race in the table with `election_date`
  equal to `D`
- **AND** no race held on `D` or later appears in the training set

#### Scenario: An earlier election in the same year trains the fold

- **WHEN** the fold for a November general election is run and special
  elections were held earlier that calendar year
- **THEN** those earlier special elections appear in the fold's training set
- **AND** they do not appear in its holdout

#### Scenario: Dates are not blended into a single holdout

- **WHEN** two elections in the same calendar year are held on different dates
- **THEN** they fall in different folds
- **AND** neither fold's metrics mix races decided on different days

#### Scenario: Splitting by date rather than randomly

- **WHEN** folds are constructed
- **THEN** every race sharing an election date falls on the same side of the
  split
- **AND** a district that recurs across cycles never has one of its races in
  training and another in the same fold's holdout

### Requirement: The fold schedule is every election date after the seed cutoff

The fold dates SHALL be every distinct `election_date` in the race table on or
after the seed cutoff of 2014-01-01. Races held before that cutoff --- those of
2010 through 2013 --- SHALL form the seed training window and SHALL NOT be
scored, preserving the seed window of the previous schedule unchanged. The schedule SHALL be derived
from the dates present in the table rather than enumerated in code, so that
adding an election year adds folds without a code change.

A fold date carrying only special elections SHALL be a scored fold on the same
footing as a general-election date. Its holdout may hold a single race.

#### Scenario: The schedule is derived from the table

- **WHEN** the fold schedule is constructed
- **THEN** it contains one fold per distinct election date at or after the
  seed cutoff
- **AND** no election date present in the table after the cutoff is absent
  from the schedule
- **AND** adding a later election year to the table adds folds without any
  change to the schedule's definition

#### Scenario: Special-election dates are scored folds

- **WHEN** an election date carries only special elections
- **THEN** it is a fold, and its races enter the pooled holdout
- **AND** its fold row is marked as a small sample rather than suppressed

#### Scenario: Seed races are training-only

- **WHEN** the fold schedule is run
- **THEN** no race held before 2014-01-01 appears in any holdout set
- **AND** every such race is available to every fold's training set

#### Scenario: The published schedule states its size

- **WHEN** the fold schedule is published
- **THEN** it reports the number of folds, the number of general-election
  dates and special-election dates among them, and the holdout race count of
  each
- **AND** the training window bounds of each fold are reported as dates

### Requirement: The three special-election handling arms are compared and published

The system SHALL score three arms for special-election handling and publish
their comparison, whichever direction it falls:

- an arm that trains and scores on all races and declares `is_special`;
- an arm that trains and scores on all races and declares no `is_special`
  term;
- a composite arm of two fits --- a general model that excludes special
  elections from both training and holdout, and a special model fit on all
  races with `is_special` declared --- in which each race is predicted by the
  component matching its own `is_special` value.

The three arms SHALL cover the same holdout races, so their comparison is
paired race by race.

#### Scenario: All three arms score the same races

- **WHEN** the three arms are scored under one definition
- **THEN** each arm produces exactly one prediction for every holdout race
  that all three admit
- **AND** the comparison is computed on that shared set
- **AND** any race an arm cannot predict is dropped from all three before
  comparing, and the count dropped is reported

#### Scenario: The composite arm routes each race to one component

- **WHEN** the composite arm predicts a holdout race
- **THEN** a special election is predicted by the special model and a general
  election by the general model
- **AND** no race is predicted by both components
- **AND** the published per-race predictions record which component produced
  each one

#### Scenario: The general component never sees a special election

- **WHEN** the composite arm's general model is fit for a fold
- **THEN** its training races exclude every special election
- **AND** its holdout excludes every special election

#### Scenario: The arms are compared on general and special races separately

- **WHEN** the three-arm comparison is published
- **THEN** the pooled paired difference between each pair of arms is reported
  with its interval and its decided or undecided label
- **AND** the difference restricted to general elections and the difference
  restricted to special elections are reported alongside it
- **AND** the holdout count behind each is stated

#### Scenario: An undecided result is published as undecided

- **WHEN** the interval on a paired difference between two arms contains zero
- **THEN** the published conclusion states that the data does not separate
  them
- **AND** no arm is adopted on the point estimate alone

## REMOVED Requirements

### Requirement: The fold schedule covers every election year from 2014 onward

**Reason**: The schedule is no longer enumerated by year. It is derived from
the distinct election dates in the race table, which is what the replacement
requirement "The fold schedule is every election date after the seed cutoff"
specifies. The enumerated year list also had to be edited by hand for each new
election year, which the derived schedule removes.

**Migration**: The ten fold years 2014-2018 and 2020-2024 become 25 fold
dates: the six general-election dates 2014-11-04, 2016-11-08, 2018-11-06,
2020-11-03, 2022-11-08 and 2024-11-05, plus the 19 special-election dates
falling in or after 2014. The seed window is unchanged --- the same 199 races
of 2010 through 2013 --- so the holdout population is exactly the 434 races
the year schedule scored, redistributed across 25 folds instead of 10. 2019 no
longer needs a stated exception, because a year with no races contributes no
dates.

### Requirement: The is_special comparison is run and published

**Reason**: Superseded by the three-arm comparison. The original requirement
asked only whether adding an `is_special` term to the baseline helps, which
presumes special elections belong in the same model as general elections ---
the assumption now under test.

**Migration**: The `baseline` versus `baseline_special` comparison becomes
arm B versus arm A of the three-arm comparison, which retains both the pooled
figures and the special-election segment breakout the original required. Arm
C adds the possibility the original could not express.

### Requirement: Evaluation is rolling-origin with an expanding training window

**Reason**: The requirement and every scenario under it are stated in terms of
a fold *year*, which names nothing once a fold is one election date. Renamed
rather than reworded in place, because "prior years" and "splitting by year"
describe the boundary that is being replaced, not the one that replaces it.

**Migration**: Replaced by "Evaluation is rolling-origin over election dates",
which keeps the rolling-origin and expanding-window guarantees unchanged and
restates the split in terms of `election_date`. The scenario "A fold trains
only on prior years" becomes "A fold trains only on earlier dates" and
"Splitting by year rather than randomly" becomes "Splitting by date rather
than randomly"; two scenarios are added covering the same-year earlier
election and the prohibition on blending dates into one holdout.
