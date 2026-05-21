#!/usr/bin/env python3
"""
Klockwork Fix Orchestration
Orchestrates the process of identifying Klockwork issues and creating PR fixes.
Similar to orchestrate_mr_test.py for unit test automation.
"""

import os
import sys
import json
import argparse
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple


class KlockworkFixOrchestrator:
    """Orchestrates Klockwork issue detection and PR creation"""

    def __init__(self, repo_dir: str = "."):
        self.repo_dir = repo_dir
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.branch_name = f"klockwork-fixes-{self.timestamp}"
        self.issues_file = "klockwork_issues.json"
        self.fixes_file = f"klockwork_fixes_{self.timestamp}.json"

    def run_collection(self, source_dir: str = "src") -> bool:
        """Run Klockwork issue collection"""
        print(f"[*] Collecting Klockwork issues from {source_dir}...")

        script_path = os.path.join(
            os.path.dirname(__file__), "collect_klockwork_issues.py"
        )
        cmd = [
            sys.executable,
            script_path,
            "--source-dir",
            source_dir,
            "--output",
            self.issues_file,
        ]

        result = subprocess.run(cmd, cwd=self.repo_dir, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"[!] Error collecting issues: {result.stderr}", file=sys.stderr)
            return False

        print(result.stdout)
        return True

    def load_issues(self) -> Dict:
        """Load collected issues"""
        issues_path = os.path.join(self.repo_dir, self.issues_file)

        if not os.path.exists(issues_path):
            print(f"[!] Issues file not found: {issues_path}", file=sys.stderr)
            return None

        with open(issues_path, "r") as f:
            return json.load(f)

    def create_fix_branch(self) -> bool:
        """Create a new branch for fixes"""
        print(f"[*] Creating fix branch: {self.branch_name}...")

        try:
            # Ensure we're on main/master
            subprocess.run(
                ["git", "checkout", "main"],
                cwd=self.repo_dir,
                capture_output=True,
                check=False,
            )
            subprocess.run(
                ["git", "checkout", "master"],
                cwd=self.repo_dir,
                capture_output=True,
                check=False,
            )

            # Create new branch
            result = subprocess.run(
                ["git", "checkout", "-b", self.branch_name],
                cwd=self.repo_dir,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                print(f"[!] Failed to create branch: {result.stderr}", file=sys.stderr)
                return False

            print(f"[+] Branch created: {self.branch_name}")
            return True
        except Exception as e:
            print(f"[!] Error creating branch: {e}", file=sys.stderr)
            return False

    def generate_fixes_report(self, issues: Dict) -> Dict:
        """Generate a fixes report from collected issues"""
        print(f"[*] Generating fixes report...")

        fixes_report = {
            "timestamp": self.timestamp,
            "total_issues": issues.get("total_issues", 0),
            "by_severity": issues.get("by_severity", {}),
            "by_rule": issues.get("by_rule", {}),
            "fixes": [],
            "pr_description": self._generate_pr_description(issues),
        }

        # Categorize issues for fixing
        critical_issues = [i for i in issues.get("issues", []) if i["severity"] == "CRITICAL"]
        high_issues = [i for i in issues.get("issues", []) if i["severity"] == "HIGH"]

        print(f"[*] Found {len(critical_issues)} CRITICAL and {len(high_issues)} HIGH severity issues")

        # Generate fix suggestions
        for issue in critical_issues[:10]:  # Focus on top critical issues
            fix_suggestion = {
                "issue": issue,
                "fix_type": self._determine_fix_type(issue),
                "priority": "CRITICAL",
            }
            fixes_report["fixes"].append(fix_suggestion)

        for issue in high_issues[:5]:  # Focus on top high issues
            fix_suggestion = {
                "issue": issue,
                "fix_type": self._determine_fix_type(issue),
                "priority": "HIGH",
            }
            fixes_report["fixes"].append(fix_suggestion)

        return fixes_report

    def _determine_fix_type(self, issue: Dict) -> str:
        """Determine the type of fix needed"""
        rule_id = issue.get("rule_id", "")

        fix_types = {
            "SV.STRBO.BOUND_COPY": "replace_strcpy_with_strncpy",
            "SV.STRBO.BOUND_CAT": "replace_strcat_with_strncat",
            "SV.BANNED.FUNCTIONS": "replace_banned_function",
            "NPD.CHECK.CALL": "add_null_check",
            "UNINIT.STACK.MUST": "initialize_variable",
            "SV.FMT_STR.GENERIC": "add_format_string_literal",
            "RH.LEAK": "add_resource_cleanup",
            "SV.MISRA.COMPL_RETURN": "add_return_value_check",
        }

        return fix_types.get(rule_id, "manual_review_required")

    def _generate_pr_description(self, issues: Dict) -> str:
        """Generate PR description"""
        total = issues.get("total_issues", 0)
        critical = issues.get("by_severity", {}).get("CRITICAL", 0)
        high = issues.get("by_severity", {}).get("HIGH", 0)

        description = f"""# Klockwork Security Fixes

## Summary
This PR addresses {total} Klockwork static analysis violations found in the codebase.

### Issue Breakdown
- 🔴 **CRITICAL**: {critical} issues
- 🟠 **HIGH**: {high} issues

### Key Violations Fixed
"""

        # Add top violations
        by_rule = issues.get("by_rule", {})
        for rule_id in sorted(by_rule.keys(), key=lambda x: by_rule[x], reverse=True)[:5]:
            description += f"- {rule_id}: {by_rule[rule_id]} occurrences\n"

        description += """
### Testing
- [ ] Automated tests pass
- [ ] Security fixes validated
- [ ] No functionality regression
- [ ] Code review completed

### References
Generated by klockwork_automation framework
"""
        return description

    def commit_fixes(self, message: str = None) -> bool:
        """Commit the fixes"""
        if message is None:
            message = f"fix(security): Address Klockwork violations - {self.timestamp}"

        print(f"[*] Committing changes: {message}...")

        try:
            subprocess.run(
                ["git", "add", "-A"],
                cwd=self.repo_dir,
                capture_output=True,
                check=True,
            )

            result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.repo_dir,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0 and "nothing to commit" not in result.stderr:
                print(f"[!] Commit failed: {result.stderr}", file=sys.stderr)
                return False

            print("[+] Changes committed")
            return True
        except Exception as e:
            print(f"[!] Error committing: {e}", file=sys.stderr)
            return False

    def create_pull_request(self, issues: Dict) -> Optional[str]:
        """Create a pull request for the fixes"""
        print("[*] Creating pull request...")

        try:
            # Prepare PR data
            title = f"fix(security): Klockwork security violations - {len(issues.get('issues', []))} issues"
            body = issues.get("pr_description", "")
            base = "main"  # or "master"

            # Use gh CLI to create PR
            cmd = [
                "gh",
                "pr",
                "create",
                "--title",
                title,
                "--body",
                body,
                "--base",
                base,
            ]

            result = subprocess.run(
                cmd,
                cwd=self.repo_dir,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                print(f"[!] Failed to create PR: {result.stderr}", file=sys.stderr)
                return None

            pr_url = result.stdout.strip()
            print(f"[+] PR created: {pr_url}")
            return pr_url

        except Exception as e:
            print(f"[!] Error creating PR: {e}", file=sys.stderr)
            return None

    def save_report(self, report: Dict) -> bool:
        """Save the fixes report"""
        report_path = os.path.join(self.repo_dir, self.fixes_file)

        try:
            with open(report_path, "w") as f:
                json.dump(report, f, indent=2)
            print(f"[+] Report saved to {report_path}")
            return True
        except Exception as e:
            print(f"[!] Error saving report: {e}", file=sys.stderr)
            return False

    def run(
        self,
        source_dir: str = "src",
        create_pr: bool = False,
        auto_commit: bool = False,
    ) -> bool:
        """Run the full orchestration"""
        print("=" * 60)
        print("Klockwork Fix Orchestration")
        print("=" * 60)

        # Step 1: Collect issues
        if not self.run_collection(source_dir):
            return False

        # Step 2: Load issues
        issues = self.load_issues()
        if not issues:
            return False

        # Step 3: Create branch
        if not self.create_fix_branch():
            return False

        # Step 4: Generate fixes report
        report = self.generate_fixes_report(issues)
        if not self.save_report(report):
            return False

        # Step 5: Commit (if enabled)
        if auto_commit:
            if not self.commit_fixes():
                print("[!] Failed to commit, but continuing...")

        # Step 6: Create PR (if enabled)
        if create_pr:
            pr_url = self.create_pull_request(issues)
            if pr_url:
                report["pr_url"] = pr_url
                self.save_report(report)
                return True
            else:
                print("[!] Failed to create PR", file=sys.stderr)
                return False

        print("\n" + "=" * 60)
        print("Orchestration complete!")
        print(f"Branch: {self.branch_name}")
        print(f"Report: {self.fixes_file}")
        print("=" * 60)

        return True


def main():
    parser = argparse.ArgumentParser(
        description="Orchestrate Klockwork issue detection and PR creation"
    )
    parser.add_argument(
        "--repo-dir",
        default=".",
        help="Repository directory (default: current directory)",
    )
    parser.add_argument(
        "--source-dir",
        default="src",
        help="Source directory to analyze (default: src)",
    )
    parser.add_argument(
        "--create-pr",
        action="store_true",
        help="Create pull request after fixing",
    )
    parser.add_argument(
        "--auto-commit",
        action="store_true",
        help="Automatically commit fixes",
    )

    args = parser.parse_args()

    orchestrator = KlockworkFixOrchestrator(args.repo_dir)
    success = orchestrator.run(
        source_dir=args.source_dir,
        create_pr=args.create_pr,
        auto_commit=args.auto_commit,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
