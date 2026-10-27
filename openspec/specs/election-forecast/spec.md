## Purpose

Defines how a response-free Massachusetts legislative target roster becomes a
reproducible, horizon-specific forecast and later a prospective evaluation.

## Requirements

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

### Requirement: A forecast fits only completed prior elections

A forecast SHALL fit its declared variant and definition on every eligible
historical race held strictly before the target election date. It SHALL NOT
reuse the fit from the final backtest fold, omit a completed eligible election,
or include any target-date result.

#### Scenario: The 2026 fit includes 2024

- **WHEN** the November 2026 forecast is fit
- **THEN** eligible races through the November 2024 general election are in
  training
- **AND** no race on or after the 2026 target date is in training

#### Scenario: A full-history fit is reproducible

- **WHEN** the same target, historical table, variant, definition, and seed
  are supplied again
- **THEN** the fit and forecast outputs are identical

### Requirement: Every dated predictor respects the forecast horizon

Each forecast SHALL declare an information horizon and an exact cutoff date.
Every dated target predictor SHALL have been measured no later than that
cutoff, and historical evaluation of that forecast SHALL use the corresponding
relative horizon rather than a later information set.

#### Scenario: The 60-day forecast uses only 60-day information

- **WHEN** the initial forecast is published at the 60-day horizon
- **THEN** no target finance amount includes activity after its declared
  60-day cutoff
- **AND** its selected model was evaluated with 60-day historical predictors

#### Scenario: The 14-day update is a separate forecast

- **WHEN** finance becomes available at the 14-day horizon
- **THEN** a new forecast is published with the new cutoff
- **AND** the 60-day forecast remains unchanged and addressable

### Requirement: Every target race receives one disclosed prediction

The operational forecast SHALL produce exactly one predictive distribution for
every valid target race. Where the dated-money component cannot be used because
candidate finance is unavailable, the race SHALL be routed to the declared
no-money fallback rather than omitted or assigned an imputed zero.

#### Scenario: Complete finance uses the money component

- **WHEN** both candidates in a target race have complete finance at the
  forecast horizon
- **THEN** the race is predicted by the declared money component
- **AND** the published row names that component

#### Scenario: Unavailable finance uses the fallback

- **WHEN** either candidate's finance is unavailable at the forecast horizon
- **THEN** the race is predicted by the declared no-money component
- **AND** the row records why the fallback was used

#### Scenario: No target race is silently lost

- **WHEN** forecast generation finishes
- **THEN** the output race identities equal the validated target identities
- **AND** a missing, duplicated, or multiply routed race fails the run

### Requirement: A forecast snapshot is immutable and self-describing

Each forecast SHALL be written as a new snapshot identified by election and
information horizon. It SHALL carry the model variant and component,
definition, training cutoff, finance cutoff, input provenance or content
digest, seed, repository commit, point margin, predictive interval, and
Democratic win probability needed to reproduce and interpret every row.

#### Scenario: A snapshot can be reproduced from its record

- **WHEN** a published forecast row is inspected
- **THEN** its inputs, fit declaration, cutoff, seed, and code revision are
  identifiable without consulting unrecorded state

#### Scenario: Publishing does not overwrite an earlier horizon

- **WHEN** a second forecast is published for the same election
- **THEN** it is written under a distinct horizon or timestamp
- **AND** the earlier snapshot remains byte-for-byte unchanged

### Requirement: Forecasts disclose extrapolation from historical support

The system SHALL compare each target race's predictors with the historical
training support used by its component. A race outside that support, or a
categorical level whose reusable effect has not been validated on a later
election, SHALL remain forecastable but SHALL carry a specific warning.

#### Scenario: An extreme target value is flagged

- **WHEN** a target PVI or money contrast lies outside the corresponding
  training range
- **THEN** the forecast row names the predictor and the exceeded range
- **AND** the prediction is not presented as ordinary interpolation

#### Scenario: A one-election timing effect is disclosed

- **WHEN** a forecast uses a timing level observed on only one historical
  general-election date
- **THEN** the snapshot reports that election-date count
- **AND** the timing effect is not described as independently validated

### Requirement: Aggregate forecasts preserve shared posterior variation

The system SHALL derive chamber and office summaries from aligned posterior
draws across target races, preserving any shared parameter or election-level
variation represented by the fitted model. It SHALL NOT construct aggregate
uncertainty by independently resampling each race's marginal win probability.

#### Scenario: Chamber draws use coherent race draws

- **WHEN** expected Democratic seats and a seat-count interval are published
- **THEN** each simulated chamber total uses one aligned posterior draw across
  all races
- **AND** the race-level predictions remain traceable from that total

#### Scenario: Offices are reported separately

- **WHEN** aggregate results are published
- **THEN** State Representative and State Senate summaries are each reported
- **AND** a combined contested-race summary does not replace them

### Requirement: The locked forecast becomes a prospective test

After certified results are available, the system SHALL score each locked
forecast snapshot against those results without refitting, changing its input
cutoff, or replacing its original predictions. Prospective scores SHALL include
margin error, interval coverage, Brier score, log loss, calibration, and the
accuracy of aggregate seat summaries.

#### Scenario: Results score the locked prediction

- **WHEN** certified 2026 results are supplied
- **THEN** they are joined to the unchanged forecast by race identity
- **AND** no model fit or prediction is regenerated during scoring

#### Scenario: Incomplete result coverage is explicit

- **WHEN** a target race lacks a certified result
- **THEN** it is listed as unscored with the reason
- **AND** published metrics state their scored and unscored race counts

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
