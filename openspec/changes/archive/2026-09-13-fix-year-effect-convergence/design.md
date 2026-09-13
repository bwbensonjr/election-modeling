## Context

See [`proposal.md`](proposal.md) for why. What follows is the state of the
code the fix has to land in, and the measurements that chose between the
candidate fixes.

**Where the knobs are today.** `legmodel/fit.py` builds every model as
`bmb.Model(variant.formula, data=prepared, family="gaussian")` and samples
with `DRAWS = 2000`, `TUNE = 1000`, `CHAINS = 4` as module constants. No
prior is ever passed, and `target_accept` is never set, so every fit runs
under bambi's auto-scaled priors at pymc's default `target_accept = 0.8`.
`Variant` (`legmodel/variants.py`) carries a name, predictors, a response and
`group_effects`; it has nowhere to put a prior or a sampler setting.
`Diagnostics` records `max_rhat`, `min_ess_bulk`, `min_ess_tail`,
`divergences`, `seed` and `n_train` --- nothing about how the sampler was
configured.

**What the auto-scaled prior actually is.** Printing the model bambi builds
for `baseline_year` on the earliest fold, under the adopted definition:

```
Intercept        ~ Normal(mu: 21.71,  sigma: 135.03)
PVI_N            ~ Normal(mu: 0.0,    sigma: 7.23)
incumbent_dem    ~ Normal(mu: 0.0,    sigma: 129.30)
incumbent_gop    ~ Normal(mu: 0.0,    sigma: 212.67)
pres_elec        ~ Normal(mu: 0.0,    sigma: 129.64)
1|election_year  ~ Normal(mu: 0.0,    sigma: HalfNormal(sigma: 135.03))
sigma            ~ HalfStudentT(nu: 4.0, sigma: 25.11)
```

The response's own standard deviation is 25.18 points. The diffuse priors on
the fixed effects are harmless --- those terms are identified by hundreds of
races --- but `HalfNormal(135)` on the between-year SD is a prior that
considers a 200-point swing between election years unremarkable, and it is
being asked to inform a quantity estimated from four groups.

The same printout settles the README's proposed fix: the sampler's variable
list is `[sigma, Intercept, PVI_N, incumbent_dem, incumbent_gop, pres_elec,
1|election_year_sigma, 1|election_year_offset]`. The `_offset` parameter is
the non-centred parameterisation. `bmb.Model` takes `noncentered=True` by
default and the project never overrides it. There is no centred funnel to
straighten.

**The collinearity, measured.** `pres_elec` is a property of the calendar
year, so a free per-year intercept spans it. Under the adopted definition it
varies within a year in exactly two years:

| Years in the table | 14 |
|---|---|
| Years where `pres_elec` varies internally | 2 (2016, 2020) |
| Races carrying that variation | 8 of 610 |
| Years in fold 2014's training window | 4 (2010-2013) |
| Years where `pres_elec` varies internally in that window | **0** |

In fold 2014 `pres_elec` *is* the 2012 indicator. Two parameters, one column.
From 2016 onwards, the 8 special elections held in a presidential year but
off the presidential ballot are the entire basis on which the fixed
`pres_elec` coefficient is distinguished from the year effects. The committed
diagnostics follow that exactly: 729 divergences and R-hat 1.18 on fold 2014,
392 and 1.09 on fold 2017, against 2 and 1.0036 on fold 2022, where the
training window holds ten years and both sources of variation.

**Which fix works, measured.** Each arm below was fit on the adopted
definition's training window for the fold, one shared seed across arms.
Divergence counts are not comparable to the committed scorecard, which used
the harness seeds; they are comparable *to each other*.

| Fold (groups) | as-is | `ta=0.95` | `ta=0.99` | scaled prior + `ta=0.95` | drop `pres_elec` | drop + scaled + `ta=0.95` |
|---|---|---|---|---|---|---|
| 2014 (4) | 123 | 120 | 16 | 16 | 105 | **0** |
| 2015 (5) | 113 | 55 | 7 | 0 | 83 | **0** |
| 2016 (6) | 157 | 173 | 3 | 3 | 76 | **0** |
| 2017 (7) | 64 | 8 | 0 | 4 | 86 | **0** |

No single remedy clears every fold, and the one the README proposed is not
among them. Raising `target_accept` alone is not even monotone --- on fold
2016 it made things worse (157 divergences to 173, R-hat 1.036, effective
sample size down to 141), which is the signature of a step size fighting a
geometry rather than a step size that is merely too large. Scaling the prior
alone clears 2015 but leaves 16 divergences on 2014, the fold where the
confounding is exact. Dropping `pres_elec` alone leaves 76 to 105 everywhere.

All three together reach **zero divergences on all four folds**, with R-hat
at or below 1.0030 and effective sample sizes three to eight times the as-is
figures (3599 to 4048, against 478 to 857).

That is why the change makes all three rather than picking the cheapest.

## Goals / Non-Goals

**Goals:**

- Make priors and sampler settings *declarable per variant and recorded per
  fit*, so a convergence remedy is a published property of a result rather
  than an edit to a module constant.
- Make the specification error --- a predictor spanned by the grouping factor
  --- a named failure rather than a divergence count.
- Re-score `baseline_year` under a corrected specification and publish
  whatever comes back.

**Non-Goals:**

- No general prior-specification language. Only what a group effect needs,
  plus a passthrough for anything else.
- No automatic remediation. The system does not retry a diverging fit at a
  higher `target_accept`; a setting is declared by a person and published.
- No change to the diagnostic thresholds themselves. `RHAT_MAX = 1.01`,
  `ESS_MIN = 400`, zero divergences stand.

## Decisions

### D1. Priors are declared on the variant, not set globally

`Variant` gains a `priors` mapping from term name to a prior declaration, and
`fit()` passes it to `bmb.Model(..., priors=...)`. A variant declaring
nothing gets exactly today's behaviour.

*Why on the variant.* The scale that is wrong for a year intercept is right
for the fixed effects, and a global override would silently move every other
variant's numbers. Scoping the declaration to the variant is what makes the
"every other variant is unchanged" guarantee checkable rather than hoped for.

*Alternative rejected: pass `auto_scale=False` and declare every prior.* That
puts five more declarations into every variant to fix one term, and it would
change `baseline`'s fits --- the one result in the project that is
cross-checked against `mapoli` by the parity test.

### D2. The group-SD prior is `HalfNormal(sigma=5)` on the points scale

Declared as a constant, not derived from the response, and stated in the
registry next to the variant.

*Why 5 and not the response SD.* The quantity is the standard deviation of
the *year* offsets after `PVI_N`, incumbency and the national environment are
accounted for --- a residual year-to-year swing. `HalfNormal(5)` puts about
95% of its mass below 10 points and its median near 3.4, which spans every
year swing in the historical record without licensing 100. Scaling to the
response's own 25.2 would be four times too loose for a quantity that is a
component of that spread, not the spread itself.

*Why a constant rather than `sigma = response_sd / 5`.* A prior that moves
with the training window makes two folds two different models. A constant is
a statement about margins in points, which is what the response is measured
in and will stay measured in.

*Alternative considered: `HalfStudentT`.* A heavier tail buys robustness for
a genuinely large year effect and costs sampling geometry in exactly the
regime that is failing. Rejected for now; recorded here so that a future
large year effect has a named next step.

### D3. `baseline_year` drops `pres_elec`

The year intercept contains `pres_elec` by construction. Keeping both asks
the sampler to split one column between two parameters on the evidence of 8
races, and on the early folds on the evidence of none.

*Consequence, stated rather than hidden.* `baseline_year` stops being nested
in `baseline`: it adds `(1|election_year)` *and* removes `pres_elec`. The
comparison machinery assumes nesting in its wording, and the spec delta makes
a non-nested comparison label itself.

*Alternative retained as a contrast arm.* `baseline_year_pres`, the same
variant keeping `pres_elec`, is registered and scored under the same
corrected prior and settings. If it converges and scores the same, the
collinearity cost nothing but sampling time and the writeup says so. If it
does not converge, that is the evidence for D3 rather than an argument for
it. Two registry entries is a cheap way to avoid asserting a modelling
decision.

*Note on `national_env`.* It is constant within an election year for the same
reason, so a variant combining it with a year intercept has the same defect.
This change registers no such variant, and the new check refuses one.

### D4. Sampler settings are declared per variant and recorded per fit

`Variant` gains optional `target_accept` and `tune`; `fit()` falls back to the
module defaults and writes the values *actually used* into `Diagnostics`, so
a defaulted fit and a declared one are equally reproducible from the CSV.
`fit_diagnostics.csv` gains `target_accept`, `tune`, `draws`, `chains` and a
`group_prior` string.

*Why record even the defaults.* The committed diagnostics today cannot
distinguish a fit that passed at `target_accept = 0.8` from one that needed
0.99. That distinction is the difference between a well-behaved posterior and
one the sampler was forced through, and it belongs in the published record.

### D5. The collinearity check runs per fold, against the training data

At fit time, for each group effect, each predictor is checked for variation
within the levels of that group *in that fold's training races*. Zero
within-group variation raises; variation confined to fewer than 30 races is
allowed but recorded as `separating_races` in the diagnostics.

*Why per fold and not on the full table.* Fold 2014 is exactly the case the
full table hides: `pres_elec` varies within a year across all 610 races, so a
table-level check passes while the fit that actually fails is the one whose
window contains none of that variation.

*Why raise rather than warn.* It sits alongside `UnidentifiablePredictorError`
and `LeakingPredictorError`, both of which refuse. A design matrix whose
columns are linearly dependent is the same class of error: the fit will
return numbers, and the numbers will describe a ridge.

*Why 30 as the disclosure threshold.* It matches `SMALL_SAMPLE = 10` in
spirit rather than in value --- a coefficient identified by fewer than 30
races out of 600 is being estimated on a thin slice and the reader should see
the count. The number is a reporting threshold only; nothing branches on it.

### D6. Adoption is conditional and the negative result is publishable

`baseline_year` is adopted only if every fold under every scored definition
passes diagnostics *and* the paired comparison against `baseline` still
favours it. The plausible bad outcome has a mechanism: divergences cluster in
the early folds, a diverging sampler explores the tails badly and tends to
produce wider predictive spread, and coverage rewards width. Part of the
0.898 to 0.927 coverage gain may be an artifact of the bad geometry.

If the gain does not survive, the README's open issue closes as *withdrawn,
with the reason*, and `baseline_national_env` stands unchallenged. The tasks
are written to produce a writeup either way.

## Risks / Trade-offs

- **The calibration gain does not survive clean sampling.** → Expected as a
  live possibility, not a failure mode. D6 makes the negative result a
  deliverable; the writeup states the mechanism above so the result is
  interpretable rather than merely disappointing.

- **Dropping `pres_elec` makes the headline comparison non-nested, and a
  reader takes the difference for the year effect alone.** → The spec delta
  requires the comparison to name both the added and the removed term, and
  the contrast arm `baseline_year_pres` bounds what the removal costs.

- **A declared prior is a researcher degree of freedom.** Choosing
  `HalfNormal(5)` after seeing which folds diverge is a decision made with
  knowledge of the outcome. → The prior is chosen on a stated scale argument
  about margins in points, fixed before rescoring, published in the registry
  and in `fit_diagnostics.csv`, and applied to every fold and every
  definition alike. It is not tuned per fold, which is the version of this
  that would actually invalidate the holdout.

- **Another variant's numbers move.** → The verification is a task, not an
  assumption: the other variants' rows are compared byte-for-byte against the
  committed CSVs and the run fails if any differ. The mechanism that would
  cause it --- a changed default, a reordered registry shifting a seed --- is
  exactly what that check catches.

- **Fold 2014 may not converge even so.** Four year groups is close to the
  floor for estimating a between-group SD at all. → If it does not, the
  honest outcomes are a higher declared `target_accept` for that variant
  (recorded, per D4) or reporting that the year effect is not fittable on the
  earliest folds. Neither is a reason to lower the diagnostic thresholds, and
  the thresholds are a non-goal.

## Migration Plan

The published outputs are append-and-replace per variant, so there is no
schema migration for the reader --- `fit_diagnostics.csv` gains columns, and
older rows are rewritten by the same run that adds them. `score.py` already
merges a rescoring into the committed outputs by definition and variant.

Rollback is `git revert`: the outputs are committed CSVs and the code change
is additive, with every new field optional and defaulting to today's
behaviour.

## Open Questions

- Whether the year effect should eventually be an ordered or autoregressive
  structure rather than exchangeable across years. Election years are ordered
  and adjacent cycles plausibly correlate, but that is a different variant
  with a different justification, and it cannot be evaluated until an
  exchangeable year effect samples cleanly. Deferred; it changes no
  requirement here.
