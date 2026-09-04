# Local Workspace Context

Read this reference only when the user's configured notes, project-note filing, or Digital Employee repositories are relevant.

## Durable state

Canonical strategy note:

```text
/Users/renjie.pu/Documents/知识库/01. 战略与思考/工作方向与战略下注.md
```

Weekly operating notes:

```text
/Users/renjie.pu/Documents/知识库/03. 工作记录/<year>/周复盘/
<year>-W<week>｜MM-DD～MM-DD.md
_index.md
```

Active Digital Employee need notes:

```text
/Users/renjie.pu/Documents/知识库/03. 工作记录/数字员工/需求/<需求名>.md
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
Gateway: /Users/renjie.pu/Projects/digital_employee_gateway
Runner:  /Users/renjie.pu/Projects/digital-worker-runner
```

Use Gateway context for ingress, orchestration, SeaTalk/card interactions, and Gateway lifecycle. Use Runner context for execution, Sandbox provisioning/lifecycle, task context, runtime, and Runner interfaces. Read both only across the handoff.

Start with the smallest relevant concept or path search. Repository details should clarify priority, dependency, risk, or the next artifact, not turn a planning request into unrequested implementation. Reading is allowed when relevant; modifying code or repository state requires an explicit request.
