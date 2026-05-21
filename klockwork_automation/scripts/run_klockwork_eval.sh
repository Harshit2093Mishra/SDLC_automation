#!/bin/bash
# Klockwork Fixer Prompt Evaluation Script
# Runs evaluation cases against the Klockwork fixer prompt
# Similar to unit_test_automation/scripts/run_prompt_eval.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUTOMATION_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
EVAL_CASES_FILE="$AUTOMATION_DIR/prompts/evals/klockwork_fixer_cases.jsonl"
RULES_FILE="$AUTOMATION_DIR/prompts/klockwork_rules.json"
PROMPT_FILE="$AUTOMATION_DIR/prompts/klockwork_fixer.prompt.yml"

# Logging functions
log_info() {
    echo -e "${BLUE}[*]${NC} $1"
}

log_pass() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_fail() {
    echo -e "${RED}[✗]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if [[ ! -f "$EVAL_CASES_FILE" ]]; then
        log_fail "Evaluation cases file not found: $EVAL_CASES_FILE"
        return 1
    fi
    
    if [[ ! -f "$RULES_FILE" ]]; then
        log_fail "Klockwork rules file not found: $RULES_FILE"
        return 1
    fi
    
    if [[ ! -f "$PROMPT_FILE" ]]; then
        log_fail "Prompt file not found: $PROMPT_FILE"
        return 1
    fi
    
    if ! command -v python3 &> /dev/null; then
        log_fail "python3 not found"
        return 1
    fi
    
    log_pass "All prerequisites satisfied"
    return 0
}

# Run a single evaluation case
run_eval_case() {
    local case_json="$1"
    local case_id=$(echo "$case_json" | python3 -c "import sys, json; print(json.load(sys.stdin).get('test_id', ''))" 2>/dev/null || echo "UNKNOWN")
    local category=$(echo "$case_json" | python3 -c "import sys, json; print(json.load(sys.stdin).get('category', ''))" 2>/dev/null || echo "UNKNOWN")
    local title=$(echo "$case_json" | python3 -c "import sys, json; print(json.load(sys.stdin).get('title', ''))" 2>/dev/null || echo "UNKNOWN")
    
    log_info "Running $case_id: $title"
    
    # Create temporary file with test code
    local temp_code=$(mktemp)
    echo "$case_json" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('input_code', ''), file=open('$temp_code', 'w'))
    " 2>/dev/null
    
    # TODO: This would integrate with actual LLM/prompt evaluation
    # For now, we'll do basic validation
    local input_code=$(echo "$case_json" | python3 -c "import sys, json; print(json.load(sys.stdin).get('input_code', ''))" 2>/dev/null || echo "")
    local expected_violations=$(echo "$case_json" | python3 -c "import sys, json; violations = json.load(sys.stdin).get('expected_violations', []); print(','.join(violations))" 2>/dev/null || echo "")
    local expected_fix=$(echo "$case_json" | python3 -c "import sys, json; print(json.load(sys.stdin).get('expected_fix_includes', ''))" 2>/dev/null || echo "")
    
    if [[ -n "$input_code" ]] && [[ -n "$expected_violations" ]]; then
        log_pass "$case_id passed basic validation"
        rm -f "$temp_code"
        return 0
    else
        log_fail "$case_id failed validation"
        rm -f "$temp_code"
        return 1
    fi
}

# Run all evaluation cases
run_all_evals() {
    log_info "Running all Klockwork fixer evaluation cases..."
    echo ""
    
    local total=0
    local passed=0
    local failed=0
    
    # Read evaluation cases
    while IFS= read -r line; do
        ((total++))
        
        if run_eval_case "$line"; then
            ((passed++))
        else
            ((failed++))
        fi
    done < "$EVAL_CASES_FILE"
    
    echo ""
    log_info "Evaluation Results:"
    log_info "==================="
    log_pass "Total: $total"
    log_pass "Passed: $passed"
    log_fail "Failed: $failed"
    
    local pass_rate=$((passed * 100 / total))
    log_info "Pass Rate: ${pass_rate}%"
    
    if [[ $failed -eq 0 ]]; then
        return 0
    else
        return 1
    fi
}

# Run specific evaluation case
run_specific_eval() {
    local case_id=$1
    
    log_info "Running specific evaluation case: $case_id"
    
    # Find and run the specific case
    local found=0
    while IFS= read -r line; do
        local id=$(echo "$line" | python3 -c "import sys, json; print(json.load(sys.stdin).get('test_id', ''))" 2>/dev/null || echo "")
        
        if [[ "$id" == "$case_id" ]]; then
            found=1
            if run_eval_case "$line"; then
                log_pass "Test case passed"
                return 0
            else
                log_fail "Test case failed"
                return 1
            fi
        fi
    done < "$EVAL_CASES_FILE"
    
    if [[ $found -eq 0 ]]; then
        log_fail "Test case not found: $case_id"
        return 1
    fi
}

# Print evaluation cases summary
print_cases_summary() {
    log_info "Available evaluation cases:"
    echo ""
    
    python3 << 'EOF' "$EVAL_CASES_FILE"
import sys
import json

cases_file = sys.argv[1]
case_count = 0

print(f"{'ID':<20} {'Category':<40} {'Severity':<10}")
print("-" * 70)

with open(cases_file, 'r') as f:
    for line in f:
        try:
            case = json.loads(line)
            test_id = case.get('test_id', '')
            category = case.get('category', '')
            severity = case.get('severity', '')
            print(f"{test_id:<20} {category:<40} {severity:<10}")
            case_count += 1
        except:
            pass

print(f"\nTotal: {case_count} cases")
EOF
}

# Show usage
show_usage() {
    cat << EOF
Klockwork Fixer Prompt Evaluation Script

Usage: $0 [OPTIONS]

Options:
    --all               Run all evaluation cases (default)
    --case ID           Run specific evaluation case (e.g., KLOCK_EVAL_001)
    --list              List all available evaluation cases
    --verbose           Enable verbose output
    --help              Show this help message

Examples:
    $0 --all                    # Run all evaluation cases
    $0 --case KLOCK_EVAL_001    # Run specific case
    $0 --list                   # List available cases

EOF
}

# Main
main() {
    echo "========================================"
    echo "Klockwork Fixer Prompt Evaluation"
    echo "========================================"
    echo ""
    
    if ! check_prerequisites; then
        return 1
    fi
    
    echo ""
    
    # Parse arguments
    local mode="all"
    local case_id=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --all)
                mode="all"
                shift
                ;;
            --case)
                mode="specific"
                case_id="$2"
                shift 2
                ;;
            --list)
                mode="list"
                shift
                ;;
            --verbose)
                set -x
                shift
                ;;
            --help)
                show_usage
                return 0
                ;;
            *)
                log_warn "Unknown option: $1"
                shift
                ;;
        esac
    done
    
    # Execute based on mode
    case $mode in
        all)
            run_all_evals
            ;;
        specific)
            run_specific_eval "$case_id"
            ;;
        list)
            print_cases_summary
            ;;
    esac
}

# Run main
main "$@"
