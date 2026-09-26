# Design

## Context

See `proposal.md` for motivation and the `interactive-forecast-web` delta for observable behavior.

The Vite application currently renders one matchup immediately, keeps the selected race only in a `<select>`, and has no URL state. The manifest already contains every race's identity, candidates, office, district, published summary, and inputs, so an overview can render without loading the larger race-draw or component assets. The static site is hosted below the `/election-modeling/` GitHub Pages base path, which rules out server-side routing and makes path-based client routes fragile on direct refresh.

Presentation is currently embedded in `main.ts`: margins, intervals, PVI values, probability percentages, and deltas use one decimal place; receipt facts use currency formatting while receipt controls use ungrouped numeric inputs. Scenario calculations use full-precision values. The bundle records a Democratic win probability and comparison candidate name but not comparison party. The locked 2026 target identifies every comparison candidate as Republican.

## Goals / Non-Goals

**Goals:**

- Separate overview and matchup states while retaining one static entry document and the repository Pages base path.
- Render the overview from manifest metadata and defer race/component asset loading until a matchup is opened.
- Centralize deterministic ordering, winner perspective, numeric formatting, and finance parsing in pure functions with unit coverage.
- Preserve full-precision published and scenario state even when its reader-facing representation is rounded.
- Keep overview and matchup navigation usable by keyboard, screen readers, direct links, refresh, browser back, and narrow screens.

**Non-Goals:**

- Refit the model, alter published summaries, reorder the manifest itself, or change bundle validation tolerances.
- Add user-controlled sorting, filtering, pagination, search, or editable overview scenarios.
- Generalize the current application to non-Republican comparison candidates or add party metadata to the immutable bundle in this change.
- Add multipage server routing, a frontend routing dependency, a backend, or massnumbers.us subset/embed output.

## Decisions

### 1. Represent the view with an optional race query parameter

The overview will be the canonical URL with no race parameter. Matchup links will use `?race=<encoded target_id>` relative to Vite's effective base URL. Startup will parse `URLSearchParams`; a valid race renders the matchup, no race renders the overview, and an unknown race renders the overview plus an error. Matchup and overview transitions will update browser history, and `popstate` will restore the corresponding view.

This keeps every direct request pointed at the deployed `index.html`, works beneath `/election-modeling/`, and makes rows real anchors with meaningful keyboard and copy-link behavior. Path routes were rejected because GitHub Pages cannot rewrite an arbitrary matchup path to the application entry point. Hash routing would refresh safely but produces less conventional URLs and weaker native query handling.

### 2. Render and sort the overview from manifest metadata

The table will use `Manifest.races` only. A copied array will be sorted by `Math.abs(published.point_margin)` using the unrounded value, then by office, numeric-aware district display, and `target_id`. Display rounding will never affect rank. Each row will provide one primary matchup link and separate cells for office/district, matchup, favored party and chance, and margin.

The narrow layout will preserve semantic table headers and links while allowing horizontal scrolling or compact cell wrapping; it will not replace the table with unlabeled visual cards. The current race selector may remain as a convenience within the matchup view, but overview navigation becomes the default entry experience.

Sorting by absolute point margin was chosen because margin is the forecast's primary signed outcome and the user requested the closest races first. Sorting by distance from 50 percent win probability was rejected because it can order races differently from the displayed point-margin competitiveness measure.

### 3. Centralize display transformations without changing model values

A presentation module will expose pure helpers for:

- whole-number signed margins, interval endpoints, PVI, percentages, and percentage-point changes;
- locale-grouped whole-dollar display;
- grouped whole-dollar receipt parsing and validation;
- likely-winner labels and probabilities derived from `dem_win_probability`; and
- party-consistent probability comparisons.

The helpers will use `Intl.NumberFormat("en-US", { maximumFractionDigits: 0 })` or equivalent whole-unit formatting. Calculations, sorting, bundle checks, chart geometry, and stored summaries will continue using their existing numeric values.

For probabilities above 0.5, the helper returns Democratic and the original probability. Below 0.5 it returns Republican and `1 - probability`. Exactly 0.5 returns Toss-up and 0.5. When published and scenario results favor the same party, the displayed delta is calculated in that party's probability direction. When the favorite flips, the UI names the old and new favorites and omits the cross-party signed probability delta.

The current 2026 target has 46 Republican comparison candidates. Bundle validation or the web build will explicitly compare the manifest race identities with `data/forecast/2026/target.csv` and fail unless every included comparison party is Republican. Hard-coding the label without validation was rejected because a future target update could silently misrepresent an opponent. Extending and replacing the immutable interactive bundle solely for already-known target metadata was rejected for this scoped presentation change.

### 4. Keep exact scenario state separate from formatted finance controls

Receipt controls will become text inputs with decimal-keyboard hints so they can display and accept comma grouping. On initial race load and reset, scenario state will retain the exact published receipt values while controls show rounded, grouped dollars. A receipt edit will parse that field into a non-negative whole-dollar scenario value and update only that predictor; changing incumbency will not reparse the rounded receipt display. This avoids turning a displayed `$75,664` back into `75664` when the locked value is `75664.4` merely because another control changed.

Formatting on commit or blur will normalize valid input. Invalid text will retain an inline error and will not replace the last valid scenario value. Using native `type="number"` was rejected because it cannot display grouping separators. Reparsing every control on each input event was rejected because it would discard hidden source precision.

### 5. Isolate view rendering while reusing the current scenario lifecycle

Application startup will load and validate the manifest, render shared provenance, and hand view state to overview and matchup render functions. Entering a matchup will reuse the existing lazy race/component loading and load-sequence guard. Leaving it will hide or clear matchup-specific status without fetching additional assets. Formatting helpers and overview ordering will be tested independently from DOM rendering.

This incremental split avoids adopting a framework or router for two view states. Keeping all behavior in the current monolithic startup function was rejected because navigation, overview rendering, formatting, and scenario state would become difficult to verify independently.

## Risks / Trade-offs

- **[The Republican label depends on a 2026 data invariant]** → Fail bundle/build validation if any manifest race maps to a non-Republican comparison candidate; add explicit party metadata in a future versioned bundle before supporting such races.
- **[Rounded controls hide source cents]** → Preserve exact source receipts in scenario state until the reader explicitly edits that receipt field, and document that controls display whole dollars.
- **[Rounded values can create apparent ties]** → Sort with full-precision margins and use deterministic tie-breakers; do not claim that visible rounded ties are ordered by their displayed value alone.
- **[A responsive table can require horizontal movement]** → Retain semantic headers and allow contained horizontal scrolling with visible focus instead of dropping columns or converting links into non-semantic click handlers.
- **[History and asynchronous asset loading can race]** → Route all navigation through one view-state handler and retain the existing load-sequence guard so stale loads cannot overwrite the active race.

## Migration Plan

1. Add pure ordering, winner-perspective, formatting, and finance-input helpers with unit tests.
2. Add the 2026 comparison-party build validation and keep the existing bundle bytes unchanged.
3. Introduce overview and matchup containers, query-parameter state, history handling, and responsive table styles.
4. Adapt matchup summaries and finance controls to the shared presentation helpers while preserving exact scenario state.
5. Run unit, browser, accessibility, bundle-validation, and production-build suites under the repository Pages base path.
6. Deploy through the existing Pages workflow. Roll back by reverting the application change; the locked forecast snapshot and interactive bundle require no rollback or migration.
