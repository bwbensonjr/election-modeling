## Why

The baseline change left five questions open at the bottom of `README.md`.
Three of them -- the two-party response, the write-in threshold, and races
with no Democratic candidate -- are one underlying question: *who counts as a
candidate, and what is the margin measured against*. Each one rebuilds the
training table and invalidates the published scorecard, so settling them one
at a time means rebuilding and republishing three times. The other two -- an
unabsorbed presidential-year bias and whether `num_candidates` belongs in the
baseline -- are variant declarations that cost almost nothing and were
deferred only because they were not the question the baseline change set out
to settle.

The scorecard also shows why these are worth settling before any new
predictor is added. The baseline's worst segment is the 11 holdout races with
no Democratic candidate: 28.35 RMSE against a pooled 15.61, with 36% coverage
of a 90% interval. The response and the predictor are measured against
different denominators -- `dem_margin` divides by every named candidate,
`PVI_N` by two-party presidential votes -- and switching the response to
two-party raises PVI's correlation with it from 0.705 to 0.724 on the same
517 races. Demographic and fundraising variables added on top of a mismatched
response would be measured against a yardstick that is itself miscalibrated.

## What Changes

- **Make the data definition a selection over one table, not a rebuild.**
  The central design decision: instead of rebuilding the training table once
  per candidate definition, publish every response and every eligibility flag
  on a single table, and make a definition a named configuration that selects
  rows and names a response column. Questions 1 through 3 then become
  configuration rather than reconstruction, the table is rebuilt once, and a
  definition that loses can be revisited without another collection run.

- **Carry a two-party response alongside the existing one (Q1).** Add
  `dem_margin_two_party`, `(dem - gop) / (dem + gop)` in points, at precinct
  and race grain, computed on the same denominator `PVI_N` already uses. Add
  `major_party_race`, true when the race has both a Democrat and a
  Republican. No rows are dropped from the published table; the D-vs-R
  restriction is a definition that filters on the flag.

- **Admit write-ins by threshold, consistently in both places (Q2).** Take
  `is_write_in` from `ma-election-db`'s candidate table, which the pipeline
  already reads for other purposes, and apply one threshold on share of
  named-candidate votes to both decisions a write-in currently splits: whether
  a race counts as contested, and whether the write-in enters the margin
  denominator. Today the ballot-line count decides the first and the precinct
  returns decide the second, which is why 28th Middlesex 2013 yields three
  different margins under three rules. The threshold is a definition
  parameter, with candidates at 0%, 2%, 5%, 8% and 15% measurable from the
  same table.

- **Handle no-Democrat races explicitly rather than by convention (Q3).**
  Keep the rows and their flag, and make the treatment a definition: keep them
  with a `no_dem_candidate` term, exclude them, or -- the README's open
  sub-question -- keep the two-party response and admit the strongest
  non-Republican as the comparison where no Republican ran. All three are
  scored, rather than one being assumed.

- **Add a cross-definition comparison mode to the scoring harness.**
  `legmodel compare` pairs on identical holdout races, which two definitions
  do not share. The new mode scores each definition on its own holdout, then
  compares on the intersection, and reports separately what each side admits
  and drops. Because a definition changes the response as well as the race
  set, the comparison also publishes the distribution of response shift on
  the intersection, so an RMSE difference cannot be read as pure accuracy
  when part of it is the target moving.

- **Register variants for the presidential-year bias (Q4).** The baseline runs
  6.4 points too Republican in non-presidential years and 2.7 too Democratic
  in presidential ones; one binary term applied identically cannot correct a
  swing of that shape. Three variants, each restricted to information knowable
  before the fold year: an interaction between `pres_elec` and incumbency, a
  hierarchical year intercept whose holdout year draws from the year-level
  hyperprior, and a signed national-environment term keyed to the party
  holding the presidency, which is the substantive story behind a midterm
  swing and is known in advance.

- **Register the `num_candidates` variant (Q5).** One registry entry scored by
  the existing harness, reported alongside the note that a two-party response
  makes it largely redundant if adopted.

- **Adopt one definition as the published default and rebuild once.**
  **BREAKING** for published outputs: the precinct and race tables gain
  columns and, if a write-in threshold is adopted, rows; the committed
  scorecard and the `is_special` figures are recomputed under the adopted
  definition. `README.md`'s Open Questions section is replaced by the answers
  and the evidence behind each.

### Non-Goals

- No new predictors from outside the current tables. Demographics, OCPF
  fundraising and a finer incumbency variable remain later changes.
- No non-Bayesian algorithms. The algorithm matrix is a later change scored by
  this same harness.
- No change to the fold schedule, the metric set, or the pooling rule. A
  definition changes which races are scored, not how they are scored, so the
  2014-through-2024 rolling origin stands.
- No precinct-grain model, and no 2026 forward prediction.
- No re-collection from electionstats. Everything needed is in the cached
  precinct returns and `ma-election-db`'s candidate table.

## Capabilities

### New Capabilities

- `response-definition`: The named data definitions themselves -- the
  eligibility filter, the write-in threshold, the response column, and the
  no-Democrat treatment -- as configuration selected over one published table,
  together with the record of which definition is adopted and on what
  evidence.

### Modified Capabilities

- `precinct-training-set`: The uncontested filter gains a write-in threshold
  rather than counting ballot lines alone; the same threshold governs the
  margin denominator; rows gain two-party vote columns and write-in
  provenance so a definition can be applied without recollection.
- `race-training-set`: Rows carry the alternate responses, the eligibility
  flags, and the write-in shares rolled up from the precinct table, so the
  race table alone is sufficient to evaluate every definition.
- `margin-model`: A variant is bound to a definition as well as a predictor
  set; a predictor must be knowable before its fold year, which constrains
  how a year effect may be specified.
- `model-scoring`: Scoring runs under a named definition; comparing two
  definitions is a distinct operation from comparing two variants, scored on
  the intersection of their holdouts with what each side admits reported
  separately.

## Impact

- **Code.** `maprecinct/training.py` and `maprecinct/races.py` for the new
  columns and the write-in threshold; a new `legmodel/definitions.py`; changes
  to `legmodel/variants.py`, `score.py`, `compare.py` and `cli.py` for
  definition-aware scoring and the new comparison mode.
- **Data.** `ma_precinct_training_set.csv.gz` and
  `ma_race_training_set.csv.gz` rebuilt with added columns and, under an
  adopted threshold, added races. Under `data/models/`, a scorecard per
  scored definition plus a new `definition_comparison.csv`.
- **New input.** `is_write_in` and `party_role` from
  `ma-election-db`'s `ma_general_election_candidates.csv.gz`, which
  `maprecinct.config` already exposes but the training stage does not yet
  read.
- **Docs.** `docs/schema.md` and `docs/race_schema.md` for the new columns;
  `docs/scoring.md` for the comparison mode; new writeups for the definition
  decision and the variant sweep; `README.md`'s Open Questions replaced by
  answers.
- **Runtime.** Roughly four definitions times six variants of rolling-origin
  scoring, ten folds each. Two hundred-odd MCMC fits on at most 600 rows --
  longer than the current run but still minutes, so it stays reproducible on
  demand rather than cached.
- **Risk.** The holdout is 346 to 424 races depending on the definition, and
  the differences under test are fractions of an RMSE point. Several of these
  comparisons will come back undecided, and the harness reports them that way
  rather than naming a winner. Where the data does not separate two
  definitions, the tie is broken on the stated principle -- the response and
  the predictor should share a denominator -- and the writeup says so.
- **Dependency.** None added. `bambi`, `pymc` and `arviz` already cover the
  hierarchical year intercept.
