# Model scoring procedure

How a margin model's accuracy is measured in this project. The procedure is
fixed so that later work -- demographic variables, OCPF fundraising, a finer
incumbency measure, non-Bayesian algorithms -- is measured against an unmoved
yardstick. A new model is scored by registering it as a variant and rerunning;
nothing below changes to accommodate it.

Run it with:

```bash
uv run legmodel score                              # score every variant
uv run legmodel score --variants baseline          # rescore one
uv run legmodel compare baseline baseline_special  # paired comparison
uv run legmodel parity                             # coefficients vs mapoli
uv run legmodel variants                           # list registered variants
```

Everything reads committed CSVs. A scoring run needs no network and no fetch
cache.

## What is scored

The race-grain table in [`race_schema.md`](race_schema.md): one row per
contested legislative race, 623 of them, 2010 through 2024.

Evaluation is always at race grain, whatever grain a model is fit at. A
precinct-level model added later aggregates its precinct predictions to a race
margin and is scored on the same 424 holdout races, so its number is directly
comparable to the ones below.

## Rolling-origin folds

Each fold trains on every race strictly before its year and predicts that
year's races. The training window expands; it never contains the future.

| Fold | Train years | Train races | Holdout races | Specials |
|---|---|---|---|---|
| 2014 | 2010-2013 | 199 | 95 | 4 |
| 2015 | 2010-2014 | 294 | 3 | 3 |
| 2016 | 2010-2015 | 297 | 62 | 3 |
| 2017 | 2010-2016 | 359 | 5 | 5 |
| 2018 | 2010-2017 | 364 | 73 | 1 |
| 2020 | 2010-2018 | 437 | 55 | 5 |
| 2021 | 2010-2020 | 492 | 2 | 2 |
| 2022 | 2010-2021 | 494 | 74 | 0 |
| 2023 | 2010-2022 | 568 | 1 | 1 |
| 2024 | 2010-2023 | 569 | 54 | 0 |

**Pooled holdout: 424 races, 24 of them special.** Races from 2010 through
2013 are the seed training window and are never scored.

2019 is an eligible fold year that produced no fold, because the table holds
no contested races for it. It is recorded as skipped in the scorecard rather
than passing unremarked.

Three choices are worth stating plainly.

**Why split by year rather than at random.** Districts recur across cycles, so
a random split puts one cycle of a district in training and another in test.
The existing `mapoli/model/margin_model_cv.py` splits 80/20 at random and
leaks in exactly this way.

**Why odd years are folds.** Restricting folds to even years would put only 9
of the 37 specials in the holdout, none of them in 2022 or 2024. Odd-year
folds are entirely special elections, which is where a special-election term
has to earn its place. Including them raises the holdout specials to 24.

**Why the training window expands rather than slides.** It matches how the
model is used: every past cycle is available when forecasting the next one.

## Metrics

The primary score is **RMSE in margin points over the pooled holdout races**.

Pooling is over races, not an average of the ten fold scores. Averaging fold
scores would give the 2023 fold, which holds one race, the same weight as the
2014 fold, which holds 95 -- and it is not a small difference: for the
baseline the mean of the fold RMSEs is 18.26 against a pooled 15.61.

RMSE alone is blind to whether a Bayesian model's predictive distribution is
honest, and the published use of this model is a win-probability rating, so
these are reported beside it:

| Metric | What it says |
|---|---|
| `rmse` | Primary score, margin points |
| `mae` | Mean absolute error, less dominated by the worst misses |
| `bias` | Mean signed error. Positive means the model is too favourable to Democrats |
| `r2` | Skill against predicting the mean of the races being scored. A within-segment figure, not comparable across segments |
| `coverage_90` | Share of races whose observed margin fell inside the 90% posterior predictive interval. Should be near 0.90 |
| `crps` | Continuous ranked probability score. Scores the whole predictive distribution, not just its centre |
| `win_accuracy` | Share of races where the side favoured at more than 50% won |
| `win_log_loss` | Penalises confident wrong calls. Probabilities come from the margin posterior, not a separate model |

Win probability is the share of a race's posterior predictive draws above
zero, so the margin forecast and the rating can never disagree.

Every metric is reported for the pooled holdout, for each fold, and for each
level of `office`, `is_special`, `pres_elec`, `redistricting_cycle` and
`no_dem_candidate`. A segment with fewer than 10 races is marked
`small_sample`; it is still reported, because suppressing it would hide the
odd-year folds, which are the special-election evidence.

## Comparing two variants

Both variants are scored on the same folds and the same holdout races; a race
missing from either side leaves the comparison entirely. The statistic is the
difference in pooled RMSE.

Its interval comes from resampling the holdout races with replacement 10,000
times and recomputing both RMSEs on each resample. Each resample is shared
between the two variants, which is what keeps the comparison paired. **When
the interval contains zero the comparison is labelled `undecided`**, and the
writeup says the data does not separate the two rather than naming whichever
RMSE happened to be lower.

A paired t-test on per-race squared errors was rejected: squared errors of
margins are heavily right-skewed -- the no-Democrat races alone sit 30 or more
points from any plausible prediction -- so the normal approximation is poor at
this sample size. ArviZ's LOO and WAIC were rejected as the deciding statistic
because they answer a leave-one-race-out question that ignores the temporal
structure this design exists to respect.

## Reproducibility

Each fit's seed is derived from its variant name and fold year and published
with its results, so a single fold can be reproduced in isolation rather than
only as part of a full run. Reruns from the committed race table reproduce the
scorecard and every per-race prediction exactly.

A fit is flagged when any parameter's R-hat exceeds 1.01, any bulk or tail ESS
falls below 400, or the sampler reports a divergent transition. A flagged fold
is published with its scores and marked in the scorecard rather than aborting
the run, because a fold whose fit struggled is information about that fold.

## Published outputs

| File | Contents |
|---|---|
| `data/models/holdout_predictions.csv.gz` | One row per variant per holdout race: point prediction, 90% interval, win probability, observed margin, and the per-race error terms every metric is built from |
| `data/models/scorecard.csv` | One row per variant per segment, with `n_races` and each metric |
| `data/models/variant_comparison.csv` | Paired differences, bootstrap intervals and verdicts |
| `data/models/coefficients.csv` | Posterior summaries per variant per fold |
| `data/models/fit_diagnostics.csv` | R-hat, ESS, divergences and seed per fit |
| `data/models/coefficient_parity.csv` | Baseline coefficients against the same fit on mapoli's district table |

Every figure in the scorecard is recomputable from
`holdout_predictions.csv.gz` alone, which is verified as part of the run.

## Baseline parity

Before the scores mean anything, the newly built race table has to be shown to
carry the same model as the established one. `legmodel parity` fits the
identical baseline on the race table and on `mapoli`'s
`model/ma_leg_two_party_2008_2025.csv` over the same races.

On all 610 comparable races three of six coefficients differ by more than a
quarter of a posterior standard deviation. Restricting to the 521 races where
the two tables carry identical margin and PVI leaves the intercept still
differing by 0.81 points -- because this pipeline normalises PVI against FEC
national two-party totals and mapoli used a slightly different baseline, which
shifts every district in a PVI vintage by the same constant. Removing that one
documented offset, **all six coefficients agree to within 0.07 posterior
standard deviations**, the intercept difference falling from 0.81 to 0.03.

The model is the same. Every remaining discrepancy traces to a documented
difference in the data, catalogued in
[`race_schema.md`](race_schema.md#validation-against-the-published-district-level-table).
