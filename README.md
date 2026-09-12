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

The 2021 redistricting gives a natural temporal holdout: train on 2010
through 2020 and test on 2022 and 2024, which also tests whether the
model survives a map change. Splitting by year rather than randomly
matters here because districts repeat across cycles and a random split
would leak the same district's behavior between train and test.

## Model Enhancements

- Incorporate OCPF fundraising data
- A finer-grained incumbency variable (take into account number of years)
- Incorporate Census demographic data

## Plan

- Define the data sources, granularity, and variables
  - Data sources - We should look at the data and scripts in these `bwbensonjr` repositories:
    - [`bwbensonjr/ma-election-db`](https://github.com/bwbensonjr/ma-election-db)
      - District-level election results
      - Precinct-level census and demographic data
    - [`bwbensonjr/mapoli/pvi`](https://github.com/bwbensonjr/mapoli/tree/master/pvi) - Scripts for precinct-level election results
  - Granularity - Our preference is to use precinct-level data, but we may use district-level results for years where we do not have precinct-level data.
- Define model accuracy measurement and scoring
- Gather the data and rebuild the baseline model and evaluate its accuracy
- Put together expanded variable data set and evaluate the variables via principle component analysis (PCA) or something similar.
- Evaluate different machine learning algorithm alternatives to Bayesian regression and decide on how to matrix testing of algorithms vs. variables.
- Iteratively test model alternatives
