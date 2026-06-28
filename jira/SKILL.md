---
name: jira
description: Manages Jira content via the smc jira CLI. Lists, searches, and views issues; creates, edits, clones, deletes, transitions, assigns, comments on, links, watches, and logs work on issues; manages epics and sprint membership; lists boards, projects, and releases; opens Jira URLs; initializes config and switches default project or board. Triggers on Jira, issue key, ticket, bug, story, task, sprint, epic, board, backlog, JQL, transition, assign, comment, worklog, watcher, and release workflows. Does not handle SWP approval or workflow tickets; use swp instead. Does not manage Confluence pages; use confluence instead.
---

# Jira Issue Management CLI

Manage Jira Server issues, epics, sprints, boards, projects, releases, and local
CLI config from the command line with `smc jira`.

For the exhaustive command tree, aliases, and every flag, read
[reference/commands.md](reference/commands.md). The sections below cover setup,
the command surface, and the behaviors that are easy to get wrong.

## Setup

Install the CLI first, then run `init` once to write the local config. Get a Jira API token,
PAT, password, or mTLS client credentials first.

```bash
smc install jira

# Pick the auth type that matches your server (bearer is the Shopee default):
smc jira init --server https://jira.shopee.io --auth-type bearer --login "$JIRA_LOGIN" --api-token "$JIRA_API_TOKEN" --project "$JIRA_PROJECT" --board "$JIRA_BOARD"
# --auth-type basic  → same flags, sends login + token/password
# --auth-type mtls   → drop --api-token, answer the certificate prompts

smc jira me                      # verify auth
smc jira project list --plain    # verify access
```

## Command surface

Run `smc jira <command> --help` for any command, or read
[reference/commands.md](reference/commands.md) for full signatures and flags.

- **issue** — `list [text]`, `view`, `create`, `edit`, `clone`, `move` (transition),
  `assign`, `delete`, `link` / `link remote` / `unlink`, `comment add`,
  `watch` / `unwatch`, `worklog add`
- **epic** — `list [EPIC-KEY]`, `create`, `add EPIC-KEY ISSUE...`, `remove ISSUE...`
- **sprint** — `list [SPRINT_ID]`, `add SPRINT_ID ISSUE...`, `close SPRINT_ID`
- **board / project / release** — `list`
- **config & utility** — `init`, `toggle` (switch default project/board), `open`,
  `me`, `serverinfo`, `completion`, `version`, `man`

Two flags apply everywhere: `-p`/`--project <KEY>` overrides the active project
for one command, and `--debug` dumps the raw API request/response.

## Key behaviors

These are the non-obvious mechanics worth knowing before running commands.

- **Config & auth resolution.** Config lives at `~/.agents/jira_config.json`.
  `JIRA_`-prefixed env vars override config values (e.g. `JIRA_API_TOKEN`,
  `JIRA_AUTH_TYPE`). The API token is resolved in order: `JIRA_API_TOKEN`, then a
  `.netrc` entry matching the Jira host and login, then the config file. `basic`
  sends login + token/password; `bearer` sends a bearer token; `mtls` uses the
  configured client certificates and only sends bearer auth if a token is present.
- **`init` vs `toggle`.** `init` writes project, board, server, auth, issue types,
  custom fields, epic fields, Jira version, and timezone. To change only the
  default project or board, use `smc jira toggle --project <KEY>` / `--board <NAME>`
  instead of regenerating all metadata.
- **Issue keys.** Most issue commands accept a full key (`PROJ-123`) or a numeric
  key (`123`). Numeric keys are expanded with the active project, so
  `smc jira -p PROJ issue view 123` resolves to `PROJ-123`. Non-numeric input is
  uppercased.
- **Automation output.** There is no global `--json`. For machine-readable output
  use `--raw` (JSON API response, on `issue list`/`view`/`create`), or `--plain`
  with `--columns`, `--no-headers`, `--delimiter`, or `--csv`. Lists default to an
  interactive TUI when a TTY is present, so always pass `--plain` (or
  `--table --plain`) for stable output in scripts and agent workflows.
- **Interactive prompts.** `create`, `edit`, `comment`, and `worklog` prompt for
  missing fields unless you supply all required fields plus `--no-input`.
- **Text input.** For long bodies/comments, prefer `--template <file>` or stdin.
  Precedence: `--body` beats `--template` for `issue create`; a positional comment
  body beats `--template` for `comment add`.
- **JQL & date filters.** `issue list` combines a raw `--jql` with the other filter
  flags and optional text search. Date filters accept `today`, `week`, `month`,
  `year`, date strings like `2026-05-13`, and Jira period strings like `-10d`.
- **Custom fields.** `--custom key=value` only works for fields configured during
  `init`. The key is the lowercased field name with spaces replaced by hyphens,
  e.g. `--custom story-points=3`.

## Guidelines for agents

1. **Check config and auth first.** Run `smc jira me` and `smc jira project list --plain`.
   If config is missing, run `smc jira init`.
2. **Resolve the target before mutating.** Use `issue list`, `issue view`,
   `epic list`, or `sprint list` before editing, transitioning, deleting, closing,
   or bulk-assigning, so you act on the right key.
3. **Use stable, non-interactive flags.** Pass required fields plus `--no-input`
   for `create`/`edit`/`comment`/`worklog`, and `--plain`/`--columns`/`--csv` for
   anything you parse — never scrape the TUI.
4. **Confirm destructive operations with the user.** `issue delete` (especially
   `--cascade`) and `sprint close` have no `--yes` flag and cannot be undone.
5. **Validate after mutating.** Re-run `issue view`, `epic list <epic>`, or
   `sprint list <sprintId>` to confirm the change landed.
6. **Reach for `--debug` only when troubleshooting** — it dumps full request and
   response payloads.

## Related Skills

- **swp** — SWP workflow tickets. Use swp for SPACE platform approval tickets (SWP-NNNNN); use jira for development issues.
- **confluence** — Wiki documentation. Reference Confluence pages in Jira issues.

## Examples

```bash
# Search, list, view
smc jira issue list "login fails" --plain --columns key,summary,status,assignee
smc jira issue list --jql 'priority = High AND status != Done' --plain
smc jira issue list --paginate 0:50 --raw
smc jira issue view PROJ-123 --comments 5 --plain

# Create / edit (non-interactive)
smc jira issue create --type Bug --summary "Login fails with expired SSO session" --priority High --label bug --body "Impact, repro, expected, actual." --no-input
echo "Description from stdin" | smc jira issue create --type Task --summary "Document runbook" --no-input
smc jira issue edit PROJ-123 --summary "Login fails after session expiry" --no-input

# Transition, assign, comment, log work
smc jira issue move PROJ-123 "In Progress" --comment "Starting investigation"
smc jira issue move PROJ-123 Done --resolution Fixed --assignee "$(smc jira me)"
smc jira issue assign PROJ-123 alice@shopee.com   # `default` to default-assign, `x` to unassign
smc jira issue comment add PROJ-123 "Verified in staging" --no-input
smc jira issue worklog add PROJ-123 "2h 30m" --comment "Debugged rollout" --no-input

# Links and watchers
smc jira issue link PROJ-123 PROJ-456 Blocks
smc jira issue link remote PROJ-123 https://confluence.example.com/display/ENG/Runbook Runbook
smc jira issue watch PROJ-123 alice@shopee.com

# Epics and sprints
smc jira epic list --table --plain --columns key,summary,status
smc jira epic add PROJ-100 PROJ-123 PROJ-124         # epic key FIRST, then issues
smc jira sprint list --current --plain --columns key,summary,status
smc jira sprint add 42 PROJ-123 PROJ-124
smc jira sprint close 42

# Projects, boards, releases, defaults
smc jira board list --plain
smc jira release list --plain
smc jira toggle --project PROJ          # switch the default project
smc jira open PROJ-123 --no-browser     # print the URL instead of opening it
```

### Workflow: read, verify, then mutate

```bash
smc jira issue list "login fails" --plain --columns key,summary,status,assignee
smc jira issue view PROJ-123 --comments 3 --plain
smc jira issue edit PROJ-123 --summary "Login fails after session expiry" --no-input
smc jira issue view PROJ-123 --plain     # confirm the change
```

### Workflow: move work through a sprint

```bash
smc jira sprint list --current --plain --columns key,summary,status,assignee
smc jira issue move PROJ-123 "In Progress" --comment "Starting investigation"
smc jira issue worklog add PROJ-123 2h --comment "Initial diagnosis" --no-input
smc jira issue move PROJ-123 Done --resolution Fixed --comment "Verified in staging"
```

## Common mistakes

| Mistake | Fix |
|---------|-----|
| Expecting a global `--json` flag | Use `--raw` on `issue list`/`view`/`create`, or `--csv`/`--plain` |
| Forgetting `--plain` on list commands in automation | Add `--plain`, plus `--columns` or `--no-headers` when parsing |
| Numeric issue key with the wrong active project | Pass `-p <KEY>` or use the full key like `PROJ-123` |
| Letting create/edit/comment/worklog prompt in agent workflows | Provide required fields and `--no-input` |
| Deleting or closing without confirmation | Confirm with the user first; there is no `--yes` flag |
| Partial or ambiguous assignee/watcher | Use an exact email, username, or display name; `x` unassigns, `default` default-assigns |
| Assuming `epic remove` takes the epic key | `epic remove` takes issue keys; `epic add` takes the epic key first |
| Expecting `--template` to override inline text | Inline `--body` or a positional comment body takes precedence |
| Looking for attachment or comment-deletion commands | This CLI adds comments but does not manage attachments or delete comments |
