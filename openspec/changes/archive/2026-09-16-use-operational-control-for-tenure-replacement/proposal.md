## Why

The project still uses the original `PVI_N + incumbent_status + pres_elec`
variant as the control for some experiments even though the selected
operational forecasts now use horizon-specific money composites without
`pres_elec`. A new predictor should be judged primarily against the model it
would replace in production, while the original baseline remains useful only
as a stable historical benchmark.

## What Changes

- Define the selected operational forecast at the relevant information horizon
  as the default primary control for model-improvement experiments.
- Preserve the original `baseline` as a secondary historical yardstick and
  require reports to distinguish it from the operational control.
- Freeze and publish the control variant, definition, information horizon,
  routing rule, and code revision before an experiment is scored.
- Register a four-year signed-tenure replacement for each component of the
  current 14-day and 60-day operational composites. The challenger replaces
  `incumbent_status`; it does not add tenure alongside it or reintroduce
  `pres_elec`.
- Compare the current and tenure-replacement composites on identical folds,
  races, finance routing, and horizon-matched inputs, with the 14-day result as
  the pre-declared primary decision and 60 days as a horizon sensitivity.
- Publish complete-finance and fallback component results, tenure-band and
  incumbent-party evidence, diagnostics, and leave-one-general-date-out
  sensitivity. An undecided or losing primary comparison retains the current
  operational model.
- Retain the completed legacy-baseline tenure experiment as historical evidence
  rather than presenting it as the operational model-selection result.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `model-scoring`: Make the frozen operational forecast the primary experiment
  control, distinguish the legacy baseline, and declare the tenure replacement
  comparison and adoption rule.
- `margin-model`: Declare horizon-matched tenure-only components and composites
  that mirror the current operational routing while replacing three-level
  incumbency.

## Impact

The change affects model variant declarations, experiment orchestration,
comparison metadata and tests, committed model outputs, and the scoring,
forecast-selection, and tenure-results documentation. It reuses the committed
tenure fields and current campaign-finance inputs, adds no dependency, and does
not change the operational forecast merely because the replacement is tested.
