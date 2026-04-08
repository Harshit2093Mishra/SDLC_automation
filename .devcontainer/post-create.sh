#!/usr/bin/env bash
set -euo pipefail

echo "Codespace ready. Running initial validation..."
bash scripts/validate.sh || true
