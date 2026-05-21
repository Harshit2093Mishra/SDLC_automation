#!/bin/bash
# test_integration.sh
# Integration test for both modules

set -e

echo "╔════════════════════════════════════════════════════════╗"
echo "║     Complete SDLC Automation Integration Test         ║"
echo "╚════════════════════════════════════════════════════════╝"

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$REPO_ROOT"

# Test environment
echo "Step 0: Verify test environment..."
echo "  Python: $(python3 --version)"
echo "  Git: $(git --version)"

# Step 1: Unit Test Automation
echo ""
echo "Step 1: Unit Test Automation"
echo "───────────────────────────"
echo "Checking collect_pr_diff.py..."

if [[ -f "unit_test_automation/scripts/collect_pr_diff.py" ]]; then
    python3 -m py_compile unit_test_automation/scripts/collect_pr_diff.py
    echo "✅ Unit test collection script is valid"
else
    echo "❌ Script not found"
    exit 1
fi

# Step 2: Klockwork Automation
echo ""
echo "Step 2: Klockwork Automation"
echo "───────────────────────────"
echo "Checking collect_klockwork_issues.py..."

if [[ -f "klockwork_automation/scripts/collect_klockwork_issues.py" ]]; then
    python3 -m py_compile klockwork_automation/scripts/collect_klockwork_issues.py
    echo "✅ Klockwork collection script is valid"
else
    echo "❌ Script not found"
    exit 1
fi

# Step 3: Check all main artifacts
echo ""
echo "Step 3: Framework Artifacts"
echo "───────────────────────────"

ARTIFACTS=(
    "unit_test_automation/README.md"
    "unit_test_automation/prompts/unit_test_generator.prompt.yml"
    "klockwork_automation/README.md"
    "klockwork_automation/prompts/klockwork_fixer.prompt.yml"
    "klockwork_automation/prompts/klockwork_rules.json"
)

for artifact in "${ARTIFACTS[@]}"; do
    if [[ -f "$artifact" ]]; then
        echo "✅ Found: $artifact"
    else
        echo "❌ Missing: $artifact"
        exit 1
    fi
done

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║        Integration Test Completed Successfully         ║"
echo "╚════════════════════════════════════════════════════════╝"
exit 0
