# Race table schema

`data/race/ma_race_training_set.csv.gz`

One row per legislative race: 633 contested State Representative and State
Senate elections from 2010 through 2024, general and special. Built by
[`maprecinct races`](pipeline.md) by rolling the precinct table in
[`schema.md`](schema.md) up to the district, and it is the table the margin
model is fit on and scored against.

Every race in the precinct table appears here. A race would be dropped only if
no precinct in it had two-party presidential votes for its PVI year, leaving
`PVI_N` undefined; no race in the current window meets that condition.

Like the precinct table, this table is **definition-neutral**: it carries every
race any declared definition admits, both responses, and the flags by which a
definition excludes a race. The race table alone is sufficient to apply a
definition -- neither the precinct table nor a candidate-level source is read.
See [`definitions.md`](definitions.md).

## How the rollup works

Two columns are recomputed from vote counts rather than carried or averaged.

**`dem_margin`** sums `dem_votes`, `opponent_votes` and `candidate_votes`
across the race's precincts and takes the Democratic share minus the
comparison candidate's share. It is not the mean of the precinct margins,
which would weight a 300-vote precinct the same as a 3,000-vote one: across
the 623 races the two differ by a median of 1.0 point and by as much as 22.9.

**`PVI_N`** sums the two-party presidential vote counts behind each precinct's
PVI and applies the PVI formula to those district totals against the same
national baseline. A precinct with no two-party presidential votes contributes
zero to both sums, which is what a precinct that cast no presidential votes
should contribute, so the precinct table's missing `PVI_N` values need no
special handling here.

Everything else is carried through from the race's precinct rows unchanged.
The build fails rather than publishing if a race's precinct rows disagree on
any carried attribute.

## Identity

| Column | Type | Description |
|---|---|---|
| `election_id` | integer | electionstats identifier for the race. The row key |
| `election_date` | date | Date the election was held |
| `election_year` | integer | Year of `election_date` |
| `redistricting_cycle` | integer | Which map the race was run under: `2001`, `2011`, or `2021` |
| `office` | string | `State Representative` or `State Senate` |
| `district` | string | District name in word-ordinal form, e.g. `Third Suffolk` |
| `district_display` | string | District name in numeric-ordinal form, e.g. `3rd Suffolk` |

## Response variable

| Column | Type | Description |
|---|---|---|
| `dem_margin` | float | Percentage points. The Democratic candidate's share of the district's votes for named candidates, minus the comparison candidate's share. Blanks and the all-others bucket are excluded from the denominator |
| `dem_margin_two_party` | float | Percentage points. The district's Democratic share of its combined Democratic and Republican vote, minus the Republican share, computed from summed precinct votes rather than averaged precinct margins. Missing where either major party is absent. Present in 523 races |
| `response_shift` | float | `dem_margin_two_party` minus `dem_margin`. Published so a comparison between definitions can separate a change in accuracy from a change in the target. Median 0.0; 36 races move more than a point, 5 move more than 10, and 16th Essex 2014 moves 54.4 |

Where no Democrat stood, `dem_margin` negates the leader's margin over the
strongest remaining candidate and `no_dem_candidate` is true, following the
precinct table. 13 races are in this position.

Both responses are vote-weighted, summing the race's precinct vote counts
before dividing. An unweighted mean of the precinct two-party margins differs
in every one of the 523 major-party races, by a median of 1.1 points and by as
much as 22.9 -- enough to flip the sign in election 124782, where the
vote-weighted margin is -9.6 and the precinct average is +13.3.

## Predictors

| Column | Type | Description |
|---|---|---|
| `PVI_N` | float | Partisan Voter Index for the district, in percentage points. The district's Democratic share of the combined two-party presidential vote across the two presidential elections preceding the race, minus the national share computed the same way |
| `incumbent_status` | string | `No_Incumbent`, `Dem_Incumbent`, or `GOP_Incumbent`. An unenrolled incumbent is classified as `GOP_Incumbent`, following the established model |
| `pres_elec` | boolean | Whether the race shared a ballot with a presidential general election |
| `is_special` | boolean | Whether the race was a special election. 38 of the 633 races |
| `num_candidates` | integer | Candidates in the race, as published in `ma-election-db`. Counts ballot lines, so a write-in is not included |

## Provenance and diagnostics

| Column | Type | Description |
|---|---|---|
| `no_dem_candidate` | boolean | True when no Democrat stood; changes how `dem_margin` is defined |
| `dem_candidate` | string | Candidate on the Democratic side of the margin |
| `opponent_candidate` | string | Candidate on the other side |
| `opponent_party` | string | That candidate's party |
| `dem_candidate_count` | integer | Democrats on the ballot. Greater than one in a handful of races |
| `major_party_race` | boolean | Both a Democrat and a Republican stood. The flag a two-party definition filters on |
| `contested_on_ballot_lines` | boolean | Two or more ballot lines, the pre-change contested test |
| `admitted_by_write_in` | boolean | Contested only because a write-in was admitted. True in 10 races |
| `num_candidates_admitted` | integer | Candidates counting admitted write-ins |
| `write_in_share` | float | District share of named-candidate votes taken by all write-ins combined |
| `top_write_in_share` | float | The same for the strongest write-in. What a write-in threshold is compared against |
| `dem_votes` | integer | District votes for `dem_candidate`. Where a Democrat stood this is that Democrat, so with `gop_votes` it is the two-party pair |
| `opponent_votes` | integer | District votes for `opponent_candidate` |
| `gop_votes` | integer | District votes for the strongest Republican, 0 where none stood. The other half of the `dem_margin_two_party` denominator |
| `write_in_votes` | integer | District votes for admitted write-in candidates |
| `candidate_votes` | integer | District votes for all admitted candidates. The denominator of `dem_margin` |
| `total_votes` | integer | All votes cast in the district, including blanks and all-others |
| `n_precincts` | integer | Precinct rows summed into this race. Ranges from 10 to 86 |
| `pvi_year` | integer | The later presidential election of the pair `PVI_N` was built from |
| `pvi_dem_votes` | float | District Democratic presidential votes across the PVI pair. Fractional where votes were areally interpolated |
| `pvi_gop_votes` | float | District Republican presidential votes across the PVI pair |
| `pvi_two_party_votes` | float | Their sum. The denominator of `PVI_N` |
| `pvi_coverage` | float | Share of the race's precincts that contributed presidential votes. Below 1.0 in 126 races, with a floor of 0.647 |
| `pvi_interpolated_share` | float | Share of `pvi_two_party_votes` that came from precincts remapped across a redistricting boundary by areal interpolation. Above zero in 114 races. These values are estimates and carry error |
| `precincts_split_across_districts` | integer | Precincts in this race that are divided between two districts, so the race's returns cover part of the precinct while its PVI covers all of it. Above zero in 23 races |

`data/race/race_pvi_coverage.csv` carries the same coverage figures for every
race including any excluded one, with a stated reason for each exclusion.

## Validation against the published district-level table

`maprecinct validate` compares every race against `mapoli`'s
`model/ma_leg_two_party_2008_2025.csv` and writes
`data/reports/race_rollup_validation.csv`. Each race is categorised rather
than merely counted, so a difference is either explained or flagged.

**`dem_margin`** — 596 of 623 agree to within 0.01 points. The 27 that do not
divide into two reference-side defects:

| Category | Races | Cause |
|---|---|---|
| `reference_no_democrat_precedence_bug` | 13 | `ma_leg_model.R`'s `democratic_margin()` multiplies the comparison share by 100 before subtracting instead of after, so every no-Democrat race in the reference is wrong. Documented in [`schema.md`](schema.md) |
| `reference_omits_candidate_from_summary_slots` | 14 | The published summary carries four candidate slots and leaves some candidates out, so its percentages rest on a denominator that omits those votes. The vote counts themselves agree exactly; only the denominator differs |

No race differs on `dem_margin` without one of these causes.

**`PVI_N`** — a national-baseline difference shifts every district in a PVI
vintage by the same amount, so the comparison separates that constant offset
from the per-district spread, as `validate.py` does for precinct PVI. 546
races agree within tolerance about their vintage's offset; none falls outside
it. The remaining 77 are marked `reference_pvi_on_different_map` and are not
compared, because the reference joined them to PVI computed on a different
redistricting cycle's precincts than the race was run under:

- **2012 races.** The reference uses the 2008 PVI on 2001-cycle geography;
  this table uses the same presidential pair reallocated to the 2011 map the
  race was actually run under.
- **2021 specials.** The reference assigns them the 2022 PVI, which is on the
  2021 map; they were run on 2011-cycle districts, so this table uses the
  2011-cycle PVI.

In both cases the two values describe different districts, so a difference
between them is not evidence about either.
