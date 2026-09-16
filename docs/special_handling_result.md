# Where do special elections belong?

> Supersession note: numeric intervals and verdicts below document the earlier
> race-bootstrap analysis. Current election-date-clustered results are in
> `data/models/variant_comparison.csv`; leave-one-general-date results are in
> `data/models/variant_comparison_sensitivity.csv`.

Special elections are 24 of the 424 races in the holdout and the model's worst
segment by a wide margin. The question this answers is not which term to add
but whether they belong in the general-election fit at all.

Three arms, scored on identical folds and identical holdout races:

- **`special_pooled_plain`** — one fit over all races, no `is_special` term.
  Identical in substance to `baseline`.
- **`special_pooled_term`** — one fit over all races, plus `is_special`. This
  is the former `baseline_special`.
- **`special_split`** — two fits. A **general model** that never sees a
  special election, in training or holdout, and a **special model** fit on all
  races with `is_special`. Each race is predicted by the component matching
  its own `is_special` value.

All three cover the same 424 races, so every comparison is paired race by
race. `special_split` is labelled non-nested against the other two: it is two
fits over two populations, not a predictor set that contains or is contained
by theirs.

## Why the question is worth asking

**Every special election in the record carries `pres_elec = False`**, because
none has ever fallen on a presidential general date. Three consequences
follow, and none of them was deliberate:

- specials sit inside the `pres_elec = False` segment, so any "non-presidential
  year" figure is a blend of 237 midterm generals and 24 specials;
- specials are the only races that separate `pres_elec` from a per-election
  effect, so they carry the entire identification of that term;
- the general-election model's `pres_elec` coefficient is estimated partly
  from a population it is never asked to predict.

## Answer

**Pooled, the three arms are indistinguishable. The finding is entirely in the
segments.**

Pooled paired differences under the adopted `two_party_or_strongest`
definition; a positive difference favours the right-hand arm:

| Comparison | n | Difference | 90% interval | Verdict |
|---|---|---|---|---|
| `plain` vs `term` | 413 | −0.063 | [−0.170, +0.047] | undecided |
| `plain` vs `split` | 413 | −0.018 | [−0.162, +0.123] | undecided |
| `term` vs `split` | 413 | +0.045 | [−0.034, +0.123] | undecided |

Only `two_party` separates any pair pooled, and marginally: `plain` over
`term` by 0.101 [0.012, 0.192], and `split` over `term` by 0.072 [0.014,
0.132].

## The segments disagree, consistently, in all four definitions

Paired differences by ballot timing under `two_party_or_strongest`:

| Comparison | Segment | n | Difference | 90% interval | Verdict |
|---|---|---|---|---|---|
| `plain` vs `term` | midterm general | 232 | −0.285 | [−0.388, −0.185] | **`plain` lower** |
| | presidential general | 157 | +0.056 | [−0.012, +0.124] | undecided |
| | special | 24 | +0.808 | [−0.057, +1.524] | undecided |
| `plain` vs `split` | midterm general | 232 | −0.342 | [−0.511, −0.177] | **`plain` lower** |
| | presidential general | 157 | +0.279 | [+0.140, +0.415] | **`split` lower** |
| | special | 24 | +0.837 | [−0.077, +1.587] | undecided |
| `term` vs `split` | midterm general | 232 | −0.057 | [−0.175, +0.060] | undecided |
| | presidential general | 157 | +0.223 | [+0.108, +0.337] | **`split` lower** |
| | special | 24 | +0.029 | [−0.082, +0.129] | undecided |

Three findings, each holding in all four scored definitions:

**1. `special_split` is better on presidential-date general elections, and
that is the only segment where any arm beats every other.** It clears zero
against both other arms under every definition — against `plain` by +0.279,
+0.229, +0.153 and +0.214, and against `term` by +0.223, +0.164, +0.138 and
+0.126. This is the arm's real effect, and it is not the one it was proposed
to deliver.

**2. Distinguishing specials at all costs accuracy on midterm generals.** Both
`term` and `split` lose to `plain` there, decided under three of four
definitions. Adding `is_special` costs 0.285 RMSE; removing specials from
training costs 0.342.

**3. On special elections themselves, `term` and `split` are
indistinguishable.** Their difference is +0.029 [−0.082, +0.129] and undecided
under every definition. That is not a surprise on inspection: `special_split`'s
special component *is* the pooled-term model. Both beat `plain` on specials —
decided under `current` (+1.156) and `write_in_5pct` (+1.071), undecided under
the two-party definitions — and both improve the segment's calibration
markedly, coverage rising from 0.708 to 0.750 and bias from −11.4 to −7.9.

## What is actually going on

The general component of `special_split` differs from `special_pooled_plain`
in exactly one way: its training set holds no special elections. Since every
special carries `pres_elec = False`, removing them changes what the `pres_elec`
term is estimated from — and the effect splits by segment, helping the
presidential-date races and hurting the midterm-date ones.

So the split arm is not really answering "do specials belong in the general
fit". It is answering "should `pres_elec` be estimated from general elections
only", and the answer on presidential-date races is yes. That is a finding
about the `pres_elec` term, arrived at sideways, and it connects directly to
the open issue in [`../README.md`](../README.md) about whether that term earns
its place at all.

## Recommendation

**No arm is adopted.** Pooled, nothing separates them under three of four
definitions, and the standing rule is that an interval spanning zero is
published as undecided rather than settled by argument.

For use rather than adoption, the segments are clear enough to act on:

- **Predicting a special election**, use `special_pooled_term` or
  `special_split` — they are equivalent there, and both beat the plain model
  on RMSE, bias and coverage.
- **Predicting a general election**, use `special_pooled_plain` on a midterm
  ballot and `special_split` on a presidential one.

That is not a satisfying single answer, and the reason is worth stating: 24
special elections spread over 17 fold dates is not enough evidence to decide
a pooled question, and the arms differ by less than the Monte Carlo noise
between two fits of the same model in three of the four definitions.

## Reproducing this

```bash
uv run legmodel score --variants special_pooled_plain special_pooled_term special_split
uv run legmodel compare special_pooled_plain special_pooled_term special_split
```

Every figure above is in `data/models/scorecard.csv` and
`data/models/variant_comparison.csv`, recomputable from
`data/models/holdout_predictions.csv.gz`. The composite arm's per-race
predictions carry a `component` column naming which fit produced each one.

**The `ballot_timing` segment has been renamed since these figures were
computed.** `presidential_general` became `presidential`, and
`midterm_general` split into `midterm_dem_pres` and `midterm_gop_pres`. The
figures above are quoted against the old three-level names; the midterm figure
covers what are now two levels. See
[`timing_result.md`](timing_result.md) for why the split was made.

See [`scoring.md`](scoring.md) for the fold schedule and the `ballot_timing`
segment, and [`is_special_result.md`](is_special_result.md) for the earlier
two-arm version of this question under the year-based schedule.
