## 1. Write-in admission in the collection pipeline

- [x] 1.1 Join `is_write_in` and `party_role` from `ma_general_election_candidates.csv.gz` onto the race candidate totals, matching on `(election_id, candidate)`; verify every named candidate in the precinct returns matches exactly one candidate record and that the build names any that do not
- [x] 1.2 Compute each write-in's share of named-candidate votes from district totals, and derive the race-level admitted set at a given threshold; verify the 2024 2nd Plymouth write-in (10.98%) is admitted at 5%, 8% and 10% and not at 15%, and that 28th Middlesex 2013's Hanlon (33.37% of named-candidate votes) is admitted at every candidate threshold, so the threshold decides which races are admitted rather than whether Hanlon counts
- [x] 1.3 Loosen the contested filter to two or more candidates counting any named write-in (design.md D2); verify 639 races are contested against the ballot-line rule's 623, that the published table grows to 633 because 6 of the 16 added races are all-Democratic fields the pre-existing no-usable-contest rule still excludes, and that `training_excluded_races.csv` records the write-in share for each remaining exclusion
- [x] 1.4 Assert at build time that no race needs per-precinct write-in detail beyond the published columns to resolve any candidate threshold, naming the race if one does; verify no race carries more than two named write-ins, so every threshold's admitted subset is expressible from `write_in_votes` and `top_write_in_votes`, and that the assertion fires when a third is injected

## 2. Definition-neutral precinct table

- [x] 2.1 Publish `dem_votes`, `gop_votes`, `write_in_votes` and `top_write_in_votes` per precinct row alongside the existing `opponent_votes` and `candidate_votes`; verify that for every row `candidate_votes` equals the sum of votes over named candidates and that `write_in_votes` is recoverable as a subset of it
- [x] 2.2 Publish `dem_margin_two_party` at precinct grain, missing where either major party is absent; verify it equals `dem_margin` exactly in a precinct where only the two major parties received votes, differs where a third candidate did, and is missing for all 13 no-Democrat races and for races with no Republican
- [x] 2.3 Publish the race-level eligibility flags on each row -- `major_party_race`, whether the race is contested on ballot lines alone, the strongest admitted write-in's share, and the candidate count counting admitted write-ins; verify `major_party_race` is true for exactly 517 of the pre-change 623 races
- [x] 2.4 Apply the threshold consistently to the denominator and the comparison candidate at the table's permissive 0% rule (design.md D3); verify a write-in is eligible to be the comparison candidate on the same terms as a ballot-line candidate, and that the comparison candidate is still fixed once per race rather than per precinct
- [x] 2.5 Extend the rollup validation with a category for races whose candidate set the threshold changes, reported as deliberate divergence rather than as a defect; verify `training_rollup_validation.csv` carries no `unexplained` rows and that every divergence from `mapoli` falls into a named category

## 3. Race table and candidate roster

- [x] 3.1 Publish `data/race/ma_race_candidates.csv.gz`, one row per `(election_id, candidate)` with party, `is_write_in`, district votes and share of named-candidate votes; verify each race's shares sum to 1 within tolerance and that the roster's candidate set per race matches the precinct returns
- [x] 3.2 Roll `dem_margin_two_party` up to race grain from summed Democratic and Republican precinct votes, not from averaged precinct margins; verify a race with uneven turnout gives a different value than the unweighted mean of its precinct two-party margins
- [x] 3.3 Carry the eligibility flags, write-in shares and both responses through to the race table; verify every column any declared definition references is present, and that applying a definition reads neither the precinct table nor a candidate-level source outside the roster
- [x] 3.4 Publish the per-race difference between the two responses and report the aggregate shift; verify the median shift is zero, that 35 of the pre-change rule's 517 major-party races shift by more than 1 point (36 of the published table's 523, the extra one being a race the write-in threshold admitted), that 5 shift by more than 10, and that 16th Essex 2014 is the largest at 54.4 points
- [x] 3.5 Document the new columns in `docs/schema.md` and `docs/race_schema.md`, stating for each how it was derived and which definitions read it; verify every published column of both tables appears in its document
- [x] 3.6 Run `maprecinct all` end to end and commit the rebuilt tables and roster; verify the race table has one row per `election_id`, that its `election_id` set is identical to the precinct table's, and that the rollup validation report is clean or has a documented cause per outlier

## 4. Definition registry

- [x] 4.1 Implement `legmodel/definitions.py` with a registry mapping a name to an eligibility predicate, a response column, a write-in threshold and a no-Democrat treatment, parallel to the variant registry; verify a definition naming a column the race table lacks raises an error saying which, and that registering a definition requires no change to fitting or scoring code
- [x] 4.2 Enforce that an eligibility predicate references only candidate presence, party and write-in share, never the response or the winner; verify a definition attempting to filter on the observed margin is rejected with a stated reason
- [x] 4.3 Register `current`, reproducing the pre-change rule exactly -- ballot-line eligibility, all-named-candidate denominator, no-Democrat races kept; verify it selects exactly the 623 races the published baseline was scored on
- [x] 4.4 Register `two_party` (major-party races only, two-party response), `write_in_5pct` (5% threshold, all-candidate response) and `two_party_or_strongest` (design.md D7), each stating its write-in threshold explicitly; verify each reports its admitted count and its dropped count with a reason per race, and that `two_party` and `two_party_or_strongest`, holding the write-in threshold at `current`'s ballot-line rule, select 517 and 610 races respectively out of that rule's 623
- [x] 4.5 Implement the three no-Democrat treatments -- keep, exclude, train-only -- as a declared definition parameter; verify train-only keeps the races in every fold's training set and produces no holdout prediction for them
- [x] 4.6 Implement `legmodel definitions` to list registered definitions with their parameters and admitted counts; verify the listed counts match what a scoring run under each definition reports

## 5. Definition-aware scoring

- [x] 5.1 Thread the definition through fitting, prediction and every output, so the response column and race set come from it; verify a scorecard row names its definition and that the same variant under two definitions produces two separately identified results
- [x] 5.2 Reject a variant naming a predictor that is constant or undefined under its definition, with an error naming both; verify a variant carrying `no_dem_candidate` fails under `two_party` rather than fitting a degenerate design matrix
- [x] 5.3 Report holdout counts per definition -- pooled races, specials, smallest training fold; verify `current` reports 424, 24 and 199, and `two_party` reports 346, 22 and 171
- [x] 5.4 Record a fold year that a definition empties as skipped rather than omitting it; verify a definition admitting no races in an odd year produces a skipped row rather than a silently shorter fold schedule
- [x] 5.5 Add the presidential-year bias segment and the write-in-admitted segment to the breakdowns, and report a segment a definition empties with a count of zero; verify segment race counts sum to the pooled holdout within each segment type and that the no-Democrat segment appears with count zero under `two_party`
- [x] 5.6 Reproduce the committed baseline scorecard under `current` restricted to its 623 races (design.md migration step 2); verify the holdout race set and every observed response are bit-identical to the committed run, that pooled RMSE, coverage and win accuracy agree with the committed 15.608 / 0.8915 / 0.9175 to within MCMC noise (15.611 / 0.8915 / 0.9151), and that the residual difference is traced to the seed now keying on the definition rather than to any change in the data

## 6. Cross-definition comparison

- [x] 6.1 Implement `legmodel compare-definitions` computing the paired difference over the intersection of two holdout sets with a bootstrap interval and a decided/undecided label; verify comparing a definition with itself yields a zero difference, an interval containing zero, and an empty exclusive set on both sides
- [x] 6.2 Report each definition's exclusive races with counts and reasons, and each definition's own score over its exclusive races; verify the dropped-races report shows `two_party` excluding exactly 106 of `current`'s 623 races on the major-party criterion, broken down as 93 with a non-Republican opponent (74 unenrolled, 8 Green-Rainbow, 4 Libertarian, 3 Pirate, 2 United Independent, 2 Workers Party) and 13 with no Democrat, and that 78 of the 106 fall in the holdout and are reported there with an RMSE of 25.30
- [x] 6.3 Report the response-shift summary over the intersection -- median, tail, and the count moving more than a stated number of points -- and zero it when both definitions name the same response; verify a comparison of two definitions differing only in eligibility reports zero shift and is labelled as isolating the eligibility rule
- [x] 6.4 State in the report that the two models trained on different race sets; verify the committed `definition_comparison.csv` carries the disclosure alongside the paired difference rather than in prose only
- [x] 6.5 Implement the write-in threshold sweep across 0%, 2%, 5%, 8%, 10% and 15%, recording admitted races and scores at each; verify the publishable counts run +10, +6, +2, +1, +1, 0 over the ballot-line rule -- the README's raw contested counts of +16, +10, +3, +1, +1, 0 less the all-Democratic fields that carry no comparison candidate, checked separately in 1.3 -- and that `threshold_sweep.csv` identifies 10% as the point where admissions stop changing

## 7. Model variants for the deferred questions

- [x] 7.1 Implement the knowability check rejecting a predictor computed from its fold year's own results; verify a variant declaring such a predictor is refused by name rather than scored
- [x] 7.2 Register `baseline_num_candidates` as the baseline plus `num_candidates`; verify the baseline's predictors are a strict subset and that the only difference is `num_candidates`
- [x] 7.3 Register `baseline_pres_incumbent` as an interaction between `pres_elec` and `incumbent_status`; verify the design matrix carries the interaction columns and that a fold whose training races lack a level still accepts a holdout race carrying it
- [x] 7.4 Register `baseline_year` as a hierarchical per-year intercept whose holdout year draws its effect from the year-level hyperprior (design.md D9); verify a holdout year absent from training produces predictions whose point estimate is near the baseline's and whose 90% interval is wider
- [x] 7.5 Register `baseline_national_env` with the term signed by the party holding the presidency (design.md D10); verify the term is negative for 2010 through 2015 and 2021 through 2023, positive for 2017 through 2019, and zero in 2012, 2016, 2020 and 2024, and that it is computed without reference to any election outcome
- [x] 7.6 Report per-variant mean signed error within presidential and non-presidential years and the gap between them; verify the baseline reproduces -6.4 and +2.7 and that a variant narrowing the gap is identifiable even when its pooled RMSE is unchanged

## 8. Run the sweep and answer the questions

- [x] 8.1 Score the definitions under `baseline` and commit the outputs (design.md D12); verify every committed `data/models/` file carries a `definition` column ahead of `variant` and that the scorecard covers `current`, `two_party`, `write_in_5pct` and `two_party_or_strongest`
- [x] 8.2 Score the variants under `current` and under the adopted definition and commit the outputs; verify each variant result is reported under both so that no variant conclusion rests on a single definition
- [x] 8.3 Run every comparison the specs require -- two-party against current, each threshold, each no-Democrat treatment, each bias variant against the baseline, and the candidate-count variant -- and commit the results; verify each carries its pooled difference, interval, label and holdout counts
- [x] 8.4 Verify reproducibility by rerunning one fold of one definition from its recorded seed and confirming its predictions match the committed holdout predictions row for row
- [x] 8.5 Adopt one definition, record the decision with its evidence, and make it the default when a run names none (design.md D14); verify a run naming no definition uses the adopted one and still records its name in the outputs, and that the superseded definitions remain scorable

## 9. Documentation and conclusion

- [x] 9.1 Extend `docs/scoring.md` with the definition concept, the cross-definition comparison mode and the response-shift disclosure; verify the described outputs match the committed files column for column
- [x] 9.2 Write up the data-definition decision -- Q1, Q2 and Q3 together -- covering each definition's holdout counts, the paired differences with intervals, the response shift, what each definition drops, and the adoption with its stated basis including the case where the data did not separate the candidates; verify every number in the writeup is present in a committed scorecard or comparison file
- [x] 9.3 Write up the variant sweep -- Q4 and Q5 -- covering each variant's pooled and segmented metrics, the presidential-year bias gap before and after, and a stated conclusion per variant including undecided ones; verify the caveat about `baseline_national_env` resting on eight non-presidential years is stated
- [x] 9.4 Replace `README.md`'s Open Questions section with the answers and links to the writeups, and restate the baseline accuracy table under the adopted definition alongside the superseded figures with the 16 admitted races named as the cause; verify the links resolve and that no unanswered question is left in the section
