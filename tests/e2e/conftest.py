from pathlib import Path

import pytest

try:
    from playwright.sync_api import sync_playwright
except Exception:  # pragma: no cover - playwright missing
    sync_playwright = None


def pytest_configure(config: pytest.Config) -> None:
    if sync_playwright is None:
        pytest.skip("playwright not installed", allow_module_level=True)
    else:
        with sync_playwright() as pw:
            chrome = Path(pw.chromium.executable_path)
            # locate headless_shell without triggering a download
            cache_dir = chrome.parents[2]
            headless_candidates = list(
                cache_dir.glob("chromium_headless_shell-*/**/headless_shell")
            )
            headless = headless_candidates[0] if headless_candidates else None
            if not chrome.exists() or headless is None or not headless.exists():
                pytest.skip(
                    "playwright browsers not installed",
                    allow_module_level=True,
                )
