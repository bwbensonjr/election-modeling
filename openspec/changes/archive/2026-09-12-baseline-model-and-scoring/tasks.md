## 1. Setup

- [x] 1.1 Add `bambi`, `pymc`, `arviz`, and `numpy` to `pyproject.toml`; verify `uv sync` succeeds and `import bambi` works in the project environment
- [x] 1.2 Create the `legmodel` package under `src/` with a `legmodel` console script registered in `pyproject.toml`; verify `uv run legmodel --help` lists the subcommands
- [x] 1.3 Add the `data/race/` and `data/models/` output directories with `.gitkeep`, matching the layout in design.md D12; verify `git status` shows them tracked

## 2. Race-grain rollup

- [x] 2.1 Implement the vote-summed district margin: sum `dem_votes`, `opponent_votes` and `candidate_votes` per `election_id` and compute `dem_margin` in points, preserving the no-Democrat negation convention; verify against a hand-computed race and confirm the result differs from the unweighted mean of precinct margins for a race with uneven turnout
- [x] 2.2 Implement district `PVI_N` by joining `data/pvi/ma_precinct_pvi.csv.gz` on `(pvi_year, redistricting_cycle, city_town, ward, precinct)`, summing `dem_votes` and `gop_votes` over the race, and applying the PVI formula against the national baseline; verify a sample district reproduces `mapoli`'s published `ma_state_leg_pvi_2008_2024.csv` value within tolerance
- [x] 2.3 Compute `pvi_coverage` and `pvi_interpolated_share` per race, and exclude only races with zero coverage; verify the excluded set is written to `data/race/race_pvi_coverage.csv` with a reason per row and that the count of races with partial coverage is reported
- [x] 2.4 Carry `election_date`, `election_year`, `redistricting_cycle`, `office`, `district`, `district_display`, `incumbent_status`, `pres_elec`, `is_special`, `num_candidates` and `no_dem_candidate` through from the precinct rows, failing the build if a race's precinct rows disagree on any of them; verify by injecting a disagreeing row into a copy of the input and confirming the build raises
- [x] 2.5 Wire the rollup in as a `maprecinct races` stage ordered after `training`, included in `maprecinct all`, writing `data/race/ma_race_training_set.csv.gz`; verify the file has exactly one row per `election_id` and that its `election_id` set is identical to the precinct table's
- [x] 2.6 Implement the validation against `mapoli/model/ma_leg_two_party_2008_2025.csv`, comparing `dem_margin` and `PVI_N` for races in both and excluding the 13 no-Democrat races as a known reference defect; verify `data/reports/race_rollup_validation.csv` records within-tolerance counts, outliers with their differences, and the excluded races listed separately
- [x] 2.7 Document the race table column by column in `docs/schema.md` or a companion document, stating how each column was derived from the precinct table; verify every published column appears in the document

## 3. Model variants and fitting

- [x] 3.1 Implement the variant registry mapping a name to a predictor list over race-table columns, rejecting a variant that names an absent column with an error that says which; verify a variant declaring a nonexistent predictor raises and that registering a new variant requires no change to the fitting code
- [x] 3.2 Register `baseline` as `PVI_N + incumbent_status + pres_elec` and `baseline_special` as those plus `is_special`; verify `baseline`'s predictors are a strict subset of `baseline_special`'s and that the only difference is `is_special`
- [x] 3.3 Implement fitting with Bambi using a Gaussian family, `incumbent_status` as a categorical with the level set fixed to `No_Incumbent`, `Dem_Incumbent`, `GOP_Incumbent` and `No_Incumbent` as reference, four chains and 2,000 draws; verify a fit on a fold whose training races contain no Republican incumbent still produces a design matrix that accepts a holdout race with one
- [x] 3.4 Implement deterministic seed derivation from `(variant, fold_year)` and record the seed with each fit; verify fitting the same variant on the same races twice yields identical posterior summaries and identical holdout predictions
- [x] 3.5 Implement the diagnostics check for R-hat above 1.01, bulk or tail ESS below 400, and divergent transitions, recording the result per fit without aborting the run; verify a deliberately under-tuned fit is flagged and still produces scores
- [x] 3.6 Implement prediction returning posterior predictive draws per race, with the point prediction as their mean, the 90% interval as their 5th and 95th percentiles, and the win probability as the fraction of draws above zero; verify the draws array has one column per predicted race and that the point prediction equals the draw mean
- [x] 3.7 Implement the parity check fitting `baseline` on both the race table and `mapoli`'s district table restricted to the same races, comparing posterior mean coefficients; verify each coefficient agrees within the stated tolerance and that any that does not is reported rather than silently accepted

## 4. Scoring harness

- [x] 4.1 Implement fold construction: fold years 2014, 2015, 2016, 2017, 2018, 2020, 2021, 2022, 2023 and 2024, each training on every race with `election_year` strictly less than the fold year; verify the per-fold train and holdout counts match the table in design.md D5 and that no fold's training set contains a race from its own year or later
- [x] 4.2 Make fold construction skip an eligible year with no races and record the skip; verify 2019 produces no fold and appears in the scorecard as skipped rather than being omitted silently
- [x] 4.3 Assert the seed window 2010 through 2013 never appears in a holdout set and that each of the 424 holdout races is predicted exactly once per variant; verify by counting predictions per `election_id` in the run output
- [x] 4.4 Implement the metric set over pooled holdout races: RMSE, MAE, mean signed error, R-squared, 90% interval coverage, CRPS from posterior draws, and win-side accuracy and log loss from the win probability; verify each metric against a hand-computed value on a small fixture
- [x] 4.5 Implement pooling over races rather than averaging fold scores; verify the pooled RMSE equals the RMSE computed directly over all 424 holdout races and differs from the mean of the ten per-fold RMSEs
- [x] 4.6 Implement segment breakdowns over `office`, `is_special`, `pres_elec`, `redistricting_cycle` and `no_dem_candidate`, plus per fold, each carrying `n_races` and a small-sample marker below the stated minimum; verify every segment's race counts sum to 424 within each segment type
- [x] 4.7 Write `data/models/holdout_predictions.csv.gz` with race identity, fold, variant, point prediction, interval bounds, win probability and observed margin; verify every metric in the scorecard can be recomputed from this file alone
- [x] 4.8 Write `data/models/scorecard.csv`, `data/models/coefficients.csv` and `data/models/fit_diagnostics.csv` in the long format of design.md D12; verify the scorecard marks any fold and variant whose fit failed diagnostics and that the pooled row discloses inclusion of a flagged fold

## 5. Variant comparison

- [x] 5.1 Implement paired comparison restricted to races present in both variants' holdout sets, dropping a race from both if it is missing from either; verify the two variants are compared over an identical race set
- [x] 5.2 Implement the paired bootstrap: resample holdout races with replacement, recompute both variants' RMSE on each resample, and report the 5th and 95th percentiles of the difference; verify the resample is shared between variants on each draw and that the procedure is reproducible from a recorded seed
- [x] 5.3 Label a comparison undecided when the interval contains zero, and write `data/models/variant_comparison.csv` with the pooled difference, the interval, the label and the special-election segment difference; verify a fixture where the two variants are identical produces an interval containing zero and the undecided label

## 6. CLI and end-to-end run

- [x] 6.1 Add `legmodel score` with a `--variants` selector and `legmodel compare` for the paired comparison, both reading only committed CSVs; verify a run with the network disabled succeeds and that `--variants baseline` rescores one variant without running the comparison
- [x] 6.2 Run `maprecinct races` end to end and commit `data/race/ma_race_training_set.csv.gz`; verify the row count is 623 less any zero-coverage exclusions and that the rollup validation report is clean or has a documented cause per outlier
- [x] 6.3 Run the full scoring of `baseline` and `baseline_special` and commit the `data/models/` outputs; verify a rerun from the committed race table reproduces identical metrics
- [x] 6.4 Verify reproducibility independently by rerunning a single fold from its recorded seed and confirming its predictions match the committed `holdout_predictions.csv.gz` rows

## 7. Documentation and conclusion

- [x] 7.1 Document the scoring procedure in `docs/` -- the fold schedule with its counts, the metric definitions, the pooling rule and the comparison method -- so a later change can score against it without rereading the code; verify the fold table matches the one actually produced by fold construction
- [x] 7.2 Write up the `is_special` result: both variants' pooled and segmented metrics, the paired difference with its interval, the special-election segment with its race count, and a stated conclusion including the case where the conclusion is that the data does not separate them; verify every number in the writeup is present in the committed scorecard
- [x] 7.3 Update `README.md` to point at the race table, the scoring procedure document and the `is_special` result, and mark the corresponding plan items complete; verify the links resolve
