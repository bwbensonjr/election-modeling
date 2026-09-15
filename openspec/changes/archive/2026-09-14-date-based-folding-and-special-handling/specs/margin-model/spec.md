## MODIFIED Requirements

### Requirement: Variants are declared, not hard-coded

A model variant SHALL be declared as a name plus either a set of predictors
drawn from the race table's columns, or a composition of two such
declarations with a routing rule, together with the definition or definitions
it is to be fit under. Adding a variant SHALL NOT require changing the fitting
or scoring procedure.

#### Scenario: A new variant is added by declaration alone

- **WHEN** a variant is declared with a new predictor set
- **THEN** it can be fit and scored through the same interface as `baseline`
- **AND** no change to the fold schedule or metric definitions is required

#### Scenario: A composite variant is added by declaration alone

- **WHEN** a variant is declared as two component declarations and a routing
  rule
- **THEN** it can be fit and scored through the same interface as a
  single-fit variant
- **AND** no change to the fold schedule or metric definitions is required

#### Scenario: A variant naming an absent column is rejected

- **WHEN** a variant declares a predictor that the race table does not carry
- **THEN** the system fails with an error naming the missing column, rather
  than silently dropping the predictor

#### Scenario: Adding a definition does not require changing variants

- **WHEN** a new definition is declared
- **THEN** existing variants can be fit under it without being redeclared
- **AND** a variant incompatible with it fails with a stated reason rather
  than being silently skipped

### Requirement: A predictor constant within a grouping level is rejected

A variant carrying a hierarchical group effect SHALL NOT also carry a
predictor that is constant within every level of that grouping factor in the
training races. Such a predictor is a linear combination of the group
indicators, so the group effect and the predictor are not separately
identified, and the fit explores a ridge rather than estimating two effects.

Where a predictor varies within only a small number of grouping levels, the
system SHALL report how many training races carry that variation, since that
count is what identifies the predictor.

This test SHALL be applied per fold against that fold's own training races.
A predictor SHALL NOT be refused, nor admitted, on the grounds of a general
claim about what determines its value; only the training data of the fold
being fit decides it.

#### Scenario: An exactly confounded predictor is refused

- **WHEN** a variant declares a group effect and a predictor whose value is
  constant within every level of that group in a fold's training races
- **THEN** the fit is refused with an error naming both the predictor and the
  grouping factor
- **AND** the refusal is recorded for that fold rather than silently skipped

#### Scenario: A weakly identified predictor is fit but disclosed

- **WHEN** a predictor varies within at least one level of the grouping
  factor, but within fewer than a stated number of training races
- **THEN** the fit proceeds
- **AND** the published diagnostics record the number of races that separate
  the predictor from the group effect

#### Scenario: The test is per fold, not per variant

- **WHEN** the same variant is fit across several folds
- **THEN** a fold whose training races separate the predictor from the group
  effect is fit
- **AND** a fold whose training races do not is refused
- **AND** the two outcomes are recorded per fold rather than resolved into a
  single verdict for the variant

## ADDED Requirements

### Requirement: Variants addressing the presidential-date bias are registered

The system SHALL register variants intended to absorb the bias that the
single `pres_elec` term leaves in place, which runs in opposite directions on
presidential-date and non-presidential-date general elections. At minimum
these SHALL include an interaction between presidential-date timing and
incumbency, a hierarchical timing effect meeting the knowability requirement,
and a signed national-environment term.

`pres_elec` is a property of a race's election date, not of its calendar
year: a special election held in a presidential year but on its own date
carries `False`. It is nonetheless near-constant within a calendar year in the
present record, because no special election has ever fallen on a presidential
general date, so the only races separating it from a calendar-year effect are
special elections. Where a variant carries both `pres_elec` and a grouping
factor, whether the two are separately identified SHALL be decided per fold
from the training races under the requirement above, and SHALL NOT be asserted
from the calendar.

#### Scenario: Each bias variant is nested against or comparable to the baseline

- **WHEN** a bias variant is scored
- **THEN** it is compared to the baseline on the same folds, races, and
  definition
- **AND** its effect on the presidential-date and non-presidential-date
  general-election segments is reported separately, not only its pooled effect

#### Scenario: Success is measured on the bias, not only on RMSE

- **WHEN** a bias variant is evaluated
- **THEN** the mean signed error within presidential-date general elections
  and within non-presidential-date general elections is reported for it and
  for the baseline
- **AND** a variant that narrows the gap between those two figures is
  identifiable as such even if its pooled RMSE is unchanged

#### Scenario: A timing term dropped for confounding is dropped on evidence

- **WHEN** a variant drops `pres_elec` because a grouping factor it carries
  spans it
- **THEN** the count of training races separating the two is published for
  each fold
- **AND** a contrast arm retaining the term under the same prior and sampler
  settings is scored alongside, so the removal rests on a measurement
- **AND** the comparison against the baseline is published as non-nested,
  naming both the term added and the term removed

#### Scenario: A year effect is publishable only if its fits are clean

- **WHEN** a hierarchical timing variant is scored
- **THEN** its result is reported as adoptable only if every fold under every
  scored definition passes sampling diagnostics
- **AND** if the calibration gain does not survive fits that pass
  diagnostics, that outcome is published rather than the variant being
  quietly retained

### Requirement: A group effect groups no coarser than the fold

A variant carrying a hierarchical group effect SHALL declare a grouping factor
whose levels do not span more than one fold's holdout. A grouping factor
coarser than the fold leaves the holdout's own level partially observed from
races the fold trains on, so the effect applied to the holdout is estimated
from a different population of races that happens to share the level.

A variant declaring a grouping factor coarser than the fold SHALL be refused
with an error naming the factor and the fold granularity, rather than fit.

#### Scenario: A coarser grouping factor is refused

- **WHEN** a variant declares a group effect on a factor whose levels contain
  races from more than one fold
- **THEN** the fit is refused with an error naming the grouping factor and
  the fold granularity
- **AND** the refusal is recorded rather than silently skipped

#### Scenario: The holdout's own level is unobserved

- **WHEN** a variant with a group effect at fold granularity predicts its
  holdout
- **THEN** the holdout level's effect is absent from the training races
- **AND** it is drawn from the distribution the fitted levels imply, widening
  the predictive interval to reflect that it is unobserved

#### Scenario: A calendar-year effect under a date schedule is refused

- **WHEN** a variant declares a per-calendar-year group effect and folds are
  election dates
- **THEN** the variant is refused, because a calendar year can contain several
  fold dates
- **AND** the error names the year factor and states that the fold granularity
  is the election date

### Requirement: A variant may be composite

A variant MAY be declared as two component variants plus a routing predicate
over the race table's columns. Fitting a composite variant SHALL fit each
component independently on its own training races for the fold. Predicting
SHALL route each holdout race to exactly one component according to the
predicate.

Each component SHALL declare its own training-race restriction, so a component
may be fit on a subset of the fold's training races. A composite variant SHALL
produce exactly one predictive distribution per holdout race, of the same form
a single-fit variant produces, so that every metric and comparison applies to
it unchanged.

#### Scenario: Each component is fit independently

- **WHEN** a composite variant is fit for a fold
- **THEN** each component is fit on its own training races, drawn from the
  races strictly preceding the fold's date
- **AND** each component's priors, sampler settings and diagnostics are
  recorded separately under a name identifying the component

#### Scenario: Every holdout race is routed to exactly one component

- **WHEN** a composite variant predicts a fold's holdout
- **THEN** the routing predicate assigns each race to exactly one component
- **AND** a race matching no component, or more than one, is an error naming
  the race rather than a silently dropped or doubled prediction

#### Scenario: A composite prediction is indistinguishable in form

- **WHEN** a composite variant's holdout predictions are published
- **THEN** each race carries a point prediction, interval bounds and a win
  probability of the same form a single-fit variant produces
- **AND** each race additionally records which component produced it

#### Scenario: A component's restriction is disclosed

- **WHEN** a composite variant is published
- **THEN** the training-race restriction of each component is stated
- **AND** the count of training races each component was fit on is reported
  per fold

### Requirement: A predictor must be knowable before its fold's election date

Every predictor a variant uses SHALL be derivable from information available
before its fold's election date. A variant SHALL NOT use a quantity that can
only be known once that election has happened.

A predictor that is knowable before the fold's election year *begins*
satisfies this by a wider margin, and SHALL be treated as the stronger case. A
predictor that becomes knowable only during that year SHALL declare an
explicit as-of date, and that date SHALL be published with every fit that uses
the predictor, because a dated predictor's value is meaningless without it and
the choice of date is the difference between a forecast and a postdiction.

A result of an election held earlier than the fold's date SHALL be treated as
knowable, including one held earlier in the same calendar year, because it was
settled before the fold's election occurred.

#### Scenario: A timing effect is specified so the holdout is predictable

- **WHEN** a variant carries a hierarchical timing effect and predicts a fold
  whose level is absent from its training data
- **THEN** that level's effect is drawn from the distribution the fitted
  levels imply, rather than from a fitted value that does not exist
- **AND** the resulting predictive interval widens to reflect that the level's
  effect is unobserved

#### Scenario: An earlier election in the same year is knowable

- **WHEN** a fold's date is a November general election and a special election
  was held that March
- **THEN** the March result is available to the fold's training set and to any
  predictor derived from prior results
- **AND** it is not refused as belonging to the fold's own year

#### Scenario: A national-environment term uses only prior information

- **WHEN** a variant carries a term describing the national political
  environment of the election year
- **THEN** that term is determined by facts settled before the fold's election
  date, such as which party holds the presidency
- **AND** it is not derived from the outcomes of the races being predicted

#### Scenario: A leaking predictor is rejected

- **WHEN** a variant declares a predictor computed from the results of the
  fold's own election date
- **THEN** the system refuses to score it and names the predictor

#### Scenario: A predictor knowable only during the fold year declares a date

- **WHEN** a variant declares a predictor that cannot be derived before the
  fold's election year begins
- **THEN** the variant declares an as-of date for it
- **AND** a variant that declares such a predictor without an as-of date is
  refused with an error naming the predictor

#### Scenario: The as-of date is before the election it predicts

- **WHEN** a dated predictor is used for a fold
- **THEN** its as-of date falls strictly before that fold's election date
- **AND** a date on or after the election date is refused rather than fit

#### Scenario: The as-of date is published with the result

- **WHEN** a fit using a dated predictor is published
- **THEN** the as-of date is carried in that fit's published record
- **AND** two fits of the same variant at different as-of dates are
  distinguishable in the published outputs

### Requirement: The three special-election handling arms are registered

The system SHALL register three variants covering the ways special elections
may be handled, so that the question is settled by comparison rather than by
assumption:

- `special_pooled_term` --- fit on all races, with `is_special` declared
  alongside the baseline predictors.
- `special_pooled_plain` --- fit on all races, with no `is_special` term.
- `special_split` --- a composite whose general component is fit on general
  elections only, with no `is_special` term, and whose special component is
  fit on all races with `is_special` declared; the routing predicate is the
  race's own `is_special` value.

The three SHALL be fit under the same definitions and the same fold schedule.

#### Scenario: The three arms are registered and fit alike

- **WHEN** the three arms are scored
- **THEN** each is fit under the same definitions and the same fold schedule
- **AND** their predictor sets differ only as declared above

#### Scenario: The general component excludes specials from training

- **WHEN** `special_split`'s general component is fit for a fold
- **THEN** its training races are the general elections strictly preceding the
  fold's date
- **AND** no special election appears among them

#### Scenario: The special component trains on everything

- **WHEN** `special_split`'s special component is fit for a fold
- **THEN** its training races are every race strictly preceding the fold's
  date, general and special alike
- **AND** it declares `is_special`

#### Scenario: A component refused for confounding is recorded

- **WHEN** a component of `special_split` declares a predictor its own
  training races leave unidentified, such as `is_special` in a training window
  holding no special elections
- **THEN** the component's fit is refused for that fold with the predictor
  named
- **AND** the refusal is recorded against the composite variant and the fold,
  rather than the fold being silently absent

## REMOVED Requirements

### Requirement: The is_special variant is the baseline plus one term

**Reason**: Superseded by the three-arm registration. The original requirement
fixed a single answer to the special-election question --- that specials
belong in the same fit as general elections, distinguished by one term --- and
made the only testable proposition whether that term helps. Every special
election in the record carries `pres_elec = False`, so specials also sit
inside the `pres_elec` segment and inside the identification of `pres_elec`
itself; whether they belong in the general-election fit at all is the question
that needs to be open.

**Migration**: `baseline_special` becomes `special_pooled_term`, with the same
predictors --- the baseline set plus `is_special` --- so the arm the original
required is retained unchanged in substance. `baseline` in that comparison
becomes `special_pooled_plain`, and the nesting the original asserted holds
between those two arms. The third arm, `special_split`, has no counterpart in
the original.

### Requirement: A predictor must be knowable before its fold year's election

**Reason**: The requirement is stated throughout in terms of a fold *year*,
which no longer names anything once a fold is one election date. Under the
year schedule its rule and the fold boundary agreed; under the date schedule
they disagree in a way that matters, because a special election held in March
is knowable before a November general in the same year and the old wording
would read as excluding it.

**Migration**: Replaced by "A predictor must be knowable before its fold's
election date", which carries every scenario of the original with `fold year`
replaced by `fold's election date`, and adds one scenario making explicit that
an earlier election in the same calendar year is knowable. The as-of
requirements for dated predictors are unchanged in substance: an as-of date
must still fall strictly before the fold's election date, and the
campaign-finance windows already satisfy this because they are computed
relative to each race's own `election_date`.

### Requirement: Variants addressing the presidential-year bias are registered

**Reason**: The requirement rests on the claim that a per-year effect "SHALL
NOT also carry a predictor determined by the calendar year, because the year
effect contains it", and its scenario "The year-effect variant carries no
calendar-determined term" encodes that claim as the test. `pres_elec` is not
determined by the calendar year --- it is determined by the election date, and
the training set reflects that --- so the rule names the wrong property. The
name is also wrong for the same reason: the bias is between presidential-date
and non-presidential-date ballots, not between calendar years.

**Migration**: Replaced by "Variants addressing the presidential-date bias are
registered", which keeps every substantive obligation --- the three registered
bias variants, the segmented reporting, the non-nested labelling, and the
clean-fits condition --- and replaces the calendar-based rule with a
data-based one: whether a grouping factor and `pres_elec` are separately
identified is decided per fold from the training races, under "A predictor
constant within a grouping level is rejected". The scenario "The year-effect
variant carries no calendar-determined term" becomes "A timing term dropped
for confounding is dropped on evidence", which requires the separating-race
count and a contrast arm rather than an appeal to the calendar. No variant
changes its predictors as a result: `baseline_year` still drops `pres_elec`,
now because every fold's training races confirm the confounding rather than
because the calendar is said to imply it.
