# Design

## Context

The 2026 forecast is generated in Python from an immutable target and horizon-specific finance snapshot. A forecast run fits each routed component, creates posterior predictive race draws in memory, and publishes race summaries plus chamber win-count draws; it does not retain the race-level draws or coefficient draws needed to recalculate a changed predictor in a browser. The current 60-day snapshot contains 46 races and all are routed to the finance component, but the web format must also describe races routed to a no-finance fallback.

The selected components are Gaussian linear regressions. Their scenario-relevant terms are PVI, two incumbency indicators with open seat as the reference, and, for finance-complete races, the horizon-matched log receipt ratio. This structure permits exact draw pairing without shipping PyMC or fitting in the browser.

There is no existing frontend or GitHub Pages workflow in the repository. Python development and model export must continue to use `uv`; a separate locked frontend toolchain is acceptable for compiling static assets.

## Goals / Non-Goals

**Goals:**

- Derive a portable web bundle from a named, locked forecast snapshot without modifying that snapshot.
- Make unchanged browser results match the published forecast and make edited scenarios deterministic and paired by posterior draw.
- Keep initial page load small enough for a public static site by loading detailed draws only for the selected race and component.
- Make the application understandable and operable on narrow screens, with keyboard controls and non-chart summaries.
- Make production deployment reproducible from committed source and committed generated forecast assets.

**Non-Goals:**

- Refit models, select variants, edit PVI, switch a race between composite components, or change the official forecast in the browser.
- Provide an API, database, accounts, saved scenarios, or server-side rendering.
- Generate a single-file application, an embeddable widget, or a race-subset build for massnumbers.us.
- Recompute chamber forecasts after a race-level hypothetical; this proposal changes one selected race only.

## Decisions

### 1. Publish static assets and perform only linear draw updates in the browser

The application will use the source race's published posterior predictive draw as its unchanged baseline. For draw `d`, a hypothetical result will be:

```text
scenario_draw[d] = published_draw[d]
                 + (scenario_incumbent_dem - published_incumbent_dem)
                   * beta_incumbent_dem[d]
                 + (scenario_incumbent_gop - published_incumbent_gop)
                   * beta_incumbent_gop[d]
                 + (scenario_money_logratio - published_money_logratio)
                   * beta_money_logratio[d]
```

The money term is omitted for components that do not declare it. This delta form preserves each published draw's intercept, PVI contribution, residual draw, parameter covariance, and all unedited inputs. It also makes the unchanged scenario byte-for-byte equal to the exported published draws and removes the need for a browser random-number generator.

The alternative was to export intercepts, all coefficients, residual scales, and generated normal draws and reconstruct each prediction. That is larger, easier to misalign, and offers no benefit when the supported scenarios change only incumbency and receipts. Running PyMC through a server or Pyodide was rejected because it would make a simple static presentation slower and operationally more complex.

### 2. Export a manifest with race and component shards

The generated bundle will live under a versioned 2026 interactive-data directory associated with one horizon. It will contain:

- A manifest with schema version, forecast provenance and digests, official race summaries, published inputs, support metadata, draw count, component-to-asset references, race-to-asset references, and a digest for every asset.
- One component asset per used model component containing aligned coefficient draw arrays for the scenario-adjustable terms and their declared predictor names.
- One race asset per target containing the aligned published posterior predictive draw array.

The application will load the manifest first, then fetch only the chosen race and its component. JSON is preferred for the first version because it is transparent, straightforward to validate in Python and TypeScript, and compressed in transit by normal static hosting. If measured production size or parsing latency is unacceptable, a later format version can introduce a binary representation without changing the behavioral contract.

A single monolithic file was rejected because selecting one race should not require parsing every race's draws. The sharded layout also leaves a clean architectural seam for a later, separately specified subset publisher without implementing one now.

### 3. Generate the bundle with Python and commit the validated output

A new `legmodel` command will refit the source snapshot's declared components with their recorded seeds, capture aligned predictive and coefficient draws, and verify the resulting race identities, component routing, and official summaries against the immutable snapshot before writing anything. Generation will use create-once-or-byte-verify semantics analogous to forecast snapshots. Any conflict will be refused rather than overwritten.

The generated bundle will be committed. The Pages deployment will not install the scientific Python stack or refit the Bayesian model. This keeps deployment quick and ensures that the site being served corresponds to reviewable forecast bytes. A developer explicitly regenerates and commits a new horizon bundle after a new official forecast snapshot exists.

Changing the existing snapshot format to retain fitting objects was rejected because it would expand the official forecast contract and make large backend-specific artifacts part of immutable publication. The interactive bundle is a derived, separately validated publication.

### 4. Keep published values separate from computed scenario values

The manifest will carry the official point margin, interval, and win probability from `races.csv`. The UI will render those fields in a persistent Published Forecast block. It will independently summarize the exported draw array for the Scenario block and assert during validation that the unchanged summary is within declared tolerances of the official fields.

This avoids presenting a rounded client-side recomputation as the official value and makes the boundary between forecast and exploration explicit. Tests will define tolerances for JSON numeric serialization and quantile implementation; the target is exact point and probability counts with interval agreement at floating-point tolerance.

### 5. Use a small TypeScript static application

The frontend will use Vite, TypeScript, semantic HTML, CSS, and focused D3 modules for the distribution visualization. It will not introduce a component framework for this single-page, single-state interaction. The frontend package manager will commit its lockfile; Python commands and tests remain under `uv`.

Application state will hold the selected target ID and editable inputs. Changing race replaces the state with that race's published values. Incumbency is represented by the same fixed levels as the model. Receipt inputs accept finite, non-negative values and derive `log((dem + 1) / (opponent + 1))` without rounding before calculation.

The chart will use a shared x-domain, a marked zero margin, distinguishable line/fill treatments in addition to color, and adjacent labeled numeric summaries. Distribution density is a view of the draws; all reported point, interval, and probability values are calculated directly from the draws rather than from the density estimate.

### 6. Validate at the exporter, calculation, UI, and deployment boundaries

Python tests will cover bundle schema, deterministic bytes, create-once behavior, source snapshot disagreement, draw alignment, supported coefficient extraction, and Python reference scenarios. TypeScript unit tests will load small fixture bundles and cover the delta equation, incumbency coding, receipt transformation, quantiles, win probabilities, reset, invalid inputs, and support warnings. Shared golden fixtures will compare fixed Python and TypeScript scenarios.

A browser smoke test will exercise race selection, both control types, reset, fallback finance behavior, and narrow-screen rendering against the production build. Accessibility checks will cover labels, keyboard operation, focus visibility, summary text, and non-color series identification.

The production build will reject an unsupported bundle schema, duplicate or missing targets, inconsistent draw lengths, a component missing a required coefficient, or an asset digest mismatch caught during build validation.

### 7. Deploy through GitHub Actions to the repository Pages site

A workflow will run on changes to the web source, committed interactive bundle, or workflow, with manual dispatch available. It will install locked frontend dependencies, run unit and browser tests, validate the bundle, build with the repository subpath as Vite's base, upload the static artifact, and deploy with GitHub's Pages actions only after all earlier jobs pass.

Production deployment will occur from the default branch under the GitHub Pages environment with the minimum `pages: write` and `id-token: write` permissions. Pull requests will build and test but will not deploy. The repository must be configured once to use GitHub Actions as its Pages source.

## Risks / Trade-offs

- **The exporter refit could differ because its Python environment changed** -> Lock dependencies, reuse the recorded seed and declarations, and refuse publication unless every unchanged race summary matches the source snapshot within strict tolerances.
- **JSON draw shards can still be several megabytes in aggregate** -> Fetch only the manifest initially and lazy-load one race plus one cached component; measure production assets before considering a new binary schema version.
- **A scenario may be mistaken for a causal claim** -> Keep the Published Forecast block visible, label every edit as model sensitivity, include a fundraising-specific non-causal explanation, and surface extrapolation warnings beside results.
- **Extreme receipt entries can overflow or produce misleading extrapolation** -> Accept only finite non-negative inputs, compute the stable declared log-ratio, warn outside training support, and never clip silently.
- **A fallback race cannot explore fundraising without changing components** -> Disable its receipt controls and explain why; component-switch counterfactuals require a separate model and are outside this proposal.
- **GitHub Pages base paths differ between local and production builds** -> set the production base from repository configuration and cover asset navigation in the production smoke test.
- **A public deployment can be replaced by a broken build** -> Gate deployment on bundle validation and tests, retain previous commits and Actions artifacts, and redeploy a known-good revision for rollback.

## Migration Plan

1. Add and test the Python interactive-bundle exporter without changing existing snapshot bytes.
2. Generate and review the create-once 2026 60-day bundle against the committed snapshot.
3. Add the frontend and shared golden fixtures; verify the unchanged and edited cases locally.
4. Add the Pages workflow and verify its build artifact on a pull request.
5. Configure the repository's Pages source to GitHub Actions and merge the known-good bundle, frontend, and workflow.
6. Verify the deployed race count, provenance, representative scenarios, responsive layout, and official snapshot link.

Rollback consists of redeploying the last known-good commit. The immutable forecast snapshot and its scoring path are unaffected by either deployment or rollback.
