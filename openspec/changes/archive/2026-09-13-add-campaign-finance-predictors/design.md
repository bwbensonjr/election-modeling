## Context

See [`proposal.md`](proposal.md) for why. What follows is what the OCPF API
actually returns, measured before this was written, and the decisions that
follow from it.

**Feed coverage, probed year by year.** `reports/legislative/depository/ytd/{year}`
returns 428 rows for 2020 and 477 for 2024, but 0 to 13 rows for every year
from 2010 through 2019. `onballot/finsummaries/{year}/{code}` is the mirror
image: populated for 2010 through 2018, empty from 2020. Neither feed spans
the modelling range, and they do not report the same quantity --- the
historical one gives final full-cycle totals (`receipts`, `expenditures`,
`inkinds`, `liabilities`, `startBalance`, `endBalance`), the current one a
snapshot as of a `bankReportEndDate`.

**Both published figures are post-election.** Of the 2020 rows, 411 of 428
carry a `bankReportEndDate` of 12/31; in 2024 it is 436 of 477. The
`finsummaries` totals are final by construction. Measured on one Boston
representative:

| Year | Receipts through Oct 31 | Full calendar year | Raised after Oct 31 |
|---|---|---|---|
| 2024 | $401,190 | $560,090 | 28% |
| 2020 | $32,935 | $111,126 | 70% |

**`search/items` solves both problems at once.** With `CpfId`,
`StartDate`/`EndDate` and `withSummary=true` it returns a date-bounded count
and total in a single call, with no paging, and it works uniformly back to
2010 --- the table above was built with it. `SearchTypeCategory` selects
receipts (`R`) or expenditures (`B`). Windows may cross a year boundary.

**The join, measured.** A deliberately naive surname-plus-given-name match
found a filer for **76-84%** of candidates on 75 sampled non-special races
across 2010, 2014 and 2018. Inspecting the residual showed it is mostly matcher weakness, not
missing data:

| Cause | Example | Fixable |
|---|---|---|
| Generational suffix | `Harold P. Naughton, Jr.` parsed with surname "jr" | yes, trivially |
| Multi-word surname | `Beverley A. Griffin Dunne`, `Kenneth William Van Tassell` | yes |
| Diminutive given name | `Bob Russell` -> `Russell, Robert W.`; `Pina Prinzivalli` -> `Prinzivalli, Giuseppina` | yes, via surname-first matching |
| Genuinely no committee | `Leah Cole`, `John F. Cruz` | no --- a real fact |

**Correction: district resolution is not free, and is not this project's to
solve.** An earlier draft of this design claimed district resolution succeeded
100% of the time. That figure came from a House-heavy sample and did not hold:
across all 633 races, resolving `office` plus `district_display` against OCPF's
`districts` reference reaches 581. The reference is the **present map only**,
so every district retired at redistricting is unreachable by name for the years
it existed, and 42 of the failures are exactly that. Folding ordinal words to
digits (`First` -> `1st`) recovers 4 more.

Worse, the years special elections cluster in have no roster in any on-ballot
feed at all: `onballot/finsummaries` returns zero rows for 2013, 2015 and 2017,
in both chambers, and the legislative feed does not begin until 2020. That is
15 races, all of them special.

Both problems are now solved in `ocpf` 0.4 (issues #2, #3, #4 and #9 on
`bwbensonjr/ocpf-cli`), which resolves a district against the map for the
**requested year** and builds special-election rosters from the candidates' own
filings. This project consumes that rather than reimplementing it.

**Special elections break a calendar-year window.** The 39 specials fall
across the whole calendar, including January 7. A year-to-date window would
measure almost nothing for an early-year special, because that campaign's
money was raised in the previous calendar year.

## Goals / Non-Goals

**Goals:**

- One money measurement that means the same thing in 2010 and 2024, measured
  strictly before each race's own election.
- A join whose failures are visible and reviewable rather than absorbed into
  a zero.
- Enough candidate measures registered that "which number correlates best" is
  answered by the scoring harness rather than chosen up front.

**Non-Goals:**

- No attempt to reach a 100% match. Some candidates genuinely never filed, and
  the design's job is to distinguish those from lookup failures, not to erase
  the distinction.
- No causal claim. See the endogeneity risk below.
- No new modelling machinery. Money is columns plus registry entries; the
  fitting, folding and scoring code is unchanged apart from carrying the as-of
  date through.

## Decisions

### D1. Money is reconstructed from line items, never read from a published total

Every figure comes from `search/items` with an explicit date window. The
published `receiptsYtd` and `finsummaries` totals are collected too, but only
as a **reconciliation check**, never as a predictor.

*Why.* It is the only measurement that is both pre-election and uniform across
the era seam. It also collapses two problems into one mechanism: there is no
"early era vs late era" branch in the predictor path, only in which feed
supplies the candidate roster.

*Cost.* One call per candidate per window instead of one call per year. At
roughly 1,250 candidate-races over two windows that is a few thousand cached
requests --- minutes once, then free.

*Implementation.* `ocpf totals` reports exactly this figure, and this project's
cached client calls the same `search/items` endpoint with the same parameters;
the two agree to the cent on the figures above. The money path stays in-process
because it runs over thousands of windows, where a subprocess per call would
cost hours rather than minutes. Rosters, which run once per race, go through
the CLI.

*Alternative rejected: use the published totals and subtract nothing.* This is
what the data invites and it would be wrong by 28-70% in the direction that
flatters the model, because post-election money follows the result.

### D2. The window is trailing and relative to each race's own election date

Money is accumulated over the **365 days ending `K` days before the race's
election date**, not over the calendar year to date.

*Why trailing.* A January special's campaign is funded in the prior calendar
year. A year-to-date window would score those races as though nobody raised
anything, and there are 39 specials --- already the model's worst segment.

*Why relative to the election.* The same reason: a fixed October date is
meaningless for a race held in March.

*Choice of `K`.* `K = 14` days as the primary window. It is late enough to
capture the campaign and early enough to be a genuine forecast, and it sits
just before the pre-election reporting deadline rather than after it. A second
window at `K = 60` is collected in the same pass, so the sensitivity of any
result to the cutoff is measurable rather than assumed. Both dates are
published.

*Consequence for the spec.* This is what forces the knowability rule from
"before the fold year" to "before the fold year's election", with a declared
as-of date. The existing predictors keep the stronger guarantee and the spec
keeps requiring them to state it.

### D3. Matching is surname-first within a district-year, and reports its residual

Resolution runs district-first, as the tool's own guidance requires: ask `ocpf`
for the race's roster, then match within that small set --- typically one to
eight filers, which is what makes surname-first viable.

The district is named to `ocpf` **by code wherever the current map still has
it**, and by name otherwise. A name alone can be ambiguous --- `1st Suffolk` is
both a Senate and a House district, and `ocpf` refuses to guess between them.
That refusal is correct, and a caller that knows the chamber should not be
asking an ambiguous question: passing the code is this project's job, not a
gap in the tool.

The rules, in order, each recorded on the row that used it:

1. Normalise both sides: strip accents, punctuation and generational suffixes
   (`Jr`, `Sr`, `II`, `III`), casefold.
2. Match on full surname, allowing multi-word surnames by trying successively
   longer trailing word groups.
3. Where more than one filer shares the surname, require the given name to
   agree on its first letter or as a prefix, which is what separates
   `Robert`/`Bob` and `Giuseppina`/`Pina` without a nickname table.
4. Anything still ambiguous is recorded as ambiguous and matched to neither.

*Why not fuzzy string distance over all filers.* Edit distance would happily
match two different people with similar surnames, and a wrong match is worse
than no match: it attributes one campaign's money to another candidate. The
district-year restriction does the disambiguating work that fuzziness would
otherwise have to guess at.

*The residual is a deliverable.* The measured 76-84% baseline is the floor to
beat, and the unmatched candidates are published so the remainder can be
inspected and classified as "no committee" rather than assumed to be either.

### D4. Unavailable money and zero money are different columns

A candidate with no committee raised zero. A candidate whose filer could not be
found has unknown money. Collapsing them would put a large fake zero into the
predictor exactly where the match is hardest, biasing any coefficient toward
zero and producing a null result that looks like evidence.

Each race therefore carries `money_candidates_matched`,
`money_candidates_total`, and a `money_complete` flag. A money variant either
filters to complete races or carries an explicit unknown indicator; it may not
impute.

### D5. The contrast is the predictor, not the amount

Four registered forms, all oriented so that larger means better for the
Democrat:

| Variant | Predictor | Handles |
|---|---|---|
| `baseline_money_share` | Dem money / (Dem + opponent money) | scale-free, bounded, undefined only when both are zero |
| `baseline_money_logratio` | `log((dem + 1) / (opp + 1))` | the order-of-magnitude view; the `+1` admits genuine zeros |
| `baseline_money_diff` | `(dem - opp) / 1000`, in thousands | absolute advantage, where the log view flattens it |
| `baseline_money_both` | `log1p(dem)` and `log1p(opp)` as two terms | lets the fit weight the two sides unequally |

*Why a contrast rather than the Democrat's raw money.* The response is a
margin --- a difference between two candidates --- so a predictor that moves
with one candidate's fundraising alone is measuring race salience as much as
advantage. A rich district with two well-funded candidates is not a Democratic
advantage.

*Why register four rather than reason to one.* This is precisely the question
the harness exists to answer, and the project's standing rule is that a
comparison whose interval spans zero is published as undecided rather than
resolved by argument. Expenditures are collected alongside receipts and the
same four forms are available over them, but receipts are scored first;
spending is closer to the outcome in time and more likely to respond to a race
already tightening.

### D6. Money is reported by incumbency segment, not only pooled

The prior is strong and specific: money should matter most in open seats and
least against an entrenched incumbent, where the incumbency term already
carries the signal. The scorecard already segments on `incumbent_status`, so
this is a reporting decision rather than new machinery --- but it is written
into the spec because a pooled null that hides an open-seat effect would be a
wrong conclusion, not merely an incomplete one.

## Risks / Trade-offs

- **Endogeneity.** Money flows toward candidates already expected to win, so a
  strong coefficient may be measuring the same expectations `PVI_N` and
  incumbency already encode, arriving by a different route. → The sweep cannot
  settle this and will not try. The writeup states it, and the incumbency
  breakdown is the closest thing to evidence available: a money effect that
  survives *within* open seats, where there is no incumbent for expectations to
  attach to, is harder to explain away than a pooled one.

- **Match failure biased toward the weak.** Candidates who are hard to match
  are disproportionately minor candidates, who also raise little. If those
  become zeros, the predictor gains fake signal --- unmatched-and-zero would
  correlate with losing. → This is the reason for D4, and it is why the
  unmatched list is a published artifact rather than a diagnostic print.

- **The 2019 hole.** 2019 has no fold (no contested races in the table) and no
  usable feed. It costs nothing here, but it means the trailing window for an
  early-2020 race reaches into a year with no roster to resolve names against.
  → Resolution is per race-year, not per money-year; the window only needs
  line items for a `cpfId` already resolved.

- **A dependency on `ocpf`'s `--json` contract.** The roster path shells out to
  a separately released tool. → `--json` is that tool's documented interface
  and is versioned; the alternative is reimplementing year-aware district
  resolution and special-election roster construction here, which is the
  subtler code and would drift. Output is cached per invocation, so a rerun
  costs neither a subprocess nor a request.

- **`isWinner` is in both feeds.** Both `finsummaries` and the depository feed
  carry a winner flag. It is the answer to the question being asked. → Added to
  the project's existing outcome-column guard so a predictor derived from it is
  refused by the same mechanism that already rejects vote counts.

- **Two windows double the collection.** `K = 14` and `K = 60` is two calls per
  candidate per category. → Bounded and cached; the alternative is asserting a
  cutoff and never knowing whether the result was an artifact of it.

- **A network dependency enters a pipeline that had none at scoring time.** →
  Collection is a separate stage writing a committed table, exactly as the
  electionstats collection already is. Scoring still reads only committed CSVs.

## Migration Plan

Additive. The race table gains columns; every existing variant ignores them and
its published numbers are unaffected, which is checkable the same way the last
change checked it --- rescore and compare the untouched variants byte for byte.

The collection stage is new and independent: it can be run, inspected and
re-run without touching the model, and the model can be scored without it until
the money columns are trusted.

Rollback is dropping the registry entries; the columns are inert without them.

## Open Questions

- Whether to collect the primary as a separate window from the general. A
  September primary is a real contest that consumes real money, and a
  general-election window that includes it mixes two campaigns. Deferred: it
  changes no requirement here, and the `K = 14` / `K = 60` pair will show
  whether cutoff sensitivity is large enough to be worth the extra dimension.
