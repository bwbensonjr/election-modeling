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

## Scoring runs under a definition

Every scoring run is performed under exactly one **data definition**, which
supplies the races eligible for training and holdout and the response scored
against. The definition is recorded in every output, so a metric is never
reported without the rule that produced it. A run naming no definition uses
the adopted default and still records its name.

A definition changes *which* races are scored, not *how*. The fold schedule,
the metric set and the pooling rule below are unaffected by it. What does
change is the holdout size, reported per definition:

| Definition | Races | Pooled holdout | Holdout specials | Smallest training fold |
|---|---|---|---|---|
| `current` | 623 | 424 | 24 | 199 |
| `two_party` | 517 | 346 | 22 | 171 |
| `two_party_or_strongest` | 610 | 413 | 24 | 197 |
| `write_in_5pct` | 625 | 426 | 24 | 199 |

See [`definitions.md`](definitions.md). The fold table below is `current`'s.

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

## Comparing two definitions

This is a different operation from comparing two variants, with different
hazards, and it has its own command. Two variants share a holdout; two
definitions do not, and may not even share a response. A single difference
would conflate three changes at once: which races are scored, which races the
models trained on, and what the response measures.

```bash
uv run legmodel compare-definitions current two_party two_party_or_strongest
```

Three sections are reported:

1. **Paired difference on shared races.** Only races both definitions hold out,
   with a paired bootstrap interval and a decided/undecided label.
2. **Exclusive races.** What each definition admits that the other does not,
   with counts, the reason each race was dropped, and each definition's score
   over its own exclusive races.
3. **Response shift.** Over the shared races, the median, 95th percentile and
   maximum of the difference between the two responses, plus how many races
   move more than a point. Zero by construction when both definitions name the
   same response column, and the row says so.

Every row carries `training_sets_differ`, because they always do: the paired
difference isolates neither the response nor the eligibility rule on its own.

**Why the third section exists.** Scored on its own holdout, `two_party` posts
12.73 RMSE against `current`'s 15.61. On the 346 races the two share, the
difference is -0.31 [-0.83, +0.38] — undecided. The gap is almost entirely the
78 races `two_party` drops, which `current` scores at 25.3. A pooled
comparison would have read a refusal to predict hard races as accuracy.

## Dated predictors and the as-of date

Most predictors here are knowable before their fold year even begins: a
district's PVI, who the incumbent is, whether the year carries a presidential
race. Campaign finance is not. The rule a variant must satisfy is therefore
that its predictors are knowable **before its fold year's election**, and a
predictor that becomes knowable only during the year has to declare an as-of
date that is published with every fit using it.

A money figure without the date it was measured on is not interpretable, and
the difference between two dates is the difference between a forecast and a
postdiction. So:

- The variant declares `as_of`. A variant naming a dated predictor without one
  is refused, and the error names the predictor.
- Where the predictor was measured a fixed distance before each race's own
  election, the declaration is relative -- `election-14d`, `election-60d` --
  and the per-race dates are carried in the race table. Every holdout race is
  then checked individually: a date on or after that race's election is
  refused rather than fit.
- The date reaches `fit_diagnostics.csv` and the scorecard's pooled row, both
  as an `as_of` column. A variant carrying no dated predictor records
  `not dated` rather than a blank, so "this fit used no dated predictor" and
  "nobody recorded the date" do not look the same.

**Two as-of dates are two results.** The same contrast measured 14 and 60 days
out is registered as two variants and published as separate rows. The
comparison between them is a comparison of measurement dates, not of model
structure, and it is what makes a result's sensitivity to the cutoff
measurable rather than assumed.

## Variants that exclude races

A variant may declare `requires`, naming boolean columns a race must carry for
that variant to be fit on it. `money_complete` is the case this exists for: a
candidate whose OCPF filer could not be found has unknown money, which is a
different fact from a candidate who raised nothing, and a variant may not
quietly turn the first into the second. It either excludes those races or
carries an explicit unknown indicator. **It may not impute**, and a variant
whose predictor is missing on a race it would be fit on is refused rather than
fit.

The exclusion applies before the folds are built, so an excluded race is
absent from training as well as from the holdout, and the variant's pooled
`n_races` in the scorecard is the count it was actually scored on. That count
sits beside the baseline's, which is how the cost of restricting to complete
races is read.

A restriction can empty a fold entirely -- the 2023 fold holds one race, and
that race's opponent has no filer. The scorecard's pooled row therefore
carries `folds_absent` alongside `folds_refused` and
`folds_failing_diagnostics`, so a year this variant could not score is
recorded rather than merely missing.

## Segments

Metrics are broken out per fold and by `office`, `is_special`, `pres_elec`,
`redistricting_cycle`, `no_dem_candidate` and `admitted_by_write_in`. A segment
a definition empties is reported with a count of zero rather than dropped —
"`two_party` admits no no-Democrat races" and "nobody broke that segment out"
must not look the same.

The pooled row additionally carries `bias_presidential_years`,
`bias_non_presidential_years` and `pres_bias_gap`. The gap is the quantity the
presidential-year variants set out to close, and a variant can narrow it
without moving pooled RMSE at all.

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

### What the sampler ran under is published too

A seed alone does not reproduce a fit. `fit_diagnostics.csv` therefore carries
the settings and priors each fit actually used, whether the variant declared
them or took the defaults:

| Column | Meaning |
|---|---|
| `target_accept` | NUTS target acceptance probability. `0.8` is pymc's default; a higher value means the variant declared one |
| `tune` | Tuning iterations, default 1000 |
| `draws`, `chains` | Posterior draws per chain and number of chains |
| `group_prior` | The variant's declared priors, or `library defaults` where it declared none |
| `separating_races` | For a variant with a group effect, how many training races keep a predictor from being exactly collinear with the grouping factor. `none` when nothing is close |
| `refused_reason` | Set when the fold was refused before sampling, so a fold that was never fit is distinguishable from one that was fit and sampled badly |
| `as_of` | The date any dated predictor was measured to, or `not dated`. See above |

This exists because a variant can be made to converge by raising
`target_accept`, and a result obtained that way is a different claim from one
obtained at the default. The scorecard's pooled row also carries
`folds_refused` alongside `folds_failing_diagnostics`, keeping the two kinds of
failure apart.

**Declared priors.** A variant that declares nothing is fit under the
modelling library's auto-scaled defaults, which is what every variant here did
until a hierarchical term made that untenable: those defaults scale a group
effect's standard deviation from the intercept, landing on a prior five times
wider than the response itself. A group effect must therefore declare a scale
for its standard deviation, and a variant that does not is refused rather than
fit under a default nobody chose. See
[`variant_results.md`](variant_results.md).

**Refused folds.** A predictor constant within every level of a variant's own
grouping factor is a linear combination of that group's indicators. The fit
would return numbers, and the numbers would describe a ridge, so the fold is
refused and the refusal published. This is checked per fold rather than on the
whole table, because a predictor can vary within a group somewhere in the
record and nowhere inside an early fold's training window.

## Published outputs

| File | Contents |
|---|---|
| `data/models/holdout_predictions.csv.gz` | One row per definition per variant per holdout race: point prediction, 90% interval, win probability, observed response, and the per-race error terms every metric is built from |
| `data/models/scorecard.csv` | One row per definition per variant per segment, with `n_races` and each metric |
| `data/models/variant_comparison.csv` | Paired differences between variants, within one definition |
| `data/models/definition_comparison.csv` | The three sections above, per definition pair |
| `data/models/definition_summary.csv` | Holdout counts per definition |
| `data/models/definition_dropped_races.csv` | Every race each definition drops, with the reason |
| `data/models/threshold_sweep.csv` | Races admitted and scores at each write-in threshold |
| `data/models/coefficients.csv` | Posterior summaries per definition per variant per fold |
| `data/models/fit_diagnostics.csv` | R-hat, ESS, divergences and seed per fit, with the sampler settings and prior declaration that produced them |
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
