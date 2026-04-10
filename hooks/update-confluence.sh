#!/bin/bash
# Global hook: remind to update confluence after planning
# Reads project-level config from .claude/confluence.json

CONFIG=".claude/confluence.json"

if [ ! -f "$CONFIG" ]; then
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
