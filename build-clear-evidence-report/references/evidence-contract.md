# Evidence contract

Use this contract to prevent polished presentation from outrunning the available evidence.

## Claim classes

Classify material statements while drafting:

| Class | Meaning | Required treatment |
|---|---|---|
| Observed fact | Directly present in a source, log, artifact, test, or accepted record | Cite or link the source; preserve relevant scope and timestamp. |
| Derived result | Computed from observed inputs | State the formula or rule, inputs, exclusions, and rounding. |
| Interpretation | An explanation consistent with evidence | Use calibrated language and identify meaningful alternatives. |
| Recommendation | A proposed action | Tie it to a reader outcome, evidence, constraint, and tradeoff. |
| Unknown | Evidence is absent or inconclusive | Name whether it is unavailable, untested, failed, not applicable, or genuinely unknown. |

The published report does not need to label every sentence, but readers must be able to distinguish these classes where confusion would change meaning.

## Numeric claim contract

For every material metric, capture the fields that affect interpretation:

- name and plain-language meaning;
- value and unit;
- denominator, population, or number of cases;
- time range or observation window;
- source;
- calculation or aggregation method;
- exclusions and missing data;
- uncertainty, variance, or the fact that only one run was observed.

Show these fields near the number, in a compact definition, or in an immediately reachable methods table. Do not make readers hunt through an appendix for a unit or denominator.

## Comparison contract

Before ranking subjects, verify:

- same or equivalent input;
- same task scope and acceptance criteria;
- relevant configuration is recorded;
- environment and tool access are equivalent or differences are disclosed;
- stopping rules are consistent;
- sample counts and missing cases are visible;
- the scoring rule was defined before interpreting results, or retrospective scoring is disclosed.

If comparability is partial, compare only the dimensions supported by the evidence. Use “not tested,” “test failed,” “not applicable,” or “not comparable” rather than a numeric placeholder.

## Source trail

Prefer the narrowest source trail that lets another reader verify a claim:

- link directly to the relevant task, file, test, log query, dataset documentation, or source record;
- give sources stable human-readable labels;
- distinguish primary evidence from summaries;
- record access dates for external or changeable sources when material;
- do not claim a link was opened or verified unless it was.

When sensitive evidence cannot be embedded, describe its type, owner, time range, and verification method without exposing restricted content.

## Evidence gaps

An evidence gap is an output, not an invitation to invent. State:

1. what is confirmed;
2. what remains unknown;
3. why the missing evidence matters;
4. the smallest additional observation that would resolve it.

