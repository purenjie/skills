---
name: confluence
description: Manages Confluence content via the smc confluence CLI. Reads page content and metadata, searches pages, finds pages by title, lists spaces and child pages, creates or updates pages, creates child pages, moves or deletes pages, exports pages with attachments, copies page trees, lists or uploads attachments, lists or creates or deletes comments, manages content properties, and converts content between markdown, storage, html, and text. Triggers on Confluence, wiki, page, attachment upload, comment, property, export, copy tree, markdown conversion, page URL, and page ID workflows. Does not handle browser-based editing or unsupported attachment deletion.
---

# confluence — Confluence Content Management CLI

Manage Confluence pages, attachments, comments, properties, exports, and local format conversion from the command line.

## Setup

Initialize the CLI first. Get a token from Confluence before running `smc confluence init`.

1. **Install the CLI**: `smc install confluence`
2. **Initialize with bearer auth**: `smc confluence init --domain confluence.shopee.io --auth-type bearer --token "$CONFLUENCE_API_TOKEN"`
3. **Initialize with basic auth**: `smc confluence init --domain confluence.shopee.io --auth-type basic --email "$CONFLUENCE_EMAIL" --token "$CONFLUENCE_API_TOKEN"`
4. **Verify**: `smc confluence spaces`

## Commands

### Read Commands

| Command | Description | Key Flags |
|---------|-------------|-----------|
| `smc confluence read <pageId\|url>` | Read page content | `--format text\|html\|markdown\|storage` |
| `smc confluence info <pageId\|url>` | Show page metadata | `--json` |
| `smc confluence search <query>` | Search pages by text or CQL | `--limit`, `--cql` |
| `smc confluence find <title>` | Find page by exact title | `--space` |
| `smc confluence children <pageId\|url>` | List child pages or descendants | `--recursive`, `--max-depth`, `--show-id`, `--show-url`, `--format` |
| `smc confluence spaces` | List accessible spaces | `--json` |

### Page Commands

| Command | Description | Key Flags |
|---------|-------------|-----------|
| `smc confluence create <title> <spaceKey>` | Create a page | `--content`, `--file`, `--format` |
| `smc confluence create-child <title> <parentId\|url>` | Create a child page | `--content`, `--file`, `--format` |
| `smc confluence update <pageId\|url>` | Update title and/or content | `--title`, `--content`, `--file`, `--format` |
| `smc confluence edit <pageId\|url>` | Save page storage content locally for editing | `--output` |
| `smc confluence move <pageId\|url> <newParentId\|url>` | Move a page to a new parent | `--title` |
| `smc confluence delete <pageId\|url>` | Delete a page | `--yes` |
| `smc confluence copy-tree <sourcePageId\|url> <targetParentId\|url> [newTitle]` | Copy a page tree | `--dry-run`, `--max-depth`, `--exclude`, `--delay-ms`, `--fail-on-error` |

### Attachment Commands

| Command | Description | Key Flags |
|---------|-------------|-----------|
| `smc confluence attachments <pageId\|url>` | List or download attachments | `--limit`, `--pattern`, `--download`, `--dest` |
| `smc confluence attachment-upload <pageId\|url>` | Upload or replace attachments | `--file`, `--replace`, `--comment`, `--minor-edit` |

### Comment Commands

| Command | Description | Key Flags |
|---------|-------------|-----------|
| `smc confluence comments <pageId\|url>` | List comments | `--format`, `--limit`, `--start`, `--all`, `--location`, `--depth` |
| `smc confluence comment <pageId\|url>` | Create a comment | `--content`, `--file`, `--format`, `--parent`, `--location` |
| `smc confluence comment-delete <commentId>` | Delete a comment | `--yes` |

### Property Commands

| Command | Description | Key Flags |
|---------|-------------|-----------|
| `smc confluence property-list <pageId\|url>` | List content properties | `--format`, `--limit`, `--start`, `--all` |
| `smc confluence property-get <pageId\|url> <key>` | Get a property value | `--format` |
| `smc confluence property-set <pageId\|url> <key>` | Set a property value | `--value`, `--file`, `--format` |
| `smc confluence property-delete <pageId\|url> <key>` | Delete a property | `--yes` |

### Other Commands

| Command | Description | Key Flags |
|---------|-------------|-----------|
| `smc confluence export <pageId\|url>` | Export page content and attachments | `--format`, `--dest`, `--file`, `--pattern`, `--referenced-only`, `--skip-attachments` |
| `smc confluence convert` | Local content conversion | `--input-file`, `--output-file`, `--input-format`, `--output-format` |
| `smc confluence init` | Initialize profile config | `--domain`, `--auth-type`, `--email`, `--token` |
| `smc confluence profile list\|use\|add\|remove` | Manage profiles | `--json` |
| `smc confluence completion <shell>` | Generate shell completion | `--json` |
| `smc confluence stats` | Show local command usage stats | `--json` |
| `smc confluence version` | Print CLI version | `--json` |

### Global Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--json`, `-j` | Structured JSON output | false |
| `--quiet`, `-q` | Reduce non-essential output | false |
| `--debug` | Print Confluence API calls and request details | false |
| `--profile <name>` | Use named profile | active/default profile |

### Command Patterns

**Read content and metadata**

```bash
smc confluence info 123456
smc confluence read 123456 --format markdown
smc confluence read "https://confluence.example.com/display/ENG/Weekly+Report" --format storage --json
```

**Search and locate a page**

```bash
smc confluence search "release note" --limit 10
smc confluence search 'space = ENG and type = page' --cql --limit 20 --json
smc confluence find "Weekly Report" --space ENG --json
```

**List descendants**

```bash
smc confluence children 123456 --show-id --show-url
smc confluence children 123456 --recursive --max-depth 3
smc confluence children 123456 --recursive --format json --json
```

**Create or update a page**

```bash
smc confluence create "Weekly Report" ENG --file ./report.md --format markdown --json
smc confluence create-child "Release Notes" 123456 --content "<p>Hello</p>" --format html
smc confluence update 123456 --title "Weekly Report v2" --content "# Updated" --format markdown --json
smc confluence edit 123456 --output ./page.xml
```

**Move or delete a page**

```bash
smc confluence move 123456 654321 --title "Moved Page" --json
smc confluence delete "https://confluence.example.com/display/ENG/Weekly+Report" --yes --json
```

**List, download, and replace attachments**

```bash
smc confluence attachments 123456 --pattern "*.pdf"
smc confluence attachments 123456 --download --dest ./downloads --pattern "*.png" --json
smc confluence attachment-upload 123456 --file ./artifact.pdf --replace --comment "refresh" --minor-edit --json
```

**List or create comments**

```bash
smc confluence comments 123456 --all --location footer --format json --json
smc confluence comment 123456 --content "LGTM" --format markdown
smc confluence comment 123456 --file ./comment.html --format html --parent 121640347 --location inline --json
smc confluence comment-delete 121640406 --yes
```

**Manage content properties**

```bash
smc confluence property-list 123456 --all --json
smc confluence property-get 123456 releaseMeta --json
smc confluence property-set 123456 releaseMeta --value '{"version":"1.2.3","owner":"ops"}' --json
smc confluence property-delete 123456 releaseMeta --yes
```

**Export a page**

```bash
smc confluence export 123456 --dest ./exports --format markdown
smc confluence export 123456 --format html --file content.html --attachments-dir assets
smc confluence export 123456 --pattern "*.png" --referenced-only --json
smc confluence export 123456 --skip-attachments --format storage
```

**Copy a page tree**

```bash
smc confluence copy-tree 10000 20000 "Knowledge Base Copy" --dry-run
smc confluence copy-tree 10000 20000 "Knowledge Base Copy" --max-depth 5 --exclude "Archive*,Draft*" --delay-ms 250 --fail-on-error --json
```

**Convert content locally**

```bash
smc confluence convert --input-file ./a.md --output-file ./a.xml --input-format markdown --output-format storage
cat a.md | smc confluence convert --input-format markdown --output-format text
```

**Profiles, stats, and shell completion**

```bash
smc confluence profile list --json
smc confluence profile add prod --domain confluence.example.com --auth-type bearer --token "$CONFLUENCE_API_TOKEN"
smc confluence profile use prod
smc confluence stats --json
smc confluence completion zsh
```

## Key Patterns

**Auth:** Runtime config resolves in order: environment variables first, then `~/.smc/.confluence-cli/config.json`. `basic` auth requires `CONFLUENCE_EMAIL` or `CONFLUENCE_USERNAME`. `bearer` auth only needs a token.

**Page references:** Most page-facing commands accept a numeric page ID, a URL with `pageId=...`, a `/pages/{id}` URL, or a legacy `/display/<space>/<title>` URL. Prefer exact IDs when available.

**JSON-first automation:** All commands support `--json`. Use it for scripts, CI, and agents instead of parsing terminal text.

**Debug behavior:** `--debug` prints request method, request URL, query params, request body, and attachment upload or download request details.

**Confirmation behavior:** `smc confluence delete`, `smc confluence comment-delete`, and `smc confluence property-delete` prompt unless `--yes` is provided. If the user rejects the prompt with `n` or `no`, text mode prints `Cancelled.` and JSON mode returns a cancelled object.

**Attachment replace:** `smc confluence attachment-upload --replace` uses filename matching. If the filename already exists on the page, the CLI updates the existing attachment instead of creating a second file.

**Attachment delete:** Not supported in the current Confluence version and intentionally not exposed by this CLI.

**Export formats:** `smc confluence export --format` supports `markdown`, `html`, `text`, and `storage`. HTML export rewrites attachment references to local relative paths.

**Children output:** `smc confluence children --format tree` is accepted, but the current output is still list-style rather than a fully rendered tree view.

## Workflows

### Read, verify, then update

```bash
smc confluence find "Weekly Report" --space ENG --json
smc confluence info 123456 --json
smc confluence update 123456 --file ./page.xml --format storage --json
smc confluence info 123456 --json
```

### Create a child page from markdown

```bash
smc confluence create-child "Release Notes" 123456 --file ./child.md --format markdown --json
```

### Replace an attachment

```bash
smc confluence attachments 123456 --json
smc confluence attachment-upload 123456 --file ./artifact.pdf --replace --json
```

### Export a page with local attachments

```bash
smc confluence export 123456 --format html --dest ./exports --json
```

### Manage a property

```bash
smc confluence property-set 123456 releaseMeta --value '{"version":"1.2.3"}' --json
smc confluence property-get 123456 releaseMeta --json
```

## Instructions

1. **If not installed**: `smc install confluence`
2. **Check auth first**: if API commands fail immediately, verify env vars or the active profile.
3. **Resolve the target before mutation**: use `smc confluence find`, `smc confluence search`, and `smc confluence info` first.
4. **Prefer `--file` for content-heavy writes**: avoid large inline payloads for page bodies and comments.
5. **Use `--json` for automation**: parse structured output instead of terminal text.
6. **Validate after mutation**: use `smc confluence info`, `smc confluence attachments`, `smc confluence comments`, or `smc confluence property-get` after changes.
7. **Use `smc confluence copy-tree --dry-run` first** for large or uncertain tree copy operations.
8. **Use `--debug` only when troubleshooting**: it prints raw request details and payload context.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Updating or deleting the wrong page after search | Always run `smc confluence info` on the chosen page ID before mutating |
| Passing plain text to `smc confluence property-set` | Use valid JSON, for example `"foo"` or `{"k":"v"}` |
| Forgetting `--yes` on destructive commands | Add `--yes` or confirm interactively |
| Expecting attachment delete to exist | It is intentionally unsupported in the current environment |
| Expecting `smc confluence children --format tree` to render a tree | Treat it as list output |
| Replacing an attachment with the wrong filename | List attachments first and confirm the exact filename |
| Using `smc confluence update` with the wrong format | Use `--format storage`, `html`, or `markdown` explicitly when needed |
