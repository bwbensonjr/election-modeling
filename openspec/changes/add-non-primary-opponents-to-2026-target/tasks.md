# Tasks

## 1. Nomination-paper supplement

- [x] 1.1 Transcribe every legislative candidate on the Secretary's 2026 State Election Candidates page who is not a 2026 primary nominee into `data/forecast/2026/nomination_candidates.csv` (columns per design D1, canonical district names, `source_as_of` set to the transcription date). Verify by a second read against the page that the file holds the 11 new opponents, the four third candidates (Frieden, Perron, Dotson, Espinola), and the no-Democrat entries such as Whipps.
- [x] 1.2 Add `build_supplement_candidates` and its validation (required fields, no duplicate of a primary nominee) to `src/legmodel/forecast.py`. Verify with unit tests in `tests/test_forecast_target.py` covering a valid row, a missing field, a primary duplicate, and a no-Democrat district that yields no matchup.

## 2. Comparison rule

- [x] 2.1 Change `select_comparison_candidate` and `expected_target_matchups` to the Republican-else-sole-non-Democrat rule with the `republican_else_sole_non_democrat` rule name and the new review statuses (design D3). Verify with tests for Dem+Rep+Unenrolled (Republican chosen, no review), Dem+Unenrolled (chosen, no review), and Dem+two non-Republicans (review required), and update the existing review test.
- [x] 2.2 Extend `verify_target_sources` to compare `comparison_rule`, `comparison_review_status`, and the nominee basis columns. Verify with a test that a stale `comparison_rule` string fails verification.
- [x] 2.3 Add a test that a non-Democratic, non-Republican incumbent opponent yields `GOP_Incumbent`, matching `training.incumbent_status`.

## 3. Revision-aware paths

- [x] 3.1 Add the forecast revision table to `src/legmodel/config.py` (`60d`, `14d`, `14d-r2` mapped to horizon, target, finance, snapshot, and bundle paths) and thread the identifier through `forecast_finance.run`, `forecast_run.run`, `interactive.run`, `forecast_score`, and the `cli.py` `forecast`, `forecast-web`, `forecast-score`, and finance subcommands. Verify `uv run pytest` passes.
- [x] 3.2 Regenerate `60d` and `14d` snapshots and both interactive bundles through the new paths. Verify each command reports "verified", and that `git status` shows no change under `data/forecast/2026/`.
- [x] 3.3 Add `revision`, `supersedes`, and `added_target_ids` to the snapshot manifest for revisions that declare a predecessor, leaving unrevised manifests unchanged. Verify with a `tests/test_forecast_run.py` test and by re-running 3.2.

## 4. Target build command

- [x] 4.1 Add `legmodel forecast-target --horizon 14d-r2` that builds the target from the primary roster, primary results, supplement, and PVI inputs, records both candidate sources and a combined digest, writes `data/forecast/2026/target_r2.csv` create-once, and runs `verify_target_sources`. Verify the command succeeds and `target_r2.csv` has 57 rows (47 House, 10 Senate).
- [x] 4.2 Add a test asserting that the 46 `target.csv` rows appear unchanged in `target_r2.csv` apart from `comparison_rule`, review status, candidate provenance, and `money_complete_14d` (14-day finance now exists), with PVI equal within the 1e-10 verification tolerance, and that the 11 added `target_id`s are exactly the districts listed in proposal.md.
- [x] 4.3 Document the supplement, the comparison rule, the build command, and the revision scheme in `docs/forecasting.md`. Verify the documented command runs as written.

## 5. Finance and forecast for the revision

- [x] 5.1 Run finance collection for `14d-r2` to produce `data/forecast/2026/finance_14d_r2.csv` with the 2026-10-20 cutoff. Verify the original 92 rows match `finance_14d.csv`, and list any new candidate with `available=False` and its `roster_error`. If a failure needs a new `ocpf-cli` lookup, stop and raise it with the user.
- [x] 5.2 Commit inputs, then publish `data/forecast/2026/snapshots/14d-r2` from a clean worktree. Verify 57 races, every new race routed to a component (fallbacks naming their reason), and a manifest naming `supersedes: "14d"`.
- [x] 5.3 Export `data/forecast/2026/interactive/14d-r2` and run `legmodel forecast-web` verification against the snapshot. Verify the export passes its tolerances for all 57 races. (Blocked on the exporter's Democrat-and-Republican-only party check; done in 6.2.)

## 6. Explorer and writeup

- [x] 6.1 Extend the exporter's designation table in `src/legmodel/interactive.py` to the D8 letters and allow them in bundle validation. Verify with a `tests/test_interactive.py` test that an Unenrolled opponent exports as `U` and an unknown designation fails, and re-verify the locked `60d` and `14d` bundles byte-for-byte.
- [x] 6.2 Export `data/forecast/2026/interactive/14d-r2` and verify it against the snapshot (completes 5.3).
- [x] 6.3 Add the designation table to `web/src/presentation.ts` and use it for candidate letters, margin labels, likely-winner names, and favorite changes; widen the `CandidateMeta.party` type and `web/src/data.ts` validation to the table. Verify with `web/src/presentation.test.ts` and `web/src/data.test.ts` cases for Republican (unchanged) and Unenrolled opponents.
- [x] 6.4 Label the incumbency option, receipts inputs, published-inputs list, and chart sides from the race's opponent designation in `web/src/main.ts` and `web/index.html`. Verify with an e2e case in `web/e2e/explorer.spec.ts` using an Unenrolled opponent.
- [x] 6.5 Point `web/scripts/validate-bundle.mjs`, `sync-data.mjs`, and `web/src/main.ts` at `14d-r2` and `target_r2.csv`, and change `bundle-validation.mjs` from "must be Republican" to "must match the designation table". Verify with `web/scripts/bundle-validation.test.mjs`, then `npm test`, `npm run build`, and `npm run test:browser`, and confirm the explorer lists 57 races.
- [x] 6.6 Update `artifacts/2026_massachusetts_legislative_forecast.md` and regenerate the `.docx` for 57 races, noting the `14d` record and that opponent party is not a predictor. Verify race counts and chamber summaries in the text match `snapshots/14d-r2`.

## 7. Integration check

- [ ] 7.1 Run `uv run pytest`, `ruff check`, and the web test suite. Confirm `git diff` touches no file under `data/forecast/2026/snapshots/60d`, `snapshots/14d`, `interactive/60d`, `interactive/14d`, `target.csv`, `finance_60d.csv`, or `finance_14d.csv`.

## Workflow follow-up

- Archive the change after the `14d-r2` explorer is deployed and reviewed.
