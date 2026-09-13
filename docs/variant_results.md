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
| 4 | `baseline_year` | Real improvement, but every fold fails sampling diagnostics |
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
| `baseline_year` | 14.503 | -1.84 | +2.11 | -4.26 | 6.37 | 0.927 |
| `baseline_national_env` | 14.237 | **-0.41** | +2.93 | **-2.46** | 5.39 | 0.923 |

### Paired comparisons against the baseline

| Definition | Variant | Difference | 90% interval | Verdict |
|---|---|---|---|---|
| adopted | `baseline_pres_incumbent` | +0.041 | [-0.073, +0.152] | undecided |
| adopted | `baseline_year` | +0.510 | [+0.349, +0.672] | **lower** |
| adopted | `baseline_national_env` | +0.775 | [+0.201, +1.363] | **lower** |
| `current` | `baseline_pres_incumbent` | +0.044 | [-0.042, +0.134] | undecided |
| `current` | `baseline_year` | +0.478 | [+0.309, +0.647] | **lower** |
| `current` | `baseline_national_env` | +0.720 | [+0.129, +1.303] | **lower** |

The direction and rough size hold under `two_party` as well
(+0.507 and +0.792), so neither result is an artifact of the definition.

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

### `baseline_year` improves calibration, but its fits are flagged

The hierarchical year intercept did what the design predicted: because a fold's
holdout year is by construction absent from training, its effect is drawn from
the year-level hyperprior, which widens the interval rather than shifting the
mean. Coverage rises from 0.898 to **0.927**, the best of any variant, and RMSE
falls 0.51.

**But every fold fails sampling diagnostics** — 9 of 10 folds under `current`
and 10 of 10 under each other definition, all divergent transitions. With ten
to fourteen years of effects, several of them single-race odd years, the
hyperprior is poorly identified. The scorecard marks the affected folds and the
pooled row discloses that it includes them.

The improvement is real and the mechanism is the one intended, but the fits
should not be published as they stand. Reparameterising the year effect, or
raising `target_accept`, is the obvious next step and is out of scope here.

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
`baseline_national_env` improves them more than the special term does — 22.68
RMSE and 0.792 coverage — which suggests some of what `is_special` was reaching
for is national environment rather than anything intrinsic to special
elections.
