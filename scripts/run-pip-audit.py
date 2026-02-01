#!/usr/bin/env python3
"""
Wrapper script for pip-audit that handles local packages and cache warnings gracefully.
"""

import os
import subprocess
import sys
from pathlib import Path


def run_pip_audit():
    """Run pip-audit with proper configuration for local packages."""

    # Set environment variables to suppress cache warnings
    env = os.environ.copy()
    env["PIP_AUDIT_SUPPRESS_CACHE_WARNINGS"] = "1"
    env["CACHECONTROL_DISABLE"] = "1"

    # Build the pip-audit command
    cmd = ["pip-audit", "--desc", "on", "--verbose"]  # Include descriptions  # More detailed output

    try:
        # Run pip-audit
        result = subprocess.run(
            cmd, env=env, capture_output=True, text=True, cwd=Path(__file__).parent.parent
        )

        # Filter out cache warnings and local package warnings
        output_lines: list[str] = []
        for line in result.stdout.split("\n"):
            # Skip cache warnings
            if "cachecontrol.controller:Cache entry deserialization failed" in line:
                continue
            # Skip local package warnings
            if "Dependency not found on PyPI and could not be audited" in line:
                continue
            if "Skip Reason" in line:
                continue
            if "docreview360" in line and "not found on PyPI" in line:
                continue
            if "fedstylevalidator" in line and "not found on PyPI" in line:
                continue
            output_lines.append(line)

        # Print filtered output
        print("\n".join(output_lines))

        # Return the exit code (0 for success, non-zero for vulnerabilities found)
        return result.returncode

    except FileNotFoundError:
        print("Error: pip-audit not found. Install it with: pip install pip-audit")
        return 1
    except Exception as e:
        print(f"Error running pip-audit: {e}")
        return 1


if __name__ == "__main__":
    exit_code = run_pip_audit()
    sys.exit(exit_code)
