# The variant sweep

Questions 4 and 5 from the README: the presidential-year bias that a single
`pres_elec` term cannot absorb, and whether `num_candidates` belongs in the
baseline. Both are variant declarations scored by the existing harness.

Every figure is in `data/models/scorecard.csv` and
`data/models/variant_comparison.csv`. Each variant is scored under the adopted
definition and under `current`, so no conclusion rests on one definition.

**Rescored under the date-based fold schedule.** Every figure below was
recomputed with one fold per election date rather than one per calendar year;
figures from the year-based schedule are superseded, not reproduced, because
the fit seed is derived from the fold. The refold confirmed almost everything:
pooled RMSE moved by less than 0.03 for every fixed-effect variant and the
rank order is unchanged. The two exceptions are recorded below, and one of
them changes a verdict. See [`scoring.md`](scoring.md) for the schedule.

## Result

| Question | Variant | Verdict |
|---|---|---|
| 4 | `baseline_national_env` | **Undecided under three of four definitions**, where it was decided under all four before the refold. Cuts bias from -2.90 to -0.56, but the term is exactly collinear with `pres_elec` for the first nine folds |
| 4 | `baseline_year` | **Adopt.** Lowers RMSE by 0.66 and closes the bias gap to -0.56; converges on every fold |
| 4 | `baseline_year_pres` | The contrast arm. Now refused on **every** fold: the sharper evidence for dropping `pres_elec` |
| 4 | `baseline_pres_incumbent` | Undecided |
| 5 | `baseline_num_candidates` | Undecided. Does not belong in the baseline |

## Question 4: the presidential-year bias

The baseline runs too Republican in non-presidential years and too Democratic
in presidential ones. A single binary term applied identically to every race
cannot correct a swing of that shape, because it shifts both directions by the
same amount.

Under `current` the baseline runs **+2.75 points of bias on presidential-date
general elections and -5.81 on midterm-date ones**, a gap of 8.56.

Those two figures are now computed over general elections only. Every special
election in the record carries `pres_elec = False`, so the old
"non-presidential" figure was a blend of 237 midterm generals and 24 specials,
and specials are the worst-calibrated population in the model. Blended, the
same gap reads 9.08. See the `ballot_timing` segment in
[`scoring.md`](scoring.md).

### What each variant does to the gap

Under the adopted definition:

| Variant | RMSE | Bias | Presidential general | Midterm general | Gap | Coverage |
|---|---|---|---|---|---|---|
| `baseline` | 15.008 | -2.90 | +2.98 | -6.01 | 8.99 | 0.896 |
| `baseline_pres_incumbent` | 14.980 | -2.69 | +2.79 | -5.52 | 8.30 | 0.906 |
| `baseline_year` | **14.344** | -2.30 | -2.29 | -1.73 | **-0.56** | **0.935** |
| `baseline_national_env` | 14.520 | **-0.56** | +2.93 | **-2.81** | 5.74 | 0.915 |

### Paired comparisons against the baseline

| Definition | Variant | Difference | 90% interval | Verdict |
|---|---|---|---|---|
| adopted | `baseline_pres_incumbent` | +0.028 | [-0.083, +0.141] | undecided |
| adopted | `baseline_year` | +0.663 | [+0.283, +1.026] | **lower** (non-nested) |
| adopted | `baseline_national_env` | +0.488 | [-0.311, +1.221] | undecided |
| `current` | `baseline_pres_incumbent` | +0.037 | [-0.049, +0.126] | undecided |
| `current` | `baseline_year` | +0.691 | [+0.312, +1.072] | **lower** (non-nested) |
| `current` | `baseline_national_env` | +0.396 | [-0.375, +1.089] | undecided |

`baseline_year` holds under `write_in_5pct` (+0.728 [+0.361, +1.087]) but is
undecided under `two_party` (+0.104 [-0.352, +0.555]), so it is decided under
three definitions of four rather than all four.

**`baseline_national_env` lost its verdict in the refold.** It was decided
under all four definitions on the year schedule (+0.720, +0.792, +0.775,
+0.712, every interval clear of zero) and is now decided under `two_party`
alone (+0.778 [+0.434, +1.129]). The point estimate fell in every definition,
so this is a real weakening rather than wider intervals; the intervals were
always wide. Why, in the next section.

`baseline_year` is marked non-nested because it adds `(1|election_year)` and
removes `pres_elec`: its difference from the baseline is the combined effect of
both, not the effect of adding a year term. `variant_comparison.csv` carries
that label and the terms on each side.

### `baseline_national_env`: the right idea, not yet identified

The term is `-1` in a non-presidential year under a Democratic president, `+1`
under a Republican one, and `0` in a presidential year. It is the substantive
story behind a midterm swing — the electorate moves against the president's
party — and, unlike a year effect, it is **known before the election**. It
remains the only variant tested that can shift a holdout year's mean, and the
only one usable for a 2026 forward prediction, where it takes the value `+1`.
That argument is structural and survives the verdict below.

It still nearly eliminates the pooled bias, from -2.90 to **-0.56**, and cuts
the midterm-general bias from -6.01 to -2.81. Its fits pass sampling
diagnostics on every fold.

**But it is exactly collinear with `pres_elec` for the first nine folds.**
Every midterm in the record before 2017 had a Democratic president, so
`national_env = -(1 - pres_elec)` identically across those training windows —
two parameters competing for one column:

| Folds | Training window contains | `national_env` |
|---|---|---|
| 2014-01-07 through 2017-07-25 (9) | D-president midterms only | **collinear with `pres_elec`** |
| 2017-10-17 through 2018-04-03 (5) | plus four 2017 specials | identified, by specials alone |
| 2018-11-06 onward (9) | plus the 2018 midterm | genuinely identified |

Nothing refuses it, because the harness's confounding check tests a predictor
against a **grouping factor** and never against another predictor. That is a
gap: `baseline_year_pres` is refused for exactly this shape of collinearity and
`baseline_national_env` is not.

The five folds in the middle band are worse than unidentified — they are
identified by special elections, and those are miscoded. `national_env` is
computed as `midterm = ~pres_elec`, and every special carries
`pres_elec = False`, so a July 2017 special is labelled a midterm-backlash
electorate. So is a March 2016 one.

Read together with the verdict above: the term is unidentified for nine folds,
identified by miscoded races for five more, and properly identified only from
2018-11-06 — at which point its entire basis for distinguishing a Republican
from a Democratic president is the single 2018 election. The undecided verdict
is a fact about the evidence, not about whether midterm backlash is real.

**The caveat that already stood, now sharper.** The term is one number whose
Republican-president level rests on 2018 alone. It should be read as "the
midterm penalty runs against the president's party and is worth about four
points", not as a precisely estimated national-environment effect.

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
problem, though not for the reason first written down here. `pres_elec` is a
property of a race's **election date**, not of its calendar year:
`src/maprecinct/training.py` computes it as `election_date in
PRESIDENTIAL_ELECTION_DATES`, and the training set honours that --- the 2016,
2020 and 2024 specials all carry `False` in presidential years. The variable
is correct; what the earlier wording did was generalise a coverage limitation
into a definitional claim.

The real structure is narrower and worth stating exactly: **every special
election in the record carries `pres_elec = False`**, because none has ever
fallen on a presidential general date. Specials are therefore the only races
that can separate `pres_elec` from a calendar-year effect, and there are few
of them. Across the adopted definition's 610 races `pres_elec` varies within a
year only in 2016 and 2020, on **8 races**, and within the 2010-2013 training
window not at all. In fold 2014, `pres_elec` *was* the 2012 indicator --- two
parameters competing for one column.

The variant drops it, and the harness refuses any variant whose own grouping
factor leaves a predictor unidentified. That refusal is decided per fold from
the training races, never from the calendar, which is why the measured result
below stands unchanged despite the corrected reasoning.

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

**Under the date schedule the contrast arm fails completely.** Grouping on
`election_date` rather than `election_year` makes `pres_elec` constant within
every level of the grouping by construction, so the arm is refused on **all 23
folds** under every definition, from the first fold's 199 training races
onward. It produces no holdout predictions and so has no scorecard row; its 23
refusal rows are published in `fit_diagnostics.csv` instead. That is the same
evidence the year-grouped arm gave, stated as sharply as it can be.

#### The corrected result

Under the adopted definition, `baseline_year` against the baseline:

Under the adopted definition, on the date schedule:

| Variant | RMSE | Bias | Presidential general | Midterm general | Gap | Coverage | Win acc. |
|---|---|---|---|---|---|---|---|
| `baseline` | 15.008 | -2.90 | +2.98 | -6.01 | 8.99 | 0.896 | 0.915 |
| `baseline_national_env` | 14.520 | **-0.56** | +2.93 | -2.81 | 5.74 | 0.915 | 0.915 |
| `baseline_year` | **14.344** | -2.30 | -2.29 | -1.73 | **-0.56** | **0.935** | **0.927** |

The paired difference against the baseline is **+0.663 [+0.283, +1.026]**, and
it holds under `current` (+0.691) and `write_in_5pct` (+0.728) but not under
`two_party` (+0.104 [-0.352, +0.555]) --- decided under three definitions of
four rather than all four.

**The improvement survived two corrections.** The original figures were RMSE
14.503 and a difference of +0.510, produced by fits that diverged; correctly
sampled on year folds the same variant posted 14.209 and +0.804; refit on date
folds with the grouping moved to `election_date` it posts 14.344 and +0.663.
The concern that the calibration gain was an artifact of bad sampling --- that
a diverging sampler explores the tails badly, inflates predictive spread, and
that coverage rewards width --- was worth having and did not materialise.
Coverage is 0.935, the highest of any variant scored.

**The bias gap is the largest change.** It goes from 6.37 under the diverging
fits to **-0.56**, closing further than `baseline_national_env` manages. The mechanism is the removed term rather than
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
the close RMSE (14.344 against 14.520) understates how differently they
behave. Reported together rather than ranked --- though only `baseline_year`
now carries a decided verdict, and `baseline_national_env`'s collinearity with
`pres_elec` (above) is a reason to treat its forward-prediction role as an
argument from structure rather than from measurement.

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
under all three definitions and barely moves the bias gap (8.99 to 8.30). The
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

The same pattern appears for `special_pooled_term` under `two_party`
(-0.097 [-0.186, -0.011], baseline lower), for the same reason.

## Bearing on the earlier `is_special` result

`baseline_special` is now registered as `special_pooled_term`, one of three
arms in a wider question --- whether special elections belong in the
general-election fit at all. That question has its own writeup:
[`special_handling_result.md`](special_handling_result.md).

The term remains undecided against the baseline under `current`
(-0.042 [-0.158, +0.075]) and under the adopted definition
(-0.064 [-0.168, +0.043]), reproducing the conclusion in
[`is_special_result.md`](is_special_result.md) on a rebuilt table, a different
response and now a different fold schedule.

Special elections are still the worst segment: 24 holdout races at an RMSE of
24.77 against a pooled 15.01, with 0.708 interval coverage. Under the date
schedule, `baseline_year` is the only variant here that improves them:

| Variant | Special RMSE | Special coverage |
|---|---|---|
| `baseline` | 24.77 | 0.708 |
| `special_pooled_term` | 24.02 | 0.708 |
| `baseline_year` | **23.68** | **0.792** |
| `baseline_national_env` | 26.40 | 0.708 |

`baseline_national_env` reversing --- it was the best of the four on the year
schedule and is now the worst --- is consistent with the collinearity above:
every special carries `pres_elec = False`, so every special gets a nonzero
`national_env` and is labelled a midterm-backlash electorate, including
specials held in presidential years. The term is being applied to 24 races it
describes incorrectly.

That a year term still beats an explicit special-election indicator suggests
some of what `is_special` was reaching for is *when* the race happened rather
than anything intrinsic to special elections. None of the four closes the gap
to the pooled figure, and 24 races is not much to diagnose from, so this stays
an open issue rather than a finding.
