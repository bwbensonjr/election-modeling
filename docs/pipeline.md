# Precinct data pipeline

Collects Massachusetts precinct-level election results and assembles the
race-precinct training table described in [`schema.md`](schema.md), then rolls
it up to the race-grain table described in [`race_schema.md`](race_schema.md).

## Prerequisites

- `uv` and Python 3.11 or later.
- A sibling checkout of
  [`ma-election-db`](https://github.com/bwbensonjr/ma-election-db) at
  `../ma-election-db`, for election identifiers, race metadata and
  incumbency. Without it the pipeline falls back to the published URL and
  needs network access.
- A sibling checkout of [`mapoli`](https://github.com/bwbensonjr/mapoli) at
  `../mapoli`, for the 2011 and 2021 precinct boundary layers and for the
  published values the validation stage compares against.

```bash
uv sync
```

## Running

The whole pipeline:

```bash
uv run maprecinct all
```

Individual stages, in dependency order:

```bash
uv run maprecinct fetch all      # retrieve precinct results (network)
uv run maprecinct normalize      # normalize payloads and reconcile totals
uv run maprecinct districts      # derive precinct-to-district mappings
uv run maprecinct pvi            # compute precinct PVI
uv run maprecinct training       # assemble the training table
uv run maprecinct validate       # compare against mapoli's published values
```

## Rebuilding from cache

`fetch` writes every raw upstream response to `cache/electionstats/`, keyed by
election identifier, and reuses it on later runs. Only the first run touches
the network; every stage after it reads the cache. To rebuild all outputs
without refetching:

```bash
uv run maprecinct normalize && uv run maprecinct districts \
  && uv run maprecinct pvi && uv run maprecinct training \
  && uv run maprecinct races && uv run maprecinct validate
```

`cache/` is gitignored. Deleting it costs a full refetch; deleting anything
under `data/` costs only the stages that produce it. To deliberately refetch a
scope, pass `--force`:

```bash
uv run maprecinct fetch presidential --force
```

The 2001-cycle precinct boundary layer is downloaded into `cache/gis/` the
first time a stage needs it.

## Scope

| Set | Coverage | Elections |
|---|---|---|
| Presidential | 2004, 2008, 2012, 2016, 2020, 2024 | 6 |
| State Representative and State Senate | 2010 through 2024, general and special | 1,651 |

Precinct-level results begin in 2002 for every office except State
Representative, which reaches back to 1980. 2004 is therefore the first
presidential election with precinct returns, and the 2004 and 2008 pair is the
earliest PVI that can be built from two of them. See the repository README for
the derivation of the 2010 floor.

## Reports

Every stage writes its checks to `data/reports/` rather than failing silently.

| Report | What it records |
|---|---|
| `fetch_failures_*.csv` | Elections whose payload could not be retrieved or was not precinct-level |
| `reconcile_*.csv` | Precinct sums that disagree with published district totals |
| `precinct_district_conflicts.csv` | Precincts assigned to more than one district in a cycle |
| `pvi_missing_precincts.csv` | Precincts with no two-party votes, and any precinct the crosswalk could not resolve |
| `pvi_district_rollup_validation.csv` | District PVI rollups against mapoli's published values |
| `training_excluded_races.csv` | Races kept out of the training table, with the reason |
| `training_missing_pvi.csv` | Training rows with no PVI value |
| `training_rollup_validation.csv` | District rollups against the existing district-level table, with each divergence categorised |

An empty report is the expected outcome for the reconciliation checks. The
validation reports are expected to be non-empty and are interpreted, not
merely counted: see `schema.md` for what the categories mean.

## Measured run

| Phase | Requests | Wall clock |
|---|---|---|
| Cold fetch, empty cache | 1,657 (1,651 legislative + 6 presidential) | 31 minutes at the 1.0s throttle, averaging 1.11s per request |
| Every later stage, warm cache | 0 | 12.5 seconds for `maprecinct all` end to end |

The cache holds 7.1 MB across 1,657 payloads. One legislative election is
rejected rather than cached, leaving 1,650 usable; see below.

## Known upstream discrepancies

These are properties of the source data, confirmed by inspection. They are
reported on every run rather than suppressed.

| Election | Discrepancy | Effect |
|---|---|---|
| 127034, 3rd Berkshire special, 2011-10-18 | The only legislative election in scope whose returns are municipality-level: a single Pittsfield row with no ward or precinct breakdown | Rejected by the fetch validator and absent from the training table. 1 race of 1,651 |
| 105591, Worcester and Norfolk Senate, 2010-11-02 | One vote is a blank in the district summary and an all-other in the precinct returns | None. Candidate totals and the overall total agree, so the margin is unaffected |
| 105765, 6th Worcester special, 2011-05-10 | The precinct returns carry one more vote for one candidate than the summary, and one more vote in total | Shifts that race's margin by under 0.02 points |

Two further categories appear in `training_rollup_validation.csv` where this
table disagrees with the existing district-level table. Both are differences
in the reference, not here, and are described in
[`schema.md`](schema.md#response-variable):

- **`reference_denominator_omits_candidates`** (14 races). The published
  summary carries only four candidate slots, so in a race with more
  candidates its percentages are shares of a short denominator and every
  percentage in the row is inflated.
- **`reference_no_democrat_precedence_bug`** (13 races). An operator
  precedence error in the reference's margin function for races with no
  Democrat on the ballot.
