# Ballot timing as one categorical

Three findings from the date-based refold pointed at one defect: the model
described ballot timing with two booleans, `pres_elec` and `national_env`,
whose joint level set the reader had to reconstruct — and which are exactly
collinear on most of the record. This replaces them with a single declared
categorical and scores the result.

Every figure below is in `data/models/scorecard.csv`,
`data/models/variant_comparison.csv`, `data/models/coefficients.csv`,
`data/models/fit_diagnostics.csv` and `data/models/definition_comparison.csv`,
recomputable from `data/models/holdout_predictions.csv.gz`.

## The three timing groups among general elections

Restricted to general elections, `~pres_elec` unambiguously *means* midterm,
and there are exactly three populations:

| Group | Races |
|---|---|
| general election on a presidential ballot | 231 |
| midterm general under a Democratic president | 271 |
| midterm general under a Republican president | 71 |

Counts are over the 610 races the adopted definition admits. **The third group
is the single 2018 election.** That is the fact the two-boolean spelling hid:
intercept plus `pres_elec` plus `national_env` is three parameters over three
groups, a saturated model, in which one parameter rests on one election.

Special elections are a fourth population, and they are the reason a
categorical needs a fourth level rather than three.

## Why two booleans became one categorical

### `national_env` was exactly collinear with `pres_elec` on nine folds

`national_env` is computed as `midterm × (−1 under a Democratic president, +1
under a Republican one)`. Every midterm in the record before 2017 fell under a
Democratic president, so across those training windows
`national_env = pres_elec − 1` identically: two parameters competing for one
column.

Nothing refused it. The harness tested a predictor against a *grouping
factor* and never against another predictor, which is why `baseline_year_pres`
was refused for this exact shape of collinearity while `baseline_national_env`
was not. The check is now pairwise over the expanded design columns as well,
and refuses on the same terms.

Separating races — how many training races stand between the two terms and
exact confounding — per fold, under the adopted definition:

| Fold | n_train | Republican-president specials in training | Separating races | Outcome |
|---|---|---|---|---|
| 2014-01-07 | 197 | 0 | 0 | refused |
| 2014-04-01 | 198 | 0 | 0 | refused |
| 2014-11-04 | 201 | 0 | 0 | refused |
| 2015-03-31 | 292 | 0 | 0 | refused |
| 2015-11-03 | 294 | 0 | 0 | refused |
| 2016-03-01 | 295 | 0 | 0 | refused |
| 2016-05-10 | 297 | 0 | 0 | refused |
| 2016-11-08 | 298 | 0 | 0 | refused |
| 2017-07-25 | 356 | 0 | 0 | refused |
| 2017-10-17 | 357 | 1 | 1 | fit |
| 2017-11-07 | 358 | 2 | 2 | fit |
| 2017-12-05 | 360 | 4 | 4 | fit |
| 2018-04-03 | 361 | 5 | 5 | fit |
| 2018-11-06 | 362 | 6 | 6 | fit |
| 2020-03-03 | 433 | 6 | 77 | fit |
| … | | | 78–82 | fit |
| 2024-11-05 | 560 | 11 | 82 | fit |

Read the middle of that table carefully. The term becomes identified on
2017-10-17, and for the five folds from there to 2018-11-06 the *entire* basis
for distinguishing a Republican from a Democratic presidency is between one
and six special elections — races that carry `pres_elec = False` and are
therefore coded as a midterm-backlash electorate they are not. Only from
2020-03-03, once the 71 races of the 2018 general are in the training window,
does the separating count jump to 77.

`baseline_national_env`'s holdout consequently falls from 413 races to **253**
under the adopted definition and to 240 under `generals_only`. Its nine
refusals are in `fit_diagnostics.csv` with the reason on each row.

### Special elections were being coded as midterms

No special election in the record has fallen on a presidential general date,
so all 37 carry `pres_elec = False` and all 37 received a `national_env` value
describing a midterm electorate. A March 2016 special was coded identically to
the 2014 midterm.

The categorical gives them their own level instead. Specials stay in training,
so every training row needs *some* value; the three candidates were to code
them by the president's party (the defect above), to give them the
presidential reference level (equally false), or to give them a level of their
own. Only the third is honest.

### The declared levels

`ballot_timing`, with `presidential` as the reference, so every coefficient
reads against a presidential ballot:

| Level | What it is |
|---|---|
| `presidential` | general election on a presidential ballot |
| `midterm_dem_pres` | general election off the presidential ballot, under a Democratic president |
| `midterm_gop_pres` | the same, under a Republican president |
| `special` | special election, whatever year or ballot it fell on |

The level set is fixed in advance rather than inferred per fold, so a fold
whose training races hold only three of the four still builds a design matrix
that accepts a holdout race carrying the fourth.

## `midterm_gop_pres` is unobserved before 2020, and says so

The only races carrying `midterm_gop_pres` are the 71 in the 2018 general.
Folds 2014-11-04, 2016-11-08 and 2018-11-06 therefore train on none of them,
and the last of those three has to predict 71 races at a level its training
window never held.

The fold is not refused. The indicator is all-zero in training, the likelihood
is flat in its coefficient, and the posterior is exactly the declared prior.
`fit_diagnostics.csv` publishes the training count at every level of every
declared categorical, zero counts included, so a prediction resting on a prior
is identifiable as one:

| Fold (generals_only) | presidential | midterm_dem_pres | midterm_gop_pres | special |
|---|---|---|---|---|
| 2014-11-04 | 74 | 110 | **0** | 17 |
| 2016-11-08 | 74 | 201 | **0** | 23 |
| 2018-11-06 | 132 | 201 | **0** | 29 |
| 2020-11-03 | 132 | 201 | 71 | 34 |
| 2022-11-08 | 181 | 201 | 71 | 36 |
| 2024-11-05 | 181 | 271 | 71 | 37 |

The variants declare `Normal(0, 10)` on every timing coefficient rather than
inheriting the fitting library's auto-scaled default, precisely because an
unobserved level's posterior *is* its prior and would otherwise be set by a
scale nobody chose. The recovered posteriors confirm it:

| Fold | `timing_midterm_gop_pres` mean | sd |
|---|---|---|
| 2014-11-04 | −0.155 | 10.03 |
| 2016-11-08 | −0.056 | 10.10 |
| 2018-11-06 | 0.050 | 9.95 |
| 2020-11-03 | 1.694 | 2.09 |
| 2022-11-08 | 1.332 | 1.95 |
| 2024-11-05 | 1.248 | 1.95 |

The first three rows are the prior read back. The last three are an estimate.

**The widened interval is the point.** Mean 90% predictive interval width on
fold 2018-11-06 is **57.7 points**, against 46.9 on 2022-11-08 and 45.9–47.9
on every other fold. The model is saying it does not know what a
Republican-president midterm looks like, rather than borrowing the Democratic
one's estimate and reporting a narrow interval from a different model.

## Comparison results

`baseline_timing` is `PVI_N + incumbent_status + ballot_timing`. It is
**non-nested** against every arm below: it adds `ballot_timing` and removes
`pres_elec` (and, against `baseline_national_env`, `national_env` too), so
each difference is the combined effect of both, not of one term.

Pooled paired differences; a positive difference favours `baseline_timing`.

| Definition | Against | n | Difference | 90% interval | Verdict |
|---|---|---|---|---|---|
| `two_party_or_strongest` | `baseline` | 413 | +0.771 | [+0.394, +1.163] | **`baseline_timing` lower** |
| `two_party_or_strongest` | `baseline_year` | 413 | +0.108 | [−0.287, +0.501] | undecided |
| `two_party_or_strongest` | `baseline_national_env` | 253 | +0.671 | [−0.133, +1.709] | undecided |
| `generals_only` | `baseline` | 389 | +0.754 | [+0.343, +1.169] | **`baseline_timing` lower** |
| `generals_only` | `baseline_year` | 389 | +0.138 | [−0.314, +0.571] | undecided |
| `generals_only` | `baseline_national_env` | 240 | −0.077 | [−0.319, +0.167] | undecided |

The `baseline_national_env` comparisons run on the races both arms still hold
out, which is 253 and 240 rather than 413 and 389, because that variant is
refused on the folds where the two terms are collinear.

**Where the gain is.** The pooled improvement over `baseline` is almost
entirely one segment:

| Segment (vs `baseline`, `two_party_or_strongest`) | n | Difference | Verdict |
|---|---|---|---|
| `midterm_gop_pres` | 71 | **+4.265** | `baseline_timing` lower |
| `presidential` | 157 | −0.036 | undecided |
| `midterm_dem_pres` | 161 | −0.407 | `baseline` lower |
| `special` | 24 | +0.979 | undecided |

That is the finding stated plainly: **the single `pres_elec` term was wrong
about 2018 by about four RMSE points, and splitting the midterm level in two
fixes it.** It costs a little on Democratic-president midterms, which is what
a pooled estimate that no longer absorbs 2018 should do.

Pooled scores:

| Definition | Variant | n | RMSE | bias | coverage 90 | pres bias gap |
|---|---|---|---|---|---|---|
| `two_party_or_strongest` | `baseline` | 413 | 15.008 | −2.895 | 0.896 | 8.99 |
| `two_party_or_strongest` | `baseline_timing` | 413 | 14.237 | −1.652 | 0.913 | 6.60 |
| `two_party_or_strongest` | `baseline_timing_money` | 398 | 12.363 | −1.322 | 0.910 | 7.03 |
| `generals_only` | `baseline` | 389 | 14.177 | −2.381 | 0.910 | 8.98 |
| `generals_only` | `baseline_timing` | 389 | 13.422 | −1.268 | 0.928 | 6.58 |
| `generals_only` | `baseline_timing_money` | 376 | 11.928 | −0.935 | 0.912 | 7.11 |

The categorical narrows the presidential-date bias gap from 8.99 to 6.60 and
halves the pooled bias, without the collinearity `baseline_national_env` used
to buy its bias reduction with.

### The `pres_elec` drop-one cost, re-measured

The standing open issue is that dropping `pres_elec` from
`baseline_money_logratio` *improves* RMSE by 0.705 [−1.100, −0.299] — decided.
Re-measured under the timing categorical
(`uv run legmodel importance --variant baseline_timing_money`), the drop-one
cost of the whole `ballot_timing` term is **+0.273 [−0.185, +0.721] —
undecided**:

| Predictor | Drop-one cost | 90% interval | Decided |
|---|---|---|---|
| `PVI_N` | +4.411 | [+3.253, +5.570] | yes |
| `incumbent_status` | +3.290 | [+2.631, +3.944] | yes |
| `money_logratio_primary` | +1.737 | [+1.191, +2.292] | yes |
| `ballot_timing` | +0.273 | [−0.185, +0.721] | no |

So the term is no longer *actively harmful* — the point estimate has crossed
from negative-and-decided to positive-and-undecided. **This is reported, not
acted on.** The open issue stays open until a variant dropping the timing term
is registered and compared under every scored definition.

## What the `special` coefficient is, and is not

In `baseline_timing_money` its marginal effect is **−1.88 [−5.67, +1.96]**,
and across folds it runs from −10.54 to −0.72. In `baseline_timing` under
`generals_only` it moves from −10.18 on the earliest fold to −3.10 on the
latest, as the training set accumulates specials.

It is **not a validated special-election effect.** Under `generals_only`
nothing in any holdout carries that level, so the coefficient is estimated
from 37 train-only races and never used to predict a scored race. It is a
nuisance parameter absorbing the level shift those races would otherwise
impose on the midterm estimates — which is its job, and the reason keeping
specials in training costs nothing. Under `two_party_or_strongest` it does
predict 24 holdout specials, and that segment's comparison against `baseline`
is undecided at +0.979.

A reader should take from it that specials sit several margin points below a
presidential-ballot general once PVI and incumbency are accounted for, and
nothing more. The question of where special elections belong was measured
separately and is not reopened here; see
[`special_handling_result.md`](special_handling_result.md).

## Reproducing this

```bash
uv run legmodel score --variants baseline_timing baseline_timing_money \
    --definitions generals_only two_party_or_strongest --append
uv run legmodel score --variants baseline_national_env \
    --definitions generals_only two_party_or_strongest --append
uv run legmodel compare baseline baseline_timing \
    --definition generals_only two_party_or_strongest --append
uv run legmodel compare baseline_national_env baseline_timing \
    --definition generals_only two_party_or_strongest --append
uv run legmodel compare baseline_year baseline_timing \
    --definition generals_only two_party_or_strongest --append
uv run legmodel compare-definitions two_party_or_strongest generals_only \
    --variant baseline_timing --append
uv run legmodel importance --variant baseline_timing_money --append
```

See [`scoring.md`](scoring.md) for the fold schedule and the segment
definitions, [`definitions.md`](definitions.md) for `generals_only`, and
[`variant_results.md`](variant_results.md) for the rest of the variant sweep.
