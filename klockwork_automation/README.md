# Klockwork Automation Framework

Automated security analysis and fixing framework for Klockwork static analysis violations in C/C++ code. Similar to the unit test automation framework, this provides end-to-end automation for identifying and fixing security issues.

## Overview

Klockwork Automation analyzes C/C++ source code for security vulnerabilities and compliance issues, generates fixes, and creates pull requests with the necessary corrections. It focuses on 20 critical security check categories including null pointer dereferences, buffer overflows, resource leaks, and more.

## Architecture

```
klockwork_automation/
├── include/
│   └── klockwork_rules.hpp          # C++ header for rule definitions
├── prompts/
│   ├── klockwork_rules.json         # All 20 security rules in JSON format
│   ├── klockwork_fixer.prompt.yml   # Prompt template for LLM-based fixing
│   └── evals/
│       ├── README.md                # Evaluation guide
│       ├── klockwork_fixer_cases.jsonl  # 20 test cases for evaluation
└── scripts/
    ├── collect_klockwork_issues.py  # Collects violations from source code
    ├── orchestrate_klockwork_fix.py # Main orchestration script
    ├── validate_klockwork_fix.sh    # Validates fixes
    └── run_klockwork_eval.sh        # Runs evaluation cases
```

## Supported Security Checks

The framework addresses 20 critical security categories:

| ID | Title | Severity | Description |
|----|-------|----------|-------------|
| NPD.CHECK.CALL | Null Pointer Dereference | CRITICAL | Check pointer returns before use |
| RH.LEAK | Resource Leak | HIGH | Ensure resources freed on all paths |
| SV.STRBO.BOUND_COPY | Buffer Overflow (strcpy) | CRITICAL | Use strncpy instead of strcpy |
| SV.STRBO.BOUND_CAT | Buffer Overflow (strcat) | CRITICAL | Use strncat instead of strcat |
| SV.TAINTED.CALL.LOOP_BOUND | Tainted Loop Bound | HIGH | Validate loop bounds |
| SV.INTOVF.ASSIGN | Integer Overflow | HIGH | Check for overflow in arithmetic |
| SV.USAGERULES.FREEING_MEMORY | Double Free / UAF | CRITICAL | Set pointer to NULL after free |
| UNINIT.STACK.MUST | Uninitialized Variable | HIGH | Initialize all local variables |
| SV.MISRA.COMPL_RETURN | Unchecked Return Value | MEDIUM | Check function return values |
| SV.FMT_STR.GENERIC | Format String Vulnerability | CRITICAL | Use format string literals |
| SV.TAINTED.ALLOC | Tainted Allocation Size | HIGH | Validate allocation sizes |
| SV.BANNED.FUNCTIONS | Banned Functions | CRITICAL | Avoid gets, sprintf, strcpy, etc. |
| SV.PASSWD.PLAINTEXT | Plaintext Password | CRITICAL | Never hardcode passwords |
| SV.RACE.CONDITION | TOCTOU Race Condition | HIGH | Use atomic file operations |
| SV.UNSIGNED_COMPARE.ALWAYS_TRUE | Always-True Comparison | MEDIUM | Fix unsigned comparisons |
| SV.MEMSET.WRONGSIZE | Wrong memset Size | HIGH | Pass buffer size, not pointer size |
| SV.ARRAY.BOUND | Array Bounds | HIGH | Validate array indices |
| SV.SIGNAL.UNSAFE | Unsafe Signal Handler | HIGH | Use only async-signal-safe functions |
| SV.WRAP.INTEGEROVERFLOW | Integer Wraparound | HIGH | Validate size arithmetic |
| SV.INSECURE.RAND | Weak RNG | CRITICAL | Use CSPRNG instead of rand() |

## Quick Start

### 1. Collect Klockwork Issues

Analyze your C/C++ codebase for security violations:

```bash
python3 scripts/collect_klockwork_issues.py \
    --source-dir src \
    --output klockwork_issues.json \
    --summary-only
```

This generates a summary of all detected issues grouped by severity and rule type.

### 2. Create Fixes with Orchestration

Automatically generate fixes and create a PR:

```bash
python3 scripts/orchestrate_klockwork_fix.py \
    --repo-dir . \
    --source-dir src \
    --auto-commit \
    --create-pr
```

This will:
- Detect all violations
- Generate fix recommendations
- Create a new branch (`klockwork-fixes-TIMESTAMP`)
- Commit changes
- Create a pull request

### 3. Validate Fixes

Validate that fixes are proper and don't break the code:

```bash
bash scripts/validate_klockwork_fix.sh
```

### 4. Run Evaluation Cases

Test the Klockwork fixer prompt against 20 evaluation cases:

```bash
# Run all evaluation cases
bash scripts/run_klockwork_eval.sh --all

# Run specific case
bash scripts/run_klockwork_eval.sh --case KLOCK_EVAL_001

# List all available cases
bash scripts/run_klockwork_eval.sh --list
```

## Usage Examples

### Example 1: Analyze Current Repository

```bash
cd /path/to/repo
python3 klockwork_automation/scripts/collect_klockwork_issues.py
```

**Output:**
```
=== Klockwork Issues Summary ===
Total issues found: 15

By Severity:
  CRITICAL: 8
  HIGH: 5
  MEDIUM: 2

By Rule:
  SV.STRBO.BOUND_COPY: 3
  SV.BANNED.FUNCTIONS: 2
  NPD.CHECK.CALL: 2
  ...
```

### Example 2: Generate PR with Fixes

```bash
# Run full orchestration with PR creation
python3 klockwork_automation/scripts/orchestrate_klockwork_fix.py \
    --create-pr \
    --auto-commit
```

### Example 3: Custom Analysis on Specific Directory

```bash
# Analyze only the driver/ directory
python3 klockwork_automation/scripts/collect_klockwork_issues.py \
    --source-dir driver
```

### Example 4: Use in CI/CD Pipeline

```bash
#!/bin/bash
# .github/workflows/klockwork-check.yml

- name: Run Klockwork Analysis
  run: |
    python3 klockwork_automation/scripts/collect_klockwork_issues.py \
      --source-dir src \
      --output klockwork_issues.json
    
    # Fail if critical issues found
    CRITICAL=$(jq '.by_severity.CRITICAL' klockwork_issues.json)
    if [[ $CRITICAL -gt 0 ]]; then
      echo "Critical issues found: $CRITICAL"
      exit 1
    fi
```

## File Descriptions

### Core Files

| File | Purpose |
|------|---------|
| `prompts/klockwork_rules.json` | Machine-readable rules for all 20 security checks |
| `prompts/klockwork_fixer.prompt.yml` | LLM prompt template for fixing violations |
| `include/klockwork_rules.hpp` | C++ enum and class definitions for integration |

### Scripts

| Script | Purpose |
|--------|---------|
| `collect_klockwork_issues.py` | Scans code for violations, generates JSON report |
| `orchestrate_klockwork_fix.py` | Main orchestration: collects issues, creates fixes, opens PRs |
| `validate_klockwork_fix.sh` | Validates fixes for correctness and integrity |
| `run_klockwork_eval.sh` | Evaluates the prompt against test cases |

### Evaluation

| File | Purpose |
|------|---------|
| `prompts/evals/klockwork_fixer_cases.jsonl` | 20 test cases (one per security category) |
| `prompts/evals/README.md` | Guide to evaluation cases |

## Output Format

### Issues Report (JSON)

```json
{
  "total_issues": 15,
  "by_severity": {
    "CRITICAL": 8,
    "HIGH": 5,
    "MEDIUM": 2,
    "LOW": 0
  },
  "by_rule": {
    "SV.STRBO.BOUND_COPY": 3,
    "SV.BANNED.FUNCTIONS": 2,
    "NPD.CHECK.CALL": 2
  },
  "issues": [
    {
      "rule_id": "SV.STRBO.BOUND_COPY",
      "file_path": "src/handler.c",
      "line_number": 42,
      "code_snippet": "strcpy(buf, user_input);",
      "description": "Buffer Overflow via String Copy",
      "severity": "CRITICAL"
    }
  ]
}
```

### Fixes Report (JSON)

```json
{
  "timestamp": "20260521_143022",
  "total_issues": 15,
  "by_severity": { ... },
  "fixes": [
    {
      "issue": { ... },
      "fix_type": "replace_strcpy_with_strncpy",
      "priority": "CRITICAL"
    }
  ],
  "pr_description": "# Klockwork Security Fixes\n\n..."
}
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Klockwork Security Check

on: [pull_request]

jobs:
  klockwork:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Check Klockwork Violations
        run: |
          python3 klockwork_automation/scripts/collect_klockwork_issues.py \
            --source-dir src \
            --output klockwork_issues.json
          
          python3 << 'EOF'
          import json
          with open('klockwork_issues.json') as f:
              issues = json.load(f)
              critical = issues['by_severity'].get('CRITICAL', 0)
              if critical > 0:
                  print(f"::error::Found {critical} CRITICAL issues")
                  exit(1)
          EOF
```

## Extension Points

The framework can be extended with:

1. **Additional Rules**: Add new patterns to `KLOCKWORK_PATTERNS` in `collect_klockwork_issues.py`
2. **Custom Fixes**: Extend `KlockworkFixOrchestrator` with custom fix strategies
3. **Integration with Klockwork Server**: Connect to actual Klockwork analysis server output
4. **Custom Validators**: Add domain-specific validation in `validate_klockwork_fix.sh`

## Related Documentation

- [Evaluation Cases](prompts/evals/README.md) - Details on 20 test cases
- [Klockwork Rules](prompts/klockwork_rules.json) - Complete rule definitions
- [C++ Integration](include/klockwork_rules.hpp) - C++ API for integration

## Contributing

To add support for new security checks:

1. Add rule to `KLOCKWORK_PATTERNS` in `collect_klockwork_issues.py`
2. Add to `klockwork_rules.json`
3. Add test case to `klockwork_fixer_cases.jsonl`
4. Update evaluation documentation

## See Also

- [Unit Test Automation](../unit_test_automation/) - Sister framework for automated unit testing
- [Main README](../README.md) - SDLC Automation overview
