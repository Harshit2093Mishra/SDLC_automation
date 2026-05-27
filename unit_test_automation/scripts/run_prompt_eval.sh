#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# run_llm_inference.sh  <filled_prompt.yml>
#
# Runs a single LLM inference using the gh models CLI.
#
# Why NOT gh models eval:
#   `gh models eval` is a BATCH evaluation tool — it runs the prompt
#   against each item in `testData`. With no testData, testResults=null.
#
# Why gh models run:
#   `gh models run` does a single inference call. We extract the system
#   and user messages from the YAML and pass them directly.
#
# Output: raw model response printed to stdout (no wrapper JSON).
# ---------------------------------------------------------------------------
set -euo pipefail

PROMPT_FILE="${1:-}"

if [ -z "$PROMPT_FILE" ] || [ ! -f "$PROMPT_FILE" ]; then
  echo "Usage: $0 <filled_prompt.yml>" >&2
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: gh CLI is required (install from https://cli.github.com/)" >&2
  exit 1
fi

if ! gh extension list 2>/dev/null | grep -q 'github/gh-models'; then
  echo "Installing gh-models extension..." >&2
  gh extension install github/gh-models >&2
fi

# ---------------------------------------------------------------------------
# Extract model, system message and user message from the YAML.
# We use Python (always available in Codespaces) for reliable YAML parsing.
# ---------------------------------------------------------------------------
read -r MODEL SYSTEM_MSG USER_MSG < <(python3 - "$PROMPT_FILE" <<'PYEOF'
import sys, yaml, json

path = sys.argv[1]
with open(path) as f:
    doc = yaml.safe_load(f)

model = doc.get("model", "openai/gpt-4o-mini")

system_msg = ""
user_msg = ""
for msg in doc.get("messages", []):
    role = msg.get("role", "")
    content = msg.get("content", "")
    if role == "system":
        system_msg = content
    elif role == "user":
        user_msg = content

# Print as JSON-safe single-line strings separated by NUL
# (using print for each so read -r can handle them)
print(model)
print(json.dumps(system_msg))
print(json.dumps(user_msg))
PYEOF
)

MODEL=$(echo "$MODEL" | tr -d '[:space:]')

# Decode JSON-encoded strings
SYSTEM_DECODED=$(python3 -c "import sys,json; print(json.loads(sys.argv[1]))" "$SYSTEM_MSG")
USER_DECODED=$(python3 -c "import sys,json; print(json.loads(sys.argv[1]))" "$USER_MSG")

# ---------------------------------------------------------------------------
# Call the model.
# gh models run reads a prompt from stdin and outputs the raw response.
# We wrap in JSON ourselves so parse_llm_json gets a clean payload.
# ---------------------------------------------------------------------------
RESPONSE=$(printf '%s' "$USER_DECODED" | \
  gh models run "$MODEL" \
    --system "$SYSTEM_DECODED" \
    2>/dev/null)

# Output the response directly — parse_llm_json handles the rest
printf '%s' "$RESPONSE"
