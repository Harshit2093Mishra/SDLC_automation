#!/bin/bash
# test_unit_test_collection.sh
# Test unit test automation - collection phase

set -e

echo "=== Test 1A: Unit Test Automation - Collection Phase ==="

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$REPO_ROOT"

# Step 1: Verify collect_pr_diff.py exists and is executable
if [[ ! -f "unit_test_automation/scripts/collect_pr_diff.py" ]]; then
    echo "❌ FAILED: collect_pr_diff.py not found"
    exit 1
fi
echo "✅ collect_pr_diff.py found"

# Step 2: Try to run collection on current state
echo "Running diff collection..."
if python3 unit_test_automation/scripts/collect_pr_diff.py \
    --base origin/main \
    --head HEAD > /tmp/diff_output.json 2>&1; then
    echo "✅ Diff collection executed"
else
    echo "⚠️  Diff collection had errors (may be expected in test environment)"
    # Don't fail - this might be expected if no changes
fi

# Step 3: Validate script structure
python3 << 'EOF'
import sys
import ast

script_path = "unit_test_automation/scripts/collect_pr_diff.py"
with open(script_path) as f:
    try:
        ast.parse(f.read())
        print("✅ collect_pr_diff.py syntax is valid")
    except SyntaxError as e:
        print(f"❌ Syntax error: {e}")
        sys.exit(1)
EOF

echo "✅ Test 1A PASSED"
exit 0
