# Report QA checklist

Apply only the checks relevant to the deliverable, but never skip evidence and primary-reading-path checks.

## Content

- The title says what the report explains.
- The opening gives the main answer or state before method detail.
- The 30-second summary is understandable without reading later sections.
- Each section answers one clear reader question.
- Repeated conclusions and methods have been consolidated.
- Specialized terms are explained on first use.
- Consequences are written in the intended reader's vocabulary.
- Facts, interpretations, recommendations, and unknowns are distinguishable.
- Limitations are specific and proportionate, not generic disclaimers.

## Evidence and data

- Every material conclusion maps to at least one source or derivation.
- Metric definitions match their displayed values.
- Values include units and the necessary denominator or population.
- Time ranges, sample sizes, aggregation, exclusions, and rounding are visible where material.
- Comparison inputs, configurations, and acceptance rules are equivalent or differences are disclosed.
- Missing, failed, untested, not applicable, and not comparable are distinct states.
- A single run is not presented as evidence of variance or general stability.
- Source labels and links identify the exact evidence rather than a generic home page.

## Structure and visuals

- Heading levels are continuous and same-level headings use the same visual style.
- Tables and charts each answer a named question.
- Compared entities and measures use an orientation that supports scanning.
- Axes, legends, sorting, color meanings, and precision are consistent.
- Color is not the sole carrier of status.
- Dense detail is moved to a deeper layer without hiding necessary context.
- Mobile or narrow layouts preserve reading order and do not clip tables silently.

## Interaction and accessibility

- Internal links land on exactly one visible target.
- External links are valid and clearly labeled.
- Hover content is also reachable by keyboard focus.
- Important explanations have visible-text fallback.
- Images have useful alternative text; decorative images use empty alternative text.
- Tables have headers and an accessible caption or label.
- Interactive controls have visible text or an accessible name.

## HTML-specific acceptance

- The file is self-contained when portability is required.
- The primary narrative remains available if JavaScript fails.
- IDs are unique and fragment links resolve.
- There are no placeholder links such as `href="#"`.
- Inline and local scripts parse and load.
- Tooltip triggers do not rely only on the native `title` attribute.
- Important metrics may use `data-report-metric`, `data-unit`, and `data-source` so deterministic validation can catch omissions.
- Non-results may use `data-status` and `data-reason` so they cannot be confused with numeric results.
- `node scripts/validate_html_report.mjs <report.html>` passes.
- The final file has been opened in the target browser and navigation, focus, hover, fallback content, and responsive behavior have been inspected.

Static checks do not prove that claims are true or that a visual is understandable. Perform a semantic review against the quality rubric after automated validation.

