## 1. Derive and publish tenure

- [x] 1.1 Add a local loader for the upstream candidate election history and derive uninterrupted tenure by stable candidate and predecessor-district identity; verify focused unit tests cover regular re-election, a special-election start, a career-gap reset, redistricting continuity, an open seat, and left censoring.
- [x] 1.2 Add ambiguity and consistency validation that refuses missing identities, multiple predecessor chains, and disagreement with upstream incumbent selection; verify each invalid fixture fails with the election and candidate identified and no name-based fallback.
- [x] 1.3 Attach `incumbent_tenure_years` and `incumbent_tenure_left_censored` to every precinct training row and update the documented precinct schema; verify tests show values are constant within races, use no current-race outcomes, and give open seats zero years with false censoring.
- [x] 1.4 Carry both tenure fields through the race rollup and update the race schema; verify rollup tests fail on within-race disagreement and reproduce the precinct value otherwise.
- [x] 1.5 Rebuild the committed precinct and race datasets with `uv run maprecinct training` and `uv run maprecinct races`, run the existing validation commands, and verify every left-censored modeled incumbent has a published lower bound of at least six years.

## 2. Declare tenure model variants

- [x] 2.1 Add signed capped-tenure derivations for two, four, and six years, including the censoring guard; verify unit tests cover Democratic, Republican, open-seat, below-cap, above-cap, and insufficient-censored-lower-bound cases.
- [x] 2.2 Register `baseline_tenure_cap4`, `baseline_tenure_cap2`, and `baseline_tenure_cap6` with the baseline predictors plus their respective derived term; verify registry tests show the four-year model distinguishes one from four years, equates ten and twelve years, and leaves `baseline` unchanged.
- [x] 2.3 Fit representative folds for all three tenure variants and verify predictor knowability, sampler diagnostics, coefficient publication, and prediction output pass the existing model tests.

## 3. Extend comparison reporting

- [x] 3.1 Add tenure bands for open seats, greater than zero to less than two years, two to less than four years, and at least four years, plus party-incumbent and censoring summaries; verify comparison tests cover boundary values, zero-count segments, and non-estimable clustered intervals.
- [x] 3.2 Add tenure comparison metadata identifying the four-year arm as primary and the two- and six-year arms as sensitivity checks; verify output tests prevent a sensitivity arm from being labelled the pre-declared primary result.
- [x] 3.3 Include the tenure question in the required comparison suite and verify its outputs contain paired clustered intervals, secondary metrics, fit diagnostics, shared race counts, tenure and party segments, censor exclusions, and leave-one-general-date-out results under every scored definition.

## 4. Run and publish the experiment

- [x] 4.1 Reproduce and score the unchanged baseline from the rebuilt tables; verify all pre-existing baseline metrics are unchanged or stop and document the exact source of any drift before running tenure comparisons.
- [x] 4.2 Score all three tenure variants under every scored definition and compare each with `baseline` on shared folds and races; verify committed score and comparison files can be regenerated from recorded seeds, priors, sampler settings, and committed inputs.
- [x] 4.3 Publish a focused tenure results document stating the primary verdict, cap sensitivities, tenure-band and party evidence, left-censoring coverage, diagnostics, and leave-one-date-out sensitivity; verify every reported figure is traceable to a committed output and an undecided or losing primary result explicitly retains the baseline.
- [x] 4.4 Update the project overview and modeling documentation with the experimental result and a ready-to-file upstream field definition and validation summary if promotion to `ma-election-db` is warranted; verify the operational forecast remains unchanged and no document claims a causal tenure effect.

## 5. Final verification

- [x] 5.1 Run `uv run pytest` and `openspec validate test-incumbency-tenure --strict`, then verify the working-tree diff contains only intended source, test, committed data, model-output, and documentation changes.
