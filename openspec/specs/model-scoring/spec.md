## Purpose

Defines how a margin model's accuracy is measured: the rolling-origin
holdout schedule, the metrics computed over pooled holdout predictions, the
published scorecard, and how two variants are compared so that a difference
is reported as decided or undecided.

## Requirements

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

### Requirement: RMSE in margin points is the primary score

The primary accuracy score SHALL be the root mean squared error between
predicted and observed `dem_margin` over the pooled holdout races, expressed
in percentage points of margin.

#### Scenario: RMSE is reported for every scored variant

- **WHEN** a variant is scored
- **THEN** its pooled holdout RMSE is reported
- **AND** the number of holdout races it was computed over is reported with it

### Requirement: Secondary metrics accompany the primary score

Each scored variant SHALL also report mean absolute error, mean signed error
as a bias measure, the coefficient of determination, the empirical coverage
of its 90% posterior predictive intervals, and the continuous ranked
probability score. Because the published use of the model is race ratings, it
SHALL also report win-side accuracy, Brier score, and log loss from the
posterior probability that `dem_margin` exceeds zero, together with probability
calibration summaries whose bins and counts are published.

#### Scenario: Calibration is measured, not assumed

- **WHEN** a variant is scored
- **THEN** the fraction of holdout races whose observed margin fell inside
  the 90% posterior predictive interval is reported
- **AND** a variant whose coverage departs from 90% is identifiable as
  miscalibrated even if its RMSE is competitive

#### Scenario: Win-side metrics come from the margin posterior

- **WHEN** win-side accuracy, Brier score, and log loss are computed
- **THEN** each race's predicted probability is the posterior predictive
  probability that `dem_margin` exceeds zero
- **AND** the observed outcome is whether the observed `dem_margin` exceeds
  zero

#### Scenario: Probability calibration retains its sample size

- **WHEN** predicted win probabilities are grouped for a calibration summary
- **THEN** each group reports its mean forecast probability, observed win
  frequency, and race count
- **AND** an empty or small group is not presented as precise evidence

### Requirement: Scores are broken out per fold and per declared segment level

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

### Requirement: Two variants are compared on identical folds and races

Comparing two variants SHALL score both on the same fold schedule and the
same holdout races, and SHALL report the difference in pooled race-weighted
RMSE together with a paired comparison. Its uncertainty interval SHALL
resample whole election-date clusters, preserving the paired races and their
shared election environment, rather than treating races held on one date as
independent evidence. Where the two variants are not nested --- where one adds
a term and also removes one --- the comparison SHALL state that, so the
difference is not read as the effect of a single term.

A composite variant, which predicts different races from different component
fits, SHALL be comparable to a single-fit variant on this procedure provided
every race in the comparison is predicted exactly once by exactly one
component. A comparison involving a composite variant SHALL name the
components and state which races each one predicted.

#### Scenario: The comparison is paired by race

- **WHEN** two variants are compared
- **THEN** the point difference is computed over the same races for both
  variants
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

- **WHEN** an interval for a paired RMSE difference is computed
- **THEN** each resample selects election dates and carries all paired races
  held on each selected date together
- **AND** the point estimate remains the RMSE difference over equally weighted
  races rather than an equally weighted mean of fold scores

#### Scenario: One election date cannot establish comparison uncertainty

- **WHEN** a comparison segment contains paired races from fewer than two
  election dates
- **THEN** its clustered interval is reported as not estimable
- **AND** the segment is labelled undecided rather than receiving a degenerate
  interval from repeated copies of the same election

#### Scenario: A variant is not declared better on a pooled difference alone

- **WHEN** one variant has a lower pooled RMSE but the clustered interval spans
  zero
- **THEN** the published conclusion states that the election dates do not
  separate them, rather than naming a winner

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

### Requirement: Two definitions are compared on the intersection of their holdouts

Comparing two definitions SHALL score each on its own holdout, then compare
them on the races both hold out, and SHALL report separately what each
definition admits that the other does not. The paired uncertainty interval on
shared races SHALL resample whole election-date clusters. A pooled score from
one definition's holdout SHALL NOT be reported as a difference against the
other's.

#### Scenario: The comparison is paired on shared races

- **WHEN** two definitions are compared
- **THEN** the point difference is computed over the races present in both
  holdout sets
- **AND** its interval resamples the election dates carrying those shared
  races and is labelled undecided when it contains zero

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

### Requirement: A dated predictor's as-of date travels with the scores

Where a scored variant carries a predictor with an as-of date, that date SHALL
appear in the published outputs for every fit and every score it produced, so
that no published metric is ambiguous about the point in time its predictors
were measured at.

#### Scenario: The as-of date reaches the published record

- **WHEN** a variant carrying a dated predictor is scored
- **THEN** the as-of date appears in the fit diagnostics and in the scorecard
  rows for that variant
- **AND** a reader can tell, without consulting the code, how far before each
  election the predictors were measured

#### Scenario: Two as-of dates are two results

- **WHEN** the same variant is scored at two different as-of dates
- **THEN** the results are published as separate rows rather than merged
- **AND** the comparison between them is reported as a comparison of dates,
  not of model structure

### Requirement: The money sweep is reported per incumbency segment

The campaign-finance comparison SHALL be published broken out by incumbency as
well as pooled, because money is expected to behave differently in an open
seat than against an incumbent, and a pooled figure can hide an effect that is
real in one segment and absent in another.

#### Scenario: Segments are reported whether or not they agree

- **WHEN** a money variant is compared to the baseline
- **THEN** the difference is reported within open seats, Democratic-held seats
  and Republican-held seats, alongside the pooled difference
- **AND** a segment whose race count is too small to carry weight is marked as
  such rather than omitted

#### Scenario: The endogeneity caveat accompanies the result

- **WHEN** a money variant's result is published
- **THEN** the writeup states that money flows toward candidates already
  expected to win, so a coefficient may reflect expectations rather than
  influence
- **AND** the result is not presented as evidence that spending changes
  outcomes

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

### Requirement: A comparison discloses election-date sensitivity

Every comparison covering general elections SHALL report its result after
omitting each general-election date in turn. The report SHALL identify a sign
change, a verdict change, or a result whose apparent gain is concentrated in
one date, rather than leaving that dependence hidden behind the pooled race
count.

#### Scenario: A one-election gain is visible

- **WHEN** a variant's pooled advantage disappears or reverses after one
  general-election date is omitted
- **THEN** that date and the leave-one-date-out result are published
- **AND** the variant is not described as robust across election cycles

#### Scenario: Sensitivity uses the same paired races

- **WHEN** one date is omitted
- **THEN** both variants lose the same paired races from that date
- **AND** all other comparison restrictions remain unchanged

### Requirement: Forecast-facing evaluation matches the target use

The published evaluation of an operational general-election forecast SHALL
report general elections separately from specials, the latest available
general-election fold, each office and incumbency level, finance-complete and
fallback races, and competitive bands defined only from pre-election inputs or
cross-fitted predictions. It SHALL also compare the target predictors with
historical support.

#### Scenario: The latest election cannot disappear into the pooled score

- **WHEN** an operational forecast variant is evaluated
- **THEN** its most recent general-election RMSE, bias, coverage, Brier score,
  and log loss appear beside its pooled general-election values

#### Scenario: Competitive races are selected without outcomes

- **WHEN** performance is reported for a competitive band
- **THEN** membership is determined from information available before that
  race's election
- **AND** the observed margin or winner is not used to choose the band

#### Scenario: Fallback performance is visible

- **WHEN** an operational composite routes incomplete-finance races to a
  fallback
- **THEN** scores for the money and fallback components are reported
  separately as well as pooled
- **AND** full coverage is not credited without showing fallback quality

### Requirement: Corrected comparison results supersede race-bootstrap verdicts

All affected variant, definition, and variable-importance comparisons SHALL be
recomputed with election-date-clustered uncertainty. Published writeups SHALL
distinguish an unchanged point estimate from a changed interval or verdict and
SHALL retain the previous race-bootstrap result only as superseded history.

#### Scenario: A timing verdict changes after clustering

- **WHEN** the clustered interval for a previously decided timing comparison
  spans zero
- **THEN** the current result is published as undecided
- **AND** the earlier decided label is explicitly marked superseded

#### Scenario: Comparison metadata names the resampling unit

- **WHEN** any comparison row is published
- **THEN** it records the resampling unit, number of election-date clusters,
  resample count, and seed
- **AND** a race-bootstrap row cannot be mistaken for a clustered result

### Requirement: Operational experiments use a frozen operational control

An experiment whose result may change an operational forecast SHALL use the
selected operational variant at the relevant information horizon as its
primary control. Before scoring, the experiment SHALL record the control's
variant name, component declarations, routing predicate, data definition,
information horizon, decision segment, and repository revision. That frozen
record SHALL remain the control even if a different model is selected while
the experiment is in progress.

The original variant named `baseline` MAY be reproduced as a secondary
historical yardstick, but a comparison against it SHALL be labelled historical
and SHALL NOT by itself justify changing the operational forecast.

#### Scenario: A forecast challenger faces the model it would replace

- **WHEN** a predictor is proposed for operational adoption
- **THEN** its primary comparison uses the selected operational forecast at
  the matching horizon
- **AND** the original `baseline` is not substituted as the primary control

#### Scenario: The control cannot move after results are visible

- **WHEN** the selected operational model changes after an experiment's
  control record is frozen
- **THEN** the in-progress experiment continues against its recorded control
- **AND** any comparison against the newly selected model is declared as a new
  experiment rather than silently replacing the control

#### Scenario: Historical replication remains available

- **WHEN** the original `baseline` is rescored for continuity
- **THEN** its result is retained and labelled as a historical benchmark
- **AND** the report distinguishes it from evidence about the current
  operational forecast

#### Scenario: Composite coverage cannot decide the comparison

- **WHEN** an operational composite is compared with a challenger
- **THEN** both are scored on shared races and matching component routes
- **AND** neither is credited for omitting a race or using a later information
  horizon

### Requirement: The incumbency-tenure hypothesis is compared and published

The completed comparison of `baseline_tenure_cap4` with `baseline` SHALL remain
published as a legacy-baseline experiment. It SHALL NOT be presented as the
test deciding whether tenure replaces incumbency in the selected operational
forecast.

The system SHALL compare `forecast_tenure_replacement_14d` against the frozen
`forecast_14d` control on identical rolling-origin folds, shared races,
finance-completeness routes, and 14-day inputs. That comparison's
general-election result under the adopted definition SHALL be the pre-declared
primary tenure-replacement decision. The corresponding 60-day operational
comparison SHALL be a horizon sensitivity and SHALL NOT replace an undecided
or losing 14-day primary result.

Both comparisons SHALL publish paired RMSE differences with
election-date-clustered uncertainty, secondary metrics, fit diagnostics, and
leave-one-general-date-out sensitivity. Testing the replacement SHALL NOT
change either operational forecast declaration automatically.

#### Scenario: The primary hypothesis is identified in advance

- **WHEN** the tenure-replacement comparisons are published
- **THEN** the 14-day general-election comparison is labelled primary
- **AND** the 60-day comparison is labelled horizon sensitivity

#### Scenario: An undecided tenure result retains the operational model

- **WHEN** the clustered interval for the primary RMSE difference contains
  zero
- **THEN** the tenure replacement is reported as undecided
- **AND** `forecast_14d` and `forecast_60d` remain selected

#### Scenario: An undecided tenure result retains the baseline

- **WHEN** the clustered interval for the legacy-baseline primary comparison
  contains zero
- **THEN** that historical tenure hypothesis remains reported as undecided
- **AND** `baseline` remains the reference for that historical comparison

#### Scenario: A primary loss rejects adoption

- **WHEN** the clustered interval shows higher RMSE for the primary tenure
  replacement
- **THEN** the result is published as evidence against adoption
- **AND** a favorable 60-day result does not silently replace the primary
  hypothesis

#### Scenario: The legacy result is not an operational decision

- **WHEN** the earlier comparison against `baseline` is cited
- **THEN** it is labelled as testing incremental tenure against the historical
  specification
- **AND** it is not described as choosing the incumbency representation for
  the current money forecast

### Requirement: Tenure results disclose where the evidence comes from

The tenure comparison SHALL report paired race counts and metrics for open
seats, tenure greater than zero and less than two years, tenure from two years
through less than four years, and tenure of at least four years. It SHALL also
report Democratic- and Republican-incumbent segments separately. Left-censored
counts and any rows excluded because a capped value is not known exactly SHALL
be reported for every variant.

An operational-composite tenure comparison SHALL additionally report
complete-finance and fallback components separately, along with the component
and finance route that produced every paired prediction. It SHALL state that
the single signed-tenure coefficient imposes equal-magnitude, opposite-party
effects where `incumbent_status` estimates separate party coefficients.

#### Scenario: Early tenure is visible

- **WHEN** the tenure comparison is published
- **THEN** races below two years and races from two through less than four years
  have separate metrics and counts
- **AND** improvement among newer incumbents cannot be hidden by long-tenured
  races

#### Scenario: Saturated tenure is visible

- **WHEN** the comparison includes incumbents with at least four years of
  service
- **THEN** that segment's metrics and count are published
- **AND** the report states that the primary predictor assigns no additional
  tenure effect beyond four years

#### Scenario: Sparse segments are not overstated

- **WHEN** a tenure or party segment contains too few election-date clusters
  for a clustered interval
- **THEN** its interval is reported as not estimable and its count is shown
- **AND** it is not used alone to claim that tenure helps or hurts

#### Scenario: Finance routing is visible

- **WHEN** the operational tenure comparison is published
- **THEN** the money and no-money component results and counts appear
  separately as well as in the primary general-election result
- **AND** a pooled result cannot hide degradation in the fallback population
