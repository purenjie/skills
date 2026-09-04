# Weekly Operating Note

Use one local note per ISO week for Monday selection, compact daily evidence, and Friday synthesis. It is a decision-and-synthesis layer, not a second task manager or technical archive.

Read [workspace-context.md](workspace-context.md) for this user's path and naming conventions. Read [integrations.md](integrations.md) only when task or Focus evidence is needed.

Keep the yearly `_index.md` as navigation and quarterly aggregation only. Add a link for a new week without duplicating its contents.

## Source boundaries

- Todoist owns current actions, status, weekly commitments, and real deadlines.
- Jira or another coordination tracker owns multi-person workflow and acceptance.
- The weekly note owns selected work, compact evidence, outcomes, judgments, and interrupts.
- Project notes own reusable technical detail.
- The strategy note owns durable direction and bet decisions.

Mention only selected lines and material changes. Do not mirror a backlog or duplicate checkboxes.

## Dashboard-first structure

The top of the note must answer within about 30 seconds:

- what is the main line;
- what meaningful outcomes have landed;
- what risk could change the plan;
- when the next protected block occurs.

Use a single-screen dashboard and keep `已完成` to three to five outcomes rather than task status:

```markdown
---
tags:
  - 工作/周复盘
week: <year>-W<week>
status: active
---

# <year>-W<week>｜MM-DD～MM-DD

> [!summary] 本周驾驶舱
> - 本周主线：
> - 已完成：
> - 当前风险：
> - 下一保护时段：

## 本周承诺

- 战略步骤：
- 外部交付：
- 独立插单预算：

## 容量与保护安排

- 主时段：
- 第一次 fallback：
- 最终 fallback：
- 可打断条件：
- 维护预算：

## 本周明确不做

- ...

## 每日对齐

### 周一 MM-DD

- 结果：
- 主动推进：
- 下一步：

## 周末复盘

### 本周判断

### 关键结果与价值

### 战略下注进展

### 中断与维护负载

### 判断变化与沉淀候选

### 下周衔接
```

Keep empty Friday synthesis sections empty during the week; do not prewrite conclusions.

## Weekly selection

On the first alignment of the week:

1. read the current durable bet and live task state;
2. read only the previous week's final judgment and carryover when available;
3. choose 2–3 active work lines and 3–5 commitments;
4. include at least one strategic step and at most one primary strategic bet;
5. set protected time, fallbacks, preemption criteria, and an interrupt budget;
6. name one to three explicit non-goals;
7. create or update the dashboard-first note;
8. preview any task-system changes separately.

Do not reconstruct a missing review or use Friday as a fake deadline for weekly intentions.

## Daily persistence contract

Morning alignment may make a detailed decision, but persist only three to five short bullets. Use the categories that carry information; omit the rest:

```markdown
### 周四 MM-DD

- 结果：one to three bounded outcomes or continuation points
- 用户问题或中断：only when it materially changed capacity
- 新发现：a judgment that changes the plan
- 主动推进：the protected artifact or its actual progress
- 下一步：only when it reduces restart cost
```

Rules:

- do not repeat unchanged protection rules;
- do not copy Todoist or Jira status;
- link to a project note instead of storing technical detail;
- do not require every category;
- do not require an end-of-day entry;
- missing days create no debt;
- keep maintenance to about three minutes.

## Friday synthesis

Update the same note with:

- one-sentence weekly judgment;
- three to five key outcomes with evidence, value, and reusable assets;
- strategic-bet progress and current conclusion;
- Focus investment when useful, explicitly separated from completion;
- justified and unjustified interruptions and what they displaced;
- recurring failure classes and prevention assets;
- changed judgments and promotion candidates;
- one strategic carryover, necessary commitments, and the next protected slot.

For each weekly commitment, decide complete, continue with a new concrete step, waiting with owner and trigger, or stop. Do not copy the daily entries into an essay.

Set `status: reviewed` only when synthesis is genuinely complete. Otherwise leave it `active` or use an existing incomplete convention.

## Progressive migration of an existing long note

When the current week's note is already long, improve only that week unless the user explicitly expands scope:

1. remove numbered headings;
2. add the dashboard;
3. compress each visible daily entry to three to five bullets;
4. preserve uncertain legacy material in one collapsed callout;
5. do not delete information, backfill missing days, modify task systems, or reorganize history in the first pass.

The collapsed source is transitional compatibility, not a permanent logging layer:

- create it only while migrating an existing note;
- do not add it to new weekly notes;
- after the two-week trial, promote reusable material to project notes and stop carrying the raw block forward;
- do not batch-clean historical weeks without a separate request.

## Two-week system-health check

After two weeks, judge the workflow by four observable tests:

- the current state is clear within 30 seconds of opening the note;
- daily weekly-note maintenance stays within about three minutes;
- the same checkbox is not maintained in multiple systems;
- at least one proactive outcome survives even during an interrupt-heavy week.

If these fail, remove fields or narrow the workflow before adding automation.

## Evidence conflicts

Todoist is authoritative for current task status. Git, sessions, Focus, and daily entries are supporting evidence. A weekly entry records a working judgment, not production truth.

When evidence conflicts materially, state the conflict and ask before persisting a completion claim.
