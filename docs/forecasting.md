# Election forecasting

The forecast workflow turns a locked, response-free candidate roster into a
dated prediction and later scores that unchanged prediction against certified
results. The 2026 scope is the contested Massachusetts State Representative
and State Senate races on November 3.

## Target construction

`data/forecast/2026/target.csv` has one row per race, keyed by
`election_date`, `office`, and canonical `district`. `target_id` is the first
20 hexadecimal characters of the SHA-256 digest of those three values joined
with `|`. `district_display` carries the numeric-ordinal spelling used by OCPF.

The pre-election roster comes from `ma-election-db`'s published 2026 Secretary
of the Commonwealth primary candidate roster and final electionstats primary
results. The normal general-election candidate artifact is unsuitable because
it is published only after general-election results exist. Primary results are
used only to identify nominees. The target contains no general-election vote,
winner, margin, or result field.

Two Republican nominees, Christopher C. Shepley in 18th Essex and Brendalee
A. Smith in 10th Bristol, qualified through primary write-in votes and were
therefore absent from the pre-primary roster. Their
`comparison_nominee_basis=final_primary_write_in_nominee` and
`comparison_nominee_review_status=confirmed_final_primary_result_only` make
that path explicit. Candidate IDs are stable hashes of primary date, office,
district, party, and source name.

`dem_candidate_id`/`dem_candidate_name` name the Democratic nominee.
`comparison_candidate_id`, `comparison_candidate_name`, and
`comparison_candidate_party` lock the other side. `comparison_rule` records
the outcome-blind rule and `comparison_review_status` records whether several
non-Democrats required an explicit pre-election choice. The four
`*_nominee_basis` and `*_nominee_review_status` fields record how each nominee
was established. Eventual vote order never changes this locked matchup.

`incumbent_status` uses the model's `Dem_Incumbent`, `GOP_Incumbent`, and
`No_Incumbent` levels. `ballot_timing` is fixed to `midterm_gop_pres` for this
election. `money_complete_60d` and `money_complete_14d` state whether both
candidates have usable OCPF finance at each horizon.

`PVI_N` is recomputed by summing the 2020 and 2024 two-party presidential votes
of every precinct assigned to the district on the 2021 map, then subtracting
the corresponding national Democratic two-party share. `pvi_year`,
`redistricting_cycle`, `pvi_coverage`, `pvi_interpolated_share`, and
`pvi_provenance` disclose the vintage, map, contributing-precinct fraction,
share of votes assigned by areal interpolation, and whether interpolation was
used.

`candidate_source`, `candidate_source_digest`, and `candidate_data_as_of`
identify the roster inputs. `pvi_source` and `pvi_source_digest` identify the
precinct PVI, district map, and national baseline inputs. Validation refuses
duplicate keys, unsupported offices, missing provenance, stale target IDs,
source-roster disagreement, non-recomputable PVI, and any result-bearing
column.

## Finance horizons

Run the candidate resolver without collecting money:

```bash
uv run legmodel target-finance --horizon 60d --dry-run
```

Freeze or verify a horizon, using only cached OCPF responses when requested:

```bash
uv run legmodel target-finance --horizon 60d
uv run legmodel target-finance --horizon 60d --cache-only
```

The 60-day cutoff is 2026-09-04 and the 14-day cutoff is 2026-10-20. Each
candidate row in `finance_60d.csv` or `finance_14d.csv` carries target and race
identity, `role`, source candidate identity, `cpf_id`, `filer_name`,
`match_rule`, `filers_considered`, `roster_source`, and `roster_error`. It also
carries `horizon`, `window_start`, exact `cutoff`, `available`, receipts and
expenditures with item counts and cache identities, and `race_complete`.
Unmatched or ambiguous filers remain unavailable; they are never assigned
zero. A published horizon is create-once: an identical cache-only rerun
verifies it, while different bytes are refused.

## Forecast snapshots

The selected operational composites are documented in
`docs/forecast_selection.md`. At 60 days, finance-complete races use
`baseline_money_logratio_no_timing_wide`; incomplete races use
`baseline_no_timing`. The 14-day composite substitutes the corresponding
14-day receipts model. The fallback is a separately fitted model, not a zero
imputation.

From a committed clean worktree, publish or verify a snapshot with:

```bash
uv run legmodel forecast --horizon 60d
```

Training applies the adopted historical definition to every completed race
strictly before the target election, including November 2024. Each component
seed hashes the composite, component, definition, latest training election,
target election, and horizon; target row order is absent from the seed.

Each `snapshots/<horizon>/` directory is create-once and contains:

- `races.csv`: target identity, matchup, composite and component, fallback
  reason, posterior mean margin, 90% predictive bounds, and Democratic win
  probability.
- `chamber_draws.csv.gz`: posterior sample index plus aligned Democratic wins
  for State Representative, State Senate, and all contested target races.
- `support_warnings.csv`: target, component, predictor and target value;
  numeric training range; categorical training race and election-date counts;
  and a named warning for extrapolation, an unseen level, or a level observed
  on only one election date.
- `manifest.json`: target, finance, training, code and output digests; composite
  and component declarations; definition; training and finance cutoffs;
  component counts and diagnostics; seeds and their inputs; and the aggregate
  limitation.

Support warnings disclose extrapolation but do not clip values, change a
prediction, or widen an interval. Generation fails for missing, duplicate, or
multiply routed target identities, a horizon-mismatched dated predictor, a
dirty worktree, or conflicting snapshot bytes.

The chamber draws preserve the shared coefficient and other posterior
dependence represented within each fitted component. Deterministic sample
alignment combines independently fitted components. It does not add a shared
2026 statewide election shock or claim correlation between component fits;
chamber intervals must not be described as accounting for that unmodeled
environment.

## Prospective scoring

After certified results are available, provide a CSV with `target_id`,
`dem_votes`, and `comparison_votes` and run:

```bash
uv run legmodel forecast-score --horizon 60d \
  --results data/forecast/2026/certified_results.csv \
  --result-source "Secretary of the Commonwealth certified results"
```

Scoring reads the locked `races.csv` and chamber draws and never calls the
fitter. It writes a create-once `score/` directory containing per-race margin
errors, coverage, Brier score and log loss; pooled, office, component and seat
metrics; ten fixed calibration bins including empty bins; explicit missing and
extra race reports; and a manifest with result provenance, digests, and scored
and unscored counts. Incomplete certified coverage is scored where possible,
but a partial observed seat count is not compared with the full snapshot's
seat distribution. The original forecast files are checked before and after
and cannot be mutated or replaced.
