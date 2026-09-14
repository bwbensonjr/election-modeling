# Variable importance in the margin model

Which predictors carry the model, and what each one is worth in margin points.
Three measures, because a coefficient alone does not answer the question: a
large coefficient on a near-constant predictor moves nothing, and a
well-identified coefficient can still cost accuracy out of sample. Which is
exactly what `pres_elec` turns out to do.

```bash
uv run legmodel importance                                  # the adopted money model
uv run legmodel importance --variant baseline               # any registered variant
uv run legmodel importance --definition current --no-write
```

Writes `data/models/variable_importance.csv`. The model analysed here is
`baseline_money_logratio` under the adopted `two_party_or_strongest`
definition: 593 races fit, 398 pooled holdout over nine folds, **13.370 RMSE**.

## The three measures

**The marginal effect** is the coefficient itself: the change in Democratic
margin per unit of the predictor, holding the others constant. Because the
model is linear and additive this is exact rather than approximate, and the
terms simply add.

**The contribution spread** is the standard deviation of a term's own
contribution to the fitted margin, over the races the model is fit on. It folds
the coefficient and the predictor's real spread into one comparable number, so
a big coefficient on a predictor that barely varies does not read as important.
A categorical's indicators are summed before the spread is taken: the quantity
of interest is what `incumbent_status` moves, not what `incumbent_gop` moves
alone.

**The drop-one cost** is the change in pooled holdout RMSE when the predictor
is removed and the rest refit over the same nine folds and the same 593 races,
with the same paired bootstrap the variant comparisons use. Every arm keeps the
full variant's `requires`, so all of them score identical races and the
comparison is genuinely paired; the build fails rather than reporting an
unpaired one.

The drop-one arms are **analysis fits**. They are not registered variants and
they write nothing into the scorecard, so this report can be regenerated
without touching a published number.

## What the model leans on

| Predictor | Drop-one cost | 90% interval | RMSE without it | Contribution SD |
|---|---|---|---|---|
| `PVI_N` | **+3.894** | [+2.702, +5.084] | 17.264 | 13.08 |
| `incumbent_status` | **+2.509** | [+1.842, +3.175] | 15.879 | 9.46 |
| `money_logratio_primary` | **+1.656** | [+1.078, +2.228] | 15.026 | 8.01 |
| `pres_elec` | **−0.722** | [−1.116, −0.320] | 12.648 | 3.45 |

Positive means the model needs it. Every interval here clears zero, including
the negative one.

**`PVI_N` is still the model.** It contributes half again as much fitted spread
as anything else, and removing it costs almost four RMSE points — more than the
other three terms' costs combined. District partisanship is the backbone and
everything else is a correction to it.

**Incumbency is the largest single jump.** Its coefficients span 25.8 margin
points from a Republican-held seat to a Democratic-held one, the biggest
discrete effect anywhere in the model — but it applies to a three-level factor
rather than a continuous range, which is why its contribution spread sits below
PVI's.

**Money ranks third, close behind incumbency.** For a predictor added in the
most recent change, +1.656 against incumbency's +2.509 is a strong showing.

## What each variable is worth

Posterior means from the final fold (trained 2010–2023), 89% equal-tailed
intervals.

### `PVI_N` — +1.445 margin points per PVI point [1.340, 1.551]

| Change | Δ margin | 89% interval |
|---|---|---|
| +1 point of district PVI | +1.45 | [+1.34, +1.55] |
| +5 points | +7.23 | [+6.70, +7.75] |
| +10 points | +14.45 | [+13.40, +15.51] |
| across the interquartile range of real districts (10.9 pts) | +15.73 | [+14.58, +16.88] |

Roughly seven PVI points per ten margin points. Across the fitted races PVI
runs from −1.5 at the 10th percentile to +20.6 at the 90th.

### `incumbent_status` — a level contrast, open seat is the reference

| Change | Δ margin | 89% interval |
|---|---|---|
| open seat → Democratic-held | +7.71 | [+5.64, +9.81] |
| open seat → Republican-held | −18.05 | [−20.83, −15.24] |
| Republican-held → Democratic-held | **+25.76** | difference of the two |

Asymmetric, and sensibly so: the average seat in this table is already
Democratic, so a Democrat holding one is close to the default while a
Republican holding one is a large departure from it.

### `money_logratio_primary` — +3.863 per unit of log ratio [3.378, 4.342]

| Change | Δ margin | 89% interval |
|---|---|---|
| even money → 2× the opponent | +2.68 | [+2.34, +3.01] |
| even money → 3× | +4.24 | [+3.71, +4.77] |
| even money → 10× | +8.89 | [+7.78, +10.00] |
| outraised 2× → outraising 2× | +5.35 | [+4.68, +6.02] |
| across the interquartile range of real races (7.9×) | +7.98 | [+6.98, +8.97] |

The effect is **scale-free**, which is why this form beat the dollar
difference: $10k against $5k, $50k against $25k and $400k against $200k are all
the same 2× advantage and all worth the same +2.68 points. A flat dollar gap is
not — $20,000 is a rout in a quiet district and a rounding error in a targeted
one. See [`money_results.md`](money_results.md).

### `pres_elec` — +7.085 for a presidential-year ballot [5.189, 8.938]

Quote this one with the caveat below. The interval is nowhere near zero, and
the holdout still says the term does more harm than good.

## The disagreement: `pres_elec` is well identified and still wrong

Both of these are true, and the second is the one that counts:

- its coefficient is large and tight — **+7.09** margin points,
  [+5.19, +8.94];
- removing it **improves** the holdout by **0.722** RMSE, [−1.116, −0.320].

The reason is the fold structure. `pres_elec` is a property of the calendar
year, and folds *are* years, so its value is constant across every race in a
holdout — a wrong year-level shift lands on all of them in the same direction.
Across the nine folds its coefficient ranges from **7.09 to 13.50**, while
`PVI_N` holds between 1.40 and 1.65 and the money term between 3.28 and 4.13.

There is no stable presidential-year effect to estimate. Mean Democratic margin
by year, presidential years marked:

| Year | 2010 | 2012\* | 2014 | 2016\* | 2018 | 2020\* | 2022 | 2024\* |
|---|---|---|---|---|---|---|---|---|
| Mean margin | +17.9 | +27.5 | +17.4 | +17.5 | +14.6 | +13.9 | +19.6 | +17.1 |

2012 was a Democratic wave; 2020 was not; 2018, a midterm, sits below both.

This corroborates a finding already in the record rather than overturning it.
The baseline was measured running 6.4 points too Republican in non-presidential
years and 2.7 too Democratic in presidential ones, and both
`baseline_national_env` and `baseline_year` were introduced to absorb the swing
a single binary cannot — see [`variant_results.md`](variant_results.md). What
is new is that once campaign finance is in the model, the binary is no longer
merely misspecified; it is net harmful.

**This is not yet a recommendation to drop it.** `baseline_money_logratio` is
the published, adopted money variant and its numbers stand as scored. Testing
`PVI_N + incumbent_status + money_logratio` without `pres_elec` is a registry
entry and a rescore, and until that is run and compared under every scored
definition there is no adopted alternative — the drop-one arm here is an
analysis fit, not a scored variant.

## A worked race

The median fitted race: an open seat in a D+6.1 district, no presidential
ballot, the Democrat outraising the opponent about 2×.

| Term | Value × coefficient | Contribution |
|---|---|---|
| Intercept | — | +0.22 |
| `PVI_N` | 6.15 × 1.445 | +8.89 |
| `incumbent_status` | open seat, the reference level | 0.00 |
| `pres_elec` | not a presidential year | 0.00 |
| `money_logratio_primary` | 0.71 × 3.863 | +2.73 |
| **Predicted Democratic margin** | | **+11.84** |

The residual scale is 12.51 margin points, so the 90% predictive band on that
race is about ±20.6. Every effect on this page is small next to the noise in a
single race, which is why the model is scored on 398 of them rather than judged
on one.

## Two caveats on "holding all else constant"

**The predictors are correlated, so the isolated move is rare.** Money
advantage correlates with `PVI_N` at 0.38, with Democratic incumbency at 0.30,
and with Republican incumbency at −0.38. A district ten points bluer also tends
to hold a better-funded Democrat. The coefficient answers "what does the model
add for one more PVI point", not "what happens in the world when a district
gets bluer" — in the world, the other terms move too.

**Money is the one predictor whose effect is not a lever.** Donors read the
same signals a forecaster does, so a candidate who looks likely to win raises
more *because* of it. The +2.68 points for doubling a money advantage is a real
forecasting improvement; it is not a claim that raising twice as much would
earn a candidate 2.68 more points. See
[`money_results.md`](money_results.md#endogeneity).

## Published output

`data/models/variable_importance.csv`, one row per design-matrix parameter:

| Column | Meaning |
|---|---|
| `predictor`, `parameter` | The declared predictor and the design column it expands to. A categorical contributes several parameters and shares one drop-one cost |
| `coefficient`, `eti89_lb`, `eti89_ub` | Final-fold posterior mean and 89% equal-tailed interval |
| `fold_min`, `fold_max` | Spread of the posterior mean across all nine folds. A wide spread here is instability, not precision |
| `contribution_sd`, `contribution_iqr` | Spread of the term's contribution to the fitted margin |
| `predictor_sd` | Spread of the predictor itself, over the fitted races |
| `drop_one_rmse`, `drop_one_cost` | Pooled holdout RMSE without the predictor, and the change from the full model |
| `ci_low`, `ci_high`, `decided` | 90% paired-bootstrap interval on the cost, and whether it clears zero |

Reproducibility follows the rest of the harness: each arm's seed derives from
its variant name and fold year, so the report regenerates exactly. All 45 fits
behind this page passed their sampling diagnostics — worst R-hat 1.0037, zero
divergent transitions.
