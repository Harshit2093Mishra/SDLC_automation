"""
Centralized configuration: paths, constants, and file-type definitions.
"""
from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Repository layout
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent

INCLUDE_DIRS: list[Path] = [
    REPO_ROOT / "include",
    REPO_ROOT / "src",
]

TESTS_DIR = REPO_ROOT / "tests"
BUILD_DIR = REPO_ROOT / "build"

# ---------------------------------------------------------------------------
# Automation assets
# ---------------------------------------------------------------------------
_AUTOMATION_DIR = Path(__file__).resolve().parent

PROMPT_TEMPLATE = _AUTOMATION_DIR / "prompts" / "unit_test_generator.prompt.yml"
BUILD_FIX_PROMPT = _AUTOMATION_DIR / "prompts" / "build_fix.prompt.yml"
EVAL_SCRIPT = _AUTOMATION_DIR / "scripts" / "run_prompt_eval.sh"

# ---------------------------------------------------------------------------
# C++ file classification
# ---------------------------------------------------------------------------
CPP_SOURCE_SUFFIXES: set[str] = {".c", ".cc", ".cpp", ".cxx"}
CPP_HEADER_SUFFIXES: set[str] = {".h", ".hh", ".hpp", ".hxx"}
CPP_SUFFIXES: set[str] = CPP_SOURCE_SUFFIXES | CPP_HEADER_SUFFIXES

TEST_NAME_TOKENS: tuple[str, ...] = ("/test", "/tests", "_test.", "Test.")
