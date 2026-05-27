"""
CMake configure / build / test helpers and AI-assisted build-fix loop.

Key improvements:
* Pre-check for "member not found" errors: deterministically removes stale
  test blocks before wasting AI retries on the wrong problem.
* Functions return result objects instead of calling sys.exit().
* attempt_ai_fix properly reconfigures after every patch.
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from unit_test_automation import config as _config
from unit_test_automation.config import REPO_ROOT, BUILD_DIR
from unit_test_automation.llm_client import generate_build_fix

MAX_FIX_ATTEMPTS = 5

# Compiler error patterns
_MEMBER_NOT_FOUND_RE = re.compile(
    r"'[^']+' has no member named '(\w+)'",
)
# Match just the filename ending in _test.cpp (ignoring directory prefix)
_TEST_FILE_RE = re.compile(
    r"(\w+_test\.cpp)",
)


@dataclass
class BuildResult:
    success: bool
    stage: str = ""        # "configure", "build", "test", "success"
    output: str = ""


# ---------------------------------------------------------------------------
# Deterministic pre-fix: remove stale tests for deleted members
# ---------------------------------------------------------------------------
def _remove_stale_member_tests(build_output: str) -> bool:
    """
    Parse compiler "has no member named X" errors and remove any TEST blocks
    that call X. This handles the case where a method was deleted and the
    primary LLM failed to add it to tests_to_remove.

    Returns True if any blocks were removed (caller should retry build).
    """
    from unit_test_automation.test_merger import extract_test_blocks, remove_tests_by_key

    # Find all "has no member named 'X'" errors
    missing_members = set(_MEMBER_NOT_FOUND_RE.findall(build_output))
    if not missing_members:
        return False

    print(f"  [AUTO-FIX] Detected missing members: {missing_members}")

    # Find all test filenames referenced in the build output
    test_filenames = set(_TEST_FILE_RE.findall(build_output))
    removed_any = False

    for test_filename in test_filenames:
        # Resolve: look in TESTS_DIR by filename (use _config for testability)
        test_path = _config.TESTS_DIR / test_filename
        if not test_path.is_file():
            continue

        text = test_path.read_text(errors="replace")
        blocks = extract_test_blocks(text)

        # Find blocks that call any of the missing members
        stale_keys = []
        for block in blocks:
            for member in missing_members:
                # Match .member( or ::member( call patterns
                pattern = r"(?:\.|::)" + re.escape(member) + r"\s*\("
                if re.search(pattern, block.text):
                    stale_keys.append(block.key)
                    print(f"  [AUTO-FIX] Removing stale test {block.key} "
                          f"(calls missing member '{member}')")
                    break

        if stale_keys:
            remove_tests_by_key(test_path, stale_keys)
            removed_any = True

    return removed_any



# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------
def configure(build_dir: Optional[Path] = None) -> BuildResult:
    bd = build_dir or BUILD_DIR
    try:
        r = subprocess.run(
            [
                "cmake", "-S", str(REPO_ROOT), "-B", str(bd),
                "-G", "Ninja",
                "-DCMAKE_BUILD_TYPE=Debug",
                "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
            ],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        out = (r.stdout or "") + "\n" + (r.stderr or "")
        return BuildResult(success=r.returncode == 0, stage="configure", output=out)
    except FileNotFoundError:
        return BuildResult(success=False, stage="configure",
                           output="cmake not found")


def build(build_dir: Optional[Path] = None, target: str = "all_tests") -> BuildResult:
    bd = build_dir or BUILD_DIR
    try:
        r = subprocess.run(
            [
                "cmake", "--build", str(bd),
                "--target", target,
                "--parallel", "--clean-first",
            ],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        out = (r.stdout or "") + "\n" + (r.stderr or "")
        return BuildResult(success=r.returncode == 0, stage="build", output=out)
    except FileNotFoundError:
        return BuildResult(success=False, stage="build",
                           output="cmake not found")


def run_tests(build_dir: Optional[Path] = None) -> BuildResult:
    bd = build_dir or BUILD_DIR
    try:
        r = subprocess.run(
            ["ctest", "--test-dir", str(bd), "--output-on-failure"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        out = (r.stdout or "") + "\n" + (r.stderr or "")
        return BuildResult(success=r.returncode == 0, stage="test", output=out)
    except FileNotFoundError:
        return BuildResult(success=False, stage="test",
                           output="ctest not found")


# ---------------------------------------------------------------------------
# AI fix loop
# ---------------------------------------------------------------------------
def attempt_ai_fix(
    build_dir: Optional[Path] = None,
    initial_output: str = "",
    lib_target: str = "project_lib",
) -> bool:
    """
    Attempt to fix build failures.

    Strategy (in order):
    1. Deterministic pre-fix: remove test blocks calling missing members.
    2. AI-assisted edits (up to MAX_FIX_ATTEMPTS).

    Returns True if the build eventually succeeds.
    """
    bd = build_dir or BUILD_DIR
    build_output = initial_output

    print(f"[ERROR] Build failed. Attempting up to {MAX_FIX_ATTEMPTS} AI-assisted fixes.")

    # ── Step 1: deterministic fix for "member not found" ──────────────────
    if _remove_stale_member_tests(build_output):
        print("  [AUTO-FIX] Stale tests removed. Rebuilding...")
        cfg = configure(bd)
        if cfg.success:
            bld = build(bd, lib_target)
            if bld.success:
                print("  [AUTO-FIX] Build fixed by removing stale tests.")
                return True
            build_output = bld.output
        else:
            build_output = cfg.output

    # ── Step 2: AI-assisted fix loop ──────────────────────────────────────
    for attempt in range(1, MAX_FIX_ATTEMPTS + 1):
        print(f"[INFO] AI fix attempt {attempt}/{MAX_FIX_ATTEMPTS}")

        parsed = generate_build_fix(build_output)
        if parsed is None:
            break

        summary = parsed.get("summary", "")
        blockers = parsed.get("blockers") or []
        edits = parsed.get("edits") or []

        print(f"[AI] summary: {summary}")
        if blockers:
            print("[AI] blockers:")
            for b in blockers:
                print(f"  - {b}")
            break

        if not edits:
            print("[INFO] AI returned no edits; stopping.")
            break

        applied = False
        for e in edits:
            path = e.get("path")
            content = e.get("content")
            if not path or content is None:
                continue
            target = REPO_ROOT / path
            # Safety: only allow edits to test files and src/ — not headers
            # in the include/ directory (those are production API contracts)
            if "include/" in str(target) and target.suffix in (".h", ".hpp"):
                print(f"[WARN] Skipping AI edit to header {target} (production API)")
                continue
            print(f"[PATCH] Applying edit to {target}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
            applied = True

        if not applied:
            print("[INFO] No valid edits applied; stopping.")
            break

        cfg = configure(bd)
        if not cfg.success:
            build_output = cfg.output
            print(f"[WARN] Config still failing after attempt {attempt}.")
            continue

        bld = build(bd, lib_target)
        build_output = bld.output
        if bld.success:
            print("[INFO] Build fixed by AI edits.")
            return True

        print(f"[WARN] Build still failing after attempt {attempt}.")

    print("[ERROR] Build could not be fixed automatically.")
    print(build_output[:2000])
    return False


# ---------------------------------------------------------------------------
# High-level helpers
# ---------------------------------------------------------------------------
def verify_source_compiles(build_dir: Optional[Path] = None) -> bool:
    """Configure + build the production library. Returns True on success."""
    bd = build_dir or BUILD_DIR
    print("[STEP] Verifying source compiles...")

    cfg = configure(bd)
    if not cfg.success:
        if "cmake not found" in cfg.output:
            print("[WARN] cmake not found; skipping source-compile check.")
            return True
        print("[ERROR] Configuration failed.")
        return attempt_ai_fix(bd, cfg.output, "project_lib")

    bld = build(bd, "project_lib")
    if not bld.success:
        print("[ERROR] Source build failed.")
        return attempt_ai_fix(bd, bld.output, "project_lib")

    print("[INFO] Source compiles successfully.")
    return True


def build_and_run_tests(build_dir: Optional[Path] = None) -> BuildResult:
    """Full configure -> build tests -> run tests."""
    bd = build_dir or BUILD_DIR

    cfg = configure(bd)
    if not cfg.success:
        return cfg

    bld = build(bd, "all_tests")
    if not bld.success:
        if attempt_ai_fix(bd, bld.output, "all_tests"):
            cfg2 = configure(bd)
            if not cfg2.success:
                return cfg2
            bld = build(bd, "all_tests")
            if not bld.success:
                return bld
        else:
            return bld

    return run_tests(bd)
