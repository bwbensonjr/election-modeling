# Election Modeling 

Election modeling based on historical data

## Scope 

Model Democratic/Republican vote margins in Massachusetts State Senate
and State Representative races.

## Resources 

- Data sources
  - [`bwbensonjr/ma-election-db`](https://github.com/bwbensonjr/ma-election-db) - District-level elections and fine-grained census data
  - [MA Commonwealth Election Statistics](https://electionstats.state.ma.us/)
  - [`bwbensonjr/ocpf-cli`](https://github.com/bwbensonjr/ocpf-cli) - OCPF command-line tool 
  - [Massachusetts Office of Campaign and Political Finance](https://www.ocpf.us/)
  - [`bwbensonjr/mapoli`](https://github.com/bwbensonjr/mapoli) - Scripts for gathering precinct-level election results
- Prior art
  - [`bwbensonjr/mapoli/model`](https://github.com/bwbensonjr/mapoli/tree/master/model)
- Model use cases
  - [MA 2022 State Senate General Election Ratings](https://www.massnumbers.us/posts/2022-10-31-state-senate-ratings/)

## Current Model 

The current [mapoli legislative model](https://github.com/bwbensonjr/mapoli/tree/master/model)
uses a Bayesian regression model with this structure:

```
dem_margin ~ PVI_N + incumbent_status + pres_elec
```

- `dem_margin = (dem_percent - gop_percent) * 100`
- `PVI_N` = [Partisan Voter Index (PVI)](https://en.wikipedia.org/wiki/Cook_Partisan_Voting_Index) which is Democratic/Republican point margin averaged over the last two presidential elections and normalized by the US-wide point margin.
- `incumbent_status`
  - `1` if there is a Democratic incumbent in the race
  - `0` if there is no incumbent in the race
  - `-1` if there is a GOP incumbent in the race
- `pres_elec`
  - `1` - The legislative election coincides with a U.S. presidential general election
  - `0` - The legislative election does not coincide with a U.S. presidential general election

## Data Availability and Training Cutoff

Every training row needs two things at the same granularity: the
Democratic/Republican margin for a legislative race, and the `PVI_N`
built from the two presidential elections preceding that race. State
Senate and State Representative districts split municipalities, so PVI
has to be aggregated to the district from **precinct-level**
presidential results. Town-level presidential returns cannot be
allocated to a district that contains only part of a town. Precinct
availability for presidential results is therefore the binding
constraint on how far back the data set can reach.

### Precinct-level availability at electionstats.state.ma.us

The `download/{election_id}/precincts_include:1/` endpoint returns
town-level rows with empty `Ward`/`Pct` columns for elections before
precinct reporting begins. It does not error, so the cutoff has to be
detected by inspecting the returned rows.

| Office | First year with precinct results |
|---|---|
| President, Governor, U.S. Senate, U.S. House, State Senate, Governor's Council | 2002 |
| State Representative | 1980 |

State Representative is the exception because rep districts are built
out of precincts, so results were always broken out that way. Every
other office reports one row per municipality (351 rows) through 2000
and roughly 2,170 precinct rows from the 2002 general onward.

Presidential elections with precinct-level results: **2004, 2008,
2012, 2016, 2020, 2024**.

### Resulting cutoff

The earliest PVI computable from two precinct-level presidential
elections is the 2008 PVI (2004 + 2008). A race in year `Y` uses the
PVI from the two most recent presidential elections completed before
`Y`, which puts the floor at the **2010 legislative elections**.

| Race year | PVI year | Source presidentials | District map |
|---|---|---|---|
| 2010 | 2008 | 2004 + 2008 | 2001 |
| 2012 | 2008 | 2004 + 2008 | 2011 (remap required) |
| 2014, 2016 | 2012 | 2008 + 2012 | 2011 |
| 2018, 2020 | 2016 | 2012 + 2016 | 2011 |
| 2022, 2024 | 2022 | 2016 + 2020 | 2021 (remap required) |
| 2026 | 2024 | 2020 + 2024 | 2021 |

`pvi_year` in `mapoli/pvi/ma_state_leg_pvi_2008_2024.csv` names the
later of the two presidential elections, except for `2022`, which is
the 2020 PVI reallocated to the 2021 district map.

**Usable range: the 2010 through 2024 legislative elections**, eight
cycles, plus 2026 as the forward prediction target. 2008 and earlier
are out of reach at any useful granularity: they would require 2000
precinct-level presidential results, which do not exist.

### Redistricting boundaries

2012 and 2022 are the first elections under new maps, so the prior
presidential votes must be reallocated from old precinct geography to
new districts. This is what mapoli's `ma_precincts_districts_*.csv`
files do via areal interpolation, and it is why post-2021 vote totals
are fractional rather than integers. Rows on either side of a
redistricting boundary are not strictly comparable and the remapped
PVI values carry interpolation error that the natively-mapped years do
not.

### Currently materialized vs. reachable

- **Materialized.** `mapoli/pvi` holds precinct presidential results
  for 2012, 2016, 2020, and 2024, normalized into `ma-election-db`
  as `precinct_presidential_vote`. This covers races from 2018
  onward.
- **Reachable without new sources.** The 2004 and 2008 precinct-level
  presidential results exist at electionstats but have not been
  fetched. Fetching them extends the training set back to 2010. The
  2001-cycle precinct-to-district crosswalk is also absent from the
  repositories, but it is derivable from the precinct-level State Rep
  and State Senate result files for 2002 through 2010, since each
  district's file enumerates its own precincts.
- **Out of reach.** Races in 2008 and earlier.

### The legislative margin is not the constraint

District-level legislative results run back to 1990 in
`ma-election-db`, State Representative precinct results back to 1980,
and State Senate precinct results back to 2002. In every case the
presidential precinct data runs out first.

### Train/test split

Splitting by year rather than randomly matters here because districts repeat
across cycles and a random split would leak the same district's behavior
between train and test.

A single split on the 2021 redistricting -- train on 2010 through 2020, test
on 2022 and 2024 -- was the initial plan. The implemented procedure generalises
it to a rolling-origin schedule over every election year from 2014 onward,
which scores 424 races instead of 128 and, by including the odd years, puts 24
special elections in the holdout instead of none. The redistricting boundary
is still tested: the 2022 fold trains entirely on the old map and predicts on
the new one, and `redistricting_cycle` is a reported segment. See
[`docs/scoring.md`](docs/scoring.md).

### Published training data

The precinct-level data set described by this section is built and committed
by the collection pipeline in [`docs/pipeline.md`](docs/pipeline.md), with the
column-by-column schema in [`docs/schema.md`](docs/schema.md).

- [`data/precinct/ma_precinct_training_set.csv.gz`](data/precinct/ma_precinct_training_set.csv.gz)
  - 14,409 rows, one per legislative race per precinct
  - 633 contested State Representative and State Senate races, general and
    special, spanning 2010 through 2024
  - `dem_margin`, `dem_margin_two_party` and `PVI_N` computed at precinct
    grain, with `incumbent_status`, `pres_elec`, `is_special`,
    `num_candidates` and the eligibility flags carried from the race
  - Against 679 rows in the district-level table the current model uses

  The table is built at the most permissive eligibility rule -- any candidate
  named in the returns counts, write-in or ballot line -- and carries the flags
  by which a stricter rule excludes a race, so who counts as a candidate is a
  downstream selection rather than a property baked in. That is 10 races more
  than the 623 the ballot-line rule admits. See
  [`docs/definitions.md`](docs/definitions.md).

Coverage matches the cutoff derived above. Of the 1,651 legislative elections
in the window, 1,650 have precinct-level returns; the 2011 3rd Berkshire
special reports municipality totals only. 2.4% of rows have no `PVI_N`,
almost all of them precincts created after 2020 that no earlier presidential
election covers, and 1.1% sit in precincts split between two districts. Both
are flagged per row rather than dropped.

## Baseline Model and Scoring

The baseline model is reproduced on the collected data and evaluated by a
fixed scoring procedure, so later variables and algorithms are measured
against an unmoved yardstick.

- **Model.** `dem_margin ~ PVI_N + incumbent_status + pres_elec`, Gaussian
  likelihood, fit at race grain with Bambi/PyMC. Coefficients agree with the
  same fit on the existing district-level table to within 0.07 posterior
  standard deviations once one documented PVI baseline offset is removed.
- **Scoring.** Rolling-origin holdout: each fold trains on every race strictly
  before its year and predicts that year's races, over every election year
  from 2014 through 2024. Pooled holdout of 424 races, 24 of them special.
  RMSE in margin points is the primary score, reported with calibration and
  win-side metrics and broken out per fold and per segment. See
  [`docs/scoring.md`](docs/scoring.md).
- **Race-grain training table.**
  [`data/race/ma_race_training_set.csv.gz`](data/race/ma_race_training_set.csv.gz),
  633 races rolled up from the precinct table, described in
  [`docs/race_schema.md`](docs/race_schema.md), with the candidate roster in
  [`data/race/ma_race_candidates.csv.gz`](data/race/ma_race_candidates.csv.gz).
- **Campaign finance.**
  [`data/race/ma_race_finance.csv.gz`](data/race/ma_race_finance.csv.gz), one
  row per candidate per race, carrying receipts and expenditures accumulated to
  a stated pre-election date. Rolled up into the race table's money columns.
  Collected by `uv run maprecinct finance`; see
  [`docs/money_results.md`](docs/money_results.md).

```bash
uv run legmodel definitions                        # list the data definitions
uv run legmodel score                              # score under the adopted definition
uv run legmodel compare baseline baseline_special  # paired comparison of variants
uv run legmodel compare-definitions current two_party_or_strongest
uv run legmodel importance                         # variable importance and effect sizes
```

### Baseline accuracy

Under the pre-change `current` definition. Superseded by the table in
[Answered Questions](#answered-questions) below, which uses the adopted
definition; both remain reproducible.

| Segment | Races | RMSE | Coverage (90%) | Win accuracy |
|---|---|---|---|---|
| Pooled | 424 | 15.61 | 0.892 | 0.918 |
| General elections | 400 | 14.96 | 0.902 | 0.922 |
| Special elections | 24 | 23.99 | 0.708 | 0.833 |
| No Democratic candidate | 11 | 28.35 | 0.364 | 0.818 |

### First result: does `is_special` help?

**Not overall.** Pooled RMSE moves from 15.608 to 15.641, a difference of
-0.033 with a 90% interval of [-0.143, +0.078], which contains zero: the data
does not separate the two models. The pooled figure hides two real and
opposite effects. The term lowers RMSE on the 24 holdout special elections by
1.13 points, and raises it on the other 400 races by 0.14, and because
specials are 5.7% of the holdout the second outweighs the first.

On specials it does cut the baseline's large pessimism about Democrats, from
-11.56 points of bias to -8.46. The recommendation is to keep `baseline` as
the reference model and use `baseline_special` when the question is about a
special election. Full writeup in
[`docs/is_special_result.md`](docs/is_special_result.md).

The comparison also surfaced larger failures than the one under test: races
with no Democratic candidate (36% interval coverage) and an unabsorbed
presidential-year bias swinging from -6.4 to +2.7 points. Both are settled in
[Answered Questions](#answered-questions) below.

## Model Enhancements

- [x] Incorporate OCPF fundraising data -- [`docs/money_results.md`](docs/money_results.md)
- A finer-grained incumbency variable (take into account number of years)
- Incorporate Census demographic data
- Candidate-committee money is collected; independent expenditures, PAC money
  and party committee spending are not, and are a separate collection problem

## Plan

- [x] Define the data sources, granularity, and variables
  - Data sources - We should look at the data and scripts in these `bwbensonjr` repositories:
    - [`bwbensonjr/ma-election-db`](https://github.com/bwbensonjr/ma-election-db)
      - District-level election results
      - Precinct-level census and demographic data
    - [`bwbensonjr/mapoli/pvi`](https://github.com/bwbensonjr/mapoli/tree/master/pvi) - Scripts for precinct-level election results
  - Granularity - Our preference is to use precinct-level data, but we may use district-level results for years where we do not have precinct-level data.
- [x] Define model accuracy measurement and scoring - [`docs/scoring.md`](docs/scoring.md)
- [x] Gather the data and rebuild the baseline model and evaluate its accuracy - [`docs/is_special_result.md`](docs/is_special_result.md)
- [x] Settle the data definition -- who counts as a candidate and what the margin is measured against - [`docs/definition_result.md`](docs/definition_result.md)
- [x] Test the deferred variables: presidential-year bias and `num_candidates` - [`docs/variant_results.md`](docs/variant_results.md)
- [x] Collect OCPF campaign finance and test it as a predictor - [`docs/money_results.md`](docs/money_results.md)
- Put together expanded variable data set and evaluate the variables via principle component analysis (PCA) or something similar.
- Evaluate different machine learning algorithm alternatives to Bayesian regression and decide on how to matrix testing of algorithms vs. variables.
- Resolve the [open issues](#open-issues) carried forward. The `baseline_year` convergence failure is resolved; special elections and the provisional data definition remain.
- Iteratively test model alternatives
## Answered Questions

The five questions deferred from the baseline work are settled, and campaign
finance -- the enhancement this README has carried as planned work since the
project started -- is answered alongside them. Questions 1 through 3 were
decided together, because each rebuilds the training table and invalidates the
scorecard; 4, 5 and 6 are variant declarations scored by the existing harness,
though 6 also adds a collection stage and new columns.

Full writeups: [`docs/definition_result.md`](docs/definition_result.md) for the
data definitions, [`docs/variant_results.md`](docs/variant_results.md) for the
variants, [`docs/money_results.md`](docs/money_results.md) for campaign
finance, [`docs/variable_importance.md`](docs/variable_importance.md) for which
predictors carry the model and what each is worth, and
[`docs/definitions.md`](docs/definitions.md) for the mechanism.

### The data definition

Who counts as a candidate, and what the margin is measured against, is now a
named **definition** applied over the published tables rather than a property
baked into them. Testing an alternative is a filter and a column choice, not a
rebuild.

```bash
uv run legmodel definitions
uv run legmodel compare-definitions current two_party_or_strongest
```

**Adopted: `two_party_or_strongest`** — the two-party margin where both major
parties stood, the margin against the strongest non-Democrat on that pair's own
two-candidate denominator where no Republican ran, races with no Democrat
excluded, and the write-in threshold left at the ballot-line rule. 610 races,
413 in the pooled holdout, all 24 holdout specials retained.

Four of the five definition comparisons came back undecided, so the choice
rests on a principle fixed before the numbers were seen: **the response and the
predictor should be measured against the same denominator.** `PVI_N` is a
two-party quantity, so the response should be too.

**1. A two-party response — undecided, and the pooled figure is a trap.** On
its own holdout the strict `two_party` definition posts 12.73 RMSE against
`current`'s 15.61, which looks decisive. On the 346 races the two share, the
difference is -0.31 [-0.83, +0.38]. The gap is not accuracy: it is the 78 races
`two_party` drops, which `current` scores at an RMSE of 25.3. Restricting to
Democrat-versus-Republican races removes the hard ones, and comparing pooled
figures would have credited the model for declining to predict them.

The README's own sub-question answers itself. `two_party_or_strongest` recovers
93 of the 106 dropped races, keeps 24 holdout specials instead of 22, and costs
nothing measurable (+0.111, undecided). There is no case for paying 67 holdout
races and two specials for a restriction the data does not reward.

**2. The write-in threshold — undecided, left at the ballot-line rule.**
`write_in_5pct` against `current` is -0.020 [-0.050, +0.007]; because both
share a response, that comparison isolates the eligibility rule cleanly. What
settles it is the other direction: the two races a 5% threshold admits score at
an RMSE of 63.2. Admissions also stop changing between 8% and 10%, so any
threshold in that range is the same rule under a different name.

The asymmetry the question identified is nonetheless fixed. A definition's
threshold now governs both decisions a write-in affects — whether a race is
contested and whether the write-in enters the denominator — so a write-in can
no longer count for one and not the other.

**3. Races with no Democratic candidate — decided: exclude them, from training
as well as scoring.** This is the only definition comparison the data settles:
+0.094 [+0.049, +0.143]. The control makes it informative — keeping them in
training while withholding them from scoring is undecided (+0.006), so the gain
comes specifically from *not training on them*. Those 13 races were distorting
the fit for the other 610, not merely resisting prediction. Most of the
apparent improvement is still removal rather than accuracy, and the writeup
says so.

### The variants

**4. Presidential-year bias — a real fix.** The baseline runs +2.7 points too
Democratic in presidential years and -6.4 too Republican in non-presidential
ones, a gap of 9.1 that one binary term cannot correct.

`baseline_national_env` adds a term signed by the party holding the presidency:
-1 in a non-presidential year under a Democratic president, +1 under a
Republican one, 0 in a presidential year. It lowers RMSE by 0.775
[+0.201, +1.363] and cuts pooled bias from -2.91 to **-0.41**. Unlike a year
effect it is known before the election, so it can shift a holdout year's mean
and carries forward to 2026, where it takes the value +1.

`baseline_year`, a hierarchical year intercept, is the other adopted
variant: RMSE 14.209, a difference of +0.804 [+0.410, +1.179], coverage 0.927,
and a presidential-year bias gap of -0.34. Its fits originally diverged on
every fold; that was a specification defect and is
[fixed](#baseline_year-fits-do-not-converge----resolved). It cannot shift a
forward year's mean, so it complements `baseline_national_env` rather than
replacing it. `baseline_pres_incumbent` is undecided.

**5. `num_candidates` — undecided; it does not belong in the baseline.** A wash
under `current` (+0.026) and under the adopted definition (-0.033), and
decidedly *worse* under the strict two-party definition (-0.064
[-0.107, -0.023]). Once the response is measured on a two-party denominator the
term adds variance without adding signal, exactly as anticipated.

**6. Campaign finance — the largest gain measured so far.**
`baseline_money_logratio` adds the log ratio of Democratic to opponent
receipts, measured 14 days before each race's own election, and lowers pooled
RMSE by **+1.700 [+1.128, +2.255]** — roughly twice what the year intercept
was worth. The effect is concentrated in open seats (+3.686
[+2.481, +4.872]) and undecided against a Democratic incumbent.

Money is never read from OCPF's published cumulative figure, which is a full
calendar-year total fetched after the fact and therefore includes money raised
after the polls closed — 28% and 70% of two cycles' totals for one Boston
filer. Every figure is reconstructed from report line items over a window
ending at a stated pre-election date. **The result is not evidence that
spending changes outcomes**; see
[`docs/money_results.md`](docs/money_results.md#endogeneity).

### Accuracy under the adopted definition

| Variant | Segment | Races | RMSE | Coverage (90%) | Win accuracy |
|---|---|---|---|---|---|
| `baseline` | Pooled | 413 | 15.01 | 0.898 | 0.910 |
| `baseline` | General elections | 389 | 14.19 | 0.910 | 0.915 |
| `baseline` | Special elections | 24 | 24.76 | 0.708 | 0.833 |
| `baseline_national_env` | Pooled | 413 | 14.24 | 0.923 | 0.915 |
| `baseline_national_env` | General elections | 389 | 13.55 | 0.931 | 0.915 |
| `baseline_national_env` | Special elections | 24 | 22.68 | 0.792 | **0.917** |
| `baseline_year` | Pooled | 413 | 14.21 | **0.927** | **0.927** |
| `baseline_year` | General elections | 389 | 13.45 | **0.938** | **0.933** |
| `baseline_year` | Special elections | 24 | 23.25 | 0.750 | 0.833 |
| `baseline_money_logratio` | Pooled | 398 | 13.37 | 0.895 | 0.920 |
| `baseline_money_logratio` | General elections | 376 | 12.81 | 0.904 | 0.928 |
| `baseline_money_logratio` | Special elections | 22 | 20.73 | 0.727 | 0.773 |
| `baseline_spend_logratio` | Pooled | 398 | **13.05** | 0.895 | 0.920 |
| `baseline_spend_logratio` | General elections | 376 | **12.61** | 0.904 | 0.931 |
| `baseline_spend_logratio` | Special elections | 22 | **19.06** | 0.727 | 0.773 |

These supersede the baseline table above but are not the same measurement:
different races and a different response. `current` stays registered and
scorable, so the earlier figures remain reproducible.

**The money row is scored on 398 races, not 413.** It excludes the 15 holdout
races where a candidate could not be resolved to an OCPF filer, because a
missing filer and a candidate who raised nothing are different facts and the
variant may not impute one into the other. The paired comparison above scores
both models on those same 398 races, so it is a like-for-like difference.

The same four contrasts over **expenditures** rather than receipts are
registered and scored too. `baseline_spend_logratio` is the most accurate
variant on this holdout, but it beats the receipts term by only +0.322
[+0.056, +0.599] and that margin is undecided under two of the four
definitions, so **`baseline_money_logratio` stays the adopted money variant** —
spending is also the more endogenous measure, being the quantity a campaign
adjusts in response to how close the race looks. See
[`docs/money_results.md`](docs/money_results.md#the-other-side-of-the-ledger).

Of the money and pre-money variants, `baseline_money_logratio` is much the most accurate, including
on special elections, which are the model's worst segment. It loses a little
interval calibration relative to `baseline_year` and gives up the ability to
score the 15 unmatched races at all. `baseline_year` is best calibrated;
`baseline_national_env` is the only one of the older pair usable for a forward
prediction, and the money term is too — a figure measured 14 days out is
knowable before the election it predicts.

## Open Issues

Known defects and limitations carried forward, as distinct from the planned
work in [Model Enhancements](#model-enhancements) and [Plan](#plan).

### `pres_elec` costs accuracy in the money model

Dropping `pres_elec` from `baseline_money_logratio` **improves** pooled holdout
RMSE by 0.722 [−1.116, −0.320] — decided — even though its coefficient is
+7.09 [+5.19, +8.94] and nowhere near zero. `pres_elec` is a property of the
calendar year and folds are years, so a wrong year-level shift lands on every
race in a holdout at once; across the nine folds the coefficient ranges from
7.09 to 13.50, and the presidential years themselves disagree (2012 +27.5 mean
margin, 2020 +13.9).

This extends the presidential-year bias already recorded under question 4
rather than contradicting it. Not yet acted on: a variant dropping the term is
a registry entry and a rescore, and no alternative is adopted until that is
compared under every scored definition. See
[`docs/variable_importance.md`](docs/variable_importance.md).

### ~~`baseline_year` fits do not converge~~ --- resolved

**Resolved.** Every fold under every definition now samples cleanly: zero
divergent transitions across all 40 fits, worst R-hat 1.0027, lowest bulk ESS
2436. The variant is adopted alongside `baseline_national_env`.

The fix is not the one this section originally proposed, and the way it was
wrong is worth keeping. It suggested a non-centred parameterisation first ---
but bambi builds group effects non-centred by default and the project never
overrode it, so the sampler had always been running the recommended fix. There
was no funnel to straighten.

The two real causes were:

- **An auto-scaled group-SD prior.** Bambi derived
  `1|election_year ~ Normal(0, HalfNormal(135))` from the intercept's scale,
  against a response whose own standard deviation is 25.2 points, and asked it
  to inform a between-year SD estimated from as few as four year groups. The
  variant now declares `HalfNormal(5)`.
- **`pres_elec` collinear with the year grouping.** A per-year intercept spans
  a term that is a property of the calendar year. Across 610 races `pres_elec`
  varies within a year only in 2016 and 2020, on 8 races; in the 2010-2013
  training window, not at all. The variant now drops it.

The improvement grew rather than shrank once the fits were clean: RMSE 14.209
against the superseded 14.503, a paired difference of +0.804 [+0.410, +1.179]
against the superseded +0.510, and coverage holding at 0.927. The
presidential-year bias gap closes from 9.46 to **-0.34**, further than
`baseline_national_env` manages --- driven by the term removed rather than the
one added, since the baseline's fitted `pres_elec` coefficient was applying a
four-point shift that miscalibrated out of sample.

`baseline_national_env` is still the variant to use for a **forward**
prediction. A year intercept cannot move a future year's mean, because that
year's effect is unobserved and is drawn from the hyperprior; the national
environment is known before the votes are cast. The two answer different
questions and are reported together rather than ranked.

Three things carried forward from the fix:

- A variant now declares its own priors and sampler settings, and
  `fit_diagnostics.csv` records what each fit actually ran under, so a result
  obtained at a raised `target_accept` is distinguishable from one obtained at
  the default.
- A predictor constant within every level of a variant's own grouping factor
  is refused per fold, with the refusal published. `national_env` has the same
  defect as `pres_elec` if combined with a year effect, and would be caught.
- `baseline_year` is no longer nested in `baseline`, and its comparison is
  labelled non-nested, naming the term added and the term removed.

Full writeup: [`docs/variant_results.md`](docs/variant_results.md).

### Special elections remain the worst segment

24 holdout races at 24.76 RMSE against a pooled 15.01, with 0.708 interval
coverage against a nominal 0.90. The model is overconfident about them, and
`is_special` does not fix it -- that term is undecided under every definition
tested.

`baseline_national_env` improves the segment more than `is_special` does
(22.68 RMSE, 0.792 coverage), which suggests part of what `is_special` was
reaching for is national environment rather than anything intrinsic to special
elections. Whatever is left is a thin-data problem: 24 holdout races is not
much to diagnose from.

### The adopted definition rests on a principle, not on a measurement

Four of the five definition comparisons came back undecided, so
`two_party_or_strongest` was adopted on the pre-registered tie-break rather
than because the data preferred it. That is the honest outcome at this holdout
size, but it means the decision is provisional: more cycles, or a variable that
interacts with the response definition, could settle it empirically. Every
superseded definition stays registered and scorable so the question can be
reopened without re-running collection.

The write-in threshold is provisional for the same reason. It sits at the
ballot-line rule because the two races a 5% threshold admits score at 63.18
RMSE, not because a threshold is wrong in principle. If genuine write-in
campaigns become more common, this is worth revisiting.
