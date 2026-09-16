## Context

The registry contains two different ideas called a baseline. `baseline` is the
stable reproduction of the original mapoli specification, while
`forecast_14d` and `forecast_60d` are the selected operational composites.
Each operational composite routes finance-complete races to a horizon-matched
receipts-log-ratio model and incomplete races to `baseline_no_timing`; neither
component uses `pres_elec`.

The first tenure experiment compared variants that retained
`incumbent_status` and added signed capped tenure to the original `baseline`.
It established the tenure derivation and measured incremental information, but
it did not test replacing incumbency status in the current forecast. The
existing scoring system can compare composites race by race and already
publishes component, tenure, clustered-interval, and leave-one-date evidence.

## Goals / Non-Goals

**Goals:**

- Give operational model-selection experiments a reproducible control that is
  distinct from the historical benchmark.
- Test the exact replacement proposed: one signed four-year tenure term instead
  of the three-level incumbency categorical.
- Preserve the operational control's information horizons, finance routing,
  race coverage, definition, and evaluation procedure.
- Make the replacement's symmetric party restriction and component-specific
  performance visible before any adoption decision.

**Non-Goals:**

- Re-estimating or changing the incumbent-tenure derivation.
- Searching the existing holdout for a new cap or party-specific tenure shape.
- Adding tenure alongside `incumbent_status`; that incremental question was the
  previous experiment.
- Automatically changing the selected 2026 forecast variants.
- Reinterpreting either tenure or incumbency coefficients causally.

## Decisions

### D1. Separate the operational control from the historical baseline

An experiment intended to affect a forecast will record a control manifest
before scoring. For this experiment it names `forecast_14d` as the primary
control, `forecast_60d` as the horizon-sensitivity control, the adopted
`two_party_or_strongest` definition, the finance-completeness route, the
general-election decision segment, and the repository revision containing the
declarations.

The variant named `baseline` remains unchanged. Its scores and the first tenure
experiment remain reproducible, but documentation will call them
"historical baseline" or "legacy-baseline experiment" when operational model
selection is discussed.

Alternative: rename `baseline` throughout the registry. Rejected because it
would churn published outputs and break stable references without changing the
underlying policy.

### D2. Mirror both operational composites and replace only incumbency

The no-money replacement component will contain `PVI_N` and
`tenure_cap4_signed`. The 14-day and 60-day money components will add their
current horizon's receipts log ratio. They will contain neither
`incumbent_status` nor either timing term.

Two challenger composites will use the same `money_complete` routing rule as
the controls. This makes the comparison a replacement of the incumbency
representation rather than a mixture of an incumbency change, a timing change,
a money-window change, and different missing-finance coverage.

Alternative: compare only the complete-finance component. Rejected because the
operational forecast promises a prediction for every target race and its
fallback is part of the model being challenged.

Alternative: include the hybrid status-plus-tenure arm. Rejected because that
was the structural question in the completed experiment; including it here
would blur the requested choice between status and tenure.

### D3. Keep the four-year shape fixed

The replacement uses the already declared signed cap-four predictor. It is zero
for open seats, positive for Democratic incumbents, negative for Republican
incumbents, and saturated after four years. The earlier two- and six-year
results do not authorize choosing a new cap for this test.

This one-column replacement is intentionally more restrictive than
`incumbent_status`: it forces equal-magnitude, opposite-party effects and makes
the effect approach zero near the start of service. Those restrictions are the
hypothesis being tested and will be stated in the results.

Alternative: use separate Democratic and Republican tenure slopes. Deferred to
a separately declared experiment because it answers whether a more flexible
tenure representation works, not whether the proposed -4 to +4 replacement
works.

### D4. Use the 14-day general-election comparison as the primary decision

The 14-day horizon is the final operational update and is pre-declared primary.
The decision row will be the general-election segment under the adopted
definition, matching the target use rather than allowing special-election error
to decide a general-election forecast. The pooled all-election row will remain
published for continuity.

The 60-day comparison tests horizon robustness. It cannot rescue a losing or
undecided 14-day result, and an isolated better point estimate at 60 days is not
a new primary hypothesis.

Alternative: treat both horizons as co-primary. Rejected because it creates two
opportunities to declare success and leaves the adoption rule ambiguous when
they disagree.

### D5. Verify route equality before computing a paired result

Pairing will continue to require the same election and fold on both sides. For
an operational-composite comparison it will additionally verify that both
sides used the same finance-completeness route and expected horizon. Any route
mismatch will fail the comparison with the affected race identified rather
than being summarized as a model difference.

Component-level rows will group the paired predictions into money and fallback
routes even though the concrete component variant names differ between the
control and challenger. This gives like-for-like component metrics without
pretending the components have identical predictor sets.

### D6. Adoption remains a separate operational change

The replacement is supported only if the primary clustered interval is wholly
in the challenger's favor, all required fits pass diagnostics, and the route
and horizon checks pass. An interval spanning zero or favoring the control
retains the current operational declarations. Party, tenure-band, fallback,
secondary-metric, and leave-one-date results explain the finding but do not
silently substitute a different primary rule.

Even a supported result will be documented as a recommendation and will not
rewrite `forecast_14d` or `forecast_60d` in this change. Promotion requires an
explicit follow-up so a completed experiment cannot alter a live forecast by
side effect.

## Risks / Trade-offs

- [The signed tenure column is too restrictive because party incumbency effects
  are asymmetric] -> Publish Democratic- and Republican-incumbent results and
  state the symmetry restriction as part of the tested hypothesis.
- [Most incumbents are already saturated at four years] -> Publish the
  pre-declared tenure bands and their election-date counts; do not infer shape
  from the pooled result alone.
- [Composite routing hides a weak fallback] -> Require route equality and show
  money and fallback comparisons separately.
- [The operational control changes during the experiment] -> Freeze its full
  declaration and revision before scoring; a new control requires a new
  experiment.
- [The 14-day primary choice understates performance needed at 60 days] ->
  Publish the full 60-day comparison as a declared horizon sensitivity without
  giving it a second path to adoption.
- [The new result appears to contradict the first tenure report] -> Label the
  old result as incremental against the historical baseline and the new result
  as replacement against the operational forecast; they answer different
  questions.

## Migration Plan

1. Add the frozen-control metadata and tenure-replacement component and
   composite declarations without changing existing variants.
2. Add route-integrity and experiment-role reporting, then verify it on focused
   fixtures before fitting models.
3. Reproduce the frozen operational controls and verify their existing scores
   are unchanged.
4. Score both replacement composites, publish the primary and sensitivity
   comparisons, and update the tenure and experiment-policy documentation.
5. Roll back by removing only the additive replacement declarations, control
   metadata, and replacement-specific outputs; the operational forecasts and
   historical baseline remain unchanged throughout.
