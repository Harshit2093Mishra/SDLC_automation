"""
Main orchestration pipeline.

Fixes the critical bug: test generation now runs for BOTH new and
modified source files. For modified files, existing tests are read,
passed to the LLM as context, and results are merged (not overwritten).
"""
from __future__ import annotations

import sys
from pathlib import Path

from unit_test_automation.config import REPO_ROOT, TESTS_DIR
from unit_test_automation.diff_collector import collect_diff, guess_test_path, DiffResult
from unit_test_automation.header_resolver import resolve_headers_for_source
from unit_test_automation.test_merger import merge_tests, remove_tests_for_source, remove_tests_by_key
from unit_test_automation.llm_client import generate_tests
from unit_test_automation.build_manager import verify_source_compiles, build_and_run_tests


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _read_source(source_path: str) -> tuple[str, str]:
    """
    Return (header_code, impl_code) for a source file.

    Header code is built by concatenating all resolvable ``#include "..."``
    headers found in the source file (via the header_resolver).
    """
    src = REPO_ROOT / source_path
    if not src.is_file():
        return "", ""

    impl_code = src.read_text(errors="replace")

    headers = resolve_headers_for_source(src)
    if headers:
        # Concatenate all resolved headers with separators
        header_parts = []
        for inc_path, content in headers.items():
            header_parts.append(f"// === {inc_path} ===\n{content}")
        header_code = "\n\n".join(header_parts)
    else:
        header_code = ""

    return header_code, impl_code


def _read_existing_tests(test_path: Path) -> str:
    """Return existing test file content, or empty string if none."""
    if test_path.is_file():
        return test_path.read_text(errors="replace")
    return ""


def _write_or_merge_tests(test_path: Path, new_code: str, existing_code: str) -> None:
    """Write new test code, merging into existing file when present."""
    TESTS_DIR.mkdir(parents=True, exist_ok=True)

    if existing_code:
        merged = merge_tests(existing_code, new_code)
        test_path.write_text(merged)
        print(f"[MERGE] Updated existing test file: {test_path}")
    else:
        test_path.write_text(new_code)
        print(f"[WRITE] Created new test file: {test_path}")


def _sanitize_test_code(new_code: str, existing_code: str) -> str:
    """
    Fix common LLM mistakes in generated test code BEFORE merging:

    1. INCLUDES: Replace any #include lines in new_code that don't match the
       existing test file with the includes from existing_code.
       This prevents the LLM inventing wrong paths like '../include/calculator.h'.

    2. SUITE NAME: If existing tests use 'TEST(Calculator, ...)' but the LLM
       generated 'TEST(CalculatorTest, ...)', rename to match.

    Only runs when existing_code is non-empty (we have a reference to copy from).
    """
    import re

    if not existing_code or not new_code:
        return new_code

    # ── 1: Include fixup ────────────────────────────────────────────────────
    INCLUDE_RE = re.compile(r'^\s*#\s*include\s+.+$', re.MULTILINE)

    existing_includes = INCLUDE_RE.findall(existing_code)
    new_includes = INCLUDE_RE.findall(new_code)

    if existing_includes and new_includes:
        # Categorize: gtest includes, project includes, stdlib includes
        def _is_gtest(inc: str) -> bool:
            return "gtest" in inc or "gmock" in inc

        def _is_project(inc: str) -> bool:
            return '"' in inc and not _is_gtest(inc)

        def _is_stdlib(inc: str) -> bool:
            return "<" in inc and not _is_gtest(inc)

        existing_project = [i for i in existing_includes if _is_project(i)]
        new_project = [i for i in new_includes if _is_project(i)]

        if existing_project and new_project:
            # Check if the LLM used different project include paths
            existing_paths = {re.search(r'["\'](.+?)["\']', i).group(1)
                              for i in existing_project
                              if re.search(r'["\'](.+?)["\']', i)}
            new_paths = {re.search(r'["\'](.+?)["\']', i).group(1)
                         for i in new_project
                         if re.search(r'["\'](.+?)["\']', i)}

            if new_paths != existing_paths:
                print(f"  [SANITIZE] Fixing includes: LLM used {new_paths}, "
                      f"replacing with {existing_paths}")
                # Remove all project includes from new_code and replace with existing ones
                for bad_inc in new_project:
                    new_code = new_code.replace(bad_inc, "", 1)
                # Insert correct project includes after first gtest include
                gtest_inc = next((i for i in new_includes if _is_gtest(i)), None)
                if gtest_inc:
                    replacement = gtest_inc + "\n" + "\n".join(existing_project)
                    new_code = new_code.replace(gtest_inc, replacement, 1)

    # ── 2: Suite name fixup ─────────────────────────────────────────────────
    TEST_MACRO_RE = re.compile(
        r'((?:TEST|TEST_F|TEST_P)\s*\(\s*)(\w+)(\s*,)',
    )

    existing_suites = {m.group(2) for m in TEST_MACRO_RE.finditer(existing_code)}
    new_suites = {m.group(2) for m in TEST_MACRO_RE.finditer(new_code)}

    if len(existing_suites) == 1 and new_suites - existing_suites:
        correct_suite = next(iter(existing_suites))
        wrong_suites = new_suites - existing_suites
        for wrong in wrong_suites:
            if wrong != correct_suite:
                print(f"  [SANITIZE] Fixing suite name: '{wrong}' -> '{correct_suite}'")
                new_code = re.sub(
                    rf'((?:TEST|TEST_F|TEST_P)\s*\(\s*){re.escape(wrong)}(\s*,)',
                    rf'\g<1>{correct_suite}\2',
                    new_code,
                )

    return new_code



# ---------------------------------------------------------------------------
# Pipeline steps
# ---------------------------------------------------------------------------
def step_collect_diff(base: str, head: str) -> DiffResult:
    print("\n[STEP 1] Collecting MR diff...")
    import json
    diff = collect_diff(base, head, cwd=str(REPO_ROOT))
    print(f"  Base: {diff.base}  ->  Head: {diff.head}")
    print(f"  Added sources   : {diff.added_sources}")
    print(f"  Modified sources: {diff.modified_sources}")
    print(f"  Deleted sources : {diff.deleted_sources}")
    return diff


def step_verify_source(build_dir: Path | None = None) -> None:
    print("\n[STEP 2] Verifying source compiles...")
    from unit_test_automation.build_manager import configure, BUILD_DIR as _BD
    bd = build_dir or _BD
    # Quick probe: if cmake isn't installed, warn and continue
    probe = configure(bd)
    if not probe.success and "cmake not found" in probe.output:
        print("[WARN] cmake not found locally. Skipping source-compile verification.")
        print("[WARN] Make sure the source compiles in your build environment before running tests.")
        return
    if not verify_source_compiles(build_dir):
        print("[FATAL] Source does not compile. Fix source before generating tests.")
        sys.exit(1)


def step_cleanup_deleted(diff: DiffResult) -> None:
    if not diff.deleted_sources:
        return
    print("\n[STEP 3] Cleaning up tests for deleted source files...")
    for deleted in diff.deleted_sources:
        test_path = TESTS_DIR / Path(guess_test_path(deleted)).name
        if remove_tests_for_source(test_path, deleted):
            print(f"  [INFO] Removed tests for deleted source: {deleted}")
        else:
            print(f"  [INFO] No tests found to remove for: {deleted}")


def step_generate_tests(diff: DiffResult) -> int:
    """
    Generate or update tests for all added and modified source files.

    KEY FIX: we no longer skip files just because a test file already
    exists.  Instead we:
      1. Read the existing test file (if any) as context.
      2. Send the diff content (not just the full file) to the LLM.
      3. Merge the LLM output into the existing test file.
    """
    print("\n[STEP 4] Generating/updating tests for changed source files...")

    sources_to_process = list(dict.fromkeys(diff.added_sources + diff.modified_sources))
    if not sources_to_process:
        print("  [INFO] No changed source files to process.")
        return 0

    generated = 0
    llm_failures: list[str] = []   # sources where LLM returned nothing
    for source in sources_to_process:
        src_path = REPO_ROOT / source
        if not src_path.is_file():
            print(f"  [SKIP] {source} no longer exists.")
            continue

        suggested_test = guess_test_path(source)
        test_path = TESTS_DIR / Path(suggested_test).name

        # Determine mode
        existing_code = _read_existing_tests(test_path)
        mode = "update" if existing_code else "create"
        print(f"\n  [{mode.upper()}] {source}  ->  {test_path}")

        # Build context for the LLM
        header_code, impl_code = _read_source(source)
        # Use combined diff: source diff + any related header diffs
        diff_content = diff.get_combined_diff_for_source(source)

        if not impl_code:
            print(f"  [WARN] Could not read {source}; skipping.")
            continue

        # Call LLM
        llm_resp = generate_tests(
            source_file=source,
            suggested_test_file=suggested_test,
            header_code=header_code,
            impl_code=impl_code,
            diff_content=diff_content,
            existing_test_code=existing_code,
        )

        if not llm_resp:
            print(f"  [ERROR] LLM returned no response for {source}.")
            print(f"  [HINT]  Check gh models auth: run 'gh auth status' and 'gh models list'")
            llm_failures.append(source)
            continue

        if "test_code" not in llm_resp:
            print(f"  [ERROR] LLM response missing 'test_code' for {source}")
            blockers = llm_resp.get("blockers", []) or []
            if blockers:
                print("  [LLM blockers]:")
                for b in blockers:
                    print(f"    - {b}")
            llm_failures.append(source)
            continue

        test_code = llm_resp.get("test_code", "")
        summary = llm_resp.get("summary", "")
        cases = llm_resp.get("test_cases", [])
        tests_to_remove = llm_resp.get("tests_to_remove", [])
        print(f"  [LLM] {summary}")
        if cases:
            print(f"  [LLM] {len(cases)} new test case(s): {[c.get('name') for c in cases]}")
        if tests_to_remove:
            print(f"  [LLM] Stale tests to remove: {tests_to_remove}")

        # Step A: remove stale tests for renamed/deleted functions
        if tests_to_remove and test_path.is_file():
            remove_tests_by_key(test_path, tests_to_remove)
            # Re-read after removal so merge sees the cleaned file
            existing_code = _read_existing_tests(test_path)

        # Step B: merge new tests in (skip if LLM had nothing new to add)
        if test_code.strip():
            # Sanitize before merging: fix wrong includes, suite names, etc.
            test_code = _sanitize_test_code(test_code, existing_code)
            _write_or_merge_tests(test_path, test_code, existing_code)
        elif tests_to_remove:
            print(f"  [INFO] Only removals; test file cleaned up.")
        generated += 1

    return generated, llm_failures


def step_build_and_test(build_dir: Path | None = None) -> None:
    print("\n[STEP 5] Building and running tests...")
    result = build_and_run_tests(build_dir)
    if result.success:
        print("\n[REPORT] PASSED: All tests passed.\n")
        print(result.output)
    else:
        print(f"\n[REPORT] FAILED: Stage '{result.stage}' failed.\n")
        print(result.output)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def run(base: str, head: str, build_dir: Path | None = None, skip_build: bool = False) -> None:
    """Full pipeline: diff -> verify -> cleanup -> generate -> build+test."""
    diff = step_collect_diff(base, head)
    step_verify_source(build_dir)
    step_cleanup_deleted(diff)
    generated, llm_failures = step_generate_tests(diff)
    print(f"\n[INFO] Generated/updated tests for {generated} file(s).")

    if llm_failures:
        print(f"\n[ABORT] LLM failed to generate tests for {len(llm_failures)} file(s):")
        for f in llm_failures:
            print(f"  - {f}")
        print("[ABORT] Building with stale/incorrect tests would be misleading.")
        print("[ABORT] Fix LLM connectivity (check 'gh auth status') and re-run.")
        sys.exit(1)

    if not skip_build:
        step_build_and_test(build_dir)
    else:
        print("[INFO] --skip-build requested; skipping build & test step.")
