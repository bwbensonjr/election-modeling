## Context

See [`proposal.md`](proposal.md) for motivation.

The pieces this touches:

- `folds.py` is small and self-contained. `Fold` carries `year: int`, `train`
  and `holdout`; `build()` loops `ELIGIBLE_FOLD_YEARS` and slices on
  `election_year`. Everything downstream reads `fold.year`.
- `fold.year` is a *value*, not just a loop variable. It is written into
  `scorecard.csv`, `holdout_predictions.csv.gz`, `coefficients.csv` and
  `fit_diagnostics.csv` as the `fold` column, and it is hashed into
  `fit.seed_for(variant, fold, definition)`. Changing its type changes every
  seed and therefore every posterior draw, which is why nothing is
  bit-reproducible across this change even where the model is unchanged.
- A `Variant` is a frozen dataclass of `name`, `predictors`, `group_effects`,
  `priors`, `target_accept`, `tune`, `as_of`, `requires`. `requires` is the
  existing mechanism for "this variant is not fit on races lacking X" --- the
  money variants use it --- and it restricts training and holdout alike, via
  `variants.restrict()` at the top of `score_variant`.
- `score_variant` already handles a fold that cannot be fit: it catches
  `GroupedPredictorError`, records a refusal row, and continues. The
  three-arm work needs that path to survive composition.
- The race table already carries `election_date` as an ISO string
  (`race_training_set` spec), and the campaign-finance as-of logic already
  compares against each race's own `election_date` (`variants.py:858`), so no
  data collection changes.

## Goals / Non-Goals

**Goals**

- One fold per election date, training on everything strictly earlier, with
  the fold schedule derived from the table rather than enumerated.
- A composite variant that is two fits plus a routing predicate, expressible
  as a declaration and scoreable through the existing interface.
- The three special-handling arms scored on a shared race set so their
  comparison is paired.
- Ballot-timing segments reported three ways, so no published figure blends
  midterm generals with specials.

**Non-Goals**

- No change to sampler settings, priors, metrics, definitions, or the
  bootstrap comparison procedure.
- No attempt to preserve any published number. The schedule change reseeds
  everything; see D6.
- No general model-selection framework. `special_split` is a composite of
  exactly two components with a boolean predicate, not an n-way router.
- No decision on whether to drop `pres_elec`. That open issue
  (`README.md:438`) is re-measured under the new schedule but not acted on.

## Decisions

### D1. `Fold.key` is the election date; `Fold.year` goes away

`Fold` becomes `key: str` (the ISO `election_date`) plus `train` and
`holdout`. The `fold` column in every published output becomes the date
string.

*Why a string and not a `datetime`.* It is what the table already holds, it
sorts correctly lexicographically as ISO-8601, it round-trips through CSV
without a parsing step, and it hashes stably into `seed_for` --- a
`Timestamp` does not, since its `repr` has changed across pandas versions and
would silently reseed every fit on a dependency bump.

*Why rename the attribute.* `fold.year` holding `"2016-11-08"` is exactly the
kind of stale name this change exists to remove. A rename also makes the
compiler --- here, the test suite and an `AttributeError` --- find all nine
call sites rather than leaving them silently wrong.

*Alternative rejected:* keeping `year` alongside a new `date`. Two fold
identities is how the current confusion arose.

### D2. The schedule is derived, with the seed cutoff as the only constant

`build()` takes the admitted races, selects the distinct `election_date`
values `>= SEED_CUTOFF` (`"2014-01-01"`), sorts them, and builds one fold
each. `ELIGIBLE_FOLD_YEARS` is deleted.

*Why the cutoff is 2014-01-01 and not 2014-11-04.* It preserves the existing
seed window exactly --- the same 199 races of 2010 through 2013 --- so the
holdout population is the same 434 races the year schedule scored,
redistributed across 25 folds instead of 10. Moving the cutoff to the first
general election would additionally push the four early-2014 specials into
training, changing two things at once and making the refold's effect
unattributable.

*What the derived schedule drops.* The old `skipped` list existed to
distinguish "2019 had no races" from "nobody thought to score 2019". A
derived schedule cannot express that: a year with no races contributes no
dates and there is nothing to skip. The `skipped` return is kept for a
different case that still exists --- a date a *definition* empties --- and the
published schedule reports fold count and per-fold holdout sizes so a missing
election is visible as an absent date rather than as a silent gap.

### D3. A grouping factor must be at fold granularity, checked at declaration

`Variant.validate()` gains a check: every `group_effects` column must be
functionally determined by `election_date` within the table --- that is, each
of its levels must lie inside one election date. `election_date` passes;
`election_year` fails, naming itself and the fold granularity.

*Why refuse rather than warn.* A coarser grouping factor is not a modelling
choice with a trade-off; it silently estimates the holdout's own level from a
different population. `baseline_year` predicting 2016-11-08 would take its
2016 effect from three specials held six months earlier and apply it to 59
general races. That is worse than the current behaviour, not a variation on
it.

*Why this is checkable at declaration and not only per fold.* Unlike the
existing `GroupedPredictorError`, which genuinely depends on the fold's
training window, "is this factor coarser than a date" is a property of the
table. Checking it once gives a clear error at registration time.

*Consequence.* `baseline_year` and `baseline_year_pres` regroup to
`election_date`. Their prior stays `HalfNormal(5)` --- it was chosen as a
statement about residual swings in margin points between elections, which is
the same quantity --- and `target_accept` stays 0.95. The number of levels
rises from ~8 to ~25, most holding 1-3 races, which the partial pooling
handles and which the existing diagnostics will surface if it does not.

### D4. A composite variant is a `Variant` subtype, not a new concept in the harness

Add `CompositeVariant(name, components, route_on, description)` where
`components` maps a boolean value to a `Variant` and `route_on` names a
boolean column. `special_split` is
`{False: general_component, True: special_component}` routed on `is_special`.

Each component is an ordinary `Variant` and carries its own `requires`. The
general component adds a `not_special` column to its `requires` --- computed
as `~is_special` when the table is prepared --- which reuses the existing
restriction mechanism instead of adding a second one. That is what makes the
general component exclude specials from training *and* holdout with no new
code path.

`score_variant` gains a branch: for a composite, run the existing per-fold
loop once per component over that component's restricted races, then
concatenate. Because each component's holdout is already disjoint (one is
general-only, the other special-only by routing), concatenation is the join.
Coefficients and diagnostics are written with `variant` set to
`"special_split"` and a new `component` column, so a composite's two fits stay
distinguishable without a second variant name leaking into the scorecard.

*Alternative rejected:* registering the two components as ordinary variants
and stitching their predictions in `compare.py`. It puts the composition in
the comparison layer, so `score`, `importance` and `sweep` would each need
their own copy of the stitching.

*Why the special component's holdout is special races only.* The user's arm 3
routes by the race being predicted. The special component trains on
everything but is only ever asked about specials, so the general races in its
training set act as the prior information its 39 specials cannot supply on
their own.

### D5. The three arms, and what `special_pooled_plain` is

- `special_pooled_term` --- `BASELINE_PREDICTORS + ("is_special",)`. This is
  today's `baseline_special`, renamed.
- `special_pooled_plain` --- `BASELINE_PREDICTORS`. Identical to `baseline`.
- `special_split` --- the composite of D4.

`special_pooled_plain` is registered as its own name rather than reusing
`baseline` so the three arms read as a set in the registry and in the
published comparison. It is an alias in substance; the parity check in D7
asserts that it and `baseline` produce identical predictions, which is a free
regression test on the composite plumbing.

*The confounding hazard in the special component.* `is_special` is constant
within the general component's training races by construction --- there are
none --- but the general component does not declare `is_special`, so there is
nothing to refuse. The special component declares `is_special` and trains on
all races, so it is identified from the first fold onward (the seed window
holds specials from 2010, 2011 and 2013). The existing per-fold refusal path
covers it if a definition ever empties that set.

### D6. Everything is rescored; nothing is preserved

`fit.seed_for` hashes `f"{variant}|{definition}|{fold}"`, so a date-valued
fold reseeds every fit. Even `baseline` on the 2022 general --- whose training
races and predictors are unchanged --- draws a different posterior.

The unchanged-variant verification in `score.py` is therefore inapplicable for
this run. Rather than delete it, gate it: the run declares a schedule change,
which skips the comparison and prints the supersession notice instead. The
check stays live for every subsequent single-variant rescore.

*Why not preserve seeds by hashing the fold's year.* It would make the refold
partially bit-comparable, but at the cost of two folds in the same year
sharing a seed, and of encoding the very year-identity being removed.

### D7. Order of work, and what is verified before the expensive part

The refold and the composite are independent of each other and both are
cheap to get wrong expensively --- a full rescore is 25 folds x every variant
x every definition. So the sequencing is: land the fold change with its unit
tests, land the composite with a parity assertion
(`special_pooled_plain` == `baseline` race for race on a single fold), then
run one variant under one definition end to end and inspect the fold
schedule and a handful of training-set boundaries by hand, and only then
launch the full rescore.

The boundary case worth checking by hand is 2016-11-08: its training set must
contain the 2016-03-01 and 2016-05-10 specials and must not contain any race
dated 2016-11-08.

## Risks / Trade-offs

**The 19 special-election folds fit a full model to predict 1-3 races.** MCMC
cost scales with the training set, not the holdout, so each of those folds
costs about what a general-election fold costs. → Accepted; it is the point of
the change. Pooling is by race, so 26 races out of 434 cannot dominate the
pooled score, and the per-fold rows are already marked small-sample.

**`baseline_year` may sample worse with ~25 sparse levels than with ~8.** Most
new levels hold 1-3 races. → The variant's declared `HalfNormal(5)` prior and
`target_accept=0.95` are unchanged, and the existing diagnostics gate
(`RHAT_MAX`, `ESS_MIN`, divergence counts) is exactly the mechanism for
catching this. If it fails, that is a publishable result about grouping
granularity, not a blocker --- the spec already requires a hierarchical
variant be reported adoptable only if every fold's fits are clean.

**A composite variant is a second code path through fitting.** → Mitigated by
the parity assertion in D7 and by making each component an ordinary `Variant`,
so the fitting, prior, diagnostic and refusal machinery is shared rather than
duplicated.

**Every published number moves at once, including numbers not under test.**
The money results, the definition comparison and the variable-importance
report all change, and disentangling "the refold did this" from "the model
does this" will be harder afterwards. → The supersession notice states the
cause, and the old `data/models/` files stay in git history. The alternative
--- running both schedules --- doubles every run permanently to buy a
one-time diff.

**The `is_special` and `pres_elec` entanglement is measured, not removed.**
Even under arm C, the general model's `pres_elec` term is still estimated
from a record where no special ever fell on a presidential date. Arm C
separates the *populations*; it does not create the missing variation. → Out
of scope, and stated as such in the writeup rather than left implicit.

## Migration Plan

1. Land `folds.py` and the `fold.key` rename with unit tests; no rescore.
2. Land the grouping-granularity check and regroup `baseline_year` /
   `baseline_year_pres` to `election_date`.
3. Land `CompositeVariant` and the three arms; assert parity of
   `special_pooled_plain` against `baseline` on one fold.
4. Smoke-run one variant under one definition; inspect the schedule and the
   2016-11-08 boundary by hand.
5. Full rescore under the schedule-change gate. Commit regenerated
   `data/models/`.
6. Rewrite the affected documents against the new numbers, including the
   three "property of the calendar year" corrections, which are wrong
   independently of the refold.

Rollback is `git revert` of the code plus the data commit; the previous
`data/models/` files are recoverable from history and were produced by a
schedule the reverted code restores.

## Open Questions

- Whether `special_split`'s general component should also drop `pres_elec`.
  Removing specials removes every `pres_elec = False` special from its
  training set, which changes what that term is estimated from --- possibly
  enough to move the drop-one result in `README.md:438`. Deferred: it is
  measurable from the arm C fits once they exist, and answering it now would
  add a fourth arm before the first three have said anything.
- Whether the three-way ballot-timing segment should replace the `pres_elec`
  and `is_special` segment breakouts or sit alongside them. The spec requires
  the three-way split; keeping the existing two is redundant but harmless, and
  the scorecard's consumers are all internal. Decide when writing
  `score.py`'s segment table.
