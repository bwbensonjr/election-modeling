# The data-definition decision

Questions 1 through 3 from the README — the two-party response, the write-in
threshold, and races with no Democratic candidate — settled together, because
each one rebuilds the training table and invalidates the scorecard. Deciding
them one at a time would have meant rebuilding and republishing three times.

Every figure here is in `data/models/definition_comparison.csv`,
`data/models/scorecard.csv`, `data/models/definition_summary.csv` or
`data/models/threshold_sweep.csv`. The procedure is in
[`definitions.md`](definitions.md) and [`scoring.md`](scoring.md).

## Result

**Adopted: `two_party_or_strongest`.** The response is the two-party margin
where both major parties stood, and the margin against the strongest
non-Democrat on that pair's own two-candidate denominator where no Republican
ran. Races with no Democratic candidate are excluded. The write-in threshold
stays at the ballot-line rule.

The measurements did not separate the candidate definitions. The choice rests
on the principle fixed in advance: **the response and the predictor should be
measured against the same denominator.**

## What each definition admits

| Definition | Races | Holdout | Specials | Smallest fold | Own RMSE |
|---|---|---|---|---|---|
| `current` | 623 | 424 | 24 | 199 | 15.611 |
| `two_party` | 517 | 346 | 22 | 171 | 12.734 |
| `two_party_or_strongest` | 610 | 413 | 24 | 197 | 15.012 |
| `write_in_5pct` | 625 | 426 | 24 | 199 | 16.184 |
| `no_dem_excluded` | 610 | 413 | 24 | 197 | 15.029 |
| `no_dem_train_only` | 623 | 413 | 24 | 199 | 15.117 |

These RMSEs are **not comparable to each other.** Each is computed over that
definition's own holdout, against its own response. The next table is the one
that compares.

## Paired on shared races

Each row is `current` against the named definition, on the races both hold out,
with a paired bootstrap interval over those races.

| Against | Shared | `current` | Other | Difference | 90% interval | Verdict |
|---|---|---|---|---|---|---|
| `two_party` | 346 | 12.423 | 12.734 | -0.311 | [-0.828, +0.380] | undecided |
| `two_party_or_strongest` | 413 | 15.123 | 15.012 | +0.111 | [-0.236, +0.589] | undecided |
| `write_in_5pct` | 424 | 15.611 | 15.631 | -0.020 | [-0.050, +0.007] | undecided |
| `no_dem_excluded` | 413 | 15.123 | 15.029 | +0.094 | [+0.049, +0.143] | **`no_dem_excluded` lower** |
| `no_dem_train_only` | 413 | 15.123 | 15.117 | +0.006 | [-0.011, +0.024] | undecided |

In every case both models also trained on different race sets, so a difference
isolates neither the response nor the eligibility rule on its own.

### Question 1: the two-party response

**Undecided, and the pooled figure is a trap.**

On its own holdout `two_party` posts 12.734 against `current`'s 15.611 — a
2.9-point improvement that looks decisive. On the 346 races the two actually
share, the difference is **-0.311 with an interval of [-0.828, +0.380]**.

The gap is not accuracy. It is the **78 holdout races `two_party` drops, which
`current` scores at an RMSE of 25.30**. Restricting to Democrat-versus-Republican
races removes the hard ones, and a pooled comparison credits the model for
declining to predict them. This is exactly what the cross-definition comparison
mode was built to expose, and reporting only the pooled numbers would have
produced a confident and wrong conclusion.

The response itself moves very little: over the shared races the median shift
is 0.000, 17 races move more than a point, and the largest is 16th Essex 2014
at 54.4. So this is a no-op for most of the data and decisive for a handful,
as the README anticipated.

**The sub-question the README flagged — whether dropping 106 races is worth
it — answers itself.** `two_party_or_strongest` recovers 93 of them by
comparing the Democrat against the strongest non-Democrat where no Republican
ran, keeps **24 holdout specials instead of 22**, and costs nothing measurable
(+0.111, undecided). Specials are the scarce segment and the `is_special`
result already rests on only 24 of them. There is no case for paying 67
holdout races and two specials for a restriction the data does not reward.

### Question 2: the write-in threshold

**Undecided, and the threshold barely matters above 10%.**

| Threshold | Races published | Added over ballot lines | Holdout |
|---|---|---|---|
| 0% (any write-in) | 633 | +10 | 434 |
| 2% | 629 | +6 | 430 |
| 5% | 625 | +2 | 426 |
| 8% | 624 | +1 | 425 |
| 10% | 624 | +1 | 425 |
| 15% | 623 | 0 | 424 |

These are publishable races. The raw contested counts the README tabulates
(+16, +10, +3, +1, +1, 0) run higher because six all-Democratic fields are
contested but carry no non-Democratic candidate to measure a margin against.

`current` against `write_in_5pct` is **-0.020 [-0.050, +0.007]**, undecided —
and because both name the same response, this comparison isolates the
eligibility rule cleanly, with a response shift of exactly zero on all but one
shared race.

What settles it is the other direction: the **two races the 5% threshold admits
are scored at an RMSE of 63.18.** A race that is contested only because someone
mounted a write-in campaign is not a race this model predicts; admitting it
adds noise and no information. Admissions also stop changing between 8% and
10%, so any threshold in that range is the same rule under a different name.

The threshold therefore stays at the ballot-line rule. The asymmetry the README
identified is nonetheless fixed: under the adopted definition a write-in is
treated the same way by the contested test and by the denominator, rather than
counting for one and not the other. 28th Middlesex 2013 keeps Hanlon's 33.4% in
the denominator because every named candidate counts at the build threshold,
and the rule that puts him there is the same rule that would have admitted the
race.

### Question 3: races with no Democratic candidate

**Decided: exclude them, from training as well as scoring.**

This is the only definition comparison the data settles. `no_dem_excluded`
against `current` is **+0.094 with an interval of [+0.049, +0.143]**, which
excludes zero.

The distinction between the two exclusion treatments is what makes this
informative:

- `no_dem_train_only` keeps the 13 races in training and withholds them from
  scoring. Against `current` it is **+0.006 [-0.011, +0.024]** — undecided, as
  it must be, since both models trained on the same races and the comparison
  runs over the same 413. This is the control.
- `no_dem_excluded` also removes them from training, and *that* is what
  produces the decided gain.

So the 13 races were not merely unpredictable, they were **distorting the fit
for the other 610**. Their response is a negated construction that means
something different from every other row, and the model was estimating one
PVI-to-margin relationship across both.

**Stated plainly, because the scorecard makes it easy to overstate:** most of
the apparent improvement from dropping these races is removal, not accuracy.
They are 11 holdout races scored at an RMSE of 28.41 against a pooled 15.12,
and taking them out lowers the pooled figure mechanically. The +0.094 above is
the part that is *not* removal — measured on the 413 races that stay, it is the
benefit of not training on them.

## The tie-break

Four of the five comparisons came back undecided, which the holdout size made
likely. The tie-break was fixed before the numbers were seen: the response and
the predictor should share a denominator. `PVI_N` is a two-party quantity, so
the response should be too.

`two_party_or_strongest` satisfies that for every race it admits — the
two-party denominator where both major parties stood, and the two-candidate
denominator otherwise — while keeping 610 races, 413 holdout races and all 24
holdout specials. `two_party` satisfies the same principle more narrowly and
pays 93 races and two specials for it, with no measured return. `current`
leaves the mismatch in place.

The adopted definition also excludes no-Democrat races by construction, which
was separately decided a real improvement.

## What this supersedes

The published baseline scorecard is recomputed. Under the adopted definition
the baseline scores **15.012 over 413 races** rather than 15.611 over 424. The
two are not the same measurement: different races, different response.

`current` remains registered and scorable, so the old figures stay reproducible
rather than merely archived. Its baseline now reads 15.611 against the
committed 15.608 — the residual is MCMC noise, because the random seed now
keys on the definition as well as the variant and fold. The holdout race set
and every observed response are bit-identical.
