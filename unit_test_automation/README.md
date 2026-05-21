# Unit Test Automation Module

Automated unit test generation and validation framework for C/C++ code changes.

## Overview

The Unit Test Automation module automatically:
1. **Detects code changes** via git diff analysis
2. **Generates unit tests** using LLM-powered analysis
3. **Validates tests** by building and running with CMake + CTest
4. **Creates PRs** with test results

## Architecture

```
Code Change
    ↓
collect_pr_diff.py (Analyze changes)
    ↓
orchestrate_mr_test.py (Generate tests via LLM)
    ↓
validate.sh (Build & run tests)
    ↓
GitHub PR Creation
```

## Components

### Scripts

- **collect_pr_diff.py** - Analyzes git diff to identify changed functions and code patterns
- **orchestrate_mr_test.py** - Orchestrates test generation workflow with LLM
- **validate.sh** - Builds project and runs CMake tests
- **run_prompt_eval.sh** - Runs evaluation test cases

### Prompts

- **unit_test_generator.prompt.yml** - LLM prompt template for test generation

### Evaluation

- **evals/unit_test_generator_cases.jsonl** - Test cases for validating framework accuracy

## Quick Start

### Analyze Code Changes

```bash
python3 scripts/collect_pr_diff.py \
    --base main \
    --head HEAD
```

### Generate Unit Tests

```bash
python3 scripts/orchestrate_mr_test.py \
    --base main \
    --head HEAD
```

### Validate Tests

```bash
bash scripts/validate.sh
```

## Usage Examples

### Example 1: Quick Analysis

```bash
cd /workspaces/SDLC_automation
python3 unit_test_automation/scripts/collect_pr_diff.py \
    --base main \
    --head HEAD
```

### Example 2: Generate and Validate

```bash
python3 unit_test_automation/scripts/orchestrate_mr_test.py \
    --base main \
    --head HEAD

bash unit_test_automation/scripts/validate.sh
```

### Example 3: Full Workflow

```bash
# Create feature branch
git checkout -b feature/new-feature

# Make changes
# ... edit files ...

# Commit changes
git commit -m "feat: add new feature"

# Run automation
python3 unit_test_automation/scripts/orchestrate_mr_test.py \
    --base main \
    --head HEAD
```

## Output Format

### PR Diff Analysis Output

```json
{
  "base_branch": "main",
  "head_branch": "HEAD",
  "changed_files": [
    {
      "file_path": "src/calculator.cpp",
      "changes": [
        {
          "function": "add",
          "type": "modified",
          "lines_changed": 5
        }
      ]
    }
  ]
}
```

## Testing

Run the test suite:

```bash
# Test collection phase
bash /workspaces/SDLC_automation/tests/automation/test_unit_test_collection.sh

# Or run from master test runner
bash /workspaces/SDLC_automation/run_all_tests.sh
```

## Integration

### With CI/CD

The module can be integrated into GitHub Actions:

```yaml
- name: Run Unit Test Automation
  run: |
    python3 unit_test_automation/scripts/orchestrate_mr_test.py \
      --base main \
      --head HEAD
```

### With Existing Tests

Works seamlessly with existing CMake + CTest infrastructure. Generated tests are automatically discovered and run by the build system.

## Requirements

- Python 3.8+
- Git
- CMake 3.15+
- C++ compiler (GCC or Clang)
- GoogleTest framework (included via CMake)

## Dependencies

- `collect_pr_diff.py` - Requires git repository
- `orchestrate_mr_test.py` - Requires gh CLI and LLM access via `gh models eval`
- `validate.sh` - Requires CMake and C++ build tools

## Performance

- Analysis: ~500ms per file
- LLM generation: 5-15s per function
- Build & validation: 10-30s depending on project size

## Troubleshooting

### Git diff not working

Ensure you're in a git repository:
```bash
git status
```

### LLM not responding

Check gh CLI is authenticated:
```bash
gh auth status
```

### Build failures

Check CMakeLists.txt is correct:
```bash
cd build && cmake .. && make
```

## See Also

- [Klockwork Automation](../klockwork_automation/README.md) - Security-focused code fixing
- [Complete Flow Guide](../COMPLETE_FLOW_AND_TESTING_GUIDE.md) - Detailed workflow documentation
- [Testing Guide](../QUICK_START_TESTING.md) - Testing approaches and examples
