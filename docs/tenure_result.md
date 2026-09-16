# Incumbency tenure experiments

The operational tenure replacement is **undecided and is not adopted**. The
pre-declared primary comparison replaces `incumbent_status` with signed
four-year-capped tenure in the current 14-day forecast. On 389 general-election
races, control RMSE is 12.039 and replacement RMSE is 12.122. The control-minus-
replacement difference is -0.083 margin points with a 90% election-date-
clustered interval of [-0.345, +0.181]. Because the interval contains zero,
`forecast_14d` and `forecast_60d` remain selected.

Every comparison figure below is in
`data/models/variant_comparison.csv` or
`data/models/variant_comparison_sensitivity.csv`. Scores, per-race predictions,
coefficients, and sampler evidence are in `data/models/scorecard.csv`,
`data/models/holdout_predictions.csv.gz`, `data/models/coefficients.csv`, and
`data/models/fit_diagnostics.csv`.

## Operational replacement experiment

The frozen control revision is
`ece7e381febdaac64d5b9a30bf16a361cd1b9140`, the definition is
`two_party_or_strongest`, and the general-election row at 14 days is the sole
adoption decision. Both sides use the same `money_complete` route:

- 14-day money: control `PVI_N + incumbent_status + money_logratio_primary`;
  replacement `PVI_N + tenure_cap4_signed + money_logratio_primary`.
- 60-day money: control `PVI_N + incumbent_status + money_logratio_wide`;
  replacement `PVI_N + tenure_cap4_signed + money_logratio_wide`.
- Fallback: control `PVI_N + incumbent_status`; replacement
  `PVI_N + tenure_cap4_signed`.

The replacement therefore tests tenure *instead of* three-level incumbency. It
does not add tenure alongside status and does not include `pres_elec` or
`ballot_timing`. Its fixed shape is:

```text
tenure_cap4_signed = party_sign * min(incumbent_tenure_years, 4)
```

Open seats are zero, Democratic incumbents are positive, Republican incumbents
are negative, and service beyond four years is saturated. A single coefficient
also imposes equal-magnitude, opposite-party effects, whereas
`incumbent_status` estimates separate Democratic and Republican coefficients.
The comparison tests predictive performance under that restriction; it does
not estimate a causal effect of tenure.

### Primary and horizon sensitivity

Differences are control RMSE minus replacement RMSE, so positive values favor
replacement.

| Role | Horizon | Segment | Races | Control RMSE | Replacement RMSE | Difference | 90% interval | Verdict |
|---|---|---|---:|---:|---:|---:|---:|---|
| Primary | 14d | General elections | 389 | 12.039 | 12.122 | -0.083 | [-0.345, +0.181] | Undecided |
| Sensitivity | 60d | General elections | 389 | 12.192 | 12.247 | -0.055 | [-0.341, +0.226] | Undecided |
| Context | 14d | All elections | 413 | 12.679 | 12.785 | -0.106 | [-0.359, +0.142] | Undecided |
| Context | 60d | All elections | 413 | 12.822 | 12.896 | -0.074 | [-0.344, +0.191] | Undecided |

The 60-day result is sensitivity evidence only. It cannot replace an undecided
or losing 14-day primary decision.

### Route, tenure-band, and party evidence

The paired populations are identical at both horizons: 398 complete-finance
races use the money route and 15 use fallback. At 14 days, the money-route
difference is -0.132 [-0.406, +0.109]; fallback is +0.560
[-0.379, +1.381]. Both are undecided.

The 14-day tenure bands show where the pooled point estimate comes from:

| Tenure band | Races | Control RMSE | Replacement RMSE | Difference | 90% interval |
|---|---:|---:|---:|---:|---:|
| Open | 113 | 13.815 | 14.173 | -0.358 | [-0.692, -0.001] |
| More than 0, less than 2 years | 48 | 9.696 | 10.689 | -0.993 | [-4.196, +0.261] |
| 2 to less than 4 years | 29 | 11.288 | 11.097 | +0.192 | [-0.157, +1.272] |
| At least 4 years | 223 | 12.814 | 12.662 | +0.152 | [-0.202, +0.387] |

The open-seat segment favors the control even though both tenure values are
zero, because replacing status changes the fitted intercept and other
coefficients. The two early-tenure bands are too sparse across election dates
to settle their different point estimates. No additional tenure effect is
assigned beyond four years.

Among 211 Democratic-incumbent races the 14-day difference is +0.001
[-0.318, +0.242]. Among 89 Republican-incumbent races it is +0.006
[-0.598, +0.414]. Neither party segment separates the representations, and the
result does not support a claim of party symmetry in the underlying data.

Three left-censored races enter each paired holdout, all with lower bounds at
or above four years, so the cap is known exactly. No holdout race is excluded
for censoring and finance coverage is identical within each pair.

### Stability and diagnostics

Omitting each general-election date leaves the all-election point difference
negative at both horizons. The 14-day values range from -0.264 to -0.043; the
60-day values range from -0.232 to -0.005. None changes sign. These are
sensitivity checks and do not replace the clustered primary interval.

The two replacement composites published 54 component-fit diagnostic rows.
All passed with zero divergences, maximum R-hat 1.0016, minimum bulk ESS
6204.1, and minimum tail ESS 5348.2. Seeds, priors, draws, tuning, chains,
horizons, and concrete components are published with the model outputs.

Before challenger interpretation, the committed `forecast_14d` and
`forecast_60d` rows were snapshotted and independently rescored. Race coverage,
component routing, seeds, settings, and training counts matched, but the
current Python/Numba backend produced small Monte Carlo drift (at most 0.125
margin points in a control point prediction and 0.099 in a coefficient mean).
Those resampled control summaries were rejected. The snapshotted control
predictions, scores, coefficients, and diagnostics were restored exactly, with
only additive route and horizon provenance, and the published comparisons were
then recomputed against that frozen control.

## Legacy incremental experiment

The earlier experiment asked a different question: it retained the historical
`baseline` specification `PVI_N + incumbent_status + pres_elec` and added a
signed tenure term. It is retained as a historical benchmark, not as evidence
choosing the incumbency representation in the operational money forecast.

| Historical arm | Role at the time | Races | Baseline RMSE | Arm RMSE | Difference | 90% interval | Verdict |
|---|---|---:|---:|---:|---:|---:|---|
| `baseline_tenure_cap4` | Pre-declared primary | 413 | 15.008 | 14.951 | +0.056 | [-0.052, +0.185] | Undecided |
| `baseline_tenure_cap2` | Shape sensitivity | 413 | 15.008 | 15.023 | -0.015 | [-0.047, +0.032] | Undecided |
| `baseline_tenure_cap6` | Shape sensitivity | 413 | 15.008 | 14.873 | +0.135 | [+0.007, +0.293] | Cap six lower |

The favorable six-year sensitivity cannot replace the pre-declared cap-four
decision. This legacy result says only that incremental tenure was undecided
against the historical baseline; it does not justify adding or replacing a
term in the selected forecasts.

## Upstream field recommendation

No upstream schema change was required because the committed race table
already carries `incumbent_tenure_years` and
`incumbent_tenure_left_censored`. An issue for `ma-election-db` remains useful
as a data-contract improvement: publish elapsed service from the victory that
began the incumbent's current uninterrupted chain, follow stable candidate and
predecessor-district identities through special elections and redistricting,
set open seats to zero, and mark chains reaching the source boundary as
left-censored lower bounds. Promotion upstream would centralize a reusable
historical attribute; it would not itself change this project's model.
