---
name: logcli
description: Queries application logs on Shopee's Space Log Platform via the smc logcli CLI — search for application names and query log entries with PQL filters. Use when the user needs to search logs, investigate errors, check application logs, troubleshoot incidents, investigate outages, find error patterns, or query log data for a service. Triggers on search logs, check logs, error logs, application logs, service logs, PQL, what errors happened, show me logs, investigate errors, troubleshoot, incident logs, outage investigation, OOMKilled in logs, log entries. DO NOT use for live server/container metrics (CPU, memory, disk) — use checking-server-metrics instead. DO NOT use for service metadata/config — use servicecmdb instead. DO NOT use for API documentation — use rap instead.
---

# Log (Space Log Platform)

Query logs and search application names on Shopee's internal Space Log Platform via the `smc logcli` CLI.

## Setup

1. **Install the CLI**: `smc install logcli`
2. **Configure token** — the CLI reads a SPACE token automatically from (in priority order):
   - `--token <TOKEN>` flag
   - `$LOGCLI_TOKEN` environment variable
   - `~/.smc/smc_token.json`
   - `~/.agent-browser/sessions/default.json`
3. **Verify**: `smc logcli search azpe` — should return application results without errors.

## Contents

- [Setup](#setup)
- [Commands](#commands)
- [Workflows](#workflows)
- [Key Patterns](#key-patterns)
- [PQL Reference](./PQL_SYNTAX.md) — Full PQL syntax: keyword search, operators, expressions, and functions
- [Instructions](#instructions)
- [Common Mistakes](#common-mistakes)
- [Examples](#examples)

## Commands

| Command | Description |
|---------|-------------|
| `smc logcli search <name>` | Search for application names (fuzzy match) |
| `smc logcli query <app>` | Query logs for an application |

**Global flags:** `--json` (raw JSON output), `--token <TOKEN>` (override token)

### Command Details

**`smc logcli search <name>`** — Case-insensitive fuzzy match for application names. Use this to discover the correct `<app>` value for `smc logcli query`.
Output columns: ID, APPLICATION NAME.
Extra flag: `--limit <N>` (default: 20) max results.

**`smc logcli query <app>`** — Query logs on the Space Log Platform.

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `<app>` | Yes | — | Application name (positional, e.g. `shopee.engineering_infra...kube-apiserver`) |
| `--pql <PQL>` | No | — | PQL query or keyword (e.g. `"error"`, `"OOMKilled"`); omit to return all logs |
| `--hours <N>` | No | 1 | Lookback window in hours (ignored if `--start` is set) |
| `--start <TIME>` | No | — | Start time; supports `HH:MM`, `YYYY-MM-DD HH:MM`, or unix timestamp |
| `--end <TIME>` | No | now | End time (same formats as `--start`) |
| `--limit <N>` | No | 20 | Max number of log entries (max: 10000) |
| `--timeout <N>` | No | 30 | Search timeout in seconds (max: 300) |

Output columns: RANK, TIMESTAMP, SEVERITY, HOST, CID, AZ, IDC, CLUSTER, MESSAGE.

## Workflows

| Need | Command |
|------|---------|
| Find application name? | `smc logcli search <keyword>` |
| Query recent errors? | `smc logcli query <app> --pql "error"` |
| Query all recent logs? | `smc logcli query <app>` |
| Broader time range? | `smc logcli query <app> --pql "error" --hours 6` |
| Specific time window? | `smc logcli query <app> --start "20:00" --end "21:00"` |
| More results? | `smc logcli query <app> --pql "error" --limit 50` |
| Complex PQL query? | `smc logcli query <app> --pql "OOMKilled AND pod"` |
| Raw data for scripting? | `smc logcli query <app> --json` |

**Find an app and query its logs:**
```bash
smc logcli search shopee.engineering_infra.infra_products.azpe.ecp_logs.kube-apiserver  # Find the app name
smc logcli query shopee.engineering_infra.infra_products.azpe.ecp_logs.kube-apiserver --pql "error"
```

## Key Patterns

**Application name:** The `<app>` value must match the full application name as displayed in the Space Log Platform UI. Use `smc logcli search` to discover it. It is a dot-separated hierarchical name.

**PQL query:** The `--pql` flag is optional. Omitting it returns all logs for the application within the time range. For full PQL syntax (keyword search, operators, expressions, functions), see [PQL_SYNTAX.md](./PQL_SYNTAX.md).

**Time range:** By default, queries look back 1 hour from now. Use `--hours` for simple lookback windows. Use `--start`/`--end` for precise time ranges (when `--start` is set, `--hours` is ignored). The `HH:MM` format assumes today; if the time is in the future, it uses yesterday.

**Token authentication:** The SPACE token is resolved automatically in this order: `--token` flag > `$LOGCLI_TOKEN` env var > `~/.smc/smc_token.json` > `~/.agent-browser/sessions/default.json`. If the token is expired or missing, the CLI automatically starts browser-based authentication — it prints a login URL to stderr and **blocks** (keeps running) while waiting up to 5 minutes for the user to visit the URL. Once authenticated, the token is saved and the CLI continues automatically.

**JSON output:** Use `--json` for machine-readable output when piping results or scripting.

## Instructions

When the user asks about logs, error investigation, or needs to search log data:

1. **If the tool is not installed or not configured:**
   - If `smc logcli` is unavailable → install it: `smc install logcli`
   - If auth/connection errors or the output shows `Please open the following URL to authenticate`:
     1. The command is **actively blocking** — it is waiting for the user to visit the URL. Do NOT cancel it.
     2. Tell the user to open the URL shown in the output in their browser to complete authentication.
     3. Do NOT ask the user to provide a token, run a different command, or set environment variables.
     4. After the user authenticates in the browser, the command will automatically continue and complete.
2. **If the application name is unknown**, use `smc logcli search <keyword>` first to find it
3. Construct the appropriate `smc logcli query <app>` command. For complex PQL queries, refer to [PQL_SYNTAX.md](./PQL_SYNTAX.md) for syntax details on operators (`parse`, `json`, `where`, `count`, `sort`, etc.) and functions.
4. Present results clearly — highlight severity, timestamp, and message content
5. If no results found, suggest broadening the time range (`--hours`) or adjusting the PQL

## Common Mistakes

**Do NOT do these:**
- Do NOT guess application names — use `smc logcli search` to find the correct name first
- Do NOT use short time ranges for infrequent events — increase `--hours` or use `--start`/`--end` for broader searches
- Do NOT set `--timeout` too low for large time ranges — increase timeout accordingly
- Do NOT combine `--start` with `--hours` — when `--start` is set, `--hours` is ignored

## Related Skills

- **servicecmdb** — Service metadata and ownership. Find the service name before querying logs.
- **checking-server-metrics** / **checking-cluster-metrics** — Correlate log errors with resource metrics.
- **ekscli** — Cluster metadata. K8s control-plane logs (kube-apiserver, kube-controller-manager, kube-scheduler) are indexed as logcli apps (e.g., `smc logcli query shopee...ecp_logs.kube-apiserver`). Use ekscli for cluster config context, logcli for the actual logs.
- **operating-kubernetes-cluster** — Live kubectl operations. After finding errors in logs, use kubectl to inspect the affected pods/events.

**Incident investigation workflow:** Troubleshoot first — concurrently: logcli (check logs) + checking-server-metrics/checking-cluster-metrics (check Grafana metrics) + operating-kubernetes-cluster/operating-server-or-container (check specific server and cluster state). Only escalate to dod (who is on call) if you cannot address the issue yourself.

## Examples

```bash
# Search for application names
smc logcli search azpe
smc logcli search shopee.engineering_infra.infra_products.azpe.ecp_logs.kube-apiserver
smc logcli search "bromo" --limit 50

# Query logs with PQL filter
smc logcli query shopee.engineering_infra.infra_products.azpe.ecp_logs.kube-apiserver --pql "error"

# Query all logs (no PQL filter)
smc logcli query shopee.engineering_infra.infra_products.azpe.ecp_logs.kube-apiserver

# Broader time range, more results
smc logcli query your.service.name --pql "OOMKilled" --hours 6 --limit 50

# Specific time window
smc logcli query your.service.name --pql "error" --start "08:00" --end "12:00"
smc logcli query your.service.name --pql "error" --start "2026-03-15 20:00" --end "2026-03-16 08:00"

# Complex PQL query
smc logcli query your.service.name --pql "error AND timeout" --hours 24

# Increase timeout for large searches
smc logcli query your.service.name --pql "panic" --hours 12 --limit 100 --timeout 60

# Raw JSON output for scripting
smc logcli query your.service.name --pql "error" --json
smc logcli search azpe --json
```
