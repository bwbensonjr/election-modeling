# Tasks

## 1. Extend candidate presentation data

- [x] 1.1 Add candidate party, municipality, and incumbent fields to the authoritative 2026 target/bundle data contract, preserving source provenance and verifying target construction tests reject missing or ambiguous municipality values
- [x] 1.2 Propagate structured Democratic and comparison candidate metadata through interactive bundle generation and validate party values, municipality presence, and incumbent flags before publishing; verify Python interactive and bundle-validation tests pass
- [x] 1.3 Update TypeScript manifest types, validation, and all unit/e2e fixtures for the structured candidate metadata; verify `npm test` passes

## 2. Implement shared presentation rules

- [x] 2.1 Add presentation helpers that format candidate identities with party, municipality, and incumbent asterisk plus accessible incumbency text; verify unit tests cover Democratic, Republican, incumbent, non-incumbent, and long municipality/name cases
- [x] 2.2 Update PVI formatting to emit `D+4`, `R+2`, and an explicit neutral/even value without spaces while retaining full-precision inputs; verify formatting tests cover positive, negative, zero, and rounding-boundary values
- [x] 2.3 Update margin formatting and summary labels to use `Likely Margin` and `Dem. +4 points`/`Rep. +2 points`, with explicit even/toss-up output; verify tests cover positive, negative, rounded-zero, and scenario-summary values

## 3. Apply the interface changes

- [x] 3.1 Use the shared candidate formatter in matchup context and overview rows, including a visible explanation of the incumbent asterisk and accessible text that does not depend on color; verify the rendered page exposes the required candidate identities
- [x] 3.2 Use the shared likely-margin formatter and label in published and hypothetical summaries and the overview table; verify overview ordering and underlying full-precision sorting remain unchanged
- [x] 3.3 Update markup and responsive styling as needed for wrapped candidate labels and the longer margin text; verify narrow viewport and accessibility browser tests pass

## 4. Validate and publish

- [x] 4.1 Regenerate or byte-verify the committed 2026 interactive bundle and confirm its manifest contains complete candidate metadata without changing published numeric forecast values
- [x] 4.2 Run the complete frontend test, browser, and production build checks (`npm test`, `npm run test:browser`, and `npm run build`) and verify the static artifact contains the new presentation
- [x] 4.3 Run the relevant Python validation/tests with `uv run pytest` and verify the existing GitHub Pages workflow remains deployable
