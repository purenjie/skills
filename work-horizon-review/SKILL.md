---
name: work-horizon-review
description: Turns long-range work judgments into one measurable strategic bet,
  bounded weekly commitments, a protected daily anchor, and a lightweight weekly
  operating note. Use for direction, strategic-bet, weekly, daily, rescue, or
  review requests when reactive work is crowding out important work.
compatibility: Todoist and Raycast Focus integrations are optional. This user's
  local strategy, weekly, project-note, and repository conventions are documented
  separately and apply only in the configured workspace.
metadata:
  copilot-enabled-agents: codex
---

# Work Horizon Review

Build a closed loop from long-range judgment to today's protected action. The system must save more attention than it costs to maintain.

Do not begin by redesigning a task manager or journal. Diagnose whether the real failure is capture, classification, selection, or protection.

## Outcome contract

A complete workflow produces only what the selected horizon needs, while preserving this chain:

```text
2–5 year direction hypothesis
        ↓
one-year capability position
        ↓
one measurable 6–8 week strategic bet
        ↓
2–3 weekly work lines and 3–5 commitments
        ↓
one daily 主动推进 item and protected block
        ↓
lightweight evidence that updates the higher-level judgment
```

Across the full system:

- keep at most one primary one-year direction and one exploration branch;
- keep at most one primary strategic bet;
- protect at least one concrete strategic step each week;
- choose one daily winner and one independently useful artifact;
- allow real incidents to preempt, but immediately reschedule displaced work;
- continue without backfilling missed days or reconstructing a diary;
- keep daily weekly-note maintenance within about three minutes;
- preserve external contracts, current task truth, and production evidence boundaries.

## Core decision rules

Importance, urgency, and scheduling are different signals. For this user, Todoist P1 means high importance, not automatically “do now.” A due date is a real commitment or defended appointment; a weekly label represents selected capacity.

Use the smallest useful Eisenhower judgment:

| Lane | Evidence | Default handling |
| --- | --- | --- |
| Q1 | Active incident, real deadline, or someone materially blocked | Do now; schedule the displaced block's fallback. |
| Q2 | Strategic or compounding work without a current urgency source | Protect capacity. |
| Q3 | Noisy or low-leverage request that can be batched, clarified, delegated, or delayed | Make its capacity cost visible. |
| Q4 | Unvalidated or low-value work | Capture, defer, or stop. |

Do not infer urgency from a noisy message, an arbitrary Friday date, or “please take a look.” When evidence changes, a task may move lanes.

Before architecture, migration, instrumentation, or implementation work, define the decision or user outcome, its observable evidence, and whether a trustworthy baseline already exists. Treat platforms and rewrites as hypotheses, not goals.

## State boundaries

Keep each kind of state in one place:

```text
Scratch capture / Raycast Note → temporary input, not durable truth
Todoist → personal actions, current status, weekly commitments, real deadlines
Jira or another coordination tracker → multi-person coordination and formal acceptance
Weekly operating note → weekly choices, compact daily evidence, outcomes, judgments, interrupts
Project notes → reusable RCA, designs, metrics, queries, contracts, and operating methods
Canonical strategy note → durable direction, active bet, metrics, and capacity rules
```

Avoid duplicate checkboxes. When Jira already tracks the work, Todoist should normally contain only the user's next action and the Jira link. Git, sessions, and Focus are supporting evidence only: code is not deployment, and time investment is not completion.

Read [references/workspace-context.md](references/workspace-context.md) only when local paths, Digital Employee repositories, or project-note filing are relevant.

## Select the smallest mode

- `direction`: test 2–5 year hypotheses and choose a primary one-year capability position. Read [references/strategy.md](references/strategy.md).
- `bet`: turn the active direction into one measurable 6–8 week test. Read [references/strategy.md](references/strategy.md).
- `weekly`: choose this week's commitments and protected capacity, then create or update one weekly operating note. Read [references/weekly-file.md](references/weekly-file.md); read [references/strategy.md](references/strategy.md) only when the active bet must be created or reconsidered.
- `daily`: run a morning alignment and write only a compact dated entry into the weekly note. Read [references/daily-alignment.md](references/daily-alignment.md) and [references/weekly-file.md](references/weekly-file.md).
- `rescue`: recover a displaced strategic bet without backfilling. Read [references/daily-alignment.md](references/daily-alignment.md) and the rescue section of [references/strategy.md](references/strategy.md).
- `full`: run direction, bet, weekly, and daily in order. Read the references as each phase becomes active rather than loading every detail at the start.

Read [references/interruption-and-maintenance.md](references/interruption-and-maintenance.md) only when reactive work, preemption, maintenance load, or recurring failures are material. Read [references/integrations.md](references/integrations.md) only when Todoist, Jira, Raycast Focus, or their evidence is used.

For an ordinary daily check-in, do not rerun direction discovery, scan the entire backlog, or load every integration. Ask at most one decisive question when the answer changes the winner, artifact, or slot.

## Diagnose the bottleneck

Distinguish among:

- **Capture failure:** real commitments never reach a trusted system.
- **Classification failure:** ideas, projects, actions, and deadlines are mixed.
- **Selection failure:** the pool is trusted, but nothing clearly wins.
- **Protection failure:** a strategic item is selected but receives only leftover time.

Use concrete recent evidence. Do not prescribe more journaling when the actual failure is selection or protection.

## Shared operating rules

- Prefer a baseline, one-page decision, safe instrumentation, feature-flagged slice, or one thin end-to-end path over a long-lived branch.
- Timebox progress and define the smallest artifact that lowers restart cost.
- Require a primary protected slot, a fallback, exact preemption criteria, and a concrete recovery slot after justified interruption.
- Keep weekly work to 2–3 lines and 3–5 commitments; excess maintenance displaces a named commitment instead of silently expanding WIP.
- Promote reusable technical conclusions to project notes; keep only a result and `[[wikilink]]` in the weekly note.
- Treat user or runtime acceptance as authoritative when code, Git, sessions, or local evidence cannot establish production truth.
- Stop polishing the planning system once the next protected action is executable.

## Authorization and evidence

Read-only inspection of local notes, repositories, Todoist, and Focus evidence is allowed when relevant to the requested review.

Explicit `weekly` or `daily` invocation authorizes only the scoped current weekly-note update unless the user asks for read-only output. It does not authorize Todoist or Jira writes, strategy-note changes, project-note changes, code changes, starting Focus, or external communication.

Before any Todoist or Jira write, strategy-note update, project-note creation or edit, Focus launch, or other external mutation:

1. show the proposed change and scope;
2. obtain explicit confirmation unless the user already explicitly requested that exact mutation;
3. execute only that scope;
4. read back or otherwise verify the result.

Never persist credentials, tokens, private chat contents, sensitive incident details, or unsupported claims. When completion evidence conflicts materially, state the conflict rather than choosing the cleaner story.

## Done condition

End when the selected mode has produced a real tradeoff and the next action is concrete. For daily mode, the user must be able to start one protected block without another prioritization conversation. For weekly mode, the note must expose the current main line, progress, risk, and next protected slot within about 30 seconds.

Do not create another logging layer, backfill history, duplicate task state, or keep refining the workflow after it is usable.
