# Klockwork Fixer Evaluation Cases

This directory contains evaluation test cases for the Klockwork fixer prompt.

## Overview

The `klockwork_fixer_cases.jsonl` file contains 20 comprehensive evaluation cases that test the Klockwork fixer's ability to:

1. **Identify violations** across all 20 Klockwork security check categories
2. **Generate fixes** that properly address security issues
3. **Maintain functionality** while adding security hardening
4. **Handle complex scenarios** with multiple violations in a single function

## Test Case Structure

Each evaluation case includes:

- `test_id`: Unique identifier (KLOCK_EVAL_001 through KLOCK_EVAL_020)
- `category`: Klockwork violation category being tested
- `title`: Human-readable test case name
- `input_code`: Vulnerable C/C++ code to analyze
- `expected_violations`: List of violation types that should be detected
- `expected_fix_includes`: Keywords/phrases the fix should contain
- `severity`: Severity level (CRITICAL, HIGH, MEDIUM, LOW)

## Categories Covered

| Test ID | Category | Severity |
|---------|----------|----------|
| KLOCK_EVAL_001 | NPD.CHECK.CALL | CRITICAL |
| KLOCK_EVAL_002 | RH.LEAK | HIGH |
| KLOCK_EVAL_003 | SV.STRBO.BOUND_COPY | CRITICAL |
| KLOCK_EVAL_004 | SV.STRBO.BOUND_CAT | CRITICAL |
| KLOCK_EVAL_005 | SV.TAINTED.CALL.LOOP_BOUND | HIGH |
| KLOCK_EVAL_006 | SV.INTOVF.ASSIGN | HIGH |
| KLOCK_EVAL_007 | SV.USAGERULES.FREEING_MEMORY | CRITICAL |
| KLOCK_EVAL_008 | UNINIT.STACK.MUST | HIGH |
| KLOCK_EVAL_009 | SV.MISRA.COMPL_RETURN | MEDIUM |
| KLOCK_EVAL_010 | SV.FMT_STR.GENERIC | CRITICAL |
| KLOCK_EVAL_011 | SV.TAINTED.ALLOC | HIGH |
| KLOCK_EVAL_012 | SV.BANNED.FUNCTIONS | CRITICAL |
| KLOCK_EVAL_013 | SV.BANNED.FUNCTIONS | CRITICAL |
| KLOCK_EVAL_014 | SV.PASSWD.PLAINTEXT | CRITICAL |
| KLOCK_EVAL_015 | SV.UNSIGNED_COMPARE.ALWAYS_TRUE | MEDIUM |
| KLOCK_EVAL_016 | SV.MEMSET.WRONGSIZE | HIGH |
| KLOCK_EVAL_017 | SV.ARRAY.BOUND | HIGH |
| KLOCK_EVAL_018 | SV.WRAP.INTEGEROVERFLOW | HIGH |
| KLOCK_EVAL_019 | SV.INSECURE.RAND | CRITICAL |
| KLOCK_EVAL_020 | Complex Multi-violation | CRITICAL |

## Usage

Run evaluation cases with:

```bash
./run_klockwork_eval.sh [--case KLOCK_EVAL_001] [--verbose]
```

## Expected Behavior

The Klockwork fixer should:

1. Parse the input code correctly
2. Identify all expected violations
3. Generate secure, working fixes
4. Provide explanations and severity levels
5. Suggest test cases to validate fixes
6. Maintain backward compatibility
