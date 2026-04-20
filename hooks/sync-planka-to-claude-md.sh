#!/bin/bash
# Hook: After Planka card update, remind to sync CLAUDE.md roadmap status
# Triggered by PostToolUse on mcp__planka__cards
#
# Prerequisites:
#   - Project must have CLAUDE.md at its root. Absent → hook is a no-op (silent).
#
# Behavior:
#   - Emits a stdout reminder to manually sync the Master Roadmap row in CLAUDE.md
#     when a Planka card transition happens (e.g. Planned → Done).
#   - Does not write files; reminder only.

CLAUDE_MD="CLAUDE.md"

if [ ! -f "$CLAUDE_MD" ]; then
  exit 0
fi

echo "CLAUDE.md sync reminder: Planka card was updated. If a roadmap item changed status (e.g. Planned → Done), update the corresponding row in CLAUDE.md Master Roadmap to match."
