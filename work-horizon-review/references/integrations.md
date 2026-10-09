# Task and Focus Integrations

Read only the relevant section when Todoist, Jira, Raycast Focus, or their evidence is actually used.

## Todoist

Todoist is authoritative for the user's current actions, status, weekly commitments, and real deadlines.

For read-only discovery, verify the CLI and inspect only the selected project, view, or dates needed for this review. Use the Todoist skill and installed CLI help for supported filters. Do not list the full backlog by default:

```bash
td auth status
td task list --help
```

If `td` is missing, offer to install `@doist/todoist-cli`; authentication belongs to the user.

Classify candidates before selecting the week:

- **External commitment:** another person is waiting or a real deadline exists.
- **Strategic step:** advances the active 6–8 week bet.
- **Independent interrupt:** legitimate work that consumes capacity without advancing a selected line.
- **Long-range candidate:** valuable but not selected this week.
- **Unclear/immature:** an idea or container without a concrete next action.
- **Waiting/stale:** blocked, expired, or no longer worth active attention.

Discover and reuse existing labels instead of creating a new taxonomy by default.

Before any create, update, move, complete, delete, date, label, or filter write, show a grouped preview and obtain confirmation. Never complete or delete tasks merely to make a review look clean. Re-read affected tasks after writing.

## Jira or another coordination tracker

Use the coordination tracker for work that requires multiple people, formal ownership, acceptance, or an organizational workflow. Do not mirror its full state in Todoist; keep only the user's next action and a link when a personal reminder is useful.

Do not create, edit, transition, or comment on an issue without an explicit scoped request or confirmed preview. Read back the affected issue after writing.

## Raycast Focus

Focus is optional evidence of protected investment, never proof of completion.

Companion scripts:

```text
<skill-dir>/scripts/raycast_focus.py
<skill-dir>/scripts/raycast_focus_collector.py
```

Persistent collector:

```text
LaunchAgent: com.renjie.work-horizon-review.raycast-focus-collector
Database: ~/Library/Application Support/work-horizon-review/raycast-focus-sessions.db
Logs: ~/Library/Logs/work-horizon-review/raycast-focus-collector*.log
```

Useful commands:

```bash
python3 "<skill-dir>/scripts/raycast_focus.py" doctor
python3 "<skill-dir>/scripts/raycast_focus.py" report --today
python3 "<skill-dir>/scripts/raycast_focus.py" report --week --format json
python3 "<skill-dir>/scripts/raycast_focus.py" start-from-journal --minutes 50 --dry-run
launchctl print "gui/$(id -u)/com.renjie.work-horizon-review.raycast-focus-collector"
```

Data-source order:

1. local collector database populated by the LaunchAgent;
2. a schema-compatible Raycast Focus Stats `sessions.db`;
3. retained Unified Log events from subsystem `com.raycast.macos`, category `focus`;
4. report evidence as unavailable when none works—never interpret missing data as zero effort.

Rules:

- resolve `<skill-dir>` from the directory containing `SKILL.md`;
- use a chosen work action or exploration question as the Focus goal only when a timed session is wanted;
- if the note has no actionable anchor, do not launch or invent one; obtain an explicit goal and use a supported direct-start command, or skip Focus without adding compulsory note fields;
- show the dry-run goal and capacity-appropriate duration, then obtain explicit confirmation before launch; do not require Focus for rest, support, or a day with no proactive block;
- keep raw goals local and persist only bounded aggregates;
- use `log stream`, not periodic `log show`, for collection;
- recover the latest Goal from Raycast Preferences when a Summary lacks a Start/Goal event;
- keep the LaunchAgent running before a session begins because missed sessions may be unrecoverable;
- fail visibly if the database schema or log format becomes incompatible;
- the parser is based on the MIT-licensed Focus Stats extension at commit `dc8eb2b1efb00f6d5e1e65981801a44225ac88af`.
