## MODIFIED Requirements

### Requirement: A definition states four things

A definition SHALL state: which races are eligible, which column is the
response, the vote share at or above which a write-in counts as a candidate,
and how races with no Democratic candidate are treated. Each SHALL be stated
explicitly, with no parameter left to a default buried in the fitting code.

A definition MAY additionally mark a class of race **train-only** on grounds
of the kind of contest it is rather than of its response --- excluded from
every holdout while retained in every fold's training set. That treatment
SHALL be stated in the same explicit way, and the class SHALL be named, so
that "this definition does not score special elections" and "this definition
does not admit special elections" are distinguishable in the declaration and
not only in the counts.

#### Scenario: Every parameter is explicit

- **WHEN** a definition is declared
- **THEN** its eligibility rule, response column, write-in threshold, and
  no-Democrat treatment are all recorded
- **AND** two definitions that differ in any one of them are distinct
  definitions

#### Scenario: A train-only class is declared, not inferred

- **WHEN** a definition marks a class of race train-only
- **THEN** the class is named in the definition's own declaration
- **AND** the published record distinguishes it from a definition that
  excludes that class from training as well

#### Scenario: The write-in threshold governs both decisions it affects

- **WHEN** a definition sets a write-in threshold
- **THEN** the same threshold decides whether a write-in makes a race
  contested and whether that write-in's votes enter the response denominator
- **AND** a write-in cannot be excluded from one decision while counting
  toward the other

### Requirement: The definitions under test are enumerated

The system SHALL provide, at minimum, a definition reproducing the rule in
force before this change, a two-party definition restricted to races with
both a Democrat and a Republican, a definition admitting write-ins above a
stated threshold, a definition that keeps races with no Republican by
comparing the Democrat against the strongest remaining candidate, and a
definition scoring general elections only. Each SHALL be scorable through the
same interface.

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

#### Scenario: The generals-only definition scores no special election

- **WHEN** the generals-only definition is applied
- **THEN** it admits the same races as the adopted definition
- **AND** every special election among them is marked train-only
- **AND** no special election appears in any fold's holdout, while every one
  of them appears in every fold's training set that precedes it

#### Scenario: Each definition reports what it admits and drops

- **WHEN** a definition is applied
- **THEN** the count of races admitted, the count dropped, and the reason each
  race was dropped are reported
- **AND** the counts of holdout races and holdout special elections under that
  definition are reported, since specials are the scarce segment
- **AND** a definition whose holdout special-election count is zero by
  declaration is distinguishable from one that simply admitted none
