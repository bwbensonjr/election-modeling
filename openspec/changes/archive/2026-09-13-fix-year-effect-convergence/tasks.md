## 1. Baseline the committed outputs

- [x] 1.1 Snapshot the committed `data/models/` CSVs into the change's working
  area (a copy, not a commit) and verify the snapshot reproduces
  `scorecard.csv` byte-for-byte, so the "nothing else moved" check in 6.1 has
  a fixed reference
- [x] 1.2 Record the current `baseline_year` diagnostics per definition and
  fold from `fit_diagnostics.csv` into `docs/variant_results.md`'s working
  notes, so the superseded figures survive the rescoring (spec: "A superseded
  result is not silently overwritten")

## 2. Declared priors

- [x] 2.1 Add a `priors` mapping to `Variant` in `legmodel/variants.py`,
  defaulting to empty, and verify a variant declaring none produces the same
  `bmb.Model` priors as today by comparing the printed model for `baseline`
  before and after
- [x] 2.2 Pass `variant.priors` through to `bmb.Model(..., priors=...)` in
  `legmodel/fit.py`, and verify `baseline`'s fit on a fixed fold and seed
  returns identical posterior means to the committed `coefficients.csv`
- [x] 2.3 Raise a named error when a variant declares a group effect without a
  prior for its group-level standard deviation, and verify the error names the
  group effect (spec: "A group effect without a declared scale is rejected")
- [x] 2.4 Render the declared group prior as a stable string for publication
  (e.g. `1|election_year ~ Normal(0, HalfNormal(5))`) and verify the same
  declaration renders identically across runs

## 3. Declared and recorded sampler settings

- [x] 3.1 Add optional `target_accept` and `tune` to `Variant`, falling back to
  the `fit.py` module defaults, and verify a variant declaring neither samples
  with `target_accept = 0.8` and `tune = 1000`
- [x] 3.2 Extend `Diagnostics` with `target_accept`, `tune`, `draws`, `chains`
  and `group_prior`, populated with the values actually used, and verify
  `as_row()` emits them for a defaulted fit as well as a declaring one
- [x] 3.3 Verify the new columns reach `data/models/fit_diagnostics.csv` by
  running a single-variant, single-definition score and inspecting the header
  (spec: "Sampler settings travel with the diagnostics")

## 4. The grouping-collinearity check

- [x] 4.1 Implement the per-fold check in `legmodel/variants.py`: for each
  group effect, refuse any predictor constant within every level of that group
  in the training races, with an error naming both the predictor and the
  grouping factor (design D5)
- [x] 4.2 Verify the check fires on the real case: `baseline_year` as currently
  declared, trained on 2010-2013 under the adopted definition, must raise and
  name `pres_elec` and `election_year`
- [x] 4.3 Record `separating_races` --- the count of training races carrying
  within-group variation --- in the diagnostics when a predictor varies within
  fewer than 30 races, and verify it reports 8 for `pres_elec` against
  `election_year` on the full adopted-definition table
- [x] 4.4 Verify the check is inert for every variant without a group effect,
  by confirming `baseline`, `baseline_special`, `baseline_num_candidates`,
  `baseline_pres_incumbent` and `baseline_national_env` still fit unchanged

## 5. Redeclare the year variants

- [x] 5.1 Redeclare `baseline_year` as `PVI_N + incumbent_status` plus
  `(1|election_year)` with the group prior from design D2 and
  `target_accept = 0.95`, and verify it fits on the 2014 fold under the
  adopted definition with zero divergences
- [x] 5.2 Register `baseline_year_pres` --- the same variant retaining
  `pres_elec` --- under the same prior and settings, as the contrast arm
  (design D3), and verify it is accepted by the 4.1 check on the later folds
  and refused on the early ones, with that refusal recorded rather than
  silently skipped
- [x] 5.3 Verify `uv run legmodel variants` lists both with their declared
  priors and settings visible

## 6. Rescore and verify nothing else moved

- [x] 6.1 Rescore every variant under all four definitions --- widened from
  the two year variants because `fit_diagnostics.csv` gained columns, and a
  partial rescore would leave the untouched variants' rows blank in them
  rather than carrying what produced them. Verify the five untouched variants
  come back identical to the 1.1 snapshot on every pre-existing column, which
  also exercises the reproducibility requirement rather than assuming it
  (spec: "An untouched variant is verified unchanged")
- [x] 6.2 Verify every `baseline_year` fold under every definition now reports
  `diagnostics_passed` true; where any fold does not, record it and stop for a
  decision rather than lowering a threshold (design D6)
- [x] 6.3 Re-run `uv run legmodel compare baseline baseline_year` under the
  adopted definition and under `current`, and verify the output labels the
  comparison non-nested, naming both the added and the removed term
- [x] 6.4 Re-run `uv run legmodel parity` and verify the `baseline`
  coefficient parity check against `mapoli` is unchanged

## 7. Publish the outcome

- [x] 7.1 Rewrite the `baseline_year` section of `docs/variant_results.md`
  with the corrected result, the superseded figures, the non-nesting caveat
  and the `baseline_year_pres` contrast; verify it states the adoption
  decision either way
- [x] 7.2 Document the recorded sampler settings and prior declaration columns
  in `docs/scoring.md`, and verify the column list matches the committed
  `fit_diagnostics.csv` header
- [x] 7.3 Replace the "`baseline_year` fits do not converge" open issue in
  `README.md` with its resolution, including the correction that the
  non-centred parameterisation was already in place and that the real causes
  were the auto-scaled group prior and the year-level collinearity
- [x] 7.4 Conditional branch not taken: the calibration gain survived clean
  sampling and grew (RMSE 14.503 to 14.209, difference +0.510 to +0.804,
  coverage held at 0.927), so the issue closes as resolved rather than
  withdrawn. Verified that both the README and the writeup state the concern
  was tested and did not materialise, and that `baseline_national_env` is
  still named as the variant to use for a forward prediction (design D6)
