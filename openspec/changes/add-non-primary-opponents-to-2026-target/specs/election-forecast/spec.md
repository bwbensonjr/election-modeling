# Spec Delta

## MODIFIED Requirements

### Requirement: A forecast target is response-free and complete

The system SHALL accept a target table with exactly one row per known contested
State Representative or State Senate race. Each row SHALL identify the
election, office, district, election date, Democratic candidate, comparison
candidate, incumbent status, 2024 PVI, ballot timing, finance completeness,
and the provenance of each input, and SHALL NOT contain an observed margin,
winner, vote total, or other election outcome.

For a forecast prepared after the state primary but before the general
election, final primary results MAY be used to identify the nominees who form
the general-election roster. The prohibition on outcomes applies to the target
general election and to any historical result fields that are unnecessary for
constructing that roster; it does not prohibit already-published primary
nomination results.

A race is contested when a Democratic candidate and at least one
non-Democratic candidate appear on the general-election ballot, whether the
non-Democrat was nominated in a primary or qualified by nomination papers.

#### Scenario: The 2026 target roster validates

- **WHEN** the committed 2026 target table is validated
- **THEN** every known contested legislative race appears exactly once
- **AND** every required pre-election field and its provenance are present

#### Scenario: An outcome-bearing target is refused

- **WHEN** a target table contains a result, winner, vote total, or observed
  response
- **THEN** forecasting is refused with the leaking column named

#### Scenario: The comparison candidate is selected before results

- **WHEN** a race has more than one non-Democratic candidate
- **THEN** the target names its comparison candidate under a documented rule
  using only pre-election information
- **AND** the eventual strongest candidate by votes is not used retrospectively
  to redefine the locked forecast

#### Scenario: Primary results establish the pre-election roster

- **WHEN** the general-election candidate artifact will not be published until
  after the general election
- **THEN** the target roster is derived from the published primary candidate
  roster, final primary nomination results, and the reviewed nomination-paper
  candidate supplement
- **AND** no target general-election vote, winner, or result is required

#### Scenario: A nomination-paper opponent makes a race contested

- **WHEN** a Democratic nominee's only general-election opponent qualified by
  nomination papers
- **THEN** the race appears in the target with that candidate as the
  comparison candidate and the candidate's ballot designation as its party
- **AND** the row's nominee basis records that the candidate came from the
  nomination-paper supplement

## ADDED Requirements

### Requirement: Nomination-paper candidates come from a reviewed source

The system SHALL read general-election legislative candidates who did not
qualify through a primary from a committed, reviewed supplement. Each row
SHALL carry office, canonical district, name, ballot designation, residence
municipality, incumbency, and the source page URL and as-of date. The target
SHALL record the supplement's content digest in its candidate provenance.

#### Scenario: The supplement is part of the recorded provenance

- **WHEN** a target is built with the supplement
- **THEN** the target's candidate source names both the primary artifacts and
  the supplement
- **AND** the candidate source digest changes when the supplement changes

#### Scenario: A malformed supplement is refused

- **WHEN** a supplement row lacks a district, name, ballot designation,
  municipality, or source as-of date, or duplicates a primary nominee
- **THEN** the target build fails naming the offending row

#### Scenario: Candidates in races without a Democrat are ignored

- **WHEN** a supplement candidate stands in a district with no Democratic
  nominee
- **THEN** no target row is created for that district

### Requirement: The comparison candidate follows the adopted definition

The comparison candidate SHALL be the Republican where one is on the ballot,
matching the adopted `two_party_or_strongest` training response. Where no
Republican stands, it SHALL be the single non-Democratic candidate. Only a
race with no Republican and several non-Democrats SHALL require an explicit
pre-election review.

#### Scenario: A Republican is chosen over a third candidate without review

- **WHEN** a race has a Democrat, a Republican, and an unenrolled or
  minor-party candidate
- **THEN** the Republican is the comparison candidate
- **AND** no review is required and the review status says so

#### Scenario: A sole non-Republican opponent is chosen without review

- **WHEN** a race has a Democrat and exactly one non-Democrat who is not a
  Republican
- **THEN** that candidate is the comparison candidate without review

#### Scenario: Several non-Republican opponents require review

- **WHEN** a race has a Democrat, no Republican, and two or more other
  candidates
- **THEN** the target build stops until a pre-election review names the
  comparison candidate

#### Scenario: A non-Democratic incumbent is coded as the model expects

- **WHEN** the comparison candidate is an incumbent of any non-Democratic
  designation
- **THEN** the race's incumbent status is `GOP_Incumbent`, matching the
  training data's grouping of non-Democratic incumbents

### Requirement: A revised target is published as a new forecast revision

A change to the set of target races after a snapshot is published SHALL be
written as a new target, finance file, and snapshot under a distinct revision
identifier. The revision SHALL keep its horizon's finance cutoff and SHALL
NOT modify any earlier target, finance file, snapshot, or interactive bundle.

#### Scenario: The expanded 2026 forecast is a distinct revision

- **WHEN** the 57-race 2026 target is forecast at the 14-day horizon
- **THEN** it is published under a revision distinct from `14d`
- **AND** its finance cutoff is the `14d` horizon's 2026-10-20 cutoff

#### Scenario: Earlier snapshots stay reproducible and scorable

- **WHEN** the revision is published
- **THEN** the `60d` and `14d` snapshots, and the target and finance files their
  manifests digest, remain byte-for-byte unchanged
- **AND** each snapshot can still be regenerated and verified from its own
  recorded inputs and later scored against certified results

#### Scenario: The revision states what changed

- **WHEN** the revision's manifest is inspected
- **THEN** it names the revision it supersedes and the races it adds
