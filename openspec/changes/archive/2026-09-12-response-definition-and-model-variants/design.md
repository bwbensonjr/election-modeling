## Context

See `proposal.md` for motivation. The constraints that shape the approach:

- **The published tables already encode one answer to the open questions.**
  `data/precinct/ma_precinct_training_set.csv.gz` and
  `data/race/ma_race_training_set.csv.gz` apply the pre-change rule at build
  time: `num_candidates >= 2` on ballot lines decides eligibility, every named
  candidate enters the denominator, and races with no Democrat are kept under
  a negated convention. Excluded races leave no trace in the table beyond a
  row in `data/reports/training_excluded_races.csv`. Any alternative
  definition therefore currently requires a rebuild.
- **The write-in flag exists and is not yet read.**
  `ma-election-db`'s `ma_general_election_candidates.csv.gz` carries
  `is_write_in` and `party_role`. `maprecinct.config.general_candidates()`
  already exposes the file; `training.py` reads only the summaries. So Q2
  needs no new source, only a join the pipeline does not currently make.
- **Write-ins are rare and nearly always singular.** Of the 1,651 legislative
  elections in the window, 1,627 have no write-in candidate, 21 have one, and
  3 have two. Exactly one race has two write-ins where either reaches 2% of
  named-candidate votes. Threshold logic can therefore be exact rather than
  approximate without costing anything.
- **Write-ins enter the two decisions by different routes today.** Eligibility
  comes from the summary's ballot-line count; the denominator comes from the
  precinct returns, where a named write-in appears as an ordinary
  `row_kind == "candidate"` row. 28th Middlesex 2013 is the illustration:
  Hanlon's 1,202 write-in votes sit in the 3,602-vote denominator but are not
  the comparison candidate, giving `dem_margin` = +14.13 where excluding them
  gives +21.2 and treating the write-in as the comparison gives +1.68.
- **The scoring harness assumes a fixed race set.** `legmodel.compare` pairs
  on `election_id` across two variants' holdout predictions, which is sound
  when both variants see the same races and meaningless when they do not.
- **A year effect is not identified for a holdout year.** Rolling-origin
  folds predict a year absent from training, so an unpooled per-year intercept
  has no fitted value for the year being predicted. This constrains how Q4 can
  be specified, and is the reason a national-environment term is in scope.
- **The holdout is small.** 424 races, 24 of them special, and the two-party
  restriction cuts that to 346 and 22. The differences under test are
  fractions of an RMSE point on that base.

## Goals / Non-Goals

**Goals:**

- Rebuild the training tables exactly once, and settle all three data
  questions against that one rebuild.
- Keep every race the pipeline can construct in the published table, so a
  losing definition can be revisited without recollection.
- Make a comparison across definitions honest about the three things that
  change at once: the holdout race set, the training race set, and the
  response itself.
- Specify the Q4 variants so that each is actually usable for a forward
  prediction of 2026, not only for backfitting the observed swing.

**Non-Goals:**

- No abstraction over response families. A definition names a response column
  on the race table; it does not introduce a link function, a transformation,
  or a likelihood change.
- No per-definition caching of fits. The run grows but stays in minutes.
- No attempt to score the two responses against one another on a common
  scale. Where the response differs, the comparison discloses the shift rather
  than trying to normalize it away.
- No change to the fold schedule, metric definitions, or pooling rule.

## Decisions

### D1: A definition is a selection over one table, not a build-time filter

The training tables become definition-neutral: they carry every race the
pipeline can construct at the most permissive eligibility rule, plus the flags
and vote components by which any stricter rule excludes a race. A definition
is a named record in a registry in `legmodel`, parallel to the existing
variant registry, holding an eligibility predicate, a response column, a
write-in threshold, and a no-Democrat treatment.

*Why.* The README's own sequencing note is the argument: each of Q1 through Q3
invalidates the published table and scorecard, and deciding them separately
means rebuilding three times. Making them a selection collapses three rebuilds
into one and makes the sweep over thresholds cheap.

*Alternative considered: a table per definition.* Rejected. It multiplies the
committed data, makes the intersection of two holdouts an inter-file join, and
makes revisiting a decision a collection run rather than a flag.

*Alternative considered: filtering in the pipeline and passing a flag.*
Rejected for the same reason -- the `maprecinct` stages would have to run once
per definition, and the fetch cache and areal interpolation are the expensive
parts.

### D2: The permissive rule is "two candidates counting any named write-in"

The precinct table's build-time filter loosens from `num_candidates >= 2` on
ballot lines to two or more candidates counting every named write-in at any
share. This is the 0% row of the README's threshold table, admitting 16 races
that are currently excluded. Every stricter threshold, including the current
behavior, is then a downstream filter over the published table.

*Why.* The loosest admissible rule is the only one that is a superset of all
the others. Choosing anything stricter would force a rebuild to test a looser
one.

*Consequence.* The loosened rule makes 16 further races contested, taking the
contested count from 623 to 639. Six of those 16 are all-Democratic fields --
a ballot-line Democrat against a Democratic write-in -- where `dem_margin` has
no non-Democratic comparison candidate, so the pre-existing "no usable
two-candidate contest" rule still excludes them. The published tables
therefore grow from 623 races to **633**, and
`data/reports/training_excluded_races.csv` shrinks by 10. The added races are
not in any definition's holdout unless its threshold admits the write-in that
made them contested.

### D3: One threshold governs eligibility and the denominator together

A definition's write-in threshold is a share of named-candidate votes computed
at race grain from district totals. A write-in at or above it is a candidate
in every respect: it counts toward the contested test, it enters the response
denominator in every precinct, and it is eligible to be the comparison
candidate. A write-in below it is none of those things, and its votes leave
the denominator.

*Why.* The current split -- ballot lines decide one, precinct returns decide
the other -- is what makes 28th Middlesex 2013 ambiguous. A single rule
applied in both places is the only way the question has one answer.

*Note on direction.* Excluding write-ins from the denominator moves *away*
from `mapoli`'s reference value, not toward it. The reference treats the
write-in as the comparison candidate. So the threshold rule is not chosen to
reproduce the reference; the rollup validation gains a category for races
whose candidate set the threshold changes, reported as deliberate divergence
rather than as a defect.

*Threshold is race-level, not precinct-level.* A write-in that clears the
threshold district-wide is admitted in every precinct of that race, including
precincts where it drew no votes. Deciding per precinct would make the
comparison candidate vary within a race, which the existing spec already
forbids for other reasons.

### D4: Threshold-dependent quantities are recoverable from published columns

The precinct table carries, per row, `dem_votes`, `gop_votes`,
`opponent_votes`, `candidate_votes` (all named candidates), `write_in_votes`
(all named write-ins), and `top_write_in_votes`. A companion race-level
candidate roster, `data/race/ma_race_candidates.csv.gz`, carries one row per
`(election_id, candidate)` with party, `is_write_in`, district votes, and
share, so the admitted set at any threshold is exact.

For the single race with two write-ins where either clears 2%, the roster plus
the already-committed `ma_precinct_legislative_results.csv.gz` resolve the
denominator exactly; no approximation from `top_write_in_votes` is used. The
build asserts that no race requires per-precinct detail beyond what the
published columns provide, and names the race if one does.

*Why a roster rather than a column per threshold.* Five thresholds times two
responses is ten columns that go stale the moment a sixth threshold is worth
testing. The roster is the underlying fact; the thresholds are queries on it.

### D5: The two-party response is an added column, not a replacement

`dem_margin_two_party` is published alongside `dem_margin` at both grains,
missing where either major party is absent. `major_party_race` marks the 517
races carrying both. Q1's restriction is the definition that filters on that
flag and names the two-party column as the response.

*Why not replace.* The two responses answer different questions and the
comparison between them is the point of Q1. Publishing both also makes the
response-shift disclosure (D8) a column subtraction rather than a re-derivation.

*Rolled up from summed votes, not averaged.* The race-grain two-party margin
sums each precinct's Democratic and Republican votes and divides, matching how
`dem_margin` and `PVI_N` are already rolled up. An average of precinct
two-party margins would weight small precincts equally with large ones.

### D6: The no-Democrat treatment is three declared options, all scored

A definition declares one of: **keep** (rows in training and holdout, with
`no_dem_candidate` available as a predictor), **exclude** (absent from both),
or **train-only** (in training, absent from the holdout and from every
metric). The two-party definition reaches **exclude** by construction rather
than by declaring it.

*Why train-only is worth having.* The segment's failure is a *prediction*
failure -- 28.35 RMSE, 36% coverage -- not evidence that the 13 races carry no
information about the PVI-to-margin relationship. Dropping them from scoring
while keeping them in training tests exactly that, and the seed window is
small enough that discarding races has a real cost.

*Reporting guard.* A treatment that removes those races from scoring lowers
pooled RMSE mechanically. The spec requires that result be reported as removal,
not as improvement, and the writeup states the pooled figure both ways.

### D7: The README's sub-question gets its own definition

`two_party_or_strongest` keeps the two-party response where a Republican ran
and, where none did, compares the Democrat against the strongest non-Democrat
on that pair's own two-candidate denominator. This admits the 93 races where a
Democrat faced a non-Republican -- 74 unenrolled, 8 Green-Rainbow, 4
Libertarian, 3 Pirate, 2 United Independent, 2 Workers Party -- that the
strict two-party definition drops.

*Why it is worth a definition rather than an assumption.* Dropping 106 races
is an 18% cut to the holdout, and the README explicitly declines to assume the
restriction is free. This definition recovers 93 of the 106 while keeping the
response two-candidate, so the denominator mismatch Q1 exists to fix stays
fixed.

### D8: Cross-definition comparison reports three things, not one

`legmodel compare-definitions A B` produces:

1. **Paired difference on the intersection.** Races in both holdout sets,
   paired bootstrap over those races, an interval, and the decided/undecided
   label -- the same machinery `legmodel compare` already uses.
2. **Exclusive sets.** What each definition admits that the other does not,
   with counts, reasons, and each definition's own score over its exclusive
   races.
3. **Response shift.** Over the intersection, the per-race difference between
   the two definitions' response columns, summarised as median, tail, and the
   count moving more than one point. Zero by construction when both
   definitions name the same response.

The report states plainly that the two models also trained on different race
sets, so the paired difference isolates neither the response nor the
eligibility rule on its own.

*Alternative considered: refit one definition's model and score it on the
other's response.* Rejected. It produces a cleaner-looking isolation of the
response change, but the resulting number describes a model nobody would ship,
and the training sets still differ.

*Alternative considered: reweighting the narrower holdout to the wider one.*
Rejected as unjustifiable on 346 races with no principled weights.

### D9: A year effect is hierarchical, and its holdout year draws from the hyperprior

`baseline_year` adds a per-year intercept with a shared prior on the year
effects. For a fold predicting year `Y`, `Y` has no fitted effect, so its
posterior predictive draws take the year effect from the year-level hyperprior
-- the distribution the observed years imply for an unobserved one. The point
prediction is therefore close to the baseline's and the interval is wider.

*Why not fixed per-year effects.* Unidentified for the holdout year. Bambi
would either fail or silently fall back to the reference year, which is worse
than failing.

*What this can and cannot do.* It cannot shift the holdout year's mean, so it
will not by itself fix the ±6.4/±2.7 bias. It is in scope because it
calibrates: if year-to-year variation is the source of the bias, the wider
interval should raise coverage even where RMSE is unchanged. That distinction
is exactly what the coverage metric is for.

### D10: The national-environment term is signed by the party holding the presidency

`baseline_national_env` adds a term that is `-1` in a non-presidential year
under a Democratic president, `+1` in a non-presidential year under a
Republican president, and `0` in a presidential year. Over the window this is
negative for 2010 through 2015 and for 2021 through 2023, positive for 2017
through 2019, and zero in 2012, 2016, 2020 and 2024.

*Why this rather than a year dummy.* It is the substantive story behind a
midterm swing -- the electorate moves against the president's party -- and,
unlike a year effect, it is known before the election. It is the only Q4
variant that can shift a holdout year's mean, and the only one usable for a
2026 forward prediction, where it would be positive.

*Caveat to state in the writeup.* It is one number fit on eight non-presidential
years, of which the sign is negative in six. It is close to being a
non-presidential-year intercept with the 2017-2019 folds flipped, and the
writeup should say so rather than over-reading a coefficient.

### D11: `baseline_pres_incumbent` is the third Q4 variant

An interaction between `pres_elec` and `incumbent_status`. The hypothesis is
that the incumbency advantage is not the same size in a presidential-year
electorate as in a midterm one, and that a single additive `pres_elec` term
forces one estimate onto both.

### D12: The matrix is pruned deliberately

The full cross of definitions and variants is not run. Definitions are
compared under `baseline` only; variants are compared under the adopted
definition and under `current`, so a variant result is not an artifact of the
definition chosen. The threshold sweep runs under `baseline` at each candidate
threshold. Concretely this is on the order of forty rolling-origin runs of ten
folds, a few hundred MCMC fits on at most 600 rows.

*Why prune.* The full cross is neither affordable in review attention nor
interpretable: most cells answer no question anyone asked, and a table of
forty numbers invites picking the best cell, which the small holdout would
reward with noise.

### D13: Output layout carries the definition in the key

`data/models/` files gain a `definition` column ahead of `variant`, and the
existing long-format files stay single files rather than splitting per
definition. Added: `definition_comparison.csv` for D8's three sections, and
`threshold_sweep.csv` for the write-in sweep. The committed outputs from the
baseline change are superseded, and the `current` definition exists so that
their numbers remain reproducible rather than merely archived.

### D14: The adoption tie-break is stated in advance

If the definition comparisons come back undecided -- which the holdout size
makes likely -- the tie is broken on the principle the README already states:
the response and the predictor should be measured against the same
denominator. That favours a two-party response. The principle is recorded here,
before the numbers are seen, so that the adoption is not a post-hoc
rationalisation of whichever cell won.

## Risks / Trade-offs

- **The comparisons are underpowered.** 346 to 424 holdout races, differences
  of tenths of an RMSE point. → Every comparison carries a bootstrap interval
  and an undecided label, D14 fixes the tie-break in advance, and the writeup
  reports interval and holdout size beside every difference.
- **A definition change moves the target, so RMSE is not purely accuracy.** →
  D8's response-shift section is mandatory for any comparison whose definitions
  name different responses; the README's own figures (median race unmoved, 35
  races beyond 1 point, largest 54.4) are the shape to expect.
- **Excluding no-Democrat races lowers pooled RMSE mechanically.** → D6's
  reporting guard: removal is reported as removal, and the pooled figure is
  given with and without the segment.
- **The two-party restriction costs 78 holdout races and 2 of 24 specials.**
  Specials are the scarce segment and the `is_special` result already rests on
  24 of them. → D7's `two_party_or_strongest` recovers 93 of the 106 dropped
  races; the smallest training fold is reported per definition so the cost is
  visible, not inferred.
- **The published baseline numbers change.** D2 admits 16 races, so the 623-race
  table and the 15.61 pooled RMSE are superseded even before a definition is
  chosen. → The `current` definition reproduces the old race set exactly; the
  writeup shows the old and new figures side by side and attributes the
  difference to the 16 admitted races.
- **The hierarchical year model is thin.** Ten to fourteen years of effects,
  several of them single-race odd years. → D9 sets the expectation that it
  affects calibration rather than the mean; the diagnostics check already in
  place will flag it if the hyperprior is poorly identified.
- **`is_write_in` is taken on trust from `ma-election-db`.** → The threshold
  sweep makes the exposure visible: at 5% the flag affects 3 admitted races
  and one denominator, so an error in it cannot move the headline result far.
  The affected races are listed by name in the sweep report.
- **Runtime grows several-fold.** → D12 prunes the matrix; the run stays in
  minutes and remains the reproducibility story rather than something cached.

## Migration Plan

1. Extend the pipeline and rebuild both tables once under D2's permissive
   rule, with the roster of D4. The table grows from 623 to 639 races and
   gains columns; nothing is removed.
2. Score the `current` definition first and confirm it reproduces the
   committed baseline scorecard on its 623 races. This is the regression gate:
   if it does not reproduce, the rebuild changed something it should not have.
3. Run the definition comparisons, the threshold sweep, and the variant sweep,
   committing outputs as they complete.
4. Adopt one definition, record the decision and its evidence, and make it the
   default for a run that names none.
5. Replace `README.md`'s Open Questions section with the answers, and update
   `docs/scoring.md`, `docs/schema.md`, and `docs/race_schema.md`.

*Rollback.* Nothing is destructive. The `current` definition keeps the
pre-change race set and response reachable, and the adopted default is one
registry entry, so reverting a decision is a one-line change plus a rescore --
not a rebuild.
