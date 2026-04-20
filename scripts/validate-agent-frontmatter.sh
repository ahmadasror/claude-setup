#!/bin/bash
# Validate frontmatter of every agents/*.md file.
# Fails CI if any agent is missing required keys or has an invalid model.
#
# Required keys: name, description, tools, model
# Allowed model values: opus | sonnet | haiku
#
# Usage: bash scripts/validate-agent-frontmatter.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AGENTS_DIR="$ROOT/agents"
FAILED=0

if [ ! -d "$AGENTS_DIR" ]; then
  echo "ERROR: $AGENTS_DIR not found" >&2
  exit 1
fi

ALLOWED_MODELS="opus sonnet haiku"

for f in "$AGENTS_DIR"/*.md; do
  name_file=$(basename "$f" .md)
  # Extract frontmatter (between first two --- lines)
  fm=$(awk '/^---$/{c++; if(c==2) exit; next} c==1' "$f")

  # Required keys
  for key in name description tools model; do
    value=$(echo "$fm" | awk -F': *' -v k="$key" '$1==k {sub(/^[^:]+: */, ""); print; exit}')
    if [ -z "$value" ]; then
      echo "FAIL $name_file: missing or empty '$key'" >&2
      FAILED=1
    fi
  done

  # Model value check
  model=$(echo "$fm" | awk -F': *' '$1=="model" {sub(/^[^:]+: */, ""); print; exit}')
  if [ -n "$model" ]; then
    if ! echo " $ALLOWED_MODELS " | grep -q " $model "; then
      echo "FAIL $name_file: model '$model' not in {$ALLOWED_MODELS}" >&2
      FAILED=1
    fi
  fi

  # name must match filename
  name=$(echo "$fm" | awk -F': *' '$1=="name" {sub(/^[^:]+: */, ""); print; exit}')
  if [ -n "$name" ] && [ "$name" != "$name_file" ]; then
    echo "FAIL $name_file: frontmatter name='$name' does not match filename" >&2
    FAILED=1
  fi
done

if [ "$FAILED" -eq 0 ]; then
  count=$(ls -1 "$AGENTS_DIR"/*.md | wc -l | tr -d ' ')
  echo "OK — $count agent(s) passed frontmatter validation"
else
  exit 1
fi
