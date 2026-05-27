"""
Resolve C++ header files by parsing ``#include`` directives in source files.

Searches configurable include directories instead of assuming headers
sit next to the ``.cpp`` file.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from unit_test_automation.config import INCLUDE_DIRS, REPO_ROOT

_INCLUDE_RE = re.compile(r'^\s*#\s*include\s+"([^"]+)"', re.MULTILINE)


def find_header(include_path: str, extra_dirs: Optional[list[Path]] = None) -> Optional[Path]:
    """
    Search known include directories for *include_path*.

    For example, given ``"example/calculator.hpp"`` and an include dir
    ``<repo>/include``, this returns ``<repo>/include/example/calculator.hpp``
    if it exists.
    """
    search_dirs = list(INCLUDE_DIRS)
    if extra_dirs:
        search_dirs.extend(extra_dirs)

    for d in search_dirs:
        candidate = d / include_path
        if candidate.is_file():
            return candidate.resolve()

    # Also try repo root
    candidate = REPO_ROOT / include_path
    if candidate.is_file():
        return candidate.resolve()

    return None


def resolve_headers_for_source(source_path: Path) -> dict[str, str]:
    """
    Parse all ``#include "..."`` directives in *source_path* and return
    a mapping of ``{include_path: header_content}`` for every header
    that can be located.
    """
    if not source_path.is_file():
        return {}

    source_text = source_path.read_text(errors="replace")
    includes = _INCLUDE_RE.findall(source_text)

    # Also search relative to the source file's own directory
    extra_dirs = [source_path.parent]

    headers: dict[str, str] = {}
    for inc in includes:
        resolved = find_header(inc, extra_dirs=extra_dirs)
        if resolved:
            headers[inc] = resolved.read_text(errors="replace")

    return headers
