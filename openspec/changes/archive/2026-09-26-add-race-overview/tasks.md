# Tasks

## 1. Presentation and Ordering Primitives

- [x] 1.1 Add pure whole-number margin, interval, PVI, percent, percentage-point, and grouped-dollar formatters, and verify unit tests cover positive, negative, zero, fractional, and large values without changing source numbers.
- [x] 1.2 Add likely-winner and party-consistent probability comparison helpers, and verify unit tests cover Democratic and Republican favorites, an exact 50 percent toss-up, same-party deltas, and a change of favorite.
- [x] 1.3 Add grouped whole-dollar receipt parsing that rejects negative, fractional, non-finite, and malformed input, and verify unit tests cover grouped and ungrouped valid values plus every rejected form.
- [x] 1.4 Add a pure competitiveness ordering helper using full-precision absolute point margin and deterministic office, numeric-district, and target-id tie-breakers, and verify unit tests prove rounded display ties do not alter ordering.
- [x] 1.5 Extend bundle/build validation to match every interactive race to the locked 2026 target and require a Republican comparison candidate, and verify validation passes for the committed bundle and fails for a missing, mismatched, or non-Republican race without modifying bundle bytes.

## 2. Overview and Navigation

- [x] 2.1 Add semantic overview and matchup view containers, a complete race table with labeled columns and real matchup links, and responsive/focus-visible styles; verify component or DOM tests cover headers, one row per manifest race, link names, and narrow-screen usability.
- [x] 2.2 Render the default overview directly from manifest metadata in competitiveness order with integer and likely-winner formatting, and verify tests show no race or component asset fetch is required before the overview is usable.
- [x] 2.3 Implement `?race=<target_id>` view state, encoded row URLs, overview return navigation, and `popstate` restoration under the Vite base path, and verify browser tests cover pointer and keyboard activation, browser back/forward, direct load, and refresh of a valid race URL.
- [x] 2.4 Handle an unknown race parameter by returning to the complete overview with an accessible error instead of selecting a fallback race, and verify a browser test covers the invalid direct URL.

## 3. Matchup Presentation

- [x] 3.1 Replace decimal matchup summaries and predictor displays with shared whole-unit formatting while leaving calculation and chart inputs at full precision, and verify unit and browser assertions cover margins, intervals, PVI, probability, and signed changes.
- [x] 3.2 Present published and hypothetical win chances for the likely winner, including Republican complements, toss-ups, same-party deltas, and favorite-change text, and verify browser fixtures exercise each state without a misleading Democratic-only label.
- [x] 3.3 Convert receipt controls to grouped text inputs backed by exact scenario state, update only the edited predictor, normalize valid input, and preserve the last valid value on errors; verify tests cover source cents surviving incumbency changes and reset, comma-formatted edits, invalid input, and scenario recalculation.
- [x] 3.4 Update margin labels and chart-adjacent copy to use Democratic and Republican language consistently for the validated 2026 bundle, and verify accessibility checks confirm the numeric summaries remain sufficient without color or chart inspection.

## 4. Integration and Delivery

- [x] 4.1 Update the interactive forecast documentation for the overview landing page, direct race URLs, whole-number presentation, grouped receipt editing, and likely-winner probabilities, and verify documented local and production URLs match the implemented query format.
- [x] 4.2 Run the frontend unit, production browser, accessibility, bundle-validation, production-build, and full Python test suites, and verify the built Pages artifact contains all 46 overview races, supports a direct matchup refresh beneath `/election-modeling/`, and leaves the committed interactive bundle unchanged.
