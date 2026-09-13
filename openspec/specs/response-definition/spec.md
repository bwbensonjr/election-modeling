## Purpose

Defines what counts as a modellable race and what the Democratic margin is
measured against, as a named configuration selected over one published table
rather than a property baked into it, so that competing answers can be scored
against each other without rebuilding the training data for each.

## Requirements

### Requirement: A data definition is a named, selectable configuration

The system SHALL express the eligibility and response rules as named data
definitions. Applying a definition SHALL be a selection of rows and a choice
of response column over the published training table, and SHALL NOT require
rebuilding or re-collecting that table.

#### Scenario: A definition is applied without rebuilding

- **WHEN** a definition is applied to the published race table
- **THEN** the resulting race set and response are derived from columns the
  table already carries
- **AND** no collection stage is re-run

#### Scenario: A definition is identified by name in every output

- **WHEN** any table, scorecard, or report is produced under a definition
- **THEN** it records the name of the definition it was produced under
- **AND** an output produced under two different definitions is
  distinguishable without inspecting its contents

### Requirement: A definition states four things

A definition SHALL state: which races are eligible, which column is the
response, the vote share at or above which a write-in counts as a candidate,
and how races with no Democratic candidate are treated. Each SHALL be stated
explicitly, with no parameter left to a default buried in the fitting code.

#### Scenario: Every parameter is explicit

- **WHEN** a definition is declared
- **THEN** its eligibility rule, response column, write-in threshold, and
  no-Democrat treatment are all recorded
- **AND** two definitions that differ in any one of them are distinct
  definitions

#### Scenario: The write-in threshold governs both decisions it affects

- **WHEN** a definition sets a write-in threshold
- **THEN** the same threshold decides whether a write-in makes a race
  contested and whether that write-in's votes enter the response denominator
- **AND** a write-in cannot be excluded from one decision while counting
  toward the other

### Requirement: A definition never consults the outcome

Eligibility SHALL depend only on the candidates in a race and their vote
shares relative to one another, never on the value of the response being
modelled or on which side won. A definition SHALL NOT admit or exclude a race
on a criterion that encodes its outcome.

#### Scenario: Filtering is outcome-blind

- **WHEN** a definition's eligibility rule is applied
- **THEN** it references candidate presence, party, and write-in share only
- **AND** no rule references the observed margin, the winner, or the
  competitiveness of the race

### Requirement: The definitions under test are enumerated

The system SHALL provide, at minimum, a definition reproducing the rule in
force before this change, a two-party definition restricted to races with
both a Democrat and a Republican, a definition admitting write-ins above a
stated threshold, and a definition that keeps races with no Republican by
comparing the Democrat against the strongest remaining candidate. Each SHALL
be scorable through the same interface.

#### Scenario: The current rule remains available as a definition

- **WHEN** the definition reproducing the pre-change rule is applied
- **THEN** it admits races on the ballot-line count alone, counts every named
  candidate in the denominator, and keeps races with no Democratic candidate
  under the negated convention
- **AND** the race set it selects is the one the published baseline was
  scored on

#### Scenario: The two-party definition excludes by construction

- **WHEN** the two-party definition is applied
- **THEN** only races carrying both a Democrat and a Republican are admitted
- **AND** the response is the two-party margin, computed on the same
  denominator as `PVI_N`
- **AND** races with no Democratic candidate are absent without needing a
  separate rule

#### Scenario: Each definition reports what it admits and drops

- **WHEN** a definition is applied
- **THEN** the count of races admitted, the count dropped, and the reason each
  race was dropped are reported
- **AND** the counts of holdout races and holdout special elections under that
  definition are reported, since specials are the scarce segment

### Requirement: The no-Democrat treatment is a stated choice among alternatives

A definition SHALL treat races with no Democratic candidate in one of three
declared ways: keep them and carry an indicator that the model may use,
exclude them from both training and scoring, or exclude them from scoring
while retaining them in training. The treatment SHALL be recorded rather than
implied by the eligibility rule.

#### Scenario: Exclusion from scoring is distinguished from exclusion from training

- **WHEN** a definition excludes races with no Democratic candidate from
  scoring only
- **THEN** those races still contribute to each fold's training set
- **AND** they produce no holdout predictions and enter no metric

#### Scenario: A kept no-Democrat race is identifiable downstream

- **WHEN** a definition keeps races with no Democratic candidate
- **THEN** the indicator distinguishing them remains available as a predictor
- **AND** the scoring segment reporting them separately is populated

### Requirement: One definition is adopted and the decision is recorded

The system SHALL designate exactly one definition as the published default,
and SHALL record the evidence behind that designation, including the case
where the measured differences did not separate the candidates and the
decision rested on a stated principle instead.

#### Scenario: The adopted definition is the default for later work

- **WHEN** a scoring run is requested without naming a definition
- **THEN** the adopted definition is used
- **AND** its name appears in the run's outputs, so the default is never
  silent

#### Scenario: An undecided comparison still yields a decision

- **WHEN** the comparison between two definitions is labelled undecided
- **THEN** the published record states that the data did not separate them
- **AND** states the principle on which the adopted definition was chosen,
  rather than presenting the choice as an empirical result

#### Scenario: The superseded definitions remain scorable

- **WHEN** a definition other than the adopted one is named
- **THEN** it can still be applied and scored
- **AND** the decision can be revisited without re-running collection
