import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

import pytest

try:
    from playwright.sync_api import sync_playwright
except Exception:
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


@pytest.fixture(scope="session")
def e2e_backend_url() -> str:
    backend = os.getenv("E2E_BACKEND_URL")
    if not backend:
        pytest.skip("E2E_BACKEND_URL not set; run scripts/run_e2e.py", allow_module_level=True)
    return backend.rstrip("/")


@pytest.fixture(scope="session")
def e2e_frontend_url() -> str:
    frontend = os.getenv("E2E_FRONTEND_URL")
    if not frontend:
        pytest.skip("E2E_FRONTEND_URL not set; run scripts/run_e2e.py", allow_module_level=True)
    return frontend.rstrip("/")


@pytest.fixture(scope="session")
def e2e_seed_data(e2e_backend_url: str) -> dict:
    req = Request(f"{e2e_backend_url}/e2e/seed", method="POST")
    with urlopen(req, timeout=10) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return payload
