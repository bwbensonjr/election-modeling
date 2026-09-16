## 1. Election-date comparison uncertainty

- [x] 1.1 Replace the paired race bootstrap with an election-date cluster bootstrap that preserves race-weighted RMSE point estimates, and verify unit tests reproduce a hand-computed multi-cluster example.
- [x] 1.2 Make comparisons with fewer than two date clusters return an unavailable interval and an `undecided` verdict, and verify a one-date segment cannot produce a zero-width interval.
- [x] 1.3 Publish `resampling_unit`, cluster count, resample count, and seed on comparison rows, and verify a written row fully identifies the clustered procedure.
- [x] 1.4 Route definition comparisons and variable-importance drop-one comparisons through the same cluster bootstrap, and verify tests show all three comparison paths preserve their existing paired race sets.
- [x] 1.5 Add general-election leave-one-date-out comparison output with omitted date, remaining races and clusters, point difference, and sign-change flag, and verify the timing comparison identifies 2018-11-06 as influential.

## 2. Forecast-facing backtest metrics

- [x] 2.1 Add Brier score to pooled, fold, and segment scoring from the posterior Democratic win probability, and verify it against a small exact probability fixture.
- [x] 2.2 Add probability calibration output with fixed bins, mean forecast, observed frequency, and counts, and verify empty and small bins remain explicit.
- [x] 2.3 Add operational forecast summaries for general elections, the latest general fold, office, incumbency, finance component, and cross-fitted probability bands, and verify no competitive band reads an observed margin or winner.
- [x] 2.4 Regenerate clustered variant, definition, and importance comparisons, then verify point differences are unchanged while intervals, verdicts, and cluster metadata match the new procedure.
- [x] 2.5 Update every comparison writeup affected by the migration, including the timing result, and verify earlier race-bootstrap intervals are marked superseded rather than silently replaced.

## 3. Horizon-matched forecast candidates

- [x] 3.1 Register `baseline_timing_money_wide` with the 60-day receipts log ratio and the timing priors, and verify its declaration, as-of value, requirements, and fixed categorical levels.
- [x] 3.2 Register the 14-day and 60-day no-timing money variants plus `baseline_no_timing`, and verify none declares either `pres_elec` or `ballot_timing` and each dated arm names the correct horizon.
- [x] 3.3 Score the matched timing and no-timing candidates under the adopted and generals-only definitions, and verify every within-horizon comparison uses identical complete-finance races.
- [x] 3.4 Compare the candidates with clustered intervals and leave-one-general sensitivity, apply the predeclared no-timing tie-break wherever the evidence is undecided, and publish the selected structure and evidence for each horizon.
- [x] 3.5 Register `forecast_60d` and `forecast_14d` composites with the selected money component and its same-structure no-money fallback, and verify synthetic complete and incomplete races route exactly once.
- [x] 3.6 Backtest each operational composite over the full admitted holdout and by component, and verify complete target coverage is reported together with separate fallback quality.

## 4. Response-free 2026 target data

- [x] 4.1 Add forecast paths and a target schema keyed by election date, office, and district, and verify duplicate keys, unsupported offices, missing provenance, and any result-bearing column are refused.
- [x] 4.2 Build a 2026 candidate-grain target from the published `ma-election-db` primary candidate roster and final primary nomination results using the existing office and district normalization, and verify no target general-election vote total or winner is required.
- [x] 4.3 Roll 2024 PVI onto each 2026 district under the 2021 map and carry PVI coverage and interpolation provenance, and verify every target PVI recomputes from the published precinct inputs.
- [x] 4.4 Implement the outcome-blind comparison-candidate rule and its explicit-review path for races with several non-Democrats, and verify changing eventual vote order cannot change a locked target matchup.
- [x] 4.5 Publish and validate `data/forecast/2026/target.csv` against the authoritative candidate roster, and verify every known contested House and Senate race appears exactly once with no outcome columns.

## 5. Future campaign finance

- [x] 5.1 Generalize candidate-to-filer resolution to accept the target candidate schema as well as historical candidates, and verify the same exact, normalized, ambiguous, and unmatched cases behave identically without results.
- [x] 5.2 Generalize dated transaction accumulation to the target election and exact 60-day or 14-day cutoff, and verify transactions after the selected cutoff are excluded.
- [x] 5.3 Add create-once forecast-finance publishing with candidate provenance, cache identities, match rule, amounts, availability, and race completeness, and verify a different rerun refuses to overwrite an existing horizon.
- [x] 5.4 Add a target-finance CLI path and cache-only reproduction test, and verify its help and dry-run output identify the target, horizon, cutoff, matched candidates, and unresolved review count.
- [x] 5.5 Reconstruct and publish `data/forecast/2026/finance_60d.csv`, review every unresolved filer, and verify its digest and exact cutoff can be reproduced from cached OCPF responses.

## 6. Forecast engine and immutable snapshots

- [x] 6.1 Add full-history forecast fitting that applies the historical definition to completed races strictly before the target date, and verify a 2026 fixture includes 2024 while excluding every target-date row.
- [x] 6.2 Add the stable forecast seed over variant, component, definition, training cutoff, target election, and horizon, and verify target row order cannot change the seed or race predictions.
- [x] 6.3 Validate target as-of dates against the requested horizon and the historical variant used to evaluate it, and verify a 14-day feature is refused in a 60-day forecast.
- [x] 6.4 Generate exactly one component-labelled posterior prediction per target race and fail on any missing, duplicate, or multiply routed identity, and verify complete and fallback fixtures cover the target exactly.
- [x] 6.5 Add component-specific support checks for numeric ranges, categorical counts, and unique election-date counts, and verify out-of-range values and the one-election Republican-midterm level produce named warnings without altering predictions.
- [x] 6.6 Preserve posterior sample alignment within each component and deterministically align component samples into office and chamber seat draws, and verify aggregate counts equal the sum of their contributing race draws.
- [x] 6.7 Write snapshot manifests, race summaries, chamber draws, and support warnings under create-once horizon directories, and verify file digests, code commit, training digest, cutoffs, seed inputs, and model declarations reproduce the snapshot.
- [x] 6.8 Add the forecast CLI command and verify a clean-worktree run can reproduce an existing snapshot byte-for-byte while a dirty or conflicting publish is refused.

## 7. Prospective scoring

- [x] 7.1 Add certified-result ingestion keyed to the locked target identity with explicit missing and extra race reports, and verify it cannot mutate or replace a forecast snapshot.
- [x] 7.2 Add prospective scoring for margin error, coverage, Brier score, log loss, calibration, component performance, and aggregate seats without calling the fitter, and verify a fixture scores the original locked predictions after model code is changed.
- [x] 7.3 Write prospective results beside the named snapshot with result provenance and scored and unscored counts, and verify repeated scoring is reproducible from the same result artifact.

## 8. Documentation and release verification

- [x] 8.1 Document target construction, outcome-blind matchup selection, finance horizons, fallback routing, support warnings, snapshot immutability, and prospective scoring, and verify every published field and command is described.
- [x] 8.2 Document that aggregate draws preserve represented posterior dependence but do not add a shared election shock, and verify no chamber interval is described as accounting for an unmodeled statewide environment.
- [x] 8.3 Run `uv run --group dev pytest`, `openspec validate --specs`, and `openspec validate 2026-forecast-readiness --type change --strict`, and resolve every failure before marking the implementation ready.
- [x] 8.4 From a committed clean revision, generate the 60-day 2026 forecast snapshot and verify its target coverage, component counts, warnings, manifest digests, and byte-for-byte reproducibility before publication.
