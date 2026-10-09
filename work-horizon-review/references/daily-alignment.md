# Daily Morning Alignment

Use this workflow to choose feasible work, resolve a capacity conflict, or establish a stopping boundary. The goal is not to plan the whole day or manufacture motivation. A day of essential commitments without extra growth work is valid.

Read [weekly-file.md](weekly-file.md) before updating persistent state. Read [interruption-and-maintenance.md](interruption-and-maintenance.md) only when reactive work is material, and [integrations.md](integrations.md) only for integrations actually used.

## Read the minimum current state

Default to:

1. the current weekly note and its latest daily entry;
2. the temporary capture note when the user supplies or exposes it;
3. only the Todoist view needed for this week's commitments, today's real deadlines, and current interrupts;
4. the relevant project-note continuation point when it lowers restart cost.

Read the canonical strategy note only when the active bet is missing, stale, or contradicted. Read Focus evidence only when it changes the judgment about protected investment. Do not scan the full backlog or reconstruct missing days.

Use already stated workload, energy, and preferences; do not ask for daily mood scores. Ask at most one decisive question, only when the answer changes the action, negotiation, or stopping boundary. Do not load personal reflections just to infer the user's emotional state; if they request that context, distinguish original notes from AI-generated interpretations.

## Three-minute capture triage

Triage only supplied captures with continuing value. Keep the scratchpad free-form; do not require a new template, daily entry, or end-of-day cleanup.

At the next morning alignment, route only items with continuing value:

- personal next action → Todoist;
- multi-person coordination or formal acceptance → Jira or the configured tracker;
- reusable RCA, reason, design, metric, or decision → project note;
- meaningful supplied outcomes or changes worth retaining → weekly note, without a daily count quota;
- no future value → discard without archiving.

Do not copy the full item across systems. When Jira owns the work, Todoist normally keeps only the user's next action and Jira link. Do not require an end-of-day cleanup.

When the scratchpad uses the user's own task names or shorthand, preserve those nouns in the weekly daily entry. Add state labels and grouping without translating concrete facts into unfamiliar management language. If a higher-level pattern emerges, propose it separately for `本周关注与判断`; preview that judgment before writing and keep it provisional until Friday review.

This triage is a decision preview, not write authorization. Follow the authorization rules in `SKILL.md` before changing anything except the scoped weekly note.

## Morning decision

### Check capacity before selecting more work

Identify unavoidable obligations, their minimum acceptance boundaries, and the usable time left after meetings, on-call duties, verification, and likely interrupts. Use rough estimates only when helpful; do not invent precision or reconstruct a full schedule.

If obligations exceed capacity, handle one concrete conflict first. Propose a scope reduction, sequence change, revised date, delegation, or request for support. Draft the smallest useful stakeholder message without sending it:

```text
今天 A 需要完成验证，B 会阻塞联调。我能保证这两项；
C 如果也必须今天完成，需要缩小范围、顺延其中一项或找人协助，请一起确认。
```

A proposal is not an agreed change. Keep unresolved commitments visible and do not claim a deadline moved before confirmation. If all obligations are genuinely urgent and the user lacks authority to reduce them, identify who can decide or help. Do not add a strategic block, suggest working faster, or assume evening capacity.

### Choose at most one proactive item when feasible

Protect genuine incidents and hard commitments. Within the remaining feasible choices, prefer a concrete question the user wants to understand, a small experiment, or an immediately useful improvement. Embed it in existing delivery when possible; it is not an extra daily assignment.

The active strategic bet is a candidate, not an automatic winner. Do not repeat career or long-term-value explanations unless they change a decision. A motivating experiment may precede systematic documentation; do not make completing an old case study a prerequisite for all new exploration.

Curiosity is optional. If nothing appeals, choose a low-friction necessary step, fulfill only existing commitments, reduce load, or stop. Do not require daily excitement, an interest score, or a streak.

### Match the result to the kind of work

- **Delivery:** define the smallest accepted result and relevant verification; keep production and safety standards unchanged.
- **Exploration:** name one question and a small test, such as predicting a failure then comparing the observed behavior. A clarified misconception or useful failed experiment can be sufficient. No mandatory document or claim of production completion.
- **Reduction or recovery:** a concrete negotiation, stopping boundary, or support choice can be the result. Rest does not need an artifact or proof that it improves productivity.

Fit the duration to actual capacity. A short trial may be enough; do not default to a 50- or 90-minute block. Avoid vague work labels, but do not turn ordinary rest or companionship into a measurable deliverable.

### Define when enough is enough

For chosen work, agree what can reasonably be finished or handed off today, and what remains queued or pending negotiation. Stopping need not wait for an empty backlog or the absence of anxiety. Do not silently abandon external obligations or critical on-call coverage.

Do not automatically refill freed time, add learning after early completion, or prescribe compensatory evening work after a break. If workload remains structurally excessive, address allocation with the relevant owner rather than repeating self-discipline advice.

When the user reports that staying busy offers relief from distress, acknowledge that function without diagnosing it. Do not abruptly demand empty time, meditation, introspection, or a more exciting goal. Offer a less demanding activity, trusted company, or support without requiring a choice or assignment. Follow the support and safety boundaries in `SKILL.md`; do not turn this into a therapy session or record private explanations in the weekly note.

### Protect only a feasible block

When work is chosen, attach one concrete slot or a first-available-block rule. Add a fallback only for likely or actual disruption, and only if capacity exists. After displacement, save the restart point and agree a feasible slot, a reduced scope, or pending renegotiation. Do not auto-book the next morning or create catch-up debt.

Use [interruption-and-maintenance.md](interruption-and-maintenance.md) for competing incidents or recurring support work. Batch only what can actually wait; use response windows matched to the role, not fixed task-count limits.

## Separate the conversation from persistence

Keep the conversation brief and use only relevant fields. This is an optional shape, not a form to complete:

```markdown
## 今日对齐
- 今天先做／先协商：
- 做到这里就可以停：
- 时段或待确认的安排：
```

Name a real displacement only when it exists. Omit task and slot fields for a support-only conversation; do not require the user to turn it into a work plan.

Persist only useful operational facts under the weekly-note contract. No note update is required when there is no new operational fact. Do not log emotional disclosures, support activities, or why stopping feels difficult. An authorized entry may record an agreed scope change, not the private explanation behind it. Omit unchanged rules, empty categories, and duplicated task state.

Use `每日进展` as the weekly section name. When a matching daily journal already exists, link the date in the heading, for example `### 周三 [[2026-09-09|09-09]]`; otherwise keep a plain date and do not create an empty journal by default.

Use trusted evidence for yesterday. A commit proves code exists, not deployment; Focus proves investment, not completion. A proposed scope or schedule change is still pending until confirmed. Resolve material evidence conflicts within the one-question daily limit, or preserve the uncertainty.

## Done condition

Finish at the smallest useful outcome; do not require all of these:

- **Work chosen:** one feasible next action, an appropriate acceptance or learning boundary, and a concrete slot or first-available-block rule.
- **Overload exposed:** one actual conflict, a concrete scope/order/support proposal, and the person or decision needed; unconfirmed changes remain pending.
- **Stopping or support:** a tolerable boundary or acknowledgment without adding a task, artifact, timer, or written entry. The user need not prove they feel better.

For chosen work, make likely or actual displacement explicit without inventing recovery capacity. Persist a compact operational entry only when useful and authorized. End before another prioritization or self-improvement exercise becomes necessary.

If weekly-note maintenance regularly exceeds about three minutes, remove fields before adding automation or another log.
