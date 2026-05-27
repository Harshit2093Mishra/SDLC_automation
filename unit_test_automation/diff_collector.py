"""
Collect changed files and **actual diff content** for a branch range.

Key improvement over the old ``collect_pr_diff.py``:
* Returns per-file unified diff content (not just file names).
* Classifies files by status (added / modified / deleted).
* Only implementation files (.cpp/.c/.cc/.cxx) appear in modified_sources.
  Changed headers are resolved to their owning source files automatically.
"""
from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from unit_test_automation.config import (
    CPP_SUFFIXES, CPP_SOURCE_SUFFIXES, CPP_HEADER_SUFFIXES,
    TEST_NAME_TOKENS, REPO_ROOT,
)


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


def _is_cpp_source(path: str) -> bool:
    """True for implementation files only (.cpp, .c, .cc, .cxx)."""
    return Path(path).suffix.lower() in CPP_SOURCE_SUFFIXES


def _is_cpp_header(path: str) -> bool:
    """True for header files only (.h, .hpp, .hh, .hxx)."""
    return Path(path).suffix.lower() in CPP_HEADER_SUFFIXES


def _is_cpp(path: str) -> bool:
    return Path(path).suffix.lower() in CPP_SUFFIXES


def _find_source_for_header(header_path: str, cwd: Optional[str] = None) -> Optional[str]:
    """
    Given a changed header (e.g. ``include/example/calculator.hpp``),
    find the implementation file that owns it.

    Strategy (in order):
    1. Search src/ for a .cpp with the same stem.
    2. Broad search of the whole repo for a .cpp whose name matches the stem.

    Returns a repo-relative POSIX path (e.g. ``src/calculator.cpp``) or None.
    """
    stem = Path(header_path).stem
    root = Path(cwd).resolve() if cwd else REPO_ROOT

    # 1) Direct stem match in src/
    for suffix in CPP_SOURCE_SUFFIXES:
        candidate = root / "src" / f"{stem}{suffix}"
        if candidate.is_file():
            return candidate.relative_to(root).as_posix()

    # 2) Broad search (exclude .git and build dirs)
    for suffix in CPP_SOURCE_SUFFIXES:
        for match in root.rglob(f"{stem}{suffix}"):
            if ".git" not in match.parts and "build" not in match.parts:
                return match.relative_to(root).as_posix()

    return None


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class ChangedFile:
    """One file touched by the MR."""
    path: str
    status: str        # "A" added, "M" modified, "D" deleted, "R" renamed, etc.
    diff_content: str = ""
    is_cpp: bool = False
    is_test: bool = False
    is_header: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DiffResult:
    """Aggregated diff information for the entire MR."""
    base: str
    head: str
    changed_files: list[ChangedFile] = field(default_factory=list)

    # Convenience views (populated by collect_diff)
    source_files: list[str] = field(default_factory=list)      # impl files (.cpp etc.)
    test_files: list[str] = field(default_factory=list)
    changed_headers: list[str] = field(default_factory=list)   # header files that changed
    added_sources: list[str] = field(default_factory=list)
    modified_sources: list[str] = field(default_factory=list)
    deleted_sources: list[str] = field(default_factory=list)

    def get_diff_for(self, path: str) -> str:
        """Return the unified diff content for a specific file path."""
        for f in self.changed_files:
            if f.path == path:
                return f.diff_content
        return ""

    def get_combined_diff_for_source(self, source_path: str) -> str:
        """
        Return the unified diff for a source file PLUS any of its changed headers.
        Gives the LLM a full picture of what changed in this MR.
        """
        stem = Path(source_path).stem
        parts = [self.get_diff_for(source_path)]
        for hdr in self.changed_headers:
            if Path(hdr).stem == stem:
                hdr_diff = self.get_diff_for(hdr)
                if hdr_diff:
                    parts.append(hdr_diff)
        return "\n\n".join(p for p in parts if p)

    def to_dict(self) -> dict:
        return {
            "base": self.base,
            "head": self.head,
            "changed_files": [f.to_dict() for f in self.changed_files],
            "source_files": self.source_files,
            "test_files": self.test_files,
            "changed_headers": self.changed_headers,
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

    Only implementation files (.cpp/.c/.cc/.cxx) go into source_files /
    added_sources / modified_sources / deleted_sources.

    When a header changes, we resolve its owning source file (e.g.
    ``include/example/calculator.hpp`` -> ``src/calculator.cpp``) and add
    that source to modified_sources so its tests get regenerated.
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
        status = parts[0][0]   # first char: A, M, D, R, C ...
        path = parts[-1]       # for renames the new name is last
        cf = ChangedFile(
            path=path,
            status=status,
            is_cpp=_is_cpp(path),
            is_test=_looks_like_test(path),
            is_header=_is_cpp_header(path),
        )
        files_by_path[path] = cf

    # 2) Per-file unified diff content
    diff_output = _run_git(
        ["diff", "--unified=5", f"{base}...{head}"],
        cwd=cwd,
    )

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
            parts = line.split(" b/", 1)
            current_path = parts[1] if len(parts) > 1 else None
        current_lines.append(line)
    _flush()

    result.changed_files = list(files_by_path.values())

    # 3) Build convenience lists
    seen_sources: set[str] = set()

    def _register_source(path: str, status: str) -> None:
        if path in seen_sources:
            return
        seen_sources.add(path)
        result.source_files.append(path)
        if status == "A":
            result.added_sources.append(path)
        elif status in ("M", "R"):
            result.modified_sources.append(path)
        elif status == "D":
            result.deleted_sources.append(path)

    for cf in result.changed_files:
        if cf.is_test:
            result.test_files.append(cf.path)
            continue

        if cf.is_header:
            # Track the header, then resolve its owning source file
            result.changed_headers.append(cf.path)
            owner = _find_source_for_header(cf.path, cwd=cwd)
            if owner:
                _register_source(owner, "M")
            continue

        if _is_cpp_source(cf.path):
            _register_source(cf.path, cf.status)

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
