## Why

The project can backtest models by election date, but it cannot yet fit a
selected model on all completed races and publish a reproducible forecast for
the known 2026 Massachusetts legislative contests. Its comparison intervals
also resample races independently, which overstates the evidence for predictors
whose value is shared by every race on an election date and makes the 2018-only
timing gain look more certain than it is.

## What Changes

- **BREAKING:** replace independent-race comparison intervals with paired,
  election-date-clustered intervals while retaining race-weighted point scores.
  Recompute affected verdicts and publish leave-one-general-election-out
  sensitivity so a conclusion driven by one election is explicit.
- Add a forward forecast workflow that reads a response-free target table,
  validates that every predictor was knowable at the forecast cutoff, fits on
  all eligible completed races strictly before the target election, and
  publishes one prediction per target race.
- Define and validate a committed 2026 target table containing the known
  contested State Representative and State Senate races, candidates,
  incumbency, 2024 PVI, ballot timing, finance completeness, and provenance.
- Support two locked information horizons: an initial 60-day forecast and an
  updated 14-day forecast. Register the missing 60-day timing-plus-money arm
  and matched no-timing money arms so ballot timing is selected under the
  clustered comparison rather than assumed.
- Add an operational composite that uses the selected money model where both
  candidates have complete OCPF data and an explicitly named no-money fallback
  elsewhere, producing full target coverage without treating an unmatched
  filer as zero.
- Extend OCPF collection to a future candidate roster that has no election
  result, preserving candidate-match review, caching, exact as-of dates, and
  the distinction between zero money and unavailable money.
- Publish immutable forecast snapshots carrying the model variant and
  component, definition, training cutoff, finance cutoff, input provenance,
  random seed, repository commit, point margin, predictive interval, and win
  probability. A later horizon creates a new snapshot rather than overwriting
  the earlier forecast.
- Add forecast-facing evaluation: Brier score and probability calibration,
  general-election and latest-fold summaries, office and incumbency segments,
  pre-election competitive bands, target-support warnings, and aggregate
  chamber draws that preserve dependence already present in posterior draws.
- Lock the 2026 forecast artifacts before results are available and provide a
  post-election scoring path so 2026 becomes a prospective test rather than
  another retrospectively selected holdout.

## Capabilities

### New Capabilities

- `election-forecast`: response-free target inputs, full-history fitting,
  horizon-specific and reproducible forecast snapshots, complete target
  coverage, aggregate outputs, and prospective scoring.

### Modified Capabilities

- `model-scoring`: cluster comparison uncertainty at the election-date level,
  add leave-one-election sensitivity and forecast-relevant probability and
  target-population diagnostics, and republish verdicts affected by the
  corrected uncertainty unit.
- `margin-model`: register horizon-matched timing and no-timing finance
  candidates plus a declared fallback composite that predicts races with
  unavailable finance without imputing it as zero.
- `campaign-finance`: collect cached, dated finance for a known future
  candidate roster before results exist and freeze comparable 60-day and
  14-day snapshots.

## Impact

- New forecast input and output files under `data/forecast/`, including a
  committed 2026 target roster and separately dated 60-day and 14-day
  snapshots.
- New forecast and prospective-score CLI commands in `src/legmodel/cli.py`,
  with fitting and publishing support in the modelling package.
- Changes to comparison and definition-comparison resampling, their tests, and
  the committed comparison tables and writeups; point RMSE values remain
  race-weighted, but intervals and decided/undecided labels may change.
- Additions to the variant registry, OCPF collection inputs, forecast-schema
  validation, target-support reporting, and model documentation.
- No new election-environment predictor, demographic feature set, model family,
  or change to the historical rolling-origin fold schedule. Those remain
  separate model-development questions after the forecast pipeline is honest
  and reproducible.
