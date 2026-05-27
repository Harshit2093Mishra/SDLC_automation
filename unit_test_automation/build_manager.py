"""
CMake configure / build / test helpers and AI-assisted build-fix loop.

Key improvements over the old monolithic script:
* Functions return result objects instead of calling ``sys.exit()``.
* ``attempt_ai_fix`` properly reconfigures after every patch.
* ``build_output`` is always initialised before use.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from unit_test_automation.config import REPO_ROOT, BUILD_DIR
from unit_test_automation.llm_client import generate_build_fix

MAX_FIX_ATTEMPTS = 5


@dataclass
class BuildResult:
    success: bool
    stage: str = ""        # "configure", "build", "test", "success"
    output: str = ""


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
                           output="[ERROR] cmake not found. Install cmake and add it to PATH.")


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
                           output="[ERROR] cmake not found. Install cmake and add it to PATH.")


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
                           output="[ERROR] ctest not found. Install cmake/ctest and add it to PATH.")


# ---------------------------------------------------------------------------
# AI fix loop
# ---------------------------------------------------------------------------
def attempt_ai_fix(
    build_dir: Optional[Path] = None,
    initial_output: str = "",
    lib_target: str = "project_lib",
) -> bool:
    """
    Attempt up to ``MAX_FIX_ATTEMPTS`` AI-assisted source edits to fix
    compilation errors.  Returns ``True`` if the build eventually succeeds.
    """
    bd = build_dir or BUILD_DIR
    build_output = initial_output

    print(f"[ERROR] Build failed. Attempting up to {MAX_FIX_ATTEMPTS} AI-assisted fixes.")

    for attempt in range(1, MAX_FIX_ATTEMPTS + 1):
        print(f"[INFO] AI fix attempt {attempt}/{MAX_FIX_ATTEMPTS}")

        parsed = generate_build_fix(build_output)
        if parsed is None:
            break

        summary = parsed.get("summary", "")
        blockers = parsed.get("blockers", [])
        edits = parsed.get("edits", [])

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
            print(f"[PATCH] Applying edit to {target}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
            applied = True

        if not applied:
            print("[INFO] No valid edits applied; stopping.")
            break

        # Reconfigure *and* rebuild after each patch
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
    """Configure + build the production library.  Returns ``True`` on success."""
    bd = build_dir or BUILD_DIR
    print("[STEP] Verifying source compiles...")

    cfg = configure(bd)
    if not cfg.success:
        print("[ERROR] Configuration failed.")
        return attempt_ai_fix(bd, cfg.output, "project_lib")

    bld = build(bd, "project_lib")
    if not bld.success:
        print("[ERROR] Source build failed.")
        return attempt_ai_fix(bd, bld.output, "project_lib")

    print("[INFO] Source compiles successfully.")
    return True


def build_and_run_tests(build_dir: Optional[Path] = None) -> BuildResult:
    """
    Full configure -> build tests -> run tests.

    Returns a :class:`BuildResult` with ``success=True`` if everything passes.
    """
    bd = build_dir or BUILD_DIR

    cfg = configure(bd)
    if not cfg.success:
        return cfg

    bld = build(bd, "all_tests")
    if not bld.success:
        # Try AI fix, then retry
        if attempt_ai_fix(bd, bld.output, "all_tests"):
            # Need to reconfigure + rebuild after fix
            cfg2 = configure(bd)
            if not cfg2.success:
                return cfg2
            bld = build(bd, "all_tests")
            if not bld.success:
                return bld
        else:
            return bld

    return run_tests(bd)
