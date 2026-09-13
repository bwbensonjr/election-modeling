# Campaign finance: does money help the model?

**Yes, and by more than any variable tested so far.** Under the adopted
definition the log ratio of Democratic to opponent receipts, measured 14 days
before each race's own election, lowers pooled RMSE from 15.070 to 13.370 --- a
difference of **+1.700 points [+1.128, +2.255]**, decided. For comparison, the
best previous variant, a hierarchical year intercept, was worth +0.804.

The effect is concentrated exactly where the prior said it would be: **+3.686
[+2.481, +4.872] in open seats**, +1.501 [+0.872, +2.110] against a Republican
incumbent, and **undecided against a Democratic incumbent** (+0.561
[-0.186, +1.277]).

**This is not evidence that spending changes outcomes.** See
[Endogeneity](#endogeneity) below, which is the reason this page reports a
predictor and not a lever.

Reproduce with:

```bash
uv run maprecinct finance
uv run legmodel score --variants baseline_money_logratio --append
uv run legmodel compare baseline baseline_money_logratio
```

## What had to be solved first

Three obstacles were measured before any of this was designed, and each shaped
the collection. They are stated here because the result is only as good as the
measurement behind it.

### The published feeds cover disjoint eras

`reports/legislative/depository/ytd/{year}` returns 428 rows for 2020 and 477
for 2024, and between 0 and 13 rows for every year from 2010 through 2019. The
historical endpoint `onballot/finsummaries/{year}/{code}` is the mirror image:
populated 2010 through 2018, empty from 2020. The seam falls at 2020, in the
middle of a 2010-2024 modelling range.

Worse, the two do not report the same quantity. `finsummaries` gives final
full-cycle totals; the depository feed gives a year-to-date snapshot. Joining
them would put a discontinuity in the middle of the training range that the
model would read as a change in the world.

### The published figures leak the outcome

Fetched after a cycle, OCPF's "year to date" figure is a full calendar-year
total: **411 of 428 rows in 2020, and 436 of 477 in 2024, carry a
`bankReportEndDate` of 12/31.** Money raised after the polls closed is in
there. Measured on one Boston representative:

| Year | Receipts through Oct 31 | Full calendar year | Raised after Oct 31 |
|---|---|---|---|
| 2024 | $401,190 | $560,090 | 28% |
| 2020 | $32,935 | $111,126 | 70% |

A model fit on the published figure would be reading the result, and it would
be flattered in exactly the direction that makes money look powerful: money
arrives after a win.

### There is no shared identifier with the race table

OCPF names filers `"Turner, Cleon H."`; the race roster names them
`"Richard J. Ross"`. The join has to be built from name, district and year,
across two redistricting cycles.

## How money is measured instead

Every figure is reconstructed from report line items via `search/items` with
`CpfId`, `StartDate`/`EndDate` and `withSummary=true`, which returns a
date-bounded count and total in one call and works uniformly back to 2010. It
solves both of the first two problems at once: the same measurement in 2010 and
2024, and one that ends strictly before the polls open.

**The window is trailing and relative to each race's own election** --- 365 days
ending 14 days before election day for the `primary` window, 60 days before for
the `wide` one. Not calendar year-to-date, because a special election held in
January is funded in the previous calendar year and there are 38 specials,
already the model's worst segment. Not a fixed October date, because a race held
in March has no October.

The published cumulative totals are collected too, but only as a reconciliation
check. **They feed no predictor.**

### What the reconciliation actually showed

The check as originally designed does not hold, for two reasons, both of which
are properties of the data rather than defects in the collection.

First, the trailing window crosses a calendar year, so it legitimately exceeds
a calendar-year figure --- 174 of 370 candidates do.

Second, on a like-for-like calendar-year comparison the line-item total still
runs a **median 13% above** the published `receiptsYtd`, with only 14 of 40
within 2%. The two measure different things: the depository figure is
bank-reported deposits, and the line items are reported receipts including
in-kind and non-depository records.

What was verified instead is what the model actually depends on: the two
correlate closely per candidate, the published figure feeds no predictor, and
the measure used is computed identically for every candidate in every year.

## The join, and its residual

Resolution runs district-first, as the tool's own guidance requires: ask `ocpf`
for the race's roster, then match within that small set --- typically one to
eight filers, which is what makes surname-first matching viable at all. The
rules, each recorded on the row that used it: normalise accents, punctuation
and generational suffixes; match on full surname, trying successively longer
trailing word groups so a multi-word surname resolves; where more than one
filer shares a surname, require the given name to agree as a prefix, which
separates `Robert`/`Bob` and `Giuseppina`/`Pina` without a nickname table.
Anything still ambiguous is recorded as ambiguous and matched to neither.

**1,244 of 1,266 candidates match, 98.3%**, against a 76-84% baseline measured
for a naive surname match on a 75-race sample. Per year:

| Year | Matched | Candidates | Rate |
|---|---|---|---|
| 2010 | 225 | 228 | 98.7% |
| 2011 | 6 | 6 | 100% |
| 2012 | 150 | 150 | 100% |
| 2013 | 14 | 14 | 100% |
| 2014 | 186 | 194 | 95.9% |
| 2015 | 6 | 6 | 100% |
| 2016 | 124 | 124 | 100% |
| 2017 | 10 | 10 | 100% |
| 2018 | 144 | 146 | 98.6% |
| 2020 | 115 | 116 | 99.1% |
| 2021 | 4 | 4 | 100% |
| 2022 | 148 | 152 | 97.4% |
| 2023 | 2 | 4 | 50% |
| 2024 | 110 | 112 | 98.2% |

Every year is at or above 95.9% except 2023, which holds two candidates across
one race.

**The residual is a deliverable, not a rounding error.** All 633 races resolve
to a district; the 22 unmatched candidates were absent from a roster that was
found, and 10 of them sat in a district-year whose roster held a single filer
--- their opponent never registered a committee at all. Every one is published
with the filers that were considered in
`data/reports/ocpf_unmatched_candidates.csv`.

A statewide cross-year filer index was tried and rejected: it matched
`Leah Cole` to `Cole, Stephen R.` A wrong match is worse than no match, because
it attributes one campaign's money to another candidate.

### Unknown money and zero money are different columns

A candidate with no committee raised zero. A candidate whose filer could not be
found has unknown money. Collapsing them would put a large fake zero exactly
where the match is hardest, biasing any coefficient toward zero and producing a
null result that looks like evidence.

So 611 of 633 races carry `money_complete`; 9 races carry a genuine zero on one
side with both candidates matched; 22 carry a null for want of a filer. A money
variant either excludes the incomplete races or carries an explicit unknown
indicator. **None of them imputes**, and the harness refuses a variant whose
predictor is missing on a race it would be fit on.

The cost of that exclusion is published rather than absorbed: the money
variants score **398 pooled holdout races against the baseline's 413**, and
the 2023 fold --- one race, whose opponent has no filer --- disappears entirely
and is recorded in the scorecard's `folds_absent` column rather than merely
going missing.

## The four measures

Registered as a sweep rather than reasoned down to one, because which contrast
carries signal is the question the harness exists to answer. All four are
oriented so a larger value is a Democratic advantage, since the response is a
margin and a predictor tracking one candidate's fundraising alone measures race
salience rather than advantage.

Under the adopted `two_party_or_strongest` definition, all on the same 398
races, compared against `baseline` scored on those same races:

| Variant | Predictor | RMSE | vs baseline | 90% interval | Verdict |
|---|---|---|---|---|---|
| `baseline_money_logratio` | `log((dem+1)/(opp+1))` | **13.370** | **+1.700** | [+1.128, +2.255] | decided |
| `baseline_money_both` | `log1p(dem)`, `log1p(opp)` separately | 13.380 | +1.690 | [+1.123, +2.244] | decided |
| `baseline_money_share` | dem / (dem + opp) | 13.524 | +1.546 | [+0.866, +2.191] | decided |
| `baseline_money_diff` | (dem - opp) / 1000 | 14.744 | +0.327 | [+0.047, +0.596] | decided |
| `baseline` | --- | 15.070 | --- | --- | --- |

The ordering is stable across all four registered definitions. RMSE difference
against `baseline` on each definition's own shared races:

| Variant | `current` | `two_party` | `two_party_or_strongest` | `write_in_5pct` |
|---|---|---|---|---|
| `baseline_money_logratio` | +2.041 | +1.026 | +1.700 | +1.876 |
| `baseline_money_both` | +2.000 | +0.990 | +1.690 | +1.863 |
| `baseline_money_share` | +2.001 | +0.976 | +1.546 | +1.812 |
| `baseline_money_diff` | +0.378 | +0.348 | +0.327 | +0.383 |

Every one of these is decided; none of the intervals spans zero. Log ratio and
the two-term form are indistinguishable from each other and best, the share is
close behind, and the untransformed difference is far weaker everywhere.

The effect is smallest under `two_party`, which is expected: that definition
already drops the 93 hardest races, so there is less error left for any
predictor to remove.

**Why the difference in dollars is the weak one.** Receipts span three orders
of magnitude across the record. On a linear scale the fit is dominated by the
handful of races where one side raised half a million dollars, and a $20,000
advantage in a race where nobody raised much --- which is most races --- is
numerically indistinguishable from no advantage at all. The log forms say that
what matters is the *ratio* of resources, which is what a relative measure like
a margin should be paired with.

**Why `logratio` rather than `both`.** They cannot be separated: +1.700 against
+1.690 on identical races. `logratio` is adopted because it is one term rather
than two and is already a contrast, so it cannot accidentally fit race salience
the way two free coefficients on the two sides could. Nothing in the data
decides between them, and this page says so rather than implying the numbers
chose.

### Where the effect lives

`baseline_money_logratio` against `baseline`, by segment:

| Segment | Races | baseline | money | Difference | 90% interval | Verdict |
|---|---|---|---|---|---|---|
| Pooled | 398 | 15.070 | 13.370 | +1.700 | [+1.128, +2.255] | decided |
| **No incumbent** | 109 | 17.983 | 14.297 | **+3.686** | [+2.481, +4.872] | decided |
| Republican incumbent | 87 | 12.609 | 11.108 | +1.501 | [+0.872, +2.110] | decided |
| **Democratic incumbent** | 202 | 14.300 | 13.739 | +0.561 | [-0.186, +1.277] | **undecided** |
| Special elections | 22 | 24.429 | 20.731 | +3.698 | [+1.080, +5.877] | decided |
| General elections | 376 | 14.335 | 12.809 | +1.526 | [+0.950, +2.102] | decided |
| State Representative | 302 | 15.435 | 13.505 | +1.929 | [+1.344, +2.530] | decided |
| State Senate | 96 | 13.861 | 12.934 | +0.927 | [-0.728, +2.417] | undecided |

This is the shape the design predicted before the numbers were seen: money
matters most in an open seat, where there is no incumbency term already
carrying the signal, and least against an entrenched Democratic incumbent,
where the outcome is close to foregone whatever the challenger raises. It also
helps substantially on special elections, which are the model's worst segment.

No segment in the comparison falls below the 10-race marking threshold, so
nothing here rests on a handful of races.

### Cutoff sensitivity

The same contrast at the second window, 60 days out instead of 14:

| Window | As-of | RMSE | vs baseline | 90% interval |
|---|---|---|---|---|
| `primary` | 14 days before the election | 13.370 | +1.700 | [+1.128, +2.255] |
| `wide` | 60 days before the election | 13.536 | +1.534 | [+0.982, +2.094] |

**The result is not an artifact of the cutoff.** Moving the measurement six
weeks earlier costs 0.166 RMSE under the adopted definition --- the two
intervals overlap almost entirely --- and the open-seat effect survives at
+3.195 [+1.982, +4.443].

Nor is the direction of that small difference stable, which is itself the
point. Against `baseline` on each definition's shared races:

| Definition | 14 days | 60 days |
|---|---|---|
| `current` | +2.041 | +1.832 |
| `two_party` | +1.026 | **+1.126** |
| `two_party_or_strongest` | +1.700 | +1.534 |
| `write_in_5pct` | +1.876 | +1.820 |

The earlier window wins under `two_party` and loses under the other three, by
margins far smaller than either variant's interval. The data does not separate
the two cutoffs, and the 14-day window is adopted on the prior stated before
the numbers were seen: it is the latest measurement that is still genuinely
pre-election, sitting just before the pre-election reporting deadline rather
than after it.

The fitted coefficient does move, from about 3.9 at 14 days to about 2.7 at 60,
which is what should happen: the earlier window has seen less of the campaign,
so the same log-ratio unit carries less information and is weighted down
accordingly.

Both dates are published with every fit and every score, in
`fit_diagnostics.csv` and in the scorecard's `as_of` column. A money figure
without the date it was measured on is not interpretable, and the difference
between two dates is the difference between a forecast and a postdiction.

### The fits themselves

All 180 money fits sampled cleanly: zero divergent transitions, worst R-hat
1.0024, lowest bulk ESS 6,560. The money coefficient is stable across folds,
running 3.28 to 4.13 at the 14-day window with a posterior standard deviation
near 0.35 --- it is not a term that appears in one window of the record and
vanishes in another.

## Endogeneity

**Money flows toward candidates already expected to win.** A strong coefficient
may be measuring the same expectations `PVI_N` and incumbency already encode,
arriving by a different route: donors read the same public signals a forecaster
does, and a candidate who looks likely to win raises more *because* of it.

The sweep cannot settle this and does not try. But the fitted coefficients show
the mechanism plainly. Adding the money term does not leave the rest of the
model alone --- it takes work away from incumbency:

| Parameter | `baseline` | `baseline_money_logratio` |
|---|---|---|
| Democratic incumbent | +11.37 | +9.06 |
| Republican incumbent | -21.49 | -17.57 |
| `PVI_N` | +1.76 | +1.51 |

(Mean of the per-fold posterior means under the adopted definition.)

Roughly a fifth of what incumbency was carrying is now carried by money. That
is consistent with money being a partial *proxy* for incumbency's advantages
rather than an independent cause of them.

The closest thing to evidence available here is the incumbency breakdown, and
it cuts slightly the other way: the effect is largest in **open seats**, where
there is no incumbent for expectations to attach to and where two candidates
start from a more even footing. A money effect that survives there is harder to
explain away as pure expectation than a pooled one would be. It is still not
causal identification, and nothing in this design could provide one.

**What this result licenses.** Money raised as of a stated date is a strong
*predictor* of a legislative margin, particularly in open seats, and including
it makes the model more accurate on races it will actually be asked about. It
does not license the claim that a candidate who raises more money thereby wins
more votes, and no figure on this page should be quoted to that effect.

## What is not here

- **No independent expenditures, PAC money, or party committee spending.** The
  candidate committee is what OCPF's legislative feeds cover; outside money is
  a separate collection problem.
- **No expenditure categorisation.** Who a committee paid, and for what, is
  available but is a different question.
- **Expenditures are collected but not scored.** The same four contrasts are
  available over spending rather than receipts. Spending is closer to the
  outcome in time and more likely to respond to a race already tightening, so
  receipts were scored first; the columns are in the table for whoever asks the
  question next.
- **No separate primary window.** A September primary is a real contest that
  consumes real money, and a general-election window that includes it mixes two
  campaigns. The 14-day and 60-day pair shows the cutoff sensitivity is small,
  which is the evidence that was deferred on.
- **No 2026 forward prediction**, though the as-of-date mechanism is what would
  make one possible: unlike a year effect, a money figure measured 14 days out
  is knowable before the election it predicts.

## Related

- [`pipeline.md`](pipeline.md#campaign-finance) --- how the collection runs and
  what it caches.
- [`race_schema.md`](race_schema.md#campaign-finance) --- the money columns and
  what missing means.
- [`scoring.md`](scoring.md#dated-predictors-and-the-as-of-date) --- the as-of
  date in the published record, and how a variant excludes races.
- [`variant_results.md`](variant_results.md) --- the variants tested before
  this one.
