# SPDX-License-Identifier: MIT
"""Automate semantic version bump and changelog generation."""

from __future__ import annotations

import subprocess
from pathlib import Path


def run() -> None:
    """Generate changelog from git commits."""
    output = subprocess.check_output(["git", "log", "--pretty=%s", "HEAD~20..HEAD"]).decode()
    Path("CHANGELOG.md").write_text(output)


if __name__ == "__main__":
    run()
