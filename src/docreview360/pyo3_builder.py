"""Stub PyO3 wheel builder used for testing (Task 108)."""

from __future__ import annotations

from pathlib import Path


def build_stub_wheel(path: str | Path) -> Path:
    """Create a dummy wheel file at ``path`` and return it."""
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("wheel")
    return dest
