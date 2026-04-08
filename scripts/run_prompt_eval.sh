#!/usr/bin/env bash
set -euo pipefail

PROMPT_FILE="${1:-prompts/unit_test_generator.prompt.yml}"

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI is required"
  exit 1
fi

if ! gh extension list | grep -q 'github/gh-models'; then
  gh extension install github/gh-models
fi

gh models eval "$PROMPT_FILE" --json
