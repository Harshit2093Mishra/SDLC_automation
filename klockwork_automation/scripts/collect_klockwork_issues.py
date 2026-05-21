#!/usr/bin/env python3
"""
Klockwork Issue Collector
Analyzes C/C++ source code for Klockwork static analysis violations
and collects the issues for fixing.
"""

import os
import sys
import json
import argparse
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# Klockwork rules patterns
KLOCKWORK_PATTERNS = {
    "NPD.CHECK.CALL": {
        "patterns": [
            r"(\w+\s*=\s*malloc\([^)]*\))\s*;\s*\*\1",
            r"(\w+\s*=\s*\w+\([^)]*\))\s*;[^;]*\*\1",
        ],
        "description": "Null Pointer Dereference",
        "severity": "CRITICAL",
    },
    "SV.STRBO.BOUND_COPY": {
        "patterns": [r"\bstrcpy\s*\(", r"\bstrcpy_s\s*\("],
        "description": "Buffer Overflow via String Copy",
        "severity": "CRITICAL",
    },
    "SV.STRBO.BOUND_CAT": {
        "patterns": [r"\bstrcat\s*\("],
        "description": "Buffer Overflow via String Concatenation",
        "severity": "CRITICAL",
    },
    "SV.BANNED.FUNCTIONS": {
        "patterns": [
            r"\bgets\s*\(",
            r"\bsprintf\s*\(",
            r"\bscanf\s*\(",
            r"\bstrcpy\s*\(",
            r"\bstrcat\s*\(",
        ],
        "description": "Use of Banned / Unsafe Functions",
        "severity": "CRITICAL",
    },
    "UNINIT.STACK.MUST": {
        "patterns": [
            r"(int|float|double|char|long|short)\s+(\w+)\s*;(?!.*=)",
        ],
        "description": "Uninitialized Stack Variable",
        "severity": "HIGH",
    },
    "SV.FMT_STR.GENERIC": {
        "patterns": [
            r"printf\s*\(\s*(\w+)\s*\)",
            r"fprintf\s*\([^,]*,\s*(\w+)\s*\)",
        ],
        "description": "Format String Vulnerability",
        "severity": "CRITICAL",
    },
    "RH.LEAK": {
        "patterns": [
            r"(malloc|calloc|realloc)\s*\([^)]*\)",
            r"(fopen|open)\s*\([^)]*\)",
        ],
        "description": "Resource Leak",
        "severity": "HIGH",
    },
    "SV.MISRA.COMPL_RETURN": {
        "patterns": [
            r"(remove|fopen|open|fclose|malloc)\s*\([^)]*\)\s*;(?!\s*if)",
        ],
        "description": "Unchecked Return Value",
        "severity": "MEDIUM",
    },
}


class KlockworkIssue:
    """Represents a single Klockwork issue"""

    def __init__(
        self,
        rule_id: str,
        file_path: str,
        line_number: int,
        code_snippet: str,
        description: str,
        severity: str,
    ):
        self.rule_id = rule_id
        self.file_path = file_path
        self.line_number = line_number
        self.code_snippet = code_snippet
        self.description = description
        self.severity = severity

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "rule_id": self.rule_id,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "code_snippet": self.code_snippet,
            "description": self.description,
            "severity": self.severity,
        }


class KlockworkCollector:
    """Collects Klockwork issues from C/C++ source code"""

    def __init__(self, source_dir: str = "."):
        self.source_dir = source_dir
        self.issues: List[KlockworkIssue] = []

    def find_source_files(self) -> List[str]:
        """Find all C/C++ source files"""
        extensions = (".c", ".cpp", ".cc", ".cxx", ".h", ".hpp", ".hxx")
        source_files = []

        for root, dirs, files in os.walk(self.source_dir):
            # Skip build and dependency directories
            dirs[:] = [d for d in dirs if d not in ["build", "_deps", ".git"]]

            for file in files:
                if file.endswith(extensions):
                    source_files.append(os.path.join(root, file))

        return source_files

    def analyze_file(self, file_path: str) -> List[KlockworkIssue]:
        """Analyze a single file for Klockwork violations"""
        issues = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception as e:
            print(f"Error reading {file_path}: {e}", file=sys.stderr)
            return issues

        for line_num, line in enumerate(lines, 1):
            # Check each pattern
            for rule_id, rule_info in KLOCKWORK_PATTERNS.items():
                for pattern in rule_info["patterns"]:
                    if re.search(pattern, line):
                        issue = KlockworkIssue(
                            rule_id=rule_id,
                            file_path=file_path,
                            line_number=line_num,
                            code_snippet=line.strip(),
                            description=rule_info["description"],
                            severity=rule_info["severity"],
                        )
                        issues.append(issue)
                        break  # Only report once per line per rule

        return issues

    def collect_all(self) -> List[KlockworkIssue]:
        """Collect all Klockwork issues from source directory"""
        source_files = self.find_source_files()
        print(f"Found {len(source_files)} source file(s) to analyze...")

        for file_path in source_files:
            print(f"Analyzing {file_path}...")
            file_issues = self.analyze_file(file_path)
            self.issues.extend(file_issues)

        return self.issues

    def save_to_json(self, output_file: str) -> None:
        """Save collected issues to JSON file"""
        data = {
            "total_issues": len(self.issues),
            "by_severity": self._count_by_severity(),
            "by_rule": self._count_by_rule(),
            "issues": [issue.to_dict() for issue in self.issues],
        }

        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)

        print(f"Saved {len(self.issues)} issues to {output_file}")

    def _count_by_severity(self) -> Dict[str, int]:
        """Count issues by severity"""
        counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for issue in self.issues:
            counts[issue.severity] = counts.get(issue.severity, 0) + 1
        return counts

    def _count_by_rule(self) -> Dict[str, int]:
        """Count issues by rule ID"""
        counts = {}
        for issue in self.issues:
            counts[issue.rule_id] = counts.get(issue.rule_id, 0) + 1
        return counts

    def print_summary(self) -> None:
        """Print summary of collected issues"""
        print("\n=== Klockwork Issues Summary ===")
        print(f"Total issues found: {len(self.issues)}")

        severity_counts = self._count_by_severity()
        print("\nBy Severity:")
        for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            count = severity_counts.get(severity, 0)
            if count > 0:
                print(f"  {severity}: {count}")

        print("\nBy Rule:")
        rule_counts = self._count_by_rule()
        for rule_id in sorted(rule_counts.keys()):
            print(f"  {rule_id}: {rule_counts[rule_id]}")

        if self.issues:
            print("\nTop Issues:")
            for issue in sorted(
                self.issues,
                key=lambda x: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}.get(
                    x.severity, 4
                ),
            )[:5]:
                print(
                    f"  [{issue.severity}] {issue.rule_id} at {issue.file_path}:{issue.line_number}"
                )


def main():
    parser = argparse.ArgumentParser(
        description="Collect Klockwork static analysis violations from C/C++ source code"
    )
    parser.add_argument(
        "--source-dir",
        default=".",
        help="Source directory to analyze (default: current directory)",
    )
    parser.add_argument(
        "--output",
        default="klockwork_issues.json",
        help="Output JSON file for collected issues",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Only print summary, don't save to file",
    )

    args = parser.parse_args()

    collector = KlockworkCollector(args.source_dir)
    collector.collect_all()
    collector.print_summary()

    if not args.summary_only:
        collector.save_to_json(args.output)


if __name__ == "__main__":
    main()
