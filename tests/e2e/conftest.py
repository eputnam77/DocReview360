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
            headless = Path(str(chrome).replace("chrome", "headless_shell"))
            if not chrome.exists() or not headless.exists():
                pytest.skip(
                    "playwright browsers not installed",
                    allow_module_level=True,
                )
