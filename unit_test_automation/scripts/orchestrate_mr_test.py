#!/usr/bin/env python3
"""
Orchestration script for automated unit test generation and reporting for C++ Merge Requests.

Steps:
1. Retrieve and parse MR diff (using collect_pr_diff.py or API)
2. For each changed source file, generate unit test prompt and call LLM (gh models eval)
3. Parse LLM response and write test files
4. Trigger build and run tests
5. Aggregate and output test results report

Usage:
  python3 orchestrate_mr_test.py --mr-link <MR_LINK>

For MVP, assumes local git checkout of MR branch and uses collect_pr_diff.py.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# --- Config ---
REPO_ROOT = Path(__file__).resolve().parent.parent
COLLECT_DIFF_SCRIPT = REPO_ROOT / "unit_test_automation/scripts/collect_pr_diff.py"
PROMPT_TEMPLATE = REPO_ROOT / "unit_test_automation/prompts/unit_test_generator.prompt.yml"
EVAL_SCRIPT = REPO_ROOT / "unit_test_automation/scripts/run_prompt_eval.sh"
TESTS_DIR = REPO_ROOT / "tests"
BUILD_SCRIPT = REPO_ROOT / "unit_test_automation/scripts/validate.sh"

# --- Helpers ---
def run(cmd, **kwargs):
    print(f"[RUN] {' '.join(map(str, cmd))}")
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, **kwargs)
    if result.returncode != 0:
        print(f"[ERROR] Command failed: {' '.join(map(str, cmd))}")
        print(result.stderr)
        sys.exit(result.returncode)
    return result.stdout

def get_diff_json():
    """Run collect_pr_diff.py and return parsed JSON."""
    out = run([sys.executable, str(COLLECT_DIFF_SCRIPT)])
    return json.loads(out)

def generate_test_for_source(source_file, suggested_test_file, header_code, impl_code):
    """Call gh models eval with prompt template and variables. Returns LLM JSON response as dict."""
    # Prepare input JSON for prompt
    input_vars = {
        "source_file": str(source_file),
        "suggested_test_file": str(suggested_test_file),
        "header_code": header_code,
        "implementation_code": impl_code,
    }
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as f:
        json.dump(input_vars, f)
        f.flush()
        input_path = f.name
    # Call run_prompt_eval.sh (which wraps gh models eval)
    out = run([str(EVAL_SCRIPT), input_path])
    # Find JSON in output
    try:
        start = out.index("{" )
        end = out.rindex("}") + 1
        llm_json = out[start:end]
        return json.loads(llm_json)
    except Exception as e:
        print(f"[ERROR] Failed to parse LLM JSON: {e}\nOutput was:\n{out}")
        return None

def write_test_file(test_file_path, test_code):
    test_path = TESTS_DIR / Path(test_file_path).name
    print(f"[WRITE] {test_path}")
    with open(test_path, "w") as f:
        f.write(test_code)
    return test_path

def build_and_test():
    """Run build and tests via validate.sh. Returns (success, output)."""
    try:
        out = run([str(BUILD_SCRIPT)])
        return True, out
    except SystemExit:
        return False, "Build or tests failed. See above."

def main():
    parser = argparse.ArgumentParser(description="Automated MR unit test generation and reporting.")
    parser.add_argument("--mr-link", type=str, help="Merge Request/PR link (not used in MVP)")
    args = parser.parse_args()

    print("[STEP 1] Collecting MR diff...")
    diff = get_diff_json()
    print(json.dumps(diff, indent=2))

    print("[STEP 2] Generating tests for changed source files...")
    for src in diff.get("source_files", []):
        suggested_test = diff["suggested_test_targets"].get(src)
        if not suggested_test:
            print(f"[WARN] No suggested test file for {src}")
            continue
        # Read code
        header_code = ""
        impl_code = ""
        src_path = REPO_ROOT / src
        if src_path.exists():
            impl_code = src_path.read_text()
        # Try to find header
        header_path = src_path.with_suffix(".hpp")
        if header_path.exists():
            header_code = header_path.read_text()
        # LLM call
        llm_resp = generate_test_for_source(src, suggested_test, header_code, impl_code)
        if not llm_resp or "test_code" not in llm_resp:
            print(f"[ERROR] No test_code generated for {src}")
            continue
        test_path = write_test_file(llm_resp["test_file_path"], llm_resp["test_code"])
        print(f"[INFO] Test written: {test_path}")

    print("[STEP 3] Building and running tests...")
    success, output = build_and_test()
    print("[REPORT] Test Results:\n" + output)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
