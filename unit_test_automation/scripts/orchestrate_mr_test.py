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
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
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

def get_diff_json(base: str, head: str):
    """Run collect_pr_diff.py and return parsed JSON."""
    out = run([sys.executable, str(COLLECT_DIFF_SCRIPT), "--base", base, "--head", head])
    return json.loads(out)

def generate_test_for_source(source_file, suggested_test_file, header_code, impl_code):
    """Call gh models eval with prompt template and variables. Returns LLM JSON response as dict."""
    # Create a temporary prompt YAML by embedding the source/header/implementation
    template_text = Path(PROMPT_TEMPLATE).read_text()
    # Indent code blocks to fit inside the YAML block scalar in the template
    def indent_block(code: str, indent: str = "      ") -> str:
        if not code:
            return ""
        return "\n".join(indent + line for line in code.splitlines())

    prompt_filled = (
        template_text
        .replace("{{source_file}}", str(source_file))
        .replace("{{suggested_test_file}}", str(suggested_test_file))
        .replace("{{header_code}}", indent_block(header_code))
        .replace("{{implementation_code}}", indent_block(impl_code))
    )
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".prompt.yml") as f:
        f.write(prompt_filled)
        f.flush()
        prompt_path = f.name
    # Call run_prompt_eval.sh (which wraps gh models eval)
    out = run([str(EVAL_SCRIPT), prompt_path])
    # Try to parse the returned wrapper JSON from `gh models eval`.
    try:
        wrapper = json.loads(out)
        # `testResults` is an array; modelResponse is the inner JSON as a string.
        for entry in wrapper.get("testResults", []):
            mr = entry.get("modelResponse")
            if not mr:
                continue
            try:
                return json.loads(mr)
            except Exception:
                # If modelResponse isn't pure JSON, try to extract JSON substring.
                try:
                    start = mr.index("{")
                    end = mr.rindex("}") + 1
                    return json.loads(mr[start:end])
                except Exception:
                    continue
        # Fallback: try to find any JSON object in the raw output.
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

def verify_source_compiles():
    """Verify current source builds before generating tests."""
    build_dir = REPO_ROOT / "build"
    print("[STEP 2] Verifying source compiles before generating tests...")

    config = subprocess.run(
        [
            "cmake",
            "-S",
            str(REPO_ROOT),
            "-B",
            str(build_dir),
            "-G",
            "Ninja",
            "-DCMAKE_BUILD_TYPE=Debug",
            "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if config.returncode != 0:
        print("[ERROR] Source configuration failed. Fix source code before generating tests.")
        print(config.stderr)
        sys.exit(config.returncode)

    build = subprocess.run(
        [
            "cmake",
            "--build",
            str(build_dir),
            "--target",
            "project_lib",
            "--parallel",
            "--clean-first",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if build.returncode != 0:
        print("[ERROR] Source compilation failed. Fix source code before generating tests.")
        print(build.stdout)
        print(build.stderr)
        sys.exit(build.returncode)
    print("[INFO] Source compiles successfully.")


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
    parser.add_argument("--base", type=str, default="origin/main", help="Base git ref for diff")
    parser.add_argument("--head", type=str, default="HEAD", help="Head git ref for diff")
    args = parser.parse_args()

    print("[STEP 1] Collecting MR diff...")
    diff = get_diff_json(args.base, args.head)
    print(json.dumps(diff, indent=2))

    verify_source_compiles()

    print("[STEP 3] Generating tests for changed source files...")
    suggested_by_test = {}
    for t in diff.get("suggested_test_targets", []):
        if isinstance(t, dict):
            suggested_by_test.setdefault(t.get("suggested_test"), []).append(t.get("source"))

    for suggested_test, sources in suggested_by_test.items():
        source = sources[0]
        if len(sources) > 1:
            print(f"[WARN] Multiple sources {sources} map to the same test target {suggested_test}; using {source}")
        test_path = TESTS_DIR / Path(suggested_test).name
        if test_path.exists():
            print(f"[INFO] Existing test target {test_path} already exists; skipping generation")
            continue
        # Read code
        header_code = ""
        impl_code = ""
        src_path = REPO_ROOT / source
        if src_path.exists():
            impl_code = src_path.read_text()
        # Try to find header
        header_path = src_path.with_suffix(".hpp")
        if header_path.exists():
            header_code = header_path.read_text()
        # LLM call
        llm_resp = generate_test_for_source(source, suggested_test, header_code, impl_code)
        if not llm_resp or "test_code" not in llm_resp:
            print(f"[ERROR] No test_code generated for {source}")
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
