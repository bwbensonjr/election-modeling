## Context

See `proposal.md` for motivation. The constraints that shape the approach:

- **The data already exists and is fixed.** `data/precinct/ma_precinct_training_set.csv.gz`
  holds 14,188 precinct rows across 623 races, 2010 through 2024, with
  `dem_margin`, `PVI_N`, `incumbent_status`, `pres_elec`, `is_special` and
  `num_candidates` already defined to match the established model. This
  change consumes that table; it does not revisit how it was built.
- **The race counts are small and unevenly distributed.** 586 general and 37
  special races. Specials cluster in odd years, which carry between one and
  seven races each. Any evaluation design has to decide what to do with
  years that hold a single race.
- **2019 is empty.** The table has no contested races for 2019, so the fold
  schedule is not simply "every year in a range".
- **The model being replicated is `stan_glm`, and the prior art is in two
  languages.** `mapoli/model/ma_leg_model.R` fits the model in R with
  rstanarm; `mapoli/model/margin_model_cv.py` already ports it to
  Bambi/PyMC but evaluates with a random 80/20 split. The Python port is the
  starting point; its split is the part being replaced.
- **The district-level reference table is partly wrong.** `docs/schema.md`
  documents an operator precedence bug in the R `democratic_margin()` that
  makes `dem_margin` wrong for the 13 races with no Democratic candidate.
  The reference is usable for validating the other 610 and not for those.

## Goals / Non-Goals

**Goals:**

- A scoring procedure fixed before any model comparison is run, so later
  variables and algorithms are measured against an unmoved yardstick.
- Separation between the data pipeline and the modeling code, so a scoring
  run never depends on the network or the fetch cache.
- Enough published detail per run -- per-race predictions, per-fold and
  per-segment breakdowns, fit diagnostics -- that a pooled number can be
  taken apart rather than trusted.
- An honest verdict mechanism: a comparison that the data cannot settle is
  reported as unsettled.

**Non-Goals:**

- No hyperparameter search, prior sensitivity analysis, or model averaging.
- No caching of fits. Twenty MCMC fits on at most 569 rows is cheap enough
  that a full rerun is the reproducibility story.
- No abstraction over model families. The scoring harness takes a fitted
  object that can produce posterior predictive draws; making that work for
  gradient boosting is a later change's problem, and the interface is chosen
  not to preclude it.

## Decisions

### D1: The race rollup is a pipeline stage; modeling is a separate package

`maprecinct` gains a `races` stage, ordered after `training`, writing
`data/race/ma_race_training_set.csv.gz`. Fitting and scoring live in a new
`legmodel` package with its own console script.

The rollup is a data product: it is derived from committed inputs by a fixed
rule, it belongs in the same dependency chain as `training` and `validate`,
and its validation against `mapoli`'s district table is the same kind of
check `validate` already performs. Modeling is not a data product -- it
consumes committed CSVs and nothing else, so keeping it in a separate
package makes the direction of dependency explicit and keeps the heavy
`pymc` dependency out of the collection path.

*Alternative considered:* put the rollup in `legmodel` and compute it in
memory at fit time. Rejected because the race table is the thing later
changes will add columns to, it needs the same validation treatment as the
other published tables, and an in-memory rollup cannot be inspected.

### D2: Margin and PVI are recomputed from summed votes, never averaged

District `dem_margin` comes from summing `dem_votes`, `opponent_votes` and
`candidate_votes` across the race's precincts. District `PVI_N` comes from
summing the `dem_votes` and `gop_votes` columns in
`data/pvi/ma_precinct_pvi.csv.gz` over the race's precincts and applying the
PVI formula to those totals, joined on `(pvi_year, redistricting_cycle,
city_town, ward, precinct)`.

Averaging precinct `PVI_N` would weight a 300-vote precinct the same as a
3,000-vote one, and would not reproduce the published district PVI. Summing
the underlying votes is the definition, and it makes the 340 precinct rows
with missing PVI self-handling: a precinct with no two-party presidential
votes contributes zero to both sums, which is exactly right, rather than
requiring a decision about how to average around a null.

### D3: Missing PVI is a coverage number, not an exclusion rule

Each race row records `pvi_coverage`, the share of its precincts that
contributed presidential votes, and `pvi_interpolated_share`, the fraction of
its PVI input votes carrying `areal_interpolation` provenance. A race is
excluded only when coverage is zero, in which case `PVI_N` is undefined and
the model has nothing to condition on. Everything else is published with its
coverage attached.

126 races contain at least one precinct with missing PVI and 50 have more
than 10% of precincts missing, but most of those precincts also cast no
legislative votes -- they are administrative artifacts rather than real
gaps. A coverage threshold picked in advance would be arbitrary; publishing
the number lets a later change exclude on it with evidence.

### D4: The model is fit at race grain

Confirmed with the user. The baseline is a replication of the existing
district-grain model, and the scoring procedure is defined at race grain so
that a later precinct-grain model is scored on the same 424 races and the
two results are directly comparable. Fitting the baseline at precinct grain
would also misstate the likelihood: `docs/schema.md` notes that precinct
rows within a race are strongly correlated, so 14,188 independent
observations would produce posterior intervals far too narrow.

### D5: Rolling-origin, expanding window, every election year from 2014

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

Pooled holdout: 424 races, 24 of them special.

The expanding window matches how the model is actually used -- every past
cycle is available when forecasting the next one -- and never trains on the
future. The seed window ends at 2013 because a first fold needs enough races
to fit four parameters with the redistricting boundary at 2012 already
inside it, so the model has seen a map change before being asked to predict
across one.

*Alternative considered, and the reason this differs from the original
request:* folds on even years only. That schedule puts 9 specials in the
holdout, none of them in 2022 or 2024, which is too thin to say anything
about `is_special` -- the variable whose value this harness exists to test.
Including odd years raises that to 24. Odd-year folds are 100% special
elections, which is the segment the term is supposed to serve.

*Alternative considered:* leave-one-year-out, training on every other year
including later ones. Rejected: it trains on the future, so it measures
interpolation rather than forecasting, and the published use case is a
forecast.

*Alternative considered:* the random 80/20 split in
`margin_model_cv.py`. Rejected for the reason the README already gives:
districts recur across cycles, so a random split leaks a district's behavior
between train and test.

### D6: Pooling is over races, not an average of fold scores

Averaging the ten fold RMSEs would give the 2023 fold, which holds one race,
the same weight as the 2014 fold, which holds 95. Pooling the 424 holdout
races and computing one RMSE weights each race equally, which is what the
primary score should mean. Per-fold RMSEs are still published, as diagnostics
rather than as ingredients of the pooled number.

### D7: RMSE is primary; calibration and win-side metrics are reported beside it

RMSE in margin points is the primary score, per the request. It is in the
units the model predicts, and squaring penalizes the large misses -- a
+15 prediction on a race the Democrat lost by 20 -- that matter most for
ratings.

It is not sufficient on its own. A Bayesian model's value here is its
predictive distribution, and RMSE is blind to whether that distribution is
honest, so 90% interval coverage and CRPS are reported alongside. The
published use case is a win-probability rating, so win-side accuracy and log
loss are derived from the posterior predictive probability that `dem_margin`
exceeds zero -- from the margin model's own draws, not from a second
logistic fit, so the margin and rating outputs cannot disagree.

### D8: The variant comparison is a paired bootstrap over races

Both variants are scored on identical folds and identical holdout races.
The comparison statistic is the difference in pooled RMSE. Its interval
comes from resampling the 424 holdout races with replacement, recomputing
both RMSEs on each resample, and taking the 5th and 95th percentiles of the
difference. Resampling races rather than residuals keeps the pairing: both
variants are always evaluated on the same resampled set.

*Alternative considered:* a paired t-test on per-race squared errors.
Rejected because squared errors of margins are heavily right-skewed -- the
13 no-Democrat races alone sit 30 to 55 points from any plausible prediction
-- so the normal approximation is poor at n=424.

*Alternative considered:* LOO or WAIC from ArviZ. These are cheaper and
well-founded, but they answer an in-sample question, leave-one-race-out,
which ignores exactly the temporal structure this design exists to respect.
They may be reported as supplementary information; they do not decide the
comparison.

### D9: Races with no Democratic candidate stay in, and get their own segment

All 13 are real contested races the model is asked to predict, 11 of them in
the holdout. They are also where a linear model in PVI does worst, and they
will contribute disproportionately to pooled RMSE. Dropping them would
flatter every variant equally and hide a real failure mode, so they stay and
`no_dem_candidate` becomes a reported segment, making their contribution to
the pooled figure visible rather than silent.

### D10: Bambi and PyMC with default priors, one seed per fit

Bambi with `family="gaussian"`, following `margin_model_cv.py`. Priors are
Bambi's defaults, which are weakly informative and autoscaled in the same
spirit as rstanarm's, so the replication is close without hand-tuning
something the original never tuned. Four chains, 2,000 draws each after
tuning.

The seed for a fit is derived deterministically from the variant name and
the fold year and is recorded in the published output, so any single fit can
be reproduced in isolation rather than only as part of a full run. A fit is
flagged when any parameter's R-hat exceeds 1.01, any bulk or tail ESS falls
below 400, or the sampler reports a divergent transition; the flag is
published with the scores rather than aborting the run, because a flagged
fold is information about the fold.

### D11: `incumbent_status` is coded as explicit indicators against the open seat

Treatment coding against the open-seat level, matching the R model, so the
two incumbency coefficients read directly as the advantage of a Democratic
or Republican incumbent over an open seat. The level set is fixed in advance
rather than inferred from the training data, so an early fold that happens
to contain no Republican incumbents still produces a design matrix
compatible with the holdout.

*Revised during implementation.* Leaving the coding to the formula does not
achieve either half of that. Formulae orders a categorical's levels
alphabetically, which silently made `Dem_Incumbent` the reference, so the
incumbency coefficients read against a Democratic hold rather than an open
seat; and naming the reference explicitly with
`C(incumbent_status, Treatment('No_Incumbent'))` fixes that but still derives
the level *set* from the values present, so a fold whose training races lack a
level builds a design matrix that then rejects a holdout race carrying it.
The variant registry therefore expands `incumbent_status` into explicit 0/1
indicator columns, `incumbent_dem` and `incumbent_gop`, with the open seat as
the all-zero reference. Variants still declare `incumbent_status`; the
expansion is an encoding detail. A level entirely absent from a training set
leaves its indicator constant, which is refused with a named error rather than
dropped, because dropping it would predict those holdout races as open seats.

### D12: Output layout

```
data/race/ma_race_training_set.csv.gz     one row per race
data/race/race_pvi_coverage.csv           per-race PVI coverage and exclusions
data/reports/race_rollup_validation.csv   agreement with mapoli's district table
data/models/holdout_predictions.csv.gz    one row per (variant, race)
data/models/scorecard.csv                 one row per (variant, segment)
data/models/variant_comparison.csv        paired differences and intervals
data/models/coefficients.csv              posterior summaries per (variant, fold)
data/models/fit_diagnostics.csv           R-hat, ESS, divergences, seed per fit
```

Long format with a `variant` column throughout, so adding a third variant
adds rows rather than files, and `scorecard.csv` carries `segment_type`,
`segment_value`, `n_races` and one column per metric.

## Risks / Trade-offs

- **424 holdout races may not separate two nested variants that differ by one
  binary term.** → This is the expected outcome as much as a risk, and D8 is
  the mitigation: the comparison reports an interval and the writeup says
  "undecided" when it spans zero. The alternative -- reporting whichever RMSE
  is lower -- is what the harness exists to prevent.
- **24 holdout specials is still thin, and they are concentrated in folds
  with tiny training sets.** → The special-election segment is reported with
  its race count attached so the weight of the evidence is visible, and the
  per-fold breakdown shows whether an effect rests on one fold.
- **Odd-year folds of one or two races produce per-fold RMSEs that are
  almost meaningless.** → They are published as diagnostics only; D6 keeps
  them out of the pooled number's weighting.
- **The 2022 fold trains across a redistricting boundary and predicts on a
  new map.** → This is realistic rather than a defect, and
  `redistricting_cycle` is a reported segment so the cost is measurable.
- **Bambi's default priors are not identical to rstanarm's.** → D10 accepts
  this, and the parity check in the `margin-model` spec is what catches it:
  if the two fits disagree beyond tolerance, the difference is reported
  rather than absorbed.
- **Twenty MCMC fits make the scoring run slow enough to discourage
  rerunning.** → Minutes on 569 rows, and a `--variants` selector lets a
  single variant be rescored without the comparison.
- **pytensor's C backend does not build on current macOS**, which blocks PyMC
  entirely: pytensor passes a `-ld64` flag that the current linker rejects, so
  every compilation fails. → The package probes the C backend once at import
  and falls back to pytensor's Python backend when it cannot build, which
  costs about two seconds per fit at this data size. An explicit
  `PYTENSOR_FLAGS` is left alone.
- **The rollup could silently disagree with the precinct table it came
  from.** → The race table's validation against `mapoli`'s district table,
  plus the `race-training-set` requirement that the build fail rather than
  publish when a race's precinct rows disagree on a carried attribute, cover
  this.

## Open Questions

- Whether `num_candidates`, the third term in the fullest R variant, belongs
  in the baseline. It is deferred: adding it is a new variant
  declaration under the `margin-model` spec's declarative-variant
  requirement, scored by the same harness, and it changes neither the specs,
  the fold schedule, nor the task breakdown.
