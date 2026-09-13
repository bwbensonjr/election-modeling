## Why

The model has exhausted what the current tables can tell it. `PVI_N`,
incumbency and election timing now sit at 14.21 RMSE under the adopted
definition, and the two variants that helped most --- a year intercept and a
national-environment term --- both work by correcting *when* a race happened
rather than by saying anything about the race itself. Every remaining variant
tested on the existing columns came back undecided.

Campaign finance is the obvious next signal and the one the README has carried
as planned work since the project started. It is the first predictor that
varies *within* a district-year: two races with identical PVI and identical
incumbency can differ by a factor of fifty in money raised, and the model
currently has no way to tell them apart.

The data is at candidate/election/district grain, which is coarser than the
precinct grain the tables are built on but exactly the grain the model is fit
at, so it drops straight into the race table.

**Three obstacles are real, and were measured rather than assumed.** Probing
the OCPF API before writing this:

1. **The published feeds cover disjoint eras.** The current legislative feed,
   `reports/legislative/depository/ytd/{year}`, carries money only from **2020
   on** --- 2010 through 2019 return between 0 and 13 rows, against 428 for
   2020. The historical endpoint `onballot/finsummaries/{year}/{code}` is the
   mirror image: populated 2010 through 2018, empty from 2020. The seam falls
   at 2020, in the middle of the 2010-2024 modelling range, and the two feeds
   do not report the same quantity --- `finsummaries` gives final full-cycle
   totals, the depository feed gives a year-to-date snapshot.

2. **The published figures leak the outcome.** Fetched today, the "year to
   date" figure is a full-year total: 411 of 428 rows in 2020, and 436 of 477
   in 2024, carry a `bankReportEndDate` of 12/31. Money raised after the polls
   close is in there. For one Boston representative, receipts through October
   31 were **$401k against $560k for the full year in 2024, and $33k against
   $111k in 2020** --- 28% and 70% of the year's money arriving after the
   election. A model fit on the published figure would be reading the result.

3. **There is no shared identifier with the race table.** OCPF names filers
   `"Turner, Cleon H."`; the race candidate roster names them
   `"Richard J. Ross"`. The join has to be built from name, district and year,
   across two redistricting cycles.

The first two are solvable together, and the probe confirmed how:
`search/items` with `CpfId`, `StartDate`/`EndDate` and `withSummary=true`
returns a **date-bounded total that works uniformly back to 2010**, in one
call, with no paging. Reconstructing money as of a fixed pre-election date
from line items sidesteps both the era seam and the leak, and gives every
cycle the same measurement.

## What Changes

- **Collect OCPF money at candidate grain, as a date-bounded total.** A new
  collection stage resolves each race's candidates to OCPF filers and records
  receipts and expenditures accumulated between the start of the election year
  and a **declared as-of date**, rather than reading a published cumulative
  figure. Responses are cached under `cache/ocpf/` alongside the existing
  electionstats cache, so the collection is reproducible and re-runs cost no
  network.

- **Make the knowability boundary an as-of date rather than a year.**
  **BREAKING** for the `margin-model` spec: today a predictor must be
  knowable *before its fold year begins*, which no campaign-finance measure
  can satisfy. The rule becomes that a predictor must be knowable **before its
  fold year's election**, and any predictor that is not knowable before the
  year must carry an explicit as-of date that is published with every fit
  using it. The existing predictors are unaffected --- they remain knowable
  before the year, which is a strictly stronger guarantee, and the spec keeps
  requiring them to say so.

- **Publish the as-of date as a first-class property of a result.** A money
  figure without the date it was measured on is not interpretable, and the
  difference between two dates is the difference between a forecast and a
  postdiction. The as-of date is recorded in the training table, in the
  variant declaration, and in the published diagnostics.

- **Record the candidate-to-filer match, including the failures.** The join is
  name-based and will not be perfect. Every race records how many of its
  candidates were matched, by what rule, and unmatched candidates are
  published in a reviewable file rather than silently becoming zero. A race
  whose match is incomplete is flagged so a variant can exclude it rather than
  treating a missing filer as a candidate who raised nothing --- those are
  different facts and must not collapse.

- **Test the candidate money measures as a declared sweep, not a guess.** The
  raw fields are receipts, expenditures, cash on hand, start balance, in-kinds
  and liabilities; the modelling question is which *contrast* between the two
  candidates carries signal. Registered as variants over a common table:
  the signed difference in money, the Democratic share of the race's total
  money, the log ratio, and the absolute amounts entered separately. Each is
  scored by the existing harness under every definition, and the answer is
  whichever the paired comparison actually separates --- including
  "none of them", which the harness is already built to report.

- **Report money's effect where it should differ.** Money is expected to
  matter far more in open seats than against an entrenched incumbent, and more
  in low-information races. The scorecard already segments by incumbency, so
  the sweep reports the money variants' effect per incumbency segment rather
  than only pooled.

### Non-Goals

- No independent expenditures, PAC money, or party committee spending. The
  candidate committee is what OCPF's legislative feeds cover; outside money is
  a separate collection problem and a later change.
- No expenditure *categorisation* --- who a committee paid, and for what, is
  available through `search/items` but is a different question from how much
  was raised.
- No change to the response definition, the fold schedule, the metric set, or
  the pooling rule. The yardstick does not move while a predictor is added
  against it.
- No 2026 forward prediction, though the as-of-date mechanism is what would
  make one possible.
- No precinct-grain money. The data does not exist at that grain.

## Capabilities

### New Capabilities

- `campaign-finance`: The OCPF collection itself --- which feed answers which
  era, how a candidate is resolved to a filer, how a date-bounded total is
  reconstructed from line items, what is cached, and how unmatched candidates
  are published rather than absorbed.

### Modified Capabilities

- `margin-model`: the knowability rule becomes the fold year's election rather
  than its start, and a predictor not knowable before the year must declare
  and publish an as-of date; the money variants are registered.
- `race-training-set`: rows gain the candidate-grain money columns rolled up
  to the race, the as-of date they were measured on, and the match-quality
  flags.
- `model-scoring`: a fit's published record carries the as-of date of any
  dated predictor it used, and the money sweep is reported per incumbency
  segment as well as pooled.

## Impact

- **Code.** A new `maprecinct/ocpf.py` (collection and caching) and
  `maprecinct/filer_match.py` (candidate-to-filer resolution); changes to
  `maprecinct/races.py` for the new columns; `legmodel/variants.py` for the
  money variants and the as-of declaration; `legmodel/fit.py` and `score.py`
  to carry the as-of date into the published record.
- **Data.** `ma_race_training_set.csv.gz` gains money and match columns; a new
  `data/race/ma_race_finance.csv.gz` at candidate grain; a new
  `data/reports/ocpf_unmatched_candidates.csv` for the review file. Model
  outputs gain the money variants' rows.
- **New input.** The OCPF API at `api.ocpf.us`, cached under `cache/ocpf/`.
  Roughly 1,200 to 2,500 summary calls for the full range, one per candidate
  per window; cached, so the cost is paid once.
- **Docs.** `docs/race_schema.md` for the new columns; `docs/scoring.md` for
  the as-of date in the published record; a new writeup for the money sweep;
  `README.md`'s planned work updated.
- **Risk.** The join is the weak point: a name-matching failure that silently
  becomes zero money would bias the coefficient toward zero and look like a
  real null result. This is why unmatched candidates are published and why a
  race's match quality is a column rather than a log line. The second risk is
  that money is largely *endogenous* --- money flows to candidates already
  expected to win, so a strong coefficient may be measuring expectations
  rather than causing them. The sweep cannot settle that, and the writeup will
  say so rather than implying the model has found a lever.
- **Dependency.** `httpx` for the API client, already a transitive dependency
  of the project's tooling and a direct dependency of `ocpf-cli`.
