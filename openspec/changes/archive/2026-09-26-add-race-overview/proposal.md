# Proposal

## Why

The forecast explorer opens directly on a single matchup, which makes it difficult to scan the full election and identify the races most likely to be competitive. Its decimal-heavy and Democratic-only presentation also implies more precision than the model supports and makes Republican-favored races harder to read.

## What Changes

- Add a table-based overview containing every race in the published bundle, ordered from the smallest absolute published point margin to the largest, with deterministic tie-breaking.
- Make each overview row a keyboard-accessible link to that race's matchup and scenario view, with a stable race-specific URL that can be opened or refreshed directly.
- Present forecast margins, interval endpoints, probabilities, probability-point changes, PVI values, and other reader-facing forecast numbers as rounded integers while retaining full precision for calculations and validation.
- Format displayed campaign-finance dollar amounts with thousands separators, including editable receipt controls without changing their underlying numeric meaning.
- Label and display win probability from the perspective of the party currently favored by the relevant published or hypothetical distribution; for example, a 40% Democratic win probability is shown as a 60% Republican win probability.
- Preserve the locked snapshot values and model calculations; these changes affect navigation and presentation, not forecast generation.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `interactive-forecast-web`: Add the all-race competitiveness overview, race-specific navigation, integer-oriented display formatting, grouped finance figures, and favored-party win-probability presentation.

## Impact

- Affects the static web application's page structure, routing or URL-state handling, table and responsive styles, shared number-formatting utilities, finance input parsing, and matchup rendering.
- Requires unit and browser coverage for competitiveness ordering, direct race links and refresh behavior, keyboard navigation, integer rounding, grouped dollar amounts, and Democratic- and Republican-favored probabilities.
- Uses the existing manifest and race assets. The build will verify the locked 2026 target's current all-Republican comparison-candidate invariant before applying Republican-facing labels, rather than silently mislabeling a future non-Republican comparison candidate.
- Adds no bundle schema, model calculation, server, database, external dependency, or massnumbers.us embed output.
