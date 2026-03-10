# SPDX-License-Identifier: MIT
"""Utility to create a minimal stub wheel for PyO3 extensions (Task 108)."""

from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile


def build_stub_wheel(path: str | Path, package: str = "ruv_fann", version: str = "0.1.0") -> Path:
    """Create a minimal wheel archive at ``path`` and return it."""

    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    dist_info = f"{package}-{version}.dist-info"
    with ZipFile(dest, "w") as zf:
        zf.writestr(f"{dist_info}/WHEEL", "Wheel-Version: 1.0\nGenerator: stub")
        zf.writestr(f"{dist_info}/METADATA", f"Name: {package}\nVersion: {version}\n")
        # empty module to satisfy import when installed
        zf.writestr(f"{package}/__init__.py", "")

    return dest
