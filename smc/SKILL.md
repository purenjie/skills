---
name: smc
description: >
  SMC plugin manager — install, update, remove, and search CLI plugins.
  Use when a required CLI tool or capability is missing and the agent needs to
  discover, install, update, remove, or inspect plugins. Triggers on:
  "install plugin", "smc install", "missing tool", "missing capability",
  "find a skill", "find a plugin", "search plugins", "list available plugins",
  "auto install plugin", "install the right skill", "update plugins".
---

# smc

SMC is the plugin manager for Shopee CLI tools. It installs, updates, removes, and searches plugins that integrate with AI agents.

## Commands

| Command                  | Action                       | Description                                                                        | Key Flags               |
| ------------------------ | ---------------------------- | ---------------------------------------------------------------------------------- | ----------------------- |
| `smc install <name>`     | Install plugin from registry | Downloads and installs a plugin; auto-triggered when command not found             | supports `name@version` |
| `smc update`             | Update all plugins           | Checks all installed plugins for updates and batch updates with confirmation       |                         |
| `smc update <name>`      | Update specific plugin       | Updates a single plugin to its latest published version                            |                         |
| `smc remove <name>`      | Uninstall plugin             | Removes plugin binary, skill files, IDE symlinks, and registry entry               |                         |
| `smc search <keyword>`   | Search plugin registry       | Searches available plugins by keyword in name or description                       |                         |
| `smc list`               | List available plugins       | Displays available plugins with latest version, installed version, and description |                         |
| `smc plugin info <name>` | View plugin details          | Shows plugin metadata, installed version, and full version history                 |                         |
| `smc version`            | Show installed versions      | Displays all installed plugins with their current versions (alias for list)        |                         |
| `smc login`              | Authenticate to SPACE        | Obtains SPACE token (required before first use or when expired)                    |                         |
| `smc token status`       | Check token validity         | Shows token owner, expiration time, and remaining validity period                  |                         |
| `smc token export`       | Export raw token             | Outputs space_token string for use in scripts or environment variables             |                         |
| `smc reset`              | Reset smc state              | Clears all plugin installations and configuration (use with caution)               |                         |

## Global Flags

- `-c, --cluster <env>` selects the SPACE/PAM environment for any smc command and plugin command.
- Default environment is `shopee`.
- Common environments include `shopee`, `shopeetest`, `seamoney`, `sea`, `ee-zone`, `id-bank`, `ph-bank`, `sg-bank`, `npt`, and non-live bank environments such as `id-bank-nonlive`, `ph-bank-nonlive`, `sg-bank-nonlive`.
- Put `-c` before or after the plugin name; both `smc -c shopeetest pam ...` and `smc pam -c shopeetest ...` are valid.
- Use the same `-c` value for `smc login`, token checks, plugin management, and plugin calls when working outside the default `shopee` environment.

## Key Patterns

- Plugin names are lowercase identifiers (e.g. `ekscli`, `servicecmdb`, `ipcli`).
- `smc install name@version` installs a specific version; without `@version` it installs the latest published version.
- Always call plugins via `smc <plugin> <subcommand>` (e.g. `smc ekscli cluster list`). SMC automatically injects authentication tokens and records audit logs.
- Use `-c <env>` or `--cluster <env>` when the task targets a non-default environment.
- Installed plugins automatically register their AI skills.

## Instructions

- Before using an installed plugin for a task, first run `smc update` to check whether any installed plugins have updates available.
- If `smc update` reports available updates, apply them before continuing with `smc <plugin> <subcommand>`.
- If the user asks for a capability and there is no clearly matching installed skill or tool, first run `smc list` to inspect available plugins and their installed versions.
- Compare the user's request against plugin descriptions and choose the smallest plugin that clearly matches the requested capability.
- If `smc list` is too broad or the best match is unclear, use `smc search <keyword>` with task-specific keywords to narrow candidates.
- If needed, run `smc plugin info <name>` before installation to confirm the best match.
- If a clear match is found and it is not installed, run `smc install <plugin-name>`.
- If multiple plugins need to be installed together, use a single command such as `smc install plugin1 plugin2 plugin3` instead of chaining multiple install commands.
- After installation, use the newly installed plugin's skill or run the plugin via `smc <plugin> <subcommand>`.
- If a CLI tool is not found but the plugin name is already known, run `smc install <tool-name>`.
- If a command fails with AUTH_EXPIRED, run `smc login` to refresh the token.
- Do not guess plugin names when the need is capability-based; discover candidates from `smc list` first.

## Discovery Workflow

When the user asks for a new capability, follow this order:

1. run `smc list`.
2. Read plugin descriptions and identify the best match for the user's request.
3. If needed, run `smc search <keyword>` or `smc plugin info <name>` to disambiguate between candidates.
4. Install only the selected plugin with `smc install <name>`.
5. Continue the task using the installed plugin's commands or skill instructions.

When the required plugin is already installed, follow this order:

1. run `smc update`.
2. If updates are available, complete the update first.
3. Continue the task using `smc <plugin> <subcommand>` or the installed plugin skill.

## Related Skills

Plugins installed via smc each have their own SKILL.md with detailed usage instructions.

## Examples

### Install plugins

```bash
# Install latest version
smc install ekscli

# Install specific version
smc install ekscli@1.2.3

# Install multiple plugins at once
smc install ekscli servicecmdb logcli
```

### Search and discover plugins

```bash
# List all available plugins in registry
smc list

# Search by keyword
smc search kubernetes

# View detailed plugin info and version history
smc plugin info ekscli
```

### Manage plugins

```bash
# List available plugins with installed version
smc list

# Show installed versions
smc version

# Update all plugins
smc update

# Update specific plugin
smc update ekscli

# Remove a plugin
smc remove ekscli
```

### Token management

```bash
# Login to SPACE (opens browser)
smc login

# Login to the test environment
smc login -c shopeetest

# Check token status and expiration
smc token status

# Check token status for a non-default environment
smc token status -c id-bank

# Export token for scripts
export SPACE_TOKEN=$(smc token export)
```

### Call plugins through smc

```bash
# Check for plugin updates before using installed plugins
smc update

# If ekscli is not installed, smc will auto-install it
smc ekscli cluster list

# Query service deployment information
smc servicecmdb service info myservice

# All plugin calls through smc handle authentication automatically
smc logcli search --service myapp --level error
```

## Common Mistakes

- **Do NOT call plugin binaries directly** (e.g. `ekscli cluster list`) — always use `smc <plugin> <subcommand>` so that token injection and audit logging work correctly.
- **Do NOT install plugins that are already installed** — use `smc list` to check installed plugins first.
- **Do NOT chain multiple install commands** like `smc install plugin1 && smc install plugin2` — install multiple plugins in one command: `smc install plugin1 plugin2`.
- **Do NOT guess which plugin to install when the need is capability-based** — use `smc list` and select by description.
- **Do NOT manually manage tokens** — use `smc login` when token expires; `smc token export` only for scripts.
