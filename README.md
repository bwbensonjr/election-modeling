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
  - 14,188 rows, one per legislative race per precinct
  - 623 contested State Representative and State Senate races, general and
    special, spanning 2010 through 2024
  - `dem_margin` and `PVI_N` computed at precinct grain, with
    `incumbent_status`, `pres_elec`, `is_special` and `num_candidates` carried
    from the race
  - Against 679 rows in the district-level table the current model uses

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
  623 races rolled up from the precinct table, described in
  [`docs/race_schema.md`](docs/race_schema.md).

```bash
uv run legmodel score                              # score every variant
uv run legmodel compare baseline baseline_special  # paired comparison
```

### Baseline accuracy

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
presidential-year bias swinging from -6.4 to +2.7 points.

## Model Enhancements

- Incorporate OCPF fundraising data
- A finer-grained incumbency variable (take into account number of years)
- Incorporate Census demographic data

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
- Put together expanded variable data set and evaluate the variables via principle component analysis (PCA) or something similar.
- Evaluate different machine learning algorithm alternatives to Bayesian regression and decide on how to matrix testing of algorithms vs. variables.
- Iteratively test model alternatives
