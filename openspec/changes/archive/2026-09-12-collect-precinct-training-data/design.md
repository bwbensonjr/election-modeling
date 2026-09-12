## Context

See `proposal.md` for motivation. The constraints that shape the approach:

- **Two sibling repositories already solve parts of this, in R.** `mapoli`
  fetches precinct results (`results/ma_results.py`) and computes PVI
  (`pvi/ma_pvi_2024.R`, `R/pvi_utils.R`); `ma-election-db` normalizes the
  results into a SQLite database and publishes gzipped CSVs. Their combined
  coverage is presidential 2012-2024 only, and their precinct reconciliation
  logic lives in R utilities (`R/precinct_utils.R`) this project cannot call
  from Python.
- **The upstream endpoint is quiet about failure.** For elections before
  precinct reporting it returns municipality rows with empty ward and
  precinct fields and a 200 status; on error it returns an HTML page, also
  without a useful status. Correctness depends on inspecting the payload.
- **Precinct geography exists in three vintages, two of which we have.**
  `mapoli/gis/shp` holds the 2011-cycle and 2021-cycle wards and precincts
  layers. The 2001-cycle layer, needed to interpolate 2004 and 2008 votes
  forward, is not present in any repository. Task 1.1 established that it is
  obtainable from outside them; see D10.
- **The response variable and predictors are already defined.**
  `mapoli/model/ma_leg_model.R` fixes `dem_margin`, `incumbent_status`, and
  the race-year to PVI-year mapping; `R/pvi_utils.R` fixes the PVI formula.
  This change reproduces those definitions at precinct grain rather than
  inventing new ones.

## Goals / Non-Goals

**Goals:**

- A staged pipeline where each stage reads committed inputs and writes
  committed outputs, so a failure or a revision in one stage does not force
  re-running the network fetch.
- Definitional parity with the existing district-level model, so a
  district rollup of the precinct table can be checked against
  `ma_leg_two_party_2008_2025.csv`.
- Explicit provenance on every remapped value, so interpolation error is
  visible to the modeler rather than buried.

**Non-Goals:**

- No modification of `mapoli` or `ma-election-db`. They are read-only inputs.
- No attempt to generalize the pipeline to offices or years beyond the scope
  in the proposal, even where the upstream data would support it.
- No database. Flat files are the interface.

## Decisions

### D1: All code and data live in `election-modeling`, in Python

The pipeline is a Python package in this repository managed with `uv` and
`pyproject.toml`, per the project development guidelines. It consumes the
sibling repositories only through their published artifacts: election
identifiers, race metadata, and incumbency from `ma-election-db`'s
`ma_general_election_summaries.csv.gz`; precinct geometry from `mapoli/gis`;
and `mapoli/pvi/ma_precincts_districts_*.csv` plus
`ma_state_leg_pvi_2008_2024.csv` as validation references.

*Alternative considered:* add the fetches to `mapoli/results` and the
normalization to `ma-election-db`, following the established pipeline
convention. Rejected because it spreads one change across three
repositories and two languages, and because the R precinct utilities would
still need Python equivalents here. The cost is that `ma_results.py`'s fetch
logic is reimplemented rather than shared.

### D2: Election identifiers come from the published summaries, not the search API

Every election to fetch is enumerated by filtering
`ma_general_election_summaries.csv.gz` on office and date range, which yields
the `election_id` for each district. The electionstats search endpoint is not
called.

*Rationale:* the summaries are already the authority for the race metadata
this change needs, so using them keeps the row set and the metadata
consistent by construction. The search endpoint also proved unreliable under
repeated querying, returning bare scalars instead of JSON.

### D3: Raw responses are cached on disk, keyed by election identifier

The fetch stage writes each raw response to a cache directory that is
gitignored, and all later stages read from the cache. Re-running the
pipeline issues no network requests for elections already cached.

*Rationale:* roughly 1,700 requests at a polite rate is a long run, and
every downstream stage will be revised several times during implementation.
*Alternative considered:* committing the raw responses. Rejected on size;
the processed outputs are committed instead.

### D4: Validation is a pipeline stage, not a test suite afterthought

Each stage ends by reconciling against an independent source and failing
loudly on mismatch: precinct sums against district totals from
`ma-election-db`, statewide sums before and after each remap, and district
PVI rollups against `mapoli`'s published values. Mismatches are written to a
report keyed by race or precinct.

*Rationale:* the failure modes here are silent and data-shaped. A race that
quietly loses three precincts still produces a plausible-looking table.

### D5: Crosswalk is identifier-first, interpolation only for the residue

Precincts are matched across a redistricting boundary on
`(city_town, ward, precinct)` after normalizing municipality names and
filling single-precinct municipalities. Matched precincts carry integer vote
totals forward unmodified. Only unmatched precincts are interpolated by area
weighting, using the two cycles' precinct polygons. Parent and child
precincts are combined before matching, following the approach in
`mapoli/R/precinct_utils.R`.

*Rationale:* most precincts survive a redistricting with their identifiers
intact, and every precinct resolved by identifier is exact rather than
estimated. *Alternative considered:* interpolating everything for
uniformity. Rejected because it would introduce estimation error into
precincts that need none, and because it makes the whole table depend on a
GIS layer we do not yet have.

### D6: PVI is keyed by presidential pair and redistricting cycle, not by a single year label

`mapoli` labels the 2016 and 2020 pair evaluated on 2021 precincts as
`pvi_year` 2022, which conflates the pair with the geography. This pipeline
keys every PVI record on both, because including specials makes the
distinction load-bearing: a 2021 special ran on 2011-cycle districts and must
join to the 2016 and 2020 pair on 2011 precincts, while a 2022 general joins
to the same pair on 2021 precincts.

*Consequence:* seven PVI datasets rather than five, and a race-year to
`(pair, cycle)` mapping table carried as data.

### D7: The margin comparison candidate is fixed at race level

`dem_margin` at district level is the Democratic share minus the strongest
non-Democratic share. Applied naively per precinct, the strongest opponent
could differ between precincts of the same race, making the column
incoherent. The opponent is therefore selected once from district totals and
then held fixed across that race's precincts.

### D8: Uncontested races are fetched but excluded from the training table

Uncontested races carry no usable margin and are filtered out, matching the
existing model's `num_candidates > 1` filter. Their precinct returns are
still fetched, because they are the source for the 2001-cycle
precinct-to-district mapping, which exists nowhere else.

### D10: 2001-cycle precinct geometry comes from the MGGG `MA_precincts_02_10` layer

Investigated under task 1.1. MassGIS publishes only the 2012 and 2022
vintages of its wards and precincts layer, with no archived 2002 edition.
The gap is filled by `mggg-states/MA-shapefiles`, whose
`MA_precincts_02_10.zip` carries 2,156 precinct polygons covering all 351
municipalities, built on 2010 Census voting tabulation districts that the
Census Bureau supplied to the Secretary of the Commonwealth. It uses the
same `-` ward convention for single-ward municipalities that this project
and `mapoli` already use, and it is published under the Open Database
License, so it is usable with attribution.

The layer also carries two-party presidential totals per precinct for 2004
and 2008. Summed statewide these reproduce the official certified results
exactly: 1,803,800 to 1,071,109 in 2004 and 1,904,097 to 1,108,854 in 2008.
That makes the layer an independent cross-check on the electionstats fetch
for precisely the two elections with no other corroborating source in any
sibling repository, so D4's validation stage checks 2004 and 2008 precinct
totals against it.

*Caveat:* the polygons are precincts as enumerated for the 2010 census, not
as they stood in 2004. Municipalities that renumbered precincts mid-decade
are reconciled by the within-cycle identifier matching the crosswalk spec
already requires, not by assuming the 2010 boundaries held for the whole
cycle.

*Alternative considered:* pulling the raw Census TIGER 2010 voting districts
layer for Massachusetts directly. It is the same underlying geometry from an
unambiguously public source, but it lacks the town, ward, and precinct
labels this pipeline joins on, which would have to be parsed back out of
`NAME10`. Kept as a fallback if the MGGG repository becomes unavailable.

### D9: Outputs are gzipped CSVs

Matching `ma-election-db`'s convention and keeping the outputs diffable by
tooling the project already uses. Parquet and SQLite were considered;
neither earns its complexity at this size.

## Risks / Trade-offs

- **~~The MassGIS 2001-cycle wards and precincts layer may not be
  available.~~ Resolved by task 1.1.** This was the largest risk, gating
  race years 2012 through 2016. The geometry was located outside MassGIS and
  verified; see D10. The contingency is retained in the specs regardless: an
  unresolvable precinct is reported rather than estimated, and its race is
  published with missing `PVI_N`.
- **Interpolated vote totals carry estimation error into the response
  variable's main predictor.** → Provenance is recorded per row (D5), so a
  model run can exclude interpolated rows or model the distinction. The
  fractional totals that result are stored as reals, as `mapoli` already does
  for the 2021 remap.
- **Precinct identifiers churn between elections, not only at redistricting
  boundaries.** → Municipalities renumber precincts mid-cycle. The crosswalk
  compares precinct sets between consecutive elections within a cycle, not
  only across cycle boundaries, and routes any difference through the same
  identifier-then-interpolate path.
- **Roughly 1,700 requests against a state government endpoint with no
  documented rate limit.** → Throttled sequential fetching with a cache
  (D3), so the full volume is issued once. A failed or malformed response
  aborts that election rather than being written as partial data.
- **Reimplementing `mapoli`'s R logic in Python risks silent divergence.** →
  D4's validation reconciles against `mapoli`'s published outputs for the
  years both cover, so divergence surfaces as a reported mismatch.
- **Precinct-grain rows within a district are strongly correlated.** → Out of
  scope for this change, which delivers data only, but the table carries
  `election_id` and district identifiers so that a model can group or cluster
  by race. Worth flagging to whoever fits the first model on it.

## Migration Plan

There is nothing to migrate. No existing consumer reads these outputs, the
district-level model in `mapoli` is untouched, and each stage can be
developed and run independently in order: investigate geography, fetch,
normalize, crosswalk, PVI, assemble. Rollback is deleting the generated
files.

## Open Questions

- ~~The numeric tolerances for the reconciliation checks in D4.~~ Resolved
  during implementation. Two separate quantities turned out to matter, and
  conflating them would have hidden the real signal:

  - **Precinct sums against published district totals: exact.** All six
    presidential elections and their candidate, blank, all-other and total
    vote counts reconcile with no difference, so this check has no tolerance
    at all. The same applies to statewide totals across a remap, which the
    crosswalk preserves to the vote.
  - **District PVI rollups against mapoli: a constant offset, then a
    spread.** mapoli's published values for a year can rest on a different
    national baseline than the FEC totals used here, which shifts every
    district in that year identically: +0.747 points for PVI year 2016 and
    -0.210 for 2020. The meaningful quantity is therefore the spread about
    that offset, not the raw difference. Observed spreads are 0.006 points
    or less for natively-mapped cycles, where no estimation is involved, so
    the tolerance there is 0.05. Remapped cycles carry areal interpolation
    that mapoli performs with a different implementation and layer, and
    their spread reaches 3.0 points on the districts containing split
    precincts, so the tolerance there is 5.0.

  The constant offsets are a definitional difference, not an error, and are
  reported rather than tuned away. This pipeline uses one auditable baseline
  across all years (D-series reference file
  `national_presidential_baseline.csv`), which mapoli's published series does
  not.
