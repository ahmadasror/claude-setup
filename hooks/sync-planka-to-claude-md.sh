#!/bin/bash
# Hook: After Planka card update, remind to sync CLAUDE.md roadmap status
# Triggered by PostToolUse on mcp__planka__cards

CLAUDE_MD="CLAUDE.md"

if [ ! -f "$CLAUDE_MD" ]; then
  exit 0
fi

echo "CLAUDE.md sync reminder: Planka card was updated. If a roadmap item changed status (e.g. Planned → Done), update the corresponding row in CLAUDE.md Master Roadmap to match."
