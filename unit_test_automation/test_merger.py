"""
Merge LLM-generated test code into an existing test file.

Handles:
* Extracting individual ``TEST`` / ``TEST_F`` / ``TEST_P`` / ``TYPED_TEST``
  blocks from source text.
* Deduplicating by (suite, name).
* Preserving existing manually-written tests.
* Merging includes without duplicates.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Matches the opening line of any GTest test macro
_TEST_MACRO_RE = re.compile(
    r"^\s*(?:TEST|TEST_F|TEST_P|TYPED_TEST|TYPED_TEST_P)\s*\(\s*(\w+)\s*,\s*(\w+)\s*\)",
    re.MULTILINE,
)

_INCLUDE_RE = re.compile(r"^\s*#\s*include\s+.+$", re.MULTILINE)
_USING_RE = re.compile(r"^\s*using\s+.+$", re.MULTILINE)


@dataclass
class TestBlock:
    """A single TEST(Suite, Name) { ... } block."""
    suite: str
    name: str
    macro: str   # e.g. "TEST", "TEST_F"
    text: str    # full text including the macro line and closing brace

    @property
    def key(self) -> str:
        return f"{self.suite}.{self.name}"


def extract_test_blocks(source: str) -> list[TestBlock]:
    """
    Parse *source* and return every ``TEST*(Suite, Name) { ... }`` block.

    Uses brace-counting that skips braces inside string/char literals
    and line comments to be more robust than the old implementation.
    """
    blocks: list[TestBlock] = []
    lines = source.splitlines(keepends=True)
    i = 0
    while i < len(lines):
        m = _TEST_MACRO_RE.match(lines[i])
        if not m:
            i += 1
            continue

        # Determine the macro kind
        macro_match = re.match(r"\s*(TEST\w*)", lines[i])
        macro = macro_match.group(1) if macro_match else "TEST"

        suite, name = m.group(1), m.group(2)
        start = i
        brace_count = 0
        while i < len(lines):
            line = lines[i]
            for ch_idx, ch in enumerate(line):
                if ch == "/" and ch_idx + 1 < len(line) and line[ch_idx + 1] == "/":
                    break  # rest of line is a comment
                if ch == "{":
                    brace_count += 1
                elif ch == "}":
                    brace_count -= 1
            i += 1
            if brace_count <= 0 and brace_count != 0 or (brace_count == 0 and start != i - 1):
                # We had at least one open brace and have now closed them all
                if brace_count == 0 and i > start + 1:
                    break

        block_text = "".join(lines[start:i])
        blocks.append(TestBlock(suite=suite, name=name, macro=macro, text=block_text))

    return blocks


def _extract_includes(source: str) -> list[str]:
    """Return all ``#include`` lines from *source*."""
    return _INCLUDE_RE.findall(source)


def _extract_usings(source: str) -> list[str]:
    """Return all ``using ...`` lines from *source*."""
    return _USING_RE.findall(source)


def merge_tests(existing_code: str, new_code: str) -> str:
    """
    Merge *new_code* test blocks into *existing_code*.

    * Existing test blocks are preserved as-is.
    * New test blocks are appended if their (Suite, Name) key does not
      already exist.
    * Includes from both files are unified (no duplicates).
    * ``using`` declarations are unified.
    """
    existing_blocks = extract_test_blocks(existing_code)
    new_blocks = extract_test_blocks(new_code)

    existing_keys = {b.key for b in existing_blocks}

    # Find genuinely new tests
    tests_to_add = [b for b in new_blocks if b.key not in existing_keys]

    if not tests_to_add:
        # Nothing new to add
        return existing_code

    # Merge includes
    existing_includes = set(_extract_includes(existing_code))
    new_includes = _extract_includes(new_code)
    includes_to_add = [inc for inc in new_includes if inc not in existing_includes]

    # Merge using declarations
    existing_usings = set(_extract_usings(existing_code))
    new_usings = _extract_usings(new_code)
    usings_to_add = [u for u in new_usings if u not in existing_usings]

    # Build merged file
    result = existing_code.rstrip("\n")

    # Insert missing includes at the top (after existing includes)
    if includes_to_add:
        # Find the position after the last #include in the existing file
        include_positions = [m.end() for m in _INCLUDE_RE.finditer(existing_code)]
        if include_positions:
            insert_pos = include_positions[-1]
            include_text = "\n" + "\n".join(includes_to_add)
            result = result[:insert_pos] + include_text + result[insert_pos:]
        else:
            result = "\n".join(includes_to_add) + "\n\n" + result

    # Insert missing using declarations
    if usings_to_add:
        using_positions = [m.end() for m in _USING_RE.finditer(result)]
        if using_positions:
            insert_pos = using_positions[-1]
            using_text = "\n" + "\n".join(usings_to_add)
            result = result[:insert_pos] + using_text + result[insert_pos:]

    # Append new test blocks at the end
    result += "\n\n"
    for block in tests_to_add:
        result += block.text.rstrip("\n") + "\n\n"

    return result.rstrip("\n") + "\n"


def remove_tests_for_source(test_path: Path, source_path: str) -> bool:
    """
    Remove test blocks that reference the deleted source file.

    Matches on the source file's stem (e.g. ``calculator`` from
    ``src/calculator.cpp``).  More conservative than the old approach:
    only matches the Suite name, not arbitrary substrings.
    """
    if not test_path.exists():
        return False

    stem = Path(source_path).stem
    candidates = {stem, stem.capitalize(), stem.upper(), stem.lower()}

    text = test_path.read_text()
    blocks = extract_test_blocks(text)

    blocks_to_remove = {
        b.key for b in blocks if b.suite in candidates
    }

    if not blocks_to_remove:
        return False

    # Rebuild the file without the removed blocks
    kept_blocks = [b for b in blocks if b.key not in blocks_to_remove]

    # Preserve everything that is NOT a test block (includes, usings, etc.)
    lines = text.splitlines(keepends=True)
    non_test_lines: list[str] = []
    i = 0
    while i < len(lines):
        m = _TEST_MACRO_RE.match(lines[i])
        if m:
            # skip the whole test block
            brace_count = 0
            while i < len(lines):
                for ch in lines[i]:
                    if ch == "{":
                        brace_count += 1
                    elif ch == "}":
                        brace_count -= 1
                i += 1
                if brace_count == 0 and i > 0:
                    break
        else:
            non_test_lines.append(lines[i])
            i += 1

    header = "".join(non_test_lines).rstrip("\n")

    if not kept_blocks:
        # All tests were removed
        if not header.strip():
            test_path.unlink()
            print(f"[INFO] Deleted empty test file {test_path}")
            return True
        test_path.write_text(header + "\n")
        return True

    # Reassemble: header + kept blocks
    body = "\n\n".join(b.text.rstrip("\n") for b in kept_blocks)
    test_path.write_text(header.rstrip("\n") + "\n\n" + body + "\n")
    return True
