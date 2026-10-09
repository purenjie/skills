---
name: work-horizon-review
description: Aligns work with real capacity, interest, and longer-term direction.
  Use for direction, strategic-bet, weekly, daily, rescue, or review requests
  when reactive work, overload, or low motivation makes prioritization hard.
  Supports concrete progress, commitment negotiation, and stopping boundaries.
metadata:
  copilot-enabled-agents: codex
---

# Work Horizon Review

Help the user make work manageable and retain room for curiosity and choice. Connect longer-term direction to concrete action when useful; do not turn every day into a test of growth. The system must save more attention than it costs.

Todoist and Raycast Focus integrations are optional. Local strategy, weekly, project-note, and repository conventions apply only in the configured workspace.

Do not begin by redesigning a task manager or journal. First distinguish actual overload, difficulty stopping, and low interest from capture, classification, selection, or protection problems. Fatigue is not automatically a planning failure.

## Outcome contract

Use the following chain for strategic work, not as a daily output quota:

```text
2-5 year direction hypothesis
        ↓
one-year capability position
        ↓
one 6-8 week strategic test
        ↓
1-2 evidence-linked weekly themes when useful
        ↓
a feasible next step, or explicit scope/capacity renegotiation
        ↓
lightweight evidence that updates the judgment
```

Across the full system:

- keep at most one primary one-year direction and one exploration branch;
- keep at most one primary strategic bet;
- aim to protect a small strategic step when capacity permits; otherwise make the conflict visible and shrink, defer, or renegotiate rather than create catch-up debt;
- select at most one proactive item, preferably within existing work; fulfilling commitments, reducing load, or stopping without a new task can be a valid daily outcome;
- keep external commitments explicit; after preemption, agree a feasible recovery slot or leave rescheduling pending, never invent capacity or silently move a deadline;
- continue without backfilling missed days or reconstructing a diary;
- keep daily weekly-note maintenance within about three minutes;
- preserve external contracts, current task truth, and production evidence boundaries.

## Core decision rules

Importance, urgency, and scheduling are different signals. For this user, Todoist P1 means high importance, not automatically “do now.” A due date is a real commitment or defended appointment; a weekly label represents selected capacity.

Use the smallest useful Eisenhower judgment:

| Lane | Evidence | Default handling |
| --- | --- | --- |
| Q1 | Active incident, real deadline, or someone materially blocked | Handle the urgency; make displaced commitments and feasible recovery or renegotiation explicit. |
| Q2 | Strategic or compounding work without a current urgency source | Protect feasible capacity, not automatic priority over interest or recovery. |
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
Weekly operating note → evidence-linked attention and judgments, familiar daily facts, outcomes, interrupts
Project notes → reusable RCA, designs, metrics, queries, contracts, and operating methods
Canonical strategy note → durable direction, active bet, metrics, and capacity rules
```

Avoid duplicate checkboxes. When Jira already tracks the work, Todoist should normally contain only the user's next action and the Jira link. Git, sessions, and Focus are supporting evidence only: code is not deployment, and time investment is not completion.

Read [references/workspace-context.md](references/workspace-context.md) only when local paths, Digital Employee repositories, or project-note filing are relevant.

## Select the smallest mode

- `direction`: test 2-5 year hypotheses and choose a primary one-year capability position. Read [references/strategy.md](references/strategy.md).
- `bet`: turn the active direction into one 6-8 week test with observable evidence, not a guaranteed delivery deadline. Read [references/strategy.md](references/strategy.md).
- `weekly`: select evidence-linked themes or expose a capacity conflict, then update one weekly note when there is something useful to retain. Read [references/weekly-file.md](references/weekly-file.md); read [references/strategy.md](references/strategy.md) only when reconsidering the bet.
- `daily`: choose feasible work, a concrete renegotiation, or a stopping boundary; persist only useful operational facts. Read [references/daily-alignment.md](references/daily-alignment.md) and [references/weekly-file.md](references/weekly-file.md).
- `rescue`: assess whether to resume, shrink, or pause displaced work without backfilling. Read [references/daily-alignment.md](references/daily-alignment.md) and the rescue section of [references/strategy.md](references/strategy.md).
- `full`: run direction, bet, weekly, and daily in order. Read the references as each phase becomes active rather than loading every detail at the start.

Read [references/interruption-and-maintenance.md](references/interruption-and-maintenance.md) only when reactive work, preemption, maintenance load, or recurring failures are material. Read [references/integrations.md](references/integrations.md) only when Todoist, Jira, Raycast Focus, or their evidence is used.

For an ordinary daily check-in, do not rerun direction discovery, scan the entire backlog, or load every integration. Ask at most one decisive question when the answer changes the action, capacity conflict, or stopping boundary. Do not repeat known feelings as a questionnaire.

## Diagnose the bottleneck

Distinguish among:

- **Capacity conflict:** real obligations exceed feasible time; help negotiate scope, sequence, timing, or support instead of prescribing more discipline.
- **Low interest or agency:** work is feasible but uninviting; look for a concrete question, small experiment, or visible improvement, preferably inside an existing obligation.
- **Difficulty stopping:** the user reports guilt, worry, or busyness as relief; respond supportively before adding goals. Do not infer a diagnosis or an avoidance pattern from a busy calendar.
- **Capture failure:** real commitments never reach a trusted system.
- **Classification failure:** ideas, projects, actions, and deadlines are mixed.
- **Selection failure:** the pool is trusted, but nothing clearly wins.
- **Protection failure:** a strategic item is selected but receives only leftover time.

Use recent concrete evidence, not more journaling. When busyness provides temporary relief from distress, do not abruptly insist on empty time, introspection, or an exciting task. Offer a less demanding activity, support from a trusted person, or a tolerable stopping boundary without making it another assignment. Rest does not need to earn its place through future productivity.

This is a work-alignment skill, not therapy. Do not probe for private causes to complete a plan. If distress is persistent or impairing, gently suggest professional support; immediate safety concerns take precedence over planning. Keep sensitive disclosures out of operational notes and reusable skill instructions.

## Shared operating rules

- For delivery, define acceptance and prefer a small verified result over a long-lived branch. For exploration, a tested guess, clarified misconception, or useful failed experiment is enough; no mandatory document.
- Curiosity, autonomy, and quick feedback are valid selection signals, not daily quotas. Do not demand excitement or justify every task through promotion, long-term value, or future productivity.
- Keep learning within agreed capacity. Do not require full project documentation before a motivating experiment, refill freed time automatically, or prescribe compensatory evening work.
- Preserve the user's concrete nouns and wording in daily evidence. Do not replace familiar facts with polished abstractions or merge unrelated items into one theme.
- Separate facts from interpretation. Every weekly judgment must name its concrete evidence, unresolved gap, and next test; treat it as provisional until the user confirms it.
- Preview AI-generated weekly judgments before writing them. After confirmation, keep them marked as current or pending Friday review rather than silently turning them into durable conclusions.
- Keep up to two weekly themes only when they reveal a meaningful pattern across concrete work; leave them empty otherwise. Do not maintain a parallel project plan or abstract category hierarchy inside the weekly note.
- For chosen work, attach one feasible slot or first-available-block rule. After displacement, reschedule only with real capacity; otherwise name the pending negotiation or pause rather than inventing a fallback.
- Make weekly tradeoffs visible only when a real conflict exists. If new work must enter, name which core outcome moves instead of maintaining a ritual list of non-goals.
- Promote reusable technical conclusions to project notes; keep only a result and `[[wikilink]]` in the weekly note.
- Treat user or runtime acceptance as authoritative when code, Git, sessions, or local evidence cannot establish production truth.
- Stop when the next action or boundary is usable. An explicit decision to add no task can be sufficient; do not turn fatigue into a new optimization project.

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

End when the selected mode provides usable help without adding unnecessary work. Daily alignment may end with one feasible next action, a concrete pending negotiation, or a stopping/support decision with no new task. Do not require a block, artifact, or written entry for every outcome. Weekly notes should expose evidence-backed judgments or a capacity conflict within about 30 seconds; leave themes empty when unsupported.

Do not create another logging layer, backfill history, duplicate task state, or keep refining the workflow after it is usable.
