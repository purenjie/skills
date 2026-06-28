---
name: smc-pam
description: Accesses privileged resources through Shopee's PAM gateway via the smc CLI — use smc subcommands (e.g. smc toc, smc mysql, smc eks, smc netdevice, smc pam …) that delegate to the PAM stack. Covers server SSH/SCP/SFTP/rsync, MySQL/Redis, EKS kubectl and pods, network devices, Bromo/Edge/Runonce containers, file upload/download, and port forwarding. Use when the user needs to log in through PAM, connect to MySQL or Redis via PAM, enter K8s pods or addons, operate network devices, or use container workflows. Triggers on smc toc, smc pam, PAM SSH, servers ssh, mysql via PAM, redis via PAM, eks kubectl, netdevice, runonce enter, services enter, smc scp, smc sftp. DO NOT use for read-only session/command auditing or replay — use pamcli instead. DO NOT use for server hardware/CMDB lookup — use servercmdb instead.
---

# PAM Gateway (`smc`)

Connect and operate through PAM using the **`smc`** CLI. Invoke **`smc …`**, not `smc-pam` directly. This is the interactive PAM gateway; use **pamcli** for read-only audit and replay.

## Commands

Use **`smc <top-level>`** (and **`smc pam <sub>`** when the verb only exists under the `pam` command in the PAM binary).

| Area                           | How to invoke (`smc`)                    | Notes                                                                                                    |
| ------------------------------ | ---------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| Server SSH                     | `smc toc …`                              | Normal server login and commands use `smc toc`; `smc pam servers ssh` is not the recommended entrypoint. |
| Server SCP / SFTP / rsync      | `smc scp …`, `smc sftp …`, `smc rsync …` | Usage is consistent with official `scp` / `sftp` / `rsync`.                                              |
| Server SOL / VNC / RDP helpers | `smc sol …`, `smc vnc …`, `smc rdp …`    | Use the top-level `smc` verb shown here.                                                                 |
| MySQL / Redis                  | `smc mysql …`, `smc redis …`             | Database access through PAM. Use `rekey` only with explicit user intent.                                 |
| EKS                            | `smc eks …`                              | Use for kubectl, pod enter, addon pod, and file transfer workflows.                                      |
| Network devices                | `smc netdevice …`                        | Use for network device SSH, SCP, sync, web, and webapp workflows. Aliases: `nd`, `netdevices`.           |
| Bromo / services               | `smc services …`, `smc enter …`          | Use for container enter, logs, command execution, and file transfer workflows.                           |
| Edge Container                 | `smc edge …`                             | Use for edge container enter, logs, command execution, and file transfer workflows.                      |
| Runonce                        | `smc runonce …`                          | Runonce job and task workflows.                                                                          |
| PAM-only tree                  | `smc pam …`                              | Use only for PAM-only subcommands such as `forward` or `windows rekey`.                                  |

**Getting flags:** Many OpenSSH-style commands disable flag parsing for compatibility. Prefer **`smc <verb> --help`** (e.g. `smc toc --help`, `smc mysql --help`, `smc pam forward --help`) for accurate flags.

## Workflows

### Server (TOC)

| Need                                                     | Command                                                           |
| -------------------------------------------------------- | ----------------------------------------------------------------- |
| Log in to a server / run multiple commands (interactive) | `smc toc <ip>`                                                    |
| Run one command on a server (non-interactive)            | `smc toc <ip> <command>`                                          |
| Copy files to/from server                                | `smc scp <src> <dst>` / `smc sftp <ip>` / `smc rsync <src> <dst>` |
| Port forwarding via PAM proxy                            | `smc pam forward …` (see `--help`)                                |

> **Hostname → IP:** If target is an IP-based hostname (e.g. `10-251-99-66-cls-xxx.shopeemobile.com` or `10-251-99-66`), convert to dotted IP (`10.251.99.66`) before passing to `smc toc`.

### Bromo / Service Containers

| Need                             | Command                                                              |
| -------------------------------- | -------------------------------------------------------------------- |
| Enter a container (interactive)  | `smc services enter <service_name>`                                  |
| View container logs              | `smc services logs <service_name>`                                   |
| Show container stats             | `smc services stats <service_name>`                                  |
| Show tasks / container list      | `smc services show <service_name>`                                   |
| List all services                | `smc services ls`                                                    |
| Run command on all containers    | `smc services run <service_name> -- <command>`                       |
| Run command on a specific task   | `smc tasks run <task_id> -- <command>`                               |
| Upload file to container (≤1 MB) | `smc services upload <service_name> <local_file> <container_path>`   |
| Download file from container     | `smc services download <service_name> <container_path> <local_file>` |

### Other

| Need                    | Command                               |
| ----------------------- | ------------------------------------- |
| Enter an edge container | `smc edge enter <service_name>`       |
| Runonce container       | `smc runonce enter <task_id>`         |
| MySQL through PAM       | `smc mysql -h … -P … -u … -p`         |
| Redis through PAM       | `smc redis …`                         |
| kubectl / pod on EKS    | `smc eks kubectl …` / `smc eks pod …` |
| Network device CLI      | `smc netdevice ssh …`                 |

## Operating Rules

**`smc` (PAM access) vs pamcli:** Use **`smc …`** to **establish** privileged sessions. Use **pamcli** to **audit** past sessions, list command logs, and replay terminal recordings.

**Server commands:** Use **`smc toc <ip>`** to create an interactive session when logging in or running multiple commands. Use **`smc toc <ip> <command>`** only for a single non-interactive command.

**Interactive sessions:** **`smc toc`**, `mysql`, `redis`, and many `eks` / container commands are TTY-oriented. In non-interactive automation, expect limitations unless the user runs them in a real terminal.

**Cluster / environment:** Target cluster is selected via the SMC SDK (e.g. `shopee`, `shopeetest`). Some commands auto-select cluster when an IP is present on the command line.

**Token authentication:** If the CLI prints a browser login URL and blocks, do not cancel; have the user complete login in the browser until the command continues (same pattern as other SMC CLIs).

## Common Mistakes

**Do NOT do these:**

- Do NOT use **`smc`** / this skill for read-only PAM audit, session lists, command logs, or asciinema replay — use **pamcli**
- Do NOT use **`smc ssh`** for server login — it is unsupported; use **`smc toc`** instead
- Do NOT tell the user to run **`smc-pam …`** in normal operations — use **`smc …`** entrypoints (`toc`, `mysql`, `pam …`, etc.)
- Do NOT guess hostnames, cluster IDs, or task IDs — ask the user or resolve via CMDB/other tools first
- Do NOT run `rekey` or destructive operations without explicit user confirmation
- Do NOT assume non-interactive runs will work for full SSH/mysql shells without a TTY
- Do NOT cancel browser login flows while the user is completing authentication

## Related Skills

- **pamcli** — PAM session lists, operation/command logs, terminal replay (read-only audit).
- **servercmdb** — Server identity and ownership; correlate targets before connecting.
- **servicecmdb** — Service ownership and deployment configuration.

## Examples

```bash
# Help
smc toc --help
smc mysql --help
smc eks --help
smc pam forward --help

# Server SSH (IP or user@host — use toc, not smc ssh)
smc toc 10.0.0.1
smc toc user@hostname

# Run one command on a server
smc toc 10.0.0.1 hostname
smc toc 10.0.0.1 uptime

# MySQL via PAM (-h = host per mysql client; CLI help: smc mysql --help)
smc mysql -h <host> -P <port> -u <user> -p

# Redis via PAM (-h = host; CLI help: smc redis --help)
smc redis -h <host> -P <port>

# EKS kubectl
smc eks kubectl <cluster_id|node_ip|hostname>

# Network device SSH
smc netdevice ssh user@device

# Bromo service container
smc services enter <service_name>

# Edge container
smc edge enter <service_name>

# Runonce task
smc runonce enter <task_id>
```
