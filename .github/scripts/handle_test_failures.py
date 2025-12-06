#!/usr/bin/env python3
"""
Handle test failures by creating or updating a PR with failure information.

This script:
1. Reads test output from test_output.log and failure summary from nightly_failures.json
2. Extracts failure signatures to detect duplicates
3. Checks for existing open PRs with the same failures
4. Updates existing PR or creates new one if needed
5. Uses a fixed branch name to avoid duplicates

Adapted for DocReview360 from BlogScriptCLI.
"""

import os
import sys
import hashlib
import re
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Any

try:
    from github import Github
except ImportError:
    print("ERROR: PyGithub not installed. Install with: pip install PyGithub")
    sys.exit(1)


def get_test_output() -> str:
    """Read test output from log file."""
    log_path = Path("test_output.log")
    if not log_path.exists():
        return "Test log file not found. Tests may have failed before output was captured."

    try:
        return log_path.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading test log: {e}"


def get_failure_summary() -> dict:
    """Read failure summary from JSON file."""
    summary_path = Path("nightly_failures.json")
    if not summary_path.exists():
        return {}

    try:
        return json.loads(summary_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Warning: Could not parse failure summary: {e}")
        return {}


def extract_failure_signature(test_output: str, failure_summary: dict) -> str:
    """
    Extract a signature/hash of the test failures to detect duplicates.

    Returns a hash based on:
    - Failing test names
    - Error messages (first line of each failure)
    - Security issues
    """
    # Extract failing test names from backend
    failing_tests = []
    test_pattern = r"FAILED\s+([^\s:]+::[^\s]+)"
    for match in re.finditer(test_pattern, test_output):
        failing_tests.append(match.group(1))

    # Extract first error line from each failure (before traceback)
    error_lines = []
    error_pattern = r"(FAILED[^\n]+\n[^\n]+\n[^\n]+)"
    for match in re.finditer(error_pattern, test_output):
        error_lines.append(match.group(1)[:200])  # First 200 chars

    # Add failure summary data if available
    summary_parts = []
    if failure_summary:
        if failure_summary.get("backend_failed"):
            summary_parts.append(f"backend:{failure_summary.get('total_backend_failures', 0)}")
        if failure_summary.get("frontend_failed"):
            summary_parts.append(f"frontend:{failure_summary.get('total_frontend_failures', 0)}")
        if failure_summary.get("security_failed"):
            summary_parts.append(f"security:{failure_summary.get('total_security_issues', 0)}")

    # Create signature from failing tests and error types
    signature_parts = sorted(failing_tests) + [line[:100] for line in error_lines[:10]] + summary_parts
    signature_text = "\n".join(signature_parts)

    # Create hash
    return hashlib.sha256(signature_text.encode()).hexdigest()[:16]


def find_existing_pr(repo: Any, branch_name: str, failure_signature: str) -> Optional[Any]:
    """
    Find an existing open PR for test failures.

    Returns the PR if found, None otherwise.
    """
    try:
        # Get all open PRs
        open_prs = repo.get_pulls(state="open", base=repo.default_branch)

        for pr in open_prs:
            # Check if PR is from our branch or has our title pattern
            if (pr.head.ref == branch_name or
                "Nightly Test Failures" in pr.title or
                pr.head.ref.startswith("nightly-test-failures")):
                return pr

        return None
    except Exception as e:
        print(f"Warning: Error checking for existing PRs: {e}")
        return None


def update_existing_pr(pr: Any, test_output: str, failure_summary: dict, failure_signature: str, default_branch: str) -> None:
    """
    Update an existing PR with new failure information.

    Adds a comment with the latest failure info and updates the PR body.
    """
    try:
        # Format failure summary for comment
        summary_text = ""
        if failure_summary:
            summary_text = f"""
**Backend Failures:** {failure_summary.get('total_backend_failures', 0)}
**Frontend Failures:** {failure_summary.get('total_frontend_failures', 0)}
**Security Issues:** {failure_summary.get('total_security_issues', 0)}
"""

        # Add a comment with the update
        comment_body = f"""## 🔄 Test Failures Update

**Time:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
**Commit:** {os.environ.get('GITHUB_SHA', 'unknown')}
**Failure Signature:** `{failure_signature}`
{summary_text}

The same test failures are still occurring. This PR has been updated with the latest test output.

<details>
<summary>Latest Test Output (truncated)</summary>

```
{test_output[:20000]}  # Limit comment size
```

</details>

---
*This comment was automatically added by the nightly test workflow.*
"""

        pr.create_issue_comment(comment_body)
        print(f"Added update comment to PR #{pr.number}")

        # Update PR body with latest timestamp
        current_body = pr.body or ""
        # Update the "Last updated" line if it exists
        updated_body = re.sub(
            r'\*Last updated:.*?\*',
            f'*Last updated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}*',
            current_body
        )

        # If no "Last updated" line exists, add it
        if "*Last updated:" not in updated_body:
            updated_body += f"\n\n*Last updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}*"

        pr.edit(body=updated_body)
        print(f"Updated PR #{pr.number} body")

    except Exception as e:
        print(f"Warning: Could not update PR: {e}")
        import traceback
        traceback.print_exc()


def create_pr_for_failures() -> None:
    """Create a PR documenting test failures."""
    # Get GitHub token from environment
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("ERROR: GITHUB_TOKEN environment variable not set")
        sys.exit(1)

    # Get repository info from GitHub Actions environment
    repo_name = os.environ.get("GITHUB_REPOSITORY")
    if not repo_name:
        print("ERROR: GITHUB_REPOSITORY environment variable not set")
        sys.exit(1)

    # Initialize GitHub client
    github = Github(token)
    repo = github.get_repo(repo_name)

    # Get test output and failure summary
    test_output = get_test_output()
    failure_summary = get_failure_summary()

    # Extract failure signature to detect duplicates
    failure_signature = extract_failure_signature(test_output, failure_summary)
    print(f"Failure signature: {failure_signature}")

    # Use fixed branch name to avoid duplicates
    branch_name = "nightly-test-failures"

    # Get default branch (usually 'main' or 'master')
    default_branch = repo.default_branch

    # Check for existing PR
    existing_pr = find_existing_pr(repo, branch_name, failure_signature)

    if existing_pr:
        print(f"Found existing PR #{existing_pr.number}: {existing_pr.html_url}")
        print("Updating existing PR instead of creating duplicate...")

        # Update existing PR with new failure information
        update_existing_pr(existing_pr, test_output, failure_summary, failure_signature, default_branch)
        return

    # No existing PR found, create new one
    print("No existing PR found. Creating new PR...")

    # Create or update branch using git
    import subprocess

    try:
        # Fetch latest from all branches
        subprocess.run(
            ["git", "fetch", "origin"],
            check=True,
            capture_output=True
        )

        # Check if branch exists remotely
        result = subprocess.run(
            ["git", "ls-remote", "--heads", "origin", branch_name],
            check=False,
            capture_output=True,
            text=True
        )

        if result.returncode == 0 and result.stdout.strip():
            # Branch exists remotely, checkout and track it
            try:
                # Try to checkout existing local branch first
                subprocess.run(
                    ["git", "checkout", branch_name],
                    check=False,
                    capture_output=True
                )
                # Pull latest changes
                subprocess.run(
                    ["git", "pull", "origin", branch_name],
                    check=True,
                    capture_output=True
                )
                print(f"Updated existing branch: {branch_name}")
            except subprocess.CalledProcessError:
                # Local branch doesn't exist, create tracking branch
                subprocess.run(
                    ["git", "checkout", "-b", branch_name, f"origin/{branch_name}"],
                    check=True,
                    capture_output=True
                )
                print(f"Checked out existing remote branch: {branch_name}")
        else:
            # Branch doesn't exist, create it from default branch
            subprocess.run(
                ["git", "checkout", "-b", branch_name, f"origin/{default_branch}"],
                check=True,
                capture_output=True
            )
            print(f"Created new branch: {branch_name}")
    except subprocess.CalledProcessError as e:
        print(f"Error with branch operations: {e}")
        if e.stdout:
            print(f"stdout: {e.stdout.decode() if isinstance(e.stdout, bytes) else e.stdout}")
        if e.stderr:
            print(f"stderr: {e.stderr.decode() if isinstance(e.stderr, bytes) else e.stderr}")
        sys.exit(1)

    # Prepare commit message and content
    commit_message = f"Update nightly test failures - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"

    # Format failure summary for report
    summary_section = ""
    if failure_summary:
        summary_section = f"""
## Failure Summary

- **Backend Tests:** {'❌ Failed' if failure_summary.get('backend_failed') else '✅ Passed'} ({failure_summary.get('total_backend_failures', 0)} failures)
- **Frontend Tests:** {'❌ Failed' if failure_summary.get('frontend_failed') else '✅ Passed'} ({failure_summary.get('total_frontend_failures', 0)} failures)
- **Security Scans:** {'❌ Failed' if failure_summary.get('security_failed') else '✅ Passed'} ({failure_summary.get('total_security_issues', 0)} issues)
"""

    # Create test failure report
    report_content = f"""# Nightly Test Failures Report

**Date:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
**Branch:** {default_branch}
**Commit:** {os.environ.get('GITHUB_SHA', 'unknown')}
**Failure Signature:** `{failure_signature}`
{summary_section}

> **Note:** This PR is automatically updated when the same failures occur. If you see this PR updated multiple times, it means the same test failures are still present.

## Test Output

<details>
<summary>Click to expand test output</summary>

```
{test_output[:40000]}  # Limit to 40k chars to avoid PR size limits
```

</details>

## Failure History

This PR tracks ongoing test failures. Each nightly run will update this PR if the same failures persist.

## Next Steps

1. Review the test failures above
2. Fix the failing tests
3. Verify locally before merging
4. This PR will automatically close when tests pass (or update if failures change)

---
*This PR was automatically created/updated by the nightly test workflow.*
*Last updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}*
"""

    # Write report to file
    report_path = Path("test_failures_report.md")
    report_path.write_text(report_content, encoding="utf-8")

    # Also save the full test log
    log_path = Path("test_output.log")
    if log_path.exists():
        # Copy log to a more descriptive name
        log_copy = Path("nightly_test_failures.log")
        log_copy.write_bytes(log_path.read_bytes())

    # Save failure summary JSON
    summary_path = Path("nightly_failures.json")
    if summary_path.exists():
        summary_copy = Path("nightly_failures_summary.json")
        summary_copy.write_bytes(summary_path.read_bytes())

    # Configure git
    import subprocess

    try:
        # Set git user (required for commits)
        subprocess.run(
            ["git", "config", "user.name", "github-actions[bot]"],
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"],
            check=True,
            capture_output=True
        )

        # Checkout the new branch
        subprocess.run(
            ["git", "checkout", branch_name],
            check=True,
            capture_output=True
        )

        # Add files
        files_added = False
        if report_path.exists():
            subprocess.run(["git", "add", str(report_path)], check=True, capture_output=True)
            files_added = True

        log_copy = Path("nightly_test_failures.log")
        if log_copy.exists():
            subprocess.run(["git", "add", "-f", str(log_copy)], check=True, capture_output=True)
            files_added = True
        elif log_path.exists():
            # Fallback: add original log if copy wasn't created
            subprocess.run(["git", "add", "-f", str(log_path)], check=True, capture_output=True)
            files_added = True

        summary_copy = Path("nightly_failures_summary.json")
        if summary_copy.exists():
            subprocess.run(["git", "add", "-f", str(summary_copy)], check=True, capture_output=True)
            files_added = True

        if not files_added:
            print("WARNING: No files to commit")
            return

        # Create commit
        result = subprocess.run(
            ["git", "commit", "-m", commit_message],
            check=True,
            capture_output=True,
            text=True
        )
        print(f"Created commit: {result.stdout}")

        # Push branch
        subprocess.run(
            ["git", "push", "origin", branch_name],
            check=True,
            capture_output=True
        )
        print(f"Pushed branch: {branch_name}")

    except subprocess.CalledProcessError as e:
        print(f"ERROR in git operations: {e}")
        if e.stdout:
            print(f"stdout: {e.stdout.decode() if isinstance(e.stdout, bytes) else e.stdout}")
        if e.stderr:
            print(f"stderr: {e.stderr.decode() if isinstance(e.stderr, bytes) else e.stderr}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Create PR
    try:
        # Check one more time if PR was created while we were working
        existing_pr = find_existing_pr(repo, branch_name, failure_signature)
        if existing_pr:
            print(f"PR #{existing_pr.number} was created by another process. Updating it instead...")
            update_existing_pr(existing_pr, test_output, failure_summary, failure_signature, default_branch)
            return

        pr_title = f"🚨 Nightly Test Failures - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
        pr_body = report_content

        pr = repo.create_pull(
            title=pr_title,
            body=pr_body,
            head=branch_name,
            base=default_branch
        )
        print(f"Created PR: {pr.html_url}")
        print(f"PR Number: {pr.number}")

    except Exception as e:
        # Check if error is because PR already exists
        if "already exists" in str(e).lower() or "pull request already exists" in str(e).lower():
            print("PR already exists, finding and updating it...")
            existing_pr = find_existing_pr(repo, branch_name, failure_signature)
            if existing_pr:
                update_existing_pr(existing_pr, test_output, failure_summary, failure_signature, default_branch)
            else:
                print("Could not find existing PR despite error message")
        else:
            print(f"ERROR creating PR: {e}")
            import traceback
            traceback.print_exc()
            # Don't exit - branch and commit were created successfully
            print(f"Branch '{branch_name}' was created but PR creation failed.")
            print(f"You can manually create a PR from branch: {branch_name}")


if __name__ == "__main__":
    create_pr_for_failures()

