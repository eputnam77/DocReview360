#!/usr/bin/env python3
"""Wrapper that forces UTF-8 mode before invoking semgrep (needed on Windows)."""
import os
import subprocess
import sys

os.environ["PYTHONUTF8"] = "1"
sys.exit(
    subprocess.run(
        ["semgrep", "--config", "p/ci", "--metrics=off", "--disable-version-check"],
        env={**os.environ},
    ).returncode
)
