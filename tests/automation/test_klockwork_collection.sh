#!/bin/bash
# test_klockwork_collection.sh
# Test klockwork automation - collection phase

set -e

echo "=== Test 2A: Klockwork Automation - Issue Collection ==="

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$REPO_ROOT"

# Verify script exists
if [[ ! -f "klockwork_automation/scripts/collect_klockwork_issues.py" ]]; then
    echo "❌ FAILED: collect_klockwork_issues.py not found"
    exit 1
fi
echo "✅ collect_klockwork_issues.py found"

# Run collection with summary only
echo "Running Klockwork issue collection..."
python3 klockwork_automation/scripts/collect_klockwork_issues.py \
    --source-dir src \
    --output /tmp/klockwork_issues_test.json \
    --summary-only > /tmp/klockwork_output.txt 2>&1

if [[ $? -ne 0 ]]; then
    echo "❌ FAILED: Issue collection failed"
    cat /tmp/klockwork_output.txt
    exit 1
fi
echo "✅ Issue collection succeeded"

# Show summary
echo "Summary output:"
cat /tmp/klockwork_output.txt | tail -15

# Validate output if file was created
if [[ -f "/tmp/klockwork_issues_test.json" ]]; then
    python3 << 'EOF'
import json
with open('/tmp/klockwork_issues_test.json') as f:
    data = json.load(f)

required_keys = ['total_issues', 'by_severity', 'by_rule', 'issues']
for key in required_keys:
    if key not in data:
        print(f"❌ Missing key: {key}")
        exit(1)

total = data['total_issues']
print(f"✅ Found {total} Klockwork issues")
print(f"   CRITICAL: {data['by_severity'].get('CRITICAL', 0)}")
print(f"   HIGH: {data['by_severity'].get('HIGH', 0)}")
print(f"   MEDIUM: {data['by_severity'].get('MEDIUM', 0)}")
EOF
fi

echo "✅ Test 2A PASSED"
exit 0
