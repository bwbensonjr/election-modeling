# Training table schema

`data/precinct/ma_precinct_training_set.csv.gz`

One row per legislative race per precinct: State Representative and State
Senate elections from 2010 through 2024, general and special, excluding races
with fewer than two candidates. Built by
[`maprecinct training`](pipeline.md).

## Identity

| Column | Type | Description |
|---|---|---|
| `election_id` | integer | electionstats identifier for the race. Unique per race; with the precinct key it forms the row key |
| `election_date` | date | Date the election was held |
| `election_year` | integer | Year of `election_date` |
| `redistricting_cycle` | integer | Which map the race was run under: `2001`, `2011`, or `2021`. A cycle covers its off-year specials, so 2011 specials are 2001-cycle and 2021 specials are 2011-cycle |
| `office` | string | `State Representative` or `State Senate` |
| `district` | string | District name in word-ordinal form, e.g. `Third Suffolk` |
| `district_display` | string | District name in numeric-ordinal form, e.g. `3rd Suffolk` |
| `city_town` | string | Municipality, unabbreviated (`North Brookfield`, not `N. Brookfield`) |
| `ward` | string | Ward, or `-` for municipalities without wards |
| `precinct` | string | Precinct within the ward. Not always numeric: `A`, `5B`, `3N` all occur |

## Response variable

| Column | Type | Description |
|---|---|---|
| `dem_margin` | float | Percentage points. The Democratic candidate's share of the precinct's votes for named candidates, minus the strongest non-Democratic candidate's share. Blanks and the all-others bucket are excluded from the denominator, matching how `ma-election-db` computes its published percentages |

The comparison candidate is chosen once per race from district totals, not
per precinct, so the column means the same thing in every precinct of a race.

Where no Democrat stood, `dem_margin` negates the leader's margin over the
strongest remaining candidate and `no_dem_candidate` is true. The existing
district-level table computes this case incorrectly, through an operator
precedence error in `mapoli/model/ma_leg_model.R`'s `democratic_margin()`,
which multiplies the comparison share by 100 before subtracting instead of
after. It reports, for instance, +38.6 for a 2012 race the Republican won
61-39. This table reports the intended value.

## Predictors

| Column | Type | Description |
|---|---|---|
| `PVI_N` | float | Partisan Voter Index for this precinct, in percentage points. The precinct's Democratic share of the combined two-party presidential vote across the two presidential elections preceding the race, minus the national share computed the same way |
| `incumbent_status` | string | `No_Incumbent`, `Dem_Incumbent`, or `GOP_Incumbent`. An unenrolled incumbent is classified as `GOP_Incumbent`, following the established model |
| `pres_elec` | boolean | Whether the race shared a ballot with a presidential general election |
| `is_special` | boolean | Whether the race was a special election |
| `num_candidates` | integer | Candidates in the race, as published in `ma-election-db` |

## Provenance and diagnostics

| Column | Type | Description |
|---|---|---|
| `pvi_year` | integer | The later presidential election of the pair `PVI_N` was built from |
| `pvi_provenance` | string | How the presidential votes behind `PVI_N` reached this precinct's geography. See below |
| `no_dem_candidate` | boolean | True when no Democrat stood; changes how `dem_margin` is defined |
| `precinct_split_across_districts` | boolean | True when this precinct is divided between two districts, so each district's returns report only its own portion under the same precinct label. `dem_margin` then covers part of the precinct while `PVI_N` covers all of it. 1.1% of rows |
| `candidate_count` | integer | Candidates counted from the precinct returns. Can exceed what the published summary represents, which carries only four candidate slots |
| `dem_candidate_count` | integer | Democrats on the ballot. Greater than one in a handful of races |
| `dem_candidate` | string | Candidate on the Democratic side of the margin |
| `opponent_candidate` | string | Candidate on the other side |
| `opponent_party` | string | That candidate's party |
| `dem_votes` | integer | Votes for `dem_candidate` in this precinct |
| `opponent_votes` | integer | Votes for `opponent_candidate` in this precinct |
| `candidate_votes` | integer | Votes for all named candidates in this precinct. The denominator of `dem_margin` |
| `total_votes` | integer | All votes cast in this precinct, including blanks and all-others |

### `pvi_provenance` values

| Value | Meaning |
|---|---|
| `native` | The presidential votes were cast on this precinct's own geography; no remapping |
| `exact_identifier` | The precinct kept its identifier across a redistricting boundary, so its votes carried over unchanged |
| `combined_children` | Subdivided precincts were summed into the parent the later cycle uses. Exact, not estimated |
| `areal_interpolation` | Votes were reallocated by area weighting because the precinct's boundaries changed. These values are estimates and carry error |

Roughly 93% of remapped precincts match exactly by identifier. Rows marked
`areal_interpolation` can be excluded or modelled separately.

## Joining and modelling notes

- Precinct rows within a race are strongly correlated. `election_id` groups a
  race; cluster or group by it rather than treating rows as independent.
- Splitting by year rather than randomly avoids leaking a district's
  behaviour between train and test, since districts recur across cycles.
- `redistricting_cycle` changes which precincts exist. Rows on either side of
  a cycle boundary are not the same units.

## Other published files

| File | Contents |
|---|---|
| `data/precinct/ma_precinct_presidential_results.csv.gz` | Normalized presidential returns, one row per election, precinct and candidate |
| `data/precinct/ma_precinct_legislative_results.csv.gz` | The same for legislative races |
| `data/precinct/ma_precinct_presidential_vote.csv.gz` | Two-party presidential totals per precinct per year |
| `data/precinct/ma_precinct_district.csv.gz` | Precinct to district mapping per redistricting cycle |
| `data/pvi/ma_precinct_pvi.csv.gz` | Precinct PVI, keyed by `pvi_year` and `redistricting_cycle` |
| `data/reference/*.csv` | National presidential baselines, the race-year to PVI mapping, and the redistricting cycle spans |
