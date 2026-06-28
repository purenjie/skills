# Jira CLI — Full Command and Flag Reference

Complete command tree, aliases, argument signatures, and every flag. `SKILL.md`
covers setup and the common workflows; read this file when you need an exact
flag name, alias, or argument order for a specific command.

## Contents

- [Complete command tree](#complete-command-tree)
- [Global flags](#global-flags)
- [Top-level command flags](#top-level-command-flags)
- [Issue command flags](#issue-command-flags)
- [Epic command flags](#epic-command-flags)
- [Sprint command flags](#sprint-command-flags)
- [Project, board, and release flags](#project-board-and-release-flags)

## Complete command tree

All commands are invoked as `smc jira <command> ...`. Parent commands without
enough arguments show help.

| Full Command | Aliases | Description |
|--------------|---------|-------------|
| `smc jira init` | `initialize`, `configure`, `config`, `setup` | Initialize local Jira config |
| `smc jira help [command]` | none | Show help for a command |
| `smc jira issue` | `issues` | Issue command group |
| `smc jira issue list [optional text to query]` | `lists`, `ls`, `search` | List/search issues |
| `smc jira issue create` | none | Create an issue |
| `smc jira issue edit ISSUE-KEY` | `update`, `modify` | Edit an issue |
| `smc jira issue move ISSUE-KEY STATE` | `transition`, `mv` | Transition an issue |
| `smc jira issue view ISSUE-KEY` | `show` | View issue details |
| `smc jira issue assign ISSUE-KEY ASSIGNEE` | `asg` | Assign, default-assign, or unassign |
| `smc jira issue link INWARD_ISSUE_KEY OUTWARD_ISSUE_KEY ISSUE_LINK_TYPE` | `ln` | Link two issues |
| `smc jira issue link remote ISSUE_KEY WEBLINK_URL WEBLINK_TITLE` | `rmln` | Add a remote web link |
| `smc jira issue unlink INWARD_ISSUE_KEY OUTWARD_ISSUE_KEY` | `uln` | Remove an issue link |
| `smc jira issue comment` | `comments` | Issue comment command group |
| `smc jira issue comment add ISSUE-KEY [COMMENT_BODY]` | none | Add a comment |
| `smc jira issue clone ISSUE-KEY` | none | Clone an issue |
| `smc jira issue delete ISSUE-KEY` | `remove`, `rm`, `del` | Delete an issue |
| `smc jira issue watch ISSUE-KEY WATCHER` | `wat` | Add a watcher |
| `smc jira issue unwatch ISSUE-KEY WATCHER` | `unwat` | Remove a watcher |
| `smc jira issue worklog` | `wlg` | Worklog command group |
| `smc jira issue worklog add ISSUE-KEY TIME_SPENT` | none | Add a worklog |
| `smc jira epic` | `epics` | Epic command group |
| `smc jira epic list [EPIC-KEY]` | `lists`, `ls` | List epics or issues in an epic |
| `smc jira epic create` | none | Create an epic |
| `smc jira epic add EPIC-KEY ISSUE-1 [...ISSUE-N]` | `assign` | Add issues to an epic |
| `smc jira epic remove ISSUE-1 [...ISSUE-N]` | `rm`, `unassign` | Remove assigned epic from issues |
| `smc jira sprint` | `sprints` | Sprint command group |
| `smc jira sprint list [SPRINT_ID]` | `lists`, `ls` | List sprints or issues in a sprint |
| `smc jira sprint add SPRINT_ID ISSUE-1 [...ISSUE-N]` | `assign` | Add issues to a sprint |
| `smc jira sprint close SPRINT_ID` | `complete` | Close a sprint |
| `smc jira board` | `boards` | Board command group |
| `smc jira board list` | `lists`, `ls` | List boards in the active project |
| `smc jira project` | `projects` | Project command group |
| `smc jira project list` | `lists`, `ls` | List accessible projects |
| `smc jira release` | `releases` | Release/version command group |
| `smc jira release list` | `lists`, `ls` | List project versions/releases |
| `smc jira open [ISSUE-KEY]` | `browse`, `navigate` | Print/open project or issue URL |
| `smc jira me` | none | Print configured Jira login |
| `smc jira serverinfo` | `systeminfo` | Print Jira server info |
| `smc jira completion [bash\|zsh\|fish\|powershell]` | none | Generate shell completion |
| `smc jira version` | none | Print CLI version/build info |
| `smc jira man` | none | Generate man pages |
| `smc jira toggle` | none | Switch default project or board |

## Global flags

| Flag | Applies To | Description |
|------|------------|-------------|
| `--project <KEY>`, `-p <KEY>` | all commands | Use a Jira project for this command |
| `--debug` | all commands | Print Jira API request/response details |

## Top-level command flags

| Command | Description | Key Flags |
|---------|-------------|-----------|
| `init` | Initialize config | `--server`, `--login`, `--auth-type`, `--api-token`, `--project`, `--board`, `--force`, `--insecure` |
| `open [ISSUE-KEY]` | Print/open URL | `--no-browser`, `-n` |
| `serverinfo` | Print server info | `--table` |
| `completion [shell]` | Generate completion | valid args: `bash`, `zsh`, `fish`, `powershell` |
| `man` | Generate man pages | `--generate`, `-g`, `--output`, `-o` |
| `toggle` | Update defaults | `--project`, `--board` |
| `me` | Print login | none |
| `version` | Print version | none |

## Issue command flags

| Command | Description | Key Flags |
|---------|-------------|-----------|
| `issue list [text]` | List/search issues | `--type`, `-t`, `--resolution`, `-R`, `--status`, `-s`, `--priority`, `-y`, `--reporter`, `-r`, `--assignee`, `-a`, `--component`, `-C`, `--label`, `-l`, `--parent`, `-P`, `--history`, `--watching`, `-w`, `--created`, `--updated`, `--created-after`, `--updated-after`, `--created-before`, `--updated-before`, `--jql`, `-q`, `--order-by`, `--reverse`, `--paginate`, `--plain`, `--no-headers`, `--no-truncate`, `--delimiter`, `--comments`, `--raw`, `--csv`, `--columns`, `--fixed-columns` |
| `issue view ISSUE-KEY` | View details | `--comments`, `--plain`, `--raw` |
| `issue create` | Create issue | `--raw`, `--type`, `-t`, `--parent`, `-P`, `--summary`, `-s`, `--body`, `-b`, `--priority`, `-y`, `--reporter`, `-r`, `--assignee`, `-a`, `--label`, `-l`, `--component`, `-C`, `--fix-version`, `--affects-version`, `--original-estimate`, `-e`, `--custom`, `--template`, `-T`, `--web`, `--no-input` |
| `issue edit ISSUE-KEY` | Edit issue | `--parent`, `-P`, `--summary`, `-s`, `--body`, `-b`, `--priority`, `-y`, `--assignee`, `-a`, `--label`, `-l`, `--component`, `-C`, `--fix-version`, `--affects-version`, `--custom`, `--skip-notify`, `--web`, `--no-input` |
| `issue clone ISSUE-KEY` | Clone issue | `--parent`, `-P`, `--summary`, `-s`, `--priority`, `-y`, `--assignee`, `-a`, `--label`, `-l`, `--component`, `-C`, `--replace`, `-H`, `--web` |
| `issue move ISSUE-KEY STATE` | Transition issue | `--comment`, `--assignee`, `-a`, `--resolution`, `-R`, `--web` |
| `issue assign ISSUE-KEY ASSIGNEE` | Assign issue | no local flags; use `default` for default assignee and `x` to unassign |
| `issue delete ISSUE-KEY` | Delete issue | `--cascade` |
| `issue link INWARD OUTWARD TYPE` | Link issues | `--web` |
| `issue link remote ISSUE URL TITLE` | Add remote link | inherited `--web` |
| `issue unlink INWARD OUTWARD` | Unlink issues | `--web` |
| `issue comment add ISSUE-KEY [BODY]` | Add comment | `--web`, `--template`, `-T`, `--no-input`, `--internal` |
| `issue worklog add ISSUE-KEY TIME_SPENT` | Add worklog | `--started`, `--timezone`, `--comment`, `--new-estimate`, `--no-input` |
| `issue watch ISSUE-KEY WATCHER` | Add watcher | no local flags |
| `issue unwatch ISSUE-KEY WATCHER` | Remove watcher | no local flags |

## Epic command flags

| Command | Description | Key Flags |
|---------|-------------|-----------|
| `epic list [EPIC-KEY]` | List epics or epic issues | `--table`, plus issue-list flags except hidden `--type` and `--parent`: `--resolution`, `-R`, `--status`, `-s`, `--priority`, `-y`, `--reporter`, `-r`, `--assignee`, `-a`, `--component`, `-C`, `--label`, `-l`, `--history`, `--watching`, `-w`, `--created`, `--updated`, `--created-after`, `--updated-after`, `--created-before`, `--updated-before`, `--jql`, `-q`, `--order-by`, `--reverse`, `--paginate`, `--plain`, `--no-headers`, `--no-truncate`, `--delimiter`, `--comments`, `--raw`, `--csv`, `--columns`, `--fixed-columns` |
| `epic create` | Create epic | `--name`, `-n`, `--summary`, `-s`, `--body`, `-b`, `--priority`, `-y`, `--reporter`, `-r`, `--assignee`, `-a`, `--label`, `-l`, `--component`, `-C`, `--fix-version`, `--affects-version`, `--custom`, `--template`, `-T`, `--web`, `--no-input` |
| `epic add EPIC-KEY ISSUE-1 [...ISSUE-N]` | Add issues to epic | no local flags |
| `epic remove ISSUE-1 [...ISSUE-N]` | Remove assigned epic | no local flags |

## Sprint command flags

| Command | Description | Key Flags |
|---------|-------------|-----------|
| `sprint list [SPRINT_ID]` | List sprints or sprint issues | Sprint flags: `--state`, `--show-all-issues`, `--table`, `--columns`, `--fixed-columns`, `--current`, `--prev`, `--next`. Output/paging flags inherited from issue list: `--paginate`, `--plain`, `--no-headers`, `--no-truncate`, `--delimiter`, `--comments`, `--raw`, `--csv`. Issue filter flags are registered but hidden for this command. |
| `sprint add SPRINT_ID ISSUE-1 [...ISSUE-N]` | Add issues to sprint | no local flags |
| `sprint close SPRINT_ID` | Close sprint | no local flags |

## Project, board, and release flags

| Command | Description | Key Flags |
|---------|-------------|-----------|
| `project list` | List projects | `--plain`, `--no-headers`, `--delimiter` |
| `board list` | List boards | `--plain`, `--no-headers`, `--delimiter` |
| `release list` | List releases/project versions | `--plain`, `--no-headers`, `--delimiter` |
