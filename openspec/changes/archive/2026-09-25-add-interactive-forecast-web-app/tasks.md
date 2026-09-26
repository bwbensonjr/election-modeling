# Tasks

## 1. Interactive Forecast Export

- [x] 1.1 Add an aligned coefficient-draw export to the fitted-model interface for the declared scenario terms, and verify Python tests preserve chain/draw ordering with posterior predictive draws.
- [x] 1.2 Add an interactive-bundle generator that captures published race draws, scenario coefficient draws, source inputs, support metadata, and snapshot provenance, and verify fixture tests cover money and no-money components.
- [x] 1.3 Implement the versioned manifest, component shards, race shards, content digests, schema validation, and create-once-or-byte-verify publication behavior, and verify tests reject mismatched summaries, routing, identities, draw lengths, and conflicting existing bytes.
- [x] 1.4 Add a `legmodel` command that exports or verifies a named forecast horizon's interactive bundle with the snapshot's recorded declarations and seeds, and verify the command succeeds on a fixture while refusing a dirty or incompatible source publication as specified.
- [x] 1.5 Generate and commit the validated 2026 60-day interactive bundle, and verify its manifest contains every snapshot race exactly once and its unchanged summaries pass the declared tolerances.

## 2. Static Application Foundation

- [x] 2.1 Create the Vite and TypeScript application with a locked frontend dependency file, production repository-base configuration, and test scripts, and verify a clean dependency install and production build succeed.
- [x] 2.2 Implement typed manifest and shard loading, schema checks, lazy race/component loading, digest validation, and component caching, and verify unit tests reject unsupported schemas, missing targets, bad digests, and inconsistent draw counts.
- [x] 2.3 Implement deterministic paired-draw scenario calculation, incumbency encoding, receipt validation and log-ratio derivation, summary statistics, deltas, reset state, and training-support checks, and verify TypeScript unit tests cover unchanged, edited, fallback, invalid, and extrapolative cases.
- [x] 2.4 Generate shared Python/TypeScript golden scenarios for each supported component shape, and verify both implementations produce point margins, intervals, win probabilities, and per-draw changes within the declared tolerances.

## 3. Race Exploration Experience

- [x] 3.1 Build the application shell, complete race selector, matchup context, official snapshot link, published predictor display, and persistent Published Forecast summaries, and verify every manifest race appears exactly once and changing races restores its published state.
- [x] 3.2 Add incumbency and candidate-receipt controls, immediate hypothetical summaries, signed margin and probability changes, reset behavior, input errors, and disabled fallback-finance behavior, and verify interaction tests cover every control path.
- [x] 3.3 Add the paired published-versus-scenario distribution visualization with a shared domain, zero-margin marker, candidate-side labels, non-color series distinctions, and direct draw-based summaries, and verify chart tests cover unchanged and changed distributions.
- [x] 3.4 Add provenance, model-sensitivity and fundraising non-causality language, component and horizon explanations, categorical support counts, and numeric extrapolation warnings, and verify the correct disclosure or warning appears for representative supported and unsupported scenarios.
- [x] 3.5 Complete responsive and accessible styling for desktop and narrow screens, labeled controls, focus visibility, keyboard operation, and chart-independent summaries, and verify automated accessibility checks and keyboard-focused browser tests pass.

## 4. Verification, Documentation, and GitHub Pages

- [x] 4.1 Add production-build browser tests for race selection, incumbency changes, fundraising changes, reset, fallback finance, asset navigation under the repository base path, and narrow-screen layout, and verify the browser suite passes against the built site.
- [x] 4.2 Add a GitHub Actions workflow that installs locked frontend dependencies, validates the committed bundle, runs unit and browser tests, builds the static site, uploads the Pages artifact, and deploys only from the default branch after successful checks; verify pull-request execution cannot deploy.
- [x] 4.3 Document local development, bundle regeneration, source-snapshot verification, production build, GitHub Pages enablement, deployment, and rollback, and verify every documented command runs from a clean checkout or is explicitly identified as repository configuration.
- [x] 4.4 Run the complete Python, frontend unit, browser, bundle-validation, and production-build suites; inspect the built artifact to confirm it contains the full 2026 bundle and no massnumbers.us subset or embed output.
