# Local Workspace Context

Read this reference only when the user's configured notes, project-note filing, or Digital Employee repositories are relevant.

## Durable state

Canonical strategy note:

```text
~/Documents/KnowledgeBase/01-strategy/work-direction.md
```

Weekly operating notes:

```text
~/Documents/KnowledgeBase/03-work-records/<year>/weekly/
<year>-W<week>｜MM-DD～MM-DD.md
_index.md
```

Daily journals:

```text
~/Documents/KnowledgeBase/06-journal/<year>/<month>/YYYY-MM-DD.md
```

When a journal exists for a weekly daily entry, link its date in the heading, for example `### 周三 [[2026-09-09|09-09]]`. If it does not exist, keep the date as plain text and do not create an empty journal by default.

Active Digital Employee need notes:

```text
~/Documents/KnowledgeBase/03-work-records/digital-employee/needs/<need-name>.md
```

Use one note per active need with no date prefix. Completed needs move to `需求/archive/`; RCA notes stay in `问题排查/`.

At the start of `direction`, `bet`, `weekly`, `full`, or `rescue`, read the canonical strategy note before asking the user to restate durable decisions. Update only affected sections and `last_reviewed` after a confirmed strategy change; append one concise dated review entry when a direction or bet changes materially. Do not add transient work logs.

## Project-note promotion

Promote content when it is reusable across days:

- meeting conclusions, open questions, or engineering boundaries;
- metrics, queries, acceptance criteria, or monitoring methods;
- design decisions, state machines, and interface contracts;
- RCA root causes and fix plans.

Keep only today's result, interruption, Focus aggregate, restart point, and a `[[wikilink]]` in the weekly note.

When a project note is requested or confirmed and none exists, use the minimal structure: frontmatter plus `背景与目标`, `方案与结论`, `待确认`, `工程边界与下一步`, and `关联`. Ask once if the need name or location is ambiguous.

## Digital Employee repositories

```text
Gateway: ~/Projects/<gateway-repository>
Runner:  ~/Projects/<runner-repository>
```

Use Gateway context for ingress, orchestration, SeaTalk/card interactions, and Gateway lifecycle. Use Runner context for execution, Sandbox provisioning/lifecycle, task context, runtime, and Runner interfaces. Read both only across the handoff.

Start with the smallest relevant concept or path search. Repository details should clarify priority, dependency, risk, or the next artifact, not turn a planning request into unrequested implementation. Reading is allowed when relevant; modifying code or repository state requires an explicit request.
