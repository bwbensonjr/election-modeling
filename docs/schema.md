# Training table schema

`data/precinct/ma_precinct_training_set.csv.gz`

One row per legislative race per precinct: State Representative and State
Senate elections from 2010 through 2024, general and special, excluding races
with fewer than two candidates. Built by
[`maprecinct training`](pipeline.md).

The table is **definition-neutral**. It is built at the most permissive
eligibility rule -- any candidate named in the returns counts, write-in or
ballot line -- and carries the flags and vote components by which a stricter
rule excludes a race. Choosing who counts as a candidate and what the margin is
measured against is a downstream selection, not a property baked in here, so
testing an alternative definition is a filter rather than a rebuild. See
[`definitions.md`](definitions.md).

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
| `dem_margin_two_party` | float | Percentage points. The Democratic candidate's share of the precinct's combined Democratic and Republican vote, minus the Republican's share. Measured on the same denominator `PVI_N` is, so response and predictor are definitionally parallel. Missing where either major party is absent, and in the 17 precincts where neither major-party candidate drew a vote |

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
| `num_candidates` | integer | Candidates in the race, as published in `ma-election-db`. Counts ballot lines, so a write-in is not included |

## Eligibility flags

Race-level, repeated across the race's precincts so the table can be filtered
at either grain. These are the columns a definition selects on.

| Column | Type | Description |
|---|---|---|
| `major_party_race` | boolean | Both a Democrat and a Republican stood. True in 523 of the 633 races; 517 of those are races the ballot-line rule also admits |
| `contested_on_ballot_lines` | boolean | The race has two or more ballot lines, which is the pre-change contested test |
| `admitted_by_write_in` | boolean | The race is contested only because a write-in was admitted. True in 10 races |
| `num_candidates_admitted` | integer | Candidates counting admitted write-ins. Ranges from 2 to 5 |
| `write_in_share` | float | Share of the district's named-candidate votes taken by all write-ins combined, 0.0 where none stood |
| `top_write_in_share` | float | The same for the strongest write-in alone. This is the quantity a write-in threshold is compared against |

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
| `dem_votes` | integer | Votes for `dem_candidate` in this precinct. Where a Democrat stood this is that Democrat, so with `gop_votes` it is the two-party pair |
| `opponent_votes` | integer | Votes for `opponent_candidate` in this precinct |
| `gop_votes` | integer | Votes for the strongest Republican in this precinct, 0 where none stood. The other half of the `dem_margin_two_party` denominator |
| `write_in_votes` | integer | Votes for admitted write-in candidates in this precinct |
| `top_write_in_votes` | integer | Votes for the strongest admitted write-in alone. With `write_in_votes` this is what lets a stricter threshold's denominator be recovered from the published table: no race carries more than two write-ins, so the votes to subtract are always one of these two columns or their difference |
| `candidate_votes` | integer | Votes for all admitted candidates in this precinct. The denominator of `dem_margin` |
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
| `data/race/ma_race_training_set.csv.gz` | The district-grain rollup of this table, one row per race. See [`race_schema.md`](race_schema.md) |
| `data/race/ma_race_candidates.csv.gz` | Candidate roster: one row per race candidate with party, write-in flag, district votes and share. The fact a write-in threshold is a query on |
| `data/reports/race_response_shift.csv` | Per-race difference between the two responses, for separating a change in accuracy from a change in the target |
