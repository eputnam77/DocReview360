"""Helpers for running E2E tests in CI."""

from __future__ import annotations

from pathlib import Path

from ..stubs import record_task_completion


def task200(readme: Path | None = None) -> bool:
    """Return ``True`` if setup instructions mention Playwright installs."""

    record_task_completion(200)
    readme = readme or Path(__file__).resolve().parents[2] / "README.md"
    text = readme.read_text(encoding="utf-8")
    return "playwright install" in text.lower()
