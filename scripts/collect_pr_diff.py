#!/usr/bin/env python3
"""
Collect changed files for a PR/branch range and focus on C++ implementation headers.

Examples:
  python3 scripts/collect_pr_diff.py --base origin/main --head HEAD
  python3 scripts/collect_pr_diff.py --base HEAD~1 --head HEAD --pretty
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

CPP_SUFFIXES = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx"}
TEST_NAME_TOKENS = ("/test", "/tests", "_test.", "Test.")


def run_git(args: list[str]) -> str:
    completed = subprocess.run(["git", *args], capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or f"git {' '.join(args)} failed")
    return completed.stdout.strip()


def looks_like_test(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return any(token in normalized for token in TEST_NAME_TOKENS)


def guess_test_path(source_path: str) -> str:
    p = Path(source_path)
    stem = p.stem
    return str(Path("tests") / f"{stem}_test.cpp")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True, help="Base git ref (e.g. origin/main)")
    parser.add_argument("--head", default="HEAD", help="Head git ref (default: HEAD)")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()

    # Use three-dot range to mirror PR semantics (changes on HEAD since merge-base with base).
    diff_output = run_git(["diff", "--name-only", f"{args.base}...{args.head}"])
    files = [line.strip() for line in diff_output.splitlines() if line.strip()]

    changed_cpp = [f for f in files if Path(f).suffix.lower() in CPP_SUFFIXES]
    source_files = [f for f in changed_cpp if not looks_like_test(f)]
    test_files = [f for f in changed_cpp if looks_like_test(f)]

    payload = {
        "base": args.base,
        "head": args.head,
        "changed_files": files,
        "changed_cpp_files": changed_cpp,
        "source_files": source_files,
        "test_files": test_files,
        "suggested_test_targets": [
            {"source": src, "suggested_test": guess_test_path(src)} for src in source_files
        ],
    }

    if args.pretty:
        print(json.dumps(payload, indent=2))
    else:
        print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
