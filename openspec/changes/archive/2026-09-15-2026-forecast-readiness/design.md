## Context

See `proposal.md` for motivation. The existing harness already supplies
rolling election-date folds, deterministic fits, posterior predictive draws,
dated finance predictors, composite variants, and committed backtest outputs.
It has no future target schema or forecast command: every normal scoring path
expects an observed response and the final published coefficients come from a
backtest fold trained only through the preceding election.

Variant and definition comparisons currently bootstrap individual paired race
errors. That is suitable for retaining race pairing but not the dependence
among races held in one statewide election. The six general-election folds are
the independent historical events relevant to November 2026; the 71 races in
the only Republican-president midterm cannot count as 71 independent
replications of that environment.

The adopted response also needs a forward-facing distinction. Historically,
`two_party_or_strongest` can identify the strongest non-Democrat from vote
totals. A forecast cannot. The target must lock a comparison candidate under
an outcome-blind rule and score that same declared matchup later.

## Goals / Non-Goals

**Goals:**

- Correct comparison uncertainty without changing race-weighted point scores
  or the rolling-origin fit schedule.
- Make every input to a 2026 prediction valid at a named forecast horizon.
- Produce a prediction for every validated target race, including races with
  incomplete finance, while disclosing which model produced it.
- Make the 60-day and 14-day forecasts immutable, reproducible, comparable,
  and prospectively scoreable.
- Preserve posterior draw alignment through chamber summaries and expose
  where a target extrapolates beyond historical support.

**Non-Goals:**

- No election-environment, polling, demographic, candidate-quality, or
  independent-expenditure predictor.
- No new model family, response definition, historical fold schedule, or
  attempt to calibrate a shared 2026 election shock that the current models do
  not represent.
- No forecast for uncontested races, special elections, or offices outside
  the Massachusetts House and Senate.
- No claim that a forecast composite selected here is permanently adopted
  after 2026.

## Decisions

### D1. Bootstrap election dates, keep the point score race-weighted

`compare.bootstrap_difference` will group the paired frame by `fold`, sample
fold keys uniformly with replacement, and concatenate all paired race errors
from each sampled key before computing the two RMSE values. A selected date
carries all its races and may appear repeatedly, which is the ordinary
one-stage cluster bootstrap. The observed point estimate remains the
difference between RMSE values over all paired races, so correcting its
uncertainty does not silently change the estimand.

The same primitive will serve variant comparisons, definition comparisons,
and variable-importance drop-one comparisons. Each row records
`resampling_unit=election_date`, `n_clusters`, the resample count, and the seed.
A segment with fewer than two date clusters gets no interval and an
`undecided` verdict; repeatedly drawing its one date would manufacture a
zero-width interval, not uncertainty.

Alternative rejected: average fold RMSE values and bootstrap those. It changes
the point estimand by giving a one-race special date the same weight as a full
general election. Alternative rejected: retain both race and cluster verdicts.
Two authoritative verdicts invite whichever one supports the desired claim;
the old race result remains only as superseded history.

### D2. General-election comparisons get deterministic leave-one-date-out rows

For each comparison containing general-election races, compute the same paired
point difference after dropping each general date in turn. Publish the omitted
date, remaining cluster and race counts, point difference, and whether its sign
differs from the full comparison. This is a sensitivity table, not another
confidence interval and not a second adoption rule.

The implementation derives date type from the paired races rather than from
calendar assumptions. A date containing only specials is not part of the
general-election leave-one-out table.

Alternative rejected: report only the minimum and maximum. The identity of
the influential election is the evidence a reader needs.

### D3. The target is a separate, response-free data product

Add `data/forecast/2026/target.csv`, keyed by a stable target identity derived
from election date, office, and district rather than a results-table ID that
may not exist yet. It carries the two declared sides of the forecast matchup,
incumbency, PVI inputs and coverage, timing, candidate-source provenance, and
finance availability, but no result columns.

A target builder will ingest the published `ma-election-db` 2026 primary
candidate roster and final primary results. These are the authoritative
pre-general sources because `ma-election-db` publishes its general-election
candidate artifact only after general-election results are available. Final
primary results are used only to identify the nominees; target-general vote
totals and winners remain unavailable and prohibited. The builder normalizes
office and district names through the existing election-data conventions,
joins 2024 PVI on the 2021 district map, and requires explicit review of
unmatched or duplicate races. When several non-Democrats stand, the target
locks the comparison candidate from pre-election information. The later score
uses the same candidate and does not replace that choice with the eventual
vote leader.

Alternative rejected: append placeholder 2026 rows to the historical race
table. That table's contract includes observed responses and result-derived
candidate fields, so placeholders would make leakage and missingness harder to
detect.

### D4. Forecasting fits the historical definition, not the target eligibility

Training first applies the selected historical definition and any component
restrictions to completed races strictly before the target date. The validated
target bypasses the historical definition's result-dependent admission logic:
its contested status and declared matchup were already fixed by the target
contract. The fitter then uses the existing `Fit.predict_draws` interface on
the response-free target features.

The forecast seed hashes the variant, component, definition, latest included
election date, target election date, and horizon. It does not include target
row order. Forecasting requires a clean worktree and records the current HEAD
as `code_commit`; generated outputs are committed afterwards, avoiding the
impossible requirement that a file contain the hash of the commit that first
contains that file.

Alternative rejected: reuse the 2024 backtest fit. It deliberately excludes
2024 and is evidence about past performance, not the full information set for
2026.

### D5. Compare a small, horizon-matched candidate grid

Register these missing ordinary variants:

- `baseline_timing_money_wide`: `PVI_N + incumbent_status + ballot_timing +
  money_logratio_wide`;
- `baseline_money_logratio_no_timing`: `PVI_N + incumbent_status +
  money_logratio_primary`;
- `baseline_money_logratio_no_timing_wide`: `PVI_N + incumbent_status +
  money_logratio_wide`;
- `baseline_no_timing`: `PVI_N + incumbent_status`, for a matching no-money
  fallback when the selected money structure omits timing.

The existing `baseline_timing_money`, `baseline_timing`, and dated baseline
money variants complete the grid. Within each horizon, compare timing versus
no timing on identical complete-finance races using the corrected clustered
interval and leave-one-general sensitivity. If the result is undecided, the
predeclared tie-break selects the no-timing structure: it uses fewer election-
level parameters and does not turn the single 2018 Republican-president
midterm into a reusable timing estimate by argument.

Alternative rejected: select the lowest pooled RMSE from every registered
variant. The holdout has already guided many earlier variants, and an open
search would add another layer of adaptive selection.

### D6. One operational composite per horizon supplies full coverage

Register `forecast_60d` and `forecast_14d` after the D5 comparison. Each routes
on the horizon-specific finance-completeness flag. The true component is the
selected dated-money variant and trains only on complete-money races. The false
component is its same-timing no-money counterpart and trains on all races
admitted by the definition. Both predict only the target rows routed to them.

The composite's published declaration freezes the chosen components and cites
the comparison output. A run fails unless the union of component predictions
equals the target exactly.

Alternative rejected: publish no result for an unmatched candidate. Complete
coverage is needed for a chamber view. Alternative rejected: encode missing
money as zero. The finance specification already distinguishes those facts.

### D7. Future OCPF collection starts from target candidates

Generalize the finance resolver and collector to accept the target's
candidate-grain view in addition to historical race candidates. All matching,
ambiguity, review, transaction accumulation, caching, and outcome-field
refusal remain shared. Store candidate snapshots at
`data/forecast/2026/finance_60d.csv` and `finance_14d.csv` with their exact
cutoffs and source cache identities.

A snapshot path is create-once. A rerun may verify byte equality but refuses
to replace different content. Corrections require a separately named revision
with a documented reason, so an input available later cannot leak into the
original horizon.

Alternative rejected: query current OCPF totals each time forecasts are
rendered. That makes a dated forecast irreproducible and eventually turns it
into a postdiction.

### D8. Forecast snapshots are directories, not mutable table cells

Use this layout:

```text
data/forecast/2026/
  target.csv
  finance_60d.csv
  finance_14d.csv
  snapshots/
    60d/
      manifest.json
      races.csv
      chamber_draws.csv.gz
      support_warnings.csv
    14d/
      manifest.json
      races.csv
      chamber_draws.csv.gz
      support_warnings.csv
```

The manifest holds file digests, model and component declarations, definition,
cutoffs, seed inputs, code commit, and training-table digest. `races.csv`
holds summaries, not observed outcomes. `chamber_draws.csv.gz` holds aligned
draw-level Democratic wins by office and combined contested target, making the
published aggregate distribution directly inspectable without committing the
larger race-by-draw matrix.

Publishing refuses a nonempty snapshot directory unless every generated byte
matches it. The 14-day run writes only its own directory.

Alternative rejected: append both horizons to one CSV. A partial rewrite can
silently alter the first forecast, and there is no natural home for its
manifest and draw-level aggregate.

### D9. Support checks disclose extrapolation but do not invent a correction

For each component, compare target numeric predictors with the min and max of
its actual training frame, record categorical training race counts and unique
election-date counts, and report any missing level. Finance checks use the
component's own horizon and completeness-restricted training set. Warnings are
published per race and summarized in the manifest.

The check does not clip values, widen intervals ad hoc, or reject an otherwise
valid forecast. Those would be new modeling choices without backtest evidence.

### D10. Preserve available dependence in aggregate draws

Within a fitted component, retain each posterior sample index across all target
races, so shared coefficient and group-effect draws move those races together.
Align independently fitted component draws by deterministic sample index when
summing seats. This preserves dependence the current models represent but does
not claim correlation between components or add an election-wide shock they do
not contain. The manifest states that limitation.

Alternative rejected: independently draw each race from its marginal win
probability. That discards even the shared posterior variation already
available and produces a needlessly narrow seat distribution.

### D11. Prospective scoring is a read-only join to locked forecasts

A separate score command reads certified results, joins them to a named
snapshot by target identity, and computes margin, interval, probability, and
aggregate metrics without calling the fitter. It records result provenance and
lists unresolved races. The original snapshot stays outcome-free and
unchanged; prospective results live beside it in a new `score/` directory.

Alternative rejected: feed 2026 into the rolling backtest before scoring the
published forecast. That answers how a newly refit model explains 2026, not how
the locked forecast performed.

## Risks / Trade-offs

- **Only six historical general-election clusters make intervals wide.** ->
  Publish the cluster count and leave-one-date sensitivity; wide uncertainty is
  the honest result, not a reason to return to race independence.
- **The 60-day snapshot date may already have passed when implementation
  begins.** -> Reconstruct it from dated OCPF transactions and cached source
  responses, refusing any source that cannot reproduce the historical
  accumulation rule.
- **The authoritative candidate roster may change through withdrawals or
  replacements.** -> Version the target roster and require each forecast
  manifest to digest the exact revision it used; never alter an existing
  snapshot.
- **Outcome-blind comparison-candidate selection may differ from the eventual
  strongest opponent.** -> Lock and disclose the rule, then score the matchup
  actually forecast rather than rewriting history.
- **A no-money fallback has a different training population from its money
  component.** -> Publish component-specific training counts and backtest
  component performance separately.
- **Aligned draws do not create a shared election shock.** -> State the
  limitation in aggregate output and leave an environment/random-shock model
  to a separate, backtested change.
- **Recomputed clustered verdicts will invalidate narrative conclusions.** ->
  Regenerate all comparison consumers in one migration and mark earlier
  race-bootstrap intervals as superseded.

## Migration Plan

1. Add cluster-aware comparison outputs and tests, then regenerate variant,
   definition, and importance comparisons without changing scored predictions.
2. Update writeups whose verdicts or uncertainty statements change, including
   the timing conclusion.
3. Register and score the matched 60-day and 14-day candidate variants, apply
   the declared tie-break where needed, and freeze the component declarations
   of `forecast_60d` and `forecast_14d`.
4. Build and validate the target roster, collect or reconstruct the 60-day
   finance snapshot, and review every unmatched candidate and support warning.
5. Generate and commit the 60-day forecast snapshot from a clean revision.
6. At the later cutoff, collect and freeze 14-day finance and publish a new
   snapshot without changing the first.
7. After certification, run prospective scoring against each locked snapshot.

Comparison migration is recoverable by checking out the prior committed CSVs
and writeups. Forecast snapshots are create-once; rollback removes only an
unpublished failed directory, never a committed horizon.
