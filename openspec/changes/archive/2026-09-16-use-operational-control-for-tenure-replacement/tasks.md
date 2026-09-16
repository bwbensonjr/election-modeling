## 1. Freeze the operational experiment control

- [x] 1.1 Add a tenure-replacement experiment declaration that records `forecast_14d` as primary control, `forecast_60d` as horizon-sensitivity control, `two_party_or_strongest` as the definition, general elections as the decision segment, `money_complete` as the route, and the pre-experiment repository revision; verify registry tests fail if any recorded component, predictor set, horizon, or route disagrees with the frozen control.
- [x] 1.2 Add comparison metadata that distinguishes `operational_control`, `primary_challenger`, `horizon_sensitivity`, and `historical_benchmark`; verify output tests prevent `baseline` or the old incremental-tenure variants from being labelled the operational control or primary replacement result.

## 2. Declare the tenure-replacement models

- [x] 2.1 Register `tenure_replacement_no_money`, `tenure_replacement_money_14d`, and `tenure_replacement_money_60d` with the exact predictor sets, requirements, and as-of horizons in the margin-model delta; verify tests show every component contains `tenure_cap4_signed`, none contains `incumbent_status`, `pres_elec`, or `ballot_timing`, and each money component uses only its matching receipts window.
- [x] 2.2 Register `forecast_tenure_replacement_14d` and `forecast_tenure_replacement_60d` with the same `money_complete` route as their controls; verify routing tests show complete-finance and fallback races go to the corresponding challenger component exactly once and that current operational declarations remain unchanged.
- [x] 2.3 Verify the replacement's substantive constraints on representative inputs: open seats map to zero, one- and four-year incumbents remain distinct, longer tenure saturates, and equal-tenure Democratic and Republican incumbents have equal-magnitude opposite signs; also verify a censored lower bound below four years refuses the replacement.

## 3. Make operational comparisons like-for-like

- [x] 3.1 Carry a normalized `money` or `fallback` route and information horizon with each operational-composite prediction; verify paired-comparison fixtures fail with the election identified when control and challenger routes or horizons disagree.
- [x] 3.2 Add component-route segments and frozen-control fields to comparison output while preserving tenure bands, party segments, censoring summaries, secondary metrics, and empty/non-estimable segment rows; verify focused tests cover both routes, a zero-count fallback, sparse election-date clusters, and the signed-tenure symmetry disclosure.
- [x] 3.3 Extend the tenure experiment command or add a focused replacement command that scores the frozen controls and both challengers without overwriting unrelated results; verify command tests show the 14-day general-election row is primary, the 60-day row is sensitivity, and the old legacy-baseline comparisons remain addressable and labelled historical.

## 4. Run the operational tenure-replacement experiment

- [x] 4.1 Fit representative folds for all three replacement components and both composites; verify predictor knowability, horizon cutoffs, sampler diagnostics, coefficient publication, route coverage, and prediction output pass the existing model tests.
- [x] 4.2 Snapshot and reproduce `forecast_14d` and `forecast_60d` from committed inputs before scoring challengers; verify every pre-existing control prediction, score, component route, diagnostic setting, and coefficient summary is unchanged or document and resolve the exact drift before interpreting the experiment.
- [x] 4.3 Score both operational controls and both tenure-replacement composites under `two_party_or_strongest` on identical rolling-origin folds and shared races; verify outputs record seeds, priors, sampler settings, the frozen control revision, horizon, and route, with no censor or finance-coverage difference between each pair.
- [x] 4.4 Publish the 14-day general-election primary comparison and the 60-day horizon sensitivity with election-date-clustered intervals and leave-one-general-date-out results; verify the decision follows the pre-declared primary interval and that a favorable sensitivity or segment cannot replace an undecided or losing primary result.

## 5. Publish the corrected experiment policy and result

- [x] 5.1 Update the tenure results document to separate the legacy incremental test from the operational replacement test and report the primary verdict, horizon sensitivity, money and fallback components, tenure bands, party asymmetry, censoring, diagnostics, and leave-one-date evidence; verify every figure is traceable to a committed output and no text makes a causal claim.
- [x] 5.2 Update the project overview, scoring policy, and forecast-selection documentation to define the operational control as the default for adoption experiments and `baseline` as a historical benchmark; verify the recorded current predictor sets and horizons match the registry and the selected operational forecasts remain unchanged.

## 6. Final verification

- [x] 6.1 Run `uv run pytest`, `openspec validate use-operational-control-for-tenure-replacement --strict`, and `git diff --check`; verify the working-tree diff contains only intended planning artifacts, source, tests, committed model outputs, and documentation changes.
