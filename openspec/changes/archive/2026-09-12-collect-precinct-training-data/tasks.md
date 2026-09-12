## 1. Setup and geography investigation

- [x] 1.1 Determine whether the MassGIS 2001-cycle wards and precincts layer is obtainable, and record the answer in design.md; verify by either downloading the layer into a local GIS input directory or documenting the specific MassGIS pages checked and the outcome
- [x] 1.2 Initialize the Python package and `pyproject.toml` with `requests`, `pandas`, `geopandas`, and an areal interpolation dependency; verify `uv sync` succeeds and the package imports
- [x] 1.3 Add the data and cache directory layout with the raw response cache gitignored; verify `git status` shows the cache untracked and the processed data directories tracked
- [x] 1.4 Record the race-year to `(presidential pair, redistricting cycle)` mapping as a committed data file matching the table in the PVI spec; verify every legislative election year from 2010 through 2024 resolves to exactly one combination

## 2. Election enumeration and fetching

- [x] 2.1 Build the election enumerator that reads `ma-election-db`'s general election summaries and lists every in-scope election with its identifier, office, district, date, and special flag; verify the count of State Representative and State Senate elections per cycle matches the summaries and that specials are included
- [x] 2.2 Implement the throttled, cached fetch client for the precinct download endpoint; verify a repeat run issues zero network requests and produces identical cache contents
- [x] 2.3 Implement payload validation that rejects non-CSV responses and responses with no populated precinct values; verify against a known pre-2002 election, which must be refused, and a known 2004 election, which must be accepted
- [x] 2.4 Fetch the six presidential elections from 2004 through 2024; verify each yields at least 2,100 precinct rows
- [x] 2.5 Fetch all State Representative and State Senate elections from 2010 through 2024, general and special; verify every enumerated election has a cached response or an explicit recorded failure

## 3. Normalization

- [x] 3.1 Implement the normalizer producing one row per `(election_id, city_town, ward, precinct)` with per-candidate votes, handling both header vintages; verify the normalized column set is identical across a 2004, a 2012, and a 2024 file
- [x] 3.2 Implement identity normalization: unabbreviate compass directions in municipality names, fill single-precinct municipalities with ward `-` and precinct `1`, and drop `TOTALS` and party-label rows; verify no normalized row has an empty ward or precinct and that municipality names join cleanly against the GIS layer
- [x] 3.3 Reconcile normalized precinct sums against district totals from `ma-election-db` for every collected election; verify the mismatch report is empty or that each entry has a documented cause
- [x] 3.4 Write the normalized presidential and legislative precinct results as gzipped CSVs; verify the files reload and round-trip to the same row counts

## 4. Precinct crosswalk

- [x] 4.1 Derive the 2001-cycle precinct-to-district mapping from the precinct-level legislative returns, including uncontested races; verify every precinct maps to exactly one district per office and that conflicts are reported
- [x] 4.2 Assemble precinct-to-district mappings for the 2011 and 2021 cycles from the normalized legislative returns; verify they agree with `mapoli`'s `ma_precincts_districts_pres_2024.csv` district assignments for the 2021 cycle
- [x] 4.3 Implement parent and child precinct combination so subdivided precincts are reduced to a common parent before matching; verify combined totals equal the sum of their children
- [x] 4.4 Implement identifier matching across redistricting boundaries and within cycles, carrying matched precincts forward with integer totals; verify the matched share is reported and that matched totals are unchanged
- [x] 4.5 Implement areal interpolation for unmatched precincts using the two cycles' precinct polygons; verify statewide Democratic and Republican totals are preserved across the remap within tolerance
- [x] 4.6 Produce the unresolved precinct report and the per-record provenance column; verify no precinct is dropped without appearing in the report and that every remapped record carries a provenance value

## 5. Precinct PVI

- [x] 5.1 Record national two-party presidential totals for 2004 through 2024 as a committed baseline file with sources; verify the 2016, 2020, and 2024 values match the constants in `mapoli/R/pvi_utils.R`
- [x] 5.2 Implement the two-election PVI calculation excluding third-party, write-in, and blank votes; verify it reproduces a hand-computed value for a sample precinct
- [x] 5.3 Produce all seven `(pair, cycle)` PVI datasets required by the PVI spec table; verify each required combination exists and that precincts with no two-party votes are recorded as missing and reported
- [x] 5.4 Validate district rollups against `mapoli`'s published `ma_state_leg_pvi_2008_2024.csv` for the combinations both cover; verify agreement within the stated tolerance and that outliers are reported
- [x] 5.5 Write the precinct PVI datasets as gzipped CSVs keyed by PVI year and cycle; verify the keys are unique

## 6. Training table assembly

- [x] 6.1 Derive `incumbent_status`, `pres_elec`, `is_special`, and `num_candidates` per race from `ma-election-db`; verify the values match `ma_leg_two_party_2008_2025.csv` for races that appear in both
- [x] 6.2 Select the strongest non-Democratic candidate once per race from district totals and compute precinct `dem_margin` against that fixed comparison; verify a race whose runner-up differs between precincts still yields one comparison candidate
- [x] 6.3 Filter out races with fewer than two candidates; verify no single-candidate race contributes rows while its precincts still appear in the crosswalk outputs
- [x] 6.4 Join PVI on both presidential pair and redistricting cycle, including the off-year special case; verify a 2021 special joins to 2011-cycle PVI and a 2022 general joins to 2021-cycle PVI
- [x] 6.5 Assemble and write the training table as a gzipped CSV; verify the row key is unique, the row count is within the estimated range, and missing `PVI_N` rows are flagged and counted
- [x] 6.6 Validate the district rollup of the training table against the existing district-level table; verify `dem_margin` agrees within rounding tolerance for races present in both and that discrepancies are reported

## 7. Documentation and publication

- [x] 7.1 Write the schema document describing every training table column, its units, and its source; verify each published column appears in the document
- [x] 7.2 Document how to run the pipeline end to end and how to rebuild from cache; verify the documented commands run on a fresh checkout with the cache present
- [x] 7.3 Update the repository README to point at the published training table and its coverage; verify the stated coverage matches the delivered data
- [x] 7.4 Run the full pipeline end to end from an empty cache and record the runtime and request count; verify all validation reports are empty or have documented entries
