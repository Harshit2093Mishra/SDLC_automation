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
BUILD_FIX_PROMPT = REPO_ROOT / "unit_test_automation/prompts/build_fix.prompt.yml"

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


def fill_prompt_template(template_path: Path, substitutions: dict) -> Path:
    template_text = template_path.read_text()
    for key, value in substitutions.items():
        template_text = template_text.replace(f"{{{{{key}}}}}", value)

    with tempfile.NamedTemporaryFile("w", delete=False, suffix=template_path.suffix) as f:
        f.write(template_text)
        f.flush()
        return Path(f.name)


def guess_test_path(source_path: str) -> str:
    source = Path(source_path)
    return str(Path("tests") / f"{source.stem}_test.cpp")


def get_candidate_keywords(source_path: str) -> list[str]:
    source = Path(source_path)
    stem = source.stem
    candidates = {stem}
    if stem:
        candidates.add(stem.capitalize())
    return sorted(candidates)


def remove_tests_for_removed_source(test_path: Path, source_path: str) -> bool:
    if not test_path.exists():
        return False

    keywords = get_candidate_keywords(source_path)
    text = test_path.read_text()
    lines = text.splitlines(keepends=True)
    filtered_lines = []
    removed_any = False
    i = 0
    while i < len(lines):
        if lines[i].lstrip().startswith("TEST("):
            start = i
            brace_count = 0
            while i < len(lines):
                brace_count += lines[i].count("{") - lines[i].count("}")
                i += 1
                if brace_count <= 0:
                    break
            block = "".join(lines[start:i])
            if any(keyword in block for keyword in keywords):
                removed_any = True
                continue
            filtered_lines.append(block)
            continue

        filtered_lines.append(lines[i])
        i += 1

    if not removed_any:
        return False

    new_text = "".join(filtered_lines).rstrip() + "\n"
    if not new_text.strip():
        test_path.unlink()
        print(f"[INFO] Deleted empty test file {test_path} after removing removed-source tests.")
        return True

    test_path.write_text(new_text)
    return True


def generate_test_for_source(source_file, suggested_test_file, header_code, impl_code):
    """Call gh models eval with prompt template and variables. Returns LLM JSON response as dict."""
    def indent_block(code: str, indent: str = "      ") -> str:
        if not code:
            return ""
        return "\n".join(indent + line for line in code.splitlines())

    prompt_path = fill_prompt_template(
        Path(PROMPT_TEMPLATE),
        {
            "source_file": str(source_file),
            "suggested_test_file": str(suggested_test_file),
            "header_code": indent_block(header_code),
            "implementation_code": indent_block(impl_code),
        },
    )
    try:
        out = run([str(EVAL_SCRIPT), str(prompt_path)])
    finally:
        prompt_path.unlink(missing_ok=True)

    try:
        wrapper = json.loads(out)
        for entry in wrapper.get("testResults", []):
            mr = entry.get("modelResponse")
            if not mr:
                continue
            try:
                return json.loads(mr)
            except Exception:
                try:
                    start = mr.index("{")
                    end = mr.rindex("}") + 1
                    return json.loads(mr[start:end])
                except Exception:
                    continue
        start = out.index("{")
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

def configure_build(build_dir: Path):
    return subprocess.run(
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


def build_target(build_dir: Path, target: str):
    return subprocess.run(
        [
            "cmake",
            "--build",
            str(build_dir),
            "--target",
            target,
            "--parallel",
            "--clean-first",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def attempt_ai_build_fix(build_dir: Path, build_output: str) -> bool:
    print("[ERROR] Source compilation failed. Will attempt up to 5 AI-assisted fixes.")
    for attempt in range(1, 6):
        print(f"[INFO] AI fix attempt {attempt}/5: sending build output to model")
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as tf:
            json.dump({"build_output": build_output}, tf)
            tf.flush()
            input_path = tf.name

        result = subprocess.run(
            [str(EVAL_SCRIPT), str(BUILD_FIX_PROMPT), input_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        os.unlink(input_path)

        if result.returncode != 0:
            print("[ERROR] AI fixer failed to run. Stderr:")
            print(result.stderr)
            break

        try:
            wrapper = json.loads(result.stdout)
        except Exception:
            print("[ERROR] Failed to parse AI response as JSON:")
            print(result.stdout)
            break

        if wrapper.get("testResults"):
            parsed = None
            for entry in wrapper.get("testResults", []):
                mr = entry.get("modelResponse") or entry.get("output")
                if not mr:
                    continue
                try:
                    parsed = json.loads(mr)
                    break
                except Exception:
                    try:
                        start = mr.index("{")
                        end = mr.rindex("}") + 1
                        parsed = json.loads(mr[start:end])
                        break
                    except Exception:
                        continue
            if parsed is None:
                print("[ERROR] AI response did not contain valid JSON in modelResponse:")
                print(result.stdout)
                break
            wrapper = parsed

        edits = wrapper.get("edits", [])
        blockers = wrapper.get("blockers", [])
        summary = wrapper.get("summary", "")
        print(f"[AI] summary: {summary}")
        if blockers:
            print("[AI] blockers:")
            for b in blockers:
                print(" - ", b)
            break

        if not edits:
            print("[INFO] AI returned no edits; stopping attempts.")
            break

        applied_any = False
        for e in edits:
            path = e.get("path")
            content = e.get("content")
            if not path or content is None:
                continue
            target = REPO_ROOT / path
            print(f"[PATCH] Applying edit to {target}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "w") as f:
                f.write(content)
            applied_any = True

        if not applied_any:
            print("[INFO] No valid edits applied; stopping attempts.")
            break

        config = configure_build(build_dir)
        if config.returncode != 0:
            build_output = (config.stdout or "") + "\n" + (config.stderr or "")
            print(f"[WARN] Configuration still failing after attempt {attempt}.")
            continue

        build = build_target(build_dir, "project_lib")
        build_output = (build.stdout or "") + "\n" + (build.stderr or "")
        if build.returncode == 0:
            print("[INFO] Build fixed by AI edits.")
            return True

        print(f"[WARN] Build still failing after attempt {attempt}.")

    print("[ERROR] Build could not be fixed automatically after 5 attempts. Please inspect and retry.")
    print(build_output)
    return False


def verify_source_compiles():
    """Verify current source builds before generating tests."""
    build_dir = REPO_ROOT / "build"
    print("[STEP 2] Verifying source compiles before generating tests...")

    config = configure_build(build_dir)
    if config.returncode != 0:
        print("[ERROR] Source configuration failed. Fix source code before generating tests.")
        print(config.stderr)
        if not attempt_ai_build_fix(build_dir, (config.stdout or "") + "\n" + (config.stderr or "")):
            sys.exit(1)
        return

    build = build_target(build_dir, "project_lib")
    if build.returncode != 0:
        print("[ERROR] Source compilation failed. Fix source code before generating tests.")
        if not attempt_ai_build_fix(build_dir, (build.stdout or "") + "\n" + (build.stderr or "")):
            sys.exit(1)
        return

    print("[INFO] Source compiles successfully.")


def build_and_test():
    """Build the test target and run tests, separating build failure from test failures."""
    build_dir = REPO_ROOT / "build"
    config = configure_build(build_dir)
    if config.returncode != 0:
        return False, "build", (config.stdout or "") + "\n" + (config.stderr or "")

    build = build_target(build_dir, "calculator_tests")
    if build.returncode != 0:
        build_output = (build.stdout or "") + "\n" + (build.stderr or "")
        print("[ERROR] Test target build failed; attempting AI-assisted build fix.")
        if attempt_ai_build_fix(build_dir, build_output):
            build = build_target(build_dir, "calculator_tests")
            if build.returncode != 0:
                return False, "build", (build.stdout or "") + "\n" + (build.stderr or "")
        else:
            return False, "build", build_output

    test = subprocess.run(
        ["ctest", "--test-dir", str(build_dir), "--output-on-failure"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if test.returncode != 0:
        return False, "test", (test.stdout or "") + "\n" + (test.stderr or "")

    return True, "success", (test.stdout or "")

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

    removed_sources = diff.get("removed_source_files", [])
    if removed_sources:
        print("[STEP 2.5] Cleaning up tests for deleted source files...")
        for removed_source in removed_sources:
            test_path = Path(guess_test_path(removed_source))
            if remove_tests_for_removed_source(test_path, removed_source):
                print(f"[INFO] Removed tests for deleted source {removed_source}")

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
        header_code = ""
        impl_code = ""
        src_path = REPO_ROOT / source
        if not src_path.exists():
            print(f"[INFO] Source {source} no longer exists; skipping test generation.")
            continue
        impl_code = src_path.read_text()
        header_path = src_path.with_suffix(".hpp")
        if header_path.exists():
            header_code = header_path.read_text()
        llm_resp = generate_test_for_source(source, suggested_test, header_code, impl_code)
        if not llm_resp or "test_code" not in llm_resp:
            print(f"[ERROR] No test_code generated for {source}")
            continue
        test_path = write_test_file(llm_resp["test_file_path"], llm_resp["test_code"])
        print(f"[INFO] Test written: {test_path}")

    print("[STEP 4] Building and running tests...")
    success, stage, output = build_and_test()
    if success:
        print("[REPORT] All tests passed successfully.\n" + output)
        return

    if stage == "build":
        print("[REPORT] Build failed. Please fix the build first.")
        print(output)
    else:
        print("[REPORT] Tests failed. See output below.")
        print(output)
    sys.exit(1)


if __name__ == "__main__":
    main()
