## ADDED Requirements

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

## MODIFIED Requirements

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
