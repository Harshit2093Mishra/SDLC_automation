"""
Collect changed files and **actual diff content** for a branch range.

Key improvement over the old ``collect_pr_diff.py``:
* Returns per-file unified diff content (not just file names).
* Classifies files by status (added / modified / deleted).
"""
from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from unit_test_automation.config import CPP_SUFFIXES, TEST_NAME_TOKENS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _run_git(args: list[str], cwd: Optional[str] = None) -> str:
    completed = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or f"git {' '.join(args)} failed")
    return completed.stdout.strip()


def _looks_like_test(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return any(token in normalized for token in TEST_NAME_TOKENS)


def _is_cpp(path: str) -> bool:
    return Path(path).suffix.lower() in CPP_SUFFIXES


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class ChangedFile:
    """One file touched by the MR."""
    path: str
    status: str  # "A" added, "M" modified, "D" deleted, "R" renamed, etc.
    diff_content: str = ""  # unified diff for this file
    is_cpp: bool = False
    is_test: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DiffResult:
    """Aggregated diff information for the entire MR."""
    base: str
    head: str
    changed_files: list[ChangedFile] = field(default_factory=list)

    # Convenience views (populated by collect_diff)
    source_files: list[str] = field(default_factory=list)      # non-test C++ sources
    test_files: list[str] = field(default_factory=list)         # test C++ files
    added_sources: list[str] = field(default_factory=list)      # new source files
    modified_sources: list[str] = field(default_factory=list)   # modified source files
    deleted_sources: list[str] = field(default_factory=list)    # deleted source files

    def get_diff_for(self, path: str) -> str:
        """Return the unified diff content for a specific file."""
        for f in self.changed_files:
            if f.path == path:
                return f.diff_content
        return ""

    def to_dict(self) -> dict:
        return {
            "base": self.base,
            "head": self.head,
            "changed_files": [f.to_dict() for f in self.changed_files],
            "source_files": self.source_files,
            "test_files": self.test_files,
            "added_sources": self.added_sources,
            "modified_sources": self.modified_sources,
            "deleted_sources": self.deleted_sources,
        }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def guess_test_path(source_path: str) -> str:
    """Convention: src/foo.cpp -> tests/foo_test.cpp"""
    return str(Path("tests") / f"{Path(source_path).stem}_test.cpp")


def collect_diff(base: str, head: str, cwd: Optional[str] = None) -> DiffResult:
    """
    Collect per-file diff information between *base* and *head*.

    Returns a :class:`DiffResult` with unified diff content for every
    changed C++ file and convenience lists for source / test / deleted files.
    """
    result = DiffResult(base=base, head=head)

    # 1) File names + status  (A/M/D/R...)
    name_status_output = _run_git(
        ["diff", "--name-status", f"{base}...{head}"],
        cwd=cwd,
    )

    files_by_path: dict[str, ChangedFile] = {}
    for line in name_status_output.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0][0]  # first char: A, M, D, R, C ...
        path = parts[-1]      # for renames the new name is last
        cf = ChangedFile(
            path=path,
            status=status,
            is_cpp=_is_cpp(path),
            is_test=_looks_like_test(path),
        )
        files_by_path[path] = cf

    # 2) Per-file unified diff content
    diff_output = _run_git(
        ["diff", "--unified=5", f"{base}...{head}"],
        cwd=cwd,
    )

    # Split the combined diff output into per-file chunks
    current_path: Optional[str] = None
    current_lines: list[str] = []

    def _flush():
        nonlocal current_path, current_lines
        if current_path and current_path in files_by_path:
            files_by_path[current_path].diff_content = "\n".join(current_lines)
        current_lines = []

    for line in diff_output.splitlines():
        if line.startswith("diff --git"):
            _flush()
            # extract b/path from "diff --git a/old b/new"
            parts = line.split(" b/", 1)
            current_path = parts[1] if len(parts) > 1 else None
        current_lines.append(line)
    _flush()  # last file

    result.changed_files = list(files_by_path.values())

    # 3) Build convenience lists
    for cf in result.changed_files:
        if not cf.is_cpp or cf.is_test:
            continue
        result.source_files.append(cf.path)
        if cf.status == "A":
            result.added_sources.append(cf.path)
        elif cf.status == "M":
            result.modified_sources.append(cf.path)
        elif cf.status == "D":
            result.deleted_sources.append(cf.path)

    for cf in result.changed_files:
        if cf.is_cpp and cf.is_test:
            result.test_files.append(cf.path)

    return result


# ---------------------------------------------------------------------------
# Stand-alone CLI (backward compat)
# ---------------------------------------------------------------------------
def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Collect MR diff with content.")
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    diff = collect_diff(args.base, args.head)
    indent = 2 if args.pretty else None
    print(json.dumps(diff.to_dict(), indent=indent))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
