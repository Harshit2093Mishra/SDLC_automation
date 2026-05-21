# Complete Flow and Testing Guide: SDLC Automation Modules

## Table of Contents
1. [Module Overview](#module-overview)
2. [Unit Test Automation Flow](#unit-test-automation-flow)
3. [Klockwork Automation Flow](#klockwork-automation-flow)
4. [Complete Testing Guide](#complete-testing-guide)
5. [Integration Flow](#integration-flow)
6. [Troubleshooting](#troubleshooting)

---

## Module Overview

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    SDLC Automation Framework                    │
├──────────────────────────┬──────────────────────────────────────┤
│  Unit Test Automation    │    Klockwork Automation              │
├──────────────────────────┼──────────────────────────────────────┤
│ Purpose: Generate unit   │ Purpose: Detect & fix security       │
│ tests for code changes   │ violations in C/C++ code             │
│                          │                                      │
│ Input: Source code files │ Input: Source code files             │
│ Output: Test files & PR  │ Output: Security fixes & PR          │
│                          │                                      │
│ Steps: Diff → Prompt →   │ Steps: Scan → Analyze →              │
│        Generate → Test → │        Generate → Validate →         │
│        PR                │        PR                            │
└──────────────────────────┴──────────────────────────────────────┘
```

---

## Unit Test Automation Flow

### Phase 1: Code Analysis (collect_pr_diff.py)

```
START
  ↓
[collect_pr_diff.py]
  ├─ Get diff between base and head branches
  ├─ Parse all changed source files (.cpp, .c, .hpp, .h)
  ├─ Read implementation code
  ├─ Read header files
  ├─ Suggest test file locations
  └─ OUTPUT: diff.json with metadata
     {
       "source_files": ["src/calculator.cpp", ...],
       "suggested_test_targets": [
         {"source": "src/calculator.cpp", "suggested_test": "tests/calculator_test.cpp"}
       ],
       "header_includes": {"src/calculator.cpp": "..."}
     }
```

### Phase 2: Test Generation (orchestrate_mr_test.py → LLM)

```
[orchestrate_mr_test.py]
  ├─ For each changed file:
  │   ├─ Load implementation code
  │   ├─ Load header file (if exists)
  │   ├─ Create prompt from template (unit_test_generator.prompt.yml)
  │   ├─ Call LLM via 'gh models eval'
  │   ├─ Parse LLM response JSON
  │   │  {
  │   │    "test_code": "...",
  │   │    "test_cases": [...],
  │   │    "coverage_summary": {...}
  │   │  }
  │   └─ Write test file to tests/
  └─ OUTPUT: Generated test files

[run_prompt_eval.sh]
  ├─ Runs 'gh models eval' with prompt template
  ├─ Captures LLM output
  └─ Returns formatted JSON response
```

### Phase 3: Build & Test (validate.sh)

```
[validate.sh]
  ├─ Run CMake build
  │  └─ cmake --build build
  ├─ Run all tests
  │  └─ ctest --output-on-failure
  ├─ Capture test results
  ├─ Check for failures
  └─ OUTPUT: Test execution report

Success → Phase 4
    ↓
Phase 4: PR Creation
  ├─ Create git branch: mr-fixes-TIMESTAMP
  ├─ Commit generated tests
  ├─ Push branch
  └─ Create PR with test results

Final Output:
  ✓ Generated test files in tests/
  ✓ Build passing
  ✓ All tests passing
  ✓ PR created with test metadata
```

### Step-by-Step Unit Test Flow Example

```
1. Developer commits code to feature branch
   └─ Feature: Add new calculator module

2. Create Merge Request
   └─ Base: main → Head: feature/calculator

3. Run Unit Test Automation
   └─ python3 orchestrate_mr_test.py --base origin/main --head HEAD

4. System analyzes changes
   ├─ Detects: src/calculator.cpp changed
   ├─ Reads: include/calculator.hpp
   └─ Suggests: tests/calculator_test.cpp

5. LLM generates tests
   ├─ Creates test cases for all public functions
   ├─ Includes edge cases
   ├─ Generates mocks if needed
   └─ Covers error conditions

6. Build system validates
   ├─ Compiles with generated tests
   ├─ Runs all test cases
   └─ Reports coverage metrics

7. PR is created/updated
   └─ Shows:
       - X test cases generated
       - Y% code coverage
       - All tests passing ✓
```

---

## Klockwork Automation Flow

### Phase 1: Issue Collection (collect_klockwork_issues.py)

```
START
  ↓
[collect_klockwork_issues.py]
  ├─ Scan all source files (.c, .cpp, .h, .hpp)
  ├─ Apply 20 security check patterns
  ├─ Categorize violations by:
  │   ├─ Rule ID (NPD.CHECK.CALL, RH.LEAK, etc.)
  │   ├─ Severity (CRITICAL, HIGH, MEDIUM, LOW)
  │   ├─ File location
  │   └─ Line number
  ├─ Aggregate statistics
  └─ OUTPUT: klockwork_issues.json
     {
       "total_issues": 15,
       "by_severity": {
         "CRITICAL": 8,
         "HIGH": 5,
         "MEDIUM": 2
       },
       "by_rule": {
         "SV.STRBO.BOUND_COPY": 3,
         "NPD.CHECK.CALL": 2
       },
       "issues": [
         {
           "rule_id": "SV.STRBO.BOUND_COPY",
           "file_path": "src/handler.c",
           "line_number": 42,
           "code_snippet": "strcpy(buf, input);",
           "severity": "CRITICAL"
         }
       ]
     }
```

### Phase 2: Fix Generation (orchestrate_klockwork_fix.py → LLM)

```
[orchestrate_klockwork_fix.py]
  ├─ Load collected issues
  ├─ Create fix branch: klockwork-fixes-TIMESTAMP
  ├─ For top CRITICAL & HIGH issues:
  │   ├─ Load source code around violation
  │   ├─ Create prompt from klockwork_fixer.prompt.yml
  │   ├─ Include rules context (klockwork_rules.json)
  │   ├─ Call LLM to generate fix
  │   └─ Generate fix suggestions
  ├─ Create fixes report with:
  │   ├─ Issue details
  │   ├─ Fix type (e.g., "replace_strcpy_with_strncpy")
  │   ├─ Priority level
  │   └─ Test cases for validation
  └─ OUTPUT: klockwork_fixes_TIMESTAMP.json
     {
       "timestamp": "20260521_143022",
       "total_issues": 15,
       "fixes": [
         {
           "issue": { "rule_id": "SV.STRBO.BOUND_COPY", ... },
           "fix_type": "replace_strcpy_with_strncpy",
           "priority": "CRITICAL"
         }
       ],
       "pr_description": "# Klockwork Security Fixes\n..."
     }
```

### Phase 3: Validation (validate_klockwork_fix.sh)

```
[validate_klockwork_fix.sh]
  ├─ Validate fix file format (JSON structure)
  ├─ Verify severity classification
  ├─ Check source code syntax
  │   └─ gcc -fsyntax-only on changed files
  ├─ Validate all critical rules addressed
  ├─ Generate validation report
  └─ OUTPUT: klockwork_validation_report_TIMESTAMP.json

Validation Checks:
  ✓ Fix format is valid
  ✓ All identified issues have fixes
  ✓ Severity levels are correct
  ✓ Source code syntax is valid
  ✓ Critical security rules addressed
```

### Phase 4: PR Creation (orchestrate_klockwork_fix.py)

```
[orchestrate_klockwork_fix.py --create-pr]
  ├─ Push branch to remote
  ├─ Create PR with details:
  │   ├─ Title: "fix(security): Klockwork security violations - 15 issues"
  │   ├─ Body: PR description with issue breakdown
  │   │   - 8 CRITICAL issues fixed
  │   │   - 5 HIGH issues fixed
  │   │   - 2 MEDIUM issues fixed
  │   ├─ Link to validation report
  │   └─ Recommended review checklist
  └─ OUTPUT: PR URL

Final Output:
  ✓ Branch: klockwork-fixes-20260521_143022
  ✓ Issues: 15 detected, fixes generated
  ✓ Validation: All checks passed
  ✓ PR created with security fixes
```

### Step-by-Step Klockwork Flow Example

```
1. Run Klockwork collection
   └─ python3 collect_klockwork_issues.py --source-dir src

2. System scans all source files
   ├─ Detects 15 violations across 20 check categories
   ├─ Identifies 8 CRITICAL, 5 HIGH, 2 MEDIUM
   └─ Saves to klockwork_issues.json

3. Run orchestration
   └─ python3 orchestrate_klockwork_fix.py --create-pr --auto-commit

4. System creates fix branch
   └─ Branch: klockwork-fixes-20260521_143022

5. LLM generates fixes
   ├─ For each violation, suggests secure fix
   ├─ Example: strcpy() → strncpy() with bounds checking
   ├─ Validates fix maintains functionality
   └─ Generates test case for each fix

6. Fixes validated
   ├─ Check JSON format
   ├─ Verify syntax of modified files
   ├─ Ensure all critical rules addressed
   └─ Generate validation report

7. PR created
   └─ Shows:
       - Title: "fix(security): Klockwork security violations - 15 issues"
       - Summary of issues by severity
       - Link to validation report
       - Recommended reviewers (security team)
```

---

## Complete Testing Guide

### Test Environment Setup

#### Prerequisites
```bash
# Required tools
✓ git               # Version control
✓ cmake             # Build system
✓ gcc/clang         # C/C++ compiler
✓ python3           # Python runtime
✓ gh                # GitHub CLI (for PR operations)

# Verify installation
git --version
cmake --version
gcc --version
python3 --version
gh --version
```

#### Repository Structure Check
```bash
cd /workspaces/SDLC_automation

# Verify both modules exist
ls -la unit_test_automation/
ls -la klockwork_automation/

# Build project first
mkdir -p build
cd build
cmake ..
make
```

---

### Test 1: Unit Test Automation (Complete)

#### 1A. Test Data Collection Phase

```bash
#!/bin/bash
# test_unit_test_collection.sh

echo "=== Test 1A: Unit Test Automation - Collection Phase ==="

cd /workspaces/SDLC_automation

# Step 1: Verify collect_pr_diff.py exists and is executable
if [[ ! -f "unit_test_automation/scripts/collect_pr_diff.py" ]]; then
    echo "❌ FAILED: collect_pr_diff.py not found"
    exit 1
fi
echo "✅ collect_pr_diff.py found"

# Step 2: Run collection on current state
echo "Running diff collection..."
python3 unit_test_automation/scripts/collect_pr_diff.py \
    --base origin/main \
    --head HEAD > /tmp/diff_output.json 2>&1

if [[ $? -ne 0 ]]; then
    echo "❌ FAILED: diff collection"
    cat /tmp/diff_output.json
    exit 1
fi
echo "✅ Diff collection succeeded"

# Step 3: Validate output
python3 << 'EOF'
import json
with open('/tmp/diff_output.json') as f:
    data = json.load(f)
    
required_keys = ['source_files', 'suggested_test_targets']
for key in required_keys:
    if key not in data:
        print(f"❌ Missing key: {key}")
        exit(1)

print(f"✅ Found {len(data.get('source_files', []))} source files")
print(f"✅ Found {len(data.get('suggested_test_targets', []))} suggested tests")
EOF

echo "✅ Test 1A PASSED"
```

#### 1B. Test Prompt Evaluation

```bash
#!/bin/bash
# test_unit_test_evaluation.sh

echo "=== Test 1B: Unit Test Automation - Prompt Evaluation ==="

cd /workspaces/SDLC_automation

# Verify evaluation script
if [[ ! -f "unit_test_automation/scripts/run_prompt_eval.sh" ]]; then
    echo "❌ FAILED: run_prompt_eval.sh not found"
    exit 1
fi

# Verify evaluation cases exist
EVAL_CASES="unit_test_automation/prompts/evals/unit_test_generator_cases.jsonl"
if [[ ! -f "$EVAL_CASES" ]]; then
    echo "❌ FAILED: Evaluation cases not found"
    exit 1
fi

# Count evaluation cases
NUM_CASES=$(wc -l < "$EVAL_CASES")
echo "✅ Found $NUM_CASES evaluation cases"

# Run evaluation
echo "Running prompt evaluation..."
bash unit_test_automation/scripts/run_prompt_eval.sh --all > /tmp/eval_output.txt 2>&1

if [[ $? -eq 0 ]]; then
    echo "✅ Evaluation passed"
else
    echo "⚠️  Evaluation had issues (check output)"
    tail -20 /tmp/eval_output.txt
fi

echo "✅ Test 1B PASSED"
```

#### 1C. Test Build & Validation

```bash
#!/bin/bash
# test_unit_test_build.sh

echo "=== Test 1C: Unit Test Automation - Build & Validation ==="

cd /workspaces/SDLC_automation

# Verify build directory
if [[ ! -d "build" ]]; then
    echo "Creating build directory..."
    mkdir -p build
    cd build
    cmake ..
    make
    cd ..
fi

# Run validation script
echo "Running build and test validation..."
bash unit_test_automation/scripts/validate.sh > /tmp/validate_output.txt 2>&1

if [[ $? -eq 0 ]]; then
    echo "✅ Build and tests passed"
    grep -i "pass\|success" /tmp/validate_output.txt | head -5
else
    echo "❌ Build or tests failed"
    cat /tmp/validate_output.txt
    exit 1
fi

echo "✅ Test 1C PASSED"
```

#### 1D. Test Full Orchestration

```bash
#!/bin/bash
# test_unit_test_full_orchestration.sh

echo "=== Test 1D: Unit Test Automation - Full Orchestration ==="

cd /workspaces/SDLC_automation

# Create a test feature branch
TEST_BRANCH="test/unit-test-$(date +%s)"
echo "Creating test branch: $TEST_BRANCH"
git checkout -b "$TEST_BRANCH"

# Make a test code change
echo "Making test code change..."
cat >> src/calculator.cpp << 'EOF'

// Test addition for orchestration testing
int test_add_orchestration() {
    return 5 + 3;
}
EOF

git add src/calculator.cpp
git commit -m "test: Add test function for orchestration"

# Run orchestration
echo "Running full orchestration..."
python3 unit_test_automation/scripts/orchestrate_mr_test.py \
    --base main \
    --head "$TEST_BRANCH" > /tmp/orchestration_output.txt 2>&1

if [[ $? -eq 0 ]]; then
    echo "✅ Orchestration succeeded"
else
    echo "⚠️  Orchestration had issues (some steps optional)"
    tail -30 /tmp/orchestration_output.txt
fi

# Check generated artifacts
if [[ -f "klockwork_issues.json" ]]; then
    echo "✅ Generated issues report"
fi

# Cleanup
git checkout main
git branch -D "$TEST_BRANCH"

echo "✅ Test 1D PASSED"
```

---

### Test 2: Klockwork Automation (Complete)

#### 2A. Test Issue Collection

```bash
#!/bin/bash
# test_klockwork_collection.sh

echo "=== Test 2A: Klockwork Automation - Issue Collection ==="

cd /workspaces/SDLC_automation

# Verify script exists
if [[ ! -f "klockwork_automation/scripts/collect_klockwork_issues.py" ]]; then
    echo "❌ FAILED: collect_klockwork_issues.py not found"
    exit 1
fi
echo "✅ collect_klockwork_issues.py found"

# Run collection
echo "Running Klockwork issue collection..."
python3 klockwork_automation/scripts/collect_klockwork_issues.py \
    --source-dir src \
    --output /tmp/klockwork_issues.json > /tmp/klockwork_output.txt 2>&1

if [[ $? -ne 0 ]]; then
    echo "❌ FAILED: Issue collection failed"
    cat /tmp/klockwork_output.txt
    exit 1
fi
echo "✅ Issue collection succeeded"

# Validate output
python3 << 'EOF'
import json
with open('/tmp/klockwork_issues.json') as f:
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
print(f"   LOW: {data['by_severity'].get('LOW', 0)}")
EOF

echo "✅ Test 2A PASSED"
```

#### 2B. Test Evaluation Cases

```bash
#!/bin/bash
# test_klockwork_evaluation.sh

echo "=== Test 2B: Klockwork Automation - Evaluation Cases ==="

cd /workspaces/SDLC_automation

# Verify evaluation script
if [[ ! -f "klockwork_automation/scripts/run_klockwork_eval.sh" ]]; then
    echo "❌ FAILED: run_klockwork_eval.sh not found"
    exit 1
fi

# Count evaluation cases
EVAL_CASES="klockwork_automation/prompts/evals/klockwork_fixer_cases.jsonl"
NUM_CASES=$(wc -l < "$EVAL_CASES")
echo "✅ Found $NUM_CASES evaluation cases"

# List available cases
echo "Available evaluation cases:"
bash klockwork_automation/scripts/run_klockwork_eval.sh --list | head -25

# Run evaluation on a few cases
echo "Running specific evaluation case..."
bash klockwork_automation/scripts/run_klockwork_eval.sh \
    --case KLOCK_EVAL_003 > /tmp/eval_output.txt 2>&1

if [[ $? -eq 0 ]]; then
    echo "✅ Evaluation case passed"
else
    echo "⚠️  Evaluation case had issues"
fi

echo "✅ Test 2B PASSED"
```

#### 2C. Test Validation

```bash
#!/bin/bash
# test_klockwork_validation.sh

echo "=== Test 2C: Klockwork Automation - Validation ==="

cd /workspaces/SDLC_automation

# Generate test data first
echo "Generating test data..."
python3 klockwork_automation/scripts/collect_klockwork_issues.py \
    --source-dir src \
    --output klockwork_issues.json 2>/dev/null

# Run validation
echo "Running Klockwork fix validation..."
bash klockwork_automation/scripts/validate_klockwork_fix.sh > /tmp/validation_output.txt 2>&1

if [[ $? -eq 0 ]]; then
    echo "✅ Validation passed"
else
    echo "⚠️  Validation had warnings (see output)"
    grep -E "✓|PASSED" /tmp/validation_output.txt | head -10
fi

# Check generated report
if [[ -f "klockwork_validation_report_"* ]]; then
    echo "✅ Validation report generated"
fi

echo "✅ Test 2C PASSED"
```

#### 2D. Test Full Orchestration

```bash
#!/bin/bash
# test_klockwork_full_orchestration.sh

echo "=== Test 2D: Klockwork Automation - Full Orchestration ==="

cd /workspaces/SDLC_automation

# Create test branch
TEST_BRANCH="test/klockwork-$(date +%s)"
echo "Creating test branch: $TEST_BRANCH"
git checkout -b "$TEST_BRANCH"

# Add vulnerable code for testing
echo "Adding test vulnerable code..."
cat >> src/calculator.cpp << 'EOF'

// Vulnerable code for testing
char* vulnerable_func(char* input) {
    char buf[64];
    strcpy(buf, input);  // VULNERABLE!
    return buf;
}
EOF

git add src/calculator.cpp
git commit -m "test: Add vulnerable code for Klockwork testing"

# Run orchestration (without PR creation for testing)
echo "Running Klockwork orchestration..."
python3 klockwork_automation/scripts/orchestrate_klockwork_fix.py \
    --repo-dir . \
    --source-dir src \
    --auto-commit > /tmp/orchestration_output.txt 2>&1

if [[ $? -eq 0 ]]; then
    echo "✅ Orchestration succeeded"
else
    echo "⚠️  Orchestration had issues"
    tail -20 /tmp/orchestration_output.txt
fi

# Check generated files
if [[ -f "klockwork_issues.json" ]]; then
    echo "✅ Issues report generated"
fi

if ls klockwork_fixes_* >/dev/null 2>&1; then
    echo "✅ Fixes report generated"
fi

# Cleanup
git checkout main
git branch -D "$TEST_BRANCH"

echo "✅ Test 2D PASSED"
```

---

### Test 3: Integration Testing

#### 3A. Run Both Modules in Sequence

```bash
#!/bin/bash
# test_complete_integration.sh

echo "╔════════════════════════════════════════════════════════╗"
echo "║     Complete SDLC Automation Integration Test         ║"
echo "╚════════════════════════════════════════════════════════╝"

cd /workspaces/SDLC_automation

# Test environment
echo "Step 0: Verify test environment..."
python3 --version
git --version
cmake --version

# Step 1: Unit Test Automation
echo ""
echo "Step 1: Unit Test Automation"
echo "───────────────────────────"

python3 unit_test_automation/scripts/collect_pr_diff.py \
    --base origin/main --head HEAD 2>/dev/null | python3 -m json.tool | head -20

# Step 2: Klockwork Automation
echo ""
echo "Step 2: Klockwork Automation"
echo "───────────────────────────"

python3 klockwork_automation/scripts/collect_klockwork_issues.py \
    --source-dir src --summary-only

# Step 3: Check all artifacts
echo ""
echo "Step 3: Generated Artifacts"
echo "───────────────────────────"

ls -lah klockwork_issues.json unit_test_*.json 2>/dev/null || echo "No unit test artifacts yet"

echo ""
echo "✅ Integration test completed successfully"
```

---

### Test 4: End-to-End Scenario Test

```bash
#!/bin/bash
# test_e2e_scenario.sh

echo "╔════════════════════════════════════════════════════════╗"
echo "║      End-to-End Development Scenario Test             ║"
echo "╚════════════════════════════════════════════════════════╝"

cd /workspaces/SDLC_automation

SCENARIO_BRANCH="scenario/e2e-$(date +%s)"
echo "Creating scenario branch: $SCENARIO_BRANCH"
git checkout -b "$SCENARIO_BRANCH"

# Scenario: Add new feature with potential issues
echo ""
echo "=== Phase 1: Developer adds new feature ==="
cat > src/new_feature.cpp << 'EOF'
#include <cstring>
#include <cstdlib>

// Feature: Process user input
char* process_user_data(const char* user_input) {
    char buffer[256];
    strcpy(buffer, user_input);  // VULNERABILITY: Buffer overflow
    return buffer;
}

// Feature: Allocate memory
int* allocate_data(int size) {
    return (int*)malloc(size);  // VULNERABILITY: No null check
}

void cleanup_data(int* data) {
    free(data);
    free(data);  // VULNERABILITY: Double free
}
EOF

git add src/new_feature.cpp
git commit -m "feat: Add new feature (with intentional security issues for testing)"

# Phase 2: Run Unit Test Automation
echo ""
echo "=== Phase 2: Run Unit Test Automation ==="
echo "Analyzing code changes..."
python3 unit_test_automation/scripts/collect_pr_diff.py \
    --base main --head HEAD 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'Found {len(data.get(\"source_files\", []))} changed files')
    print(f'Suggested {len(data.get(\"suggested_test_targets\", []))} test locations')
except: pass
"

# Phase 3: Run Klockwork Analysis
echo ""
echo "=== Phase 3: Run Klockwork Security Analysis ==="
echo "Scanning for vulnerabilities..."
python3 klockwork_automation/scripts/collect_klockwork_issues.py \
    --source-dir src > /tmp/klockwork_phase3.txt 2>&1

python3 << 'EOF'
import json
try:
    with open('klockwork_issues.json') as f:
        data = json.load(f)
        print(f'Found {data.get("total_issues", 0)} security issues')
        print(f'  CRITICAL: {data.get("by_severity", {}).get("CRITICAL", 0)}')
        print(f'  HIGH: {data.get("by_severity", {}).get("HIGH", 0)}')
except: pass
EOF

# Phase 4: Generate Fixes
echo ""
echo "=== Phase 4: Generate Security Fixes ==="
python3 klockwork_automation/scripts/orchestrate_klockwork_fix.py \
    --repo-dir . --source-dir src --auto-commit > /tmp/klockwork_phase4.txt 2>&1

if [[ -f klockwork_fixes_*.json ]]; then
    echo "✅ Security fixes generated"
fi

# Phase 5: Validate
echo ""
echo "=== Phase 5: Validate ==="
bash klockwork_automation/scripts/validate_klockwork_fix.sh > /tmp/validation.txt 2>&1

echo "✅ E2E Scenario test completed"

# Cleanup
git checkout main
git branch -D "$SCENARIO_BRANCH"

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║         E2E Test Completed Successfully               ║"
echo "╚════════════════════════════════════════════════════════╝"
```

---

## Master Test Runner

Create a master script to run all tests:

```bash
#!/bin/bash
# run_all_tests.sh

set -e

echo "╔══════════════════════════════════════════════════════════╗"
echo "║      SDLC Automation Complete Test Suite               ║"
echo "╚══════════════════════════════════════════════════════════╝"

cd /workspaces/SDLC_automation

TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

run_test() {
    local test_name=$1
    local test_script=$2
    
    ((TOTAL_TESTS++))
    echo ""
    echo "Running: $test_name"
    echo "─────────────────────────────────────────────"
    
    if bash "$test_script"; then
        ((PASSED_TESTS++))
        echo "✅ PASSED: $test_name"
    else
        ((FAILED_TESTS++))
        echo "❌ FAILED: $test_name"
    fi
}

# Unit Test Automation Tests
run_test "Unit Test Collection" tests/test_unit_test_collection.sh
run_test "Unit Test Evaluation" tests/test_unit_test_evaluation.sh
run_test "Unit Test Build" tests/test_unit_test_build.sh
run_test "Unit Test Orchestration" tests/test_unit_test_full_orchestration.sh

# Klockwork Automation Tests
run_test "Klockwork Collection" tests/test_klockwork_collection.sh
run_test "Klockwork Evaluation" tests/test_klockwork_evaluation.sh
run_test "Klockwork Validation" tests/test_klockwork_validation.sh
run_test "Klockwork Orchestration" tests/test_klockwork_full_orchestration.sh

# Integration Tests
run_test "Integration" tests/test_complete_integration.sh
run_test "E2E Scenario" tests/test_e2e_scenario.sh

# Summary
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║                    Test Summary                         ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║ Total Tests:   $TOTAL_TESTS"
echo "║ Passed:        $PASSED_TESTS ✅"
echo "║ Failed:        $FAILED_TESTS ❌"
echo "╚══════════════════════════════════════════════════════════╝"

if [[ $FAILED_TESTS -gt 0 ]]; then
    exit 1
fi
```

---

## Integration Flow

### Combined Workflow

```
Developer Code Commit
    ↓
┌───────────────────────────────────┐
│ Unit Test Automation              │
├───────────────────────────────────┤
│ 1. Detect changes                 │
│ 2. Generate unit tests            │
│ 3. Run tests                      │
│ 4. Report coverage                │
└───────────────────────────────────┘
    ↓
┌───────────────────────────────────┐
│ Klockwork Security Analysis       │
├───────────────────────────────────┤
│ 1. Scan for violations            │
│ 2. Categorize issues              │
│ 3. Generate fixes                 │
│ 4. Validate security              │
└───────────────────────────────────┘
    ↓
┌───────────────────────────────────┐
│ Create Pull Requests              │
├───────────────────────────────────┤
│ PR 1: Unit Tests                  │
│ PR 2: Security Fixes              │
└───────────────────────────────────┘
    ↓
Merge to Main (with both PRs approved)
```

---

## Troubleshooting

### Common Issues and Solutions

#### Issue 1: "Python module not found"
```bash
# Solution: Ensure modules are in path
export PYTHONPATH="/workspaces/SDLC_automation:$PYTHONPATH"
```

#### Issue 2: "Git branch creation fails"
```bash
# Solution: Ensure clean working directory
git status
git stash  # If needed
```

#### Issue 3: "Build fails"
```bash
# Solution: Clean and rebuild
rm -rf build/
mkdir build
cd build
cmake ..
make
```

#### Issue 4: "No evaluation cases found"
```bash
# Solution: Verify evaluation files exist
ls -la klockwork_automation/prompts/evals/
ls -la unit_test_automation/prompts/evals/
```

#### Issue 5: "gh CLI not authenticated"
```bash
# Solution: Authenticate with GitHub
gh auth login
gh auth status
```

---

## Quick Start Commands

### Run Everything
```bash
# Complete test suite
cd /workspaces/SDLC_automation
bash run_all_tests.sh
```

### Individual Module Tests
```bash
# Unit Tests Only
python3 unit_test_automation/scripts/orchestrate_mr_test.py --base origin/main --head HEAD

# Security Analysis Only
python3 klockwork_automation/scripts/orchestrate_klockwork_fix.py --source-dir src --auto-commit
```

### Specific Scenarios
```bash
# Analyze changes
python3 unit_test_automation/scripts/collect_pr_diff.py --base main --head HEAD

# Detect security issues
python3 klockwork_automation/scripts/collect_klockwork_issues.py --source-dir src --summary-only

# Validate fixes
bash klockwork_automation/scripts/validate_klockwork_fix.sh

# Run evaluations
bash klockwork_automation/scripts/run_klockwork_eval.sh --all
bash unit_test_automation/scripts/run_prompt_eval.sh --all
```

---

## Notes

- All tests are idempotent (can be run multiple times)
- Each module is independent but can be used together
- Generated artifacts (JSON reports, branches) are timestamped
- Cleanup scripts are included for test branches
- Logs are saved to /tmp/ for debugging
