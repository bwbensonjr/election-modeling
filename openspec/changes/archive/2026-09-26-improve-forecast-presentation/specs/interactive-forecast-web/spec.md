# Spec Delta

## MODIFIED Requirements

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
