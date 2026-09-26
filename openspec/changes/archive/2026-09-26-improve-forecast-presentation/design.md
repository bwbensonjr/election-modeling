# Design

## Context

The static application currently receives candidate names and a single race-level incumbency status in the interactive manifest. Its formatting helpers render PVI as a signed number and margins as `D +4`/`R +2`, while overview and matchup templates duplicate candidate and margin presentation. The target roster already identifies each candidate's party and incumbent flag during target construction, but those fields are not carried into the published web bundle; municipality is not currently part of the target schema.

## Goals / Non-Goals

**Goals:**

- Add a presentation-ready candidate identity contract to the interactive bundle for both sides of every matchup.
- Keep display formatting centralized so overview and detail views cannot drift.
- Preserve full-precision numeric fields and all existing scenario behavior, ordering, URL behavior, and provenance checks.
- Make the incumbent asterisk discoverable to screen-reader and keyboard users.

**Non-Goals:**

- Changing the forecast model, candidate selection rule, PVI calculation, or margin calculation.
- Replacing the immutable forecast snapshot or changing the scenario controls.
- Displaying every municipality in a district; the municipality is the candidate's source-roster municipality.

## Decisions

1. **Use structured candidate metadata, then format in the browser.** Extend each race's manifest metadata with candidate objects containing the source name, party letter, municipality, and incumbent boolean. Keep the source name and fields separate rather than storing only a preformatted string so validation and future presentation changes remain possible. The browser formatter will produce `Name* (D-Municipality)` and use the same function in the overview and matchup.

   **Alternative considered:** store only the final display strings. This is simpler for the browser but loses semantic fields needed for validation, accessibility, and future styling, so it is rejected.

2. **Derive party letters from locked candidate party values at export time.** Democratic and Republican candidates map to `D` and `R`; any unsupported party must fail bundle generation or be handled by an explicit presentation rule rather than silently receiving a wrong label. The current 2026 invariant is a Democratic-versus-Republican matchup, but the manifest remains authoritative.

   **Alternative considered:** infer the second party from `incumbent_status` or from the margin sign. This would conflate model state with candidate identity and is rejected.

3. **Carry municipality from the authoritative candidate roster.** Add a normalized candidate municipality field to the roster/target join, require it for published 2026 candidates, and propagate it into the manifest. The value represents the candidate's municipality, not the district's full municipality list. Missing or ambiguous source values should block publication rather than produce a misleading parenthetical.

   **Alternative considered:** derive a municipality from district geography. That cannot identify where a candidate lives and is rejected.

4. **Centralize display semantics in presentation helpers.** Add candidate formatting, party-directed likely-margin formatting, and PVI formatting helpers. Use `Math.round`/existing whole-number locale formatting for display only; retain signed `point_margin` and `PVI_N` for calculations and sorting. Use `Even` or `Neutral` consistently for rounded zero values, with tests fixing the selected wording.

   **Alternative considered:** inline strings in each template. This risks inconsistent labels between the overview and detail views and is rejected.

5. **Treat the asterisk as semantic text, not color or decoration alone.** Render the asterisk in the candidate label and include a concise visible legend or explanatory note near the matchup/overview. The accessible name should preserve the candidate identity and announce incumbency in text.

## Risks / Trade-offs

- [Existing committed fixtures lack new metadata] → Update TypeScript fixtures and bundle-validation fixtures, and regenerate/verify the committed bundle as part of implementation.
- [Candidate source data cannot provide municipality for every nominee] → Add explicit validation and report the affected race/source record; do not fall back to district-wide geography.
- [Long candidate labels reduce table readability on mobile] → Preserve responsive table behavior, allow normal wrapping, and test narrow viewport rendering and accessible names.
- [Party formatting assumptions break with a future non-major-party comparison] → Validate party values in the export and keep the party mapping in one helper so a future presentation change is explicit.

## Migration Plan

1. Extend target/bundle metadata and validation, then update unit fixtures.
2. Implement shared formatting and apply it to overview, matchup, and summary labels.
3. Regenerate or verify the 2026 interactive bundle, run TypeScript/unit/browser/accessibility tests, and build the static site.
4. Deploy through the existing GitHub Pages workflow. Roll back by reverting the application and bundle changes; forecast snapshots remain untouched.
