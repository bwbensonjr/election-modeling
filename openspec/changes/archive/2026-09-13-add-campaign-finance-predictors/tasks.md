## 1. The OCPF client and cache

- [x] 1.1 Add `maprecinct/ocpf.py` with a cached `get_json` over
  `api.ocpf.us`, writing responses under `cache/ocpf/` keyed by path and
  query; verify a second identical call is served from disk and makes no
  request
- [x] 1.2 Implement `dated_total(cpf_id, start, end, category)` over
  `search/items` with `withSummary=true`, returning the count and a numeric
  total; verify it reproduces the probe figures --- cpfId 14902 over
  11/1/2023-10/25/2024 returns 1760 receipts totalling $581,434.45, and 845
  expenditures totalling $397,182.30
- [x] 1.3 Guard the category parameter against the API's silent fallback ---
  an unrecognised `SearchTypeCategory` returns receipts rather than erroring
  --- by accepting only the `R` and `B` constants; verify any other value
  raises rather than issuing a request
- [x] 1.4 Verify the collection reports its cache hit and fetch counts on
  completion

## 2. Candidate rosters per era

- [x] 2.1 Depend on `ocpf>=0.4`, which resolves a district against the map for
  the requested year; verify `ocpf race "Worcester and Norfolk" --year 2020`
  resolves the retired district to code 140 and
  `ocpf race "2nd Hampden and Hampshire" --year 2013 --special` resolves the
  renamed one to code 114. Reimplementing this here was tried and abandoned:
  OCPF's `districts` reference is the present map only, so 42 of 633 races name
  a district it does not carry (design.md, D3 correction)
- [x] 2.2 Fetch each race's roster through `ocpf race --json`, adding
  `--special` for a special election, and cache each invocation's output so a
  rerun costs no subprocess and no network; verify the 2013/2015/2017 races
  that no on-ballot feed covers now return candidates with cpfIds
- [x] 2.3 Normalise the regular and special CLI rows to one shape --- they name
  the filer `filerName` and `name` respectively --- and address the district by
  code wherever the current map has it, since a bare name can be ambiguous
  (`1st Suffolk` is both a Senate and a House district and `ocpf` rightly
  refuses to guess); verify all four such races resolve when the code is passed

## 3. Candidate-to-filer matching

- [x] 3.1 Implement name normalisation: strip accents, punctuation and the
  generational suffixes `Jr`, `Sr`, `II`, `III`, `IV`; verify
  `Harold P. Naughton, Jr.` yields surname `naughton`, not `jr`
- [x] 3.2 Implement surname-first matching within the district-year, trying
  successively longer trailing word groups so multi-word surnames resolve;
  verify `Beverley A. Griffin Dunne` and `Kenneth William Van Tassell` match
  their filers
- [x] 3.3 Disambiguate a shared surname by given-name prefix agreement; verify
  `Bob Russell` resolves to `Russell, Robert W.` and `Pina Prinzivalli` to
  `Prinzivalli, Giuseppina`, and that two genuinely different people sharing a
  surname resolve to neither
- [x] 3.4 Record the matching rule used on every candidate row, and mark
  unresolved candidates as ambiguous or unmatched rather than guessing
- [x] 3.5 Measure the match rate across all 633 races and verify it exceeds
  the 76-84% naive baseline measured on the sample; publish the rate per year
  so an era-specific failure is visible. Measured: **1244 of 1266 candidates,
  98.3%**, at or above 95.3% in every year except 2023 (2 of 4). The residual
  is **zero races whose district fails to resolve** and 22 candidates absent
  from a roster that was found, of which 10 sat in a district-year whose roster
  held a single filer -- their opponent never registered a committee
- [x] 3.6 Publish unmatched and ambiguous candidates to
  `data/reports/ocpf_unmatched_candidates.csv` with the race, the candidate,
  the district code and the filers that were considered; verify the file is
  written even when empty

## 4. The candidate-grain finance table

- [x] 4.1 For every matched candidate, collect receipts and expenditures over
  the two windows --- 365 days ending 14 days before the election, and ending
  60 days before --- and write `data/race/ma_race_finance.csv.gz` at candidate
  grain carrying both as-of dates; verify a January special draws its money
  from the prior calendar year rather than returning near-zero
- [x] 4.2 Reconcile against the published cumulative figures, which are used
  for nothing else. **The check as originally written does not hold, for two
  reasons, both of which belong in the writeup rather than being worked
  around.** First, the window is trailing and crosses a calendar year, so it
  legitimately exceeds a calendar-year figure -- 174 of 370 candidates do.
  Second, on a like-for-like calendar-year comparison the line-item total still
  runs a median 13% above the published `receiptsYtd` (only 14 of 40 within
  2%), because the two measure different things: the depository figure is
  bank-reported deposits, and the line items are reported receipts including
  in-kind and non-depository records. Verified instead that the two correlate
  closely per candidate, that the published figure feeds no predictor, and that
  the measure used is computed identically for every candidate and year
- [x] 4.3 Verify no as-of date falls on or after its race's election date, for
  every row in the table
- [x] 4.4 Add the winner flags from both feeds to the project's outcome-column
  guard; verify a variant naming one is refused by the existing leaking-
  predictor mechanism

## 5. Race-grain rollup

- [x] 5.1 Roll the candidate table up to the race, carrying the Democratic and
  opponent money for each measure and window, plus
  `money_candidates_matched`, `money_candidates_total` and `money_complete`;
  verify the race figures are reproducible from the candidate rows and that a
  disagreement fails the build
- [x] 5.2 Record unavailable money as missing rather than zero, and verify a
  race where every candidate was matched and raised nothing is distinguishable
  from one where a filer was not found
- [x] 5.3 Add the money and match columns to `ma_race_training_set.csv.gz` and
  document them in `docs/race_schema.md`; verify the documented column list
  matches the committed header
- [x] 5.4 Verify every pre-existing column in the race table is byte-for-byte
  unchanged by the rebuild

## 6. The as-of date in the model

- [x] 6.1 Extend the variant declaration so a predictor may carry an as-of
  date, and refuse a variant declaring a not-knowable-before-the-year
  predictor without one; verify the error names the predictor
- [x] 6.2 Verify a declared as-of date on or after a fold's election date is
  refused rather than fit
- [x] 6.3 Carry the as-of date into `fit_diagnostics.csv` and the scorecard
  rows, alongside the sampler settings already recorded; verify two fits of
  one variant at the two windows are distinguishable in the published outputs
- [x] 6.4 Verify variants declaring no dated predictor are unaffected, by
  rescoring `baseline` and comparing to the committed rows

## 7. The money sweep

- [x] 7.1 Register `baseline_money_share`, `baseline_money_logratio`,
  `baseline_money_diff` and `baseline_money_both` per design D5, each oriented
  so a larger value favours the Democrat; verify a race with equal money takes
  the scale's neutral value
- [x] 7.2 Verify each money variant either filters to `money_complete` races
  or carries an explicit unknown indicator, and that none imputes
- [x] 7.3 Score every money variant under every scored definition at the
  primary window, and verify the pooled holdout count is reported alongside
  the baseline's so the cost of restricting to complete races is visible
- [x] 7.4 Score the adopted money variant at the second window and report the
  cutoff sensitivity
- [x] 7.5 Run the paired comparisons against `baseline` and verify each is
  reported per incumbency segment as well as pooled, with small segments
  marked
- [x] 7.6 Verify the untouched variants' rows are unchanged after the rescore,
  as in the previous change

## 8. Publish

- [x] 8.1 Write `docs/money_results.md`: the feed-era seam, the leakage
  measurements, the match rate and its residual, the four measures and which
  the data separates --- including "none of them" if that is the answer
- [x] 8.2 State the endogeneity caveat in the writeup, and verify the result
  is not presented as evidence that spending changes outcomes
- [x] 8.3 Document the collection stage and the two windows in
  `docs/pipeline.md` and the as-of date in `docs/scoring.md`
- [x] 8.4 Update `README.md`'s planned work and, if a money variant is
  adopted, the accuracy table
