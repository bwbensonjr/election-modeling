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
uv run legmodel compare baseline baseline_year     # paired comparison
uv run legmodel parity                             # coefficients vs mapoli
uv run legmodel variants                           # list registered variants
uv run legmodel importance                         # variable importance and effect sizes
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

**A fold is one election date, not one calendar year.** Each fold trains on
every race held strictly before its date and predicts the races held on that
date. The training window expands; it never contains the future.

Under the `current` definition that is **23 folds over 424 races** --- 6
general-election dates carrying 400 races, and 17 special-election dates
carrying 24 between them. The schedule is derived from the `election_date`
values in the race table rather than enumerated in code, so a new election
year adds folds without a code change.

| Fold | Train window | Train | Holdout | Specials | Date |
|---|---|---|---|---|---|
| 2014-01-07 | 2010-05-11 - 2013-11-05 | 199 | 1 | 1 | special |
| 2014-04-01 | 2010-05-11 - 2014-01-07 | 200 | 3 | 3 | special |
| 2014-11-04 | 2010-05-11 - 2014-04-01 | 203 | 91 | 0 | general |
| 2015-03-31 | 2010-05-11 - 2014-11-04 | 294 | 2 | 2 | special |
| 2015-11-03 | 2010-05-11 - 2015-03-31 | 296 | 1 | 1 | special |
| 2016-03-01 | 2010-05-11 - 2015-11-03 | 297 | 2 | 2 | special |
| 2016-05-10 | 2010-05-11 - 2016-03-01 | 299 | 1 | 1 | special |
| 2016-11-08 | 2010-05-11 - 2016-05-10 | 300 | 59 | 0 | general |
| 2017-07-25 | 2010-05-11 - 2016-11-08 | 359 | 1 | 1 | special |
| 2017-10-17 | 2010-05-11 - 2017-07-25 | 360 | 1 | 1 | special |
| 2017-11-07 | 2010-05-11 - 2017-10-17 | 361 | 2 | 2 | special |
| 2017-12-05 | 2010-05-11 - 2017-11-07 | 363 | 1 | 1 | special |
| 2018-04-03 | 2010-05-11 - 2017-12-05 | 364 | 1 | 1 | special |
| 2018-11-06 | 2010-05-11 - 2018-04-03 | 365 | 72 | 0 | general |
| 2020-03-03 | 2010-05-11 - 2018-11-06 | 437 | 1 | 1 | special |
| 2020-05-19 | 2010-05-11 - 2020-03-03 | 438 | 2 | 2 | special |
| 2020-06-02 | 2010-05-11 - 2020-05-19 | 440 | 2 | 2 | special |
| 2020-11-03 | 2010-05-11 - 2020-06-02 | 442 | 50 | 0 | general |
| 2021-03-30 | 2010-05-11 - 2020-11-03 | 492 | 1 | 1 | special |
| 2021-11-30 | 2010-05-11 - 2021-03-30 | 493 | 1 | 1 | special |
| 2022-11-08 | 2010-05-11 - 2021-11-30 | 494 | 74 | 0 | general |
| 2023-11-07 | 2010-05-11 - 2022-11-08 | 568 | 1 | 1 | special |
| 2024-11-05 | 2010-05-11 - 2023-11-07 | 569 | 54 | 0 | general |

Races held before **2014-01-01** are the seed training window --- the same 199
races of 2010 through 2013 the previous year-based schedule seeded on --- and
are never scored. Keeping the cutoff at the start of 2014 rather than at the
first general election of 2014 is what leaves the holdout population
unchanged by the refold: the same races are scored, redistributed across 23
folds instead of 10.

`2023-05-30` and `2024-03-05` are election dates the `current` definition
admits no races on. They are reported as skipped rather than omitted, which
requires measuring the schedule against the dates in the record rather than
only the dates the definition admits --- otherwise "this definition admitted
nobody that day" and "no election was held that day" look identical.

Run `uv run legmodel folds` to print the schedule under any definition.

Four choices are worth stating plainly.

**Why an earlier election in the same year trains the fold.** Predicting the
2016-11-08 general, a real forecaster had the 2016-03-01 and 2016-05-10
special results in hand. A year-based split discarded them because they shared
a calendar year with the race being predicted. That was information loss
rather than leakage --- strictly conservative --- but it was not the
forecasting task either. Under a date schedule those two specials are in the
training set, as the `Train window` column shows.

**Why several dates are never scored as one event.** The old fold 2017 blended
four dates from July through December, and fold 2020 blended five. Their
metrics mixed races decided on different days, months apart, with different
information available before each. One date, one fold.

**Why split by date rather than at random.** Districts recur across cycles, so
a random split puts one cycle of a district in training and another in test.
The existing `mapoli/model/margin_model_cv.py` splits 80/20 at random and
leaks in exactly this way.

**Why the training window expands rather than slides.** It matches how the
model is used: every past cycle is available when forecasting the next one.

### Special-election dates are folds

17 of the 23 folds are special-election dates holding one to three races each.
They are scored on the same footing as a general election, and their fold rows
are marked as small samples rather than suppressed.

Pooling is **by race, not by fold**, so those 24 races cannot outweigh the 400
on general-election dates merely by occupying more folds. Restricting folds to
general elections would put no special election in the holdout at all, which
is where a special-election term --- or the decision to fit specials
separately --- has to earn its place. See
[`special_handling_result.md`](special_handling_result.md).

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
   with a paired election-date-cluster interval and a decided/undecided label.
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

Most predictors here are knowable before their fold's election year even
begins: a district's PVI, who the incumbent is, whether the ballot carries a
presidential race. Campaign finance is not. The rule a variant must satisfy is
therefore that its predictors are knowable **before its fold's election
date**, and a predictor that becomes knowable only during that year has to
declare an as-of date that is published with every fit using it.

The date, not the year, is the boundary. A special election held in March is
knowable before a general election that November, so its result is available
to that fold — both as a training race and to any predictor derived from
prior results.

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
`ballot_timing`, `redistricting_cycle`, `no_dem_candidate` and
`admitted_by_write_in`. A segment a definition empties is reported with a
count of zero rather than dropped — "`two_party` admits no no-Democrat races"
and "nobody broke that segment out" must not look the same.

### Why `ballot_timing` exists alongside `pres_elec`

**Every special election in the record carries `pres_elec = False`**, because
none has ever fallen on a presidential general date. So the `pres_elec` False
level is not "midterm general elections" — it is a mixture of midterm
generals and specials, and specials are the model's worst-calibrated
population by a wide margin. A bias figure read off that level silently
carries a group the reader is not thinking about.

`ballot_timing` splits them apart:

| Level | What it holds | Races |
|---|---|---|
| `presidential` | general elections on a presidential ballot | 231 |
| `midterm_dem_pres` | general elections off the presidential ballot, under a Democratic president | 271 |
| `midterm_gop_pres` | the same, under a Republican president | 71 |
| `special` | special elections, whatever year or ballot they fell on | 37 |

Counts are over the 610 races the adopted definition admits.

It sits alongside the `pres_elec` and `is_special` breakouts rather than
replacing them, so nothing that read the scorecard before loses a row.

**These are the predictor's own levels, not a set the scorecard derives.**
`ballot_timing` is also a declared categorical predictor
([`variants.py`](../src/legmodel/variants.py)), and a segment row and a
coefficient describing the same population have to be labelled the same — two
level sets under one name is how a writeup ends up with the two quietly
describing different races. The segment reads the level each race's own
predictor carried, which travels with the race in
`holdout_predictions.csv.gz`.

A definition that scores no special election reports `special` with a count of
zero rather than omitting the row, which is how `generals_only` declaring that
it holds out no specials is distinguishable from a run that happened to score
none.

**Renamed from the three-level segment.** The earlier breakout had
`presidential_general`, `midterm_general` and `special`.
`presidential_general` became `presidential`, and **`midterm_general` split in
two** — `midterm_dem_pres` and `midterm_gop_pres` — because the midterm
electorate moves against the party holding the presidency and the record holds
only one Republican-president midterm, the 71 races of 2018. Blending it into
270 Democratic-president midterms hid exactly the group that matters. Any
figure quoted against the old names is a figure over a different population.

The pooled row additionally carries `bias_presidential_general`,
`bias_midterm_general` and `pres_bias_gap`. These three column names predate
the level split and are unaffected by it: `bias_midterm_general` is measured
over the union of `midterm_dem_pres` and `midterm_gop_pres`, because the gap is
a claim about presidential versus non-presidential *ballots*. **All three are
computed over general elections only**, so the special-election segment cannot move a figure
that is supposed to measure ballot timing. The gap is the quantity the
presidential-date variants set out to close, and a variant can narrow it
without moving pooled RMSE at all.

## Comparing two variants

Both variants are scored on the same folds and the same holdout races; a race
missing from either side leaves the comparison entirely. The statistic is the
difference in pooled RMSE.

Its interval comes from sampling election-date fold keys with replacement
10,000 times, carrying every paired race from each sampled date, and
recomputing both race-weighted RMSEs. The point estimate remains equally
weighted by race; only the uncertainty unit changes. A comparison with fewer
than two dates has no estimable interval and is `undecided`. Each row records
`resampling_unit`, `n_clusters`, `bootstrap_resamples`, and `bootstrap_seed`.
The separate sensitivity tables repeat the point comparison after omitting
each general-election date.

Race-bootstrap intervals published before the 2026 forecast-readiness change
are superseded history. They are not interchangeable with the current
election-date-clustered intervals.

A paired t-test on per-race squared errors was rejected: squared errors of
margins are heavily right-skewed -- the no-Democrat races alone sit 30 or more
points from any plausible prediction -- so the normal approximation is poor at
this sample size. ArviZ's LOO and WAIC were rejected as the deciding statistic
because they answer a leave-one-race-out question that ignores the temporal
structure this design exists to respect.

## Reproducibility

Each fit's seed is derived from its variant name, its definition and its fold
— the fold's election date — and published with its results, so a single fold
can be reproduced in isolation rather than only as part of a full run. Reruns
from the committed race table reproduce the scorecard and every per-race
prediction exactly.

Because the seed is derived from the fold, **changing the fold schedule
reseeds every fit**, and figures computed under two schedules are not
comparable race by race. Every published output therefore carries a
`fold_schedule` stamp, and a run appending to outputs carrying a different
stamp — or none — is refused by name rather than quietly mixing the two.

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
| `level_counts` | Training races at each declared level of each categorical the variant declares, zero counts included. A level at zero has a flat likelihood, so its coefficient is a draw from the declared prior rather than an estimate. `no categorical declared` where the variant declares none |
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
| `data/models/holdout_predictions.csv.gz` | One row per definition per variant per holdout race: point prediction, 90% interval, win probability, observed response, the per-race error terms every metric is built from, and the `ballot_timing` level the race's own predictor carried |
| `data/models/scorecard.csv` | One row per definition per variant per segment, with `n_races` and each metric |
| `data/models/variant_comparison.csv` | Paired differences between variants, within one definition |
| `data/models/variant_comparison_sensitivity.csv` | Variant comparisons after omitting each general-election date |
| `data/models/definition_comparison.csv` | The three sections above, per definition pair |
| `data/models/definition_comparison_sensitivity.csv` | Definition comparisons after omitting each general-election date |
| `data/models/probability_calibration.csv` | Fixed Democratic-win probability bins with forecast means, outcomes, and counts |
| `data/models/definition_summary.csv` | Holdout counts per definition |
| `data/models/definition_dropped_races.csv` | Every race each definition drops, with the reason |
| `data/models/threshold_sweep.csv` | Races admitted and scores at each write-in threshold |
| `data/models/coefficients.csv` | Posterior summaries per definition per variant per fold |
| `data/models/fit_diagnostics.csv` | R-hat, ESS, divergences and seed per fit, with the sampler settings and prior declaration that produced them |
| `data/models/coefficient_parity.csv` | Baseline coefficients against the same fit on mapoli's district table |
| `data/models/variable_importance.csv` | Per-predictor marginal effect, contribution spread and drop-one holdout cost. See [`variable_importance.md`](variable_importance.md) |
| `data/models/variable_importance_sensitivity.csv` | Drop-one costs after omitting each general-election date |

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
