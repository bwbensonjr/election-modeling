# Interactive forecast application

The forecast explorer is a static GitHub Pages application for the locked 2026 legislative forecast. Its landing page lists every race in one published horizon with the closest published point margins first. Selecting a district opens its matchup page, where the explorer recalculates paired predictive draws when a reader changes incumbency or, where the selected component uses it, candidate receipts.

The explorer does not refit a model, change the official forecast, switch a race between composite components, or estimate a causal effect of fundraising. Race-subset and massnumbers.us embed builds are outside this application.

## Read and link to the forecast

The overview is the application root:

- Local development: `http://localhost:5173/`
- GitHub Pages: `https://bwbensonjr.github.io/election-modeling/`

Each table row links to a stable matchup URL using the locked race identity, for example `?race=<target_id>`. A local link therefore looks like `http://localhost:5173/?race=<target_id>`, and the deployed equivalent is `https://bwbensonjr.github.io/election-modeling/?race=<target_id>`. Direct links and browser refreshes restore that race; an unknown identity returns to the complete overview with an error instead of substituting another race.

The overview and matchup views identify candidates by name, party, and source-roster municipality, with an asterisk marking an incumbent. They show likely margins as party-directed text such as `Dem. +4 points`, and PVI as compact party-directed text such as `D+4` or `R+2`. Margins, interval endpoints, PVI, probabilities, and changes use whole numbers. This is display rounding only: ordering, scenario calculations, forecast verification, and predictive draws retain full precision. Win probability is labeled for the likely winner, so a 40 percent Democratic probability is displayed as a 60 percent Republican probability; exactly 50 percent is labeled a toss-up.

Published receipts and receipt controls use comma-separated whole dollars. The application retains the locked full-precision receipt value until that particular control is edited. Readers may enter grouped or ungrouped non-negative whole dollars; invalid or fractional entries do not replace the last valid scenario value.

## Prerequisites

- Python 3.11 or newer with `uv`
- Node.js 24 with npm
- Chromium installed for Playwright browser tests

Install the locked frontend dependencies and browser once:

```bash
cd web
npm ci
npx playwright install chromium
```

## Regenerate the web bundle

An official forecast snapshot must already exist, and publication requires a clean worktree. Export or byte-verify the 60-day bundle with:

```bash
uv run legmodel forecast-web --horizon 60d
```

The command refits the snapshot's declared component with its recorded seed, verifies every race and summary against the locked snapshot, and creates or verifies `data/forecast/2026/interactive/60d/`. It refuses conflicting existing bytes rather than overwriting them.

A later official 14-day snapshot can use the same command with `--horizon 14d`. The initial web application intentionally points to the 60-day bundle until a separate application update selects a newer horizon.

## Develop and verify locally

From `web/`:

```bash
npm test
npm run build
npm run dev
```

The build validates every committed asset digest, copies the committed bundle into Vite's ignored `public/data/` staging directory, type-checks the application, and writes `web/dist/`.

Bundle validation also matches every interactive race and its candidate name, municipality, party, and incumbency metadata to `data/forecast/2026/target.csv`. It verifies the initial application's all-Republican comparison-candidate invariant before the interface uses Republican-facing labels. A future bundle with another comparison party must carry an explicit presentation update rather than being silently mislabeled.

Run the production browser and accessibility suite with:

```bash
npm run test:browser
```

That command builds with the `/election-modeling/` repository base path and starts a local preview server. It requires permission to listen on localhost.

Run the complete Python suite from the repository root:

```bash
uv run pytest
```

## GitHub Pages deployment

The workflow in `.github/workflows/pages.yml` tests and builds changes on pull requests but deploys only a successful push to the repository's default branch. The deploy job has `pages: write` and `id-token: write`; pull-request jobs have read-only repository access and cannot deploy.

One repository setting must be configured outside the codebase: under **Settings > Pages > Build and deployment**, select **GitHub Actions** as the source. The first default-branch run creates or updates the `github-pages` environment and publishes the site.

## Rollback

Revert the application or bundle change to the last known-good commit and rerun the Pages workflow. The deployment is derived only from committed files, so the rebuilt artifact restores that revision. Rollback does not modify the immutable forecast snapshot or its prospective-scoring outputs.
