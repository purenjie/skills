#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

usage() {
  cat <<USAGE
Usage:
  scripts/sync-skill-links.sh <target> <skill...>
  scripts/sync-skill-links.sh <target> --all

Targets:
  alma     -> ~/.config/alma/skills
  claude   -> ~/.claude/skills
  codex    -> \\${CODEX_HOME:-~/.codex}/skills

Examples:
  scripts/sync-skill-links.sh claude confluence jira web-access
  scripts/sync-skill-links.sh alma newapi-channel-manager task-dashboard-review
  scripts/sync-skill-links.sh codex --all
USAGE
}

target="${1:-}"
[[ -n "$target" ]] || { usage; exit 1; }
shift || true

case "$target" in
  alma) dest="$HOME/.config/alma/skills" ;;
  claude) dest="$HOME/.claude/skills" ;;
  codex) dest="${CODEX_HOME:-$HOME/.codex}/skills" ;;
  -h|--help|help) usage; exit 0 ;;
  *) echo "unknown target: $target" >&2; usage; exit 1 ;;
esac

mkdir -p "$dest"

if [[ "${1:-}" == "--all" ]]; then
  mapfile -t skills < <(find "$ROOT" -mindepth 1 -maxdepth 1 -type d ! -name .git ! -name scripts -exec basename {} \; | sort)
else
  skills=("$@")
fi

[[ ${#skills[@]} -gt 0 ]] || { echo "no skills specified" >&2; usage; exit 1; }

for skill in "${skills[@]}"; do
  src="$ROOT/$skill"
  link="$dest/$skill"
  if [[ ! -d "$src" ]]; then
    echo "missing skill source: $src" >&2
    exit 1
  fi
  if [[ -e "$link" || -L "$link" ]]; then
    if [[ -L "$link" ]]; then
      rm "$link"
    else
      backup="$link.backup.$(date +%Y%m%d%H%M%S)"
      mv "$link" "$backup"
      echo "backed up existing directory: $link -> $backup"
    fi
  fi
  ln -s "$src" "$link"
  echo "linked: $target/$skill -> $src"
done
