# Data definitions

A **definition** answers two questions the training data cannot answer for
itself: *who counts as a candidate*, and *what is the margin measured against*.
It is a named configuration applied over the published tables, not a property
baked into them, so testing an alternative is a filter and a column choice
rather than a rebuild.

```bash
uv run legmodel definitions                       # list them
uv run legmodel score --definitions two_party     # score under one
uv run legmodel compare-definitions current two_party
```

## What a definition states

Four things, all explicit — none left to a default inside the fitting code:

| Parameter | Meaning |
|---|---|
| **Eligibility** | Which races are admitted, as a list of named criteria |
| **Response** | Which column the model is fit against |
| **Write-in threshold** | The share of named-candidate votes at which a write-in counts as a candidate |
| **No-Democrat treatment** | `keep`, `exclude`, or `train_only` |

A definition **may** additionally mark a named class of race **train-only** on
grounds of the kind of contest it is rather than of its response. That is a
fifth statement, declared the same explicit way, and the class is named in the
definition's own record — so "this definition does not *score* special
elections" and "this definition does not *admit* special elections" are
distinguishable in the declaration and not only in the counts. Like
eligibility, a train-only class may read only columns describing the kind of
contest and who stood in it, never the outcome.

### Eligibility is declared, not coded

A criterion is registered with the columns it reads, and those columns must
come from a fixed allowlist covering candidate presence, party, and write-in
share. A criterion that reads a response column, a vote count, or the winner is
refused at registration:

```
eligibility criterion 'close_race' reads ['dem_margin'], which is not a
candidate-presence, party, or write-in column. Eligibility must not depend on
the outcome of the race
```

This is what makes outcome-blindness a property of the system rather than a
convention. Filtering races on how close they turned out would leak the answer
into the training set.

### The write-in threshold governs both decisions

Before this change the two decisions a write-in affects were made by different
rules: the ballot-line count decided whether a race was contested, and the
precinct returns decided whether the write-in's votes entered the margin
denominator. That is why 28th Middlesex 2013 has three defensible margins:

| Rule | `dem_margin` |
|---|---|
| Write-ins excluded from the denominator | +21.2 |
| Write-in in the denominator, not the comparison (the pre-change rule) | +14.13 |
| Write-in *is* the comparison candidate (mapoli) | +1.68 |

A definition's threshold settles both at once. A write-in at or above it is a
candidate in every respect — it counts toward the contested test, it enters the
denominator in every precinct, and it may be the comparison candidate. A
write-in below it is none of those things.

The threshold is compared against a **district** share, so a write-in that
clears it is admitted in every precinct of that race, including precincts where
it drew no votes. Deciding per precinct would let the comparison candidate vary
within a race.

### The no-Democrat treatment

`keep` leaves the races in and lets a variant use `no_dem_candidate` as a
predictor. `exclude` removes them from training and scoring. `train_only`
keeps them in every fold's training set but withholds them from the holdout —
which tests whether they inform the fit without letting their prediction
failures dominate the score.

A treatment that removes them from scoring lowers pooled RMSE mechanically.
That is reported as removal, not as improvement.

## The registered definitions

| Name | Response | Threshold | No-Dem | Train-only | Races | Holdout | Specials |
|---|---|---|---|---|---|---|---|
| `current` | `dem_margin` | ballot lines | keep | none | 623 | 424 | 24 |
| `two_party` | `dem_margin_two_party` | ballot lines | exclude | none | 517 | 346 | 22 |
| `two_party_or_strongest` | two-party, else strongest pair | ballot lines | exclude | none | 610 | 413 | 24 |
| `generals_only` | two-party, else strongest pair | ballot lines | exclude | `special_elections` | 610 | 389 | 0 |
| `write_in_5pct` | `dem_margin` | 5% | keep | none | 625 | 426 | 24 |

`current` reproduces the rule in force before this change, including its
asymmetry: eligibility on ballot lines, with every named candidate — write-ins
included — in the denominator. It exists so the published baseline scorecard
stays recomputable rather than merely archived.

`two_party_or_strongest` uses the two-party margin where both major parties
stood, and where no Republican ran compares the Democrat against the strongest
non-Democrat **on that pair's own two-candidate denominator**. It is not
`dem_margin`, which divides by every named candidate and would reintroduce the
mismatch the two-party response exists to remove.

`generals_only` is the adopted definition with one thing added: the same 610
races, the same response, the same threshold and the same no-Democrat
treatment, and special elections marked train-only. Any difference between the
two is therefore attributable to the holdout population alone. Its holdout is
**389 races over 6 general-election dates**, and its zero special elections are
zero *by declaration*: all 37 admitted specials stay in the frame and inform
every fit that follows them. `definition_summary.csv` carries the declaration
alongside the counts (`train_only`, `train_only_races`, `training_specials`),
so a reader does not have to infer it from a zero.

## How a threshold is resolved

A definition reads the race table and its companion roster,
`data/race/ma_race_candidates.csv.gz`. The roster carries every named
candidate's district votes and share, so the admitted set at any threshold is
exact rather than inferred from the race table's aggregate write-in columns.

The published tables are built at the most permissive threshold — any named
write-in counts — so every stricter threshold is a filter over them. Recomputing
at that build threshold reproduces the published `dem_margin`,
`dem_margin_two_party`, `no_dem_candidate` and `major_party_race` columns to
within floating-point noise, which is the check that the recomputation and the
pipeline have not drifted apart.

## Comparing two definitions

`legmodel compare` pairs two variants on identical holdout races. Two
definitions do not share a holdout and may not share a response, so comparing
them is a different operation with different hazards. A single number would
hide three simultaneous changes: which races are scored, which races the models
trained on, and what the response measures.

`legmodel compare-definitions` reports all three:

1. **Paired difference on shared races** — the races both definitions hold out,
   with an election-date-clustered interval and a decided/undecided label.
2. **Exclusive races** — what each admits that the other does not, with counts,
   reasons, and each side's score over its own exclusive races.
3. **Response shift** — over the shared races, how far the two responses differ.
   Zero by construction when both name the same response column.

The report states that the two models also trained on different race sets, so
the paired difference isolates neither the response nor the eligibility rule on
its own.

**Why this matters here.** Scored on its own holdout, `two_party` posts an RMSE
of 12.73 against `current`'s 15.61 — an apparently decisive win. On the 346
races the two actually share, the difference is -0.31 with a 90% interval of
[-0.83, +0.38]: undecided. Nearly all of the apparent gap is the 78 races
`two_party` drops, which `current` scores at an RMSE of 25.3. Comparing the two
pooled figures directly would have credited the model for declining to predict
the hard races.

## The adopted definition

Exactly one definition is the published default, used when a run names none,
and its name appears in every output so the default is never silent. The
superseded definitions stay scorable, so a decision can be revisited without
re-running collection.

Where the comparisons come back undecided — which the holdout size makes
likely — the tie is broken on a principle fixed before the numbers were seen:
**the response and the predictor should be measured against the same
denominator.** `PVI_N` is a two-party quantity, so the response should be too.
See [`definition_result.md`](definition_result.md) for the decision and its
evidence.
