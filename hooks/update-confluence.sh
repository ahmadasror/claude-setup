#!/bin/bash
# Global hook: remind to update Confluence after planning (ExitPlanMode).
# Reads project-level config from .claude/confluence.json
#
# Prerequisites:
#   - `jq` installed (brew install jq / apt install jq)
#   - Project-level config at .claude/confluence.json with shape:
#       { "url": "https://...", "space": "TEAM", "section": "Planning" }
#     `space` and `section` are optional.
#   - Absent config → hook is a no-op (silent).
#
# Behavior:
#   - Emits a stdout reminder pointing to the configured Confluence target.
#   - Does not write to Confluence; reminder only.

CONFIG=".claude/confluence.json"

if [ ! -f "$CONFIG" ]; then
  exit 0
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "update-confluence.sh: 'jq' not found — install it or remove this hook from settings.json." >&2
  exit 0
fi

URL=$(cat "$CONFIG" | jq -r '.url')
SPACE=$(cat "$CONFIG" | jq -r '.space // ""')
SECTION=$(cat "$CONFIG" | jq -r '.section // "Planning"')

MSG="Reminder: Update confluence dengan hasil planning.
- URL: $URL"

[ -n "$SPACE" ] && MSG="$MSG
- Space: $SPACE"

MSG="$MSG
- Section: $SECTION
- Isi: judul plan, keputusan, next steps, owner"

echo "$MSG"
