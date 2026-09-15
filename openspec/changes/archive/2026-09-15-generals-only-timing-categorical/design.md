## Context

See [`proposal.md`](proposal.md) for motivation.

What the code already provides, and what it does not:

- **`CATEGORICAL_LEVELS` / `CATEGORICAL_INDICATORS`** in `variants.py` already
  do exactly what `ballot_timing` needs: a fixed level set imposed in
  `prepare()` rather than inferred per fold, expanded into explicit indicator
  columns so the reference level is chosen deliberately rather than
  alphabetically. `incumbent_status` is the existing instance. Adding a second
  categorical is a registry entry, not a mechanism.
- **`check_grouping()`** refuses a predictor spanned by a grouping factor,
  using `separating_races()` — the count of races that would have to be removed
  to leave the predictor constant within every level. That helper is already
  general: it takes a frame, a predictor and a *column to group by*. It does
  not care that the column is a declared group effect. Extending the check to
  predictor-versus-predictor is a second caller, not a second algorithm.
- **`scoreable`** is the train-only mechanism. `folds.build()` applies it to
  the holdout side only, so a race marked unscoreable trains every fold and
  enters none. `definitions.py` sets it for the no-Democrat train-only
  treatment. `generals_only` needs the same flag set on a different predicate.
- **`ballot_timing` already exists in `score.py`** as a derived *segment*
  column with three levels (`presidential_general`, `midterm_general`,
  `special`). This change introduces a *predictor* of the same name with four
  levels. They must not collide, and the spec now requires them to agree.
- **Nothing publishes per-level training counts.** `fit_diagnostics.csv`
  carries sampler settings, priors and separating-race counts, but not how many
  training races carried each categorical level. That is new.

## Goals / Non-Goals

**Goals**

- One declared timing categorical, replacing the two booleans in the variants
  this change registers.
- A generals-only scored population, with specials retained in training.
- Collinear fixed effects refused per fold, on the same terms and with the same
  reporting as a predictor spanned by a grouping factor.
- A fold that cannot observe a level still predicts it, with the reliance on
  the prior visible in the published outputs.

**Non-Goals**

- No change to the fold schedule, the money predictors, PVI, or data
  collection.
- No removal of `pres_elec` or `national_env` from the variants that already
  carry them. The existing registry stays scorable so the date-refold figures
  remain reproducible; `baseline_national_env` becomes the *refused* arm rather
  than a deleted one.
- No crossing of `generals_only` with the other five definitions.
- No attempt to fix the `pres_elec` drop-one finding. It is re-measured under
  the new predictor and reported, not acted on.

## Decisions

### D1. `ballot_timing` is a derived categorical with four levels, `special` among them

Computed in `derive()` from `is_special`, `pres_elec` and `PRESIDENT_PARTY`;
declared in `CATEGORICAL_LEVELS` with `presidential` first, so it is the
reference and every coefficient reads against a presidential ballot.

*Why a `special` level rather than dropping specials from the term.* Specials
stay in the training set (user decision), so every training row needs a value.
The three candidate treatments are: code them by the president's party, which
is precisely the defect this change exists to remove; give them the
presidential reference level, which asserts something equally false; or give
them their own level. Only the third is honest, and it has a side benefit —
under `generals_only` the `special` coefficient is estimated from 37 train-only
races and never used for a holdout prediction, so it absorbs their level shift
without letting them move the midterm estimates.

*Why not drop specials from training instead.* That was measured in the
previous change: `special_split`'s general component excludes them and beat the
pooled arms on presidential-date generals under all four definitions while
losing on midterm-date ones. It trades one segment for another. Keeping them
train-only preserves 37 races of evidence without letting them into a score.

*Alternative rejected:* an ordered or numeric timing scale. The three general
levels are not ordered in any way the model should assume, and imposing an
order is exactly the assumption `national_env`'s `-1/0/+1` coding smuggled in.

### D2. The collinearity check reuses `separating_races`, and runs pairwise over declared predictors

`check_grouping()` becomes two checks sharing one helper:

- predictor versus each declared `group_effects` column (today's behaviour);
- predictor versus each *other* declared predictor, over the expanded design
  columns, refusing when `separating_races(frame, a, b) == 0`.

*Why the expanded columns rather than the declared predictors.* A categorical
expands to several indicators, and it is an indicator that is collinear with
something, not the declared name. Checking `incumbent_dem` against `pres_elec`
is meaningful; checking `incumbent_status` against it is not well defined.

*Why pairwise and not a rank test on the design matrix.* A rank deficiency
tells you the matrix is singular; it does not tell you which two terms to
name, and the error message is the point. Pairwise exact collinearity covers
the case actually observed (`national_env` versus `pres_elec`) and produces an
error a reader can act on. A general rank check would also fire on the
all-zero indicator from D3, which must *not* refuse.

*Consequence, and it is the intended one:* `baseline_national_env` is refused
on its first nine folds. It keeps its 14 remaining folds and so still produces
a scorecard row — unlike `baseline_year_pres`, which is refused everywhere.
Its holdout count drops, and the paired comparison against the baseline
narrows to the races both still hold out. That is the published evidence.

### D3. An unobserved level is fit from its prior, and the counts are published

The level set is fixed, so `midterm_gop_pres` has an indicator column in every
fold. For folds 2014-11-04 through 2018-11-06 that column is all zero in
training. Bambi will happily fit it: the likelihood is flat in that
coefficient, so the posterior is the prior.

*Why this must not trigger D2's refusal.* An all-zero column is constant, and a
naive collinearity test would flag it against the intercept. The pairwise check
is therefore defined over pairs of *declared predictors* and skips a column
with no variation in training — that case is D3's, and it is disclosed rather
than refused.

*What makes it honest.* `fit_diagnostics.csv` gains a `level_counts` field:
the training-race count per categorical level, per fold. A zero there is the
signal that the corresponding coefficient is a prior draw. Fold 2018-11-06
will show `midterm_gop_pres: 0` and predict 71 races on it.

*The prior matters more than usual here.* An unobserved level's posterior *is*
its prior, so bambi's auto-scaled default would be doing real work on 71 races
unexamined. The variant declares an explicit prior for the timing coefficients
on the same reasoning that `baseline_year` declares `HalfNormal(5)` rather than
inheriting `HalfNormal(135)`.

### D4. `generals_only` sets `scoreable`, and is registered beside the adopted definition

It copies `two_party_or_strongest` and additionally sets
`scoreable &= ~is_special`. Race eligibility, response column, write-in
threshold and no-Democrat treatment are unchanged, so any difference between
the two is attributable to the holdout population alone.

*Why a definition and not a variant `requires`.* The definition layer is what
the spec says decides "the races eligible for training and holdout". A variant
restriction would make the holdout population vary by variant within one
scorecard, which is harder to read and makes paired comparisons narrower than
they need to be. `no_dem_train_only` is the existing precedent for exactly this
shape.

*What it costs.* Six folds instead of 23, 389 holdout races instead of 413. The
comparison against `two_party_or_strongest` runs on the 389 races both hold
out, under the existing definition-comparison procedure, which already reports
the races exclusive to each side — the guard against crediting a definition for
declining to score its hardest segment.

### D5. The segment and the predictor share a level set

`score.ballot_timing()` currently returns three levels for the segment. It
becomes the same four-level function the predictor uses, and the segment reads
the prepared column rather than recomputing it.

*Why they must agree.* The spec now requires a segment row and a coefficient
describing the same population to be labelled the same. Two functions named
`ballot_timing` returning different level sets is the kind of divergence that
produces a writeup where a coefficient and a segment quietly describe different
races.

*Migration note:* `midterm_general` becomes `midterm_dem_pres` +
`midterm_gop_pres`, and `presidential_general` becomes `presidential`. The
scorecard's `ballot_timing` rows change names and split one row into two. Only
this change's own documents consume them so far.

### D6. What gets registered, and what it is compared against

- `baseline_timing` — `PVI_N + incumbent_status + ballot_timing`. The direct
  replacement for `baseline`, differing by one declared term.
- `baseline_timing_money` — the same plus `money_logratio_primary`, so the
  adopted money variant has a timing-categorical counterpart.

Both are scored under `generals_only` and under `two_party_or_strongest`, so
the timing question and the population question are separable rather than
confounded in a single arm.

## Risks / Trade-offs

**Six folds is few, and three of them cannot observe the third level.** →
Accepted and disclosed rather than mitigated; it is a fact about a record
holding one Republican-president midterm. The level counts published per fold
are what stop it being invisible, and the widened 2018 intervals are the
honest expression of it.

**Fold 2018-11-06 predicts 71 races on a prior-drawn coefficient.** That fold
is also the most informative one for the question the term exists to answer. →
The alternative considered was a 2-level fallback for folds that cannot support
3, which was not chosen: it would make different folds fit different models,
and a comparison across folds would then be measuring the fallback as much as
the term. Reporting a wide interval is preferable to reporting a narrow one
from a different model.

**The `special` coefficient is estimated from train-only races and never
scored.** A reader may take it for a special-election effect that has been
validated. → It has not been, and the writeup must say so. Under
`generals_only` nothing in the holdout carries that level, so the coefficient
is a nuisance parameter absorbing a level shift, not a finding.

**Refusing `baseline_national_env` on nine folds changes its published
numbers.** Its holdout shrinks and its comparison against the baseline narrows
to shared races. → That is the intended result, and the existing paired
procedure already drops a race missing from either side. The previous figures
stay in git history and the writeup states why they moved.

**Two `ballot_timing` definitions could drift apart during implementation.** →
D5 makes the segment read the prepared predictor column rather than recompute
it, so there is one function and one level set by construction.

## Migration Plan

1. Land `ballot_timing` as a derived categorical with its level set and
   indicators; verify the four levels over the committed table.
2. Land the predictor-versus-predictor collinearity check; verify it refuses
   `baseline_national_env` on exactly the nine folds identified, and refuses
   nothing that was previously fit.
3. Land per-fold level-count disclosure in the diagnostics.
4. Land `generals_only`; verify 6 folds, 389 holdout races, 37 specials
   train-only, and that every special appears in the training sets.
5. Register `baseline_timing` and `baseline_timing_money`; score under both
   definitions with `--append`, since the fold schedule is unchanged and the
   `fold_schedule` stamp still matches.
6. Compare, and write up.

Rollback is `git revert` plus restoring `data/models/` from history; the new
definition's rows are additive, so reverting removes cells rather than
corrupting existing ones.

## Open Questions

- Whether `generals_only` should eventually become the adopted definition. It
  cannot be decided here: the comparison against `two_party_or_strongest` runs
  on 389 shared races and says nothing about the 24 specials only the latter
  scores. Deferred until the timing result is in.
- What prior the timing coefficients should declare. D3 establishes that an
  explicit one is needed because an unobserved level's posterior is its prior;
  the scale is a judgement about plausible timing shifts in margin points and
  is best fixed while looking at the fitted levels from the folds that do
  observe all four. Does not change the task breakdown.
