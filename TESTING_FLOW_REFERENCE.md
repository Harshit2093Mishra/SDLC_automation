# SDLC Automation Testing - Visual Flow Reference

## 🎯 Quick Reference

### For the Impatient (1 line to test everything)

```bash
cd /workspaces/SDLC_automation && bash run_all_tests.sh
```

---

## 📊 Complete Flow Diagrams

### Unit Test Automation Flow

```
┌─────────────────────────────────────────────────────────────┐
│              UNIT TEST AUTOMATION FLOW                      │
└─────────────────────────────────────────────────────────────┘

    1. Code Changed
         ↓
    ┌──────────────────────────────────────┐
    │ collect_pr_diff.py                   │
    │ ────────────────────────────────────  │
    │ • Parse git diff base → head          │
    │ • Extract changed source files       │
    │ • Suggest test file locations        │
    │ OUTPUT: diff.json                    │
    └──────────────────────────────────────┘
         ↓
    ┌──────────────────────────────────────┐
    │ orchestrate_mr_test.py               │
    │ ────────────────────────────────────  │
    │ • Load diff.json                     │
    │ • For each changed file:             │
    │   - Load source code                 │
    │   - Create LLM prompt                │
    │   - Call LLM (gh models eval)        │
    │ • Parse LLM response                 │
    │ • Write test files                   │
    │ OUTPUT: Generated test .cpp files    │
    └──────────────────────────────────────┘
         ↓
    ┌──────────────────────────────────────┐
    │ validate.sh                          │
    │ ────────────────────────────────────  │
    │ • CMake build                        │
    │ • Run CTest                          │
    │ • Verify all tests pass              │
    │ OUTPUT: Test results                 │
    └──────────────────────────────────────┘
         ↓
    📊 RESULT: Tests generated, passing, PR ready

TEST ENTRY POINT: tests/automation/test_unit_test_collection.sh
```

### Klockwork Automation Flow

```
┌─────────────────────────────────────────────────────────────┐
│             KLOCKWORK AUTOMATION FLOW                       │
└─────────────────────────────────────────────────────────────┘

    1. Code Exists
         ↓
    ┌──────────────────────────────────────┐
    │ collect_klockwork_issues.py          │
    │ ────────────────────────────────────  │
    │ • Scan all source files              │
    │ • Apply 20 security check patterns   │
    │ • Categorize by severity:            │
    │   - CRITICAL (8 types)               │
    │   - HIGH (7 types)                   │
    │   - MEDIUM (3 types)                 │
    │   - LOW (2 types)                    │
    │ OUTPUT: klockwork_issues.json        │
    └──────────────────────────────────────┘
         ↓
    ┌──────────────────────────────────────┐
    │ orchestrate_klockwork_fix.py         │
    │ ────────────────────────────────────  │
    │ • Load issues.json                   │
    │ • Create git branch                  │
    │ • For top CRITICAL + HIGH issues:    │
    │   - Create LLM prompt                │
    │   - Include rule context             │
    │   - Generate fix suggestions         │
    │ • Create PR description              │
    │ OUTPUT: klockwork_fixes_*.json       │
    │ OUTPUT: PR created (optional)        │
    └──────────────────────────────────────┘
         ↓
    ┌──────────────────────────────────────┐
    │ validate_klockwork_fix.sh            │
    │ ────────────────────────────────────  │
    │ • Validate JSON format               │
    │ • Check severity levels              │
    │ • Verify all rules addressed         │
    │ • Test source syntax                 │
    │ OUTPUT: validation_report.json       │
    └──────────────────────────────────────┘
         ↓
    ┌──────────────────────────────────────┐
    │ run_klockwork_eval.sh                │
    │ ────────────────────────────────────  │
    │ • Run 20 evaluation test cases       │
    │ • Validate detection accuracy        │
    │ • Verify fix generation works        │
    │ OUTPUT: Test results                 │
    └──────────────────────────────────────┘
         ↓
    🔒 RESULT: Security issues fixed, validated, PR ready

TEST ENTRY POINTS:
  - tests/automation/test_klockwork_collection.sh
  - tests/automation/test_klockwork_evaluation.sh
  - tests/automation/test_klockwork_validation.sh
```

---

## 🧪 Test Execution Map

```
run_all_tests.sh (Master Runner)
    │
    ├─── Section 1: Build & Environment ────────────────┐
    │                                                    │
    │    test_build_validation.sh                       │
    │    • Verify CMake setup                           │
    │    • Build project                                │
    │    • Check compilation                            │
    │                                                    │
    ├─── Section 2: Unit Test Automation ───────────────┤
    │                                                    │
    │    test_unit_test_collection.sh                   │
    │    • Verify collect_pr_diff.py exists             │
    │    • Check syntax validity                        │
    │    • Validate script structure                    │
    │                                                    │
    ├─── Section 3: Klockwork Automation ───────────────┤
    │                                                    │
    │    test_klockwork_collection.sh                   │
    │    • Verify collection script exists              │
    │    • Run issue collection                         │
    │    • Validate JSON output                         │
    │                                                    │
    │    test_klockwork_evaluation.sh                   │
    │    • Check evaluation cases exist                 │
    │    • Run sample test case                         │
    │    • Verify evaluation framework                  │
    │                                                    │
    │    test_klockwork_validation.sh                   │
    │    • Run validation script                        │
    │    • Check validation logic                       │
    │    • Generate validation report                   │
    │                                                    │
    ├─── Section 4: Integration Testing ────────────────┤
    │                                                    │
    │    test_integration.sh                            │
    │    • Verify both modules present                  │
    │    • Check all artifacts exist                    │
    │    • Validate framework integrity                 │
    │                                                    │
    └─────────────────────────────────────────────────────┘
         │
         ↓
    📋 Summary Report with Pass/Fail Status
```

---

## 🚀 Running Tests - Different Ways

### Way 1: Run Everything (Recommended)
```bash
cd /workspaces/SDLC_automation
bash run_all_tests.sh
```
⏱️ Time: ~30-40 seconds
📊 Output: Complete test summary with pass/fail status

### Way 2: Run Specific Test
```bash
bash tests/automation/test_klockwork_collection.sh
bash tests/automation/test_unit_test_collection.sh
bash tests/automation/test_integration.sh
```
⏱️ Time: ~5-10 seconds each
📊 Output: Individual test results

### Way 3: Run with Options
```bash
bash run_all_tests.sh --verbose      # Show full output
bash run_all_tests.sh --keep-logs    # Save logs for inspection
bash run_all_tests.sh --quick        # Fast subset only
```

### Way 4: Run Modules Directly
```bash
# Unit Test Analysis
python3 unit_test_automation/scripts/collect_pr_diff.py --base main --head HEAD

# Klockwork Analysis
python3 klockwork_automation/scripts/collect_klockwork_issues.py --source-dir src --summary-only

# Klockwork Evaluation
bash klockwork_automation/scripts/run_klockwork_eval.sh --list
bash klockwork_automation/scripts/run_klockwork_eval.sh --case KLOCK_EVAL_001

# Klockwork Validation
bash klockwork_automation/scripts/validate_klockwork_fix.sh
```

---

## 📁 Test File Organization

```
/workspaces/SDLC_automation/
├── 📄 COMPLETE_FLOW_AND_TESTING_GUIDE.md     ← 600+ lines detailed guide
├── 📄 QUICK_START_TESTING.md                 ← Quick reference (this file)
├── 📄 TESTING_FLOW_REFERENCE.md              ← Visual diagrams (this file)
│
├── 🔧 run_all_tests.sh                       ← Master test runner
│
├── 📁 tests/
│   └── automation/
│       ├── test_build_validation.sh          ← Build check
│       ├── test_unit_test_collection.sh      ← Unit test phase 1
│       ├── test_klockwork_collection.sh      ← Klockwork phase 1
│       ├── test_klockwork_evaluation.sh      ← Klockwork phase 2
│       ├── test_klockwork_validation.sh      ← Klockwork phase 3
│       └── test_integration.sh               ← Integration test
│
├── unit_test_automation/
│   ├── 📄 README.md
│   ├── scripts/
│   └── prompts/
│
├── klockwork_automation/
│   ├── 📄 README.md
│   ├── scripts/
│   └── prompts/
│       ├── klockwork_rules.json              ← 20 security rules
│       └── klockwork_fixer.prompt.yml        ← LLM prompt template
```

---

## 🎓 Learning Path

### 1. Start Here: Quick Verification
```bash
# Run quick test to verify everything is installed
bash /workspaces/SDLC_automation/run_all_tests.sh --quick
```

### 2. Then: Run Full Test Suite
```bash
# Run comprehensive tests
bash /workspaces/SDLC_automation/run_all_tests.sh
```

### 3. Then: Read the Complete Guide
```bash
# Understand all the details
less /workspaces/SDLC_automation/COMPLETE_FLOW_AND_TESTING_GUIDE.md
```

### 4. Finally: Try It on Real Code
```bash
# Create a test branch
git checkout -b feature/test-automation

# Make some code changes
# ... add or modify files ...

# Run the automation
python3 unit_test_automation/scripts/orchestrate_mr_test.py --base main --head HEAD
python3 klockwork_automation/scripts/orchestrate_klockwork_fix.py --source-dir src --create-pr
```

---

## 📊 Expected Test Results

### Successful Run
```
╔══════════════════════════════════════════════════════════╗
║    SDLC Automation Complete Test Suite                  ║
╚══════════════════════════════════════════════════════════╝

[✓] Build and Validation
[✓] Unit Test Collection Phase
[✓] Klockwork Collection Phase
[✓] Klockwork Evaluation Cases
[✓] Klockwork Validation
[✓] Integration Test

╔══════════════════════════════════════════════════════════╗
║                    Test Summary                         ║
║ Total Tests:    6
║ Passed:        6 ✅
║ Failed:        0
║ Pass Rate: 100%
╚══════════════════════════════════════════════════════════╝
```

### What Each Test Checks

| Test | Checks |
|------|--------|
| Build & Validation | CMake setup, compilation |
| Unit Test Collection | PR diff analysis script |
| Klockwork Collection | Source code scanning |
| Klockwork Evaluation | Test case execution |
| Klockwork Validation | Fix validation logic |
| Integration | All components work together |

---

## 🔍 Debugging Failed Tests

### Check individual test logs
```bash
cat /tmp/sdlc_automation_test_*/test_klockwork_collection.sh.log
```

### Run test with full output
```bash
bash tests/automation/test_klockwork_collection.sh 2>&1 | tee /tmp/test_output.log
```

### Verify dependencies
```bash
python3 --version
git --version
cmake --version
gcc --version
```

### Check script syntax
```bash
bash -n tests/automation/test_klockwork_collection.sh
```

---

## 📝 Test Summary

**Total Files Created:**
- 1 Master test runner
- 6 Individual test scripts
- 2 Documentation files

**Total Testing Coverage:**
- ✓ Build environment
- ✓ Unit test automation
- ✓ Klockwork automation (3 phases)
- ✓ Integration testing

**Execution Time:** ~30-40 seconds for full suite

**Artifacts Generated:**
- Test logs (timestamped)
- Pass/fail summary
- Detailed error logs for debugging

---

## 🚀 Next: Run Your First Test

```bash
cd /workspaces/SDLC_automation
bash run_all_tests.sh
```

Then check the summary and logs to understand the flow!
