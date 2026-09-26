# Proposal

## Why

The published 2026 forecast is reproducible but static, so readers cannot inspect a race's full predictive distribution or see how the fitted model responds to alternative pre-election inputs. A browser-based presentation can make those mechanics explorable without running Python, refitting the model, or changing the locked forecast.

## What Changes

- Export a versioned interactive-forecast bundle containing the 2026 race inputs, published predictive draws, relevant posterior coefficient draws, predictor support, and provenance needed for client-side scenario evaluation.
- Add a static web application that lets a reader select a 2026 race, compare the published and hypothetical predictive distributions, change incumbency status and candidate fundraising, and reset the scenario.
- Report scenario changes in point margin, 90% predictive interval, and Democratic win probability while clearly distinguishing model sensitivity from a causal claim or official forecast update.
- Preserve the published snapshot as the authoritative forecast and verify client-side calculations against the Python prediction implementation.
- Publish the generated site to GitHub Pages through a reproducible GitHub Actions workflow.
- Exclude reusable race-subset or embeddable outputs for massnumbers.us; that distribution mode will be planned separately.

## Capabilities

### New Capabilities

- `interactive-forecast-web`: Defines the portable model bundle, in-browser counterfactual evaluation, race-level user experience, provenance and interpretation disclosures, verification, and GitHub Pages publication.

### Modified Capabilities

None. The existing `election-forecast` snapshot and prospective-scoring requirements remain unchanged.

## Impact

- Adds a Python export/build path alongside the existing forecast snapshot publication code.
- Adds static frontend source, generated web assets, browser-focused tests, and GitHub Pages deployment configuration.
- May add a frontend build toolchain and charting dependency; Python development and model generation remain managed with `uv` and `pyproject.toml`.
- Does not alter model selection, fitting, forecast inputs, immutable snapshots, prospective scoring, or the official 2026 forecast values.
- Does not add a server, database, user accounts, persisted scenarios, arbitrary refitting, massnumbers.us embedding, or race-subset publishing.
