## Why

**The fold schedule does not match the forecasting task.** `src/legmodel/folds.py`
trains on `election_year < Y` and holds out `election_year == Y`, so a fold is a
calendar year rather than an election. Two consequences follow. Predicting the
2016-11-08 general discards the 2016-03-01 and 2016-05-10 special results that a
real forecaster would have had in hand -- information loss, not leakage, but not
the task either. And several folds score unrelated dates as one event: fold 2017
blends four dates from July through December, fold 2020 blends five, fold 2014
scores a January special alongside the November general.

**Special elections sit inside the general-election evaluation without a decision
having been made.** All 39 special elections in the record carry
`pres_elec = False`, by construction -- none has ever fallen on a presidential
general date. So the `pres_elec = False` segment is a mixture of 313 midterm
generals and 39 specials, and specials are the model's worst segment by a wide
margin (24.76 RMSE and 0.708 interval coverage against a pooled 15.01 and 0.898).
They currently contribute to the pooled score, to the non-presidential bias
figure, and to the identification of `pres_elec` itself, none of it deliberate.

A third thing is worth correcting while the fold code is open. Three documents
state that `pres_elec` "is a property of the calendar year"
(`README.md:473`, `docs/variant_results.md:116`,
`docs/variable_importance.md:129`). It is not: `src/maprecinct/training.py:347`
computes it as `election_date in PRESIDENTIAL_ELECTION_DATES`, and the training
set honours that -- the 2016, 2020 and 2024 specials all carry `False` in
presidential years. The variable is correct; the prose generalises a data
coverage limitation into a definitional claim. The measured results that rested
on it stand, because the harness tests confounding per fold from the data rather
than from the claim.

## What Changes

- **BREAKING: folds are built from `election_date`, not `election_year`.** A fold
  holds out every race sharing one election date and trains on every race
  strictly preceding that date. The schedule goes from 10 fold years to 25 folds:
  6 general-election dates carrying 408 races, and 19 special-election dates
  carrying 26 races between them. Races before 2014-11-04 remain the seed window.
- **BREAKING: roughly 2.8x the fits per variant per definition.** Accepted
  deliberately: each special is now predicted from everything that happened
  before it, which is the point of the change.
- **`baseline_year` regroups from `election_year` to `election_date`.** Under date
  folds a per-year effect for the holdout year becomes partially observed -- the
  2016-11-08 fold would estimate the 2016 effect from three specials held six
  months earlier and apply it to 59 general races. Grouping on the date keeps the
  holdout level unobserved and drawn from the hyperprior, which is the honest
  forward-prediction posture the variant already claims. `baseline_year_pres`
  follows it, so the contrast arm stays a contrast.
- **Three special-election handling arms are registered and scored against each
  other**, replacing the single `baseline_special` question:
  - *Arm A* -- specials in training and holdout, `is_special` declared.
  - *Arm B* -- specials in training and holdout, no `is_special` term.
  - *Arm C* -- a composite of two fits: a general model that excludes specials
    from training and holdout entirely, and a special model fit on all races with
    `is_special` declared. Each race is predicted by the model matching its own
    `is_special` value.
- **A variant may be composite.** Arm C needs a variant that is two fits plus a
  routing rule rather than one predictor set, which the current declaration model
  (`name` plus predictors) cannot express.
- **Segment reporting separates specials from midterm generals.** The
  non-presidential bias figure is currently a blend of the two; it is reported
  three ways instead (presidential general, midterm general, special).
- **Everything is rescored and the old figures are marked superseded**, following
  the convention already in `model-scoring`. The three documents above are
  corrected to state the real structure: `pres_elec` is a property of the
  election date, and it is near-constant within a calendar year only because
  every special election in the record falls off the presidential date.

Non-goals: no new predictors, no change to the response definitions, no change to
data collection. The money and spend variants are rescored but not redesigned.

## Capabilities

### New Capabilities

None. Both areas of change fall inside existing capabilities' stated purposes.

### Modified Capabilities

- `model-scoring`: the rolling-origin requirement changes from year folds to date
  folds; the fold-schedule requirement is restated as a date schedule with a seed
  cutoff; segment breakouts gain the three-way presidential/midterm/special split;
  the `is_special` comparison requirement is replaced by a three-arm comparison
  including a composite arm that scores a different race set from the others.
- `margin-model`: a variant may be composite, declaring two fits and a routing
  predicate; a group effect declared on a calendar-determined factor must group at
  the fold's own granularity; the requirement covering presidential-year bias
  variants is reworded so that it rests on the measured per-fold confounding
  rather than on the incorrect claim that `pres_elec` is determined by the year.

## Impact

**Code.** `src/legmodel/folds.py` (rewritten -- `Fold.year` becomes a date,
`ELIGIBLE_FOLD_YEARS` becomes a derived date schedule); `src/legmodel/score.py`
(fold identity, the `pres_elec`/`is_special` segment split, per-fold rows, the
`folds_absent` / `folds_refused` bookkeeping keyed by date); `src/legmodel/fit.py`
(`seed_for` takes a date-valued fold, so every seed and therefore every published
number changes); `src/legmodel/variants.py` (composite variants, the three arms,
`baseline_year` regrouping); `src/legmodel/compare.py` (the small-sample rationale at
line 139 names the odd-year folds as the special-election evidence; under date
folds that becomes the special-date folds); `src/legmodel/importance.py` and
`src/legmodel/sweep.py` (both iterate folds).

**Published data.** Every file under `data/models/` is regenerated:
`scorecard.csv`, `variant_comparison.csv`, `holdout_predictions.csv.gz`,
`coefficients.csv`, `fit_diagnostics.csv`, `definition_comparison.csv`,
`variable_importance.csv`, `threshold_sweep.csv`, `coefficient_parity.csv`,
`definition_summary.csv`.

**Documents.** `README.md`, `docs/variant_results.md`,
`docs/variable_importance.md`, `docs/is_special_result.md`, `docs/scoring.md`,
`docs/money_results.md` -- every quoted metric moves, and the three
"property of the calendar year" sentences are wrong independently of the refold.

**Not affected.** Data collection, the precinct pipeline, PVI computation, and the
campaign-finance as-of logic, which is already keyed to each race's own
`election_date` and so needs no change to work under date folds.
