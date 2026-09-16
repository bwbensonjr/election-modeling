## Why

The current model treats every incumbent of a given party alike, although an
incumbent's early years may add more electoral advantage than later years.
Testing a tenure-aware term will determine whether distinguishing roughly one
year from four years improves out-of-sample margins without assuming that ten
and twelve years have meaningfully different effects.

## What Changes

- Derive uninterrupted incumbent tenure as of each election from
  `ma-election-db` candidate identities and election history, including special
  elections, career gaps, district changes, and source-history censoring.
- Keep the existing `incumbent_status` baseline unchanged and publish tenure as
  an additional, pre-election race attribute.
- Register a primary diminishing-returns tenure variant capped at four years
  and limited two- and six-year cap sensitivity variants.
- Score tenure variants against the baseline on identical rolling-origin folds,
  publish election-date-clustered uncertainty and leave-one-general-date-out
  sensitivity, and report where the effect is supported across tenure ranges.
- Derive the experimental field locally rather than block on an upstream schema
  change. Document the derivation for possible promotion to `ma-election-db`
  after its definition and usefulness have been validated.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `precinct-training-set`: Publish incumbent tenure derived from upstream
  candidate and election history with explicit continuity and censoring rules.
- `race-training-set`: Carry the race-level tenure value and its provenance into
  the committed modeling table.
- `margin-model`: Declare diminishing-returns tenure variants while preserving
  the existing baseline.
- `model-scoring`: Add the tenure question and its range-specific diagnostics to
  the comparisons that must be run and published.

## Impact

The change affects the local `ma-election-db` ingestion and training-table
build, the committed precinct and race datasets and schemas, model variant
declarations, tests, score outputs, and the tenure-results writeup. It adds no
runtime dependency and does not change `ma-election-db`; implementation needs a
sibling checkout only when rebuilding the committed data, as the current data
pipeline already does. Existing baseline results remain the comparison
yardstick and the operational forecast is not changed merely because a tenure
variant is tested.
