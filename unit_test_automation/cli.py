"""
CLI entry point for the unit-test auto-generation tool.

Usage:
    # From repo root:
    python -m unit_test_automation --base origin/main --head HEAD

    # With explicit MR link (informational; base/head still required):
    python -m unit_test_automation --mr-link https://github.com/org/repo/pull/42 \
        --base origin/main --head feature/my-branch

    # Skip the final build+test step (useful for dry-runs):
    python -m unit_test_automation --base origin/main --head HEAD --skip-build
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m unit_test_automation",
        description="Automated C++ unit test generation for Merge Requests.",
    )
    parser.add_argument(
        "--mr-link",
        type=str,
        default="",
        help="Merge Request / PR link (informational; not used programmatically in MVP).",
    )
    parser.add_argument(
        "--base",
        type=str,
        default="origin/main",
        help="Base git ref for diff (default: origin/main).",
    )
    parser.add_argument(
        "--head",
        type=str,
        default="HEAD",
        help="Head git ref for diff (default: HEAD).",
    )
    parser.add_argument(
        "--build-dir",
        type=str,
        default="",
        help="Override the CMake build directory.",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Generate tests but skip the build and test step.",
    )

    args = parser.parse_args()

    if args.mr_link:
        print(f"[INFO] MR link: {args.mr_link}")

    build_dir = Path(args.build_dir) if args.build_dir else None

    # Import here so import errors surface cleanly
    from unit_test_automation.orchestrator import run

    run(
        base=args.base,
        head=args.head,
        build_dir=build_dir,
        skip_build=args.skip_build,
    )


if __name__ == "__main__":
    main()
