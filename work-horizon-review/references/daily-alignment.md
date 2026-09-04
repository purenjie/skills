# Daily Morning Alignment

Use this workflow to decide what receives the first meaningful block, what may legitimately preempt it, and how displaced proactive work resumes. The goal is not to plan the whole day.

Read [weekly-file.md](weekly-file.md) before updating persistent state. Read [interruption-and-maintenance.md](interruption-and-maintenance.md) only when reactive work is material, and [integrations.md](integrations.md) only for integrations actually used.

## Read the minimum current state

Default to:

1. the current weekly note and its latest daily entry;
2. the temporary capture note when the user supplies or exposes it;
3. only the Todoist view needed for this week's commitments, today's real deadlines, and current interrupts;
4. the relevant project-note continuation point when it lowers restart cost.

Read the canonical strategy note only when the active bet is missing, stale, or contradicted. Read Focus evidence only when it changes the judgment about protected investment. Do not scan the full backlog or reconstruct missing days.

Ask about meetings, incidents, or hard commitments only when they are not discoverable and would change the winner or slot.

## Three-minute capture triage

Treat Raycast Note or another scratchpad as temporary input, not another task system. A lightweight capture shape is:

```markdown
## 今日主动

- [ ] one protected item

## 今日义务

- [ ] bounded hard commitments

## 临时捕获

- undecided observations, requests, or symptoms
```

At the next morning alignment, route only items with continuing value:

- personal next action → Todoist;
- multi-person coordination or formal acceptance → Jira or the configured tracker;
- reusable RCA, reason, design, metric, or decision → project note;
- yesterday's one to three most important outcomes or changes → weekly note;
- no future value → discard without archiving.

Do not copy the full item across systems. When Jira owns the work, Todoist normally keeps only the user's next action and Jira link. Do not require an end-of-day cleanup.

This triage is a decision preview, not write authorization. Follow the authorization rules in `SKILL.md` before changing anything except the scoped weekly note.

## Morning decision

### Choose one winner

Use this order:

1. a real incident or hard external commitment when delay has material cost;
2. otherwise, the next concrete step of the active strategic bet;
3. otherwise, the most valuable important-but-not-urgent commitment that leaves a reusable result.

Choose one主动推进 item, not several equal priorities. Other work may appear as hard commitments or maintenance.

### Define one artifact

Translate the winner into something that can exist after one 50- or 90-minute block: a baseline, verified query, bounded fix and regression, deployment verification, protocol decision, focused dashboard, or RCA with a confirmed boundary and next hypothesis.

Reject vague anchors such as “optimize”, “work on monitoring”, “fix bugs”, or “look into it.” When enough evidence exists, produce the decision artifact instead of expanding instrumentation.

### Protect the block

Specify:

- primary slot or first-available-block rule;
- same-day fallback when possible;
- final fallback, normally the next working day's first block;
- exact preemption criteria.

“After urgent work” and “when I have time” are not slots. Ordinary bugs, confirmations, reviews, and help requests wait for a maintenance window.

### Bound the rest

- identify today's real hard commitments;
- choose at most one or two maintenance windows;
- name one to three attractive or noisy things that will not receive active investment today.

Use [interruption-and-maintenance.md](interruption-and-maintenance.md) when an issue may preempt the block or maintenance repeatedly exceeds budget.

## Separate the conversation from persistence

The conversational decision may be complete:

```markdown
## 今日对齐

- 主动推进：
- 今日最小产物：
- 为什么今天选它：

## 保护安排

- 主时段：
- 同日 fallback：
- 最终 fallback：
- 可打断条件：

## 外部承诺与维护

- 今日硬承诺：
- 维护窗口与预算：

## 今日不做

- ...
```

Do not persist all of this every day. The weekly note receives only three to five short bullets using the persistence contract in [weekly-file.md](weekly-file.md). Omit unchanged protection rules, empty categories, and duplicated task status.

Use trusted evidence for yesterday. A commit proves code exists, not deployment; Focus proves investment, not completion. Ask one concise question only when a conflict changes today's winner or the durable record.

## Done condition

Daily alignment is complete when:

- one winner and one concrete artifact are clear;
- primary, fallback, and preemption conditions are explicit;
- reactive work has a bounded lane;
- the not-do boundary prevents predictable drift;
- the compact weekly-note entry is written when persistence is authorized;
- the user can start without another prioritization conversation.

If weekly-note maintenance regularly exceeds about three minutes, remove fields before adding automation or another log.
