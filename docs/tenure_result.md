# Incumbency tenure experiment

The pre-declared four-year tenure variant is **undecided and is not adopted**.
Under the adopted `two_party_or_strongest` definition it lowers pooled RMSE
from 15.008 to 14.951, a difference of +0.056 margin points with a 90%
election-date-clustered interval of [-0.052, +0.185]. Because that interval
contains zero, the existing `baseline` remains the reference model and the
operational forecast is unchanged.

Every figure below comes from `data/models/variant_comparison.csv`,
`data/models/variant_comparison_sensitivity.csv`, `data/models/scorecard.csv`,
or `data/models/fit_diagnostics.csv`. Per-race results are reproducible from
`data/models/holdout_predictions.csv.gz`.

## Question and design

The baseline distinguishes Democratic, Republican, and open-seat incumbency
but gives a first-term incumbent the same value as one who has served for a
decade. This experiment retains that status term and adds signed continuous
service with diminishing returns:

```text
tenure_cap4_signed = party_sign * min(incumbent_tenure_years, 4)
```

`party_sign` is +1 for a Democratic incumbent, -1 for a Republican incumbent,
and 0 for an open seat. Thus one and four years remain distinct, while ten and
twelve years are equivalent. The coefficient tests predictive change within
incumbent races; it does not estimate a causal effect of remaining in office.

The four-year cap was declared primary before scoring. Two- and six-year caps
were declared shape sensitivities, not candidates in a search for the best
historical cap. All arms use identical rolling-origin folds and shared holdout
races.

## Pooled result

Positive RMSE differences favor the tenure variant.

| Arm | Role | Races | Baseline RMSE | Arm RMSE | Difference | 90% clustered interval | Verdict |
|---|---|---:|---:|---:|---:|---:|---|
| `baseline_tenure_cap4` | Primary | 413 | 15.008 | 14.951 | +0.056 | [-0.052, +0.185] | Undecided |
| `baseline_tenure_cap2` | Sensitivity | 413 | 15.008 | 15.023 | -0.015 | [-0.047, +0.032] | Undecided |
| `baseline_tenure_cap6` | Sensitivity | 413 | 15.008 | 14.873 | +0.135 | [+0.007, +0.293] | Cap six lower |

The six-year arm is favorable, but it cannot replace the pre-declared primary
arm after observing the holdout. The result supports further study of the
shape; it does not support adding tenure to the baseline now.

For the primary arm, MAE improves by 0.059 points, CRPS by 0.020, coverage
rises from 0.896 to 0.906, and win accuracy rises from 0.915 to 0.920. Brier
score and win log loss worsen slightly. These secondary metrics do not change
the undecided primary RMSE verdict.

## Where the point improvement comes from

| Segment | Races | Baseline RMSE | Cap-four RMSE | Difference | 90% clustered interval | Verdict |
|---|---:|---:|---:|---:|---:|---|
| Open seat | 113 | 18.022 | 17.994 | +0.028 | [-0.020, +0.090] | Undecided |
| More than 0, less than 2 years | 48 | 11.070 | 10.709 | +0.361 | [-0.405, +0.925] | Undecided |
| 2 to less than 4 years | 29 | 12.267 | 11.873 | +0.394 | [-0.811, +0.871] | Undecided |
| At least 4 years | 223 | 14.374 | 14.385 | -0.011 | [-0.207, +0.167] | Undecided |

The point estimates match the motivating shape: the gains are concentrated
below four years and disappear in the saturated group. The early-tenure bands
are too sparse across election dates for their wide intervals to establish the
effect. The cap-four predictor assigns no additional tenure effect after four
years.

The party split is asymmetric. Among 211 Democratic-incumbent races, cap four
improves RMSE by +0.308 [+0.198, +0.414]. Among 89 Republican-incumbent races,
it worsens the point estimate by -0.543, but the interval [-1.000, +0.021]
still reaches zero. That limited and conflicting Republican evidence is
another reason not to promote the primary variant.

## Censoring coverage

Tenure is derived locally from stable `ma-election-db` candidate identities,
victories, and predecessor-district links. Eight of the 633 committed race
rows reach the beginning of available upstream history before their true
service start. They publish lower bounds and
`incumbent_tenure_left_censored = true`; the smallest lower bound is 17.996
years, above every tested cap.

Three left-censored races enter the adopted holdout. No race is excluded for
unknown capped tenure under any arm or scored definition. Their small segment
is published but is not used for a standalone claim.

## Robustness and diagnostics

Leaving out each general-election date keeps the primary point difference
positive: +0.002 to +0.114 across the six omissions. Cap six is also positive
under every omission, from +0.057 to +0.172. Cap two is negative under five
omissions and barely positive (+0.0003) when 2024 is omitted. These checks
describe date sensitivity; they do not override the primary clustered
interval.

The experiment produced 429 tenure-variant fit diagnostics across seven data
definitions. All passed: zero divergences, zero refused folds, maximum R-hat
1.0038, minimum bulk ESS 2221.3, and minimum tail ESS 2931.4. All 21
definition-by-arm comparisons and 126 leave-one-general-date-out rows were
published. Rebuilt baseline score rows exactly reproduce the pre-experiment
metrics; newly populated categorical level counts are diagnostic metadata, not
a fitted-result change.

## Upstream field recommendation

The experiment did not need an upstream schema change: fitting reads the
committed race table and never reconstructs candidate history. The derivation
nevertheless proved reusable across the full training record, so an issue for
`ma-election-db` is warranted as a data-contract improvement, independently of
whether this model adopts the predictor.

A ready-to-file definition is:

> Add `incumbent_tenure_years` and
> `incumbent_tenure_left_censored` to legislative race output. For the selected
> incumbent, measure elapsed days divided by 365.2425 from the victory that
> began the current uninterrupted chain of service to the current election
> date, excluding the current result. Follow stable `candidate_id` and
> `district_id_prev` through regular elections, special elections, and
> redistricting. Stop at a loss, absence, career gap, broken chain, or source
> boundary. Open seats receive 0 years and false censoring. A chain reaching
> the source boundary publishes its observed tenure as a lower bound and sets
> censoring true. Missing identity, ambiguous predecessors, or disagreement
> with the selected incumbent must fail with the election and candidate
> identified; candidate-name matching is not a fallback.

Validation should cover regular re-election, special-election starts, career
gap resets, redistricting continuity, open seats, source-boundary censoring,
missing identities, ambiguous predecessor chains, and agreement with upstream
incumbent selection. Promotion upstream would centralize a generally useful
historical attribute; it would not itself change this project's retained
baseline or forecast selection.
