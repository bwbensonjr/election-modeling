## 1. The `ballot_timing` categorical

- [x] 1.1 Add `ballot_timing` to `DERIVED` in `variants.py`, computed in `derive()` from `is_special`, `pres_elec` and `PRESIDENT_PARTY`: `special` where `is_special`, else `presidential` where `pres_elec`, else `midterm_dem_pres` or `midterm_gop_pres` by the president's party. Verify over the committed table that the four levels hold 37, 231, 271 and 71 races, and that no special election carries a midterm level.
- [x] 1.2 Declare `ballot_timing` in `CATEGORICAL_LEVELS` and `CATEGORICAL_INDICATORS` with `presidential` as the reference, so `prepare()` imposes the level set rather than inferring it per fold. Verify `expand("ballot_timing")` returns three indicator columns and that a frame containing only presidential races still produces all three.
- [x] 1.3 Add the knowability declaration for `ballot_timing` --- it is derived from the election date and the party holding the presidency, both settled before the race. Verify it passes `check_knowable` and that a variant declaring it validates against the race table.
- [x] 1.4 Add tests covering the level assignment, including that a special election held in a presidential year takes `special` and not a midterm level, and that the level set is fold-independent. Verify `uv run --group dev pytest` passes.

## 2. Predictor-versus-predictor collinearity

- [x] 2.1 Extend `check_grouping()` in `variants.py` to test each pair of declared predictors' expanded columns with the existing `separating_races()` helper, refusing with `GroupedPredictorError` (or a sibling naming both predictors) when the separating count is zero. Skip any column with no variation in the training races --- that is the unobserved-level case in task 3, which must be disclosed rather than refused. Verify a synthetic frame where two columns are exact affine functions of each other is refused with both named.
- [x] 2.2 Verify against the real record that `baseline_national_env` is refused on exactly the nine folds 2014-01-07 through 2017-07-25 and fit on the remaining fourteen, and that no variant previously fit is newly refused. Run `uv run legmodel score --variants baseline_national_env --definitions two_party_or_strongest --no-write` and check the refusal rows against `fit_diagnostics.csv`.
- [x] 2.3 Add tests for the pairwise check: an exactly collinear pair refused, a pair separated by even one race fit, and a constant column skipped rather than refused. Verify all pass.

## 3. Unobserved levels are fit and disclosed

- [x] 3.1 Add a per-fold, per-level training-race count to the fit diagnostics, published in `fit_diagnostics.csv` for every categorical a variant declares. Verify a fold whose training races carry no `midterm_gop_pres` reports that level with a count of zero rather than omitting it.
- [x] 3.2 Confirm a fold with an all-zero indicator fits rather than failing, and that the resulting coefficient's posterior matches its declared prior. Verify on fold 2018-11-06 that the fit completes, all 71 holdout races receive predictions, and the `midterm_gop_pres` posterior mean and SD are close to the prior's.
- [x] 3.3 Declare an explicit prior for the `ballot_timing` coefficients on the registered variants rather than inheriting bambi's auto-scaled default, since an unobserved level's posterior is its prior and would otherwise be set by a default nobody chose (design.md, D3). Verify the declaration appears in `fit_diagnostics.csv` and that `uv run legmodel variants` prints it.
- [x] 3.4 Confirm the 2018-11-06 predictive intervals are wider than the folds that observe all four levels, which is the honest expression of the unobserved level. Verify by comparing mean interval width on that fold against 2022-11-08.

## 4. The `generals_only` definition

- [x] 4.1 Register `generals_only` in `definitions.py`: identical to `two_party_or_strongest` in eligibility, response, write-in threshold and no-Democrat treatment, additionally setting `scoreable &= ~is_special`. Verify `uv run legmodel definitions` lists it and reports the same admitted-race count as the adopted definition.
- [x] 4.2 Declare the train-only class explicitly in the definition's own record, so "does not score specials" is distinguishable from "does not admit specials" in the published declaration and not only in the counts. Verify the distinction appears in `definition_summary.csv`.
- [x] 4.3 Verify the fold schedule under `generals_only`: `uv run legmodel folds --definition generals_only` should print 6 folds over 389 holdout races, all general dates, with every special election present in the training sets and none in a holdout.
- [x] 4.4 Report the holdout population in the run summary --- holdout count, zero holdout specials by declaration, and the count of specials retained in training. Verify `uv run legmodel score --definitions generals_only` prints it and that `definition_summary.csv` carries it.

## 5. Segment and predictor share a level set

- [x] 5.1 Replace `score.ballot_timing()`'s three-level derivation with the four-level predictor column, and have the segment read the prepared column rather than recompute it, so there is one function and one level set (design.md, D5). Verify the scorecard's `ballot_timing` rows carry the four new level names.
- [x] 5.2 Confirm the segment rows and the variant's coefficients agree: a race contributes to the segment row matching the level its own predictor carried. Verify by joining `holdout_predictions.csv.gz` to `coefficients.csv` for one fold of `baseline_timing`.
- [x] 5.3 Ensure a definition scoring no special election reports the `special` level with a count of zero rather than omitting the row. Verify under `generals_only`.
- [x] 5.4 Update the documents that quote the old three-level segment names --- `docs/scoring.md` and `docs/special_handling_result.md` --- and note that `midterm_general` has split in two. Verify no document names a level the code no longer produces.

## 6. Register and score

- [x] 6.1 Register `baseline_timing` (`PVI_N + incumbent_status + ballot_timing`) and `baseline_timing_money` (the same plus `money_logratio_primary`). Verify `uv run legmodel variants` lists both with their declared formulas and priors.
- [x] 6.2 Score both under `generals_only` and `two_party_or_strongest` with `--append`, since the fold schedule is unchanged and the `fold_schedule` stamp still matches. Verify the run appends rather than replacing, and that existing cells are untouched.
- [x] 6.3 Rescore `baseline_national_env` under both definitions so its published rows reflect the nine refused folds. Verify its holdout count falls and that its refusal rows appear in `fit_diagnostics.csv`.
- [x] 6.4 Run the paired comparisons: `baseline_timing` against `baseline`, against `baseline_national_env`, and against `baseline_year`, under both definitions; and `generals_only` against `two_party_or_strongest` on the races both hold out. Verify each is published with its interval, its decided/undecided label, and its `ballot_timing` segment breakdown.
- [x] 6.5 Re-measure the `pres_elec` drop-one cost under the timing categorical --- `uv run legmodel importance --variant baseline_timing_money` --- and report it. Do not act on it; the open issue stays open until a variant dropping the term is registered and compared under every scored definition.

## 7. Documents

- [x] 7.1 Write `docs/timing_result.md`: the three timing groups among generals, why two booleans became one categorical, the collinearity that motivated it with its per-fold table, the comparison results, and what the `special` coefficient is and is not. Verify every figure is recomputable from the committed outputs.
- [x] 7.2 Close the two open issues in `README.md` that this change resolves --- the `national_env` collinearity and the timing entanglement --- stating what was done and what the measurement showed, in the style of the resolved `baseline_year` section. Verify neither is still listed as open.
- [x] 7.3 Update `docs/definitions.md` and `docs/definition_result.md` for the sixth definition, including its holdout population and why it is not adopted on this evidence. Verify the definition table lists it.
- [x] 7.4 Update `docs/variant_results.md` for the timing variants and for `baseline_national_env`'s refusals, marking its previously published figures as superseded by the collinearity refusal rather than by a rescore. Verify the refusal count matches `fit_diagnostics.csv`.
- [x] 7.5 Add the timing categorical to `docs/scoring.md`'s segment section and `docs/race_schema.md` if the column is persisted. Verify the level definitions match the code.
