# The variant sweep

Questions 4 and 5 from the README: the presidential-year bias that a single
`pres_elec` term cannot absorb, and whether `num_candidates` belongs in the
baseline. Both are variant declarations scored by the existing harness.

Every figure is in `data/models/scorecard.csv` and
`data/models/variant_comparison.csv`. Each variant is scored under the adopted
definition and under `current`, so no conclusion rests on one definition.

## Result

| Question | Variant | Verdict |
|---|---|---|
| 4 | `baseline_national_env` | **Adopt.** Lowers RMSE by 0.78 and cuts bias from -2.91 to -0.41 |
| 4 | `baseline_year` | **Adopt alongside.** Lowers RMSE by 0.80 and closes the bias gap to -0.34; converges on every fold once specified correctly |
| 4 | `baseline_year_pres` | The contrast arm. Refused on 3 folds, diverges on 2 more: the evidence for dropping `pres_elec` |
| 4 | `baseline_pres_incumbent` | Undecided |
| 5 | `baseline_num_candidates` | Undecided. Does not belong in the baseline |

## Question 4: the presidential-year bias

The baseline runs too Republican in non-presidential years and too Democratic
in presidential ones. A single binary term applied identically to every race
cannot correct a swing of that shape, because it shifts both directions by the
same amount.

Under `current` the baseline reproduces the README's figures exactly:
**+2.74 points of bias in presidential years, -6.35 in non-presidential ones**,
a gap of 9.08.

### What each variant does to the gap

Under the adopted definition:

| Variant | RMSE | Bias | Presidential | Non-presidential | Gap | Coverage |
|---|---|---|---|---|---|---|
| `baseline` | 15.012 | -2.91 | +2.96 | -6.51 | 9.46 | 0.898 |
| `baseline_pres_incumbent` | 14.972 | -2.67 | +2.81 | -6.03 | 8.84 | 0.901 |
| `baseline_year` | 14.209 | -1.89 | -2.11 | -1.76 | **-0.34** | **0.927** |
| `baseline_national_env` | 14.237 | **-0.41** | +2.93 | **-2.46** | 5.39 | 0.923 |

### Paired comparisons against the baseline

| Definition | Variant | Difference | 90% interval | Verdict |
|---|---|---|---|---|
| adopted | `baseline_pres_incumbent` | +0.041 | [-0.073, +0.152] | undecided |
| adopted | `baseline_year` | +0.804 | [+0.410, +1.179] | **lower** (non-nested) |
| adopted | `baseline_national_env` | +0.775 | [+0.201, +1.363] | **lower** |
| `current` | `baseline_pres_incumbent` | +0.044 | [-0.042, +0.134] | undecided |
| `current` | `baseline_year` | +0.749 | [+0.360, +1.144] | **lower** (non-nested) |
| `current` | `baseline_national_env` | +0.720 | [+0.129, +1.303] | **lower** |

The direction and rough size hold under `two_party` (+0.796 and +0.792) and
`write_in_5pct` (+0.809 and +0.712) as well, so no result here is an artifact
of the definition.

`baseline_year` is marked non-nested because it adds `(1|election_year)` and
removes `pres_elec`: its difference from the baseline is the combined effect of
both, not the effect of adding a year term. `variant_comparison.csv` carries
that label and the terms on each side.

### `baseline_national_env` is the one to use

The term is `-1` in a non-presidential year under a Democratic president, `+1`
under a Republican one, and `0` in a presidential year. It is the substantive
story behind a midterm swing — the electorate moves against the president's
party — and, unlike a year effect, it is **known before the election**. It is
the only variant tested that can shift a holdout year's mean, and the only one
usable for a 2026 forward prediction, where it takes the value `+1`.

It nearly eliminates the pooled bias, from -2.91 to **-0.41**, and cuts the
non-presidential-year bias from -6.51 to -2.46. Its fits pass sampling
diagnostics on every fold.

**The caveat, stated because the coefficient invites over-reading.** The term
is one number fit on eight non-presidential years, of which the sign is
negative in six. It is close to being a non-presidential-year intercept with
the 2017-2019 folds flipped. It should be read as "the midterm penalty runs
against the president's party and is worth about four points", not as a
precisely estimated national-environment effect.

### `baseline_year` converges, and is the strongest variant tested

The hierarchical year intercept did what the design predicted: because a
fold's holdout year is by construction absent from training, its effect is
drawn from the year-level hyperprior, which widens the interval rather than
shifting the mean.

**Its fits originally diverged on every fold** --- 9 of 10 under `current`, 10
of 10 under each other definition. That was a specification defect, not a
property of the data, and it is fixed. Under the corrected specification every
fold under every definition now samples cleanly: **zero divergent transitions
across all 40 fits**, worst R-hat 1.0027, lowest bulk effective sample size
2436, against a worst R-hat of 1.275 and an ESS of 11.8 before.

#### What was wrong

Three things, of which the one the earlier writeup proposed was not among
them.

**The non-centred parameterisation was already in place.** Bambi builds group
effects non-centred by default and the project never overrode it --- the
sampler's variable list has always read `1|election_year_offset`. Reaching for
that fix first would have changed nothing.

**The group-SD prior was auto-scaled off the intercept.** Bambi derived
`1|election_year ~ Normal(0, HalfNormal(135.03))` against a response whose own
standard deviation is 25.2 points: a prior treating a 200-point swing between
election years as unremarkable, asked to inform a quantity estimated from as
few as four year groups, six of which hold 7 races or fewer. The variant now
declares `HalfNormal(5)`, a statement about residual year-to-year swings in
margin points, and the declaration is published in `fit_diagnostics.csv`.

**`pres_elec` was collinear with the year grouping.** This was the larger
problem. `pres_elec` is a property of the calendar year, so a per-year
intercept spans it: across the adopted definition's 610 races it varies within
a year only in 2016 and 2020, on **8 races**, and within the 2010-2013
training window not at all. In fold 2014, `pres_elec` *was* the 2012
indicator --- two parameters competing for one column. The variant now drops
it, and the harness refuses any variant carrying a predictor its own grouping
factor contains.

#### The contrast arm is the evidence

Dropping a term because it is confounded is an argument, not a measurement, so
`baseline_year_pres` --- the same variant keeping `pres_elec`, under the same
prior and the same `target_accept` --- was scored alongside. It fails in
exactly the pattern the diagnosis predicts:

| Folds | Races separating `pres_elec` from the year effect | Divergences | Folds failing |
|---|---|---|---|
| 2014-2016 | 0 | refused before sampling | 12 of 12 |
| 2017, 2018 | 3 | 29 | 7 of 8 |
| 2020-2024 | 3 to 8 | 0 | 0 of 20 |

The residual divergences track the separating-race count and nothing else.
With the term kept, a quarter of the folds cannot be fit at all and the rest
converge only once enough races exist to tell the two apart. That is the case
for dropping it, and it did not rest on the modelling argument alone.

The cost of keeping it is also visible in the scores: because
`baseline_year_pres` forfeits three folds, it is scored on 254 holdout races
against 413, and its presidential-year bias gap stays at 7.59 where
`baseline_year` closes it.

#### The corrected result

Under the adopted definition, `baseline_year` against the baseline:

| Variant | RMSE | Bias | Presidential | Non-presidential | Gap | Coverage | Win acc. |
|---|---|---|---|---|---|---|---|
| `baseline` | 15.012 | -2.91 | +2.96 | -6.51 | 9.46 | 0.898 | 0.910 |
| `baseline_national_env` | 14.237 | **-0.41** | +2.93 | -2.46 | 5.39 | 0.923 | 0.915 |
| `baseline_year` | **14.209** | -1.89 | -2.11 | -1.76 | **-0.34** | **0.927** | **0.927** |

The paired difference against the baseline is **+0.804 [+0.410, +1.179]**, and
it holds under every definition (+0.749, +0.796, +0.809). All four intervals
clear zero.

**The improvement grew rather than shrank.** The superseded figures were RMSE
14.503 and a difference of +0.510 [+0.349, +0.672]; correctly sampled, the
same variant posts 14.209 and +0.804. The concern that the calibration gain
was an artifact of bad sampling --- that a diverging sampler explores the
tails badly, inflates predictive spread, and that coverage rewards width ---
was worth having and did not materialise. Coverage held at 0.927 while RMSE
fell.

**The bias gap is the largest change and the most surprising.** It goes from
6.37 under the diverging fits to **-0.34**, closing further than
`baseline_national_env` manages. The mechanism is the removed term rather than
the added one: a year intercept cannot shift a holdout year's mean, since that
year's effect is unobserved. What moved is that the baseline's fitted
`pres_elec` coefficient was applying a four-point presidential-year shift to
every race, and out of sample, alongside a year effect, that shift was
actively miscalibrating. Removing it left the gap near zero.

#### What it still cannot do

**`baseline_year` cannot shift a future year's mean.** A holdout year's effect
is drawn from the hyperprior, centred near zero, which widens the interval
without moving the point estimate. `baseline_national_env` remains the only
variant tested that can move a forward prediction, because the party holding
the presidency is known in advance. For the 2026 target it takes the value
`+1`; the year variant has nothing to say.

The two are not alternatives so much as answers to different questions, and
the near-identical RMSE (14.209 against 14.237) understates how differently
they behave. Reported together rather than ranked.

#### The superseded diagnostics, recorded

The figures in the tables at the top of this page under the pre-fix
`baseline_year` were produced by the fits below, which failed diagnostics.
They are superseded, not reproduced. Divergent transitions per fold:

| Fold | `current` | `two_party` | `two_party_or_strongest` | `write_in_5pct` |
|---|---|---|---|---|
| 2014 | 264 | 269 | 729 | 154 |
| 2015 | 109 | 247 | 212 | 345 |
| 2016 | 191 | 819 | 96 | 277 |
| 2017 | 66 | 101 | 392 | 41 |
| 2018 | 68 | 85 | 45 | 48 |
| 2020 | 7 | 3 | 6 | 6 |
| 2021 | 4 | 15 | 7 | 9 |
| 2022 | 2 | 11 | 14 | 6 |
| 2023 | 6 | 2 | 1 | 2 |
| 2024 | 0 | 1 | 2 | 3 |
| **total** | **717** | **1553** | **1504** | **891** |
| **now** | **0** | **0** | **0** | **0** |

| Definition | Folds failing, before | Worst R-hat | Lowest bulk ESS | Folds failing, now |
|---|---|---|---|---|
| `current` | 9 of 10 | 1.0238 | 247.3 | 0 of 10 |
| `two_party` | 10 of 10 | 1.2751 | 11.8 | 0 of 10 |
| `two_party_or_strongest` | 10 of 10 | 1.1843 | 15.9 | 0 of 10 |
| `write_in_5pct` | 10 of 10 | 1.0540 | 55.8 | 0 of 10 |

The divergences concentrated in the early folds, whose training windows hold
four to seven year groups and no within-year variation in `pres_elec` at all,
and fell by two orders of magnitude once the window reached 2020. Both
patterns were the diagnosis rather than the symptom.

### `baseline_pres_incumbent` does not help

The interaction between presidential-year timing and incumbency is undecided
under all three definitions and barely moves the bias gap (9.46 to 8.84). The
incumbency advantage does not appear to differ enough between presidential and
midterm electorates to matter at this sample size.

## Question 5: `num_candidates`

**Undecided. It does not belong in the baseline.**

| Definition | Difference | 90% interval | Verdict |
|---|---|---|---|
| `current` | +0.026 | [-0.087, +0.130] | undecided |
| adopted | -0.033 | [-0.107, +0.035] | undecided |
| `two_party` | -0.064 | [-0.107, -0.023] | **baseline lower** |

Under `current` it is a wash. Under the adopted definition it is a wash. Under
the strict two-party definition it is **decidedly worse** — which is the
expected result and confirms the README's guess: once the response is measured
on a two-party denominator, the count of candidates carries information the
response has already absorbed, and the term adds variance without adding signal.

The same pattern appears for `baseline_special` under `two_party`
(-0.096 [-0.164, -0.028], baseline lower), for the same reason.

## Bearing on the earlier `is_special` result

`baseline_special` remains undecided under `current` (-0.027 [-0.134, +0.082])
and under the adopted definition (-0.017 [-0.116, +0.086]), reproducing the
conclusion in [`is_special_result.md`](is_special_result.md) on a rebuilt table
and a different response.

Special elections are still the worst general segment: 24 holdout races at an
RMSE of 24.76 against a pooled 15.01, with 0.708 interval coverage. Notably
both of the adopted variants improve them more than the special term does:

| Variant | Special RMSE | Special coverage |
|---|---|---|
| `baseline` | 24.76 | 0.708 |
| `baseline_special` | 23.86 | 0.750 |
| `baseline_year` | 23.25 | 0.750 |
| `baseline_national_env` | **22.68** | **0.792** |

That a national-environment term and a year term each beat an explicit
special-election indicator suggests some of what `is_special` was reaching for
is *when* the race happened rather than anything intrinsic to special
elections. None of the four closes the gap to the pooled figure, and 24 races
is not much to diagnose from, so this stays an open issue rather than a
finding.
