# Report modes

Choose the mode from the reader outcome, not from the source material's format. Combine modes only when the reader genuinely needs both; keep one primary mode so the report has a clear spine.

## Evaluation or comparison

Use when the reader needs to understand relative performance, quality, suitability, or tradeoffs.

Default spine:

1. Overall finding and what can or cannot be concluded
2. Evaluation scope and test scenarios
3. Compared subjects and configurations
4. Method, acceptance rules, and comparability limits
5. Result overview
6. Scenario-level evidence and explanations
7. Cost, reliability, capability, or other decision-relevant dimensions
8. Evidence boundary

Rules:

- Explain a score before relying on it.
- Show non-participation and its reason at the point of comparison.
- Do not continue ranking after a fairness assumption fails.

## Status or progress

Use when the reader needs an accurate current picture of work.

Default spine:

1. Current state in one sentence
2. Completed outcomes with evidence
3. Work in progress
4. Risks, blockers, and ownership
5. Next milestones or required decisions

Separate completed, verified, deployed, and accepted. Code completion does not prove runtime success.

## Incident or investigation

Use when the reader needs to understand an abnormal event and its causes.

Default spine:

1. Impact and current status
2. Timeline
3. Confirmed cause and contributing conditions
4. Evidence that supports or contradicts the cause
5. Containment, correction, and prevention
6. Remaining uncertainty

Do not label correlation as root cause. Keep observation, hypothesis, and confirmation status visible.

## Technical explanation

Use when the reader needs a correct mental model rather than a decision.

Default spine:

1. Plain-language definition and purpose
2. Concrete example or analogy
3. Components and boundaries
4. Sequence or data flow
5. Failure modes and practical implications
6. Deeper technical detail or references

Prefer one stable example carried through the explanation over several disconnected examples.

## Proposal or plan

Use when the reader needs to understand a recommended future approach.

Default spine:

1. Problem and desired outcome
2. Recommended approach
3. Why this approach fits the current constraints
4. Boundaries, interfaces, and affected areas
5. Execution stages and verification
6. Risks, rollback, and unresolved decisions

Keep current state, target state, proposal, and implementation status separate.

## Research or analysis

Use when the reader needs to understand findings from incomplete or exploratory evidence.

Default spine:

1. Research question and concise answer
2. Scope and sources
3. Findings ordered by importance
4. Supporting data and counter-evidence
5. Interpretation
6. Limitations and follow-up questions

Do not turn exploratory patterns into causal or universal claims.

## Mixed reports

If two modes are required, select one primary mode and embed only the necessary secondary section. Examples:

- A status report may include a short incident explanation for one delayed milestone.
- An evaluation may end with a proposal, but the recommendation must remain distinguishable from measured results.
- A technical explanation may include a small comparison table without becoming a full evaluation.

