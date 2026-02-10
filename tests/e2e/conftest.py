import importlib.util
import json
import os
import sys
import types
from pathlib import Path
from urllib.request import Request, urlopen

import pytest

playwright_spec = importlib.util.find_spec("playwright")
sync_api_spec = importlib.util.find_spec("playwright.sync_api") if playwright_spec else None

if sync_api_spec is None:
    sync_playwright = None
    if "playwright.sync_api" not in sys.modules:
        stub_module = types.ModuleType("playwright.sync_api")

        class Page:  # noqa: D401 - simple stub for type imports
            """Stub Playwright Page."""

        stub_module.Page = Page
        sys.modules["playwright.sync_api"] = stub_module
        if "playwright" not in sys.modules:
            root_module = types.ModuleType("playwright")
            root_module.sync_api = stub_module
            sys.modules["playwright"] = root_module
else:
    from playwright.sync_api import sync_playwright


def _playwright_ready() -> tuple[bool, str]:
    if sync_playwright is None:
        return False, "playwright not installed"
    try:
        with sync_playwright() as pw:
            chrome = Path(pw.chromium.executable_path)
            # locate headless_shell without triggering a download
            cache_dir = chrome.parents[2]
            headless_candidates = list(
                cache_dir.glob("chromium_headless_shell-*/**/headless_shell")
            )
            headless = headless_candidates[0] if headless_candidates else None
            if not chrome.exists() or headless is None or not headless.exists():
                return False, "playwright browsers not installed"
    except Exception as exc:  # noqa: BLE001 - surface skip reason in constrained envs
        return False, f"playwright unavailable: {exc}"
    return True, ""


def pytest_configure(config: pytest.Config) -> None:
    ready, reason = _playwright_ready()
    config._playwright_ready = ready
    config._playwright_skip_reason = reason


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if getattr(config, "_playwright_ready", True):
        return
    reason = getattr(config, "_playwright_skip_reason", "playwright not installed")
    skip_marker = pytest.mark.skip(reason=reason)
    for item in items:
        item.add_marker(skip_marker)


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
