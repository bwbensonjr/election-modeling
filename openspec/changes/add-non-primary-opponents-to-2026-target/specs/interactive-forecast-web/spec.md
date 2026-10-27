# Spec Delta

## ADDED Requirements

### Requirement: The opponent is presented by its ballot designation

Where the application names the non-Democratic side, it SHALL use the
comparison candidate's ballot designation, not assume a Republican. This
covers the candidate's party letter, margin and likely-winner labels, the
incumbency option, the receipts labels, and the chart's side labels. Races with
a Republican opponent SHALL keep their existing wording.

#### Scenario: A Republican opponent keeps the existing labels

- **WHEN** a race's comparison candidate is a Republican
- **THEN** the candidate is shown as `(R-<municipality>)`, a favorable margin
  as `Rep. +<whole number> points`, and the likely winner as `Republican`

#### Scenario: A non-Republican opponent is labeled by designation

- **WHEN** a race's comparison candidate is unenrolled, independent, or of a
  minor party
- **THEN** the candidate's party letter is that designation's letter, such as
  `U` for Unenrolled or `I` for Independent
- **AND** a margin favoring the opponent reads `<designation> +<whole number>
  points` and a likely win reads with the designation's name
- **AND** the incumbency option, opponent receipts label, and chart side label
  name the designation instead of Republican

#### Scenario: A change of favorite names the actual parties

- **WHEN** a scenario moves the favorite between the Democrat and a
  non-Republican opponent
- **THEN** the favorite change names the Democratic party and the opponent's
  designation

#### Scenario: An unknown designation fails the build

- **WHEN** a bundle race carries a comparison party with no defined letter and
  label
- **THEN** bundle export and site validation fail naming the race
