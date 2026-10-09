---
name: build-clear-evidence-report
description: Create or restructure evidence-backed reports that explain complex work clearly to a defined audience, including evaluations, status updates, incident reviews, technical explainers, plans, and research summaries. Use when a durable report or HTML artifact needs clear hierarchy, traceable claims, or delivery QA; not for casual short answers or raw monitoring dashboards.
---

# Build Clear Evidence Report

Build a report that lets its intended reader understand the subject without reconstructing the analysis. Optimize for comprehension and trust, not document length or visual density.

## Establish the report contract

Before drafting, identify:

- **Audience:** who will read it, what they already know, and which terms need translation.
- **Reader outcome:** what they should understand, decide, explain, or do after reading.
- **Mode:** evaluation, status, incident, technical explanation, proposal, or research.
- **Evidence boundary:** available sources, missing evidence, sample size, time range, and comparability limits.
- **Deliverable:** chat response, Markdown, HTML, document, slide deck, or another requested format.

Infer these from the request and supplied materials when safe. Ask only when different answers would materially change the report. Preserve the user's language and chosen format.

For mode selection and mode-specific sections, read [references/report-modes.md](references/report-modes.md). Do not impose every section on every report.

## Build the message before the artifact

Create a message map with three reading depths:

1. **30 seconds:** what this is and the most important answer or current state.
2. **3 minutes:** the few reasons and evidence needed to understand why.
3. **Deep read:** method, detailed results, examples, limitations, and source trail.

Every included section must help answer at least one of these questions:

- What is this or what happened?
- What is the main finding or state?
- Why is that credible?
- What does it mean for this reader?

Remove material that answers none of them. Keep essential explanations in visible text; hover, footnotes, and appendices may add detail but must not carry the only copy of a key fact.

## Convert evidence into claims

Read [references/evidence-contract.md](references/evidence-contract.md) whenever the report contains quantitative claims, comparisons, scores, benchmarks, incident causality, or recommendations.

Maintain these distinctions in wording and presentation:

- **Observed fact:** directly supported by a cited source or artifact.
- **Derived result:** calculated from stated inputs and a reproducible rule.
- **Interpretation:** a reasoned explanation consistent with the evidence.
- **Recommendation:** a proposed action, not an observed fact.
- **Unknown:** unavailable, untested, not applicable, or inconclusive; name which one.

Never turn missing data into zero, incomparable evidence into a ranking, or an interpretation into a fact. For meaningful numbers, expose the value, unit, denominator or population, time range, method, and source wherever those fields affect interpretation.

## Write for the reader

- Lead with the answer, state, or explanation; provide method after the reader knows why it matters.
- Translate specialized terms on first use with a short plain-language definition. Keep identifiers and formal names intact where precision matters.
- Explain consequences in the reader's vocabulary. Prefer a concrete example over an extra abstract paragraph.
- Use headings that state the question or finding, not internal process names.
- Use a table for exact repeated comparisons, a chart for patterns or scale, a flow for sequence, and prose for nuance. Do not visualize a relationship that is clearer in one sentence.
- Put models, teams, versions, or other compared entities on rows when readers need to scan the same measures across them, unless the opposite orientation is materially clearer.

## Produce and verify the deliverable

Before delivery, score the report using [references/quality-standard.md](references/quality-standard.md) and complete the relevant checks in [references/qa-checklist.md](references/qa-checklist.md). A report is ready when it scores at least 85/100 and has no release blocker. If evidence constraints prevent that threshold, deliver an explicitly labeled draft or evidence-gap report instead of claiming completion.

For HTML reports:

1. Keep the primary reading path usable without hover or JavaScript.
2. Prefer semantic headings, tables, links, buttons, and figures.
3. Annotate important metric elements with `data-report-metric`, `data-unit`, and `data-source` when practical.
4. Represent non-results explicitly with `data-status` and `data-reason` rather than numeric placeholders.
5. Run `node scripts/validate_html_report.mjs <report.html>` from this skill directory.
6. Open the final file in a real browser and verify navigation, hover/focus behavior, responsive layout, and visible fallback content. Static validation does not replace runtime inspection.

## Deliver

Provide the artifact link and a concise handoff containing:

- the intended audience and reader outcome;
- the evidence boundary and any material caveat;
- validation performed and anything not verified.

Do not describe unperformed browser checks, source verification, or reproducibility checks as passed.
