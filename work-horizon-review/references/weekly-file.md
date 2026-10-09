# Weekly Operating Note

Use one local note per ISO week for selection, compact operational evidence, and synthesis. It is a decision-and-synthesis layer, not a second task manager, emotional diary, or proof that every week produced growth. Do not create a note merely to record a support-only conversation.

Read [workspace-context.md](workspace-context.md) for this user's path and naming conventions. Read [integrations.md](integrations.md) only when task or Focus evidence is needed.

Keep the yearly `_index.md` as navigation and quarterly aggregation only. Add a link for a new week without duplicating its contents.

## Source boundaries

- Todoist owns current actions, status, weekly commitments, and real deadlines.
- Jira or another coordination tracker owns multi-person workflow and acceptance.
- The weekly note owns selected work, compact evidence, outcomes, judgments, and interrupts.
- Project notes own reusable technical detail.
- The strategy note owns durable direction and bet decisions.

Mention only selected lines and material changes. Do not mirror a backlog or duplicate checkboxes.

## Facts and judgments

The weekly note preserves two different layers without letting either replace the other:

- **Facts:** concrete work in the user's familiar nouns and wording, including the real delivery state.
- **Current judgments:** a higher-level interpretation of what several facts mean, what remains unresolved, and what should be tested next.

Do not polish concrete facts into unfamiliar abstractions. Avoid phrases such as “close the loop”, “build a mechanism”, or “complete governance” unless the note also names the object, evidence, and changed decision.

An AI-generated judgment is provisional:

1. support it with at least two concrete facts when possible;
2. name the unresolved gap or disconfirming evidence;
3. preview it to the user before writing;
4. after confirmation, label it as a current judgment pending Friday review;
5. on Friday, confirm, revise, or remove it.

## Judgment-first structure

The top of the note should answer within about 30 seconds:

- what one or two evidence-backed themes deserve attention, if any;
- which facts support the current interpretation and what remains unresolved;
- what feasible next step or capacity negotiation comes next.

Do not add separate standing sections for a dashboard, a large weekly project plan, or generic tradeoff rules. Use this default structure:

```markdown
---
tags:
  - 工作/周复盘
week: <year>-W<week>
status: active
---

# <year>-W<week>｜MM-DD～MM-DD

## 本周关注与判断

> [!abstract] Concrete theme name
> - 事实：
> - 当前判断（待周末确认）：
> - 尚未解决：
> - 下一步：
> - 来源：[[#周三 MM-DD]]

## 每日进展

### 周三 [[YYYY-MM-DD|MM-DD]]

- [已上线] concrete result in the user's wording
- [待补] concrete missing part
- [问题] material interruption or symptom

## 周末回顾

### 本周确认的判断

### 关键结果

### 未完成与下周继续

## Todoist 承诺

> [!note]- 展开查看
> - ...
```

Keep empty Friday synthesis sections empty during the week; do not prewrite conclusions.

## Weekly attention and judgment

On the first alignment of the week:

1. read only the relevant durable direction, selected live commitments, and known capacity;
2. read the previous week's judgment and carryover when available, without rebuilding missing days;
3. if a capacity conflict exists, address it before selecting new work; choose at most one strategic step if feasible, otherwise consider shrinking or pausing it;
4. select up to two themes only when supported by concrete facts; name the unresolved gap and next advancement or negotiation, not a mandatory growth narrative;
5. preview newly generated or materially changed judgments before writing them;
6. keep the daily facts and links that let the user reconstruct why the judgment exists;
7. preview task-system changes separately.

Do not reproduce a complete project plan, acceptance checklist, or generic policy section in the weekly note. Those belong in Todoist, Jira, or project notes. If no evidence-backed pattern exists yet, keep concrete daily facts and leave the judgment section empty rather than manufacturing a theme.

Do not reconstruct a missing review or use Friday as a fake deadline for weekly intentions.

## Daily persistence contract

Raycast Note or another scratchpad may remain free-form. When routing it into the weekly note, preserve the user's task names and concrete language. Add only lightweight state labels, grouping, and links unless the user approves a broader rewrite.

Keep only useful new operational facts. A single fact is enough; do not fill a three-to-five-item quota or require an entry when nothing needs recording. Allow nested details when compression would make the record unfamiliar or ambiguous. Use only categories that carry information:

```markdown
### 周四 [[YYYY-MM-DD|MM-DD]]

- [已上线] a concrete accepted result
- [待验证] implementation or deployment awaiting evidence
- [待确认] an unresolved decision
- [问题] a material symptom or interruption
- [取舍] what displaced which planned work, only when it happened
```

Rules:

- preserve the user's nouns, identifiers, and distinction among developed, deployed, verified, and followed up;
- do not turn an unclear capture into a confident explanation; retain the wording and mark it `待确认`;
- status labels in the weekly note are snapshots, not a second task system;
- link to a project note instead of storing technical detail;
- when a matching daily journal exists, link the date in the heading, for example `### 周三 [[2026-09-09|09-09]]`;
- when the journal does not exist, keep a plain date heading and do not create an empty journal by default;
- do not require an end-of-day entry;
- missing days create no debt;
- distinguish a proposed scope/date change from one accepted by the relevant stakeholder;
- record a useful learning result only when supplied and worth retaining; do not demand an artifact for exploration;
- do not store emotional disclosures, reasons for distress, rest activities, mood scores, or excitement streaks; any separately requested personal reflection belongs outside this work-note workflow;
- keep maintenance to about three minutes.

## Real tradeoffs

Do not maintain a standing `本周取舍` section with generic rules. Record an actual displacement in the corresponding daily entry:

```markdown
- [取舍] Incident response displaced the baseline block; restart query saved. Rescheduling is pending workload agreement, not automatically assigned to tomorrow.
```

If no work was displaced, omit the field.

## Friday synthesis

Update the same note with:

- review every current judgment and explicitly confirm, revise, or remove it;
- keep only judgments grounded by the week's daily facts and delivery evidence;
- record the key results that actually exist, with appropriate acceptance or learning boundaries; do not require a fixed count or reusable asset for each;
- classify incomplete work as continue, waiting, renegotiate, or stop, with a real continuation or decision needed;
- carry forward necessary commitments and, only if feasible, one strategic step; repeated displacement calls for scope or allocation review, not catch-up work;
- keep Todoist links collapsed and navigational rather than reproducing task state.

Do not copy the daily entries into an essay. A confirmed judgment should explain what the concrete work collectively changed, not merely restate the task list in abstract language.

Set `status: reviewed` only when synthesis is genuinely complete. Otherwise leave it `active` or use an existing incomplete convention.

## Progressive migration of an existing long note

When the current week's note is already long, improve only that week unless the user explicitly expands scope:

1. remove numbered headings;
2. replace overlapping dashboard, weekly-plan, and generic tradeoff sections with `本周关注与判断`;
3. separate concrete facts from provisional interpretation;
4. preserve the user's familiar daily wording and link existing journal dates;
5. keep uncertain legacy material in one collapsed callout;
6. do not delete information, backfill missing days, modify task systems, or reorganize history in the first pass.

The collapsed source is transitional compatibility, not a permanent logging layer:

- create it only while migrating an existing note;
- do not add it to new weekly notes;
- after the two-week trial, promote reusable material to project notes and stop carrying the raw block forward;
- do not batch-clean historical weeks without a separate request.

## Lightweight usefulness check

After roughly a week of actual use, discuss whether the workflow helped; do not create a scorecard, daily survey, or tracking layer. Missing days do not restart a trial.

- Did a real conflict become easier to negotiate, or did a stopping boundary become usable?
- Was there room for a small interesting question or experiment when desired, without turning it into extra homework? Lack of excitement is not failure.
- Did alignment and note maintenance feel lighter, with no duplicate task state or compulsory entries?

Use only available evidence and the user's feedback. Do not require all three outcomes, justify rest through improved output, or judge success by whether every week delivered a strategic artifact. If the workflow adds pressure without practical help, remove rules or stop the trial rather than automate more tracking.

## Evidence conflicts

Todoist is authoritative for current task status. Git, sessions, Focus, and daily entries are supporting evidence. A weekly entry records a working judgment, not production truth.

When evidence conflicts materially, state the conflict and ask before persisting a completion claim.
