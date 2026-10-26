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

`dem_candidate_id`/`dem_candidate_name` name the Democratic nominee, while
`dem_candidate_municipality` and `dem_candidate_incumbent` carry the
Secretary roster's residence and incumbency flag. `comparison_candidate_id`,
`comparison_candidate_name`, `comparison_candidate_party`,
`comparison_candidate_municipality`, and `comparison_candidate_incumbent`
lock the other side and its presentation metadata. `comparison_rule` records
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
source-roster disagreement, missing candidate municipality data,
non-recomputable PVI, and any result-bearing
column.

## Nomination-paper candidates and forecast revisions

The original `target.csv` holds only primary nominees, so it misses races in
which a Democrat faces a candidate who reached the ballot by nomination papers
(unenrolled, independent, or a minor-party designation). The adopted
`two_party_or_strongest` definition trains on races of that kind, so they
belong in the target.

`data/forecast/2026/nomination_candidates.csv` is a hand-reviewed transcription
of every legislative candidate on the Secretary's
[2026 State Election Candidates](https://www.sec.state.ma.us/divisions/elections/research-and-statistics/2026-state-election-candidates.htm)
page who is not a primary nominee. The page blocks scripted downloads, so it
is transcribed by hand. Columns are `office`, canonical `district`,
`district_display`, `party` (the ballot designation as printed), `name`,
`municipality`, `is_incumbent`, `source_url`, and `source_as_of`. The file
lists every such candidate, including third candidates in races that already
have a Republican and candidates in districts with no Democrat, so it
reconciles with the whole page. When it was transcribed, the page listed 186
Democratic and 59 Republican legislative candidates, the same counts as the
primary nominees, and every contested Democrat-versus-Republican race named
the same candidates as the target. The build refuses a row that is missing a field, repeats a
primary nominee, or names a district absent from the 2021 district map.
Supplement candidate IDs hash the general-election date, so they cannot
collide with primary IDs. Their `*_nominee_basis` is `nomination_paper`.

The comparison candidate follows `comparison_rule=republican_else_sole_non_democrat`,
which mirrors the adopted training response. It is the Republican when one is
on the ballot (`comparison_review_status=not_required_republican_present`),
otherwise the only non-Democrat
(`not_required_one_non_democratic_candidate`). Only a race with no Republican
and several other candidates requires an explicit pre-election review. A
non-Democratic incumbent opponent of any designation is coded `GOP_Incumbent`,
as the training data codes it. Opponent party is not a predictor.

A change to the set of target races is published as a new forecast revision,
leaving every earlier target, finance file, snapshot, and bundle untouched.
`legmodel.config.FORECAST_2026_REVISIONS` maps each forecast to its horizon
and files:

| Forecast | Horizon | Target | Finance | Races |
|---|---|---|---|---|
| `60d` | 60d | `target.csv` | `finance_60d.csv` | 46 |
| `14d` | 14d | `target.csv` | `finance_14d.csv` | 46 |
| `14d-r2` | 14d | `target_r2.csv` | `finance_14d_r2.csv` | 57 |

`14d-r2` supersedes `14d`. It uses the same 2026-10-20 cutoff and adds 11
races, eight for State Representative and three for State Senate. Every
`--horizon` option below accepts a forecast name, and the snapshot and bundle
directories are named after it. Build or verify a revision's target with:

```bash
uv run legmodel forecast-target --horizon 14d-r2
```

The command reads the ma-election-db primary roster and results, the
supplement, and the precinct PVI inputs. It recomputes PVI, runs the same
source verification as the original target, and creates the target once.
Later runs only verify the bytes. Its `candidate_source_digest` covers the
roster, results, and supplement in that order. Its `money_complete_*` flags
record which finance horizons were complete when the target was built.
Forecasting recomputes completeness from the finance file. A superseding
snapshot's manifest adds `revision`, `supersedes`, `added_target_ids`, and
`removed_target_ids`.

The original `target.csv` was written before the comparison rule had a name in
code. Its `comparison_rule` and `comparison_review_status` values
(`republican_nominee_from_2026_primary`, `not_required_one_republican_nominee`)
are kept as published. The `60d` snapshot manifest also digests the target and
training table as they stood before the 2026-09-26 presentation commit. Its
races and chamber draws still regenerate byte-for-byte, but its manifest
digests no longer match the current files.

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
