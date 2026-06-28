# Shared Skills Repository

This repository is the single source of truth for Jay's reusable skills.

## Layout

Each skill is stored as a normal directory at repo root:

```text
~/GitHub/skills/<skill-name>/SKILL.md
```

Do not copy skills into Alma, Claude Code, or Codex. Expose them with symlinks instead.

## Agent entry directories

- Alma: `~/.config/alma/skills`
- Claude Code: `~/.claude/skills`
- Codex: `${CODEX_HOME:-~/.codex}/skills`

## Sync links

Use the helper script:

```bash
cd ~/GitHub/skills
scripts/sync-skill-links.sh claude confluence jira web-access
scripts/sync-skill-links.sh alma newapi-channel-manager task-dashboard-review
scripts/sync-skill-links.sh codex jira web-access
```

To expose everything to one target:

```bash
scripts/sync-skill-links.sh claude --all
```

Prefer explicit skill lists over `--all`, because fewer exposed skills means less context noise and fewer accidental triggers.

## Manual symlink form

The script is just wrapping this pattern:

```bash
mkdir -p ~/.claude/skills
ln -s ~/GitHub/skills/jira ~/.claude/skills/jira
```

If an entry already exists, remove it first if it is a symlink, or back it up if it is a real directory.

## Update flow

```bash
cd ~/GitHub/skills
git pull
# symlinks do not need refreshing unless skill names changed
```

Because the entry points are symlinks, changes in this repo are immediately visible to Alma / Claude Code / Codex.
