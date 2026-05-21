#!/usr/bin/env bash
set -euo pipefail

PROMPT_FILE="${1:-unit_test_automation/prompts/unit_test_generator.prompt.yml}"
INPUT_JSON="${2:-}"

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI is required"
  exit 1
fi

if ! gh extension list | grep -q 'github/gh-models'; then
  gh extension install github/gh-models
fi

# If an input JSON file is provided, pipe it to gh models eval via stdin
if [ -n "$INPUT_JSON" ] && [ -f "$INPUT_JSON" ]; then
  cat "$INPUT_JSON" | gh models eval "$PROMPT_FILE" --json --input -
else
  gh models eval "$PROMPT_FILE" --json
fi
