# Quick Start Testing Guide

## Overview

This guide shows you how to test both the **Unit Test Automation** and **Klockwork Automation** modules.

## Directory Structure

```
/workspaces/SDLC_automation/
├── COMPLETE_FLOW_AND_TESTING_GUIDE.md     ← Comprehensive flow guide
├── QUICK_START_TESTING.md                 ← This file
├── run_all_tests.sh                       ← Master test runner
├── unit_test_automation/
│   ├── scripts/
│   ├── prompts/
│   └── include/
├── klockwork_automation/
│   ├── scripts/
│   ├── prompts/
│   └── include/
└── tests/
    └── automation/
        ├── test_unit_test_collection.sh
        ├── test_klockwork_collection.sh
        ├── test_klockwork_evaluation.sh
        ├── test_klockwork_validation.sh
        ├── test_build_validation.sh
        └── test_integration.sh
```

---

## Option 1: Run Everything at Once (Recommended)

```bash
cd /workspaces/SDLC_automation
bash run_all_tests.sh
```

**Expected Output:**
```
╔══════════════════════════════════════════════════════════╗
║    SDLC Automation Complete Test Suite                  ║
╠══════════════════════════════════════════════════════════╣
║ Test logs directory: /tmp/sdlc_automation_test_XXXXX
╚══════════════════════════════════════════════════════════╝

[Section 1: Build & Environment]
[✓] Build and Validation

[Section 2: Unit Test Automation]
[✓] Unit Test Collection Phase

[Section 3: Klockwork Automation]
[✓] Klockwork Collection Phase
[✓] Klockwork Evaluation Cases
[✓] Klockwork Validation

[Section 4: Integration Testing]
[✓] Integration Test

╔══════════════════════════════════════════════════════════╗
║                    Test Summary                         ║
╠══════════════════════════════════════════════════════════╣
║ Total Tests:    6
║ Passed:        6 ✅
║ Failed:        0
║ Skipped:       0
║
║ Pass Rate: 100%
╚══════════════════════════════════════════════════════════╝
```

---

## Option 2: Run Individual Module Tests

### Unit Test Automation Tests

```bash
# Test collection phase
bash /workspaces/SDLC_automation/tests/automation/test_unit_test_collection.sh

# Expected output:
# === Test 1A: Unit Test Automation - Collection Phase ===
# ✅ collect_pr_diff.py found
# ✅ collect_pr_diff.py syntax is valid
# ✅ Test 1A PASSED
```

### Klockwork Automation Tests

```bash
# Test collection phase
bash /workspaces/SDLC_automation/tests/automation/test_klockwork_collection.sh

# Expected output:
# === Test 2A: Klockwork Automation - Issue Collection ===
# ✅ collect_klockwork_issues.py found
# ✅ Issue collection succeeded
# ✅ Found X Klockwork issues
# ✅ Test 2A PASSED

# Test evaluation
bash /workspaces/SDLC_automation/tests/automation/test_klockwork_evaluation.sh

# Test validation
bash /workspaces/SDLC_automation/tests/automation/test_klockwork_validation.sh
```

---

## Option 3: Run Actual Module Commands

### Unit Test Automation Workflow

```bash
cd /workspaces/SDLC_automation

# Step 1: Collect PR diff
python3 unit_test_automation/scripts/collect_pr_diff.py \
    --base origin/main \
    --head HEAD | python3 -m json.tool

# Step 2: Run evaluation
bash unit_test_automation/scripts/run_prompt_eval.sh --help
```

### Klockwork Automation Workflow

```bash
cd /workspaces/SDLC_automation

# Step 1: Collect Klockwork issues
python3 klockwork_automation/scripts/collect_klockwork_issues.py \
    --source-dir src \
    --summary-only

# Step 2: Run evaluation
bash klockwork_automation/scripts/run_klockwork_eval.sh --list

# Step 3: Validate fixes
bash klockwork_automation/scripts/validate_klockwork_fix.sh
```

---

## Test Options

### Run with Verbose Output

```bash
bash run_all_tests.sh --verbose
```

This shows all test output directly in the console instead of saving to files.

### Keep Test Logs

```bash
bash run_all_tests.sh --keep-logs
```

This preserves the test log directory for inspection.

### Quick Test (Essential Only)

```bash
bash run_all_tests.sh --quick
```

Runs a subset of tests for faster validation.

---

## Understanding Test Results

### Passing Test
```
[✓] Test Name
```
The test completed successfully.

### Failed Test
```
[✗] Test Name
  See log: /tmp/sdlc_automation_test_XXXXX/test_name.sh.log
```
The test failed. Check the log file for details.

### Skipped Test
```
[⊘] Test Name
```
The test was skipped (usually because required file wasn't found).

---

## Common Test Scenarios

### Scenario 1: Verify Both Modules Are Installed

```bash
bash /workspaces/SDLC_automation/tests/automation/test_integration.sh
```

**What it checks:**
- ✓ Python is available
- ✓ Git is available  
- ✓ Unit test automation files exist
- ✓ Klockwork automation files exist
- ✓ All core prompt files are present

### Scenario 2: Test Klockwork Detection

```bash
python3 /workspaces/SDLC_automation/klockwork_automation/scripts/collect_klockwork_issues.py \
    --source-dir src \
    --output /tmp/test_issues.json

cat /tmp/test_issues.json | python3 -m json.tool
```

**What to look for:**
```json
{
  "total_issues": 0,
  "by_severity": {
    "CRITICAL": 0,
    "HIGH": 0,
    "MEDIUM": 0,
    "LOW": 0
  },
  "by_rule": {},
  "issues": []
}
```

(If no issues found, that's expected - code is clean!)

### Scenario 3: Test Klockwork Evaluation

```bash
bash /workspaces/SDLC_automation/klockwork_automation/scripts/run_klockwork_eval.sh --case KLOCK_EVAL_001
```

**Expected output:**
```
Running KLOCK_EVAL_001: Null Pointer Dereference Detection
[✓] KLOCK_EVAL_001 passed basic validation
```

---

## Test Execution Timeline

| Test | Duration | Description |
|------|----------|-------------|
| Build & Validation | ~5-10s | Builds project and checks environment |
| Unit Test Collection | ~2-3s | Validates diff collection script |
| Klockwork Collection | ~5-10s | Scans source code for violations |
| Klockwork Evaluation | ~2-3s | Tests evaluation cases |
| Klockwork Validation | ~3-5s | Validates fix format and structure |
| Integration Test | ~2-3s | Verifies all components work together |
| **Total** | **~20-40s** | Entire test suite |

---

## Troubleshooting

### Issue: "Command not found: bash"

**Solution:**
```bash
which bash  # Should return /bin/bash
```

### Issue: "Permission denied" on test scripts

**Solution:**
```bash
chmod +x /workspaces/SDLC_automation/run_all_tests.sh
chmod +x /workspaces/SDLC_automation/tests/automation/*.sh
```

### Issue: "Python module not found"

**Solution:**
```bash
python3 --version  # Should be 3.7+
export PYTHONPATH="/workspaces/SDLC_automation:$PYTHONPATH"
```

### Issue: "Git branch error"

**Solution:**
```bash
cd /workspaces/SDLC_automation
git status      # Check if repo is clean
git stash       # If needed
```

---

## Next Steps

After running tests successfully:

1. **Read the complete flow guide:**
   ```bash
   cat COMPLETE_FLOW_AND_TESTING_GUIDE.md | less
   ```

2. **Run actual automation on your code:**
   ```bash
   # Unit tests
   python3 unit_test_automation/scripts/orchestrate_mr_test.py --base main --head HEAD

   # Security fixes
   python3 klockwork_automation/scripts/orchestrate_klockwork_fix.py --source-dir src --create-pr
   ```

3. **Create a feature branch and test:**
   ```bash
   git checkout -b feature/test-automation
   # Make code changes
   git commit -m "test: Add code for automation testing"
   # Then run the orchestration scripts
   ```

---

## Test Files Location

All test files are located in:
```
/workspaces/SDLC_automation/tests/automation/
```

Test logs are saved to (timestamped):
```
/tmp/sdlc_automation_test_XXXXXXXXXX/
```

---

## Questions or Issues?

Refer to the comprehensive guide:
```bash
less /workspaces/SDLC_automation/COMPLETE_FLOW_AND_TESTING_GUIDE.md
```

Or check individual module READMEs:
```bash
cat /workspaces/SDLC_automation/unit_test_automation/README.md
cat /workspaces/SDLC_automation/klockwork_automation/README.md
```
