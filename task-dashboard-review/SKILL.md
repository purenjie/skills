# Skill: task-dashboard-review

Use this skill when Jay asks to review, inspect, clean up, analyze, or plan from his Todoist task list. Trigger examples: `巡检任务清单`, `帮我看看今天做什么`, `分析 todoist`, `整理任务`, `任务驾驶舱`, `今天怎么安排`, `帮我拆下一步行动`.

## Mode

Default mode is **semi-auto**.

Low-risk actions may be executed directly after analysis:
- Rename vague tasks into action-oriented titles.
- Add descriptions that clarify completion criteria.
- Add subtasks for the next concrete action.
- Add lightweight due dates within the current week when the intent is clear.
- Convert an Inbox item into a parent task with subtasks when project creation is unavailable or too heavy.

Ask before high-impact actions:
- Delete/archive tasks or projects.
- Complete tasks.
- Move a task far into the future.
- Change priority to P1.
- Create many tasks/projects at once.
- Any change that could surprise Jay.

## Principles

- Todoist is Jay\s cockpit, not a debt ledger.
- Protect Today. Today should contain only a few tasks that can actually be touched or closed.
- Prefer strong judgment. Do not bounce vague categorization back to Jay unless missing information would cause real damage.
- Every task should be one of: action, clarification-needed action, project, thought/emotion, material, principle/memory, noise.
- Vague project-like tasks must not remain as ghost tasks. Add: completion definition, expected time horizon, and next action.
- For projects, split only the next useful action unless a small scaffold clearly reduces friction.

## Standard Read Scope

For a lightweight review:
1. Read Todoist Today including overdue.
2. Read Inbox.
3. Search or inspect P1/P2 tasks if the day feels overloaded.

For a weekly/deep review:
1. Read Today and overdue.
2. Read Inbox.
3. Inspect active projects with unclear next actions.
4. Look for stale, repeated, or postponed items.

Use Todoist MCP tools when available, especially:
- `todoist__find-tasks-by-date` for Today/overdue.
- `todoist__find-tasks` for Inbox, labels, priorities, and keyword searches.
- `todoist__search` for targeted lookup.
- `todoist__fetch` / `todoist__fetch-object` for details.
- `todoist__add-tasks`, `todoist__update-tasks`, `todoist__add-projects`, `todoist__add-sections` for writeback.

If MCP is not exposed in the current thread, tell Jay directly and ask him to reconnect/restart the thread, or use any available authenticated Todoist path.

## Review Output

Keep the reply compact and judgment-forward:

1. **整体判断** — one short paragraph on the current task system state: overload, fuzzy debt, missing next actions, or clean enough to execute.
2. **今天优先** — 1-3 concrete tasks to focus on.
3. **需要整理的任务** — vague or risky tasks, with suggested rewrite or handling.
4. **我已处理** — direct Todoist edits already made under semi-auto mode.
5. **需要你确认** — only destructive or high-impact actions.

Avoid dumping the entire task list unless Jay asks for it.

## Rewrite Rules

Good task format:
`动词 + 对象 + 时间/场景 + 完成标准`

Examples:
- Bad: `WorkBuddy 调研`
- Good: `今天用 WorkBuddy 跑 1 个真实工作场景，记下 3 条观察`
- Bad: `投资复盘`
- Good: `复盘本周持仓偏离，决定是否用增量资金补防守端`

For touch tasks, enforce a decision boundary:
- Touch at most 1-3 times.
- Then decide: project / defer with review date / delete or park.

## Writeback Style

- Use a small amount of emoji when it improves scanability, especially for parent tasks or sections.
