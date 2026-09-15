## Why

Three findings from the date-based folding change point at the same defect, and
none of them was acted on there.

**`national_env` is exactly collinear with `pres_elec` for nine of 23 folds.**
Every midterm in the record before 2017 had a Democratic president, so
`national_env = -(1 - pres_elec)` identically across those training windows ---
two parameters competing for one column. It becomes identified on 2017-10-17,
when a Trump-era special first enters the training window, and genuinely
identified only from 2018-11-06. Nothing refuses it: the harness tests a
predictor against a *grouping factor* and never against another predictor, so
`baseline_year_pres` is refused for this exact shape of collinearity while
`baseline_national_env` is not. That variant lost its verdict in the refold ---
undecided under three definitions of four, where it was decided under all
four --- and this is the most likely reason.

**The two timing booleans are one variable wearing two hats.** Restricted to
general elections, `~pres_elec` unambiguously means midterm, and there are
exactly three timing groups: presidential ballot (231 races), midterm under a
Democratic president (271), midterm under a Republican one (71). Intercept plus
`pres_elec` plus `national_env` is three parameters over three groups --- a
saturated model. They are not redundant, but they are also not naturally two
variables, and stating them as two hides both the saturation and the fact that
the third group is the single 2018 election.

**Special elections contaminate every timing figure.** No special election has
ever fallen on a presidential general date, so all 37 carry
`pres_elec = False`. They therefore receive a `national_env` value describing a
midterm-backlash electorate they are not: a March 2016 special is coded
identically to the 2014 midterm. For the five folds where `national_env` is
identified but 2018 has not happened, those miscoded races are the entire basis
for the estimate.

Restricting the scored population to general elections dissolves the first two
problems and isolates the third.

## What Changes

- **A `generals_only` definition**, admitting every race the adopted
  `two_party_or_strongest` definition does, but marking special elections
  **train-only**: they inform every fit and enter no holdout. This reuses the
  `scoreable` mechanism the train-only no-Democrat treatment already uses. The
  holdout falls from 413 races over 23 folds to **389 over 6**, all of them
  general elections.
- **BREAKING: a `ballot_timing` categorical replaces `pres_elec` and
  `national_env`** in the variants this change registers. Four levels, with
  `presidential` as the reference:

  | Level | Races | What it is |
  |---|---|---|
  | `presidential` | 231 | general election on a presidential ballot |
  | `midterm_dem_pres` | 271 | general election, midterm under a Democratic president |
  | `midterm_gop_pres` | 71 | general election, midterm under a Republican president |
  | `special` | 37 | special election --- train-only under `generals_only` |

  The fourth level exists because specials stay in training and must carry
  *some* timing value; coding them by the president's party is the defect above.
- **BREAKING: the confounding refusal extends to predictor-versus-predictor.**
  A variant carrying two predictors that are exactly collinear in a fold's
  training races is refused for that fold, with both named, exactly as a
  predictor spanned by a grouping factor already is. `baseline_national_env`
  will be refused on its first nine folds as a result, and that refusal is the
  published evidence for replacing it.
- **`midterm_gop_pres` is unobserved before 2018 and drawn from its prior.**
  Fold 2018-11-06 must predict a level its training window has never held. The
  level set stays fixed at four everywhere, the indicator is all-zero in
  training for the first three folds, and its coefficient comes from the prior
  --- which widens that fold's intervals rather than silently borrowing another
  level's estimate. Each fold publishes how many training races carry each
  level, so a prediction resting on a prior is identifiable as one.

Non-goals: no change to the fold schedule, the response definitions already
registered, the money predictors, PVI, or data collection. The existing
definitions stay registered and scorable, so the date-refold figures remain
reproducible.

**Depends on `date-based-folding-and-special-handling` being archived first.**
That change renames the requirement "Variants addressing the presidential-year
bias are registered" to "...presidential-date bias...", and the delta here
modifies it under the new name. Applied before that archive, this change's
delta targets a requirement the main spec does not yet carry. Every finding
above comes from that change's rescore, so the ordering is natural rather than
imposed.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `margin-model`: a `ballot_timing` categorical is registered and the
  timing-bias variants are restated in terms of it; the confounding refusal is
  broadened from predictor-versus-grouping-factor to include
  predictor-versus-predictor; a categorical level absent from a fold's training
  races is fit from its prior and disclosed rather than refused.
- `response-definition`: a definition may mark a race train-only on grounds of
  the race's own kind rather than its response, which is what `generals_only`
  needs; `generals_only` is registered and its holdout population stated.
- `model-scoring`: the `ballot_timing` segment becomes a predictor level set
  rather than a derived one, and a scoring run under `generals_only` reports a
  holdout of general elections only.

## Impact

**Code.** `src/legmodel/variants.py` (the `ballot_timing` derived categorical,
its `CATEGORICAL_LEVELS`/`CATEGORICAL_INDICATORS` entries, the new
predictor-versus-predictor check, and variants declaring it);
`src/legmodel/definitions.py` (the `generals_only` definition and its
`scoreable` rule); `src/legmodel/score.py` (the segment already exists as a
derived column and must not collide with the predictor of the same name);
`src/legmodel/fit.py` (per-fold disclosure of level counts).

**Published data.** A new definition adds cells to `scorecard.csv`,
`holdout_predictions.csv.gz`, `coefficients.csv`, `fit_diagnostics.csv`,
`definition_summary.csv` and `definition_comparison.csv`. Existing cells are
appended to rather than replaced --- the fold schedule is unchanged, so the
`fold_schedule` stamp still matches and no supersession applies.

**Documents.** `README.md` (two open issues close, and the timing discussion is
restated), `docs/variant_results.md`, `docs/scoring.md` (the `ballot_timing`
section gains a predictor sense), `docs/definitions.md` and
`docs/definition_result.md` (a sixth definition), plus a writeup for the
timing-categorical result.

**Not affected.** The precinct pipeline, PVI, campaign-finance collection, the
fold schedule, and the money and spend variants, which carry no timing term
beyond the `pres_elec` they inherit from `BASELINE_PREDICTORS` and which this
change leaves registered as they are.
