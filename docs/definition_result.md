# The data-definition decision

> Supersession note: numeric intervals and verdicts below document the earlier
> race-bootstrap analysis. They are superseded by the election-date-clustered
> rows in `data/models/definition_comparison.csv` and its leave-one-date
> sensitivity table. Point estimates still describe the paired race sets.

*Rescored under the date-based fold schedule; figures computed on the
year-based schedule are superseded, not reproduced. Every verdict on this page
survived the refold unchanged. See [`scoring.md`](scoring.md).*

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
| `current` | 623 | 424 | 24 | 199 | 15.612 |
| `two_party` | 517 | 346 | 22 | 171 | 12.761 |
| `two_party_or_strongest` | 610 | 413 | 24 | 197 | 15.008 |
| `write_in_5pct` | 625 | 426 | 24 | 199 | 16.161 |
| `no_dem_excluded` | 610 | 413 | 24 | 197 | 15.031 |
| `no_dem_train_only` | 623 | 413 | 24 | 199 | 15.113 |
| `generals_only` | 610 | 389 | 0 | 201 | 14.177 |

These RMSEs are **not comparable to each other.** Each is computed over that
definition's own holdout, against its own response. The next table is the one
that compares.

## Paired on shared races

Each row is `current` against the named definition, on the races both hold out,
with a paired election-date-cluster interval over those races.

| Against | Shared | `current` | Other | Difference | 90% interval | Verdict |
|---|---|---|---|---|---|---|
| `two_party` | 346 | 12.447 | 12.761 | -0.314 | [-0.837, +0.384] | undecided |
| `two_party_or_strongest` | 413 | 15.123 | 15.008 | +0.115 | [-0.237, +0.601] | undecided |
| `write_in_5pct` | 424 | 15.612 | 15.607 | +0.006 | [-0.021, +0.029] | undecided |
| `no_dem_excluded` | 413 | 15.123 | 15.031 | +0.092 | [+0.048, +0.138] | **`no_dem_excluded` lower** |
| `no_dem_train_only` | 413 | 15.123 | 15.113 | +0.010 | [-0.008, +0.029] | undecided |

In every case both models also trained on different race sets, so a difference
isolates neither the response nor the eligibility rule on its own.

### Question 1: the two-party response

**Undecided, and the pooled figure is a trap.**

On its own holdout `two_party` posts 12.761 against `current`'s 15.612 — a
2.9-point improvement that looks decisive. On the 346 races the two actually
share, the difference is **-0.314 with an interval of [-0.837, +0.384]**.

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
(+0.115, undecided). Specials are the scarce segment and the `is_special`
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

`current` against `write_in_5pct` is **+0.006 [-0.021, +0.029]**, undecided —
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
against `current` is **+0.092 with an interval of [+0.048, +0.138]**, which
excludes zero.

The distinction between the two exclusion treatments is what makes this
informative:

- `no_dem_train_only` keeps the 13 races in training and withholds them from
  scoring. Against `current` it is **+0.010 [-0.008, +0.029]** — undecided, as
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
and taking them out lowers the pooled figure mechanically. The +0.092 above is
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

## The sixth definition: `generals_only`

Registered later, with the ballot-timing work, and **not adopted on this
evidence.**

It is `two_party_or_strongest` with special elections marked **train-only**:
the same 610 races, the same response, the same threshold, the same
no-Democrat treatment. All 37 admitted specials stay in every fold's training
set and none enters a holdout. The holdout is **389 races over 6
general-election dates**, against 413 over 23 — the schedule loses the 17
special-election dates entirely, because a definition that scores no special
has nothing to hold out on a date that carried only specials.

Paired against the adopted definition on the races both hold out, using
`baseline_timing` (the only variant scored under both at the time):

| Against | Shared | `two_party_or_strongest` | `generals_only` | Difference | 90% interval | Verdict |
|---|---|---|---|---|---|---|
| `generals_only` | 389 | 13.426 | 13.422 | +0.004 | [-0.012, +0.022] | undecided |

The response column is identical and the shift on shared races is exactly
zero, so this isolates the training question alone: withholding 24 specials
from the holdout changes what the models trained on, and it moved nothing.

**Why that is not an argument for adopting it.** The 24 races exclusive to
`two_party_or_strongest` are scored at RMSE **23.790** — the worst segment in
the model by a wide margin. A definition that declines to score its hardest
races posts a lower pooled figure for that reason alone, and the pooled
`generals_only` number (14.177 for `baseline`, against 15.008) is mostly that
effect rather than a better model. The existing definition-comparison
procedure reports the exclusive races separately precisely so that cannot be
banked as an improvement.

What it is good for is isolating the timing question: with specials out of the
holdout, a timing figure is about ballots rather than about a mixture of
ballots and specials. See [`timing_result.md`](timing_result.md), where every
result is reported under both definitions and none of them depends on the
choice.

## What this supersedes

The published baseline scorecard is recomputed. Under the adopted definition
the baseline scores **15.008 over 413 races** rather than 15.612 over 424. The
two are not the same measurement: different races, different response.

`current` remains registered and scorable, so the old figures stay reproducible
rather than merely archived. Its baseline now reads 15.612 against the 15.608
committed before the definition machinery existed. That residual was MCMC
noise from the seed gaining a definition component; it is now also a refold,
since the seed keys on the fold and folds are election dates. The holdout race
set and every observed response remain bit-identical — 424 races either way —
which is the check that matters: the refold redistributed those races across
23 folds rather than 10, and did not change which races are scored.
