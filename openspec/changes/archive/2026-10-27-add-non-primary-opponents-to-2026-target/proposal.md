# Proposal

## Why

The 2026 forecast target covers 46 races, but the Secretary of the
Commonwealth's general-election candidate list shows 57 contested legislative
races with a Democrat on the ballot. The 11 missing races have a Democrat
facing a candidate who qualified by nomination papers (unenrolled, independent,
or a minor party), so they never appear in the primary roster the target is
built from. The adopted training definition, `two_party_or_strongest`, already
trains on 93 historical races of exactly this kind, so the omission is a
roster gap, not a modelling limit. The election is November 3, so the fix has
to land as a new forecast revision before then.

## What Changes

- Add a reviewed, committed supplement of 2026 legislative candidates who are
  on the general-election ballot without a primary nomination, transcribed from
  the Secretary's 2026 State Election Candidates page with its URL and as-of
  date.
- Build the target candidate roster from primary nominees plus that
  supplement, so the 11 races below enter the target:
  - House: 1st Barnstable, 2nd Bristol, 1st Franklin, 5th Hampden,
    5th Norfolk, 4th Suffolk, 10th Suffolk, 2nd Worcester
  - Senate: Norfolk & Plymouth, Suffolk & Middlesex, Worcester & Middlesex
- Replace the per-race review for several non-Democrats with a fixed
  comparison rule that mirrors the adopted training definition: the
  Republican nominee where one stands, otherwise the single non-Democrat.
  Review is required only when no Republican stands and several non-Democrats
  do. The four target races that already have a third candidate (5th Essex,
  3rd Hampden, 7th Worcester, Senate 1st Middlesex) keep their Republican
  comparison.
- Publish the expanded 57-race target, its 14-day finance, and its forecast as
  a new revision (`14d-r2`) using the same 2026-10-20 finance cutoff. The
  existing `60d` and `14d` snapshots, their target, and their finance files
  stay byte-for-byte unchanged and remain scorable.
- Point the interactive explorer and the forecast writeup at the `14d-r2`
  revision. The explorer, which assumes a Republican opponent throughout,
  labels each opponent by ballot designation: party letter, margin and
  likely-winner wording, incumbency option, receipts label, and chart sides.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `election-forecast`: the target roster includes nomination-paper candidates
  from a reviewed source, the comparison candidate follows a fixed rule that
  matches the adopted definition, and a revised target is published as a new
  revision without changing earlier snapshots.
- `interactive-forecast-web`: the explorer names the non-Democratic side by
  the opponent's ballot designation instead of assuming a Republican.

## Impact

- `src/legmodel/forecast.py`: roster builder, comparison selection, and
  source verification.
- `src/legmodel/forecast_finance.py`, `forecast_run.py`, `interactive.py`,
  `config.py`: revision-aware target, finance, snapshot, and bundle paths.
- New data: `data/forecast/2026/nomination_candidates.csv`,
  `data/forecast/2026/target_r2.csv`, `data/forecast/2026/finance_14d_r2.csv`,
  `data/forecast/2026/snapshots/14d-r2/`, and
  `data/forecast/2026/interactive/14d-r2/`.
- `web/` explorer (presentation, data validation, build scripts) and
  `artifacts/2026_massachusetts_legislative_forecast.*` move to the revision.
- `docs/forecasting.md` documents the supplement, comparison rule, and
  revision.
- The OCPF filer match for the new candidates uses the existing `ocpf-cli`
  roster path. If it cannot resolve a candidate, the gap is reported and that
  race falls back to the no-money component rather than being dropped.
