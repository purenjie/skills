---
name: rap
description: Queries the RAP API documentation platform via the smc rap CLI to search service repositories, discover API endpoints, and retrieve request/response schemas. Use when the user asks about API docs, API schema, endpoint documentation, swagger, openapi, request parameters, response format, or needs to discover which APIs a service exposes. Also use proactively for API discovery when needing to call an unknown internal API. Triggers on rap, api docs, api schema, api endpoint, swagger, openapi, request params, response format, find API, discover endpoints. DO NOT use for service deployment config or ownership — use servicecmdb instead. DO NOT use for application logs — use logcli instead.
---

# RAP (API Documentation Platform)

Query the internal RAP API documentation platform to discover services, search endpoints, and retrieve API schemas including request parameters and response formats. Use the `smc rap` CLI for fast lookups — or as an API discovery tool to find and call internal service APIs you don't already know.

## Setup

1. **Install the CLI**: `smc install rap`
2. **Configure auth** — the CLI reads the `space_auth_live` cookie automatically from (in priority order):
   - `--token <TOKEN>` flag
   - `$RAP_TOKEN` environment variable
   - `~/.agent-browser/sessions/default.json` (browser session file)
3. **Verify**: `smc rap repos "order"` — should return repository results without errors.

## Contents

- [Setup](#setup)
- [Commands](#commands)
- [Workflows](#workflows)
- [Key Patterns](#key-patterns)
- [Instructions](#instructions)
- [Common Mistakes](#common-mistakes)
- [Examples](#examples)

## Commands

| Command | Description |
|---------|-------------|
| `smc rap repos [name]` | Search repositories by name (fuzzy match) |
| `smc rap interfaces <repo_id>` | List all interfaces/endpoints in a repository |
| `smc rap schema <interface_id>` | Get interface schema (params & response format) |
| `smc rap import <repo_id> --file <path>` | Import swagger/openapi data into a repository |

**Global flags:** `--json` (raw JSON output), `--token <TOKEN>` (override auth), `--limit <N>` (pagination limit, default 25, max 100), `--cursor <N>` (pagination cursor)

### Command Details

**`smc rap repos [name]`** — Search repositories by name. If no name given, lists all. Supports pagination via `--limit` and `--cursor`.
Output columns: ID, NAME, UPDATED, DESCRIPTION.

**`smc rap interfaces <repo_id>`** — List all modules and interfaces in a repository. Groups endpoints by module.
Output: module name, then per-interface: ID, METHOD, URL, NAME.

**`smc rap schema <interface_id>`** — Get the full schema for an interface, grouped by scope (request/response).
Output: endpoint info, then per-scope table: NAME, TYPE, REQUIRED, DESCRIPTION.

**`smc rap import <repo_id> --file <path>`** — Import a swagger/openapi JSON file into a repository.
Extra flags: `--type <Swagger|RAP|YAPI|PB>` (default: Swagger), `--mode <add|cover|clean>` (default: cover).

## Workflows

**Determine which command to use:**

| Need | Command |
|------|---------|
| Find a repository for a service? | `smc rap repos <service_name>` |
| List all endpoints in a repo? | `smc rap repos <name>` then `smc rap interfaces <repo_id>` |
| Get full API schema for an endpoint? | `smc rap interfaces <repo_id>` then `smc rap schema <interface_id>` |

**Find all APIs for a service:**
```bash
smc rap repos "bromo"                   # Find the repository ID
smc rap interfaces 1677                 # List all endpoints by module
smc rap schema 738762                   # Get full schema for one endpoint
```

**If search returns multiple results:**
```bash
smc rap repos "order"                   # May return many matches
# Pick the specific repo ID from the results, then:
smc rap interfaces 2185                 # Use the exact ID
```

**API discovery — find and call an unknown internal API:**

When you need to query an internal system but don't know its API, use RAP to discover it:
```bash
# Step 1: Find the service's API repository
smc rap repos "dns"                     # Search for the DNS service

# Step 2: List available endpoints
smc rap interfaces 1234                 # List all DNS API endpoints

# Step 3: Get the schema for the endpoint you need
smc rap schema 56789 --json             # Get request params and response format as JSON

# Step 4: Construct and execute the API call using the discovered schema
curl -X GET "https://dns.shopee.io/api/v1/domains?name=example.shopee.io" \
  -H "Authorization: Bearer $TOKEN"
```

This workflow lets you answer questions about any internal system by discovering its API first, then calling it directly.

## Key Patterns

**Repository lookup:** Use `smc rap repos <name>` to find a repository ID. If the search returns 0 results, try broader search terms or check the service name. If it returns multiple matches, pick the specific one by ID.

**Two-step and three-step workflows:**
- **Find endpoints:** `smc rap repos <name>` → `smc rap interfaces <repo_id>`
- **Get full schema:** `smc rap repos <name>` → `smc rap interfaces <repo_id>` → `smc rap schema <interface_id>`
- **Discover & call API:** `smc rap repos` → `smc rap interfaces` → `smc rap schema --json` → construct HTTP request

**Pagination:** Use `--limit N` (max 100) and `--cursor N` to page through large result sets. The cursor value comes from the position in the previous result.

**Authentication:** Uses `space_auth_live` cookie from `~/.agent-browser/sessions/default.json`. If the cookie is missing, the CLI automatically starts browser-based authentication — it prints a login URL to stderr and **blocks** (keeps running) while waiting up to 5 minutes for the user to visit the URL. Once authenticated, the token is saved and the CLI continues automatically.

**JSON output:** Use `--json` for machine-readable output when you need to parse or pipe results — especially in the API discovery workflow where you need exact parameter names and types.

## Instructions

When the user asks about APIs, endpoints, request/response formats, API documentation, or when you need to discover an internal API to answer a question:

1. **If the tool is not installed or not configured:**
   - If `smc rap` is unavailable → install it: `smc install rap`
   - If auth/permission errors or the output shows `Please open the following URL to authenticate`:
     1. The command is **actively blocking** — it is waiting for the user to visit the URL. Do NOT cancel it.
     2. Tell the user to open the URL shown in the output in their browser to complete authentication.
     3. Do NOT ask the user to provide a token, run a different command, or set environment variables.
     4. After the user authenticates in the browser, the command will automatically continue and complete.
2. **For direct API documentation queries:**
   - Identify what the user needs and pick the matching command from the Workflows table
   - If a repository ID is needed but not known, use `smc rap repos <name>` first
   - For full API details, chain: `smc rap repos` → `smc rap interfaces` → `smc rap schema`
   - Present results clearly — highlight endpoint URL, method, and key parameters
3. **For API discovery (calling unknown internal APIs):**
   - Search RAP for the service: `smc rap repos <service_name>`
   - List its endpoints: `smc rap interfaces <repo_id>`
   - Get the schema with `--json`: `smc rap schema <interface_id> --json`
   - Parse the JSON to extract: endpoint URL, HTTP method, required parameters, and response format
   - Construct the HTTP call using curl or the appropriate tool
   - Use the `space_auth_live` cookie or SPACE token for authentication when calling the discovered API
4. Use `--json` when output will be piped or processed further

## Common Mistakes

**Do NOT do these:**
- Do NOT pass repository names where repository IDs are required — `smc rap interfaces bromo` will fail; use `smc rap interfaces 1677` instead
- Do NOT skip the lookup chain — always start with `smc rap repos` to find the ID, then `smc rap interfaces`, then `smc rap schema`
- Do NOT forget `--json` when you need to parse the output programmatically (e.g., in the API discovery workflow)
- Do NOT assume API authentication — when calling discovered APIs, check if they require SPACE auth headers

## Related Skills

- **servicecmdb** — Service metadata, ownership, deployment config. Find which service you need API docs for.
- **logcli** — Application logs. Check logs for API errors after discovering endpoints.

## Examples

```bash
# Search for repositories related to "order"
smc rap repos order

# Search with pagination
smc rap repos order --limit 10
smc rap repos order --limit 10 --cursor 10

# List all interfaces in repository 1677 (Bromo)
smc rap interfaces 1677

# Get full schema for interface 738762
smc rap schema 738762

# Get schema as JSON for programmatic use
smc rap schema 738762 --json

# Import swagger data into a repository
smc rap import 5137 --file ./swagger.json
smc rap import 5137 --file ./openapi.json --type Swagger --mode add

# API discovery workflow: find DNS API and call it
smc rap repos dns                       # Find DNS service repo
smc rap interfaces 1234                 # List DNS endpoints
smc rap schema 56789 --json             # Get schema for the endpoint you need

# Raw JSON output for scripting
smc rap repos order --json
smc rap interfaces 1677 --json
```
