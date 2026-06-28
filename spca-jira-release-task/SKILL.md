---
name: spca-jira-release-task
description: Use this skill whenever Jay asks to create, review, repair, or close SPCA Jira release tasks for Digital Employee versions, especially prompts like "提交 Jira 单到这个版本", "补几张 SPCA 单", "按发版内容创建 task", "把这些 Jira 状态改 DONE", or when a Jira version URL such as jira.shopee.io/projects/SPCA/versions/... is provided. This skill captures Jay's SPCA defaults: digital employee component, Jay as assignee/reporter/designer/developer, Low priority, controlled title categories, creation-before-confirmation review, and post-create verification.
---

# SPCA Jira Release Task Workflow

This skill handles Jay's Digital Employee release-task workflow in SPCA Jira. It is intentionally narrower than the generic Jira skill: use it to apply Jay's local SPCA conventions reliably, not as a general Jira reference.

## When To Use

Use this skill when Jay asks to:

- Create Jira tasks for an SPCA release/version.
- Convert release notes, changelog bullets, or implementation items into Jira tasks.
- Review or optimize Jira task titles for Digital Employee work.
- Fix fields on SPCA Jira tasks created incorrectly, especially assignee, component, priority, or status.
- Mark SPCA tasks as DONE/finished/closed.

If the user asks a general Jira question unrelated to SPCA release-task creation, use the generic `jira` skill instead.

## Required Tooling

Use `smc jira` through the shell. Prefer stable, non-interactive commands:

```bash
smc jira me
smc jira release list -p SPCA
smc jira issue create ... --no-input
smc jira issue list ... --plain --no-truncate --columns ...
smc jira issue view <KEY> --plain
smc jira issue assign <KEY> renjie.pu@shopee.com
smc jira issue move <KEY> Closed
```

Do not expose raw API tokens or credentials in chat. If config/auth fails, say config needs attention without printing secrets.

## Default Field Rules

For SPCA Digital Employee release tasks, apply these defaults unless Jay explicitly overrides them:

| Field | Default |
|---|---|
| Project | `SPCA` |
| Issue Type | `Task` |
| Priority | `Low` |
| Fix Version | the version Jay specified |
| Component | `digital employee` |
| Assignee | `renjie.pu@shopee.com` |
| Reporter | `renjie.pu@shopee.com` if supported; otherwise verify creator/reporter is Jay after creation |
| Designer | `renjie.pu@shopee.com` if the configured custom field exists |
| Developer | `renjie.pu@shopee.com` if the configured custom field exists |
| Labels | Do not invent labels by default |

Important: always pass the assignee explicitly with `-a renjie.pu@shopee.com`. If this is omitted, Jira may assign the task to the project default assignee, commonly `Kong`, which is wrong for Jay's SPCA release-task workflow.

### Custom Fields

The CLI supports `--custom key=value`, but custom field keys depend on the local Jira config created by `smc jira init`. Before setting Component/Designer/Developer through custom fields, inspect the available fields in `~/.agents/jira_config.json` or use `smc jira issue create --help` / project metadata as needed. If the field key is unknown, create the task with the safe core fields first, then verify and repair fields through Jira-supported commands or report the exact missing field mapping.

Do not guess custom field keys.

## Version Resolution

If Jay provides a Jira version URL like:

```text
https://jira.shopee.io/projects/SPCA/versions/203316
```

Resolve it as:

- Project: `SPCA`
- Version ID: `203316`
- Version name: query with `smc jira release list -p SPCA` and match the ID.

Use the version name with `--fix-version` when creating tasks, for example:

```bash
--fix-version "digital-employee-0625"
```

After creation, list the version contents to confirm the tasks landed in the target fixVersion.

## Title Format

Use this title pattern:

```text
[服务][类别] 简短标题
```

Examples:

```text
[Gateway][体验] 优化 DE 无法识别任务时的回复话术
[Gateway][修复] 修复意图识别接口丢失历史消息导致识别错误
[Runner][性能] 优化 QA warm pool 降低 DE 响应耗时
```

Keep titles concise. Put quantified impact, background, root cause, and implementation detail in the description rather than overloading the title.

## Category Taxonomy

Use these categories first. Keep the set compact so release notes remain scannable.

| Category | Use For |
|---|---|
| `功能` | New user-visible or operator-visible capability |
| `修复` | Bug fixes, wrong behavior, lost context/data, broken state transitions |
| `体验` | Wording, display, interaction, UX flow, confusing UI/message cleanup |
| `性能` | Response time, latency, startup time, throughput, efficiency improvements |
| `稳定性` | Timeout recovery, retry, fallback, resource reuse, failure handling |
| `可观测` | Alerts, logs, metrics, tracing, diagnosis, investigation support |

Judgment examples:

- Reply wording / fallback response copy -> `体验`
- Removing a visible technical prefix like `[new msg]` -> `体验`
- Missing `history msg` causing wrong intent detection -> `修复`
- Warm pool reducing QA response time by 30%+ -> `性能`
- Sandbox timeout/destroy/recreate/recover behavior -> `稳定性`
- Sandbox startup failure alert to a group -> `可观测`

If a category is ambiguous, propose a category and one alternative, then ask Jay to confirm before creation.

## Description Style

Write descriptions in compact Chinese. Include enough context for future release review:

```text
背景：...
目标：...
影响：...
```

For very small tasks, a single compact paragraph is fine. Do not add filler. Quantified effects such as `整体响应时间优化 30%+` belong in the description.

## Creation Workflow

1. Load the generic `jira` skill if command syntax is needed.
2. Verify auth and project context:

   ```bash
   smc jira me
   smc jira release list -p SPCA
   ```

3. Resolve the target version name from the provided version URL or ID.
4. Transform Jay's raw items into proposed Jira rows with: service, category, title, description, priority, fixVersion.
5. Show the proposal to Jay before mutating Jira, unless he explicitly says to create directly.
6. After Jay confirms, create tasks with explicit defaults.

Example command:

```bash
smc jira issue create \
  -p SPCA \
  -t Task \
  -s "[Gateway][体验] 优化 DE 无法识别任务时的回复话术" \
  -a renjie.pu@shopee.com \
  -y Low \
  --fix-version "digital-employee-0625" \
  -b "优化用户没有询问消息，或无法识别任务类型时的响应话术，提升兜底场景下的用户体验。" \
  --no-input
```

If Component/Designer/Developer custom field keys are confirmed, include them with `--custom`. If not confirmed, do not guess; verify after creation and repair where possible.

## Post-Create Verification

Always verify after creating or editing tasks. Use a stable list command:

```bash
smc jira issue list -p SPCA \
  --jql 'fixVersion = "digital-employee-0625"' \
  --plain --no-truncate \
  --columns KEY,SUMMARY,STATUS,ASSIGNEE,REPORTER,PRIORITY,LABELS \
  --order-by created --reverse
```

For each newly created task, confirm:

- FixVersion is the target version.
- Priority is `Low` unless overridden.
- Assignee is Jay / `renjie.pu@shopee.com`.
- Reporter is Jay.
- Component is `digital employee` if the field is available.
- Labels are not invented unless Jay specified them.

If a task is assigned to `Kong` or another project default assignee, immediately repair it:

```bash
smc jira issue assign SPCA-1234 renjie.pu@shopee.com
```

## DONE / Closed Mapping

SPCA may not have a literal `Done` transition. If Jay says to update status to `DONE`, treat the intent as completion. Try `Done` only if available; if Jira reports available states like:

```text
Doing, Closed, Waiting, Icebox, Blocking
```

then use `Closed` as the completion state:

```bash
smc jira issue move SPCA-1234 Closed
```

After moving, list the tasks again and confirm status.

## Repair Workflow For Existing Tasks

When Jay asks to fix a batch of already-created tasks:

1. Resolve the issue keys.
2. View or list current fields.
3. Apply only the requested/known-safe repairs.
4. Verify final fields.

Common repair commands:

```bash
smc jira issue assign SPCA-5510 renjie.pu@shopee.com
smc jira issue move SPCA-5510 Closed
```

For bulk operations, use a shell loop but keep it narrow to the explicit issue keys. Do not bulk-edit a whole version unless Jay asked for that scope.

## Communication Style

Be direct and compact. Jay prefers not to babysit field-level Jira details. Surface decisions that need judgment, especially category naming or unknown custom field keys. For routine defaults, apply the rule and report the result.

When reporting completion, include the issue keys and final important fields. Example:

```text
搞定，SPCA-5510 到 SPCA-5517 都在 digital-employee-0625，Priority=Low，Assignee/Reporter=Renjie Pu，Status=Closed。
```

## Known Pitfalls

- Do not rely on Jira's default assignee. It may assign to `Kong`.
- Do not assume `Done` is a valid status. In SPCA, completion may be `Closed`.
- Do not invent labels under this skill. Labels need Jay's explicit rule before being standardized.
- Do not print credentials from `.netrc`, config, debug output, or environment variables.
- Do not scrape interactive TUI output; use `--plain`, `--raw`, or explicit columns.
