# Election Modeling 

Election modeling based on historical data

## Scope 

Model Democratic/Republican vote margins in Massachusetts State Senate
and State Representative races.

## Resources 

- Data sources
  - [`bwbensonjr/ma-election-db`](https://github.com/bwbensonjr/ma-election-db)
  - [MA Commonwealth Election Statistics](https://electionstats.state.ma.us/)
  - [`bwbensonjr/ocpf-cli`](https://github.com/bwbensonjr/ocpf-cli) - OCPF command-line tool 
  - [Massachusetts Office of Campaign and Political Finance](https://www.ocpf.us/)
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

## Model Enhancements

- Incorporate OCPF fundraising data
- A finer-grained incumbency variable (take into account number of years)
- Incorporate Census demographic data

## Plan

- Define the granularity, variables, and data sources
- Define model accuracy measurement and scoring
- Gather the data and rebuild the baseline model and evaluate its accuracy
- Put together expanded variable data set and evaluate the variables via principle component analysis (PCA) or something similar.
- Evaluate different machine learning algorithm alternatives to Bayesian regression and decide on how to matrix testing of algorithms vs. variables.
- Iteratively test model alternatives
