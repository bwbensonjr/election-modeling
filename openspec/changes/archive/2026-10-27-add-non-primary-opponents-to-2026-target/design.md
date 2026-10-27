# Design

## Context

See proposal.md for why. Today the target pipeline works like this:

- `forecast.build_target_candidates` joins the ma-election-db 2026 primary
  roster to the final primary results and keeps only primary winners.
  Candidates who reached the ballot by nomination papers never enter that
  join.
- `forecast.expected_target_matchups` drops any race with no non-Democrat.
  When a race has several non-Democrats, `select_comparison_candidate` raises
  `TargetReviewRequired`. If the four three-way races had reached it, they
  would have stopped there.
- `data/forecast/2026/target.csv` has no committed build script. It is
  checked by `verify_target_sources`, which compares candidate identity
  columns, and by `validate_target`. Its `comparison_rule` value
  (`republican_nominee_from_2026_primary`) differs from the string the code
  emits (`primary_nominee_then_pre_election_review`). Verification does not
  compare that column, so nothing currently catches the difference.
- Snapshots are create-once. `forecast_run.run` takes the target and finance
  paths from `config`, derives the snapshot directory from the horizon name,
  and refuses to overwrite different bytes. `interactive.run` derives its
  snapshot, finance, and bundle paths from the horizon name the same way.
- The adopted training definition is `two_party_or_strongest`. It uses the
  Republican margin where a Republican ran and the strongest non-Democrat
  otherwise. `training.incumbent_status` groups every non-Democratic incumbent
  with `GOP_Incumbent`.

The Secretary's page is protected by bot detection, so it cannot be fetched
by script. Any snapshot of it has to be transcribed by hand and reviewed.

## Goals / Non-Goals

**Goals:**

- Build the 57-race target with a reproducible command from committed inputs.
- Encode the comparison rule so that the four three-way races and the 11 new
  races need no ad hoc review.
- Publish a `14d-r2` forecast and bundle without touching the `60d` or `14d`
  artifacts.

**Non-Goals:**

- No `60d` revision. The 60-day snapshot stays a 46-race prospective record.
- No model change. Opponent party is not added as a predictor. The adopted
  definition already pools non-Republican opponents with Republicans, so the
  forecast does the same.
- No collection of non-legislative offices.
- No new `ocpf-cli` capability. A resolution gap is reported, not fixed here.

## Decisions

**D1. A hand-reviewed supplement CSV in this repo.**
The file is `data/forecast/2026/nomination_candidates.csv`, with columns
`office, district, district_display, party, name, municipality,
is_incumbent, source_url, source_as_of`. It lists every legislative
candidate on the Secretary's general-election page who is not a primary
nominee, not only the 11 needed opponents. That includes the independents in
three-way races and candidates in districts with no Democrat, such as
Susannah Whipps in 2nd Franklin. Listing all of them makes the file a
complete reconciliation of the Secretary's page, and the builder ignores rows
that do not create a contested race. `party` holds the ballot designation
exactly as printed (`Unenrolled`, `Independent`, `Workers Party`,
`Gulf War Veteran`, `Transparency Inclusion Environment`). `district` uses
the ma-election-db canonical spelling, so the file joins to the primary
roster and the PVI rollup.
Alternative considered: a `general_2026/` builder in ma-election-db. The user
chose the local file. Eleven opponents plus a few third candidates does not
justify a new upstream artifact five days before publication.

**D2. Supplement rows become candidates through a separate path.**
A new `build_supplement_candidates` turns each supplement row into the same
candidate frame that `build_target_candidates` produces. The candidate ID
uses the general-election date in the existing `source_candidate_id` hash,
so the IDs cannot collide with primary IDs. It sets
`nominee_basis=nomination_paper` and
`nominee_review_status=confirmed_secretary_general_candidate_list`. The two
frames are concatenated. A supplement row that matches a primary nominee by
office, district, and normalized name is an error, because it means the
transcription is wrong.

**D3. The comparison rule lives in code.**
`select_comparison_candidate` returns the Republican when exactly one stands,
with status `not_required_republican_present`. Otherwise it returns the sole
non-Democrat, with status `not_required_one_non_democratic_candidate`.
Otherwise it requires a review, as it does today. The rule name becomes
`republican_else_sole_non_democrat`, and `verify_target_sources` starts
comparing `comparison_rule` and `comparison_review_status`, so the stale
string found in Context cannot drift again. Incumbent status keeps the
existing `GOP_Incumbent` coding for any non-Democratic incumbent, matching
`training.incumbent_status`.

**D4. The target build becomes a command.**
`legmodel forecast-target --horizon 14d-r2` loads the primary roster, primary
results, supplement, and PVI inputs. It runs the existing matchup and PVI
logic, writes `target_r2.csv` create-once, and calls `verify_target_sources`.
The flag is `--horizon` to match the other forecast commands, and it accepts
only superseding revisions, because original targets predate the builder.
The unrevised `target.csv` is never rewritten, so the 14d manifest's
`target_digest` still matches its file.

**D5. Revision-aware paths.**
`config` gains a revision table that maps a forecast identifier (`60d`,
`14d`, `14d-r2`) to its horizon, target path, finance path, snapshot
directory, and bundle directory. `forecast_finance.run`, `forecast_run.run`,
and `interactive.run` take that identifier instead of a bare horizon, and use
the table's horizon for the window and cutoff. With the unchanged
identifiers, the existing outputs must regenerate and verify byte-for-byte.
That check is the guard against breaking earlier snapshots. The `14d-r2`
manifest adds `revision`, `supersedes: "14d"`, and `added_target_ids`.

**D6. Finance for the new candidates reuses the existing resolver.**
`forecast_finance.resolve` already resolves candidates through
`ocpf.race_roster` for each district. Unenrolled and minor-party candidates
appear in that roster when they have an OCPF committee. A candidate with no
committee, or with no unique match, gets `available=False`. The race then
routes to the existing no-money fallback component, with `fallback_reason`
set as it is today. For the 46 original races, `finance_14d_r2.csv` must
equal `finance_14d.csv` row for row, apart from added rows.

**D7. The explorer and writeup switch to `14d-r2`.**
The web build reads the `14d-r2` bundle. The writeup reports 57 races and
notes that the 46-race `14d` snapshot remains the prospective record
published on its date.

**D8. One designation table drives every opponent label.**
The bundle schema stays at version 2. A candidate's `party` remains a short
letter, so the locked `60d` and `14d` bundles, which hold only `D` and `R`,
regenerate byte-for-byte. The Python exporter and the web app share one table
that maps a ballot designation to a letter, a likely-winner name, and a
margin label:

| Designation | Letter | Margin label |
|---|---|---|
| Democratic | D | Dem. |
| Republican | R | Rep. |
| Unenrolled | U | Unenrolled |
| Independent | I | Independent |
| Workers Party | WP | Workers Party |
| Gulf War Veteran | GWV | Gulf War Veteran |

Only the two major parties get abbreviated margin labels. The others use the
full designation, so no new abbreviation is invented. The likely-winner,
incumbency option, receipts label, and chart side label take the
designation's name from the race's comparison candidate. The model still
codes a non-Democratic incumbent as `GOP_Incumbent`. Only the label changes:
`Unenrolled incumbent` and similar. The site build's comparison-party check
changes from "must be Republican" to "must have a table entry that agrees with
the target". The build reads `14d-r2` and its target from a single constant.
Alternative considered: a schema-3 bundle that carries the full designation
per candidate. Rejected, because it would make the locked bundles
unverifiable without a schema branch, and a fixed table covers the six
designations on the 2026 ballot.

## Risks / Trade-offs

- [Transcription error in the supplement] → The supplement is reconciled
  against the Secretary's page by a second read. A test asserts that the
  supplement and primary nominees together reproduce the 57 contested
  districts listed in the proposal.
- [Non-Republican opponents behave differently from Republicans, so pooled
  margins may be biased for these 11 races] → This is accepted because it
  matches the adopted definition. The writeup states that opponent party is
  not a predictor. If the backtest's segment for no-Republican races exists,
  its error is cited.
- [OCPF cannot resolve some new candidates] → Those races fall back to the
  no-money component and are listed in the run summary. If a missing
  `ocpf-cli` lookup is the cause, it is raised with the user rather than
  built here.
- [Readers confuse `14d` and `14d-r2`] → Both manifests and the explorer
  name the revision, and the `14d-r2` manifest records what it supersedes.
- [Paths refactored for revisions alter an existing snapshot by accident]
  → `publish_snapshot` already refuses differing bytes. The task list
  regenerates `60d`, `14d`, and both bundles and requires a "verified"
  result before `14d-r2` is created.

## Migration Plan

1. Land the supplement, builder, comparison rule, and revision paths. Verify
   that `60d` and `14d` regenerate as "verified".
2. Build `target_r2.csv` and `finance_14d_r2.csv`, and commit them.
3. From that clean commit, publish `snapshots/14d-r2` and
   `interactive/14d-r2`.
4. Switch the web build and writeup, then deploy.

Rollback: point the web build back at `14d`. The revision files are
additive, so nothing else needs reverting.
