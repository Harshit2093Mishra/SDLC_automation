#!/usr/bin/env bash
set -euo pipefail

echo "Codespace ready. Running initial validation..."
bash unit_test_automation/scripts/validate.sh || true
