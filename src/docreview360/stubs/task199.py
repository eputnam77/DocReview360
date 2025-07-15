"""Playwright E2E baseline helpers."""

from __future__ import annotations

from ..stubs import record_task_completion

try:  # pragma: no cover - optional dependency
    import importlib

    playwright_version = importlib.import_module("playwright").__version__
except Exception:  # pragma: no cover - Playwright not installed
    playwright_version = ""


def task199() -> str:
    """Return the installed Playwright version.

    The test suite uses this as a simple sanity check that the
    Playwright browsers were installed correctly for the E2E
    baseline. Returning an empty string indicates the dependency
    is missing.
    """

    record_task_completion(199)
    return str(playwright_version)
