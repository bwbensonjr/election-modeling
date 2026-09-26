# Proposal

## Why

The 2026 forecast explorer currently presents candidate names, PVI, and margin values in abbreviated or ambiguous forms. Readers need enough party, municipality, incumbency, and forecast-direction context to identify the matchup and interpret the model output quickly and consistently across the overview and race detail views.

## What Changes

- Display each candidate as their name followed by party and municipality, such as `Margaret R. Scarsdale (D-Pepperell)`.
- Append an asterisk to a candidate name when that candidate is the incumbent, and make the incumbent notation understandable to readers.
- Format every PVI value with a party letter and no spaces, such as `D+4` or `R+2`; preserve an explicit neutral representation for an even PVI.
- Rename displayed forecast margin labels to `Likely Margin` and format values as party-specific text such as `Dem. +4 points` or `Rep. +2 points`, including an explicit even/toss-up representation.
- Apply the same presentation rules to the overview matchup rows, selected-race context, published summary, and hypothetical scenario summary without changing underlying forecast values or scenario calculations.
- Extend presentation and browser coverage for party, municipality, incumbency, PVI, and likely-margin edge cases.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `interactive-forecast-web`: Change the reader-facing race identity, PVI, and margin presentation requirements while preserving the locked bundle, calculation, ordering, and static-site behavior.

## Impact

- `web/src/main.ts`, `web/src/presentation.ts`, and related TypeScript types and templates will need display-formatting updates.
- The interactive bundle export and validation will need to expose or verify municipality, candidate party, and candidate-specific incumbency data needed by the browser; the immutable numeric forecast fields remain unchanged.
- Unit and Playwright tests and the interactive forecast specification will be updated. No model fit, forecast math, URL behavior, or external dependency is expected to change.
