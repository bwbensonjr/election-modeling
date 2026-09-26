# Interactive forecast application

The forecast explorer is a static GitHub Pages application for the locked 2026 legislative forecast. It displays every race in one published horizon and recalculates paired predictive draws when a reader changes incumbency or, where the selected component uses it, candidate receipts.

The explorer does not refit a model, change the official forecast, switch a race between composite components, or estimate a causal effect of fundraising. Race-subset and massnumbers.us embed builds are outside this application.

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
