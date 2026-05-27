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


def _scan_block(lines: list[str], start: int) -> int:
    """
    Given that lines[start] is a TEST macro line, return the index of the
    line AFTER the closing brace of that block.

    Uses brace-counting that ignores braces inside // comments and
    double-quoted strings.
    """
    brace_count = 0
    opened = False
    i = start
    while i < len(lines):
        line = lines[i]
        in_string = False
        j = 0
        while j < len(line):
            ch = line[j]
            if in_string:
                if ch == "\\" and j + 1 < len(line):
                    j += 1      # skip escaped char
                elif ch == '"':
                    in_string = False
            else:
                if ch == "/" and j + 1 < len(line) and line[j + 1] == "/":
                    break       # rest of line is a comment
                if ch == '"':
                    in_string = True
                elif ch == "{":
                    brace_count += 1
                    opened = True
                elif ch == "}":
                    brace_count -= 1
            j += 1
        i += 1
        if opened and brace_count == 0:
            break
    return i


def extract_test_blocks(source: str) -> list[TestBlock]:
    """
    Parse *source* and return every ``TEST*(Suite, Name) { ... }`` block.
    """
    blocks: list[TestBlock] = []
    lines = source.splitlines(keepends=True)
    i = 0
    while i < len(lines):
        m = _TEST_MACRO_RE.match(lines[i])
        if not m:
            i += 1
            continue
        macro_match = re.match(r"\s*(TEST\w*)", lines[i])
        macro = macro_match.group(1) if macro_match else "TEST"
        suite, name = m.group(1), m.group(2)
        start = i
        i = _scan_block(lines, start)
        block_text = "".join(lines[start:i])
        blocks.append(TestBlock(suite=suite, name=name, macro=macro, text=block_text))
    return blocks


def _extract_header_lines(lines: list[str]) -> list[str]:
    """Return only the lines that are NOT part of any test block."""
    header_lines: list[str] = []
    i = 0
    while i < len(lines):
        if _TEST_MACRO_RE.match(lines[i]):
            i = _scan_block(lines, i)   # skip the whole block
        else:
            header_lines.append(lines[i])
            i += 1
    return header_lines


def _extract_includes(source: str) -> list[str]:
    return _INCLUDE_RE.findall(source)


def _extract_usings(source: str) -> list[str]:
    return _USING_RE.findall(source)


def merge_tests(existing_code: str, new_code: str) -> str:
    """
    Merge *new_code* test blocks into *existing_code*.

    * Existing test blocks are preserved as-is.
    * New test blocks are appended ONLY if their (Suite, Name) key does
      not already exist — duplicates are silently dropped.
    * Includes from both files are unified (no duplicates).
    * ``using`` declarations are unified.
    """
    existing_blocks = extract_test_blocks(existing_code)
    new_blocks = extract_test_blocks(new_code)
    existing_keys = {b.key for b in existing_blocks}
    tests_to_add = [b for b in new_blocks if b.key not in existing_keys]

    if not tests_to_add:
        return existing_code

    # Merge includes
    existing_includes = set(_extract_includes(existing_code))
    includes_to_add = [
        inc for inc in _extract_includes(new_code)
        if inc not in existing_includes
    ]

    # Merge using declarations
    existing_usings = set(_extract_usings(existing_code))
    usings_to_add = [
        u for u in _extract_usings(new_code)
        if u not in existing_usings
    ]

    result = existing_code.rstrip("\n")

    if includes_to_add:
        positions = [m.end() for m in _INCLUDE_RE.finditer(existing_code)]
        if positions:
            insert_pos = positions[-1]
            result = result[:insert_pos] + "\n" + "\n".join(includes_to_add) + result[insert_pos:]
        else:
            result = "\n".join(includes_to_add) + "\n\n" + result

    if usings_to_add:
        positions = [m.end() for m in _USING_RE.finditer(result)]
        if positions:
            insert_pos = positions[-1]
            result = result[:insert_pos] + "\n" + "\n".join(usings_to_add) + result[insert_pos:]

    result += "\n\n"
    for block in tests_to_add:
        result += block.text.rstrip("\n") + "\n\n"

    return result.rstrip("\n") + "\n"


def remove_tests_for_source(test_path: Path, source_path: str) -> bool:
    """Remove all test blocks whose Suite name matches the deleted source stem."""
    if not test_path.exists():
        return False
    stem = Path(source_path).stem
    candidates = {stem, stem.capitalize(), stem.upper(), stem.lower()}
    text = test_path.read_text()
    blocks = extract_test_blocks(text)
    keys = [b.key for b in blocks if b.suite in candidates]
    if not keys:
        return False
    return remove_tests_by_key(test_path, keys)


def remove_tests_by_key(test_path: Path, keys_to_remove: list[str]) -> bool:
    """
    Remove specific test blocks from *test_path* by their ``Suite.Name`` key.

    Rebuilds the file as:
      header (non-test lines) + kept_block texts only

    This avoids the double-append bug of text.replace() + re-appending blocks.
    """
    if not test_path.exists() or not keys_to_remove:
        return False

    keys_set = set(keys_to_remove)
    text = test_path.read_text()
    blocks = extract_test_blocks(text)

    remove_keys = {b.key for b in blocks if b.key in keys_set}
    if not remove_keys:
        return False

    kept_blocks = [b for b in blocks if b.key not in remove_keys]
    print(f"  [CLEANUP] Removing stale test blocks: {sorted(remove_keys)}")

    # Build header: all lines that are NOT part of ANY test block
    lines = text.splitlines(keepends=True)
    header = "".join(_extract_header_lines(lines)).rstrip("\n")

    if not kept_blocks:
        if not header.strip():
            test_path.unlink()
            print(f"  [INFO] Deleted empty test file {test_path}")
            return True
        test_path.write_text(header + "\n")
        return True

    body = "\n\n".join(b.text.rstrip("\n") for b in kept_blocks)
    test_path.write_text(header.rstrip("\n") + "\n\n" + body + "\n")
    return True
