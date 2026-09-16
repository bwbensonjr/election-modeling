## Context

The training builder currently reads race summaries from `ma-election-db`,
derives the three-level `incumbent_status`, repeats it at precinct grain, and
then carries it into the race rollup. Upstream candidate output includes stable
`candidate_id`, `is_winner`, `is_incumbent`, election dates, and
`district_id_prev`, but no tenure column. Its history begins well before the
2010 modeling window, so any incumbent whose service start is censored at the
source boundary has already exceeded all proposed caps by the first modeled
race.

The model registry already supports predictors derived from committed race
columns and the scoring system already provides rolling election-date folds,
clustered paired comparisons, and leave-one-general-date-out sensitivity.

## Goals / Non-Goals

**Goals:**

- Produce a fold-safe, auditable measure of continuous service known before
  each election.
- Test the specific diminishing-returns hypothesis with a four-year primary
  cap and narrowly pre-declared sensitivity checks.
- Preserve exact reproduction of the current baseline and isolate the
  incremental value of tenure within incumbent races.

**Non-Goals:**

- Changing `ma-election-db` or making local implementation depend on a future
  upstream release.
- Selecting a best cap by searching the historical holdout scores.
- Automatically adding tenure to the operational forecast or claiming a
  causal effect of time in office.
- Combining nonconsecutive periods of service into lifetime tenure.

## Decisions

### D1. Derive tenure locally, then consider upstream promotion

The experiment will derive tenure in this repository from the published
upstream history. This keeps the modeling change reproducible and unblocked,
and it lets this project settle modeling-specific choices such as continuous
service, censoring, and saturation before proposing an upstream contract.

An upstream issue is deferred until the result is known. If the field is useful
or the derivation proves broadly reusable, the results document will include a
ready-to-file definition and validation summary for `ma-election-db`.

Alternative: require `ma-election-db` to publish tenure first. Rejected because
the source already exposes the identities and links needed for the experiment,
while upstream ownership would delay the test and prematurely freeze a
definition.

### D2. Follow the selected incumbent's uninterrupted identity chain

For each race, start with the same incumbent selected by the upstream race
summary. Follow `candidate_id` backward from the immediately preceding victory,
using `district_id_prev` at each boundary. Regular and special victories are
both nodes in the chain. Tenure starts at the oldest consecutive victory found;
a loss, absence from the relevant predecessor race, or other break ends the
chain. Elapsed years are days divided by 365.2425.

This matches the upstream definition of who is currently incumbent while
avoiding name-based joins. Multiple-incumbent redistricting races continue to
use upstream's selected same-district-preferred incumbent, keeping tenure and
`incumbent_status` about the same person.

Alternative: count all prior wins by a candidate. Rejected because it would
combine service separated by a career gap and would not represent current
incumbency length.

### D3. Publish a value and a censoring flag

Open seats receive `0` years and `false` censoring. An observed uninterrupted
start produces an exact value. A chain reaching the source boundary produces a
lower bound and a true censoring flag. Candidate identity ambiguity or a broken
predecessor link fails the build with a targeted report; names are never a
fallback identity.

The proposed caps are valid for a censored row only when its lower bound is at
least the cap. Given the current source and model windows this is expected for
every censored modeled incumbent, but the condition is validated rather than
assumed.

Alternative: publish missing tenure for censored incumbents. Rejected because a
lower bound beyond a cap determines the capped predictor exactly and discarding
those entrenched incumbents would bias the experiment.

### D4. Test a signed capped increment alongside incumbent status

The primary derived predictor is:

`tenure_cap4_signed = party_sign * min(incumbent_tenure_years, 4)`

where `party_sign` is `+1` for `Dem_Incumbent`, `-1` for `GOP_Incumbent`, and
`0` for `No_Incumbent`. The baseline incumbency indicators stay in the model.
The new coefficient therefore asks whether additional early tenure changes the
margin within incumbent races, while imposing the substantively coherent rule
that additional tenure helps either incumbent party in its own direction.

Two- and six-year caps test whether the conclusion is sensitive to a nearby
saturation choice. They are sensitivity analyses, not candidates in a cap
optimization exercise. An uncapped term is omitted because old service is
left-censored and because it encodes the opposite of the motivating hypothesis.

Alternatives: replace `incumbent_status` with tenure, which would conflate
having an incumbent with length of service; or fit separate party-specific
tenure slopes, which spends limited Republican-incumbent information on an
asymmetry not posed by this question.

### D5. Adoption requires the primary comparison

The primary four-year variant is compared with the unchanged baseline using
the existing paired, election-date-clustered procedure. A clustered interval
spanning zero is undecided and leaves the baseline in place. The cap
sensitivities, tenure bands, party segments, diagnostics, and leave-one-date-out
results explain robustness but cannot substitute for a losing or undecided
primary result.

The results will be committed alongside the existing model artifacts and a
focused tenure writeup. Promotion into forecast candidates, if supported, is a
separate change so that an experiment does not silently alter operations.

## Risks / Trade-offs

- [Stable candidate IDs or predecessor links contain historical errors] ->
  Cross-check derived incumbent presence against `is_incumbent`, validate
  representative specials, career gaps, and redistricting cases, and fail on
  ambiguous chains.
- [The four-year cap is substantively plausible but arbitrary] -> Declare it as
  primary before scoring and show only narrow two- and six-year sensitivity.
- [Tenure proxies for electoral safety, fundraising, or candidate quality] ->
  Treat the comparison as predictive, not causal, and retain PVI and incumbent
  status in every arm.
- [Few short-tenure or Republican-incumbent races limit inference] -> Publish
  race and election-date counts, and label non-estimable clustered intervals.
- [Rebuilding committed tables causes unrelated model drift] -> Verify the
  baseline's existing outputs are unchanged before interpreting tenure scores.

## Migration Plan

1. Add and validate tenure derivation while leaving published model inputs
   untouched.
2. Rebuild the committed precinct and race tables and update their schemas.
3. Reproduce the baseline; stop and diagnose any unrelated score drift.
4. Register and score the three tenure variants, then publish artifacts and the
   tenure writeup.
5. Roll back by removing the additive tenure columns, variants, and tenure-only
   outputs; the baseline and existing model behavior require no data migration.
