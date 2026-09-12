## Why

The current legislative model trains on 679 district-level rows covering
2008-2025, which is thin for a four-variable regression and leaves no room
for the demographic and fundraising variables the project plans to add.
Massachusetts State Senate and State Representative districts split
municipalities, so precinct-level presidential results are required to
compute PVI for a district at all, and the same precinct results support
modeling at precinct grain directly. The README cutoff analysis establishes
that this is feasible for legislative elections from 2010 onward: precinct
results begin in 2002 for all offices, making 2004 the first presidential
with precinct returns and 2008 PVI (2004 + 2008) the earliest PVI built
from two precinct-level presidential elections.

## What Changes

- Add a reproducible Python/`uv` collection pipeline in this repository
  that fetches precinct-level results from
  `electionstats.state.ma.us/elections/download/{election_id}/precincts_include:1/`
  for:
  - President: 2004, 2008, 2012, 2016, 2020, 2024 (one election per year)
  - State Representative and State Senate: every election from 2010
    through 2024, general and special (one election per district per cycle,
    roughly 1,700 requests including specials and uncontested races)
- Add a precinct crosswalk spanning the 2001, 2011, and 2021 redistricting
  cycles. Precincts are matched on `(city_town, ward, precinct)` first and
  carried over exactly where identifiers are stable; only the residue is
  resolved by areal interpolation, which requires obtaining the MassGIS
  2001-cycle wards and precincts layer (mapoli currently holds only the
  2011 and 2021 vintages).
- Compute precinct-level `PVI_N` for each combination of presidential pair
  and redistricting cycle the window requires, normalized against the
  national two-party margin. Because off-year specials run on the previous
  cycle's districts, two pairs must be produced on two geographies each,
  giving seven PVI datasets rather than one per presidential election.
- Assemble a race-precinct training table: one row per
  `(election_id, city_town, ward, precinct)` carrying `dem_margin` and
  `PVI_N` computed at precinct grain, with `incumbent_status`, `pres_elec`,
  `is_special`, and `num_candidates` repeated from the district-level race.
  Estimated 10,000 to 15,000 rows across the eight cycles, against 679 rows
  in the current district-level table; the exact count depends on how many
  races are two-party contested and is confirmed during implementation.
- Commit the processed outputs as gzipped CSVs so the modeling work does not
  depend on re-running collection.
- Reuse existing `bwbensonjr` artifacts rather than re-deriving them:
  election IDs, `incumbent_status`, and race metadata come from
  `ma-election-db`'s published general election summaries; mapoli's
  `ma_precincts_districts_*.csv` files serve as a cross-check for the
  2012-2024 presidential precinct totals; mapoli's GIS layers supply the
  2011 and 2021 precinct geometry.

### Non-Goals

- No changes to model structure, fitting, or evaluation. This change
  delivers data only.
- No primary elections, no offices beyond State Representative and State
  Senate, no legislative races before 2010. Presidential results are
  collected as a PVI input only, not as modeling rows in their own right.
- No demographic or OCPF fundraising variables; those are separate
  enhancements that will consume this table.

## Capabilities

### New Capabilities

- `precinct-election-results`: Fetching, caching, and normalizing
  precinct-level general election results from electionstats for the
  presidential and legislative elections in scope.
- `precinct-crosswalk`: Mapping precincts across the 2001, 2011, and 2021
  redistricting cycles, and reallocating presidential votes onto the
  precinct geography a given race was run under.
- `precinct-pvi`: Computing precinct-level PVI from two consecutive
  presidential elections against a national two-party baseline.
- `precinct-training-set`: Assembling and publishing the race-precinct
  training table with the model's response and predictor variables.

### Modified Capabilities

None. `openspec/specs/` is currently empty; this change introduces the
project's first capabilities.

## Impact

- **New code in this repository.** A collection package plus `pyproject.toml`
  dependencies: `requests` and `pandas` for fetching and reshaping,
  `geopandas` and an areal interpolation library for the crosswalk residue.
- **New committed data.** Raw fetch cache (gitignored) plus processed
  gzipped CSVs for precinct results, the crosswalk, precinct PVI, and the
  training table.
- **External dependencies.** The electionstats download endpoint, which has
  no documented rate limit and returns HTML error pages on failure, so
  fetches must be cached, throttled, and validated. The MassGIS 2001-cycle
  wards and precincts layer, whose availability is not yet confirmed and is
  the main risk to covering race years 2012 through 2016.
- **No changes to sibling repositories.** `mapoli` and `ma-election-db` are
  read-only inputs here.
- **Reconciliation risk.** Precincts that were renumbered across a
  redistricting boundary and cannot be matched by identifier will carry
  interpolated vote totals, and any precinct that cannot be resolved either
  way must be reported rather than silently dropped.
