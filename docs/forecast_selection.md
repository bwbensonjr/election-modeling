# Forecast structure selection

The 14-day and 60-day candidates compare ballot timing with no timing on the
same complete-finance races. Point differences below are no-timing RMSE minus
timing RMSE, so a positive point estimate favors timing. The interval samples
whole election dates and the point estimate remains race-weighted.

| Horizon | Definition | Races | Dates | Difference | 90% interval | Verdict |
|---|---|---:|---:|---:|---:|---|
| 14d | `two_party_or_strongest` | 398 | 21 | +0.280 | [-0.841, +1.395] | undecided |
| 14d | `generals_only` | 376 | 6 | +0.211 | [-1.015, +1.401] | undecided |
| 60d | `two_party_or_strongest` | 398 | 21 | +0.164 | [-0.926, +1.224] | undecided |
| 60d | `generals_only` | 376 | 6 | +0.142 | [-1.041, +1.278] | undecided |

Both horizons select the no-timing structure under the predeclared simplicity
tie-break. This is not an accuracy win: the historical election dates do not
separate the structures. Leave-one-general-election sensitivity also reverses
the point sign after omitting 2018-11-06 in every comparison, and after
omitting 2016-11-08 in three of four comparisons.

The resulting operational declarations are:

- `forecast_14d`: `baseline_money_logratio_no_timing` when finance is complete,
  otherwise `baseline_no_timing`.
- `forecast_60d`: `baseline_money_logratio_no_timing_wide` when finance is
  complete, otherwise `baseline_no_timing`.

The evidence rows are published in `data/models/forecast_selection.csv`, with
full sensitivity in `data/models/variant_comparison_sensitivity.csv`.
