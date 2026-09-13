# Does `is_special` improve the baseline?

The first question put to the scoring harness in
[`scoring.md`](scoring.md): does adding a special-election term to the
baseline model lower holdout error?

- `baseline` — `dem_margin ~ PVI_N + incumbent_status + pres_elec`
- `baseline_special` — the same plus `is_special`

Both scored on the identical ten folds and the identical 424 holdout races,
24 of them special.

## Answer

**No, not overall. The pooled difference is undecided, and the term's real
effect is hidden inside it.**

| | baseline | baseline_special | difference | 90% interval | verdict |
|---|---|---|---|---|---|
| **Pooled (424)** | **15.608** | **15.641** | **-0.033** | **[-0.143, +0.078]** | **undecided** |
| Special elections (24) | 23.993 | 22.868 | +1.125 | [+0.266, +1.792] | `baseline_special` lower |
| General elections (400) | 14.956 | 15.098 | -0.142 | [-0.215, -0.070] | `baseline` lower |

RMSE in margin points; a positive difference favours `baseline_special`.

The pooled verdict is not "no effect". It is two real and opposite effects
that cancel. The term helps where it should -- special elections, where it cuts
RMSE by 1.13 points, an interval clear of zero -- and hurts slightly everywhere
else, by 0.14 points, also clear of zero. Because specials are 24 of 424
races, 5.7% of the holdout, the 1.13-point gain on them is worth about 0.06
points pooled, which the 0.14-point loss on the other 400 more than erases.

## What the term is doing

The coefficient is positive in every fold and grows as folds accumulate
specials, settling around +4.7 points by the 2024 fold:

| Fold | 2014 | 2015 | 2016 | 2017 | 2018 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|---|---|---|---|
| `is_special` mean | 3.04 | 2.04 | 4.74 | 5.32 | 7.67 | 3.18 | 5.90 | 6.23 | 5.10 | 4.66 |
| 89% interval low | -4.22 | -4.19 | -1.38 | -0.16 | 2.38 | -2.14 | 1.04 | 1.37 | 0.58 | 0.20 |

So the model does learn something: Democrats outperform their PVI and
incumbency baseline in Massachusetts special elections by roughly four to six
points. The estimate only separates from zero once enough specials have
accumulated, from the 2018 fold onward.

What it buys is visible in the bias rather than in the pooled RMSE. On the 24
holdout specials the baseline is badly pessimistic about Democrats, averaging
**-11.56** points of signed error; adding the term cuts that to **-8.46**.
Interval coverage on specials rises from 0.708 to 0.792 against a nominal
0.90. Both are real improvements on a segment the baseline handles poorly.
Neither is enough to fix it.

The cost is that one extra parameter, estimated from 13 to 37 training
specials, perturbs the fit for the 400 general elections that carry the pooled
score. That is why the general-election RMSE rises by a small but
interval-clear 0.14 points.

## Recommendation

**Keep `baseline` as the reference model.** It is the simpler specification
and the data does not show the pooled score improving.

**Use `baseline_special` when the question is about a special election.** For
rating a specific special, an 8.5-point bias is better than an 11.6-point one,
and this is the situation the term was added for. That the pooled number does
not reward it is a statement about how few specials there are, not about
whether the effect is real.

Neither model should be trusted on a special election as it stands. RMSE of
22.9 against 15.0 on generals, and coverage of 0.79 against a nominal 0.90,
say the predictive distribution is too narrow there.

## Where the model actually fails

The comparison surfaced larger problems than `is_special`. Both variants
behave nearly identically on all of these, so they are properties of the
baseline specification rather than of the term under test. Figures below are
for `baseline`.

| Segment | Races | RMSE | Bias | Coverage |
|---|---|---|---|---|
| Pooled | 424 | 15.61 | -2.87 | 0.892 |
| No Democratic candidate | 11 | 28.35 | +11.88 | **0.364** |
| Special elections | 24 | 23.99 | -11.56 | 0.708 |
| Non-presidential years | 261 | 16.84 | -6.36 | 0.854 |
| Presidential years | 163 | 13.40 | +2.72 | 0.951 |
| State Representative | 323 | 16.02 | -2.90 | 0.876 |
| State Senate | 101 | 14.21 | -2.76 | 0.941 |

- **Races with no Democratic candidate are the worst segment by a wide
  margin.** 28.35 RMSE and 36% coverage: the model is confidently wrong about
  them nine times in ten. They are only 11 races, but they contribute
  disproportionately to the pooled figure. A term for "no Democrat on the
  ballot" looks a more promising addition than `is_special`.
- **`pres_elec` is carrying a bias it cannot absorb.** The model runs 6.4
  points too Republican in non-presidential years and 2.7 points too
  Democratic in presidential ones, which a single binary term applied to every
  race cannot fix. A year effect, or an interaction with incumbency, is worth
  testing.
- **Calibration is good overall** — 89.2% coverage against a nominal 90%, and
  91.8% win-side accuracy — but that pooled figure averages over segments
  running from 0.36 to 0.95. The aggregate looks healthy because the
  well-calibrated majority outweighs the badly-calibrated minority.

## Reproducing this

```bash
uv run legmodel score
uv run legmodel compare baseline baseline_special
```

Every number above is in `data/models/scorecard.csv` and
`data/models/variant_comparison.csv`, and all of them are recomputable from
`data/models/holdout_predictions.csv.gz`.
