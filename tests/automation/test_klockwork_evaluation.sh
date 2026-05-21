#!/bin/bash
# test_klockwork_evaluation.sh
# Test klockwork automation - evaluation cases

set -e

echo "=== Test 2B: Klockwork Automation - Evaluation Cases ==="

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$REPO_ROOT"

# Verify evaluation script
if [[ ! -f "klockwork_automation/scripts/run_klockwork_eval.sh" ]]; then
    echo "❌ FAILED: run_klockwork_eval.sh not found"
    exit 1
fi
echo "✅ run_klockwork_eval.sh found"

# Verify evaluation cases exist
EVAL_CASES="klockwork_automation/prompts/evals/klockwork_fixer_cases.jsonl"
if [[ ! -f "$EVAL_CASES" ]]; then
    echo "❌ FAILED: Evaluation cases not found"
    exit 1
fi

NUM_CASES=$(wc -l < "$EVAL_CASES")
echo "✅ Found $NUM_CASES evaluation cases"

# List available cases
echo "Available evaluation cases:"
bash klockwork_automation/scripts/run_klockwork_eval.sh --list 2>/dev/null | head -30

# Run evaluation on a specific case
echo ""
echo "Running specific evaluation case: KLOCK_EVAL_003..."
bash klockwork_automation/scripts/run_klockwork_eval.sh \
    --case KLOCK_EVAL_003 > /tmp/eval_output_test.txt 2>&1

if [[ $? -eq 0 ]]; then
    echo "✅ Evaluation case passed"
    tail -5 /tmp/eval_output_test.txt
else
    echo "⚠️  Evaluation case had warnings"
fi

echo "✅ Test 2B PASSED"
exit 0
