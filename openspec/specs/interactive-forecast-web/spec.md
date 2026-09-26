# Interactive Forecast Web Specification

## Purpose

Defines a portable, browser-based presentation of a locked election forecast that lets readers inspect race distributions and evaluate clearly labeled model-sensitivity scenarios without refitting or changing the official forecast.

## Requirements

### Requirement: An interactive bundle is traceable to a locked forecast

The system SHALL export a versioned interactive bundle from one named, immutable forecast snapshot. The bundle SHALL identify the election, horizon, model variant and component, data definition, training cutoff, finance cutoff, code revision, source digests, bundle schema version, race identities, original predictor values, original forecast summaries, predictive draws, applicable coefficient draws, and historical predictor support needed to reproduce every supported browser calculation.

The export SHALL fail rather than publish a bundle whose race identities, component assignments, provenance, or original summaries disagree with the source snapshot.

#### Scenario: Bundle provenance identifies its source forecast

- **WHEN** a reader inspects the interactive application's methodology and provenance
- **THEN** the application identifies the locked snapshot, information horizon, cutoffs, model declaration, data definition, and code revision from which its bundle was generated
- **AND** the official snapshot remains independently addressable

#### Scenario: A mismatched export is refused

- **WHEN** an exported race, component, or published summary does not agree with the named locked snapshot
- **THEN** bundle generation fails with the mismatched field and race identified
- **AND** no replacement bundle is published

### Requirement: The unchanged browser scenario reproduces the published race forecast

For every race exposed by the application, the unchanged browser scenario SHALL reproduce the source snapshot's predictive distribution closely enough that its point margin, 90% predictive interval, and Democratic win probability pass declared numeric tolerances. The application SHALL display the source snapshot values as the published forecast and SHALL NOT relabel a recalculated or hypothetical value as published.

#### Scenario: Initial race view matches the locked snapshot

- **WHEN** a reader selects a race and has not changed any input
- **THEN** the published point margin, 90% interval, and Democratic win probability match the source snapshot
- **AND** the scenario result is visually indistinguishable in value within the declared verification tolerances

#### Scenario: Browser and Python calculations are compared

- **WHEN** the same fixed scenario is evaluated by the browser calculation and the Python reference calculation
- **THEN** their draw summaries pass the declared cross-language tolerances
- **AND** a tolerance failure blocks publication

### Requirement: A reader can evaluate supported race-level scenarios

The application SHALL let a reader select any race contained in the published bundle and change that race's incumbency status among open seat, Democratic incumbent, and Republican incumbent. For a race using a finance component, the application SHALL also accept non-negative Democratic and opponent receipt amounts and SHALL derive the same horizon-matched log receipt ratio used by the fitted model.

The scenario SHALL change only the reader-edited predictors. It SHALL preserve the selected race's PVI, candidates, horizon, model component, posterior draw alignment, and all other locked inputs. The application SHALL provide a reset action that restores all inputs and results to the published race values.

#### Scenario: Incumbency status is changed

- **WHEN** a reader changes a selected race from its published incumbency status to another supported status
- **THEN** the application immediately recalculates the predictive distribution using the corresponding fitted incumbency effect
- **AND** the published forecast remains visible for comparison

#### Scenario: Candidate receipts are changed

- **WHEN** a reader enters non-negative receipt amounts for both candidates in a race using a finance component
- **THEN** the application recalculates the scenario with `log((dem_receipts + 1) / (opponent_receipts + 1))`
- **AND** it uses the receipt window belonging to the bundle's declared information horizon

#### Scenario: Finance is unavailable to the selected component

- **WHEN** a selected race was routed to a component without a finance predictor
- **THEN** the application disables fundraising edits and explains that the component does not use finance
- **AND** it does not switch components or impute missing money in response to a scenario edit

#### Scenario: Scenario inputs are reset

- **WHEN** a reader activates reset after changing one or more inputs
- **THEN** all controls return to the selected race's published values
- **AND** the scenario summaries and distribution return to the unchanged result

### Requirement: Scenario distributions preserve paired model variation

The application SHALL calculate a hypothetical draw by applying the changed predictor values to the corresponding coefficient draw while retaining the same published predictive draw as the unchanged baseline. Published and hypothetical results SHALL therefore be paired by draw rather than generated from independent random samples.

#### Scenario: Repeating a scenario is deterministic

- **WHEN** a reader enters the same scenario values more than once
- **THEN** the application returns the same point margin, interval, win probability, and plotted distribution each time
- **AND** no new random sampling occurs in the browser

#### Scenario: An unchanged predictor contributes no artificial difference

- **WHEN** a scenario input is left at its published value
- **THEN** that predictor contributes zero change to every paired draw
- **AND** Monte Carlo resampling noise does not create a displayed scenario difference

### Requirement: The race view communicates the distribution and its change

For the selected race, the application SHALL show the matchup, office, district, published predictor values, published point margin, published 90% predictive interval, published likely-winner probability, and an overlaid or otherwise directly comparable view of the published and scenario predictive distributions. Each candidate name SHALL include the candidate's party letter and municipality in the form `<name> (<party>-<municipality>)`, and SHALL include an asterisk immediately after the name when that candidate is the incumbent. The application SHALL provide an accessible explanation that an asterisk denotes incumbency. It SHALL also report the scenario point margin, 90% interval, likely-winner probability, and changes in point margin and win probability subject to the favored-party comparison rules.

The distribution view SHALL mark a zero Democratic margin and identify which side of zero favors each candidate. Numeric summaries SHALL remain available without relying on color or visual inspection of the chart. Published and scenario margin summaries SHALL use the label `Likely Margin` and express the favored party in words as `Dem. +<whole number> points` or `Rep. +<whole number> points`; an even result SHALL be labeled explicitly as even or a toss-up.

#### Scenario: Candidate identity is fully displayed

- **WHEN** a reader views a race matchup
- **THEN** each candidate is shown with their name, party letter, and municipality in the required parenthesized format
- **AND** an incumbent candidate's name includes an asterisk
- **AND** the interface explains the meaning of the asterisk

#### Scenario: Likely margin is labeled and party-directed

- **WHEN** a published or hypothetical summary has a positive Democratic point margin
- **THEN** the summary label is `Likely Margin`
- **AND** the value is displayed as `Dem. +<whole number> points`

#### Scenario: Republican or even margin is unambiguous

- **WHEN** a summary has a negative point margin or a rounded zero point margin
- **THEN** the value is displayed as `Rep. +<whole number> points` for a negative margin or an explicit even/toss-up label for zero
- **AND** the sign is not left for the reader to infer from a bare number

#### Scenario: A changed scenario is compared with the forecast

- **WHEN** a reader changes a supported input
- **THEN** the race view shows both published and scenario distributions and summaries
- **AND** it reports the whole-point change in point margin and a party-consistent probability comparison

#### Scenario: The chart is not the only source of information

- **WHEN** a reader cannot distinguish the plotted series by color or cannot inspect the chart visually
- **THEN** labeled numeric summaries still communicate each distribution's point estimate, interval, likely winner, and win probability
- **AND** the controls and summaries remain operable by keyboard

### Requirement: Readers can scan races by published competitiveness

The application SHALL provide an overview table containing every race in the published bundle exactly once. The table SHALL order races by ascending absolute published point margin so the smallest expected margins appear first, with ties resolved by office, district, and stable race identity.

Each row SHALL identify the office, district, matchup, likely winning party, that party's displayed win probability, and the published point margin. The matchup SHALL use each candidate's name, party letter, and municipality, and SHALL mark incumbent candidates with an asterisk. The point-margin column SHALL be labeled `Likely Margin` and use the same party-directed words-and-points format as the race view. The table SHALL remain understandable and operable on narrow screens and without relying on color alone.

#### Scenario: The overview opens with the closest races first

- **WHEN** a reader opens the application without selecting a race-specific URL
- **THEN** the application displays the complete race overview
- **AND** each row's absolute published point margin is no smaller than the row before it, apart from deterministic ties

#### Scenario: Overview rows identify candidates and margins

- **WHEN** a reader scans an overview row
- **THEN** both candidates include party, municipality, and incumbent notation when applicable
- **AND** the margin column is labeled `Likely Margin` and identifies the favored party in words

#### Scenario: A reader opens a matchup from the overview

- **WHEN** a reader activates a race row using a pointer or keyboard
- **THEN** the application navigates to the matchup and scenario view for that exact race
- **AND** the resulting URL identifies the race

#### Scenario: A race-specific URL is loaded directly

- **WHEN** a reader opens or refreshes a valid race-specific URL
- **THEN** the application restores the matchup and scenario view for that race
- **AND** provides a way to return to the complete overview

#### Scenario: A race-specific URL is invalid

- **WHEN** the URL identifies no race in the published bundle
- **THEN** the application displays the complete overview with an understandable error message
- **AND** does not substitute an unrelated race

### Requirement: Reader-facing forecast values communicate appropriate precision

The application SHALL display reader-facing forecast margins, predictive interval endpoints, percentage probabilities, percentage-point changes, PVI values, and similar forecast quantities as integers rounded to the nearest whole unit. Full-precision values SHALL remain unchanged for scenario calculation, ordering, bundle validation, and cross-language verification. PVI SHALL always include its party letter with no intervening space, using `D+<whole number>` for a Democratic advantage, `R+<whole number>` for a Republican advantage, and an explicit neutral value for an even PVI.

The application SHALL display campaign-finance dollar amounts with locale-appropriate thousands separators. Editable receipt controls SHALL accept non-negative whole-dollar values with or without grouping separators and SHALL preserve the entered numeric amount when recalculating scenarios.

#### Scenario: Forecast quantities are presented without decimal precision

- **WHEN** the overview or a matchup view displays a forecast quantity to a reader
- **THEN** the displayed value is rounded to a whole point or whole percent as applicable
- **AND** the underlying forecast and scenario calculations continue to use their original precision

#### Scenario: PVI includes party direction

- **WHEN** the application displays a PVI value
- **THEN** a Democratic advantage is formatted like `D+4` and a Republican advantage like `R+2`
- **AND** no spaces appear between the party letter, sign, and number
- **AND** an even PVI is explicitly identified as neutral or even

#### Scenario: Campaign receipts are grouped and remain editable

- **WHEN** a published or hypothetical receipt amount is displayed
- **THEN** the dollar figure uses thousands separators and no fractional dollars
- **AND** a reader can edit the grouped value without changing its numeric interpretation

### Requirement: Win probability is presented for the likely winner

The application SHALL present each published and hypothetical win probability from the perspective of the party whose probability exceeds 50 percent. It SHALL label that party explicitly and SHALL display its probability as the Democratic win probability when that value exceeds one half or as one minus the Democratic win probability when that value is below one half. An exactly even probability SHALL be labeled as a 50 percent toss-up rather than assigning a likely winner.

Probability-point comparisons SHALL describe the change in the displayed likely winner's chance when the same party remains favored. When the favored party changes between compared distributions, the application SHALL identify the change of favorite rather than presenting a potentially misleading signed delta across different party perspectives.

#### Scenario: A Republican is favored

- **WHEN** a distribution has a 40 percent Democratic win probability
- **THEN** the application displays a 60 percent Republican win probability
- **AND** does not label the displayed 60 percent as Democratic

#### Scenario: A Democrat is favored

- **WHEN** a distribution has a 64 percent Democratic win probability
- **THEN** the application displays a 64 percent Democratic win probability

#### Scenario: The race is exactly even

- **WHEN** a distribution has a 50 percent Democratic win probability
- **THEN** the application displays a 50 percent toss-up
- **AND** does not designate either party as the likely winner

#### Scenario: A scenario changes the favorite

- **WHEN** a hypothetical scenario changes which party has a win probability above 50 percent
- **THEN** the application labels the new likely winner and its probability
- **AND** explicitly communicates that the favorite changed instead of showing a cross-party signed probability delta

### Requirement: Hypothetical and extrapolative results are disclosed

Every edited result SHALL be labeled as a model sensitivity scenario, not an official forecast update or a causal estimate. The application SHALL explain that fundraising is associated with forecast outcomes and that changing an amount does not establish the causal effect of raising that money.

The application SHALL compare each changed numeric predictor with the training support for the selected component and SHALL warn when the hypothetical value is outside that support. It SHALL also disclose the training count for a selected categorical level when that count indicates limited or absent support.

#### Scenario: A reader changes fundraising

- **WHEN** a scenario uses receipt amounts different from the published amounts
- **THEN** the result is labeled hypothetical and non-causal
- **AND** the official published values remain visually distinct

#### Scenario: A scenario exceeds training support

- **WHEN** the derived fundraising contrast lies below or above the component's historical training range
- **THEN** the application names the predictor and displays the supported range
- **AND** it still calculates the scenario without clipping the entered amounts

### Requirement: The application runs as a static GitHub Pages site

The production application SHALL be deployable to the repository's GitHub Pages site as static files. All race selection, scenario calculation, charting, and reset behavior SHALL run in the browser after loading versioned assets; the application SHALL NOT require a Python runtime, application server, database, user account, or writable remote service.

The Pages deployment SHALL be produced by a repeatable workflow from committed source and a committed, validated interactive bundle. The workflow SHALL test and build the site before replacing the deployed Pages artifact.

#### Scenario: A reader opens the deployed page

- **WHEN** the GitHub Pages site and its versioned assets are available
- **THEN** a reader can use every interactive scenario feature without contacting an application API
- **AND** refreshing the page does not depend on server-side session state

#### Scenario: A site build fails validation

- **WHEN** automated tests, bundle validation, or the production build fails
- **THEN** the deployment workflow does not replace the current GitHub Pages artifact
- **AND** the failure is reported by the workflow

### Requirement: Scope is limited to the complete 2026 race application

The initial application SHALL present the races contained in its complete 2026 forecast bundle. It SHALL NOT generate embeddable widgets, massnumbers.us-specific artifacts, or user-selected race-subset builds as part of this capability.

#### Scenario: The initial production bundle is published

- **WHEN** the GitHub Pages application is built for a 2026 forecast snapshot
- **THEN** its race selector contains every race in that bundle exactly once
- **AND** no separate subset or embed artifact is emitted
