# Spec Delta

## ADDED Requirements

### Requirement: Readers can scan races by published competitiveness

The application SHALL provide an overview table containing every race in the published bundle exactly once. The table SHALL order races by ascending absolute published point margin so the smallest expected margins appear first, with ties resolved by office, district, and stable race identity.

Each row SHALL identify the office, district, matchup, likely winning party, that party's displayed win probability, and the published point margin. The table SHALL remain understandable and operable on narrow screens and without relying on color alone.

#### Scenario: The overview opens with the closest races first

- **WHEN** a reader opens the application without selecting a race-specific URL
- **THEN** the application displays the complete race overview
- **AND** each row's absolute published point margin is no smaller than the row before it, apart from deterministic ties

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

The application SHALL display reader-facing forecast margins, predictive interval endpoints, percentage probabilities, percentage-point changes, PVI values, and similar forecast quantities as integers rounded to the nearest whole unit. Full-precision values SHALL remain unchanged for scenario calculation, ordering, bundle validation, and cross-language verification.

The application SHALL display campaign-finance dollar amounts with locale-appropriate thousands separators. Editable receipt controls SHALL accept non-negative whole-dollar values with or without grouping separators and SHALL preserve the entered numeric amount when recalculating scenarios.

#### Scenario: Forecast quantities are presented without decimal precision

- **WHEN** the overview or a matchup view displays a forecast quantity to a reader
- **THEN** the displayed value is rounded to a whole point or whole percent as applicable
- **AND** the underlying forecast and scenario calculations continue to use their original precision

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

## MODIFIED Requirements

### Requirement: The race view communicates the distribution and its change

For the selected race, the application SHALL show the matchup, office, district, published predictor values, published point margin, published 90% predictive interval, published likely-winner probability, and an overlaid or otherwise directly comparable view of the published and scenario predictive distributions. It SHALL also report the scenario point margin, 90% interval, likely-winner probability, and changes in point margin and win probability subject to the favored-party comparison rules.

The distribution view SHALL mark a zero Democratic margin and identify which side of zero favors each candidate. Numeric summaries SHALL remain available without relying on color or visual inspection of the chart.

#### Scenario: A changed scenario is compared with the forecast

- **WHEN** a reader changes a supported input
- **THEN** the race view shows both published and scenario distributions and summaries
- **AND** it reports the whole-point change in point margin and a party-consistent probability comparison

#### Scenario: The chart is not the only source of information

- **WHEN** a reader cannot distinguish the plotted series by color or cannot inspect the chart visually
- **THEN** labeled numeric summaries still communicate each distribution's point estimate, interval, likely winner, and win probability
- **AND** the controls and summaries remain operable by keyboard
